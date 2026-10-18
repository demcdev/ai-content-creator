#!/usr/bin/env python3
"""
Servidor local del panel. Expone por HTTP lo que ya sabe el framework —canales, videos, etapas, sellos, identidad y el
«siguiente paso»— para que una interfaz (selector-nichos) lo muestre y (Fase 2a) un conjunto CERRADO de acciones que
delegan en los programas de herramientas/: crear video, elegir identidad, aprobar puertas y sellar revisiones. No usa IA
ni claves, no hace commits y solo escucha en 127.0.0.1.

  python herramientas/panel/servidor.py                 # http://127.0.0.1:8765
  python herramientas/panel/servidor.py --puerto 9000

Lectura (GET, JSON):
  /api/salud                             {"ok": true}
  /api/canales                           canales con su identidad y el avance de cada video
  /api/opciones                          voces, animaciones y fuentes válidas para la identidad
  /api/canales/<canal>/identidad         frase con la identidad base del canal (la de «identidad.py resumen»)
  /api/canales/<canal>/ideas             ideas de video de <canal>/estrategia/*ideas-de-video*.md (con «usada» si ya hay video)
  /api/pasos                             instrucción de cada paso (de pasos.json) y si se puede ejecutar desde el panel
  /api/trabajo?desde=N                   estado y eventos (desde el N) del paso que se ejecuta o se ejecutó
  /api/video/<canal>/<video>             etapas, siguiente paso, puertas y sellos de un video
  /api/video/<canal>/<video>/siguiente  salida de «canal.py siguiente --seco» (no ejecuta ni escribe nada)
  /api/video/<canal>/<video>/comandos?paso=P   comandos sin IA que ejecutaría un paso de tipo «comandos» y qué variables de entorno faltan

Acciones (POST con cuerpo JSON; exigen Origin del selector + cabecera X-Panel + Content-Type application/json):
  /api/video                             {canal, nombre, idea?}       crea el siguiente video (nuevo-video.py); con idea deja 01-guion/idea.md
  /api/video/<canal>/<video>/identidad   {base: canal|propia, ...}    identidad.py video
  /api/video/<canal>/<video>/aprobar     {puerta: idea|guion|corte}   estado-video.py --aprobar
  /api/video/<canal>/<video>/sellar      {rol}                        estado-video.py --sellar (si el informe dice PASA)
  /api/video/<canal>/<video>/licencia    {codigo}                     acepta una fila 🔎 del registro de licencias si su prueba ya está guardada
  /api/video/<canal>/<video>/ejecutar    {paso}                       Claude Code sin pantalla para el paso ACTUAL (ejecutor.py)
  /api/trabajo/cancelar                  {}                           termina el paso en ejecución

La lógica no se duplica: se importan estado-video.py y _comun.py. Si cambian las etapas allí, el panel las ve igual.
"""
import argparse
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import datetime
from urllib.parse import parse_qs, unquote, urlparse

sys.dont_write_bytecode = True
HERR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERR, 'nucleo'))
from _comun import CANALES, F_LICENCIAS, RAIZ, filas_licencias, identidad_efectiva, leer, listar_canales, ruta, videos_de  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ejecutor import Ejecutor, rellenar  # noqa: E402

CANAL_PY = os.path.join(HERR, 'canal', 'canal.py')
ORIGENES = {'http://localhost:5173', 'http://127.0.0.1:5173'}     # el selector en modo desarrollo
HOSTS = {'localhost', '127.0.0.1', '[::1]'}                        # contra DNS rebinding
PUERTO = 8765
NUEVO_PY = os.path.join(HERR, 'video', 'nuevo-video.py')
ESTADO_PY = os.path.join(HERR, 'video', 'estado-video.py')
IDENTIDAD_PY = os.path.join(HERR, 'identidad', 'identidad.py')
PUERTAS = ('idea', 'guion', 'corte')
INFORMES = {'auditor-guion': '02-revision/informe-auditor-guion.md', 'verificador': '02-revision/informe-verificador.md',
            'auditor-final': '02-revision/informe-auditor-final.md'}
FUENTES = ('inter', 'montserrat', 'space')
NOMBRE_PROHIBIDO = re.compile(r'[\\/:*?"<>|]')


class ErrorPanel(Exception):
    """Error que se le explica al usuario (código HTTP + mensaje)."""
    def __init__(self, mensaje, codigo=400):
        super().__init__(mensaje)
        self.codigo = codigo


