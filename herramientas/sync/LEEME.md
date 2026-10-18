# sync · una sola fuente para los subagentes de cada herramienta de IA

Claude Code y Gemini CLI leen los subagentes de carpetas distintas y con campos distintos. Para no mantener dos copias, **se edita una sola** y este programa genera las demás.

| | Ruta | ¿Se edita? |
|---|---|---|
| Fuente | `.agents/subagents/<nombre>.md` | **Sí** |
| Generado para Claude Code | `.claude/agents/<nombre>.md` | No |
| Generado para Gemini CLI | `.gemini/agents/<nombre>.md` | No |
| Skills (fuente) | `.agents/skills/<skill>/SKILL.md` | **Sí** (Gemini la lee directo; Claude Code usa una copia en la carpeta .claude/skills, que este programa crea) |

## Uso

Desde la raíz del proyecto:

- `python herramientas/sync/sync-agentes.py` genera lo que falte o haya cambiado.
- `python herramientas/sync/sync-agentes.py --seco` dice qué cambiaría, sin escribir.
- `python herramientas/sync/sync-agentes.py --revisar` solo comprueba (código 1 si algo está desactualizado). Lo ejecuta el pre-commit (`.githooks/pre-commit`).

## Formato de un subagente fuente

Mira `.agents/subagents/auditor.md`. El bloque inicial lleva los datos comunes y, aparte, lo que solo entiende cada herramienta; el cuerpo (las instrucciones) se copia tal cual a ambas.

```
---
name: auditor
description: Cuándo usarlo y qué devuelve (en una sola línea)
tools: read, search, find, shell, write
claude:
  model: sonnet
  maxTurns: 20
gemini:
  max_turns: 20
---
(instrucciones)
```

- `name` debe coincidir con el nombre del archivo.
- `tools` usa nombres neutros; el programa los traduce:

| Neutro | Claude Code | Gemini CLI |
|---|---|---|
| `read` | `Read` | `read_file` |
| `search` | `Grep` | `grep_search` |
| `find` | `Glob` | `glob` |
| `shell` | `Bash` | `run_shell_command` |
| `write` | `Write` | `write_file` |
| `edit` | `Edit` | `replace` |
| `web_fetch` | `WebFetch` | `web_fetch` |
| `web_search` | `WebSearch` | `google_web_search` |

- Bloque `claude:`: se copia tal cual al frontmatter de Claude Code (`model`, `maxTurns`, `effort`, `color`, `omitClaudeMd`…).
- Bloque `gemini:`: se copia tal cual al de Gemini CLI (`max_turns`, `timeout_mins`, `temperature`…). Si no se pone `model`, Gemini usa el de la sesión.
- A la versión de Gemini se le añade al final una nota con la equivalencia de nombres de herramientas, porque las instrucciones nombran las de Claude Code.

## Límites

- En Gemini CLI un subagente no puede llamar a otro.
- Un archivo de `.claude/agents/` o `.gemini/agents/` sin fuente se avisa pero no se borra.
- Para añadir otra herramienta de IA, agregar su generador en `sync-agentes.py` (`GENERADORES`).
