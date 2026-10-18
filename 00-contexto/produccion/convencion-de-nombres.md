# Convención de nombres y de carpetas (todo el proyecto)

Una sola regla de nombres para carpetas y archivos, y un lugar fijo para cada cosa. Al crear algo nuevo, copiar el patrón de lo que ya existe.

## Reglas de nombres
1. **Minúsculas, sin tildes, sin espacios y con guiones** (`kebab-case`): `hace-eones`, `escaleta-audiovisual.md`, `01-voyager-1`. Así no hace falta entrecomillar rutas y los enlaces no se rompen por mayúsculas ni espacios.
2. **Prefijo numérico de dos dígitos solo cuando el orden importa** (etapas, pasos, secuencia): `01-guion`, `02-revision`… El número va primero y luego un guion. Lo que no tiene orden (identidad, estrategia, `_archivo`) no lleva número.
3. **Los videos** se llaman `NN-nombre-corto` y viven en `<canal>/videos/`; `NN` es el orden de publicación del canal (`01-voyager-1`, `02-edad-del-universo`).
4. **Fechas** en formato `AAAA-MM-DD` cuando van en un nombre (`indice-de-copias-2026-10-13.txt`).
5. **Una carpeta = una cosa.** En la raíz de cada carpeta de contenido solo va su `LEEME.md` (qué hay, para qué sirve) y las subcarpetas. Los archivos de trabajo van dentro de la subcarpeta que corresponde. Excepciones técnicas: `CLAUDE.md` y `.gitignore` en la raíz del proyecto; en las carpetas de código (`06-montaje/`) los scripts y sus datos conviven porque se ejecutan desde ahí.
6. **`_archivo/`** guarda lo descartado o las versiones anteriores; el guion bajo inicial significa «los scripts lo ignoran». Los archivos auxiliares de un script que no son entregables también empiezan por `_` (`_render_y_1440.sh`).
7. **`LEEME.md`** es la única excepción de mayúsculas: se escribe así en todas partes para que destaque al principio de la lista.

### Código
- Programas que se ejecutan desde la terminal: `kebab-case.py` (`nuevo-video.py`, `estado-video.py`).
- Módulos que se importan: `snake_case.py` (`escenas_base.py`, `montar.py`), porque Python no importa nombres con guion.
- Scripts de un video: `video01.py`, `video02.py` (el nombre lleva el número del video).

### Excepciones (se conservan tal cual)
- `05-licencias/` de cada video: las fichas, capturas y copias de términos son **evidencia**; conservan el nombre con el que se guardaron (`M03-ficha-pia00373-2026-10-13.html`) y los códigos de material (`M01`, `V1`, `O-G`) que cita el registro.
- `herramientas/montaje/fuentes/` (nombres de las tipografías) y `.estado/` (sellos de revisión de cada video).

## Estructura del proyecto
| Carpeta | Qué contiene |
|---|---|
| `00-contexto/` | Lo global de todos los canales. `politicas/` (políticas y reglas), `produccion/` (checklists, técnicas, estructura y esta convención), `investigacion/` (resumen unificado de videos analizados) |
| `01-nicho/` | Decisión de nicho. `analisis/` y `datos/` |
| `02-canales/` | Un canal por carpeta |
| `herramientas/` | Programas que sirven a todos los canales: `voz/`, `montaje/` y los scripts de estado, validación e identidad |
| `.claude/agents/` | Subagentes del proyecto (`auditor`, `verificador`) |

## Estructura de un canal (`02-canales/<canal>/`)
| Carpeta | Qué contiene |
|---|---|
| `LEEME.md` | Mapa del canal |
| `identidad/` | `identidad.json` (nombre, colores, logo, fuente, voz, animación, música, efectos) e `identidad-del-canal.md` (promesa, tono, reglas editoriales) |
| `estrategia/` | `01-ideas-de-video.md`, `02-politicas-y-checklist.md` (lo lee el auditor), `03-modelos-de-referencia.md`, `04-plan-de-90-dias.md` |
| `videos/` | Un video por carpeta (`NN-nombre-corto/`) |

## Estructura de un video (`02-canales/<canal>/videos/NN-nombre/`)
Una carpeta por etapa, en el orden del flujo de trabajo:

| Carpeta | Etapa | Archivos principales |
|---|---|---|
| `LEEME.md` | Índice y estado del video | (se regenera con `estado-video.py --escribir`) |
| `identidad/` | Qué identidad usa el video | `identidad.json` (`{"base": "canal"}` o `{"base": "propia", ...}`) |
| `01-guion/` | Escribir | `guion.md`, `verificacion-de-cifras.md`, `texto-para-subtitulos.txt` |
| `02-revision/` | Revisar | `informe-auditor-guion.md`, `informe-verificador.md` |
| `03-escaleta/` | Planear la producción | `escaleta-audiovisual.md` (planilla de 3 columnas + escaleta técnica), `guia-de-montaje.md` |
| `04-voz/` | Locución | audio, `ajustes.txt`, `polly/`, `partes/` |
| `05-licencias/` | Derechos | `registro-de-licencias.md`, `originales/`, `fichas/`, `musica/`, `capturas-musica/` |
| `06-montaje/` | Montar | `video.py` (o `video01.py`), `montaje.json`, `tiempos.json`, `escenas.json`, `musica/`, `salida/` |
| `07-miniaturas/` | Miniaturas | `encargo-de-miniaturas.md` y las imágenes |
| `08-entregables/` | Resultado final | `.mp4` y `.srt` |
| `09-publicacion/` | Publicar y medir | `capitulos-y-descripcion.md`, `metricas-y-seguimiento.md` |
| `_archivo/` | Descartado | versiones anteriores |

## Cómo se resuelve una ruta en los scripts
Los nombres de carpetas y archivos de un video están definidos **una sola vez** en `herramientas/_comun.py` (`GUION`, `VOZ`, `F_GUION`, `F_LICENCIAS`…). Si un nombre cambia, se cambia allí y en esta tabla. Los programas aceptan el video como `<canal>/<n>` (por ejemplo `hace-eones/2`), con o sin la forma antigua (`"Hace Eones/Video 02"`).
