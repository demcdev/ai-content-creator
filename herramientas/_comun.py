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
