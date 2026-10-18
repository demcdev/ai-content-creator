"""
Video 2 · ¿Cómo sabemos la edad del universo si nadie estuvo allí? — versión en PAPEL RECORTADO EN CAPAS.

Criterios (16-oct-2026): siempre algo visual mientras habla la voz, poco texto, cada medida con un gráfico,
animación calmada (movimiento continuo, sin temblor), sin siluetas de personas innecesarias.
Escenas = las de «Escaleta audiovisual.md» (E01…E39); los tiempos salen de tiempos.json (voz real de Raúl).

Uso (desde esta carpeta):
  python video02_papel.py --frame 95.0 f.png        un fotograma
  python video02_papel.py --rango 60 120             tramo de prueba -> salida/papel_rango_60_120.mp4 (con audio)
  python video02_papel.py                            video completo por partes de 60 s -> salida/video-02-papel.mp4
  python video02_papel.py --rehacer                  vuelve a recortar las piezas fijas (cache_papel/)
"""
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

AQUI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.dirname(AQUI)
HERR = os.path.normpath(os.path.join(V2, '..', 'montaje'))
sys.path.insert(0, HERR)
import papel as PP      # noqa: E402
import pintura as P     # noqa: E402

FUENTE = os.path.join(HERR, 'fuentes', 'inter', 'Inter-VF.ttf')
ORIG = os.path.join(V2, 'Licencias', 'originales')
CACHE = os.path.join(AQUI, 'cache_papel')
SALIDA = os.path.join(AQUI, 'salida')
AUDIO = os.path.join(SALIDA, '_audio-con-musica.wav')
W, H, FPS = 1920, 1080, 24

AMBAR = (240, 178, 76)
CREMA = (238, 228, 204)
TINTA = (34, 30, 42)
AZUL = (92, 132, 204)
VERDE = (104, 170, 104)
ROJO = (206, 84, 62)

with open(os.path.join(AQUI, 'tiempos.json'), encoding='utf-8') as _f:
    _TJ = json.load(_f)
F = _TJ['frases']
DUR = round(float(_TJ['total']) + 1.6, 2)
N = int(DUR * FPS)


def a(i):
    return F[i]['ini']


def b(i):
    return F[i]['fin']


def w(i, trozo):
    f = F[i]
    pos = f['texto'].find(trozo)
    if pos < 0:
        raise ValueError((i, trozo))
    return f['ini'] + (f['fin'] - f['ini']) * pos / len(f['texto'])

# ------------------------------------------------------------------ utilidades


def suave(u):
    u = min(1.0, max(0.0, u))
    return 0.5 - 0.5 * math.cos(math.pi * u)


def lerp(p, q, t):
    return p + (q - p) * t


_fuentes = {}


def fuente(px, peso=900):
    key = (int(px), peso)
    if key not in _fuentes:
        f = ImageFont.truetype(FUENTE, max(6, int(px)))
        try:
            f.set_variation_by_axes([32 if px > 60 else 14, peso])
        except Exception:
            pass
        _fuentes[key] = f
    return _fuentes[key]


def mascara_texto(L, texto, cx, cy, tam, peso=900):
    f = fuente(tam * L.k, peso)
    im = Image.new('L', (L.w, L.h), 0)
    ImageDraw.Draw(im).text(L.p(cx, cy), texto, font=f, fill=255, anchor='mm')
    return np.asarray(im, np.float32) / 255


def circulo(L, cx, cy, r):
    return L.mascara(lambda d, L: d.ellipse([*L.p(cx - r, cy - r), *L.p(cx + r, cy + r)], fill=255), 0)


def poli(L, pts, suav=0):
    pts = P.suave_poli(pts, suav) if suav else pts
    return L.mascara(lambda d, L: d.polygon(L.ps(pts), fill=255), 0)

# ------------------------------------------------------------------ piezas fijas (se recortan una vez)


PIEZAS = {}


def guardar(nombre, pl):
    PIEZAS[nombre] = (pl.capa(), pl.L)


def pieza_fondo():
    L = P.Lienzo(-160, -100, 2080, 1180, 1.05)
    pl = PP.Plano(L, 3)
    pl.pieza(np.ones((L.h, L.w), np.float32), PP.degradado((12, 15, 42), (36, 46, 92), L.y0, L.y1), sombra=None, bisel=0, textura=1.3)
    xx, yy = L.xy
    an = math.radians(-22)
    d = ((xx - 960) * (-math.sin(an)) + (yy - 520) * math.cos(an)) / 210
    ond = (L.fbm(380, 3, 7) - 0.5) * 1.6
    for off, ancho, col, al, rg in ((0.0, 1.1, (44, 62, 140), 0.32, 0.9), (0.15, 0.62, (64, 86, 160), 0.22, 0.8),
                                    (-0.12, 0.5, (178, 132, 76), 0.26, 0.9), (0.05, 0.26, (226, 192, 140), 0.22, 1.0)):
        m = (np.abs(d - off + ond * 0.5) < ancho).astype(np.float32)
        if col[0] > 220:
            m = m * (L.fbm(120, 3, 11) > 0.47)
        pl.pieza(m, col, rasgado=rg, sombra=(1, 2, 3, 0.18), alfa=al, bisel=0.15, textura=1.5)
    for sem, col, al in ((21, (30, 92, 104), 0.18), (23, (76, 52, 120), 0.15)):
        m = (L.fbm(300, 4, sem) > 0.66).astype(np.float32)
        pl.pieza(m, col, rasgado=0.9, sombra=(1, 2, 3, 0.15), alfa=al, bisel=0.1, textura=1.5)
    pl.sumar(P.estrellas(L.w, L.h, 1300, 31, k=L.k * 0.8, densidad=np.exp(-d * d), sesgo=3.2))
    guardar('fondo', pl)


def pieza_tapa():
    L = P.Lienzo(0, 0, W, H, 1.0)
    pl = PP.Plano(L, 5)
    pl.pieza(np.ones((L.h, L.w), np.float32), (16, 14, 22), sombra=None, bisel=0, textura=1.4)
    guardar('tapa', pl)


def pieza_tierra():
    L = P.Lienzo(-110, -110, 110, 110, 2.0)
    pl = PP.Plano(L, 41)
    disco = circulo(L, 0, 0, 92)
    pl.pieza(disco, (52, 104, 176), sombra=None, bisel=0.6)
    rnd = np.random.RandomState(4)
    for _ in range(5):
        cx, cy = rnd.uniform(-60, 60), rnd.uniform(-60, 60)
        pts = [(cx + math.cos(t) * r, cy + math.sin(t) * r) for t, r in zip(np.linspace(0, 6.28, 9)[:-1], rnd.uniform(14, 40, 8))]
        pl.pieza(poli(L, pts, 5), (92, 150, 82), rasgado=0.8, sombra=(1, 1.5, 1.5, 0.35), cortar=disco, bisel=0.3)
    for _ in range(4):
        cx, cy = rnd.uniform(-70, 70), rnd.uniform(-70, 70)
        pl.pieza(poli(L, PP.mechon(cx, cy, rnd.uniform(-0.4, 0.4), 70, 16)), (244, 244, 248), rasgado=0.9, sombra=None, alfa=0.7, cortar=disco, bisel=0)
    xx, yy = L.xy
    pl.pieza(((xx * 0.6 + yy * 0.3) > 28).astype(np.float32) * disco, (14, 16, 44), rasgado=0.7, sombra=None, alfa=0.55, cortar=disco, bisel=0)
    guardar('tierra', pl)


def pieza_sol():
    L = P.Lienzo(-150, -150, 150, 150, 1.8)
    pl = PP.Plano(L, 43)
    rayos = []
    for i in range(16):
        t = i / 16 * 2 * math.pi
        r1 = 138 if i % 2 == 0 else 116
        rayos += [(math.cos(t - 0.14) * 80, math.sin(t - 0.14) * 80), (math.cos(t) * r1, math.sin(t) * r1), (math.cos(t + 0.14) * 80, math.sin(t + 0.14) * 80)]
    pl.pieza(poli(L, rayos), (246, 196, 82), rasgado=0.4, sombra=None, bisel=0.5)
    pl.pieza(circulo(L, 0, 0, 86), (238, 140, 54), sombra=(2, 3, 3, 0.4), bisel=0.6)
    pl.pieza(circulo(L, -14, -14, 58), (250, 186, 80), rasgado=0.9, sombra=None, alfa=0.7, bisel=0)
    guardar('sol', pl)


def _estrella_pts(n, r1, r2, rot=-math.pi / 2):
    pts = []
    for i in range(2 * n):
        t = rot + i * math.pi / n
        r = r1 if i % 2 == 0 else r2
        pts.append((math.cos(t) * r, math.sin(t) * r))
    return pts


def pieza_estrella():
    L = P.Lienzo(-90, -90, 90, 90, 2.2)
    pl = PP.Plano(L, 47)
    pl.pieza(poli(L, _estrella_pts(5, 78, 32)), (248, 236, 196), rasgado=0.1, sombra=None, bisel=0.8)
    guardar('estrella', pl)


def pieza_regla():
    """Tira de papel = 13 797 millones de años (1 400 px); la astilla ámbar del final = 23 millones."""
    L = P.Lienzo(-740, -60, 740, 60, 1.6)
    pl = PP.Plano(L, 51)
    pl.pieza(L.mascara(lambda d, L: d.rectangle([*L.p(-700, -26), *L.p(700, 26)], fill=255), 0), CREMA, rasgado=0.15, sombra=None, bisel=0.5)
    marcas = Image.new('L', (L.w, L.h), 0)
    d = ImageDraw.Draw(marcas)
    for i in range(0, 15):
        x = -700 + i * 1400 / 13.797
        if x > 700:
            break
        d.line([*L.p(x, -26), *L.p(x, -6 if i % 5 else 6)], fill=255, width=int(2.4 * L.k))
    pl.pieza(np.asarray(marcas, np.float32) / 255, TINTA, sombra=None, bisel=0, textura=0.5)
    pl.pieza(L.mascara(lambda d, L: d.rectangle([*L.p(697.7, -26), *L.p(700, 26)], fill=255), 0), (226, 120, 40), sombra=None, bisel=0)
    guardar('regla', pl)


def pieza_lupa():
    L = P.Lienzo(-130, -130, 130, 130, 2.0)
    pl = PP.Plano(L, 53)
    dentro = circulo(L, 0, 0, 104)
    pl.pieza(dentro, (30, 36, 72), sombra=None, bisel=0)
    pl.pieza(L.mascara(lambda d, L: d.rectangle([*L.p(-140, -60), *L.p(34, 60)], fill=255), 0), CREMA, sombra=None, cortar=dentro, bisel=0.3)
    pl.pieza(L.mascara(lambda d, L: d.rectangle([*L.p(-58, -60), *L.p(34, 60)], fill=255), 0), (226, 120, 40), sombra=(-3, 0, 3, 0.35), cortar=dentro, bisel=0.3)
    pl.pieza(L.mascara(lambda d, L: d.rectangle([*L.p(-118, -60), *L.p(-110, 10)], fill=255), 0), TINTA, sombra=None, cortar=dentro, bisel=0)
    pl.pieza(circulo(L, 0, 0, 124) * (1 - circulo(L, 0, 0, 104)), (52, 44, 40), sombra=None, bisel=0.8)
    pl.pieza(L.mascara(lambda d, L: d.ellipse([*L.p(-80, -88), *L.p(-20, -50)], fill=255), 0), (255, 255, 255), rasgado=0.6, sombra=None, alfa=0.25, cortar=dentro, bisel=0)
    guardar('lupa', pl)


def pieza_rollo():
    L = P.Lienzo(-20, -40, 20, 40, 3.0)
    pl = PP.Plano(L, 95)
    pl.pieza(L.mascara(lambda d, L: d.rounded_rectangle([*L.p(-13, -32), *L.p(13, 32)], radius=10 * L.k, fill=255), 0), (226, 214, 188), sombra=None, bisel=1.0)
    pl.pieza(L.mascara(lambda d, L: d.rectangle([*L.p(4, -30), *L.p(11, 30)], fill=255), 0), (150, 138, 116), sombra=None, alfa=0.5, bisel=0)
    guardar('rollo', pl)


def _galaxia(pl, L, r, col=(196, 178, 230), nucleo=(250, 226, 170), cortar=None, fondo=None):
    if fondo is not None:
        pl.pieza(circulo(L, 0, 0, r * 1.2), fondo, sombra=None, bisel=0.3)
    for brazo in range(2):
        pts = []
        for s in np.linspace(0.05, 1, 30):
            t = brazo * math.pi + s * 4.2
            rr = r * (0.1 + s * 0.82)
            pts.append((math.cos(t) * rr, math.sin(t) * rr * 0.62))
        m = L.mascara(lambda d, L, pts=pts: d.line(L.ps(pts), fill=255, width=int(r * 0.18 * L.k), joint='curve'), 0)
        pl.pieza(m, col, rasgado=0.9, sombra=None, alfa=0.8, cortar=cortar, bisel=0)
    pl.pieza(circulo(L, 0, 0, r * 0.2), nucleo, rasgado=0.7, sombra=None, cortar=cortar, bisel=0)


def pieza_reloj(i):
    """Los tres relojes: 0 = fondo cósmico (marmolado), 1 = expansión (galaxia), 2 = estrellas viejas (gigante roja)."""
    L = P.Lienzo(-190, -190, 190, 190, 1.8)
    pl = PP.Plano(L, 61 + i)
    pl.pieza(circulo(L, 0, 0, 172), (30, 34, 66), sombra=None, bisel=0.7)
    pl.pieza(circulo(L, 0, 0, 150), CREMA, sombra=(2, 3, 3, 0.45), bisel=0.5)
    marcas = Image.new('L', (L.w, L.h), 0)
    d = ImageDraw.Draw(marcas)
    for j in range(12):
        t = j / 12 * 2 * math.pi
        r0 = 122 if j % 3 else 112
        d.line([*L.p(math.cos(t) * r0, math.sin(t) * r0), *L.p(math.cos(t) * 140, math.sin(t) * 140)], fill=255, width=int((3 if j % 3 else 6) * L.k))
    pl.pieza(np.asarray(marcas, np.float32) / 255, TINTA, sombra=None, bisel=0, textura=0.5)
    emb = circulo(L, 0, 0, 78)
    if i == 0:
        pl.pieza(emb, (204, 120, 66), sombra=None, bisel=0.3)
        for sem, col in ((3, (70, 120, 170)), (5, (232, 170, 92)), (7, (150, 70, 52))):
            m = (P.fbm(L.w, L.h, int(18 * L.k), 3, 300 + sem) > 0.55).astype(np.float32)
            pl.pieza(m, col, rasgado=0.8, sombra=None, alfa=0.75, cortar=emb, bisel=0)
    elif i == 1:
        pl.pieza(emb, (26, 30, 66), sombra=None, bisel=0.3)
        _galaxia(pl, L, 70, cortar=emb)
    else:
        pl.pieza(emb, (20, 22, 50), sombra=None, bisel=0.3)
        pl.pieza(circulo(L, 0, 0, 48), (214, 92, 52), rasgado=0.3, sombra=(1, 2, 2, 0.4), cortar=emb, bisel=0.5)
        pl.pieza(circulo(L, -10, -10, 30), (238, 136, 70), rasgado=0.9, sombra=None, alfa=0.7, cortar=emb, bisel=0)
    guardar('reloj%d' % i, pl)


