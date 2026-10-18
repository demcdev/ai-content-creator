# Estructura de un canal y de un video (todos los canales)

Cada canal es una carpeta dentro de `02_canales/`. **Lo global del canal va en su raíz; todo lo de cada video, dentro de su carpeta.** Lo que sirve a todos los canales vive en `00_contexto/` y `herramientas/`.

## Raíz de un canal
| Archivo / carpeta | Qué es |
|---|---|
| `00 - Identidad del canal.md` | Nombre, promesa, tono, reglas editoriales y voz en uso (la comparativa de voces está en `00_contexto/`) |
| `02 - 12 ideas de video.md` | Banco de ideas |
| `03 - Politicas y checklist.md` | Checklist de políticas del nicho (lo lee el auditor) |
| `04 - Modelos de referencia.md` | Canales que se estudian (patrones, no copias) |
| `05 - Plan de 90 dias.md` | Calendario y metas |
| `identidad.json` | Nombre, colores, logo y fuente del canal (lo leen las librerías de montaje; sin logo dibujan un disco ámbar) |
| `Video NN - Nombre/` | Un video por carpeta |

## Un video = una carpeta
| Dentro | Qué guarda |
|---|---|
| `Guion.md` | Guion con marcas de verificación |
| `Escaleta audiovisual.md` | Un solo documento con dos partes: la **Planilla** de 3 columnas (fase 1, skill `guionista-retencion`) y la **escaleta técnica** por escenas con origen y licencia (fase 3, skill `escaleta-audiovisual`) |
| `Verificacion de cifras.md` | Cada cifra con fuente y fecha |
| `Revision/` | `Informe auditor-guion.md` e `Informe verificador.md` de los agentes revisores |
| `Capitulos y descripcion.md` | Descripción, capítulos, fuentes, transparencia |
| `Texto para subtitulos.txt` | Texto limpio para subtitular y para la voz (escenas y rótulos: en la escaleta) |
| `Miniaturas/` | Imágenes (el encargo va como sección dentro de `Capitulos y descripcion.md`) |
| `Registro de licencias.md` · `Licencias/` | Una fila por material; originales, fichas, música, capturas |
| `Voz/` · `Montaje/` · `Entregables/` | Audio, scripts del video y video final con `.srt` |
| `Metricas y seguimiento.md` | Números a 2–3, 7 y 28 días y decisiones |

## Crear un video nuevo
```bash
python herramientas/nuevo-video.py "<canal>" <n> "Nombre corto del video"
```
Crea la carpeta con todos los documentos de partida. No pisa nada y el canal debe existir.

## Flujo
checklist de escritura (`00_contexto/Checklist-escritura-guion.md`) → guion (`guionista-retencion`) → `validar-video.py` → `verificador` y `auditor` → sello → escaleta (`escaleta-audiovisual`) → voz → montaje → publicación → métricas.

## Herramientas globales (`herramientas/`)
`nuevo-video.py`, `validar-video.py`, `estado-video.py`, `respaldar.py`, `escaleta-a-escenas.py`, `voz/` (sintetizador de voz; `voces.json` lista las voces disponibles y Claude pregunta cuál usar en cada video) y `montaje/` (librerías de render y tubería de montaje). Las librerías de montaje son de todos los canales: toman nombre, colores, logo y fuente de `<canal>/identidad.json`; un video nuevo recibe de `nuevo-video.py` un `Montaje/video.py` de 10 líneas y un `montaje.json`; `escaleta-a-escenas.py` convierte la escaleta técnica en `Montaje/escenas.json` y `video.py --frame 60 f.png` ya muestra el video completo con tarjetas en las escenas pendientes, que se reemplazan una a una por escenas propias (`P.registrar('E07', fn)`). Los videos 1 y 2 conservan sus scripts propios (`video01.py`, `video02.py`).

## Técnica general (en `00_contexto/`)
- `Retencion-tecnicas-de-montaje.md` · `Voz-IA-comparativa.md` · `Checklist-escritura-guion.md` · `Politicas-YouTube-Cumplimiento.md` · `Reglas-detalladas.md`.

## Historial de la reorganización (17-oct-2026)
Se archivó y borró lo exploratorio (Andamio IA, Tarea-video, mascota, intermedios de render), el sintetizador de voz pasó a `herramientas/voz/`, los informes de agentes a `Revision/`, los documentos 06 y 07 a `00_contexto/` y la plantilla de video quedó en 7 documentos (la planilla de producción pasó a ser una sección de la escaleta). Los documentos de producción se dejaron planos en la raíz del video porque pertenecen a etapas distintas y los leen el lint y el estado; el problema de «qué hago ahora» lo resuelve `estado-video.py`. Las librerías de montaje pasaron a `herramientas/montaje/` y la identidad de cada canal quedó en su `identidad.json`.
