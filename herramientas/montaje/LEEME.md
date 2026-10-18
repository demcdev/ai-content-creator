# Librerías de montaje (compartidas por todos los videos)

> **Cómo está organizado (13-oct-2026):** aquí quedan solo las **librerías comunes** (`montar.py`, `estilo.py`, `ui.py`, `aa.py`, `globo.py`, `fuentes/`, `datos/`).
> Los **scripts de cada video** (guion de escenas, tiempos, música, render, miniaturas) viven en la carpeta de ese video: `Video NN - Nombre/Montaje/`. Allí se ejecutan; ellos importan estas librerías solos.
> Ejemplo, video 1: `Video 01 - Voyager 1/Montaje/video01.py`. Los archivos que se citan abajo sin ruta (`video01.py`, `alinear.py`, `miniaturas.py`, `capitulos.py`, `tiempos.json`, `musica/`, `salida/`) están en esa carpeta.
> Rutas del video en curso: `montar.py` lee `HE_VIDEO` (carpeta del video; por defecto el video 1) para encontrar `Voz/` y `Licencias/originales/`.

Genera un video MP4 1080p a 30 fps a partir de:
- el **audio real** del video (`Video NN - Nombre/Voz/`),
- las **imágenes oficiales** guardadas en `Video NN - Nombre/Licencias/originales/`,
- **esquemas animados** hechos con código (cifras de la hoja «Verificacion de cifras» del video),
- **rótulos «Dato verificado»** y **subtítulos**, sincronizados con los silencios del audio.

## Identidad del canal (`identidad.json`)
Las librerías no llevan marca propia: leen `<canal>/identidad.json` (nombre, colores `BG/AMBAR/HUESO/TIERRA`, `logo` relativo al canal y `fuente`). El canal se deduce de la carpeta del video (`HE_VIDEO`, o la carpeta que contiene `Montaje/` del script que se ejecuta). Sin archivo valen los valores de Hace Eones; sin logo se dibuja un disco ámbar.

## Un video nuevo (tubería común)
`nuevo-video.py` deja en `Video NN/Montaje/` un `video.py` y un `montaje.json`. Flujo: guion → voz → `python herramientas/montaje/alinear.py "<video>"` (deja `tiempos.json`) → `python herramientas/escaleta-a-escenas.py "<video>"` (deja `escenas.json`) → `python video.py --frame 60 f.png`. Todo lo común vive en `pipeline.py` (fotogramas, rótulos, subtítulos, música, verificación «nada se tapa con nada», render en partes); las escenas pendientes salen como tarjetas de `escenas_base.py` y se reemplazan registrando una función por id. `montaje.json` admite `rotulos` (por frase del guion), `creditos`, `capitulos`, `musica` y `nombre`. `alinear.py` es único: detecta solo si la voz es de Polly (`Voz/polly/parte-NN.txt`) o de Google y pesa las frases en consecuencia; admite `kmax` y `correcciones` en `montaje.json`. Los videos 1 y 2 conservan sus `alinear.py` originales; el unificado da los mismos tiempos con los mismos textos.

## Video completo (13-oct-2026)
- `alinear.py` mide los silencios del audio y deja en `tiempos.json` el inicio y el fin de cada una de las **120 frases** del guion (validado a mano en el borrador).
- `video01.py` dibuja las 28 escenas (fotos oficiales, esquemas animados, rótulos, subtítulos) y renderiza el video completo en **4 procesos en paralelo**:
  ```powershell
  python video01.py          # -> salida\video-01-completo.mp4 (+ .srt), unos 10 minutos
  python video01.py --frame 150 f.png   # un fotograma, para revisar el diseño
  ```
- Para cambiar un rótulo, una escena o un tiempo: listas `ROTULOS` y `ESCENAS` en `video01.py`; `T('inicio de la frase')` busca el tiempo de una frase del guion.
- Si cambias el guion o el audio: regenera el audio, ejecuta `python alinear.py` y revisa que las proporciones sigan bien (hay una lista `CORRECCIONES` para tramos concretos).

## Uso (borrador de 2 minutos)
```powershell
cd "herramientas\montaje"   # el borrador del video 1; necesita HE_VIDEO con la carpeta del video
python montar.py                          # video completo del borrador -> salida\video-01-borrador-0-2min.mp4 (+ .srt)
python montar.py --frame 25.0 prueba.png  # solo un fotograma, para revisar el diseño sin renderizar todo
```
Requisitos: Python 3, `Pillow`, `numpy` y `ffmpeg` en el PATH. Tipografía: Segoe UI de Windows (**solo para el borrador**; la licencia para video monetizado está sin verificar, fila F1 del registro).