def pieza_aguja(nombre, largo, ancho):
    L = P.Lienzo(-ancho * 1.4 - 10, -largo - 10, ancho * 1.4 + 10, ancho * 2 + 10, 2.0)
    pl = PP.Plano(L, len(nombre) + int(largo))
    pts = [(-ancho / 2, ancho * 1.4), (-ancho * 0.32, -largo * 0.8), (0, -largo), (ancho * 0.32, -largo * 0.8), (ancho / 2, ancho * 1.4)]
    pl.pieza(poli(L, pts), (24, 22, 30), sombra=None, bisel=0.5)
    pl.pieza(circulo(L, 0, 0, ancho * 0.7), (214, 168, 80), sombra=(0.6, 1, 1, 0.5), bisel=0.9)
    guardar(nombre, pl)


def pieza_separador(i):
    L = P.Lienzo(-26, -560, 26, 560, 1.4)
    pl = PP.Plano(L, 80 + i)
    pl.pieza(L.mascara(lambda d, L: d.rectangle([*L.p(-16, -560), *L.p(16, 560)], fill=255), 0), (40, 34, 52), rasgado=0.9, sombra=None, bisel=0.4)
    guardar('separador%d' % i, pl)


def _baldosa(L, x, y, s, tab_der=True, tab_abajo=True):
    def fn(d, L):
        d.rounded_rectangle([*L.p(x, y), *L.p(x + s, y + s)], radius=8 * L.k, fill=255)
        r = s * 0.16
        if tab_der:
            d.ellipse([*L.p(x + s - r * 0.4, y + s / 2 - r), *L.p(x + s + r * 1.6, y + s / 2 + r)], fill=255)
        if tab_abajo:
            d.ellipse([*L.p(x + s / 2 - r, y + s - r * 0.4), *L.p(x + s / 2 + r, y + s + r * 1.6)], fill=255)
    return L.mascara(fn, 0)


def pieza_puzle():
    """El modelo del universo como un rompecabezas de 3 × 3 al que le falta la pieza de arriba a la derecha."""
    L = P.Lienzo(-250, -250, 250, 250, 1.6)
    pl = PP.Plano(L, 101)
    s = 140
    rnd = np.random.RandomState(8)
    for fila in range(3):
        for col in range(3):
            if (fila, col) == (0, 2):
                continue
            x, y = -215 + col * (s + 4), -215 + fila * (s + 4)
            m = _baldosa(L, x, y, s, col < 2, fila < 2)
            pl.pieza(m, [(34, 44, 96), (44, 56, 116)][(fila + col) % 2], sombra=(2, 3, 3, 0.45), bisel=0.6)
            pts = [(x + rnd.uniform(15, s - 15), y + rnd.uniform(15, s - 15)) for _ in range(6)]
            mk = L.mascara(lambda d, L, pts=pts: [d.ellipse([*L.p(px - 3, py - 3), *L.p(px + 3, py + 3)], fill=255) for px, py in pts], 0)
            pl.pieza(mk * m, (236, 222, 180), sombra=None, bisel=0, textura=0.4)
    anillo = circulo(L, 0, 0, 150) * (1 - circulo(L, 0, 0, 144))
    pl.pieza(anillo * (L.xy[0] < 75 + 0 * L.xy[1]) + anillo * (L.xy[1] > -75), (236, 200, 140), sombra=None, bisel=0, textura=0.4, alfa=0.8)
    hueco = L.mascara(lambda d, L: d.rounded_rectangle([*L.p(-215 + 2 * (s + 4), -215), *L.p(-215 + 2 * (s + 4) + s, -215 + s)], radius=8 * L.k, outline=255, width=int(3 * L.k)), 0)
    xx, yy = L.xy
    pl.pieza(hueco * (np.sin((xx + yy) / 7) > 0), (236, 200, 140), sombra=None, bisel=0, textura=0.3, alfa=0.7)
    guardar('puzle', pl)
    L2 = P.Lienzo(-110, -110, 110, 110, 1.6)
    pl2 = PP.Plano(L2, 103)
    pl2.pieza(_baldosa(L2, -70, -70, s, False, True), AMBAR, sombra=None, bisel=0.8)
    guardar('pieza_suelta', pl2)


def pieza_iconos():
    # burbuja de pensamiento
    L = P.Lienzo(-200, -150, 200, 170, 1.4)
    pl = PP.Plano(L, 111)
    pl.pieza(poli(L, [(-170, 0), (-120, -100), (0, -128), (130, -100), (176, 0), (120, 90), (0, 112), (-130, 88)], 6), CREMA, rasgado=0.4, sombra=None, bisel=0.5)
    for (cx, cy, r) in ((-150, 120, 20), (-178, 152, 11)):
        pl.pieza(circulo(L, cx, cy, r), CREMA, rasgado=0.4, sombra=(2, 3, 3, 0.4), bisel=0.5)
    guardar('burbuja', pl)
    # explosión
    L = P.Lienzo(-140, -140, 140, 140, 1.8)
    pl = PP.Plano(L, 113)
    pl.pieza(poli(L, _estrella_pts(12, 125, 62, 0.1)), (214, 74, 48), rasgado=0.3, sombra=None, bisel=0.6)
    pl.pieza(poli(L, _estrella_pts(9, 74, 38, 0.4)), (246, 196, 82), rasgado=0.5, sombra=(1, 2, 2, 0.4), bisel=0.5)
    guardar('explosion', pl)
    # aspa (dos tiras cruzadas)
    L = P.Lienzo(-170, -170, 170, 170, 1.6)
    pl = PP.Plano(L, 115)
    for t in (0.78, -0.78):
        ca, sa = math.cos(t), math.sin(t)
        pts = [(-150 * ca - 16 * sa, -150 * sa + 16 * ca), (150 * ca - 16 * sa, 150 * sa + 16 * ca), (150 * ca + 16 * sa, 150 * sa - 16 * ca), (-150 * ca + 16 * sa, -150 * sa - 16 * ca)]
        pl.pieza(poli(L, pts), AMBAR, rasgado=0.5, sombra=(2, 3, 3, 0.45), bisel=0.6)
    guardar('aspa', pl)
    # comprobado (marca de verificación)
    L = P.Lienzo(-90, -90, 90, 90, 2.0)
    pl = PP.Plano(L, 117)
    pl.pieza(poli(L, [(-70, 0), (-46, -24), (-18, 6), (52, -66), (76, -42), (-18, 54)]), VERDE, rasgado=0.1, sombra=None, bisel=0.8)
    guardar('check', pl)
    # punto denso y caliente (montón de discos comprimidos)
    L = P.Lienzo(-70, -70, 70, 70, 2.2)
    pl = PP.Plano(L, 119)
    rnd = np.random.RandomState(12)
    for _ in range(46):
        r = rnd.uniform(8, 20)
        tt, rr = rnd.uniform(0, 6.28), rnd.uniform(0, 42) ** 0.9
        col = [(250, 214, 120), (246, 160, 70), (255, 236, 190), (230, 110, 52)][rnd.randint(4)]
        pl.pieza(circulo(L, math.cos(tt) * rr, math.sin(tt) * rr, r), col, sombra=(0.8, 1.2, 1.2, 0.4), bisel=0.6)
    guardar('denso', pl)
    # chincheta / bandera
    L = P.Lienzo(-40, -100, 40, 10, 2.0)
    pl = PP.Plano(L, 121)
    pl.pieza(L.mascara(lambda d, L: d.rectangle([*L.p(-3, -96), *L.p(3, 6)], fill=255), 0), (60, 52, 50), sombra=None, bisel=0.5)
    pl.pieza(poli(L, [(3, -96), (36, -84), (3, -70)]), ROJO, rasgado=0.2, sombra=(1, 1.5, 1.5, 0.4), bisel=0.6)
    guardar('bandera', pl)
    # termómetro (el líquido se dibuja aparte)
    L = P.Lienzo(-60, -210, 60, 230, 1.8)
    pl = PP.Plano(L, 123)
    pl.pieza(L.mascara(lambda d, L: (d.rounded_rectangle([*L.p(-22, -200), *L.p(22, 160)], radius=22 * L.k, fill=255),
                                     d.ellipse([*L.p(-44, 128), *L.p(44, 216)], fill=255)), 0), (240, 236, 226), sombra=None, bisel=0.7)
    marcas = Image.new('L', (L.w, L.h), 0)
    d = ImageDraw.Draw(marcas)
    for j in range(9):
        y = -170 + j * 36
        d.line([*L.p(-22, y), *L.p(-8 if j % 2 else 0, y)], fill=255, width=int(2.5 * L.k))
    pl.pieza(np.asarray(marcas, np.float32) / 255, TINTA, sombra=None, bisel=0, textura=0.5)
    guardar('termometro', pl)
    # mapa del fondo cósmico (ilustración propia en óvalo, papeles de colores superpuestos)
    L = P.Lienzo(-420, -220, 420, 220, 1.4)
    pl = PP.Plano(L, 125)
    ov = L.mascara(lambda d, L: d.ellipse([*L.p(-400, -200), *L.p(400, 200)], fill=255), 0)
    pl.pieza(ov, (64, 96, 176), sombra=None, bisel=0.6)
    n = P.fbm(L.w, L.h, int(26 * L.k), 4, 77)
    for umbral, col in ((0.42, (90, 160, 204)), (0.52, (236, 206, 110)), (0.6, (226, 132, 62)), (0.68, (190, 70, 50))):
        pl.pieza((n > umbral).astype(np.float32), col, rasgado=0.7, sombra=(1, 1.5, 1.5, 0.3), cortar=ov, bisel=0.2)
    guardar('mapa_cmb', pl)
    # galaxia pequeña
    L = P.Lienzo(-70, -70, 70, 70, 2.0)
    pl = PP.Plano(L, 127)
    _galaxia(pl, L, 56)
    guardar('galaxia', pl)
    # satélite Planck (cuerpo, pantalla solar y deflector del telescopio)
    L = P.Lienzo(-140, -150, 140, 120, 1.8)
    pl = PP.Plano(L, 129)
    pl.pieza(poli(L, [(-130, 70), (130, 70), (100, 100), (-100, 100)]), (54, 66, 120), sombra=None, bisel=0.6)
    pl.pieza(poli(L, [(-120, 64), (120, 64), (120, 74), (-120, 74)]), (200, 206, 216), sombra=None, bisel=0.4)
    pl.pieza(L.mascara(lambda d, L: d.rectangle([*L.p(-46, 6), *L.p(46, 64)], fill=255), 0), (176, 182, 196), sombra=(1, 2, 2, 0.4), bisel=0.6)
    pl.pieza(poli(L, [(-70, 6), (-40, -130), (60, -140), (78, 6)]), (214, 218, 226), rasgado=0.1, sombra=(1, 2, 2, 0.4), bisel=0.7)
    pl.pieza(poli(L, [(-40, -130), (60, -140), (52, -116), (-30, -108)]), (40, 44, 70), sombra=None, bisel=0.3)
    guardar('satelite', pl)
    # signo de aviso
    L = P.Lienzo(-70, -70, 70, 70, 2.0)
    pl = PP.Plano(L, 131)
    pl.pieza(poli(L, [(0, -60), (60, 50), (-60, 50)]), AMBAR, sombra=None, bisel=0.8)
    pl.pieza(mascara_texto(L, '!', 0, 12, 70), TINTA, sombra=None, bisel=0)
    guardar('aviso', pl)


def pieza_foto(nombre, archivo, ancho, recorte=None):
    """Foto oficial impresa y pegada: borde blanco de papel fotográfico y dos tiras de cinta."""
    im = Image.open(os.path.join(ORIG, archivo)).convert('RGB')
    if recorte:
        im = im.crop(recorte)
    k = 1.25
    wpx = int(ancho * k)
    hpx = int(im.height * wpx / im.width)
    im = im.resize((wpx, hpx), Image.LANCZOS)
    borde = int(16 * k)
    L = P.Lienzo(-ancho / 2 - 30, -(hpx / k) / 2 - 40, ancho / 2 + 30, (hpx / k) / 2 + 30, k)
    pl = PP.Plano(L, sum(map(ord, nombre)))
    x0, y0 = int((L.w - wpx) / 2), int(30 * k + (40 - 30) * k)
    hoja = np.zeros((L.h, L.w), np.float32)
    hoja[y0 - borde:y0 + hpx + borde, x0 - borde:x0 + wpx + borde] = 1
    pl.pieza(hoja, (244, 242, 236), sombra=None, bisel=0.5, textura=0.6)
    rgb = pl.P.copy()
    rgb[y0:y0 + hpx, x0:x0 + wpx] = np.asarray(im, np.float32)
    pl.P = rgb
    for cx in (x0 + wpx * 0.12, x0 + wpx * 0.88):
        m = np.zeros((L.h, L.w), np.float32)
        m[int(y0 - borde - 14 * k):int(y0 - borde + 18 * k), int(cx - 50 * k):int(cx + 50 * k)] = 1
        pl.pieza(m, (240, 232, 200), rasgado=0.6, sombra=None, alfa=0.7, bisel=0, textura=1.4)
    guardar(nombre, pl)


def construir(rehacer=False):
    os.makedirs(CACHE, exist_ok=True)
    meta_p = os.path.join(CACHE, 'meta.json')
    if os.path.exists(meta_p) and not rehacer:
        return
    t0 = time.time()
    pieza_fondo()
    pieza_tapa()
    pieza_tierra()
    pieza_sol()
    pieza_estrella()
    pieza_regla()
    pieza_lupa()
    pieza_rollo()
    for i in range(3):
        pieza_reloj(i)
    pieza_aguja('minutero', 120, 12)
    pieza_aguja('horario', 78, 16)
    for i in range(2):
        pieza_separador(i)
    pieza_puzle()
    pieza_iconos()
    pieza_iconos2()
    pieza_foto('foto_wmap', 'M01-wmap-9yr-cmb.png', 900)
    pieza_foto('foto_hubble', 'M02-hubble-host-galaxies-nasa-2000.jpg', 1100)
    pieza_foto('foto_gaia', 'M03-gaia-allsky-4k.jpg', 860)
    meta = {}
    for n, (img, L) in PIEZAS.items():
        img.save(os.path.join(CACHE, n + '.png'))
        meta[n] = [L.x0, L.y0, L.k]
    with open(meta_p, 'w') as f:
        json.dump(meta, f, indent=1)
    print('  piezas: %.1f s' % (time.time() - t0), flush=True)


