"""Funciones compartidas por estado-video.py y validar-video.py (solo biblioteca estándar)."""
import hashlib
import json
import os
import re
import sys
import unicodedata

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CANALES = os.path.join(RAIZ, '02-canales')

# Estructura de un video (ver 00-contexto/produccion/estructura-de-un-canal.md): una carpeta numerada por etapa.
GUION = '01-guion'
REVISION = '02-revision'
ESCALETA = '03-escaleta'
VOZ = '04-voz'
LICENCIAS = '05-licencias'
MONTAJE = '06-montaje'
MINIATURAS = '07-miniaturas'
ENTREGABLES = '08-entregables'
PUBLICACION = '09-publicacion'
IDENTIDAD = 'identidad'
ARCHIVO = '_archivo'

# Archivos principales de un video (ruta relativa a la carpeta del video)
F_GUION = GUION + '/guion.md'
F_CIFRAS = GUION + '/verificacion-de-cifras.md'
F_SUBTITULOS = GUION + '/texto-para-subtitulos.txt'
F_INFORME_AUDITOR = REVISION + '/informe-auditor-guion.md'
F_INFORME_VERIFICADOR = REVISION + '/informe-verificador.md'
F_ESCALETA = ESCALETA + '/escaleta-audiovisual.md'
F_GUIA_MONTAJE = ESCALETA + '/guia-de-montaje.md'
F_LICENCIAS = LICENCIAS + '/registro-de-licencias.md'
F_ENCARGO_MINIATURAS = MINIATURAS + '/encargo-de-miniaturas.md'
F_CAPITULOS = PUBLICACION + '/capitulos-y-descripcion.md'
F_METRICAS = PUBLICACION + '/metricas-y-seguimiento.md'
F_IDENTIDAD = IDENTIDAD + '/identidad.json'          # tanto en el canal como en el video


def ruta(base, relativa):
    """base + una ruta relativa con «/» (la normaliza al separador del sistema)."""
    return os.path.join(base, *relativa.split('/'))


def slug(texto):
    """'Hace Eones' -> 'hace-eones'; 'Video 02 - Edad del universo' -> 'video-02-edad-del-universo'."""
    t = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


def carpeta_canal(video):
    """El canal de un video: <canal>/videos/<video>."""
    return os.path.dirname(os.path.dirname(os.path.abspath(video)))


def listar_canales():
    return sorted(d for d in os.listdir(CANALES) if os.path.isdir(os.path.join(CANALES, d))) if os.path.isdir(CANALES) else []


def resolver_canal(nombre):
    """Acepta 'hace-eones', 'Hace Eones' o una ruta; devuelve la carpeta del canal (o None)."""
    if os.path.isdir(nombre) and os.path.dirname(os.path.abspath(nombre)) == CANALES:
        return os.path.abspath(nombre)
    for d in listar_canales():
        if slug(d) == slug(nombre):
            return os.path.join(CANALES, d)
    return None


def videos_de(canal):
    """Carpetas de video de un canal (<canal>/videos/NN-nombre), en orden."""
    base = os.path.join(canal, 'videos')
    return sorted(os.path.join(base, d) for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))) if os.path.isdir(base) else []


def consola():
    """Fuerza UTF-8 en la salida (la consola de Windows suele no serlo)."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


def resolver_video(arg):
    """Acepta una ruta, o '<canal>/<n>' (p. ej. 'hace-eones/2', 'Hace Eones/Video 02', 'hace-eones/02-edad').
    Devuelve la carpeta del video (<canal>/videos/NN-nombre)."""
    ab = os.path.abspath(arg)
    if os.path.isdir(ab) and os.path.exists(ruta(ab, F_GUION)):
        return ab
    canal_txt, resto = os.path.split(arg.rstrip('/\\'))
    canal = resolver_canal(canal_txt) if canal_txt else None
    if canal:
        m = re.fullmatch(r'\s*(?:video\s*)?(\d+)\s*', resto, re.I)
        prefijo = ('%02d' % int(m.group(1))) if m else slug(re.sub(r'^video\s*', '', resto, flags=re.I))
        hallados = [v for v in videos_de(canal) if os.path.basename(v).startswith(prefijo)]
        if len(hallados) == 1:
            return hallados[0]
        if len(hallados) > 1:
            sys.exit('Ambiguo, coinciden: ' + ', '.join(os.path.basename(h) for h in hallados))
    sys.exit('No encuentro la carpeta del video: %r (usa la ruta o "canal/NN", p. ej. "hace-eones/2")' % arg)


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
    """Identidad que vale para un video: la del canal (<canal>/identidad/identidad.json) y, si el video declara base «propia»,
    lo que cambie su propio <video>/identidad/identidad.json. Devuelve (identidad, origen) con el origen de cada valor
    («defecto», «canal» o «video»). La identidad lleva además 'base' del video ('', 'canal' o 'propia') y 'logo_ruta'."""
    video = os.path.abspath(video)
    canal = carpeta_canal(video)
    ident = {'nombre': os.path.basename(canal).replace('-', ' ').upper(), 'logo': '', 'fuente': 'inter', 'voz': '', 'animacion': '',
             'musica': {'pistas': []}, 'efectos': {'usar': False}, 'colores': dict(COLORES_DEFECTO)}
    origen = {k: 'defecto' for k in list(ident)}
    c = _json(ruta(canal, F_IDENTIDAD))
    for k in CLAVES_IDENTIDAD:
        if c.get(k):
            ident[k], origen[k] = c[k], 'canal'
    if c.get('colores'):
        ident['colores'].update(c['colores'])
        origen['colores'] = 'canal'
    v = _json(ruta(video, F_IDENTIDAD))
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
