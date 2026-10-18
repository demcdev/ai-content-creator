"""
Pintura por código para la escena de Galileo: ruido, volumen pseudo-3D (sombreado a partir de la distancia al borde),
pinceladas con forma de cerda, empaste (impasto), estrellas «a toques» y textura de papel/lienzo.
Todo se pinta una vez en lienzos grandes; los fotogramas solo mueven la cámara sobre ellos.
"""
import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

# ---------------------------------------------------------------- ruido


def ruido(w, h, cx, cy, semilla):
    rnd = np.random.RandomState(semilla % (2 ** 31))
    g = rnd.rand(max(2, cy) + 2, max(2, cx) + 2).astype(np.float32)
    return np.asarray(Image.fromarray(g, 'F').resize((w, h), Image.BICUBIC), np.float32)


def fbm(w, h, celda, octavas, semilla, pers=0.5, aspecto=1.0):
    """Ruido fractal normalizado (media 0.5, desviación ≈ 0.17). celda: tamaño en px de la celda base; aspecto>1 estira en x."""
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for i in range(octavas):
        cx = int(w / (celda * aspecto) * 2 ** i) + 1
        cy = int(h / celda * 2 ** i) + 1
        acc += ruido(w, h, cx, cy, semilla + 31 * i) * amp
        tot += amp
        amp *= pers
    acc /= tot
    return (acc - acc.mean()) / (acc.std() + 1e-6) * 0.17 + 0.5


def mezclar(a, b, t):
    t = np.asarray(t, np.float32)
    if t.ndim == 2:
        t = t[..., None]
    return np.asarray(a, np.float32) * (1 - t) + np.asarray(b, np.float32) * t


def suave_poli(pts, n=8, cerrado=True):
    """Curva Catmull-Rom a través de los puntos (formas orgánicas)."""
    P = list(pts)
    m = len(P)
    out = []
    rango = range(m) if cerrado else range(m - 1)
    for i in rango:
        p0 = P[(i - 1) % m] if cerrado else P[max(0, i - 1)]
        p1 = P[i]
        p2 = P[(i + 1) % m]
        p3 = P[(i + 2) % m] if cerrado else P[min(m - 1, i + 2)]
        for j in range(n):
            t = j / n
            t2, t3 = t * t, t * t * t
            x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    if not cerrado:
        out.append(P[-1])
    return out

# --------------------------------------------------------------- lienzo


class Lienzo:
    """Lienzo en coordenadas de diseño (las de la pantalla 1920×1080 a zoom 1) con densidad k píxeles por unidad."""

    def __init__(self, x0, y0, x1, y1, k):
        self.x0, self.y0, self.x1, self.y1, self.k = x0, y0, x1, y1, k
        self.w = int(round((x1 - x0) * k))
        self.h = int(round((y1 - y0) * k))
        self._g = None

    def p(self, x, y):
        return ((x - self.x0) * self.k, (y - self.y0) * self.k)

    def ps(self, pts):
        return [self.p(x, y) for x, y in pts]

    @property
    def xy(self):
        if self._g is None:
            yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
            self._g = (xx / self.k + self.x0, yy / self.k + self.y0)
        return self._g

    def mascara(self, fn, blur=0.6):
        im = Image.new('L', (self.w, self.h), 0)
        fn(ImageDraw.Draw(im), self)
        m = np.asarray(im, np.float32) / 255.0
        return ndimage.gaussian_filter(m, blur * self.k) if blur else m

    def fbm(self, celda, octavas, semilla, **kw):
        return fbm(self.w, self.h, max(2, int(celda * self.k)), octavas, semilla, **kw)

# ------------------------------------------------------- volumen y luz


def relieve(mascara, radio):
    """Altura 0..1 con perfil circular a partir de la distancia al borde: da volumen a una silueta."""
    d = ndimage.distance_transform_edt(mascara > 0.5).astype(np.float32)
    x = np.clip(d / radio, 0, 1)
    return np.sqrt(np.clip(1 - (1 - x) ** 2, 0, 1))


def lambert(alto, luz, escala):
    gy, gx = np.gradient(alto)
    nx, ny = -gx * escala, -gy * escala
    n = np.sqrt(nx * nx + ny * ny + 1)
    L = np.asarray(luz, np.float32)
    L = L / np.linalg.norm(L)
    return np.clip((nx * L[0] + ny * L[1] + L[2]) / n, 0, 1)


