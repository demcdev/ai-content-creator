#!/usr/bin/env python3
"""Miniaturas del video 1 (1280×720), con el estilo del canal. Todo propio salvo la ilustración PIA26353 (NASA/JPL-Caltech).

  python miniaturas.py        -> ../Miniaturas/ (A, B, C, V1–V4 y FINAL, más las versiones pequeñas 168×94)
"""
import math
import os

import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'montaje')))
from estilo import base, bloom, dibujar_planeta, linea_glow
from montar import AMBAR, AQUI, BG, H, HUESO, W, blk, cargar, mezcla, neg, pegar, punto, reg, sprite_texto
from ui import _marca

SALIDA = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Miniaturas'))
os.makedirs(SALIDA, exist_ok=True)


def texto_grande(fr, lineas, x, y, tam, color=AMBAR, interlineado=1.0):
    fnt = blk(tam)
    for ln in lineas:
        s = sprite_texto(ln, fnt, color)
        sombra = s[1].filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.9))
        fr.paste(Image.new('RGB', sombra.size, (2, 4, 12)), (int(x - 6), int(y + 6)), sombra)
        halo = s[1].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.45))
        fr.paste(Image.new('RGB', halo.size, color), (int(x - 6), int(y - 6)), halo)
        pegar(fr, s, x, y, 1.0)
        y += int(s[1].size[1] * 0.80 * interlineado)
    return y


def marca(fr):
    """Logo real del canal (círculo con anillos), arriba a la izquierda."""
    rgb, mk = _marca(88)
    ImageDraw.Draw(fr).ellipse((108, 98, 108 + 90, 98 + 90), outline=mezcla(BG, AMBAR, 0.6), width=2)
    fr.paste(rgb, (109, 99), mk)


def guardar(fr, nombre):
    im = fr.resize((1280, 720), Image.LANCZOS)
    im.save(os.path.join(SALIDA, nombre + '.png'), optimize=True)
    im.resize((168, 94), Image.LANCZOS).save(os.path.join(SALIDA, nombre + '-168x94.png'))


def viñeta(fr, k=0.55):
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    m = (1 - np.clip(d - 0.55, 0, 1) * k)[..., None]
    return Image.fromarray(np.clip(np.asarray(fr, np.float32) * m, 0, 255).astype('uint8'))


def a_dia_luz(lineas=('A 1', 'DÍA LUZ')):
    fr = base(12.0)
    im = cargar('M01-PIA26353.jpg')
    h = H
    w = int(im.width * h / im.height)
    im = im.resize((w, h), Image.LANCZOS)
    x0 = W - w + 430
    fr.paste(im, (x0, 0))
    # degradado a azul noche por la izquierda para el texto
    g = np.clip((np.arange(W) - 640) / 700.0, 0, 1) ** 1.1
    capa = np.asarray(Image.new('RGB', (W, H), BG), np.float32)
    arr = np.asarray(fr, np.float32) * g[None, :, None] + capa * (1 - g[None, :, None])
    fr = Image.fromarray(arr.astype('uint8'))
    fr = viñeta(fr, 0.5)
    marca(fr)
    texto_grande(fr, list(lineas), 110, 330, 215)
    return fr


def fuera():
    fr = base(30.0)
    cx, cy = 1300, 370
    # heliosfera: burbuja translúcida
    rx, ry = 400, 275
    pts = [(cx + rx * math.cos(2 * math.pi * i / 240), cy + ry * math.sin(2 * math.pi * i / 240)) for i in range(241)]
    relleno = Image.new('L', (W, H), 0)
    ImageDraw.Draw(relleno).polygon(pts, fill=70)
    relleno = relleno.filter(ImageFilter.GaussianBlur(28))
    fr.paste(Image.new('RGB', (W, H), (60, 90, 190)), (0, 0), relleno)
    linea_glow(fr, pts, AMBAR, 7, 1.0)
    dibujar_planeta(fr, 'sol', cx - 70, cy, 40, (1, 0))
    # la nave, diminuta, justo fuera del borde
    nx, ny = cx + rx + 62, cy - 30
    punto(fr, nx, ny, 12, HUESO, 1.0, 5.0)
    fr = bloom(fr, 0.30)
    fr = viñeta(fr, 0.5)
    marca(fr)
    texto_grande(fr, ['¿FUERA?'], 110, 690, 205)
    return fr


