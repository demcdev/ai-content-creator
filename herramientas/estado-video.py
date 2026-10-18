#!/usr/bin/env python3
"""
Estado de un video leyendo sus archivos (no usa IA, no gasta tokens) y sellos de revisión.

  python herramientas/estado-video.py "hace-eones/2"                 # imprime el estado
  python herramientas/estado-video.py "hace-eones/2" --escribir      # además guarda el estado en LEEME.md
  python herramientas/estado-video.py "hace-eones/2" --aprobar idea guion corte
  python herramientas/estado-video.py "hace-eones/2" --sellar auditor-guion verificador
  python herramientas/estado-video.py "hace-eones/2" --revisar auditor-guion   # ¿cambió el guion desde el sello?
  python herramientas/estado-video.py "hace-eones/2" --diff auditor-guion      # solo lo que cambió

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

from _comun import (ENTREGABLES, F_CAPITULOS, F_CIFRAS, F_ESCALETA, F_GUION, F_LICENCIAS, F_METRICAS, F_SUBTITULOS, MINIATURAS, MONTAJE,
                    VOZ, archivos, consola, filas_datos, identidad_efectiva, leer, resolver_video, resumen_licencias, ruta, sha,
                    seccion_h2, sin_seccion, tamano)

ROLES_GUION = ('verificador', 'auditor-guion')
ROL_FINAL = 'auditor-final'
PUERTAS = {'idea': 'idea y packaging', 'guion': 'guion revisado', 'corte': 'corte final'}


def cargar(carpeta):
    arch = os.path.join(carpeta, '.estado', 'estado.json')
    try:
        with open(arch, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {'puertas': {}, 'sellos': {}}


def guardar(carpeta, datos):
    os.makedirs(os.path.join(carpeta, '.estado'), exist_ok=True)
    with open(os.path.join(carpeta, '.estado', 'estado.json'), 'w', encoding='utf-8') as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)


def firma_final(carpeta):
    mp4 = archivos(ruta(carpeta, ENTREGABLES), ('.mp4',), recursivo=False)
    if not mp4:
        return None
    ultimo = max(mp4, key=os.path.getmtime)
    return '%s:%d:%d' % (os.path.basename(ultimo), os.path.getsize(ultimo), int(os.path.getmtime(ultimo)))


def firma_actual(carpeta, rol):
    if rol == ROL_FINAL:
        return firma_final(carpeta)
    guion = ruta(carpeta, F_GUION)
    return sha(guion) if os.path.exists(guion) else None


def vigencia(carpeta, datos, rol):
    """'vigente' | 'cambiado' | 'nunca'"""
    sello = datos['sellos'].get(rol)
    if not sello:
        return 'nunca'
    return 'vigente' if sello['firma'] == firma_actual(carpeta, rol) else 'cambiado'


def etapas(carpeta, datos):
    """Lista de (clave, nombre, ok, detalle, quien_la_hace)."""
    f = lambda n: ruta(carpeta, n)
    res = []
    add = lambda *x: res.append(x)

    add('p-idea', 'Puerta: idea y packaging', 'idea' in datos['puertas'], datos['puertas'].get('idea', ''), 'tú: --aprobar idea')
    n = filas_datos(leer(f(F_CIFRAS)))
    add('investigacion', 'Investigación y cifras', n > 0, '%d filas en tablas' % n, 'subagente investigador')
    g = tamano(f(F_GUION))
    add('guion', 'Guion', g > 1500, '%.1f KB' % (g / 1024), 'conversación + skill guionista-retencion')
    partes = {r: vigencia(carpeta, datos, r) for r in ROLES_GUION}
    ok = all(v == 'vigente' for v in partes.values())
    add('rev-guion', 'Revisión del guion (sellos)', ok, ', '.join('%s: %s' % kv for kv in partes.items()),
        'validar-video.py y luego verificador + auditor')
    add('p-guion', 'Puerta: guion revisado', 'guion' in datos['puertas'], datos['puertas'].get('guion', ''), 'tú: --aprobar guion')
    esc = leer(f(F_ESCALETA))
    n = filas_datos(sin_seccion(esc, 'Planilla de producción'))
    add('escaleta', 'Escaleta audiovisual', n > 0, '%d escenas' % n, 'skill escaleta-audiovisual')
    n = filas_datos(seccion_h2(esc, 'Planilla de producción'))
    add('planilla', 'Planilla (sección de la escaleta)', n > 0, '%d filas' % n, 'skill guionista-retencion')
    ident, _ = identidad_efectiva(carpeta)
    add('identidad', 'Identidad del video', ident['base'] in ('canal', 'propia'), ident['base'] or '', 'preguntar: ¿identidad del canal o propia? (identidad.py)')
    n = len(archivos(f(VOZ), ('.mp3', '.wav', '.m4a', '.ogg', '.flac')))
    add('voz', 'Voz', n > 0, '%d audios' % n, 'voz de la identidad del video (voces.json) y herramientas/voz')
    n = len(archivos(f(MINIATURAS), ('.png', '.jpg', '.jpeg', '.webp'), ignorar_guion_bajo=True))
    add('miniaturas', 'Miniaturas', n > 0, '%d imágenes' % n, 'subagente miniaturas')
    lic = resumen_licencias(leer(f(F_LICENCIAS)))
    if lic and lic[0] > 0:
        add('licencias', 'Licencias', lic[2] == 0, '%d de %d listas (resumen manual)' % (lic[1], lic[0]), 'tú, con las fichas')
    else:
        add('licencias', 'Licencias', False, 'sin filas', 'tú, con las fichas')
    n = len([x for x in archivos(f(MONTAJE), ('.py', '.json', '.mp4', '.mov', '.png')) if not os.path.basename(x).startswith('_')])
    add('montaje', 'Montaje', n > 0, '%d archivos' % n, 'animación de la identidad del video (animaciones.json) y scripts de montaje')
    firma = firma_final(carpeta)
    add('video', 'Video final (.mp4)', firma is not None, firma.split(':')[0] if firma else '', 'scripts de montaje')
    v = vigencia(carpeta, datos, ROL_FINAL)
    add('rev-final', 'Control final (sello)', v == 'vigente', v, 'validar-video.py --etapa final y luego auditor')
    add('p-corte', 'Puerta: corte final', 'corte' in datos['puertas'], datos['puertas'].get('corte', ''), 'tú: --aprobar corte')
    ok = tamano(f(F_CAPITULOS)) > 800
    add('descripcion', 'Capítulos y descripción', ok, '', 'skill SEO')
    ok = tamano(f(F_SUBTITULOS)) > 200 or bool(archivos(f(ENTREGABLES), ('.srt',), recursivo=False))
    add('subtitulos', 'Subtítulos', ok, '', 'herramientas de voz')
    n = filas_datos(leer(f(F_METRICAS)))
    add('metricas', 'Métricas publicadas', n > 0, '%d registros' % n, 'analista (vidIQ)')
    return res


def render(carpeta, datos, markdown=False):
    rel = os.path.relpath(carpeta, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    lista = etapas(carpeta, datos)
    sig = next((e for e in lista if not e[2]), None)
    out = []
    if markdown:
        out += ['# ' + os.path.basename(carpeta), '',
                'Carpeta del video, una por etapa: `01-guion` → `02-revision` → `03-escaleta` → `04-voz` → `05-licencias` → `06-montaje` → `07-miniaturas` → `08-entregables` → `09-publicacion`; `identidad/` guarda la identidad propia del video.', '',
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
    ap.add_argument('--escribir', action='store_true', help='guarda el estado en el LEEME.md de la carpeta del video')
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
                sys.exit('No hay nada que sellar para %s (falta %s).' % (rol, 'el .mp4 en 08-entregables/' if rol == ROL_FINAL else F_GUION))
            datos['sellos'][rol] = {'firma': firma, 'fecha': hoy}
            if rol in ROLES_GUION:
                os.makedirs(os.path.join(carpeta, '.estado'), exist_ok=True)
                shutil.copyfile(ruta(carpeta, F_GUION), os.path.join(carpeta, '.estado', rol + '.Guion.md'))
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
        ahora = (leer(ruta(carpeta, F_GUION)) or '').splitlines()
        salida = list(difflib.unified_diff(antes, ahora, 'sellado', 'actual', n=1, lineterm=''))
        print('\n'.join(salida) if salida else 'Sin diferencias.')
        return 0

    texto = render(carpeta, datos)
    print(texto, end='')
    if a.escribir:
        with open(os.path.join(carpeta, 'LEEME.md'), 'w', encoding='utf-8') as fh:
            fh.write(render(carpeta, datos, markdown=True))
        print('LEEME.md (estado) guardado.')
    return 0


if __name__ == '__main__':
    sys.exit(principal())
