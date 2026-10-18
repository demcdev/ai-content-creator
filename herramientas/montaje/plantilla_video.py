"""
Montaje de este video. Se ejecuta desde esta carpeta (Montaje/), con tiempos.json y escenas.json al lado (tiempos.json: `python herramientas/montaje/alinear.py "<video>"`):

  python video.py --frame 60 f.png     un fotograma (segundo 60), para revisar el diseño
  python video.py --verificar          regla «nada se tapa con nada» (rótulos, créditos, capítulos)
  python video.py                      render completo en 4 procesos -> salida/<nombre>.mp4 y .srt

Todo lo común está en herramientas/montaje/pipeline.py. Las escenas salen de escenas.json (se generan desde la
escaleta con `python herramientas/escaleta-a-escenas.py "<video>"`); las que aún no tienen diseño aparecen como
tarjetas. Para diseñar una: define una función fn(t) que devuelva un fotograma y regístrala con su id.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'herramientas', 'montaje')))

from pipeline import Proyecto  # noqa: E402

P = Proyecto(__file__)

# Escenas propias, una por una (ejemplo):
#   def esc_gancho(t):
#       fr = estilo.base(t)                      # fondo; helpers en montar.py, estilo.py y ui.py
#       return fr
#   P.registrar('E01', esc_gancho)

if __name__ == '__main__':
    P.main(__file__)