def bandas(lam, niveles=4, peso=0.55, blur=1.2):
    """Cuantiza la luz en manchas de color (como capas de pintura) con bordes suaves."""
    q = np.floor(lam * niveles + 0.5) / niveles
    q = ndimage.gaussian_filter(q, blur)
    return lam * (1 - peso) + q * peso


def iluminar(base, lam, col_luz, col_amb, col_sombra, sombra=0.35):
    base = np.asarray(base, np.float32)
    lam3 = lam[..., None]
    return base * (np.asarray(col_amb, np.float32) / 255 + np.asarray(col_luz, np.float32) / 255 * lam3) \
        + np.asarray(col_sombra, np.float32) * (1 - lam3) * sombra


def borde_luz(mascara, dx, dy, k, ancho=4.0, blur=1.5):
    """Luz de contorno (rim): píxeles de la silueta cuyo vecino hacia la fuente cae fuera."""
    s = ndimage.shift(mascara, (-dy * ancho * k, -dx * ancho * k), order=1, mode='constant')
    r = np.clip(mascara - s, 0, 1)
    return ndimage.gaussian_filter(r, blur * k)

# --------------------------------------------------------------- pincel


_T = [(t, 0.28 + 0.72 * math.sqrt(max(0.0, 1 - t * t))) for t in np.linspace(-1, 1, 9)]


def _trazo(x, y, ca, sa, L, w, b):
    izq, der = [], []
    for t, f in _T:
        bx = (1 - t * t) * b * L
        cx = x + ca * t * L * 0.5 - sa * bx
        cy = y + sa * t * L * 0.5 + ca * bx
        hw = w * 0.5 * f
        izq.append((cx - sa * hw, cy + ca * hw))
        der.append((cx + sa * hw, cy - ca * hw))
    return izq + der[::-1]


def pinceladas(lienzo, fuente, mascara, n, largo, ancho, angulo, semilla, jitter=6.0, lum=6.0, alfa=170,
               var=0.45, curva=0.16, cerdas=0, umbral=0.5, ang_ruido=0.18):
    """Pinta n pinceladas sobre `lienzo` (PIL RGB) tomando el color de `fuente` (H×W×3 float) donde mascara > umbral.
    angulo: escalar o campo H×W (radianes). cerdas>0 añade estrías finas dentro de cada trazo (marca del pincel)."""
    d = ImageDraw.Draw(lienzo, 'RGBA')
    rnd = np.random.RandomState(semilla)
    H, W = mascara.shape
    xs = rnd.rand(n) * (W - 1)
    ys = rnd.rand(n) * (H - 1)
    jl = rnd.randn(n) * lum
    jc = rnd.randn(n, 3) * jitter * 0.5
    va = rnd.randn(n) * ang_ruido
    vl = 1 + var * (rnd.rand(n) * 2 - 1)
    vw = 1 + var * 0.6 * (rnd.rand(n) * 2 - 1)
    vb = (rnd.rand(n) * 2 - 1) * curva
    campo = not np.isscalar(angulo)
    for i in range(n):
        xi, yi = int(xs[i]), int(ys[i])
        if mascara[yi, xi] < umbral:
            continue
        a = (angulo[yi, xi] if campo else angulo) + va[i]
        ca, sa = math.cos(a), math.sin(a)
        L, w = largo * vl[i], ancho * vw[i]
        c = fuente[yi, xi] + jc[i] + jl[i]
        col = (int(min(255, max(0, c[0]))), int(min(255, max(0, c[1]))), int(min(255, max(0, c[2]))))
        d.polygon(_trazo(xs[i], ys[i], ca, sa, L, w, vb[i]), fill=col + (alfa,))
        if cerdas:
            for j in range(cerdas):
                off = (j / max(1, cerdas - 1) - 0.5) * w * 0.6 if cerdas > 1 else 0
                f = 0.84 if j % 2 else 1.14
                cc = tuple(int(min(255, max(0, v * f))) for v in col)
                x0, y0 = xs[i] - sa * off - ca * L * 0.4, ys[i] + ca * off - sa * L * 0.4
                x1, y1 = xs[i] - sa * off + ca * L * 0.4, ys[i] + ca * off + sa * L * 0.4
                d.line((x0, y0, x1, y1), fill=cc + (int(alfa * 0.45),), width=max(1, int(w * 0.12)))
    return lienzo


