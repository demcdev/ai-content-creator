# AI Content Creator

Pipeline de producción de contenido con IA: de la idea al video publicado, con revisión de políticas en cada paso. Hoy produce para **YouTube**; la estructura está pensada para crecer a otras plataformas (TikTok, Instagram, Facebook…).

## Qué hace

```
nicho → guion → revisión (políticas + cifras) → escaleta → voz → montaje → miniaturas → publicación
```

- **Guiones** con técnicas de retención (gancho, bucles abiertos, una sola CTA).
- **Revisión automática**: lint del guion, subagentes `auditor` (políticas de YouTube) y `verificador` (cifras contra fuentes).
- **Voz IA** declarada, con catálogo de voces por canal.
- **Montaje por código**: animaciones propias e imágenes oficiales con licencia, con verificación de solapes antes de renderizar.
- **Miniaturas** definidas como datos y generadas por script.
- **Registro de licencias** de cada asset y historial de producción como prueba de autoría.

## Estructura

| Carpeta | Contenido |
|---|---|
| `00-contexto/` | Políticas de YouTube, guías de producción e investigación |
| `01-nicho/` | Análisis de nichos |
| `02-canales/` | Un canal por carpeta (`identidad/`, `estrategia/`, `videos/`) |
| `herramientas/` | Programas compartidos: `canal`, `video`, `voz`, `montaje`, `identidad`, `validacion`, `panel`, `nucleo` |
| `.claude/agents/` | Subagentes de revisión |

Cada video vive en `02-canales/<canal>/videos/NN-nombre/` con una carpeta por etapa (`01-guion` … `09-publicacion`).

## Uso

Una sola entrada, desde la raíz del proyecto:

```bash
python herramientas/canal/canal.py ayuda --corta        # lista las órdenes
python herramientas/canal/canal.py siguiente "<canal>/<n>"  # hace lo automático y dice qué falta
```

Requiere Python 3. Las claves de voz se leen solo desde variables de entorno (nunca se guardan en el repo).

## Qué no se versiona

Audio, video y renders (`*.mp4`, `*.wav`, `*.mp3`, `salida/`, `cache*/`), claves y transcripciones de agentes. Ver `.gitignore`.

## Cumplimiento

Todo el contenido debe respetar las políticas de YouTube (contenido original, copyright, IA declarada, apto para anunciantes). Detalle en `00-contexto/politicas/`.
