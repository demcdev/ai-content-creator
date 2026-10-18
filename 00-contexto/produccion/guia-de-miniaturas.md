# Guía de miniaturas · reglas con fuente

> **Para qué sirve:** es la base de diseño del paso «Miniaturas» de cualquier canal y video. Quien diseñe las miniaturas (una persona o Claude Code) la lee **antes** de decidir nada y escribe en el encargo qué regla aplicó en cada decisión. Fuentes consultadas el **18-oct-2026**; si algo cambia en YouTube, esta guía se revisa (YouTube actualiza sus páginas de ayuda).
>
> **Lo que NO es:** una receta que garantice clics. Nadie puede predecir qué miniatura ganará: por eso se hacen **tres variantes realmente distintas** y se decide con el test A/B de YouTube (regla R5).

## 0. Cómo leer el «nivel de evidencia»

| Nivel | Qué es | Cómo se trata |
|---|---|---|
| **A** | Documentación oficial de YouTube / Google | **Obligatorio** (especificaciones, políticas) o recomendación del propio YouTube |
| **B** | Estándar técnico reconocido (W3C) | Se adopta como regla de legibilidad, aclarando que es una adaptación (WCAG es de accesibilidad web) |
| **C** | Estudio observacional publicado | **Tendencia a probar en el A/B**, nunca ley; se dice en qué contexto se midió |
| **D** | Heurística del proyecto | Criterio de diseño nuestro, **sin respaldo externo**; se puede romper si el A/B lo contradice |

## 1. Fuentes verificadas

| Id | Fuente | Tipo | Qué aporta (resumen propio) | Enlace |
|---|---|---|---|---|
| F1 | YouTube Help · «Add custom thumbnails» | A | Resolución recomendada 3840×2160 (mínimo 640 px de ancho), JPG/PNG, 16:9; límite 2 MB desde móvil y 50 MB desde computadora; las miniaturas con desnudez, odio, violencia o contenido dañino se rechazan y pueden dar strike | <https://support.google.com/youtube/answer/72431> |
| F2 | YouTube Help · «Thumbnail & title tips» | A | Pensar en la audiencia (suscriptores vs. espectadores casuales); regla de los tercios; fuente fácil de leer; **no hacer el diseño demasiado complejo**; el tamaño más grande posible porque se ve distinto en cada dispositivo; los estilos cambian con el tiempo; medir el CTR en Home y Suggested en las primeras 24 h (en videos con impresiones por encima del promedio) y el de suscriptores en el feed de suscripciones; el título debe ser exacto | <https://support.google.com/youtube/answer/12340300> |
| F3 | YouTube Help · «A/B test titles & thumbnails» | A | Hasta 3 variantes; gana la de mayor **porcentaje del tiempo de reproducción** (no el CTR); variantes demasiado parecidas alargan la prueba o no dan ganador; dura de unos días a 2 semanas; solo en computadora, no en Shorts; si alguna variante es menor de 720p, **todas** se reducen a 480p | <https://support.google.com/youtube/answer/16391400> |
| F4 | YouTube Data API · recurso «Thumbnails» | A | Tamaños en que se sirve una miniatura de video: 120×90, **320×180**, 480×360, 640×480 y 1280×720 | <https://developers.google.com/youtube/v3/docs/thumbnails> |
| F5 | W3C · WCAG 2.2, criterio 1.4.3 «Contrast (Minimum)» | B | Contraste mínimo entre texto y fondo de 4,5:1 (3:1 para texto grande); la fórmula usa la luminancia relativa, no el matiz; razones: baja visión y daltonismo; aconseja evitar rojo sobre negro | <https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html> |
| F6 | Koh & Cui (2022), *Decision Support Systems* 160, 113820 · «An exploration of the relation between the visual attributes of thumbnails and the view-through of videos» | C | 3 745 videos de marketing de 38 marcas (automóvil, bebida, restaurante, juguetes) en YouTube, con atributos medidos por visión por computadora. Relaciones **no lineales**: complejidad de elementos en U; complejidad de objetos en U invertida (demasiados objetos estorban); colorido en U; el brillo depende del colorido (combinaciones «bajo colorido + bajo brillo» o «alto + alto» rindieron mejor); calidad de imagen en U invertida (ni distorsionada ni sobre-retocada). Es observacional y de contenido de marcas: **no se generaliza sin probar**. Leí el manuscrito del autor | <http://www.byungwan.com/papers/Thumbnails.pdf> · doi:10.1016/j.dss.2022.113820 |
| F7 | Dong (2024), *Lecture Notes in Education Psychology and Public Media* 41(1) | — | **Leído y descartado como base de reglas**: analiza 30 videos de una sola creadora en una plataforma china (RED). Muestra demasiado pequeña para generalizar | <https://doi.org/10.54254/2753-7048/41/20240778> |

