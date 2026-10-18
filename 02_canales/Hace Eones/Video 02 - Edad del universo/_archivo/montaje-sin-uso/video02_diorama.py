"""
Video 2 · ¿Cómo sabemos la edad del universo si nadie estuvo allí? — versión DIORAMA DE PAPEL EN 3D (aprobada el 16-oct-2026).

Los primeros 41 s son la prueba aprobada (Tarea-video/diorama_video.py). Desde ahí la cámara recorre una mesa larga con una
«estación» por escena de la escaleta: piezas de cartón de pie, gráficos de cartón que se animan con cada medida, fotos
oficiales y sellos «Dato verificado». Voz de Raúl + música (salida/_audio-con-musica.wav) + efectos suaves.

Se entrega en 10 partes iguales para validarlas una a una; al final se unen.
  python video02_diorama.py --parte 1            -> salida/diorama/video-02-diorama-parte-01.mp4
  python video02_diorama.py --frame 95.0 f.png   -> un fotograma
  python video02_diorama.py --hoja 142 214 6 h.png -> hoja de contacto de un tramo
  python video02_diorama.py --verificar 41 120   -> piezas cortadas en los bordes en ese tramo
  python video02_diorama.py --unir               -> salida/video-02-diorama-final.mp4 (cuando las 10 partes estén validadas)
"""
import functools
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
TAREA = os.path.normpath(os.path.join(AQUI, '..', '..', '..', 'Tarea-video'))
sys.path.insert(0, TAREA)
import diorama_video as D     # noqa: E402
import diorama_demo as DD     # noqa: E402
import pintura as P           # noqa: E402

W, H, FPS = 1920, 1080, 24
f32 = np.float32
SALIDA = os.path.join(AQUI, 'salida', 'diorama')
CACHE = os.path.join(AQUI, 'cache_diorama2')
AUDIO_VOZ = os.path.join(AQUI, 'salida', '_audio-con-musica.wav')
with open(os.path.join(AQUI, 'tiempos.json'), encoding='utf-8') as _f:
    _TJ = json.load(_f)
F = _TJ['frases']
DUR = round(float(_TJ['total']) + 1.6, 2)
N = int(DUR * FPS)
PARTES = 10
T_D = 40.8                     # hasta aquí manda la prueba aprobada de 41 s
ESC_PIEZAS = 1.2               # las piezas de las estaciones, un 20 % más grandes

suave, suave3, lerp = D.suave, D.suave3, D.lerp


def a(i):
    return F[i]['ini']


def b(i):
    return F[i]['fin']


def w(i, trozo):
    f = F[i]
    pos = f['texto'].find(trozo)
    if pos < 0:
        raise ValueError((i, trozo, f['texto']))
    return f['ini'] + (f['fin'] - f['ini']) * pos / len(f['texto'])

# ================================================================== tipografía y piezas de texto


@functools.lru_cache(maxsize=256)
def fuente(px, peso=700, ancho=75):
    return DD.fuente(px, peso, ancho)


@functools.lru_cache(maxsize=256)
def etiqueta(texto, tam=70, papel=(240, 236, 226), tinta=(28, 26, 32)):
    return DD.etiqueta(texto, tam, sum(map(ord, texto)) % 97, papel=papel, tinta=tinta)


@functools.lru_cache(maxsize=128)
def cartel(texto, alto=300):
    return D.cartel(texto, alto, sum(map(ord, texto)) % 89 + 3)


@functools.lru_cache(maxsize=64)
def sprite(nombre):
    return DD.sprite(nombre)


@functools.lru_cache(maxsize=32)
def fondo_panel(w_, h_, semilla=5, color=(240, 232, 212)):
    col = DD.carton(w_, h_, semilla, color)
    im = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).convert('RGBA')
    ImageDraw.Draw(im).rectangle([6, 6, w_ - 7, h_ - 7], outline=(120, 96, 70, 255), width=6)
    return im


def cartel_h0():
    """«H₀» (Bahnschrift no tiene el subíndice: se compone a mano)."""
    a_ = cartel('H', 300)
    b_ = cartel('0', 170)
    im = Image.new('RGBA', (a_.width + b_.width - 40, a_.height), (0, 0, 0, 0))
    im.alpha_composite(a_, (0, 0))
    im.alpha_composite(b_, (a_.width - 40, a_.height - b_.height))
    return im

# ================================================================== gráficos de cartón (se redibujan con su progreso)


TINTA = (28, 26, 32)
AMBAR = (240, 168, 56)
AZUL = (70, 112, 186)
ROJO = (196, 40, 36)
VERDE = (70, 150, 80)
NAR = (226, 128, 60)


def _eje(d, x0, x1, y, v0, v1, marcas, tam=40):
    X = lambda v: x0 + (v - v0) / (v1 - v0) * (x1 - x0)   # noqa: E731
    d.line([x0 - 20, y, x1 + 20, y], fill=TINTA, width=6)
    for v, txt in marcas:
        d.line([X(v), y - 16, X(v), y + 16], fill=TINTA, width=4)
        if txt:
            d.text((X(v), y + 46), txt, font=fuente(tam, 600), fill=TINTA, anchor='mm')
    return X


def _barra(d, X, c, m, y, col, g, grosor=40, etiqueta_txt=None, tam=46):
    if g <= 0:
        return
    xa, xb = X(c - m * g), X(c + m * g)
    if xb - xa < 10:
        xa, xb = X(c) - 5, X(c) + 5
    d.rounded_rectangle([xa, y - grosor / 2, xb, y + grosor / 2], radius=8, fill=col + (255,))
    d.line([X(c), y - grosor / 2 - 14, X(c), y + grosor / 2 + 14], fill=TINTA, width=6)
    if etiqueta_txt:
        d.text((X(c), y - grosor / 2 - 14 - tam * 0.6), etiqueta_txt, font=fuente(tam, 700), fill=TINTA, anchor='mm')


def _transl(im, caja, fill):
    """Rectángulo translúcido mezclado sobre el panel (dibujarlo directo dejaría el cartón transparente)."""
    capa = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(capa).rectangle(caja, fill=fill)
    im.alpha_composite(capa)


def _titulo(d, w_, texto, sub=None, col=(170, 60, 24)):
    d.text((w_ / 2, 80), texto, font=fuente(84), fill=col + (255,), anchor='mm')
    if sub:
        d.text((w_ / 2, 158), sub, font=fuente(52, 500), fill=(60, 54, 60, 255), anchor='mm')


def g_2013_2018(p13, p18, pl):
    im = fondo_panel(1700, 960, 11).copy()
    d = ImageDraw.Draw(im)
    d.text((850, 90), 'PLANCK: CASI NO SE MOVIÓ', font=fuente(104), fill=(170, 60, 24, 255), anchor='mm')
    d.text((850, 180), 'edad del universo, en millones de años', font=fuente(58, 500), fill=(60, 54, 60, 255), anchor='mm')
    Y = lambda v: 700 - (v - 13700) / 200 * 420   # noqa: E731
    X = _eje(d, 260, 1440, 800, 2011, 2020, [(2013, '2013'), (2018, '2018')], 76)
    if pl > 0:
        x0, y0, x1, y1 = X(2013), Y(13820), X(2018), Y(13797)
        n = 14
        for i in range(int(n * pl)):
            if i % 2 == 0:
                d.line([lerp(x0, x1, i / n), lerp(y0, y1, i / n), lerp(x0, x1, (i + 1) / n), lerp(y0, y1, (i + 1) / n)], fill=(90, 80, 70, 255), width=8)
        d.text(((x0 + x1) / 2, (y0 + y1) / 2 - 70), 'CASI IGUAL', font=fuente(70), fill=(90, 80, 70, int(255 * pl)), anchor='mm')
    if p13 > 0:
        r = 34 * p13
        d.ellipse([X(2013) - r, Y(13820) - r, X(2013) + r, Y(13820) + r], fill=AZUL + (255,))
        d.text((X(2013), Y(13820) + 100), '13 820', font=fuente(96), fill=AZUL + (255,), anchor='mm')
    if p18 > 0:
        g = suave(p18 * 1.5)
        d.line([X(2018), Y(13797 + 23 * g), X(2018), Y(13797 - 23 * g)], fill=AMBAR + (255,), width=22)
        r = 34 * min(1, p18 * 2)
        d.ellipse([X(2018) - r, Y(13797) - r, X(2018) + r, Y(13797) + r], fill=AMBAR + (255,))
        d.text((X(2018), Y(13797) + 100), '13 797 ± 23', font=fuente(96), fill=(170, 100, 20, 255), anchor='mm')
    return im


def g_wmap_planck(g1, g2, gc):
    im = fondo_panel(1700, 900, 13).copy()
    d = ImageDraw.Draw(im)
    d.text((850, 86), 'DOS SATÉLITES, LA MISMA RESPUESTA', font=fuente(96), fill=(170, 60, 24, 255), anchor='mm')
    d.text((850, 170), 'edad del universo, en millones de años', font=fuente(58, 500), fill=(60, 54, 60, 255), anchor='mm')
    X = _eje(d, 160, 1540, 770, 13650, 13900, [(13700, '13 700'), (13800, '13 800'), (13900, '13 900')], 64)
    if gc > 0:
        capa = Image.new('RGBA', im.size, (0, 0, 0, 0))
        dc = ImageDraw.Draw(capa)
        dc.rectangle([X(13797 - 23), 270, X(13772 + 59), 720], fill=AMBAR + (int(90 * gc),))
        dc.text((X(13797), 690), 'SE SOLAPAN', font=fuente(62), fill=(150, 90, 20, int(255 * gc)), anchor='mm')
        im.alpha_composite(capa)
    _barra(d, X, 13772, 59, 400, AZUL, g1, 70, 'WMAP · 13 772 ± 59' if g1 > 0.3 else None, 78)
    _barra(d, X, 13797, 23, 590, AMBAR, g2, 70, 'PLANCK · 13 797 ± 23' if g2 > 0.3 else None, 78)
    return im


def g_hubble(npts, pl, corr, fade):
    im = fondo_panel(1700, 1000, 17).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, 'HUBBLE, 1929: 24 GALAXIAS', 'cuanto más lejos, más rápido se alejan')
    ox, oy, ax, ay = 200, 860, 1560, 240
    d.line([ox, oy, ax, oy], fill=TINTA, width=6)
    d.line([ox, oy, ox, ay], fill=TINTA, width=6)
    d.text((ax - 120, oy + 50), 'DISTANCIA', font=fuente(44, 600), fill=TINTA, anchor='mm')
    d.text((ox + 120, ay - 30), 'VELOCIDAD', font=fuente(44, 600), fill=TINTA, anchor='mm')
    rnd = np.random.RandomState(46)
    xs = np.sort(rnd.uniform(0.03, 0.135, 24))
    ys = np.clip(xs * 7 * 0.85 * (1 + rnd.normal(0, 0.12, 24)), 0.02, 0.98)
    for j in range(min(24, int(npts))):
        xf = xs[j] * lerp(1, 7, corr)
        x, y = ox + xf * (ax - ox), oy - ys[j] * (oy - ay)
        col = AZUL + (int(255 * (1 - 0.75 * fade)),)
        d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=col)
    if pl > 0:
        pend = lerp(5.95, 0.85, corr)
        ex_, ey_ = (1 / pend, 1.0) if pend > 1 else (1.0, pend)
        col = AMBAR if fade > 0.5 else (150, 120, 90)
        d.line([ox, oy, ox + ex_ * pl * (ax - ox), oy - ey_ * pl * (oy - ay)], fill=col + (255,), width=10)
    if corr > 0.05:
        d.text((1150, 780), 'DISTANCIAS × 7', font=fuente(60), fill=ROJO + (int(255 * min(1, corr * 2)),), anchor='mm')
    return im


