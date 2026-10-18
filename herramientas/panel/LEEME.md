# panel · servidor local para la interfaz

Servidor que le cuenta a una interfaz lo que el framework ya sabe (canales, videos, etapas, sellos, identidad, «siguiente paso») y le deja ejecutar un conjunto **cerrado** de acciones: las que delegan en los programas de `herramientas/` y, para los pasos de IA que lo permiten, Claude Code sin pantalla. La interfaz es la pantalla **Producción** de `Proyectos-dev\selector-nichos` (repo aparte).

```
python herramientas/panel/servidor.py            # http://127.0.0.1:8765  (--puerto N para cambiarlo); sin claves de voz
herramientas\panel\iniciar-panel.cmd          # lo mismo, con las claves de voz guardadas (ver abajo)
python herramientas/panel/probar-servidor.py     # prueba completa en una copia temporal, con un «claude» falso; no gasta nada ni toca tu proyecto
```

Archivos: `servidor.py` (rutas y seguridad) · `ejecutor.py` (lanza y vigila Claude Code y los comandos) · `pasos.json` (instrucción y permisos de cada paso) · `iniciar-panel.cmd` / `.ps1` y `credenciales.ps1` (arranque con las claves guardadas) · `probar-servidor.py`.

| Ruta | Qué hace |
|---|---|
| GET `/api/salud` | `{"ok": true}` |
| GET `/api/canales` | canales, su identidad base y el avance de cada video |
| GET `/api/opciones` | voces, animaciones (con su estado) y fuentes válidas |
| GET `/api/canales/<canal>/identidad` | frase de la identidad base (`identidad.py resumen`) |
| GET `/api/canales/<canal>/ideas` | ideas de `estrategia/*ideas-de-video*.md`, con `usada` si ya hay video |
| GET `/api/pasos` | instrucción de cada paso (de `pasos.json`) y si se puede ejecutar desde el panel; no expone la lista de permisos |
| GET `/api/trabajo?desde=N` | estado del paso que corre o corrió, con sus eventos desde el N (la interfaz sondea cada segundo) |
| GET `/api/video/<canal>/<video>` | etapas, siguiente paso, puertas, sellos y el veredicto de cada informe (`informes`) |
| GET `/api/video/<canal>/<video>/comandos?paso=P` | comandos sin IA que ejecutaría un paso de tipo `comandos`, las variables de entorno que exige y cuáles faltan (solo los nombres, nunca los valores) |
| GET `/api/video/<canal>/<video>/siguiente` | `canal.py siguiente --seco` (no ejecuta ni escribe) |
| POST `/api/video` `{canal, nombre, idea?}` | crea el siguiente video (`nuevo-video.py`; número = último + 1); con `idea` deja `01-guion/idea.md` y rechaza ideas ya usadas |
| POST `…/<video>/identidad` `{base: canal\|propia, voz?, animacion?, fuente?}` | `identidad.py video`; rechaza animaciones que no estén `disponible` o `parcial` |
| POST `…/<video>/aprobar` `{puerta: idea\|guion\|corte}` | `estado-video.py --aprobar` |
| POST `…/<video>/sellar` `{rol}` | `estado-video.py --sellar`; los tres sellos (`auditor-guion`, `verificador`, `auditor-final`) exigen que su informe en `02-revision/` (`informe-<rol>.md`, o `<rol>.md`) diga PASA |
| POST `…/<video>/licencia` `{codigo}` | decisión tuya: pasa a ✅ («aceptada por ti» + fecha) una fila 🔎 del registro de licencias; **solo si su prueba ya está guardada** (ficha, captura o descarga que cita la columna «Captura»); solo toca la celda Estado de esa fila |
| POST `…/<video>/ejecutar` `{paso}` | Claude Code sin pantalla para el **paso actual** del video; solo pasos con `ejecutable` en `pasos.json`; 409 si ya hay uno corriendo |
| POST `/api/trabajo/cancelar` | termina el paso en ejecución (y sus procesos hijos) |

## Ejecutar pasos con Claude Code

