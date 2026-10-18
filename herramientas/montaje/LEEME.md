# Librerías de montaje (compartidas por todos los videos)

> **Cómo está organizado (17-oct-2026):** en la raíz solo está este `LEEME.md`; todo lo demás va en carpetas, y cada carpeta nueva tiene su propio `LEEME.md`:
>
> | Carpeta | Qué contiene |
> |---|---|
> | `comun/` | Librerías que usan todos los estilos: `montar.py` (fuentes, imágenes, texto), `ui.py` (cajas, rótulos, créditos, capítulos) y `aa.py` (dibujo suavizado) |
> | `tuberia/` | `pipeline.py` (escenas → fotogramas → mp4) y `alinear.py` (voz → `tiempos.json`) |
> | `catalogo/` | `animaciones.json` (catálogo de estilos) y `animaciones.py` (lista y aplica un estilo); `escenas.json` (tipos de escena por datos) y `escenas.py` (lista, explica y valida) |
> | `plantillas/` | `plantilla_video.py`, la que copia `nuevo-video.py` a cada video, y `escenas-ejemplo.json` (un caso de cada tipo de escena) |
> | `animaciones/<id>/` | Un estilo por carpeta, con el mismo id que el catálogo: `espacial/` (`estilo.py`, `escenas_base.py`, `globo.py`, `datos/`) y `papel-recortado/` (`papel.py`, `pintura.py`) |
> | `fuentes/` | Tipografías de licencia abierta |
>
> Los scripts de video añaden a `sys.path` `comun/` (y `tuberia/` si usan la tubería) y la carpeta de su estilo (ver `plantillas/plantilla_video.py`). La tubería (`cargar_estilo` en `pipeline.py`) elige el estilo según la animación de la identidad (o de `montaje.json`); un estilo sin `estilo.py` y `escenas_base.py` (hoy `papel-recortado`) cae en el espacial con un aviso.
>
> Los **scripts de cada video** (escenas, tiempos, música, render, miniaturas) viven en la carpeta de ese video: `videos/NN-nombre/06-montaje/`. Allí se ejecutan; ellos importan estas librerías solos. Los archivos que se citan sin ruta (`video01.py`, `miniaturas.py`, `capitulos.py`, `tiempos.json`, `musica/`, `salida/`) están en esa carpeta.

Genera un video MP4 1080p a 30 fps a partir de:
- el **audio real** del video (`videos/NN-nombre/04-voz/`),
- las **imágenes oficiales** guardadas en `videos/NN-nombre/05-licencias/originales/`,
- **esquemas animados** hechos con código (cifras de `01-guion/verificacion-de-cifras.md`),
- **rótulos «Dato verificado»** y **subtítulos**, sincronizados con los silencios del audio.

Requisitos: Python 3, `Pillow`, `numpy`, `scipy` y `ffmpeg` en el PATH. Tipografía: Inter (licencia abierta SIL OFL), en `fuentes/inter/`; también están `montserrat/` y `spacegrotesk/`.

## Identidad (`identidad/identidad.json`)
Las librerías no llevan marca propia: leen la identidad del video (`herramientas/nucleo/_comun.py: identidad_efectiva`): `<canal>/identidad/identidad.json` (nombre, colores `BG/AMBAR/HUESO/TIERRA`, `logo` relativo al canal, `fuente` —inter, montserrat o space—, `voz`, `animacion`, `musica` con sus pistas y `efectos`) y, si el video declara base «propia», lo que cambie `<video>/identidad/identidad.json`. El video en curso es `HE_VIDEO` o la carpeta que contiene `06-montaje/` del script que se ejecuta; de ahí se deduce el canal (`<canal>/videos/<video>`). Sin archivo valen unos colores por defecto; sin logo se dibuja un disco ámbar.

## Animación (`catalogo/animaciones.json`)
Catálogo de estilos con su estado (`disponible`, `parcial`, `por construir`), puntuación, riesgo de políticas y cómo se hace; salió del análisis del video B20 del [resumen unificado](../../00-contexto/investigacion/resumen-videos-de-youtube.md). `python herramientas/montaje/catalogo/animaciones.py` lista las ofrecidas, `animaciones.py <id>` explica una y `animaciones.py <id> "<canal>/<n>" --aplicar` la guarda en la identidad propia del video. Normalmente la animación sale de la identidad del canal o del video (`herramientas/identidad/identidad.py`). Hoy solo `espacial` está lista del todo; `papel-recortado` tiene librerías (`papel.py`, `pintura.py`) pero sus escenas se diseñan una a una.