def pieza_iconos2():
    # pan (masa que crece)
    L = P.Lienzo(-280, -170, 280, 170, 1.4)
    pl = PP.Plano(L, 141)
    pl.pieza(poli(L, [(-260, 40), (-230, -80), (-120, -140), (0, -150), (120, -140), (230, -80), (260, 40), (200, 120), (0, 140), (-200, 120)], 6),
             (214, 168, 108), rasgado=0.2, sombra=None, bisel=0.8)
    for x in (-120, 0, 120):
        pl.pieza(poli(L, PP.mechon(x, -60, 1.2, 150, 22, 0.1)), (238, 206, 150), rasgado=0.5, sombra=None, bisel=0.3, alfa=0.9)
    guardar('pan', pl)
    # rebobinar
    L = P.Lienzo(-90, -60, 90, 60, 2.0)
    pl = PP.Plano(L, 143)
    for dx in (-40, 30):
        pl.pieza(poli(L, [(dx + 40, -46), (dx + 40, 46), (dx - 34, 0)]), CREMA, sombra=(1, 2, 2, 0.4), bisel=0.7)
    guardar('rebobinar', pl)
    # cefeida (estrella que pulsa) y supernova
    L = P.Lienzo(-90, -90, 90, 90, 2.0)
    pl = PP.Plano(L, 145)
    pl.pieza(poli(L, _estrella_pts(8, 70, 34)), (250, 222, 120), rasgado=0.2, sombra=None, bisel=0.7)
    pl.pieza(circulo(L, 0, 0, 30), (255, 246, 210), sombra=None, bisel=0.4)
    guardar('cefeida', pl)
    L = P.Lienzo(-110, -110, 110, 110, 2.0)
    pl = PP.Plano(L, 147)
    pl.pieza(poli(L, _estrella_pts(14, 100, 46, 0.2)), (240, 240, 255), rasgado=0.6, sombra=None, bisel=0.5)
    pl.pieza(poli(L, _estrella_pts(10, 60, 28, 0.5)), (255, 214, 120), rasgado=0.5, sombra=(1, 2, 2, 0.35), bisel=0.5)
    guardar('supernova', pl)
    # sobre y su solapa
    L = P.Lienzo(-200, -140, 200, 140, 1.6)
    pl = PP.Plano(L, 149)
    pl.pieza(L.mascara(lambda d, L: d.rectangle([*L.p(-180, -110), *L.p(180, 120)], fill=255), 0), (226, 210, 176), sombra=None, bisel=0.6)
    pl.pieza(poli(L, [(-180, 120), (0, 0), (180, 120)]), (212, 194, 158), sombra=(0, -2, 2, 0.3), bisel=0.4)
    guardar('sobre', pl)
    L = P.Lienzo(-200, -20, 200, 140, 1.6)
    pl = PP.Plano(L, 151)
    pl.pieza(poli(L, [(-180, 0), (180, 0), (0, 120)]), (234, 220, 186), sombra=None, bisel=0.7)
    guardar('solapa', pl)
    # telescopio Webb (espejo de hexágonos dorados y parasol)
    L = P.Lienzo(-170, -170, 170, 170, 1.8)
    pl = PP.Plano(L, 153)
    pl.pieza(poli(L, [(-160, 120), (160, 120), (120, 160), (-120, 160)]), (150, 110, 170), sombra=None, bisel=0.5)
    pl.pieza(poli(L, [(-150, 104), (150, 104), (160, 120), (-160, 120)]), (190, 160, 210), sombra=None, bisel=0.3)
    r = 30
    centros = [(0, 0)] + [(math.cos(t) * r * 1.8, math.sin(t) * r * 1.8) for t in np.arange(6) * math.pi / 3 + math.pi / 6] + \
              [(math.cos(t) * r * 3.5, math.sin(t) * r * 3.5) for t in np.arange(12) * math.pi / 6]
    for cx, cy in centros:
        if abs(cx) < 1 and abs(cy) < 1:
            continue
        hexa = [(cx + math.cos(t) * r, cy - 20 + math.sin(t) * r) for t in np.arange(6) * math.pi / 3]
        pl.pieza(poli(L, hexa), (222, 178, 80), sombra=(1, 1.5, 1.5, 0.35), bisel=0.7)
    guardar('webb', pl)
    # antena ACT sobre montañas
    L = P.Lienzo(-260, -200, 260, 140, 1.5)
    pl = PP.Plano(L, 155)
    for (pts, col) in (([(-260, 140), (-150, -40), (-60, 30), (40, -90), (150, 10), (260, -50), (260, 140)], (70, 64, 96)),
                       ([(-260, 140), (-200, 40), (-90, 90), (20, 20), (140, 80), (260, 30), (260, 140)], (104, 92, 112))):
        pl.pieza(poli(L, pts), col, rasgado=0.5, sombra=(1, 2, 3, 0.35), bisel=0.4)
    pl.pieza(L.mascara(lambda d, L: d.rectangle([*L.p(-12, -20), *L.p(12, 60)], fill=255), 0), (210, 206, 200), sombra=None, bisel=0.5)
    pl.pieza(L.mascara(lambda d, L: d.pieslice([*L.p(-110, -190), *L.p(110, 30)], 20, 160, fill=255), 0), (232, 230, 226), sombra=(1, 2, 2, 0.4), bisel=0.7)
    guardar('act', pl)
    # comentario, documento, lápiz, botones de cierre
    L = P.Lienzo(-150, -110, 150, 130, 1.6)
    pl = PP.Plano(L, 157)
    pl.pieza(L.mascara(lambda d, L: (d.rounded_rectangle([*L.p(-140, -100), *L.p(140, 70)], radius=36 * L.k, fill=255),
                                     d.polygon(L.ps([(-60, 60), (-90, 120), (-10, 64)]), fill=255)), 0), CREMA, sombra=None, bisel=0.6)
    for cx in (-60, 0, 60):
        pl.pieza(circulo(L, cx, -14, 13), TINTA, sombra=None, bisel=0)
    guardar('comentario', pl)
    L = P.Lienzo(-110, -140, 110, 140, 1.8)
    pl = PP.Plano(L, 159)
    pl.pieza(poli(L, [(-96, -126), (50, -126), (96, -80), (96, 126), (-96, 126)]), (244, 240, 230), sombra=None, bisel=0.6)
    pl.pieza(poli(L, [(50, -126), (96, -80), (50, -80)]), (214, 206, 190), sombra=(-1, 1, 1.5, 0.35), bisel=0.5)
    lineas = Image.new('L', (L.w, L.h), 0)
    d = ImageDraw.Draw(lineas)
    for j in range(7):
        y = -60 + j * 26
        d.line([*L.p(-70, y), *L.p(70 - (j % 3) * 30, y)], fill=255, width=int(4 * L.k))
    pl.pieza(np.asarray(lineas, np.float32) / 255, (120, 112, 120), sombra=None, bisel=0, textura=0.5)
    guardar('documento', pl)
    L = P.Lienzo(-100, -100, 100, 100, 2.0)
    pl = PP.Plano(L, 161)
    pl.pieza(circulo(L, 0, 0, 86), (46, 52, 96), sombra=None, bisel=0.6)
    pl.pieza(L.mascara(lambda d, L: (d.rounded_rectangle([*L.p(-46, -6), *L.p(-20, 56)], radius=6 * L.k, fill=255),
                                     d.rounded_rectangle([*L.p(-16, -10), *L.p(44, 56)], radius=12 * L.k, fill=255),
                                     d.polygon(L.ps([(-16, -6), (6, -58), (22, -54), (14, -8)]), fill=255)), 0), CREMA, sombra=(1, 2, 2, 0.4), bisel=0.6)
    guardar('like', pl)
    L = P.Lienzo(-100, -100, 100, 100, 2.0)
    pl = PP.Plano(L, 163)
    pl.pieza(circulo(L, 0, 0, 86), (46, 52, 96), sombra=None, bisel=0.6)
    pl.pieza(poli(L, [(-44, 34), (-34, -20), (-18, -44), (0, -50), (18, -44), (34, -20), (44, 34), (54, 44), (-54, 44)], 4), AMBAR, sombra=(1, 2, 2, 0.4), bisel=0.6)
    pl.pieza(circulo(L, 0, 56, 11), AMBAR, sombra=(1, 2, 2, 0.4), bisel=0.6)
    guardar('campana', pl)

# ------------------------------------------------------------------ carga y composición


SPR = {}
FIJOS = {}


def cargar():
    if SPR:
        return
    with open(os.path.join(CACHE, 'meta.json')) as f:
        meta = json.load(f)
    for n, (x0, y0, k) in meta.items():
        im = Image.open(os.path.join(CACHE, n + '.png')).convert('RGBA')
        SPR[n] = (im.convert('RGBa'), x0, y0, k, im.size)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dd = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    FIJOS['vineta'] = (1 - 0.34 * np.clip(dd - 0.3, 0, 1) ** 1.3)[..., None]
    FIJOS['papel'] = P.textura_papel(W, H, 9)[..., None]
    FIJOS['fibra'] = (1 + (P.fbm(W, H, 3, 3, 17, aspecto=3.0) - 0.5) * 0.12 + (P.fbm(W, H, 50, 4, 19) - 0.5) * 0.1).astype(np.float32)
    FIJOS['dist'] = np.hypot(xx - 960, yy - 540)
    ang = np.arctan2(yy - 540, xx - 960)
    FIJOS['borde'] = (np.sin(ang * 7 + 1) * 0.5 + np.sin(ang * 13 + 2) * 0.3 + np.sin(ang * 29) * 0.2 + np.sin(ang * 61 + 4) * 0.12).astype(np.float32)
    FIJOS['tapa'] = np.asarray(SPR['tapa'][0].convert('RGBA').convert('RGB'), np.float32)


def _texto_sprite(clave, texto, tam, color, tinta, peso, tipo, barra):
    """Rótulos y cifras: se recortan la primera vez que se usan (en cada proceso) y se guardan en SPR."""
    if clave in SPR:
        return
    f = fuente(tam, peso)
    bb = f.getbbox(texto)
    tw = bb[2] - bb[0]
    tam = int(tam)
    semilla = int(sum(map(ord, texto)) * 7 + tam) % 100000
    if tipo == 'glifo':
        L = P.Lienzo(-tw / 2 - tam * 0.3, -tam * 0.75, tw / 2 + tam * 0.3, tam * 0.75, 1.5)
        pl = PP.Plano(L, semilla)
        pl.pieza(mascara_texto(L, texto, 0, 0, tam, peso), color, rasgado=0.08, sombra=None, bisel=0.7)
    else:
        wd = tw / 2 + tam * 0.65 + (tam * 0.25 if barra else 0)
        h = tam * 0.95
        L = P.Lienzo(-wd - 20, -h - 20, wd + 20, h + 20, 2.0)
        pl = PP.Plano(L, semilla)
        m = L.mascara(lambda d, L: d.polygon(L.ps([(-wd, -h * 0.82), (wd, -h * 0.9), (wd * 0.99, h * 0.86), (-wd * 1.01, h * 0.8)]), fill=255), 0)
        pl.pieza(m, color, rasgado=0.35, sombra=None, bisel=0.4)
        if barra:
            mb = L.mascara(lambda d, L: d.rectangle([*L.p(-wd, -h * 0.82), *L.p(-wd + tam * 0.22, h * 0.8)], fill=255), 0)
            pl.pieza(mb * m, barra, sombra=None, bisel=0.2)
        pl.pieza(mascara_texto(L, texto, tam * 0.12 if barra else 0, 0, tam, peso), tinta, sombra=None, bisel=0, textura=0.6)
    img = pl.capa()
    SPR[clave] = (img.convert('RGBa'), L.x0, L.y0, L.k, img.size)


def poner(lienzo, clave, x, y, esc=1.0, rot=0.0, alfa=1.0, altura=5.0, corte_x=1.0):
    """Pega la pieza `clave` con su origen local en (x, y). `altura` separa la pieza del fondo (sombra más lejana y suave)."""
    if alfa <= 0.003 or esc <= 0.01:
        return
    img, x0, y0, k, (iw, ih) = SPR[clave]
    if corte_x < 1:
        iw = max(1, int(iw * corte_x))
        img = img.crop((0, 0, iw, ih))
    c, s = math.cos(rot), math.sin(rot)
    esq = [(x + esc * (c * px - s * py), y + esc * (s * px + c * py)) for px, py in
           ((x0, y0), (x0 + iw / k, y0), (x0, y0 + ih / k), (x0 + iw / k, y0 + ih / k))]
    m = int(altura * 1.6 + 6)
    bx0 = int(math.floor(min(p[0] for p in esq))) - m
    by0 = int(math.floor(min(p[1] for p in esq))) - m
    bx1 = int(math.ceil(max(p[0] for p in esq))) + m
    by1 = int(math.ceil(max(p[1] for p in esq))) + m
    cx0, cy0, cx1, cy1 = max(0, bx0), max(0, by0), min(W, bx1), min(H, by1)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    A, B = k * c / esc, k * s / esc
    D, E = -k * s / esc, k * c / esc
    C = -k * x0 - (A * x + B * y) + A * cx0 + B * cy0
    Fv = -k * y0 - (D * x + E * y) + D * cx0 + E * cy0
    sub = img.transform((cx1 - cx0, cy1 - cy0), Image.AFFINE, (A, B, C, D, E, Fv), resample=Image.BICUBIC).convert('RGBA')
    al = sub.getchannel('A')
    if alfa < 1:
        al = al.point(lambda v: int(v * alfa))
        sub.putalpha(al)
    if altura > 0:
        sa = al.filter(ImageFilter.GaussianBlur(altura * 0.45 + 1.2)).point(lambda v: int(v * 0.5))
        sombra = Image.new('RGBA', sub.size, PP.SOMBRA + (0,))
        sombra.putalpha(sa)
        lienzo.alpha_composite(sombra, (int(cx0 + altura * 0.45), int(cy0 + altura * 0.75)))
    lienzo.alpha_composite(sub, (cx0, cy0))


def ventana(t, t0, t1, din=0.45, dout=0.5):
    """Entrada y salida calmadas: devuelve (alfa, desplazamiento vertical, altura) o None si la pieza no está."""
    if t < t0 - 0.01 or t > t1 + dout:
        return None
    p = suave((t - t0) / din)
    q = suave((t - t1) / dout)
    return p * (1 - q), -22 * (1 - p) - 34 * q, 4 + 16 * (1 - p) + 24 * q


def PZ(lz, clave, t, t0, t1, x, y, esc=1.0, rot=0.0, alt=0.0, din=0.45, dout=0.5, alfa=1.0, corte_x=1.0):
    v = ventana(t, t0, t1, din, dout)
    if v:
        poner(lz, clave, x, y + v[1], esc, rot, alfa=v[0] * alfa, altura=v[2] + alt, corte_x=corte_x)
    return v


def TX(lz, texto, t, t0, t1, x, y, tam=40, tipo='etiqueta', color=CREMA, tinta=TINTA, peso=800, barra=None, esc=1.0, rot=0.0, alt=0.0, alfa=1.0):
    clave = 'tx|%s|%d|%s|%s|%d|%s|%s' % (texto, tam, color, tinta, peso, tipo, barra)
    if ventana(t, t0, t1) is None:
        return None
    _texto_sprite(clave, texto, tam, color, tinta, peso, tipo, barra)
    return PZ(lz, clave, t, t0, t1, x, y, esc, rot, alt, alfa=alfa)


def CIFRA(lz, texto, t, t0, t1, x, y, tam=170, color=AMBAR, **kw):
    return TX(lz, texto, t, t0, t1, x, y, tam=tam, tipo='glifo', color=color, peso=900, **kw)


def DATO(lz, texto, t, t0, t1):
    """Sello «Dato verificado» (fuente de la cifra), abajo a la izquierda."""
    clave_w = fuente(28, 600).getbbox('Dato verificado · ' + texto)[2]
    return TX(lz, 'Dato verificado · ' + texto, t, t0, t1, 40 + clave_w / 2 + 40, 990, tam=28, color=(234, 226, 206), peso=600, barra=AMBAR)