- **Qué lanza:** `claude -p --output-format stream-json --verbose --permission-mode dontAsk --strict-mcp-config --model <modelo> --disallowedTools … --allowedTools …` con la instrucción por la entrada estándar, en la raíz del proyecto. Se carga el `CLAUDE.md`, las skills y los agentes igual que en una sesión normal.
- **Pasos ejecutables hoy con Claude Code:** `investigacion`, `guion` (modelo opus), `rev-guion`, `escaleta`, `planilla`, `miniaturas`, `licencias`, `montaje` (por datos: directivas «@tipo» en la escaleta, sin código propio), `rev-final` y `descripcion`. Pasos de comandos: `voz`, `video` y `subtitulos` (`exportar-srt.py`). Cada uno trae en `pasos.json` el texto de sus permisos (lo que la interfaz muestra antes de confirmar). Todos escriben solo en los archivos de su paso **de ese video**; ninguno puede sellar, aprobar, usar git ni servidores MCP. `rev-guion` y `rev-final` pueden lanzar los agentes `auditor` y `verificador` y correr `validar`, `verificar-cifras` y `estado-video --revisar/--diff`, no `--sellar` ni `--aprobar`.
- **Permisos mínimos:** `dontAsk` niega todo lo que no esté en la lista del paso (nadie aprueba nada en una ejecución sin pantalla). Sin git, sin servidores MCP, sin leer `.env*`. Lo que lea de la web no puede ampliar esos permisos. Los permisos negados salen en el registro. Probado con corridas reales baratas: la herramienta `Skill`, los subagentes y sus escrituras respetan la lista.
- **Miniaturas por datos, no por código:** Claude lee primero `00-contexto/produccion/guia-de-miniaturas.md`, analiza el tema del video y solo escribe `07-miniaturas/encargo-de-miniaturas.md` (con la justificación por regla) y `07-miniaturas/miniaturas.json` (tres variantes con paleta, composición y motivo propios); las imágenes las dibuja `herramientas/video/generar-miniaturas.py` (programa fijo del framework, que valida contraste y diversidad y dibuja). Así Claude nunca escribe ni ejecuta código propio —lo que anularía los permisos por archivo—. La imagen de una variante solo se acepta si está en `05-licencias/originales/` **y figura en el registro de licencias** (regla 3).
- **Regla de oro para escribir:** en `permitidas` usar `Edit(ruta)`, que cubre también a la herramienta Write. `Write(ruta)` **no concede nada** en la práctica (probado con seis variantes). `probar-servidor.py` revisa que ningún permiso de `pasos.json` se salga de lo previsto.
- **Licencias:** Claude lee las licencias en la web y guarda **fichas de texto** (URL, fecha y extracto) en `05-licencias/fichas/`; marca ✅ solo con la prueba existente y deja 🔎 lo que es una **inferencia** (p. ej. la política general de la fuente) para que lo decidas tú con el botón «Aceptar ✅». Las capturas de pantalla y las descargas las guardas tú.
- **Comandos tal cual:** las instrucciones piden ejecutar `python herramientas/...` sin `cd` ni `&&`; si Claude antepone un `cd`, el permiso no coincide y se niega.
- **Una sola fuente de instrucciones:** `pasos.json`. El panel muestra y copia **exactamente** lo que el servidor ejecuta (los marcadores `{ref}`, `{carpeta}`, `{hoy}` se rellenan). Se relee en cada consulta: editarlo no exige reiniciar. Para volver ejecutable otro paso, agregarle un bloque `ejecutable` con `modelo`, `minutos`, `permisos` (texto para el usuario), `permitidas` y `prohibidas` (los `{canal}`/`{video}` se rellenan; en `Write`/`Edit` una `/` inicial es la raíz del proyecto).
- **Controles:** un solo trabajo a la vez; tope de tiempo por paso (`minutos`); solo se acepta el paso que sea el **actual** del video; la interfaz pide confirmar (gasta uso de Claude) y puede cancelar.
- **Historial:** `<video>/.estado/ejecuciones/<fecha>-<paso>.jsonl` guarda la instrucción enviada, los permisos y cada evento (prueba de producción propia, regla 6).
- **Programa:** se busca `claude` en el PATH, o en la variable `CLAUDE_BIN` (así lo usa la prueba con el falso).

## Pasos de comandos (sin IA)

Algunos pasos no necesitan a Claude: son programas del framework. Se marcan en `pasos.json` con `"tipo": "comandos"` y se ejecutan directamente, con el mismo registro en vivo, cancelar, tope de tiempo e historial:

