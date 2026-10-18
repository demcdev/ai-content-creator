"""
Miniatura del video 2 en formato «cuadrícula de pruebas»: un titular grande arriba y 12 casillas luminosas sobre fondo oscuro,
cada una con algo que SÍ aparece en el video (patrón de catálogo; arte, textos y paleta propios del canal).

  python miniatura_cuadricula.py   -> ../Miniaturas/miniatura-cuadricula-*.png (1280×720) y sus vistas de 168×94
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.dirname(AQUI)
TAREA = os.path.normpath(os.path.join(VIDEO, '..', '..', 'Tarea-video'))
sys.path.insert(0, TAREA)
import diorama_demo as DD   # noqa: E402  (sprites propios del video y tipografía del diorama)

SALIDA = os.path.join(VIDEO, 'Miniaturas')
W, H = 1280, 720
AMBAR = (240, 176, 64)
f32 = np.float32


def sprite(nombre, alto):
    s = DD.sprite(nombre)
    bb = s.getchannel('A').getbbox()
    s = s.crop(bb)
    return s.resize((max(1, int(s.width * alto / s.height)), alto), Image.LANCZOS)


def tenir(s, col, k=0.55):
    """Lleva un recorte de papel hacia un color luminoso (sin perder el dibujo)."""
    a = np.asarray(s, f32)
    a[..., :3] = a[..., :3] * (1 - k) + np.asarray(col, f32) * k * (0.5 + a[..., :3].mean(-1, keepdims=True) / 255)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def brillo(lienzo, s, x, y, col, radio=26, fuerza=1.4):
    """Pega un sprite con halo de luz alrededor (el «glow» de las casillas)."""
    halo = Image.new('RGBA', lienzo.size, (0, 0, 0, 0))
    m = Image.new('L', lienzo.size, 0)
    m.paste(s.getchannel('A'), (int(x), int(y)))
    m = m.filter(ImageFilter.GaussianBlur(radio))
    arr = np.asarray(lienzo, f32)
    g = np.asarray(m, f32)[..., None] / 255 * fuerza
    arr[..., :3] = arr[..., :3] + g * np.asarray(col, f32)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    out.alpha_composite(s, (int(x), int(y)))
    return out


def fondo_casilla(w, h, col, semilla, centro=(0.5, 0.45)):
    rnd = np.random.RandomState(semilla)
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot((xx - w * centro[0]) / w, (yy - h * centro[1]) / h)
    base = np.asarray((6, 6, 16), f32)[None, None] + np.asarray(col, f32)[None, None] * np.exp(-(d / 0.42) ** 2)[..., None] * 0.95
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert('RGBA')
    dr = ImageDraw.Draw(im)
    for _ in range(55):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        r = rnd.choice([1, 1, 1.5, 2])
        dr.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(rnd.uniform(120, 255))))
    for _ in range(3):
        x, y, r = rnd.uniform(10, w - 10), rnd.uniform(10, h - 50), rnd.uniform(5, 9)
        dr.line([x - r, y, x + r, y], fill=(255, 255, 255, 230), width=2)
        dr.line([x, y - r, x, y + r], fill=(255, 255, 255, 230), width=2)
    return im


def estrella_destello(lienzo, cx, cy, col, r=60):
    """Estrella de luz pintada: núcleo blanco, halo de color y cuatro rayos."""
    w, h = lienzo.size
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot(xx - cx, yy - cy)
    arr = np.asarray(lienzo, f32)
    halo = np.exp(-(d / r) ** 2)[..., None] * np.asarray(col, f32) * 1.6
    nucleo = np.exp(-(d / (r * 0.28)) ** 2)[..., None] * 255
    rayos = (np.exp(-((xx - cx) / 2.2) ** 2) + np.exp(-((yy - cy) / 2.2) ** 2)) * np.exp(-(d / (r * 1.8)) ** 2)
    arr[..., :3] += halo + nucleo + rayos[..., None] * 200
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')


def arte(nombre, w, h):
    """Dibujo de cada casilla. Todo sale de piezas propias del video (no hay imágenes de terceros)."""
    if nombre == 'FONDO CÓSMICO':
        im = fondo_casilla(w, h, (40, 90, 170), 1)
        return brillo(im, sprite('mapa_cmb', int(h * 0.62)), w / 2 - sprite('mapa_cmb', int(h * 0.62)).width / 2, h * 0.1, (90, 150, 255))
    if nombre == 'PLANCK':
        im = fondo_casilla(w, h, (30, 70, 140), 2)
        s = tenir(sprite('satelite', int(h * 0.66)), (170, 210, 255), 0.25)
        return brillo(im, s, w / 2 - s.width / 2, h * 0.07, (120, 170, 255))
    if nombre == '380 000 AÑOS':
        im = fondo_casilla(w, h, (150, 70, 20), 3)
        return estrella_destello(im, w / 2, h * 0.42, (255, 150, 60), r=h * 0.32)
    if nombre == 'HUBBLE 1929':
        im = fondo_casilla(w, h, (90, 40, 140), 4)
        g = tenir(sprite('galaxia', int(h * 0.36)), (200, 140, 255), 0.35)
        dr = ImageDraw.Draw(im)
        for (fx, fy, dx, dy) in ((0.22, 0.25, -1, -0.4), (0.78, 0.22, 1, -0.4), (0.3, 0.6, -1, 0.5), (0.72, 0.6, 1, 0.5)):
            x, y = w * fx, h * fy
            dr.line([x + dx * 4, y + dy * 4, x + dx * 40, y + dy * 40], fill=(255, 210, 120, 255), width=5)
            im = brillo(im, g, x - g.width / 2, y - g.height / 2, (180, 120, 255), radio=14)
        return im
    if nombre == 'CEFEIDAS':
        im = fondo_casilla(w, h, (160, 120, 20), 5)
        dr = ImageDraw.Draw(im)
        for k, r in enumerate((h * 0.42, h * 0.33, h * 0.24)):
            dr.ellipse([w / 2 - r, h * 0.42 - r, w / 2 + r, h * 0.42 + r], outline=(255, 220, 120, 140 - k * 30), width=4)
        s = sprite('cefeida', int(h * 0.42))
        return brillo(im, s, w / 2 - s.width / 2, h * 0.42 - s.height / 2, (255, 200, 80))
    if nombre == 'SUPERNOVAS':
        im = fondo_casilla(w, h, (40, 120, 170), 6)
        im = estrella_destello(im, w / 2, h * 0.42, (120, 220, 255), r=h * 0.26)
        s = sprite('supernova', int(h * 0.5))
        return brillo(im, s, w / 2 - s.width / 2, h * 0.42 - s.height / 2, (150, 230, 255), radio=20, fuerza=1.0)
    if nombre == 'SH0ES · 73':
        im = fondo_casilla(w, h, (30, 60, 160), 7)
        g = tenir(sprite('galaxia', int(h * 0.5)), (120, 170, 255), 0.4)
        im = brillo(im, g, w * 0.28 - g.width / 2, h * 0.38 - g.height / 2, (90, 140, 255))
        dr = ImageDraw.Draw(im)
        dr.text((w * 0.7, h * 0.4), '73', font=DD.fuente(int(h * 0.42), 900, 75), fill=(140, 190, 255, 255), anchor='mm', stroke_width=5, stroke_fill=(10, 14, 40, 255))
        return im
    if nombre == 'ESTRELLAS VIEJAS':
        im = fondo_casilla(w, h, (150, 40, 30), 8)
        im = estrella_destello(im, w * 0.5, h * 0.4, (255, 90, 50), r=h * 0.27)
        im = estrella_destello(im, w * 0.2, h * 0.24, (255, 170, 90), r=h * 0.09)
        return estrella_destello(im, w * 0.8, h * 0.62, (255, 130, 70), r=h * 0.08)
    if nombre == 'GAIA · 160':
        im = fondo_casilla(w, h, (60, 50, 120), 9)
        rnd = np.random.RandomState(160)
        dr = ImageDraw.Draw(im)
        for _ in range(160):
            r = abs(rnd.normal(0, 0.24)) * h
            t = rnd.uniform(0, 2 * math.pi)
            x, y = w / 2 + r * math.cos(t) * 1.3, h * 0.42 + r * math.sin(t) * 0.8
            c = rnd.choice([0, 1, 2])
            col = [(255, 170, 110), (255, 230, 170), (190, 210, 255)][c]
            rr = rnd.uniform(1.5, 4)
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col + (255,))
        return im.filter(ImageFilter.GaussianBlur(0.4))
    if nombre == 'WEBB':
        im = fondo_casilla(w, h, (150, 110, 20), 10)
        s = sprite('webb', int(h * 0.7))
        return brillo(im, s, w / 2 - s.width / 2, h * 0.04, (255, 190, 80))
    if nombre == 'ACT · CHILE':
        im = fondo_casilla(w, h, (40, 110, 110), 11, centro=(0.5, 0.3))
        s = sprite('act', int(h * 0.6))
        return brillo(im, s, w / 2 - s.width / 2, h * 0.14, (90, 220, 210), fuerza=0.9)
    if nombre == 'LA TENSIÓN':
        im = fondo_casilla(w, h, (170, 20, 30), 12)
        dr = ImageDraw.Draw(im)
        f = DD.fuente(int(h * 0.4), 900, 75)
        dr.text((w * 0.25, h * 0.4), '67', font=f, fill=(255, 200, 90, 255), anchor='mm', stroke_width=5, stroke_fill=(30, 5, 5, 255))
        dr.text((w * 0.75, h * 0.4), '73', font=f, fill=(140, 190, 255, 255), anchor='mm', stroke_width=5, stroke_fill=(30, 5, 5, 255))
        pts = [(w * 0.5 + (10 if k % 2 else -10), h * (0.12 + 0.07 * k)) for k in range(9)]   # grieta entre las dos cifras
        dr.line(pts, fill=(255, 70, 60, 255), width=7, joint='curve')
        return im
    raise KeyError(nombre)


CASILLAS = ['FONDO CÓSMICO', 'PLANCK', '380 000 AÑOS', 'HUBBLE 1929',
            'CEFEIDAS', 'SUPERNOVAS', 'SH0ES · 73', 'ESTRELLAS VIEJAS',
            'GAIA · 160', 'WEBB', 'ACT · CHILE', 'LA TENSIÓN']


def rotulo(d, texto, x, y, px, col=(255, 255, 255)):
    f = DD.fuente(px, 800, 75)
    while f.getbbox(texto)[2] - f.getbbox(texto)[0] > 286 and px > 20:
        px -= 2
        f = DD.fuente(px, 800, 75)
    d.text((x, y), texto, font=f, fill=col + (255,), anchor='mm', stroke_width=max(3, px // 9), stroke_fill=(0, 0, 0, 255))


def miniatura(titular):
    lienzo = Image.new('RGBA', (W, H), (8, 8, 14, 255))
    d = ImageDraw.Draw(lienzo)
    # titular: blanco, condensado y con contorno; la palabra clave en el ámbar del canal
    px = 96
    f = DD.fuente(px, 900, 75)
    while f.getbbox(''.join(t for t, _ in titular))[2] > W - 60:
        px -= 2
        f = DD.fuente(px, 900, 75)
    total = sum(f.getbbox(t)[2] - f.getbbox(t)[0] for t, _ in titular)
    x = (W - total) / 2
    for t, col in titular:
        d.text((x, 58), t, font=f, fill=col + (255,), anchor='lm', stroke_width=6, stroke_fill=(0, 0, 0, 255))
        x += f.getbbox(t)[2] - f.getbbox(t)[0]
    # cuadrícula 4 × 3
    cols, filas, gap, top = 4, 3, 10, 116
    cw = (W - gap * (cols + 1)) / cols
    ch = (H - top - gap * filas) / filas
    for k, nombre in enumerate(CASILLAS):
        cx, cy = gap + (k % cols) * (cw + gap), top + (k // cols) * (ch + gap)
        casilla = arte(nombre, int(cw), int(ch))
        mask = Image.new('L', casilla.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, casilla.width - 1, casilla.height - 1], 12, fill=255)
        lienzo.paste(casilla, (int(cx), int(cy)), mask)
        ImageDraw.Draw(lienzo).rounded_rectangle([cx, cy, cx + casilla.width - 1, cy + casilla.height - 1], 12, outline=(255, 255, 255, 60), width=2)
        rotulo(ImageDraw.Draw(lienzo), nombre, cx + cw / 2, cy + ch - 26, 38)
    return lienzo.convert('RGB')


def guardar(im, nombre):
    os.makedirs(SALIDA, exist_ok=True)
    im.save(os.path.join(SALIDA, nombre + '.png'), optimize=True)
    im.resize((168, 94), Image.LANCZOS).save(os.path.join(SALIDA, nombre + '-168x94.png'))
    print('miniatura:', os.path.join(SALIDA, nombre + '.png'))


if __name__ == '__main__':
    BL = (255, 255, 255)
    guardar(miniatura([('CADA ', BL), ('PRUEBA ', AMBAR), ('DE LA EDAD DEL UNIVERSO', BL)]), 'miniatura-cuadricula-cada-prueba')
    guardar(miniatura([('LA EDAD DEL UNIVERSO, ', BL), ('PRUEBA POR PRUEBA', AMBAR)]), 'miniatura-cuadricula-prueba-por-prueba')
