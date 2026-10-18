#!/usr/bin/env python3
"""
Genera las miniaturas de un video a partir de DATOS (07-miniaturas/miniaturas.json), sin ejecutar código del video:
quien escribe el JSON (una persona o Claude Code) elige concepto, paleta, composición, motivo y texto; el dibujo lo hace
este programa. Las reglas de diseño y sus fuentes están en 00-contexto/produccion/guia-de-miniaturas.md (léela antes).

  python herramientas/video/generar-miniaturas.py "<canal>/<n>"             # dibuja todas las variantes
  python herramientas/video/generar-miniaturas.py "<canal>/<n>" --validar   # solo revisa el JSON
  python herramientas/video/generar-miniaturas.py "<canal>/<n>" --alto 720  # borrador rápido (por defecto 2160 = 3840×2160)

Cada variante (1 a 6):
  id, concepto (obligatorio y distinto en cada una), texto (1-2 líneas, máx. 4 palabras), subtexto (opcional),
  paleta {fondo, texto, acento} en #RRGGBB (el texto debe tener contraste >= 4,5:1; WCAG 1.4.3),
  composicion: texto-izquierda | texto-derecha | centrado | texto-abajo,
  motivo {tipo: anillo|esfera|orbitas|ondas|ninguno, posicion: [x, y] (0-1), tamano: 0.1-0.6, detalle: liso|bandas},
  estilo_texto: brillo | plano | caja,   fondo: estrellas | degradado | solido | radial,   fuente: inter | montserrat | space,
  imagen (opcional): archivo en 05-licencias/originales/ que figure en 05-licencias/registro-de-licencias.md.

Con 2 o más variantes se exige que difieran de verdad (composición, motivo, fondo, estilo de texto o paleta): YouTube avisa
que variantes parecidas alargan el test A/B o no dan ganador.
Salida en 07-miniaturas/ (el id va en minúsculas en los nombres): miniatura-<id>.png (3840×2160), -movil.jpg (menos de 2 MB, para subir desde el móvil), -320x180.png
(tamaño «medium» que sirve YouTube) y -160x90.png (prueba de esfuerzo). Imprime contraste, brillo y colorido de cada una.
Usa solo Pillow y numpy. No usa IA, red ni claves.
"""
import argparse
import io
import json
import math
import os
import random
import re
import sys

sys.dont_write_bytecode = True
HERR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERR, 'nucleo'))
from _comun import consola, identidad_efectiva, leer, resolver_video, ruta  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

CARPETA = '07-miniaturas'
F_SPEC = CARPETA + '/miniaturas.json'
EXT = ('.png', '.jpg', '.jpeg', '.webp')
FUENTES = {'inter': 'inter/Inter-VF.ttf', 'montserrat': 'montserrat/Montserrat-VF.ttf', 'space': 'spacegrotesk/SpaceGrotesk-VF.ttf'}
COMPOSICIONES = ('texto-izquierda', 'texto-derecha', 'centrado', 'texto-abajo')
MOTIVOS = ('anillo', 'esfera', 'orbitas', 'ondas', 'ninguno')
ESTILOS = ('brillo', 'plano', 'caja')
FONDOS = ('estrellas', 'degradado', 'solido', 'radial')
CONTRASTE_MIN = 4.5          # WCAG 1.4.3 (AA); se adopta también para texto grande porque la miniatura se ve reducida
ASPECTO = 16 / 9
POSICION_MOTIVO = {'texto-izquierda': (0.70, 0.45), 'texto-derecha': (0.30, 0.45), 'centrado': (0.5, 0.5), 'texto-abajo': (0.70, 0.30)}
HEX = re.compile(r'#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})')


class ErrorSpec(Exception):
    pass


