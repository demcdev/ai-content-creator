# Librerías de montaje (compartidas por todos los videos)

> **Cómo está organizado (17-oct-2026):** en la raíz solo está este `LEEME.md`; todo lo demás va en carpetas, y cada carpeta nueva tiene su propio `LEEME.md`:
>
> | Carpeta | Qué contiene |
> |---|---|
> | `comun/` | Librerías que usan todos los estilos: `montar.py` (fuentes, imágenes, texto), `ui.py` (cajas, rótulos, créditos, capítulos) y `aa.py` (dibujo suavizado) |
> | `tuberia/` | `pipeline.py` (escenas → fotogramas → mp4) y `alinear.py` (voz → `tiempos.json`) |
> | `catalogo/` | `animaciones.json` (catálogo de estilos) y `animaciones.py` (lista y aplica un estilo) |
> | `plantillas/` | `plantilla_video.py`, la que copia `nuevo-video.py` a cada video |
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
`nuevo-video.py` deja en `videos/NN-nombre/06-montaje/` un `video.py` y un `montaje.json`. Flujo: guion → voz → `python herramientas/montaje/tuberia/alinear.py "<canal>/<n>"` (deja `tiempos.json`) → `python herramientas/video/escaleta-a-escenas.py "<canal>/<n>"` (deja `escenas.json`) → `python video.py --frame 60 f.png` desde `06-montaje/`. Todo lo común vive en `tuberia/pipeline.py` (fotogramas, rótulos, subtítulos, música, verificación «nada se tapa con nada», render en partes); las escenas pendientes salen como tarjetas de `animaciones/espacial/escenas_base.py` y se reemplazan registrando una función por id. `montaje.json` admite `rotulos` (por frase del guion), `creditos`, `capitulos`, `musica` y `nombre`. `alinear.py` es único: detecta solo si la voz es de Polly (`04-voz/polly/parte-NN.txt`) o de Google y pesa las frases en consecuencia; admite `kmax` y `correcciones` en `montaje.json`.

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
