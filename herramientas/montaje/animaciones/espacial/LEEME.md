# animaciones/espacial/
- `estilo.py`: fondo (nebulosa, estrellas en paralaje), brillo, paneles de cristal, planetas procedurales, texto con resplandor.
- `escenas_base.py`: despacha cada entrada de `escenas.json` a su fábrica (placeholder, portada, texto) y a `escenas_datos.py`.
- `escenas_datos.py`: escenas por datos (cifra, comparacion, barras, linea_tiempo, lista, imagen con marco, cita, mapa, cierre). Esquema de cada una: `../../catalogo/escenas.json`; guía en `../../LEEME.md`.
- `globo.py`: Tierra giratoria general (proyección ortográfica). Lo propio de cada escena va en el video que la usa (ejemplo: `videos/01-voyager-1/06-montaje/dsn_voyager.py`).
- `datos/`: `ne_110m_land.geojson` (Natural Earth, dominio público), contornos de continentes.
