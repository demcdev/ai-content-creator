"""
Miniatura del video 2 a partir de la ilustración del pulpo detective (Miniaturas/origen/pulpo-tres-tiempos-original.jpg).

Se conserva el dibujo (pulpo, marcos, garabatos) y se cambia lo que no corresponde al video:
  - «PASADO / PRESENTE / FUTURO» -> los tres relojes del video: LUZ ANTIGUA, EXPANSIÓN, ESTRELLAS (cada marco con su reloj
    de latón, el mismo del diorama);
  - el letrero de arriba -> «3 RELOJES, 1 PROBLEMA» (complementa el título, no lo repite);
  - se borran las rayas sin sentido («fo=mentira», «f=metira»).

  python miniatura_pulpo.py   -> ../Miniaturas/miniatura-pulpo-3-relojes.png (1280×720) y su vista de 168×94
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.dirname(AQUI)
HACE_EONES = os.path.dirname(VIDEO)
TAREA = os.path.normpath(os.path.join(HACE_EONES, '..', 'Tarea-video'))
sys.path.insert(0, TAREA)
import diorama_video as D   # noqa: E402  (relojes de latón del diorama)

ORIGEN = os.path.join(VIDEO, 'Miniaturas', 'origen', 'pulpo-tres-tiempos-original.jpg')
SALIDA = os.path.join(VIDEO, 'Miniaturas')
INTER = os.path.join(HACE_EONES, 'Herramientas', 'montaje', 'fuentes', 'inter', 'Inter-VF.ttf')
AMBAR = (240, 176, 64)
TINTA = (20, 18, 24)


def fuente(px, peso=900):
    f = ImageFont.truetype(INTER, px)
    f.set_variation_by_axes([32, peso])
    return f


def coefs(dst, w, h):
    """Coeficientes de Image.PERSPECTIVE que llevan el rectángulo w×h a la cuadrilátera dst (TL, TR, BR, BL)."""
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def pegar_en_quad(base, img, quad, conservar=None):
    """Pega img (RGBA) deformada a quad. conservar: (bbox) zona donde se respeta el dibujo original claro (tentáculos)."""
    W, H = base.size
    capa = img.transform((W, H), Image.PERSPECTIVE, coefs(quad, *img.size), Image.BICUBIC)
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).polygon(quad, fill=255)
    a = np.minimum(np.asarray(mask, np.float32), np.asarray(capa.getchannel('A'), np.float32)) / 255
    if conservar:
        orig = np.asarray(base, np.float32)
        mx, mn = orig.max(-1), orig.min(-1)
        claro = ((mx - mn) < 40) & (mn > 120)          # trazo gris/blanco del tentáculo, no la ilustración saturada
        x0, y0, x1, y1 = conservar
        zona = np.zeros_like(claro)
        zona[y0:y1, x0:x1] = True
        a = np.where(zona & claro, 0, a)
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32)[..., None] / 255
    out = np.asarray(base, np.float32) * (1 - a) + np.asarray(capa.convert('RGB'), np.float32) * a
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def cielo(w, h, fondo, semilla):
    """Fondo de los marcos: cielo pintado con estrellitas, en la paleta de cada marco original."""
    rnd = np.random.RandomState(semilla)
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot(xx - w / 2, yy - h / 2) / (0.75 * max(w, h))
    arr = np.asarray(fondo, np.float32)[None, None] * (1.15 - 0.45 * d[..., None])
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')
    dr = ImageDraw.Draw(im)
    for _ in range(90):
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.choice([2, 3, 3, 4, 6])
        dr.ellipse([x - r, y - r, x + r, y + r], fill=(255, 250, 230, 230))
    for _ in range(5):
        x, y, r = rnd.uniform(40, w - 40), rnd.uniform(40, h - 40), rnd.uniform(14, 22)
        pts = [(x + (r if k % 2 == 0 else r * 0.42) * math.cos(math.pi / 2 + k * math.pi / 5),
                y - (r if k % 2 == 0 else r * 0.42) * math.sin(math.pi / 2 + k * math.pi / 5)) for k in range(10)]
        dr.polygon(pts, fill=(255, 214, 80, 255), outline=(30, 24, 20, 255))
    return im


def panel_reloj(i, fondo, semilla, w=840, h=800, lado=600, ang=0.0):
    im = cielo(w, h, fondo, semilla)
    rel = D.reloj_img(i, ang)
    rel = rel.resize((lado, int(lado * rel.height / rel.width)), Image.LANCZOS)
    sombra = Image.new('RGBA', rel.size, (0, 0, 0, 0))
    sombra.putalpha(rel.getchannel('A').filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.55)))
    im.alpha_composite(sombra, ((w - rel.width) // 2 + 14, (h - rel.height) // 2 + 22))
    im.alpha_composite(rel, ((w - rel.width) // 2, (h - rel.height) // 2))
    return im


def rotulo(texto, w, h, color, papel=None, px=200):
    """Palabra rotulada a mano: color lleno con contorno negro grueso, como las del dibujo original."""
    im = Image.new('RGBA', (w, h), papel + (255,) if papel else (0, 0, 0, 0))
    f = fuente(px)
    while f.getbbox(texto)[2] - f.getbbox(texto)[0] > w * 0.9:
        px -= 6
        f = fuente(px)
    d = ImageDraw.Draw(im)
    d.text((w / 2, h / 2), texto, font=f, fill=color + (255,), anchor='mm', stroke_width=max(6, px // 14), stroke_fill=TINTA + (255,))
    return im


def letrero(base):
    """«3 RELOJES, 1 PROBLEMA» en el lugar del letrero original; «1 PROBLEMA» en el bloque ámbar del canal."""
    d = ImageDraw.Draw(base)
    papel = tuple(int(v) for v in np.median(np.asarray(base.crop((20, 20, 160, 160))).reshape(-1, 3), 0))
    d.rectangle([150, 0, 2000, 178], fill=papel)
    f = fuente(150)
    a, b = '3 RELOJES,', '1 PROBLEMA'
    wa = f.getbbox(a)[2] - f.getbbox(a)[0]
    wb = f.getbbox(b)[2] - f.getbbox(b)[0]
    pad, hueco = 34, 44
    total = wa + hueco + wb + 2 * pad
    x0 = (2000 - total) / 2
    yc = 92
    d.text((x0, yc), a, font=f, fill=TINTA, anchor='lm')
    bx0 = x0 + wa + hueco
    d.rounded_rectangle([bx0, yc - 82, bx0 + wb + 2 * pad, yc + 82], radius=18, fill=AMBAR, outline=TINTA, width=6)
    d.text((bx0 + pad, yc), b, font=f, fill=TINTA, anchor='lm')
    return papel


def borrar(base, cajas, papel):
    d = ImageDraw.Draw(base)
    for c in cajas:
        if len(c) == 4 and not isinstance(c[0], tuple):
            d.rectangle(c, fill=papel)
        else:
            d.polygon(c, fill=papel)


# zonas ya en color (marcos, rótulos, letrero central) y recuadros donde los tentáculos pasan por encima de ellas
ZONAS = [[(212, 383), (620, 330), (665, 720), (260, 770)], [(262, 774), (668, 722), (684, 838), (279, 890)],
         [(1482, 345), (1925, 390), (1900, 750), (1458, 705)], [(1458, 709), (1900, 754), (1886, 866), (1443, 822)],
         [(812, 688), (1265, 688), (1265, 1075), (812, 1075)]]
CONSERVAR = [(360, 270, 480, 405), (1655, 315, 1775, 420), (780, 660, 870, 770), (1215, 680, 1320, 800)]
OJOS = [(930, 490, 82), (1140, 490, 82)]
CABEZA = (1035, 470, 285, 250)            # centro y radios de la cabeza peluda
SOMBRERO = [(960, 205), (1010, 185), (1062, 200), (1098, 192), (1118, 238), (1124, 290), (1210, 292), (1222, 318),
            (1190, 350), (1100, 362), (1000, 365), (900, 352), (850, 330), (848, 300), (900, 296), (930, 292), (944, 238)]


def _rampa(L, paradas):
    """Mapa de degradado: luminancia (0–1) -> color, interpolando entre paradas (pos, (r, g, b))."""
    pos = np.array([p for p, _ in paradas], np.float32)
    cols = np.array([c for _, c in paradas], np.float32)
    return np.stack([np.interp(L, pos, cols[:, k]) for k in range(3)], -1)


def colorear(base, zonas, conservar, respetar_titular=True):
    """Da color al dibujo a lápiz: trazos y sombras en coral, magenta y morado; el papel se vuelve un cielo celeste y
    lila hacia los bordes; la cabeza del pulpo, rosada; el sombrero, marrón; los ojos siguen blancos.
    Lo que ya tiene color (marcos, relojes, rótulos, el bloque ámbar) no se toca."""
    W, H = base.size
    arr = np.asarray(base, np.float32)
    mx, mn = arr.max(-1), arr.min(-1)
    gris = (mx - mn) < 48                                         # lápiz y papel (sin color propio)
    L = arr.mean(-1) / 255
    m = Image.new('L', (W, H), 255)
    dm = ImageDraw.Draw(m)
    for q in zonas:
        dm.polygon(q, fill=0)
    m = np.asarray(m) > 0
    o = np.asarray(Image.open(ORIGEN).convert('RGB'), np.int16)
    claro_o = ((o.max(-1) - o.min(-1)) < 40) & (o.min(-1) > 120)
    for (x0, y0, x1, y1) in conservar:                            # tentáculos por encima de los marcos
        m[y0:y1, x0:x1] |= claro_o[y0:y1, x0:x1] & gris[y0:y1, x0:x1]
    if respetar_titular:
        m[:190, :] = False                                         # el titular conserva su tinta negra
    aplica = (m & gris).astype(np.float32)

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # papel: crema en el centro, cielo celeste (izquierda) a lila (derecha) hacia los bordes
    d = np.hypot((xx - W * 0.52) / (W * 0.5), (yy - H * 0.55) / (H * 0.55))
    borde = np.clip((d - 0.35) / 0.5, 0, 1)[..., None] ** 0.9
    cielo_c = np.asarray((120, 205, 255), np.float32) * (1 - xx / W)[..., None] + np.asarray((200, 150, 255), np.float32) * (xx / W)[..., None]
    papel = np.asarray((255, 244, 232), np.float32) * (1 - borde) + cielo_c * borde
    # cabeza rosada (máscara suave), ojos blancos
    cx, cy, rx, ry = CABEZA
    cab = np.clip(1.25 - np.hypot((xx - cx) / rx, (yy - cy) / ry), 0, 1) ** 0.7
    ojo = np.zeros((H, W), np.float32)
    for (ex, ey, r) in OJOS:
        ojo = np.maximum(ojo, np.clip((r - np.hypot(xx - ex, yy - ey)) / 6, 0, 1))
    papel = papel * (1 - cab[..., None] * 0.85) + np.asarray((255, 196, 214), np.float32) * cab[..., None] * 0.85
    papel = papel * (1 - ojo[..., None]) + 255 * ojo[..., None]

    trazos = _rampa(L, [(0.0, (18, 14, 26)), (0.22, (52, 18, 52)), (0.42, (150, 34, 96)), (0.6, (232, 62, 104)), (0.78, (255, 120, 112)), (0.9, (255, 186, 168))])
    sm = Image.new('L', (W, H), 0)
    ImageDraw.Draw(sm).polygon(SOMBRERO, fill=255)
    sombrero = np.asarray(sm.filter(ImageFilter.GaussianBlur(4)), np.float32)[..., None] / 255
    marron = _rampa(L, [(0.0, (40, 22, 14)), (0.45, (120, 72, 36)), (0.75, (190, 140, 80)), (0.92, (232, 205, 160))])
    trazos = trazos * (1 - sombrero) + marron * sombrero
    ojo3 = ojo[..., None]
    trazos = trazos * (1 - ojo3) + _rampa(L, [(0.0, (12, 10, 20)), (0.6, (90, 90, 110)), (0.92, (235, 235, 240))]) * ojo3

    luz = np.clip((L - 0.8) / 0.12, 0, 1)[..., None]           # cuánto es papel y cuánto trazo
    papel_s = papel * (1 - sombrero) + np.asarray((236, 214, 176), np.float32) * sombrero
    # cuerpo y tentáculos: el gris medio del sombreado pasa a coral saturado (no a rosa pálido)
    medio = np.clip(1 - np.abs(L - 0.72) / 0.2, 0, 1)[..., None] * (1 - ojo3) * (1 - sombrero)
    trazos = trazos * (1 - medio * 0.65) + np.asarray((255, 92, 110), np.float32) * medio * 0.65
    nuevo = trazos * (1 - luz) + papel_s * luz
    a = aplica[..., None]
    out = arr * (1 - a) + nuevo * a
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def main():
    D.cargar()
    base = Image.open(ORIGEN).convert('RGB')
    papel = letrero(base)
    borrar(base, [[(652, 320), (805, 262), (835, 262), (835, 335), (812, 388), (652, 388)], (1683, 893, 1845, 952)], papel)   # «fo=mentira» y «f=metira»

    # izquierda · LUZ ANTIGUA (reloj con el mapa del fondo cósmico)
    q_img = [(212, 383), (620, 330), (665, 720), (260, 770)]
    q_lbl = [(262, 774), (668, 722), (684, 838), (279, 890)]
    base = pegar_en_quad(base, panel_reloj(0, (40, 46, 60), 3), q_img, conservar=(360, 270, 480, 405))
    base = pegar_en_quad(base, rotulo('LUZ ANTIGUA', 820, 230, (214, 52, 44), papel=papel), q_lbl)

    # derecha · ESTRELLAS (reloj con una estrella vieja)
    q_img = [(1482, 345), (1925, 390), (1900, 750), (1458, 705)]
    q_lbl = [(1458, 709), (1900, 754), (1886, 866), (1443, 822)]
    base = pegar_en_quad(base, panel_reloj(2, (52, 30, 84), 7), q_img, conservar=(1655, 315, 1775, 420))
    base = pegar_en_quad(base, rotulo('ESTRELLAS', 880, 230, (40, 84, 196), papel=papel), q_lbl)

    # centro · EXPANSIÓN (el letrero azul que sostiene el pulpo; rótulo amarillo como el original)
    q_cen = [(812, 688), (1265, 688), (1265, 1075), (812, 1075)]
    can = cielo(906, 774, (22, 46, 104), 5)
    rel = D.reloj_img(1, 0.0)
    rel = rel.resize((440, int(440 * rel.height / rel.width)), Image.LANCZOS)
    can.alpha_composite(rel, ((906 - rel.width) // 2, 40))
    can.alpha_composite(rotulo('EXPANSIÓN', 860, 210, (250, 214, 60)), (23, 548))
    # se respetan las dos patas que agarran el letrero por arriba
    base = pegar_en_quad(base, can, q_cen, conservar=(780, 660, 870, 770))
    zona_pata = (1215, 680, 1320, 800)
    orig = Image.open(ORIGEN).convert('RGB').crop(zona_pata)
    o = np.asarray(orig, np.int16)
    claro = Image.fromarray((((o.max(-1) - o.min(-1)) < 40) & (o.min(-1) > 120)).astype(np.uint8) * 255)
    base.paste(orig, zona_pata[:2], claro.filter(ImageFilter.GaussianBlur(0.8)))

    base = colorear(base, ZONAS, CONSERVAR)

    os.makedirs(SALIDA, exist_ok=True)
    final = base.resize((1280, 714), Image.LANCZOS)
    lienzo = Image.new('RGB', (1280, 720), papel)
    lienzo.paste(final, (0, 3))
    ruta = os.path.join(SALIDA, 'miniatura-pulpo-3-relojes.png')
    lienzo.save(ruta, optimize=True)
    lienzo.resize((168, 94), Image.LANCZOS).save(os.path.join(SALIDA, 'miniatura-pulpo-3-relojes-168x94.png'))
    print('miniatura:', ruta)


if __name__ == '__main__':
    main()
