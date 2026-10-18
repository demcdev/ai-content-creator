#!/usr/bin/env python3
"""
Genera los subtítulos (.srt) de un video SIN renderizarlo: salen de 06-montaje/tiempos.json (alinear la voz primero).

  python herramientas/montaje/tuberia/exportar-srt.py "hace-eones/3"

Escribe 06-montaje/salida/<nombre>.srt y lo copia a 08-entregables/. Falla si no hay frases alineadas. No usa IA.
"""
import os
import shutil
import sys

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
HERR = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, os.path.join(HERR, 'nucleo'))
sys.path.insert(0, os.path.join(HERR, 'montaje', 'comun'))
sys.path.insert(0, AQUI)
from _comun import ENTREGABLES, MONTAJE, resolver_video  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    carpeta = resolver_video(sys.argv[1])
    if not os.path.exists(os.path.join(carpeta, MONTAJE, 'tiempos.json')):
        sys.exit('Falta 06-montaje/tiempos.json: alinea la voz primero (canal.py alinear "<video>").')
    from pipeline import Proyecto
    P = Proyecto(os.path.join(carpeta, MONTAJE, 'video.py'))
    if not P.subs:
        sys.exit('tiempos.json no tiene frases: no hay nada que subtitular.')
    os.makedirs(P.salida, exist_ok=True)
    origen = os.path.join(P.salida, P.nombre + '.srt')
    P.escribir_srt(origen)
    destino = os.path.join(carpeta, ENTREGABLES)
    os.makedirs(destino, exist_ok=True)
    shutil.copy2(origen, os.path.join(destino, P.nombre + '.srt'))
    print('%d subtítulos -> %s/%s.srt' % (len(P.subs), ENTREGABLES, P.nombre))


if __name__ == '__main__':
    main()