def g_reloj_reves(g1, g2):
    im = fondo_panel(1700, 900, 19).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, 'EL RELOJ AL REVÉS', 'si la expansión hubiera ido siempre a la misma velocidad')
    x0 = 220
    for (g, val, h0, y, col, txt) in ((g1, 13.4, '73,04', 430, AMBAR, '≈ 13 400 M de años'), (g2, 14.5, '67,4', 680, AZUL, '≈ 14 500 M de años')):
        if g <= 0:
            continue
        largo = 1240 * val / 14.5
        d.rounded_rectangle([x0, y - 44, x0 + largo * suave(g), y + 44], radius=10, fill=col + (255,))
        d.text((x0, y - 92), 'CON H0 = ' + h0, font=fuente(68), fill=TINTA, anchor='lm')
        if g > 0.8:
            d.text((x0 + largo, y + 96), txt.replace('≈', '~'), font=fuente(68), fill=TINTA, anchor='rm')
    return im


def g_orden(g, gn, gp=1.0):
    im = fondo_panel(1700, 820, 23).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, 'ORDEN DE MAGNITUD', 'la expansión no fue constante, pero la zona está clara')
    X = _eje(d, 170, 1530, 660, 12000, 15000, [(12000, '12 000'), (13000, '13 000'), (14000, '14 000'), (15000, '15 000')], 60)
    if g > 0:
        _transl(im, [X(13000), 300, X(13000) + (X(14000) - X(13000)) * suave(g), 640], AMBAR + (110,))
        d.text((X(13500), 268), 'ENTRE 13 000 Y 14 000 M', font=fuente(58), fill=(150, 90, 20, 255), anchor='mm')
    for v, col, txt in ((13400, (170, 100, 20), '~13 400'), (14500, AZUL, '~14 500')):
        if gp > 0:
            y = 640 - 30 * suave(gp)
            d.polygon([(X(v), y + 20), (X(v) - 22, y - 20), (X(v) + 22, y - 20)], fill=col + (255,))
            d.text((X(v), y - 60), txt, font=fuente(60), fill=col + (255,), anchor='mm')
    if gn > 0:
        d.line([X(13800), 300, X(13800), 660], fill=ROJO + (255,), width=10)
        d.text((X(13800) + 24, 380), 'NASA ~ 13 800 M', font=fuente(56), fill=ROJO + (255,), anchor='lm')
    return im


def g_universo_estrella(g, gl):
    im = fondo_panel(1700, 760, 29).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, 'NINGUNA ESTRELLA PUEDE SER', 'más vieja que el universo')
    x0, x1 = 160, 1460
    d.rounded_rectangle([x0, 280, x1, 380], radius=12, fill=(226, 214, 190, 255), outline=(90, 80, 70, 255), width=5)
    d.text((x0 + 24, 330), 'EDAD DEL UNIVERSO', font=fuente(64), fill=TINTA, anchor='lm')
    if g > 0:
        d.rounded_rectangle([x0, 460, x0 + (x1 - x0) * 0.97 * suave(g), 560], radius=12, fill=NAR + (255,))
        if g > 0.5:
            d.text((x0 + 24, 510), 'ESTRELLA MÁS VIEJA', font=fuente(64), fill=(255, 250, 240, 255), anchor='lm')
    if gl > 0:
        d.line([x1, 240, x1, 620], fill=ROJO + (255,), width=14)
        d.text((x1, 670), 'LÍMITE', font=fuente(66), fill=ROJO + (255,), anchor='mm')
    return im

def g_cuadricula(g):
    im = fondo_panel(1700, 900, 31).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, '160 ESTRELLAS MUY VIEJAS', 'elegidas entre unas 3 000 candidatas del satélite Gaia')
    rnd = np.random.RandomState(73)
    elegidas = set(rnd.choice(3000, 160, replace=False))
    for idx in range(3000):
        c, f_ = idx % 100, idx // 100
        x, y = 157 + c * 14, 240 + f_ * 17.5
        if idx in elegidas and g > 0:
            r = 9 * min(1, g * 1.5)
            d.ellipse([x - r, y - r, x + r, y + r], fill=AMBAR + (255,), outline=(150, 90, 20, 255), width=2)
        else:
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(150, 140, 128, 255))
    d.ellipse([300 - 10, 830 - 10, 300 + 10, 830 + 10], fill=(150, 140, 128, 255))
    d.text((330, 830), '3 000 CANDIDATAS', font=fuente(60), fill=TINTA, anchor='lm')
    if g > 0:
        d.ellipse([960 - 14, 830 - 14, 960 + 14, 830 + 14], fill=AMBAR + (255,), outline=(150, 90, 20, 255), width=3)
        d.text((995, 830), '160 ELEGIDAS', font=fuente(60), fill=(150, 90, 20, 255), anchor='lm')
    return im

def g_media(g1, g2):
    im = fondo_panel(1700, 820, 37).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, 'LA EDAD DE LAS ESTRELLAS', 'millones de años')
    X = _eje(d, 170, 1530, 680, 12000, 15000, [(12000, '12 000'), (13000, '13 000'), (14000, '14 000'), (15000, '15 000')], 60)
    if g2 > 0:
        _transl(im, [X(12800), 590, X(14800), 640], AZUL + (110,))
        d.text((X(14800), 560), '± 1 000', font=fuente(56), fill=AZUL + (255,), anchor='rm')
    if g1 > 0:
        r = 34 * min(1, g1 * 2)
        d.ellipse([X(13600) - r, 500 - r, X(13600) + r, 500 + r], fill=NAR + (255,))
        d.text((X(13600), 430), 'MEDIA ~13 600', font=fuente(66), fill=TINTA, anchor='mm')
    if g2 > 0:
        xa = X(13800)
        xb = xa + (X(15000) - xa) * suave(g2)
        d.line([xa, 320, xb, 320], fill=AMBAR + (255,), width=22)
        d.polygon([(xb + 36, 320), (xb, 292), (xb, 348)], fill=AMBAR + (255,))
        d.line([xa, 290, xa, 680], fill=AMBAR + (255,), width=6)
        d.text((xa - 20, 260), 'UNIVERSO: COMO MÍNIMO 13 800', font=fuente(60), fill=(150, 90, 20, 255), anchor='mm')
    return im

def g_histograma(n, g14, g138):
    im = fondo_panel(1700, 900, 41).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, '70 ESTRELLAS, NINGUNA MÁS VIEJA QUE EL UNIVERSO', 'edad en millones de años · 90 % de confianza · reparto ilustrativo')
    X = _eje(d, 170, 1530, 760, 12000, 15000, [(12000, '12 000'), (13000, '13 000'), (14000, '14 000'), (15000, '15 000')], 60)
    cuentas = [3, 5, 7, 9, 10, 10, 9, 7, 5, 3, 2]
    orden = [(c, k) for c in range(11) for k in range(cuentas[c])]
    rnd = np.random.RandomState(77)
    rnd.shuffle(orden)
    for (c, k) in orden[:max(0, int(n))]:
        xa = X(13000 + c * 100) + 4
        ya = 744 - (k + 1) * 34
        d.rectangle([xa, ya, xa + (X(13100) - X(13000)) - 8, ya + 28], fill=NAR + (255,))
    if g14 > 0:
        d.line([X(14100), 260, X(14100), 760], fill=ROJO + (int(255 * g14),), width=10)
        d.text((X(14100) + 20, 300), 'NINGUNA > 14 100', font=fuente(60), fill=ROJO + (int(255 * g14),), anchor='lm')
    if g138 > 0:
        d.line([X(13800), 230, X(13800), 760], fill=AMBAR + (int(255 * g138),), width=8)
        d.text((X(13800) - 20, 250), '~13 800', font=fuente(60), fill=(150, 90, 20, int(255 * g138)), anchor='rm')
    return im


def g_precision(g1, g2):
    im = fondo_panel(1700, 760, 43).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, 'MENOS PRECISO… PERO SIN MODELO', 'tamaño del margen de error')
    X = _eje(d, 170, 1530, 650, 12500, 15000, [(13000, '13 000'), (14000, '14 000')], 60)
    _barra(d, X, 13797, 23, 340, AMBAR, g1, 56, 'PLANCK (± 23)' if g1 > 0.3 else None, 66)
    _barra(d, X, 13800, 1000, 530, NAR, g2, 56, 'ESTRELLAS VIEJAS (± 1 000)' if g2 > 0.3 else None, 66)
    return im


def g_tres(g1, g2, g3, gb):
    im = fondo_panel(1700, 960, 47).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, 'TRES RELOJES, LA MISMA ZONA', 'edad del universo en millones de años')
    X = _eje(d, 460, 1560, 830, 12500, 15000, [(13000, '13 000'), (14000, '14 000'), (15000, '15 000')], 60)
    if gb > 0:
        _transl(im, [X(13800) - 14, 280, X(13800) + 14, 800], AMBAR + (int(150 * gb),))
        d.text((X(13800), 245), '~13 800', font=fuente(64), fill=(150, 90, 20, 255), anchor='mm')
    filas = ((g1, 13797, 23, AMBAR, 'LUZ ANTIGUA', 380), (g2, 13950, 550, AZUL, 'EXPANSIÓN', 540), (g3, 13800, 1000, NAR, 'ESTRELLAS', 700))
    for g, c, m, col, txt, y in filas:
        d.text((70, y), txt, font=fuente(62), fill=TINTA + (255,) if g > 0 else (150, 140, 128, 255), anchor='lm')
        if g > 0:
            _barra(d, X, c, m, y, col, g, 52)
    return im


def g_tension(g1, g2, g8, g5):
    im = fondo_panel(1700, 960, 53).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, 'DOS MEDIDAS QUE NO SE TOCAN', 'velocidad de expansión hoy (km/s por megaparsec)')
    X = _eje(d, 170, 1530, 820, 64, 76, [(65, '65'), (67, '67'), (69, '69'), (71, '71'), (73, '73'), (75, '75')], 60)
    _barra(d, X, 67.4, 0.5, 520, AMBAR, g1, 56, 'PLANCK · 67,4' if g1 > 0.3 else None, 66)
    _barra(d, X, 73.04, 1.04, 520, AZUL, g2, 56, 'CEFEIDAS · 73,04' if g2 > 0.3 else None, 66)
    if g8 > 0:
        _transl(im, [X(67.9), 500, X(67.9) + (X(72.0) - X(67.9)) * suave(g8), 540], ROJO + (150,))
        d.text((X(70), 320), '8 %', font=fuente(110), fill=ROJO + (int(255 * min(1, g8 * 2)),), anchor='mm')
    if g5 > 0:
        paso = (X(1.15) - X(0))
        for j in range(5):
            if g5 * 5 > j:
                xa = X(67.9) + j * paso
                d.rectangle([xa + 3, 620, xa + paso - 3, 652], fill=AMBAR + (255,))
        d.text((X(70), 716), '~5 VECES EL MARGEN DE ERROR', font=fuente(62), fill=TINTA, anchor='mm')
    return im


