#!/usr/bin/env python3
"""
Catálogo de animaciones (animaciones.json): listar, explicar una y aplicarla a un video.

  python herramientas/montaje/catalogo/animaciones.py                          # lista las ofrecidas, con su estado
  python herramientas/montaje/catalogo/animaciones.py --todas                  # también las no ofrecidas y las descartadas
  python herramientas/montaje/catalogo/animaciones.py papel-recortado          # cómo se hace, riesgos y ejemplos
  python herramientas/montaje/catalogo/animaciones.py papel-recortado "<canal>/3" --aplicar   # la guarda en la identidad propia del video

Claude pregunta al usuario cuál usar antes de montar (regla del CLAUDE.md) y después ejecuta --aplicar con la elegida.
No genera video ni usa IA.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(AQUI)), 'nucleo'))   # herramientas/nucleo
from _comun import resolver_video  # noqa: E402


def cargar():
    with open(os.path.join(AQUI, 'animaciones.json'), encoding='utf-8') as f:
        return json.load(f)


def punt(a):
    p = a.get('puntuacion')
    return '%d/30' % p['total'] if p else 'propio'


def listar(datos, todas):
    for a in sorted(datos['animaciones'], key=lambda x: x['orden']):
        if not a['ofrecer'] and not todas:
            continue
        print('%-16s %-34s %-13s %s' % (a['id'], a['nombre'], a['estado'], punt(a)))
        print('                 %s' % a['cuando_usar'])
    if todas:
        print('\nDescartadas:')
        for d in datos['descartadas']:
            print('  %s -> %s' % (d['ids'], d['motivo']))


def explicar(a):
    print('%s (%s) · estado: %s · puntuación: %s' % (a['nombre'], a['id'], a['estado'], punt(a)))
    print(a['descripcion'])
    print('Cuándo usarla: %s' % a['cuando_usar'])
    print('Riesgo de políticas: %s' % a['riesgo'])
    print('Cómo se hace:')
    for linea in a['como_se_hace']:
        print('  - %s' % linea)
    if a.get('usada_en'):
        print('Usada en: %s' % ', '.join(a['usada_en']))
    if a['estado'] != 'disponible':
        print('\nAviso: este estilo no tiene escenas genéricas listas; elegirlo implica diseñar (o construir) sus escenas.')


def aplicar(a, video):
    carpeta = resolver_video(video)
    arch = os.path.join(carpeta, 'identidad', 'identidad.json')
    datos = json.load(open(arch, encoding='utf-8')) if os.path.exists(arch) else {}
    if datos.get('base') == 'canal':
        print('Este video usa la identidad del canal (con su animación). Para una distinta: python herramientas/identidad/identidad.py video "%s" --base propia --animacion %s' % (video, a['id']))
        return 1
    datos['base'] = 'propia'
    datos['animacion'] = a['id']
    with open(arch, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    print('Animación «%s» guardada en la identidad propia del video: %s' % (a['id'], arch))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('id', nargs='?')
    ap.add_argument('video', nargs='?')
    ap.add_argument('--todas', action='store_true')
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()
    datos = cargar()
    if not a.id:
        listar(datos, a.todas)
        return 0
    elegida = [x for x in datos['animaciones'] if x['id'] == a.id]
    if not elegida:
        print('No existe la animación «%s». Disponibles: %s' % (a.id, ', '.join(x['id'] for x in datos['animaciones'])))
        return 1
    if a.aplicar:
        if not a.video:
            print('Indica el video: animaciones.py <id> "<video>" --aplicar')
            return 1
        return aplicar(elegida[0], a.video)
    else:
        explicar(elegida[0])
    return 0


if __name__ == '__main__':
    sys.exit(main())
