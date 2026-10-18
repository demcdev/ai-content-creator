# animaciones/espacial/
- `estilo.py`: fondo (nebulosa, estrellas en paralaje), brillo, paneles de cristal, planetas procedurales, texto con resplandor.
- `escenas_base.py`: escenas genéricas (portada, texto, imagen, cierre, placeholder) para armar un video completo desde el primer día.
- `globo.py`: Tierra giratoria general (proyección ortográfica). Lo propio de cada escena va en el video que la usa (ejemplo: `Video 01/Montaje/dsn_voyager.py`).
- `datos/`: `ne_110m_land.geojson` (Natural Earth, dominio público), contornos de continentes.
