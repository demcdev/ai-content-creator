#!/usr/bin/env python3
"""
Prueba del servidor del panel sin tocar tu proyecto: copia herramientas/ a una carpeta temporal, crea allí un canal de
prueba, arranca el servidor de esa copia y ejercita lecturas, acciones y rechazos.

  python herramientas/panel/probar-servidor.py        # sale 0 si todo pasa
"""
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
QUI = os.path.dirname(os.path.abspath(__file__))
HERR = os.path.dirname(QUI)
ORIGEN = 'http://localhost:5173'
PUERTO = 8791
fallos = []


def comprobar(nombre, condicion, detalle=''):
    print(('OK    ' if condicion else 'FALLA ') + nombre + ('' if condicion else '  -> ' + str(detalle)))
    if not condicion:
        fallos.append(nombre)


def pedir(metodo, ruta, cuerpo=None, cabeceras=None):
    c = http.client.HTTPConnection('127.0.0.1', PUERTO, timeout=90)
    h = dict(cabeceras or {})
    datos = None
    if cuerpo is not None:
        datos = json.dumps(cuerpo).encode('utf-8')
        h.setdefault('Content-Type', 'application/json')
    c.request(metodo, ruta, body=datos, headers=h)
    r = c.getresponse()
    texto = r.read().decode('utf-8')
    c.close()
    try:
        return r.status, json.loads(texto)
    except ValueError:
        return r.status, texto


def accion(ruta, cuerpo):
    return pedir('POST', ruta, cuerpo, {'Origin': ORIGEN, 'X-Panel': '1'})


FALSO_PY = r'''
import json, os, sys, time
prompt = sys.stdin.read()
open(os.environ['FALSO_LOG'], 'w', encoding='utf-8').write(json.dumps(sys.argv[1:]))
open(os.environ['FALSO_PROMPT'], 'w', encoding='utf-8').write(prompt)
open(os.environ['FALSO_ENV'], 'w', encoding='utf-8').write(json.dumps({k: (k in os.environ) for k in ('AWS_ACCESS_KEY_ID', 'GOOGLE_TTS_API_KEY', 'CLAUDECODE')}))
try:
    modo = open(os.environ['FALSO_MODO'], encoding='utf-8').read().strip()
except OSError:
    modo = 'ok'
def emitir(o):
    print(json.dumps(o), flush=True)
emitir({'type': 'system', 'subtype': 'init', 'session_id': 'sesion-falsa'})
emitir({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'Buscando la fuente primaria'},
        {'type': 'tool_use', 'name': 'WebSearch', 'input': {'query': 'Event Horizon Telescope M87 2019'}}]}})
if modo == 'lento':
    time.sleep(60)
if modo == 'error':
    emitir({'type': 'result', 'subtype': 'error_during_execution', 'is_error': True, 'result': 'Se acabo el saldo', 'total_cost_usd': 0.0, 'session_id': 'sesion-falsa'})
    sys.exit(1)
emitir({'type': 'user', 'message': {'content': [{'type': 'tool_result', 'is_error': True, 'content': 'permiso negado'}]}})
emitir({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'Listo: 5 cifras', 'total_cost_usd': 0.0123,
        'session_id': 'sesion-falsa', 'permission_denials': [{'tool_name': 'Bash', 'tool_input': {'command': 'git commit'}}]})
'''