def papel_dyn(lz, formas, color, alfa=1.0, altura=4.0, bisel=0.6, dy=0.0):
    """Pieza de papel dibujada en el momento (barras, tiras, flechas): formas en coordenadas de pantalla.
    formas: [('rect', x0, y0, x1, y1), ('poly', pts), ('ell', x0, y0, x1, y1), ('line', pts, ancho)]."""
    if alfa <= 0.003:
        return
    xs, ys = [], []
    for f in formas:
        if f[0] in ('rect', 'ell'):
            xs += [f[1], f[3]]
            ys += [f[2], f[4]]
        else:
            xs += [p[0] for p in f[1]]
            ys += [p[1] for p in f[1]]
    m = int(altura * 1.6 + 10)
    x0, y0 = max(0, int(min(xs)) - m), max(0, int(min(ys) + dy) - m)
    x1, y1 = min(W, int(max(xs)) + m + 1), min(H, int(max(ys) + dy) + m + 1)
    if x1 <= x0 or y1 <= y0:
        return
    ss = 2
    mk = Image.new('L', ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    d = ImageDraw.Draw(mk)

    def q(px, py):
        return ((px - x0) * ss, (py + dy - y0) * ss)
    for f in formas:
        if f[0] == 'rect':
            d.rectangle([*q(min(f[1], f[3]), min(f[2], f[4])), *q(max(f[1], f[3]), max(f[2], f[4]))], fill=255)
        elif f[0] == 'ell':
            d.ellipse([*q(f[1], f[2]), *q(f[3], f[4])], fill=255)
        elif f[0] == 'poly':
            d.polygon([q(*p) for p in f[1]], fill=255)
        elif f[0] == 'line':
            d.line([q(*p) for p in f[1]], fill=255, width=max(1, int(f[2] * ss)), joint='curve')
    mk = mk.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    a = np.asarray(mk, np.float32) / 255
    col = np.zeros(a.shape + (3,), np.float32) + np.asarray(color, np.float32)
    col *= FIJOS['fibra'][y0:y1, x0:x1, None]
    if bisel:
        hi = np.clip(a - np.roll(np.roll(a, 1, 0), 1, 1), 0, 1)
        lo = np.clip(a - np.roll(np.roll(a, -1, 0), -1, 1), 0, 1)
        col *= (1 + bisel * 0.35 * hi - bisel * 0.35 * lo)[..., None]
    capa = Image.fromarray(np.concatenate([np.clip(col, 0, 255), (a * alfa * 255)[..., None]], 2).astype(np.uint8), 'RGBA')
    if altura > 0:
        sa = capa.getchannel('A').filter(ImageFilter.GaussianBlur(altura * 0.45 + 1.2)).point(lambda v: int(v * 0.5))
        sombra = Image.new('RGBA', capa.size, PP.SOMBRA + (0,))
        sombra.putalpha(sa)
        lz.alpha_composite(sombra, (int(x0 + altura * 0.45), int(y0 + altura * 0.75)))
    lz.alpha_composite(capa, (x0, y0))


def DYN(lz, formas, color, t, t0, t1, alt=0.0, bisel=0.6, alfa=1.0, din=0.45, dout=0.5):
    v = ventana(t, t0, t1, din, dout)
    if v:
        papel_dyn(lz, formas, color, alfa=v[0] * alfa, altura=v[2] + alt, bisel=bisel, dy=v[1])
    return v


def hilo(lz, pts, color=(236, 200, 130), ancho=3.0, alfa=1.0, sombra=True, discontinuo=False):
    """Hilo o trazo fino (flechas, órbitas, rayos de luz) con sombra suave."""
    if len(pts) < 2 or alfa <= 0.003:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    m = int(ancho * 3 + 12)
    x0, y0 = max(0, int(min(xs)) - m), max(0, int(min(ys)) - m)
    x1, y1 = min(W, int(max(xs)) + m + 1), min(H, int(max(ys)) + m + 1)
    if x1 <= x0 or y1 <= y0:
        return
    ss = 3
    mk = Image.new('L', ((x1 - x0) * ss, (y1 - y0) * ss), 0)
    d = ImageDraw.Draw(mk)
    q = [((px - x0) * ss, (py - y0) * ss) for px, py in pts]
    if discontinuo:
        for i in range(0, len(q) - 1, 2):
            d.line([q[i], q[i + 1]], fill=255, width=max(1, int(ancho * ss)))
    else:
        d.line(q, fill=255, width=max(1, int(ancho * ss)), joint='curve')
    mk = mk.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    if sombra:
        sa = mk.filter(ImageFilter.GaussianBlur(2.5)).point(lambda v: int(v * 0.4 * alfa))
        sm = Image.new('RGBA', mk.size, PP.SOMBRA + (0,))
        sm.putalpha(sa)
        lz.alpha_composite(sm, (x0 + 3, y0 + 4))
    capa = Image.new('RGBA', mk.size, tuple(color) + (0,))
    capa.putalpha(mk.point(lambda v: int(v * alfa)))
    lz.alpha_composite(capa, (x0, y0))


def segmentos(pts, n_div=1):
    """Convierte una polilínea en pares (para hilos discontinuos)."""
    out = []
    for p0, p1 in zip(pts[:-1], pts[1:]):
        for j in range(n_div):
            out.append((lerp(p0[0], p1[0], j / n_div), lerp(p0[1], p1[1], j / n_div)))
    out.append(pts[-1])
    return out


def fondo(t):
    z = 1.0 + 0.05 * (0.5 - 0.5 * math.cos(2 * math.pi * t / 240))
    img, x0, y0, k, _ = SPR['fondo']
    cx, cy = 960 + 14 * math.sin(t * 0.05), 540 + 8 * math.sin(t * 0.037)
    A = k / z
    C = k * (cx - x0) - A * 960
    Fv = k * (cy - y0) - A * 540
    return img.transform((W, H), Image.AFFINE, (A, 0, C, 0, A, Fv), resample=Image.BICUBIC).convert('RGBA')


def brillo(arr, cx, cy, sigma, color, fuerza):
    R = int(sigma * 3)
    x0, x1 = max(0, int(cx) - R), min(W, int(cx) + R + 1)
    y0, y1 = max(0, int(cy) - R), min(H, int(cy) + R + 1)
    if x1 <= x0 or y1 <= y0 or fuerza <= 0.005:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma * sigma)) * fuerza
    arr[y0:y1, x0:x1] += g[..., None] * np.asarray(color, np.float32)


def tapa(lienzo, r):
    """Cartulina negra con un agujero de radio r en el centro (luz detrás)."""
    if r > 1300:
        return lienzo
    borde = r + FIJOS['borde'] * (2 + r * 0.04)
    hueco = np.clip((borde - FIJOS['dist']) / 1.2 + 0.5, 0, 1)
    arr = np.asarray(lienzo.convert('RGB'), np.float32)
    sombra = np.clip((FIJOS['dist'] - borde + 16) / 16, 0, 1) * hueco
    arr = arr * (1 - 0.6 * sombra[..., None])
    canto = np.exp(-((FIJOS['dist'] - borde + 1.5) / 1.6) ** 2)
    carton = FIJOS['tapa'] + canto[..., None] * np.array([70, 64, 78], np.float32)
    arr = arr * hueco[..., None] + carton * (1 - hueco[..., None])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')


def reloj(lz, i, x, y, esc, t, alfa=1.0, altura=5, vel=1.0, ang=None):
    """Reloj de papel con agujas (giran despacio salvo que se fije `ang` para el minutero)."""
    poner(lz, 'reloj%d' % i, x, y, esc, alfa=alfa, altura=altura)
    base = [0.4, 2.1, 4.0][i] + t * [0.45, 0.35, 0.55][i] * vel
    am = base if ang is None else ang
    poner(lz, 'horario', x, y, esc, rot=am / 3 + [1.2, -0.6, 2.4][i], alfa=alfa, altura=altura + 4)
    poner(lz, 'minutero', x, y, esc, rot=am, alfa=alfa, altura=altura + 7)


def RELOJ(lz, i, t, t0, t1, x, y, esc=1.0, **kw):
    v = ventana(t, t0, t1)
    if v:
        reloj(lz, i, x, y + v[1], esc, t, alfa=v[0], altura=v[2], **kw)
    return v


def eje(lz, t, t0, t1, x0, x1, y, vmin, vmax, marcas, tam=24, color=CREMA):
    """Eje de papel con marcas de tinta y etiquetas pequeñas. marcas: [(valor, texto)]."""
    v = ventana(t, t0, t1)
    if not v:
        return lambda val: x0 + (val - vmin) / (vmax - vmin) * (x1 - x0)
    papel_dyn(lz, [('rect', x0 - 20, y - 5, x1 + 20, y + 5)], color, alfa=v[0], altura=v[2] - 2, dy=v[1])
    X = lambda val: x0 + (val - vmin) / (vmax - vmin) * (x1 - x0)   # noqa: E731
    for val, txt in marcas:
        papel_dyn(lz, [('rect', X(val) - 2, y - 14, X(val) + 2, y + 14)], CREMA, alfa=v[0], altura=1, bisel=0, dy=v[1])
        if txt:
            TX(lz, txt, t, t0, t1, X(val), y + 46, tam=tam, color=(226, 218, 198), peso=700)
    return X


def barra_error(lz, X, centro, margen, y, color, t, t0, t1, grosor=22, alt=4.0, crece=0.6):
    """Barra de error de papel: crece desde el valor central hasta ± margen."""
    v = ventana(t, t0, t1)
    if not v:
        return
    g = suave((t - t0) / crece)
    xa, xb = X(centro - margen * g), X(centro + margen * g)
    if xb - xa < 6:
        xa, xb = X(centro) - 3, X(centro) + 3
    papel_dyn(lz, [('rect', xa, y - grosor / 2, xb, y + grosor / 2)], color, alfa=v[0], altura=v[2] + alt, dy=v[1])
    papel_dyn(lz, [('rect', X(centro) - 3, y - grosor / 2 - 10, X(centro) + 3, y + grosor / 2 + 10)], TINTA, alfa=v[0], altura=v[2] + alt + 2, bisel=0, dy=v[1])

# ------------------------------------------------------------------ escenas
# Cada escena dibuja sobre `lz` (PIL RGBA) y añade luces a `ex`. Los tiempos salen de la voz: a(i), b(i), w(i, 'palabra').


TOKEN_LAMBDA = (a(18), a(45) - 0.4)           # ΛCDM queda en la esquina desde «Va a volver» hasta el Reloj 2
PULSOS_LAMBDA = [w(31, 'modelo'), a(42), w(42, 'depende')]


def s_inicio(lz, t, ex):
    """E01–E04 (0:00–0:40): la luz, Tierra/Sol/estrella que se retiran, la tira del tiempo, la lupa, tres relojes."""
    if t < 9.0:
        r = 4 + 34 * suave(t / 2.6) + 10 * suave((t - 3.0) / 3) + 1600 * suave((t - 7.35) / 1.25) ** 2.2
        ex.append((960, 540, 40 + r * 0.8, (255, 214, 150), 0.9 * (1 - suave((t - 7.6) / 1.2))))
        ex.append((960, 540, 12 + r * 0.25, (255, 246, 220), 1.4 * (1 - suave((t - 7.6) / 1.0))))
        lz = tapa(lz, r)
        for clave, x, y, t0, t1 in (('tierra', 520, 600, w(1, 'la Tierra'), w(1, 'el Sol')), ('sol', 1400, 560, w(1, 'el Sol'), w(1, 'una sola')),
                                    ('estrella', 960, 290, w(1, 'una sola'), b(1) + 0.15)):
            if t0 - 0.05 < t < t1 + 0.9:
                p, q = suave((t - t0 + 0.05) / 0.4), suave((t - t1) / 0.6)
                poner(lz, clave, x + (x - 960) * 1.4 * q, y - 260 * q, esc=1.0 + 0.15 * q, rot=0.5 * q * (1 if x > 960 else -1),
                      alfa=p * (1 - q * 0.2), altura=5 + 20 * (1 - p) + 70 * q)
    # E02: la tira del tiempo y la lupa
    if 8.0 <= t < 22.6:
        q_fuera = suave((t - a(3) + 0.3) / 0.6)
        q2 = suave((t - 21.55) / 0.5)
        ini = 8.7
        des = suave((t - ini) / 2.8)
        if t > ini:
            ry = 660 - 300 * q2
            poner(lz, 'regla', 960, ry, alfa=1 - q2, altura=5 + 50 * q2, corte_x=0.03 + 0.97 * des)
            if des < 1:
                poner(lz, 'rollo', 260 + 1400 * des + 10, ry, alfa=1 - q2, altura=8)
            ex.append((255, ry, 22 + 6 * math.sin(t * 6), (255, 226, 160), 0.9 * (1 - q2) * min(1, (t - ini) * 3)))
            ex.append((255, ry, 70, (255, 190, 110), 0.25 * (1 - q2) * min(1, (t - ini) * 3)))
            if des > 0.97:
                pt = suave((t - ini - 2.8) / 0.35)
                poner(lz, 'tierra', 1712, ry, esc=0.26, alfa=pt * (1 - q2), altura=4 + 20 * (1 - pt) + 30 * q2)
        for j, ch in enumerate('13797'):
            t0 = w(2, '13') - 0.15 + j * 0.12
            if t > t0:
                p = suave((t - t0) / 0.35)
                x = [690, 830, 1050, 1190, 1330][j] - 80
                CIFRA(lz, ch, t, t0, 1e9, x, 360 - 520 * q_fuera * (1 + j * 0.1), tam=210, rot=0.2 * q_fuera * (j - 2), alfa=p * (1 - q_fuera))
        if t > w(2, 'millones de') - 0.1:
            TX(lz, 'millones de años', t, w(2, 'millones de') - 0.1, 1e9, 930, 520 - 400 * q_fuera, tam=54, peso=700, alfa=1 - q_fuera)
        if w(2, '13') < t < 21.6:
            DATO(lz, 'Planck 2018 (ESA)', t, w(2, '13') + 0.6, 21.2)
        if t > w(2, '23 millones') - 0.15:
            pl = suave((t - w(2, '23 millones') + 0.15) / 0.4)
            lx, ly = 1640, 400 - 300 * q2
            esl = 0.7 + 0.3 * pl
            pts = segmentos([(lx, ly + 124 * esl), (1659, 640 - 300 * q2)], 14)
            hilo(lz, pts, alfa=pl * (1 - q2), ancho=3, discontinuo=True)
            poner(lz, 'lupa', lx, ly, esc=esl, alfa=pl * (1 - q2), altura=14 + 30 * (1 - pl) + 40 * q2)
            TX(lz, '± 23 M', t, w(2, '23 millones') + 0.25, 1e9, lx, ly - 175 * esl, tam=46, color=(244, 196, 104), peso=800, rot=-0.04, alfa=1 - q2)
        if t > w(3, '0,17') - 0.2:
            CIFRA(lz, '0,17 %', t, w(3, '0,17') - 0.15, 1e9, 880, 400 - 320 * q2, tam=170, alfa=1 - q2)
    # E03–E04: «¿Cómo es posible?», un reloj, tres relojes, separadores y el desajuste
    if a(4) - 0.1 < t < a(5) + 0.5:
        CIFRA(lz, '¿?', t, a(4) - 0.1, a(5) - 0.15, 960, 520, tam=260)
    fuera = suave((t - a(9) + 0.2) / 0.6)
    if a(5) < t < a(9) + 0.6:
        mover = suave((t - a(6)) / 0.6)
        foco = suave((t - a(8)) / 0.9)
        pos = [(lerp(960, 500, mover), 540), (1420, 540), (960, 540)]
        aparece = [a(5), a(6) + 0.2, a(6) + 0.45]
        destino = [(700, 540), (1220, 540), (960, 1500)]
        dej = suave((t - w(8, 'dejan')) / 0.7)
        for i in range(3):
            if t < aparece[i]:
                continue
            p = suave((t - aparece[i]) / 0.4)
            x = lerp(pos[i][0], destino[i][0], foco)
            y = lerp(pos[i][1], destino[i][1], foco) - 300 * fuera
            esc = (0.8 if i else lerp(1.0, 0.8, mover)) * (1 + 0.18 * foco * (i < 2))
            al = p * (1 - fuera)
            alt = 5 + 20 * (1 - p) + 40 * fuera
            poner(lz, 'reloj%d' % i, x, y, esc, alfa=al, altura=alt)
            base = [0.4, 2.1, 4.0][i] + t * [0.45, 0.35, 0.55][i]
            obj = -0.55
            af = suave((t - w(8, 'se afinan')) / 0.9) if i < 2 else 0
            am = lerp(base, obj + 2 * math.pi * round((base - obj) / (2 * math.pi)), af)
            if i == 1:
                am += 0.55 * dej
            ah = lerp(am / 3 + [1.2, -0.6, 2.4][i], obj - 1.3 + (0.3 * dej if i == 1 else 0), af)
            if i == 1 and dej > 0:
                lo, hi = sorted((obj, am - 2 * math.pi * round((am - obj) / (2 * math.pi))))
                cu = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                rr = 112 * esc
                ImageDraw.Draw(cu).pieslice([x - rr, y - rr, x + rr, y + rr], -90 + math.degrees(lo), -90 + math.degrees(hi), fill=AMBAR + (int(150 * dej * al),))
                lz.alpha_composite(cu)
                poner(lz, 'minutero', x, y, esc, rot=obj, alfa=0.35 * dej * al, altura=1)
            poner(lz, 'horario', x, y, esc, rot=ah, alfa=al, altura=alt + 4)
            poner(lz, 'minutero', x, y, esc, rot=am, alfa=al, altura=alt + 7)
        if w(7, 'no se conocen') - 0.1 < t < a(8) + 1.2:
            q = suave((t - a(8)) / 0.7)
            for i, x in enumerate((730, 1190)):
                p = suave((t - w(7, 'no se conocen') + 0.1 - i * 0.15) / 0.5)
                poner(lz, 'separador%d' % i, x, -600 + 1140 * p - 1200 * q, altura=12)
        CIFRA(lz, '?', t, w(8, 'dejan') + 0.3, a(9) - 0.2, 960, 330, tam=176)
    return lz


