@AGENTS.md

## Claude Code

Las reglas y la estructura del proyecto están en `AGENTS.md` (se importa arriba): no las repitas aquí. Esta sección es solo para lo que es propio de Claude Code.

- **Subagentes:** `.claude/agents/` es **generado** desde `.agents/subagents/` con `python herramientas/sync/sync-agentes.py`. Edita siempre la fuente y vuelve a generar.
- **Skills:** `.claude/skills/` es una copia **generada** desde `.agents/skills/` con el mismo comando. Si las mismas skills siguen en `~/.claude/skills/`, la versión global puede tener prioridad sobre la del proyecto: bórralas de ahí para no tener dos.
- **Hook de validación** (PostToolUse): `.claude/settings.json`.
- **Panel:** `herramientas/panel/` lanza Claude Code con `claude -p`; solo funciona con Claude Code.