## Qué hay hecho
- **Borrador de 2 minutos** (0:00–1:59): gancho, presentación de la nave y primera parte del Acto 1.
- Escenas: `A1` distancia (animación), imagen de la sonda con zoom suave, lista de «cinco cosas», `A2` trayectoria (parte inicial).
- Los **tiempos** salen de los silencios del audio (`ffmpeg silencedetect`): cada bloque de subtítulos tiene su inicio y fin medidos.

## Cómo se ajusta
- **Tiempos de rótulos:** lista `ROTULOS` en `montar.py` (inicio, fin, línea 1, línea 2, estilo).
- **Subtítulos:** lista `BLOQUES` (texto, inicio, fin). El texto debe ser **idéntico al guion**.
- **Escenas:** lista `ESCENAS` (inicio, fin, función).
- **Colores y tamaños:** constantes al principio del archivo (azul noche `#0B1026`, ámbar `#F2B84B`, hueso `#F5F1E8`).

## Límites actuales
- Sin música (hay que descargarla de la YouTube Audio Library y mezclarla aparte).
- Estilo de infografía documental limpia; no es una producción cinematográfica.
- Es un borrador: se revisa siempre antes de publicar (reglas 6 y 17) y las imágenes siguen en el registro de licencias.

## Estilo espacial (v2 del video 1)
- `estilo.py`: fondo (nebulosa + estrellas), brillo (`bloom`), marco HUD, paneles de cristal (`panel`), etiquetas con pastilla (`etq`, para que ninguna línea pase bajo el texto), texto/líneas con resplandor, planetas procedurales (`dibujar_planeta`) y vista oblicua del sistema solar (`Vista`).
- `video01.py` usa esos módulos. La escena de instrumentos usa el diagrama oficial de la NASA (`originales/M12-diagrama-instrumentos.jpg`, convertido a tema oscuro). `video01_v1.py` es la primera versión (plana), `video01_v2.py` copia de la versión actual.
- Fotograma suelto para revisar: `python video01.py --frame 232 salida/prueba/f.png`.
- Regla de montaje: ningún texto debe quedar debajo de una línea; si hay riesgo, usar `etq` o mover el texto.

## Interfaz v3 (13-oct-2026)
- `ui.py`: marca del canal, rótulos «Dato verificado» / «Cálculo propio» con barrido de luz de entrada y salida, cajas de vidrio con esquinas cortadas, títulos con etiqueta, pastillas, iconos y anillos de progreso.
- `etiqueta_esquema()` («ESQUEMA · NO A ESCALA») solo se pone en escenas con tamaños o posiciones que no son reales (trayectoria, heliosfera, Oort, estrella). No es obligatoria por YouTube: es honestidad editorial.
- **Tiempos:** las escenas están escritas con `tiempos_095.json` (primer audio). `tiempos.json` es el del audio definitivo (`python alinear.py`) y `video01.py` traduce el tiempo (`t_viejo`) frase a frase, así que no hay que reescribir las escenas al cambiar la voz. Los subtítulos y la duración usan los tiempos nuevos.
- **Música:** `musica/` con las pistas descargadas de la Biblioteca de audio (nombres que empiecen por *Event Horizon*, *Singularity*, *Spaghettification*). `video01.py` las mezcla bajo la voz (baja sola al hablar) y las corta con fundido. Si faltan, el video sale solo con voz.
- `capitulos.py`: tiempos de capítulos para YouTube Studio con el audio final.
- `miniaturas.py`: miniaturas A, B y C en `../Miniaturas/` (dentro de la carpeta del video).

## Tipografía, globo y datos (13-oct-2026)
- **Tipografía:** Inter (SIL OFL), en `fuentes/inter/`. `montar.py` elige la familia con la variable de entorno `HE_FUENTE` (`inter` por defecto, `montserrat`, `space`, `segoe`). Las otras dos fuentes abiertas se dejaron en `fuentes/` por si se quiere comparar.
- **Globo de la Red de Espacio Profundo:** `globo.py` dibuja la Tierra giratoria con los continentes de Natural Earth (`datos/ne_110m_land.geojson`, dominio público, descargado el 13-oct-2026 de github.com/nvkelso/natural-earth-vector). La dirección de Voyager 1 es aproximada (ascensión recta ≈ 17 h 14 m, declinación ≈ +12°); por eso la escena lleva la etiqueta «ESQUEMA · POSICIÓN APROXIMADA».
- El video ya no lleva logo ni nombre del canal en la esquina (aparecen bajo el video y en la marca de agua de Studio).
