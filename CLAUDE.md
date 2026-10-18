# Proyecto: Canal de YouTube

Responde siempre en español.

> Este archivo es un **índice**. El texto íntegro de cada regla está en [reglas-detalladas.md](00-contexto/politicas/reglas-detalladas.md); las políticas completas, en [politicas-youtube-cumplimiento.md](00-contexto/politicas/politicas-youtube-cumplimiento.md) (67 KB: léelo por secciones con Grep, no entero). Si una línea de abajo y el texto íntegro discrepan, manda el texto íntegro.

## Cumplimiento de políticas de YouTube (obligatorio)
Todo lo que se cree (nicho, guiones, voz, edición, miniaturas, títulos, descripciones, subida) debe cumplir las políticas para no perder la monetización ni el canal. **Si una idea o recomendación choca con estas reglas, avisa antes de ejecutarla y propone una alternativa que cumpla.** Resumen (número = regla en reglas-detalladas.md):
1. Nada masivo, genérico o plantillado; cada video con concepto e historia propios.
2. Material de terceros solo con comentario o transformación sustancial (se evalúa por canal).
3. Copyright: no hay «regla de X segundos»; dar crédito no protege. Música solo con licencia que cubra monetizar; guardar la licencia de cada asset.
4. IA: declarar «Uso de IA = Sí» si el contenido realista es sintético; sin personas IA como expertos; sin imágenes engañosas.
5. No copiar guiones, estructuras, miniaturas ni títulos de otros canales (modelar patrones, no replicar).
6. Guardar el historial de producción como prueba de autoría.
7. Sin spam ni producción masiva; nada de espejar, acelerar o recortar material ajeno.
8. Apto para anunciantes: cuidado con narco, gore, tragedias, autolesión, desinformación médica, odio, groserías fuertes en título o miniatura.
9. Títulos y miniaturas sin engaño ni suplantación; imágenes antiguas no se presentan como actuales.
12. Temas sensibles: el contexto educativo va **dentro del video o el audio**. Sin excepción: abuso infantil, decapitaciones, material de perpetradores, instrucciones de autolesión/bombas/armas, doxxing, pornografía dura.
13. Prohibido siempre: doxxing, suplantar nombre/voz/imagen de otros (también con IA), comprar o inflar métricas, promesas de «hazte rico», bienes regulados, hackeo, retos peligrosos, glorificar criminales.
14. Menores: nunca en situaciones peligrosas ni con datos personales. 19. Semejanza: ni caras, voces ni nombres de personas reales sin permiso, ni imitarlas con IA.
Operativas, consultar el detalle cuando el tema aparezca: 10 YPP · 11 strikes · 15 música/Creator Music · 16 claims · 17 apelaciones · 18 «hecho para niños» · 20 patrocinios y afiliados · 21 términos de servicio · 22 AdSense · 23 revisiones de monetización.

## Otras reglas permanentes (resumen; íntegras en reglas-detalladas.md)
- **Análisis de videos:** cada video que el usuario pase se agrega como acordeón `<details>` en la Parte B del [Resumen unificado](00-contexto/investigacion/resumen-videos-de-youtube.md) (B16, B17…), nunca como archivo aparte; usar solo descripción, metadatos y subtítulos (jamás descargar el video); evaluarlo contra las reglas de arriba. Formato exacto: ver Reglas-detalladas.
- **Guiones:** siempre con la skill global `guionista-retencion` (`~/.claude/skills/guionista-retencion/SKILL.md`). Se conservan las marcas `[✔ n]`, `{pausa}`, `[Pantalla: …]`. Mandan las políticas: el gancho no promete lo que el video no entrega ni usa miedo o urgencia falsos.
- **Checklist de escritura (todos los canales):** al escribir un guion y antes de llamar al auditor o al verificador, repasar [checklist-escritura-guion.md](00-contexto/produccion/checklist-escritura-guion.md). Si un agente encuentra un fallo nuevo, añadir una línea ahí.
- **Producción:** guion (con su planilla de 3 columnas como sección «Planilla de producción» de `03-escaleta/escaleta-audiovisual.md`) → skill global `escaleta-audiovisual` (la escaleta técnica va en el mismo archivo) → script de montaje. 16:9, animaciones propias por código + imágenes oficiales con licencia, sin personas ni imágenes de IA presentadas como reales; cada escena indica origen y fila de licencia.
- **Composición:** nada se tapa con nada; zona segura (≈ y 150–745); movimiento continuo; texto dentro de su caja; sin marco HUD; estilo único de cajas (`ui.caja` / `ui.pastilla`, en `herramientas/montaje/comun/ui.py`); cierre con suscribirse, like y campanita; correr la verificación de solapes antes de renderizar. **Leer la sección completa antes de escribir una escaleta o montar.**
- **Identidad por canal y por video:** cada canal tiene su identidad en `<canal>/identidad/identidad.json` (nombre, **colores**, logo, **fuente**, **voz** —un id de `herramientas/voz/voces.json`—, **animación** —un id de `herramientas/montaje/catalogo/animaciones.json`—, **música** —pistas— y **efectos** de sonido). Si el canal no la tiene, defínela antes del primer video preguntando al usuario (`python herramientas/identidad.py canal "<canal>" --voz <id> --animacion <id> --fuente <inter|montserrat|space> --color BG=r,g,b --musica "Pista1,Pista2" --efectos si|no`). **Al crear cada video, pregunta siempre al usuario si se basará en la identidad del canal o tendrá una propia** (herramienta de preguntas) y ejecuta `python herramientas/identidad.py video "<video>" --base canal` o, si es propia, pregunta qué cambia (voz, animación, colores, nombre, logo o fuente; ofrece las opciones de los catálogos con su estado y su riesgo de políticas) y ejecuta `--base propia` con esos valores. Con base «canal» no se vuelve a preguntar la voz ni la animación: valen las del canal; con «propia» valen las elegidas para ese video. **Redacción de las opciones:** usa la frase que imprime `python herramientas/identidad.py resumen "<canal>"` para la opción «la base del canal»: nombra la voz, la animación, la fuente, los colores base con sus valores en hex entre paréntesis, la música y los efectos, pero nunca el nombre de la marca del canal (nada de «colores de <canal>»), porque la pregunta es la misma para cualquier canal. En «propia», ofrece también fuente (inter, montserrat, space, segoe), música y efectos entre lo que puede cambiar. Una animación que no está `disponible` exige proponer primero qué construir. El render completo no arranca sin base elegida. Voz: `python herramientas/voz/voces.py --video "<video>"` imprime los comandos de la voz de la identidad. Claves de voz solo por variable de entorno: nunca pedirlas ni leerlas. Para añadir una voz o un estilo, agregar una entrada a su catálogo.
- **Voz y narración:** tono cercano y dinámico (no solemne), narrativa explicativa con analogías cotidianas, estilo storytelling con misterio, hipótesis y resolución. Siguen mandando veracidad y voz IA declarada.