def g_act(g1, g2):
    im = fondo_panel(1700, 800, 59).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, 'ACT (CHILE) CONFIRMA A PLANCK', 'otra técnica, el mismo resultado')
    X = _eje(d, 170, 1530, 690, 64, 76, [(65, '65'), (67, '67'), (69, '69'), (71, '71'), (73, '73'), (75, '75')], 60)
    _barra(d, X, 67.4, 0.5, 370, AMBAR, g1, 56, 'PLANCK · 67,4' if g1 > 0.3 else None, 66)
    if g2 > 0:
        d.text((X(67.4), 470), 'ACT · 2025: CONCUERDA', font=fuente(66), fill=(70, 110, 80, int(255 * min(1, g2 * 2))), anchor='mm')
        _transl(im, [X(67.4) - 70, 510, X(67.4) + 70, 560], (110, 150, 120, int(230 * g2)))
    d.text((X(73.04), 470), 'CEFEIDAS · 73', font=fuente(56), fill=(120, 130, 150, 255), anchor='mm')
    return im


def g_freedman(g1, g2, g3):
    im = fondo_panel(1700, 900, 61).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, 'Y UN TERCER EQUIPO, EN MEDIO', 'velocidad de expansión hoy (km/s por megaparsec)')
    X = _eje(d, 170, 1530, 790, 64, 76, [(65, '65'), (67, '67'), (69, '69'), (71, '71'), (73, '73'), (75, '75')], 60)
    _barra(d, X, 67.4, 0.5, 620, AMBAR, g1, 56, 'PLANCK · 67,4' if g1 > 0.3 else None, 62)
    _barra(d, X, 73.04, 1.04, 620, AZUL, g2, 56, 'CEFEIDAS · 73,04' if g2 > 0.3 else None, 62)
    _barra(d, X, 70.39, 1.94, 400, VERDE, g3, 56, 'FREEDMAN · 70,39' if g3 > 0.3 else None, 66)
    return im


def g_importa(g1, g2, gd):
    im = fondo_panel(1700, 820, 67).copy()
    d = ImageDraw.Draw(im)
    _titulo(d, 1700, 'SI LA EXPANSIÓN LOCAL VALIERA PARA TODO', 'edad del universo, en millones de años')
    X = _eje(d, 170, 1530, 690, 12400, 14200, [(12500, '12 500'), (13000, '13 000'), (13500, '13 500'), (14000, '14 000')], 60)
    if g1 > 0:
        r = 30 * min(1, g1 * 2)
        d.ellipse([X(13800) - r, 330 - r, X(13800) + r, 330 + r], fill=AMBAR + (255,))
        d.text((X(13800), 268), 'PLANCK · 13 800', font=fuente(62), fill=(150, 90, 20, 255), anchor='mm')
    if g2 > 0:
        d.rounded_rectangle([X(12700), 470, X(12700) + (X(12900) - X(12700)) * suave(g2), 520], radius=10, fill=AZUL + (255,))
        d.text((X(12700), 420), '12 700 – 12 900 · EXPANSIÓN LOCAL', font=fuente(62), fill=AZUL + (255,), anchor='lm')
    if gd > 0:
        xa, xb = X(12800), X(12800) + (X(13800) - X(12800)) * suave(gd)
        d.line([xa, 590, xb, 590], fill=ROJO + (255,), width=10)
        d.line([xa, 568, xa, 612], fill=ROJO + (255,), width=8)
        if gd > 0.95:
            d.line([xb, 568, xb, 612], fill=ROJO + (255,), width=8)
            d.text(((xa + xb) / 2, 636), 'CASI 1 000 M DE AÑOS', font=fuente(56), fill=ROJO + (255,), anchor='mm')
    return im


def tarjeta_nivel(palabra, col, icono, alfa=1.0):
    im = fondo_panel(700, 900, sum(map(ord, palabra)) % 50, (244, 238, 222)).copy()
    d = ImageDraw.Draw(im)
    d.rectangle([6, 6, 694, 150], fill=col + (255,))
    if icono == 'check':
        d.line([(200, 470), (310, 590), (520, 330)], fill=col + (255,), width=64, joint='curve')
    elif icono == 'aprox':
        for yb in (400, 540):
            pts = [(170 + i * 9, yb + 34 * math.sin(i / 40 * 2 * math.pi)) for i in range(41)]
            d.line(pts, fill=col + (255,), width=44, joint='curve')
    else:
        d.text((350, 470), icono, font=fuente(300), fill=col + (255,), anchor='mm')
    d.text((350, 780), palabra.upper(), font=fuente(84), fill=TINTA, anchor='mm')
    return im


@functools.lru_cache(maxsize=8)
def tablero_epoca(titulo, que):
    im = fondo_panel(1100, 900, 71 if que == 'hoy' else 73, (34, 44, 92)).copy()
    d = ImageDraw.Draw(im)
    d.text((550, 100), titulo, font=fuente(84), fill=(244, 236, 214, 255), anchor='mm')
    if que == 'hoy':
        g = sprite('galaxia')
        rnd = np.random.RandomState(4)
        for j in range(5):
            gg = g.resize((180, 180), Image.LANCZOS).rotate(rnd.uniform(0, 360), resample=Image.BICUBIC)
            im.alpha_composite(gg, (int(rnd.uniform(80, 800)), int(rnd.uniform(220, 620))))
    else:
        m = sprite('mapa_cmb')
        m = m.resize((820, int(m.height * 820 / m.width)), Image.LANCZOS)
        im.alpha_composite(m, (140, 300))
    return im


@functools.lru_cache(maxsize=8)
@functools.lru_cache(maxsize=128)
def escalon_icono(numero, alto_px, icono, nombre, aparece, tam=1.0):
    """Peldaño con el número arriba, el objeto en el centro y su nombre abajo. aparece y tam vienen cuantizados."""
    im = escalon_base(numero, alto_px).copy()
    if aparece > 0:
        spr = sprite(icono)
        lado = int(min(230, alto_px - 150) * tam)
        g = spr.resize((lado, int(lado * spr.height / spr.width)), Image.LANCZOS)
        if aparece < 1:
            g.putalpha(Image.fromarray((np.asarray(g.getchannel('A'), f32) * aparece).astype(np.uint8)))
        im.alpha_composite(g, (210 - g.width // 2, int(alto_px * 0.52 - g.height / 2)))
        d = ImageDraw.Draw(im)
        d.text((210, alto_px - 46), nombre, font=fuente(50), fill=(90, 66, 44, 255), anchor='mm')
    return im


def escalon_base(numero, alto_px):
    col = DD.carton(420, alto_px, numero, (196, 176, 140))
    im = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).convert('RGBA')
    d = ImageDraw.Draw(im)
    d.rectangle([4, 4, 415, alto_px - 5], outline=(110, 86, 60, 255), width=6)
    d.text((56, 58), str(numero), font=fuente(90), fill=(110, 86, 60, 255), anchor='mm')
    return im


def peldano(numero, alto_px, icono, nombre, t_on, pulso=False):
    def img(t):
        ap = round(suave((t - t_on) / 0.5) * 8) / 8
        tam = round((1 + 0.1 * math.sin(2 * math.pi * t / 1.3)) * 12) / 12 if pulso else 1.0
        return escalon_icono(numero, alto_px, icono, nombre, ap, tam)
    return img


def escalon(numero, alto_px):
    col = DD.carton(420, alto_px, numero, (196, 176, 140))
    im = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).convert('RGBA')
    d = ImageDraw.Draw(im)
    d.rectangle([4, 4, 415, alto_px - 5], outline=(110, 86, 60, 255), width=6)
    d.text((210, alto_px / 2), str(numero), font=fuente(160), fill=(110, 86, 60, 255), anchor='mm')
    return im


@functools.lru_cache(maxsize=16)
def estrella_color(nombre, col):
    base = sprite('sol')
    arr = np.asarray(base, f32).copy()
    lum = arr[..., :3].mean(-1, keepdims=True) / 255
    arr[..., :3] = np.clip(lum * np.asarray(col, f32) * 1.3, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), 'RGBA')

# ================================================================== mesa larga


TRAMO = 7800.0


def fabricar_tramos(rehacer=False):
    os.makedirs(CACHE, exist_ok=True)
    listo = os.path.join(CACHE, 'mesa_1.jpg')
    if os.path.exists(listo) and not rehacer:
        return
    x0, x1, z0, z1 = D.MESA
    w_, h_ = int(TRAMO * D.PX_MESA), int((z1 - z0) * D.PX_MESA)
    for k in (0, 1):
        base = DD.carton(w_, h_, 40 + k, (226, 214, 188))
        im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert('RGBA')
        rnd = np.random.RandomState(50 + k)
        d = ImageDraw.Draw(im)
        tinta = (52, 60, 98)
        for cx_, cy_ in ((w_ * 0.25, h_ * 0.5), (w_ * 0.7, h_ * 0.45)):
            for r in range(120, 1100, 105):
                d.ellipse([cx_ - r, cy_ - r, cx_ + r, cy_ + r], outline=tinta, width=2)
        for _ in range(2200):
            x, y = rnd.uniform(0, w_), rnd.uniform(0, h_)
            r = rnd.choice([1.5, 2.5, 3.5, 5])
            d.ellipse([x - r, y - r, x + r, y + r], fill=tinta)
        mesa = D.collage(im, 55, 60 + k, (0.5, 0.85))
        arr = np.asarray(mesa.convert('RGB'), f32) * np.linspace(0.78, 1.0, h_, dtype=f32)[:, None, None]
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(os.path.join(CACHE, 'mesa_%d.jpg' % k), quality=90)
        pared = D.collage(DD.textura_pared().resize((2800, 1050), Image.LANCZOS).convert('RGBA'), 55, 70 + k, (0.75, 1.15))
        arr_p = np.asarray(pared.convert('RGB'), f32)
        l_ = arr_p.mean(-1, keepdims=True)
        arr_p = (arr_p * 0.8 + l_ * 0.2) * 0.78
        Image.fromarray(np.clip(arr_p, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)).save(os.path.join(CACHE, 'pared_%d.jpg' % k), quality=90)
    print('  tramos de mesa listos', flush=True)


TR = {}


def cargar():
    D.cargar()
    if TR:
        return
    for k in (0, 1):
        TR['mesa%d' % k] = Image.open(os.path.join(CACHE, 'mesa_%d.jpg' % k)).convert('RGB')
        TR['pared%d' % k] = Image.open(os.path.join(CACHE, 'pared_%d.jpg' % k)).convert('RGB')


