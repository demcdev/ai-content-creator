# tuberia/
De la voz al video terminado.

- `alinear.py`: mide los silencios del audio y deja `tiempos.json` en `videos/NN-nombre/06-montaje/` (`python herramientas/montaje/tuberia/alinear.py "<video>"`).
- `pipeline.py`: clase `Proyecto`; lee `escenas.json`, `tiempos.json` y `montaje.json`, elige el estilo (`cargar_estilo`), dibuja los fotogramas y los junta con voz, música y subtítulos.
