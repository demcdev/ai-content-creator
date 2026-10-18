# canal/
Punto de entrada único del flujo de un video: `python herramientas/canal/canal.py <orden> ...`. Delega en los demás programas de `herramientas/` y automatiza lo que no necesita IA ni decisión humana. No usa IA ni claves.

`python herramientas/canal/canal.py ayuda --corta` imprime la lista de órdenes en pocas líneas. El video se indica como `<canal>/<n>` (p. ej. `hace-eones/2`) o como ruta.

## Órdenes propias
- `siguiente <video> [--seco]`: corre los pasos automáticos y se detiene en el primer paso que necesita a una persona o a la IA, con lo que falta y el comando, la skill o el subagente que toca. Código de salida: 0 todo completo · 1 hay algo que arreglar · 2 decisión humana · 3 paso de IA. Con `--seco` no ejecuta ni escribe nada (solo corre el lint, que es de lectura).
- `contexto <video> [--para guion|revision|escaleta]`: el contexto mínimo para ese paso, para no leer documentos enteros. Incluye la identidad efectiva, el lint, las cifras sin ✅, los sellos con su `--diff`, las reglas aplicables (secciones de `reglas-detalladas.md`), la checklist del canal y la de escritura sin ejemplos, los datos de montaje y las licencias. Sin `--para`, elige según la etapa en la que va el video.
- `alinear`, `escenas`: igual que los programas de origen, pero incrementales (ver abajo). `escenas` regenera con `--fusionar`: actualiza nombre, tiempos y descripción desde la escaleta y conserva el `tipo` y los campos propios de cada escena.
- `montar <video> [--frame S f.png | --verificar | --solo-audio | N] [--script x.py]`: ejecuta el script de `06-montaje/` (el de `"script"` en `montaje.json`, `video.py` o el único `.py`). Sin opciones, antes de renderizar pone al día los tiempos y las escenas, comprueba los solapes y, al terminar, copia el `.mp4` y el `.srt` a `08-entregables/`.
- `publicar <video>`: lint final, sello del control final, lista de entregables y las secciones «Declaración de IA» y «Antes de subir» de la checklist del canal. No sube nada: la subida se hace a mano en YouTube Studio.

## Órdenes que delegan tal cual
`nuevo` → `video/nuevo-video.py` · `estado` → `video/estado-video.py` · `validar` → `video/validar-video.py` · `identidad` → `identidad/identidad.py` · `voz` → `voz/voces.py` (`voz <video>` equivale a `--video <video>`) · `animaciones` → `montaje/catalogo/animaciones.py` · `revisar-proyecto` → `validacion/validar-proyecto.py`.

## Pasos automáticos e incrementales
| Paso | Se rehace cuando cambia | Resultado |
|---|---|---|
| validar (guion y, si hay `.mp4`, final) | guion, tabla de cifras, el propio lint (y en final: escaleta, licencias, voz, entregables, miniaturas) | `PASA` o `FALLA` |
| alinear | el `.wav` más grande de `04-voz/` (tamaño y fecha), `texto-para-subtitulos.txt`, `polly/` y `partes/`, `kmax` y `correcciones` de `montaje.json`, `voz/sustituciones.json` | `06-montaje/tiempos.json` |
| escenas | la escaleta técnica (sin la planilla) | `06-montaje/escenas.json` (solo si el video usa `video.py` o ya tiene `escenas.json`) |
| verificar solapes | `.py` y `.json` de `06-montaje/`, la identidad efectiva y el código de `herramientas/montaje/` | número de solapes (necesita `tiempos.json`) |

Las huellas se guardan en `<video>/.estado/huellas.json` (no se versiona: depende de las fechas de los archivos de esta máquina). Para rehacer un paso aunque nada haya cambiado: `alinear <video> --forzar`, o `escenas <video> --forzar` (esta segunda opción pierde los tipos).
