"""
Estilo espacial de Hace Eones: fondo con nebulosa y estrellas, brillo (bloom), paneles de cristal, texto con resplandor
y planetas realistas dibujados por código (esferas con textura procedural e iluminación). Todo es material propio.
"""
import math

import os

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import aa
from montar import AMBAR, BG, H, HUESO, W, blk, clamp, lerp, mezcla, neg, pegar, reg, sprite_texto, ss

_c = {}
FONDO_ULT = {}          # último fondo limpio entregado a una escena (para rellenar bordes al desplazar el contenido)

# --------------------------------------------------------------------------- ruido


def _ruido(w, h, celdas, semilla):
    rnd = np.random.RandomState(semilla)
    g = rnd.rand(max(2, celdas // 2) + 2, celdas + 1).astype('float32')
    g[:, -1] = g[:, 0]
    im = Image.fromarray((g * 255).astype('uint8')).resize((w, h), Image.BICUBIC)
    return np.asarray(im).astype('float32') / 255


def fbm(w, h, celdas, semilla):
    acc, tot = 0.0, 0.0
    for i, c in enumerate(celdas):
        acc = acc + _ruido(w, h, c, semilla + i * 7) * (0.55 ** i)
        tot += 0.55 ** i
    return acc / tot

# ------------------------------------------------------------------------- fondo


def _warp(n, wx, wy, ax, ay):
    from scipy.ndimage import map_coordinates
    h, w = n.shape
    yy, xx = np.mgrid[0:h, 0:w].astype('float32')
    return map_coordinates(n, [yy + wy * ay, xx + wx * ax], order=1, mode='reflect')


def _banda_via_lactea(w, h):
    """Máscara 0..1 de una banda diagonal suave (la Vía Láctea), con polvo oscuro y grumos."""
    yy, xx = np.mgrid[0:h, 0:w].astype('float32')
    ang = math.radians(-24)
    d = ((xx - w * 0.52) * math.sin(ang) + (yy - h * 0.50) * math.cos(ang)) / (h * 0.20)
    banda = np.exp(-d * d)
    grumos = fbm(w, h, [3, 6, 12, 24], 61)
    polvo = np.clip((fbm(w, h, [4, 9, 18, 36], 77) - 0.52) * 3.2, 0, 1)
    return np.clip(banda * (0.35 + 1.1 * grumos) * (1 - 0.65 * polvo), 0, 1)


def _base():
    """Fondo: nebulosa con filamentos (ruido deformado), banda de Vía Láctea con polvo y viñeta. Sutil, no exagerado."""
    w, h = W // 2, H // 2
    wx = fbm(w, h, [3, 6], 71) - 0.5
    wy = fbm(w, h, [3, 6], 93) - 0.5
    n1 = _warp(fbm(w, h, [3, 6, 12, 24, 48], 5), wx, wy, 220, 170)
    n2 = _warp(fbm(w, h, [4, 9, 18, 36], 21), wy, wx, 160, 120)
    n3 = fbm(w, h, [2, 5], 33)
    n4 = fbm(w, h, [3, 7], 47)
    nube1 = np.clip((n1 - 0.46) * 3.0, 0, 1) ** 1.35
    nube2 = np.clip((n2 - 0.50) * 3.4, 0, 1) ** 1.5
    violeta = np.array([68, 46, 158], np.float32)
    turquesa = np.array([12, 118, 170], np.float32)
    rosa = np.array([150, 58, 122], np.float32)
    mezcla_vt = n3[..., None]
    col = violeta * (1 - mezcla_vt) + turquesa * mezcla_vt
    base = np.zeros((h, w, 3), np.float32) + np.array(BG, np.float32)
    base += nube1[..., None] * col * 0.36
    base += (nube2 * np.clip((n4 - 0.45) * 3, 0, 1))[..., None] * rosa * 0.20
    # banda de Vía Láctea, cálida en el centro y azulada en los bordes
    via = _banda_via_lactea(w, h)
    base += via[..., None] * np.array([156, 150, 190], np.float32) * 0.17
    base += (via ** 2.2)[..., None] * np.array([210, 170, 120], np.float32) * 0.10
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot((xx - w / 2) / w, (yy - h / 2) / h)
    base *= (1.0 - np.clip(d - 0.34, 0, 1)[..., None] * 0.85)
    base += np.clip(0.55 - d, 0, 1)[..., None] * np.array([6, 9, 22], np.float32)
    # polvo muy fino (rompe el degradado y evita bandas de color)
    base += (np.random.RandomState(4).rand(h, w, 1).astype('float32') - 0.5) * 2.2
    return Image.fromarray(np.clip(base, 0, 255).astype('uint8')).resize((W, H), Image.BICUBIC), via


_TEMP = np.array([[170, 195, 255], [210, 222, 255], [255, 250, 240], [255, 232, 190], [255, 196, 140]], np.float32)
_PESO_TEMP = np.array([0.26, 0.30, 0.24, 0.13, 0.07])


def _capa_estrellas(n, semilla, via, brillo_max, glow=False, sesgo=3.0, tam=1.0):
    """Capa aditiva de estrellas (2W de ancho para poder desplazarla). Brillo con ley de potencias: muchas tenues y pocas brillantes;
    más densas dentro de la Vía Láctea. glow=True añade halo suave y pequeños rayos de difracción a las más brillantes."""
    rnd = np.random.RandomState(semilla)
    lienzo = np.zeros((H, 2 * W, 3), np.float32)
    vh, vw = via.shape
    puestas = 0
    while puestas < n:
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        dens = via[min(vh - 1, y * vh // H), min(vw - 1, x * vw // W)]
        if rnd.rand() > 0.40 + 0.60 * dens:
            continue
        puestas += 1
        b = 28 + (brillo_max - 28) * rnd.rand() ** sesgo
        c = _TEMP[rnd.choice(5, p=_PESO_TEMP)]
        c = c / 255.0 * b
        fx, fy = rnd.rand(), rnd.rand()
        radio = 1 if b < 150 else 2
        sig = (0.55 + 0.35 * min(1, b / 255)) * tam
        yy, xx = np.mgrid[-radio - 1:radio + 2, -radio - 1:radio + 2].astype('float32')
        psf = np.exp(-((xx - fx) ** 2 + (yy - fy) ** 2) / (2 * sig * sig))
        psf = psf[..., None] * c[None, None, :]
        for dx in (0, W):
            x0, y0 = x + dx - radio - 1, y - radio - 1
            if y0 < 0 or y0 + psf.shape[0] > H or x0 < 0 or x0 + psf.shape[1] > 2 * W:
                continue
            lienzo[y0:y0 + psf.shape[0], x0:x0 + psf.shape[1]] += psf
        if glow and b > 150:
            R = int(14 + 16 * rnd.rand())
            yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype('float32')
            r2 = xx * xx + yy * yy
            halo = (np.exp(-r2 / (2 * (R / 3.2) ** 2)) * 0.42 + np.exp(-r2 / (2 * (R / 9.0) ** 2)) * 0.7)[..., None] * (c * 0.45)[None, None, :]
            # rayos de difracción (cruz) tenues
            L = int(R * 2.2)
            rayos = np.zeros((2 * L + 1, 2 * L + 1), np.float32)
            t_ = np.arange(-L, L + 1, dtype='float32')
            falloff = np.exp(-np.abs(t_) / (L * 0.34))
            rayos[L, :] += falloff
            rayos[:, L] += falloff
            rayos = rayos[..., None] * (c * 0.42)[None, None, :]
            for dx in (0, W):
                y0, x0 = y - R, x + dx - R
                if y0 >= 0 and y0 + 2 * R + 1 <= H and x0 >= 0 and x0 + 2 * R + 1 <= 2 * W:
                    lienzo[y0:y0 + 2 * R + 1, x0:x0 + 2 * R + 1] += halo
                y0, x0 = y - L, x + dx - L
                if y0 >= 0 and y0 + 2 * L + 1 <= H and x0 >= 0 and x0 + 2 * L + 1 <= 2 * W:
                    lienzo[y0:y0 + 2 * L + 1, x0:x0 + 2 * L + 1] += rayos
    return Image.fromarray(np.clip(lienzo, 0, 255).astype('uint8'))


def _capas():
    if 'fondo' not in _c:
        fondo, via = _base()
        _c['fondo'] = fondo
        _c['e1'] = _capa_estrellas(2600, 3, via, 150, sesgo=3.4)
        _c['e2'] = _capa_estrellas(380, 8, via, 235, sesgo=2.6)
        _c['e3'] = _capa_estrellas(9, 12, via, 255, glow=True, sesgo=0.7, tam=1.1)
    return _c


def base(t):
    """Fondo espacial con tres capas de estrellas en paralaje lento. Se cachea el último fotograma."""
    c = _capas()
    o1, o2, o3 = int((t * 1.6) % W), int((t * 4.0) % W), int((t * 7.5) % W)
    k = (o1, o2, o3)
    if c.get('ult_k') == k:
        FONDO_ULT['bg'] = c['ult']
        return c['ult'].copy()
    fr = c['fondo'].copy()
    for clave, off in (('e1', o1), ('e2', o2), ('e3', o3)):
        fr = ImageChops.add(fr, c[clave].crop((off, 0, off + W, H)))
    c['ult_k'], c['ult'] = k, fr
    FONDO_ULT['bg'] = fr
    return fr.copy()


def bloom(fr, k=0.35, umbral=140):
    pq = fr.resize((W // 8, H // 8), Image.BILINEAR)
    lut = [min(255, int(max(0, v - umbral) * k * 3)) for v in range(256)]
    b = pq.point(lut * 3).filter(ImageFilter.GaussianBlur(3))
    return ImageChops.add(fr, b.resize((W, H), Image.BILINEAR))


def hud(fr, a=0.5):
    """Marco de esquinas (estilo visor). Desde el video 2 está APAGADO por defecto (decisión del 14-oct-2026); HE_HUD=1 lo activa."""
    if os.environ.get('HE_HUD', '0') != '1':
        return
    m, L = 30, 64
    pares = []
    for x, y, sx, sy in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        pares.append(((x, y), (x + sx * L, y)))
        pares.append(((x, y), (x, y + sy * L)))
    aa.lineas(fr, pares, AMBAR, 2, a * 0.75)

# ------------------------------------------------------------------ paneles y texto


def _mascara(w, h, r):
    k = ('mk', w, h, r)
    if k not in _c:
        s = 3
        m = Image.new('L', (w * s, h * s), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, w * s - 1, h * s - 1), r * s, fill=255)
        _c[k] = m.resize((w, h), Image.LANCZOS)
    return _c[k]


def panel(fr, x0, y0, x1, y1, color=AMBAR, a=1.0, radio=16, oscuro=0.55, blur=14):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    w, h = x1 - x0, y1 - y0
    if w < 8 or h < 8 or a <= 0:
        return
    reg_ = fr.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(blur))
    reg_ = Image.blend(reg_, Image.new('RGB', reg_.size, (5, 8, 22)), oscuro)
    m = _mascara(w, h, radio)
    fr.paste(reg_, (x0, y0), m.point(lambda v: int(v * a)) if a < 1 else m)
    aa.rrect(fr, (x0, y0, x1, y1), radio, color, 2, 0.85 * a)


def etq(fr, s, fnt, color, x, y, a=1.0, ax='l', ay='t', pad=10):
    """Texto con una pastilla oscura detrás, para que ninguna línea pase por debajo de las letras."""
    if a <= 0:
        return
    spr = sprite_texto(s, fnt, color)
    w, h = spr[1].size
    if ax == 'm':
        x0 = x - w / 2
    elif ax == 'r':
        x0 = x - w
    else:
        x0 = x
    y0 = y if ay == 't' else (y - h / 2 if ay == 'm' else y - h)
    bx0, by0 = int(x0 - pad), int(y0 - pad // 2)
    bw, bh = int(w + 2 * pad), int(h + pad)
    m = _mascara(bw, bh, 10).point(lambda v: int(v * 0.86 * a))
    fr.paste(Image.new('RGB', (bw, bh), (6, 9, 24)), (bx0, by0), m)
    aa.rrect(fr, (bx0, by0, bx0 + bw, by0 + bh), 10, color, 1, 0.30 * a)
    pegar(fr, spr, x0, y0, a, 'l', 't')


def txt_glow(fr, s, fnt, color, x, y, a=1.0, ax='l', ay='t', radio=10, fuerza=0.55):
    if a <= 0:
        return
    spr = sprite_texto(s, fnt, color)
    k = ('glw', s, id(fnt), color, radio)
    if k not in _c:
        w, h = spr[1].size
        m = Image.new('L', (w + 4 * radio, h + 4 * radio), 0)
        m.paste(spr[1], (2 * radio, 2 * radio))
        _c[k] = (Image.new('RGB', m.size, color), m.filter(ImageFilter.GaussianBlur(radio)))
    rgb, m = _c[k]
    w, h = spr[1].size
    if ax == 'm':
        x0 = x - w / 2
    elif ax == 'r':
        x0 = x - w
    else:
        x0 = x
    y0 = y if ay == 't' else (y - h / 2 if ay == 'm' else y - h)
    fr.paste(rgb, (int(x0 - 2 * radio), int(y0 - 2 * radio)), m.point(lambda v: int(v * fuerza * a)))
    pegar(fr, spr, x0, y0, a, 'l', 't')


def linea_glow(fr, pts, color, ancho=3, a=1.0, glow=1.0, cache=False):
    """Línea suavizada con resplandor (transparencia real: nunca más oscura que el fondo)."""
    if len(pts) < 2:
        return
    aa.linea(fr, pts, color, ancho, a, glow=glow, ss=3 if cache else 2, cache=cache)

# ------------------------------------------------------------------- planetas

_ST = {}


def _tex(nombre):
    if nombre in _ST:
        return _ST[nombre]
    w, h = 512, 256
    lat = np.linspace(90, -90, h)[:, None] * np.ones((1, w))
    f1 = fbm(w, h, [4, 8, 16, 32], 3)
    f2 = fbm(w, h, [6, 12, 24, 48], 9)
    if nombre == 'tierra':
        oc = np.array([12, 50, 128], np.float32)
        t = np.clip((f1 - 0.52) * 5, 0, 1)[..., None]
        tierra = np.array([58, 112, 56], np.float32) * (1 - t) + np.array([134, 110, 72], np.float32) * t
        c = np.where((f1 > 0.52)[..., None], tierra, oc)
        hielo = np.clip((np.abs(lat) - 72) / 8, 0, 1)[..., None]
        c = c * (1 - hielo) + 245 * hielo
        nube = np.clip((f2 - 0.50) * 3.5, 0, 1)[..., None] * 0.85
        c = c * (1 - nube) + 255 * nube
    elif nombre == 'jupiter':
        b = 0.5 + 0.5 * np.sin(np.radians(lat) * 17 + f2 * 3.2)
        t = np.clip(b * 0.75 + f1 * 0.25, 0, 1)[..., None]
        c1, c2, c3 = np.array([236, 212, 178], np.float32), np.array([196, 134, 92], np.float32), np.array([132, 88, 66], np.float32)
        c = np.where(t < 0.5, c1 * (1 - t * 2) + c2 * (t * 2), c2 * (1 - (t - 0.5) * 2) + c3 * ((t - 0.5) * 2))
        lon = np.linspace(-1, 1, w)[None, :] * np.ones((h, 1))
        mancha = np.clip(1 - (((lon - 0.35) / 0.12) ** 2 + ((lat + 22) / 7) ** 2), 0, 1)[..., None]
        c = c * (1 - mancha) + np.array([196, 88, 66], np.float32) * mancha
    elif nombre == 'saturno':
        b = 0.5 + 0.5 * np.sin(np.radians(lat) * 13 + f2 * 2.2)
        t = np.clip(b * 0.6 + f1 * 0.4, 0, 1)[..., None]
        c = np.array([232, 212, 160], np.float32) * (1 - t) + np.array([198, 172, 122], np.float32) * t
    elif nombre == 'marte':
        t = np.clip((f1 - 0.45) * 3, 0, 1)[..., None]
        c = np.array([182, 92, 56], np.float32) * (1 - t) + np.array([112, 62, 46], np.float32) * t
        hielo = np.clip((np.abs(lat) - 80) / 6, 0, 1)[..., None]
        c = c * (1 - hielo) + 240 * hielo
    elif nombre == 'venus':
        t = np.clip(f2 * 1.2, 0, 1)[..., None]
        c = np.array([240, 220, 168], np.float32) * (1 - t * 0.5) + np.array([210, 176, 120], np.float32) * (t * 0.5)
    elif nombre == 'mercurio':
        f3 = fbm(w, h, [24, 48, 96], 15)
        t = np.clip(f3, 0, 1)[..., None]
        c = np.array([150, 144, 138], np.float32) * (0.55 + 0.6 * t)
    elif nombre == 'urano':
        t = np.clip(f1, 0, 1)[..., None]
        c = np.array([158, 214, 224], np.float32) * (0.92 + 0.12 * t)
    elif nombre == 'neptuno':
        b = 0.5 + 0.5 * np.sin(np.radians(lat) * 9 + f2 * 2.0)
        c = np.array([40, 78, 200], np.float32) * (0.78 + 0.3 * b[..., None])
    else:  # sol
        g = fbm(w, h, [16, 32, 64, 128], 41)[..., None]
        c = np.array([255, 150, 28], np.float32) + g * np.array([0, 95, 70], np.float32)
    _ST[nombre] = np.clip(c, 0, 255).astype('uint8')
    return _ST[nombre]


def planeta(nombre, R, luz=(1.0, 0.0), fase=0.0):
    """Esfera con textura procedural, luz desde `luz` (dx, dy en pantalla) y rotación `fase` (0..1)."""
    k = ('pl', nombre, R, round(luz[0], 1), round(luz[1], 1), int(fase * 24) % 24)
    if k in _c:
        return _c[k]
    S = 2 * R + 6
    yy, xx = np.mgrid[0:S, 0:S].astype('float32')
    u = (xx - S / 2 + 0.5) / R
    v = (yy - S / 2 + 0.5) / R
    d2 = u * u + v * v
    z = np.sqrt(np.clip(1 - d2, 0, 1))
    ny = -v
    lat = np.arcsin(np.clip(ny, -1, 1))
    lon = np.arctan2(u, z) + (int(fase * 24) % 24) / 24 * 2 * math.pi
    tex = _tex(nombre)
    th, tw = tex.shape[:2]
    tx = (((lon / (2 * math.pi)) + 0.5) % 1.0 * tw).astype(int) % tw
    ty = np.clip(((0.5 - lat / math.pi) * th).astype(int), 0, th - 1)
    col = tex[ty, tx].astype('float32')
    if nombre == 'sol':
        col *= (0.78 + 0.34 * z)[..., None]
    else:
        L = np.array([luz[0], -luz[1], 0.40], np.float32)
        L /= np.linalg.norm(L)
        nd = np.clip(u * L[0] + ny * L[1] + z * L[2], 0, 1)
        col *= (0.07 + 0.93 * nd ** 0.85)[..., None]
        if nombre in ('tierra', 'venus', 'urano', 'neptuno', 'marte'):
            rim = ((1 - z) ** 3 * (0.15 + 0.85 * nd))[..., None]
            tinte = {'tierra': (80, 150, 255), 'venus': (255, 220, 160), 'urano': (170, 230, 240), 'neptuno': (90, 130, 255), 'marte': (255, 170, 120)}[nombre]
            col = col + rim * np.array(tinte, np.float32) * 0.9
    alfa = np.clip((1 - np.sqrt(d2)) * R + 0.5, 0, 1)
    spr = (Image.fromarray(np.clip(col, 0, 255).astype('uint8')), Image.fromarray((alfa * 255).astype('uint8')))
    _c[k] = spr
    return spr


def anillos(R, mitad, inclin=0.42):
    """Anillos de Saturno vistos en perspectiva. mitad: 'atras' (parte lejana) o 'frente'."""
    k = ('an', R, mitad)
    if k in _c:
        return _c[k]
    ancho = int(R * 5.2)
    alto = int(R * 5.2 * inclin) + 8
    yy, xx = np.mgrid[0:alto, 0:ancho].astype('float32')
    u = (xx - ancho / 2) / R
    v = (yy - alto / 2) / (R * inclin)
    r = np.hypot(u, v)
    a = ((r > 1.30) & (r < 2.30)).astype('float32')
    a *= 0.45 + 0.35 * np.sin(r * 22) ** 2
    a *= np.where((r > 1.92) & (r < 2.0), 0.15, 1.0)
    a *= np.clip((r - 1.30) / 0.05, 0, 1) * np.clip((2.30 - r) / 0.05, 0, 1)
    a *= 0.9
    if mitad == 'atras':
        a = np.where(yy < alto / 2, a, 0)
    else:
        a = np.where(yy >= alto / 2, a, 0)
    col = np.zeros((alto, ancho, 3), np.float32) + np.array([224, 202, 158], np.float32)
    spr = (Image.fromarray(col.astype('uint8')), Image.fromarray((np.clip(a, 0, 1) * 255).astype('uint8')))
    _c[k] = spr
    return spr


def dibujar_planeta(fr, nombre, x, y, R, luz, a=1.0, fase=0.0, resplandor=True):
    if a <= 0:
        return
    if nombre == 'saturno':
        rgb, m = anillos(R, 'atras')
        fr.paste(rgb, (int(x - rgb.width / 2), int(y - rgb.height / 2)), m.point(lambda v: int(v * a)) if a < 1 else m)
    rgb, m = planeta(nombre, R, luz, fase)
    if resplandor and nombre == 'sol':
        pegar(fr, _brillo(int(R * 3.4), (255, 150, 40)), x, y, 0.75 * a, 'm', 'm')
    fr.paste(rgb, (int(x - rgb.width / 2), int(y - rgb.height / 2)), m.point(lambda v: int(v * a)) if a < 1 else m)
    if nombre == 'saturno':
        rgb, m = anillos(R, 'frente')
        fr.paste(rgb, (int(x - rgb.width / 2), int(y - rgb.height / 2)), m.point(lambda v: int(v * a)) if a < 1 else m)


def _brillo(radio, color):
    k = ('br', radio, color)
    if k not in _c:
        n = radio * 2
        yy, xx = np.mgrid[0:n, 0:n]
        d = np.hypot(xx - radio + 0.5, yy - radio + 0.5) / radio
        al = np.clip(1 - d, 0, 1) ** 2.4
        _c[k] = (Image.new('RGB', (n, n), color), Image.fromarray((al * 255).astype('uint8')))
    return _c[k]


# ------------------------------------------------------------------ perspectiva


class Vista:
    """Vista oblicua del plano de los planetas: elevación ~27°, centro en (cx, cy)."""

    def __init__(self, cx=960, cy=440, inclin=0.46):
        self.cx, self.cy, self.k = cx, cy, inclin
        self.kz = math.sqrt(1 - inclin * inclin)

    def p(self, X, Y, Z=0.0):
        return self.cx + X, self.cy + Y * self.k - Z * self.kz

    def orbita(self, r, n=180):
        return [self.p(r * math.cos(2 * math.pi * i / n), -r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]

    def planeta(self, r, ang_deg):
        a = math.radians(ang_deg)
        return r * math.cos(a), -r * math.sin(a)


def capa_orbitas(vista, radios, color=HUESO, alfa=0.20):
    k = ('orb', vista.cx, vista.cy, vista.k, tuple(radios))
    if k not in _c:
        s = 2
        im = Image.new('L', (W * s, H * s), 0)
        d = ImageDraw.Draw(im)
        for r in radios:
            pts = [(x * s, y * s) for x, y in vista.orbita(r)]
            d.line(pts, fill=int(255 * alfa), width=2 * s)
        _c[k] = im.resize((W, H), Image.LANCZOS)
    return _c[k]
