#!/usr/bin/env python3
"""
Convierte la escaleta técnica de un video en 06-montaje/escenas.json (la lista de escenas que lee el montaje).

  python herramientas/video/escaleta-a-escenas.py "hace-eones/3"
  python herramientas/video/escaleta-a-escenas.py "<canal>/3" --forzar     # sobrescribe un escenas.json existente
  python herramientas/video/escaleta-a-escenas.py "<canal>/3" --fusionar   # actualiza tiempos y textos, conserva tipo y campos propios

Lee las filas de la parte «escaleta técnica» de `escaleta-audiovisual.md` (no la planilla) con el formato
`| **E07 · Nombre de la escena** | 03:12–03:40 | descripción | ... |` y deja, por escena:
{id, nombre, ini, fin, tipo: "placeholder", descripcion}. Cambia el `tipo` a portada, texto, imagen o cierre
(ver herramientas/montaje/animaciones/espacial/escenas_base.py) o registra una escena propia en 06-montaje/video.py.
No usa IA y no gasta tokens.
"""
import argparse
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nucleo'))
from _comun import F_ESCALETA, MONTAJE, leer, resolver_video, ruta, sin_seccion  # noqa: E402

FILA = re.compile(r'^\|\s*\*\*(E\d+\w*)\s*[·.:-]\s*(.+?)\*\*\s*\|\s*([\d:.]+)\s*[–-]\s*([\d:.]+)\s*\|(.*)$')


def segundos(txt):
    partes = [float(x) for x in txt.split(':')]
    s = 0.0
    for p in partes:
        s = s * 60 + p
    return round(s, 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video')
    ap.add_argument('--forzar', action='store_true')
    ap.add_argument('--fusionar', action='store_true', help='rehace nombre, tiempos y descripción desde la escaleta y conserva el resto de campos de cada id')
    a = ap.parse_args()
    carpeta = resolver_video(a.video)
    texto = sin_seccion(leer(ruta(carpeta, F_ESCALETA)), 'Planilla de producción')
    escenas = []
    for linea in texto.splitlines():
        m = FILA.match(linea)
        if not m:
            continue
        id_, nombre, ini, fin, resto = m.groups()
        desc = resto.split('|')[0].strip()
        escenas.append({'id': id_, 'nombre': nombre.strip(), 'ini': segundos(ini), 'fin': segundos(fin), 'tipo': 'placeholder',
                        'descripcion': re.sub(r'\*\*|`', '', desc)[:300]})
    if not escenas:
        sys.exit('No encontré filas de escenas («| **E01 · Nombre** | 00:00–00:30 | ...») en la escaleta técnica.')
    os.makedirs(os.path.join(carpeta, MONTAJE), exist_ok=True)
    destino = os.path.join(carpeta, MONTAJE, 'escenas.json')
    conservadas = 0
    if os.path.exists(destino) and a.fusionar:
        with open(destino, encoding='utf-8') as f:
            previas = {e.get('id'): e for e in json.load(f)}
        for i, e in enumerate(escenas):
            if e['id'] in previas:
                escenas[i] = dict(previas[e['id']], **{k: e[k] for k in ('id', 'nombre', 'ini', 'fin', 'descripcion')})
                conservadas += 1
    elif os.path.exists(destino) and not a.forzar:
        sys.exit('Ya existe %s. Usa --fusionar (conserva tipos) o --forzar para sobrescribirlo.' % destino)
    with open(destino, 'w', encoding='utf-8') as f:
        json.dump(escenas, f, ensure_ascii=False, indent=1)
    print('%d escenas -> %s (de %s a %s)%s' % (len(escenas), destino, escenas[0]['ini'], escenas[-1]['fin'],
                                             ' · %d ya existían (conservan tipo y campos propios)' % conservadas if a.fusionar else ''))


if __name__ == '__main__':
    main()