def s_puzle(lz, t, ex):
    """E04 (0:40–0:52): al modelo le falta una pieza; y lo que está en juego, casi mil millones de años."""
    PZ(lz, 'puzle', t, a(9) + 0.2, a(10) - 0.3, 960, 520)
    v = ventana(t, w(9, 'le falte') - 0.2, a(10) - 0.3)
    if v:
        flot = math.sin(t * 1.3) * 8
        poner(lz, 'pieza_suelta', 1290, 290 + flot + v[1], rot=0.25 + 0.04 * math.sin(t), alfa=v[0], altura=26)
        ex.append((1185, 375, 90, (255, 200, 120), 0.18 * v[0]))
    t0, t1 = a(10) - 0.1, a(11) - 0.3
    PZ(lz, 'regla', t, t0, t1, 960, 640)
    PZ(lz, 'tierra', t, t0 + 0.3, t1, 1712, 640, esc=0.26)
    v = ventana(t, w(10, 'casi mil') - 0.3, t1)
    if v:
        g = suave((t - w(10, 'casi mil') + 0.3) / 0.8)
        xe = 1660
        papel_dyn(lz, [('rect', xe - 101 * g, 640 - 34, xe, 640 + 34)], AMBAR, alfa=v[0] * 0.92, altura=v[2] + 6, dy=v[1])
        hilo(lz, [(xe - 101 * g, 600 + v[1]), (xe - 101 * g, 470 + v[1])], alfa=v[0] * g, ancho=3)
        TX(lz, '≈ 1 000 M de años', t, w(10, 'casi mil'), t1, xe - 101 - 40, 430, tam=44, color=(244, 196, 104))
    ex.append((255, 640, 22, (255, 226, 160), 0.8 * (ventana(t, t0, t1) or (0,))[0]))


def s_reloj1_intro(lz, t, ex):
    """E05–E07 (0:52–1:31): el primer reloj; el malentendido; el estado denso y caliente; ΛCDM."""
    v = RELOJ(lz, 0, t, a(11) - 0.1, a(13) - 0.4, 960, 540, esc=lerp(1.0, 1.5, suave((t - a(11)) / 3.0)))
    if v:
        ex.append((960, 540, 120, (255, 190, 120), 0.12 * v[0]))
    # «algo explotó en algún sitio»: burbuja de pensamiento con una explosión que se tacha
    t0, t1 = a(13) + 0.2, a(15) - 0.3
    PZ(lz, 'burbuja', t, t0, t1, 960, 520, esc=1.6)
    PZ(lz, 'explosion', t, w(14, 'algo explot') - 0.1, t1, 960, 500)
    PZ(lz, 'bandera', t, w(14, 'en alg') - 0.1, t1, 1050, 560, esc=0.9)
    PZ(lz, 'aspa', t, w(14, 'en alg') + 1.0, t1, 960, 510, esc=1.05, alt=10)
    # la tira del tiempo desde un estado muy denso y caliente hasta hoy
    t0, t1 = a(15) - 0.1, a(18) - 0.1
    v = ventana(t, t0, t1)
    if v:
        des = suave((t - t0 - 0.3) / 2.6)
        ry = lerp(620, 470, suave((t - w(16, 'modelo est') + 0.4) / 0.8)) + v[1]
        inc = 0.05 * suave((t - a(17)) / 0.8) * (1 - suave((t - a(17) - 2.4) / 0.8)) * math.sin((t - a(17)) * 3)
        poner(lz, 'regla', 960, ry + inc * 300, rot=inc, alfa=v[0], altura=v[2], corte_x=0.03 + 0.97 * des)
        if des < 1:
            poner(lz, 'rollo', 260 + 1400 * des + 10, ry, alfa=v[0], altura=8)
        poner(lz, 'denso', 250, ry, esc=0.9 + 0.05 * math.sin(t * 3), alfa=v[0], altura=v[2] + 6)
        ex.append((250, ry, 60, (255, 170, 80), 0.5 * v[0]))
        if des > 0.97:
            poner(lz, 'tierra', 1712, ry - inc * 600, esc=0.3, alfa=v[0], altura=v[2])
        PZ(lz, 'bandera', t, w(15, 'punto de partida') - 0.1, t1, 255, ry - 60, esc=1.0)
    # ΛCDM: la base sobre la que se apoya la tira
    t0 = w(16, 'modelo est') - 0.1
    v = ventana(t, t0, a(18) + 0.2)
    if v:
        inc = 0.05 * suave((t - a(17)) / 0.8) * (1 - suave((t - a(17) - 2.4) / 0.8)) * math.sin((t - a(17)) * 3)
        papel_dyn(lz, [('poly', [(860, 500), (1060, 500), (1100, 640), (820, 640)])], (70, 82, 140), alfa=v[0], altura=v[2], dy=v[1])
        TX(lz, 'ΛCDM', t, t0, a(18) + 0.2, 960, 580, tam=64, tipo='glifo', color=AMBAR, rot=inc)


def s_lambda(lz, t, ex):
    """La ficha ΛCDM queda fija arriba a la izquierda y pulsa cuando la voz la menciona."""
    v = ventana(t, *TOKEN_LAMBDA)
    if not v:
        return
    pulso = max([math.exp(-((t - p - 0.4) / 0.5) ** 2) for p in PULSOS_LAMBDA] + [0])
    entra = suave((t - TOKEN_LAMBDA[0]) / 0.9)
    x, y = lerp(960, 150, entra), lerp(580, 110, entra)
    TX(lz, 'ΛCDM', t, TOKEN_LAMBDA[0], TOKEN_LAMBDA[1], x, y, tam=64, tipo='glifo', color=AMBAR, esc=lerp(1.0, 0.62, entra) * (1 + 0.15 * pulso))
    if pulso > 0.02:
        ex.append((x, y, 70, (255, 200, 110), 0.5 * pulso))


PART = None


def _particulas():
    global PART
    if PART is None:
        rnd = np.random.RandomState(5)
        n = 90
        pr = np.stack([rnd.uniform(140, 1780, n), rnd.uniform(140, 940, n)], 1)
        el = pr + rnd.uniform(-90, 90, (n, 2))
        fase = rnd.uniform(0, 6.28, (n, 2))
        camino = [(960.0, 540.0)]
        for _ in range(70):
            x, y = camino[-1]
            ang = rnd.uniform(0, 6.28)
            nx, ny = x + math.cos(ang) * 46, y + math.sin(ang) * 46
            nx, ny = min(1300, max(620, nx)), min(760, max(320, ny))
            camino.append((nx, ny))
        PART = (pr, el, fase, camino)
    return PART


def s_niebla(lz, t, ex):
    """E08–E09 (1:31–2:04): la luz más antigua; la niebla de partículas; se enfría, se forman átomos y la luz queda libre."""
    v = RELOJ(lz, 0, t, a(19) - 0.1, a(21) - 0.4, 960, 540, esc=1.1)
    if v:
        ex.append((960, 540, 60 + 30 * math.sin(t * 2), (255, 220, 150), 0.6 * v[0]))
    t0, t1 = a(21) - 0.2, a(25) + 0.6
    v = ventana(t, t0, t1, din=1.0, dout=0.8)
    if v:
        pr, el, fase, camino = _particulas()
        osc = np.stack([np.sin(t * 0.5 + fase[:, 0]) * 14, np.cos(t * 0.45 + fase[:, 1]) * 12], 1)
        p_pr = pr + osc
        une = suave((t - w(24, 'los átomos')) / 2.0)
        p_el = el + osc * 1.4 + ((p_pr + np.array([16, -8])) - (el + osc * 1.4)) * une
        despeja = suave((t - w(24, 'la niebla')) / 1.4)
        centro = np.array([960, 540])
        p_pr = p_pr + (p_pr - centro) * despeja * 0.5
        p_el = p_el + (p_el - centro) * despeja * 0.5
        al = v[0] * (1 - 0.8 * despeja)
        sm = Image.new('L', (W, H), 0)
        ds = ImageDraw.Draw(sm)
        for (x, y) in p_pr:
            ds.ellipse([x - 13 + 4, y - 13 + 6, x + 13 + 4, y + 13 + 6], fill=int(120 * al))
        for (x, y) in p_el:
            ds.ellipse([x - 6 + 3, y - 6 + 4, x + 6 + 3, y + 6 + 4], fill=int(110 * al))
        sm = sm.filter(ImageFilter.GaussianBlur(3))
        sc = Image.new('RGBA', (W, H), PP.SOMBRA + (0,))
        sc.putalpha(sm)
        lz.alpha_composite(sc)
        d = ImageDraw.Draw(lz, 'RGBA')
        for (x, y) in p_pr:
            d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=(232, 136, 70, int(255 * al)))
            d.ellipse([x - 9, y - 11, x + 3, y - 1], fill=(248, 176, 110, int(200 * al)))
        for (x, y) in p_el:
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(150, 196, 240, int(255 * al)))
        # el rayo de luz rebota sin avanzar (camino en zigzag que se queda en la misma zona)
        prog = suave((t - w(21, 'la luz no')) / 6.0)
        n = max(2, int(len(camino) * prog))
        hilo(lz, camino[:n], color=(255, 214, 130), ancho=3, alfa=v[0] * (1 - despeja))
        if n > 1:
            ex.append((camino[n - 1][0], camino[n - 1][1], 14, (255, 220, 150), 0.9 * v[0] * (1 - despeja)))
    # 380 000 años en la tira del tiempo: una astilla al principio
    t0, t1 = w(22, '380') - 0.3, a(23) - 0.2
    PZ(lz, 'regla', t, t0, t1, 960, 960, esc=0.8)
    v = ventana(t, t0 + 0.4, t1)
    if v:
        x0 = 960 - 700 * 0.8
        hilo(lz, [(x0 + 2, 930 + v[1]), (x0 + 60, 860 + v[1])], alfa=v[0], ancho=3)
        ex.append((x0 + 2, 960, 16, (255, 220, 150), 0.9 * v[0]))
    TX(lz, '380 000 años', t, t0 + 0.5, t1, 960 - 700 * 0.8 + 150, 840, tam=40, color=(244, 196, 104))
    # termómetro que baja hasta 2 700 °C
    t0, t1 = a(23) - 0.1, a(24) + 1.4
    v = PZ(lz, 'termometro', t, t0, t1, 1600, 520)
    if v:
        nivel = lerp(1.0, 0.42, suave((t - t0 - 0.6) / 3.5))
        top = 520 + 160 - 340 * nivel
        papel_dyn(lz, [('rect', 1600 - 9, top, 1600 + 9, 520 + 170), ('ell', 1600 - 30, 520 + 142, 1600 + 30, 520 + 202)], ROJO, alfa=v[0], altura=1, bisel=0.3, dy=v[1])
    TX(lz, '2 700 °C', t, w(23, '2 700') - 0.2, t1, 1600 + 150, 520 + 160 - 340 * 0.42, tam=44, color=(244, 196, 104))
    # la luz queda libre: un rayo recto cruza la pantalla
    t0 = a(25) - 0.1
    v = ventana(t, t0, a(26) - 0.3)
    if v:
        g = suave((t - t0) / 1.0)
        hilo(lz, [(0, 540), (W * g, 540)], color=(255, 222, 150), ancho=4, alfa=v[0])
        ex.append((W * g, 540, 30, (255, 230, 170), v[0]))


def s_fondo_cosmico(lz, t, ex):
    """E10–E11 (2:04–2:34): la luz llega de todas direcciones; el mapa del fondo cósmico; 2,7 K; Planck; semillas."""
    t0, t1 = a(26) - 0.1, a(27) - 0.3
    v = PZ(lz, 'tierra', t, t0, t1, 960, 540, esc=0.7)
    if v:
        for j in range(20):
            ang = j / 20 * 2 * math.pi + 0.1
            g = suave((t - t0 - 0.2 - (j % 5) * 0.12) / 1.4)
            r0, r1 = 900, lerp(900, 90, g)
            hilo(lz, [(960 + math.cos(ang) * r0, 540 + math.sin(ang) * r0), (960 + math.cos(ang) * r1, 540 + math.sin(ang) * r1)],
                 color=(255, 214, 140), ancho=2.5, alfa=v[0] * 0.8, sombra=False)
    # el mapa (ilustración propia)
    t0, t1 = a(27) - 0.1, a(31) - 0.4
    v = ventana(t, t0, t1)
    if v:
        zoom = suave((t - a(30)) / 2.0)
        x = lerp(lerp(960, 760, suave((t - a(28)) / 0.8)), 960, suave((t - a(29)) / 1.0))
        esc = lerp(lerp(1.0, 0.8, suave((t - a(28)) / 0.8)), 0.95, suave((t - a(29)) / 1.0)) * (1 + 0.35 * zoom)
        y = 520 + 40 * zoom
        poner(lz, 'mapa_cmb', x, y + v[1], esc, alfa=v[0], altura=v[2])
        TX(lz, 'Ilustración propia', t, t0 + 0.6, t1, x + 300 * esc, y + 230 * esc, tam=24, color=(226, 218, 198), peso=600)
        # semillas: galaxias que brotan de las manchas
        g = suave((t - w(30, 'semillas')) / 1.6)
        if g > 0:
            rnd = np.random.RandomState(31)
            for j in range(7):
                gx, gy = rnd.uniform(-300, 300), rnd.uniform(-140, 140)
                if (gx / 330) ** 2 + (gy / 170) ** 2 > 1:
                    continue
                poner(lz, 'galaxia', x + gx * esc, y + gy * esc + v[1], esc=0.45 * g * (0.7 + 0.3 * math.sin(j)), rot=j, alfa=v[0], altura=6 + 8 * g)
    # 2,7 K: el termómetro baja casi al fondo
    t0, t1 = a(28) - 0.1, a(29) - 0.3
    v = PZ(lz, 'termometro', t, t0, t1, 1560, 520, esc=0.9)
    if v:
        nivel = lerp(0.42, 0.04, suave((t - t0 - 0.4) / 3.0))
        top = 520 + (160 - 340 * nivel) * 0.9
        papel_dyn(lz, [('rect', 1560 - 8, top, 1560 + 8, 520 + 153), ('ell', 1560 - 27, 520 + 128, 1560 + 27, 520 + 182)], AZUL, alfa=v[0], altura=1, bisel=0.3, dy=v[1])
    TX(lz, '2,7 K ≈ −270 °C', t, w(28, '2,7') - 0.2, a(29) - 0.3, 1560, 300, tam=44, color=(170, 200, 244))
    # Planck recorre el cielo
    t0, t1 = a(29) - 0.1, a(30) + 2.5
    v = ventana(t, t0, t1)
    if v:
        g = (t - t0) / (t1 - t0)
        poner(lz, 'satelite', lerp(1560, 1380, g), 230 + 10 * math.sin(t) + v[1], esc=0.9, rot=-0.15, alfa=v[0], altura=v[2] + 20)
        TX(lz, '4,5 años', t, w(29, 'cuatro') - 0.1, t1, lerp(1560, 1380, g), 420, tam=36, color=(226, 218, 198))
    if a(29) < t < a(31):
        DATO(lz, 'Planck · ESA · 2009–2013', t, a(29) + 0.4, a(31) - 0.5)


