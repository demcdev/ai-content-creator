# Encargo de miniaturas · La primera foto de un agujero negro

Base: [guía de miniaturas](../../../../../00-contexto/produccion/guia-de-miniaturas.md) (método de la sección 4). Datos en [miniaturas.json](miniaturas.json); las dibuja `herramientas/video/generar-miniaturas.py`. Fecha: 18-oct-2026.

## 1. Resumen del video

- **Pregunta:** ¿cómo se fotografía algo que no deja escapar la luz?
- **Objeto central:** el anillo brillante con el centro oscuro (la sombra) de M87*, y la red de radiotelescopios del tamaño del planeta.
- **Emoción honesta:** asombro y un poco de desconcierto («es imposible verlo… y se vio»).
- **Dato más llamativo (verificado):** una red de ocho observatorios repartidos por la Tierra funcionó como un solo telescopio (filas 8 y 18 de la tabla de cifras). La miniatura no pone cifras: no hay ninguna fila `parcial` o sin verificar a la vista.

## 2. Las tres variantes

| | A · el objeto | B · la pregunta | C · el dato |
|---|---|---|---|
| **Se ve** | Anillo naranja con disco negro, a la derecha, sobre cielo estrellado | Ondas concéntricas (señal de radio) a la izquierda | Esfera de planeta arriba a la derecha, sobre azul vivo |
| **Texto** | «SOLO SU / SOMBRA» | «¿VER LO / INVISIBLE?» | «PLANETA / TELESCOPIO» |
| **Paleta** | fondo `#07070C`, texto `#FFF1DC`, acento `#FF8A1F` | fondo `#0B1F22`, texto `#0B1F22` sobre caja `#4DE3C8` | fondo `#0B5BD3`, texto `#FFFFFF`, acento `#3FD08A` |
| **Por qué ese color** | Naranja/dorado es el color del gas caliente en las imágenes oficiales del EHT; casi negro = el vacío | Verde-cian sobre gris oscuro: la señal de radio (1,3 mm), el instrumento y no el objeto | Azul vivo = la Tierra; verde = continentes. Evita el amarillo, que una esfera leería como el Sol |
| **Composición** | texto-izquierda, motivo a la derecha (x 0,80) | texto-derecha, motivo a la izquierda (x 0,18) | texto-abajo, motivo en el tercio superior derecho |
| **Fondo / estilo / fuente** | estrellas · brillo · Montserrat | degradado · caja · Space | radial · plano · Inter |
| **Contraste / brillo / colorido** | 18,1:1 · 34 · 39 (oscura y sobria) | 10,7:1 · 51 · 58 (oscura, acento fuerte) | 6,1:1 · 106 · 132 (clara y saturada) |
| **Reglas** | D1 un solo motivo; D2 foco en un cruce de tercios; D3 contraste > 4,5; D5; D6 (paleta del tema, no del canal); D7 | D3 (en `caja`, acento vs fondo); D9 (pregunta que entiende un espectador casual); D10 (3 palabras, complementa el título) | D3; D7 (alto + alto); D9; D10 (2 palabras) |

Reglas comunes: R1 (3840×2160, 16:9, PNG/JPG), R5 (tres variantes distintas en concepto, composición, motivo, paleta, fondo y estilo de texto), R7 (diseño propio, no copiado), D4 (revisadas a 320×180 con el texto legible). Solo una variante, la A, se acerca a la identidad oscura del canal; ninguna usa los colores de marca como paleta única.

## 3. Hipótesis para el A/B

- **A vs B:** ¿gana el **objeto** (lo que se ve) o la **pregunta** (la duda que abre el video)?
- **C:** ¿el **dato/mecanismo** («planeta = telescopio»), en una paleta clara, atrae más tiempo de reproducción que dos miniaturas oscuras (D7)?
- Aprendizaje secundario: si ganan las oscuras, probar más variantes sobrias; si gana C, probar acentos claros en otros videos.

## 4. Cómo medir

Test A/B de Studio con las tres (solo en computadora; subir las `miniatura-<id>.png` de 3840×2160, R1). Se decide por el **% del tiempo de reproducción**; mirar también el CTR de Home y Suggested en las primeras 24 h si hay impresiones suficientes. No cambiar título ni nada más durante la prueba (de unos días a 2 semanas).

## 5. Honestidad

- **A:** «Solo su sombra» es exactamente lo que el video explica (se fotografía la sombra, no el agujero). El anillo es un **dibujo propio**; no se presenta como la imagen real del EHT. Sin imagen externa ni licencia.
- **B:** la pregunta se responde en el video (4:50 y cierre). Las ondas son gráfico propio; no promete ver el interior del agujero. Sin imagen externa.
- **C:** el video explica que es una red de radiotelescopios que actúa como uno solo, no un aparato del tamaño de la Tierra; la esfera es gráfico propio, no una foto. Sin imagen externa.
- No se usa ninguna imagen oficial del EHT: el registro de licencias del video está vacío y la fila 23 de la tabla de cifras está sin verificar. Sin personas, caras ni imágenes de IA. Si más adelante se guarda la licencia, se podrá probar una versión con la imagen oficial, rotulada y con crédito.
- Pendiente de revisar a mano: A y B muestran el aviso «letras algo pequeñas para el móvil» (se leen bien a 320×180, pero conviene mirarlas también a 160×90).
