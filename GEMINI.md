@./AGENTS.md

## Gemini CLI

Las reglas y la estructura del proyecto están en `AGENTS.md` (se importa arriba). Esta sección es solo para lo que es propio de Gemini CLI.

- **Subagentes:** `.gemini/agents/` es **generado** desde `.agents/subagents/` con `python herramientas/sync/sync-agentes.py`. Un subagente no puede llamar a otro: orquesta desde la sesión principal.
- **Skills:** Gemini CLI las lee de `.agents/skills/` (`guionista-retencion` y `escaleta-audiovisual`); se activan por su descripción y Gemini pide confirmación antes de cargarlas.
- **Nombres de herramientas:** `AGENTS.md` usa los de Claude Code. «Grep» equivale a `grep_search`, «Read» a `read_file`, y la «herramienta de preguntas» a pedirle la decisión al usuario en la conversación.
- **Hooks:** no hay ninguno de Gemini configurado; la red de seguridad es el pre-commit de git (`.githooks/pre-commit`).
- **Panel:** `herramientas/panel/` solo funciona con Claude Code.