## Un video nuevo (tubería común)
`nuevo-video.py` deja en `videos/NN-nombre/06-montaje/` un `video.py` y un `montaje.json`. Flujo: guion → voz → `python herramientas/montaje/tuberia/alinear.py "<canal>/<n>"` (deja `tiempos.json`) → `python herramientas/video/escaleta-a-escenas.py "<canal>/<n>"` (deja `escenas.json`) → `python video.py --frame 60 f.png` desde `06-montaje/`. Todo lo común vive en `tuberia/pipeline.py` (fotogramas, rótulos, subtítulos, música, verificación «nada se tapa con nada», render en partes); las escenas pendientes salen como tarjetas de `animaciones/espacial/escenas_base.py`, las que traen tipo y datos se dibujan solas (ver «Escenas por datos») y cualquiera se reemplaza registrando una función por id. `montaje.json` admite `rotulos` (por frase del guion), `creditos`, `capitulos`, `musica` y `nombre`. `alinear.py` es único: detecta solo si la voz es de Polly (`04-voz/polly/parte-NN.txt`) o de Google y pesa las frases en consecuencia; admite `kmax` y `correcciones` en `montaje.json`.

## Escenas por datos (sin escribir código)
Un video nuevo se monta declarando sus escenas en `06-montaje/escenas.json`: cada una es un objeto `{id, nombre, ini, fin, tipo, …parámetros}` y la tubería la dibuja con las fábricas de `animaciones/espacial/escenas_datos.py` (el tipo `placeholder`, por defecto, deja una tarjeta pendiente). El esquema de cada tipo (parámetros, ejemplo) está en `catalogo/escenas.json`; `python herramientas/montaje/catalogo/escenas.py` lista los tipos, `escenas.py <tipo>` explica uno y `escenas.py --validar "<canal>/<n>"` revisa el `escenas.json` de un video. Un ejemplo completo, con un caso de cada tipo, está en [`plantillas/escenas-ejemplo.json`](plantillas/escenas-ejemplo.json) (los nombres de imagen son de ejemplo: guarda las tuyas en `05-licencias/originales/`).

| Tipo | Qué dibuja | Requeridos | Opcionales |
|---|---|---|---|
| `placeholder` | Tarjeta con id, nombre y descripción | — | `descripcion` |
| `portada` | Título grande y subtítulo | — | `titulo`, `subtitulo` |
| `texto` | Líneas grandes que aparecen una a una | `lineas` | — |
| `cifra` | Cifra grande con su unidad; con `rotulo`/`fuente` lleva el sello «Dato verificado» | `valor` | `unidad`, `etiqueta`, `detalle`, `color`, `eyebrow`, `titulo`, `ayuda` |
| `comparacion` | 2 o 3 valores en tarjetas de cristal | `items` `[{rotulo, valor, unidad?, detalle?, color?, t?}]` | `separador`, `eyebrow`, `titulo`, `ayuda` |
| `barras` | Barras horizontales que crecen desde 0, con eje y unidad | `items` `[{rotulo, valor, color?, t?}]` (2–8) | `unidad`, `sufijo`, `maximo`, `eyebrow`, `titulo`, `ayuda` |
| `linea_tiempo` | 2–7 hitos equiespaciados, con la etiqueta «ESQUEMA · SIN ESCALA» | `eventos` `[{fecha, texto, color?, t?}]` | `con_etiqueta_escala`, `eyebrow`, `titulo`, `ayuda` |
| `lista` | Panel con puntos que se encienden al ritmo de la voz | `puntos` (2–6 textos o `{texto, t?}`) | `titulo`, `eyebrow`, `numerada` |
| `imagen` | Imagen oficial con zoom lento: a pantalla completa o en marco redondeado (`marco: true`) sobre su fondo desenfocado | `archivo` | `zoom0`, `zoom1`, `centro0`, `centro1`, `marco`, `pie`, `credito` |
| `cita` | Cita textual con autor y fuente | `texto`, `autor` | `fuente`, `eyebrow`, `titulo`, `color` |
| `mapa` | Globo giratorio con 1–5 lugares numerados y su lista | `puntos` `[{nombre, lat, lon, detalle?, t?}]` | `titulo`, `eyebrow`, `giro` |
| `cierre` | Título (o lista de fuentes) y los botones suscribirse, me gusta y campanita | — | `titulo`, `subtitulo`, `fuentes`, `mensaje` |