def s_planck_edad(lz, t, ex):
    """E12 (2:34–2:58): patrón + modelo → edad; 2013 → 2018, casi no se movió."""
    t0, t1 = a(31) - 0.1, a(32) - 0.2
    PZ(lz, 'mapa_cmb', t, t0, t1, 460, 520, esc=0.45)
    v = ventana(t, t0 + 0.3, t1)
    if v:
        g = suave((t - t0 - 0.3) / 1.6)
        hilo(lz, [(660, 520), (lerp(660, 1220, g), 520)], ancho=4, alfa=v[0])
    RELOJ(lz, 0, t, t0 + 1.2, t1, 1400, 520, esc=0.8)
    # gráfico: dos mediciones casi a la misma altura
    t0, t1 = a(32) - 0.1, a(35) - 0.3
    v = ventana(t, t0, t1)
    if v:
        Y = lambda val: 760 - (val - 13700) / 200 * 520     # noqa: E731
        X = eje(lz, t, t0, t1, 600, 1320, 820, 2011, 2020, [(2013, '2013'), (2018, '2018')])
        papel_dyn(lz, [('rect', 560, 240, 566, 820)], CREMA, alfa=v[0], altura=2, dy=v[1])
        t13 = w(32, '13 820') - 0.1
        if t > t13:
            DYN(lz, [('ell', X(2013) - 16, Y(13820) - 16, X(2013) + 16, Y(13820) + 16)], AZUL, t, t13, t1, alt=6)
            TX(lz, '13 820 M', t, t13, t1, X(2013), Y(13820) - 60, tam=36, color=(170, 200, 244))
        t18 = w(33, '13 797') - 0.1
        if t > t18:
            g = suave((t - t18 - 0.4) / 0.6)
            DYN(lz, [('rect', X(2018) - 5, Y(13797 + 23 * g), X(2018) + 5, Y(13797 - 23 * g))], AMBAR, t, t18, t1, alt=4)
            DYN(lz, [('ell', X(2018) - 16, Y(13797) - 16, X(2018) + 16, Y(13797) + 16)], AMBAR, t, t18, t1, alt=6)
            TX(lz, '13 797 ± 23 M', t, t18, t1, X(2018) + 40, Y(13797) + 80, tam=36, color=(244, 196, 104))
        tq = a(34) - 0.1
        if t > tq:
            g = suave((t - tq) / 0.8)
            hilo(lz, segmentos([(X(2013), Y(13820)), (lerp(X(2013), X(2018), g), lerp(Y(13820), Y(13797), g))], 12), ancho=3, alfa=v[0], discontinuo=True)
        DATO(lz, 'Planck 2013 y 2018 (ESA)', t, t13, t1)


def s_wmap(lz, t, ex):
    """E13–E14 (2:58–3:54): ¿y si Planck se equivocó?; WMAP; barras compatibles; depende del modelo; aparece el reloj 2."""
    CIFRA(lz, '?', t, a(35) - 0.1, a(36) - 0.3, 960, 520, tam=200)
    t0, t1 = a(36) - 0.1, a(37) - 0.4
    v = ventana(t, t0, t1)
    if v:
        z = 1 + 0.06 * suave((t - t0) / (t1 - t0))
        poner(lz, 'foto_wmap', 960, 470 + v[1], esc=z * 0.95, rot=-0.02, alfa=v[0], altura=v[2] + 6)
        TX(lz, 'WMAP (NASA): el mismo fondo cósmico, no es Planck', t, t0 + 0.6, t1, 960, 840, tam=32, peso=700)
        TX(lz, 'NASA / WMAP Science Team', t, t0 + 0.6, t1, 1640, 940, tam=24, color=(226, 218, 198), peso=600)
    # barras de error: WMAP (ancha) y Planck (estrecha) se solapan
    t0, t1 = a(37) - 0.1, a(41) - 0.3
    if ventana(t, t0, t1):
        X = eje(lz, t, t0, t1, 360, 1560, 820, 13650, 13900, [(13700, '13 700'), (13800, '13 800'), (13900, '13 900')])
        barra_error(lz, X, 13772, 59, 560, AZUL, t, t0 + 0.2, t1)
        TX(lz, 'WMAP · 13 772 ± 59 M', t, t0 + 0.4, t1, X(13772), 500, tam=34, color=(170, 200, 244))
        tp = w(38, '13 797') - 0.2
        barra_error(lz, X, 13797, 23, 680, AMBAR, t, tp, t1)
        TX(lz, 'Planck · 13 797 ± 23 M', t, tp + 0.2, t1, X(13797), 740, tam=34, color=(244, 196, 104))
        tc = a(40) - 0.2
        v = ventana(t, tc, t1)
        if v:
            papel_dyn(lz, [('rect', X(13797 - 23), 520, X(13772 + 59), 720)], AMBAR, alfa=v[0] * 0.28, altura=0, bisel=0)
            PZ(lz, 'check', t, tc + 0.2, t1, X(13850) + 80, 620, esc=0.9, alt=10)
    # depende del modelo; el reloj 2 entra
    t0, t1 = a(41) - 0.1, a(45) - 0.4
    mover = suave((t - a(44)) / 0.8)
    RELOJ(lz, 0, t, t0, t1, lerp(960, 560, mover), 540, esc=lerp(1.1, 0.8, mover))
    v = ventana(t, w(42, 'depende') - 0.2, a(44))
    if v:
        hilo(lz, segmentos([(190, 140), (lerp(960, 560, mover) - 150, 450)], 16), ancho=3, alfa=v[0], discontinuo=True)
    RELOJ(lz, 1, t, a(44) + 0.3, t1, 1380, 540, esc=0.9)
    PZ(lz, 'aviso', t, w(44, 'problemas') - 0.2, t1, 1500, 380, esc=0.9, alt=10)


def s_hubble(lz, t, ex):
    """E15–E16b (3:54–4:30): Hubble se equivocó por siete; diagrama velocidad–distancia; los puntos se corren × 7."""
    t0, t1 = a(45) - 0.1, a(46) - 0.3
    v = ventana(t, t0, t1)
    if v:
        g = suave((t - t0) / 4.0)
        for j, (dx, dy) in enumerate([(-1, -0.3), (1, 0.2), (-0.3, -1), (0.4, 1)]):
            poner(lz, 'galaxia', 960 + dx * (140 + 260 * g), 520 + dy * (90 + 150 * g) + v[1], esc=0.8, rot=j, alfa=v[0], altura=v[2])
        CIFRA(lz, '× 7', t, w(45, 'factor') - 0.2, t1, 960, 520, tam=200)
    t0, t1 = a(46) - 0.1, a(51) - 0.3
    v = ventana(t, t0, t1)
    if not v:
        return
    ox, oy, ax, ay = 420, 860, 1500, 260
    DYN(lz, [('rect', ox - 3, ay, ox + 3, oy)], CREMA, t, t0, t1)
    DYN(lz, [('rect', ox, oy - 3, ax, oy + 3)], CREMA, t, t0, t1)
    TX(lz, 'distancia →', t, t0 + 0.3, t1, ax - 110, oy + 44, tam=30, peso=700)
    TX(lz, 'velocidad ↑', t, t0 + 0.3, t1, ox + 110, ay - 30, tam=30, peso=700)
    TX(lz, '1929', t, w(46, '1929') - 0.1, t1, ox + 160, ay + 60, tam=40)
    rnd = np.random.RandomState(46)
    xs = np.sort(rnd.uniform(0.03, 0.135, 24))
    ys = np.clip(xs * 7 * 0.85 * (1 + rnd.normal(0, 0.12, 24)), 0.02, 0.98)
    corr = suave((t - w(48, 'siete veces') - 0.2) / 2.5)
    fade = suave((t - a(49)) / 1.0)
    for j in range(24):
        tj = a(46) + 1.5 + j * 0.2
        if t < tj:
            continue
        p = suave((t - tj) / 0.3)
        xf = xs[j] * lerp(1, 7, corr)
        X, Y = ox + xf * (ax - ox), oy - ys[j] * (oy - ay)
        papel_dyn(lz, [('ell', X - 9, Y - 9, X + 9, Y + 9)], AZUL, alfa=p * v[0] * (1 - 0.8 * fade), altura=4, dy=v[1])
    tl = a(46) + 4.0
    TX(lz, '24 galaxias', t, a(47) - 0.1, w(48, 'siete veces') - 0.3, 760, 420, tam=40, color=(170, 200, 244))
    if t > tl:
        pend = lerp(5.95, 0.85, corr)
        ex_, ey_ = (1 / pend, 1.0) if pend > 1 else (1.0, pend)
        g = suave((t - tl) / 0.7)
        col = (236, 200, 130) if fade < 0.5 else (255, 210, 120)
        hilo(lz, [(ox, oy + v[1]), (ox + ex_ * g * (ax - ox), oy - ey_ * g * (oy - ay) + v[1])], color=col, ancho=4 + 2 * fade, alfa=v[0])
        if fade > 0:
            ex.append((ox + ex_ * (ax - ox) * 0.6, oy - ey_ * (oy - ay) * 0.6, 160, (255, 200, 110), 0.2 * fade * v[0]))
    TX(lz, 'distancias × 7', t, w(48, 'siete veces') - 0.1, a(49) - 0.2, 1100, 820, tam=40, color=(244, 196, 104))
    PZ(lz, 'check', t, a(49) + 0.4, t1, 1380, 420, esc=1.1, alt=10)


def s_pan(lz, t, ex):
    """E17 (4:30–4:48): el espacio se estira como la masa de pan; rebobinar; constante de Hubble."""
    t0, t1 = a(51) - 0.1, a(54) - 0.3
    v = ventana(t, t0, t1)
    if not v:
        return
    crece = suave((t - t0 - 0.3) / 3.5)
    rebob = suave((t - w(52, 'rebobinar') - 0.2) / 2.5)
    e = lerp(lerp(0.7, 1.15, crece), 0.6, rebob)
    poner(lz, 'pan', 960, 600 + v[1], esc=e, alfa=v[0], altura=v[2])
    for j, (gx, gy) in enumerate([(-160, -30), (-40, 50), (90, -60), (180, 30), (10, -110), (-110, 70)]):
        poner(lz, 'galaxia', 960 + gx * e, 600 + gy * e + v[1], esc=0.3, rot=j, alfa=v[0], altura=v[2] + 4)
    PZ(lz, 'rebobinar', t, w(52, 'rebobinar') - 0.1, t1, 960, 260, esc=0.9)
    CIFRA(lz, 'H₀', t, w(53, 'constante') - 0.2, t1, 1560, 330, tam=150)


def s_escalera(lz, t, ex):
    """E18 (4:48–5:06): ¿cómo se mide?; escalera de distancias: cefeidas, supernovas, galaxias lejanas."""
    CIFRA(lz, '?', t, a(54) - 0.1, a(55) - 0.2, 960, 460, tam=200)
    t0, t1 = a(55) - 0.1, a(59) - 0.3
    if not ventana(t, t0, t1):
        return
    pasos = [(380, 800, 760), (760, 680, 1140), (1140, 560, 1520)]
    for j, (x0, y0, x1) in enumerate(pasos):
        DYN(lz, [('rect', x0, y0, x1, 900)], [(150, 138, 170), (124, 114, 150), (100, 92, 130)][j], t, t0 + j * 0.25, t1, alt=2)
    v = ventana(t, a(56) - 0.2, t1)
    if v:
        pul = 1 + 0.14 * math.sin(2 * math.pi * t / 1.3)
        poner(lz, 'cefeida', 570, 720 + v[1], esc=0.8 * pul, alfa=v[0], altura=v[2] + 6)
        ex.append((570, 720, 50 * pul, (255, 220, 130), 0.35 * v[0]))
    PZ(lz, 'supernova', t, a(57) - 0.2, t1, 950, 590, esc=0.9, alt=6)
    PZ(lz, 'galaxia', t, a(57) + 2.0, t1, 1330, 470, esc=0.9, alt=6)
    v = ventana(t, a(58) - 0.2, t1)
    if v:
        g = suave((t - a(58) + 0.2) / 1.2)
        for (p0, p1) in (((600, 660), (920, 540)), ((980, 530), (1300, 420))):
            n = 20
            pts = []
            for i in range(int(n * g) + 1):
                s_ = i / n
                pts.append((lerp(p0[0], p1[0], s_), lerp(p0[1], p1[1], s_) - math.sin(math.pi * s_) * 80))
            hilo(lz, pts, ancho=3, alfa=v[0])


def s_shoes(lz, t, ex):
    """E19–E21c (5:06–6:11): foto del Hubble; 73,04; el reloj al revés; dos barras de edad; orden de magnitud; guárdalas."""
    t0, t1 = a(59) - 0.1, a(60) - 0.3
    v = ventana(t, t0, t1)
    if v:
        sube = suave((t - w(59, '73,04') + 0.4) / 0.8)
        poner(lz, 'foto_hubble', 960, lerp(470, 360, sube) + v[1], esc=lerp(1.0, 0.78, sube), rot=0.015, alfa=v[0], altura=v[2] + 6)
        TX(lz, 'NASA, ESA, Adam G. Riess (STScI, JHU)', t, t0 + 0.6, t1, 960, lerp(760, 640, sube), tam=26, color=(226, 218, 198), peso=600)
    CIFRA(lz, '73,04', t, w(59, '73,04') - 0.2, t1, 860, 820, tam=150)
    TX(lz, '± 1,04', t, w(59, '1,04') - 0.2, t1, 1240, 830, tam=48, color=(244, 196, 104))
    if w(59, '73,04') < t < t1 + 0.5:
        DATO(lz, 'Riess et al. 2022 · ApJ Letters', t, w(59, '73,04'), t1)
    # el reloj al revés
    t0, t1 = a(60) - 0.1, a(61) + 0.8
    v = ventana(t, t0, t1)
    if v:
        reloj(lz, 1, 960, 500 + v[1], 1.0, t, alfa=v[0], altura=v[2], ang=-(t - t0) * 5)
        poner(lz, 'rebobinar', 960, 230 + v[1], esc=0.8, alfa=v[0], altura=v[2])
    # dos barras: con 73,04 → 13 400; con 67,4 → 14 500
    t0, t1 = a(61) + 0.6, a(63) - 0.3
    x0 = 360
    for (tt, val, h0, y, col, colt) in ((a(61) + 0.6, 13.4, '73,04', 470, AMBAR, (244, 196, 104)),
                                        (w(62, '67,4') - 0.2, 14.5, '67,4', 650, AZUL, (170, 200, 244))):
        v = ventana(t, tt, t1)
        if v:
            g = suave((t - tt) / 3.0)
            largo = 1200 * val / 14.5
            papel_dyn(lz, [('rect', x0, y - 22, x0 + largo * g, y + 22)], col, alfa=v[0], altura=v[2], dy=v[1])
            TX(lz, 'H₀ ' + h0, t, tt, t1, x0 - 10, y - 62, tam=34, color=colt)
            TX(lz, '≈ %s M de años' % ('13 400' if val < 14 else '14 500'), t, tt + 1.0, t1, x0 + largo - 130, y + 64, tam=34, color=colt)
    # orden de magnitud: 13 000 – 14 000 millones
    t0, t1 = a(63) - 0.1, a(66) - 0.3
    if ventana(t, t0, t1):
        v = ventana(t, t0, w(64, 'orden') - 0.2)
        if v:
            pts = [(560 + i * 9, 360 - 120 * (math.tanh((i - 45) / 18) * 0.5 + 0.5) - 30 * math.sin(i / 14)) for i in range(91)]
            hilo(lz, pts, ancho=4, alfa=v[0])
            TX(lz, 'la expansión cambia con el tiempo', t, t0 + 0.3, w(64, 'orden') - 0.2, 960, 470, tam=32, peso=700)
        X = eje(lz, t, w(64, 'orden') - 0.3, t1, 360, 1560, 760, 12000, 15000,
                [(12000, '12 000'), (13000, '13 000'), (14000, '14 000'), (15000, '15 000')])
        DYN(lz, [('rect', X(13000), 600, X(14000), 744)], AMBAR, t, w(64, '13 000') - 0.2, t1, alt=0, alfa=0.4, bisel=0)
        DYN(lz, [('rect', X(13800) - 4, 560, X(13800) + 4, 760)], AMBAR, t, a(65) - 0.1, t1, alt=6)
        TX(lz, 'NASA ≈ 13 800 M', t, a(65), t1, X(13800), 510, tam=36, color=(244, 196, 104))
    # 73 y 67: guárdalas (entran en un sobre)
    t0, t1 = a(66) - 0.1, a(69) - 0.3
    guard = suave((t - a(68) - 0.2) / 1.0)
    dentro = suave((t - a(68) - 1.0) / 0.4)
    for txt, ta, xa in (('73', w(66, '73'), 760), ('67', w(66, '67'), 1160)):
        CIFRA(lz, txt, t, ta - 0.2, t1, lerp(xa, 960 + (xa - 960) * 0.2, guard), lerp(440, 760, guard), tam=200,
              esc=lerp(1, 0.4, guard), alfa=1 - dentro)
    PZ(lz, 'sobre', t, a(68) - 0.4, t1, 960, 780, esc=0.9)
    PZ(lz, 'solapa', t, a(68) + 1.1, t1, 960, 780 - 110 * 0.9, esc=0.9, alt=4)