def _cargar_estado():
    espec = importlib.util.spec_from_file_location('estado_video', os.path.join(HERR, 'video', 'estado-video.py'))
    mod = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(mod)
    return mod


EV = _cargar_estado()
def nombres_secretos():
    """Variables de entorno con claves (las que declaran las voces en voces.json): se quitan del entorno de Claude Code,
    que no las necesita. Solo los pasos de «comandos» (voz) las reciben."""
    return {k for v in _catalogo('voz', 'voces.json').get('voces', []) for k in v.get('claves_env', [])}


EJ = Ejecutor(RAIZ, nombres_secretos)
PASOS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pasos.json')


def pasos_cfg():
    """pasos.json se relee en cada consulta: editar una instrucción no exige reiniciar el servidor."""
    try:
        with open(PASOS_JSON, encoding='utf-8') as f:
            return json.load(f).get('pasos', {})
    except (OSError, ValueError):
        return {}


def pasos_publicos():
    """Lo que ve la interfaz: la instrucción de cada paso y si se puede ejecutar desde el panel (no los permisos)."""
    return {k: {'instruccion': v.get('instruccion', ''), 'ejecutable': bool(v.get('ejecutable')),
                'permisos': (v.get('ejecutable') or {}).get('permisos', ''),
                'tipo': (v.get('ejecutable') or {}).get('tipo', 'ia')} for k, v in pasos_cfg().items()}


def resolver_comandos(carpeta, canal, ejecutable):
    """Comandos SIN IA de un paso de tipo «comandos»: [(texto, argv)], las variables de entorno que exige y el nombre de la voz.
    Salen de la voz de la identidad del video (origen «voz», de voces.json) o de la lista fija del paso en pasos.json.
    Solo se aceptan programas `python` o `node` dentro de herramientas/; nunca shell."""
    rel = _rel(carpeta).replace('\\', '/')
    numero = int(re.match(r'(\d+)', os.path.basename(carpeta)).group(1))
    nombre = ''
    if ejecutable.get('origen') == 'voz':
        voz_id = (identidad_efectiva(carpeta)[0] or {}).get('voz')
        voz = next((v for v in _catalogo('voz', 'voces.json').get('voces', []) if v.get('id') == voz_id), None)
        if not voz:
            raise ErrorPanel('La identidad de este video no tiene una voz definida (o no está en voces.json).', 409)
        plantillas, claves, nombre = voz.get('pasos', []), voz.get('claves_env', []), voz.get('nombre', voz_id)
        sust = {'guion': rel + '/01-guion/guion.md', 'voz': rel + '/04-voz', 'video': rel}
    else:
        plantillas, claves = ejecutable.get('comandos', []), ejecutable.get('claves_env', [])
        sust = {'ref': '%s/%d' % (canal, numero), 'carpeta': rel}
    comandos = []
    for plantilla in plantillas:
        tokens = [rellenar(t, **sust) for t in shlex.split(plantilla)]
        if len(tokens) < 2 or tokens[0] not in ('python', 'node') or not tokens[1].startswith('herramientas/') or '..' in tokens[1]:
            raise ErrorPanel('Comando no permitido (solo python o node dentro de herramientas/): %s' % plantilla, 500)
        programa = sys.executable if tokens[0] == 'python' else shutil.which('node')
        if not programa:
            raise ErrorPanel('No encuentro Node.js («node») en el PATH del servidor.', 409)
        comandos.append((shlex.join(tokens), [programa] + tokens[1:]))
    return comandos, list(claves), nombre


def comandos_de_paso(carpeta, canal, paso):
    cfg = (pasos_cfg().get(paso) or {}).get('ejecutable') or {}
    if cfg.get('tipo') != 'comandos':
        raise ErrorPanel('Ese paso no se ejecuta con comandos.', 400)
    comandos, claves, nombre = resolver_comandos(carpeta, canal, cfg)
    return {'comandos': [c[0] for c in comandos], 'claves': claves, 'faltan': [k for k in claves if not os.environ.get(k)], 'voz': nombre}


