#!/usr/bin/env python3
"""
Video 2 completo (Edad del universo) · montador automático de Hace Eones.

Sigue «Escaleta audiovisual.md» (44 escenas) con los tiempos reales de `tiempos.json` (alineación de las 134 frases con la voz).
Imágenes reales: solo M01 (WMAP, NASA), M02 (collage de Hubble, NASA/ESA) y M03 (mapa de Gaia, ESA); el resto son animaciones propias.
Este script vive en la carpeta del video; las librerías compartidas están en «herramientas/montaje».

  python video02.py --frame 150 f.png       un fotograma (segundo 150) para revisar el diseño
  python video02.py                         render completo en paralelo -> salida/video-02-completo.mp4 (+ .srt)
  python video02.py --solo-audio            vuelve a mezclar la música sin renderizar el video
"""
import json
import math
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.abspath(os.path.join(AQUI, '..'))
os.environ['HE_VIDEO'] = VIDEO          # montar.py lee las imágenes de «Licencias/originales» de ESTE video
sys.path.insert(0, os.path.abspath(os.path.join(AQUI, '..', '..', '..', '..', 'herramientas', 'montaje', 'comun')))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'herramientas', 'montaje', 'animaciones', 'espacial'))

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import aa as trazo
from estilo import FONDO_ULT, base, bloom, etq, fbm, hud, linea_glow, panel, txt_glow  # noqa
from ui import (HIELO, ROJO, VERDE, anillo_arco, caja, credito, ease_in, ease_out, etiqueta_esquema, icono_hex, pastilla,  # noqa
                rotulo, sl, sb, sprite_esp, titulo, cta)
from montar import (AMBAR, BG, FPS, H, HUESO, NEGRO, W, aparecer, blk, brillo, cargar, clamp, envolver, lerp, mezcla, neg,  # noqa
                    pegar, punto, reg, sprite_texto, ss, trocear_texto, escena_imagen)
from ui import icono_cta  # noqa
TIERRA_C = (96, 158, 255)


def punto(fr, x, y, r, color, alpha=1.0, halo=3.0):
    """Punto con núcleo suavizado en posición subpíxel (así los puntos que se mueven despacio no avanzan a saltos de un píxel)."""
    if alpha <= 0.004:
        return
    if halo:
        pegar(fr, brillo(int(r * halo), color), x, y, alpha * 0.55, 'm', 'm')
    trazo.elipse(fr, (x - r, y - r, x + r, y + r), color, 1, alpha, relleno=True, ss=3)

AUDIO = os.path.join(VIDEO, 'Voz', 'video2-raul.wav')
NUEVO = json.load(open(os.path.join(AQUI, 'tiempos.json'), encoding='utf8'))
FRASES_N = NUEVO['frases']
FIN_AUDIO = NUEVO['total']
COLA = 2.0
DURACION = FIN_AUDIO + COLA
GRIS = mezcla(BG, HUESO, 0.55)
CX, CY = W // 2, 470            # centro del área de contenido (deja libres el borde superior y los rótulos de abajo)

# colores de los tres relojes (se mantienen en todo el video)
C1, C2, C3 = HIELO, AMBAR, VERDE


def I(prefijo, n=0):
    k = 0
    for f in FRASES_N:
        if f['texto'].startswith(prefijo):
            if k == n:
                return f['ini']
            k += 1
    raise KeyError(prefijo)


def Fin(prefijo, n=0):
    k = 0
    for f in FRASES_N:
        if f['texto'].startswith(prefijo):
            if k == n:
                return f['fin']
            k += 1
    raise KeyError(prefijo)


# ------------------------------------------------------------------ utilidades de dibujo
def P(t, a, d=0.6):
    return ss((t - a) / d)


def Q(t, a, b, d=0.5):
    return aparecer(t, a, b, d)


def txt(fr, s, fnt, color, x, y, a=1.0, ax='l', ay='t'):
    if a > 0.004:
        pegar(fr, sprite_texto(s, fnt, color), x, y, a, ax, ay)


def linea(fr, pts, color, ancho=3, a=1.0, glow=0.0):
    if a > 0.004 and len(pts) > 1:
        trazo.linea(fr, pts, color, ancho, a, glow=glow, ss=3)


def anillo(fr, x, y, r, color, a=1.0, ancho=3, glow=0.5):
    if a > 0.004:
        trazo.elipse(fr, (x - r, y - r, x + r, y + r), color, ancho, a, glow=glow, ss=3)


def reloj(fr, cx, cy, r, ang, color, a=1.0, ang2=None):
    """Reloj abstracto: anillo, marcas y manecilla (ang en grados desde las 12)."""
    if a <= 0.004:
        return
    pegar(fr, brillo(int(r * 1.7), color), cx, cy, 0.30 * a, 'm', 'm')
    anillo(fr, cx, cy, r, color, a, 4)
    for k in range(12):
        th = math.radians(k * 30)
        r0, r1 = r * (0.84 if k % 3 else 0.78), r * 0.93
        linea(fr, [(cx + r0 * math.sin(th), cy - r0 * math.cos(th)), (cx + r1 * math.sin(th), cy - r1 * math.cos(th))], color, 3 if k % 3 == 0 else 2, 0.8 * a)
    th = math.radians(ang)
    linea(fr, [(cx, cy), (cx + 0.72 * r * math.sin(th), cy - 0.72 * r * math.cos(th))], HUESO, 5, a, 0.4)
    if ang2 is not None:
        th = math.radians(ang2)
        linea(fr, [(cx, cy), (cx + 0.5 * r * math.sin(th), cy - 0.5 * r * math.cos(th))], color, 6, a)
    punto(fr, cx, cy, 6, color, a, 2.5)


_FC = {}


def _ruido_fft(h, w, beta, semilla):
    """Ruido fractal PERIÓDICO (sin costuras) generado en el espacio de frecuencias: sirve para nubes de gas que se desplazan en bucle."""
    rng = np.random.RandomState(semilla)
    F = np.fft.fft2(rng.randn(h, w))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1.0
    n = np.real(np.fft.ifft2(F * f ** (-beta / 2.0)))
    return ((n - n.mean()) / (n.std() + 1e-9)).astype(np.float32)


def _fc():
    """Campos de la nebulosa (a media resolución): nube de gas, filamentos, polvo oscuro, tono y textura fina."""
    if 'A' not in _FC:
        from scipy.ndimage import map_coordinates
        h, w = H // 2, W // 2
        A = _ruido_fft(h, w, 3.2, 11)
        wx, wy = _ruido_fft(h, w, 3.0, 12) * 38, _ruido_fft(h, w, 3.0, 13) * 38
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        _FC['A'] = map_coordinates(A, [yy + wy, xx + wx], order=1, mode='wrap').astype(np.float32)
        B = _ruido_fft(h, w, 3.4, 21)
        _FC['R'] = ((1 - np.abs(np.tanh(B * 0.8))) ** 3).astype(np.float32)
        _FC['C'] = _ruido_fft(h, w, 3.4, 31)
        _FC['Hn'] = _ruido_fft(h, w, 3.6, 41)
        _FC['F'] = _ruido_fft(h, w, 2.8, 51)
        d = np.hypot((xx - w / 2) / (w / 2), (yy - h * 0.46) / (h / 2)).astype(np.float32)
        _FC['centro'] = np.exp(-d * d * 1.7)[..., None].astype(np.float32)
        _FC['vig'] = np.clip(1.12 - 0.40 * d, 0.50, 1.0)[..., None].astype(np.float32)
        rng = np.random.RandomState(5)
        _FC['stars'] = (rng.rand(700) * 6.2832, rng.rand(700), 0.25 + 0.75 * rng.rand(700))
    return _FC


def _mezcla3(a, b, c, s):
    return np.array(mezcla(a, b, s / 0.5) if s < 0.5 else mezcla(b, c, (s - 0.5) / 0.5), np.float32)


def _roll_sub(a, shift):
    """Desplaza en horizontal con precisión de subpíxel (mezcla lineal de dos desplazamientos enteros)."""
    n = a.shape[1]
    s = shift % n
    i = int(s)
    f = s - i
    return np.roll(a, i, axis=1) * (1 - f) + np.roll(a, i + 1, axis=1) * f


def _roll2(a, sx, sy):
    """Desplazamiento periódico continuo en x e y (subpíxel)."""
    r = _roll_sub(a, sx)
    n = r.shape[0]
    s = sy % n
    i = int(s)
    f = s - i
    return np.roll(r, i, axis=0) * (1 - f) + np.roll(r, i + 1, axis=0) * f