**Claves comunes a todos los tipos**
- `rotulo` + `fuente` + `fila`: la escena muestra el rótulo «Dato verificado» (abajo a la izquierda) con la fuente como segunda línea; `fila` es el número de la cifra en `01-guion/verificacion-de-cifras.md` (la tubería avisa si esa fila no existe). `rotulo` puede ser un objeto `{l1, l2, estilo: "dato"|"calculo", desde, dur, frase}`; con estilo `calculo` sale «Cálculo propio». Una cifra, una fuente.
- `credito`: crédito de la imagen (arriba a la derecha) durante toda la escena.
- `t` (segundos desde el inicio de la escena) o `frase` (el comienzo de una frase del guion que está en `tiempos.json`, con `n` si se repite y `desde` para desplazarla): marca cuándo aparece la escena o cada elemento de una lista; así las animaciones siguen a la voz sin calcular tiempos. Sin ellos, los elementos se reparten parejo.
- Los números se escriben tal cual (`13.797`) y salen con formato español (`13,797`; `13797` → «13 797»); un texto se muestra como está. Los colores son `ambar`, `hielo`, `verde`, `rojo`, `hueso` o `[r, g, b]`.

**Reglas de composición que ya cumplen** (no hay que cuidarlas a mano): contenido en la zona segura, texto que baja de tamaño si no cabe en su caja, cajas con `ui.caja`, imágenes con esquinas redondeadas y borde suave, movimiento continuo, y nada bajo el rótulo, el crédito ni el capítulo (`python video.py --verificar` lo comprueba). Una imagen a pantalla completa con foto clara choca con el crédito y el rótulo: usa `marco: true`, o una foto oscura y sin rótulo. Las citas deben ser cortas y con comentario propio (regla 2 de políticas).

**Desde la escaleta.** `python herramientas/video/escaleta-a-escenas.py "<canal>/<n>"` lee la escaleta técnica y, si la fila de una escena trae una directiva entre comillas invertidas `` `@tipo clave=valor; clave=valor` ``, deja la escena ya diseñada; sin directiva queda como `placeholder`. Los valores son JSON si lo son (números, `true`, listas `[...]`, objetos `{...}`) o texto; el separador es `;` (nunca `|`, que rompe la tabla):

```
| **E03 · La cifra** | 00:16–00:28 | Cifra grande. `@cifra valor=13.797; unidad="miles de millones de años"; rotulo="Edad del universo (ΛCDM)"; fuente="Planck 2018"; fila=1` | Voz | Propio |
| **E07 · Hoy veremos** | 01:16–01:30 | `@lista titulo="Hoy vamos a ver tres cosas"; puntos=[{"texto":"El primer reloj","frase":"Vamos con el primero"},"El segundo","El tercero"]` | Voz | Propio |
```

Flujo sin código: `nuevo-video.py` → guion → voz → `alinear.py` → escaleta con directivas → `escaleta-a-escenas.py` → `python video.py --frame 60 f.png` y `--verificar`. Lo que un tipo no pueda hacer se diseña aparte con `P.registrar('E05', mi_funcion)` (ver `plantillas/plantilla_video.py`). Los videos 1 y 2 conservan sus scripts propios y no usan estos tipos.

## Ejemplos completos: videos 1 y 2
Los dos videos publicados conservan scripts propios, anteriores a la tubería común, en su carpeta `06-montaje/`:
- **Video 1** (`videos/01-voyager-1/06-montaje/`): `video01.py` dibuja las escenas (fotos oficiales, esquemas animados, rótulos, subtítulos) y renderiza en 4 procesos en paralelo; `borrador.py` (primeros 2 minutos, escenas que `video01.py` reutiliza); `dsn_voyager.py` (estaciones de la Red de Espacio Profundo y dirección de Voyager 1); `capitulos.py` (tiempos de capítulos para YouTube Studio); `miniaturas.py` (miniaturas en `../07-miniaturas/`); `_render_y_1440.sh` y `_hoja_fuentes.py` (auxiliares); `tiempos.json` (120 frases, 753,9 s, del audio definitivo) y `tiempos-095.json` (del primer audio).
- **Video 2** (`videos/02-edad-del-universo/06-montaje/`): `video02.py` (versión publicada, estilo espacial) y `video02_papel.py` (versión alternativa en papel recortado, sin publicar).

