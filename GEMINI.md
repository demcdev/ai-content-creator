@./AGENTS.md

## Antigravity CLI y Gemini CLI

Las reglas y la estructura del proyecto están en `AGENTS.md` (se importa arriba). Esta sección es solo para lo que es propio de las herramientas de Google.

- **Qué usar:** desde el 18-jun-2026 Gemini CLI ya no acepta el inicio de sesión con una cuenta personal de Google (error «This client is no longer supported for Gemini Code Assist for individuals»); sigue disponible con una clave de API de pago o con licencia Code Assist Standard o Enterprise. Para una cuenta personal, la herramienta de Google es **Antigravity CLI** (`agy`).
- **Instalar Antigravity CLI (Windows, PowerShell):** `irm https://antigravity.google/cli/install.ps1 | iex`; después abrir una terminal nueva y comprobar con `agy --version`. Conviene leer el script antes de ejecutarlo.
- **Comprobado el 18-oct-2026 con `agy` 1.4.2:** lee `AGENTS.md`, reconoce las skills `guionista-retencion` y `escaleta-audiovisual`, lista los subagentes `auditor` y `verificador` (los ubica en `.agents/subagents/`) y ejecuta los scripts de `herramientas/`. Para ver qué carga en la carpeta: `agy inspect`.
- **Gemini CLI (solo con clave de API de pago o licencia):** lo que sigue de esta sección.

- **Subagentes:** `.gemini/agents/` es **generado** desde `.agents/subagents/` con `python herramientas/sync/sync-agentes.py`. Un subagente no puede llamar a otro: orquesta desde la sesión principal.
- **Skills:** Gemini CLI las lee de `.agents/skills/` (`guionista-retencion` y `escaleta-audiovisual`); se activan por su descripción y Gemini pide confirmación antes de cargarlas.
- **Nombres de herramientas:** `AGENTS.md` usa los de Claude Code. «Grep» equivale a `grep_search`, «Read» a `read_file`, y la «herramienta de preguntas» a pedirle la decisión al usuario en la conversación.
- **Hooks:** no hay ninguno de Gemini configurado; la red de seguridad es el pre-commit de git (`.githooks/pre-commit`).
- **Panel:** `herramientas/panel/` solo funciona con Claude Code.
