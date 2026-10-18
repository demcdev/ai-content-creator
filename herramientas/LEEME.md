# herramientas · programas que sirven a todos los canales

En la raíz solo está este `LEEME.md`; cada programa vive en la carpeta de su tema (las carpetas de código mezclan scripts y datos porque se ejecutan desde ahí). Todo se ejecuta desde la raíz del proyecto. **La entrada habitual es una sola:** `python herramientas/canal/canal.py <orden> ...` (`ayuda --corta` lista las órdenes; `siguiente <video>` hace lo automático y dice qué falta; `contexto <video> --para guion|revision|escaleta` da el contexto mínimo de cada paso). Los programas de abajo se pueden seguir llamando directamente: `python herramientas/<carpeta>/<programa>.py ...`.

| Carpeta | Qué hace | Programas principales |
|---|---|---|
| [canal/](canal/LEEME.md) | Punto de entrada único: delega en los demás y automatiza los pasos sin IA (incrementales por huellas) | `canal.py` |
| [video/](video/LEEME.md) | Ciclo de vida de un video | `nuevo-video.py` (crea la carpeta), `estado-video.py` (etapa y siguiente paso), `validar-video.py` (lint del guion), `verificar-cifras.py` (cifras contra su tabla, cuentas y fuentes), `escaleta-a-escenas.py` |
| [identidad/](identidad/LEEME.md) | Identidad de cada canal y de cada video | `identidad.py` |
| [validacion/](validacion/LEEME.md) | Que nada se rompa al renombrar o editar | `validar-proyecto.py` |
| [voz/](voz/LEEME.md) | Sintetizador de voz | `voces.py`, `sintetizar*.py/.mjs` |
| [montaje/](montaje/LEEME.md) | Render del video: librerías, tubería, catálogo de animaciones | `tuberia/alinear.py`, `catalogo/animaciones.py` |
| [panel/](panel/LEEME.md) | Servidor local para la pantalla «Producción» del selector de nichos (lee estado; crea videos, elige identidad, aprueba puertas y sella) | `servidor.py`, `iniciar-panel.cmd` (arranque con las claves de voz cifradas), `probar-servidor.py` |
| [sync/](sync/LEEME.md) | Genera los subagentes de Claude Code y Gemini CLI desde una sola fuente (`.agents/subagents/`) | `sync-agentes.py` |
| [nucleo/](nucleo/LEEME.md) | Biblioteca compartida por los programas anteriores | `_comun.py`, `requirements.txt` (dependencias de pip: `pip install -r herramientas/nucleo/requirements.txt`) |

Nombres y carpetas: [convencion-de-nombres.md](../00-contexto/produccion/convencion-de-nombres.md).
