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
> Los **scripts de cada video** (guion de escenas, tiempos, música, render, miniaturas) viven en la carpeta de ese video: `videos/NN-nombre/06-montaje/`. Allí se ejecutan; ellos importan estas librerías solos.
> Ejemplo, video 1: `videos/01-voyager-1/06-montaje/video01.py`. Los archivos que se citan abajo sin ruta (`video01.py`, `alinear.py`, `miniaturas.py`, `capitulos.py`, `tiempos.json`, `musica/`, `salida/`) están en esa carpeta.
> Rutas del video en curso: `montar.py` lee `HE_VIDEO` (o deduce la carpeta del video desde el script que se ejecuta) para encontrar `05-licencias/originales/` y la identidad del canal.

Genera un video MP4 1080p a 30 fps a partir de:
- el **audio real** del video (`videos/NN-nombre/04-voz/`),
- las **imágenes oficiales** guardadas en `videos/NN-nombre/05-licencias/originales/`,
- **esquemas animados** hechos con código (cifras de la hoja «verificacion-de-cifras.md» del video),
- **rótulos «Dato verificado»** y **subtítulos**, sincronizados con los silencios del audio.

## Identidad del canal (`identidad.json`)
Las librerías no llevan marca propia: leen la identidad del video (`herramientas/_comun.py: identidad_efectiva`): `<canal>/identidad.json` (nombre, colores `BG/AMBAR/HUESO/TIERRA`, `logo` relativo al canal, `fuente` —inter, montserrat o space—, `voz`, `animacion`, `musica` con sus pistas y `efectos`) y, si el video declara base «propia», lo que cambie `<video>/identidad/identidad.json`. El canal se deduce de la carpeta del video (`HE_VIDEO`, o la carpeta que contiene `06-montaje/` del script que se ejecuta). Sin archivo valen unos colores por defecto; sin logo se dibuja un disco ámbar.

## Animación (`animaciones.json`)
Catálogo de estilos con su estado (`disponible`, `parcial`, `por construir`), puntuación, riesgo de políticas y cómo se hace; salió del análisis del video B20 del resumen. `python herramientas/montaje/catalogo/animaciones.py` lista las ofrecidas, `animaciones.py <id>` explica una y `animaciones.py <id> "<video>" --aplicar` la guarda en la identidad propia del video. Normalmente la animación sale de la identidad del canal o del video (`herramientas/identidad.py`). Hoy solo `espacial` está lista del todo; `papel-recortado` tiene librerías (`papel.py`, `pintura.py`) pero sus escenas se diseñan una a una.

## Un video nuevo (tubería común)
`nuevo-video.py` deja en `videos/NN-nombre/06-montaje/` un `video.py` y un `montaje.json`. Flujo: guion → voz → `python herramientas/montaje/tuberia/alinear.py "<video>"` (deja `tiempos.json`) → `python herramientas/escaleta-a-escenas.py "<video>"` (deja `escenas.json`) → `python video.py --frame 60 f.png`. Todo lo común vive en `pipeline.py` (fotogramas, rótulos, subtítulos, música, verificación «nada se tapa con nada», render en partes); las escenas pendientes salen como tarjetas de `escenas_base.py` y se reemplazan registrando una función por id. `montaje.json` admite `rotulos` (por frase del guion), `creditos`, `capitulos`, `musica` y `nombre`. `alinear.py` es único: detecta solo si la voz es de Polly (`04-voz/polly/parte-NN.txt`) o de Google y pesa las frases en consecuencia; admite `kmax` y `correcciones` en `montaje.json`.

## Video completo (13-oct-2026)
- `alinear.py` mide los silencios del audio y deja en `tiempos.json` el inicio y el fin de cada una de las **120 frases** del guion (validado a mano en el borrador).
- `video01.py` dibuja las 28 escenas (fotos oficiales, esquemas animados, rótulos, subtítulos) y renderiza el video completo en **4 procesos en paralelo**:
  ```powershell
  python video01.py          # -> salida\video-01-completo.mp4 (+ .srt), unos 10 minutos
  python video01.py --frame 150 f.png   # un fotograma, para revisar el diseño
  ```
- Para cambiar un rótulo, una escena o un tiempo: listas `ROTULOS` y `ESCENAS` en `video01.py`; `T('inicio de la frase')` busca el tiempo de una frase del guion.
- Si cambias el guion o el audio: regenera el audio, ejecuta `python alinear.py` y revisa que las proporciones sigan bien (hay una lista `CORRECCIONES` para tramos concretos).

## Borrador del video 1
El borrador de los primeros minutos del video 1 (escenas A1, A2 y la lista de «cinco cosas», que `video01.py` reutiliza) vive en `videos/01-voyager-1/06-montaje/borrador.py`, no aquí:
```powershell
cd "02-canales\<canal>ideos-voyager-1-montaje"
python borrador.py                          # render del borrador -> salida\video-01-borrador-0-2min.mp4 (+ .srt)
python borrador.py --frame 25.0 prueba.png  # solo un fotograma
```
Requisitos: Python 3, `Pillow`, `numpy` y `ffmpeg` en el PATH. Tipografía: Inter (licencia abierta SIL OFL), en `fuentes/inter/`.

