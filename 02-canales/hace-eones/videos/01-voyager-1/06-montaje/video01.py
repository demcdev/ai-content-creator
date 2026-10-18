#!/usr/bin/env python3
"""
Video 1 completo (Voyager 1) · montador automático de Hace Eones.

Lee tiempos.json (alineación de las 120 frases con el audio real) y dibuja cada escena con las imágenes oficiales
guardadas en «05-licencias/originales» de este video y esquemas animados con código.
Este script vive en la carpeta del video; las librerías compartidas están en «herramientas/montaje».

  python video01.py --frame 150 f.png       un fotograma (segundo 150) para revisar el diseño
  python video01.py                         render completo en paralelo -> salida/video-01-completo.mp4 (+ .srt)
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', 'herramientas', 'montaje', 'comun')))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', 'herramientas', 'montaje', 'animaciones', 'espacial'))
import aa as trazo
import globo
import dsn_voyager as dsn

from estilo import (FONDO_ULT, Vista, base, bloom, capa_orbitas, dibujar_planeta, etq, hud, linea_glow, panel, txt_glow, _mascara)  # noqa
from ui import (capitulo, cta, _contenido_rotulo, HIELO, anillo_arco, caja, credito, ease_in, ease_out, etiqueta_esquema, icono_hex, logo, pastilla, rotulo, sl, titulo)  # noqa
from montar import (AMBAR, BG, HUESO, FPS, H, NEGRO, ORIG, TIERRA, W, FONDO, DEGRADADO_INF,  # noqa
                    aparecer, blk, brillo, cargar, clamp, disco, envolver,
                    escena_imagen, lerp, mezcla, neg, pegar, punto, reg, sprite_texto, ss, trocear_texto)
from borrador import AUDIO, a1_distancia, a2_trayectoria, dibujar_rotulo, escena_lista  # noqa: E402  (escenas del primer borrador)

AQUI = os.path.dirname(os.path.abspath(__file__))   # carpeta «06-montaje» de este video (tiempos, música, salida)

# Las escenas están escritas con los tiempos del primer audio (ritmo 0,95): tiempos-095.json.
# El audio definitivo (tiempos.json) tiene otro ritmo; t_viejo() traduce cada instante del video al del primer audio,
# de modo que cada escena sigue clavada a su frase. Los subtítulos y la duración usan los tiempos nuevos.
TIEMPOS = json.load(open(os.path.join(AQUI, 'tiempos-095.json'), encoding='utf8'))
NUEVO = json.load(open(os.path.join(AQUI, 'tiempos.json'), encoding='utf8'))
FRASES = TIEMPOS['frases']
FRASES_N = NUEVO['frases']
FIN_AUDIO = NUEVO['total']
COLA = 2.0                       # 2 s de silencio al final (la guía lo pide)
DURACION = FIN_AUDIO + COLA
DURACION_V = TIEMPOS['total'] + COLA


def _anclas():
    assert len(FRASES) == len(FRASES_N), 'distinto número de frases: {} y {}'.format(len(FRASES), len(FRASES_N))
    v, n = [0.0], [0.0]
    for i, (fo, fn) in enumerate(zip(FRASES, FRASES_N)):
        if i == 0 and len(fn['texto']) > len(fo['texto']) + 10:
            # la primera frase ahora lleva la comparación con el móvil: el tramo viejo coincide con el principio
            corte = len(fo['texto']) / float(len(fn['texto']))
            ps = fn['ini'] + (fn['fin'] - fn['ini']) * corte
            global SPLIT_N
            SPLIT_N = ps
            pares = [(fo['ini'], fn['ini']), (fo['fin'], ps), (fo['fin'] + 0.1, fn['fin'])]
        else:
            pares = [(fo['ini'], fn['ini']), (fo['fin'], fn['fin'])]
        for a, b in pares:
            if a > v[-1] and b > n[-1]:
                v.append(a)
                n.append(b)
    v.append(TIEMPOS['total'])
    n.append(NUEVO['total'])
    return np.array(v), np.array(n)


SPLIT_N = None
_V, _N = _anclas()


def t_nuevo(to):
    """Instante del video final que corresponde a un instante del primer audio."""
    return float(np.interp(to, _V, _N))


def t_viejo(t):
    """Instante equivalente en el primer audio (tiempo de las escenas)."""
    if t >= _N[-1]:
        return _V[-1] + (t - _N[-1])
    return float(np.interp(t, _N, _V))
GRIS = mezcla(BG, HUESO, 0.55)
VERDE = (120, 205, 190)
ROJO = (232, 96, 84)


def T(prefijo, n=0):
    k = 0
    for f in FRASES:
        if f['texto'].startswith(prefijo):
            if k == n:
                return f
            k += 1
    raise KeyError(prefijo)


def I(prefijo, n=0): return T(prefijo, n)['ini']
def F(prefijo, n=0): return T(prefijo, n)['fin']

# --------------------------------------------------------------- utilidades de dibujo

_cache = {}


def txt(fr, s, fnt, color, x, y, a=1.0, ax='l', ay='t'):
    if a > 0:
        pegar(fr, sprite_texto(s, fnt, color), x, y, a, ax, ay)


def linea(fr, p0, p1, color, ancho=3, a=1.0):
    trazo.linea(fr, [p0, p1], color, ancho, a, ss=3)


def anillo(fr, x, y, r, color=AMBAR, a=1.0, ancho=4):
    if a <= 0:
        return
    pegar(fr, brillo(int(r * 1.8), color), x, y, 0.35 * a, 'm', 'm')
    trazo.elipse(fr, (x - r, y - r, x + r, y + r), color, ancho, a, ss=3)


def fondo_borroso(archivo, oscuro=0.84, desenfoque=26, t=0.0):
    k = ('bg', archivo)
    if k not in _cache:
        im = cargar(archivo)
        s = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.BICUBIC)
        x0, y0 = (im.width - W) // 2, (im.height - H) // 2
        im = im.crop((x0, y0, x0 + W, y0 + H)).filter(ImageFilter.GaussianBlur(desenfoque))
        _cache[k] = Image.blend(im, Image.new('RGB', (W, H), BG), min(0.96, oscuro + 0.07))
    # el cielo estrellado queda por detrás de la foto desenfocada (se funde con ella): todas las escenas se sienten «espaciales»
    fr = ImageChops.screen(_cache[k], base(t))
    FONDO_ULT['bg'] = fr
    return fr


def mascara_disco(archivo):
    k = ('mk', archivo)
    if k not in _cache:
        im = imagen(archivo)
        m = Image.new('L', im.size, 0)
        e = int(im.width * 0.012)
        ImageDraw.Draw(m).ellipse((e, e, im.width - e, im.height - e), fill=255)
        _cache[k] = m.filter(ImageFilter.GaussianBlur(3))
    return _cache[k]


def imagen(archivo):
    k = ('im', archivo)
    if k not in _cache:
        _cache[k] = cargar(archivo)
    return _cache[k]


def pegar_img(fr, im, cx, cy, h, a=1.0, marco=True, mascara=None):
    w = int(im.width * h / im.height)
    r = im.resize((w, int(h)), Image.BICUBIC)
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    if mascara is not None:
        mk = mascara.resize(r.size, Image.BICUBIC)
        fr.paste(r, (x0, y0), mk.point(lambda v: int(v * a)) if a < 1 else mk)
    else:
        fr.paste(r, (x0, y0), Image.new('L', r.size, int(255 * a)) if a < 1 else None)
    if marco:
        trazo.rect(fr, (x0, y0, x0 + w, y0 + int(h)), HUESO, 2, 0.34 * a)
    return x0, y0, x0 + w, y0 + int(h)


def foto(t, ini, fin, archivo, h0, h1, cx, cy, pie=None, oscuro=0.84, fondo=True):
    fr = fondo_borroso(archivo, oscuro, t=t) if fondo else base(t)
    u = ss((t - ini) / max(0.1, fin - ini))
    x0, y0, x1, y1 = pegar_img(fr, imagen(archivo), cx, cy - 28, lerp(h0, h1, u) * 0.93)
    if pie:
        txt(fr, pie, reg(26), HUESO, cx, y1 + 14, 0.9, 'm')
    return fr


def _grad(size, c0, c1, ang=45.0):
    """Degradado lineal c0→c1 con el ángulo dado (grados), como imagen RGB."""
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = math.radians(ang)
    u = (xx * math.cos(a) + yy * math.sin(a))
    u = (u - u.min()) / max(1e-6, u.max() - u.min())
    c0, c1 = np.array(c0, np.float32), np.array(c1, np.float32)
    return Image.fromarray((c0 * (1 - u[..., None]) + c1 * u[..., None]).astype('uint8'))


def _rel(lienzo, mascara, c0, c1, ang=45.0):
    """Pega en el lienzo RGBA la forma `mascara` rellena con un degradado."""
    lienzo.paste(_grad(mascara.size, c0, c1, ang), (0, 0), mascara)


def icono(nombre):
    k = ('icono', nombre)
    if k in _cache:
        return _cache[k]
    s = 4
    if nombre == 'sonda':
        w, h = 260, 170
        m = Image.new('RGBA', (w * s, h * s), (0, 0, 0, 0))
        def forma(f):
            mk = Image.new('L', (w * s, h * s), 0)
            f(ImageDraw.Draw(mk))
            return mk
        d = ImageDraw.Draw(m)
        d.line((104 * s, 98 * s, 30 * s, 22 * s), fill=(160, 166, 188, 255), width=3 * s)                 # brazo del magnetómetro
        d.ellipse((24 * s, 16 * s, 38 * s, 30 * s), fill=(200, 204, 220, 255))
        d.line((110 * s, 140 * s, 70 * s, 168 * s), fill=(150, 156, 178, 255), width=4 * s)               # antena
        d.line((128 * s, 120 * s, 238 * s, 128 * s), fill=(150, 156, 178, 255), width=4 * s)              # brazo del RTG
        _rel(m, forma(lambda dd: dd.rectangle((92 * s, 98 * s, 130 * s, 142 * s), fill=255)), (92, 90, 108), (40, 40, 56), 70)   # cuerpo
        _rel(m, forma(lambda dd: dd.rectangle((214 * s, 116 * s, 252 * s, 142 * s), fill=255)), (150, 120, 96), (70, 52, 44), 90)  # RTG
        _rel(m, forma(lambda dd: dd.ellipse((40 * s, 18 * s, 170 * s, 120 * s), fill=255)), (250, 246, 240), (132, 128, 142), 55)  # plato
        _rel(m, forma(lambda dd: dd.ellipse((60 * s, 34 * s, 152 * s, 106 * s), fill=255)), (150, 146, 164), (236, 232, 240), 55)  # concavidad
        d.ellipse((40 * s, 18 * s, 170 * s, 120 * s), outline=(255, 255, 255, 190), width=2 * s)
        d.ellipse((101 * s, 58 * s, 113 * s, 70 * s), fill=(90, 90, 110, 255))
    else:  # antena de la Tierra
        w, h = 240, 190
        m = Image.new('RGBA', (w * s, h * s), (0, 0, 0, 0))
        def forma(f):
            mk = Image.new('L', (w * s, h * s), 0)
            f(ImageDraw.Draw(mk))
            return mk
        d = ImageDraw.Draw(m)
        _rel(m, forma(lambda dd: dd.polygon([(110 * s, 100 * s), (56 * s, 188 * s), (164 * s, 188 * s)], fill=255)), (150, 164, 206), (58, 66, 104), 90)
        d.line((110 * s, 106 * s, 76 * s, 186 * s), fill=(210, 220, 245, 200), width=2 * s)
        d.line((110 * s, 106 * s, 144 * s, 186 * s), fill=(210, 220, 245, 200), width=2 * s)
        _rel(m, forma(lambda dd: dd.ellipse((20 * s, 20 * s, 200 * s, 130 * s), fill=255)), (252, 254, 255), (126, 142, 190), 60)
        _rel(m, forma(lambda dd: dd.ellipse((46 * s, 38 * s, 174 * s, 112 * s), fill=255)), (140, 156, 204), (238, 244, 255), 60)
        d.ellipse((20 * s, 20 * s, 200 * s, 130 * s), outline=(255, 255, 255, 200), width=2 * s)
        d.line((110 * s, 76 * s, 110 * s, 12 * s), fill=(196, 206, 232, 255), width=4 * s)
        d.ellipse((103 * s, 4 * s, 117 * s, 18 * s), fill=(240, 246, 255, 255))
    m = m.resize((m.width // s, m.height // s), Image.LANCZOS)
    rgb = Image.new('RGB', m.size, (0, 0, 0))
    rgb.paste(m, (0, 0), m)
    _cache[k] = (rgb, m.getchannel('A'), m.size)
    return _cache[k]


def pegar_icono(fr, nombre, cx, cy, esc=1.0, a=1.0):
    rgb, al, (w, h) = icono(nombre)
    if esc != 1.0:
        rgb = rgb.resize((int(w * esc), int(h * esc)), Image.LANCZOS)
        al = al.resize(rgb.size, Image.LANCZOS)
    if a < 1:
        al = al.point(lambda v: int(v * a))
    fr.paste(rgb, (int(cx - rgb.width / 2), int(cy - rgb.height / 2)), al)


def bits(fr, x0, x1, y, t, vel, color, a=1.0, n=14):
    L = abs(x1 - x0)
    sgn = 1 if x1 > x0 else -1
    for k in range(n):
        d = (t * vel + k * L / n) % L
        trazo.rect(fr, (x0 + sgn * d - 5, y - 5, x0 + sgn * d + 5, y + 5), color, 1, a, relleno=True, ss=2)

# --------------------------------------------------------------------- escenas

def esc_lista(t):
    """«Hoy vamos a ver cinco cosas»: ruta de cinco puntos que se iluminan al ritmo de la voz."""
    ini = 90.22
    fr = escena_imagen('M01-PIA26353.jpg', t, ini, ini + 20, 1.22, 1.22, (0.58, 0.45), (0.58, 0.45), oscuro=0.78, desenfoque=18)
    p = ease_out((t - 90.3) / 0.9)
    ancho = 148 + 52 + max(neg(38).getlength(s) for s in ('Lo que descubrió en su camino', 'Una foto que cambió cómo nos vemos', 'La frontera de la burbuja del Sol', 'Cómo se habla con una nave tan lejana', 'Qué le queda de energía')) + 64
    px, py, alto = int((W - ancho) / 2), 96, 660          # panel centrado en pantalla (por encima de los subtítulos)
    caja(fr, px, py, int(ancho), alto, AMBAR, 1.0, p, c=28, oscuro=0.55, blur=16)
    a = ss((t - 90.7) / 0.6) * clamp(p * 2)
    titulo(fr, 'EN ESTE VIDEO', 'Hoy vamos a ver cinco cosas', px + 64, py + 44, a, 'l', 48)
    items = [(92.28, 'Lo que descubrió en su camino'), (94.18, 'Una foto que cambió cómo nos vemos'),
             (97.05, 'La frontera de la burbuja del Sol'), (100.46, 'Cómo se habla con una nave tan lejana'),
             (102.9, 'Qué le queda de energía')]
    x0, y0, dy = px + 96, py + 232, 88
    d = ImageDraw.Draw(fr)
    for i, (t0, texto) in enumerate(items):
        aa = ease_out((t - t0) / 0.6)
        if aa <= 0:
            continue
        y = y0 + i * dy
        if i > 0:    # tramo de la ruta que une con el punto anterior
            ya = y0 + (i - 1) * dy
            trazo.linea(fr, [(x0, ya + 30), (x0, ya + 30 + (dy - 60) * aa)], AMBAR, 2, 0.6, ss=2)
        sig = items[i + 1][0] if i + 1 < len(items) else 1e9
        suave = ss((t - t0) / 0.4) * (1 - ss((t - sig) / 0.5))
        anillo_arco(fr, x0, y, 24, AMBAR, 1.0, aa, 3, -90, 0.45)
        if suave > 0.02:
            punto(fr, x0, y, 20 * suave, AMBAR, suave, 1.7)
        pegar(fr, sprite_texto(str(i + 1), neg(26), mezcla(AMBAR, BG, suave)), x0, y, aa, 'm', 'm')
        col = mezcla(mezcla(BG, HUESO, 0.72), HUESO, suave)
        pegar(fr, sprite_texto(texto, neg(38), col), x0 + 52 + (1 - aa) * 18, y, aa, 'l', 'm')
    return fr


def esc_jupiter(t):
    return foto(t, 119.10, 140.94, 'M03d-PIA00378.jpg', 560, 620, 960, 370, 'Voyager 1 · 2-mar-1979 · Ío delante de Júpiter')


def esc_io(t):
    fr = base(t)
    u = ss((t - 140.94) / 22.4)
    pegar_img(fr, imagen('M03b-PIA02308-galileo.jpg'), 700, 360, lerp(620, 680, u), 1.0, marco=False, mascara=mascara_disco('M03b-PIA02308-galileo.jpg'))
    txt(fr, 'Ío', blk(54), HUESO, 700, 880, 0.0, 'm')
    a = ss((t - 153.81) / 0.8)
    if a > 0:
        x0, y0, x1, y1 = pegar_img(fr, imagen('M03-PIA00379.jpg'), 1450, 360, 400, a)
        txt(fr, 'Voyager 1 · 8-mar-1979', reg(26), HUESO, 1450, y1 + 14, 0.9 * a, 'm')
        # círculo sobre la nube del borde izquierdo de la luna (≈ 19 % / 36 % de la imagen)
        px, py = x0 + 0.19 * (x1 - x0), y0 + 0.36 * (y1 - y0)
        anillo(fr, px, py, 40 + 4 * math.sin(t * 5), AMBAR, a * ss((t - 154.3) / 0.6))
    etiqueta_esquema_opcional = None
    return fr


def esc_io2(t):
    return foto(t, 163.31, 172.01, 'M03c-PIA00373.jpg', 560, 620, 960, 360, 'Voyager 1 · 4-mar-1979 · penacho de más de 100 km')


def esc_saturno(t):
    if t < 181.0:
        return foto(t, 172.01, 181.0, 'M04-PIA02225.jpg', 590, 640, 960, 360, 'Voyager 1 · 18-oct-1980 · a 34 millones de km de Saturno')
    return foto(t, 181.0, 191.63, 'M05-PIA01531.jpg', 590, 640, 960, 360, 'Anillos de Saturno · imagen compuesta de varias tomas')


def esc_titan(t):
    fr = foto(t, 191.63, 214.5, 'M06-PIA02238.jpg', 560, 620, 760, 360, 'Imagen realzada · Voyager 1 · 12-nov-1980')
    a = ss((t - 201.0) / 0.8)
    txt(fr, '90 % nitrógeno', blk(84), AMBAR, 1180, 330, a)
    txt(fr, 'con metano e hidrocarburos', reg(40), HUESO, 1180, 440, ss((t - 205.0) / 0.8))
    return fr


# ---- sistema solar en perspectiva (A2): planetas con relieve, trayectoria con resplandor
VISTA = Vista(960, 440)
ORB = [64, 98, 140, 182, 290, 410, 510, 575]
NOM = ['mercurio', 'venus', 'tierra', 'marte', 'jupiter', 'saturno', 'urano', 'neptuno']
ANG = {'mercurio': 40, 'venus': 300, 'tierra': 205, 'marte': 118, 'jupiter': 112, 'saturno': 28, 'urano': 335, 'neptuno': 248}
RAD = {'mercurio': 6, 'venus': 10, 'tierra': 12, 'marte': 8, 'jupiter': 28, 'saturno': 21, 'urano': 15, 'neptuno': 14}


def _pos(n):
    return VISTA.planeta(ORB[NOM.index(n)], ANG[n])


def sistema(fr, t, a_orb=1.0, a_pl=1.0, atenuar=()):
    cap = capa_orbitas(VISTA, ORB)
    fr.paste(Image.new('RGB', (W, H), HUESO), (0, 0), cap.point(lambda v: int(v * a_orb)))
    items = sorted((VISTA.p(*_pos(n))[1], n, VISTA.p(*_pos(n))[0]) for n in NOM)
    sol = False
    for sy, n, sx in items:
        if not sol and sy >= VISTA.cy:
            dibujar_planeta(fr, 'sol', VISTA.cx, VISTA.cy, 44, (1, 0), a_pl)
            sol = True
        dx, dy = VISTA.cx - sx, VISTA.cy - sy
        nr = max(1.0, math.hypot(dx, dy))
        dibujar_planeta(fr, n, sx, sy, RAD[n], (dx / nr, dy / nr), a_pl * (0.45 if n in atenuar else 1.0), fase=t * 0.03)
    if not sol:
        dibujar_planeta(fr, 'sol', VISTA.cx, VISTA.cy, 44, (1, 0), a_pl)


def _bez3(p0, c, p2, n=70):
    return [((1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * c[0] + s * s * p2[0], (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * c[1] + s * s * p2[1], 0.0) for s in [i / n for i in range(n + 1)]]


def _trayectoria3d():
    E, J, S = _pos('tierra'), _pos('jupiter'), _pos('saturno')
    cE = ((E[0] + J[0]) / 2 * 1.5, (E[1] + J[1]) / 2 * 1.5)
    cJ = ((J[0] + S[0]) / 2 * 1.5, (J[1] + S[1]) / 2 * 1.5)
    plano = _bez3(E, cE, J) + _bez3(J, cJ, S)[1:]
    nS = math.hypot(S[0], S[1])
    d = (S[0] / nS, S[1] / nS)
    a = math.radians(35)
    fuera = [(S[0] + d[0] * s * math.cos(a), S[1] + d[1] * s * math.cos(a), s * math.sin(a)) for s in range(0, 296, 8)]
    return plano, fuera


PLANO, FUERA = _trayectoria3d()


def dibujar_trayecto(fr, pts3, n, color=AMBAR, a=1.0, sombra=False):
    pts = [VISTA.p(*q) for q in pts3[:n + 1]]
    if len(pts) > 1:
        linea_glow(fr, pts, color, 4, a)
        if sombra:
            pares = []
            for i in range(0, len(pts3[:n + 1]), 3):
                q = pts3[i]
                pares.append((VISTA.p(q[0], q[1], 0), VISTA.p(*q)))
            trazo.lineas(fr, pares, color, 1, 0.30 * a)
            linea_glow(fr, [VISTA.p(q[0], q[1], 0) for q in pts3[:n + 1]], color, 2, 0.30 * a)
    return pts[-1] if pts else None


def cabeza_sonda(fr, x, y, esc=0.34, a=1.0):
    punto(fr, x, y, 7, AMBAR, a, 5.0)
    pegar_icono(fr, 'sonda', x + 8, y - 22, esc, a)


def a2n(t, ini):
    """A2 · Trayectoria (parte inicial): el sistema solar en perspectiva, con planetas reales."""
    u = t - ini
    fr = base(t)
    sistema(fr, t, ss(u / 1.6), ss((u - 0.6) / 1.6))
    prog = ss((u - 2.4) / 8.6)
    n = int(prog * (len(PLANO) - 1))
    if n > 1:
        cab = dibujar_trayecto(fr, PLANO, n)
        cabeza_sonda(fr, *cab)
    E, J, S = VISTA.p(*_pos('tierra')), VISTA.p(*_pos('jupiter')), VISTA.p(*_pos('saturno'))
    etq(fr, 'Tierra', neg(28), HUESO, E[0] - 24, E[1] - 4, ss((u - 1.4) / 0.8), 'r', 'm')
    etq(fr, 'Júpiter', neg(28), HUESO, J[0] - 42, J[1] - 4, ss((n / len(PLANO) - 0.46) / 0.05), 'r', 'm')
    etq(fr, 'Saturno', neg(28), HUESO, S[0] + 42, S[1] + 2, ss((n / len(PLANO) - 0.9) / 0.05), 'l', 'm')
    etiqueta_esquema(fr)
    return fr


def esc_maniobra(t):
    """Después de Saturno: la nave sale del plano de los planetas (≈ 35° al norte)."""
    fr = base(t)
    sistema(fr, t, 1.0, 1.0, atenuar=('urano', 'neptuno'))
    dibujar_trayecto(fr, PLANO, len(PLANO) - 1, AMBAR, 0.55)
    S = VISTA.p(*_pos('saturno'))
    pr2 = ss((t - 222.5) / 9.5)
    n2 = int(pr2 * (len(FUERA) - 1))
    if n2 > 0:
        cab = dibujar_trayecto(fr, FUERA, n2, AMBAR, 1.0, sombra=True)
        cabeza_sonda(fr, *cab)
    else:
        cabeza_sonda(fr, *S)
    etq(fr, 'Saturno', neg(28), HUESO, S[0] + 40, S[1] + 6, 0.95, 'l', 'm')
    a35 = ss((t - 227.3) / 0.8)
    if a35 > 0 and n2 > 4:
        etq(fr, '≈ 35° fuera del plano', blk(44), AMBAR, 1340, 215, a35, 'r', 'm')
        etq(fr, 'hacia el norte', reg(30), HUESO, 1340, 277, a35, 'r', 'm')
    U, N = VISTA.p(*_pos('urano')), VISTA.p(*_pos('neptuno'))
    a_u = ss((t - 229.22) / 0.8)
    etq(fr, 'Urano · Voyager 2, 1986', reg(26), HUESO, U[0] + 30, U[1] + 4, a_u, 'l', 'm')
    etq(fr, 'Neptuno · Voyager 2, 1989', reg(26), HUESO, N[0] + 30, N[1] + 4, a_u, 'l', 'm')
    a_e = ss((t - 235.9) / 0.8)
    if n2 > 0:
        fin = VISTA.p(*FUERA[-1])
        txt_glow(fr, 'espacio interestelar', blk(46), AMBAR, fin[0] - 50, fin[1] - 12, a_e, 'r', 'm')
    etiqueta_esquema(fr)
    return fr


def esc_pbd(t):
    pos_tierra = (0.759, 0.560)   # el punto, medido en la imagen de 453×614
    if 273.43 <= t < 293.31 + 0.9:
        fr = foto(t, 273.43, 293.31, 'M08-PIA00451.jpg', 440, 480, 960, 350, 'Mosaico de 1990 · seis planetas visibles', oscuro=0.9, fondo=False)
        return fr
    fr = fondo_borroso('M07-PIA00452.jpg', 0.86, t=t)
    h = lerp(380, 620, ss((t - 241.38) / 18.0)) if t < 260 else lerp(620, 650, ss((t - 260) / 50.0))
    x0, y0, x1, y1 = pegar_img(fr, imagen('M07-PIA00452.jpg'), 960, 335, h * 0.95)
    if t >= 259.99:
        px, py = x0 + pos_tierra[0] * (x1 - x0), y0 + pos_tierra[1] * (y1 - y0)
        a = ss((t - 267.6) / 0.6) * (1 - ss((t - 273.3) / 0.8))
        anillo(fr, px, py, 36 + 3 * math.sin(t * 5), AMBAR, a)
        txt(fr, 'la Tierra', neg(32), AMBAR, px + 56, py - 18, a)
    txt(fr, 'Pale Blue Dot · 14-feb-1990', reg(26), HUESO, 960, y1 + 12, 0.9, 'm')
    return fr


def a1n(t):
    """A1 · Distancia (0:00–0:43), con el estilo espacial nuevo."""
    fr = base(t)
    ex, ey, px, py = 260, 450, 1660, 450
    prog = ss((t - 0.6) / 20.0)
    salida = 1 - ss((t - 29.0) / 5.0)
    x = lerp(ex, px, prog)
    if prog > 0 and salida > 0:
        linea_glow(fr, [(ex, ey), (x, py)], HUESO, 2, 0.55 * salida)
        trazo.lineas(fr, [((lerp(ex, px, i / 14), ey - 9), (lerp(ex, px, i / 14), ey + 9)) for i in range(0, 15) if lerp(ex, px, i / 14) <= x], HUESO, 2, 0.30 * salida)
    dibujar_planeta(fr, 'tierra', ex, ey, 26, (1, 0), salida, fase=t * 0.04)
    txt(fr, 'Tierra', neg(30), HUESO, ex, ey + 50, 0.9 * salida * ss((t - 0.4) / 1.0), 'm')
    pulso = 1 + 0.12 * math.sin(t * 3.2)
    if t < 29.0:
        punto(fr, x, py, 9 * pulso, AMBAR, 1.0, 5.0)
    else:
        u = ss((t - 29.0) / 8.0)
        cx, cy = lerp(px, 960, u), lerp(py, 450, u)
        punto(fr, cx, cy, 9 * pulso, AMBAR, 1.0, 5.0)
        txt(fr, 'Voyager 1', neg(34), HUESO, cx, cy + 54, 0.9 * ss((t - 30.0) / 1.2), 'm')
    n = 25900 * prog
    cifra = '≈ {:,} millones de km'.format(int(round(n / 100.0) * 100) if prog < 1 else 25900).replace(',', ' ')
    txt_glow(fr, cifra, blk(92), AMBAR, 960, 210, ss((t - 0.5) / 0.8) * salida, 'm')
    txt_glow(fr, '= 1 día luz', blk(70), HUESO, 960, 318, ss((t - 22.6) / 0.8) * salida, 'm')
    if 16.7 <= t <= 19.9:
        q = ss((t - 16.7) / 3.0)
        for k in range(10):
            qq = max(0, q - k * 0.012)
            punto(fr, lerp(ex, px, qq), ey, 5, HUESO, 0.5 * (1 - k / 10), 2.4)
        punto(fr, lerp(ex, px, q), ey, 7, HUESO, 1.0, 3.8)
    if 16.6 <= t < 29.0:
        horas = 23 * ss((t - 16.7) / 3.0)
        etq(fr, 'Una orden de radio: {:.0f} h'.format(horas), neg(42), HUESO, 960, 520, aparecer(t, 16.6, 28.0, 0.5) * salida, 'm')
    if 20.6 < t < 31:
        r = 24 + 6 * math.sin(t * 4)
        pegar(fr, brillo(int(r * 2.4), AMBAR), px, py, 0.55 * aparecer(t, 20.6, 31, 0.8), 'm', 'm')
    return fr


# ---- heliosfera (A3)
SOL = (430, 540)
HP = (760, 540, 560, 380)       # centro x, y, semieje x, y de la heliopausa
TS = (700, 540, 330, 250)       # choque de terminación


def elipse(fr, e, color, a, ancho=3):
    cx, cy, rx, ry = e
    pts = [(cx + rx * math.cos(2 * math.pi * i / 220), cy + ry * math.sin(2 * math.pi * i / 220)) for i in range(221)]
    linea_glow(fr, pts, color, ancho, a, cache=True)


def corte_hp(p0, p1):
    for i in range(0, 1001):
        s = i / 1000
        x, y = lerp(p0[0], p1[0], s), lerp(p0[1], p1[1], s)
        if ((x - HP[0]) / HP[2]) ** 2 + ((y - HP[1]) / HP[3]) ** 2 >= 1:
            return x, y
    return p1


V2_FIN = (1800, 790)
V2_CORTE = corte_hp(SOL, V2_FIN)


def pos_v1(t):
    if t < 328:
        return SOL[0] + 30 * ss((t - 322) / 6), SOL[1]
    if t < 335.2:
        return lerp(SOL[0] + 30, TS[0] + TS[2], ss((t - 328) / 7.2)), SOL[1]
    if t < 366.5:
        return TS[0] + TS[2], SOL[1]
    if t < 394.4:
        return lerp(TS[0] + TS[2], HP[0] + HP[2], ss((t - 366.5) / 27.9)), SOL[1]
    return lerp(HP[0] + HP[2], 1720, ss((t - 394.4) / 60.0)), SOL[1]


def esc_helio(t):
    fr = base(t)
    E = []          # las etiquetas se dibujan al final: ninguna línea queda por encima de un texto

    def et(*args, **kw):
        E.append((args, kw))
    # viento solar: partículas que salen del Sol
    a_v = ss((t - 312.0) / 1.2)
    dibujar_planeta(fr, 'sol', SOL[0], SOL[1], 26, (1, 0))
    part = []
    for k in range(18):
        ang = k * 2 * math.pi / 18
        for m in range(5):
            r = ((t * 70 + m * 80 + k * 17) % 400)
            if r < 40:
                continue
            x, y = SOL[0] + r * math.cos(ang), SOL[1] + r * math.sin(ang)
            if ((x - HP[0]) / HP[2]) ** 2 + ((y - HP[1]) / HP[3]) ** 2 < 1:
                part.append((x, y))
    trazo.puntos(fr, part, 2.2, (255, 214, 120), 0.6 * a_v)
    et(fr, 'Viento solar', neg(34), HUESO, 520, 190, ss((t - 313.2) / 0.8) * (1 - ss((t - 322) / 1.0)), 'm')
    # heliopausa y medio interestelar
    a_hp = ss((t - 318.3) / 1.5)
    elipse(fr, HP, (150, 180, 255), a_hp * 0.8, 3)
    et(fr, 'Heliosfera', neg(40), HUESO, 560, 110, ss((t - 318.5) / 0.8))
    a_h2 = ss((t - 321.8) / 0.8)
    et(fr, 'Heliopausa', neg(34), (150, 180, 255), HP[0] + HP[2] + 30, HP[1] - 190, a_h2)
    trazo.linea(fr, [(HP[0] + HP[2] + 26, HP[1] - 150), (HP[0] + HP[2] + 2, HP[1] - 24)], (150, 180, 255), 2, a_h2, ss=3)
    et(fr, 'Espacio interestelar', neg(40), HUESO, 1590, 250, ss((t - 324.2) / 0.8), 'm')
    a_ts = ss((t - 327.7) / 1.2)
    elipse(fr, TS, AMBAR, a_ts * 0.8, 3)
    et(fr, 'Choque de terminación', neg(30), AMBAR, TS[0] + 20, TS[1] + TS[3] + 22, a_ts, 'm')
    # Voyager 1
    if t >= 322:
        x, y = pos_v1(t)
        a = ss((t - 322) / 1.0)
        punto(fr, x, y, 9, AMBAR, a, 4.2)
        et(fr, 'Voyager 1', neg(28), HUESO, x, y - 74, a, 'm')
    if 335.2 <= t < 345:
        et(fr, '16-dic-2004', blk(40), AMBAR, TS[0] + TS[2], TS[1] + 40, aparecer(t, 335.2, 345, 0.5), 'm')
    # el instrumento de plasma
    ap = aparecer(t, 344.2, 354.5, 0.6)
    if ap > 0:
        et(fr, 'Instrumento de plasma de Voyager 1:', reg(32), HUESO, 1610, 640, ap, 'm')
        et(fr, 'dejó de funcionar en 1980', blk(46), ROJO, 1610, 686, ap, 'm')
    # 2013: la vibración del plasma
    for a0, a1, s1, s2, c in ((371.5, 382.4, '9-abr-2013', 'el instrumento de ondas de plasma capta una vibración', AMBAR),
                              (382.7, 390.3, 'más de 40 veces más denso', 'que el plasma medido por Voyager 2 dentro de la burbuja', AMBAR),
                              (390.6, 394.3, 'No era plasma del Sol: era plasma interestelar', '', HUESO)):
        aa = aparecer(t, a0, a1, 0.5)
        if aa > 0:
            yy = 620
            for ln in envolver(s1, 24):
                et(fr, ln, blk(46), c, 1610, yy, aa, 'm')
                yy += 56
            for ln in (envolver(s2, 34) if s2 else []):
                et(fr, ln, reg(30), HUESO, 1610, yy + 6, aa, 'm')
                yy += 38
    # 25-ago-2012
    if 394.4 <= t < 402.7:
        et(fr, '25-ago-2012', blk(60), AMBAR, 1610, 620, aparecer(t, 394.4, 402.7, 0.5), 'm')
    # Voyager 2
    if t >= 402.7:
        u = ss((t - 402.7) / 8.0)
        x, y = lerp(SOL[0], V2_CORTE[0], u), lerp(SOL[1], V2_CORTE[1], u)
        if t > 409.95:
            x, y = lerp(V2_CORTE[0], 1700, ss((t - 409.95) / 25)), lerp(V2_CORTE[1], 790 + 0, ss((t - 409.95) / 25))
        linea(fr, SOL, (x, y), HUESO, 2, 0.35)
        punto(fr, x, y, 8, VERDE, 1.0, 3.6)
        et(fr, 'Voyager 2', neg(28), VERDE, x, y + 24, 1.0, 'm')
        if 409.95 <= t < 421.9:
            et(fr, '5-nov-2018', blk(50), VERDE, 1610, 620, aparecer(t, 409.95, 421.9, 0.5), 'm')
    for args_, kw_ in E:
        etq(*args_, **kw_)
    etiqueta_esquema(fr)
    return fr


def esc_zumbido(t):
    fr = base(t)
    cy = 610
    a = ss((t - 423.7) / 1.5)
    pts = []
    for i in range(0, W + 1, 6):
        x = i
        amp = 38 * math.sin(x / 55.0 - t * 4.0) * (0.55 + 0.45 * math.sin(x / 420.0 + t))
        # erupciones solares: picos esporádicos
        if 436.0 <= t <= 441.2:
            for pc in (940 + 140 * (t - 436), 300 + 160 * (t - 436)):
                amp += 190 * math.exp(-((x - pc) / 40.0) ** 2) * math.sin((x - pc) / 9.0 - t * 14)
        pts.append((x, cy + amp))
    if a > 0:
        linea_glow(fr, pts, AMBAR, 4, a)
    txt(fr, 'Ondas de plasma · Voyager 1', reg(32), GRIS, W // 2, 220, a, 'm')
    txt(fr, 'un zumbido débil y constante del gas interestelar', blk(46), HUESO, W // 2, 300, aparecer(t, 424.0, 436.0, 0.6), 'm')
    txt(fr, 'antes solo se medía cuando una erupción solar lo agitaba', reg(40), HUESO, W // 2, 300, aparecer(t, 436.0, 441.2, 0.5), 'm')
    txt(fr, 'ahora: la densidad del medio, día tras día', blk(44), AMBAR, W // 2, 300, aparecer(t, 441.4, 449.5, 0.6), 'm')
    return fr


def esc_enlace(t):
    fr = base(t)
    ex, ey, sx, sy = 420, 520, 1500, 520
    if t < 472.8:
        a_ic = ss((t - 450.3) / 0.8)
        pegar_icono(fr, 'antena', ex, ey, 1.25, a_ic)
        pegar_icono(fr, 'sonda', sx, sy, 1.25, a_ic)
        txt(fr, 'Tierra', neg(30), HUESO, ex, ey + 140, a_ic, 'm')
        txt(fr, 'Voyager 1', neg(30), HUESO, sx, sy + 120, a_ic, 'm')
        txt(fr, 'antena de 3,7 m', reg(34), AMBAR, sx, sy - 150, aparecer(t, 450.5, 458.5, 0.5), 'm')
        linea(fr, (ex + 150, ey), (sx - 150, sy), HUESO, 2, 0.2)
        if t < 466.2:
            a_b = ss((t - 453.0) / 0.8)
            bits(fr, sx - 150, ex + 150, ey, t, 70, AMBAR, a_b)
            txt(fr, 'bajada: 160 bits por segundo', blk(42), AMBAR, W // 2, 380, a_b, 'm')
        if 459.1 <= t < 466.0:
            a = aparecer(t, 459.1, 466.0, 0.5)
            txt(fr, '3 MB × 8 ÷ 160 bit/s ≈ 150 000 s', blk(52), HUESO, W // 2, 250, a, 'm')
            txt(fr, '≈ 42 horas para una foto de móvil', blk(52), AMBAR, W // 2, 322, a, 'm')
        if 466.2 <= t < 472.8:
            a = ss((t - 466.2) / 0.8)
            bits(fr, ex + 150, sx - 150, ey, t, 22, HUESO, a, 8)
            txt(fr, 'subida (órdenes): 16 bits por segundo', blk(42), HUESO, W // 2, 380, a, 'm')
    else:
        a = ss((t - 472.9) / 0.8)
        # reloj digital frente a la señal de Voyager 1
        x0, y0 = 480, 400
        trazo.rrect(fr, (x0 - 190, y0 - 90, x0 + 190, y0 + 90), 22, HUESO, 5, a)
        txt(fr, '12:45', blk(96), HUESO, x0, y0, a, 'm', 'm')
        txt(fr, 'lo que necesita un reloj digital', reg(34), HUESO, x0, y0 + 140, a, 'm')
        punto(fr, 1440, y0, 4, AMBAR, a, 6.0)
        txt(fr, 'lo que llega de Voyager 1', reg(34), HUESO, 1440, y0 + 140, a, 'm')
        txt(fr, '20 mil millones de veces menor', blk(66), AMBAR, W // 2, 190, a, 'm')
        txt(fr, '≈', blk(90), HUESO, W // 2, y0, a, 'm', 'm')
    return fr


def esc_mapa(t):
    """Red de Espacio Profundo: la Tierra gira y, en cada momento, la estación que ve a Voyager 1 apunta hacia ella."""
    fr = base(t)
    a = ss((t - 483.6) / 1.0)
    titulo(fr, 'COMUNICACIONES', 'Red de Espacio Profundo de la NASA', W // 2, 56, a, 'm', 50)
    etq(fr, 'tres complejos, casi equidistantes: siempre hay uno que ve a la nave', reg(32), HUESO, W // 2, 176, ss((t - 492.9) / 0.8), 'm')
    cx, cy, R = 640, 600, 320
    fi = math.radians(-20 + 20.0 * max(0.0, t - 484.0))              # la Tierra, acelerada (≈ 20° por segundo)
    ga = ss((t - 483.8) / 1.0)
    globo.dibujar_globo(fr, cx, cy, R, fi, ga)
    d = dsn.direccion_sonda()
    est = dsn.estado(fi)
    t_pin = {'Canberra': 485.3, 'Madrid': 486.7, 'Goldstone': 488.5}
    # rayos (todos paralelos: la sonda está tan lejos que su dirección es la misma desde las tres estaciones)
    for nombre, rx, ry, vis, act, el in est:
        pa = ss((t - t_pin[nombre]) / 0.8)
        if not vis or pa <= 0:
            continue
        x, y = globo.punto_pantalla(cx, cy, R, rx, ry)
        z = math.sqrt(max(0.0, 1 - rx * rx - ry * ry))
        vi = clamp((z - 0.22) / 0.2) * pa
        if act:
            L = 760
            linea_glow(fr, [(x, y), (x + d[0] * L, y + d[1] * L)], AMBAR, 3, 0.9 * vi)
            for k in range(6):                                          # pulsos de la señal en camino
                s = ((t * 150 + k * L / 6) % L)
                punto(fr, x + d[0] * s, y + d[1] * s, 4, HUESO, 0.8 * vi * (1 - s / L), 2.4)
        col = AMBAR if act else GRIS
        anillo(fr, x, y, 11, col, 0.95 * vi, 3)
        punto(fr, x, y, 4, col, vi, 2.2)
        nom = {'Goldstone': 'Goldstone', 'Madrid': 'Madrid', 'Canberra': 'Canberra'}[nombre]
        ox = -20 if rx < 0 else 20
        etq(fr, nom, neg(28), HUESO if act else GRIS, x + ox, y - 36, 0.95 * vi, 'r' if rx < 0 else 'l', 'm')
    # la sonda, muy lejos, en la dirección de los rayos
    sa = ss((t - 486.0) / 1.0)
    sx, sy = cx + d[0] * 1030, cy + d[1] * 1030
    if sa > 0:
        pegar_icono(fr, 'sonda', sx, sy, 0.62, sa)
        etq(fr, 'Voyager 1', neg(30), HUESO, sx, sy + 70, sa, 'm')
        etq(fr, '≈ 25 900 millones de km', reg(24), GRIS, sx, sy + 118, sa * 0.9, 'm')
    # estado de cada antena
    x0 = 1290
    for i, (nombre, rx, ry, vis, act, el) in enumerate(sorted(est, key=lambda e: ['Goldstone', 'Madrid', 'Canberra'].index(e[0]))):
        y0 = 700 + i * 112
        pa = ease_out((t - (t_pin[nombre] + 0.4)) / 0.8)
        if pa <= 0.02:
            continue
        col = AMBAR if act else GRIS
        caja(fr, x0, y0, 540, 96, col if act else (96, 108, 140), 1.0, pa, c=14, oscuro=0.6)
        tx = clamp((pa - 0.35) / 0.6)
        if tx <= 0:
            continue
        punto(fr, x0 + 40, y0 + 48, 11, col, tx, 2.6 if act else 1.0)
        pegar(fr, sprite_texto(nombre, neg(30), HUESO if act else GRIS), x0 + 74, y0 + 14, tx)
        pegar(fr, sprite_texto('ve a la nave · apunta hacia ella' if act else 'sin contacto: la nave está bajo el horizonte', sl(23), AMBAR if act else GRIS), x0 + 74, y0 + 54, tx)
    etiqueta_esquema(fr, 'ESQUEMA · POSICIÓN APROXIMADA')
    return fr


def esc_antenas(t):
    fr = base(t)
    a = ss((t - 502.5) / 0.6)
    x0, y0, x1, y1 = pegar_img(fr, imagen('M09-dsn-goldstone-marte.png'), 560, 430, 560, a)
    txt(fr, 'Goldstone (California) · antena de 70 m', reg(26), HUESO, 560, y1 + 12, 0.9 * a, 'm')
    txt(fr, 'NASA', reg(22), GRIS, 560, y1 + 46, 0.9 * a, 'm')
    x0, y0, x1, y1 = pegar_img(fr, imagen('M09-dsn-canberra.jpg'), 1360, 430, 380, a)
    txt(fr, 'Canberra (Australia)', reg(26), HUESO, 1360, y1 + 12, 0.9 * a, 'm')
    txt(fr, 'NASA/CSIRO/Canberra Deep Space Communication Complex', reg(22), GRIS, 1360, y1 + 46, 0.9 * a, 'm')
    return fr


def esc_idavuelta(t):
    fr = base(t)
    ex, sx, y = 420, 1500, 480
    pegar_icono(fr, 'antena', ex, y, 1.0)
    pegar_icono(fr, 'sonda', sx, y, 1.0)
    u1 = ss((t - 509.5) / 3.0)
    u2 = ss((t - 513.0) / 3.0)
    linea(fr, (ex + 130, y - 22), (lerp(ex + 130, sx - 130, u1), y - 22), AMBAR, 4)
    linea(fr, (sx - 130, y + 22), (lerp(sx - 130, ex + 130, u2), y + 22), HUESO, 4)
    txt(fr, 'orden: ≈ 23 h', blk(44), AMBAR, W // 2, y - 120, ss((t - 509.5) / 0.6))
    txt(fr, 'respuesta: ≈ 23 h', blk(44), HUESO, W // 2, y + 70, ss((t - 513.0) / 0.6))
    a = ss((t - 516.2) / 0.8)
    txt(fr, '≈ 46 horas de ida y vuelta', blk(70), AMBAR, W // 2, 190, a, 'm')
    txt(fr, 'Aquí no existe el «reintentar»', blk(54), HUESO, W // 2, 770 - 120, ss((t - 518.95) / 0.8), 'm')
    return fr


def cilindro_rtg(w, h, pulso=1.0):
    """Generador de plutonio como cilindro metálico incandescente: luz lateral, aletas y brillo interior."""
    xx = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    lat = np.cos(xx * math.pi / 2 * 0.95) ** 0.8 * np.ones((h, 1), np.float32)          # (h, w): 1 en el centro, 0 en los bordes
    luz = np.clip(0.30 + 0.80 * lat + 0.22 * np.clip(-xx, 0, 1), 0, 1.35)
    caliente = np.array([255, 160, 74], np.float32)
    frio = np.array([86, 34, 20], np.float32)
    mix = np.clip(0.30 + 0.70 * lat, 0, 1)[..., None]
    col = (frio * (1 - mix) + caliente * mix) * luz[..., None] * pulso
    fr_ = (yy * 7) % 1.0
    ranura = np.clip(1 - np.abs(fr_ - 0.5) / 0.07, 0, 1) * np.ones((1, w), np.float32)    # aletas de enfriamiento
    col *= (1 - 0.35 * ranura)[..., None]
    col += np.array([60, 36, 18], np.float32) * ((np.abs(fr_ - 0.5) < 0.06) * np.ones((1, w), np.float32) * lat)[..., None]
    casq = (np.clip(1 - yy / 0.05, 0, 1) + np.clip((yy - 0.95) / 0.05, 0, 1)) * np.ones((1, w), np.float32)   # tapas oscuras
    col *= (1 - 0.55 * casq)[..., None]
    return Image.fromarray(np.clip(col, 0, 255).astype('uint8'))


def pegar_capsula(fr, im, cx, cy, a):
    """Cápsula vertical con relleno de degradado (el generador de plutonio)."""
    w, h = im.size
    m = Image.new('L', (w * 3, h * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 3 - 1, h * 3 - 1), 60 * 3, fill=255)
    m = m.resize((w, h), Image.LANCZOS)
    fr.paste(im, (int(cx - w / 2), int(cy - h / 2)), m.point(lambda v: int(v * a)) if a < 1 else m)
    trazo.rrect(fr, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 60, HUESO, 2, 0.55 * a)


def esc_rtg(t):
    fr = base(t)
    # plutonio → calor → electricidad
    a = ss((t - 526.0) / 0.8)
    cx, cy = 480, 470
    pegar(fr, brillo(190, (255, 120, 60)), cx, cy, 0.5 * a * (0.8 + 0.2 * math.sin(t * 4)), 'm', 'm')
    if a > 0:
        pegar_capsula(fr, cilindro_rtg(150, 270, 0.92 + 0.08 * math.sin(t * 3.2)), cx, cy, a)
    txt(fr, 'plutonio-238', neg(34), HUESO, cx, cy + 170, a, 'm')
    txt(fr, 'decae y da calor', sl(32), GRIS, cx, cy + 212, ss((t - 531.2) / 0.8), 'm')
    ac = ss((t - 532.5) / 0.8)
    for k in range(3):
        xx = cx + 140 + ((t * 90 + k * 60) % 180)
        txt(fr, '›', blk(60), (255, 150, 90), xx, cy - 8, ac * (1 - ((xx - cx - 140) / 180)), 'm', 'm')
    ex = cx + 420
    icono_hex(fr, ex, cy, 78, AMBAR, ac, '')
    if ac > 0:
        trazo.poli(fr, [(ex + 8, cy - 46), (ex - 24, cy + 6), (ex + 2, cy + 6), (ex - 10, cy + 48), (ex + 28, cy - 8), (ex + 4, cy - 8)], AMBAR, ac)
    txt(fr, 'electricidad', neg(34), AMBAR, ex, cy + 130, ac, 'm')
    p1 = ease_out((t - 533.0) / 0.8)
    caja(fr, 1080, 250, 740, 340, AMBAR, 1.0, p1, c=22, oscuro=0.6)
    txt(fr, '3 generadores en un brazo', sl(34), HUESO, 1450, 290, ss((t - 533.4) / 0.8), 'm')
    txt_glow(fr, '158 W', blk(110), AMBAR, 1450, 350, ss((t - 537.5) / 0.8), 'm')
    txt(fr, 'cada uno, al lanzarse (1977)', sl(36), HUESO, 1450, 495, ss((t - 537.9) / 0.8), 'm')
    p2 = ease_out((t - 541.9) / 0.8)
    caja(fr, 1080, 620, 740, 190, ROJO, 1.0, p2, c=22, oscuro=0.6)
    txt_glow(fr, '−4 W por año', blk(72), ROJO, 1450, 650, ss((t - 542.3) / 0.8), 'm')
    txt(fr, 'se apagan calentadores e instrumentos', sl(32), HUESO, 1450, 748, ss((t - 545.9) / 0.8), 'm')
    return fr


def diagrama():
    """Diagrama oficial de la NASA (fondo blanco) convertido a tema oscuro: el blanco pasa a transparente."""
    k = ('diag',)
    if k not in _cache:
        s = 1.0
        im = Image.open(os.path.join(ORIG, 'M12-diagrama-instrumentos.jpg')).convert('RGB')
        im = im.resize((int(640 * s), int(482 * s)), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32)
        mn, mx, lum = a.min(2), a.max(2), a.mean(2)
        gris = (mx - mn) < 40
        alfa = np.where(gris, np.clip((255 - lum) / 255 * 1.6, 0, 1), np.clip((255 - mn) / 255 * 1.7, 0, 1))
        col = np.where(gris[..., None], np.array(HUESO, np.float32), a)
        _cache[k] = (Image.fromarray(col.astype('uint8')), Image.fromarray((alfa * 255).astype('uint8')))
    return _cache[k]


DX0, DY0, DS = 130, 206, 1.0


def _dp(x, y):
    return DX0 + x * DS, DY0 + y * DS


def esc_instrumentos(t):
    """Dónde está cada instrumento en la nave (diagrama oficial de la NASA)."""
    fr = base(t)
    p = ease_out((t - 553.2) / 0.9)
    titulo(fr, 'LA SONDA POR DENTRO', 'Instrumentos científicos de Voyager 1', 96, 100, ss((t - 553.4) / 0.7), 'l', 42)
    caja(fr, DX0 - 26, DY0 - 16, 640 * DS + 52, 482 * DS + 32, AMBAR, 1.0, p, c=22, oscuro=0.45)
    rgb, m = diagrama()
    fr.paste(rgb, (DX0, DY0), m.point(lambda v: int(v * clamp(p * 1.6 - 0.3) * 0.95)))
    ROJ, VER = ROJO, VERDE
    # 1 · LECP (apagado): anillo rojo que parpadea sobre el brazo con los instrumentos
    a1 = ss((t - 558.0) / 0.7)
    if a1 > 0:
        x, y = _dp(495, 152)
        r = 22 + 4 * math.sin(t * 6)
        anillo(fr, x, y, r, ROJ, a1)
        punto(fr, x, y, 5, ROJ, a1, 2.0)
    # 2 · ondas de plasma: las dos antenas largas en «V»
    a2 = ss((t - 565.2) / 0.7)
    if a2 > 0:
        linea_glow(fr, [_dp(0, 433), _dp(275, 322)], VER, 3, a2)
        linea_glow(fr, [_dp(352, 380), _dp(378, 482)], VER, 3, a2)
        for q in ((36, 410), (368, 442)):
            x, y = _dp(*q)
            anillo(fr, x, y, 20, VER, a2, 3)
    # 3 · magnetómetro: brazo largo
    a3 = ss((t - 566.5) / 0.7)
    if a3 > 0:
        linea_glow(fr, [_dp(0, 165), _dp(298, 282)], VER, 3, a3)
        x, y = _dp(52, 197)
        anillo(fr, x, y, 20, VER, a3, 3)
    tarjetas = (('1', 'Partículas cargadas de baja energía (LECP)', 'apagado el 17-abr-2026, para ahorrar energía', ROJ, 558.0, 'APAGADO'),
                ('2', 'Ondas de plasma', 'usa las dos antenas largas en «V»', VER, 565.2, 'ACTIVO'),
                ('3', 'Magnetómetro', 'en el brazo largo', VER, 566.5, 'ACTIVO'))
    for i, (n, nombre, estado, c, t0, chip) in enumerate(tarjetas):
        p2 = ease_out((t - t0) / 0.7)
        if p2 < 0.02:
            continue
        y0 = 206 + i * 176
        caja(fr, 940, y0, 880, 150, c, 1.0, p2, c=18, oscuro=0.6)
        tx = clamp((p2 - 0.3) / 0.6)
        if tx <= 0:
            continue
        anillo_arco(fr, 1004, y0 + 75, 28, c, 1.0, tx, 3, -90, 0.5)
        pegar(fr, sprite_texto(n, blk(30), c), 1004, y0 + 75, tx, 'm', 'm')
        pegar(fr, sprite_texto(nombre, neg(31), HUESO), 1060, y0 + 30, tx)
        pegar(fr, sprite_texto(estado, sl(27), c), 1060, y0 + 84, tx)
        pastilla(fr, chip, 1796, y0 + 112, c, tx, 'r')
        if i == 0:
            linea(fr, (1062, y0 + 30 + 24), (1062 + 619 * tx, y0 + 30 + 24), ROJO, 3, tx)
    return fr


def esc_chip(t):
    fr = base(t)
    y = 520
    la = ss((t - 571.4) / 0.8)
    linea_glow(fr, [(160, y), (1760, y)], HUESO, 2, 0.28 * la)
    puntos = ((300, '14-nov-2023', 'datos ilegibles', ROJO, 573.3), (780, '18-abr-2024', 'código reubicado y enviado', AMBAR, 597.2),
              (1180, '20-abr-2024', 'datos de estado', VERDE, 606.5), (1620, '22-may-2024', 'ciencia de dos instrumentos', VERDE, 611.0))
    for k, (x, f, d, c, t0) in enumerate(puntos):
        p = ease_out((t - t0) / 0.7)
        if p <= 0.01:
            continue
        arriba = k % 2 == 0
        cy0 = y - 250 if arriba else y + 70
        linea(fr, (x, (y - 70) if arriba else (y + 20)), (x, (y - 20) if arriba else (y + 70)), c, 2, 0.6 * p)
        anillo_arco(fr, x, y, 16, c, 1.0, p, 3, -90, 0.5)
        punto(fr, x, y, 6, c, p, 2.6)
        caja(fr, x - 230, cy0 + (0 if arriba else 0) + (70 if arriba else 0) * 0, 460, 130, c, 1.0, p, c=14, oscuro=0.6, barra=False)
        tx = clamp((p - 0.3) / 0.6)
        pegar(fr, sprite_texto(f, neg(38), c), x, cy0 + 18, tx, 'm')
        pegar(fr, sprite_texto(d, sl(29), HUESO), x, cy0 + 72, tx, 'm')
    a1 = ss((t - 586.3) / 0.8) * (1 - ss((t - 598) / 0.8))
    a2 = ss((t - 598.0) / 0.8)
    titulo(fr, 'EL PROBLEMA', 'Un solo chip de memoria dejó de funcionar', W // 2, 96, a1, 'm', 50, HUESO)
    titulo(fr, 'LA SOLUCIÓN', 'Dividir el código y reubicarlo en otras zonas de memoria', W // 2, 96, a2, 'm', 50, HUESO)
    return fr


def esc_frase(t):
    fr = base(t)
    titulo(fr, 'LO QUE NO SABEMOS', 'Una frase que se repite muchísimo', W // 2, 96, ss((t - 625.7) / 0.8), 'm', 50)
    p = ease_out((t - 628.8) / 0.9)
    caja(fr, 230, 330, 1460, 190, AMBAR, 1.0, p, c=24, oscuro=0.6)
    tx = clamp((p - 0.35) / 0.6)
    pegar(fr, sprite_texto('«Voyager 1 salió del Sistema Solar»', blk(66), HUESO), W // 2, 425, tx, 'm', 'm')
    k = ss((t - 634.2) / 0.6)
    if k > 0:
        linea_glow(fr, [(300, 425), (300 + 1320 * k, 425)], AMBAR, 5, 1.0)
    pastilla(fr, 'NO ES EXACTA', W // 2, 578, AMBAR, ss((t - 634.3) / 0.6), 'm')
    p2 = ease_out((t - 636.1) / 0.8)
    caja(fr, 380, 650, 1160, 130, VERDE, 1.0, p2, c=20, oscuro=0.6)
    tx2 = clamp((p2 - 0.35) / 0.6)
    pegar(fr, sprite_texto('Salió de la heliosfera', blk(58), HUESO), W // 2, 715, tx2, 'm', 'm')
    return fr


def esc_oort(t):
    fr = base(t)
    cx, cy = 700, 540
    a = ss((t - 639.7) / 1.0)
    for r, c, ancho in ((260, (150, 180, 255), 3), (470, (150, 180, 255), 3)):
        trazo.elipse(fr, (cx - r, cy - r, cx + r, cy + r), c, ancho, 0.7 * a, glow=0.5, cache=True)
    punto(fr, cx, cy, 10, (255, 214, 120), a, 3.0)
    trazo.elipse(fr, (cx - 34, cy - 34, cx + 34, cy + 34), AMBAR, 3, a, glow=0.6, cache=True)
    etq(fr, 'heliosfera', reg(28), HUESO, cx, cy + 50, a, 'm')
    etq(fr, 'Nube de Oort', blk(46), (150, 180, 255), cx, cy - 560 + 110, ss((t - 644.0) / 0.8), 'm')
    etq(fr, 'un enorme reservorio de cometas', reg(30), HUESO, cx, cy - 560 + 170, ss((t - 645.0) / 0.8), 'm')
    etq(fr, '≈ 1 000 UA', neg(30), GRIS, cx + 260, cy + 20, ss((t - 646.0) / 0.8), 'm')
    etq(fr, '≈ 100 000 UA', neg(30), GRIS, cx + 470, cy + 60, ss((t - 648.0) / 0.8), 'm')
    # Voyager 1 sale de la burbuja
    if t >= 640:
        u = ss((t - 640.0) / 16.0)
        d = 34 + (260 - 34) * u if t < 656 else 260 + (470 - 260) * ss((t - 660.0) / 8.0)
        punto(fr, cx + d, cy, 8, AMBAR, 1.0, 4.0)
        etq(fr, 'Voyager 1', neg(28), HUESO, cx + d, cy - 74, 1.0, 'm')
    etq(fr, '≈ 300 años', blk(64), AMBAR, 1560, 300, ss((t - 653.0) / 0.8), 'm')
    etq(fr, 'hasta su borde interior', reg(34), HUESO, 1560, 380, ss((t - 653.5) / 0.8), 'm')
    etq(fr, 'posiblemente ≈ 30 000', blk(50), AMBAR, 1560, 470, ss((t - 656.5) / 0.8), 'm')
    etq(fr, 'para cruzarla', reg(34), HUESO, 1560, 540, ss((t - 657.2) / 0.8), 'm')
    etq(fr, 'sin energía ni combustible:', blk(42), HUESO, 1560, 660, ss((t - 668.0) / 0.8), 'm')
    etq(fr, 'en silencio', blk(42), HUESO, 1560, 730, ss((t - 668.0) / 0.8), 'm')
    etiqueta_esquema(fr)
    return fr


def esc_niveles(t):
    fr = base(t)
    titulo(fr, 'LO QUE SE SABE Y LO QUE NO', '¿Qué sabemos de verdad sobre su futuro?', W // 2, 92, ss((t - 674.3) / 0.8), 'm', 50)
    filas = (('Comprobado', 'sus instrumentos miden el medio interestelar cerca del Sol', VERDE, 678.0, 'ok'),
             ('Probable', 'más tiempo de datos gracias al plan «Big Bang» (en Voyager 1, previsto en los próximos meses)', AMBAR, 687.9, 'prob'),
             ('Sin fecha', 'NASA no da una fecha de fin: busca mantener las dos sondas el mayor tiempo posible', HIELO, 703.4, 'sin'))
    for i, (n, dsc, c, t0, ic) in enumerate(filas):
        p = ease_out((t - t0) / 0.8)
        if p <= 0.01:
            continue
        y = 250 + i * 222
        caja(fr, 220, y, 1480, 190, c, 1.0, p, c=20, oscuro=0.6)
        tx = clamp((p - 0.35) / 0.55)
        if tx <= 0:
            continue
        cx, cy = 320, y + 95
        if ic == 'ok':
            icono_hex(fr, cx, cy, 34, c, tx, 'check', 3)
        elif ic == 'prob':
            anillo_arco(fr, cx, cy, 32, c, 0.66 * tx, tx, 5, -90, 0.25)
            punto(fr, cx, cy, 5, c, tx, 2.4)
        else:
            anillo_arco(fr, cx, cy, 32, c, 1.0, tx, 5, -90, 0.25, True)
        off = (1 - tx) * 16
        pegar(fr, sprite_texto(n, blk(46), c), 396 + off, y + 22, tx)
        for j, ln in enumerate(envolver(dsc, 80)[:2]):
            pegar(fr, sprite_texto(ln, sl(31), HUESO), 396 + off, y + 90 + j * 40, tx)
    return fr


def esc_disco(t):
    return foto(t, 715.49, 748.8, 'M10-PIA14113.jpg', 560, 600, 960, 360, 'Composición de la NASA: la sonda y el disco de oro')


def esc_estrella(t):
    fr = base(t)
    a = ss((t - 748.9) / 0.8)
    y = 470
    punto(fr, 300, y, 9, AMBAR, a, 4.0)
    txt(fr, 'Voyager 1', neg(30), HUESO, 300, y + 36, a, 'm')
    sx = 1560
    punto(fr, sx, y, 18, (255, 236, 190), a, 3.4)
    txt(fr, 'AC +79 3888', blk(40), HUESO, sx, y - 76, a, 'm')
    txt(fr, '(Gliese 445)', reg(30), GRIS, sx, y + 40, a, 'm')
    u = ss((t - 750.0) / 10.0)
    linea(fr, (300, y), (lerp(300, sx - 90, u), y), AMBAR, 3, a)
    punto(fr, lerp(300, sx - 90, u), y, 8, AMBAR, a, 4.0)
    txt(fr, 'pasará a 1,7 años luz', blk(64), AMBAR, W // 2, 250, ss((t - 751.5) / 0.8), 'm')
    txt(fr, 'en el año 40 272', blk(64), HUESO, W // 2, 330, ss((t - 753.0) / 0.8), 'm')
    etiqueta_esquema(fr)
    return fr


def esc_fuentes(t):
    fr = base(t)
    titulo(fr, 'REFERENCIAS', 'Fuentes', W // 2, 100, ss((t - 762.0) / 0.8), 'm', 56)
    nombres = ('NASA Science', 'NASA/JPL', 'NASA Space Place', 'NASA NTRS', 'NASA History Office', 'Universidad de Cornell · Nature Astronomy')
    for i, n in enumerate(nombres):
        t0 = 762.8 + i * 0.5
        p = ease_out((t - t0) / 0.6)
        if p <= 0.01:
            continue
        y = 262 + i * 76
        caja(fr, 560, y, 800, 60, AMBAR, 1.0, p, c=12, oscuro=0.6, barra=False)
        tx = clamp((p - 0.3) / 0.6)
        icono_hex(fr, 600, y + 30, 11, AMBAR, tx, 'check', 2)
        pegar(fr, sprite_texto(n, neg(30), HUESO), 636 + (1 - tx) * 12, y + 30, tx, 'l', 'm')
    pegar(fr, sprite_texto('Los enlaces están en la descripción', sl(34), GRIS), W // 2, 262 + 6 * 76 + 24, ss((t - 766.0) / 0.8), 'm')
    return fr


def esc_plano_sonda(t):
    return escena_imagen('M01-PIA26353.jpg', t, 616.25, 625.6, 1.2, 1.28, (0.55, 0.5), (0.5, 0.5), oscuro=0.25)


# ------------------------------------------------------------------ guion de escenas
def B(fn, k=0.32):
    return lambda t: bloom(fn(t), k)


ESCENAS = [
    (0.0, 42.91, B(a1n)),
    (42.91, 69.45, lambda t: escena_imagen('M01-PIA26353.jpg', t, 42.91, 69.45, 1.0, 1.10, (0.5, 0.5), (0.46, 0.52))),
    (69.45, 90.22, lambda t: escena_imagen('M01-PIA26353.jpg', t, 69.45, 90.22, 1.10, 1.22, (0.46, 0.52), (0.58, 0.45))),
    (90.22, 105.64, esc_lista),
    (105.64, 119.10, B(lambda t: a2n(t, 105.64))),
    (119.10, 140.94, esc_jupiter),
    (140.94, 163.31, esc_io),
    (163.31, 172.01, esc_io2),
    (172.01, 191.63, esc_saturno),
    (191.63, 214.50, esc_titan),
    (214.50, 241.38, esc_maniobra),
    (241.38, 311.93, esc_pbd),
    (311.93, 421.90, esc_helio),
    (421.90, 450.27, esc_zumbido),
    (450.27, 483.45, esc_enlace),
    (483.45, 502.44, esc_mapa),
    (502.44, 507.41, esc_antenas),
    (507.41, 525.78, esc_idavuelta),
    (525.78, 553.06, esc_rtg),
    (553.06, 571.25, esc_instrumentos),
    (571.25, 616.25, esc_chip),
    (616.25, 625.60, esc_plano_sonda),
    (625.60, 639.60, esc_frase),
    (639.60, 674.20, esc_oort),
    (674.20, 715.49, esc_niveles),
    (715.49, 748.78, esc_disco),
    (748.78, 761.89, esc_estrella),
    (761.89, DURACION_V, esc_fuentes),
]
ESQUEMAS = {'esc_maniobra', 'esc_helio', 'esc_zumbido', 'esc_enlace', 'esc_mapa', 'esc_idavuelta', 'esc_rtg', 'esc_instrumentos', 'esc_chip', 'esc_frase', 'esc_oort', 'esc_niveles', 'esc_estrella', 'esc_fuentes'}
ESCENAS = [(a, b, (B(fn) if getattr(fn, '__name__', '') in ESQUEMAS else fn)) for a, b, fn in ESCENAS]

# Sin subtítulos incrustados, la parte baja queda libre: se baja el contenido para centrarlo verticalmente.
# (inicio de la escena en el primer audio: píxeles hacia abajo). Las escenas a pantalla completa no se mueven.
DESPLAZ = {105.64: 70, 119.10: 105, 140.94: 100, 163.31: 105, 172.01: 105, 191.63: 105, 214.5: 70,
           241.38: 105, 421.9: 30, 450.27: 70, 502.44: 80, 507.41: 80, 553.06: 40, 571.25: 40,
           625.6: 60, 715.49: 105, 748.78: 120, 761.89: 60}


def desplazar(fn, dy):
    if not dy:
        return fn

    def f(t):
        FONDO_ULT['bg'] = None
        fr = fn(t)
        bg = FONDO_ULT.get('bg')
        if bg is not None:       # el fondo se queda quieto; solo baja lo que la escena dibujó encima (diferencia con el fondo limpio)
            b = np.asarray(bg, np.int16)
            delta = np.asarray(fr, np.int16) - b
            mov = np.zeros_like(delta)
            mov[dy:] = delta[:H - dy]
            return Image.fromarray(np.clip(b + mov, 0, 255).astype('uint8'))
        out = Image.new('RGB', (W, H))
        out.paste(fr.crop((0, 0, W, H - dy)), (0, dy))
        out.paste(fr.crop((0, dy, W, 2 * dy)).transpose(Image.FLIP_TOP_BOTTOM), (0, 0))
        return out
    return f


ESCENAS = [(a, b, desplazar(fn, DESPLAZ.get(a, 0))) for a, b, fn in ESCENAS]
XF = 0.9

CREDITOS = [
    (42.91, 90.22, 'NASA/JPL-Caltech · Concepto artístico'),
    (119.10, 140.94, 'NASA/JPL · Voyager 1'),
    (140.94, 163.31, 'NASA/JPL/University of Arizona · sonda Galileo, 1999'),
    (153.81, 163.31, 'NASA/JPL · Voyager 1'),
    (163.31, 172.01, 'NASA/JPL · Voyager 1'),
    (172.01, 181.0, 'NASA/JPL-Caltech · Voyager 1'),
    (181.0, 191.63, 'NASA/JPL-Caltech · Voyager 1'),
    (191.63, 214.5, 'NASA/JPL · Voyager 1'),
    (241.38, 273.43, 'NASA/JPL-Caltech · Voyager 1'),
    (273.43, 293.31, 'NASA/JPL-Caltech · Voyager 1'),
    (293.31, 311.93, 'NASA/JPL-Caltech · Voyager 1'),
    (502.44, 507.41, 'NASA · NASA/CSIRO/Canberra Deep Space Communication Complex'),
    (616.25, 625.6, 'NASA/JPL-Caltech · Concepto artístico'),
    (715.49, 748.78, 'NASA/JPL-Caltech'),
    (553.06, 571.25, 'NASA/JPL-Caltech · diagrama de la sonda (etiquetas en inglés)'),
]

# Tarjetas de capítulo (tiempo del primer audio): inicio, número, título corto
CAPITULOS_B = [(43.0, 2, 'Qué es Voyager 1'), (105.8, 3, 'El gran viaje'), (241.6, 4, 'El punto azul pálido'), (312.2, 5, 'La frontera del Sol'),
               (450.5, 6, 'Hablar con una nave'), (526.0, 7, 'Energía y reparación'), (625.8, 8, 'Lo que NO sabemos'), (715.7, 9, 'El disco de oro')]

ROTULOS = [
    (23.5, 30.8, '1 día luz ≈ 25 900 millones de km · hito: 18-nov-2026', 'Fuente: NASA Science', 'dato'),
    (49.3, 56.5, 'Lanzamiento: 5-sep-1977', 'Fuente: NASA Science', 'dato'),
    (80.5, 86.6, 'Velocidad: unos 17 km/s respecto del Sol', 'Fuente: NASA Science (dato de ago-2024)', 'dato'),
    (86.6, 92.0, '17 km/s × 86 400 s ≈ 1,47 millones de km por día', 'Cálculo propio, con la velocidad de NASA', 'calculo'),
    (107.0, 114.5, 'Alineación de los planetas exteriores: cada ≈ 175 años', 'Fuente: NASA NTRS · JPL', 'dato'),
    (I('El 5 de marzo de 1979') + 0.5, I('El 5 de marzo de 1979') + 8.0, 'Júpiter: máximo acercamiento 5-mar-1979, a ≈ 280 000 km', 'Fuente: NASA Science', 'dato'),
    (141.5, 163.0, 'Ío visto por la sonda Galileo, 1999', 'NASA/JPL/University of Arizona', 'dato'),
    (I('Era un volcán'), I('Era un volcán') + 9.0, 'Primera erupción volcánica vista fuera de la Tierra', '8-mar-1979 · descubierta por L. Morabito (JPL) · NASA History Office', 'dato'),
    (I('El 12 de noviembre de 1980') + 0.5, I('El 12 de noviembre de 1980') + 8.5, 'Saturno: 12-nov-1980, a ≈ 126 000 km', 'Fuente: NASA Science', 'dato'),
    (I('Para verla de cerca') + 4.5, I('Para verla de cerca') + 11.5, 'Titán: paso a ≈ 6 500 km, 12-nov-1980', 'Fuente: NASA Science', 'dato'),
    (I('Y 34 minutos después'), I('Y 34 minutos después') + 8.0, 'Imagen del 14-feb-1990 · 34 minutos después, las cámaras se apagaron para siempre', 'Fuente: NASA Science', 'dato'),
    (I('Y al retroceder los datos'), I('Y al retroceder los datos') + 8.5, 'Heliopausa cruzada el 25-ago-2012 · confirmada en 2013', 'Fuente: NASA/JPL · Univ. de Iowa', 'dato'),
    (I('El 5 de noviembre de 2018'), I('El 5 de noviembre de 2018') + 8.0, 'Voyager 2 salió de la heliosfera el 5-nov-2018', 'Fuente: NASA/JPL', 'dato'),
    (I('En 2021, un equipo'), I('En 2021, un equipo') + 9.0, 'Zumbido persistente del gas interestelar (2021)', 'Fuente: Univ. de Cornell · Nature Astronomy', 'dato'),
    (451.0, 458.8, 'Antena de 3,7 m · bajada a 160 bits/s · subida a 16 bits/s', 'Fuente: NASA Science', 'dato'),
    (I('Para ponerlo en escala') + 1.8, I('Para ponerlo en escala') + 6.8, '3 MB × 8 ÷ 160 bit/s ≈ 150 000 s ≈ 42 h', 'Cálculo propio · el tamaño de 3 MB es un ejemplo', 'calculo'),
    (I('Cuando la señal llega') + 0.3, I('Cuando la señal llega') + 9.5, 'Señal 20 mil millones de veces más débil que un reloj digital', 'Fuente: NASA Space Place', 'dato'),
    (I('Y hay un detalle') + 6.0, I('Y hay un detalle') + 11.0, '2 × 23 h ≈ 46 h de ida y vuelta', 'Cálculo propio, con el dato de NASA (≈ 23 h)', 'calculo'),
    (I('Hoy la nave pierde'), I('Hoy la nave pierde') + 6.5, 'Pierde ≈ 4 W de potencia por año', 'Fuente: NASA/JPL, abril de 2026', 'dato'),
    (I('El 17 de abril de este año'), I('El 17 de abril de este año') + 10.0, '17-abr-2026: apagado el instrumento LECP · quedan 2 científicos', 'Fuente: NASA/JPL, abril de 2026', 'dato'),
    (I('El 20 de abril de 2024'), I('El 20 de abril de 2024') + 9.0, 'Fallo del 14-nov-2023 · datos de estado el 20-abr-2024 · ciencia el 22-may-2024', 'Fuente: NASA/JPL', 'dato'),
    (I('Según la NASA, la nave tardará'), I('Según la NASA, la nave tardará') + 8.0, 'Nube de Oort: ≈ 300 años al borde interior · posiblemente ≈ 30 000 para cruzarla', 'Fuente: NASA Science', 'dato'),
    (I('Y lleva consigo un mensaje') + 0.3, I('Y lleva consigo un mensaje') + 13.0, 'Disco de oro: 115 imágenes · 35 sonidos · 90 min de música · 55 idiomas', 'Fuente: NASA Science', 'dato'),
]

# ----------------------------------------------------------------------- subtítulos


def construir_subtitulos():
    subs = []
    for f in FRASES_N:
        partes = trocear_texto(f['texto'])
        total = sum(len(p) for p in partes)
        t0 = f['ini']
        for p in partes:
            d = (f['fin'] - f['ini']) * len(p) / total
            subs.append((p, t0, t0 + d))
            t0 += d
    return subs


SUBS = construir_subtitulos()
SUBS_QUEMADOS = os.environ.get('HE_SUBS', '0') == '1'   # por defecto el video sale SIN subtítulos incrustados (van en el .srt)
NOMBRE = 'video-01-con-subtitulos' if SUBS_QUEMADOS else 'video-01-completo'


def dibujar_subtitulo(fr, t):
    for txt_, a, b in SUBS:
        if a - 0.05 <= t <= b + 0.15:
            sp = [sprite_texto(l, reg(42), HUESO) for l in envolver(txt_)]
            ancho = max(s[1].size[0] for s in sp) + 60
            alto = sum(s[1].size[1] for s in sp) + 22
            y0 = 1080 - 52 - alto
            x0 = (W - ancho) // 2
            fr.paste(Image.new('RGB', (ancho, alto), (4, 6, 16)), (x0, y0), _mascara(ancho, alto, 16).point(lambda v: int(v * 0.62)))
            trazo.rrect(fr, (x0, y0, x0 + ancho, y0 + alto), 16, HUESO, 1, 0.2)
            y = y0 + 9
            for s in sp:
                pegar(fr, s, W // 2, y, 1.0, 'm')
                y += s[1].size[1]
            return


def escribir_srt(ruta):
    def f(s):
        ms = int(round(s * 1000))
        return '{:02d}:{:02d}:{:02d},{:03d}'.format(ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)
    with open(ruta, 'w', encoding='utf-8') as fh:
        for i, (tx, a, b) in enumerate(SUBS, 1):
            fh.write('{}\n{} --> {}\n{}\n\n'.format(i, f(a), f(b), '\n'.join(envolver(tx))))

# --------------------------------------------------------------------- fotograma


def fotograma(t):
    to = t_viejo(t)                     # tiempo de las escenas (primer audio)
    capas = []
    n = len(ESCENAS)
    for i, (a, b, fn) in enumerate(ESCENAS):
        ini = a - XF / 2 if i else -1e9
        fin = b - XF / 2 if i < n - 1 else 1e9
        al = clamp((to - ini) / XF) if i else 1.0
        if i < n - 1:
            al *= 1 - clamp((to - fin) / XF)
        if al > 0:
            capas.append((al, fn))
    fr = capas[0][1](to)
    for al, fn in capas[1:]:
        fr = Image.blend(fr, fn(to), al) if al < 1 else fn(to)
    hud(fr, 0.5)
    vis = [c for c in CREDITOS if aparecer(to, c[0] + 0.6, c[1] - 0.2, 0.5) > 0]
    for k, (a, b, texto) in enumerate(vis):
        credito(fr, texto, aparecer(to, a + 0.6, b - 0.2, 0.5), k)
    for r in ROTULOS:
        rotulo(fr, to, r[0], r[1], r[2], r[3], r[4])
    for ini_c, num_c, tit_c in CAPITULOS_B:
        capitulo(fr, to, ini_c + 0.4, num_c, tit_c)
    cta(fr, to, 424.6, 432.4)          # a mitad del video: suscribirse, dar like y comentar
    # Arranque (tiempo del audio nuevo): «69 kilobytes» y, debajo en pila, la comparación con el móvil y el portátil.
    fin0 = FRASES_N[0]['fin'] + 2.0
    h1 = _contenido_rotulo('Memoria a bordo: unos 69 kilobytes', 'Fuente: NASA, vía MuckRock (FOIA, 2016)', 'dato')[1]
    rotulo(fr, t, 5.0, fin0, 'Memoria a bordo: unos 69 kilobytes', 'Fuente: NASA, vía MuckRock (FOIA, 2016)', 'dato')
    if SPLIT_N is not None:
        rotulo(fr, t, SPLIT_N + 0.2, fin0 + 3.0, 'Una foto de móvil (≈ 3 MB) ≈ 43 veces esa memoria', 'Cálculo propio · un portátil con 8 GB ≈ 116 000 veces (valores de ejemplo)', 'calculo', base=912 - h1 - 18)
    if SUBS_QUEMADOS:
        dibujar_subtitulo(fr, t)
    k = clamp((t - (DURACION - 1.2)) / 1.2)
    if k > 0:
        fr = Image.blend(fr, NEGRO, k)
    return fr


def render_rango(f0, f1, salida):
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '{}x{}'.format(W, H), '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', '-threads', '2', '-g', '30', salida]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(np.asarray(fotograma(f / FPS)).tobytes())
        if (f - f0) % 600 == 0:
            print('  parte {}-{}: {:.0f} %'.format(f0, f1, 100.0 * (f - f0) / max(1, f1 - f0)), flush=True)
    p.stdin.close()
    p.wait()


# --------------------------------------------------------------------------- música
# Pistas de la Biblioteca de audio de YouTube (sin atribución), en este orden. Se buscan en «musica/» por el nombre.
MUSICA = ['False Vacuum Decay', 'Rapid Unscheduled Disassembly', 'Spaghettification']


def mezclar_musica(wav):
    """Mezcla la música bajo la voz (baja sola cuando se habla). Si faltan las pistas, deja solo la voz."""
    carpeta = os.path.join(AQUI, 'musica')
    pistas = []
    for n in MUSICA:
        hallado = [f for f in sorted(os.listdir(carpeta)) if f.lower().startswith(n.lower()) and f.lower().endswith(('.mp3', '.wav', '.m4a', '.aac'))] if os.path.isdir(carpeta) else []
        if hallado:
            pistas.append(os.path.join(carpeta, hallado[0]))
    if len(pistas) < len(MUSICA):
        print('Sin música (faltan pistas en {}): el video lleva solo la voz.'.format(carpeta))
        return wav
    d = DURACION
    ent = ['-i', wav] + sum((['-i', x] for x in pistas), [])
    cadena = '[1:a][2:a]acrossfade=d=4:c1=tri:c2=tri[m12];[m12][3:a]acrossfade=d=4:c1=tri:c2=tri[m123];'
    cadena += '[m123]aresample=48000,loudnorm=I=-24:TP=-3:LRA=7,atrim=0:{d:.2f},afade=t=in:d=3,afade=t=out:st={s:.2f}:d=4[mus];'.format(d=d, s=d - 4)
    cadena += '[0:a]aresample=48000,asplit=2[voz1][voz2];[mus][voz1]sidechaincompress=threshold=0.015:ratio=6:attack=30:release=600[duck];'
    cadena += '[duck][voz2]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=11[out]'
    salida = os.path.join(AQUI, 'salida', '_audio-con-musica.wav')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + ent + ['-filter_complex', cadena, '-map', '[out]', '-ac', '2', salida], check=True)
    return salida


def main():
    os.makedirs(os.path.join(AQUI, 'salida'), exist_ok=True)
    a = sys.argv[1:]
    if len(a) >= 3 and a[0] == '--frame':
        fotograma(float(a[1])).save(a[2])
        return
    if a and a[0] == '--solo-audio':        # cambia la música sin volver a renderizar el video
        tmp = os.path.join(AQUI, 'salida', '_partes')
        wav = os.path.join(AQUI, 'salida', '_audio-completo.wav')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', AUDIO, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,apad=pad_dur={}'.format(COLA), '-t', str(DURACION), '-ac', '1', wav], check=True)
        wav = mezclar_musica(wav)
        final = os.path.join(AQUI, 'salida', NOMBRE + '.mp4')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', os.path.join(tmp, 'lista.txt'), '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', final], check=True)
        print('listo:', final)
        return
    if len(a) >= 4 and a[0] == '--rango':
        render_rango(int(a[1]), int(a[2]), a[3])
        return
    total = int(DURACION * FPS)
    partes = int(a[0]) if a else 4
    paso = -(-total // partes)
    tmp = os.path.join(AQUI, 'salida', '_partes')
    os.makedirs(tmp, exist_ok=True)
    procs, archivos = [], []
    for k in range(partes):
        f0, f1 = k * paso, min(total, (k + 1) * paso)
        out = os.path.join(tmp, 'parte_{:02d}.mp4'.format(k))
        archivos.append(out)
        procs.append(subprocess.Popen([sys.executable, os.path.abspath(__file__), '--rango', str(f0), str(f1), out]))
    for p in procs:
        p.wait()
        if p.returncode:
            raise SystemExit('Falló una parte del render')
    lista = os.path.join(tmp, 'lista.txt')
    open(lista, 'w').write(''.join("file '{}'\n".format(x.replace('\\', '/')) for x in archivos))
    wav = os.path.join(AQUI, 'salida', '_audio-completo.wav')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', AUDIO, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,apad=pad_dur={}'.format(COLA), '-t', str(DURACION), '-ac', '1', wav], check=True)
    wav = mezclar_musica(wav)
    escribir_srt(os.path.join(AQUI, 'salida', NOMBRE + '.srt'))
    final = os.path.join(AQUI, 'salida', NOMBRE + '.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lista, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', final], check=True)
    print('listo:', final)


if __name__ == '__main__':
    main()