def tramos_visibles():
    cx = D.CAM[0]
    out = []
    if cx < 6400 + 4500:
        out.append((-1400.0, 6400.0, D.FIJ['mesa'], D.FIJ['pared'], -2600.0, 7400.0))
    k = 1
    while True:
        x0 = 6400 + (k - 1) * TRAMO
        if x0 > cx + 6000:
            break
        if x0 + TRAMO > cx - 6000:
            v = (k - 1) % 2
            out.append((x0, x0 + TRAMO, TR['mesa%d' % v], TR['pared%d' % v], x0, x0 + TRAMO))
        k += 1
    return out


def escenario_largo(t):
    lz = Image.new('RGB', (W, H), (26, 28, 34))
    _, z0, z1 = None, D.MESA[2], D.MESA[3]
    for (x0, x1, mesa, pared, px0, px1) in tramos_visibles():
        xw0, yw0, s = D.proy(px0, D.Z_PARED, 2600)
        xw1, yw1, _ = D.proy(px1, D.Z_PARED, 0)
        if xw1 > 0 and xw0 < W:
            lz.paste(pared.resize((max(1, int(xw1 - xw0) + 2), max(1, int(yw1 - yw0))), Image.BILINEAR), (int(xw0), int(yw0)))
        esq = [D.proy(x0, z1)[:2], D.proy(x1, z1)[:2], D.proy(x1, z0)[:2], D.proy(x0, z0)[:2]]
        mw, mh = mesa.size
        co = D.coefs([(0, 0), (mw, 0), (mw, mh), (0, mh)], esq)
        proyec = mesa.transform((W, H), Image.PERSPECTIVE, co, Image.BILINEAR)
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).polygon(esq, fill=255)
        lz.paste(proyec, (0, 0), m)
    arr = np.asarray(lz, f32)
    yb = D.proy(D.CAM[0], z1)[1]
    banda = np.exp(-np.clip(D.FIJ['yy'][:, :1] - yb, 0, None) / 40) * (D.FIJ['yy'][:, :1] >= yb)
    arr = arr * (1 - 0.45 * banda[..., None])
    arriba = np.clip((yb - D.FIJ['yy'][:, :1]) / 300, 0, 1)
    arr = arr * (1 - 0.25 * arriba[..., None])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')

# ================================================================== estaciones (una por escena)


def V(v, t):
    return v(t) if callable(v) else v


def pie(img, dx, Z, alto, on, off=None, **kw):
    return dict(tipo='pie', img=img, dx=dx, Z=Z, alto=alto, on=on, off=off, **kw)


def tumb(img, dx, Z, ancho, fondo, on, off=None, **kw):
    return dict(tipo='tumb', img=img, dx=dx, Z=Z, ancho=ancho, fondo=fondo, on=on, off=off, **kw)


def fn(dibujar, on, off=None, Z=700, **kw):
    return dict(tipo='fn', dibujar=dibujar, on=on, off=off, Z=Z, **kw)


def dato(texto, on, off=None):
    return tumb(lambda t, tx=texto: etiqueta('DATO VERIFICADO · ' + tx, 44, papel=(244, 232, 200), tinta=(170, 80, 20)),
                0, 470, 760, 120, on, off, sfx='sello')


def reloj_vivo(i, vel=1.0, ang=None):
    return lambda t: D.reloj_img(i, ang(t) if ang else ([0.4, 2.1, 4.0][i] + t * [0.35, 0.28, 0.42][i] * vel))


def separando(i, g0, t0, dur=4.0):
    """Desplazamiento de una galaxia que se aleja del centro (para la expansión)."""
    dirs = [(-1, -0.2), (1, 0.15), (-0.45, 0.3), (0.5, -0.3)]
    return lambda t: dirs[i][0] * (g0 + 220 * suave((t - t0) / dur))


def _cinta_con_tramo(desde_frac, color=(240, 170, 60)):
    """Cinta del tiempo (13 797 M) con un tramo final marcado en ámbar."""
    reg = sprite('regla')
    im = reg.copy()
    d = ImageDraw.Draw(im)
    x0 = int(im.width * (0.04 + 0.92 * desde_frac))
    d.rectangle([x0, int(im.height * 0.3), int(im.width * 0.96), int(im.height * 0.7)], fill=color + (235,))
    return im


@functools.lru_cache(maxsize=256)
def pan_galaxias(alto):
    """Pan con galaxias incrustadas: la imagen escala con la masa, las galaxias se dibujan más pequeñas en proporción
    para que conserven su tamaño en pantalla; así solo crece la distancia entre ellas."""
    im = sprite('pan').copy()
    gal = sprite('galaxia')
    lado = int(round(230 * 190 / alto))
    g = gal.resize((lado, lado), Image.LANCZOS)
    for fx, fy in ((0.24, 0.42), (0.47, 0.33), (0.72, 0.43), (0.36, 0.66), (0.62, 0.68)):
        im.alpha_composite(g, (int(im.width * fx - lado / 2), int(im.height * fy - lado / 2)))
    return im


ST = []


def estacion(nombre, X, t_in, items, dz=-330, h=560, focos=()):
    ST.append(dict(nombre=nombre, X=X, t_in=t_in, items=items, dz=dz, h=h, focos=list(focos)))


