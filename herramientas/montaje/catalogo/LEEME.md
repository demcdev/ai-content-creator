# catalogo/
Catálogo de estilos de animación.

- `animaciones.json`: cada estilo con su estado, riesgo de políticas y cómo se hace. Para añadir uno, agrega una entrada.
- `escenas.json`: tipos de escena que se declaran solo con datos en el `escenas.json` de un video (parámetros requeridos y opcionales, con ejemplo). Para añadir un tipo: una fábrica en `animaciones/<estilo>/escenas_datos.py`, su nombre en `TIPOS_DATOS` de `escenas_base.py` y su entrada aquí.
- `escenas.py`: `python herramientas/montaje/catalogo/escenas.py` lista los tipos; con un tipo, lo explica; `--validar "<canal>/<n>"` revisa el `escenas.json` de un video.
- `animaciones.py`: `python herramientas/montaje/catalogo/animaciones.py` lista los estilos; con un id y un video, lo guarda en la identidad propia del video (`--aplicar`).