def horas():
    fr = base(50.0)
    y = 800
    ex, sx = 230, 1620
    linea_glow(fr, [(ex, y), (sx, y)], AMBAR, 6, 1.0)
    dibujar_planeta(fr, 'tierra', ex, y, 40, (1, 0))
    punto(fr, sx, y, 14, HUESO, 1.0, 5.0)
    for i in range(1, 12):
        x = ex + (sx - ex) * i / 12
        ImageDraw.Draw(fr).line((x, y - 12, x, y + 12), fill=mezcla(BG, HUESO, 0.35), width=3)
    fr = bloom(fr, 0.30)
    fr = viñeta(fr, 0.5)
    marca(fr)
    texto_grande(fr, ['23 HORAS'], 110, 230, 240)
    pegar(fr, sprite_texto('de ida', neg(110), HUESO), 124, 500, 0.95)
    return fr


# ------------------------------------------------------------------ estilo «sonda grande + palabra en bloque»
def fondo_sonda(cx=1330, cy=600, alto=1020, oscuro=0.22, izq=0.55, realce=0.0):
    """Ilustración de la sonda (NASA/JPL-Caltech, PIA26353): la sonda se coloca en (cx, cy); los bordes se rellenan
    prolongando el fondo; se entona hacia azul noche y se oscurece la izquierda para el texto."""
    im = cargar('M01-PIA26353.jpg')
    w = int(im.width * alto / im.height)
    im = im.resize((w, alto), Image.LANCZOS)
    x0, y0 = int(cx - 0.52 * w), int(cy - 0.50 * alto)
    arr = np.asarray(im, np.float32)
    lienzo = np.zeros((H, W, 3), np.float32)
    # se recorta lo que sobra y se prolonga el borde si falta
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    cw, ch = min(w - sx0, W - dx0), min(alto - sy0, H - dy0)
    lienzo[dy0:dy0 + ch, dx0:dx0 + cw] = arr[sy0:sy0 + ch, sx0:sx0 + cw]
    if dx0 > 0:
        lienzo[:, :dx0] = lienzo[:, dx0:dx0 + 1]
    if dx0 + cw < W:
        lienzo[:, dx0 + cw:] = lienzo[:, dx0 + cw - 1:dx0 + cw]
    if dy0 > 0:
        lienzo[:dy0] = lienzo[dy0:dy0 + 1]
    if dy0 + ch < H:
        lienzo[dy0 + ch:] = lienzo[dy0 + ch - 1:dy0 + ch]
    lienzo = lienzo * (1 - oscuro) + np.asarray(BG, np.float32) * oscuro
    if realce > 0:     # la sonda resalta: más contraste y luz concentrada alrededor de ella
        yy, xx = np.mgrid[0:H, 0:W]
        foco = np.exp(-(((xx - cx) / 520.0) ** 2 + ((yy - cy) / 470.0) ** 2))[..., None]
        c = 1.0 + 0.45 * realce
        lienzo = (lienzo - 110) * c + 110
        lienzo = lienzo * (1 + 0.55 * realce * foco) + np.array([40, 26, 6], np.float32) * realce * foco
    g = np.clip((np.arange(W) - 120) / (W * 0.62), 0, 1) ** 0.9              # 0 a la izquierda → 1 a la derecha
    g = (izq + (1 - izq) * g)[None, :, None]
    lienzo = lienzo * g + np.asarray(BG, np.float32) * (1 - g)
    return viñeta(Image.fromarray(np.clip(lienzo, 0, 255).astype('uint8')), 0.5)


def _tight(s):
    rgb, m = s
    bb = m.getbbox()
    return rgb.crop(bb), m.crop(bb)


def caja_texto(fr, texto, x, y, tam, relleno=AMBAR, tinta=BG, pad=(36, 22)):
    """Palabra destacada en un bloque de color (relleno ámbar, letras azul noche, centradas en el bloque)."""
    rgb, m = _tight(sprite_texto(texto, blk(tam), tinta))
    w, h = m.size
    bw, bh = w + 2 * pad[0], h + 2 * pad[1]
    sombra = Image.new('L', (bw + 80, bh + 80), 0)
    ImageDraw.Draw(sombra).rounded_rectangle((40, 48, 40 + bw, 48 + bh), 12, fill=150)
    sombra = sombra.filter(ImageFilter.GaussianBlur(18))
    fr.paste(Image.new('RGB', sombra.size, (2, 4, 12)), (int(x - 40), int(y - 40)), sombra)
    mk = Image.new('L', (bw, bh), 0)
    ImageDraw.Draw(mk).rounded_rectangle((0, 0, bw - 1, bh - 1), 12, fill=255)
    fr.paste(Image.new('RGB', (bw, bh), relleno), (int(x), int(y)), mk)
    fr.paste(rgb, (int(x + pad[0]), int(y + pad[1])), m)
    return x + bw, y + bh