def definir():
    ST.clear()
    X = 6800.0
    paso = 3300.0
    interr = lambda t: D.PZ['interr']   # noqa: E731

    # E04b · al modelo le falta algo · casi mil millones de años
    estacion('puzle', X, 42.3, [
        pie(lambda t: sprite('puzle'), -280, 820, 420, a(9) + 1.6),
        pie(lambda t: sprite('pieza_suelta'), 330, 680, 150, w(9, 'le falte') - 0.2),
        tumb(lambda t: sprite('regla'), 0, 560, 1100, 110, a(10) - 0.2),
        tumb(lambda t: _cinta_con_tramo(1 - 1000 / 13797), 0, 561, 1100, 110, w(10, 'casi mil') - 0.3),
        pie(lambda t: cartel('CASI 1 000 M', 150), 380, 640, 120, w(10, 'casi mil')),
    ], focos=[(w(10, 'casi mil'), 0.0, 80)])
    X += paso
    # E05 · el primer reloj
    estacion('reloj1', X, a(11) - 0.1, [
        pie(reloj_vivo(0), 0, 790, 440, a(11) - 0.2),
        pie(lambda t: etiqueta('RELOJ 1', 80), 0, 600, 90, a(11) + 0.3),
    ])
    X += paso
    # E06 · el malentendido · estado denso y caliente
    off_b = a(15) - 0.4
    estacion('malentendido', X, a(13) - 0.1, [
        pie(burbuja_pensamiento, -200, 840, 400, a(13) + 0.2, off_b),
        fn(lambda lz, t, X0: None, w(14, 'algo explot') - 0.1, sfx='levanta'),
        fn(lambda lz, t, X0: None, w(14, 'en alg') + 0.9, sfx='rotulador'),
        tumb(lambda t: sprite('regla'), 100, 600, 1000, 110, a(15) - 0.1),
        pie(lambda t: sprite('denso'), -420, 640, 170, w(15, 'estado muy') - 0.1),
        pie(lambda t: sprite('bandera'), -420, 580, 90, w(15, 'punto de partida')),
        pie(lambda t: sprite('tierra'), 630, 600, 55, w(15, 'punto de partida') + 0.4),
        pie(lambda t: etiqueta('ESTADO MUY DENSO Y CALIENTE', 54), -150, 520, 60, w(15, 'estado muy') + 0.3),
    ])
    X += paso
    # E07 · ΛCDM
    tiembla = lambda t: 10 * math.sin(t * 18) * suave((t - a(17)) / 0.4) * (1 - suave((t - a(17) - 3) / 0.6))   # noqa: E731
    estacion('lcdm', X, a(16) - 0.2, [
        pie(lambda t: cartel('13 797', 200), -520, 700, 110, w(16, 'todas las cifras') - 0.1),
        pie(lambda t: cartel('ΛCDM', 300), tiembla, 820, 300, w(16, 'modelo est') - 0.2),
        pie(lambda t: etiqueta('MODELO ESTÁNDAR DE LA COSMOLOGÍA', 56), 0, 620, 70, w(16, 'modelo est') + 0.4),
        tumb(lambda t: sprite('regla'), 0, 540, 1100, 110, a(17) - 0.1),
        pie(interr, 520, 600, 140, w(17, 'la cifra')),
    ], focos=[(a(18), 0.0, 120)])
    X += paso
    # E08–E09 · la luz más antigua · la niebla · se despeja
    estacion('niebla', X, a(19) - 0.2, [
        pie(reloj_vivo(0), -560, 830, 300, a(19) - 0.1),
        pie(lambda t: D.PZ['luz'], -150, 760, lambda t: 150 + 25 * math.sin(t * 2.2), w(19, 'una luz') - 0.1, a(21) - 0.2, grosor=0),
        fn(dibujar_niebla, a(21) - 0.3, Z=760),
        pie(lambda t: etiqueta('380 000 AÑOS', 70), -60, 560, 80, w(22, '380') - 0.2, a(24) - 0.3),
        pie(lambda t: sprite('termometro'), 620, 760, 340, a(23) - 0.1, a(26) + 0.5),
        fn(lambda lz, t, X0: termometro_liquido(lz, t, X0 + 620, 760, 340, a(23) + 0.4, 3.5, 1.0, 0.42, (206, 60, 44)), a(23) - 0.1, a(26) + 0.5, Z=759),
        pie(lambda t: etiqueta('2 700 °C', 70, papel=(250, 214, 140)), 620, 600, 80, w(23, '2 700') - 0.2),
        fn(dibujar_rayo_libre, a(25) - 0.1, Z=600),
    ])
    X += paso
    # E10–E11 · fondo cósmico · 2,7 K · Planck
    estacion('cmb', X, a(26) - 0.2, [
        pie(lambda t: sprite('tierra'), 0, 760, 150, a(26) - 0.1, a(27) - 0.4),
        fn(dibujar_rayos_tierra, a(26), a(27) - 0.4, Z=761),
        pie(lambda t: sprite('mapa_cmb'), -150, 830, 330, a(27) - 0.1),
        pie(lambda t: etiqueta('ILUSTRACIÓN PROPIA', 44), -150, 620, 50, a(27) + 0.5),
        pie(lambda t: sprite('termometro'), 560, 740, 300, a(28) - 0.1),
        fn(lambda lz, t, X0: termometro_liquido(lz, t, X0 + 560, 740, 300, a(28) + 0.3, 3.0, 0.42, 0.05, (90, 130, 210)), a(28) - 0.1, Z=739),
        pie(lambda t: etiqueta('2,7 K  (-270 °C)', 64, papel=(200, 220, 246)), 560, 580, 72, w(28, '2,7') - 0.2),
    ])
    X += paso
    estacion('planck', X, a(29) - 0.2, [
        pie(lambda t: sprite('satelite'), -540, 820, 300, a(29) - 0.1),
        pie(lambda t: etiqueta('4,5 AÑOS', 70), -540, 610, 80, w(29, 'cuatro')),
        pie(lambda t: sprite('mapa_cmb'), 60, 840, 320, a(30) - 0.2),
    ] + [pie(lambda t: sprite('galaxia'), 60 + gx, 690, 105, w(30, 'semillas') + j * 0.15)
         for j, gx in enumerate((-280, -140, 0, 140, 280))] + [
        pie(reloj_vivo(0), 560, 780, 260, a(31) + 0.6),
        dato('PLANCK · ESA · 2009–2013', a(29) + 0.5),
    ])
    X += paso
    # E12 · 2013 → 2018
    estacion('graf1', X, a(32) - 0.2, [
        pie(lambda t: g_2013_2018(suave((t - w(32, '13 820') + 0.2) / 0.5), suave((t - w(33, '13 797') + 0.2) / 0.6), suave((t - a(34) + 0.1) / 0.8)),
            0, 840, 480, a(32) - 0.1, grosor=8),
        dato('PLANCK 2013 Y 2018 (ESA)', w(32, '13 820')),
    ])
    X += paso
    # E13–E14 · WMAP · compatibles
    estacion('wmap', X, a(35) - 0.2, [
        pie(interr, -560, 700, 200, a(35) - 0.1, a(36) + 2.5),
        pie(lambda t: sprite('foto_wmap'), 0, 860, 400, a(36) - 0.1, a(37) - 0.4, grosor=6),
        tumb(lambda t: etiqueta('NASA / WMAP SCIENCE TEAM', 40), 0, 500, 560, 90, a(36) + 0.4, a(37) - 0.4),
        pie(lambda t: cartel('13 772', 200), -640, 760, 115, w(36, '13 772') - 0.2, a(37) - 0.4),
        pie(lambda t: etiqueta('± 59 M', 80, papel=(250, 214, 140)), -640, 560, 75, w(36, 'margen') - 0.1, a(37) - 0.4),
        pie(lambda t: etiqueta('OTRO SATÉLITE · OTRO EQUIPO', 54), 0, 600, 60, w(36, 'otro instrumento'), w(36, '13 772') - 0.3),
        pie(lambda t: g_wmap_planck(suave((t - a(37) - 0.2) / 0.8), suave((t - w(38, '13 797') + 0.2) / 0.8), suave((t - 214.0) / 0.6)),
            0, 840, 460, a(37) - 0.1, grosor=8),
        pie(lambda t: sprite('check'), 640, 640, 150, 215.4),
    ])
    X += paso
    # E14b · depende del modelo · el segundo reloj
    estacion('depende', X, a(41) - 0.2, [
        pie(reloj_vivo(0), -300, 800, 380, a(41) - 0.1),
        pie(lambda t: cartel('ΛCDM', 200), -300, 600, 110, w(42, 'depende') - 0.1),
        pie(reloj_vivo(1), 380, 820, 340, w(44, 'segundo')),
        pie(lambda t: sprite('aviso'), 600, 620, 140, w(44, 'problemas') - 0.1),
    ], focos=[(w(42, 'depende'), -300, 100)])
    X += paso
    # E15–E16 · Hubble × 7
    estacion('hubble', X, a(45) - 0.2, [
    ] + [pie(lambda t: sprite('galaxia'), (lambda t, x0=x0: x0 * lerp(1, 2.5, suave((t - a(45) - 0.6) / 2.4))), 840, 190,
             a(45) - 0.1 + j * 0.15, a(46) - 0.3) for j, x0 in enumerate((-290, -110, 110, 290))] + [
        pie(lambda t: cartel('× 7', 200), 0, 540, 200, w(45, 'factor') - 0.2, a(46) - 0.3),
        pie(lambda t: g_hubble((t - a(46) - 1.2) / 0.25, suave((t - a(46) - 4.0) / 0.8), suave((t - w(48, 'siete veces') - 0.2) / 2.5), suave((t - a(49)) / 1.0)),
            0, 850, 500, a(46) - 0.1, grosor=8),
        pie(lambda t: sprite('check'), 640, 640, 140, a(49) + 0.4),
    ])
    X += paso
    # E17 · el pan que crece · rebobinar · H0
    crece = lambda t: lerp(lerp(190, 300, suave((t - a(51)) / 3.5)), 170, suave((t - w(52, 'rebobinar') - 0.2) / 2.5))   # noqa: E731
    estacion('pan', X, a(51) - 0.2, [
        pie(lambda t: pan_galaxias(int(round(crece(t)))), -150, 800, crece, a(51) - 0.1),
        pie(lambda t: sprite('rebobinar'), -150, 600, 90, w(52, 'rebobinar') - 0.1),
        pie(lambda t: cartel_h0(), 520, 760, 220, w(53, 'constante') - 0.2),
    ])
    X += paso
    # E18 · escalera de distancias
    estacion('escalera', X, a(54) - 0.2, [
        pie(interr, 0, 700, 180, a(54) - 0.1, a(55) - 0.2),
        pie(peldano(1, 380, 'cefeida', 'CEFEIDAS', a(56) + 0.4, pulso=True), -480, 820, 200, a(55)),
        pie(peldano(2, 500, 'supernova', 'SUPERNOVAS', a(57) - 0.2), 0, 820, 265, a(55) + 0.25),
        pie(peldano(3, 620, 'galaxia', 'GALAXIAS LEJANAS', a(57) + 2.0), 480, 820, 330, a(55) + 0.5),
        fn(lambda lz, t, X0: flechas_escalera(lz, t, X0), a(58) - 0.2, Z=630),
    ])
    X += paso
    # E19–E20 · SH0ES · 73,04
    estacion('shoes', X, a(59) - 0.2, [
        pie(lambda t: sprite('foto_hubble'), -280, 900, 330, a(59) - 0.1, grosor=6),
        tumb(lambda t: etiqueta('NASA, ESA, ADAM G. RIESS (STSCI, JHU)', 38), -280, 760, 600, 80, a(59) + 0.4),
        pie(lambda t: etiqueta('42 SUPERNOVAS', 64), -280, 570, 70, w(59, '42') - 0.1),
        pie(lambda t: cartel('73,04', 250), 560, 840, 170, w(59, '73,04') - 0.2),
        pie(lambda t: etiqueta('KM/S POR MEGAPARSEC', 54), 560, 730, 55, w(59, 'kil') - 0.1),
        pie(lambda t: etiqueta('± 1,04', 80, papel=(250, 214, 140)), 560, 630, 80, w(59, '1,04') - 0.1),
        dato('RIESS ET AL. 2022 · APJ LETTERS', w(59, '73,04')),
    ], focos=[(w(59, '73,04'), 200, 60)])
    X += paso
    # E21 · el reloj al revés · orden de magnitud · guárdalas
    estacion('reves', X, a(60) - 0.2, [
        pie(reloj_vivo(1, ang=lambda t: -(t - a(60)) * 5), -620, 800, 300, a(60) - 0.1, a(63) - 0.3),
        pie(lambda t: sprite('rebobinar'), -620, 610, 80, a(60) + 0.2, a(63) - 0.3),
        pie(lambda t: g_reloj_reves(suave((t - a(61) - 0.6) / 3.0), suave((t - w(62, '67,4') + 0.2) / 3.0)), 150, 840, 430, a(61) + 0.2, a(63) - 0.3, grosor=8),
        pie(lambda t: g_orden(suave((t - w(64, '13 000') + 0.3) / 1.0), suave((t - a(65) + 0.1) / 0.6), suave((t - a(63) - 0.2) / 0.8)), 0, 840, 430, a(63) - 0.1, a(66) - 0.3, grosor=8),
        pie(lambda t: cartel('73', 250), -260, 780, 220, w(66, '73') - 0.2, a(68) + 0.7),
        pie(lambda t: cartel('67', 250), 260, 780, 220, w(66, '67') - 0.2, a(68) + 0.7),
        pie(lambda t: sprite('sobre'), 0, 620, 170, a(68) - 0.4),
    ])
    X += paso
    # E22–E25b · las estrellas más viejas
    estacion('estrellas', X, a(69) - 0.2, [
        pie(reloj_vivo(0), -450, 800, 280, a(69) - 0.4, w(69, 'olvida la luz') + 0.1),
        pie(reloj_vivo(1), 0, 800, 280, a(69) - 0.4, w(69, 'olvida la exp') + 0.1),
        pie(reloj_vivo(2), 600, 660, 220, w(69, 'olvida la exp') + 0.5),
        pie(lambda t: g_universo_estrella(suave((t - a(70) - 0.4) / 4.0), suave((t - w(70, 'no puede') + 0.2) / 0.5)), -120, 860, 400, a(70) - 0.1, a(71) - 0.3, grosor=8),
        pie(interr, -120, 620, 150, a(71) - 0.1, a(72) - 0.2),
        pie(lambda t: estrella_color('azul', (150, 190, 255)), -420, 760, lambda t: 200 * (1 - 0.6 * suave((t - a(72) - 4) / 3)), a(72) - 0.2, a(73) - 0.3),
        pie(lambda t: estrella_color('amarilla', (255, 230, 150)), -100, 760, 150, a(72), a(73) - 0.3),
        pie(lambda t: estrella_color('roja', (240, 120, 80)), 200, 760, lambda t: 110 * (1 + 0.5 * suave((t - a(72) - 2) / 4)), a(72) + 0.2, a(73) - 0.3),
        pie(lambda t: sprite('documento'), -560, 780, 250, a(73) - 0.1, w(73, 'Gaia') - 0.4),
        tumb(lambda t: etiqueta('ASTRONOMY & ASTROPHYSICS · MARZO 2026', 44), -300, 560, 640, 90, a(73) + 0.4, a(74) - 0.3),
        pie(lambda t: g_cuadricula(suave((t - w(73, 'elegidas')) / 1.4)), 30, 850, 400, a(73) + 1.6, a(74) - 0.3, grosor=8),
        pie(lambda t: sprite('foto_gaia'), -560, 780, 220, w(73, 'Gaia') - 0.1, a(74) - 0.3, grosor=5),
        pie(lambda t: g_media(suave((t - a(74) - 0.3) / 0.6), suave((t - w(75, 'como mínimo') + 0.2) / 1.0)), -120, 860, 400, a(74) - 0.1, a(76) - 0.3, grosor=8),
        pie(lambda t: g_histograma((t - a(77) - 0.3) / 0.06, suave((t - w(77, '14 100') + 0.2) / 0.5), suave((t - a(79) + 0.1) / 0.5)), -120, 860, 440, a(76) - 0.1, grosor=8),
        dato('TOMASETTI ET AL. 2026 · A&A 707, A111', w(73, 'marzo')),
    ])
    X += paso
    # E26 · menos preciso pero sin modelo · tres relojes, tres caminos
    estacion('sin_modelo', X, a(80) - 0.2, [
        pie(lambda t: g_precision(suave((t - a(80) - 0.2) / 0.6), suave((t - a(80) - 0.8) / 0.8)), 0, 860, 400, a(80) - 0.1, a(81) - 0.3, grosor=8),
        pie(reloj_vivo(2), 0, 790, 380, a(81) - 0.1),
        pie(lambda t: cartel('ΛCDM', 200), 470, 700, 130, a(81) + 0.2, a(84) - 0.3),
        pie(lambda t: sprite('aspa'), 470, 680, 170, w(81, 'no usa') + 0.3, a(84) - 0.3, sfx='rotulador'),
        pie(reloj_vivo(0), -500, 790, 300, a(84) - 0.1),
        pie(reloj_vivo(1), 500, 790, 300, a(84) + 0.1),
        fn(lambda lz, t, X0: caminos(lz, t, X0), a(85) - 0.2, Z=640),
    ])
    X += paso
    # E27 · juntos: la misma zona
    estacion('juntos', X, a(86) - 0.2, [
        pie(lambda t: g_tres(suave((t - a(87)) / 0.8), suave((t - a(88)) / 0.8), suave((t - a(89)) / 0.8), suave((t - a(90) - 1.5) / 0.8)), 0, 850, 480, a(86) - 0.1, grosor=8),
    ], focos=[(a(90) + 1.5, 0.0, 90)])
    X += paso
    # E28–E30 · pero hay un problema · tensión de Hubble
    estacion('tension', X, a(91) - 0.2, [
        pie(lambda t: sprite('aviso'), 0, 700, 220, a(91) - 0.1, a(92) + 0.4),
        pie(lambda t: sprite('sobre'), 0, 620, 170, a(92) - 0.1, a(93) - 0.3),
        pie(lambda t: cartel('73', 250), -300, 760, 220, a(92) + 0.6, a(93) - 0.3),
        pie(lambda t: cartel('67', 250), 300, 760, 220, a(92) + 0.8, a(93) - 0.3),
        pie(lambda t: g_tension(suave((t - a(93) - 0.4) / 0.8), suave((t - a(94)) / 0.8), suave((t - w(95, '8 %') + 0.3) / 0.8), suave((t - w(95, 'cinco') + 0.8) / 1.2)),
            0, 850, 480, a(93) - 0.1, grosor=8),
        pie(lambda t: etiqueta('TENSIÓN DE HUBBLE', 80, papel=(250, 214, 140)), 0, 560, 85, a(96) - 0.1),
    ], focos=[(w(95, '8 %'), 0.0, 90)])
    X += paso
    # E30b · el puente entre épocas
    estacion('puente', X, a(97) - 0.2, [
        pie(lambda t: tablero_epoca('HOY · SE MIDE', 'hoy'), -500, 830, 380, a(97) + 0.2, grosor=8),
        pie(lambda t: tablero_epoca('INICIO · SE PREDICE', 'inicio'), 500, 830, 380, a(97) + 0.5, grosor=8),
        pie(lambda t: cartel('73,04', 200), -500, 540, 95, w(99, 'hoy') - 0.2),
        pie(lambda t: cartel('67,4', 200), 500, 540, 95, w(100, 'predicci') - 0.2),
    ] + [pie(lambda t: escalon(0, 180), -230 + j * 92, 760, 70, a(101) - 0.2 + j * 0.12) for j in range(6) if j != 3] + [
        pie(interr, 46, 700, 170, a(101) + 1.4),
    ])
    X += paso
    # E31–E32 · ¿error de medición? Webb · ACT
    estacion('webb', X, a(102) - 0.2, [
        tumb(lambda t: sprite('regla'), -300, 560, 700, 90, a(102) - 0.1, a(105) - 0.3),
        pie(interr, -300, 700, 210, a(102) - 0.1, w(104, 'descartar') - 0.2),
        pie(lambda t: sprite('webb'), 350, 800, 330, w(104, 'Webb') - 0.2, a(105) - 0.3),
        tumb(lambda t: etiqueta('WEBB · 2024', 50), 350, 560, 360, 90, w(104, 'Webb'), a(105) - 0.3),
        pie(lambda t: sprite('check'), -300, 690, 170, w(104, 'descartar'), a(105) - 0.3),
        pie(lambda t: sprite('act'), -440, 820, 290, a(105) - 0.1),
        pie(lambda t: g_act(suave((t - a(105) - 0.6) / 0.8), suave((t - w(105, 'confirmaron') + 0.2) / 0.8)), 380, 840, 360, a(105) + 0.3, grosor=8),
        dato('ACT COLLABORATION · JCAP · NOV-2025', w(105, 'ACT')),
    ])
    X += paso
    # E33 · el tercero en discordia
    estacion('freedman', X, a(106) - 0.2, [
        pie(lambda t: g_freedman(suave((t - a(106)) / 0.6), suave((t - a(106) - 0.3) / 0.6), suave((t - w(107, '70,39') + 0.3) / 0.8)), 0, 850, 480, a(106) - 0.1, grosor=8),
        dato('FREEDMAN ET AL. 2025 · APJ 985, 203', w(107, '70,39')),
    ])
    X += paso
    # E34 · lo que está en juego
    estacion('importa', X, a(108) - 0.2, [
        pie(interr, 0, 720, 180, a(108) - 0.1, a(110) - 0.2),
        pie(lambda t: sprite('check'), 260, 720, 160, a(109) - 0.1, a(110) - 0.2),
        pie(lambda t: g_importa(suave((t - a(111) - 0.3) / 0.6), suave((t - w(111, '12 700') + 0.2) / 0.8), suave((t - a(112) + 0.1) / 1.0)),
            0, 840, 430, a(111) - 0.2, grosor=8),
    ], focos=[(a(112), 0.0, 90)])
    X += paso
    # E35–E36 · tres niveles
    apaga = lambda t: 1 - 0.55 * suave((t - a(116) - 0.8) / 0.8)   # noqa: E731
    estacion('niveles', X, a(113) - 0.2, [
        pie(lambda t: tarjeta_nivel('Comprobado', VERDE, 'check'), -520, 820, 360, a(114) - 0.1, alfa=apaga),
        pie(interr, 0, 720, 190, a(113) - 0.1, a(114) - 0.3),
        pie(reloj_vivo(0), -40, 720, 170, w(114, 'tres m') - 0.2, w(114, 'difieren') - 0.4),
        pie(reloj_vivo(1), 230, 720, 170, w(114, 'tres m'), w(114, 'difieren') - 0.4),
        pie(reloj_vivo(2), 500, 720, 170, w(114, 'tres m') + 0.2, w(114, 'difieren') - 0.4),
        pie(lambda t: etiqueta('13 000 – 14 000 M', 66), 230, 560, 70, w(114, '13 000') - 0.2, w(114, 'difieren') - 0.4),
        pie(lambda t: cartel('67', 250), 60, 740, 150, w(114, 'difieren') - 0.1, a(115) - 0.3),
        pie(lambda t: cartel('73', 250), 420, 740, 150, w(114, 'difieren') + 0.1, a(115) - 0.3),
        pie(lambda t: etiqueta('NO COINCIDEN', 66, papel=(250, 214, 140)), 240, 560, 70, w(114, 'difieren') + 0.4, a(115) - 0.3),
        pie(lambda t: tarjeta_nivel('Probable', AMBAR, 'aprox'), 0, 820, 360, a(115) - 0.1, alfa=apaga),
        pie(lambda t: tarjeta_nivel('Sin resolver', ROJO, '?'), 520, 820, 360, a(116) - 0.1),
    ], focos=[(a(116) + 0.8, 520, 110)])
    X += paso
    estacion('riess', X, a(117) - 0.2, [
        tumb(lambda t: sprite('regla'), -380, 560, 640, 90, a(117) - 0.1),
        pie(interr, -380, 700, 160, a(117) - 0.1),
        pie(lambda t: etiqueta('¿UN ERROR QUE NADIE HA ENCONTRADO?', 48), -380, 600, 60, a(117) + 0.2, a(119) + 0.1),
        pie(lambda t: sprite('puzle'), 400, 840, 380, a(118) - 0.2),
        pie(lambda t: etiqueta('ADAM RIESS: «FALTA ALGO EN EL MODELO»', 50), 0, 520, 62, a(119) + 0.3),
    ])
    X += paso
    # E37 · nadie estuvo allí… pero el universo dejó pruebas
    estacion('pruebas', X, a(120) - 0.3, [
        pie(lambda t: D.tarjeta('tierra', t, a(120) - 3), -430, 800, 260, a(121) - 0.4, a(122) + 0.2),
        pie(lambda t: D.tarjeta('sol', t, a(120) - 3), 0, 800, 260, a(121) - 0.3, a(122) + 0.2),
        pie(lambda t: D.tarjeta('estrella', t, a(120) - 3), 430, 800, 260, a(121) - 0.2, a(122) + 0.2),
        pie(lambda t: sprite('mapa_cmb'), -480, 820, 230, a(123) - 0.2, a(126) - 0.3),
        pie(lambda t: sprite('galaxia'), lambda t: -60 - 80 * suave((t - a(124)) / 2), 800, 120, a(124) - 0.2, a(126) - 0.3),
        pie(lambda t: sprite('galaxia'), lambda t: 60 + 80 * suave((t - a(124)) / 2), 820, 120, a(124), a(126) - 0.3),
        pie(lambda t: sprite('estrella'), 480, 800, 200, a(125) - 0.2, a(126) - 0.3),
        pie(reloj_vivo(0, ang=lambda t: -0.55), -460, 800, 300, a(126) - 0.1),
        pie(reloj_vivo(1, ang=lambda t: -0.5), 0, 800, 300, a(126) + 0.1),
        pie(reloj_vivo(2, ang=lambda t: -0.6), 460, 800, 300, a(126) + 0.3),
    ])
    X += paso
    estacion('avance', X, a(127) - 0.2, [
        pie(lambda t: sprite('puzle'), -120, 830, 420, a(127) - 0.1),
        pie(lambda t: sprite('pieza_suelta'), lambda t: lerp(560, 240, suave((t - a(127)) / 5.0)), 700, 140, a(127) + 0.3),
    ])
    X += paso
    # E38 · pregunta al público
    estacion('pregunta', X, a(128) - 0.2, [
        pie(interr, 0, 760, 230, a(128) - 0.1, w(129, 'error') - 0.5),
        tumb(lambda t: sprite('regla'), -430, 580, 600, 90, w(129, 'error') - 0.3),
        pie(interr, -430, 720, 160, w(129, 'error') - 0.1),
        pie(lambda t: etiqueta('ERROR DE MEDICIÓN', 60), -430, 620, 70, w(129, 'error') + 0.2),
        pie(lambda t: cartel('VS', 200), 0, 760, 120, w(129, 'modelo') - 0.6, a(130) - 0.4),
        pie(lambda t: sprite('puzle'), 440, 840, 320, w(129, 'modelo') - 0.2),
        pie(lambda t: etiqueta('FALTA ALGO EN EL MODELO', 60), 440, 620, 70, w(129, 'modelo') + 0.2),
        pie(lambda t: sprite('comentario'), -80, 740, 120, a(130) - 0.1),
        pie(lambda t: sprite('documento'), 120, 740, 120, a(131) - 0.2),
    ])
    X += paso
    # E39 · suscríbete
    estacion('cta', X, a(133) - 0.2, [
        pie(lambda t: cartel('SUSCRÍBETE', 240), -330, 780, 160, w(133, 'suscr') - 0.2),
        pie(lambda t: sprite('like'), 300, 760, 180, w(133, 'like') - 0.2),
        pie(lambda t: sprite('campana'), 560, 760, 180, w(133, 'campanita') - 0.2),
    ])
    # decorado de fondo: cohetes, el telescopio Webb y láminas espaciales de pie detrás de cada estación
    fondo = (('pg_cohete', 560), ('pg_webb', 280), ('pg_lam0', 300), ('pg_cohete', 600), ('pg_lam1', 260), ('pg_webb', 300), ('pg_lam2', 280))
    for k, st in enumerate(ST):
        clave, alto = fondo[k % len(fondo)]
        lado = -1 if k % 2 == 0 else 1
        st['items'].insert(0, pie(lambda t, c=clave: D.PZ[c], lado * 950, 1600, alto, st['t_in'] - 1.6, sfx='ninguno'))
        clave2, alto2 = fondo[(k + 3) % len(fondo)]
        st['items'].insert(0, pie(lambda t, c=clave2: D.PZ[c], -lado * 1250, 1750, alto2, st['t_in'] - 1.6, sfx='ninguno'))


