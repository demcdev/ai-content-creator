"""
Globo terrestre giratorio (estilo espacial).

Los continentes salen de Natural Earth (datos/ne_110m_land.geojson, dominio público). El globo se dibuja por código con
proyección ortográfica, luz y atmósfera. Aquí solo está lo general: la orientación de la cámara (eje inclinado de la
Tierra), el dibujo y la conversión de latitud/longitud a pantalla. Lo propio de cada escena (estaciones, dirección de
una sonda, etc.) vive en el video que lo usa; ejemplo: Video 01/Montaje/dsn_voyager.py.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import map_coordinates

AQUI = os.path.dirname(os.path.abspath(__file__))
_c = {}

# eje de rotación de la Tierra (norte) en el sistema de la cámara (x derecha, y arriba, z hacia el espectador)
A = np.array([-0.25, 0.80, 0.55])
A = A / np.linalg.norm(A)
_B = np.array([1.0, 0.0, 0.0]) - A * A[0]
_B = _B / np.linalg.norm(_B)
_C = np.cross(A, _B)
# base del cuerpo: e1 (lon 0 a φ=0) y e2
E1 = _B
E2 = np.cross(A, E1)


def _tierra():
    if 'mask' in _c:
        return _c['mask']
    d = json.load(open(os.path.join(AQUI, 'datos', 'ne_110m_land.geojson'), encoding='utf8'))
    Wm, Hm = 4096, 2048
    im = Image.new('L', (Wm, Hm), 0)
    dr = ImageDraw.Draw(im)

    def xy(p):
        return ((p[0] + 180) / 360 * Wm, (90 - p[1]) / 180 * Hm)

    for f in d['features']:
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for poly in polys:
            dr.polygon([xy(p) for p in poly[0]], fill=255)
            for hole in poly[1:]:
                dr.polygon([xy(p) for p in hole], fill=0)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    _c['mask'] = np.asarray(im, np.float32) / 255.0
    return _c['mask']


def vec_estacion(lat, lon, fi):
    la, lo = math.radians(lat), math.radians(lon) + fi
    return math.cos(la) * (math.cos(lo) * E1 + math.sin(lo) * E2) + math.sin(la) * A


def dibujar_globo(fr, cx, cy, R, fi, a=1.0):
    """Pega el globo (disco de radio R px) sobre fr. fi = giro de la Tierra en radianes."""
    mask = _tierra()
    n = int(2 * R + 2)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xx - R) / R
    y = -(yy - R) / R
    r2 = x * x + y * y
    dentro = r2 < 1.0
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    v = np.stack([x, y, z], axis=-1)
    lat = np.arcsin(np.clip(v @ A, -1, 1))
    lon = np.arctan2(v @ E2, v @ E1) - fi
    Wm, Hm = mask.shape[1], mask.shape[0]
    u = ((np.degrees(lon) + 180) % 360) / 360 * (Wm - 1)
    w = (90 - np.degrees(lat)) / 180 * (Hm - 1)
    tierra = map_coordinates(mask, [w.ravel(), u.ravel()], order=1, mode='nearest').reshape(n, n)
    L = np.array([-0.55, 0.55, 0.62])
    L = L / np.linalg.norm(L)
    dif = np.clip(v @ L, 0, 1)
    luz = 0.22 + 0.95 * dif
    oceano = np.array([10, 30, 78], np.float32)
    suelo = np.array([96, 134, 142], np.float32)
    col = oceano[None, None, :] * (1 - tierra[..., None]) + suelo[None, None, :] * tierra[..., None]
    col = col * luz[..., None]
    # retícula tenue cada 30°
    dl = np.abs(((np.degrees(lon) + 15) % 30) - 15)
    dp = np.abs(((np.degrees(lat) + 15) % 30) - 15)
    grat = np.clip(1 - np.minimum(dl * np.cos(lat), dp) / 0.7, 0, 1) * 0.14
    col = col * (1 - grat[..., None]) + np.array([150, 190, 255], np.float32) * grat[..., None]
    # borde con atmósfera
    rim = (1 - z) ** 3.2
    col = col + np.array([60, 120, 255], np.float32) * rim[..., None] * 0.9
    alfa = np.clip((1.0 - np.sqrt(r2)) * R / 1.6, 0, 1) * a
    rgb = Image.fromarray(np.clip(col, 0, 255).astype('uint8'))
    # resplandor exterior
    g = int(R * 0.35)
    halo = Image.new('L', (n + 2 * g, n + 2 * g), 0)
    ImageDraw.Draw(halo).ellipse((g, g, g + n, g + n), fill=110)
    halo = halo.filter(ImageFilter.GaussianBlur(g * 0.45))
    fr.paste(Image.new('RGB', halo.size, (50, 100, 220)), (int(cx - R - g), int(cy - R - g)), halo.point(lambda q: int(q * 0.55 * a)))
    fr.paste(rgb, (int(cx - R), int(cy - R)), Image.fromarray((alfa * 255).astype('uint8')))


def punto_pantalla(cx, cy, R, rx, ry):
    return cx + rx * R, cy + ry * R
