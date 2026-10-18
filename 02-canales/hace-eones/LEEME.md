# Hace Eones · mapa de la carpeta

Canal de ciencia y universo. La estructura general y el flujo están en [estructura-de-un-canal.md](../../00-contexto/produccion/estructura-de-un-canal.md); los nombres, en [convencion-de-nombres.md](../../00-contexto/produccion/convencion-de-nombres.md). Aquí solo lo propio de este canal.

| Carpeta | Qué hay |
|---|---|
| `identidad/` | `identidad.json` (nombre, colores, logo, fuente, voz, animación, música; las librerías de montaje lo leen) e `identidad-del-canal.md` (promesa, tono, reglas editoriales y voz en uso) |
| `estrategia/` | `01-ideas-de-video.md` · `02-politicas-y-checklist.md` (lo lee el auditor) · `03-modelos-de-referencia.md` · `04-plan-de-90-dias.md` |
| `videos/` | Un video por carpeta: `01-voyager-1/` (publicado el 13-oct-2026) y `02-edad-del-universo/` (publicado) |

Los textos de ambos videos están corregidos; falta regenerar voz y video (ver memoria).

## Dónde se ejecuta cada cosa
- **Voz:** desde `herramientas/voz/` (raíz del proyecto) con `--salida` apuntando a `videos/NN-nombre/04-voz`.
- **Render y miniaturas:** desde `videos/NN-nombre/06-montaje/`; las librerías comunes se importan desde `herramientas/montaje/` (leen `identidad/identidad.json` del canal; `HE_VIDEO` indica el video en curso).