# ---------------------------------------------------------------- dibujos especiales


NIEBLA = {}


def burbuja_pensamiento(t):
    """Burbuja de pensamiento con la explosión dentro; al decir «en algún sitio» se tacha con una X roja."""
    b_ = sprite('burbuja').copy()
    if t > w(14, 'algo explot') - 0.1:
        ex = sprite('explosion')
        k = suave((t - w(14, 'algo explot') + 0.1) / 0.4)
        lado = int(b_.height * 0.62 * (0.6 + 0.4 * k))
        e2 = ex.resize((lado, lado), Image.LANCZOS)
        b_.alpha_composite(e2, (int(b_.width * 0.53 - lado / 2), int(b_.height * 0.43 - lado / 2)))
    g = (t - w(14, 'en alg') - 0.9) / 0.5
    if g > 0:
        d = ImageDraw.Draw(b_)
        cx, cy, r = b_.width * 0.53, b_.height * 0.43, b_.height * 0.33
        for k_, ((x0, y0), (x1, y1)) in enumerate((((cx - r, cy - r), (cx + r, cy + r)), ((cx + r, cy - r), (cx - r, cy + r)))):
            p = min(1.0, max(0.0, g * 2 - k_))
            if p > 0:
                d.line([x0, y0, x0 + (x1 - x0) * p, y0 + (y1 - y0) * p], fill=(200, 40, 40, 240), width=max(6, int(b_.height * 0.05)))
    return b_



