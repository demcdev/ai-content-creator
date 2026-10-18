# Proyecto: Canal de YouTube

Responde siempre en español.

> Este archivo es un **índice**. El texto íntegro de cada regla está en [Reglas-detalladas.md](00_contexto/Reglas-detalladas.md); las políticas completas, en [Politicas-YouTube-Cumplimiento.md](00_contexto/Politicas-YouTube-Cumplimiento.md) (67 KB: léelo por secciones con Grep, no entero). Si una línea de abajo y el texto íntegro discrepan, manda el texto íntegro.

## Cumplimiento de políticas de YouTube (obligatorio)
Todo lo que se cree (nicho, guiones, voz, edición, miniaturas, títulos, descripciones, subida) debe cumplir las políticas para no perder la monetización ni el canal. **Si una idea o recomendación choca con estas reglas, avisa antes de ejecutarla y propone una alternativa que cumpla.** Resumen (número = regla en Reglas-detalladas.md):
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

## Otras reglas permanentes (resumen; íntegras en Reglas-detalladas.md)
- **Análisis de videos:** cada video que el usuario pase se agrega como acordeón `<details>` en la Parte B del [Resumen unificado](00_contexto/Resumen%20-%20Videos%20de%20YouTube.md) (B16, B17…), nunca como archivo aparte; usar solo descripción, metadatos y subtítulos (jamás descargar el video); evaluarlo contra las reglas de arriba. Formato exacto: ver Reglas-detalladas.
- **Guiones:** siempre con la skill global `guionista-retencion` (`~/.claude/skills/guionista-retencion/SKILL.md`). Se conservan las marcas `[✔ n]`, `{pausa}`, `[Pantalla: …]`. Mandan las políticas: el gancho no promete lo que el video no entrega ni usa miedo o urgencia falsos.
- **Checklist de escritura (todos los canales):** al escribir un guion y antes de llamar al auditor o al verificador, repasar [Checklist-escritura-guion.md](00_contexto/Checklist-escritura-guion.md). Si un agente encuentra un fallo nuevo, añadir una línea ahí.
- **Producción:** guion → skill global `escaleta-audiovisual` (guardar `Escaleta audiovisual.md` en la carpeta del video) → script de montaje. 16:9, animaciones propias por código + imágenes oficiales con licencia, sin personas ni imágenes de IA presentadas como reales; cada escena indica origen y fila de licencia.
- **Composición:** nada se tapa con nada; zona segura (≈ y 150–745); movimiento continuo; texto dentro de su caja; sin marco HUD; estilo único de cajas (`ui.caja` / `ui.pastilla`); cierre con suscribirse, like y campanita; correr la verificación de solapes antes de renderizar. **Leer la sección completa antes de escribir una escaleta o montar.**
- **Voz y narración:** tono cercano y dinámico (no solemne), narrativa explicativa con analogías cotidianas, estilo storytelling con misterio, hipótesis y resolución. Siguen mandando veracidad y voz IA declarada.

## Cómo trabajar sin gastar tokens de más
- No leer `Resumen - Videos de YouTube.md` (178 KB) ni `Politicas-YouTube-Cumplimiento.md` (67 KB) enteros: buscar con Grep y leer solo la sección. Para revisar un guion, usar primero `Hace Eones/03 - Politicas y checklist.md` (6 KB).
- Antes de llamar a un agente revisor, correr `python herramientas/validar-video.py "<video>"`; solo si pasa se justifica la revisión con IA.
- Para saber en qué etapa va un video: `python herramientas/estado-video.py "<video>"` (no gasta tokens). Si el guion no cambió desde la última revisión sellada, no se revisa de nuevo; si cambió, se revisa solo el `--diff`.
- **Flujo de revisión de un guion:** checklist de escritura → `validar-video.py` → subagentes `auditor` (políticas y calidad; ruta + modo `guion` o `final`) y `verificador` (cifras contra fuentes; solo la ruta) → correcciones → el productor (la conversación principal) sella con `estado-video.py --sellar`. Cada agente corre el lint y consulta el sello; no editan nada. Informe en `<video>/Revision/` (veredicto `PASA` o `FALLA` en la primera línea, máximo 300 palabras, con archivo y línea de cada hallazgo).
- Si se corrige un guion ya con voz o video hecho: ajustar el texto (subtítulos, escaleta, planilla, capítulos, descripción) y anotar en memoria que falta regenerar voz y video.

## Estructura de la carpeta
| Carpeta | Qué guarda |
|---|---|
| `00_contexto/` | Lo global de todos los canales: políticas, `Reglas-detalladas.md`, resumen unificado de videos, `Checklist-escritura-guion.md`, `Estructura-de-un-canal.md` (cómo se organiza un canal y un video), `Retencion-tecnicas-de-montaje.md` y `Voz-IA-comparativa.md` |
| `01_nicho/` | Análisis de nicho y `datos/`. La app `selector-nichos` vive aparte, en `Proyectos-dev\selector-nichos\` |
| `02_canales/` | Un canal por carpeta (`Hace Eones/`, `Archivo Aracne/`) |
| `02_canales/<canal>/_archivo/` y `Video NN/_archivo/` | Lo descartado o las versiones anteriores de un video (los scripts las ignoran). Hoy solo existe en el Video 02 |
| `.claude/agents/` | Subagentes del proyecto (`auditor`, `verificador`) |
| `herramientas/` | Sirven a todos los canales: `estado-video.py` (etapa y siguiente paso), `validar-video.py` (lint gratis), `nuevo-video.py <canal> <n> "<nombre>"` (crea la carpeta de un video) y `voz/` (sintetizador de voz) |

- Un canal nuevo va como carpeta hermana de `Hace Eones/` dentro de `02_canales/`; lo global del canal en su raíz y cada video en su propia carpeta (ver [Estructura-de-un-canal.md](00_contexto/Estructura-de-un-canal.md)).
- Al mover algo, actualizar también los enlaces.