# ------------------------------------------------------------------ color
def a_rgb(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminancia(rgb):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    la, lb = luminancia(a), luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def mezcla(a, b, t):
    return tuple(int(round(x * (1 - t) + y * t)) for x, y in zip(a, b))


# ------------------------------------------------------------------ validación
def validar(video, spec):
    """Devuelve (variantes, avisos) o lanza ErrorSpec con TODOS los problemas."""
    errores, avisos = [], []
    variantes = spec.get('variantes') if isinstance(spec, dict) else None
    if not isinstance(variantes, list) or not 1 <= len(variantes) <= 6:
        raise ErrorSpec('«variantes» debe ser una lista de 1 a 6 elementos.')
    registro = (leer(ruta(video, '05-licencias/registro-de-licencias.md')) or '').lower()
    ids = set()
    for i, v in enumerate(variantes, 1):
        if not isinstance(v, dict):
            errores.append('variante %d: debe ser un objeto.' % i)
            continue
        vid = str(v.get('id', ''))
        p = 'variante %s' % (vid or i)
        if not re.fullmatch(r'[A-Za-z0-9-]{1,20}', vid):
            errores.append('%s: «id» debe ser letras, números o guion (hasta 20).' % p)
        elif vid in ids:
            errores.append('%s: «id» repetido.' % p)
        ids.add(vid)
        if not isinstance(v.get('concepto'), str) or len(v['concepto'].strip()) < 3:
            errores.append('%s: falta «concepto» (una frase: qué idea explora esta variante).' % p)
        texto = v.get('texto')
        if not isinstance(texto, list) or not 1 <= len(texto) <= 2 or not all(isinstance(t, str) and t.strip() for t in texto):
            errores.append('%s: «texto» debe ser una lista de 1 o 2 líneas con texto.' % p)
        else:
            palabras = sum(len(t.split()) for t in texto)
            if palabras > 4:
                errores.append('%s: el texto tiene %d palabras; el máximo es 4 (idealmente 3 o menos).' % (p, palabras))
            elif palabras == 4:
                avisos.append('%s: 4 palabras es el tope; mejor 3 o menos.' % p)
            if any(len(t) > 18 for t in texto):
                errores.append('%s: una línea de más de 18 letras no se lee en el móvil.' % p)
        sub = v.get('subtexto')
        if sub is not None and (not isinstance(sub, str) or len(sub.split()) > 3):
            errores.append('%s: «subtexto» debe ser texto de hasta 3 palabras.' % p)
        pal = v.get('paleta')
        colores = {}
        if not isinstance(pal, dict) or not all(isinstance(pal.get(k), str) and HEX.fullmatch(pal[k]) for k in ('fondo', 'texto', 'acento')):
            errores.append('%s: «paleta» debe tener «fondo», «texto» y «acento» en formato #RRGGBB.' % p)
        else:
            colores = {k: a_rgb(pal[k]) for k in ('fondo', 'texto', 'acento')}
        estilo = v.get('estilo_texto', 'brillo')
        if estilo not in ESTILOS:
            errores.append('%s: «estilo_texto» debe ser uno de: %s.' % (p, ', '.join(ESTILOS)))
        if colores and estilo in ESTILOS:
            par = (colores['acento'], colores['fondo']) if estilo == 'caja' else (colores['texto'], colores['fondo'])
            c = contraste(*par)
            if c < CONTRASTE_MIN:
                errores.append('%s: el contraste del texto es %.1f:1 y el mínimo es %.1f:1 (WCAG 1.4.3). Aclara el texto u oscurece el fondo (o al revés).' % (p, c, CONTRASTE_MIN))
            tx = colores['texto']
            if estilo != 'caja' and tx[0] > 150 and tx[1] < 90 and tx[2] < 90 and luminancia(colores['fondo']) < 0.05:
                avisos.append('%s: rojo sobre fondo muy oscuro se lee mal con daltonismo (WCAG lo desaconseja); prueba un rojo más claro o rosado.' % p)
            if estilo != 'caja' and contraste(colores['acento'], colores['fondo']) < 3:
                avisos.append('%s: el acento casi no se distingue del fondo (menos de 3:1): el motivo se perderá.' % p)
        if v.get('composicion', 'texto-izquierda') not in COMPOSICIONES:
            errores.append('%s: «composicion» debe ser una de: %s.' % (p, ', '.join(COMPOSICIONES)))
        if v.get('fondo', 'degradado') not in FONDOS:
            errores.append('%s: «fondo» debe ser uno de: %s.' % (p, ', '.join(FONDOS)))
        if v.get('fuente') is not None and v['fuente'] not in FUENTES:
            errores.append('%s: «fuente» debe ser una de: %s.' % (p, ', '.join(FUENTES)))
        mot = v.get('motivo', {'tipo': 'ninguno'})
        if not isinstance(mot, dict) or mot.get('tipo', 'ninguno') not in MOTIVOS:
            errores.append('%s: «motivo.tipo» debe ser uno de: %s.' % (p, ', '.join(MOTIVOS)))
        else:
            pos = mot.get('posicion')
            if pos is not None and not (isinstance(pos, list) and len(pos) == 2 and all(isinstance(n, (int, float)) and 0 <= n <= 1 for n in pos)):
                errores.append('%s: «motivo.posicion» debe ser [x, y] con valores entre 0 y 1.' % p)
            tam = mot.get('tamano')
            if tam is not None and not (isinstance(tam, (int, float)) and 0.1 <= tam <= 0.6):
                errores.append('%s: «motivo.tamano» debe estar entre 0,1 y 0,6 (fracción de la altura).' % p)
            if mot.get('detalle') not in (None, 'liso', 'bandas'):
                errores.append('%s: «motivo.detalle» debe ser «liso» o «bandas».' % p)
        img = v.get('imagen')
        if img:
            absoluta = os.path.realpath(ruta(video, str(img)))
            permitido = os.path.realpath(ruta(video, '05-licencias/originales'))
            if not absoluta.startswith(permitido + os.sep):
                errores.append('%s: la imagen debe estar en 05-licencias/originales/.' % p)
            elif not absoluta.lower().endswith(EXT):
                errores.append('%s: la imagen debe ser png, jpg o webp.' % p)
            elif not os.path.isfile(absoluta):
                errores.append('%s: no existe la imagen %s.' % (p, img))
            elif os.path.basename(absoluta).lower() not in registro:
                errores.append('%s: «%s» no figura en 05-licencias/registro-de-licencias.md (regla 3: sin registro no se usa).' % (p, os.path.basename(absoluta)))
            if isinstance(mot, dict) and mot.get('tipo', 'ninguno') != 'ninguno':
                avisos.append('%s: imagen y motivo a la vez suben la complejidad; la guía recomienda un solo punto focal (D1).' % p)
    if not errores and len(variantes) >= 2:
        for a in range(len(variantes)):
            for b in range(a + 1, len(variantes)):
                if _diferencias(variantes[a], variantes[b]) < 2:
                    errores.append('Las variantes %s y %s se parecen demasiado (deben diferir en al menos 2 de: composición, motivo, fondo, estilo de texto, paleta). '
                                   'YouTube avisa que variantes parecidas alargan el test A/B o no dan ganador.' % (variantes[a]['id'], variantes[b]['id']))
        conceptos = [v['concepto'].strip().lower() for v in variantes]
        if len(set(conceptos)) < len(conceptos):
            errores.append('Cada variante debe explorar un concepto distinto: hay conceptos repetidos.')
        if len({v['paleta']['fondo'].lower() + v['paleta']['acento'].lower() for v in variantes}) == 1:
            avisos.append('Las variantes comparten fondo y acento: la guía (D6) pide derivar la paleta del tema y variar el brillo/colorido entre variantes.')
    if errores:
        raise ErrorSpec('\n'.join(errores))
    return variantes, avisos


def _diferencias(a, b):
    """Cuántos rasgos de diseño distinguen a dos variantes (composición, motivo, fondo, estilo de texto, paleta)."""
    n = 0
    n += a.get('composicion', 'texto-izquierda') != b.get('composicion', 'texto-izquierda')
    n += (a.get('motivo') or {}).get('tipo', 'ninguno') != (b.get('motivo') or {}).get('tipo', 'ninguno')
    n += a.get('fondo', 'degradado') != b.get('fondo', 'degradado')
    n += a.get('estilo_texto', 'brillo') != b.get('estilo_texto', 'brillo')
    fa, fb = a_rgb(a['paleta']['fondo']), a_rgb(b['paleta']['fondo'])
    ca, cb = a_rgb(a['paleta']['acento']), a_rgb(b['paleta']['acento'])
    n += (math.dist(fa, fb) > 90) or (math.dist(ca, cb) > 120)
    return n


# ------------------------------------------------------------------ dibujo
def fuente(familia, tam, peso=900):
    f = ImageFont.truetype(os.path.join(HERR, 'montaje', 'fuentes', FUENTES.get(familia, FUENTES['inter'])), tam)
    vals = []
    for ax in f.get_variation_axes():
        nombre = ax['name'] if isinstance(ax['name'], str) else ax['name'].decode()
        vals.append(max(ax['minimum'], min(ax['maximum'], peso)) if 'eight' in nombre else ax['default'])
    f.set_variation_by_axes(vals)
    return f


def lienzo_fondo(W, H, pal, tipo, semilla, foco):
    fondo = np.array(pal['fondo'], np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    if tipo == 'solido':
        arr = np.broadcast_to(fondo, (H, W, 3)).copy()
    elif tipo == 'degradado':
        t = (yy / H)[..., None]
        arr = fondo * (1.30 - 0.40 * t)
    else:                                                    # radial y estrellas: foco de luz suave hacia el motivo
        d = np.clip(np.hypot((xx - foco[0] * W) / (W * 0.65), (yy - foco[1] * H) / (H * 0.85)), 0, 1)[..., None]
        arr = fondo * (1.0 + 0.85 * (1 - d) ** 1.5)
    im = Image.fromarray(np.clip(arr, 0, 255).astype('uint8'))
    if tipo == 'estrellas':
        azar = random.Random(semilla)
        dib = ImageDraw.Draw(im, 'RGBA')
        for _ in range(170):
            x, y, r = azar.randrange(W), azar.randrange(H), azar.choice((1, 1, 1, 2)) * max(1, H // 720)
            if x > W * 0.80 and y > H * 0.78:
                continue
            dib.ellipse((x - r, y - r, x + r, y + r), fill=tuple(pal['texto']) + (azar.randrange(50, 190),))
    return im


def pegar_color(im, mascara, color, opacidad=1.0):
    m = mascara.point(lambda p: int(p * opacidad)) if opacidad < 1 else mascara
    im.paste(Image.new('RGB', im.size, tuple(color)), (0, 0), m)


def resplandor(im, mascara, color, radios, fuerza):
    for r, k in zip(radios, fuerza):
        pegar_color(im, mascara.filter(ImageFilter.GaussianBlur(r)), color, k)


def motivo_anillo(im, cx, cy, r, pal):
    W, H = im.size
    acento, fondo = pal['acento'], pal['fondo']
    claro = mezcla(acento, (255, 255, 255), 0.55)
    anillo = Image.new('L', (W, H), 0)
    ImageDraw.Draw(anillo).ellipse((cx - r, cy - r, cx + r, cy + r), outline=255, width=max(2, int(r * 0.13)))
    disco = Image.new('L', (W, H), 0)
    ImageDraw.Draw(disco).ellipse((cx - r * 1.75, cy - r * 0.30, cx + r * 1.75, cy + r * 0.30), outline=255, width=max(2, int(r * 0.10)))
    resplandor(im, anillo, acento, (r * 0.35, r * 0.12), (0.55, 0.8))
    resplandor(im, disco, acento, (r * 0.30, r * 0.10), (0.45, 0.7))
    pegar_color(im, anillo, mezcla(acento, claro, 0.5))
    pegar_color(im, disco, claro, 0.9)
    sombra = Image.new('L', (W, H), 0)
    ImageDraw.Draw(sombra).ellipse((cx - r * 0.84, cy - r * 0.84, cx + r * 0.84, cy + r * 0.84), fill=255)
    pegar_color(im, sombra.filter(ImageFilter.GaussianBlur(max(1, r * 0.02))), mezcla(fondo, (0, 0, 0), 0.7))


def motivo_esfera(im, cx, cy, r, pal, detalle):
    W, H = im.size
    acento = np.array(pal['acento'], np.float32)
    x0, y0 = int(max(0, cx - r * 1.4)), int(max(0, cy - r * 1.4))
    x1, y1 = int(min(W, cx + r * 1.4)), int(min(H, cy + r * 1.4))
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx, ny = (xx - cx) / r, (yy - cy) / r
    d2 = nx ** 2 + ny ** 2
    nz = np.sqrt(np.clip(1 - d2, 0, 1))
    luz = np.array([-0.55, -0.6, 0.58], np.float32)
    luz /= np.linalg.norm(luz)
    difusa = np.clip(nx * luz[0] + ny * luz[1] + nz * luz[2], 0, 1)
    brillo = (0.10 + 0.95 * difusa ** 1.1)[..., None]
    base = np.broadcast_to(acento, brillo.shape[:2] + (3,)).copy()
    if detalle == 'bandas':
        banda = (0.5 + 0.5 * np.sin(ny * 9.0 + 0.8 * np.sin(nx * 3.0)))[..., None]
        base = base * (0.72 + 0.38 * banda)
    col = np.clip(base * brillo, 0, 255)
    region = np.asarray(im.crop((x0, y0, x1, y1)), np.float32)
    borde = np.clip((1.0 - np.sqrt(np.clip(d2, 0, 4))) * r / 2.0, 0, 1)[..., None]       # borde suavizado
    im.paste(Image.fromarray(np.clip(region * (1 - borde) + col * borde, 0, 255).astype('uint8')), (x0, y0))
    halo = Image.new('L', (W, H), 0)
    ImageDraw.Draw(halo).ellipse((cx - r, cy - r, cx + r, cy + r), outline=255, width=max(2, int(r * 0.04)))
    resplandor(im, halo, pal['acento'], (r * 0.10, r * 0.03), (0.35, 0.5))


def motivo_orbitas(im, cx, cy, r, pal):
    W, H = im.size
    acento = pal['acento']
    lineas = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(lineas)
    puntos = []
    for k, esc in enumerate((0.5, 0.85, 1.2, 1.6)):
        rx, ry = r * esc * 1.5, r * esc * 0.55
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=255, width=max(2, int(r * 0.022)))
        ang = k * 1.7 + 0.6
        puntos.append((cx + rx * math.cos(ang), cy + ry * math.sin(ang), r * (0.07 - 0.01 * k)))
    resplandor(im, lineas, acento, (r * 0.05,), (0.6,))
    pegar_color(im, lineas, acento, 0.75)
    pm = Image.new('L', (W, H), 0)
    dp = ImageDraw.Draw(pm)
    for x, y, pr in puntos:
        dp.ellipse((x - pr, y - pr, x + pr, y + pr), fill=255)
    dp.ellipse((cx - r * 0.16, cy - r * 0.16, cx + r * 0.16, cy + r * 0.16), fill=255)
    resplandor(im, pm, mezcla(acento, (255, 255, 255), 0.4), (r * 0.08,), (0.8,))
    pegar_color(im, pm, mezcla(acento, (255, 255, 255), 0.6))


def motivo_ondas(im, cx, cy, r, pal):
    W, H = im.size
    acento = pal['acento']
    for k in range(1, 6):
        rr = r * k * 0.34
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=255, width=max(2, int(r * 0.03)))
        resplandor(im, m, acento, (r * 0.04,), (0.5 * (1.05 - k * 0.15),))
        pegar_color(im, m, acento, max(0.18, 0.95 - k * 0.17))
    centro = Image.new('L', (W, H), 0)
    ImageDraw.Draw(centro).ellipse((cx - r * 0.12, cy - r * 0.12, cx + r * 0.12, cy + r * 0.12), fill=255)
    resplandor(im, centro, acento, (r * 0.15,), (0.9,))
    pegar_color(im, centro, mezcla(acento, (255, 255, 255), 0.7))


def poner_motivo(im, v, pal, composicion):
    mot = v.get('motivo') or {'tipo': 'ninguno'}
    tipo = mot.get('tipo', 'ninguno')
    if tipo == 'ninguno':
        return
    W, H = im.size
    fx, fy = mot.get('posicion') or POSICION_MOTIVO[composicion]
    r = (mot.get('tamano') or 0.30) * H
    cx, cy = fx * W, fy * H
    if tipo == 'anillo':
        motivo_anillo(im, cx, cy, r, pal)
    elif tipo == 'esfera':
        motivo_esfera(im, cx, cy, r, pal, mot.get('detalle', 'liso'))
    elif tipo == 'orbitas':
        motivo_orbitas(im, cx, cy, r, pal)
    elif tipo == 'ondas':
        motivo_ondas(im, cx, cy, r, pal)


def extension_motivo(v, composicion, W, H):
    """Rectángulo (x0, y0, x1, y1) que ocupa el motivo, o None."""
    mot = v.get('motivo') or {}
    tipo = mot.get('tipo', 'ninguno')
    if tipo == 'ninguno':
        return None
    fx, fy = mot.get('posicion') or POSICION_MOTIVO[composicion]
    r = (mot.get('tamano') or 0.30) * H
    ancho, alto = {'anillo': (1.75, 1.0), 'esfera': (1.0, 1.0), 'orbitas': (2.4, 0.88), 'ondas': (1.7, 1.7)}[tipo]
    return fx * W - ancho * r, fy * H - alto * r, fx * W + ancho * r, fy * H + alto * r


def choque_motivo_texto(v, composicion, cajas, W, H):
    """Fracción del texto que queda tapada por el motivo (0 a 1). En «centrado» el motivo es fondo y no se mide."""
    ext = extension_motivo(v, composicion, W, H)
    if not ext or composicion == 'centrado':
        return 0.0
    tapado = total = 0.0
    for x0, y0, x1, y1 in cajas:
        total += (x1 - x0) * (y1 - y0)
        ox, oy = min(x1, ext[2]) - max(x0, ext[0]), min(y1, ext[3]) - max(y0, ext[1])
        if ox > 0 and oy > 0:
            tapado += ox * oy
    return tapado / total if total else 0.0


def poner_imagen(im, ruta_img, pal, composicion):
    """Imagen licenciada: franja lateral con degradado hacia el texto, o a toda la miniatura (centrado / texto-abajo)."""
    W, H = im.size
    foto = Image.open(ruta_img).convert('RGB')
    fondo = np.array(pal['fondo'], np.float32)
    if composicion in ('texto-izquierda', 'texto-derecha'):
        ancho = int(W * 0.62)
        esc = max(ancho / foto.width, H / foto.height)
        foto = foto.resize((max(ancho, int(foto.width * esc)), max(H, int(foto.height * esc))), Image.LANCZOS)
        x0, y0 = (foto.width - ancho) // 2, (foto.height - H) // 2
        foto = foto.crop((x0, y0, x0 + ancho, y0 + H))
        g = np.clip(np.arange(ancho) / (ancho * 0.55), 0, 1) ** 1.2
        if composicion == 'texto-derecha':
            g = g[::-1]
        x_pos = 0 if composicion == 'texto-derecha' else W - ancho
        capa = np.asarray(im.crop((x_pos, 0, x_pos + ancho, H)), np.float32)
        res = np.asarray(foto, np.float32) * g[None, :, None] + capa * (1 - g[None, :, None])
        im.paste(Image.fromarray(res.astype('uint8')), (x_pos, 0))
    else:
        esc = max(W / foto.width, H / foto.height)
        foto = foto.resize((max(W, int(foto.width * esc)), max(H, int(foto.height * esc))), Image.LANCZOS)
        x0, y0 = (foto.width - W) // 2, (foto.height - H) // 2
        foto = foto.crop((x0, y0, x0 + W, y0 + H))
        if composicion == 'centrado':
            peso = np.full((H, W, 1), 0.55, np.float32)
        else:
            peso = (np.clip(np.arange(H) / H, 0, 1) ** 1.3 * 0.9)[:, None, None] * np.ones((1, W, 1), np.float32)
        im.paste(Image.fromarray((np.asarray(foto, np.float32) * (1 - peso) + fondo * peso).astype('uint8')), (0, 0))


def poner_texto(im, v, pal, familia, tam_lienzo=None):
    """Dibuja el texto; con im=None solo mide y devuelve las cajas del texto (para detectar choques con el motivo)."""
    W, H = tam_lienzo or im.size
    comp = v.get('composicion', 'texto-izquierda')
    estilo = v.get('estilo_texto', 'brillo')
    lineas = [t.strip().upper() for t in v['texto']]
    hay_figura = bool(v.get('imagen')) or (v.get('motivo') or {}).get('tipo', 'ninguno') != 'ninguno'
    ancho_max = int(W * {'texto-izquierda': 0.58 if hay_figura else 0.80, 'texto-derecha': 0.58 if hay_figura else 0.80,
                         'centrado': 0.84, 'texto-abajo': 0.74}[comp])
    ext = extension_motivo(v, comp, W, H)
    if ext and comp in ('texto-izquierda', 'texto-derecha'):           # el texto no invade el motivo si hay sitio
        libre = (ext[0] - 0.02 * W - 0.06 * W) if comp == 'texto-izquierda' else ((W - 0.06 * W) - (ext[2] + 0.02 * W))
        if libre >= W * 0.25:
            ancho_max = min(ancho_max, int(libre))
    sub = v.get('subtexto')
    alto_max = int(H * (0.30 if comp == 'texto-abajo' else (0.58 if sub else 0.66)))
    tam = int(H * 0.46)
    while tam > 20:
        f = fuente(familia, tam)
        medidas = [f.getbbox(t) for t in lineas]
        ancho = max(m[2] - m[0] for m in medidas)
        alto = sum(m[3] - m[1] for m in medidas) + int(tam * 0.16) * (len(lineas) - 1)
        if ancho <= ancho_max and alto <= alto_max:
            break
        tam -= max(2, H // 360)
    if tam < H * 0.12:
        raise ErrorSpec('variante %s: el texto quedaría ilegible en el móvil (letras de menos del 12 %% de la altura): acórtalo o, si hay un motivo, aléjalo del texto (posicion) o hazlo más pequeño (tamano).' % v['id'])
    if tam < H * 0.18 and im is not None:
        print('AVISO variante %s: letras algo pequeñas para el móvil; prueba menos letras o dos líneas.' % v['id'])
    margen = int(W * 0.06)
    sub_f = fuente(familia, max(int(H * 0.05), int(tam * 0.28)), 700) if sub else None
    sub_b = sub_f.getbbox(sub) if sub else None
    sub_alto = (sub_b[3] - sub_b[1] + int(tam * 0.12)) if sub else 0
    total = alto + sub_alto
    y = int(H * 0.90) - total if comp == 'texto-abajo' else int((H - total) / 2) - (int(H * 0.02) if sub else 0)

    def posx(b):
        if comp == 'texto-derecha':
            return W - margen - (b[2] - b[0]) - b[0]
        if comp == 'centrado':
            return int((W - (b[2] - b[0])) / 2) - b[0]
        return margen - b[0]

    paso = int(tam * 0.16)
    cajas, cy = [], y
    for m in medidas:
        cajas.append((posx(m) + m[0], cy, posx(m) + m[2], cy + (m[3] - m[1])))
        cy += (m[3] - m[1]) + paso
    y_sub = cy + int(tam * 0.04)
    if sub:
        cajas.append((posx(sub_b) + sub_b[0], y_sub, posx(sub_b) + sub_b[2], y_sub + (sub_b[3] - sub_b[1])))
    for x0, y0, x1, y1 in cajas:
        if x0 < W * 0.05 or x1 > W * 0.95 or y0 < H * 0.05 or y1 > H * 0.95:
            raise ErrorSpec('variante %s: el texto invade el margen del 5 %% del borde; acórtalo o cambia la composición.' % v['id'])
        if x1 > W * 0.85 and y1 > H * 0.85:
            raise ErrorSpec('variante %s: el texto invade la esquina inferior derecha (la duración del video); cambia la composición.' % v['id'])
    if im is None:
        return cajas
    color_texto = pal['texto']
    if estilo == 'caja':
        bx0 = min(c[0] for c in cajas) - int(tam * 0.22)
        by0 = min(c[1] for c in cajas) - int(tam * 0.18)
        bx1 = max(c[2] for c in cajas) + int(tam * 0.22)
        by1 = max(c[3] for c in cajas) + int(tam * 0.18)
        ImageDraw.Draw(im).rectangle((bx0, by0, bx1, by1), fill=tuple(pal['acento']))
        color_texto = pal['fondo']
    capa = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sombra = Image.new('L', (W, H), 0)
    dc, ds = ImageDraw.Draw(capa), ImageDraw.Draw(sombra)
    cy = y
    for t, m in zip(lineas, medidas):
        x = posx(m)
        if estilo == 'brillo':
            ds.text((x + max(3, H // 120), cy - m[1] + max(4, H // 90)), t, font=f, fill=235)
        dc.text((x, cy - m[1]), t, font=f, fill=tuple(color_texto) + (255,))
        cy += (m[3] - m[1]) + paso
    if estilo == 'brillo':
        pegar_color(im, sombra.filter(ImageFilter.GaussianBlur(H / 50)), mezcla(pal['fondo'], (0, 0, 0), 0.8))
        halo = capa.split()[3].filter(ImageFilter.GaussianBlur(H / 70)).point(lambda p: int(p * 0.30))
        im.paste(Image.new('RGB', (W, H), tuple(pal['acento'])), (0, 0), halo)
    im.paste(capa, (0, 0), capa)
    if sub:
        ImageDraw.Draw(im).text((posx(sub_b), y_sub - sub_b[1]), sub, font=sub_f, fill=tuple(color_texto))


def perfil(im, pal, v):
    """Datos informativos (sin umbrales): contraste del texto, brillo medio y colorido (Hasler-Süsstrunk, la medida de F6)."""
    arr = np.asarray(im.resize((480, 270)), np.float32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    brillo = float(np.mean(0.299 * r + 0.587 * g + 0.114 * b))
    rg, yb = r - g, 0.5 * (r + g) - b
    colorido = float(math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean()))
    par = (pal['acento'], pal['fondo']) if v.get('estilo_texto') == 'caja' else (pal['texto'], pal['fondo'])
    elementos = ['texto']
    if (v.get('motivo') or {}).get('tipo', 'ninguno') != 'ninguno':
        elementos.append('motivo:' + v['motivo']['tipo'])
    if v.get('imagen'):
        elementos.append('imagen')
    return contraste(*par), brillo, colorido, elementos


def dibujar(video, v, ident, alto):
    W, H = int(round(alto * ASPECTO)), alto
    pal = {k: a_rgb(v['paleta'][k]) for k in ('fondo', 'texto', 'acento')}
    comp = v.get('composicion', 'texto-izquierda')
    foco = (v.get('motivo') or {}).get('posicion') or POSICION_MOTIVO[comp]
    familia = v.get('fuente') or ident.get('fuente') or 'inter'
    cajas = poner_texto(None, v, pal, familia, (W, H))
    tapado = choque_motivo_texto(v, comp, cajas, W, H)
    if tapado > 0.15:
        print('AVISO variante %s: el motivo tapa el %d %% del texto; mueve el motivo (posicion), hazlo más pequeño (tamano) o cambia la composición.' % (v['id'], round(tapado * 100)))
    im = lienzo_fondo(W, H, pal, v.get('fondo', 'degradado'), v['id'], foco)
    if v.get('imagen'):
        poner_imagen(im, os.path.realpath(ruta(video, v['imagen'])), pal, comp)
    poner_motivo(im, v, pal, comp)
    poner_texto(im, v, pal, familia)
    return im, pal


def guardar(im, salida, vid):
    """PNG a tamaño completo, JPG para móvil (menos de 2 MB) y vistas de 320×180 y 160×90."""
    vid = vid.lower()      # los nombres de archivo del proyecto van en minúsculas (convención de nombres)
    destino = os.path.join(salida, 'miniatura-%s.png' % vid)
    im.save(destino, optimize=True)
    mov = im.resize((1920, 1080), Image.LANCZOS) if im.height > 1080 else im
    calidad = 90
    while True:
        buf = io.BytesIO()
        mov.save(buf, 'JPEG', quality=calidad, optimize=True)
        if buf.tell() < 1_900_000 or calidad <= 50:
            break
        calidad -= 5
    with open(os.path.join(salida, 'miniatura-%s-movil.jpg' % vid), 'wb') as f:
        f.write(buf.getvalue())
    im.resize((320, 180), Image.LANCZOS).save(os.path.join(salida, 'miniatura-%s-320x180.png' % vid))
    im.resize((160, 90), Image.LANCZOS).save(os.path.join(salida, 'miniatura-%s-160x90.png' % vid))
    return os.path.getsize(destino) / 1024, buf.tell() / 1024


def principal():
    consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video')
    ap.add_argument('--validar', action='store_true', help='solo revisa el JSON')
    ap.add_argument('--alto', type=int, default=2160, help='alto en píxeles (2160 = 3840×2160; menos para un borrador rápido)')
    a = ap.parse_args()
    video = resolver_video(a.video)
    texto = leer(ruta(video, F_SPEC))
    if texto is None:
        print('No existe %s: crea ese archivo con las variantes (ver 00-contexto/produccion/guia-de-miniaturas.md, sección 5).' % F_SPEC)
        return 1
    try:
        variantes, avisos = validar(video, json.loads(texto))
    except ValueError as e:
        print('%s no es JSON válido: %s' % (F_SPEC, e))
        return 1
    except ErrorSpec as e:
        print('ERROR en %s:\n%s' % (F_SPEC, e))
        return 1
    for av in avisos:
        print('AVISO ' + av)
    if a.validar:
        print('OK: %d variante(s) válidas.' % len(variantes))
        return 0
    ident, _ = identidad_efectiva(video)
    salida = ruta(video, CARPETA)
    os.makedirs(salida, exist_ok=True)
    try:
        for v in variantes:
            im, pal = dibujar(video, v, ident, a.alto)
            kb_png, kb_jpg = guardar(im, salida, v['id'])
            c, brillo, colorido, elementos = perfil(im, pal, v)
            print('OK miniatura-%s · %dx%d · %.0f KB (móvil %.0f KB) · contraste %.1f:1 · brillo %.0f/255 · colorido %.0f · %s · «%s»' % (
                v['id'].lower(), im.width, im.height, kb_png, kb_jpg, c, brillo, colorido, '+'.join(elementos), v['concepto'].strip()))
    except ErrorSpec as e:
        print('ERROR: %s' % e)
        return 1
    print('Comprueba las vistas -320x180.png (tamaño real en YouTube) y -160x90.png: el texto debe leerse sin esfuerzo (guía D4).')
    return 0


if __name__ == '__main__':
    sys.exit(principal())