def dibujar_niebla(lz, t, X0):
    """Partículas (protones y electrones) rebotando; el rayo de luz no avanza; al enfriarse se unen y se despeja."""
    if 'p' not in NIEBLA:
        rnd = np.random.RandomState(5)
        n = 70
        NIEBLA['p'] = np.stack([rnd.uniform(-260, 460, n), rnd.uniform(620, 900, n), rnd.uniform(30, 300, n)], 1)
        NIEBLA['e'] = NIEBLA['p'] + rnd.uniform(-60, 60, (n, 3))
        NIEBLA['f'] = rnd.uniform(0, 6.28, (n, 3))
    p0, e0, fa = NIEBLA['p'], NIEBLA['e'], NIEBLA['f']
    osc = np.stack([np.sin(t * 0.6 + fa[:, 0]) * 18, np.sin(t * 0.5 + fa[:, 1]) * 14, np.cos(t * 0.55 + fa[:, 2]) * 16], 1)
    une = suave((t - w(24, 'los átomos')) / 2.0)
    pp = p0 + osc
    ee = e0 + osc * 1.4 + ((pp + np.array([16, 0, 10])) - (e0 + osc * 1.4)) * une
    despeja = suave((t - w(24, 'la niebla')) / 1.6)
    al = suave((t - a(21) + 0.3) / 1.0) * (1 - despeja)
    if al < 0.02:
        return
    d = ImageDraw.Draw(lz, 'RGBA')
    pts = []
    for arr_, r_, col in ((pp, 12, (232, 136, 70)), (ee, 6, (150, 196, 240))):
        for X_, Z_, Y_ in arr_:
            sx, sy, s = D.proy(X0 + X_, Z_, Y_)
            pts.append((Z_, sx, sy, r_ * s, col))
    for Z_, sx, sy, r_, col in sorted(pts, key=lambda q: -q[0]):
        d.ellipse([sx - r_, sy - r_, sx + r_, sy + r_], fill=col + (int(255 * al),))
    rnd = np.random.RandomState(9)
    camino = [(X0 + 100, 760, 160)]
    for _ in range(40):
        x, z, y = camino[-1]
        camino.append((min(X0 + 420, max(X0 - 220, x + rnd.uniform(-60, 60))), min(890, max(630, z + rnd.uniform(-40, 40))), min(280, max(40, y + rnd.uniform(-40, 40)))))
    prog = suave((t - w(21, 'la luz no')) / 6.0)
    n = max(2, int(len(camino) * prog))
    D.linea(lz, [D.proy(x, z, y)[:2] for x, z, y in camino[:n]], (255, 214, 130), 4, al)


def dibujar_rayo_libre(lz, t, X0):
    g = suave((t - a(25) + 0.1) / 1.0)
    al = 1 - suave((t - a(26) + 0.5) / 0.6)
    if g <= 0 or al <= 0:
        return
    p0 = D.proy(X0 - 900, 700, 160)[:2]
    p1 = D.proy(X0 - 900 + 1800 * g, 700, 160)[:2]
    D.linea(lz, [p0, p1], (255, 226, 160), 6, al)


def dibujar_rayos_tierra(lz, t, X0):
    al = suave((t - a(26)) / 0.5) * (1 - suave((t - a(27) + 0.6) / 0.5))
    if al <= 0:
        return
    tx, ty, s = D.proy(X0, 760, 75)
    for j in range(18):
        ang = j / 18 * 2 * math.pi + 0.1
        g = suave((t - a(26) - (j % 6) * 0.12) / 1.4)
        r0, r1 = 900, lerp(900, 90 * s, g)
        D.linea(lz, [(tx + math.cos(ang) * r0, ty + math.sin(ang) * r0 * 0.6), (tx + math.cos(ang) * r1, ty + math.sin(ang) * r1 * 0.6)], (255, 214, 140), 3, al * 0.85)


def termometro_liquido(lz, t, X, Z, alto, t0, dur, n0, n1, col):
    """Columna de líquido del termómetro de cartón (baja de n0 a n1)."""
    sx, sy, s = D.proy(X, Z)
    nivel = lerp(n0, n1, suave((t - t0) / dur))
    h_ = alto * s
    tubo_bajo = sy - h_ * 0.13
    tubo_alto = sy - h_ * 0.93
    top = lerp(tubo_bajo, tubo_alto, nivel)
    d = ImageDraw.Draw(lz, 'RGBA')
    ancho = 0.05 * alto * s
    d.rectangle([sx - ancho / 2, top, sx + ancho / 2, tubo_bajo], fill=col + (255,))
    d.ellipse([sx - ancho * 1.8, sy - h_ * 0.16, sx + ancho * 1.8, sy - h_ * 0.02], fill=col + (255,))


def flechas_escalera(lz, t, X0):
    g = suave((t - a(58) + 0.2) / 1.2)
    for (xa, xb) in ((-480, 0), (0, 480)):
        p0 = (X0 + xa + 60, 640, 200)
        p1 = (X0 + xb - 60, 640, 240)
        pts = []
        for i in range(int(20 * g) + 1):
            s_ = i / 20
            pts.append(D.proy(lerp(p0[0], p1[0], s_), 640, lerp(p0[2], p1[2], s_) + math.sin(math.pi * s_) * 120)[:2])
        D.linea(lz, pts, (196, 40, 40), 5)


def caminos(lz, t, X0):
    g = suave((t - a(85) + 0.2) / 1.2)
    for xc in (-500, 0, 500):
        pts = []
        for i in range(int(20 * g) + 1):
            s_ = i / 20
            pts.append(D.proy(X0 + xc * (0.3 + 0.7 * s_), lerp(500, 780, s_), 0)[:2])
        D.linea(lz, pts, (196, 40, 40), 6)


def oscuridad_final(arr, t, X0):
    """Callback del inicio: «Nadie estuvo allí» se cuenta casi a oscuras con un punto de luz; con «pruebas» vuelve la luz."""
    t0, t1 = a(120) - 0.3, a(122) + 1.4
    if not (t0 < t < t1):
        return arr
    baja = suave((t - t0) / 1.2)
    sube = suave((t - a(122) + 0.1) / 1.4)
    lx, ly, sl = D.proy(X0, 1000, 330)
    d = np.hypot(D.FIJ['xx'] - lx, (D.FIJ['yy'] - ly) * 1.25)
    r = (560 + 700 * sube) * sl
    amb = 1 - baja * (1 - sube) * 0.95
    luz = np.clip(amb + np.exp(-(d / max(10.0, r)) ** 2), 0, 1)
    arr = arr * luz[..., None]
    g = np.exp(-(np.hypot(D.FIJ['xx'] - lx, D.FIJ['yy'] - ly) / 8) ** 2) * 1.5 * baja * (1 - sube)
    return arr + g[..., None] * np.array([255, 238, 200], f32)

# ================================================================== cámara


CLAVES = []
HZ = 240.0          # horizonte de las estaciones: la cámara mira un poco hacia la mesa y centra el contenido


def preparar_camara():
    CLAVES.clear()
    CLAVES.append((T_D, 1995.0, -2150.0, 1000.0, 240.0))
    CLAVES.append((T_D + 0.5, 1995.0, -2170.0, 1005.0, 238.0))
    for k, st in enumerate(ST):
        llegada = max(st['t_in'], CLAVES[-1][0] + 0.8)
        salida_sig = ST[k + 1]['t_in'] - 1.5 if k + 1 < len(ST) else DUR
        CLAVES.append((llegada, st['X'], st['dz'], st['h'], HZ))
        if salida_sig > llegada + 0.3:
            CLAVES.append((salida_sig, st['X'], st['dz'] + 60, st['h'] - 10, HZ))


_camara_d = D.camara


def camara(t):
    if t < T_D:
        return _camara_d(t)
    k = 0
    while k + 1 < len(CLAVES) and CLAVES[k + 1][0] < t:
        k += 1
    t0, x0, z0, h0, hz0 = CLAVES[k]
    if k + 1 < len(CLAVES):
        t1, x1, z1, h1, hz1 = CLAVES[k + 1]
        u = suave3((t - t0) / max(0.01, t1 - t0))
    else:
        t1, x1, z1, h1, hz1 = CLAVES[k]
        u = 0
    x, z, h, hz = lerp(x0, x1, u), lerp(z0, z1, u), lerp(h0, h1, u), lerp(hz0, hz1, u)
    st = estacion_activa(x)
    if st:
        for (tf, fx, dz) in st['focos']:
            uu = t - tf
            if -0.6 < uu < 3.4:
                g = suave3((uu + 0.6) / 0.9) if uu < 0.3 else 1 - suave3((uu - 0.3) / 3.1)
                x += (st['X'] + fx - x) * 0.25 * g
                z += dz * g
    D.CAM_H[0] = hz
    return x, z, h