- **`voz`**: ejecuta los comandos de la voz de la **identidad del video** tal como están en `herramientas/voz/voces.json` (`pasos`, con `{guion}`, `{voz}`, `{video}`). Cada voz declara en `claves_env` las variables de entorno que necesita (Polly: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`; Google: `GOOGLE_TTS_API_KEY`).
- **`video`**: `canal.py montar` (alinea la voz, genera escenas, comprueba solapes, renderiza y copia a `08-entregables/`).

Reglas: solo `python` o `node` con un script dentro de `herramientas/` (sin shell, sin `..`); se ejecutan en orden y se detienen en el primer error. **Las claves nunca pasan por el panel ni por el chat**: el panel solo dice cuáles faltan (nombres, jamás valores) y no ejecuta hasta que estén. Los comandos de voz pueden tener costo (Polly: gratis 12 meses, luego ≈1 USD por video).

### Claves de voz: guardadas cifradas, cargadas solo para el servidor

`iniciar-panel.cmd` (doble clic o desde una terminal en la raíz del proyecto) enciende el servidor con las claves guardadas en el **Administrador de credenciales de Windows**, cifradas con tu cuenta (DPAPI): no están en texto plano, ni en un archivo, ni en variables de entorno permanentes, ni en el historial de PowerShell. Solo se usa la API nativa de Windows; no se instala ni se descarga nada.

| Orden | Qué hace |
|---|---|
| `iniciar-panel.cmd -Configurar` | pide cada clave (oculta al escribir; Enter vacío conserva la guardada) y la guarda |
| `iniciar-panel.cmd` | carga las guardadas **solo en esa ventana** y enciende el servidor |
| `iniciar-panel.cmd -SoloComprobar` | dice cuáles hay (solo nombres) y no enciende nada |
| `iniciar-panel.cmd -Olvidar` | borra las guardadas |

Los nombres salen de `claves_env` en `herramientas/voz/voces.json`. Al pasar el entorno a **Claude Code** el servidor **quita esas variables** (los pasos de IA nunca las reciben); solo los pasos de «comandos» las ven. Límite honesto: cualquier programa que corra con tu usuario de Windows puede pedirle una credencial al Administrador de credenciales, igual que cualquier otra aplicación; lo que se evita es dejarlas en claro y que viajen a todo lo que abras. Recomendado además: un usuario de AWS (IAM) solo con permiso para Polly y una alerta de presupuesto de 1 USD. El permiso `Bypass` del `.cmd` vale solo para ese proceso y no cambia la configuración de Windows.

## Decisiones

- **Python y solo biblioteca estándar**: mismo lenguaje que `canal.py`, sin instalar nada. No duplica lógica: importa `estado-video.py` y `nucleo/_comun.py` y llama a los demás programas como lo harías a mano.
- **Seguridad**: solo escucha en `127.0.0.1`; rechaza cualquier `Host` que no sea local (DNS rebinding). Las acciones POST exigen `Origin` del selector (`localhost:5173`), la cabecera `X-Panel: 1` y `Content-Type: application/json`, lo que obliga al navegador a una consulta previa que otras páginas no pasan. Los videos y canales se buscan por nombre en el listado, nunca por ruta recibida; los programas se lanzan con lista de argumentos (sin shell); no hay comandos libres y la interfaz nunca manda texto para Claude: solo «paso + video». No usa ni lee claves.
- **Ideas de video**: se leen de la tabla de `<canal>/estrategia/*ideas-de-video*.md`. Al crear un video desde una idea, se guarda `01-guion/idea.md` y la idea queda «usada»; los videos anteriores al panel se emparejan por número.
- **Qué no hace**: no hace commits (los haces tú), no sella ni aprueba por ti y no pisa guiones ni documentos fuera de los permisos de cada paso. Aprobar y sellar son tus decisiones: el selector pide confirmación antes de cada una.
- **Selector separado**: la interfaz vive en su propio repo (pruebas y despliegue propios); este servidor vive aquí porque depende de `canal.py`. Se hablan solo por esta API.
- **Pendiente**: (1) `metricas`, que depende de herramientas sin definir (vidIQ); (2) un cuadro «Pedir ajustes» que continúe la misma conversación (`--resume` con la sesión guardada).
