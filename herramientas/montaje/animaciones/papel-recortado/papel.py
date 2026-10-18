"""
Papel recortado en capas: cada elemento es una pieza de papel con borde cortado (tijera) o rasgado (con el alma blanca
de la fibra a la vista), textura de fibras y manchas, un leve bisel por el grosor del papel y sombra sobre lo que tiene debajo.
Las piezas se apilan en «planos» (como un multiplano de animación); los planos se separan en profundidad y la cámara
los mueve con paralaje.
"""
import numpy as np
from scipy import ndimage

import pintura as P

SOMBRA = (8, 6, 14)


def rampa(e, w):
    return np.clip(e / w * 0.5 + 0.5, 0, 1)


class Plano:
    def __init__(self, L, semilla=1):
        self.L = L
        h, w = L.h, L.w
        k = L.k
        self.P = np.zeros((h, w, 3), np.float32)      # color premultiplicado
        self.A = np.zeros((h, w), np.float32)
        self.fino = P.fbm(w, h, max(2, int(2.0 * k)), 3, semilla)
        self.medio = P.fbm(w, h, max(3, int(13 * k)), 3, semilla + 5)
        self.fibra = P.fbm(w, h, max(2, int(3 * k)), 3, semilla + 9, aspecto=3.0)
        self.mota = P.fbm(w, h, max(4, int(55 * k)), 4, semilla + 13)
        self.n = 0

    def _sub(self, arr, y0, y1, x0, x1, oy, ox):
        h, w = arr.shape
        return arr[np.ix_((np.arange(y0, y1) + oy) % h, (np.arange(x0, x1) + ox) % w)]

    def _over(self, rgb, a, y0, y1, x0, x1):
        a3 = a[..., None]
        self.P[y0:y1, x0:x1] = rgb * a3 + self.P[y0:y1, x0:x1] * (1 - a3)
        self.A[y0:y1, x0:x1] = a + self.A[y0:y1, x0:x1] * (1 - a)

    def pieza(self, m, color, rasgado=0.0, sombra=(3, 4, 4, 0.45), alfa=1.0, luz=None, alma=(240, 232, 216), bisel=0.35,
              textura=1.0, cortar=None, suave=0.0):
        """m: máscara 0..1 (tamaño del lienzo). color: tupla, o función (X, Y) -> H×W×3 en coordenadas de diseño.
        rasgado: 0 = corte limpio … 1 = papel rasgado a mano. sombra: (dx, dy, desenfoque, opacidad) en px de diseño.
        luz: función (X, Y) -> H×W×3 multiplicador. cortar: máscara que recorta la pieza (p. ej. el disco de un planeta)."""
        L = self.L
        k = L.k
        h, w = m.shape
        ys, xs = np.nonzero(m > 0.02)
        if len(ys) == 0:
            return None
        mg = int((10 + rasgado * 14 + ((abs(sombra[0]) + abs(sombra[1]) + 3 * sombra[2]) if sombra else 0) + suave * 3) * k) + 4
        y0, y1 = max(0, ys.min() - mg), min(h, ys.max() + mg + 1)
        x0, x1 = max(0, xs.min() - mg), min(w, xs.max() + mg + 1)
        rnd = np.random.RandomState(self.n * 7 + 11)
        oy, ox = rnd.randint(0, h), rnd.randint(0, w)
        self.n += 1
        sub = m[y0:y1, x0:x1]
        fino = self._sub(self.fino, y0, y1, x0, x1, oy, ox)
        medio = self._sub(self.medio, y0, y1, x0, x1, oy + 17, ox + 29)
        b = ndimage.gaussian_filter(sub, (1.0 + suave) * k)
        e = b - 0.5 + (medio - 0.5) * rasgado * 0.9 + (fino - 0.5) * (0.1 + rasgado * 0.7)
        ww = 0.07 + suave * 0.3
        mm = rampa(e, ww)
        if cortar is not None:
            mm = mm * cortar[y0:y1, x0:x1]
        X, Y = L.xy
        X, Y = X[y0:y1, x0:x1], Y[y0:y1, x0:x1]
        col = color(X, Y) if callable(color) else np.zeros(sub.shape + (3,), np.float32) + np.asarray(color, np.float32)
        tex = 1 + (self._sub(self.fibra, y0, y1, x0, x1, oy, ox) - 0.5) * 0.12 * textura \
            + (self._sub(self.mota, y0, y1, x0, x1, oy, ox) - 0.5) * 0.10 * textura
        col = col * tex[..., None]
        if rasgado > 0:
            e2 = e - 0.05 - rasgado * 0.07 - (fino - 0.5) * 0.25 * rasgado
            nuc = np.clip(mm - rampa(e2, ww), 0, 1)
            if cortar is not None:
                nuc = nuc * cortar[y0:y1, x0:x1]
            col = col * (1 - nuc[..., None]) + np.asarray(alma, np.float32) * nuc[..., None]
        if bisel:
            hi = P.borde_luz(mm, -0.6, -0.8, k, 1.3, 0.6)
            lo = P.borde_luz(mm, 0.6, 0.8, k, 1.3, 0.6)
            col = col * (1 + bisel * 0.4 * hi - bisel * 0.4 * lo)[..., None]
        if luz is not None:
            col = col * luz(X, Y)
        if sombra:
            dx, dy, bl, sa = sombra
            s = ndimage.gaussian_filter(ndimage.shift(mm, (dy * k, dx * k), order=1), bl * k) * sa * alfa
            self._over(np.zeros_like(col) + np.array(SOMBRA, np.float32), s, y0, y1, x0, x1)
        self._over(col, mm * alfa, y0, y1, x0, x1)
        full = np.zeros((h, w), np.float32)
        full[y0:y1, x0:x1] = mm
        return full

    def sumar(self, rgb_add, mascara=None):
        """Luz que atraviesa el papel (estrellas como agujeros de alfiler, vidrios del farol)."""
        a = self.A if mascara is None else mascara
        self.P += rgb_add * a[..., None]

    def rgb(self):
        return self.P / np.maximum(self.A, 1e-4)[..., None]

    def capa(self):
        return P.capa(self.rgb(), self.A)


