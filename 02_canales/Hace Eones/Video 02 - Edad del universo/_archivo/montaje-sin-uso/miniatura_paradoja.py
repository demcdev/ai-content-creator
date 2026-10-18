"""
Miniatura «la paradoja» del video 2: el plano de apertura del diorama (Tierra, Sol y estrella tachados, sello «SIN TESTIGOS»)
con «NADIE ESTUVO ALLÍ» arriba y la cifra en el bloque ámbar del canal. Todo es material propio del video.

  python video02_diorama.py --frame 7.7 cache_miniatura/f_7.7.png   (fotograma base, ya generado)
  python miniatura_paradoja.py   -> ../Miniaturas/miniatura-paradoja-nadie-estuvo-alli.png (1280×720) y su vista de 168×94
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.dirname(AQUI)
HACE_EONES = os.path.dirname(VIDEO)
BASE = os.path.join(AQUI, 'cache_miniatura', 'f_7.7.png')
SALIDA = os.path.join(VIDEO, 'Miniaturas')
INTER = os.path.join(HACE_EONES, 'Herramientas', 'montaje', 'fuentes', 'inter', 'Inter-VF.ttf')
LOGO = os.path.join(HACE_EONES, 'Identidad visual', 'logo-hace-eones-800.png')
W, H = 1280, 720
AMBAR = (240, 178, 64)
HUESO = (246, 238, 222)
NOCHE = (12, 16, 30)


def fuente(px, peso=900):
    f = ImageFont.truetype(INTER, px)
    f.set_variation_by_axes([32, peso])
    return f


def sombra_texto(lienzo, xy, texto, f, color, anchor='mm', difus=14):
    capa = Image.new('L', lienzo.size, 0)
    ImageDraw.Draw(capa).text((xy[0] + 4, xy[1] + 7), texto, font=f, fill=235, anchor=anchor)
    capa = capa.filter(ImageFilter.GaussianBlur(difus))
    lienzo.paste(Image.new('RGB', lienzo.size, (0, 0, 0)), (0, 0), capa)
    ImageDraw.Draw(lienzo).text(xy, texto, font=f, fill=color, anchor=anchor)


def marca(lienzo, n=62, x=24, y=20):
    im = Image.open(LOGO).convert('RGB').crop((110, 110, 690, 690)).resize((n * 4, n * 4), Image.LANCZOS)
    m = Image.new('L', (n * 4, n * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, n * 4 - 1, n * 4 - 1), fill=255)
    lienzo.paste(im.resize((n, n), Image.LANCZOS), (x, y), m.resize((n, n), Image.LANCZOS))
    ImageDraw.Draw(lienzo).ellipse((x - 1, y - 1, x + n, y + n), outline=AMBAR, width=2)


PINES = [(287, 256), (642, 254), (996, 256)]     # borde superior de cada tarjeta en la miniatura (1280×720)
PIN = os.path.normpath(os.path.join(HACE_EONES, '..', 'Tarea-video', 'cache_vox', 'pin_rojo.png'))


def hilo(d, p0, p1, comba, color, ancho):
    """Tramo de hilo entre dos puntos, con la comba de un hilo tenso pero no rígido."""
    pts = []
    for i in range(41):
        s = i / 40
        pts.append((p0[0] + (p1[0] - p0[0]) * s, p0[1] + (p1[1] - p0[1]) * s + comba * 4 * s * (1 - s)))
    d.line(pts, fill=color, width=ancho, joint='curve')


TARJETAS = [(188, 240, 388, 478), (542, 238, 744, 478), (895, 240, 1097, 478)]   # las tarjetas tapan el hilo


def realce(fr):
    """Más contraste y color en las tres tarjetas y el sello, y un viñeteado más oscuro alrededor: las pruebas saltan
    a la vista incluso en la vista pequeña del móvil."""
    from PIL import ImageEnhance
    z = ImageEnhance.Contrast(fr).enhance(1.28)
    z = ImageEnhance.Color(z).enhance(1.45)
    z = ImageEnhance.Brightness(z).enhance(1.1)
    m = Image.new('L', fr.size, 0)
    dm = ImageDraw.Draw(m)
    for (x0, y0, x1, y1) in TARJETAS:
        dm.rectangle([x0 + 4, y0 + 4, x1 - 4, y1 - 4], fill=255)
    o = np.asarray(fr, np.int16)
    sello = np.zeros((H, W), bool)
    sello[430:552, 470:812] = True
    rojo = sello & (o[..., 0] - o[..., 1] > 45)                                  # solo la tinta roja del sello
    m = np.maximum(np.asarray(m), np.asarray(Image.fromarray((rojo * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))))
    m = Image.fromarray(m).filter(ImageFilter.GaussianBlur(2.5))
    out = Image.composite(z, fr, m)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot((xx - W / 2) / (W * 0.62), (yy - H * 0.5) / (H * 0.62))
    k = 1 - 0.38 * np.clip(d - 0.55, 0, 1) / 0.45
    return Image.fromarray(np.clip(np.asarray(out, np.float32) * k[..., None], 0, 255).astype(np.uint8))


def tablero(fr):
    """Las tres tarjetas colgadas de un hilo rojo con chinchetas, como en un tablero de pruebas. El hilo pasa por detrás
    de cada tarjeta y solo se ve entre ellas y bajo la chincheta que la sujeta."""
    tramo = [(-30, 200)] + PINES + [(W + 30, 200)]
    combas = [6, 24, 24, 6]
    capa = Image.new('RGBA', fr.size, (0, 0, 0, 0))
    sombra = Image.new('L', fr.size, 0)
    ds = ImageDraw.Draw(sombra)
    for (p0, p1, c) in zip(tramo, tramo[1:], combas):
        hilo(ds, (p0[0] + 3, p0[1] + 7), (p1[0] + 3, p1[1] + 7), c, 170, 8)
    capa.paste((0, 0, 0, 255), (0, 0), sombra.filter(ImageFilter.GaussianBlur(4)))
    d = ImageDraw.Draw(capa)
    for (p0, p1, c) in zip(tramo, tramo[1:], combas):
        hilo(d, p0, p1, c, (226, 36, 30, 255), 7)
        hilo(d, (p0[0], p0[1] - 2), (p1[0], p1[1] - 2), c, (255, 128, 110, 255), 2)      # brillo del hilo
    tapa = Image.new('L', fr.size, 255)
    dt = ImageDraw.Draw(tapa)
    for r in TARJETAS:
        dt.rectangle(r, fill=0)
    for (x, y) in PINES:
        dt.ellipse([x - 11, y - 11, x + 11, y + 11], fill=255)
    capa.putalpha(Image.fromarray(np.minimum(np.asarray(capa.getchannel('A')), np.asarray(tapa))))
    fr.paste(capa.convert('RGB'), (0, 0), capa.getchannel('A'))
    pin = Image.open(PIN).convert('RGBA')
    pin = pin.crop(pin.getbbox()).resize((36, 36), Image.LANCZOS)
    for (x, y) in PINES:
        sm = pin.getchannel('A').filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.6))
        fr.paste(Image.new('RGB', pin.size, (0, 0, 0)), (int(x - 18 + 3), int(y - 18 + 5)), sm)
        fr.paste(pin, (int(x - 18), int(y - 18)), pin)


def main():
    fr = Image.open(BASE).convert('RGB')
    fr = fr.crop((120, 75, 1800, 1020)).resize((W, H), Image.LANCZOS)     # acerca las tres tarjetas
    # oscurece arriba y abajo para que el texto se lea sobre el fondo desenfocado
    yy = np.linspace(0, 1, H)[:, None, None]
    k = 1 - 0.55 * np.clip((0.33 - yy) / 0.33, 0, 1) - 0.6 * np.clip((yy - 0.8) / 0.2, 0, 1)
    fr = Image.fromarray(np.clip(np.asarray(fr, np.float32) * k, 0, 255).astype(np.uint8))

    fr = realce(fr)
    tablero(fr)
    sombra_texto(fr, (W / 2, 96), 'NADIE ESTUVO ALLÍ', fuente(116), HUESO)

    # «13 797» en el bloque ámbar + «MILLONES DE AÑOS» al lado
    fn, fs = fuente(100), fuente(48, 800)
    num = '13 797'
    bw = fn.getbbox(num)[2] - fn.getbbox(num)[0] + 56
    sw = max(fs.getbbox('MILLONES')[2], fs.getbbox('DE AÑOS')[2])
    x0 = (W - (bw + 26 + sw)) / 2
    yc = 636
    capa = Image.new('L', (W, H), 0)
    ImageDraw.Draw(capa).rounded_rectangle([x0 + 6, yc - 50 + 10, x0 + bw + 6, yc + 50 + 10], 14, fill=200)
    fr.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 0), capa.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(fr)
    d.rounded_rectangle([x0, yc - 50, x0 + bw, yc + 50], 14, fill=AMBAR)
    d.text((x0 + bw / 2, yc + 2), num, font=fn, fill=NOCHE, anchor='mm')
    sombra_texto(fr, (x0 + bw + 26, yc - 24), 'MILLONES', fs, HUESO, anchor='lm', difus=8)
    sombra_texto(fr, (x0 + bw + 26, yc + 28), 'DE AÑOS', fs, HUESO, anchor='lm', difus=8)

    os.makedirs(SALIDA, exist_ok=True)
    ruta = os.path.join(SALIDA, 'miniatura-paradoja-nadie-estuvo-alli.png')
    fr.save(ruta, optimize=True)
    fr.resize((168, 94), Image.LANCZOS).save(os.path.join(SALIDA, 'miniatura-paradoja-nadie-estuvo-alli-168x94.png'))
    print('miniatura:', ruta)


if __name__ == '__main__':
    main()
