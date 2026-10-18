# validacion/
Validador global: comprueba que nada se haya roto al renombrar, mover o editar archivos. No usa IA ni gasta tokens y tarda unos 2 segundos.

```bash
python herramientas/validacion/validar-proyecto.py            # revisa todo el proyecto
python herramientas/validacion/validar-proyecto.py --estricto # los avisos también fallan
python herramientas/validacion/validar-proyecto.py --vigilar  # revalida solo a cada cambio o renombre
python herramientas/validacion/validar-proyecto.py --memoria  # incluye la memoria de Claude (solo avisos)
```

**Qué revisa:** enlaces markdown y sus anclas; rutas y comandos citados entre comillas invertidas; sintaxis, rutas literales e imports de los `.py`; JSON válido; nombres y rutas obsoletos; archivos que se acaban de renombrar o borrar (git) y que otros archivos siguen citando; y, como avisos, la convención de nombres y la estructura (solo `LEEME.md` en la raíz de cada carpeta, carpetas por etapa en cada video). `ERROR` = algo está roto y el programa sale con código 1; `AVISO` = conviene mirarlo.

**Cuándo se ejecuta solo**
- **Claude Code:** `.claude/settings.json` lo lanza (`--hook`) después de cada `Write`, `Edit`, `MultiEdit` y de los comandos `Bash`/`PowerShell` que mueven, renombran o borran archivos. Si hay errores, se los devuelve a Claude para que los corrija.
- **Git:** `.githooks/pre-commit` lo corre antes de cada commit y lo cancela si hay errores. Se activa una vez por clon con `python herramientas/validacion/validar-proyecto.py --instalar-git`.
- **A mano o en una terminal aparte:** `--vigilar` cubre los cambios que hagas tú en el editor.

**Configuración:** `config.json` (carpetas excluidas, rutas generadas que no se exigen, patrones obsoletos con su mensaje, carpetas obligatorias de un video). Para citar a propósito un nombre antiguo, escribe `validar:ignorar` en esa línea (en un comentario HTML en `.md`, o `# validar:ignorar` en `.py`). Cuando cambies un nombre de carpeta o archivo, añade su patrón antiguo a `obsoletos` para que nadie vuelva a citarlo.