def s_estrellas(lz, t, ex):
    """E22–E25b (6:11–7:32): olvida la luz y la expansión; ninguna estrella mayor que el universo; 160 de 3 000; Gaia; edades."""
    olv1 = suave((t - w(69, 'olvida la luz')) / 0.6)
    olv2 = suave((t - w(69, 'olvida la exp')) / 0.6)
    t0, t1 = a(69) - 0.4, a(70) + 0.6
    v = ventana(t, t0, t1)
    if v:
        reloj(lz, 0, 560, 540 - 600 * olv1 + v[1], 0.75, t, alfa=v[0] * (1 - olv1), altura=v[2] + 40 * olv1)
        reloj(lz, 1, 960, 540 - 600 * olv2 + v[1], 0.75, t, alfa=v[0] * (1 - olv2), altura=v[2] + 40 * olv2)
    RELOJ(lz, 2, t, w(69, 'olvida la exp') + 0.6, a(70) - 0.2, 1360, 540, esc=0.9)
    # el universo y la estrella más vieja: la tira de la estrella no puede pasar el final
    t0, t1 = a(70) - 0.1, a(71) - 0.3
    PZ(lz, 'regla', t, t0, t1, 960, 470)
    PZ(lz, 'galaxia', t, t0 + 0.3, t1, 210, 470, esc=0.6)
    v = ventana(t, t0 + 0.6, t1)
    if v:
        g = suave((t - t0 - 0.6) / 4.0)
        papel_dyn(lz, [('rect', 260, 580, 260 + 1380 * g, 624)], (238, 150, 72), alfa=v[0], altura=v[2], dy=v[1])
        poner(lz, 'estrella', 210, 602 + v[1], esc=0.45, alfa=v[0], altura=v[2])
        DYN(lz, [('rect', 1656, 420, 1666, 660)], ROJO, t, w(70, 'no puede') - 0.2, t1, alt=8)
    # ¿cómo se sabe la edad de una estrella?
    CIFRA(lz, '?', t, a(71) - 0.1, a(72) - 0.2, 960, 300, tam=170)
    t0, t1 = a(71) - 0.1, a(73) - 0.3
    v = ventana(t, t0, t1)
    if v:
        ev = suave((t - a(72) - 0.5) / 7.0)
        for (x, r, c0, c1, apaga) in ((600, 74, (150, 190, 255), (220, 90, 60), 1.0), (960, 52, (255, 236, 160), (240, 150, 80), 0.25), (1320, 32, (230, 120, 80), (220, 100, 70), 0.0)):
            k = min(1, ev / max(0.3, 1 - apaga * 0.4)) * (0.2 + 0.8 * apaga)
            col = tuple(int(lerp(c0[i], c1[i], k)) for i in range(3))
            rr = r * (1 + 0.25 * k * apaga) * (1 - 0.6 * max(0, ev - 0.75) * 4 * apaga)
            al = v[0] * (1 - 0.85 * max(0, (ev - 0.8) * 5) * apaga)
            papel_dyn(lz, [('ell', x - rr, 560 - rr, x + rr, 560 + rr)], col, alfa=al, altura=v[2] + 4, dy=v[1])
            ex.append((x, 560 + v[1], rr * 1.4, col, 0.25 * al))
    PZ(lz, 'documento', t, a(73) - 0.1, w(73, '160') - 0.5, 960, 500, esc=1.3)
    TX(lz, 'Astronomy & Astrophysics · marzo 2026', t, a(73) + 0.3, w(73, '160') - 0.5, 960, 740, tam=36)
    # 160 de 3 000 candidatas (cuadrícula) y Gaia
    t0, t1 = w(73, '160') - 0.4, a(74) - 0.3
    v = ventana(t, t0, t1)
    if v:
        rnd = np.random.RandomState(73)
        elegidas = set(rnd.choice(3000, 160, replace=False))
        g = suave((t - w(73, 'elegidas')) / 1.4)
        d = ImageDraw.Draw(lz, 'RGBA')
        for idx in range(3000):
            c, f_ = idx % 75, idx // 75
            x, y = 257 + c * 19, 189 + f_ * 17 + v[1]
            if idx in elegidas and g > 0:
                d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=AMBAR + (int(255 * v[0] * g),))
            else:
                d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(226, 218, 198, int(150 * v[0])))
    tg = w(73, 'Gaia') - 0.2
    PZ(lz, 'foto_gaia', t, tg, a(74) - 0.3, 1330, 470, esc=0.55, rot=0.03, alt=10)
    TX(lz, 'ESA/Gaia/DPAC · CC BY-SA 3.0 IGO', t, tg + 0.3, a(74) - 0.3, 1330, 760, tam=24, color=(226, 218, 198), peso=600)
    if w(73, 'marzo') < t < a(80):
        DATO(lz, 'Tomasetti et al. 2026 · A&A 707, A111', t, w(73, 'marzo'), a(80) - 0.5)
    # edad media 13 600 y límite inferior 13 800
    t0, t1 = a(74) - 0.1, a(76) - 0.3
    if ventana(t, t0, t1):
        X = eje(lz, t, t0, t1, 360, 1560, 780, 12000, 15000, [(12000, '12 000'), (13000, '13 000'), (14000, '14 000'), (15000, '15 000')])
        DYN(lz, [('ell', X(13600) - 16, 660 - 16, X(13600) + 16, 660 + 16)], AMBAR, t, a(74) + 0.3, t1, alt=6)
        TX(lz, 'media 13 600 M', t, a(74) + 0.5, t1, X(13600), 600, tam=34, color=(244, 196, 104))
        DYN(lz, [('rect', X(12800), 690, X(14800), 760)], AZUL, t, a(75) + 0.2, t1, alt=0, alfa=0.35, bisel=0)
        DYN(lz, [('poly', [(X(13800), 470), (X(14800), 470), (X(14800), 446), (X(15000), 486), (X(14800), 526), (X(14800), 502), (X(13800), 502)])],
            AMBAR, t, w(75, 'como mínimo') - 0.2, t1, alt=6)
        TX(lz, 'mínimo 13 800 M', t, w(75, 'como mínimo'), t1, X(13800) + 40, 420, tam=34, color=(244, 196, 104))
    # 70 estrellas por encima de 13 000 y ninguna por encima de 14 100
    t0, t1 = a(76) - 0.1, a(80) - 0.3
    if ventana(t, t0, t1):
        X = eje(lz, t, t0, t1, 360, 1560, 800, 12000, 15000, [(12000, '12 000'), (13000, '13 000'), (14000, '14 000'), (15000, '15 000')])
        v = ventana(t, w(77, '13 000') - 0.3, t1)
        if v:
            hilo(lz, segmentos([(X(13000), 790), (X(13000), 330)], 14), ancho=3, alfa=v[0], discontinuo=True)
        DYN(lz, [('rect', X(14100) - 5, 320, X(14100) + 5, 792)], ROJO, t, w(77, '14 100') - 0.2, t1, alt=8)
        cuentas = [3, 5, 7, 9, 10, 10, 9, 7, 5, 3, 2]
        orden = [(c, k) for c in range(11) for k in range(cuentas[c])]
        rnd = np.random.RandomState(77)
        rnd.shuffle(orden)
        ts = a(77) + 0.3
        for n_, (c, k) in enumerate(orden):
            tj = ts + n_ * 0.06
            if t < tj:
                continue
            xa = X(13000 + c * 100) + 3
            ya = 786 - (k + 1) * 17
            DYN(lz, [('rect', xa, ya, xa + 34, ya + 14)], (238, 150, 72), t, tj, t1, alt=2, din=0.3)
        DYN(lz, [('rect', X(13800) - 3, 300, X(13800) + 3, 792)], AMBAR, t, a(79) - 0.2, t1, alt=4)
        TX(lz, '≈ 13 800 M', t, a(79), t1, X(13800), 260, tam=36, color=(244, 196, 104))


def s_juntos(lz, t, ex):
    """E26–E27 (7:32–8:12): menos preciso pero sin modelo; tres relojes, tres caminos; juntos señalan 13 800."""
    t0, t1 = a(80) - 0.1, a(81) - 0.3
    if ventana(t, t0, t1):
        X = eje(lz, t, t0, t1, 360, 1560, 760, 12500, 15000, [(13000, '13 000'), (14000, '14 000')])
        barra_error(lz, X, 13797, 23, 520, AMBAR, t, t0 + 0.2, t1)
        poner(lz, 'reloj0', 280, 520, 0.3, alfa=(ventana(t, t0, t1) or (0,))[0], altura=4)
        barra_error(lz, X, 13800, 1000, 640, (238, 150, 72), t, t0 + 0.8, t1)
        poner(lz, 'reloj2', 280, 640, 0.3, alfa=(ventana(t, t0 + 0.8, t1) or (0,))[0], altura=4)
    t0, t1 = a(81) - 0.1, a(84) - 0.3
    v = RELOJ(lz, 2, t, t0, t1, 960, 540, esc=1.1)
    TX(lz, 'ΛCDM', t, t0 + 0.3, w(81, 'no usa') + 0.6, 1260, 300, tam=64, tipo='glifo', color=AMBAR)
    if v and t > a(83) - 0.2:
        ex.append((960, 540, 200, (255, 210, 130), 0.25 * v[0] * suave((t - a(83) + 0.2) / 0.6)))
    t0, t1 = a(84) - 0.1, a(86) - 0.3
    for i, x in enumerate((500, 960, 1420)):
        RELOJ(lz, i, t, t0 + i * 0.2, t1, x, 480, esc=0.75)
    v = ventana(t, a(85) - 0.2, t1)
    if v:
        g = suave((t - a(85) + 0.2) / 1.2)
        for x, xb in ((500, 300), (960, 960), (1420, 1620)):
            pts = [(lerp(xb, x, s_), lerp(1080, 620, s_) + math.sin(s_ * math.pi) * 30) for s_ in np.linspace(0, g, 20)]
            hilo(lz, pts, ancho=4, alfa=v[0])
    # juntos
    t0, t1 = a(86) - 0.1, a(91) - 0.3
    if ventana(t, t0, t1):
        X = eje(lz, t, t0, t1, 500, 1600, 860, 12500, 15000, [(13000, '13 000'), (14000, '14 000'), (15000, '15 000')])
        filas = [(a(87), 0, 13797, 23, AMBAR, 400), (a(88), 1, 13950, 550, AZUL, 560), (a(89), 2, 13800, 1000, (238, 150, 72), 720)]
        for (tt, i, c, m, col, y) in filas:
            v = ventana(t, tt - 0.2, t1)
            if v:
                poner(lz, 'reloj%d' % i, 380, y + v[1], 0.32, alfa=v[0], altura=v[2])
                barra_error(lz, X, c, m, y, col, t, tt, t1)
        v = ventana(t, a(90) + 1.5, t1)
        if v:
            papel_dyn(lz, [('rect', X(13800) - 10, 330, X(13800) + 10, 790)], AMBAR, alfa=v[0] * 0.5, altura=0, bisel=0)
            ex.append((X(13800), 560, 120, (255, 200, 110), 0.25 * v[0]))
        TX(lz, '≈ 13 800 M', t, a(90) + 1.6, t1, X(13800), 290, tam=40, color=(244, 196, 104))


def s_tension(lz, t, ex):
    """E28–E30b (8:12–9:11): pero hay un problema; 67,4 frente a 73,04; tensión de Hubble; el puente entre épocas."""
    PZ(lz, 'aviso', t, a(91) - 0.1, a(92) - 0.2, 960, 460, esc=1.5, alt=10)
    t0, t1 = a(92) - 0.1, a(93) - 0.3
    PZ(lz, 'sobre', t, t0, t1, 960, 760, esc=0.9)
    sale_ = suave((t - t0 - 0.6) / 1.0)
    for txt, xa in (('73', 760), ('67', 1160)):
        CIFRA(lz, txt, t, t0 + 0.5, t1, lerp(960, xa, sale_), lerp(740, 420, sale_), tam=200, esc=lerp(0.4, 1, sale_))
    t0, t1 = a(93) - 0.1, a(97) - 0.3
    if ventana(t, t0, t1):
        X = eje(lz, t, t0, t1, 360, 1560, 820, 64, 76, [(65, '65'), (67, '67'), (69, '69'), (71, '71'), (73, '73'), (75, '75')])
        tp, ts = a(93) + 0.4, a(94) - 0.1
        barra_error(lz, X, 67.4, 0.5, 620, AMBAR, t, tp, t1)
        TX(lz, 'Planck · 67,4', t, tp + 0.2, t1, X(67.4), 550, tam=36, color=(244, 196, 104))
        barra_error(lz, X, 73.04, 1.04, 620, AZUL, t, ts, t1)
        TX(lz, 'Cefeidas · 73,04', t, ts + 0.2, t1, X(73.04), 550, tam=36, color=(170, 200, 244))
        tg = w(95, '8 %') - 0.3
        DYN(lz, [('rect', X(67.9), 600, X(72.0), 640)], ROJO, t, tg, t1, alt=0, alfa=0.45, bisel=0)
        CIFRA(lz, '8 %', t, tg + 0.2, t1, X(70), 440, tam=110, color=(236, 120, 96))
        tc = w(95, 'cinco') - 0.8
        for j in range(5):
            xa = X(67.9) + j * (X(1.15) - X(0)) * 0.99
            DYN(lz, [('rect', xa + 2, 690, xa + (X(1.15) - X(0)) - 2, 712)], AMBAR, t, tc + j * 0.2, t1, alt=4)
        TX(lz, '≈ 5 márgenes de error', t, tc + 1.2, t1, X(70), 760, tam=32, color=(244, 196, 104))
        TX(lz, 'TENSIÓN DE HUBBLE', t, a(96) - 0.1, t1, 960, 200, tam=60)
    t0, t1 = a(97) - 0.1, a(102) - 0.3
    if ventana(t, t0, t1):
        DYN(lz, [('rect', 220, 300, 800, 760)], (54, 64, 116), t, t0 + 0.2, t1, alt=6)
        DYN(lz, [('rect', 1120, 300, 1700, 760)], (54, 64, 116), t, t0 + 0.4, t1, alt=6)
        v = ventana(t, a(99) - 0.2, t1)
        if v:
            g = suave((t - a(99)) / 3.0)
            for j, (gx, gy) in enumerate([(-1, -0.4), (1, -0.2), (-0.4, 1), (0.6, 0.8)]):
                poner(lz, 'galaxia', 510 + gx * (60 + 120 * g), 520 + gy * (50 + 90 * g) + v[1], esc=0.55, rot=j, alfa=v[0], altura=v[2] + 4)
        TX(lz, 'HOY · se mide', t, a(99) - 0.1, t1, 510, 700, tam=36)
        PZ(lz, 'mapa_cmb', t, a(100) - 0.2, t1, 1410, 500, esc=0.55, alt=4)
        TX(lz, 'INICIO · se predice', t, a(100) - 0.1, t1, 1410, 700, tam=36)
        for j in range(9):
            if j == 4:
                continue
            x = 820 + j * 32
            DYN(lz, [('rect', x, 512, x + 26, 548)], (196, 160, 110), t, a(101) - 0.2 + j * 0.12, t1, alt=4)
        v = ventana(t, a(101) + 1.4, t1)
        if v:
            CIFRA(lz, '?', t, a(101) + 1.4, t1, 820 + 4 * 32 + 13, 450, tam=110, alfa=0.75 + 0.25 * math.sin(t * 2.5))


