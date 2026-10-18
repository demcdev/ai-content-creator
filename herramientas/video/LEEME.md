# video/
Programas del ciclo de vida de un video. Reciben el video como `<canal>/<n>` (por ejemplo `hace-eones/2`) o como ruta.

- `nuevo-video.py "<canal>" <n> "Nombre"`: crea `videos/NN-nombre/` con una carpeta por etapa y los documentos de partida.
- `estado-video.py <video> [--escribir] [--aprobar … | --sellar … | --revisar … | --diff …]`: etapa en la que va, siguiente paso y sellos de revisión (`--escribir` guarda el estado en el `LEEME.md` del video).
- `validar-video.py <video> [--etapa guion|montaje|final]`: lint gratuito del guion, las cifras, las licencias y los entregables.
- `escaleta-a-escenas.py <video> [--forzar | --validar]`: convierte la escaleta técnica en `06-montaje/escenas.json`; si la fila de una escena trae una directiva `` `@tipo clave=valor; …` `` (cifra, comparacion, barras, linea_tiempo, lista, imagen, cita, mapa, cierre…), la deja ya diseñada. Tipos y parámetros: `python herramientas/montaje/catalogo/escenas.py`. `--validar` revisa un `escenas.json` ya escrito.