## Qué hay hecho
- **Borrador de 2 minutos** (0:00–1:59): gancho, presentación de la nave y primera parte del Acto 1.
- Escenas: `A1` distancia (animación), imagen de la sonda con zoom suave, lista de «cinco cosas», `A2` trayectoria (parte inicial).
- Los **tiempos** salen de los silencios del audio (`ffmpeg silencedetect`): cada bloque de subtítulos tiene su inicio y fin medidos.

## Cómo se ajusta
- **Tiempos de rótulos (borrador):** lista `ROTULOS` en `videos/01-voyager-1/06-montaje/borrador.py` (inicio, fin, línea 1, línea 2, estilo).
- **Subtítulos:** lista `BLOQUES` (texto, inicio, fin). El texto debe ser **idéntico al guion**.
- **Escenas:** lista `ESCENAS` (inicio, fin, función).
- **Colores y tamaños:** constantes al principio del archivo (azul noche `#0B1026`, ámbar `#F2B84B`, hueso `#F5F1E8`).

## Límites actuales
- Sin música (hay que descargarla de la YouTube Audio Library y mezclarla aparte).
- Estilo de infografía documental limpia; no es una producción cinematográfica.
- Es un borrador: se revisa siempre antes de publicar (reglas 6 y 17) y las imágenes siguen en el registro de licencias.

## Estilo espacial (v2 del video 1)
- `animaciones/espacial/estilo.py`: fondo (nebulosa + estrellas), brillo (`bloom`), marco HUD, paneles de cristal (`panel`), etiquetas con pastilla (`etq`, para que ninguna línea pase bajo el texto), texto/líneas con resplandor, planetas procedurales (`dibujar_planeta`) y vista oblicua del sistema solar (`Vista`).
- `video01.py` usa esos módulos. La escena de instrumentos usa el diagrama oficial de la NASA (`originales/M12-diagrama-instrumentos.jpg`, convertido a tema oscuro). `video01_v1.py` es la primera versión (plana), `video01_v2.py` copia de la versión actual.
- Fotograma suelto para revisar: `python video01.py --frame 232 salida/prueba/f.png`.
- Regla de montaje: ningún texto debe quedar debajo de una línea; si hay riesgo, usar `etq` o mover el texto.

## Interfaz v3 (13-oct-2026)
- `ui.py`: marca del canal, rótulos «Dato verificado» / «Cálculo propio» con barrido de luz de entrada y salida, cajas de vidrio con esquinas cortadas, títulos con etiqueta, pastillas, iconos y anillos de progreso.
- `etiqueta_esquema()` («ESQUEMA · NO A ESCALA») solo se pone en escenas con tamaños o posiciones que no son reales (trayectoria, heliosfera, Oort, estrella). No es obligatoria por YouTube: es honestidad editorial.
- **Tiempos:** las escenas están escritas con `tiempos_095.json` (primer audio). `tiempos.json` es el del audio definitivo (`python alinear.py`) y `video01.py` traduce el tiempo (`t_viejo`) frase a frase, así que no hay que reescribir las escenas al cambiar la voz. Los subtítulos y la duración usan los tiempos nuevos.
- **Música:** `musica/` con las pistas descargadas de la Biblioteca de audio (nombres que empiecen por *Event Horizon*, *Singularity*, *Spaghettification*). `video01.py` las mezcla bajo la voz (baja sola al hablar) y las corta con fundido. Si faltan, el video sale solo con voz.
- `capitulos.py`: tiempos de capítulos para YouTube Studio con el audio final.
- `miniaturas.py`: miniaturas A, B y C en `../07-miniaturas/` (dentro de la carpeta del video).

## Tipografía, globo y datos (13-oct-2026)
- **Tipografía:** Inter (SIL OFL), en `fuentes/inter/`. `montar.py` elige la familia con la variable de entorno `HE_FUENTE` (`inter` por defecto, `montserrat`, `space`). Las otras dos fuentes abiertas se dejaron en `fuentes/` por si se quiere comparar.
- **Globo de la Red de Espacio Profundo:** `animaciones/espacial/globo.py` dibuja la Tierra giratoria (general) con los continentes de Natural Earth (`animaciones/espacial/datos/ne_110m_land.geojson`, dominio público, descargado el 13-oct-2026 de github.com/nvkelso/natural-earth-vector). Las estaciones y la dirección de Voyager 1 (parámetros de esa escena) están en `videos/01-voyager-1/06-montaje/dsn_voyager.py`. La dirección de Voyager 1 es aproximada (ascensión recta ≈ 17 h 14 m, declinación ≈ +12°); por eso la escena lleva la etiqueta «ESQUEMA · POSICIÓN APROXIMADA».
- El video ya no lleva logo ni nombre del canal en la esquina (aparecen bajo el video y en la marca de agua de Studio).
