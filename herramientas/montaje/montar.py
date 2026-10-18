#!/usr/bin/env python3
"""
Librería común de montaje: fuentes, utilidades de dibujo, fondo de estrellas, imágenes con zoom y texto para subtítulos.

Toma la identidad del video en curso (colores, nombre, logo y fuente) de <canal>/identidad.json; el video en curso es
HE_VIDEO o la carpeta que contiene la carpeta «Montaje» del script que se ejecuta. No tiene escenas propias: las escenas
viven en cada video (Video NN/Montaje/) o salen de pipeline.py y animaciones/<estilo>/escenas_base.py.
"""
import json
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 30

# Carpeta del video en curso: la variable de entorno HE_VIDEO, o si no, la carpeta que contiene la carpeta «Montaje»
# del script que se está ejecutando (video01.py, video02.py...). El canal es la carpeta que contiene al video.
VIDEO = os.environ.get('HE_VIDEO') or os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
CANAL = os.path.dirname(VIDEO)
RAIZ = CANAL

# Identidad: la del canal (<canal>/identidad.json) y, si el video declara base «propia», lo que cambie su identidad.json.
sys.path.insert(0, os.path.dirname(AQUI))
from _comun import identidad_efectiva  # noqa: E402

IDENT, _ORIGEN = identidad_efectiva(VIDEO)
NOMBRE = IDENT['nombre']
LOGO = IDENT['logo_ruta']
BG, AMBAR, HUESO, TIERRA = (tuple(IDENT['colores'][k]) for k in ('BG', 'AMBAR', 'HUESO', 'TIERRA'))
ORIG = os.path.join(VIDEO, 'Licencias', 'originales')

# ---------------------------------------------------------------- utilidades

_fuentes = {}


# Familia tipográfica: la de identidad.json (inter, montserrat o space) o la variable de entorno HE_FUENTE.
# Las tres son de licencia abierta (SIL OFL) y están en «fuentes/».
FAMILIA = os.environ.get('HE_FUENTE', IDENT['fuente'])
_VF = {'montserrat': 'montserrat/Montserrat-VF.ttf', 'inter': 'inter/Inter-VF.ttf', 'space': 'spacegrotesk/SpaceGrotesk-VF.ttf'}
_PESOS = {'light': 300, 'reg': 400, 'bold': 700, 'black': 900}


def fuente_peso(peso, tam):
    k = (FAMILIA, peso, tam)
    if k not in _fuentes:
        f = ImageFont.truetype(os.path.join(AQUI, 'fuentes', _VF[FAMILIA]), tam)
        vals = []
        for ax in f.get_variation_axes():
            nom = ax['name'] if isinstance(ax['name'], str) else ax['name'].decode()
            if 'eight' in nom:
                vals.append(max(ax['minimum'], min(ax['maximum'], _PESOS[peso])))
            else:
                vals.append(ax['default'])
        f.set_variation_by_axes(vals)
        _fuentes[k] = f
    return _fuentes[k]


def reg(t): return fuente_peso('reg', t)
def neg(t): return fuente_peso('bold', t)
def blk(t): return fuente_peso('black', t)


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ss(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)
def lerp(a, b, t): return a + (b - a) * t
def mezcla(c1, c2, t): return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def aparecer(t, a, b, d=0.35):
    """Opacidad 0→1→0 con entrada en a y salida en b."""
    return ss((t - a) / d) * (1 - ss((t - (b - d)) / d))


_sprites = {}


def sprite_texto(txt, fnt, color):
    k = (txt, id(fnt), color)
    if k not in _sprites:
        x0, y0, x1, y1 = fnt.getbbox(txt)
        m = Image.new('L', (x1 + 6, y1 + 6), 0)
        ImageDraw.Draw(m).text((2, 2), txt, font=fnt, fill=255)
        _sprites[k] = (Image.new('RGB', m.size, color), m)
    return _sprites[k]


def pegar(frame, spr, x, y, alpha=1.0, ax='l', ay='t'):
    rgb, m = spr
    w, h = m.size
    if ax == 'm': x -= w // 2
    elif ax == 'r': x -= w
    if ay == 'm': y -= h // 2
    elif ay == 'b': y -= h
    if alpha < 1:
        m = m.point(lambda v: int(v * alpha))
    frame.paste(rgb, (int(x), int(y)), m)