def ejecutar_paso(carpeta, canal, cuerpo):
    """Lanza el paso ACTUAL de un video: Claude Code con la instrucción y los permisos de pasos.json, o, si es de tipo
    «comandos», directamente los programas del framework (sin IA)."""
    paso = cuerpo.get('paso')
    cfg = pasos_cfg().get(paso) if isinstance(paso, str) else None
    if not cfg or not cfg.get('ejecutable'):
        raise ErrorPanel('Ese paso no se puede ejecutar desde el panel todavía: copia la instrucción y pégala en Claude Code.')
    sig = resumen_video(carpeta)['siguiente']
    if not sig or sig['clave'] != paso:
        raise ErrorPanel('«%s» no es el paso actual de este video.' % paso, 409)
    if cfg['ejecutable'].get('tipo') == 'comandos':
        comandos, claves, _ = resolver_comandos(carpeta, canal, cfg['ejecutable'])
        faltan = [k for k in claves if not os.environ.get(k)]
        if faltan:
            raise ErrorPanel('Faltan variables de entorno en el servidor: %s. Ponlas en la terminal donde enciendes el servidor '
                             '(PowerShell: $env:NOMBRE = "valor") y reinícialo; nunca las pegues en el chat.' % ', '.join(faltan), 409)
        try:
            return EJ.iniciar_comandos(carpeta, canal, paso, comandos, cfg['ejecutable'].get('minutos', 30)).a_dict(0)
        except ValueError as e:
            raise ErrorPanel(str(e), 409)
    numero = int(re.match(r'(\d+)', os.path.basename(carpeta)).group(1))
    instruccion = rellenar(cfg['instruccion'], ref='%s/%d' % (canal, numero), carpeta=_rel(carpeta).replace('\\', '/'),
                           hoy=datetime.date.today().isoformat())
    try:
        t = EJ.iniciar(carpeta, canal, paso, instruccion, cfg['ejecutable'])
    except ValueError as e:
        raise ErrorPanel(str(e), 409)
    return t.a_dict(0)


def _identidad(carpeta_video):
    try:
        ident, _ = identidad_efectiva(carpeta_video)
    except Exception:
        return None
    return {k: ident.get(k) for k in ('nombre', 'fuente', 'voz', 'animacion', 'colores', 'base')}


def ruta_evidencia(carpeta, captura):
    """Ruta absoluta del archivo de prueba (ficha, captura o descarga) que cita la columna «Captura», si existe dentro del proyecto."""
    m = re.search(r'`([^`]+\.(?:txt|png|jpe?g|pdf|webp|md))`', captura) or re.search(r'(\S+\.(?:txt|png|jpe?g|pdf|webp))', captura)
    if not m:
        return None
    raiz = os.path.realpath(RAIZ) + os.sep
    for base in (os.path.join(carpeta, '05-licencias'), carpeta):
        candidata = os.path.realpath(os.path.join(base, m.group(1)))
        if candidata.startswith(raiz) and os.path.isfile(candidata):
            return candidata
    return None


def licencias_de(carpeta):
    """Filas del registro de licencias con su estado simplificado (lista, captura, pendiente, descartada)."""
    filas = []
    for codigo, material, estado, captura in filas_licencias(leer(ruta(carpeta, F_LICENCIAS))):
        e = 'descartada' if '❌' in estado else 'lista' if '✅' in estado else 'captura' if '🔎' in estado else 'pendiente'
        filas.append({'codigo': codigo, 'material': material[:110], 'estado': e, 'captura': captura[:160], 'evidencia': ruta_evidencia(carpeta, captura) is not None})
    return filas


def resumen_video(carpeta):
    datos = EV.cargar(carpeta)
    lista = EV.etapas(carpeta, datos)
    sig = next((e for e in lista if not e[2]), None)
    etapas = [{'clave': c, 'nombre': n, 'ok': bool(ok), 'detalle': d, 'quien': q} for c, n, ok, d, q in lista]
    return {
        'nombre': os.path.basename(carpeta),
        'ruta': os.path.relpath(carpeta, RAIZ).replace('\\', '/'),
        'etapas': etapas,
        'hechas': sum(1 for e in etapas if e['ok']),
        'total': len(etapas),
        'siguiente': ({'clave': sig[0], 'nombre': sig[1], 'quien': sig[4]} if sig else None),
        'puertas': datos.get('puertas', {}),
        'sellos': {rol: {'fecha': s.get('fecha', ''), 'vigencia': EV.vigencia(carpeta, datos, rol)}
                   for rol, s in datos.get('sellos', {}).items()},
        'informes': {rol: estado_informe(carpeta, rol) for rol in INFORMES},
        'licencias': licencias_de(carpeta),
        'identidad': _identidad(carpeta),
    }