def pintar(fuente, mascara, pasadas, semilla, base_blur=1.5, empaste_f=14.0, luz=(-0.6, -0.8)):
    """Pinta una zona: fondo suavizado + varias pasadas de pinceladas + empaste. Devuelve RGB float.
    pasadas: lista de dicts con n, largo, ancho, angulo y opciones de `pinceladas`."""
    base = ndimage.gaussian_filter(fuente, (base_blur, base_blur, 0))
    lienzo = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    for i, p in enumerate(pasadas):
        p = dict(p)
        pinceladas(lienzo, fuente, mascara, semilla=semilla + 101 * i, **p)
    arr = np.asarray(lienzo, np.float32)
    if empaste_f:
        arr = empaste(arr, empaste_f, luz)
    return arr


def empaste(rgb, fuerza=14.0, luz=(-0.6, -0.8), sigma=0.9):
    """Relieve de pintura: las crestas de los trazos que miran a la luz se aclaran y las otras se oscurecen."""
    lum = rgb.mean(2)
    g = ndimage.gaussian_filter(lum, sigma)
    gy, gx = np.gradient(g)
    e = -(gx * luz[0] + gy * luz[1])
    e = np.tanh(e / 6.0) * fuerza
    return np.clip(rgb + e[..., None], 0, 255)


def capa(rgb, alfa):
    a = np.clip(alfa, 0, 1)[..., None] * 255
    return Image.fromarray(np.concatenate([np.clip(rgb, 0, 255), a], 2).astype(np.uint8), 'RGBA')

# ------------------------------------------------------------- estrellas


_TEMP = np.array([[176, 196, 255], [214, 224, 255], [255, 246, 228], [255, 226, 176], [255, 196, 132]], np.float32)
_PESO = np.array([0.22, 0.30, 0.24, 0.15, 0.09])


def _gauss(R, fx, fy, s):
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
    return np.exp(-((xx - fx) ** 2 + (yy - fy) ** 2) / (2 * s * s))


def estrellas(w, h, n, semilla, k=1.0, densidad=None, bmin=30, bmax=255, sesgo=3.0, halo=True, excluir=None):
    """Capa aditiva de estrellas pintadas a toques: núcleo irregular (dos manchas) y halo suave en las brillantes."""
    rnd = np.random.RandomState(semilla)
    out = np.zeros((h, w, 3), np.float32)
    puestas, intentos = 0, 0
    while puestas < n and intentos < n * 20:
        intentos += 1
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        if densidad is not None and rnd.rand() > 0.3 + 0.7 * densidad[y, x]:
            continue
        if excluir is not None and excluir[y, x] > 0.2:
            continue
        puestas += 1
        b = bmin + (bmax - bmin) * rnd.rand() ** (sesgo * 1.5)
        c = _TEMP[rnd.choice(5, p=_PESO)] / 255.0 * b
        s = (0.55 + 1.0 * (b / 255) ** 2) * k
        R = int(s * 3 + 2)
        if x - R < 0 or y - R < 0 or x + R + 1 > w or y + R + 1 > h:
            continue
        fx, fy = rnd.rand() - 0.5, rnd.rand() - 0.5
        ox, oy = rnd.randn() * 0.5 * s, rnd.randn() * 0.5 * s
        nucleo = _gauss(R, fx, fy, s) + 0.55 * _gauss(R, fx + ox, fy + oy, s * 0.8)
        out[y - R:y + R + 1, x - R:x + R + 1] += np.clip(nucleo, 0, 1.2)[..., None] * c
        if halo and b > 165:
            sh = s * (5 + 4 * rnd.rand())
            R2 = int(sh * 3)
            if x - R2 >= 0 and y - R2 >= 0 and x + R2 + 1 <= w and y + R2 + 1 <= h:
                out[y - R2:y + R2 + 1, x - R2:x + R2 + 1] += _gauss(R2, 0, 0, sh)[..., None] * c * 0.13
    return out


def resplandor(w, h, cx, cy, sigma, color, fuerza=1.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma * sigma)) * fuerza
    return g[..., None] * (np.asarray(color, np.float32) / 255.0)

# ----------------------------------------------------- papel y grano


def textura_papel(w, h, semilla=7):
    """Multiplicador ≈1 con fibras de papel, manchas suaves y trama de lienzo muy fina."""
    fib = fbm(w, h, 3, 3, semilla, aspecto=3.0)
    man = fbm(w, h, 160, 4, semilla + 9)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    trama = np.sin(xx * 2 * math.pi / 3.3) * np.sin(yy * 2 * math.pi / 3.3)
    return 1 + (fib - 0.5) * 0.08 + (man - 0.5) * 0.09 + trama * 0.012