def brillo(radio, color):
    k = ('glow', radio, color)
    if k not in _sprites:
        n = radio * 2
        yy, xx = np.mgrid[0:n, 0:n]
        d = np.hypot(xx - radio + 0.5, yy - radio + 0.5) / radio
        a = np.clip(1 - d, 0, 1) ** 2.2
        _sprites[k] = (Image.new('RGB', (n, n), color), Image.fromarray((a * 255).astype('uint8')))
    return _sprites[k]


def disco(radio, color):
    k = ('disc', radio, color)
    if k not in _sprites:
        s = 4
        m = Image.new('L', (radio * 2 * s, radio * 2 * s), 0)
        ImageDraw.Draw(m).ellipse((0, 0, radio * 2 * s - 1, radio * 2 * s - 1), fill=255)
        m = m.resize((radio * 2, radio * 2), Image.LANCZOS)
        _sprites[k] = (Image.new('RGB', m.size, color), m)
    return _sprites[k]


def punto(frame, x, y, r, color, alpha=1.0, halo=3.0):
    if halo:
        pegar(frame, brillo(int(r * halo), color), x, y, alpha * 0.55, 'm', 'm')
    pegar(frame, disco(max(2, int(r)), color), x, y, alpha, 'm', 'm')


# ------------------------------------------------------------------ fondo

def fondo_estrellas():
    rnd = random.Random(7)
    base = np.zeros((H, W, 3), dtype=np.float32) + np.array(BG, dtype=np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot((xx - W / 2) / W, (yy - H / 2) / H)
    base += (np.clip(0.6 - d, 0, 1)[..., None] * np.array([10, 14, 30], dtype=np.float32))
    im = Image.fromarray(np.clip(base, 0, 255).astype('uint8'))
    dr = ImageDraw.Draw(im)
    for _ in range(320):
        x, y = rnd.randrange(W), rnd.randrange(H)
        b = rnd.choice([70, 90, 120, 160, 210])
        dr.point((x, y), fill=(b, b, min(255, b + 20)))
        if rnd.random() < 0.08:
            dr.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(b, b, min(255, b + 20)))
    return im


FONDO = fondo_estrellas()
DEGRADADO_INF = Image.fromarray((np.clip((np.linspace(0, 1, H) - 0.55) / 0.45, 0, 1) ** 1.4 * 170).astype('uint8')[:, None].repeat(W, 1))
NEGRO = Image.new('RGB', (W, H), (0, 0, 0))

# --------------------------------------------------------------- imágenes


def cargar(nombre):
    return Image.open(os.path.join(ORIG, nombre)).convert('RGB')


def recorte(im, zoom, cx, cy):
    w, h = im.size
    cw, ch = w / zoom, h / zoom
    x0 = clamp(cx * w - cw / 2, 0, w - cw)
    y0 = clamp(cy * h - ch / 2, 0, h - ch)
    return im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BILINEAR)


_cache_im = {}


def escena_imagen(archivo, t, ini, fin, z0, z1, c0, c1, oscuro=0.0, desenfoque=0):
    if archivo not in _cache_im:
        _cache_im[archivo] = cargar(archivo)
    im = _cache_im[archivo]
    u = ss((t - ini) / (fin - ini))
    fr = recorte(im, lerp(z0, z1, u), lerp(c0[0], c1[0], u), lerp(c0[1], c1[1], u))
    if desenfoque:
        fr = fr.filter(ImageFilter.GaussianBlur(desenfoque))
    if oscuro:
        fr = Image.blend(fr, Image.new('RGB', (W, H), BG), oscuro)
    fr.paste(NEGRO, (0, 0), DEGRADADO_INF)
    return fr


# ------------------------------------------------------------ texto para subtítulos


def trocear_texto(txt, maximo=84):
    partes, actual = [], ''
    for fr in [p for p in txt.replace('. ', '.|').replace(': ', ':|').replace(', ', ',|').split('|')]:
        if actual and len(actual) + 1 + len(fr) > maximo:
            partes.append(actual)
            actual = fr
        else:
            actual = (actual + ' ' + fr).strip()
    if actual:
        partes.append(actual)
    return [p.rstrip(',') for p in partes]


def envolver(txt, ancho=46):
    if len(txt) <= ancho:
        return [txt]
    mitad = len(txt) // 2
    corte = txt.rfind(' ', 0, mitad + 8)
    corte = corte if corte > 0 else mitad
    return [txt[:corte].strip(), txt[corte:].strip()]
