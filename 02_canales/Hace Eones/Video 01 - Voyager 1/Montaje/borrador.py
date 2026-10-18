"""
Borrador de los primeros minutos del video 1: la versión inicial del montaje, con las escenas A1 (distancia),
A2 (trayectoria) y la lista de «cinco cosas» que video01.py reutiliza. Todo lo común (fuentes, utilidades,
imágenes, fondo) vive en herramientas/montaje/montar.py.

  python borrador.py --frame 25 f.png       un fotograma del borrador
  python borrador.py                        render del borrador (salida/video-01-borrador-0-2min.mp4 y .srt)
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'herramientas', 'montaje')))

from montar import (AMBAR, BG, FONDO, FPS, H, HUESO, NEGRO, NOMBRE, TIERRA, VIDEO, W, aparecer, blk, brillo, clamp, envolver, escena_imagen, lerp, mezcla, neg, pegar, punto, reg, sprite_texto, ss, trocear_texto)  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))   # carpeta Montaje de este video
AUDIO = os.path.join(VIDEO, 'Voz', '01-Video-1-Voyager-1-guion.wav')
DURACION = 119.1  # el borrador termina justo antes de «Al acercarse a Júpiter…»


# ------------------------------------------------------------- animaciones


def a1_distancia(t):
    """A1 · Distancia (0:00–0:43): la nave se aleja, la cifra sube, un pulso de luz tarda ~23 h."""
    fr = FONDO.copy()
    dr = ImageDraw.Draw(fr)
    ex, ey, px, py = 260, 520, 1660, 520
    prog = ss((t - 0.6) / 20.0)
    salida = 1 - ss((t - 29.0) / 5.0)  # tras 1 día luz, el esquema se desvanece
    x = lerp(ex, px, prog)
    # línea Tierra → nave
    if prog > 0 and salida > 0:
        dr.line((ex, ey, x, py), fill=mezcla(BG, HUESO, 0.35 * salida), width=3)
        for i in range(0, 15):
            tx = lerp(ex, px, i / 14)
            if tx <= x:
                dr.line((tx, ey - 9, tx, ey + 9), fill=mezcla(BG, HUESO, 0.22 * salida), width=2)
    # Tierra
    punto(fr, ex, ey, 17, TIERRA, salida, 2.6)
    pegar(fr, sprite_texto('Tierra', neg(30), HUESO), ex, ey + 44, 0.85 * salida * ss((t - 0.4) / 1.0), 'm')
    # nave
    pulso = 1 + 0.12 * math.sin(t * 3.2)
    if t < 29.0:
        punto(fr, x, py, 9 * pulso, AMBAR, 1.0, 4.2)
    else:
        u = ss((t - 29.0) / 8.0)
        cx, cy = lerp(px, 960, u), lerp(py, 540, u)
        punto(fr, cx, cy, 9 * pulso, AMBAR, 1.0, 4.2)
    if t >= 29.0:
        pegar(fr, sprite_texto('Voyager 1', neg(34), HUESO), lerp(px, 960, ss((t - 29.0) / 8.0)), lerp(py, 540, ss((t - 29.0) / 8.0)) + 54, 0.9 * ss((t - 30.0) / 1.2), 'm')
    # cifra de distancia
    n = 25900 * prog
    cifra = '≈ {:,} millones de km'.format(int(round(n / 100.0) * 100) if prog < 1 else 25900).replace(',', ' ')
    pegar(fr, sprite_texto(cifra, blk(92), AMBAR), 960, 210, ss((t - 0.5) / 0.8) * salida, 'm')
    pegar(fr, sprite_texto('= 1 día luz', blk(70), HUESO), 960, 318, ss((t - 22.6) / 0.8) * salida, 'm')
    # pulso de luz de la Tierra a la nave (~23 h)
    if 16.7 <= t <= 19.9:
        q = ss((t - 16.7) / 3.0)
        lx = lerp(ex, px, q)
        for k in range(8):
            qq = max(0, q - k * 0.012)
            punto(fr, lerp(ex, px, qq), ey, 5, HUESO, 0.5 * (1 - k / 8), 2.2)
        punto(fr, lx, ey, 7, HUESO, 1.0, 3.4)
    if 16.6 <= t < 29.0:
        horas = 23 * ss((t - 16.7) / 3.0)
        pegar(fr, sprite_texto('Una orden de radio: {:.0f} h'.format(horas), neg(42), HUESO), 960, 590, aparecer(t, 16.6, 28.0, 0.5) * salida, 'm')
    # anillo de «1 día luz»
    if t > 20.6 and t < 31:
        r = 24 + 6 * math.sin(t * 4)
        pegar(fr, brillo(int(r * 2.2), AMBAR), px, py, 0.55 * aparecer(t, 20.6, 31, 0.8), 'm', 'm')
    pegar(fr, sprite_texto('Esquema no a escala', reg(24), mezcla(BG, HUESO, 0.7)), W - 96, 54, 0.9, 'r')
    return fr


def bezier(p0, c, p2, n):
    return [((1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * c[0] + s * s * p2[0], (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * c[1] + s * s * p2[1]) for s in [i / n for i in range(n + 1)]]


def _trayectoria():
    cx, cy = 960, 540
    P = lambda r, a: (cx + r * math.cos(math.radians(a)), cy - r * math.sin(math.radians(a)))
    tierra, jupiter, saturno = P(130, 200), P(300, 100), P(440, 20)
    pts = bezier(tierra, (650, 380), jupiter, 90) + bezier(jupiter, (1180, 170), saturno, 90)[1:] + bezier(saturno, (1600, 300), (1760, 120), 70)[1:]
    return tierra, jupiter, saturno, pts


TRAY = _trayectoria()


def a2_trayectoria(t, ini):
    """A2 · Trayectoria (parte inicial): Tierra → Júpiter → Saturno, esquema no a escala."""
    u = t - ini
    fr = FONDO.copy()
    dr = ImageDraw.Draw(fr)
    cx, cy = 960, 540
    tierra, jupiter, saturno, pts = TRAY
    a_orb = ss(u / 1.6)
    for r in (130, 300, 440):
        dr.ellipse((cx - r, cy - r, cx + r, cy + r), outline=mezcla(BG, HUESO, 0.16 * a_orb), width=2)
    punto(fr, cx, cy, 14, (255, 214, 120), a_orb, 3.6)
    pegar(fr, sprite_texto('Sol', reg(26), mezcla(BG, HUESO, 0.7)), cx, cy + 34, a_orb, 'm')
    a_pl = ss((u - 1.0) / 1.5)
    punto(fr, *tierra, 11, TIERRA, a_pl, 2.6)
    punto(fr, *jupiter, 20, (214, 160, 108), a_pl, 2.2)
    punto(fr, *saturno, 17, (226, 205, 150), a_pl, 2.2)
    pegar(fr, sprite_texto('Tierra', neg(28), HUESO), tierra[0] - 20, tierra[1] + 26, a_pl, 'r')
    prog = ss((u - 2.4) / 8.8)
    n = int(prog * (len(pts) - 1))
    if n > 1:
        dr.line([(int(a), int(b)) for a, b in pts[:n + 1]], fill=AMBAR, width=4, joint='curve')
        punto(fr, pts[n][0], pts[n][1], 8, AMBAR, 1.0, 3.8)
    if n > len(pts) * 0.40:
        pegar(fr, sprite_texto('Júpiter', neg(30), HUESO), jupiter[0] + 34, jupiter[1] - 14, ss((n / len(pts) - 0.40) / 0.06))
    if n > len(pts) * 0.76:
        pegar(fr, sprite_texto('Saturno', neg(30), HUESO), saturno[0] + 30, saturno[1] + 22, ss((n / len(pts) - 0.76) / 0.06))
    pegar(fr, sprite_texto('Esquema no a escala', reg(24), mezcla(BG, HUESO, 0.7)), W - 96, 54, 0.9, 'r')
    return fr


def escena_lista(t, ini):
    """Lista de «cinco cosas»: una a una, al ritmo de la voz."""
    fr = escena_imagen('M01-PIA26353.jpg', t, ini, ini + 20, 1.22, 1.22, (0.58, 0.45), (0.58, 0.45), oscuro=0.78, desenfoque=18)
    pegar(fr, sprite_texto('Hoy vamos a ver cinco cosas', blk(64), AMBAR), 300, 200, ss((t - 90.3) / 0.6))
    items = [
        (92.28, '1', 'Lo que descubrió en su camino'),
        (94.18, '2', 'Una foto que cambió cómo nos vemos'),
        (97.05, '3', 'La frontera de la burbuja del Sol'),
        (100.46, '4', 'Cómo se habla con una nave tan lejana'),
        (102.9, '5', 'Qué le queda de energía'),
    ]
    for i, (t0, num, txt) in enumerate(items):
        a = ss((t - t0) / 0.5)
        y = 330 + i * 106 + (1 - a) * 14
        punto(fr, 340, y + 34, 28, AMBAR, a, 1.0)
        pegar(fr, sprite_texto(num, blk(38), BG), 340, y + 34, a, 'm', 'm')
        pegar(fr, sprite_texto(txt, neg(52), HUESO), 400, y, a)
    return fr

# --------------------------------------------------------------- rótulos
# (inicio, fin, línea 1, línea 2, estilo)
ROTULOS = [
    (5.8, 11.8, 'Memoria a bordo: unos 69 kilobytes', 'Fuente: NASA, vía MuckRock (FOIA, 2016)', 'dato'),
    (23.5, 30.8, '1 día luz ≈ 25 900 millones de km · hito: 18-nov-2026', 'Fuente: NASA Science', 'dato'),
    (49.3, 56.5, 'Lanzamiento: 5-sep-1977', 'Fuente: NASA Science', 'dato'),
    (80.5, 86.6, 'Velocidad: unos 17 km/s respecto del Sol', 'Fuente: NASA Science (dato de ago-2024)', 'dato'),
    (86.6, 92.0, '17 km/s × 86 400 s ≈ 1,47 millones de km por día', 'Cálculo propio, con la velocidad de NASA', 'calculo'),
    (107.0, 114.5, 'Alineación de los planetas exteriores: cada ≈ 175 años', 'Fuente: NASA NTRS · JPL', 'dato'),
]


def dibujar_rotulo(fr, t, r):
    ini, fin, l1, l2, estilo = r
    a = aparecer(t, ini, fin, 0.35)
    if a <= 0:
        return
    c1 = AMBAR if estilo == 'calculo' else HUESO
    s1 = sprite_texto(l1, neg(36), c1)
    s2 = sprite_texto(l2, reg(26), mezcla(HUESO, BG, 0.30))
    w = max(s1[1].size[0], s2[1].size[0]) + 28 * 2 + 10
    h = s1[1].size[1] + s2[1].size[1] + 30
    x, y = 96, 742 + (1 - a) * 14
    caja = Image.new('RGB', (w, h), BG)
    fr.paste(caja, (x, int(y)), Image.new('L', (w, h), int(222 * a)))
    fr.paste(Image.new('RGB', (10, h), AMBAR), (x, int(y)), Image.new('L', (10, h), int(255 * a)))
    pegar(fr, s1, x + 38, y + 10, a)
    pegar(fr, s2, x + 38, y + 14 + s1[1].size[1], a)


# -------------------------------------------------------------- subtítulos
# (texto, inicio, fin) medidos con los silencios del audio real
BLOQUES = [
    ('En 1977 lanzamos una nave cuyos ordenadores tienen, en total, unos 69 kilobytes de memoria.', 0.34, 8.35),
    ('Hoy, casi cincuenta años después, sigue funcionando, y una orden de radio, viajando a la velocidad de la luz, tarda unas 23 horas en llegar hasta ella.', 9.14, 19.51),
    ('El 18 de noviembre de este año se convertirá en el primer objeto construido por humanos a un día luz de la Tierra.', 20.57, 27.39),
    ('Pero lo más curioso no es lo lejos que está.', 28.11, 30.46),
    ('Es cómo seguimos hablando con ella, lo que no sabemos de ella, y una frase que se repite muchísimo sobre esta nave y que no es del todo cierta. Al final del video te digo cuál.', 31.43, 41.63),
    ('Pero empecemos por el principio. Esta nave se llama Voyager 1.', 42.91, 47.24),
    ('Se lanzó el 5 de septiembre de 1977, dieciséis días después de su gemela, Voyager 2. Pero tomó un camino más rápido, y el 15 de diciembre de ese mismo año ya la había adelantado.', 48.51, 62.15),
    ('Nació para visitar Júpiter y Saturno.', 62.81, 65.12),
    ('Casi medio siglo después sigue enviando datos.', 65.51, 68.64),
    ('Desde el 17 de febrero de 1998 es el objeto más lejano que ha construido la humanidad, el día que superó a la sonda Pioneer 10.', 69.45, 79.73),
    ('Y no se detiene: se aleja del Sol a unos 17 kilómetros por segundo.', 80.25, 84.99),
    ('Eso son casi un millón y medio de kilómetros más lejos cada día.', 85.60, 89.36),
    ('Hoy vamos a ver cinco cosas:', 90.23, 91.85),
    ('lo que descubrió en su camino,', 92.28, 93.80),
    ('una fotografía que cambió cómo nos vemos,', 94.18, 96.59),
    ('cómo sabemos que cruzó la frontera de la burbuja del Sol,', 97.05, 100.03),
    ('cómo se habla con una nave tan lejana, y qué le queda de energía.', 100.46, 104.14),
    ('La misión aprovechó una alineación de los planetas exteriores que se repite solo cada unos 175 años: usar la gravedad de cada planeta como una honda para ganar velocidad sin gastar combustible.', 105.64, 118.01),
]


def construir_subtitulos():
    subs = []
    for txt, a, b in BLOQUES:
        partes = trocear_texto(txt)
        total = sum(len(p) for p in partes)
        t0 = a
        for p in partes:
            d = (b - a) * len(p) / total
            subs.append((p, t0, t0 + d))
            t0 += d
    return subs


SUBS = construir_subtitulos()


def dibujar_subtitulo(fr, t):
    for txt, a, b in SUBS:
        if a - 0.05 <= t <= b + 0.15:
            lineas = envolver(txt)
            sp = [sprite_texto(l, reg(42), HUESO) for l in lineas]
            ancho = max(s[1].size[0] for s in sp) + 56
            alto = sum(s[1].size[1] for s in sp) + 20
            y0 = 1080 - 56 - alto
            fr.paste(Image.new('RGB', (ancho, alto), (0, 0, 0)), ((W - ancho) // 2, y0), Image.new('L', (ancho, alto), 120))
            y = y0 + 8
            for s in sp:
                pegar(fr, s, W // 2, y, 1.0, 'm')
                y += s[1].size[1]
            return


def escribir_srt(ruta):
    def f(s):
        ms = int(round(s * 1000))
        return '{:02d}:{:02d}:{:02d},{:03d}'.format(ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)
    with open(ruta, 'w', encoding='utf-8') as fh:
        for i, (txt, a, b) in enumerate(SUBS, 1):
            fh.write('{}\n{} --> {}\n{}\n\n'.format(i, f(a), f(b), '\n'.join(envolver(txt))))

# -------------------------------------------------------------- composición

ESCENAS = [
    # (inicio, fin, función)
    (0.0, 42.91, lambda t: a1_distancia(t)),
    (42.91, 69.45, lambda t: escena_imagen('M01-PIA26353.jpg', t, 42.91, 69.45, 1.0, 1.10, (0.5, 0.5), (0.46, 0.52))),
    (69.45, 90.23, lambda t: escena_imagen('M01-PIA26353.jpg', t, 69.45, 90.23, 1.10, 1.22, (0.46, 0.52), (0.58, 0.45))),
    (90.23, 105.64, lambda t: escena_lista(t, 90.23)),
    (105.64, DURACION, lambda t: a2_trayectoria(t, 105.64)),
]
XF = 0.9
CREDITOS = [(42.91, 90.23, 'NASA/JPL-Caltech · Concepto artístico')]


def fotograma(t):
    capas = []
    for i, (a, b, fn) in enumerate(ESCENAS):
        ini = a - XF / 2 if i else -1e9
        fin = b - XF / 2 if i < len(ESCENAS) - 1 else 1e9
        al = clamp((t - ini) / XF) if i else 1.0
        al *= (1 - clamp((t - fin) / XF)) if i < len(ESCENAS) - 1 else 1.0
        if al > 0:
            capas.append((al, fn))
    fr = capas[0][1](t)
    for al, fn in capas[1:]:
        fr = Image.blend(fr, fn(t), al) if al < 1 else fn(t)
    pegar(fr, sprite_texto(NOMBRE, neg(22), mezcla(BG, HUESO, 0.55)), 96, 50, 0.9)
    for a, b, txt in CREDITOS:
        k = aparecer(t, a + 0.6, b - 0.2, 0.5)
        if k > 0:
            pegar(fr, sprite_texto(txt, reg(24), HUESO), W - 96, 54, 0.9 * k, 'r')
    for r in ROTULOS:
        dibujar_rotulo(fr, t, r)
    dibujar_subtitulo(fr, t)
    # cierre: fundido a negro
    k = clamp((t - (DURACION - 1.0)) / 1.0)
    if k > 0:
        fr = Image.blend(fr, NEGRO, k)
    return fr


def preparar_audio(destino):
    filtro = 'loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st={:.2f}:d=1.0,aresample=48000'.format(DURACION - 1.0)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', AUDIO, '-t', str(DURACION), '-af', filtro, '-ac', '1', destino], check=True)


def main():
    os.makedirs(os.path.join(VIDEO, 'Montaje', 'salida'), exist_ok=True)
    if len(sys.argv) >= 4 and sys.argv[1] == '--frame':
        fotograma(float(sys.argv[2])).save(sys.argv[3])
        print('fotograma guardado', sys.argv[3])
        return
    salida = os.path.join(VIDEO, 'Montaje', 'salida', 'video-01-borrador-0-2min.mp4')
    wav = os.path.join(AQUI, 'salida', '_audio-borrador.wav')
    preparar_audio(wav)
    escribir_srt(os.path.join(AQUI, 'salida', 'video-01-borrador-0-2min.srt'))
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '{}x{}'.format(W, H), '-r', str(FPS), '-i', '-',
           '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
           '-shortest', '-movflags', '+faststart', salida]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DURACION * FPS)
    for i in range(total):
        p.stdin.write(np.asarray(fotograma(i / FPS)).tobytes())
        if i % 150 == 0:
            print('  {:>4.0f} % ({} s)'.format(100.0 * i / total, int(i / FPS)), flush=True)
    p.stdin.close()
    p.wait()
    print('listo:', salida)


if __name__ == '__main__':
    main()