## Cómo trabajar sin gastar tokens de más
- No leer `resumen-videos-de-youtube.md` (178 KB) ni `politicas-youtube-cumplimiento.md` (67 KB) enteros: buscar con Grep y leer solo la sección. Para revisar un guion, usar primero `<canal>/estrategia/02-politicas-y-checklist.md` (6 KB).
- Antes de llamar a un agente revisor, correr `python herramientas/validar-video.py "<video>"`; solo si pasa se justifica la revisión con IA.
- Para saber en qué etapa va un video: `python herramientas/estado-video.py "<video>"` (no gasta tokens). Si el guion no cambió desde la última revisión sellada, no se revisa de nuevo; si cambió, se revisa solo el `--diff`.
- **Flujo de revisión de un guion:** checklist de escritura → `validar-video.py` → subagentes `auditor` (políticas y calidad; ruta + modo `guion` o `final`) y `verificador` (cifras contra fuentes; solo la ruta) → correcciones → el productor (la conversación principal) sella con `estado-video.py --sellar`. Cada agente corre el lint y consulta el sello; no editan nada. Informe en `<video>/02-revision/` (veredicto `PASA` o `FALLA` en la primera línea, máximo 300 palabras, con archivo y línea de cada hallazgo).
- Si se corrige un guion ya con voz o video hecho: ajustar el texto (subtítulos, escaleta con su planilla, capítulos, descripción) y anotar en memoria que falta regenerar voz y video.

## Estructura de la carpeta
| Carpeta | Qué guarda |
|---|---|
| `00-contexto/` | Lo global de todos los canales, en tres carpetas: `politicas/` (`politicas-youtube-cumplimiento.md`, `reglas-detalladas.md`), `produccion/` (`convencion-de-nombres.md`, `estructura-de-un-canal.md`, `checklist-escritura-guion.md`, `retencion-tecnicas-de-montaje.md`, `voz-ia-comparativa.md`) e `investigacion/` (resumen unificado de videos) |
| `01-nicho/` | Análisis de nicho (`analisis/`) y `datos/`. La app `selector-nichos` vive aparte, en `Proyectos-dev\selector-nichos\` |
| `02-canales/` | Un canal por carpeta (`hace-eones/`, `archivo-aracne/`; cada uno con `identidad/`, `estrategia/` y `videos/`) |
| `02-canales/<canal>/_archivo/` y `videos/NN-nombre/_archivo/` | Lo descartado o las versiones anteriores de un video (los scripts las ignoran). Hoy solo existe en el Video 02 |
| `.claude/agents/` | Subagentes del proyecto (`auditor`, `verificador`) |
| `herramientas/` | Sirven a todos los canales: `estado-video.py` (etapa y siguiente paso), `validar-video.py` (lint gratis), `nuevo-video.py <canal> <n> "<nombre>"` (crea la carpeta de un video), `identidad.py` (identidad del canal y de cada video), `voz/` (sintetizador de voz; `voces.json` lista las voces), `escaleta-a-escenas.py` (escaleta → `06-montaje/escenas.json`) y `montaje/` (`alinear.py` voz → `tiempos.json`, `animaciones.json` catálogo de estilos, librerías y tubería de render; leen `<canal>/identidad.json`) |

- **Nombres y carpetas:** todo en minúsculas con guiones (`kebab-case`), sin tildes ni espacios; orden con prefijo `01-`, `02-`… solo cuando importa; en la raíz de cada carpeta solo su `LEEME.md`. Un video = `<canal>/videos/NN-nombre/` con una carpeta por etapa (`01-guion` … `09-publicacion`). Texto completo y excepciones: [convencion-de-nombres.md](00-contexto/produccion/convencion-de-nombres.md).
- Un canal nuevo va como carpeta nueva dentro de `02-canales/`, con la misma estructura que los demás (`identidad/`, `estrategia/`, `videos/`); cada video en su propia carpeta (ver [estructura-de-un-canal.md](00-contexto/produccion/estructura-de-un-canal.md)).
- Al mover algo, actualizar también los enlaces.