def estacion_activa(x):
    mejor = None
    for st in ST:
        if abs(st['X'] - x) < 1700:
            mejor = st
    return mejor


D.camara = camara
D.escenario = escenario_largo

# ================================================================== composición


def escena(t):
    arr = D.escena(t)          # mesa larga + las piezas de los primeros 41 s (con nuestra cámara)
    if t < T_D - 0.5:
        return arr
    lz = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')
    cx = D.CAM[0]
    z_foco = 780.0
    tumbados, pies = [], []
    activa = None
    for st in ST:
        if abs(st['X'] - cx) > 4200 or t < st['t_in'] - 2.0:
            continue
        if abs(st['X'] - cx) < 1700:
            activa = st
        X0 = st['X']
        for it in st['items']:
            if t < it['on'] - 0.01:
                continue
            off = it.get('off')
            cae = suave3((t - off) / 0.5) if off is not None else 0.0
            if cae >= 0.999:
                continue
            if it['tipo'] == 'tumb':
                al = suave((t - it['on']) / 0.4) * (1 - cae)
                tumbados.append((it, X0, al))
            else:
                pies.append((V(it['Z'], t), it, X0, cae))
    for it, X0, al in tumbados:
        D.tumbado(lz, it['img'](t), X0 + V(it['dx'], t), it['Z'], it['ancho'], it['fondo'], alfa=al)
    for Zv, it, X0, cae in sorted(pies, key=lambda q: -q[0]):
        if it['tipo'] == 'fn':
            it['dibujar'](lz, t, X0)
            continue
        alfa = V(it.get('alfa', 1.0), t)
        esc = 1.0 if it.get('sfx') == 'ninguno' else ESC_PIEZAS
        D.de_pie(lz, it['img'](t), X0 + V(it['dx'], t), Zv, V(it['alto'], t) * esc, t, z_foco, grosor=it.get('grosor', 12),
                 levanta=D.entra(t, it['on'], it.get('din', 0.6)), cae=cae, alfa=alfa, lado=it.get('lado', 0.5))
    arr = np.asarray(lz.convert('RGB'), f32)
    if activa and activa['nombre'] == 'pruebas':
        arr = oscuridad_final(arr, t, activa['X'])
    return arr


def fotograma(i):
    cargar()
    if not ST:
        definir()
        preparar_camara()
    t = i / FPS
    return D.acabado(escena(t), t)


def _bytes(i):
    return fotograma(i).tobytes()

# ================================================================== audio


def efectos_completos(ruta):
    """Efectos de todo el video: los de la prueba de 41 s + uno suave por cada pieza que se levanta, un barrido por viaje
    de cámara, sellos, rotuladores y un golpe en las revelaciones. Nivel fijo, siempre por debajo de la voz."""
    from scipy import signal
    from scipy.io import wavfile
    sr = 48000
    n = int(DUR * sr)
    out = np.zeros(n)
    tmp = os.path.join(SALIDA, '_efectos_41s.wav')
    D.efectos(tmp)
    _, x41 = wavfile.read(tmp)
    x41 = x41.astype(float) / 32768
    m41 = min(len(x41), int(T_D * sr))
    out[:m41] += x41[:m41]
    rnd = np.random.RandomState(11)

    def lp(x, fc):
        return signal.sosfilt(signal.butter(2, fc, 'lowpass', fs=sr, output='sos'), x)

    def poner(t0, x, nv):
        i0 = int(t0 * sr)
        mm = min(len(x), n - i0)
        if i0 >= 0 and mm > 0:
            out[i0:i0 + mm] += x[:mm] * nv

    def levanta(t0, nv=0.06):
        m = int(0.16 * sr)
        tt = np.arange(m) / sr
        poner(t0, lp(rnd.randn(m), 1800) * np.sin(np.pi * tt / tt[-1]) * 0.6 + np.sin(2 * np.pi * 140 * tt) * np.exp(-tt / 0.03) * 0.5, nv)

    def barrido(t0, dur=1.4, nv=0.06):
        m = int(dur * sr)
        poner(t0 - dur * 0.4, lp(rnd.randn(m), 700) * np.sin(np.linspace(0, np.pi, m)) ** 3, nv)

    def sello(t0, nv=0.1):
        m = int(0.25 * sr)
        tt = np.arange(m) / sr
        poner(t0, np.sin(2 * np.pi * 95 * tt) * np.exp(-tt / 0.05) + lp(rnd.randn(m), 1800) * np.exp(-tt / 0.03) * 0.6, nv)

    def rotulador(t0, nv=0.06):
        m = int(0.25 * sr)
        x = signal.sosfilt(signal.butter(2, [2500, 8000], 'bandpass', fs=sr, output='sos'), rnd.randn(m))
        poner(t0, x * np.sin(np.linspace(0, np.pi, m)), nv)

    def impacto(t0, nv=0.08):
        m = int(1.6 * sr)
        tt = np.arange(m) / sr
        f_ = 55 * (1 + 0.5 * np.exp(-tt / 0.05))
        fase = 2 * np.pi * np.cumsum(f_) / sr
        poner(t0, (np.sin(fase) + 0.5 * np.sin(2 * fase)) * np.exp(-tt / 0.45), nv)

    for k, st in enumerate(ST):
        barrido(st['t_in'] - 0.6)
        for it in st['items']:
            if it['on'] < T_D:
                continue
            tipo = it.get('sfx', 'levanta' if it['tipo'] == 'pie' else None)
            if tipo == 'levanta':
                levanta(it['on'])
            elif tipo == 'sello':
                sello(it['on'])
            elif tipo == 'rotulador':
                rotulador(it['on'] + 0.1)
        for (tf, _, _) in st['focos']:
            impacto(tf)
    out = np.tanh(out * 1.6) / 1.6
    wavfile.write(ruta, sr, (np.clip(out, -1, 1) * 32767).astype(np.int16))


def audio_final():
    """Voz + música (mezcla del video 2) + efectos."""
    ruta = os.path.join(SALIDA, '_audio-diorama.wav')
    fx = os.path.join(SALIDA, '_efectos-diorama.wav')
    efectos_completos(fx)
    cadena = '[0:a]aresample=48000[v];[1:a]aresample=48000[f];[v][f]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[out]'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', AUDIO_VOZ, '-i', fx, '-filter_complex', cadena, '-map', '[out]', '-ac', '2', ruta], check=True)
    return ruta

# ================================================================== render por partes


def limites_parte(k):
    paso = N / PARTES
    return int(round((k - 1) * paso)), int(round(k * paso))


def render_parte(k, audio):
    i0, i1 = limites_parte(k)
    mp4 = os.path.join(SALIDA, 'video-02-diorama-parte-%02d.mp4' % k)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-ss', '%.4f' % (i0 / FPS), '-t', '%.4f' % ((i1 - i0) / FPS), '-i', audio,
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
           '-movflags', '+faststart', mp4]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    from multiprocessing import Pool
    t0 = time.time()
    with Pool(max(1, (os.cpu_count() or 4) - 1)) as pool:
        for j, bts in enumerate(pool.imap(_bytes, range(i0, i1), chunksize=4)):
            pr.stdin.write(bts)
            if j % 240 == 0:
                print(f'  parte {k}: {(i0 + j) / FPS:6.1f} s ({time.time() - t0:.0f} s)', flush=True)
    pr.stdin.close()
    pr.wait()
    print('parte lista:', mp4, flush=True)
    return mp4


def verificar(t0, t1, paso=0.25, margen=12):
    cargar()
    definir()
    preparar_camara()
    malos = []
    t = t0
    while t < t1:
        p, q = camara(t - 0.1), camara(t + 0.1)
        quieta = abs(p[0] - q[0]) + abs(p[1] - q[1]) < 25
        D.REG.clear()
        escena(t)
        if quieta:
            for tag, x0, y0, x1, y1 in D.REG:
                if tag == 'deco' or x1 < 0 or y1 < 0 or x0 > W or y0 > H:
                    continue
                if x0 < -margen or y0 < -margen or x1 > W + margen or y1 > H + margen:
                    malos.append((round(t, 2), tag, x0, y0, x1, y1))
        t += paso
    return malos


def main():
    args = sys.argv[1:]
    os.makedirs(SALIDA, exist_ok=True)
    D.fabricar('--rehacer' in args)
    fabricar_tramos('--rehacer' in args)
    definir()
    preparar_camara()
    if '--frame' in args:
        i = args.index('--frame')
        t = float(args[i + 1])
        ruta = args[i + 2] if len(args) > i + 2 else os.path.join(SALIDA, 'dio-%07.2f.png' % t)
        Image.fromarray(fotograma(int(round(t * FPS)))).save(ruta)
        print('fotograma:', ruta)
        return
    if '--hoja' in args:
        # hoja de contacto: --hoja t0 t1 paso ruta.png
        from multiprocessing import Pool
        i = args.index('--hoja')
        t0, t1, paso, ruta = float(args[i + 1]), float(args[i + 2]), float(args[i + 3]), args[i + 4]
        ts = list(np.arange(t0, t1 + 1e-6, paso))
        with Pool(7) as pool:
            fs = pool.map(fotograma, [int(round(x * FPS)) for x in ts])
        w, h = 480, 270
        hoja = Image.new('RGB', (w * 4, (h + 24) * ((len(fs) + 3) // 4)), (20, 20, 20))
        dh = ImageDraw.Draw(hoja)
        for k, (x, f) in enumerate(zip(ts, fs)):
            px, py = (k % 4) * w, (k // 4) * (h + 24)
            hoja.paste(Image.fromarray(f).resize((w, h)), (px, py + 24))
            dh.text((px + 6, py + 4), '%.1f s' % x, fill=(255, 255, 255))
        hoja.save(ruta)
        print('hoja:', ruta)
        return
    if '--verificar' in args:
        i = args.index('--verificar')
        for m in verificar(float(args[i + 1]), float(args[i + 2])):
            print('CORTE', m)
        print('fin de la verificación')
        return
    if '--unir' in args:
        lista = os.path.join(SALIDA, 'lista.txt')
        with open(lista, 'w') as f:
            for k in range(1, PARTES + 1):
                f.write("file '%s'\n" % os.path.join(SALIDA, 'video-02-diorama-parte-%02d.mp4' % k).replace('\\', '/'))
        final = os.path.join(AQUI, 'salida', 'video-02-diorama-final.mp4')
        # solo se concatena la imagen; el audio sale del máster en una sola pieza (al concatenar AAC, el relleno
        # inicial de cada parte se acumula y desfasa el sonido ~21 ms por unión)
        audio = os.path.join(SALIDA, '_audio-diorama.wav')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lista, '-i', audio,
                        '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', '%.4f' % (N / FPS),
                        '-movflags', '+faststart', final], check=True)
        print('video final:', final)
        return
    audio = os.path.join(SALIDA, '_audio-diorama.wav')
    if '--audio' in args or not os.path.exists(audio):
        audio = audio_final()
    if '--parte' in args:
        i = args.index('--parte')
        for k in args[i + 1].split(','):
            render_parte(int(k), audio)


if __name__ == '__main__':
    main()