def _crear_claude_falso(tmp):
    """Un «claude» de mentira con la misma salida (stream-json) para probar el ejecutor sin gastar nada."""
    py = os.path.join(tmp, 'claude_falso.py')
    with open(py, 'w', encoding='utf-8') as f:
        f.write(FALSO_PY)
    if os.name == 'nt':
        exe = os.path.join(tmp, 'claude-falso.cmd')
        with open(exe, 'w', encoding='utf-8') as f:
            f.write('@echo off\r\n"%s" "%s" %%*\r\n' % (sys.executable, py))
    else:
        exe = os.path.join(tmp, 'claude-falso.sh')
        with open(exe, 'w', encoding='utf-8') as f:
            f.write('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (sys.executable, py))
        os.chmod(exe, 0o755)
    return exe


def esperar_trabajo(estados, segundos=30):
    fin = time.time() + segundos
    while time.time() < fin:
        d = pedir('GET', '/api/trabajo')[1]
        if d.get('estado') in estados:
            return d
        time.sleep(0.3)
    return pedir('GET', '/api/trabajo')[1]


def principal():
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding='utf-8', errors='replace')
    tmp = tempfile.mkdtemp(prefix='panel-prueba-')
    srv = None
    try:
        shutil.copytree(HERR, os.path.join(tmp, 'herramientas'), ignore=shutil.ignore_patterns('__pycache__', 'node_modules'))
        canal = os.path.join(tmp, '02-canales', 'canal-prueba')
        os.makedirs(os.path.join(canal, 'identidad'))
        os.makedirs(os.path.join(canal, 'videos'))
        with open(os.path.join(canal, 'identidad', 'identidad.json'), 'w', encoding='utf-8') as f:
            json.dump({'nombre': 'PRUEBA', 'voz': 'polly-raul', 'animacion': 'espacial', 'fuente': 'inter'}, f)
        os.makedirs(os.path.join(canal, 'estrategia'))
        with open(os.path.join(canal, 'estrategia', '01-ideas-de-video.md'), 'w', encoding='utf-8') as f:
            f.write('# Ideas\n\n| # | Semana | Pregunta | Tipo | Angulo | Fuentes | Material | Riesgo |\n|---|---|---|---|---|---|---|---|\n'
                    '| 1 | 1 | **Idea uno** | Espacio | Angulo uno | NASA | Imagenes | Bajo |\n'
                    '| 2 | 2 | **Idea dos: subtitulo** | Cosmologia | Angulo dos | ESA | Graficos | Medio |\n')
        falso = _crear_claude_falso(tmp)
        entorno = {**os.environ, 'CLAUDE_BIN': falso, 'FALSO_LOG': os.path.join(tmp, 'argv.json'),
                   'FALSO_MODO': os.path.join(tmp, 'modo.txt'), 'FALSO_PROMPT': os.path.join(tmp, 'prompt.txt'),
                   'FALSO_ENV': os.path.join(tmp, 'entorno.json'), 'AWS_ACCESS_KEY_ID': 'valor-falso-de-prueba', 'CLAUDECODE': '1'}
        srv = subprocess.Popen([sys.executable, os.path.join(tmp, 'herramientas', 'panel', 'servidor.py'), '--puerto', str(PUERTO)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=tmp, env=entorno)
        for _ in range(50):
            try:
                if pedir('GET', '/api/salud')[0] == 200:
                    break
            except OSError:
                time.sleep(0.2)

        # lectura
        s, d = pedir('GET', '/api/canales')
        comprobar('lista canales (vacío de videos)', s == 200 and d[0]['nombre'] == 'canal-prueba' and d[0]['videos'] == [], d)
        s, d = pedir('GET', '/api/opciones')
        comprobar('opciones traen voces y animaciones con estado', s == 200 and d['voces'] and any(a['estado'] for a in d['animaciones']), d)
        s, d = pedir('GET', '/api/canales/canal-prueba/identidad')
        comprobar('frase de identidad del canal', s == 200 and 'voz' in d['texto'].lower(), d)

        s, d = pedir('GET', '/api/canales/canal-prueba/ideas')
        comprobar('lista las ideas de la tabla', s == 200 and [i['n'] for i in d['ideas']] == [1, 2] and d['ideas'][1]['titulo'] == 'Idea dos: subtitulo'
                  and not any(i['usada'] for i in d['ideas']), d)
        s, d = pedir('GET', '/api/canales/no-existe/ideas')
        comprobar('ideas de un canal inexistente: 404', s == 404, d)

        # rechazos de seguridad
        s, _ = pedir('POST', '/api/video', {'canal': 'canal-prueba', 'nombre': 'Hola'}, {'Origin': 'http://evil.com', 'X-Panel': '1'})
        comprobar('POST con otro Origin se rechaza', s == 403, s)
        s, _ = pedir('POST', '/api/video', {'canal': 'canal-prueba', 'nombre': 'Hola'}, {'Origin': ORIGEN})
        comprobar('POST sin X-Panel se rechaza', s == 403, s)
        s, _ = pedir('POST', '/api/video', {'canal': 'canal-prueba', 'nombre': 'Hola'}, {'X-Panel': '1'})
        comprobar('POST sin Origin se rechaza', s == 403, s)
        s, _ = pedir('GET', '/api/salud', None, {'Host': 'evil.com'})
        comprobar('Host ajeno se rechaza', s == 403, s)

        # crear video
        s, d = accion('/api/video', {'canal': 'canal-prueba', 'nombre': 'Mi primer video'})
        comprobar('crea el video 01', s == 201 and d['video'] == '01-mi-primer-video', d)
        s, d = accion('/api/video', {'canal': 'canal-prueba', 'nombre': 'Idea dos', 'idea': 99})
        comprobar('idea desconocida se rechaza', s == 404, d)
        s, d = pedir('GET', '/api/canales/canal-prueba/ideas')
        comprobar('la idea 1 queda marcada como usada', [i['usada'] for i in d['ideas']] == [True, False], d)
        s, d = accion('/api/video', {'canal': 'canal-prueba', 'nombre': 'Segundo video', 'idea': 2})
        comprobar('el siguiente es el 02', s == 201 and d['numero'] == 2, d)
        idea_md = os.path.join(canal, 'videos', d['video'] or 'x', '01-guion', 'idea.md')
        texto_idea = open(idea_md, encoding='utf-8').read() if os.path.exists(idea_md) else ''
        comprobar('con idea deja 01-guion/idea.md', 'Angulo dos' in texto_idea)
        enlace = re.search(r'\]\(([^)]+\.md)\)', texto_idea)
        comprobar('el enlace de idea.md apunta a un archivo que existe',
                  bool(enlace) and os.path.exists(os.path.normpath(os.path.join(os.path.dirname(idea_md), enlace.group(1)))), enlace and enlace.group(1))
        s, d = pedir('GET', '/api/canales/canal-prueba/ideas')
        comprobar('la idea 2 queda usada por su idea.md', [i['usada'] for i in d['ideas']] == [True, True], d)
        s, d = accion('/api/video', {'canal': 'canal-prueba', 'nombre': 'Otra vez', 'idea': 2})
        comprobar('una idea ya usada se rechaza (409)', s == 409, d)
        s, d = accion('/api/video', {'canal': 'canal-prueba', 'nombre': 'a/b'})
        comprobar('nombre con caracteres prohibidos se rechaza', s == 400, d)
        s, d = accion('/api/video', {'canal': '../..', 'nombre': 'Valido'})
        comprobar('canal inexistente se rechaza', s == 404, d)
        v = '01-mi-primer-video'

        # identidad
        s, d = accion('/api/video/canal-prueba/%s/identidad' % v, {'base': 'canal'})
        comprobar('identidad base canal', s == 200 and d['video']['identidad']['base'] == 'canal', d)
        s, d = accion('/api/video/canal-prueba/%s/identidad' % v, {'base': 'propia', 'animacion': 'carboncillo'})
        comprobar('animación por construir se rechaza', s == 400, d)
        s, d = accion('/api/video/canal-prueba/%s/identidad' % v, {'base': 'propia'})
        comprobar('propia sin cambios se rechaza', s == 400, d)
        s, d = accion('/api/video/canal-prueba/%s/identidad' % v, {'base': 'propia', 'fuente': 'montserrat'})
        comprobar('identidad propia con fuente', s == 200 and d['video']['identidad']['fuente'] == 'montserrat', d)

        # puertas y sellos
        s, d = accion('/api/video/canal-prueba/%s/aprobar' % v, {'puerta': 'idea'})
        comprobar('aprueba la puerta idea', s == 200 and 'idea' in d['video']['puertas'], d)
        s, d = accion('/api/video/canal-prueba/%s/aprobar' % v, {'puerta': 'otra'})
        comprobar('puerta desconocida se rechaza', s == 400, d)
        s, d = accion('/api/video/canal-prueba/%s/sellar' % v, {'rol': 'auditor-guion'})
        comprobar('sellar sin informe se rechaza (409)', s == 409, d)
        rev = os.path.join(canal, 'videos', v, '02-revision')
        with open(os.path.join(rev, 'informe-auditor-guion.md'), 'w', encoding='utf-8') as f:
            f.write('# Informe\n\nVeredicto: **FALLA** (2 errores)\n')
        s, d = accion('/api/video/canal-prueba/%s/sellar' % v, {'rol': 'auditor-guion'})
        comprobar('sellar con informe FALLA se rechaza (409)', s == 409, d)
        with open(os.path.join(rev, 'informe-auditor-guion.md'), 'w', encoding='utf-8') as f:
            f.write('# Informe\n\nVeredicto: **PASA con observaciones**\n')
        with open(os.path.join(canal, 'videos', v, '01-guion', 'guion.md'), 'a', encoding='utf-8') as f:
            f.write('x' * 50)
        s, d = accion('/api/video/canal-prueba/%s/sellar' % v, {'rol': 'auditor-guion'})
        comprobar('sellar con informe PASA funciona', s == 200 and d['video']['sellos'].get('auditor-guion', {}).get('vigencia') == 'vigente', d)
        s, d = accion('/api/video/canal-prueba/%s/sellar' % v, {'rol': 'root'})
        comprobar('rol desconocido se rechaza', s == 400, d)
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        comprobar('el video informa el estado de los informes', d['informes']['auditor-guion']['veredicto'] == 'PASA'
                  and d['informes']['verificador']['existe'] is False and d['informes']['auditor-final']['existe'] is False, d['informes'])
        with open(os.path.join(rev, 'verificador.md'), 'w', encoding='utf-8') as f:     # nombre alterno que a veces usan los agentes
            f.write('Veredicto: PASA\n\nESTADO del script: 5 cifras\n')
        s, d = accion('/api/video/canal-prueba/%s/sellar' % v, {'rol': 'verificador'})
        comprobar('acepta el informe con el nombre «<rol>.md» y sella', s == 200 and d['video']['sellos'].get('verificador', {}).get('vigencia') == 'vigente'
                  and d['video']['informes']['verificador']['veredicto'] == 'PASA', d)
        s, d = accion('/api/video/canal-prueba/%s/sellar' % v, {'rol': 'auditor-final'})
        comprobar('el sello final también exige su informe (409)', s == 409, d)

        s, d = pedir('GET', '/api/canales')
        comprobar('la lista ya muestra los 2 videos', len(d[0]['videos']) == 2, d)

        # registro de licencias: el estado se cuenta desde la tabla (sin tabla manual «0. Resumen de estado»)
        NL = chr(10)
        reg_lic = os.path.join(canal, 'videos', v, '05-licencias', 'registro-de-licencias.md')
        encabezado = NL.join(['# Registro', '', '| Código | Material | Fuente / ficha | Licencia | Captura | Estado |', '|---|---|---|---|---|---|', ''])
        filas_lic = ['| **L01** | Imagen del anillo | https://x | CC BY | `a.png` | ✅ |', '| **L02** | Voz Polly | https://y | AWS | — | 🔎 falta captura |',
                     '| **L03** | Música | Studio | YT | — | ⏳ pendiente |', '| **L04** | Foto descartada | z | — | — | ❌ |']
        with open(reg_lic, 'w', encoding='utf-8') as f:
            f.write(encabezado + NL.join(filas_lic) + NL)
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        lic = {x['codigo']: x['estado'] for x in d['licencias']}
        comprobar('licencias: las filas salen con su estado (lista, captura, pendiente, descartada)', lic == {'L01': 'lista', 'L02': 'captura', 'L03': 'pendiente', 'L04': 'descartada'}, d['licencias'])
        et = next(e for e in d['etapas'] if e['clave'] == 'licencias')
        comprobar('licencias: 1 de 3 listas (la descartada no cuenta) y el paso sigue pendiente', et['detalle'] == '1 de 3 listas' and not et['ok'], et)
        with open(reg_lic, 'w', encoding='utf-8') as f:
            f.write(encabezado + NL.join(['| **L01** | Imagen | https://x | CC BY | `a.png` | ✅ |', '| **L02** | Voz | https://y | AWS | `b.png` | ✅ |', '| **L03** | Foto descartada | z | — | — | ❌ |']) + NL)
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        et = next(e for e in d['etapas'] if e['clave'] == 'licencias')
        comprobar('licencias: con todas las filas ✅ el paso queda listo', et['ok'] and et['detalle'] == '2 de 2 listas', et)

        # aceptar una licencia: decisión del usuario, solo con la prueba guardada
        fichas = os.path.join(canal, 'videos', v, '05-licencias', 'fichas')
        os.makedirs(fichas, exist_ok=True)
        with open(os.path.join(fichas, 'l02-politica-2026-10-18.txt'), 'w', encoding='utf-8') as f:
            f.write('URL: https://y' + NL + 'Fecha: 2026-10-18' + NL + 'La política dice CC BY 4.0.' + NL)
        with open(reg_lic, 'w', encoding='utf-8', newline='') as f:
            f.write(encabezado + NL.join([
                '| **L01** | Imagen sin prueba | https://x | inferida de la política general | ☐ Falta: capturar la política | 🔎 |',
                '| **L02** | Imagen con ficha | https://y | inferida de la política general | `fichas/l02-politica-2026-10-18.txt` | 🔎 |',
                '| **L03** | Ya lista | https://z | CC BY | `fichas/l02-politica-2026-10-18.txt` | ✅ |']) + NL)
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        ev = {x['codigo']: x['evidencia'] for x in d['licencias']}
        comprobar('licencias: la fila indica si su prueba existe', ev == {'L01': False, 'L02': True, 'L03': True}, d['licencias'])
        ruta_lic = '/api/video/canal-prueba/%s/licencia' % v
        s, d = accion(ruta_lic, {'codigo': 'L01'})
        comprobar('aceptar una licencia sin su prueba guardada se rechaza (409)', s == 409 and 'prueba' in d['error'], d)
        s, d = accion(ruta_lic, {'codigo': 'L03'})
        comprobar('aceptar una fila que ya está ✅ se rechaza (409)', s == 409, d)
        s, d = accion(ruta_lic, {'codigo': 'L99'})
        comprobar('aceptar una fila inexistente: 404', s == 404, d)
        s, d = accion(ruta_lic, {'codigo': '../../x'})
        comprobar('código de licencia inválido: 400', s == 400, d)
        s, d = accion(ruta_lic, {'codigo': 'L02'})
        lic = {x['codigo']: x['estado'] for x in d['video']['licencias']} if s == 200 else {}
        comprobar('con la prueba guardada, aceptar la deja ✅ y las demás filas no cambian', s == 200 and lic == {'L01': 'captura', 'L02': 'lista', 'L03': 'lista'}, (s, d))
        texto_reg = open(reg_lic, encoding='utf-8').read()
        comprobar('queda constancia con la fecha en el registro', 'aceptada por ti el ' in texto_reg and '| **L01** | Imagen sin prueba' in texto_reg and texto_reg.count('aceptada por ti') == 1, texto_reg)
        s, d = pedir('POST', ruta_lic, {'codigo': 'L01'}, {'Origin': 'http://evil.com', 'X-Panel': '1'})
        comprobar('aceptar licencias desde otro Origin se rechaza', s == 403, s)

        # informe del control final desactualizado: cambió algo del video después de escribirse
        inf_final = os.path.join(canal, 'videos', v, '02-revision', 'informe-auditor-final.md')
        with open(inf_final, 'w', encoding='utf-8') as f:
            f.write('Veredicto: FALLA' + NL + NL + 'La ficha de publicación está vacía.' + NL)
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        comprobar('un informe recién escrito no figura como desactualizado', d['informes']['auditor-final']['veredicto'] == 'FALLA' and d['informes']['auditor-final']['obsoleto'] is False, d['informes']['auditor-final'])
        time.sleep(2.2)
        with open(os.path.join(canal, 'videos', v, '09-publicacion', 'capitulos-y-descripcion.md'), 'a', encoding='utf-8') as f:
            f.write('Descripción nueva.' + NL)
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        comprobar('si cambia el video después del informe, queda desactualizado', d['informes']['auditor-final']['obsoleto'] is True, d['informes']['auditor-final'])
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        comprobar('los informes del guion nunca se marcan desactualizados (se escriben antes de las correcciones)', d['informes']['auditor-guion']['obsoleto'] is False, d['informes']['auditor-guion'])
        os.remove(inf_final)

        # hallazgos del informe a la vista
        with open(inf_final, 'w', encoding='utf-8') as f:
            f.write(NL.join(['Veredicto: FALLA', '', '## Hallazgos', '1. Subtítulos · el .srt está vacío → ejecutar canal.py alinear',
                             '2. Música · la descripción acredita pistas que el render no lleva', '', '## Correcto', '- todo lo demás']) + NL)
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        h = d['informes']['auditor-final']['hallazgos']
        comprobar('el informe expone sus hallazgos numerados (y solo ellos)', len(h) == 2 and h[0].startswith('Subtítulos') and h[1].startswith('Música'), h)
        os.remove(inf_final)

        # montaje: escenas «placeholder» con el script de la plantilla sin tocar = montaje sin hacer
        esc_json = os.path.join(canal, 'videos', v, '06-montaje', 'escenas.json')
        with open(esc_json, 'w', encoding='utf-8') as f:
            json.dump({'escenas': [{'id': 'E01', 'tipo': 'placeholder'}, {'id': 'E02', 'tipo': 'placeholder'}, {'id': 'E03', 'tipo': 'cifra'}]}, f)
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        mont = next(e for e in d['etapas'] if e['clave'] == 'montaje')
        comprobar('montaje: con escenas placeholder y el script de la plantilla no se da por hecho', not mont['ok'] and '2 de 3 escenas sin diseñar' in mont['detalle'], mont)
        with open(esc_json, 'w', encoding='utf-8') as f:
            json.dump({'escenas': [{'id': 'E01', 'tipo': 'cifra'}, {'id': 'E02', 'tipo': 'barras'}]}, f)
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        mont = next(e for e in d['etapas'] if e['clave'] == 'montaje')
        comprobar('montaje: con todas las escenas diseñadas queda hecho', mont['ok'], mont)
        with open(os.path.join(canal, 'videos', v, '06-montaje', 'video.py'), 'a', encoding='utf-8') as f:
            f.write(NL + '# script propio' + NL)
        with open(esc_json, 'w', encoding='utf-8') as f:
            json.dump({'escenas': [{'id': 'E01', 'tipo': 'placeholder'}]}, f)
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        mont = next(e for e in d['etapas'] if e['clave'] == 'montaje')
        comprobar('montaje: con un video.py propio no se cuentan las placeholder (el script las resuelve)', mont['ok'], mont)

        # video final y subtítulos: un .mp4 con escenas sin diseñar o un .srt vacío no cuentan
        entreg = os.path.join(canal, 'videos', v, '08-entregables')
        os.makedirs(entreg, exist_ok=True)
        with open(os.path.join(entreg, 'v.mp4'), 'wb') as f:
            f.write(b'x' * 300)
        open(os.path.join(entreg, 'v.srt'), 'w').close()
        with open(esc_json, 'w', encoding='utf-8') as f:
            json.dump({'escenas': [{'id': 'E01', 'tipo': 'placeholder'}, {'id': 'E02', 'tipo': 'cifra'}]}, f)
        plantilla_py = os.path.join(HERR, 'montaje', 'plantillas', 'plantilla_video.py')
        guardado = open(os.path.join(canal, 'videos', v, '06-montaje', 'video.py'), 'rb').read()
        shutil.copy(plantilla_py, os.path.join(canal, 'videos', v, '06-montaje', 'video.py'))
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        et = {e['clave']: e for e in d['etapas']}
        comprobar('video final: un .mp4 con escenas sin diseñar no se da por hecho', not et['video']['ok'] and 'sin terminar' in et['video']['detalle'], et['video'])
        comprobar('subtítulos: un .srt vacío no se da por hecho', not et['subtitulos']['ok'] and 'vacío' in et['subtitulos']['detalle'], et['subtitulos'])
        with open(esc_json, 'w', encoding='utf-8') as f:
            json.dump({'escenas': [{'id': 'E01', 'tipo': 'cifra'}]}, f)
        with open(os.path.join(entreg, 'v.srt'), 'w', encoding='utf-8') as f:
            f.write('1' + NL + '00:00:00,000 --> 00:00:02,000' + NL + 'texto ' * 50 + NL)
        s, d = pedir('GET', '/api/video/canal-prueba/%s' % v)
        et = {e['clave']: e for e in d['etapas']}
        comprobar('video final y subtítulos: con escenas diseñadas y .srt con contenido sí cuentan', et['video']['ok'] and et['subtitulos']['ok'], (et['video'], et['subtitulos']))
        with open(os.path.join(canal, 'videos', v, '06-montaje', 'video.py'), 'wb') as f:
            f.write(guardado)
        shutil.rmtree(entreg)

        # pasos.json: ningún permiso se sale de lo previsto
        pj = json.load(open(os.path.join(HERR, 'panel', 'pasos.json'), encoding='utf-8'))['pasos']
        libres = {'Read', 'Glob', 'Grep', 'WebSearch', 'WebFetch', 'Agent'}
        malos = []
        for clave, paso in pj.items():
            ej = paso.get('ejecutable')
            if not ej:
                continue
            if ej.get('tipo') == 'comandos':     # sin IA: solo python o node dentro de herramientas/
                cmds = ej.get('comandos', []) if ej.get('origen') != 'voz' else []
                if not ej.get('permisos') or any(c.split()[0] not in ('python', 'node') or not c.split()[1].startswith('herramientas/') or '..' in c for c in cmds):
                    malos.append((clave, 'comando fuera de herramientas/ o sin texto de permisos'))
                continue
            for r in ej['permitidas']:
                bien = (r in libres or (r.startswith('Skill(') and r.endswith(')'))
                        or (r.startswith('Edit(/02-canales/{canal}/videos/{video}/') and r.endswith(')'))
                        or (r.startswith('Bash(python herramientas/') and r.endswith(')')))
                if not bien or any(x in r for x in ('sellar', 'aprobar', 'git ', '--escribir')):
                    malos.append((clave, r))
            if not any(r.startswith('Edit(') for r in ej['permitidas']) or 'Bash(git *)' not in ej.get('prohibidas', []) or not ej.get('permisos'):
                malos.append((clave, 'falta Edit, prohibir git o el texto de permisos'))
        comprobar('pasos.json: permisos dentro de lo previsto (Edit acotado al video, sin sellar/aprobar/git)', not malos, malos)
        comprobar('pasos.json: hay pasos de IA ejecutables', {'investigacion', 'guion', 'rev-guion', 'escaleta', 'planilla', 'miniaturas', 'licencias', 'montaje', 'rev-final', 'descripcion'} <= {k for k, v in pj.items() if v.get('ejecutable')})

        pm = pj['montaje']['ejecutable']['permitidas']
        editables = sorted(r for r in pm if r.startswith('Edit('))
        comprobar('montaje: solo edita el texto de subtítulos, la escaleta y montaje.json de ese video, y no puede renderizar ni sellar',
                  editables == ['Edit(/02-canales/{canal}/videos/{video}/01-guion/texto-para-subtitulos.txt)', 'Edit(/02-canales/{canal}/videos/{video}/03-escaleta/escaleta-audiovisual.md)', 'Edit(/02-canales/{canal}/videos/{video}/06-montaje/montaje.json)']
                  and 'Bash(python herramientas/canal/canal.py montar * --verificar)' in pm
                  and not any(r.endswith('montar *)') or 'WebFetch' in r or 'WebSearch' in r for r in pm), pm)
        # ejecutar con Claude Code (con un «claude» falso)
        v2 = '02-segundo-video'
        s, d = pedir('GET', '/api/pasos')
        comprobar('pasos: investigación ejecutable, métricas no', s == 200 and d['investigacion']['ejecutable'] and not d['metricas']['ejecutable']
                  and 'permitidas' not in json.dumps(d), d)
        comprobar('pasos: la instrucción trae marcadores sin rellenar', '{ref}' in d['investigacion']['instruccion'])
        s, d = accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'metricas'})
        comprobar('un paso no ejecutable se rechaza (400)', s == 400, d)
        s, d = accion('/api/video/canal-prueba/%s/ejecutar' % v2, {'paso': 'investigacion'})
        comprobar('un paso que no es el actual se rechaza (409)', s == 409, d)
        s, d = accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion; rm -rf /'})
        comprobar('un paso inventado se rechaza', s == 400, d)

        s, d = accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion'})
        comprobar('ejecutar investigación arranca (202)', s == 202 and d['estado'] == 'corriendo', d)
        t = esperar_trabajo(('terminado', 'error', 'cancelado'))
        tipos = [e['t'] for e in t.get('eventos', [])]
        comprobar('termina bien con costo y sesión', t.get('estado') == 'terminado' and t.get('costo') == 0.0123 and t.get('sesion') == 'sesion-falsa', t)
        comprobar('el registro trae texto, herramienta, aviso y fin', all(x in tipos for x in ('texto', 'herramienta', 'aviso', 'fin')), tipos)
        comprobar('muestra los permisos negados', any('Permiso negado' in e['texto'] for e in t.get('eventos', [])), t.get('eventos'))
        argv = json.load(open(os.path.join(tmp, 'argv.json'), encoding='utf-8'))
        comprobar('usa dontAsk, sin MCP y salida stream-json', all(x in argv for x in ('-p', 'dontAsk', '--strict-mcp-config', 'stream-json')), argv)
        perm = argv[argv.index('--allowedTools') + 1:]
        esperado = 'Edit(/02-canales/canal-prueba/videos/%s/01-guion/verificacion-de-cifras.md)' % v
        comprobar('permisos mínimos: edita solo la tabla de cifras de ese video', esperado in perm and not any(p in ('Edit', 'Write', 'Bash') for p in perm), perm)
        comprobar('prohíbe git', 'Bash(git *)' in argv[argv.index('--disallowedTools') + 1:], argv)
        entorno_ia = json.load(open(os.path.join(tmp, 'entorno.json'), encoding='utf-8'))
        comprobar('Claude Code NO recibe las claves de voz ni CLAUDECODE (aunque el servidor las tenga)', entorno_ia == {'AWS_ACCESS_KEY_ID': False, 'GOOGLE_TTS_API_KEY': False, 'CLAUDECODE': False}, entorno_ia)
        prompt = open(os.path.join(tmp, 'prompt.txt'), encoding='utf-8').read()
        comprobar('la instrucción llega rellenada por stdin', 'canal-prueba/1' in prompt and '{ref}' not in prompt and '{carpeta}' not in prompt and '{hoy}' not in prompt, prompt[:200])
        comprobar('deja el historial en .estado/ejecuciones', bool(t.get('registro')) and os.path.exists(os.path.join(tmp, *t['registro'].split('/'))), t.get('registro'))
        s, d = pedir('GET', '/api/trabajo?desde=%d' % t['n'])
        comprobar('desde=N devuelve solo lo nuevo', s == 200 and d['eventos'] == [] and d['n'] == t['n'], d)

        # cancelar y un solo trabajo a la vez
        open(os.path.join(tmp, 'modo.txt'), 'w').write('lento')
        s, d = accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion'})
        comprobar('segundo trabajo arranca', s == 202, d)
        s, d2 = accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion'})
        comprobar('con uno en curso, otro se rechaza (409)', s == 409, d2)
        s, d2 = accion('/api/trabajo/cancelar', {})
        comprobar('cancelar responde que canceló', s == 200 and d2.get('cancelado') is True, d2)
        t = esperar_trabajo(('cancelado', 'terminado', 'error'), 15)
        comprobar('queda cancelado', t.get('estado') == 'cancelado', t)
        s, d2 = accion('/api/trabajo/cancelar', {})
        comprobar('cancelar sin nada en curso no falla', s == 200 and d2.get('cancelado') is False, d2)

        open(os.path.join(tmp, 'modo.txt'), 'w').write('error')
        accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion'})
        t = esperar_trabajo(('terminado', 'error', 'cancelado'))
        comprobar('un fallo de Claude Code queda como error con su motivo', t.get('estado') == 'error' and 'saldo' in t.get('motivo', ''), t)

        s, _ = pedir('POST', '/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion'}, {'Origin': 'http://evil.com', 'X-Panel': '1'})
        comprobar('ejecutar desde otro Origin se rechaza', s == 403, s)

        # pasos de tipo «comandos» (sin IA): se redefine «investigacion» en la copia temporal con un programa de prueba
        with open(os.path.join(tmp, 'herramientas', 'panel', 'eco-prueba.py'), 'w', encoding='utf-8') as f:
            f.write(chr(10).join([
                'import sys, time',
                'm = sys.argv[1]',
                'print(m, flush=True)',
                "if m == 'fail':",
                "    print('boom', flush=True); sys.exit(3)",
                "if m == 'env':",
                "    import os; print(m, 'AWS_ACCESS_KEY_ID' in os.environ, flush=True)",
                "if m == 'lento':",
                '    time.sleep(60)',
            ]) + chr(10))
        pj_tmp = os.path.join(tmp, 'herramientas', 'panel', 'pasos.json')
        base_pasos = json.load(open(pj_tmp, encoding='utf-8'))

        def definir(comandos, claves=(), origen=None):
            ej = {'tipo': 'comandos', 'minutos': 1, 'permisos': 'prueba', 'comandos': list(comandos), 'claves_env': list(claves)}
            if origen:
                ej['origen'] = origen
            base_pasos['pasos']['investigacion']['ejecutable'] = ej
            json.dump(base_pasos, open(pj_tmp, 'w', encoding='utf-8'), ensure_ascii=False)

        ruta_cmd = '/api/video/canal-prueba/%s/comandos?paso=investigacion' % v
        definir(['python herramientas/panel/eco-prueba.py ok', 'python herramientas/panel/eco-prueba.py ok2'], ['CLAVE_PRUEBA_FALTA'])
        s, d = pedir('GET', ruta_cmd)
        comprobar('comandos: lista lo que ejecutaría y las claves que faltan', s == 200 and len(d['comandos']) == 2 and d['faltan'] == ['CLAVE_PRUEBA_FALTA']
                  and d['comandos'][0] == 'python herramientas/panel/eco-prueba.py ok', d)
        s, d = pedir('GET', '/api/pasos')
        comprobar('pasos: el tipo de cada paso (comandos / ia)', d['investigacion']['tipo'] == 'comandos' and d['guion']['tipo'] == 'ia', d)
        s, d = accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion'})
        comprobar('sin las variables de entorno no ejecuta (409) y dice cuáles faltan', s == 409 and 'CLAVE_PRUEBA_FALTA' in d['error'], d)

        definir(['python herramientas/panel/eco-prueba.py ok', 'python herramientas/panel/eco-prueba.py ok2'])
        s, d = accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion'})
        comprobar('ejecuta los comandos (202)', s == 202 and d['estado'] == 'corriendo', d)
        t = esperar_trabajo(('terminado', 'error', 'cancelado'))
        textos = [(e['t'], e['texto']) for e in t.get('eventos', [])]
        comprobar('comandos: ambos corren en orden y terminan', t.get('estado') == 'terminado' and ('salida', 'ok') in textos and ('salida', 'ok2') in textos
                  and ('comando', '$ python herramientas/panel/eco-prueba.py ok2') in textos, textos)
        comprobar('comandos: dejan historial', bool(t.get('registro')) and os.path.exists(os.path.join(tmp, *t['registro'].split('/'))), t.get('registro'))

        definir(['python herramientas/panel/eco-prueba.py env'])
        accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion'})
        t = esperar_trabajo(('terminado', 'error', 'cancelado'))
        comprobar('los pasos de comandos SÍ reciben las claves del entorno del servidor', ('salida', 'env True') in [(e['t'], e['texto']) for e in t.get('eventos', [])], t.get('eventos'))

        definir(['python herramientas/panel/eco-prueba.py fail', 'python herramientas/panel/eco-prueba.py ok'])
        accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion'})
        t = esperar_trabajo(('terminado', 'error', 'cancelado'))
        textos = [e['texto'] for e in t.get('eventos', [])]
        comprobar('comandos: si uno falla se detiene con su código', t.get('estado') == 'error' and 'código 3' in t.get('motivo', '')
                  and 'boom' in textos and not any(x.endswith('eco-prueba.py ok') for x in textos), t)

        definir(['python herramientas/panel/eco-prueba.py lento'])
        s, d = accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion'})
        time.sleep(1.5)
        s, d2 = accion('/api/trabajo/cancelar', {})
        t = esperar_trabajo(('cancelado', 'terminado', 'error'), 15)
        comprobar('comandos: se pueden cancelar', d2.get('cancelado') is True and t.get('estado') == 'cancelado' and t.get('segundos', 99) < 20, t)

        for malo in ('bash -c "echo hola"', 'python ../fuera.py', 'python herramientas/../fuera.py', 'node'):
            definir([malo])
            s, d = accion('/api/video/canal-prueba/%s/ejecutar' % v, {'paso': 'investigacion'})
            comprobar('comando no permitido se rechaza: %s' % malo, s == 500 and 'no permitido' in d.get('error', '').lower(), (s, d))
        definir([], origen='voz')
        if shutil.which('node'):
            s, d = pedir('GET', ruta_cmd)
            comprobar('origen voz: usa los comandos de la voz de la identidad (Polly en el canal de prueba)', s == 200 and d['voz'].startswith('Amazon Polly')
                      and d['comandos'][0].startswith('node herramientas/voz/preparar-polly.mjs 02-canales/canal-prueba/videos/%s/01-guion/guion.md' % v)
                      and 'AWS_ACCESS_KEY_ID' in d['claves'], d)
    finally:
        if srv:
            srv.terminate()
            srv.wait(timeout=10)
        shutil.rmtree(tmp, ignore_errors=True)
    print('\n%s' % ('TODO OK' if not fallos else 'FALLARON %d: %s' % (len(fallos), '; '.join(fallos))))
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(principal())
