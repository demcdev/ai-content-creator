Veredicto: PASA

Auditor final, video 03, 18-oct-2026. Lint: PASA (0 errores, 20 avisos de estado "verificada" que el validador no reconoce como ✅, sin gravedad).

Comprobado
- Licencias (3): registro con 6 filas listas; fichas L01, L02, L06 guardadas. El video no usa imágenes del EHT, música ni fotos externas, y las capturas de música no son necesarias.
- IA y fuentes (4): capitulos-y-descripcion.md líneas 57-61 declaran voz Polly y gráficos propios; fuentes en 41-48; Studio "sintético = Sí" en línea 121.
- Miniaturas (9): A, B y C existen en 07-miniaturas con versiones 160x90, 320x180 y móvil. Son candidatas al test A/B, sin elegida. Ninguna promete más de lo que el video entrega.
- Subida oculta o no listada (17): línea 117.
- Subtítulos: 08-entregables/video-03-completo.srt existe (174 bloques).

Hallazgos (no bloquean)
1. Reglas 9/4 · capitulos-y-descripcion.md:80-90 · la tabla de control tiene marcas viejas (0:46, 2:10, 4:29...) que no coinciden con los capítulos pegables de las líneas 31-39 (0:52, 1:53, 3:48...) → regenerar la tabla desde tiempos.json para evitar pegar la equivocada.
2. Regla 17 · mismo archivo:7 · las marcas de capítulo no son verificables por mí (no puedo ver el mp4); en tiempos.json no hallé los títulos de capítulo → comprobar a mano cada marca (±1 s) en el video final.
3. Regla 4 · 06-montaje/escenas.json (líneas 23, 37...) y guion.md:127,163 · los rótulos "Fuente: ESO, eso1907" aparecen sobre gráficos propios. Es una atribución de datos, no de imagen, pero conviene que no parezca imagen de ESO → rotular "Ilustración propia. Datos: ESO".
4. Registro de licencias:17-21 · la lista "Lo que falta antes de montar" sigue con casillas abiertas y L04/L05 figuran ✅ sin usarse → anotar "no usado en este video".
5. Miniaturas B (miniaturas.json:10) · fondo y texto comparten #0B1F22; el estilo "caja" puede dejar el texto poco legible a 160x90 → mirarla a mano.

Para ti (solo en Studio)
- "Hecho para niños = No" y "Contenido sintético = Sí".
- Subir oculto o no listado y esperar los avisos de copyright.
- Recomprobar en ESO el número de observatorios si lo citas.
- Subir el .srt y revisar las miniaturas.
