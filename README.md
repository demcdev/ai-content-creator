# AI Content Creator

Pipeline de producción de contenido con IA: de la idea al video publicado, con revisión de políticas en cada paso. Hoy produce para **YouTube**; la estructura está pensada para crecer a otras plataformas (TikTok, Instagram, Facebook…).

## Qué hace

```
nicho → guion → revisión (políticas + cifras) → escaleta → voz → montaje → miniaturas → publicación
```

- **Guiones** con técnicas de retención (gancho, bucles abiertos, una sola CTA).
- **Revisión automática**: lint del guion, subagentes `auditor` (políticas de YouTube) y `verificador` (cifras contra fuentes).
- **Voz IA** declarada, con catálogo de voces por canal.
- **Montaje por código**: animaciones propias e imágenes oficiales con licencia, con verificación de solapes antes de renderizar.
- **Miniaturas** definidas como datos y generadas por script.
- **Registro de licencias** de cada asset y historial de producción como prueba de autoría.

## Estructura

| Carpeta | Contenido |
|---|---|
| `00-contexto/` | Políticas de YouTube, guías de producción e investigación |
| `01-nicho/` | Análisis de nichos |
| `02-canales/` | Un canal por carpeta (`identidad/`, `estrategia/`, `videos/`) |
| `herramientas/` | Programas compartidos: `canal`, `video`, `voz`, `montaje`, `identidad`, `validacion`, `panel`, `sync`, `nucleo` |
| `.agents/` | Fuente única de los subagentes de revisión; `.claude/agents/` y `.gemini/agents/` se generan de aquí |

Cada video vive en `02-canales/<canal>/videos/NN-nombre/` con una carpeta por etapa (`01-guion` … `09-publicacion`).

Las instrucciones para los agentes de IA (Claude Code, Antigravity CLI, Gemini CLI y otros) están en [`AGENTS.md`](AGENTS.md); `CLAUDE.md` y `GEMINI.md` solo lo importan y añaden lo propio de cada herramienta.

## Cómo se usa

Este proyecto **no es una aplicación que se enciende**: es un espacio de trabajo donde cada video avanza por etapas. En cada etapa trabaja una de tres cosas:

| Quién | Qué hace | Ejemplo |
|---|---|---|
| **Tú** | Decides y apruebas | Elegir la idea, aprobar el guion, subir el video a YouTube Studio |
| **El agente de IA** (Claude Code o Antigravity CLI, abierto en esta carpeta) | Los pasos creativos: escribir, revisar, hacer la escaleta | Le escribes «sigue con el video 3» y usa las skills y subagentes de `.agents/` |
| **Los scripts** (`herramientas/`) | Lo automático, sin IA y gratis | Validar el guion, alinear la voz, generar escenas, montar el video |

Todos los scripts se lanzan por **una sola entrada**, desde la raíz del proyecto:

```bash
python herramientas/canal/canal.py ayuda --corta             # lista todas las órdenes
python herramientas/canal/canal.py siguiente "hace-eones/3"  # hace lo automático y te dice qué falta
```

`"hace-eones/3"` es `<canal>/<número de video>`. `siguiente` es la orden que más vas a usar: ejecuta los pasos automáticos que toquen y **se detiene en el primer paso que necesita a una persona o a la IA**, diciendo cuál es y con qué comando, skill o subagente.

### El camino de un video

| # | Etapa | Quién | Orden o herramienta |
|---|---|---|---|
| 1 | Crear la carpeta del video | Script | `canal.py nuevo "<canal>" <n> "Nombre corto"` |
| 2 | Idea y guion | IA (skill `guionista-retencion`) | Se lo pides al agente |
| 3 | Comprobar el guion | Script | `canal.py validar "<canal>/<n>"` |
| 4 | Revisar políticas y cifras | IA (subagentes `auditor` y `verificador`) | Se lo pides al agente |
| 5 | Escaleta de imagen y sonido | IA (skill `escaleta-audiovisual`) | Se lo pides al agente |
| 6 | Voz | Script (necesita claves, ver abajo) | `canal.py voz "<canal>/<n>"` muestra los comandos de la voz del video |
| 7 | Alinear voz y escenas | Script, solo si algo cambió | `canal.py siguiente ...` (o `alinear` y `escenas`) |
| 8 | Montaje y render | Script | `canal.py montar "<canal>/<n>"` |
| 9 | Publicación | Script y tú | `canal.py publicar "<canal>/<n>"` prepara el lint final y la lista de entregables; **no sube nada**: la subida la haces tú en YouTube Studio |

En cualquier momento, `canal.py estado "<canal>/<n>"` dice en qué etapa va un video y `canal.py revisar-proyecto` comprueba nombres, enlaces y estructura de todo el proyecto.

### Primera vez en un PC

1. Instalar Python 3 y Node.js, y tener `ffmpeg` en el PATH.
2. `pip install -r herramientas/nucleo/requirements.txt` (dependencias en [`requirements.txt`](herramientas/nucleo/requirements.txt)).
3. Guardar las claves de voz una sola vez (sección siguiente).
4. Para trabajar con un agente de IA: abrir Claude Code (`claude`) o Antigravity CLI (`agy`) en esta carpeta; ambos leen `AGENTS.md`. Gemini CLI ya no admite cuentas personales de Google; ver [`GEMINI.md`](GEMINI.md).

## Panel y claves de voz

El panel es una interfaz local para lanzar los pasos de un video. La voz necesita claves (Amazon Polly y/o Google); se guardan **cifradas en el Administrador de credenciales de Windows**, nunca en un archivo del repositorio. Se usan estos dos comandos, desde una terminal en la raíz del proyecto:

| Comando | Para qué sirve | Cuándo se ejecuta |
|---|---|---|
| `herramientas\panel\iniciar-panel.cmd -Configurar` | Pide cada clave (se oculta al escribir) y la guarda cifrada con tu cuenta de Windows. Un Enter vacío conserva la que ya estaba guardada. | **Una sola vez** por PC o cuenta de Windows, antes de usar el panel por primera vez. Se repite solo si cambias o rotas una clave. |
| `herramientas\panel\iniciar-panel.cmd` | Carga las claves guardadas **solo en esa ventana** y enciende el servidor del panel (http://127.0.0.1:8765). | **Cada vez** que vayas a trabajar con el panel. Si cierras la ventana, las claves se van de la memoria. |

Otras dos opciones del mismo comando: `-SoloComprobar` (dice qué claves hay guardadas, solo los nombres, y no enciende nada) y `-Olvidar` (borra las guardadas). Los nombres de las variables están en [`.env.example`](.env.example); el detalle completo, en [`herramientas/panel/LEEME.md`](herramientas/panel/LEEME.md).

Si no usas el panel, define las claves a mano en la sesión de PowerShell (por ejemplo `$env:GOOGLE_TTS_API_KEY = "..."`); duran solo mientras esa ventana esté abierta.

## Qué no se versiona

Audio, video y renders (`*.mp4`, `*.wav`, `*.mp3`, `salida/`, `cache*/`), claves y transcripciones de agentes. Ver `.gitignore`.

## Cumplimiento

Todo el contenido debe respetar las políticas de YouTube (contenido original, copyright, IA declarada, apto para anunciantes). Detalle en `00-contexto/politicas/`.