def luz_farol(pos, radio, fuerza=1.0, amb=0.55, calido=(1.0, 0.74, 0.46), frio=(0.6, 0.66, 0.95), estir=1.1):
    """Multiplicador de luz: ambiente frío de noche + farol cálido que cae con la distancia."""
    def f(X, Y):
        d = np.hypot(X - pos[0], (Y - pos[1]) * estir)
        l = fuerza / (1 + (d / radio) ** 2)
        return np.stack([amb * frio[i] + l * calido[i] * 1.3 for i in range(3)], -1).astype(np.float32)
    return f


def degradado(c0, c1, y0, y1):
    def f(X, Y):
        t = np.clip((Y - y0) / (y1 - y0), 0, 1)[..., None]
        return np.asarray(c0, np.float32) * (1 - t) + np.asarray(c1, np.float32) * t
    return f


def mechon(cx, cy, ang, largo, ancho, curva=0.15):
    """Polígono en forma de hoja (mechón de pelo o barba de papel)."""
    import math
    ca, sa = math.cos(ang), math.sin(ang)
    izq, der = [], []
    for i in range(13):
        t = i / 12 * 2 - 1
        bx = (1 - t * t) * curva * largo
        x = cx + ca * t * largo / 2 - sa * bx
        y = cy + sa * t * largo / 2 + ca * bx
        hw = ancho / 2 * (1 - abs(t) ** 1.6) ** 0.8
        izq.append((x - sa * hw, y + ca * hw))
        der.append((x + sa * hw, y - ca * hw))
    return izq + der[::-1]