def texto_hueso(fr, texto, x, y, tam, color=HUESO):
    rgb, m = _tight(sprite_texto(texto, blk(tam), color))
    sombra = m.filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.9))
    fr.paste(Image.new('RGB', sombra.size, (2, 4, 12)), (int(x - 5), int(y + 6)), sombra)
    fr.paste(rgb, (int(x), int(y)), m)
    return x + m.size[0], y + m.size[1]


def v_lejana():
    fr = fondo_sonda(cx=1380, cy=620)
    marca(fr)
    ya = texto_hueso(fr, 'LA NAVE MÁS', 110, 230, 120)[1]
    caja_texto(fr, 'LEJANA', 110, ya + 40, 190)
    return fr


def v_horas():
    fr = fondo_sonda(cx=1400, cy=640)
    linea_glow(fr, [(1190, 560), (190, 860)], AMBAR, 5, 0.9)          # la orden de radio, de la Tierra a la sonda
    dibujar_planeta(fr, 'tierra', 160, 865, 36, (1, 0))
    fr = bloom(fr, 0.28)
    marca(fr)
    ya = texto_hueso(fr, 'UNA ORDEN TARDA', 110, 190, 100)[1]
    caja_texto(fr, '23 HORAS', 110, ya + 36, 190)
    return fr


def v_fuera():
    fr = fondo_sonda(cx=1380, cy=620)
    cx, cy, rx, ry = 1290, 640, 640, 470                                 # borde de la heliosfera (esquema)
    pts = [(cx + rx * math.cos(2 * math.pi * i / 260), cy + ry * math.sin(2 * math.pi * i / 260)) for i in range(261)]
    linea_glow(fr, pts, AMBAR, 5, 0.7)
    fr = bloom(fr, 0.22)
    marca(fr)
    xb, yb = caja_texto(fr, '¿FUERA?', 110, 230, 230)
    texto_hueso(fr, 'DEL SISTEMA SOLAR', 116, yb + 50, 74)
    return fr


def v_casi(realce=0.0, lineas=('CASI 1', 'DÍA LUZ'), centrado=False):
    fr = fondo_sonda(cx=1400, cy=600, realce=realce)
    if realce:
        fr = bloom(fr, 0.18, umbral=170)
    marca(fr)
    if centrado:     # el bloque de texto queda centrado verticalmente (alineado a la izquierda)
        alto_total = 190 * 0.72 + 36 + 210 * 0.72 + 44 + 40
        y = int((H - alto_total) / 2)
    else:
        y = 190
    ya = texto_hueso(fr, lineas[0], 110, y, 190)[1]
    caja_texto(fr, lineas[1], 110, ya + 36, 210)
    return fr


if __name__ == '__main__':
    guardar(a_dia_luz(('CASI 1', 'DÍA LUZ')), 'miniatura-A-casi-1-dia-luz')      # para publicar ANTES del 18-nov-2026
    guardar(a_dia_luz(), 'miniatura-A-1-dia-luz')                              # solo si se publica DESPUÉS del hito
    guardar(fuera(), 'miniatura-B-fuera')
    guardar(horas(), 'miniatura-C-23-horas')
    guardar(v_lejana(), 'miniatura-V1-la-nave-mas-lejana')
    guardar(v_horas(), 'miniatura-V2-23-horas-caja')
    guardar(v_fuera(), 'miniatura-V3-fuera-del-sistema-solar')
    guardar(v_casi(), 'miniatura-V4-casi-1-dia-luz-caja')
    guardar(v_casi(realce=1.0, lineas=('A CASI 1', 'DÍA LUZ'), centrado=True), 'miniatura-FINAL-a-casi-1-dia-luz')
    print('listo:', SALIDA)
