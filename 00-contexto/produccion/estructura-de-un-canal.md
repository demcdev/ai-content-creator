# Estructura de un canal y de un video (todos los canales)

> La regla de nombres, las tablas de carpetas y el significado de cada una están en [convencion-de-nombres.md](convencion-de-nombres.md). Aquí: cómo se usa.

Cada canal es una carpeta dentro de `02-canales/` con tres partes: `identidad/`, `estrategia/` y `videos/`. **Lo global del canal va fuera de `videos/`; todo lo de cada video, dentro de su carpeta.** Lo que sirve a todos los canales vive en `00-contexto/` y `herramientas/`.

```
02-canales/<canal>/
  LEEME.md
  identidad/        identidad.json · identidad-del-canal.md
  estrategia/       01-ideas-de-video.md · 02-politicas-y-checklist.md · 03-modelos-de-referencia.md · 04-plan-de-90-dias.md
  videos/
    NN-nombre/
      LEEME.md      estado del video
      identidad/    identidad.json del video
      01-guion/  02-revision/  03-escaleta/  04-voz/  05-licencias/  06-montaje/  07-miniaturas/  08-entregables/  09-publicacion/  _archivo/
```

## Crear un canal nuevo
Copiar la estructura de arriba (carpetas `identidad/`, `estrategia/`, `videos/` y un `LEEME.md`), con el nombre del canal en `kebab-case`. Antes del primer video, definir su identidad: `python herramientas/identidad/identidad.py canal "<canal>" --voz <id> --animacion <id> ...`.

## Crear un video nuevo
```bash
python herramientas/video/nuevo-video.py "<canal>" <n> "Nombre corto del video"
```
Crea `videos/NN-nombre-corto/` con todas las carpetas por etapa y los documentos de partida. No pisa nada y el canal debe existir.

## Flujo
checklist de escritura (`00-contexto/produccion/checklist-escritura-guion.md`) → guion (`guionista-retencion`) → `validar-video.py` → `verificador` y `auditor` → sello → escaleta (`escaleta-audiovisual`) → voz → `alinear.py` → montaje → publicación → métricas. `estado-video.py` dice en qué etapa va el video y cuál es el siguiente paso.

## Herramientas globales (`herramientas/`)
Una carpeta por tema (ver `herramientas/LEEME.md`): `video/` (`nuevo-video.py`, `validar-video.py`, `estado-video.py`, `escaleta-a-escenas.py`), `identidad/` (`identidad.py`: identidad del canal y del video; Claude pregunta al crear cada video si usa la del canal o una propia), `validacion/` (`validar-proyecto.py`: revisa enlaces, referencias y nombres tras cada cambio), `nucleo/` (`_comun.py`), `voz/` (sintetizador de voz; `voces.json` lista las voces disponibles y Claude pregunta cuál usar en cada video) y `montaje/` (librerías de render, tubería y catálogo de animaciones; ver su `LEEME.md`). Las librerías de montaje son de todos los canales: toman nombre, colores, logo y fuente de `<canal>/identidad/identidad.json`. Un video nuevo recibe de `nuevo-video.py` un `06-montaje/video.py` de pocas líneas y un `montaje.json`; `escaleta-a-escenas.py` convierte la escaleta técnica en `06-montaje/escenas.json` y `video.py --frame 60 f.png` ya muestra el video completo con tarjetas en las escenas pendientes, que se reemplazan una a una por escenas propias (`P.registrar('E07', fn)`). Los videos 1 y 2 conservan sus scripts propios (`video01.py`, `video02.py`).

## Técnica general (en `00-contexto/`)
- `produccion/`: `retencion-tecnicas-de-montaje.md` · `voz-ia-comparativa.md` · `checklist-escritura-guion.md` · `convencion-de-nombres.md`.
- `politicas/`: `politicas-youtube-cumplimiento.md` · `reglas-detalladas.md`.

## Historial
- **17-oct-2026 (1):** se archivó y borró lo exploratorio, el sintetizador de voz pasó a `herramientas/voz/`, los informes de agentes a `02-revision/` y la plantilla de video quedó en 7 documentos.
- **17-oct-2026 (2):** convención de nombres única. Todo en `kebab-case`; los documentos de producción de cada video se agruparon en una carpeta por etapa (`01-guion` … `09-publicacion`); cada canal separó `identidad/`, `estrategia/` y `videos/`; `00-contexto/` y `01-nicho/` se subdividieron por tema. Los scripts leen los nombres de `herramientas/nucleo/_comun.py`.
- **18-oct-2026 (1):** estándar multi-herramienta. `AGENTS.md` es la fuente de las reglas; `CLAUDE.md` y `GEMINI.md` lo importan y añaden solo lo propio de cada herramienta. Skills y subagentes viven en `.agents/` y `herramientas/sync/sync-agentes.py` genera las copias de `.claude/` y `.gemini/` (copias y no enlaces simbólicos, porque Claude Code solo lee `.claude/` y en Windows los enlaces son frágiles). El panel sigue siendo solo para Claude Code (usa `claude -p`).
- **18-oct-2026 (2):** orden y reproducibilidad. `.gitattributes` (los saltos de línea CRLF/LF marcaban cambios falsos), `.editorconfig`, `herramientas/nucleo/requirements.txt` y `.env.example` (las claves no se leen de ningún `.env`: van en el Administrador de credenciales o en la sesión). Las capturas de música con «♪» en el nombre pasaron a `musica-N-…`.
- **18-oct-2026 (3):** Gemini CLI ya no admite cuentas personales de Google desde el 18-jun-2026. En este equipo se usa Antigravity CLI (`agy`), que se comprobó que lee `AGENTS.md`, las skills y los subagentes. **Pendiente:** copia de seguridad de los medios (unos 3 GB de `02-canales/` fuera de git), un ejecutor común de tests y archivar los videos ya publicados.