```powershell
cd "02-canales\hace-eones\videos\01-voyager-1\06-montaje"
python video01.py                     # -> salida\video-01-completo.mp4 (+ .srt)
python video01.py --frame 150 f.png   # un fotograma, para revisar el diseño
python borrador.py --frame 25.0 f.png # un fotograma del borrador
```
- Para cambiar un rótulo, una escena o un tiempo: listas `ROTULOS` y `ESCENAS` en `video01.py`; `T('inicio de la frase')` busca el tiempo de una frase del guion.
- Si cambias el guion o el audio: regenera el audio, ejecuta `python herramientas/montaje/tuberia/alinear.py "hace-eones/1"` y revisa que las proporciones sigan bien (hay una lista `CORRECCIONES` para tramos concretos).
- **Tiempos del video 1:** las escenas están escritas con `tiempos-095.json` (primer audio). `tiempos.json` es el del audio definitivo y `video01.py` traduce el tiempo (`t_viejo`) frase a frase, así que no hay que reescribir las escenas al cambiar la voz.
- **Música:** `06-montaje/musica/` con las pistas descargadas de la Biblioteca de audio (nombres que empiecen por *Event Horizon*, *Singularity*, *Spaghettification*). Se mezclan bajo la voz (baja sola al hablar) y se cortan con fundido. Si faltan, el video sale solo con voz. Las licencias están en `05-licencias/`.

## Estilo espacial
- `animaciones/espacial/estilo.py`: fondo (nebulosa + estrellas), brillo (`bloom`), marco HUD, paneles de cristal (`panel`), etiquetas con pastilla (`etq`, para que ninguna línea pase bajo el texto), texto/líneas con resplandor, planetas procedurales (`dibujar_planeta`) y vista oblicua del sistema solar (`Vista`).
- La escena de instrumentos del video 1 usa el diagrama oficial de la NASA (`05-licencias/originales/M12-diagrama-instrumentos.jpg`, convertido a tema oscuro).
- Regla de montaje: ningún texto debe quedar debajo de una línea; si hay riesgo, usar `etq` o mover el texto.
- `comun/ui.py`: rótulos «Dato verificado» / «Cálculo propio» con barrido de luz de entrada y salida, cajas de vidrio con esquinas cortadas, títulos con etiqueta, pastillas, iconos y anillos de progreso.
- `etiqueta_esquema()` («ESQUEMA · NO A ESCALA») solo se pone en escenas con tamaños o posiciones que no son reales (trayectoria, heliosfera, Oort, estrella). No es obligatoria por YouTube: es honestidad editorial.
- El video no lleva logo ni nombre del canal en la esquina (aparecen bajo el video y en la marca de agua de Studio).

## Tipografía, globo y datos
- **Tipografía:** Inter (SIL OFL), en `fuentes/inter/`. `comun/montar.py` elige la familia con la identidad (`fuente`) o la variable de entorno `HE_FUENTE` (`inter` por defecto, `montserrat`, `space`).
- **Globo de la Red de Espacio Profundo:** `animaciones/espacial/globo.py` dibuja la Tierra giratoria (general) con los continentes de Natural Earth (`animaciones/espacial/datos/ne_110m_land.geojson`, dominio público, descargado el 13-oct-2026 de github.com/nvkelso/natural-earth-vector). Las estaciones y la dirección de Voyager 1 (parámetros de esa escena) están en `videos/01-voyager-1/06-montaje/dsn_voyager.py`. La dirección de Voyager 1 es aproximada (ascensión recta ≈ 17 h 14 m, declinación ≈ +12°); por eso la escena lleva la etiqueta «ESQUEMA · POSICIÓN APROXIMADA».

## Límites actuales
- El estilo es de infografía documental limpia; no es una producción cinematográfica.
- Los efectos de sonido de la identidad solo están declarados: la tubería aún no los mezcla.
- Todo video se revisa antes de publicar (reglas 6 y 17) y las imágenes siguen en el registro de licencias.
