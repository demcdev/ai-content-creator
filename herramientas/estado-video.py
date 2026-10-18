#!/usr/bin/env python3
"""
Estado de un video leyendo sus archivos (no usa IA, no gasta tokens) y sellos de revisión.

  python herramientas/estado-video.py "Hace Eones/Video 02"                 # imprime el estado
  python herramientas/estado-video.py "Hace Eones/Video 02" --escribir      # además guarda Estado.md
  python herramientas/estado-video.py "Hace Eones/2" --aprobar idea guion corte
  python herramientas/estado-video.py "Hace Eones/2" --sellar auditor-guion verificador
  python herramientas/estado-video.py "Hace Eones/2" --revisar auditor-guion   # ¿cambió el guion desde el sello?
  python herramientas/estado-video.py "Hace Eones/2" --diff auditor-guion      # solo lo que cambió

Qué guarda: <video>/.estado/estado.json (puertas aprobadas y sellos) y una copia del guion por sello,
para poder mostrar solo el cambio. Códigos de --revisar: 0 sin cambios · 3 cambió · 4 nunca sellado.
Roles con sello sobre el guion: verificador, auditor-guion. Sello sobre el video final: auditor-final.
"""
import argparse
import sys
sys.dont_write_bytecode = True  # no dejar __pycache__ en la carpeta
import datetime
import difflib
import json
import os
import re
import shutil
import sys

from _comun import (archivos, consola, filas_datos, leer, resolver_video, resumen_licencias, sha,
                    seccion_h2, sin_seccion, tamano)

ROLES_GUION = ('verificador', 'auditor-guion')
ROL_FINAL = 'auditor-final'
PUERTAS = {'idea': 'idea y packaging', 'guion': 'guion revisado', 'corte': 'corte final'}


def cargar(carpeta):
    ruta = os.path.join(carpeta, '.estado', 'estado.json')
    try:
        with open(ruta, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {'puertas': {}, 'sellos': {}}


def guardar(carpeta, datos):
    os.makedirs(os.path.join(carpeta, '.estado'), exist_ok=True)
    with open(os.path.join(carpeta, '.estado', 'estado.json'), 'w', encoding='utf-8') as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)


def firma_final(carpeta):
    mp4 = archivos(os.path.join(carpeta, 'Entregables'), ('.mp4',), recursivo=False)
    if not mp4:
        return None
    ruta = max(mp4, key=os.path.getmtime)
    return '%s:%d:%d' % (os.path.basename(ruta), os.path.getsize(ruta), int(os.path.getmtime(ruta)))


def firma_actual(carpeta, rol):
    if rol == ROL_FINAL:
        return firma_final(carpeta)
    ruta = os.path.join(carpeta, 'Guion.md')
    return sha(ruta) if os.path.exists(ruta) else None


def vigencia(carpeta, datos, rol):
    """'vigente' | 'cambiado' | 'nunca'"""
    sello = datos['sellos'].get(rol)
    if not sello:
        return 'nunca'
    return 'vigente' if sello['firma'] == firma_actual(carpeta, rol) else 'cambiado'


def etapas(carpeta, datos):
    """Lista de (clave, nombre, ok, detalle, quien_la_hace)."""
    f = lambda n: os.path.join(carpeta, n)
    res = []
    add = lambda *x: res.append(x)

    add('p-idea', 'Puerta: idea y packaging', 'idea' in datos['puertas'], datos['puertas'].get('idea', ''), 'tú: --aprobar idea')
    n = filas_datos(leer(f('Verificacion de cifras.md')))
    add('investigacion', 'Investigación y cifras', n > 0, '%d filas en tablas' % n, 'subagente investigador')
    g = tamano(f('Guion.md'))
    add('guion', 'Guion', g > 1500, '%.1f KB' % (g / 1024), 'conversación + skill guionista-retencion')
    partes = {r: vigencia(carpeta, datos, r) for r in ROLES_GUION}
    ok = all(v == 'vigente' for v in partes.values())
    add('rev-guion', 'Revisión del guion (sellos)', ok, ', '.join('%s: %s' % kv for kv in partes.items()),
        'validar-video.py y luego verificador + auditor')
    add('p-guion', 'Puerta: guion revisado', 'guion' in datos['puertas'], datos['puertas'].get('guion', ''), 'tú: --aprobar guion')
    esc = leer(f('Escaleta audiovisual.md'))
    n = filas_datos(sin_seccion(esc, 'Planilla de producción'))
    add('escaleta', 'Escaleta audiovisual', n > 0, '%d escenas' % n, 'skill escaleta-audiovisual')
    n = filas_datos(seccion_h2(esc, 'Planilla de producción'))
    add('planilla', 'Planilla (sección de la escaleta)', n > 0, '%d filas' % n, 'skill guionista-retencion')
    n = len(archivos(f('Voz'), ('.mp3', '.wav', '.m4a', '.ogg', '.flac')))
    add('voz', 'Voz', n > 0, '%d audios' % n, 'preguntar qué voz (voces.json) y herramientas/voz')
    n = len(archivos(f('Miniaturas'), ('.png', '.jpg', '.jpeg', '.webp'), ignorar_guion_bajo=True))
    add('miniaturas', 'Miniaturas', n > 0, '%d imágenes' % n, 'subagente miniaturas')
    lic = resumen_licencias(leer(f('Registro de licencias.md')))
    if lic and lic[0] > 0:
        add('licencias', 'Licencias', lic[2] == 0, '%d de %d listas (resumen manual)' % (lic[1], lic[0]), 'tú, con las fichas')
    else:
        add('licencias', 'Licencias', False, 'sin filas', 'tú, con las fichas')
    n = len([x for x in archivos(f('Montaje'), ('.py', '.json', '.mp4', '.mov', '.png')) if not os.path.basename(x).startswith('_')])
    add('montaje', 'Montaje', n > 0, '%d archivos' % n, 'preguntar la animación (animaciones.json) y scripts de montaje')
    firma = firma_final(carpeta)
    add('video', 'Video final (.mp4)', firma is not None, firma.split(':')[0] if firma else '', 'scripts de montaje')
    v = vigencia(carpeta, datos, ROL_FINAL)
    add('rev-final', 'Control final (sello)', v == 'vigente', v, 'validar-video.py --etapa final y luego auditor')
    add('p-corte', 'Puerta: corte final', 'corte' in datos['puertas'], datos['puertas'].get('corte', ''), 'tú: --aprobar corte')
    ok = tamano(f('Capitulos y descripcion.md')) > 800
    add('descripcion', 'Capítulos y descripción', ok, '', 'skill SEO')
    ok = tamano(f('Texto para subtitulos.txt')) > 200 or bool(archivos(f('Entregables'), ('.srt',), recursivo=False))
    add('subtitulos', 'Subtítulos', ok, '', 'herramientas de voz')
    n = filas_datos(leer(f('Metricas y seguimiento.md')))
    add('metricas', 'Métricas publicadas', n > 0, '%d registros' % n, 'analista (vidIQ)')
    return res


