# Hace Eones · mapa de la carpeta

Canal de ciencia y universo. La estructura general (raíz de un canal, un video = una carpeta, cómo crear uno nuevo y el flujo) está en [Estructura-de-un-canal.md](../../00_contexto/Estructura-de-un-canal.md). Aquí solo lo propio de este canal.

| Archivo / carpeta | Qué es |
|---|---|
| `00 - Identidad del canal.md` · `02` · `03` · `04` · `05` | Documentos del canal (ver la estructura general). La voz en uso está en la `00`. |
| `identidad.json` | Nombre, colores, logo y fuente del canal; las librerías globales de montaje lo leen |

Videos hechos: `Video 01 - Voyager 1/` (publicado el 13-oct-2026) · `Video 02 - Edad del universo/` (publicado). Los textos de ambos están corregidos; falta regenerar voz y video (ver memoria).

## Dónde se ejecuta cada cosa
- **Voz:** desde `herramientas/voz/` (raíz del proyecto) con `--salida` apuntando a `Video NN - …/Voz`.
- **Render y miniaturas:** desde `Video NN - …/Montaje/`; las librerías comunes se importan desde `herramientas/montaje/` (leen `identidad.json` del canal) (`HE_VIDEO` indica el video en curso).
