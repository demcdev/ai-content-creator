"""
Trazos con suavizado (antialiasing) y transparencia real para Hace Eones.

Antes las líneas se dibujaban con PIL directamente y con un color ya mezclado con el azul de fondo: salían con
escalones y, sobre la nebulosa, MÁS OSCURAS que el cielo. Aquí cada trazo se dibuja en una máscara de mayor
resolución, se reduce (suavizado) y se compone con su color y su opacidad reales; el brillo (glow) es opcional.
Las formas fijas se guardan en caché para no recalcularlas en cada fotograma.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

_cache = {}


def _bbox(pts, margen, W, H):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = int(min(xs) - margen), int(min(ys) - margen)
    x1, y1 = int(max(xs) + margen) + 1, int(max(ys) + margen) + 1
    return max(0, x0), max(0, y0), min(W, x1), min(H, y1)


def _componer(fr, mask, x0, y0, color, a, glow, ancho):
    """mask: 'L' (0..255) del trazo ya suavizado."""
    if a <= 0:
        return
    if glow > 0:
        r = max(2.0, ancho * 2.4)
        g = mask.filter(ImageFilter.GaussianBlur(r))
        ga = np.asarray(g, np.float32) / 255.0
        ma = np.asarray(mask, np.float32) / 255.0
        tot = 1 - (1 - ma) * (1 - np.clip(ga * (2.4 + glow), 0, 1) * 0.45 * glow)
        mask = Image.fromarray((np.clip(tot, 0, 1) * 255).astype('uint8'))
    if a < 1:
        mask = mask.point(lambda v: int(v * a))
    fr.paste(Image.new('RGB', mask.size, color), (0, 0), None) if False else fr.paste(Image.new('RGB', mask.size, color), (x0, y0), mask)


def _dibujar(fr, forma, color, a, ancho, glow, ss, clave=None):
    """forma: función (draw, ss, ox, oy) que dibuja en la máscara ampliada; devuelve la caja (x0,y0,x1,y1) de pantalla."""
    W, H = fr.size
    caja = forma['caja'](W, H)
    x0, y0, x1, y1 = caja
    if x1 <= x0 or y1 <= y0:
        return
    k = (clave, ss, ancho) if clave is not None else None
    if k is not None and k in _cache:
        mask = _cache[k]
    else:
        big = Image.new('L', ((x1 - x0) * ss, (y1 - y0) * ss), 0)
        forma['dib'](ImageDraw.Draw(big), ss, x0, y0)
        mask = big.resize((x1 - x0, y1 - y0), Image.LANCZOS if ss > 1 else Image.BILINEAR)
        if k is not None:
            if len(_cache) > 400:
                _cache.clear()
            _cache[k] = mask
    _componer(fr, mask, x0, y0, color, a, glow, ancho)


def linea(fr, pts, color, ancho=2, a=1.0, glow=0.0, ss=3, cache=False):
    """Polilínea suavizada."""
    if len(pts) < 2 or a <= 0:
        return
    m = ancho * 3 + 4

    def dib(d, s, ox, oy):
        seq = [((p[0] - ox) * s, (p[1] - oy) * s) for p in pts]
        d.line(seq, fill=255, width=max(1, int(round(ancho * s))), joint='curve')

    clave = ('l', tuple((round(p[0], 1), round(p[1], 1)) for p in pts)) if cache else None
    _dibujar(fr, {'caja': lambda W, H: _bbox(pts, m + (ancho * 4 if glow else 0), W, H), 'dib': dib}, color, a, ancho, glow, ss, clave)


def lineas(fr, pares, color, ancho=1, a=1.0, ss=3):
    """Muchos segmentos sueltos en una sola pasada: [((x0,y0),(x1,y1)), ...]."""
    if not pares or a <= 0:
        return
    pts = [p for par in pares for p in par]

    def dib(d, s, ox, oy):
        for p0, p1 in pares:
            d.line(((p0[0] - ox) * s, (p0[1] - oy) * s, (p1[0] - ox) * s, (p1[1] - oy) * s), fill=255, width=max(1, int(round(ancho * s))))

    _dibujar(fr, {'caja': lambda W, H: _bbox(pts, ancho * 2 + 3, W, H), 'dib': dib}, color, a, ancho, 0, ss)


def elipse(fr, caja, color, ancho=2, a=1.0, relleno=False, glow=0.0, ss=3, cache=False):
    """Elipse (contorno o relleno) suavizada. caja = (x0, y0, x1, y1)."""
    if a <= 0:
        return
    x0, y0, x1, y1 = caja
    m = ancho * 2 + 3 + (ancho * 5 if glow else 0)

    def dib(d, s, ox, oy):
        cj = ((x0 - ox) * s, (y0 - oy) * s, (x1 - ox) * s, (y1 - oy) * s)
        if relleno:
            d.ellipse(cj, fill=255)
        else:
            d.ellipse(cj, outline=255, width=max(1, int(round(ancho * s))))

    clave = ('e', round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1), relleno) if cache else None
    _dibujar(fr, {'caja': lambda W, H: _bbox([(x0, y0), (x1, y1)], m, W, H), 'dib': dib}, color, a, ancho, glow, ss, clave)


def rrect(fr, caja, radio, color, ancho=1, a=1.0, relleno=False, ss=3, cache=True):
    """Rectángulo redondeado suavizado."""
    if a <= 0:
        return
    x0, y0, x1, y1 = caja

    def dib(d, s, ox, oy):
        cj = ((x0 - ox) * s, (y0 - oy) * s, (x1 - ox) * s, (y1 - oy) * s)
        if relleno:
            d.rounded_rectangle(cj, radio * s, fill=255)
        else:
            d.rounded_rectangle(cj, radio * s, outline=255, width=max(1, int(round(ancho * s))))

    clave = ('r', round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1), radio, relleno) if cache else None
    _dibujar(fr, {'caja': lambda W, H: _bbox([(x0, y0), (x1, y1)], ancho * 2 + 3, W, H), 'dib': dib}, color, a, ancho, 0, ss, clave)


def rect(fr, caja, color, ancho=1, a=1.0, relleno=False, ss=3):
    x0, y0, x1, y1 = caja

    def dib(d, s, ox, oy):
        cj = ((x0 - ox) * s, (y0 - oy) * s, (x1 - ox) * s, (y1 - oy) * s)
        if relleno:
            d.rectangle(cj, fill=255)
        else:
            d.rectangle(cj, outline=255, width=max(1, int(round(ancho * s))))

    _dibujar(fr, {'caja': lambda W, H: _bbox([(x0, y0), (x1, y1)], ancho * 2 + 3, W, H), 'dib': dib}, color, a, ancho, 0, ss)


def poli(fr, pts, color, a=1.0, ancho=0, ss=3):
    """Polígono relleno (ancho=0) o contorno suavizado."""
    if a <= 0:
        return

    def dib(d, s, ox, oy):
        seq = [((p[0] - ox) * s, (p[1] - oy) * s) for p in pts]
        if ancho:
            d.line(seq + [seq[0]], fill=255, width=max(1, int(round(ancho * s))), joint='curve')
        else:
            d.polygon(seq, fill=255)

    _dibujar(fr, {'caja': lambda W, H: _bbox(pts, ancho * 2 + 3, W, H), 'dib': dib}, color, a, ancho, 0, ss)


def puntos(fr, centros, r, color, a=1.0, ss=4):
    """Muchos puntos pequeños (partículas) con posición subpíxel, en una sola pasada."""
    if not centros or a <= 0:
        return

    def dib(d, s, ox, oy):
        for x, y in centros:
            d.ellipse(((x - r - ox) * s, (y - r - oy) * s, (x + r - ox) * s, (y + r - oy) * s), fill=255)

    _dibujar(fr, {'caja': lambda W, H: _bbox(centros, r + 3, W, H), 'dib': dib}, color, a, 1, 0, ss)
