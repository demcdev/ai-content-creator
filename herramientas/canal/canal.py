#!/usr/bin/env python3
"""
Punto de entrada único del flujo de un video: delega en los programas de herramientas/ y automatiza lo que no
necesita IA ni decisión humana. No usa IA ni claves. Se ejecuta desde la raíz del proyecto:

  python herramientas/canal/canal.py ayuda --corta              # lista de comandos en pocas líneas
  python herramientas/canal/canal.py siguiente "hace-eones/3"   # hace lo automático y dice qué falta
  python herramientas/canal/canal.py contexto "hace-eones/3" --para guion|revision|escaleta

El video se indica como «<canal>/<n>» (p. ej. hace-eones/3) o como ruta. Los pasos automáticos (validar, alinear,
escenas, verificar solapes) son incrementales: guardan la huella de sus entradas en <video>/.estado/huellas.json y no
se rehacen si nada cambió. Con --seco, «siguiente» solo dice qué haría (no escribe nada).
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
HERR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # herramientas/
sys.path.insert(0, os.path.join(HERR, 'nucleo'))
from _comun import (ENTREGABLES, F_CIFRAS, F_ESCALETA, F_GUION, F_IDENTIDAD, F_LICENCIAS, F_SUBTITULOS, MINIATURAS, MONTAJE,  # noqa: E402
                    RAIZ, REVISION, VOZ, archivos, carpeta_canal, consola, filas_datos, identidad_efectiva, leer, resolver_video,
                    ruta, seccion_h2, sha, sin_seccion, tamano)

YO = 'python herramientas/canal/canal.py'
P = {   # programas en los que se delega (ruta relativa a herramientas/)
    'nuevo': 'video/nuevo-video.py', 'estado': 'video/estado-video.py', 'validar': 'video/validar-video.py',
    'escenas': 'video/escaleta-a-escenas.py', 'identidad': 'identidad/identidad.py', 'voz': 'voz/voces.py',
    'animaciones': 'montaje/catalogo/animaciones.py', 'alinear': 'montaje/tuberia/alinear.py',
    'revisar-proyecto': 'validacion/validar-proyecto.py',
}
MEDIOS = ('.wav', '.mp3', '.mp4', '.mov', '.m4a', '.ogg', '.flac')
F_REGLAS = '00-contexto/politicas/reglas-detalladas.md'
F_CHECKLIST = '00-contexto/produccion/checklist-escritura-guion.md'
F_CHECK_CANAL = 'estrategia/02-politicas-y-checklist.md'     # dentro de la carpeta del canal

AYUDA_CORTA = '''Uso: %s <orden> [video] [opciones]     (video = "<canal>/<n>", p. ej. hace-eones/3)
  siguiente <v> [--seco]          hace lo automático (validar, alinear, escenas, solapes) y dice qué falta
  contexto <v> [--para guion|revision|escaleta]   contexto mínimo para ese paso (no leer documentos enteros)
  estado <v> [--aprobar P | --sellar R | --revisar R | --diff R | --escribir]
  nuevo <canal> <n> "<nombre>"    crea la carpeta del video
  validar <v> [--etapa guion|montaje|final]       lint gratis
  identidad mostrar|resumen|canal|video ...       identidad del canal o del video
  voz [<v>]                       voces disponibles o comandos de la voz del video
  animaciones [id] [<v> --aplicar]                catálogo de animaciones
  alinear <v> [--forzar]          voz -> 06-montaje/tiempos.json (solo si cambió)
  escenas <v> [--forzar]          escaleta -> 06-montaje/escenas.json (solo si cambió; conserva tipos)
  montar <v> [--frame S f.png | --verificar | --solo-audio | N] [--script x.py]
  publicar <v>                    lint final, entregables y checklist «antes de subir» (no sube nada)
  revisar-proyecto [--solo-errores]               enlaces, nombres y estructura de todo el proyecto''' % YO


# ------------------------------------------------------------------ utilidades
def rel(p):
    return os.path.relpath(p, RAIZ).replace(os.sep, '/')


def nombre_corto(carpeta):
    """'<canal>/<n>' para los comandos que se imprimen."""
    m = re.match(r'(\d+)', os.path.basename(carpeta))
    canal = os.path.basename(carpeta_canal(carpeta))
    return '%s/%d' % (canal, int(m.group(1))) if m else rel(carpeta)


def correr(programa, args, capturar=False, cwd=None):
    """Ejecuta un programa de herramientas/ (o una ruta) con este mismo Python. Devuelve (código, salida)."""
    script = programa if os.path.isabs(programa) else os.path.join(HERR, *programa.split('/'))
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    r = subprocess.run([sys.executable, script] + list(args), cwd=cwd or RAIZ, env=env, text=True, encoding='utf-8',
                       errors='replace', capture_output=capturar)
    return r.returncode, ((r.stdout or '') + (r.stderr or '')) if capturar else ''


def cargar_modulo(nombre, relativa):
    spec = importlib.util.spec_from_file_location(nombre, os.path.join(HERR, *relativa.split('/')))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def firma(archivo):
    """Huella de un archivo: contenido para texto, tamaño y fecha para medios (no se leen 50 MB de audio)."""
    if not os.path.exists(archivo):
        return '-'
    if archivo.lower().endswith(MEDIOS):
        return '%d:%d' % (os.path.getsize(archivo), int(os.path.getmtime(archivo)))
    return sha(archivo)


def huella(*partes):
    h = hashlib.sha256()
    for p in partes:
        h.update(json.dumps(p, sort_keys=True, ensure_ascii=False).encode('utf-8'))
    return h.hexdigest()[:16]


class Huellas:
    """<video>/.estado/huellas.json: {paso: {huella, fecha, resultado}}."""

    def __init__(self, carpeta, seco=False):
        self.arch = os.path.join(carpeta, '.estado', 'huellas.json')
        self.seco = seco
        try:
            with open(self.arch, encoding='utf-8') as f:
                self.datos = json.load(f)
        except (OSError, ValueError):
            self.datos = {}

    def vigente(self, paso, h):
        d = self.datos.get(paso)
        return d if d and d.get('huella') == h else None

    def guardar(self, paso, h, resultado):
        self.datos[paso] = {'huella': h, 'fecha': datetime.date.today().isoformat(), 'resultado': resultado}
        if self.seco:
            return
        os.makedirs(os.path.dirname(self.arch), exist_ok=True)
        with open(self.arch, 'w', encoding='utf-8') as f:
            json.dump(self.datos, f, ensure_ascii=False, indent=1)


def script_montaje(carpeta, elegido=None):
    """(ruta, motivo): el script de 06-montaje que monta el video (montaje.json «script», video.py o el único .py)."""
    m = os.path.join(carpeta, MONTAJE)
    if elegido:
        p = elegido if os.path.isabs(elegido) else os.path.join(m, elegido)
        return (p, '') if os.path.exists(p) else (None, 'no existe %s' % rel(p))
    cfg = leer(os.path.join(m, 'montaje.json'))
    nombre = (json.loads(cfg).get('script') if cfg else None) or 'video.py'
    if os.path.exists(os.path.join(m, nombre)):
        return os.path.join(m, nombre), ''
    pys = sorted(f for f in os.listdir(m) if f.endswith('.py') and not f.startswith('_')) if os.path.isdir(m) else []
    if len(pys) == 1:
        return os.path.join(m, pys[0]), ''
    if not pys:
        return None, 'no hay script de montaje en 06-montaje/'
    return None, 'varios scripts en 06-montaje/ (%s): indica uno con --script o con "script" en montaje.json' % ', '.join(pys)


def codigo_montaje():
    """Huella del código común de montaje (si cambia, se vuelve a verificar)."""
    base = os.path.join(HERR, 'montaje')
    return [(rel(p), sha(p)) for p in sorted(archivos(base, ('.py',)))]


# ------------------------------------------------------------------ pasos automáticos (incrementales)
# Cada paso devuelve (estado, mensaje): estado = 'hecho' | 'al-dia' | 'omitido' | 'falla' | 'haria'
def paso_validar(carpeta, h, etapa='guion', seco=False):
    if tamano(ruta(carpeta, F_GUION)) <= 1500:
        return 'omitido', 'el guion aún es la plantilla'
    entradas = [firma(ruta(carpeta, F_GUION)), firma(ruta(carpeta, F_CIFRAS)), sha(os.path.join(HERR, *P['validar'].split('/'))), etapa]
    if etapa != 'guion':
        entradas += [firma(ruta(carpeta, F_ESCALETA)), firma(ruta(carpeta, F_LICENCIAS)),
                     sorted(firma(x) for x in archivos(ruta(carpeta, VOZ), MEDIOS))]
    if etapa == 'final':
        entradas += [sorted(firma(x) for x in archivos(ruta(carpeta, ENTREGABLES), ('.mp4', '.srt'), recursivo=False)),
                     sorted(firma(x) for x in archivos(ruta(carpeta, MINIATURAS), ('.png', '.jpg', '.jpeg', '.webp')))]
    hv = huella(entradas)
    paso = 'validar-' + etapa
    previo = h.vigente(paso, hv)
    if previo:
        r = previo['resultado']
        return ('al-dia' if r['codigo'] == 0 else 'falla'), 'sin cambios desde el %s → %s' % (previo['fecha'], r['salida'])
    codigo, salida = correr(P['validar'], [carpeta, '--etapa', etapa], capturar=True)
    lineas = salida.strip().splitlines()
    resumen = '\n'.join([lineas[0] if lineas else '(sin salida)'] + [x for x in lineas if x.startswith('[ERROR]')])
    h.guardar(paso, hv, {'codigo': codigo, 'salida': resumen})
    return ('hecho' if codigo == 0 else 'falla'), resumen


def entradas_alinear(carpeta):
    voz = ruta(carpeta, VOZ)
    wavs = [os.path.join(voz, f) for f in os.listdir(voz) if f.lower().endswith('.wav')] if os.path.isdir(voz) else []
    if not wavs:
        return None
    audio = max(wavs, key=os.path.getsize)
    cfg = json.loads(leer(os.path.join(carpeta, MONTAJE, 'montaje.json')) or '{}')
    polly = os.path.join(voz, 'polly')
    partes = os.path.join(voz, 'partes')
    return [os.path.basename(audio), firma(audio), firma(ruta(carpeta, F_SUBTITULOS)),
            {k: cfg.get(k) for k in ('kmax', 'correcciones')},
            sorted(firma(x) for x in archivos(polly, ('.txt', '.mp3'), recursivo=False)),
            sorted(firma(x) for x in archivos(partes, ('.wav',), recursivo=False)),
            firma(os.path.join(HERR, 'voz', 'sustituciones.json')), sha(os.path.join(HERR, *P['alinear'].split('/')))]


def paso_alinear(carpeta, h, seco=False, forzar=False):
    e = entradas_alinear(carpeta)
    if e is None:
        return 'omitido', 'no hay voz todavía (04-voz/*.wav)'
    if tamano(ruta(carpeta, F_SUBTITULOS)) == 0:
        return 'omitido', 'falta %s' % F_SUBTITULOS
    hv = huella(e)
    tiempos = os.path.join(carpeta, MONTAJE, 'tiempos.json')
    previo = h.vigente('alinear', hv)
    if not forzar and previo and os.path.exists(tiempos):
        return 'al-dia', 'tiempos.json al día (%s)' % previo['resultado']
    if seco:
        return 'haria', 'alinearía la voz -> 06-montaje/tiempos.json (%s)' % ('la voz o el texto cambiaron' if os.path.exists(tiempos) else 'no existe')
    codigo, salida = correr(P['alinear'], [carpeta], capturar=True)
    ultima = re.sub(r' -> .*$', '', (salida.strip().splitlines() or [''])[-1])
    if codigo:
        return 'falla', salida.strip()[-600:]
    h.guardar('alinear', hv, ultima)
    return 'hecho', ultima


def paso_escenas(carpeta, h, seco=False, forzar=False):
    texto = sin_seccion(leer(ruta(carpeta, F_ESCALETA)) or '', 'Planilla de producción')
    if filas_datos(texto) == 0:
        return 'omitido', 'la escaleta técnica no tiene escenas'
    destino = os.path.join(carpeta, MONTAJE, 'escenas.json')
    if not os.path.exists(destino) and not os.path.exists(os.path.join(carpeta, MONTAJE, 'video.py')):
        return 'omitido', 'el montaje es propio (sin video.py ni escenas.json): no usa escenas.json'
    hv = huella(sha_texto(texto), sha(os.path.join(HERR, *P['escenas'].split('/'))))
    previo = h.vigente('escenas', hv)
    if not forzar and previo and os.path.exists(destino):
        return 'al-dia', 'escenas.json al día (%s)' % previo['resultado']
    if seco:
        return 'haria', 'regeneraría 06-montaje/escenas.json desde la escaleta (conservando tipos)'
    codigo, salida = correr(P['escenas'], [carpeta, '--forzar' if forzar else '--fusionar'], capturar=True)
    if codigo:
        return 'falla', salida.strip()[-600:]
    linea = re.sub(r' -> .*?\(', ' (', salida.strip().splitlines()[-1])
    h.guardar('escenas', hv, linea)
    return 'hecho', linea


def sha_texto(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()[:16]


def paso_verificar(carpeta, h, seco=False, script=None):
    m = os.path.join(carpeta, MONTAJE)
    if not os.path.exists(os.path.join(m, 'tiempos.json')):
        return 'omitido', 'falta 06-montaje/tiempos.json (alinear la voz primero)'
    sc, motivo = script_montaje(carpeta, script)
    if not sc:
        return 'omitido', motivo
    ident, _ = identidad_efectiva(carpeta)
    locales = sorted((f, firma(os.path.join(m, f))) for f in os.listdir(m) if f.endswith(('.py', '.json')))
    hv = huella(os.path.basename(sc), locales, ident, codigo_montaje())
    previo = h.vigente('verificar', hv)
    if previo:
        n = previo['resultado']
        return ('al-dia' if n == 0 else 'falla'), 'sin cambios: %s solapes' % n
    if seco:
        return 'haria', 'correría «%s --verificar» (nada se tapa con nada)' % os.path.basename(sc)
    codigo, salida = correr(sc, ['--verificar'], capturar=True, cwd=m)
    total = re.search(r'total solapes:\s*(\d+)', salida)
    if codigo or not total:
        return 'falla', salida.strip()[-600:]
    n = int(total.group(1))
    h.guardar('verificar', hv, n)
    return ('hecho' if n == 0 else 'falla'), '%d solapes%s' % (n, '' if n == 0 else ':\n' + '\n'.join(
        x for x in salida.splitlines() if x.startswith('SOLAPE'))[:1500])


# ------------------------------------------------------------------ siguiente
def guia(clave, carpeta, det, datos):
    """(tipo, qué falta, [cómo]) de una etapa pendiente. tipo: HUMANO, IA o COMANDO."""
    v = nombre_corto(carpeta)
    q = '"%s"' % v
    ctx = '%s contexto %s --para %%s' % (YO, q)
    if clave == 'p-idea':
        return 'HUMANO', 'aprobar la idea y el packaging (título, miniatura, promesa que el video cumple).', [
            'tú decides; luego: %s estado %s --aprobar idea' % (YO, q)]
    if clave == 'investigacion':
        return 'IA', 'la tabla 01-guion/verificacion-de-cifras.md está vacía (%s).' % det, [
            'investigar cifras con fuente primaria y llenar la tabla', ctx % 'guion']
    if clave == 'guion':
        return 'IA', '01-guion/guion.md sigue siendo la plantilla (%s).' % det, [
            'escribir con la skill guionista-retencion', ctx % 'guion']
    if clave == 'rev-guion':
        faltan = [r for r in ('verificador', 'auditor-guion') if not ('%s: vigente' % r) in det]
        como = [ctx % 'revision']
        for r in faltan:
            if '%s: cambiado' % r in det:
                como.append('solo lo cambiado: %s estado %s --diff %s' % (YO, q, r))
        if 'auditor-guion' in faltan:
            como.append('subagente auditor: «%s modo guion»' % rel(carpeta))
        if 'verificador' in faltan:
            como.append('subagente verificador: «%s»' % rel(carpeta))
        como.append('tras corregir: %s estado %s --sellar %s' % (YO, q, ' '.join(faltan)))
        return 'IA', 'revisión del guion sin sello vigente (%s).' % det, como
    if clave == 'p-guion':
        return 'HUMANO', 'aprobar el guion revisado.', ['%s estado %s --aprobar guion' % (YO, q)]
    if clave == 'escaleta':
        return 'IA', 'la escaleta técnica no tiene escenas.', ['skill escaleta-audiovisual', ctx % 'escaleta']
    if clave == 'planilla':
        return 'IA', 'falta la «Planilla de producción» (3 columnas) en la escaleta.', ['skill guionista-retencion', ctx % 'escaleta']
    if clave == 'identidad':
        ident = cargar_modulo('identidad_mod', P['identidad'])
        return 'HUMANO', 'elegir la identidad del video (preguntar con la herramienta de preguntas).', [
            'opción «la base del canal»: ' + ident.resumen(carpeta),
            '%s identidad video %s --base canal' % (YO, q),
            'o propia: %s identidad video %s --base propia --voz <id> --animacion <id> ...' % (YO, q)]
    if clave == 'voz':
        return 'COMANDO', 'no hay audio en 04-voz/ (la síntesis usa clave y cuesta: confirma antes).', [
            '%s voz %s   (imprime los pasos de la voz de la identidad)' % (YO, q)]
    if clave == 'miniaturas':
        return 'IA', 'no hay miniaturas en 07-miniaturas/.', ['subagente o skill de miniaturas; encargo en 07-miniaturas/']
    if clave == 'licencias':
        return 'HUMANO', 'licencias incompletas (%s).' % det, ['completar 05-licencias/registro-de-licencias.md con fichas y capturas']
    if clave == 'montaje':
        return 'COMANDO', 'no hay archivos de montaje.', ['%s escenas %s' % (YO, q)]
    if clave == 'video':
        return 'COMANDO', 'falta el video final en 08-entregables/ (render de varios minutos).', [
            '%s montar %s --frame 60 f.png   (revisar un fotograma)' % (YO, q), '%s montar %s   (render y copia a 08-entregables/)' % (YO, q)]
    if clave == 'rev-final':
        return 'IA', 'control final sin sello vigente (%s).' % det, [
            'subagente auditor: «%s modo final»' % rel(carpeta), 'tras corregir: %s estado %s --sellar auditor-final' % (YO, q)]
    if clave == 'p-corte':
        return 'HUMANO', 'aprobar el corte final.', ['%s estado %s --aprobar corte' % (YO, q)]
    if clave == 'descripcion':
        return 'IA', '09-publicacion/capitulos-y-descripcion.md está vacío.', ['skill SEO (descripción propia, fuentes y capítulos)']
    if clave == 'subtitulos':
        return 'COMANDO', 'no hay subtítulos (.txt o .srt).', ['el render deja el .srt: %s montar %s' % (YO, q)]
    if clave == 'metricas':
        return 'HUMANO', 'publicar y anotar métricas (2–3 días, 7 y 28).', ['%s publicar %s' % (YO, q), 'anotar en 09-publicacion/metricas-y-seguimiento.md']
    return 'HUMANO', det, []


def cmd_siguiente(argv):
    ap = argparse.ArgumentParser(prog='canal.py siguiente')
    ap.add_argument('video')
    ap.add_argument('--seco', action='store_true', help='no ejecuta ni escribe nada: solo dice qué haría')
    a = ap.parse_args(argv)
    carpeta = resolver_video(a.video)
    ev = cargar_modulo('estado_video', P['estado'])
    datos = ev.cargar(carpeta)
    h = Huellas(carpeta, seco=a.seco)
    print('VIDEO: %s%s' % (rel(carpeta), '   (modo seco: no se ejecuta nada)' if a.seco else ''))

    pasos = [('validar guion', lambda: paso_validar(carpeta, h, 'guion', a.seco)),
             ('alinear voz', lambda: paso_alinear(carpeta, h, a.seco)),
             ('escenas', lambda: paso_escenas(carpeta, h, a.seco)),
             ('verificar solapes', lambda: paso_verificar(carpeta, h, a.seco))]
    if ev.firma_final(carpeta):
        pasos.append(('validar final', lambda: paso_validar(carpeta, h, 'final', a.seco)))
    print('AUTOMÁTICO:')
    fallos = {}
    marca = {'hecho': 'hecho', 'al-dia': 'al día', 'omitido': '—', 'falla': 'FALLA', 'haria': 'haría'}
    for nombre, fn in pasos:
        estado, msg = fn()
        if estado == 'falla':
            fallos[nombre] = msg
        lineas = msg.splitlines() or ['']
        print('  [%-6s] %-17s %s' % (marca[estado], nombre, lineas[0]))
        for x in lineas[1:]:
            print('  %s%s' % (' ' * 28, x))

    lista = ev.etapas(carpeta, datos)
    pendientes = [e for e in lista if not e[2]]
    if not pendientes:
        print('SIGUIENTE: todo completo.')
        return 0
    clave, nombre, _, det, _ = pendientes[0]
    if clave == 'rev-guion' and 'validar guion' in fallos:
        tipo, falta, como = 'ARREGLAR', 'el lint del guion falla: corrige antes de pedir revisión con IA.', [
            '%s validar "%s"' % (YO, nombre_corto(carpeta))]
    elif clave == 'video' and 'verificar solapes' in fallos:
        tipo, falta, como = 'ARREGLAR', 'la verificación de solapes falla: nada se tapa con nada antes de renderizar.', [
            '%s montar "%s" --verificar' % (YO, nombre_corto(carpeta))]
    elif clave == 'rev-final' and 'validar final' in fallos:
        tipo, falta, como = 'ARREGLAR', 'el lint final falla.', ['%s validar "%s" --etapa final' % (YO, nombre_corto(carpeta))]
    else:
        tipo, falta, como = guia(clave, carpeta, det, datos)
    print('SE DETIENE EN: %s  [%s]' % (nombre, tipo))
    print('  Falta: ' + falta)
    for c in como:
        print('  → ' + c)
    if len(pendientes) > 1:
        print('DESPUÉS: ' + ' · '.join(e[1] for e in pendientes[1:4]) + (' · …' if len(pendientes) > 4 else ''))
    return 2 if tipo == 'HUMANO' else 3 if tipo == 'IA' else 1


# ------------------------------------------------------------------ contexto
def checklist_compacta():
    """La checklist de escritura sin los ejemplos entre paréntesis (mismo contenido, menos tokens)."""
    out = []
    for l in (leer(os.path.join(RAIZ, *F_CHECKLIST.split('/'))) or '').splitlines():
        if l.startswith('## '):
            out.append(l[3:] + ':')
        elif l.startswith('- [ ]'):
            out.append('  - ' + re.sub(r'\s*\*\([^)]*\)\*\s*$', '', l[6:]).replace('**', ''))
    return out


def seccion_canal(carpeta, titulo):
    texto = leer(ruta(carpeta_canal(carpeta), F_CHECK_CANAL)) or ''
    s = seccion_h2(texto, titulo)
    return [l.replace('**', '') for l in s.splitlines()[1:] if l.strip()] if s else []


def regla(titulo):
    s = seccion_h2(leer(os.path.join(RAIZ, *F_REGLAS.split('/'))) or '', titulo)
    return [l for l in s.splitlines()[1:] if l.strip()]


def cifras_pendientes(carpeta):
    filas, sin_ok = 0, []
    for l in (leer(ruta(carpeta, F_CIFRAS)) or '').splitlines():
        m = re.match(r'^\|\s*\**(\d+)\**\s*\|', l)
        if not m:
            continue
        filas += 1
        c = [x.strip().replace('**', '') for x in l.strip().strip('|').split('|')]
        if '✅' not in c[-1]:
            sin_ok.append('  #%s %s → %s' % (m.group(1), c[1][:90], c[-1][:70]))
    return filas, sin_ok


def identidad_lineas(carpeta):
    ident, origen = identidad_efectiva(carpeta)
    hexa = lambda rgb: '#%02X%02X%02X' % tuple(rgb)
    anim = {x['id']: x for x in json.loads(leer(os.path.join(HERR, 'montaje', 'catalogo', 'animaciones.json')) or '{}').get('animaciones', [])}
    a = anim.get(ident['animacion'], {})
    return ['base del video: %s' % (ident['base'] or 'SIN ELEGIR (preguntar: ¿canal o propia?)'),
            'voz: %s (%s) · fuente: %s (%s)' % (ident['voz'] or '—', origen['voz'], ident['fuente'], origen['fuente']),
            'animación: %s%s (%s)' % (ident['animacion'] or '—', ' · %s · estado %s' % (a.get('nombre', ''), a.get('estado', '?')) if a else '', origen['animacion']),
            'colores: ' + ', '.join('%s %s' % (k, hexa(v)) for k, v in ident['colores'].items()),
            'música: %s · efectos: %s' % (', '.join(ident['musica'].get('pistas', [])) or '—', 'sí' if ident['efectos'].get('usar') else 'no')]


def bloque(titulo, lineas):
    if lineas:
        print('\n## ' + titulo)
        for l in lineas:
            print(l)


def cmd_contexto(argv):
    ap = argparse.ArgumentParser(prog='canal.py contexto')
    ap.add_argument('video')
    ap.add_argument('--para', choices=['guion', 'revision', 'escaleta'])
    a = ap.parse_args(argv)
    carpeta = resolver_video(a.video)
    ev = cargar_modulo('estado_video', P['estado'])
    datos = ev.cargar(carpeta)
    lista = ev.etapas(carpeta, datos)
    sig = next((e for e in lista if not e[2]), None)
    para = a.para or {'investigacion': 'guion', 'guion': 'guion', 'rev-guion': 'revision', 'p-guion': 'revision',
                      'escaleta': 'escaleta', 'planilla': 'escaleta'}.get(sig[0] if sig else '', 'guion')
    q = '"%s"' % nombre_corto(carpeta)
    print('# Contexto para «%s» · %s' % (para, rel(carpeta)))
    print('Etapa actual: %s' % (sig[1] if sig else 'todo completo'))
    guion = ruta(carpeta, F_GUION)
    print('Archivos: %s (%.1f KB) · %s · %s' % (F_GUION, tamano(guion) / 1024, F_CIFRAS, F_ESCALETA))
    bloque('Identidad efectiva', identidad_lineas(carpeta))

    if para in ('guion', 'revision'):
        codigo, salida = correr(P['validar'], [carpeta], capturar=True)
        lint = [l for l in salida.strip().splitlines() if not l.startswith('Video:')]
        bloque('Lint del guion (validar-video.py)', lint if tamano(guion) > 1500 else ['(guion aún en plantilla)'])
        filas, pend = cifras_pendientes(carpeta)
        bloque('Cifras: %d filas, %d sin ✅' % (filas, len(pend)), pend or ['  (todas en ✅)' if filas else '  (tabla vacía)'])
    if para == 'guion':
        bloque('Reglas: guiones', regla('guiones'))
        bloque('Reglas: voz y narración', regla('voz y narración'))
        bloque('Checklist del canal: antes de grabar', seccion_canal(carpeta, 'Antes de grabar'))
        bloque('Checklist de escritura (todos los canales)', checklist_compacta())
    if para == 'revision':
        sellos = []
        for r in ('verificador', 'auditor-guion'):
            vig = ev.vigencia(carpeta, datos, r)
            fecha = datos['sellos'].get(r, {}).get('fecha', '')
            sellos.append('  %s: %s%s' % (r, vig, ' (%s)' % fecha if fecha else ''))
            if vig == 'cambiado':
                sellos.append('    solo lo cambiado: %s estado %s --diff %s' % (YO, q, r))
        bloque('Sellos de revisión', sellos)
        informes = []
        for f in sorted(archivos(ruta(carpeta, REVISION), ('.md',), recursivo=False)):
            primera = ((leer(f) or '').strip().splitlines() or [''])[0]
            informes.append('  %s: %s' % (os.path.basename(f), primera[:100]))
        bloque('Informes previos (primera línea)', informes)
        bloque('Cómo se revisa', ['  1) lint sin errores  2) subagentes auditor («%s modo guion») y verificador («%s»)' % (rel(carpeta), rel(carpeta)),
                                  '  3) corregir  4) %s estado %s --sellar verificador auditor-guion' % (YO, q),
                                  '  Informe en 02-revision/: PASA o FALLA en la primera línea, máx. 300 palabras, archivo y línea por hallazgo.'])
        bloque('Checklist del canal: declaración de IA', seccion_canal(carpeta, 'Declaración de IA'))
        bloque('Checklist de escritura (todos los canales)', checklist_compacta())
    if para == 'escaleta':
        esc = leer(ruta(carpeta, F_ESCALETA)) or ''
        t = json.loads(leer(os.path.join(carpeta, MONTAJE, 'tiempos.json')) or '{}')
        e = json.loads(leer(os.path.join(carpeta, MONTAJE, 'escenas.json')) or '[]')
        datos_v = ['  planilla: %d filas · escaleta técnica: %d escenas' % (filas_datos(seccion_h2(esc, 'Planilla de producción')),
                                                                          filas_datos(sin_seccion(esc, 'Planilla de producción'))),
                   '  voz alineada: %s' % ('%.1f s, %d frases (06-montaje/tiempos.json)' % (t['total'], len(t['frases'])) if t else 'no (sin tiempos.json: usar la duración estimada del guion)'),
                   '  escenas.json: %s' % ('%d escenas, %d aún placeholder' % (len(e), sum(1 for x in e if x.get('tipo') == 'placeholder')) if e else 'no existe')]
        lic = []
        for l in (leer(ruta(carpeta, F_LICENCIAS)) or '').splitlines():
            c = [x.strip().replace('**', '') for x in l.strip().strip('|').split('|')]
            if l.startswith('|') and len(c) >= 4 and re.match(r'^(?:[A-Z]{1,4}|♪)-?\d+$', c[0]):
                lic.append('  %s · %s · %s' % (c[0], c[1][:60], c[-1][:30]))
        bloque('Datos del video', datos_v)
        bloque('Licencias registradas (código · material · estado)', lic or ['  (registro sin filas: cada escena necesita origen y fila de licencia)'])
        bloque('Reglas: producción', regla('producción de cada video'))
        bloque('Reglas: composición', regla('composición'))
        bloque('Formato de fila que lee escaleta-a-escenas', ['  | **E07 · Nombre de la escena** | 03:12–03:40 | descripción | audio | origen y licencia |'])
    return 0


# ------------------------------------------------------------------ montar y publicar
def cmd_alinear(argv):
    ap = argparse.ArgumentParser(prog='canal.py alinear')
    ap.add_argument('video')
    ap.add_argument('--forzar', action='store_true')
    a, resto = ap.parse_known_args(argv)
    carpeta = resolver_video(a.video)
    if resto:      # opciones de alinear.py (--ver, --salida): se delega tal cual
        return correr(P['alinear'], [carpeta] + resto)[0]
    estado, msg = paso_alinear(carpeta, Huellas(carpeta), forzar=a.forzar)
    print('alinear: %s · %s' % (estado, msg))
    return 1 if estado == 'falla' else 0


def cmd_escenas(argv):
    ap = argparse.ArgumentParser(prog='canal.py escenas')
    ap.add_argument('video')
    ap.add_argument('--forzar', action='store_true', help='rehace escenas.json desde cero (pierde los tipos)')
    a = ap.parse_args(argv)
    carpeta = resolver_video(a.video)
    estado, msg = paso_escenas(carpeta, Huellas(carpeta), forzar=a.forzar)
    print('escenas: %s · %s' % (estado, msg))
    return 1 if estado == 'falla' else 0


def cmd_montar(argv):
    ap = argparse.ArgumentParser(prog='canal.py montar', description='Ejecuta el script de 06-montaje; sin opciones, render completo.')
    ap.add_argument('video')
    ap.add_argument('--script', help='script de 06-montaje a usar si hay varios')
    a, resto = ap.parse_known_args(argv)
    carpeta = resolver_video(a.video)
    sc, motivo = script_montaje(carpeta, a.script)
    if not sc:
        sys.exit(motivo)
    completo = not resto or (len(resto) == 1 and resto[0].isdigit())
    h = Huellas(carpeta)
    if completo or resto[0] == '--verificar':
        for nombre, fn in (('alinear', paso_alinear), ('escenas', paso_escenas)):
            estado, msg = fn(carpeta, h)
            print('%s: %s · %s' % (nombre, estado, msg.splitlines()[0] if msg else ''))
            if estado == 'falla':
                return 1
    if resto[:1] == ['--verificar']:
        estado, msg = paso_verificar(carpeta, h, script=sc)
        print('verificar: %s · %s' % (estado, msg))
        return 1 if estado == 'falla' else 0
    if completo:
        estado, msg = paso_verificar(carpeta, h, script=sc)
        print('verificar: %s · %s' % (estado, msg))
        if estado == 'falla':
            return 1
    codigo, _ = correr(sc, resto, cwd=os.path.dirname(sc))
    if codigo == 0 and completo:
        cfg = json.loads(leer(os.path.join(carpeta, MONTAJE, 'montaje.json')) or '{}')
        nombre = cfg.get('nombre', 'video-completo')
        destino = ruta(carpeta, ENTREGABLES)
        os.makedirs(destino, exist_ok=True)
        for ext in ('.mp4', '.srt'):
            origen = os.path.join(os.path.dirname(sc), 'salida', nombre + ext)
            if os.path.exists(origen):
                shutil.copy2(origen, os.path.join(destino, nombre + ext))
                print('copiado a %s/%s' % (ENTREGABLES, nombre + ext))
    return codigo


def cmd_publicar(argv):
    ap = argparse.ArgumentParser(prog='canal.py publicar', description='Prepara la subida: no sube nada.')
    ap.add_argument('video')
    a = ap.parse_args(argv)
    carpeta = resolver_video(a.video)
    ev = cargar_modulo('estado_video', P['estado'])
    datos = ev.cargar(carpeta)
    codigo, salida = correr(P['validar'], [carpeta, '--etapa', 'final'], capturar=True)
    print(salida.strip())
    print('\nControl final: %s · puerta «corte»: %s' % (ev.vigencia(carpeta, datos, ev.ROL_FINAL), datos['puertas'].get('corte', 'sin aprobar')))
    print('\nEntregables:')
    for f in sorted(archivos(ruta(carpeta, ENTREGABLES), ('.mp4', '.srt'), recursivo=False)) + \
            sorted(archivos(ruta(carpeta, MINIATURAS), ('.png', '.jpg', '.jpeg', '.webp'), ignorar_guion_bajo=True)):
        print('  ' + rel(f))
    print('  %s (descripción, capítulos, fuentes)' % rel(ruta(carpeta, '09-publicacion/capitulos-y-descripcion.md')))
    for titulo in ('Declaración de IA', 'Antes de subir'):
        lineas = seccion_canal(carpeta, titulo)
        if lineas:
            print('\n' + titulo + ':')
            print('\n'.join(lineas))
    print('\nSubir en YouTube Studio a mano (oculto o no listado primero). Después: anotar métricas en 09-publicacion/metricas-y-seguimiento.md.')
    return codigo


# ------------------------------------------------------------------ despacho
def delegar(orden, argv):
    if orden == 'voz' and len(argv) == 1 and not argv[0].startswith('-'):
        argv = ['--video', argv[0]]
    return correr(P[orden], argv)[0]


def cmd_ayuda(argv):
    if '--corta' in argv:
        print(AYUDA_CORTA)
    else:
        print(__doc__.strip() + '\n\n' + AYUDA_CORTA + '\n\nDetalle de cada programa: herramientas/LEEME.md')
    return 0


PROPIOS = {'siguiente': cmd_siguiente, 'contexto': cmd_contexto, 'alinear': cmd_alinear, 'escenas': cmd_escenas,
           'montar': cmd_montar, 'publicar': cmd_publicar, 'ayuda': cmd_ayuda}


def main():
    consola()
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        return cmd_ayuda(['--corta'])
    orden, argv = sys.argv[1], sys.argv[2:]
    if orden in PROPIOS:
        return PROPIOS[orden](argv)
    if orden in P:
        return delegar(orden, argv)
    print('Orden desconocida: %s\n' % orden)
    print(AYUDA_CORTA)
    return 1


if __name__ == '__main__':
    sys.exit(main())