def lista_canales():
    salida = []
    for nombre in listar_canales():
        carpeta = os.path.join(CANALES, nombre)
        videos = videos_de(carpeta)
        salida.append({
            'nombre': nombre,
            'identidad': _identidad(os.path.join(carpeta, 'videos', '00-resumen')),   # la del canal, no la de un video con identidad propia
            'videos': [resumen_video(v) for v in videos],
        })
    return salida


def carpeta_video(canal, video):
    """Solo acepta nombres que existen en el listado (nunca rutas arbitrarias)."""
    if canal not in listar_canales():
        return None
    for v in videos_de(os.path.join(CANALES, canal)):
        if os.path.basename(v) == video:
            return v
    return None


def siguiente_seco(carpeta):
    rel = os.path.relpath(carpeta, RAIZ)
    p = subprocess.run([sys.executable, CANAL_PY, 'siguiente', rel, '--seco'], cwd=RAIZ, capture_output=True,
                       timeout=90, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    return {'salida': p.stdout.decode('utf-8', 'replace'), 'error': p.stderr.decode('utf-8', 'replace'), 'codigo': p.returncode}


def _catalogo(*partes):
    try:
        with open(os.path.join(HERR, *partes), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def opciones():
    """Lo que se puede elegir en la identidad, con el estado de cada animación."""
    voces = [{'id': v['id'], 'nombre': v.get('nombre', v['id'])} for v in _catalogo('voz', 'voces.json').get('voces', [])]
    anims = [{'id': a['id'], 'nombre': a.get('nombre', a['id']), 'estado': a.get('estado', '')}
             for a in _catalogo('montaje', 'catalogo', 'animaciones.json').get('animaciones', [])]
    return {'voces': voces, 'animaciones': anims, 'fuentes': list(FUENTES)}


def _correr(args, timeout=60):
    """Ejecuta un programa del proyecto (lista de argumentos, nunca por shell) y devuelve (código, salida)."""
    p = subprocess.run([sys.executable, *args], cwd=RAIZ, capture_output=True, timeout=timeout,
                       env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    return p.returncode, (p.stdout.decode('utf-8', 'replace') + p.stderr.decode('utf-8', 'replace')).strip()


def _rel(carpeta):
    return os.path.relpath(carpeta, RAIZ)


def identidad_canal_texto(canal):
    if canal not in listar_canales():
        raise ErrorPanel('canal no encontrado', 404)
    codigo, salida = _correr([IDENTIDAD_PY, 'resumen', canal])
    if codigo != 0:
        raise ErrorPanel(salida or 'no pude leer la identidad del canal', 500)
    return {'texto': salida}


def ideas_de(canal):
    """Ideas de video del canal: filas numeradas de la tabla de <canal>/estrategia/*ideas-de-video*.md.
    «usada» = ya hay un video que parte de ella (ver abajo)."""
    if canal not in listar_canales():
        raise ErrorPanel('canal no encontrado', 404)
    est = os.path.join(CANALES, canal, 'estrategia')
    arch = next((os.path.join(est, f) for f in sorted(os.listdir(est)) if 'ideas-de-video' in f and f.endswith('.md')), None) if os.path.isdir(est) else None
    if not arch:
        return {'ideas': [], 'archivo': None}
    ideas = []
    with open(arch, encoding='utf-8') as f:
        for linea in f:
            celdas = [re.sub(r'\*\*|`', '', c).strip() for c in linea.strip().strip('|').split('|')]
            if len(celdas) >= 8 and celdas[0].isdigit():
                ideas.append({'n': int(celdas[0]), 'semana': celdas[1], 'titulo': celdas[2], 'tipo': celdas[3], 'angulo': celdas[4],
                              'fuentes': celdas[5], 'visual': celdas[6], 'riesgo': celdas[7], 'usada': False})
    # Una idea está usada si algún video la declara en 01-guion/idea.md; los videos anteriores al panel (sin idea.md)
    # se emparejan por número, porque la tabla y esos videos comparten numeración.
    titulos = {i['titulo']: i for i in ideas}
    por_n = {i['n']: i for i in ideas}
    for v in videos_de(os.path.join(CANALES, canal)):
        try:
            with open(os.path.join(v, '01-guion', 'idea.md'), encoding='utf-8') as f:
                m = re.search(r'\*\*Pregunta del video:\*\*\s*(.+)', f.read())
            if m and m.group(1).strip() in titulos:
                titulos[m.group(1).strip()]['usada'] = True
        except OSError:
            m = re.match(r'(\d+)-', os.path.basename(v))
            if m and int(m.group(1)) in por_n:
                por_n[int(m.group(1))]['usada'] = True
    return {'ideas': ideas, 'archivo': os.path.relpath(arch, RAIZ).replace('\\', '/')}


def _guardar_idea(carpeta, idea, archivo):
    """Deja la idea elegida como punto de partida del video (01-guion/idea.md). No pisa nada."""
    destino = os.path.join(carpeta, '01-guion', 'idea.md')
    if os.path.exists(destino):
        return
    texto = ('# Idea de partida · %s\n\n> Copiada de [%s](%s) al crear el video desde el panel. El título es de trabajo: '
             'el final se decide con datos y siempre es propio (reglas 5 y 9).\n\n'
             '- **Pregunta del video:** %s\n- **Semana:** %s\n- **Tipo:** %s\n- **Ángulo propio / gancho:** %s\n'
             '- **Fuentes primarias:** %s\n- **Material visual:** %s\n- **Riesgo:** %s\n') % (
        idea['titulo'], archivo, os.path.relpath(os.path.join(RAIZ, archivo), os.path.dirname(destino)).replace('\\', '/'),
        idea['titulo'], idea['semana'], idea['tipo'], idea['angulo'], idea['fuentes'], idea['visual'], idea['riesgo'])
    with open(destino, 'w', encoding='utf-8') as f:
        f.write(texto)


def crear_video(cuerpo):
    canal = str(cuerpo.get('canal', ''))
    nombre = re.sub(r'\s+', ' ', str(cuerpo.get('nombre', ''))).strip()
    if canal not in listar_canales():
        raise ErrorPanel('canal no encontrado', 404)
    if not 3 <= len(nombre) <= 60 or NOMBRE_PROHIBIDO.search(nombre):
        raise ErrorPanel('El nombre debe tener entre 3 y 60 caracteres y no usar \\ / : * ? " < > |')
    idea = None
    if cuerpo.get('idea') not in (None, ''):
        catalogo = ideas_de(canal)
        idea = next((i for i in catalogo['ideas'] if i['n'] == cuerpo['idea']), None)
        if not idea:
            raise ErrorPanel('idea desconocida: %s' % cuerpo['idea'], 404)
        if idea['usada']:
            raise ErrorPanel('La idea %s ya tiene un video.' % idea['n'], 409)
    carpetas = videos_de(os.path.join(CANALES, canal))
    numeros = [int(m.group(1)) for m in (re.match(r'(\d+)-', os.path.basename(v)) for v in carpetas) if m]
    n = max(numeros or [0]) + 1
    codigo, salida = _correr([NUEVO_PY, canal, str(n), nombre])
    if codigo != 0:
        raise ErrorPanel(salida or 'no se pudo crear el video', 500)
    nuevos = [v for v in videos_de(os.path.join(CANALES, canal)) if os.path.basename(v).startswith('%02d-' % n)]
    if idea and nuevos:
        _guardar_idea(nuevos[0], idea, catalogo['archivo'])
    return {'video': os.path.basename(nuevos[0]) if nuevos else None, 'numero': n, 'salida': salida}


def fijar_identidad(carpeta, cuerpo):
    base = cuerpo.get('base')
    if base not in ('canal', 'propia'):
        raise ErrorPanel('base debe ser «canal» o «propia»')
    args = [IDENTIDAD_PY, 'video', _rel(carpeta), '--base', base]
    if base == 'propia':
        op = opciones()
        voz, anim, fuente = cuerpo.get('voz'), cuerpo.get('animacion'), cuerpo.get('fuente')
        if voz and voz not in [v['id'] for v in op['voces']]:
            raise ErrorPanel('voz desconocida: %s' % voz)
        if anim:
            est = next((a['estado'] for a in op['animaciones'] if a['id'] == anim), None)
            if est is None:
                raise ErrorPanel('animación desconocida: %s' % anim)
            if est not in ('disponible', 'parcial'):
                raise ErrorPanel('La animación «%s» está «%s»: primero hay que construirla.' % (anim, est))
        if fuente and fuente not in FUENTES:
            raise ErrorPanel('fuente desconocida: %s' % fuente)
        if not (voz or anim or fuente):
            raise ErrorPanel('Con identidad propia indica al menos una voz, una animación o una fuente.')
        for clave, valor in (('--voz', voz), ('--animacion', anim), ('--fuente', fuente)):
            if valor:
                args += [clave, valor]
    codigo, salida = _correr(args)
    if codigo != 0:
        raise ErrorPanel(salida or 'no se pudo guardar la identidad', 500)
    return {'salida': salida, 'video': resumen_video(carpeta)}


def aprobar_puerta(carpeta, cuerpo):
    puerta = cuerpo.get('puerta')
    if puerta not in PUERTAS:
        raise ErrorPanel('puerta debe ser una de: %s' % ', '.join(PUERTAS))
    codigo, salida = _correr([ESTADO_PY, _rel(carpeta), '--aprobar', puerta])
    if codigo != 0:
        raise ErrorPanel(salida or 'no se pudo aprobar', 500)
    return {'video': resumen_video(carpeta)}


def cambios_despues(carpeta, rol, desde):
    """¿Hay archivos que ese informe revisa y que cambiaron después de escribirse? (el informe quedó desactualizado).
    Solo se usa con el control final (mira todo el video salvo 02-revision, .estado y _archivo): los informes del guion se escriben
    ANTES de las correcciones y el sello ya detecta si el guion cambió después."""
    base = os.path.join(carpeta, '01-guion') if rol != 'auditor-final' else carpeta
    for raiz, dirs, archivos in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ('.estado', '02-revision', '_archivo', 'salida', 'cache')]
        for nombre in archivos:
            try:
                if os.path.getmtime(os.path.join(raiz, nombre)) > desde + 1:
                    return True
            except OSError:
                pass
    return False


def hallazgos_de(texto):
    """Los hallazgos numerados del informe (sección «## Hallazgos»), recortados: lo que hay que corregir, a la vista."""
    m = re.search(r'^##\s*Hallazgos[^\n]*\n(.*?)(?=^##\s|\Z)', texto, re.S | re.M)
    if not m:
        return []
    items = [re.sub(r'\s+', ' ', x).strip() for x in re.findall(r'^\s*\d+\.\s+(.*?)(?=^\s*\d+\.\s|\Z)', m.group(1), re.S | re.M)]
    return [i[:260] for i in items[:8]]


def estado_informe(carpeta, rol):
    """Qué dice el informe de un rol: {existe, veredicto: PASA|FALLA|''}. Busca el nombre estándar y, si no, «<rol>.md»
    (los agentes a veces lo nombran así). El veredicto es el de la línea «Veredicto:» o «Resultado:» de las primeras líneas."""
    for rel in (INFORMES[rol], '02-revision/%s.md' % rol):
        arch = os.path.join(carpeta, *rel.split('/'))
        try:
            with open(arch, encoding='utf-8') as f:
                contenido = f.read()
        except OSError:
            continue
        cabecera = contenido.splitlines()[:12]
        linea = next((x for x in cabecera if re.match(r'\s*(Veredicto|Resultado)\b', x, re.I)), '')
        veredicto = 'FALLA' if re.search(r'\bFALLA\b', linea) else 'PASA' if re.search(r'\bPASA\b', linea) else ''
        return {'existe': True, 'veredicto': veredicto, 'archivo': rel, 'texto': contenido.strip()[:3000], 'hallazgos': hallazgos_de(contenido),
                'obsoleto': rol == 'auditor-final' and cambios_despues(carpeta, rol, os.path.getmtime(arch))}
    return {'existe': False, 'veredicto': '', 'archivo': INFORMES[rol]}


def aceptar_licencia(carpeta, cuerpo):
    """Decisión del usuario: da por buena una fila 🔎 (licencia leída o inferida de la política general de la fuente) cuando YA existe su
    prueba guardada. Solo cambia la celda Estado de esa fila y deja constancia con la fecha. Sin prueba no hay aceptación (regla 3)."""
    codigo = str(cuerpo.get('codigo', ''))
    if not re.fullmatch(r'[A-Za-z0-9-]{1,10}', codigo):
        raise ErrorPanel('código de licencia no válido')
    arch = ruta(carpeta, F_LICENCIAS)
    with open(arch, encoding='utf-8', newline='') as f:
        texto = f.read()
    filas = {c: (e, cap) for c, _m, e, cap in filas_licencias(texto)}
    if codigo not in filas:
        raise ErrorPanel('No encuentro la fila %s en el registro.' % codigo, 404)
    estado, captura = filas[codigo]
    if '🔎' not in estado:
        raise ErrorPanel('Solo se pueden aceptar filas en 🔎 (licencia leída, pendiente de tu confirmación); %s está en «%s».' % (codigo, estado.strip()[:30]), 409)
    if ruta_evidencia(carpeta, captura) is None:
        raise ErrorPanel('A %s le falta la prueba guardada (ficha, captura o descarga en 05-licencias/). Guárdala primero: sin registro completo no se acepta (regla 3).' % codigo, 409)
    salida, hecho = [], False
    for linea in texto.split(chr(10)):
        celdas = [c.strip() for c in linea.strip().strip('|').split('|')]
        if not hecho and linea.lstrip().startswith('|') and celdas and re.sub(r'[*`]', '', celdas[0]) == codigo:
            CR = chr(13)
            fin = linea.rstrip(CR).rstrip()
            corte = fin[:-1].rfind('|') if fin.endswith('|') else -1
            if corte > 0:
                linea = fin[:corte + 1] + ' ✅ aceptada por ti el %s |' % datetime.date.today().isoformat() + (CR if linea.endswith(CR) else '')
                hecho = True
        salida.append(linea)
    if not hecho:
        raise ErrorPanel('No pude actualizar la fila %s.' % codigo, 500)
    with open(arch, 'w', encoding='utf-8', newline='') as f:
        f.write(chr(10).join(salida))
    return {'video': resumen_video(carpeta)}


def informe_pasa(carpeta, rol):
    """(ok, motivo): el informe del rol existe y su veredicto es PASA."""
    e = estado_informe(carpeta, rol)
    if not e['existe']:
        return False, 'No existe %s: ejecuta primero esa revisión.' % e['archivo']
    if e['veredicto'] != 'PASA':
        return False, 'El informe de %s no dice PASA: corrige y revisa de nuevo antes de sellar.' % rol
    return True, ''


def sellar_rol(carpeta, cuerpo):
    rol = cuerpo.get('rol')
    if rol not in INFORMES:
        raise ErrorPanel('rol debe ser uno de: %s' % ', '.join(INFORMES))
    ok, motivo = informe_pasa(carpeta, rol)
    if not ok:
        raise ErrorPanel(motivo, 409)
    codigo, salida = _correr([ESTADO_PY, _rel(carpeta), '--sellar', rol])
    if codigo != 0:
        raise ErrorPanel(salida or 'no se pudo sellar', 409)
    return {'video': resumen_video(carpeta)}


class Manejador(BaseHTTPRequestHandler):
    server_version = 'PanelCanal/1'

    def _enviar(self, codigo, cuerpo):
        datos = json.dumps(cuerpo, ensure_ascii=False).encode('utf-8')
        self.send_response(codigo)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(datos)))
        self.send_header('Cache-Control', 'no-store')
        self._cabeceras_cors()
        self.end_headers()
        self.wfile.write(datos)

    def _cabeceras_cors(self):
        origen = self.headers.get('Origin')
        if origen in ORIGENES:
            self.send_header('Access-Control-Allow-Origin', origen)
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Panel')
            self.send_header('Vary', 'Origin')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cabeceras_cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _partes(self):
        return [unquote(p) for p in urlparse(self.path).path.strip('/').split('/') if p]

    def _host_ok(self):
        return (self.headers.get('Host') or '').rsplit(':', 1)[0] in HOSTS

    def do_POST(self):
        """Acciones: solo desde el selector (Origin), con cabecera propia y JSON, y de una lista cerrada."""
        if not self._host_ok():
            return self._enviar(403, {'error': 'host no permitido'})
        if self.headers.get('Origin') not in ORIGENES or self.headers.get('X-Panel') != '1' \
                or not (self.headers.get('Content-Type') or '').startswith('application/json'):
            return self._enviar(403, {'error': 'origen no permitido'})
        try:
            largo = int(self.headers.get('Content-Length') or 0)
            if largo > 10_000:
                return self._enviar(413, {'error': 'cuerpo demasiado grande'})
            cuerpo = json.loads(self.rfile.read(largo) or b'{}')
            if not isinstance(cuerpo, dict):
                raise ErrorPanel('el cuerpo debe ser un objeto JSON')
            partes = self._partes()
            if partes == ['api', 'video']:
                return self._enviar(201, crear_video(cuerpo))
            if partes == ['api', 'trabajo', 'cancelar']:
                return self._enviar(200, {'cancelado': EJ.cancelar()})
            if len(partes) == 5 and partes[:2] == ['api', 'video'] and partes[4] in ('identidad', 'aprobar', 'sellar', 'ejecutar', 'licencia'):
                carpeta = carpeta_video(partes[2], partes[3])
                if not carpeta:
                    return self._enviar(404, {'error': 'video no encontrado'})
                if partes[4] == 'ejecutar':
                    return self._enviar(202, ejecutar_paso(carpeta, partes[2], cuerpo))
                accion = {'identidad': fijar_identidad, 'aprobar': aprobar_puerta, 'sellar': sellar_rol, 'licencia': aceptar_licencia}[partes[4]]
                return self._enviar(200, accion(carpeta, cuerpo))
            return self._enviar(404, {'error': 'ruta no encontrada'})
        except ErrorPanel as e:
            return self._enviar(e.codigo, {'error': str(e)})
        except ValueError:
            return self._enviar(400, {'error': 'JSON no válido'})
        except subprocess.TimeoutExpired:
            return self._enviar(504, {'error': 'el programa tardó demasiado'})
        except Exception as e:
            return self._enviar(500, {'error': '%s: %s' % (type(e).__name__, e)})

    def do_GET(self):
        if not self._host_ok():
            return self._enviar(403, {'error': 'host no permitido'})
        partes = self._partes()
        try:
            if partes == ['api', 'salud']:
                return self._enviar(200, {'ok': True})
            if partes == ['api', 'canales']:
                return self._enviar(200, lista_canales())
            if partes == ['api', 'opciones']:
                return self._enviar(200, opciones())
            if partes == ['api', 'pasos']:
                return self._enviar(200, pasos_publicos())
            if partes == ['api', 'trabajo']:
                try:
                    desde = max(0, int(parse_qs(urlparse(self.path).query).get('desde', ['0'])[0]))
                except ValueError:
                    desde = 0
                return self._enviar(200, EJ.estado(desde))
            if len(partes) == 4 and partes[:2] == ['api', 'canales'] and partes[3] == 'identidad':
                return self._enviar(200, identidad_canal_texto(partes[2]))
            if len(partes) == 4 and partes[:2] == ['api', 'canales'] and partes[3] == 'ideas':
                return self._enviar(200, ideas_de(partes[2]))
            if len(partes) in (4, 5) and partes[:2] == ['api', 'video']:
                carpeta = carpeta_video(partes[2], partes[3])
                if not carpeta:
                    return self._enviar(404, {'error': 'video no encontrado'})
                if len(partes) == 4:
                    return self._enviar(200, resumen_video(carpeta))
                if partes[4] == 'siguiente':
                    return self._enviar(200, siguiente_seco(carpeta))
                if partes[4] == 'comandos':
                    paso = parse_qs(urlparse(self.path).query).get('paso', [''])[0]
                    return self._enviar(200, comandos_de_paso(carpeta, partes[2], paso))
            return self._enviar(404, {'error': 'ruta no encontrada'})
        except ErrorPanel as e:
            return self._enviar(e.codigo, {'error': str(e)})
        except subprocess.TimeoutExpired:
            return self._enviar(504, {'error': 'canal.py tardó demasiado'})
        except Exception as e:   # el panel nunca debe caerse por un archivo raro
            return self._enviar(500, {'error': '%s: %s' % (type(e).__name__, e)})

    def log_message(self, formato, *args):
        sys.stderr.write('[panel] ' + formato % args + '\n')


class Servidor(ThreadingHTTPServer):
    # En Windows, SO_REUSEADDR deja que varios procesos escuchen en el mismo puerto y cada petición cae en uno distinto
    # (versiones viejas del servidor respondiendo junto a la nueva). Sin reutilización, el segundo arranque falla con aviso.
    allow_reuse_address = os.name != 'nt'


def principal():
    ap = argparse.ArgumentParser(description='Servidor local del panel')
    ap.add_argument('--puerto', type=int, default=PUERTO)
    a = ap.parse_args()
    try:
        srv = Servidor(('127.0.0.1', a.puerto), Manejador)
    except OSError:
        sys.exit('El puerto %d ya está en uso: probablemente ya hay un servidor del panel encendido. Ciérralo antes (o usa --puerto).' % a.puerto)
    print('Panel en http://127.0.0.1:%d  (Ctrl+C para parar)' % a.puerto)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    principal()