def s_pruebas(lz, t, ex):
    """E31–E34 (9:11–10:06): ¿error de medición? Webb; ACT; el tercero; lo que está en juego."""
    t0, t1 = a(102) - 0.1, a(105) - 0.3
    PZ(lz, 'regla', t, t0, t1, 820, 640, esc=0.75)
    CIFRA(lz, '?', t, t0, w(104, 'descartar') - 0.2, 820, 460, tam=160)
    PZ(lz, 'webb', t, w(104, 'Webb') - 0.2, t1, 1430, 420, esc=1.0, alt=10)
    TX(lz, 'Webb · 2024', t, w(104, 'Webb'), t1, 1430, 640, tam=36)
    PZ(lz, 'check', t, w(104, 'descartar') - 0.1, t1, 820, 470, esc=1.2, alt=12)
    t0, t1 = a(105) - 0.1, a(106) - 0.3
    PZ(lz, 'act', t, t0, t1, 560, 520, esc=1.0)
    if ventana(t, t0, t1):
        X = eje(lz, t, t0 + 0.3, t1, 1000, 1720, 760, 64, 76, [(67, '67'), (73, '73')])
        barra_error(lz, X, 67.4, 0.5, 640, AMBAR, t, t0 + 0.5, t1)
        barra_error(lz, X, 67.6, 0.6, 590, (250, 214, 150), t, w(105, 'confirmaron') - 0.2, t1)
        TX(lz, 'ACT 2025 ≈ Planck', t, w(105, 'confirmaron'), t1, 1200, 520, tam=34, color=(244, 196, 104))
        DATO(lz, 'ACT · Hill et al. · JCAP 2025', t, w(105, 'ACT'), t1)
    t0, t1 = a(106) - 0.1, a(108) - 0.3
    if ventana(t, t0, t1):
        X = eje(lz, t, t0, t1, 360, 1560, 780, 64, 76, [(65, '65'), (67, '67'), (69, '69'), (71, '71'), (73, '73'), (75, '75')])
        barra_error(lz, X, 67.4, 0.5, 600, AMBAR, t, t0 + 0.2, t1)
        barra_error(lz, X, 73.04, 1.04, 600, AZUL, t, t0 + 0.4, t1)
        tv = w(107, '70,39') - 0.3
        barra_error(lz, X, 70.39, 1.8, 600, VERDE, t, tv, t1)
        TX(lz, '70,39', t, tv + 0.2, t1, X(70.39), 520, tam=44, color=(160, 220, 160))
        DATO(lz, 'Freedman et al. 2025 · ApJ 985, 203', t, tv, t1)
    t0, t1 = a(108) - 0.1, a(113) - 0.3
    CIFRA(lz, '?', t, t0, a(110) - 0.2, 960, 420, tam=160)
    PZ(lz, 'check', t, a(109) - 0.1, a(110) - 0.2, 1120, 420, esc=0.9, alt=8)
    v = PZ(lz, 'regla', t, a(110) - 0.1, t1, 960, 640)
    if v:
        tm = w(111, '12 700') - 0.3
        xe, xm = 1660, 260 + 1400 * 12.8 / 13.797
        v2 = ventana(t, tm, t1)
        if v2:
            g = suave((t - tm) / 1.0)
            papel_dyn(lz, [('rect', lerp(xe, xm, g), 606, xe, 674)], AMBAR, alfa=v2[0] * 0.92, altura=v2[2] + 6, dy=v2[1])
            poner(lz, 'bandera', xm, 600 + v2[1], esc=1.0, alfa=v2[0], altura=v2[2])
        TX(lz, '12 700 – 12 900 M', t, tm + 0.6, t1, xm - 120, 520, tam=34, color=(244, 196, 104))
        TX(lz, '≈ 1 000 M de años', t, a(112) - 0.1, t1, (xe + xm) / 2, 760, tam=40, color=(244, 196, 104))


def s_cierre(lz, t, ex):
    """E35–E39 (10:06–11:47): tres niveles; ¿error o modelo?; nadie estuvo allí; pregunta; suscripción."""
    t0, t1 = a(113) - 0.1, a(117) - 0.3
    tarjetas = [(a(114), 480, VERDE, 'check', 'Comprobado'), (a(115), 960, AMBAR, '≈', 'Probable'), (a(116), 1440, ROJO, '?', 'Sin resolver')]
    foco = suave((t - a(116) - 0.8) / 0.8)
    for (tt, x, col, icono, palabra) in tarjetas:
        v = ventana(t, tt - 0.2, t1)
        if not v:
            continue
        al = 1 - 0.55 * foco * (palabra != 'Sin resolver')
        es = 1 + 0.08 * foco * (palabra == 'Sin resolver') * (1 + 0.3 * math.sin(t * 3))
        papel_dyn(lz, [('rect', x - 200 * es, 330 - 170 * es, x + 200 * es, 330 + 230 * es)], CREMA, alfa=v[0] * al, altura=v[2], dy=v[1] + 120)
        papel_dyn(lz, [('rect', x - 200 * es, 330 - 170 * es, x + 200 * es, 330 - 120 * es)], col, alfa=v[0] * al, altura=0, dy=v[1] + 120)
        if icono == 'check':
            poner(lz, 'check', x, 470 + v[1], esc=es, alfa=v[0] * al, altura=v[2] + 4)
        else:
            CIFRA(lz, icono, t, tt - 0.2, t1, x, 470, tam=150, color=col, esc=es, alfa=al)
        TX(lz, palabra, t, tt, t1, x, 640, tam=40, tinta=TINTA, color=CREMA, alfa=al)
    t0, t1 = a(117) - 0.1, a(120) - 0.3
    PZ(lz, 'regla', t, t0, t1, 560, 600, esc=0.6)
    CIFRA(lz, '?', t, t0 + 0.2, t1, 560, 440, tam=140)
    PZ(lz, 'puzle', t, a(118) - 0.2, t1, 1360, 540, esc=0.75)
    v = ventana(t, a(119) - 0.2, t1)
    if v:
        ex.append((1360 + 145 * 0.75, 540 - 145 * 0.75, 90, (255, 200, 110), 0.4 * v[0] * (0.7 + 0.3 * math.sin(t * 2))))
    TX(lz, 'Adam Riess: «falta algo en el modelo»', t, a(119), t1, 1360, 860, tam=32)
    # nadie estuvo allí: la luz en la cartulina; luego las pruebas
    t0, t1 = a(120) - 0.1, a(122) - 0.2
    if t0 < t < t1 + 1.2:
        abre = suave((t - t1) / 1.2)
        cierra = suave((t - t0) / 0.8)
        r = lerp(1600, 40, cierra) + 1600 * abre ** 2.2
        ex.append((960, 540, 40 + r * 0.6, (255, 214, 150), 0.8 * cierra * (1 - abre)))
        lz = tapa(lz, r)
    t0, t1 = a(122) + 0.4, a(126) - 0.2
    PZ(lz, 'mapa_cmb', t, a(123) - 0.2, t1, 470, 520, esc=0.42)
    v = ventana(t, a(124) - 0.2, t1)
    if v:
        g = suave((t - a(124)) / 2.0)
        for j, (gx, gy) in enumerate([(-1, -0.4), (1, -0.2), (-0.4, 1), (0.6, 0.8)]):
            poner(lz, 'galaxia', 960 + gx * (40 + 80 * g), 520 + gy * (30 + 60 * g) + v[1], esc=0.45, rot=j, alfa=v[0], altura=v[2] + 4)
    PZ(lz, 'estrella', t, a(125) - 0.2, t1, 1450, 520, esc=0.9)
    for i, x in enumerate((470, 960, 1450)):
        RELOJ(lz, i, t, a(126) - 0.1 + i * 0.15, a(127) - 0.2, x, 520, esc=0.75)
    t0, t1 = a(127) - 0.1, a(128) - 0.3
    PZ(lz, 'puzle', t, t0, t1, 960, 540, esc=0.9)
    v = ventana(t, t0 + 0.3, t1)
    if v:
        g = suave((t - t0) / 6.0)
        poner(lz, 'pieza_suelta', lerp(1330, 1095, g * 0.75), lerp(250, 380, g * 0.75) + v[1], esc=0.9, rot=lerp(0.3, 0.05, g), alfa=v[0], altura=lerp(30, 14, g))
    # pregunta al público
    t0, t1 = a(128) - 0.1, a(133) - 0.3
    PZ(lz, 'regla', t, w(129, 'error') - 0.2, t1, 520, 560, esc=0.5)
    CIFRA(lz, '?', t, w(129, 'error'), t1, 520, 430, tam=120)
    TX(lz, 'error de medición', t, w(129, 'error') + 0.2, t1, 520, 700, tam=36)
    CIFRA(lz, 'o', t, w(129, 'modelo') - 0.6, t1, 960, 470, tam=110, color=CREMA)
    PZ(lz, 'puzle', t, w(129, 'modelo') - 0.2, t1, 1360, 500, esc=0.55)
    TX(lz, 'falta algo en el modelo', t, w(129, 'modelo'), t1, 1360, 700, tam=36)
    PZ(lz, 'comentario', t, a(130) - 0.2, t1, 960, 860, esc=0.7)
    PZ(lz, 'documento', t, a(131) - 0.2, t1, 1700, 860, esc=0.6)
    # suscripción (única CTA)
    t0, t1 = a(133) - 0.1, DUR
    TX(lz, 'SUSCRÍBETE', t, w(133, 'suscr') - 0.2, t1, 600, 540, tam=60, color=(204, 52, 44), tinta=(250, 246, 240), peso=900)
    PZ(lz, 'like', t, w(133, 'like') - 0.2, t1, 1050, 540, esc=1.1)
    PZ(lz, 'campana', t, w(133, 'campanita') - 0.2, t1, 1330, 540, esc=1.1)
    return lz


ESCENAS = [s_inicio, s_puzle, s_reloj1_intro, s_lambda, s_niebla, s_fondo_cosmico, s_planck_edad, s_wmap,
           s_hubble, s_pan, s_escalera, s_shoes, s_estrellas, s_juntos, s_tension, s_pruebas, s_cierre]


def escena(t):
    lz = fondo(t)
    ex = []
    for s in ESCENAS:
        r = s(lz, t, ex)
        if r is not None:
            lz = r
    arr = np.asarray(lz.convert('RGB'), np.float32)
    for x, y, sg, c, f in ex:
        brillo(arr, x, y, sg, c, f)
    return arr


def acabado(arr, t):
    l = arr.mean(2, keepdims=True)
    arr = l + (arr - l) * 0.95
    arr = arr * FIJOS['vineta'] * FIJOS['papel']
    rnd = np.random.RandomState(int(t * 24) % 100000)
    g = rnd.randn(H // 2, W // 2).astype(np.float32)
    g = np.asarray(Image.fromarray(g, 'F').resize((W, H), Image.BILINEAR), np.float32)
    arr = arr + (g * 2.2)[..., None]
    return np.clip(arr, 0, 255).astype(np.uint8)


def fotograma(i):
    cargar()
    t = i / FPS
    return acabado(escena(t), t)


def _bytes(i):
    return fotograma(i).tobytes()

# ------------------------------------------------------------------ render


def render(i0, i1, mp4, con_audio=False):
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-']
    if con_audio:
        cmd += ['-ss', '%.3f' % (i0 / FPS), '-t', '%.3f' % ((i1 - i0) / FPS), '-i', AUDIO, '-c:a', 'aac', '-b:a', '192k']
    cmd += ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    from multiprocessing import Pool
    t0 = time.time()
    with Pool(max(1, (os.cpu_count() or 4) - 1)) as pool:
        for j, bts in enumerate(pool.imap(_bytes, range(i0, i1), chunksize=4)):
            pr.stdin.write(bts)
            if j % 240 == 0:
                print(f'  {(i0 + j) / FPS:7.1f} s ({time.time() - t0:.0f} s)', flush=True)
    pr.stdin.close()
    pr.wait()


def main():
    args = sys.argv[1:]
    os.makedirs(SALIDA, exist_ok=True)
    construir('--rehacer' in args)
    if '--frame' in args:
        i = args.index('--frame')
        t = float(args[i + 1])
        ruta = args[i + 2] if len(args) > i + 2 else os.path.join(SALIDA, 'papel-%07.2f.png' % t)
        Image.fromarray(fotograma(int(round(t * FPS)))).save(ruta)
        print('fotograma:', ruta)
        return
    if '--rango' in args:
        i = args.index('--rango')
        s0, s1 = float(args[i + 1]), float(args[i + 2])
        mp4 = os.path.join(SALIDA, 'papel_rango_%d_%d.mp4' % (s0, s1))
        render(int(s0 * FPS), int(s1 * FPS), mp4, con_audio=True)
        print('tramo:', mp4)
        return
    partes = os.path.join(SALIDA, '_partes_papel')
    os.makedirs(partes, exist_ok=True)
    lista = []
    paso = 60 * FPS
    for i0 in range(0, N, paso):
        i1 = min(N, i0 + paso)
        mp4 = os.path.join(partes, 'p%05d.mp4' % (i0 // FPS))
        lista.append(mp4)
        if os.path.exists(mp4) and '--forzar' not in args:
            continue
        print('parte', i0 // FPS, flush=True)
        render(i0, i1, mp4)
    with open(os.path.join(partes, 'lista.txt'), 'w') as f:
        for m in lista:
            f.write("file '%s'\n" % m.replace('\\', '/'))
    final = os.path.join(SALIDA, 'video-02-papel.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', os.path.join(partes, 'lista.txt'), '-i', AUDIO,
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', final], check=True)
    print('video:', final)


if __name__ == '__main__':
    main()