def render(carpeta, datos, markdown=False):
    rel = os.path.relpath(carpeta, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    lista = etapas(carpeta, datos)
    sig = next((e for e in lista if not e[2]), None)
    out = []
    if markdown:
        out += ['# Estado · ' + os.path.basename(carpeta), '',
                '> Generado por `herramientas/estado-video.py` el %s. No se edita a mano: se regenera.' % datetime.date.today().isoformat(), '',
                '**Siguiente paso:** ' + (('%s → %s' % (sig[1], sig[4])) if sig else 'todo completo'), '',
                '| Etapa | Estado | Detalle | Quién |', '|---|---|---|---|']
        for c, nombre, ok, det, quien in lista:
            out.append('| %s | %s | %s | %s |' % (nombre, 'listo' if ok else 'pendiente', det, quien))
    else:
        out += ['VIDEO: ' + rel,
                'SIGUIENTE: ' + (('%s  (%s)' % (sig[1], sig[4])) if sig else 'todo completo')]
        for c, nombre, ok, det, quien in lista:
            out.append('  [%s] %-30s %s' % ('OK' if ok else '..', nombre, det))
    return '\n'.join(out) + '\n'


def principal():
    consola()
    ap = argparse.ArgumentParser(description='Estado de un video sin gastar tokens')
    ap.add_argument('video')
    ap.add_argument('--escribir', action='store_true', help='guarda Estado.md en la carpeta del video')
    ap.add_argument('--aprobar', nargs='+', choices=sorted(PUERTAS), metavar='PUERTA')
    ap.add_argument('--sellar', nargs='+', choices=list(ROLES_GUION) + [ROL_FINAL], metavar='ROL')
    ap.add_argument('--revisar', choices=list(ROLES_GUION) + [ROL_FINAL])
    ap.add_argument('--diff', choices=list(ROLES_GUION))
    a = ap.parse_args()

    carpeta = resolver_video(a.video)
    datos = cargar(carpeta)
    hoy = datetime.date.today().isoformat()

    if a.aprobar:
        for p in a.aprobar:
            datos['puertas'][p] = hoy
        guardar(carpeta, datos)
    if a.sellar:
        for rol in a.sellar:
            firma = firma_actual(carpeta, rol)
            if not firma:
                sys.exit('No hay nada que sellar para %s (falta %s).' % (rol, 'el .mp4 en Entregables/' if rol == ROL_FINAL else 'Guion.md'))
            datos['sellos'][rol] = {'firma': firma, 'fecha': hoy}
            if rol in ROLES_GUION:
                os.makedirs(os.path.join(carpeta, '.estado'), exist_ok=True)
                shutil.copyfile(os.path.join(carpeta, 'Guion.md'), os.path.join(carpeta, '.estado', rol + '.Guion.md'))
        guardar(carpeta, datos)

    if a.revisar:
        v = vigencia(carpeta, datos, a.revisar)
        fecha = datos['sellos'].get(a.revisar, {}).get('fecha', '')
        print({'vigente': 'SIN CAMBIOS desde el sello del %s: no hace falta revisar de nuevo.' % fecha,
               'cambiado': 'CAMBIADO desde el sello del %s: revisar (usa --diff para ver solo el cambio).' % fecha,
               'nunca': 'NUNCA SELLADO: revisar completo.'}[v])
        return {'vigente': 0, 'cambiado': 3, 'nunca': 4}[v]
    if a.diff:
        previa = os.path.join(carpeta, '.estado', a.diff + '.Guion.md')
        if not os.path.exists(previa):
            sys.exit('No hay copia sellada para %s: revisar completo.' % a.diff)
        antes = leer(previa).splitlines()
        ahora = (leer(os.path.join(carpeta, 'Guion.md')) or '').splitlines()
        salida = list(difflib.unified_diff(antes, ahora, 'sellado', 'actual', n=1, lineterm=''))
        print('\n'.join(salida) if salida else 'Sin diferencias.')
        return 0

    texto = render(carpeta, datos)
    print(texto, end='')
    if a.escribir:
        with open(os.path.join(carpeta, 'Estado.md'), 'w', encoding='utf-8') as fh:
            fh.write(render(carpeta, datos, markdown=True))
        print('Estado.md guardado.')
    return 0


if __name__ == '__main__':
    sys.exit(principal())