def _suave(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def fondo_cosmico(t):
    """Nebulosa de gas y polvo que «se enfría» con el video: brasa (hidrógeno incandescente) → magenta/violeta → azul y turquesa.
    Todo es periódico y se mueve de forma continua (capas a distinta velocidad); se calcula a media resolución y se amplía."""
    c = _fc()
    s = clamp(t / DURACION)
    c1 = _mezcla3((255, 92, 38), (200, 66, 160), (64, 108, 235), s)
    c2 = _mezcla3((255, 178, 92), (112, 120, 255), (58, 196, 212), s)
    A = _roll2(c['A'], t * 2.0, t * 0.6)
    R = _roll2(c['R'], t * 3.2, -t * 0.5)
    C = _roll2(c['C'], t * 1.2, t * 0.3)
    Hn = _roll2(c['Hn'], -t * 1.0, t * 0.4)
    Fn = _roll2(c['F'], t * 4.5, t * 1.0)
    gas = _suave((0.5 + 0.26 * A - 0.36) / 0.46)
    dens = (gas * 0.70 + R * gas * 0.85) * (0.82 + 0.26 * np.clip(0.5 + 0.25 * Fn, 0, 1))
    dens *= 1 - 0.72 * _suave((0.5 + 0.25 * C - 0.52) / 0.26)          # vetas de polvo oscuro
    dens = np.clip(dens, 0, 1.2) ** 1.2
    tono = np.clip(0.5 + 0.30 * Hn, 0, 1)[..., None]
    col = dens[..., None] * (c1 * (1 - tono) + c2 * tono) * 0.34
    img = np.array((3, 4, 9), np.float32) + col + c['centro'] * c1 * 0.05
    img *= c['vig']
    fr = Image.fromarray(np.clip(img, 0, 255).astype('uint8')).filter(ImageFilter.GaussianBlur(1.0)).resize((W, H), Image.BICUBIC)
    # estrellas que se alejan del centro (puntos suaves, a resolución completa)
    ang, r0, br = c['stars']
    rn = 0.08 + 0.92 * ((r0 + t * 0.010 * (0.4 + br)) % 1.0)
    rr = (rn ** 1.35) * 1250
    xs = W / 2 + np.cos(ang) * rr
    ys = H * 0.46 + np.sin(ang) * rr * 0.62
    al = np.sin(np.pi * ((rn - 0.08) / 0.92)) ** 0.7 * br
    ok = (xs > 1) & (xs < W - 2) & (ys > 1) & (ys < H - 2)
    xs, ys, al = xs[ok], ys[ok], al[ok]
    cap = np.zeros((H, W), np.float32)
    x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
    fx, fy = xs - x0, ys - y0
    val = (70 + 185 * al).astype(np.float32)
    for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(cap, (y0 + dy, x0 + dx), val * wgt)
    gr = al > 0.62
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        np.add.at(cap, (y0[gr] + dy, x0[gr] + dx), val[gr] * 0.35)
    arr = np.asarray(fr, np.float32) + cap[..., None] * np.array((0.96, 0.95, 0.91), np.float32)
    fr = Image.fromarray(np.clip(arr, 0, 255).astype('uint8'))
    FONDO_ULT['bg'] = fr
    return fr


def cielo(t, k=1.0):
    fr = fondo_cosmico(t)
    if k < 1:
        fr = Image.blend(Image.new('RGB', (W, H), (0, 0, 0)), fr, k)
    return fr


_T = [0.0]                          # instante del fotograma en curso (lo usa el envoltorio de títulos)
_titulo_base = titulo


def _tarjeta_capitulo_activa(t):
    return any(ini + 0.4 <= t <= ini + 0.4 + 4.8 for ini, _, _ in CAPITULOS_B)


def titulo(fr, eyebrow, texto, x, y, a=1.0, ax='l', tam=44, color=HUESO):
    """Título de escena. Nunca se reubica en pleno video (eso se vería como un salto): los títulos son lo bastante cortos para no chocar con la tarjeta de capítulo (lo comprueba --verificar)."""
    return _titulo_base(fr, eyebrow, texto, x, y, a, ax, tam, color)


def ayuda(fr, texto, a=1.0, y=715, color=GRIS):
    """Línea de explicación en lenguaje llano debajo de una gráfica (dentro de la zona segura)."""
    if a > 0.004:
        txt(fr, texto, reg(30), color, CX, y, a, 'm')


_MS = {}


def imagen_suave(fr, im, cx, cy, w, h, a=1.0, radio=40, borde=True, pluma=7, z=1.0):
    """Pega una imagen con esquinas redondeadas y borde difuminado (nunca un rectángulo de esquinas vivas). El zoom z usa una caja con decimales."""
    if a <= 0.004:
        return
    bw, bh = im.width / z, im.height / z
    bx, by = (im.width - bw) / 2, (im.height - bh) / 2
    s = im.resize((w, h), Image.BICUBIC, box=(bx, by, bx + bw, by + bh))
    k = (w, h, radio, pluma)
    if k not in _MS:
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle((pluma, pluma, w - pluma, h - pluma), radio, fill=255)
        _MS[k] = m.filter(ImageFilter.GaussianBlur(pluma * 0.7))
    pegar(fr, brillo(int(max(w, h) * 0.55), HIELO), cx, cy, 0.10 * a, 'm', 'm')
    fr.paste(s, (int(cx - w / 2), int(cy - h / 2)), _MS[k].point(lambda q: int(q * a)))
    if borde:
        trazo.rrect(fr, (cx - w / 2 + pluma, cy - h / 2 + pluma, cx + w / 2 - pluma, cy + h / 2 - pluma), radio, HUESO, 1, 0.25 * a)


def flecha(fr, p0, p1, color, ancho=3, a=1.0, punta=14):
    linea(fr, [p0, p1], color, ancho, a)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for d in (2.6, -2.6):
        linea(fr, [p1, (p1[0] + punta * math.cos(ang + d), p1[1] + punta * math.sin(ang + d))], color, ancho, a)


def eje_x(fr, x0, x1, y, v0, v1, paso, a=1.0, fmt='{:.1f}', dec=False, color=GRIS):
    linea(fr, [(x0, y), (x1, y)], color, 2, 0.8 * a)
    v = v0
    while v <= v1 + 1e-9:
        x = x0 + (x1 - x0) * (v - v0) / (v1 - v0)
        linea(fr, [(x, y - 6), (x, y + 6)], color, 2, 0.8 * a)
        s = fmt.format(v)
        if dec:
            s = s.replace('.', ',')
        txt(fr, s, reg(24), color, x, y + 14, a, 'm')
        v += paso


def barra_v(fr, X, y, v0, v1, color, a=1.0, alto=26, centro=None):
    """Barra horizontal de un valor con su margen (X convierte valor → píxel)."""
    if a <= 0.004:
        return
    x0, x1 = X(v0), X(v1)
    trazo.rrect(fr, (x0, y - alto // 2, x1, y + alto // 2), alto // 2, color, 2, a, relleno=False, cache=False)
    fr.paste(Image.new('RGB', (max(1, int(x1 - x0)), alto), color), (int(x0), int(y - alto // 2)), Image.new('L', (max(1, int(x1 - x0)), alto), int(70 * a)))
    if centro is not None:
        punto(fr, X(centro), y, 9, color, a, 3.0)


# ---------------------------------------------------------------- escenas
def esc_gancho(t):
    """E01–E05 · 0:00–0:56: paradoja, cifra, tres relojes."""
    k0 = ss((t - 7.2) / 2.6)                          # el fondo aparece despacio después de las dos primeras frases
    fr = cielo(t, k0)
    num = P(t, 8.4, 1.0) * (1 - P(t, 22.2, 0.6))
    if t < 8.3:
        # E01: negro, un punto de luz que respira y dos frases, una tras otra
        pul = 0.75 + 0.25 * math.sin(t * 1.6)
        pegar(fr, brillo(46 + int(14 * pul), HUESO), CX, CY + 150, (0.55 + 0.4 * pul) * P(t, 0.0, 0.8) * (1 - P(t, 7.4, 0.9)), 'm', 'm')
        c1 = Q(t, 0.2, 3.5, 0.6)
        txt(fr, 'NADIE ESTUVO ALLÍ', blk(78), HUESO, CX, CY - 40, c1, 'm', 'm')
        c2 = Q(t, 3.7, 7.7, 0.6)
        txt(fr, 'NI LA TIERRA, NI EL SOL,', blk(64), HUESO, CX, CY - 80, c2, 'm', 'm')
        txt(fr, 'NI UNA SOLA ESTRELLA', blk(64), AMBAR, CX, CY + 0, c2, 'm', 'm')
    else:
        # E02: la cifra aparece donde estaba el punto de luz; ± 23 millones y 0,17 %
        txt_glow(fr, '13 797 000 000', blk(78), AMBAR, CX, 250, num, 'm', 'm')
        txt(fr, 'DE AÑOS', blk(36), HUESO, CX, 250 + 74, num, 'm', 'm')
        txt(fr, '± 23 millones', neg(58), HUESO, CX, 365, P(t, 10.4) * (1 - P(t, 22.2, 0.6)), 'm', 'm')
        p = P(t, 17.4, 0.8) * (1 - P(t, 22.2, 0.6))
        if p > 0:
            txt_glow(fr, '0,17 %', blk(190), AMBAR, CX, 560, p, 'm', 'm')
            txt(fr, 'error relativo: 0,023 ÷ 13,797 ≈ 0,0017', reg(30), GRIS, CX, 690, P(t, 19.2) * (1 - P(t, 22.2, 0.6)), 'm')
    if t >= 22.2:
        # E03: ¿? y tres relojes
        q = P(t, 22.5, 0.5) * (1 - P(t, 25.4, 0.6))
        txt_glow(fr, '¿?', blk(240), AMBAR, CX, CY, q, 'm', 'm')
        xs = (CX - 480, CX, CX + 480)
        cols = (C1, C2, C3)
        res = I('Y aquí viene lo que')
        for i, (x, c) in enumerate(zip(xs, cols)):
            a = P(t, 25.6 + i * 1.0, 0.6)
            ang = 40 + 28 * t * (1 + 0.15 * i)
            ang2 = ang * 0.08
            if t > res + 3.5 and i > 0:                      # dos de ellos se desalinean y vibran
                d = (-1) ** i * min(95, 26 * (t - res - 3.5))
                ang += d
                x += math.sin(t * 9.0) * 2.0 * min(1, (t - res - 3.5) / 2)
            reloj(fr, x, CY + 20, 130, ang, c, a * (1 - P(t, 52.0, 1.0) * (i > 0)), ang2)
        titulo(fr, 'EL PLAN', '3 RELOJES', CX, 96, P(t, 27.0) * (1 - P(t, 52.0, 0.6)), 'm', 54)
        if t > res + 5:
            pastilla(fr, '¿POR QUÉ NO COINCIDEN?', CX, CY + 220, ROJO, P(t, res + 5.0) * (1 - P(t, 50.0, 0.6)), 'm')
        tj = I('Lo que está en juego, según')
        e = P(t, tj + 1.0, 0.8) * (1 - P(t, 52.0, 0.6))
        txt_glow(fr, '≈ 1 000 millones de años en juego', blk(50), AMBAR, CX, CY + 300, e, 'm', 'm')
        txt(fr, 'cálculo propio · se explica al final', reg(26), GRIS, CX, CY + 345, e, 'm')
        # E05: el reloj 1 llena la pantalla
        if t > 52.0:
            u = P(t, 52.0, 1.2)
            reloj(fr, lerp(xs[0], CX, u), lerp(CY + 20, CY, u), lerp(130, 190, u), 40 + 28 * t, C1, 1.0, (40 + 28 * t) * 0.08)
            titulo(fr, 'PRIMER RELOJ', 'La luz más antigua', CX, 96, P(t, 52.6), 'm', 50)
    return fr


def esc_medir(t):
    """E06–E07 · 0:56–1:31: qué es «la edad del universo» y se siembra ΛCDM."""
    fr = cielo(t)
    titulo(fr, 'ANTES DE EMPEZAR', '¿Qué estamos midiendo?', CX, 96, P(t, 56.7), 'm', 50)
    y = 520
    x0, x1 = 260, 1660
    k = P(t, 57.5, 1.2)
    linea(fr, [(x0, y), (lerp(x0, x1, k), y)], HUESO, 4, 0.9, 0.4)
    for i, (x, s, c) in enumerate(((x0, 'estado muy denso y muy caliente', AMBAR), (x1, 'HOY', HIELO))):
        punto(fr, x, y, 12, c, k, 3.5)
        txt(fr, s, blk(34) if i else neg(30), c, x, y + 46, k, 'm' if i else 'l')
    # «algo explotó en algún sitio» tachado
    f = I('Cuando decimos')
    a = P(t, f + 1.0) * (1 - P(t, 75.0, 0.6))
    txt(fr, '«algo explotó en algún sitio»', neg(44), GRIS, CX, 300, a, 'm', 'm')
    s = P(t, f + 3.5, 0.7)
    if a > 0:
        w = sprite_texto('«algo explotó en algún sitio»', neg(44), GRIS)[1].size[0]
        linea(fr, [(CX - w / 2, 300), (CX - w / 2 + w * s, 300)], ROJO, 5, a)
    # el tiempo transcurrido
    h = I('Hablamos del tiempo')
    br = P(t, h + 0.4, 0.8) * (1 - P(t, 75.0, 0.6))
    if br > 0:
        linea(fr, [(x0 + 12, y - 40), (x0 + 12, y - 62), (x1 - 12, y - 62), (x1 - 12, y - 40)], AMBAR, 3, br, 0.6)
        txt_glow(fr, 'tiempo transcurrido = la edad', blk(40), AMBAR, CX, y - 120, br, 'm', 'm')
    # ΛCDM
    l = I('Y un detalle más')
    big = P(t, l, 0.7) * (1 - P(t, l + 8.5, 0.7))
    txt_glow(fr, 'ΛCDM', blk(190), AMBAR, CX, 400, big, 'm', 'm')
    txt(fr, 'el modelo estándar de la cosmología', reg(34), HUESO, CX, 520, big, 'm')
    pastilla(fr, 'ΛCDM · MODELO ESTÁNDAR', W - 96, 190, AMBAR, P(t, l + 8.5, 0.7), 'r')
    return fr


def _particulas(n, semilla):
    rng = np.random.RandomState(semilla)
    return rng.rand(n, 2), rng.rand(n, 2) * 6.28, 0.4 + rng.rand(n) * 0.9


PART = _particulas(260, 7)


def esc_niebla(t):
    """E08–E09 · 1:31–2:04: niebla opaca y luego se despeja."""
    fr = cielo(t)
    titulo(fr, 'RELOJ 1 · LA LUZ', 'Una niebla que no deja pasar la luz', CX, 96, P(t, 91.9) * (1 - P(t, 111.0, 0.6)), 'm', 46)
    clear = P(t, I('Entonces los átomos') + 0.9, 1.6)
    pos, ph, vel = PART
    brumas = Image.new('RGB', (W, H), (0, 0, 0))
    d = ImageDraw.Draw(brumas)
    pts = []
    for (px, py), (a, b), v in zip(pos, ph, vel):
        x = 120 + px * (W - 240) + math.sin(t * v * 2.2 + a) * 22 + clear * (px - 0.5) * 900
        y = 250 + py * 470 + math.cos(t * v * 2.0 + b) * 18
        pts.append((x, y))
    al = (1 - clear) * Q(t, 92.2, 124.0, 1.0)
    fr = Image.blend(fr, ImageChops.screen(fr, Image.new('RGB', (W, H), mezcla(BG, (255, 190, 130), 0.16))), 0.9 * al)
    for x, y in pts:
        pegar(fr, brillo(34, mezcla(BG, (255, 190, 130), 0.9)), x, y, 0.30 * al, 'm', 'm')
    trazo.puntos(fr, pts, 3.2, (255, 214, 150), 0.8 * al, ss=3)
    # 380 000 años y 2 700 °C
    txt_glow(fr, '380 000 años', blk(96), AMBAR, CX, 175, P(t, I('Así fue el universo') + 0.8) * (1 - P(t, 111.0, 0.6)), 'm', 'm')
    h = I('Hasta que, poco a poco')
    txt_glow(fr, '2 700 °C', blk(110), HUESO, CX, 175, P(t, h + 1.0) * (1 - P(t, 124.0, 0.6)), 'm', 'm')
    # barrido de luz
    r = I('Entonces los átomos')
    u = P(t, r + 0.6, 1.8)
    if 0 < u < 1:
        x = lerp(-200, W + 200, u)
        for dx, aa_ in ((-120, 0.10), (-60, 0.20), (0, 0.5)):
            linea(fr, [(x + dx, 120), (x + dx, 900)], HUESO, 60 - abs(dx) * 0.3, aa_ * (1 - u * 0.4))
    luz = ss((t - r - 1.2) / 2.0)
    if luz > 0:
        fr = Image.blend(fr, ImageChops.screen(fr, Image.new('RGB', (W, H), mezcla(BG, HIELO, 0.20))), luz * 0.8)
        txt_glow(fr, 'la niebla se despejó', blk(64), HUESO, CX, 770, luz, 'm', 'm')
    pastilla(fr, 'ILUSTRACIÓN PROPIA', 96, 196, AMBAR, 0.9)
    return fr


_CMB = {}


def mapa_cmb():
    if 'im' not in _CMB:
        w, h = 1200, 600
        n = fbm(w, h, [24, 60, 140], 11)
        n = (n - n.min()) / (n.max() - n.min() + 1e-9)
        n = np.clip((n - 0.5) * 1.5 + 0.5, 0, 1)
        stops = np.array([(22, 34, 84), (40, 78, 140), (88, 128, 170), (170, 160, 150), (214, 150, 104)], np.float32)
        idx = n * (len(stops) - 1)
        i0 = np.clip(idx.astype(int), 0, len(stops) - 2)
        f = (idx - i0)[..., None]
        rgb = stops[i0] * (1 - f) + stops[i0 + 1] * f
        im = Image.fromarray(rgb.astype('uint8'))
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).ellipse((0, 0, w - 1, h - 1), fill=255)
        _CMB['im'] = (im, m.filter(ImageFilter.GaussianBlur(1.2)))
    return _CMB['im']


def esc_cmb(t):
    """E10–E11 · 2:04–2:34: fondo cósmico (ilustración propia, sin esquinas duras) y Planck."""
    fr = cielo(t)
    im, _ = mapa_cmb()
    u = P(t, I('La misión Planck') + 6.0, 4.0)
    zoom = 1.0 + 1.1 * u
    cx = 0.55 - 0.2 * u
    w, h = im.size
    cw, ch = w / zoom, h / zoom
    x0 = clamp(cx * w - cw / 2, 0, w - cw)
    y0 = clamp(0.5 * h - ch / 2, 0, h - ch)
    Wd, Hd = 960, 480
    sub = im.resize((Wd, Hd), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))      # caja con decimales: el zoom avanza sin saltos
    if 'm' not in _CMB:
        m = Image.new('L', (Wd * 2, Hd * 2), 0)
        ImageDraw.Draw(m).ellipse((2, 2, Wd * 2 - 3, Hd * 2 - 3), fill=255)
        _CMB['m'] = m.resize((Wd, Hd), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))
    a = Q(t, 124.4, 154.2, 0.8)
    X0, Y0 = 330, 215
    pegar(fr, brillo(480, HIELO), X0 + Wd // 2, Y0 + Hd // 2, 0.18 * a, 'm', 'm')
    fr.paste(sub, (X0, Y0), _CMB['m'].point(lambda q: int(q * a)))              # la máscara elíptica es fija: el zoom nunca deja esquinas
    trazo.elipse(fr, (X0, Y0, X0 + Wd, Y0 + Hd), HUESO, 2, 0.35 * a)
    pastilla(fr, 'ILUSTRACIÓN PROPIA · NO ES UNA IMAGEN REAL', X0, 182, AMBAR, a)
    titulo(fr, 'EL FONDO CÓSMICO DE MICROONDAS', 'La luz más antigua que existe', CX, 56, P(t, 124.5) * (1 - P(t, 139.0, 0.6)), 'm', 46)
    s = I('Se ha enfriado tanto')
    ta = P(t, s + 1.0) * (1 - P(t, 139.4, 0.6))
    if ta > 0:
        caja(fr, 1450, 330, 340, 230, AMBAR, 1.0, ta, c=18, oscuro=0.6)
        txt(fr, '2,7 K', blk(84), AMBAR, 1620, 410, ta, 'm', 'm')
        txt(fr, '≈ −270 °C', neg(38), HUESO, 1620, 490, ta, 'm', 'm')
    se = I('Su mapa muestra')
    txt_glow(fr, 'las manchas son semillas de estrellas y galaxias', neg(38), HUESO, X0 + Wd // 2, 705, P(t, se + 0.4) * (1 - P(t, 154.0, 0.6)) * (t > 139.8), 'm', 'm')
    return fr


def esc_dos_puntos(t):
    """E12 · 2:34–2:58: 2013 → 2018 (casi no se movió)."""
    fr = cielo(t)
    titulo(fr, 'PLANCK · MISMA MEDICIÓN, DOS ENTREGAS', '2013 → 2018', CX, 96, P(t, 154.8), 'm', 50)
    x0, x1, y0, y1 = 480, 1440, 620, 240
    Y = lambda v: lerp(y0, y1, (v - 13.70) / (13.90 - 13.70))
    linea(fr, [(x0, y0), (x0, y1)], GRIS, 2, 0.8 * P(t, 155.0))
    for v in (13.7, 13.8, 13.9):
        linea(fr, [(x0 - 8, Y(v)), (x0 + 8, Y(v))], GRIS, 2, 0.8 * P(t, 155.0))
        txt(fr, ('%.1f' % v).replace('.', ','), reg(26), GRIS, x0 - 20, Y(v), P(t, 155.0), 'r', 'm')
    txt(fr, 'miles de millones de años', reg(24), GRIS, x0, y1 - 40, P(t, 155.0), 'l')
    p1 = P(t, I('En 2013, los primeros') + 0.6)
    p2 = P(t, I('En 2018, con la misión') + 0.6)
    xa, xb = 760, 1240
    punto(fr, xa, Y(13.82), 14, C1, p1, 3.5)
    txt(fr, '2013', neg(34), HUESO, xa, y0 + 24, p1, 'm')
    txt_glow(fr, '13,82', blk(52), C1, xa, Y(13.82) - 56, p1, 'm', 'm')
    punto(fr, xb, Y(13.797), 14, AMBAR, p2, 3.5)
    linea(fr, [(xb, Y(13.797 + 0.023)), (xb, Y(13.797 - 0.023))], AMBAR, 5, p2)
    for yy in (13.797 + 0.023, 13.797 - 0.023):
        linea(fr, [(xb - 16, Y(yy)), (xb + 16, Y(yy))], AMBAR, 4, p2)
    txt(fr, '2018', neg(34), HUESO, xb, y0 + 24, p2, 'm')
    txt_glow(fr, '13,797 ± 0,023', blk(52), AMBAR, xb, Y(13.797) - 110, p2, 'm', 'm')
    if p2 > 0:
        linea(fr, [(xa + 22, Y(13.82)), (xb - 24, Y(13.797) - 2)], HUESO, 3, 0.55 * p2)
    txt(fr, 'casi no se movió', neg(40), HUESO, CX, 690, P(t, I('Fíjate: casi') + 0.2), 'm', 'm')
    return fr


def _imagen_fija(archivo, t, ini, fin, z0, z1, c0, c1, oscuro=0.0, mascara=False):
    return escena_imagen(archivo, t, ini, fin, z0, z1, c0, c1, oscuro=oscuro)


def esc_wmap(t):
    """E13 · 2:58–3:17: WMAP (M01), imagen real de la NASA, en su elipse (sin esquinas) sobre la nebulosa."""
    fr = cielo(t)
    key = ('wmap', 3)
    w, h = 1100, 550
    if key not in _CMB:
        im = cargar('M01-wmap-9yr-cmb.png').resize((2200, 1100), Image.LANCZOS)
        m = Image.new('L', (w * 2, h * 2), 0)
        ImageDraw.Draw(m).ellipse((4, 4, w * 2 - 5, h * 2 - 5), fill=255)
        _CMB[key] = (im, m.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.0)))
    im, m = _CMB[key]
    a = Q(t, 178.4, 197.2, 0.7)
    z = lerp(1.0, 1.07, P(t, 178.4, 19.0))
    bw, bh = im.width / z, im.height / z
    sub = im.resize((w, h), Image.BICUBIC, box=((im.width - bw) / 2, (im.height - bh) / 2, (im.width + bw) / 2, (im.height + bh) / 2))
    pegar(fr, brillo(520, HIELO), CX, 450, 0.20 * a, 'm', 'm')
    fr.paste(sub, (CX - w // 2, 450 - h // 2), m.point(lambda q: int(q * a)))
    titulo(fr, 'WMAP · NASA', 'Otro satélite, el mismo fondo cósmico', CX, 56, P(t, 178.6) * (1 - P(t, 196.5, 0.6)), 'm', 42)
    return fr


def X_edad(a, b, v0, v1):
    return lambda v: lerp(a, b, (v - v0) / (v1 - v0))


def esc_compatibles(t):
    """E14–E14b · 3:17–3:54: WMAP frente a Planck; después «depende del modelo»."""
    fr = cielo(t)
    X = X_edad(360, 1560, 13.60, 13.95)
    k = Q(t, 197.7, 218.6, 0.8)
    if k > 0:
        titulo(fr, 'DOS SATÉLITES · DOS EQUIPOS', '¿Dicen lo mismo?', CX, 96, k, 'm', 50)
        eje_x(fr, 360, 1560, 580, 13.60, 13.95, 0.05, k, '{:.2f}', True)
        txt(fr, 'edad del universo según cada medición (miles de millones de años)', reg(26), GRIS, CX, 650, k, 'm')
        txt(fr, '←  más joven', reg(26), GRIS, 360, 695, k, 'l')
        txt(fr, 'más viejo  →', reg(26), GRIS, 1560, 695, k, 'r')
        pw = P(t, I('Dicho de otra forma') + 0.3)
        pp = P(t, I('Y Planck, 13 797') + 0.1)
        for yb, c, n, v0, e, pa in ((290, C2, 'WMAP (NASA)', 13.772, 0.059, pw), (440, C1, 'Planck (ESA)', 13.797, 0.023, pp)):
            barra_v(fr, X, yb, v0 - e, v0 + e, c, pa, 30, v0)
            txt(fr, '%s · %s' % (n, ('%.3f' % v0).replace('.', ',')), blk(34), c, X(13.60), yb - 70, pa, 'l')
            txt(fr, 'la barra = margen de error (±%s)' % ('%.3f' % e).replace('.', ','), reg(22), c, X(13.60), yb + 30, pa, 'l')
        c = P(t, I('La diferencia, de unos 25') + 0.5) * (1 - P(t, 218.4, 0.5))
        if c > 0:
            trazo.rrect(fr, (X(13.774) - 6, 250, X(13.831) + 6, 500), 18, HUESO, 2, 0.8 * c)
            txt(fr, 'las barras se solapan → son compatibles', blk(40), HUESO, CX, 520, P(t, I('Son compatibles') + 0.1) * (1 - P(t, 218.4, 0.5)), 'm', 'm')
    u = P(t, 218.9, 0.7)
    if u > 0:
        fr = Image.blend(fr, cielo(t), u)
        txt_glow(fr, 'ΛCDM', blk(150), AMBAR, CX, 300, u * (0.55 + 0.45 * abs(math.sin(t * 2.4))), 'm', 'm')
        txt_glow(fr, 'depende del modelo', blk(70), HUESO, CX, 470, P(t, I('Pero tiene una condición') + 0.1), 'm', 'm')
        s = P(t, I('Porque el segundo reloj') + 0.2)
        reloj(fr, 460, 640, 90, 40 + 28 * t, C1, 0.9 * (1 - s))
        if s > 0:
            reloj(fr, 1460, 640, 90, 30 * t, C2, s, 0.0)
            txt(fr, 'el segundo reloj mira el presente', neg(38), C2, CX, 730, s, 'm')
    return fr


def espiral(fr, cx, cy, r, color, a=1.0, giro=0.0, n=220):
    pts = []
    for i in range(n):
        u = i / (n - 1)
        th = giro + u * 9.5
        rr = r * (0.12 + 0.88 * u)
        pts.append((cx + rr * math.cos(th), cy + rr * math.sin(th) * 0.55))
    trazo.puntos(fr, pts, 3.0, color, 0.9 * a, ss=3)
    pegar(fr, brillo(int(r * 0.9), color), cx, cy, 0.5 * a, 'm', 'm')


def esc_hubble29(t):
    """E15–E16b · 3:54–4:30: 1929, 24 galaxias, factor 7."""
    fr = cielo(t, 1.0)
    if t < 239.8:
        fr = Image.blend(Image.new('RGB', (W, H), (0, 0, 0)), fr, 0.35)
        p = P(t, 234.3, 0.5) * (1 - P(t, 239.4, 0.5))
        txt_glow(fr, '1929', blk(300), AMBAR, CX + 150, CY, p, 'm', 'm')
        espiral(fr, CX - 520, CY, 190, HIELO, p, t * 0.8)
        return fr
    titulo(fr, 'HUBBLE · 1929', 'Cuanto más lejos, más rápido se aleja', CX, 80, P(t, 239.9) * (1 - P(t, 270.0, 0.6)), 'm', 44)
    x0, x1, y0, y1 = 460, 1360, 640, 230
    ax = P(t, 240.5)
    flecha(fr, (x0, y0), (x1 + 40, y0), GRIS, 2, 0.8 * ax)
    flecha(fr, (x0, y0), (x0, y1 - 30), GRIS, 2, 0.8 * ax)
    txt(fr, 'distancia a la galaxia →', reg(26), GRIS, x1 + 40, y0 + 14, ax, 'r')
    txt(fr, 'velocidad con la que se aleja ↑', reg(26), GRIS, x0 - 10, y1 - 70, ax, 'l')
    rng = np.random.RandomState(29)
    pts = []
    for i in range(24):
        d = (i + 1) / 24
        pts.append((x0 + 60 + d * 780, y0 - 30 - d * 330 + rng.randn() * 30 * (0.4 + d * 0.5)))
    n = int(24 * ss((t - 244.2) / 6.0))
    for (x, y) in pts[:n]:
        punto(fr, x, y, 7, HIELO, 1.0, 3.0)
    lin = P(t, 250.6, 1.4)
    linea(fr, [(x0 + 40, y0 - 20), (lerp(x0 + 40, x1 - 40, lin), lerp(y0 - 20, y1 + 20, lin))], AMBAR, 4, lin, 0.5)
    txt(fr, 'tendencia: más lejos, más rápido', neg(28), AMBAR, x1 - 30, y1 - 10, lin, 'r')
    pastilla(fr, '24 GALAXIAS CERCANAS · 1 PUNTO = 1 GALAXIA', 1600, 255, AMBAR, P(t, I('Lo hizo con solo') + 0.2) * (1 - P(t, 262.0, 0.6)), 'm')
    s = I('Pero sus distancias')
    a = P(t, s + 1.0) * (1 - P(t, 262.0, 0.6))
    if a > 0:
        linea(fr, [(x0 + 40, y0 - 20), (x1 - 40, y0 - 20 - (y0 - y1 - 40) / 7)], ROJO, 4, a * 0.9)
        txt_glow(fr, 'las distancias estaban', blk(40), ROJO, 1600, 330, a, 'm', 'm')
        txt_glow(fr, '7 veces mal', blk(70), ROJO, 1600, 395, a, 'm', 'm')
        txt(fr, 'la recta roja es la medida de 1929;', reg(26), HUESO, 1600, 480, a, 'm')
        txt(fr, 'la amarilla, la real', reg(26), HUESO, 1600, 515, a, 'm')
    b = P(t, 262.2, 0.8) * (1 - P(t, 270.3, 0.5))
    if b > 0:
        txt_glow(fr, 'Se corrigen las cifras, no la idea', blk(52), HUESO, CX, 715, b, 'm', 'm')
    ayuda(fr, 'Cada punto es una galaxia: cuanto más lejos está, más rápido se aleja.', P(t, 245.0) * (1 - P(t, 262.0, 0.6)), 700)
    return fr


def esc_pan(t):
    """E17 · 4:30–4:48: el espacio se estira (masa de pan)."""
    fr = cielo(t)
    titulo(fr, 'LA EXPANSIÓN', 'El espacio entre galaxias se estira', CX, 90, P(t, 270.9), 'm', 46)
    e = 1.0 + 0.9 * ss((t - 271.0) / 15.0)
    cx0, cy0 = CX, 520
    gx = [-3, -2, -1, 0, 1, 2, 3]
    for gy in range(-2, 3):
        linea(fr, [(cx0 + x * 150 * e, cy0 + gy * 95 * e) for x in gx], HIELO, 2, 0.30 * Q(t, 271, 288.4, 0.8))
    for x in gx:
        linea(fr, [(cx0 + x * 150 * e, cy0 + gy * 95 * e) for gy in range(-2, 3)], HIELO, 2, 0.30 * Q(t, 271, 288.4, 0.8))
    for x in gx:
        for gy in range(-2, 3):
            if (x + gy) % 2 == 0:
                punto(fr, cx0 + x * 150 * e, cy0 + gy * 95 * e, 9, AMBAR, Q(t, 271, 288.4, 0.8), 3.2)
    h = I('Esa velocidad se llama')
    txt_glow(fr, 'H₀ · constante de Hubble', blk(54), AMBAR, CX, 880, P(t, h + 0.6) * (1 - P(t, 288.0, 0.5)), 'm', 'm')
    return fr


def esc_escalera(t):
    """E18 · 4:48–5:06: la escalera de distancias, con cada peldaño dibujado y explicado."""
    fr = cielo(t)
    titulo(fr, 'COMO SE MIDE', 'La escalera de distancias', CX, 90, P(t, 288.8), 'm', 50)
    tt = t - 289.0
    cols = ((200, 'Estrellas cercanas', 'se miden por paralaje', HIELO, 289.9),
            (720, 'Cefeidas', 'su pulso revela su brillo real', AMBAR, I('Primero, estrellas')),
            (1240, 'Supernovas Ia', 'tan brillantes que se ven muy lejos', VERDE, I('Después, supernovas')))
    notas = ('la estrella parece moverse frente al fondo cuando la Tierra cambia de lado',
             'cuanto más despacio late, más brilla de verdad',
             'una sola brilla como su galaxia entera')
    for i, (x, n, d, c, t0) in enumerate(cols):
        p = ease_out((t - t0) / 0.8)
        if p <= 0.01:
            continue
        y, h = 170 + (2 - i) * 20, 480
        caja(fr, x, y, 480, h, c, 1.0, p, c=18, oscuro=0.6, barra=False)
        tx = clamp((p - 0.4) / 0.5)
        txt(fr, n, blk(36), c, x + 240, y + 36, tx, 'm', 'm')
        txt(fr, d, sl(24), HUESO, x + 240, y + 76, tx, 'm', 'm')
        cx = x + 240
        top = y + 112                       # zona del dibujo: de top a top + 250
        if i == 0:
            # paralaje: la Tierra recorre su órbita; la estrella se proyecta en un punto distinto del fondo lejano
            est = (cx, top + 95)
            fondo_y = top + 18
            sol = (cx, top + 215)
            R = 78
            anillo(fr, sol[0], sol[1], R, GRIS, 0.6 * tx, 2, 0.0)
            punto(fr, sol[0], sol[1], 7, (255, 214, 120), tx, 3.2)
            linea(fr, [(x + 30, fondo_y), (x + 450, fondo_y)], GRIS, 1, 0.5 * tx)
            for k in range(11):
                punto(fr, x + 40 + k * 40, fondo_y, 2.0, GRIS, 0.7 * tx, 0)
            txt(fr, 'estrellas muy lejanas', reg(18), GRIS, x + 240, fondo_y - 24, tx, 'm')
            punto(fr, est[0], est[1], 8, HUESO, tx, 3.4)
            ang = math.sin(tt * 1.1) * 1.2
            for e_ang, etq_ in ((-1.2, 'enero'), (1.2, 'julio')):                  # las dos posiciones extremas, siempre visibles y tenues
                ex, ey = sol[0] + R * math.sin(e_ang), sol[1] - R * math.cos(e_ang) * 0.4
                linea(fr, [(ex, ey), (est[0] + (est[0] - ex) * 0.9, est[1] - (ey - est[1]) * 0.9)], c, 1, 0.35 * tx)
                txt(fr, etq_, reg(18), GRIS, ex, ey + 12, tx, 'm')
            ex, ey = sol[0] + R * math.sin(ang), sol[1] - R * math.cos(ang) * 0.4
            punto(fr, ex, ey, 6, TIERRA_C, tx, 3.0)
            k_ = (fondo_y - ey) / (est[1] - ey)
            px = ex + (est[0] - ex) * k_
            linea(fr, [(ex, ey), (px, fondo_y)], c, 2, 0.9 * tx)
            punto(fr, px, fondo_y, 5, AMBAR, tx, 3.0)
        elif i == 1:
            # cefeida: la estrella late; su curva de luz muestra el ritmo
            per = 2.2
            ph = (tt % per) / per
            r = 30 + 14 * math.sin(2 * math.pi * ph)
            pegar(fr, brillo(int(r * 2.8), c), cx, top + 80, (0.30 + 0.45 * (r - 16) / 28) * tx, 'm', 'm')
            punto(fr, cx, top + 80, r, mezcla(c, HUESO, 0.35), tx, 0)
            base_y, alt = top + 220, 58
            pts = [(x + 50 + k * 5.0, base_y - alt * (0.5 + 0.5 * math.sin(2 * math.pi * (k / 80.0 * 2.0)))) for k in range(81)]
            linea(fr, pts, c, 3, 0.9 * tx)
            cur = x + 50 + 400 * ((tt / per / 2.0) % 1.0)
            linea(fr, [(cur, base_y - alt - 10), (cur, base_y + 12)], HUESO, 2, 0.6 * tx)
            txt(fr, 'brillo en el tiempo', reg(18), GRIS, x + 240, base_y + 24, tx, 'm')
        else:
            # supernova Ia: destello en una galaxia lejana
            espiral(fr, cx, top + 120, 110, HIELO, 0.8 * tx, tt * 0.25)
            fl = max(0.0, math.sin(tt * 1.4)) ** 3
            sx, sy = cx + 62, top + 100
            pegar(fr, brillo(int(34 + 60 * fl), HUESO), sx, sy, (0.5 + 0.5 * fl) * tx, 'm', 'm')
            for k in range(8):
                th = k * math.pi / 4 + 0.3
                linea(fr, [(sx + 8 * math.cos(th), sy + 8 * math.sin(th)), (sx + (22 + 34 * fl) * math.cos(th), sy + (22 + 34 * fl) * math.sin(th))], HUESO, 2, 0.8 * fl * tx)
            txt(fr, 'la explosión (destello) en su galaxia', reg(18), GRIS, cx, top + 246, tx, 'm')
        for j, ln in enumerate(envolver(notas[i], 42)[:2]):
            txt(fr, ln, reg(21), HUESO, cx, y + h - 66 + j * 28, tx, 'm')
    a_ = P(t, 290.5)
    flecha(fr, (220, 718), (1700, 718), GRIS, 2, 0.7 * a_)
    txt(fr, 'más cerca', reg(24), GRIS, 220, 704, a_, 'l')
    txt(fr, 'más lejos', reg(24), GRIS, 1700, 704, a_, 'r')
    s = P(t, I('Cada peldaño') + 0.1)
    txt_glow(fr, 'cada peldaño calibra al siguiente', neg(34), HUESO, CX, 135, s, 'm', 'm')
    return fr


def esc_hubble_imagen(t):
    """E19 · 5:06–5:13: collage real de Hubble (M02) con esquinas redondeadas y borde suave."""
    fr = cielo(t)
    key = ('hub', 1)
    if key not in _CMB:
        _CMB[key] = cargar('M02-hubble-host-galaxies-esa-large.jpg')
    a = Q(t, 306.9, 313.6, 0.6)
    imagen_suave(fr, _CMB[key], CX, 440, 1500, 670, a, z=lerp(1.0, 1.08, P(t, 306.8, 7.0)))
    return fr


def esc_73(t):
    """E20–E21c · 5:13–6:11: 73,04, el reloj al revés, orden de magnitud."""
    fr = cielo(t)
    if t < 323.0:
        p = P(t, 313.6, 0.8) * (1 - P(t, 322.6, 0.6))
        txt_glow(fr, '73,04', blk(240), AMBAR, CX, CY - 60, p, 'm', 'm')
        txt(fr, 'km/s por megaparsec (cefeidas y supernovas)', reg(40), HUESO, CX, CY + 80, p, 'm')
        pastilla(fr, '42 SUPERNOVAS Ia', CX, CY + 150, AMBAR, P(t, I('El equipo SH0ES') + 8.0) * (1 - P(t, 322.6, 0.6)), 'm')
        return fr
    if t < 345.4:
        titulo(fr, 'EL RELOJ AL REVÉS', 'Si la expansión fuera siempre igual…', CX, 70, P(t, 323.2) * (1 - P(t, 345.0, 0.6)), 'm', 46)
        for i, (h0, edad, c, t0) in enumerate((('73,04', '13 400', AMBAR, 326.0), ('67,4', '14 500', C1, I('Pero con la cifra'))), 0):
            p = ease_out((t - t0) / 0.8) * (1 - P(t, 345.0, 0.6))
            if p <= 0.01:
                continue
            x = CX - 430 + i * 860
            caja(fr, x - 340, 200, 680, 450, c, 1.0, p, c=22, oscuro=0.6)
            txt(fr, 'H₀ = ' + h0, blk(54), c, x, 270, p, 'm', 'm')
            txt(fr, 'edad = 977,8 ÷ H₀', reg(34), GRIS, x, 350, p, 'm', 'm')
            txt_glow(fr, edad, blk(120), HUESO, x, 470, p, 'm', 'm')
            txt(fr, 'millones de años', reg(36), HUESO, x, 570, p, 'm', 'm')
        ayuda(fr, 'Una expansión más rápida hoy significa un universo más joven.', P(t, 337.0) * (1 - P(t, 345.0, 0.6)), 690)
        return fr
    if t < 363.0:
        u = P(t, 345.4, 0.7)
        titulo(fr, 'NO ES LA EDAD EXACTA', 'Pero el orden de magnitud está claro', CX, 70, u, 'm', 46)
        X = X_edad(360, 1560, 12.5, 15.0)
        eje_x(fr, 360, 1560, 600, 12.5, 15.0, 0.5, u, '{:.1f}', True)
        txt(fr, 'miles de millones de años', reg(26), GRIS, CX, 650, u, 'm')
        barra_v(fr, X, 430, 13.0, 14.0, C2, P(t, 349.9), 40)
        txt(fr, '13 000 – 14 000 millones de años', blk(46), C2, CX, 350, P(t, 349.9), 'm', 'm')
        m = P(t, I('NASA lo resume igual') + 0.5)
        linea(fr, [(X(13.8), 385), (X(13.8), 560)], HUESO, 3, m)
        txt(fr, 'NASA: ≈ 13 800', neg(36), HUESO, X(13.8) + 16, 500, m, 'l', 'm')
        return fr
    return fr


def esc_guardalas(t):
    fr = cielo(t)
    f = I('Fíjate en esas dos cifras')
    p = P(t, f - 0.1, 0.5) * (1 - P(t, 370.8, 0.6))
    txt_glow(fr, '73', blk(300), AMBAR, CX - 330, CY, p, 'm', 'm')
    txt_glow(fr, '67', blk(300), C1, CX + 330, CY, p, 'm', 'm')
    txt(fr, 'guárdalas', blk(54), HUESO, CX, CY + 220, P(t, I('Pero guárdalas') - 0.2), 'm', 'm')
    return fr


def esc_estrellas(t):
    """E22–E23 · 6:11–6:48: estrellas viejas y 160 de 3 000."""
    fr = cielo(t)
    if t < 398.3:
        titulo(fr, 'RELOJ 3 · LAS ESTRELLAS', 'Las estrellas más viejas', CX, 80, P(t, 371.7), 'm', 48)
        txt(fr, 'El universo no puede ser más joven que sus estrellas más viejas', neg(34), HUESO, CX, 190, P(t, 376.4) * 1.0, 'm')
        rng = np.random.RandomState(3)
        n = 70
        masa = rng.rand(n)
        xs = rng.rand(n) * 1200 + 360
        ys = rng.rand(n) * 400 + 270
        for i in range(n):
            vida = 376.5 + (1 - masa[i]) ** 0.7 * 16
            a = Q(t, 372.0, 1e9, 0.8) * (1 - P(t, vida, 1.5))
            col = mezcla((255, 150, 110), (150, 190, 255), masa[i])
            punto(fr, xs[i] + math.sin(t + i) * 2, ys[i], 4 + masa[i] * 7, col, a, 3.4)
        txt(fr, 'las más masivas se apagan primero', neg(38), HUESO, CX, 700, P(t, I('Las estrellas cambian') + 0.4), 'm', 'm')
        return fr
    titulo(fr, 'GAIA SELECCIONÓ', '160 estrellas muy viejas y fiables', CX, 80, P(t, 398.5), 'm', 46)
    cols, filas = 60, 50
    pts_n, pts_h = [], []
    rng = np.random.RandomState(11)
    elegidas = set(rng.choice(cols * filas, 160, replace=False))
    k = ss((t - 399.0) / 3.0)
    for i in range(cols * filas):
        x = 360 + (i % cols) * 20
        y = 230 + (i // cols) * 9.2
        (pts_h if i in elegidas and t > 402.5 else pts_n).append((x, y))
    trazo.puntos(fr, pts_n, 2.4, HUESO, 0.6 * k, ss=2)
    trazo.puntos(fr, pts_h, 5.2, AMBAR, P(t, 402.5), ss=2)
    txt(fr, '≈ 3 000 candidatas', neg(34), GRIS, 360, 700, k, 'l')
    txt_glow(fr, '160 elegidas', blk(44), AMBAR, 1560, 700, P(t, 402.6), 'r', 'm')
    return fr


def esc_gaia(t):
    """E24 · 6:48–6:57: mapa del cielo de Gaia (M03), recortado a su elipse (sin el rectángulo negro)."""
    fr = cielo(t)
    key = ('gaia', 2)
    w = 1300
    if key not in _CMB:
        im = cargar('M03-gaia-allsky-4k.jpg')
        arr = np.asarray(im.convert('L'))
        ys, xs = np.where(arr > 10)
        im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        h = int(w * im.height / im.width)
        src = im.resize((2000, int(2000 * im.height / im.width)), Image.LANCZOS)
        m = Image.new('L', (w * 2, h * 2), 0)
        ImageDraw.Draw(m).ellipse((4, 4, w * 2 - 5, h * 2 - 5), fill=255)
        _CMB[key] = (src, m.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2)), h)
    src, m, h = _CMB[key]
    a = Q(t, 408.6, 417.7, 0.6)
    z = lerp(1.0, 1.10, P(t, 408.5, 9.0))
    bw, bh = src.width / z, src.height / z
    sub = src.resize((w, h), Image.BICUBIC, box=((src.width - bw) / 2, (src.height - bh) / 2, (src.width + bw) / 2, (src.height + bh) / 2))
    pegar(fr, brillo(560, HIELO), CX, 440, 0.12 * a, 'm', 'm')
    fr.paste(sub, (CX - w // 2, 440 - h // 2), m.point(lambda q: int(q * a)))
    return fr


def esc_limite(t):
    """E25–E26 · 6:57–7:54: límite inferior, 70 estrellas, sin modelo."""
    fr = cielo(t)
    X = X_edad(360, 1560, 12.5, 15.0)
    if t < 429.3:
        titulo(fr, 'RELOJ 3 · EL RESULTADO', 'El universo tiene, como mínimo…', CX, 80, P(t, 417.7), 'm', 46)
        eje_x(fr, 360, 1560, 560, 12.5, 15.0, 0.5, P(t, 418.0), '{:.1f}', True)
        txt(fr, 'miles de millones de años', reg(26), GRIS, CX, 600, P(t, 418.0), 'm')
        a = P(t, I('Su edad media') + 0.2)
        punto(fr, X(13.6), 400, 12, C3, a, 3.2)
        txt(fr, 'edad media de las estrellas: 13,6', neg(32), C3, X(13.6), 345, a, 'm')
        l = P(t, I('De ahí sale un límite') + 1.0)
        trazo.rrect(fr, (X(13.8), 440, X(15.0), 480), 20, HUESO, 2, 0.8 * l)
        txt(fr, 'el universo es más viejo que esto →', reg(26), HUESO, X(13.8), 490, l, 'l')
        txt_glow(fr, 't ≥ 13,8 mil millones de años', blk(54), HUESO, CX, 690, l, 'm', 'm')
        return fr
    if t < 452.1:
        titulo(fr, 'RELOJ 3 · LA DISTRIBUCIÓN', 'Ninguna estrella supera al universo', CX, 80, P(t, 429.5), 'm', 44)
        eje_x(fr, 360, 1560, 600, 12.5, 15.0, 0.5, P(t, 429.7), '{:.1f}', True)
        txt(fr, 'edad de cada estrella (miles de millones de años)', reg(26), GRIS, CX, 650, P(t, 429.7), 'm')
        rng = np.random.RandomState(70)
        edades = np.clip(rng.randn(70) * 0.35 + 13.62, 13.02, 14.08)
        n = int(70 * ss((t - 430.5) / 5.0))
        for i in range(n):
            punto(fr, X(edades[i]), 540 - (i % 7) * 26, 7, C3, 1.0, 3.0)
        linea(fr, [(X(13.0), 270), (X(13.0), 590)], HUESO, 3, 0.7 * P(t, 435))
        txt(fr, '13 000', neg(30), HUESO, X(13.0), 230, P(t, 435), 'm')
        linea(fr, [(X(14.1), 270), (X(14.1), 590)], ROJO, 3, 0.7 * P(t, 441))
        txt(fr, '14 100', neg(30), ROJO, X(14.1), 230, P(t, 441), 'm')
        txt_glow(fr, '70 estrellas > 13 000 millones · ninguna > 14 100', neg(38), HUESO, CX, 715, P(t, I('Con un 90 %') + 4.0), 'm', 'm')
        return fr
    titulo(fr, 'RELOJ 3 · SU VENTAJA', 'No usa ningún modelo cosmológico', CX, 80, P(t, 452.3), 'm', 46)
    s = P(t, I('Pero tiene una ventaja') + 0.5)
    caja(fr, CX - 520, 230, 1040, 200, C3, 1.0, s, c=24, oscuro=0.6)
    txt_glow(fr, 'SIN MODELO COSMOLÓGICO', blk(64), C3, CX, 330, s, 'm', 'm')
    j = P(t, I('Tres relojes.') - 0.3)
    for i, (x, c) in enumerate(((CX - 400, C1), (CX, C2), (CX + 400, C3))):
        reloj(fr, x, 570, 80, 30 * t * (1 + 0.1 * i), c, j, 0.0)
    txt(fr, 'tres caminos distintos', neg(38), HUESO, CX, 690, P(t, I('Tres caminos') - 0.2), 'm')
    return fr


def esc_coinciden(t):
    """E27–E28 · 7:54–8:16: los tres relojes alrededor de 13,8 y «pero hay un problema»."""
    fr = cielo(t)
    X = X_edad(360, 1560, 12.5, 15.0)
    if t < 492.0:
        titulo(fr, 'TRES RELOJES JUNTOS', 'Señalan la misma zona', CX, 80, P(t, 474.3), 'm', 50)
        eje_x(fr, 360, 1560, 600, 12.5, 15.0, 0.5, P(t, 474.4), '{:.1f}', True)
        txt(fr, 'edad del universo (miles de millones de años)', reg(26), GRIS, CX, 650, P(t, 474.4), 'm')
        trazo.rrect(fr, (X(13.5), 215, X(14.1), 570), 24, AMBAR, 2, 0.8 * P(t, 484), relleno=False)
        for yb, c, n, v0, v1, cen, key in ((290, C1, 'luz más antigua', 13.797 - 0.023, 13.797 + 0.023, 13.797, 'Un reloj basado'),
                                           (410, C2, 'velocidad de expansión', 13.0, 14.5, None, 'Otro, en la velocidad'),
                                           (530, C3, 'estrellas más viejas', 13.8, 15.0, None, 'Otro, en las estrellas')):
            pa = P(t, I(key))
            barra_v(fr, X, yb, v0, v1, c, pa, 30, cen)
            txt(fr, n, neg(30), c, X(12.5), yb - 56, pa, 'l')
        txt_glow(fr, 'la franja ámbar: ≈ 13 800 millones de años', blk(42), AMBAR, CX, 700, P(t, I('Cada uno con su margen') + 4.0), 'm', 'm')
        return fr
    u = P(t, 492.4, 0.5)
    fr = Image.blend(Image.new('RGB', (W, H), (0, 0, 0)), cielo(t), 0.15 + 0.1 * u)
    txt_glow(fr, '67,4', blk(230), C1, CX - 470, CY - 20, u, 'm', 'm')
    txt_glow(fr, '73,04', blk(230), AMBAR, CX + 450, CY - 20, P(t, 493.3), 'm', 'm')
    txt(fr, 'Pero hay un problema', blk(54), HUESO, CX, 690, P(t, 492.2), 'm', 'm')
    return fr


def esc_tension(t):
    """E29–E33 · 8:16–9:48: tensión de Hubble, qué se compara, Riess/Webb, ACT, Freedman."""
    fr = cielo(t)
    X = X_edad(360, 1560, 64.0, 76.0)

    def grafico(fr, a, con_medias=True):
        eje_x(fr, 360, 1560, 670, 64.0, 76.0, 2.0, a, '{:.0f}', True)
        txt(fr, 'velocidad de expansión H₀ (km/s por megaparsec)', reg(26), GRIS, CX, 722, a, 'm')
        txt(fr, '←  más lenta', reg(24), GRIS, 360, 715 + 0, a * 0, 'l')

    if t < 551.7:
        pa = P(t, 497.2)
        pb = P(t, I('Y las cefeidas dan') + 0.1)
        c = P(t, I('Esa diferencia es de un 8 %') + 0.4)
        # E29 y E30 (hasta 524,6): la gráfica de las dos medidas con el título «tensión de Hubble»
        gr = P(t, 496.8, 0.5) * (1 - P(t, 524.6, 0.6))
        if gr > 0:
            ttl = 'Dos medidas que no se tocan' if t < 518.9 else 'TENSIÓN DE HUBBLE'
            titulo(fr, 'LA TENSIÓN DE HUBBLE' if t < 518.9 else 'ESTO SE LLAMA', ttl, CX, 70, gr, 'm', 50)
            grafico(fr, gr)
            barra_v(fr, X, 450, 67.4 - 0.5, 67.4 + 0.5, C1, pa * gr, 34, 67.4)
            txt(fr, 'Planck · 67,4 ± 0,5', blk(32), C1, X(67.4), 390, pa * gr, 'm')
            barra_v(fr, X, 450, 73.04 - 1.04, 73.04 + 1.04, C2, pb * gr, 34, 73.04)
            txt(fr, 'cefeidas · 73,04 ± 1,04', blk(32), C2, X(73.04), 390, pb * gr, 'm')
            if c > 0:
                linea(fr, [(X(67.9), 520), (X(72.0), 520)], HUESO, 3, c * gr)
                txt_glow(fr, '≈ 8 %', blk(64), HUESO, CX, 535, c * gr, 'm', 'm')
                txt(fr, '≈ 5 veces el margen de error', neg(34), HUESO, CX, 610, P(t, I('Esa diferencia es de un 8 %') + 3.5) * gr, 'm', 'm')
        if t >= 521.5:
            u = P(t, 524.0, 0.8)
            fr2 = cielo(t)
            titulo(fr2, 'QUÉ SE COMPARA', 'TENSIÓN DE HUBBLE', CX, 70, u, 'm', 56)
            pq = P(t, 521.9, 0.6) * (1 - P(t, 524.6, 0.5))
            qq = P(t, 525.0, 0.6) * (1 - P(t, 532.0, 0.5))
            txt_glow(fr2, '«no son dos experimentos que discrepan;', blk(52), HUESO, CX, 340, qq, 'm', 'm')
            txt_glow(fr2, 'se está midiendo algo distinto»', blk(52), AMBAR, CX, 410, qq, 'm', 'm')
            txt(fr2, 'Adam Riess · NASA, 2019', reg(28), GRIS, CX, 480, qq, 'm')
            q1 = P(t, I('Una medición dice') + 0.2)
            q2 = P(t, I('La otra es una predicción') + 0.2)
            caja(fr2, 200, 220, 600, 330, C2, 1.0, q1, c=20, oscuro=0.6)
            txt(fr2, 'HOY', blk(48), C2, 500, 280, q1, 'm', 'm')
            txt(fr2, 'una medición', reg(34), HUESO, 500, 350, q1, 'm', 'm')
            txt(fr2, '73,04', blk(100), HUESO, 500, 460, q1, 'm', 'm')
            caja(fr2, 1120, 220, 600, 330, C1, 1.0, q2, c=20, oscuro=0.6)
            txt(fr2, 'UNIVERSO TEMPRANO', blk(40), C1, 1420, 280, q2, 'm', 'm')
            txt(fr2, 'una predicción', reg(34), HUESO, 1420, 350, q2, 'm', 'm')
            txt(fr2, '67,4', blk(100), HUESO, 1420, 460, q2, 'm', 'm')
            br = P(t, 543.9, 0.8)
            txt_glow(fr2, '?', blk(150), HUESO, CX, 385, br * (0.6 + 0.4 * math.sin(t * 5)), 'm', 'm')
            txt(fr2, 'el puente entre las dos épocas', neg(38), HUESO, CX, 640, br, 'm', 'm')
            fr = Image.blend(fr, fr2, u)
        return fr
    if t < 577.3:
        titulo(fr, '¿UN ERROR DE MEDICIÓN?', 'Eso fue lo primero que se pensó', CX, 70, P(t, 551.9), 'm', 48)
        a = P(t, 552.0) * (1 - P(t, 563.8, 0.5))
        txt(fr, 'error de medición', blk(70), GRIS, CX, 330, a, 'm', 'm')
        w = sprite_texto('error de medición', blk(70), GRIS)[1].size[0]
        s = P(t, 556.5, 0.8)
        linea(fr, [(CX - w / 2, 330), (CX - w / 2 + w * s, 330)], ROJO, 6, a)
        if t < 564.3:
            pastilla(fr, 'WEBB + HUBBLE · 2024', CX, 470, AMBAR, P(t, 556.0), 'm')
            txt(fr, 'descartado con muy alta confianza', neg(42), HUESO, CX, 570, P(t, I('En 2024, con el telescopio') + 3.0), 'm', 'm')
        else:
            txt_glow(fr, 'ACT (Chile) · noviembre de 2025', blk(52), HUESO, CX, 470, P(t, 564.5), 'm', 'm')
            txt(fr, 'confirma el valor de Planck con otra técnica', neg(40), C1, CX, 560, P(t, 567.0), 'm', 'm')
            txt(fr, 'la discrepancia es aún más sólida', reg(38), HUESO, CX, 630, P(t, 571.5), 'm', 'm')
        return fr
    titulo(fr, 'OTRO EQUIPO · OTRAS ESTRELLAS', 'Un valor intermedio', CX, 70, P(t, 577.5), 'm', 50)
    eje_x(fr, 360, 1560, 670, 64.0, 76.0, 2.0, 1.0, '{:.0f}', True)
    txt(fr, 'velocidad de expansión H₀ (km/s por megaparsec)', reg(26), GRIS, CX, 722, 1.0, 'm')
    barra_v(fr, X, 460, 67.4 - 0.5, 67.4 + 0.5, C1, 0.8, 34, 67.4)
    txt(fr, 'Planck 67,4', neg(28), C1, X(67.4), 410, 0.8, 'm')
    barra_v(fr, X, 460, 73.04 - 1.04, 73.04 + 1.04, C2, 0.8, 34, 73.04)
    txt(fr, 'cefeidas 73,04', neg(28), C2, X(73.04), 410, 0.8, 'm')
    m = P(t, I('Otro grupo, con otro tipo') + 4.0)
    punto(fr, X(70.39), 460, 14, C3, m, 3.5)
    txt_glow(fr, '70,39', blk(64), C3, X(70.39), 320, m, 'm', 'm')
    txt(fr, 'Freedman 2025 · estrellas gigantes rojas', neg(28), C3, X(70.39), 540, m, 'm')
    return fr


def esc_en_juego(t):
    """E34 · 9:48–10:06: casi 1 000 millones de años."""
    fr = cielo(t)
    titulo(fr, 'LO QUE ESTÁ EN JUEGO', '¿Importa?', CX, 80, P(t, 588.3), 'm', 54)
    X = X_edad(360, 1560, 12.4, 14.2)
    eje_x(fr, 360, 1560, 600, 12.4, 14.2, 0.2, P(t, 588.8), '{:.1f}', True)
    txt(fr, 'edad del universo (miles de millones de años)', reg(26), GRIS, CX, 650, P(t, 588.8), 'm')
    a = P(t, I('Con el mismo modelo') + 0.2)
    punto(fr, X(13.8), 430, 14, AMBAR, a, 3.5)
    txt(fr, '13 800 (si todo va bien)', blk(40), AMBAR, X(13.8), 370, a, 'm')
    b = P(t, I('Con el mismo modelo') + 5.0)
    barra_v(fr, X, 430, 12.7, 12.9, HIELO, b, 34)
    txt(fr, '12 700 – 12 900 (si gana la medida local)', blk(34), HIELO, X(12.8), 370, b, 'm')
    g = P(t, I('La diferencia es de casi'))
    linea(fr, [(X(12.9), 500), (X(13.8), 500)], AMBAR, 5, g, 0.5)
    txt_glow(fr, 'casi 1 000 millones de años', blk(56), AMBAR, CX, 525, g, 'm', 'm')
    return fr


def esc_niveles(t):
    """E35–E36 · 10:06–10:51: comprobado, probable, sin resolver."""
    fr = cielo(t)
    titulo(fr, 'LO QUE SE SABE Y LO QUE NO', '¿Qué sabemos de verdad?', CX, 70, P(t, 606.8), 'm', 50)
    filas = (('Comprobado', 'tres métodos independientes: 13 000 – 14 000 millones; la tensión es real', VERDE, I('Comprobado'), 'ok'),
             ('Probable', 'unos 13 800 millones, si el modelo estándar es correcto', AMBAR, I('Probable'), 'prob'),
             ('Sin resolver', '¿por qué no coinciden? ¿falta algo en el modelo?', ROJO, I('Sin resolver'), 'sin'))
    for i, (n, d, c, t0, ic) in enumerate(filas):
        p = ease_out((t - t0) / 0.8)
        if p <= 0.01:
            continue
        y = 240 + i * 170
        foco = (i == 2 and t > 631.3)
        caja(fr, 220, y, 1480, 150, c, 1.0, p, c=20, oscuro=0.6)
        tx = clamp((p - 0.35) / 0.55)
        cx, cy = 320, y + 75
        if ic == 'ok':
            icono_hex(fr, cx, cy, 34, c, tx, 'check', 3)
        elif ic == 'prob':
            anillo_arco(fr, cx, cy, 32, c, 0.66 * tx, tx, 5, -90, 0.25)
        else:
            anillo_arco(fr, cx, cy, 32, c, 1.0, tx, 5, -90, 0.25, True)
        pegar(fr, sprite_texto(n, blk(42), c), 396, y + 16, tx)
        for j, ln in enumerate(envolver(d, 76)[:2]):
            pegar(fr, sprite_texto(ln, sl(30), HUESO), 396, y + 76 + j * 36, tx)
        if foco:
            trazo.rrect(fr, (216, y - 4, 1704, y + 154), 22, c, 3, 0.4 + 0.4 * math.sin(t * 4))
    return fr


def esc_cierre(t):
    """E37–E39 · 10:51–fin: nadie estuvo allí, pregunta y pantalla final (con like, comentario y campanita)."""
    fr = cielo(t)
    if t < 678.8:
        pq = P(t, 651.1, 0.6) * (1 - P(t, 655.2, 0.5))
        txt_glow(fr, '¿Cómo sabemos la edad del universo', blk(62), HUESO, CX, 430, pq, 'm', 'm')
        txt_glow(fr, 'si nadie estuvo allí?', blk(62), AMBAR, CX, 510, pq, 'm', 'm')
        txt_glow(fr, 'Nadie estuvo allí.', blk(84), HUESO, CX, 190, P(t, I('Nadie estuvo allí.')), 'm', 'm')
        txt_glow(fr, 'Pero el universo dejó pruebas.', blk(70), AMBAR, CX, 290, P(t, I('Pero el universo dejó')), 'm', 'm')
        for i, (n, d, c, t0) in enumerate((('una luz', 'que todavía nos llega', C1, I('Una luz que')), ('una expansión', 'que todavía podemos medir', C2, I('Una expansión que')), ('estrellas', 'que todavía brillan', C3, I('Estrellas que')))):
            p = P(t, t0, 0.7)
            x = CX - 520 + i * 520
            reloj(fr, x, 520, 90, 30 * t * (1 + 0.1 * i), c, p, 0.0)
            txt(fr, n, blk(40), c, x, 630, p, 'm')
            txt(fr, d, reg(30), HUESO, x, 680, p, 'm')
        s = P(t, I('Tres relojes que no') + 0.4)
        txt(fr, 'tres relojes que no se hablan entre sí', neg(38), HUESO, CX, 400 if False else 740, s, 'm', 'm')
        return fr
    if t < 694.3:
        titulo(fr, 'AHORA TÚ', 'Si tuvieras que apostar…', CX, 130, P(t, 679.0), 'm', 54)
        txt_glow(fr, '¿Un error de medición', blk(70), HUESO, CX, 400, P(t, I('Si tuvieras que apostar') + 1.0), 'm', 'm')
        txt_glow(fr, 'o un modelo incompleto?', blk(70), AMBAR, CX, 490, P(t, I('Si tuvieras que apostar') + 4.0), 'm', 'm')
        txt(fr, 'cuéntamelo en los comentarios', reg(40), HUESO, CX, 640, P(t, I('Cuéntamelo')), 'm', 'm')
        return fr
    titulo(fr, 'REFERENCIAS', 'Fuentes', CX, 50, P(t, 694.6), 'm', 46)
    nombres = ('Planck 2018 (A&A 641) · ESA', 'WMAP 9 años (Hinshaw et al.) · NASA', 'Riess et al. 2022 · ApJ Letters', 'Freedman et al. 2025 · ApJ 985, 203',
               'Tomasetti et al. 2026 · A&A 707, A111', 'ACT · JCAP, nov-2025', 'Bahcall 2015 · PNAS 112', 'Mapa del cielo: ESA/Gaia/DPAC, CC BY-SA 3.0 IGO')
    for i, n in enumerate(nombres):
        p = ease_out((t - (694.8 + i * 0.3)) / 0.5)
        if p <= 0.01:
            continue
        y = 150 + i * 46
        caja(fr, 560, y, 800, 38, AMBAR, 1.0, p, c=9, oscuro=0.6, barra=False)
        tx = clamp((p - 0.3) / 0.6)
        icono_hex(fr, 590, y + 19, 7, AMBAR, tx, 'check', 2)
        pegar(fr, sprite_texto(n, neg(22), HUESO), 614, y + 19, tx, 'l', 'm')
    txt(fr, 'Los enlaces están en la descripción', sl(26), GRIS, CX, 530, P(t, 698.0), 'm')
    b0 = I('Y si te gustó')
    botones = (('campana', 'SUSCRÍBETE', True, b0 + 1.0), ('like', 'ME GUSTA', False, b0 + 2.6), ('campana', 'ACTIVA LA CAMPANITA', False, b0 + 4.0))
    anchos = [360, 300, 500]
    xtot = sum(anchos) + 30 * (len(anchos) - 1)
    x = CX - xtot // 2
    for (tipo, texto, prim, t0), wd in zip(botones, anchos):
        a = P(t, t0, 0.5)
        if a > 0:
            caja(fr, x, 590, wd, 86, AMBAR if prim else HUESO, 1.0, a, c=16, oscuro=0.6, barra=False)
            icono_cta(fr, tipo, x + 46, 633, 30, AMBAR if prim else HUESO, a)
            txt(fr, texto, blk(28), AMBAR if prim else HUESO, x + 82, 633, a, 'l', 'm')
        x += wd + 30
    txt(fr, 'cada semana, una pregunta, con sus datos y de dónde salen', reg(30), HUESO, CX, 705, P(t, b0 + 1.0), 'm')
    return fr


# ------------------------------------------------------------------ guion de escenas
def B(fn, k=0.28):
    return lambda t: bloom(fn(t), k)


ESCENAS = [
    (0.0, 56.4, esc_gancho),
    (56.4, 91.7, esc_medir),
    (91.7, 124.2, esc_niebla),
    (124.2, 154.6, esc_cmb),
    (154.6, 178.3, esc_dos_puntos),
    (178.3, 197.5, esc_wmap),
    (197.5, 234.2, esc_compatibles),
    (234.2, 270.7, esc_hubble29),
    (270.7, 288.6, esc_pan),
    (288.6, 306.8, esc_escalera),
    (306.8, 313.5, esc_hubble_imagen),
    (313.5, 363.0, esc_73),
    (363.0, 371.4, esc_guardalas),
    (371.4, 408.5, esc_estrellas),
    (408.5, 417.5, esc_gaia),
    (417.5, 474.1, esc_limite),
    (474.1, 496.7, esc_coinciden),
    (496.7, 588.2, esc_tension),
    (588.2, 606.6, esc_en_juego),
    (606.6, 650.9, esc_niveles),
    (650.9, DURACION, esc_cierre),
]
ESCENAS = [(a, b, B(fn)) for a, b, fn in ESCENAS]
XF = 0.7

CREDITOS = [
    (178.3, 197.5, 'NASA / WMAP Science Team'),
    (306.8, 313.7, 'NASA, ESA, Adam G. Riess (STScI, JHU)'),
    (408.5, 417.8, 'ESA/Gaia/DPAC · CC BY-SA 3.0 IGO'),
]

CAPITULOS_B = [(56.4, 2, 'Qué estamos midiendo'), (91.7, 3, 'Reloj 1: la luz'), (234.2, 4, 'Reloj 2: la expansión'), (371.4, 5, 'Reloj 3: las estrellas'),
               (474.1, 6, '¿Coinciden?'), (588.2, 7, 'Lo que está en juego'), (606.6, 8, 'Lo que no sabemos')]

ROTULOS = [
    (10.0, 18.8, 'Edad del universo: 13,797 ± 0,023 miles de millones de años', 'Fuente: Planck 2018 (A&A 641) · modelo ΛCDM', 'dato'),
    (19.0, 22.2, '0,023 ÷ 13,797 ≈ 0,0017 → 0,17 %', 'Cálculo propio', 'calculo'),
    (I('Cuando decimos') + 0.4, I('Hablamos del tiempo') + 6.5, 'Edad = tiempo desde un estado muy denso y muy caliente', 'Fuente: ESA · modelo del Big Bang', 'dato'),
    (I('Imagina estar dentro'), I('Imagina estar dentro') + 8.0, 'El fondo cósmico se formó ≈ 380 000 años después del Big Bang', 'Fuente: ESA · Planck', 'dato'),
    (I('Esa luz sigue'), I('Esa luz sigue') + 7.0, 'Temperatura actual del fondo cósmico: 2,726 K (≈ −270 °C)', 'Fuente: ESA (medida por COBE y WMAP)', 'dato'),
    (I('La misión Planck') + 0.2, I('La misión Planck') + 7.0, 'Planck: lanzada en 2009 · 4,5 años de observación', 'Fuente: ESA', 'dato'),
    (I('En 2013, los primeros') + 0.2, I('En 2013, los primeros') + 6.0, 'Primeros datos de Planck (2013): 13,82 miles de millones de años', 'Fuente: ESA', 'dato'),
    (I('Antes, el satélite') + 0.4, I('Antes, el satélite') + 11.0, 'WMAP (NASA), 9 años: 13,772 ± 0,059 miles de millones de años', 'Fuente: Hinshaw et al. 2013, ApJS 208, 19', 'dato'),
    (I('La diferencia, de unos 25') + 0.3, I('La diferencia, de unos 25') + 8.0, 'Margen conjunto: √(0,059² + 0,023²) ≈ 0,063', 'Cálculo propio · 13,772 ± 0,059 frente a 13,797 ± 0,023', 'calculo'),
    (I('Lo hizo con solo') + 0.2, I('Lo hizo con solo') + 8.5, 'Hubble, 1929: 24 galaxias · distancias ≈ 7 veces demasiado pequeñas', 'Fuente: N. A. Bahcall, PNAS 112 (2015)', 'dato'),
    (I('El equipo SH0ES') + 7.4, I('El equipo SH0ES') + 16.0, 'H₀ = 73,04 ± 1,04 km/s/Mpc · 42 supernovas Ia', 'Fuente: Riess et al. 2022, ApJ Letters 934, L7', 'dato'),
    (I('Si la expansión hubiera') + 1.0, I('Si la expansión hubiera') + 9.5, '1 ÷ H₀ ≈ 13 400 millones de años (H₀ = 73,04)', 'Cálculo propio: 977,8 ÷ H₀', 'calculo'),
    (I('Pero con la cifra') + 3.0, I('Pero con la cifra') + 7.2, '977,8 ÷ 67,4 ≈ 14 500 millones de años', 'Cálculo propio · H₀ de Planck: 67,4 ± 0,5', 'calculo'),
    (I('NASA lo resume igual') + 0.3, I('NASA lo resume igual') + 5.8, 'Con H₀ entre ≈ 70 y 76, la edad ronda los 13 800 millones', 'Fuente: NASA · «The Hubble Constant and Hubble Tension»', 'dato'),
    (I('En marzo de 2026') + 1.0, I('En marzo de 2026') + 11.5, '160 estrellas de unas 3 000 candidatas de Gaia DR3', 'Fuente: Tomasetti et al. 2026, A&A 707, A111', 'dato'),
    (I('De ahí sale un límite') + 0.4, I('De ahí sale un límite') + 9.0, 't ≥ 13,8 ± 1,0 (estad.) ± 1,4 (sist.) miles de millones de años', 'Fuente: Tomasetti et al. 2026, A&A 707, A111', 'dato'),
    (I('Con un 90 %') + 0.4, I('Con un 90 %') + 10.0, 'Al 90 %: 70 estrellas > 13 000 millones · ninguna > 14 100', 'Fuente: Tomasetti et al. 2026', 'dato'),
    (I('Con la misma historia') + 0.4, I('Con la misma historia') + 8.0, 'H₀ de Planck: 67,4 ± 0,5 km/s/Mpc', 'Fuente: Planck Collaboration 2018, A&A 641, A6', 'dato'),
    (I('Esa diferencia es de un 8 %') + 0.3, I('Esa diferencia es de un 8 %') + 7.5, '5,64 ÷ 1,15 ≈ 4,9 veces el margen de error', 'Cálculo propio', 'calculo'),
    (I('Uno de los investigadores') + 0.3, I('Uno de los investigadores') + 7.0, '«No son dos experimentos que discrepan»', 'Adam Riess (STScI y Univ. Johns Hopkins) · NASA, 25-abr-2019', 'dato'),
    (I('En 2024, con el telescopio') + 0.3, I('En 2024, con el telescopio') + 8.0, 'Con Webb y Hubble se descarta un error de medición', 'Fuente: NASA, 11-mar-2024', 'dato'),
    (I('Y en noviembre de 2025') + 0.5, I('Y en noviembre de 2025') + 11.0, 'ACT confirma el valor de Planck · tensión «aún más robusta»', 'Fuente: ACT Collaboration (JCAP, nov-2025) · C. Hill, Univ. de Columbia', 'dato'),
    (I('Otro grupo, con otro tipo') + 0.3, I('Otro grupo, con otro tipo') + 10.5, 'H₀ = 70,39 ± 1,22 (est.) ± 1,33 (sist.) km/s/Mpc', 'Fuente: Freedman et al. 2025, ApJ 985, 203', 'dato'),
    (I('Con el mismo modelo') + 1.0, I('Con el mismo modelo') + 11.5, 'Con la expansión local en todo el pasado: ≈ 12 700–12 900 millones', 'Cálculo propio · modelo plano, Ωm entre 0,30 y 0,315', 'calculo'),
    (I('El propio Riess') + 0.3, I('El propio Riess') + 8.5, '«Probabilidad muy fuerte de que falte algo en el modelo»', 'Adam Riess · NASA, 25-abr-2019', 'dato'),
]
ROTULOS = [r for r in ROTULOS if r[1] > r[0]]

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
SUBS_QUEMADOS = os.environ.get('HE_SUBS', '0') == '1'
NOMBRE = 'video-02-con-subtitulos' if SUBS_QUEMADOS else 'video-02-completo'


def dibujar_subtitulo(fr, t):
    from estilo import _mascara
    for txt_, a, b in SUBS:
        if a - 0.05 <= t <= b + 0.15:
            sp = [sprite_texto(l, reg(42), HUESO) for l in envolver(txt_)]
            ancho = max(s[1].size[0] for s in sp) + 60
            alto = sum(s[1].size[1] for s in sp) + 22
            y0 = 1080 - 52 - alto
            x0 = (W - ancho) // 2
            fr.paste(Image.new('RGB', (ancho, alto), (4, 6, 16)), (x0, y0), _mascara(ancho, alto, 16).point(lambda v: int(v * 0.62)))
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
    _T[0] = t
    capas = []
    n = len(ESCENAS)
    for i, (a, b, fn) in enumerate(ESCENAS):
        ini = a - XF / 2 if i else -1e9
        fin = b - XF / 2 if i < n - 1 else 1e9
        al = clamp((t - ini) / XF) if i else 1.0
        if i < n - 1:
            al *= 1 - clamp((t - fin) / XF)
        if al > 0:
            capas.append((al, fn))
    fr = capas[0][1](t)
    for al, fn in capas[1:]:
        fr = Image.blend(fr, fn(t), al) if al < 1 else fn(t)
    # sin marco de esquinas (decisión del 14-oct-2026)
    vis = [c for c in CREDITOS if aparecer(t, c[0] + 0.4, c[1] - 0.2, 0.5) > 0]
    for k, (a, b, texto) in enumerate(vis):
        credito(fr, texto, aparecer(t, a + 0.4, b - 0.2, 0.5), k)
    for r in ROTULOS:
        rotulo(fr, t, r[0], r[1], r[2], r[3], r[4])
    for ini_c, num_c, tit_c in CAPITULOS_B:
        from ui import capitulo
        capitulo(fr, t, ini_c + 0.4, num_c, tit_c)
    cta(fr, t, 300.0, 307.0) if False else None
    if SUBS_QUEMADOS:
        dibujar_subtitulo(fr, t)
    k = clamp((t - (DURACION - 1.2)) / 1.2)
    if k > 0:
        fr = Image.blend(fr, NEGRO, k)
    return fr


def _caja_rotulo(t, r):
    """Caja (x0, y0, x1, y1) del rótulo si está visible en el instante t (misma geometría que ui.rotulo)."""
    ini, fin = r[0], r[1]
    dur = fin - ini
    din, dout = min(1.3, 0.22 * dur), min(1.0, 0.18 * dur)
    p = ss((t - ini) / din) * (1 - ss((t - (fin - dout)) / dout))
    if p <= 0.35:
        return None
    from ui import _contenido_rotulo
    w, h = _contenido_rotulo(r[2], r[3], r[4])[:2]
    return (96, 912 - h, 96 + w, 912)


def cajas_overlay(t):
    """Cajas fijas que ocupan rótulos, créditos y tarjetas de capítulo en el instante t."""
    cajas = []
    for r in ROTULOS:
        c = _caja_rotulo(t, r)
        if c:
            cajas.append(('rótulo', c))
    vis = [c for c in CREDITOS if aparecer(t, c[0] + 0.4, c[1] - 0.2, 0.5) > 0.35]
    for k, (a, b, texto) in enumerate(vis):
        w = sprite_texto(texto, reg(21), HUESO)[1].size[0] + 110
        cajas.append(('crédito', (W - 96 - w, 40 + 32 * k, W - 96, 76 + 32 * k)))
    for ini_c, num_c, tit_c in CAPITULOS_B:
        din, dout = 0.9, 0.7
        p = ss((t - (ini_c + 0.4)) / din) * (1 - ss((t - (ini_c + 0.4 + 4.8 - dout)) / dout))
        if p > 0.35:
            w = int(max(130, sprite_texto(tit_c, neg(30), HUESO)[1].size[0]) + 118)
            cajas.append(('capítulo', (W - 96 - w, 124, W - 96, 216)))
    return cajas


def escena_sin_overlays(t):
    capas = []
    n = len(ESCENAS)
    for i, (a, b, fn) in enumerate(ESCENAS):
        ini = a - XF / 2 if i else -1e9
        fin = b - XF / 2 if i < n - 1 else 1e9
        al = clamp((t - ini) / XF) if i else 1.0
        if i < n - 1:
            al *= 1 - clamp((t - fin) / XF)
        if al > 0:
            capas.append((al, fn))
    fr = capas[0][1](t)
    for al, fn in capas[1:]:
        fr = Image.blend(fr, fn(t), al) if al < 1 else fn(t)
    return fr


def verificar(paso=1.0, umbral=140):
    """Regla «nada se tapa con nada»: lista los instantes en que el contenido de la escena invade un rótulo, crédito o tarjeta de capítulo."""
    malos = []
    t = 1.0
    while t < DURACION - 1:
        _T[0] = t
        cajas = cajas_overlay(t)
        if cajas:
            esc = np.asarray(escena_sin_overlays(t), np.int16)
            bg = np.asarray(fondo_cosmico(t), np.int16)
            tinta = np.abs(esc - bg).max(axis=2) > 70
            for nombre, (x0, y0, x1, y1) in cajas:
                x0, y0, x1, y1 = max(0, int(x0) - 8), max(0, int(y0) - 8), min(W, int(x1) + 8), min(H, int(y1) + 8)
                n = int(tinta[y0:y1, x0:x1].sum())
                if n > umbral:
                    malos.append((round(t, 1), nombre, n, (x0, y0, x1, y1)))
        t += paso
    return malos


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
# Pistas de la Biblioteca de audio de YouTube (sin atribución). Se buscan en «musica/» por el nombre. Tramos: (pista, inicio del tramo)
MUSICA = ['Singularity', 'Event Horizon']
CAMBIO_MUSICA = 234.2        # Reloj 2: entra la segunda pista


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
    cadena = '[1:a]aresample=48000,aloop=loop=-1:size=2e9,atrim=0:{a:.2f}[m1];'.format(a=CAMBIO_MUSICA + 4)
    cadena += '[2:a]aresample=48000,aloop=loop=-1:size=2e9,atrim=0:{b:.2f}[m2];'.format(b=d - CAMBIO_MUSICA + 4)
    cadena += '[m1][m2]acrossfade=d=4:c1=tri:c2=tri[m12];'
    cadena += '[m12]loudnorm=I=-24:TP=-3:LRA=7,atrim=0:{d:.2f},afade=t=in:d=3,afade=t=out:st={s:.2f}:d=4[mus];'.format(d=d, s=d - 4)
    cadena += '[0:a]aresample=48000,asplit=2[voz1][voz2];[mus][voz1]sidechaincompress=threshold=0.015:ratio=6:attack=30:release=600[duck];'
    cadena += '[duck][voz2]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=11[out]'
    salida = os.path.join(AQUI, 'salida', '_audio-con-musica.wav')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + ent + ['-filter_complex', cadena, '-map', '[out]', '-ac', '2', salida], check=True)
    return salida


def preparar_voz():
    wav = os.path.join(AQUI, 'salida', '_audio-completo.wav')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', AUDIO, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,apad=pad_dur={}'.format(COLA), '-t', str(DURACION), '-ac', '1', wav], check=True)
    return wav


def main():
    os.makedirs(os.path.join(AQUI, 'salida'), exist_ok=True)
    a = sys.argv[1:]
    if len(a) >= 3 and a[0] == '--frame':
        fotograma(float(a[1])).save(a[2])
        return
    tmp = os.path.join(AQUI, 'salida', '_partes')
    if a and a[0] == '--solo-audio':        # cambia la música sin volver a renderizar el video
        wav = mezclar_musica(preparar_voz())
        final = os.path.join(AQUI, 'salida', NOMBRE + '.mp4')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', os.path.join(tmp, 'lista.txt'), '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', final], check=True)
        print('listo:', final)
        return
    if a and a[0] == '--verificar':
        malos = verificar(float(a[1]) if len(a) > 1 else 1.0)
        for m in malos:
            print('SOLAPE', m)
        print('total solapes:', len(malos))
        return
    if len(a) >= 4 and a[0] == '--rango':
        render_rango(int(a[1]), int(a[2]), a[3])
        return
    total = int(DURACION * FPS)
    partes = int(a[0]) if a else 4
    paso = -(-total // partes)
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
    open(lista, 'w').write(''.join("file '{}'\n".format(x.replace(os.sep, '/')) for x in archivos))
    wav = mezclar_musica(preparar_voz())
    escribir_srt(os.path.join(AQUI, 'salida', NOMBRE + '.srt'))
    final = os.path.join(AQUI, 'salida', NOMBRE + '.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lista, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', final], check=True)
    print('listo:', final)


if __name__ == '__main__':
    main()
