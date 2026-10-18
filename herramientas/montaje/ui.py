"""
Interfaz espacial (v3): marca, rótulos «Dato verificado», tarjetas, títulos y etiquetas.

Estilo: vidrio oscuro con esquinas cortadas, bordes con degradado, textos con letra espaciada y entradas con barrido
de luz. Es sobrio a propósito: pocos elementos, mucho contraste y nada que tape el contenido.
Todo es código propio (sin plantillas ni recursos de terceros).
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import aa
from montar import AMBAR, BG, H, HUESO, LOGO, NOMBRE, W, blk, clamp, fuente_peso, lerp, mezcla, neg, pegar, reg, sprite_texto, ss

HIELO = (150, 190, 255)
VERDE = (120, 205, 190)
ROJO = (232, 96, 84)
GRIS = mezcla(BG, HUESO, 0.55)
VIDRIO = (5, 8, 22)

_c = {}


def sl(t): return fuente_peso('light', t)         # ligera
def sb(t): return fuente_peso('bold', t)          # negrita


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp(x)
    return x ** 2

# ------------------------------------------------------------------ texto con letra espaciada


def sprite_esp(texto, fnt, color, track=3):
    """Texto con espacio extra entre letras (rótulos pequeños en mayúsculas)."""
    k = ('esp', texto, id(fnt), color, track)
    if k not in _c:
        anchos = [fnt.getlength(ch) + track for ch in texto]
        w = int(sum(anchos)) + 6
        x0, y0, x1, y1 = fnt.getbbox('Hg')
        h = y1 + 8
        m = Image.new('L', (w, h), 0)
        d = ImageDraw.Draw(m)
        x = 2.0
        for ch, aw in zip(texto, anchos):
            d.text((x, 2), ch, font=fnt, fill=255)
            x += aw
        _c[k] = (Image.new('RGB', m.size, color), m)
    return _c[k]


def _poly(w, h, c):
    return [(0, 0), (w - c, 0), (w, c), (w, h), (c, h), (0, h - c)]


def mascara_chaflan(w, h, c):
    k = ('chaf', w, h, c)
    if k not in _c:
        s = 3
        m = Image.new('L', (w * s, h * s), 0)
        ImageDraw.Draw(m).polygon([(x * s, y * s) for x, y in _poly(w - 1, h - 1, c)], fill=255)
        _c[k] = m.resize((w, h), Image.LANCZOS)
    return _c[k]


def _columnas(w, h, frente, suave=30):
    """Máscara de barrido: visible a la izquierda de «frente» (px), con borde suave."""
    xs = np.arange(w, dtype=np.float32)
    col = np.clip((frente - xs) / suave, 0, 1)
    return np.repeat(col[None, :], h, axis=0)

# ---------------------------------------------------------------------------- caja de vidrio


def _marco(w, h, c, color, barra=True):
    """Borde con degradado (fuerte a la izquierda, tenue a la derecha), esquinas cortadas y barra de acento."""
    k = ('marco', w, h, c, color, barra)
    if k in _c:
        return _c[k]
    s = 3
    m = Image.new('L', (w * s, h * s), 0)
    d = ImageDraw.Draw(m)
    pts = [(x * s, y * s) for x, y in _poly(w - 2, h - 2, c)]
    d.line(pts + [pts[0]], fill=255, width=2 * s, joint='curve')
    m = m.resize((w, h), Image.LANCZOS)
    a = np.asarray(m, np.float32) / 255
    xs = np.linspace(1.0, 0.28, w, dtype=np.float32)[None, :]
    a = a * xs
    # destellos en las esquinas cortadas
    rgb = Image.new('RGB', (w, h), color)
    al = Image.fromarray((a * 255).astype('uint8'))
    if barra:
        b = Image.new('L', (w, h), 0)
        ImageDraw.Draw(b).rounded_rectangle((0, c + 4, 4, h - c - 4), 2, fill=255)
        glow = b.filter(ImageFilter.GaussianBlur(5)).point(lambda v: int(v * 0.8))
        al = Image.fromarray(np.maximum(np.asarray(al), np.maximum(np.asarray(b), np.asarray(glow))))
    _c[k] = (rgb, al)
    return _c[k]


def caja(fr, x0, y0, w, h, color=AMBAR, a=1.0, p=1.0, c=14, oscuro=0.6, blur=12, barra=True, relleno=None, suave=30):
    """Panel de vidrio con borde de degradado. p = fracción revelada de izquierda a derecha (barrido)."""
    x0, y0, w, h = int(x0), int(y0), int(w), int(h)
    if a <= 0 or p <= 0 or w < 20 or h < 20:
        return
    # recorte a la pantalla
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(W, x0 + w), min(H, y0 + h)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    vid = fr.crop((cx0, cy0, cx1, cy1)).filter(ImageFilter.GaussianBlur(blur))
    vid = Image.blend(vid, Image.new('RGB', vid.size, relleno or VIDRIO), oscuro)
    m = np.asarray(mascara_chaflan(w, h, c), np.float32) / 255
    if p < 1:
        m = m * _columnas(w, h, p * w + 10, suave)
    m = m * a
    mm = m[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    fr.paste(vid, (cx0, cy0), Image.fromarray((mm * 255).astype('uint8')))
    rgb, al = _marco(w, h, c, color, barra)
    al = np.asarray(al, np.float32) / 255
    if p < 1:
        al = al * _columnas(w, h, p * w + 10, suave)
    al = al * a
    aa = al[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    fr.paste(rgb.crop((cx0 - x0, cy0 - y0, cx1 - x0, cy1 - y0)), (cx0, cy0), Image.fromarray((aa * 255).astype('uint8')))


def barrido(fr, x, y0, y1, a=1.0, color=HUESO):
    """Línea de luz vertical (frente del barrido de entrada)."""
    if a <= 0:
        return
    h = int(y1 - y0)
    k = ('barr', h, color)
    if k not in _c:
        xs = np.arange(-24, 25, dtype=np.float32)[None, :]
        ys = np.arange(h, dtype=np.float32)[:, None]
        borde = np.clip(np.minimum(ys, h - 1 - ys) / 18, 0, 1)
        nuc = np.exp(-(xs / 1.6) ** 2)
        hal = np.exp(-(xs / 12.0) ** 2) * 0.35
        al = np.clip(nuc + hal, 0, 1) * borde
        _c[k] = (Image.new('RGB', (49, h), color), Image.fromarray((al * 255).astype('uint8')))
    rgb, m = _c[k]
    if a < 1:
        m = m.point(lambda v: int(v * a))
    fr.paste(rgb, (int(x) - 24, int(y0)), m)

# ------------------------------------------------------------------------------ iconos


def _s3(w, h):
    return Image.new('L', (w * 3, h * 3), 0)


def icono_hex(fr, cx, cy, r, color, a=1.0, glifo='check', ancho=2):
    """Hexágono con un símbolo dentro (check, igual, reloj de arena…)."""
    s = 3
    n = int(r * 2 + 12)
    m = Image.new('L', (n * s, n * s), 0)
    d = ImageDraw.Draw(m)
    c = n * s / 2
    R = r * s
    pts = [(c + R * math.cos(math.radians(60 * i - 90)), c + R * math.sin(math.radians(60 * i - 90))) for i in range(6)]
    d.line(pts + [pts[0]], fill=255, width=2 * s, joint='curve')
    u = R / 2.2
    if glifo == 'check':
        d.line([(c - u * 0.55, c + u * 0.05), (c - u * 0.1, c + u * 0.5), (c + u * 0.62, c - u * 0.42)], fill=255, width=int(2.2 * s), joint='curve')
    elif glifo == 'igual':
        d.line([(c - u * 0.55, c - u * 0.22), (c + u * 0.55, c - u * 0.22)], fill=255, width=int(2.2 * s))
        d.line([(c - u * 0.55, c + u * 0.24), (c + u * 0.55, c + u * 0.24)], fill=255, width=int(2.2 * s))
    m = m.resize((n, n), Image.LANCZOS)
    if a < 1:
        m = m.point(lambda v: int(v * a))
    fr.paste(Image.new('RGB', m.size, color), (int(cx - n / 2), int(cy - n / 2)), m)


def anillo_arco(fr, cx, cy, r, color, frac=1.0, a=1.0, ancho=4, inicio=-90, relleno_tenue=0.18, guion=False):
    """Anillo con un arco resaltado (progreso). frac = fracción del círculo resaltada."""
    if a <= 0:
        return
    s = 3
    n = int(r * 2 + ancho * 2 + 16)
    c = n * s / 2
    R = r * s
    caja_ = (c - R, c - R, c + R, c + R)
    base_ = Image.new('L', (n * s, n * s), 0)
    d = ImageDraw.Draw(base_)
    if guion:
        for i in range(12):
            d.arc(caja_, i * 30 + inicio, i * 30 + 18 + inicio, fill=255, width=ancho * s)
    else:
        d.ellipse(caja_, outline=int(255 * relleno_tenue), width=ancho * s)
    arc = Image.new('L', (n * s, n * s), 0)
    if frac > 0 and not guion:
        ImageDraw.Draw(arc).arc(caja_, inicio, inicio + 360 * clamp(frac), fill=255, width=ancho * s)
    m = Image.fromarray(np.maximum(np.asarray(base_), np.asarray(arc)))
    m = m.resize((n, n), Image.LANCZOS)
    hal = m.filter(ImageFilter.GaussianBlur(5)).point(lambda v: int(v * 0.55))
    fr.paste(Image.new('RGB', m.size, color), (int(cx - n / 2), int(cy - n / 2)), hal.point(lambda v: int(v * a)))
    fr.paste(Image.new('RGB', m.size, color), (int(cx - n / 2), int(cy - n / 2)), m.point(lambda v: int(v * a)) if a < 1 else m)

# ----------------------------------------------------------------------------- marca


def _marca(n=40):
    """Logo real del canal (el PNG que indica `logo` en identidad.json),
    recortado en círculo, igual que se ve el avatar en YouTube."""
    k = ('marca', n)
    if k in _c:
        return _c[k]
    if LOGO and os.path.exists(LOGO):                        # logo del canal (identidad.json); es un PNG de 800 px
        im = Image.open(LOGO).convert('RGB')
    else:                                                    # sin logo: disco ámbar liso
        im = Image.new('RGB', (800, 800), (242, 184, 75))
    im = im.crop((110, 110, 690, 690))                       # solo los anillos, sin el cielo de los bordes
    s = 4
    big = im.resize((n * s, n * s), Image.LANCZOS)
    m = Image.new('L', (n * s, n * s), 0)
    ImageDraw.Draw(m).ellipse((0, 0, n * s - 1, n * s - 1), fill=255)
    rgb = big.resize((n, n), Image.LANCZOS)
    mk = m.resize((n, n), Image.LANCZOS)
    _c[k] = (rgb, mk)
    return _c[k]


def logo(fr, a=1.0):
    """Marca del canal: el logo real en círculo + el nombre con letra espaciada."""
    rgb, mk = _marca(42)
    x, y = 90, 34
    txt = sprite_esp(NOMBRE, neg(19), mezcla(BG, HUESO, 0.80), 3.4)
    sombra = txt[1].filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.9))
    fr.paste(Image.new('RGB', sombra.size, (3, 5, 14)), (x + 54 - 2, y + 11), sombra)
    aa.elipse(fr, (x - 1, y - 1, x + 43, y + 43), AMBAR, 1, 0.55 * a)
    fr.paste(rgb, (x, y), mk.point(lambda v: int(v * a)) if a < 1 else mk)
    pegar(fr, txt, x + 54, y + 12, a)


def etiqueta_esquema(fr, texto='ESQUEMA · NO A ESCALA', a=0.9):
    """Aviso discreto bajo la marca. Solo en escenas que dibujan posiciones o tamaños que no son reales."""
    x, y = 96, 44
    aa.poli(fr, [(x + 1, y + 9), (x + 6, y + 4), (x + 11, y + 9), (x + 6, y + 14)], AMBAR, 0.75 * a, ancho=1)
    pegar(fr, sprite_esp(texto, sb(14), mezcla(BG, HUESO, 0.62 * a), 2.6), x + 18, y + 2, 1.0)


def credito(fr, texto, a=1.0, k=0):
    """Crédito de la imagen (arriba a la derecha)."""
    if a <= 0:
        return
    x = W - 96
    y = 46 + 32 * k
    s = sprite_texto(texto, reg(21), mezcla(BG, HUESO, 0.82))
    pegar(fr, s, x, y, a, 'r')
    pegar(fr, sprite_esp('IMAGEN', sb(12), mezcla(BG, AMBAR, 0.85), 2.4), x - s[1].size[0] - 16, y + 5, a, 'r')

# ----------------------------------------------------------------------------- rótulo de dato


def _contenido_rotulo(l1, l2, estilo):
    k = ('rot', l1, l2, estilo)
    if k in _c:
        return _c[k]
    calc = estilo == 'calculo'
    color = HIELO if calc else AMBAR
    cab = sprite_esp('CÁLCULO PROPIO' if calc else 'DATO VERIFICADO', sb(15), color, 2.8)
    s1 = sprite_texto(l1, neg(31), HUESO)
    s2 = sprite_texto(l2, sl(22), mezcla(BG, HUESO, 0.62))
    pad = 28
    ix = pad + 36                                  # inicio del texto (tras el icono)
    w = int(max(s1[1].size[0], s2[1].size[0], cab[1].size[0] + 140) + ix + pad + 6)
    h = int(cab[1].size[1] + s1[1].size[1] + s2[1].size[1] + 38)
    _c[k] = (w, h, color, cab, s1, s2, ix)
    return _c[k]


def rotulo(fr, t, ini, fin, l1, l2, estilo='dato', base=912):
    """Rótulo de dato: aparece con un barrido de luz lento y suave (1,3 s) y se retira igual (1,0 s)."""
    dur = fin - ini
    din, dout = min(1.3, 0.22 * dur), min(1.0, 0.18 * dur)       # los rótulos cortos entran y salen más deprisa para que se lean
    pi = ss((t - ini) / din)
    po = ss((t - (fin - dout)) / dout)
    p = pi * (1 - po)
    if p <= 0.005:
        return
    w, h, color, cab, s1, s2, ix = _contenido_rotulo(l1, l2, estilo)
    x0 = 96
    y0 = int(base - h + (1 - p) * 12)                  # sube unos píxeles al entrar y baja al salir
    a = clamp(p * 2.2)
    caja(fr, x0, y0, w, h, color, a, p, c=16, oscuro=0.62, suave=90)
    icono_hex(fr, x0 + 34, y0 + 28, 12, color, a * clamp((p - 0.35) * 2.5), 'igual' if estilo == 'calculo' else 'check')
    tex = ss((p - 0.30) / 0.70)                       # el texto se descubre detrás del barrido
    off = int((1 - tex) * 18)
    if tex > 0:
        rec = lambda spr, x, y: _pegar_recortado(fr, spr, x0 + x + off, y0 + y, tex * a, (p * w + 40) - (x + off))
        rec(cab, ix, 14)
        lx0, lx1 = ix + cab[1].size[0] + 14, w - 30
        if lx1 > lx0:
            aa.linea(fr, [(x0 + lx0, y0 + 25), (x0 + lx0 + (lx1 - lx0) * tex, y0 + 25)], color, 1, 0.40 * a * tex, ss=2)
            aa.elipse(fr, (x0 + lx0 + (lx1 - lx0) * tex - 2.5, y0 + 22.5, x0 + lx0 + (lx1 - lx0) * tex + 2.5, y0 + 27.5), color, 1, 0.85 * a * tex, relleno=True, ss=2)
        rec(s1, ix, 14 + cab[1].size[1] + 4)
        rec(s2, ix, 14 + cab[1].size[1] + 4 + s1[1].size[1] + 2)
    if p > 0.98:                                      # brillo que recorre el borde superior mientras está quieto
        u = ((t - ini - din) / 3.6) % 2.0
        if u < 1.0:
            bx = x0 + 16 + (w - 60) * u
            aa.linea(fr, [(bx - 40, y0 + 1), (bx + 40, y0 + 1)], HUESO, 2, 0.5 * math.sin(math.pi * u), ss=2)
    if p < 0.995:                                     # frente de luz del barrido, tenue
        barrido(fr, x0 + p * w, y0 + 4, y0 + h - 4, 0.55 * (1 - p) ** 0.5, color)


def _pegar_recortado(fr, spr, x, y, a, limite):
    """Pega un sprite recortado a la derecha de «limite» (px desde su borde izquierdo)."""
    rgb, m = spr
    w, h = m.size
    if limite <= 0:
        return
    if limite < w:
        col = _columnas(w, h, limite, 14)
        m = Image.fromarray((np.asarray(m, np.float32) * col).astype('uint8'))
    if a < 1:
        m = m.point(lambda v: int(v * a))
    fr.paste(rgb, (int(x), int(y)), m)

# -------------------------------------------------------------------------------- títulos


def titulo(fr, eyebrow, texto, x, y, a=1.0, ax='l', tam=44, color=HUESO):
    """Etiqueta pequeña con letra espaciada + título. y = arriba de la etiqueta."""
    if a <= 0:
        return
    e = sprite_esp(eyebrow, sb(16), AMBAR, 3.0)
    s = sprite_texto(texto, neg(tam), color)
    wmax = max(e[1].size[0] + 60, s[1].size[0])
    x0 = x if ax == 'l' else (x - wmax / 2 if ax == 'm' else x - wmax)
    ex = x0 if ax == 'l' else (x - e[1].size[0] / 2 if ax == 'm' else x - e[1].size[0])
    pegar(fr, e, ex, y, a)
    ly = y + 11
    if ax == 'l':
        aa.linea(fr, [(ex + e[1].size[0] + 12, ly), (ex + e[1].size[0] + 52, ly)], AMBAR, 1, 0.5 * a, ss=2)
    sx = x0 if ax == 'l' else (x - s[1].size[0] / 2 if ax == 'm' else x - s[1].size[0])
    pegar(fr, s, sx, y + 26, a)
    return y + 26 + s[1].size[1]


def pastilla(fr, texto, x, y, color=AMBAR, a=1.0, ax='l'):
    """Etiqueta pequeña con el MISMO estilo que los rótulos «Dato verificado»: cristal oscuro, esquina cortada, barra lateral e
    icono hexagonal. (Regla del canal, 14-oct-2026: ninguna caja de texto usa cápsulas redondeadas con borde.)"""
    if a <= 0:
        return
    s = sprite_esp(texto, sb(15), color, 2.6)
    w, h = s[1].size
    bw, bh = w + 62, max(40, h + 22)
    x0 = x if ax == 'l' else (x - bw / 2 if ax == 'm' else x - bw)
    caja(fr, int(x0), int(y), bw, bh, color, a, 1.0, c=10, oscuro=0.62, blur=12, barra=True, suave=40)
    icono_hex(fr, int(x0) + 26, int(y) + bh // 2, 8, color, a, 'igual' if 'CÁLCULO' in texto.upper() else 'check', 2)
    pegar(fr, s, x0 + 44, y + (bh - h) // 2, a)


# ------------------------------------------------------------------- tarjetas de capítulo y llamada a la acción

def _pt(cx, cy, s, pts):
    return [(cx + (x - 12) * s, cy + (y - 12) * s) for x, y in pts]


def icono_cta(fr, tipo, cx, cy, s, color, a=1.0):
    """Iconos de línea de 24×24 (campana, pulgar arriba, comentario), dibujados con trazo suavizado."""
    w = max(1.4, 1.7 * s)
    if tipo == 'campana':
        dom = [(12 + 6.2 * math.cos(math.radians(g)), 10 + 6.2 * math.sin(math.radians(g))) for g in range(180, 361, 15)]
        pts = [(5.8, 17)] + [(5.8, 10)] + dom[1:-1] + [(18.2, 10), (18.2, 17), (20, 18), (4, 18), (5.8, 17)]
        aa.linea(fr, _pt(cx, cy, s, pts), color, w, a, ss=3)
        aa.linea(fr, _pt(cx, cy, s, [(10, 20.5), (14, 20.5)]), color, w, a, ss=3)
        aa.linea(fr, _pt(cx, cy, s, [(12, 3.2), (12, 4.2)]), color, w, a, ss=3)
    elif tipo == 'like':
        pts = [(8.5, 21), (8.5, 10.5), (12, 3.5), (14.2, 4.4), (13.4, 9), (20, 9), (21.2, 11), (19.4, 19), (17.6, 21), (8.5, 21)]
        aa.linea(fr, _pt(cx, cy, s, pts), color, w, a, ss=3)
        aa.linea(fr, _pt(cx, cy, s, [(2.6, 10.5), (6.4, 10.5), (6.4, 21), (2.6, 21), (2.6, 10.5)]), color, w, a, ss=3)
    else:  # comentario
        aa.rrect(fr, (cx - 9 * s, cy - 8 * s, cx + 9 * s, cy + 4 * s), max(2, 3 * s), color, w, a, ss=3, cache=False)
        aa.linea(fr, _pt(cx, cy, s, [(7.5, 16), (7.5, 20.5), (12, 16)]), color, w, a, ss=3)


def capitulo(fr, t, ini, num, titulo, dur=4.8):
    """Tarjeta de capítulo (arriba a la derecha): número en anillo + título, con barrido de luz."""
    din, dout = 0.9, 0.7
    p = ss((t - ini) / din) * (1 - ss((t - (ini + dur - dout)) / dout))
    if p <= 0.01:
        return
    cab = sprite_esp('CAPÍTULO ' + str(num).zfill(2), sb(14), AMBAR, 2.8)
    s1 = sprite_texto(titulo, neg(30), HUESO)
    w = int(max(cab[1].size[0] + 60, s1[1].size[0]) + 118)
    h = 92
    x0, y0 = W - 96 - w, 124
    caja(fr, x0, y0, w, h, AMBAR, 1.0, p, c=14, oscuro=0.6, suave=70)
    tx = ss((p - 0.3) / 0.7)
    if tx > 0:
        anillo_arco(fr, x0 + 52, y0 + h // 2, 24, AMBAR, 1.0, tx, 3, -90, 0.5)
        pegar(fr, sprite_texto(str(num), blk(26), AMBAR), x0 + 52, y0 + h // 2, tx, 'm', 'm')
        off = int((1 - tx) * 14)
        pegar(fr, cab, x0 + 96 + off, y0 + 16, tx)
        pegar(fr, s1, x0 + 96 + off, y0 + 16 + cab[1].size[1] + 2, tx)
    if p < 0.99:
        barrido(fr, x0 + p * w, y0 + 4, y0 + h - 4, 0.5 * (1 - p) ** 0.5, AMBAR)


def cta(fr, t, ini, fin):
    """A mitad del video: invita a suscribirse, dar like y comentar. Tarjeta de cristal con el logo y tres botones animados."""
    din, dout = 1.1, 0.9
    p = ss((t - ini) / din) * (1 - ss((t - (fin - dout)) / dout))
    if p <= 0.01:
        return
    w, h = 640, 236
    x0, y0 = W - 96 - w, 912 - h
    caja(fr, x0, y0, w, h, AMBAR, 1.0, p, c=20, oscuro=0.62, suave=90)
    tx = ss((p - 0.35) / 0.65)
    if tx <= 0:
        return
    u = t - ini
    # logo
    rgb, mk = _marca(64)
    aa.elipse(fr, (x0 + 28, y0 + 26, x0 + 94, y0 + 92), AMBAR, 1.5, 0.6 * tx)
    fr.paste(rgb, (x0 + 29, y0 + 27), mk.point(lambda v: int(v * tx)))
    pegar(fr, sprite_texto('¿Te está gustando el video?', neg(30), HUESO), x0 + 116 + (1 - tx) * 12, y0 + 24, tx)
    pegar(fr, sprite_texto('Suscríbete, dale like y deja un comentario:', sl(22), mezcla(BG, HUESO, 0.80)), x0 + 116, y0 + 66, tx)
    pegar(fr, sprite_texto('ayudas al canal a seguir creciendo.', sl(22), mezcla(BG, HUESO, 0.80)), x0 + 116, y0 + 92, tx)
    # botones
    botones = (('campana', 'SUSCRIBIRME', True), ('like', 'ME GUSTA', False), ('comentar', 'COMENTAR', False))
    bx = x0 + 28
    by = y0 + 150
    for i, (tipo, texto, primario) in enumerate(botones):
        s = sprite_esp(texto, sb(15), BG if primario else HUESO, 2.4)
        bw = s[1].size[0] + 70
        bh = 50
        ta = ss((u - (1.2 + 0.25 * i)) / 0.5) * tx
        if ta <= 0:
            bx += bw + 14
            continue
        activo = ss((u - (2.6 + 1.2 * i)) / 0.4) * (1 - ss((u - (3.8 + 1.2 * i)) / 0.5))     # pulso en cada botón, uno tras otro
        if primario:
            aa.rrect(fr, (bx, by, bx + bw, by + bh), 25, AMBAR, 1, ta, relleno=True, cache=False)
        else:
            aa.rrect(fr, (bx, by, bx + bw, by + bh), 25, HUESO, 1.5, 0.55 * ta, cache=False)
            if activo > 0:
                aa.rrect(fr, (bx, by, bx + bw, by + bh), 25, AMBAR, 2, activo * ta, cache=False)
        if activo > 0:      # onda que se expande desde el botón activo
            e = 14 * activo
            aa.rrect(fr, (bx - e, by - e * 0.6, bx + bw + e, by + bh + e * 0.6), 25 + e, AMBAR, 1.5, 0.45 * (1 - activo) * ta, cache=False)
        icolor = BG if primario else (AMBAR if activo > 0.3 else HUESO)
        icono_cta(fr, tipo, bx + 28, by + bh / 2, 0.9, icolor, ta)
        pegar(fr, s, bx + 50, by + 13, ta)
        bx += bw + 14
