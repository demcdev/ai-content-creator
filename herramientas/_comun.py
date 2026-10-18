"""Funciones compartidas por estado-video.py y validar-video.py (solo biblioteca estándar)."""
import hashlib
import json
import os
import re
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CANALES = os.path.join(RAIZ, '02_canales')


def consola():
    """Fuerza UTF-8 en la salida (la consola de Windows suele no serlo)."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


def resolver_video(arg):
    """Acepta una ruta, o 'Hace Eones/Video 02', o 'Hace Eones/2'. Devuelve la carpeta del video."""
    candidatos = [os.path.abspath(arg), os.path.join(CANALES, arg)]
    for c in candidatos:
        if os.path.isdir(c) and os.path.exists(os.path.join(c, 'Guion.md')):
            return c
    canal, resto = os.path.split(arg.rstrip('/\\'))
    base = os.path.join(CANALES, canal) if canal else CANALES
    if os.path.isdir(base):
        m = re.fullmatch(r'\s*(\d+)\s*', resto)
        prefijo = ('Video %02d' % int(m.group(1))) if m else resto
        hallados = sorted(d for d in os.listdir(base)
                          if d.lower().startswith(prefijo.lower()) and os.path.isdir(os.path.join(base, d)))
        if len(hallados) == 1:
            return os.path.join(base, hallados[0])
        if len(hallados) > 1:
            sys.exit('Ambiguo, coinciden: ' + ', '.join(hallados))
    sys.exit('No encuentro la carpeta del video: %r (usa la ruta o "Canal/Video NN")' % arg)


def leer(ruta):
    try:
        with open(ruta, encoding='utf-8') as fh:
            return fh.read()
    except OSError:
        return None


def tamano(ruta):
    try:
        return os.path.getsize(ruta)
    except OSError:
        return 0


def sha(ruta):
    h = hashlib.sha256()
    with open(ruta, 'rb') as fh:
        for bloque in iter(lambda: fh.read(65536), b''):
            h.update(bloque)
    return h.hexdigest()[:16]


SEPARADOR = re.compile(r'^\|[\s:\-|]+$')


def filas_datos(texto):
    """Filas con contenido de las tablas markdown (sin encabezado ni separador)."""
    if not texto:
        return 0
    lineas = texto.splitlines()
    n = 0
    for i, linea in enumerate(lineas):
        if SEPARADOR.match(linea):
            j = i + 1
            while j < len(lineas) and lineas[j].startswith('|') and not SEPARADOR.match(lineas[j]):
                if re.search(r'\w', lineas[j]):
                    n += 1
                j += 1
    return n


def archivos(carpeta, extensiones, recursivo=True, ignorar_guion_bajo=False):
    """Lista de archivos con esas extensiones dentro de la carpeta."""
    salida = []
    if not os.path.isdir(carpeta):
        return salida
    for raiz, dirs, nombres in os.walk(carpeta):
        dirs[:] = [d for d in dirs if d not in ('versiones anteriores', '_archivo')]
        for nombre in nombres:
            if ignorar_guion_bajo and nombre.startswith('_'):
                continue
            if nombre.lower().endswith(tuple(extensiones)):
                salida.append(os.path.join(raiz, nombre))
        if not recursivo:
            break
    return salida


def resumen_licencias(texto):
    """(filas, listas, pendientes) sumando la tabla «0. Resumen de estado» del registro de licencias."""
    if not texto:
        return None
    m = re.search(r'##\s*0\.[^\n]*\n(.*?)(?=\n##\s)', texto, re.S)
    if not m:
        return None
    filas = listas = pend = 0
    for linea in m.group(1).splitlines():
        celdas = [c.strip() for c in linea.strip().strip('|').split('|')]
        if len(celdas) >= 4 and all(re.fullmatch(r'\d+', c) for c in celdas[1:4]):
            filas += int(celdas[1])
            listas += int(celdas[2])
            pend += int(celdas[3])
    return filas, listas, pend


def _limites_seccion(texto, titulo):
    """(líneas, inicio, fin) de la sección «## ...titulo...» hasta el siguiente «## » (sin contar «###»)."""
    lineas = texto.splitlines()
    for i, l in enumerate(lineas):
        if l.startswith('## ') and titulo.lower() in l.lower():
            j = i + 1
            while j < len(lineas) and not lineas[j].startswith('## '):
                j += 1
            return lineas, i, j
    return lineas, None, None


def seccion_h2(texto, titulo):
    """Texto de la sección «## ...titulo...» (vacío si no existe)."""
    lineas, i, j = _limites_seccion(texto or '', titulo)
    return '\n'.join(lineas[i:j]) if i is not None else ''


def sin_seccion(texto, titulo):
    """El texto sin esa sección."""
    lineas, i, j = _limites_seccion(texto or '', titulo)
    return '\n'.join(lineas[:i] + lineas[j:]) if i is not None else (texto or '')


# ------------------------------------------------------------------ identidad (canal + video)
COLORES_DEFECTO = {'BG': [11, 16, 38], 'AMBAR': [242, 184, 75], 'HUESO': [245, 241, 232], 'TIERRA': [96, 158, 255]}
CLAVES_IDENTIDAD = ('nombre', 'logo', 'fuente', 'voz', 'animacion', 'musica', 'efectos')


def _json(ruta):
    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    return {}


def identidad_efectiva(video):
    """Identidad que vale para un video: la del canal (<canal>/identidad.json) y, si el video declara base «propia»,
    lo que cambie su propio <video>/identidad.json. Devuelve (identidad, origen) con el origen de cada valor
    («defecto», «canal» o «video»). La identidad lleva además 'base' del video ('', 'canal' o 'propia') y 'logo_ruta'."""
    video = os.path.abspath(video)
    canal = os.path.dirname(video)
    ident = {'nombre': os.path.basename(canal).upper(), 'logo': '', 'fuente': 'inter', 'voz': '', 'animacion': '',
             'musica': {'pistas': []}, 'efectos': {'usar': False}, 'colores': dict(COLORES_DEFECTO)}
    origen = {k: 'defecto' for k in list(ident)}
    c = _json(os.path.join(canal, 'identidad.json'))
    for k in CLAVES_IDENTIDAD:
        if c.get(k):
            ident[k], origen[k] = c[k], 'canal'
    if c.get('colores'):
        ident['colores'].update(c['colores'])
        origen['colores'] = 'canal'
    v = _json(os.path.join(video, 'identidad.json'))
    base = v.get('base', '')
    logo_en = canal
    if base == 'propia':
        for k in CLAVES_IDENTIDAD:
            if v.get(k):
                ident[k], origen[k] = v[k], 'video'
                if k == 'logo':
                    logo_en = video
        if v.get('colores'):
            ident['colores'].update(v['colores'])
            origen['colores'] = 'video'
    ident['base'] = base
    ident['logo_ruta'] = os.path.join(logo_en, ident['logo']) if ident['logo'] else ''
    return ident, origen