> No encontré una fuente seria que respalde reglas numéricas como «máximo 3 palabras», «letras de al menos el 18 % de la altura» o «el ámbar sobre azul rinde mejor». Están marcadas como **D** más abajo. Tampoco leí la política de miniaturas de YouTube (<https://support.google.com/youtube/answer/9229980>) completa: F1 resume lo que se rechaza; ante duda, leerla.

## 2. Reglas obligatorias

| Id | Regla | Nivel | Fuente |
|---|---|---|---|
| R1 | **Formato:** 16:9, JPG o PNG. Producir en **3840×2160** (el generador lo hace). Nunca menos de 1280×720: si una variante baja de 720p, el test A/B reduce **todas** a 480p. Subir desde una computadora (el test A/B solo existe ahí; límite 50 MB). Si se sube desde móvil, usar la versión `-movil.jpg` (menos de 2 MB) | A | F1, F3 |
| R2 | **Políticas:** nada de desnudez, odio, violencia ni contenido dañino. La miniatura **solo muestra lo que el video entrega** (reglas 9 del proyecto); el texto no promete ni exagera | A + proyecto | F1, F2, regla 9 |
| R3 | **Sin personas reconocibles, ni voces/marcas de otros, ni imágenes de IA presentadas como reales** | proyecto | reglas 4, 19 |
| R4 | **Licencias:** cualquier imagen externa debe estar en `05-licencias/originales/` y figurar en el registro de licencias (el generador lo exige) | proyecto | regla 3 |
| R5 | **Tres variantes realmente distintas** (composición, motivo, paleta, concepto), no retoques de una misma. Variantes parecidas alargan el test o no dan ganador | A | F3 |
| R6 | **Cómo decidir:** con el test A/B de Studio; gana la de mayor % del tiempo de reproducción. Mirar además el CTR de Home y Suggested en las primeras 24 h si hay impresiones suficientes. Cambiar **una cosa a la vez**. Una prueba tarda de unos días a 2 semanas | A | F2, F3 |
| R7 | **No copiar** miniaturas de otros canales: se estudian patrones, no composiciones | proyecto | regla 5 |

## 3. Reglas de diseño

| Id | Regla | Nivel | Fuente / nota |
|---|---|---|---|
| D1 | **Un solo punto focal y poca complejidad:** como máximo **un motivo gráfico o una imagen**, más el texto. Ni demasiado vacío ni sobrecargado | A + C | F2 («no demasiado complejo»); F6 (relaciones no lineales: hay un punto medio) |
| D2 | **Regla de los tercios:** el foco (motivo, objeto o imagen) va en un cruce de tercios, no en el centro geométrico | A | F2 |
| D3 | **Contraste del texto ≥ 4,5:1** contra su fondo, medido por luminancia (WCAG). Se adopta 4,5 y no 3 porque la miniatura se ve reducida y con compresión; **el generador lo comprueba y rechaza** lo que no llegue. Evitar rojo puro sobre negro | B | F5 |
| D4 | **Legibilidad a tamaño real:** revisar la versión de **320×180** (tamaño «medium» servido, F4) y la de **160×90** (prueba de esfuerzo, D). Si no se lee a 320×180, está mal | A + D | F4 |
| D5 | **Fuente gruesa y fácil de leer**, en mayúsculas o altas y bajas según el tono; una sola familia por variante | A | F2 («fuente fácil de leer») |
| D6 | **Color: no hay un color ganador respaldado.** La paleta de cada variante se **deriva del tema del video** (sección 4) y se verifica con D3. No usar siempre los colores del canal: como mucho **una** de las tres variantes puede usar la paleta del canal | D | método del proyecto |
| D7 | **Brillo y colorido:** F6 sugiere que «bajo colorido + bajo brillo» o «alto + alto» rinden mejor que las mezclas intermedias. **Hipótesis a probar**, no regla: el generador informa el brillo y el colorido de cada variante para que las tres exploren zonas distintas | C | F6 (contenido de marcas) |
| D8 | **Calidad de imagen:** nítida, sin distorsión ni retoque excesivo | C | F6 |
| D9 | **Audiencia:** un canal nuevo atrae sobre todo a espectadores casuales; para ellos conviene lo universalmente comprensible (un objeto, una pregunta, un dato), no referencias internas del canal | A | F2 |
| D10 | **Texto corto:** pocas palabras (idealmente 3 o menos; el generador rechaza más de 4) y que **complemente** el título en vez de repetirlo | D | heurística del proyecto, sin respaldo externo |
| D11 | **Frescura:** los estilos cambian con el tiempo; revisar de vez en cuando qué se ve en tu nicho, **sin copiar** (R7) | A | F2 |

## 4. Método para decidir el diseño según el tema (nivel D, método del proyecto)

1. **Leer** `01-guion/idea.md` y el guion: anotar (a) la **pregunta o promesa** del video, (b) el **objeto o fenómeno visual central**, (c) la **emoción honesta** (asombro, duda, escala), (d) el **dato más llamativo ya verificado** en la tabla de cifras.
2. **Elegir tres conceptos distintos** (R5), por ejemplo: *el objeto* (lo que se ve), *la pregunta* (la duda que abre el video) y *el dato* (la cifra que sorprende). Cada uno con su `concepto` escrito en una frase.
3. **Para cada concepto elegir** composición, motivo y fondo **diferentes** a los de las otras variantes (el generador rechaza las que se parezcan demasiado).
4. **Paleta por variante, desde el tema:** parte del color real del fenómeno (el que tiene en las imágenes científicas oficiales) para el acento; elige un fondo que contraste con él; y verifica D3. Ejemplos **ilustrativos**, no reglas: un agujero negro → naranja/dorado sobre casi negro; Venus → amarillo azufre sobre ocre oscuro; hielo/océano → celeste y blanco sobre azul profundo; prehistoria → verdes y tierras; una señal de radio → verde o cian sobre gris oscuro. Si dos variantes comparten el mismo acento, que difieran claramente en fondo y composición.
5. **Explorar brillo/colorido** (D7): una variante oscura y sobria, otra clara y saturada, y una intermedia con un acento fuerte. El generador informa los números.
6. **Redactar el encargo** (plantilla de la sección 6) con la justificación y la hipótesis de cada variante, y luego escribir `miniaturas.json` y ejecutar el generador.

## 5. Formato de `07-miniaturas/miniaturas.json` (lo que lee el generador)

```json
{"variantes": [
  {"id": "A", "concepto": "el objeto",
   "texto": ["LINEA 1", "LINEA 2"], "subtexto": "opcional (hasta 3 palabras)",
   "paleta": {"fondo": "#0B0B10", "texto": "#FFF4E0", "acento": "#FF8A1F"},
   "composicion": "texto-izquierda",
   "motivo": {"tipo": "anillo", "posicion": [0.68, 0.45], "tamano": 0.30},
   "estilo_texto": "brillo", "fondo": "estrellas", "fuente": "montserrat",
   "imagen": "05-licencias/originales/archivo.jpg"}
]}
```

| Campo | Valores | Notas |
|---|---|---|
| `id` | letras, números o guion | único |
| `concepto` | frase | obligatorio; distinto en cada variante |
| `texto` | 1 o 2 líneas | máx. 4 palabras (idealmente 3) y 18 letras por línea |
| `paleta` | `fondo`, `texto`, `acento` en `#RRGGBB` | el texto debe tener contraste ≥ 4,5:1 con el fondo (con `estilo_texto: caja`, entre `acento` y `fondo`) |
| `composicion` | `texto-izquierda`, `texto-derecha`, `centrado`, `texto-abajo` | por defecto `texto-izquierda` |
| `motivo.tipo` | `anillo` (anillo luminoso con disco), `esfera` (cuerpo esférico; `detalle: "bandas"` opcional), `orbitas`, `ondas` (señal), `ninguno` | `posicion` = [x, y] como fracción del lienzo; `tamano` = fracción de la altura (0,1–0,6) |
| `estilo_texto` | `brillo`, `plano`, `caja` | `caja`: texto en el color de fondo sobre una caja del color de acento |
| `fondo` | `estrellas`, `degradado`, `solido`, `radial` | |
| `fuente` | `inter`, `montserrat`, `space` | por defecto, la de la identidad |
| `imagen` | ruta dentro de `05-licencias/originales/` | opcional; **debe figurar en el registro de licencias** |

El generador (`herramientas/video/generar-miniaturas.py`) valida todo esto, dibuja a 3840×2160 y deja `miniatura-<id>.png` (el id va en minúsculas en el nombre del archivo), `-movil.jpg` (menos de 2 MB), `-320x180.png` y `-160x90.png`, e imprime por variante el contraste del texto, el brillo, el colorido y los elementos usados.

## 6. Plantilla del encargo (`07-miniaturas/encargo-de-miniaturas.md`)

1. **Resumen del video** en 3 líneas: pregunta, objeto central, dato más llamativo (verificado).
2. **Las tres variantes:** para cada una, `concepto`, qué se ve, texto, paleta (con el motivo del color elegido en relación con el tema), composición y **qué regla de la guía aplica** (ids D/R).
3. **Hipótesis:** qué espera aprender el A/B de cada variante (p. ej. «¿gana la pregunta o el objeto?»).
4. **Cómo medir:** test A/B de Studio con las tres; mirar % del tiempo de reproducción y, si hay impresiones, el CTR de Home y Suggested en 24 h; no cambiar nada más durante la prueba.
5. **Honestidad:** una línea por variante que confirme que no promete nada que el video no entregue y qué imagen/licencia usa (o que es solo gráfico propio).

## 7. Lo que no tiene respaldo (para no tratarlo como ley)

- «Máximo 3 palabras», «letras de al menos el 18 % de la altura» y «una sola imagen real y clara»: heurísticas del proyecto (D).
- «El ámbar sobre azul noche funciona mejor»: no hay evidencia; era la identidad del canal, no una conclusión de diseño.
- Que los rostros expresivos mejoren el rendimiento: F2 lo menciona como ejemplo para públicos casuales, pero **este proyecto no usa personas reconocibles** (R3).
- Cualquier cifra de «CTR esperado» que no salga de **tu propio** canal.
