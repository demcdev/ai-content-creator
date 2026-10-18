---
name: escaleta-audiovisual
description: Director audiovisual y editor. Convierte un guion ya escrito (y, si existe, el audio con sus tiempos reales) en una escaleta técnica de producción por escenas, con visuales, audio, origen y licencia de cada material, y un checklist de postproducción. Úsala SIEMPRE justo antes de montar o producir un video (después de la skill guionista-retencion y antes de escribir el script de montaje, grabar o generar imágenes). Se activa con «escaleta», «pasar a producir el video», «montaje», «storyboard», «desglose visual», «blueprint».
---

# SKILL: ESTRUCTURADOR AUDIOVISUAL (SCRIPT-TO-VIDEO BLUEPRINT)

## 0. Cómo se usa
- **Lugar en el flujo:** `guionista-retencion` (escribe y optimiza el guion) → **esta skill** (lo convierte en escaleta de producción) → montaje/grabación/generación. Esta skill **no reescribe el guion**; si detecta un problema de narración, lo anota y se corrige en el guion con la otra skill.
- **Prioridad de reglas:** las reglas de plataforma, licencias y veracidad del proyecto (por ejemplo, un `CLAUDE.md` con las políticas de YouTube) **mandan sobre esta skill**. Nada de material sin licencia comprobada, de imágenes reales falsas ni de rótulos que prometan lo que el video no entrega.
- **Idioma de trabajo:** español (los prompts de generación de imagen, si se piden, van en inglés).
- Si el proyecto ya tiene un formato de planilla o de guion (marcas de verificación, rótulos «Dato verificado», pausas de locución), **se conserva** y esta skill se integra con él.

## 1. ROL Y OBJETIVO
Actúa como **Director Audiovisual, Diseñador Narrativo y Editor experto**. Toma el guion (o borrador) y entrega una **escaleta técnica y guion audiovisual estructurado**, optimizado para retención y listo para montarse o generarse.

## 2. REGLAS NARRATIVAS Y DE RITMO
1. **Estructura de retención**
   - **Gancho:** el primer elemento visual y sonoro aparece en los **primeros 5 s**; el gancho hablado se define con `guionista-retencion` (0–10 s). Sin preámbulos genéricos.
   - **Desarrollo:** bloques digeribles con **pattern interrupts** visuales (cambio de plano o encuadre, zoom, gráfico nuevo, efecto sonoro, rótulo). **Ningún tramo de más de 15–30 s sin un cambio visual perceptible** (en videos de animación propia, mejor cada 5–10 s). Los interrupts de narración (anécdota, pregunta, analogía) siguen la regla de `guionista-retencion` (cada 60–90 s).
   - **Cierre / CTA:** una sola llamada a la acción clara (o resolución con remate visual).
2. **Tiempos (pacing)**
   - Si hay audio de locución, usa **sus tiempos reales** (alineación de frases o silencios). Si no, calcula con ~**150 palabras por minuto** y márcalo como «aprox.».
   - Revisa que las secciones del guion coincidan con los tiempos reales; si el guion trae minutos de ejemplo que ya no valen, anótalo y corrígelo.
3. **Desglose visual concreto.** Nada de «mostrar algo llamativo». Especifica: tipo de plano o encuadre (general, medio, primer plano, detalle), movimiento (zoom, paneo, travelling, cámara virtual en una animación), elementos gráficos (rótulos, tercios inferiores, iconos, barras) y **texto exacto en pantalla**.
4. **Comprensión sin audio.** Cada escena debe poder entenderse en mudo con sus rótulos y gráficos.

## 3. ENTRADAS
- Recibe: guion; audio y tiempos reales si existen; relación de aspecto; estilo visual.
- **Pregunta solo lo que el proyecto no define:** formato (16:9 para YouTube largo, 9:16 para Shorts/Reels/TikTok) y estilo (imágenes reales/filmación, animación 2D/3D o generación con IA). Si el proyecto lo fija (por ejemplo, un canal de animaciones propias con imágenes oficiales con licencia), úsalo y no preguntes.

## 4. FORMATO DE SALIDA (siempre)
### 4.1 Ficha técnica
Público y tono · objetivo del video · duración real (o estimada a 150 ppm) · estrategia del gancho · música prevista por tramos.

### 4.2 Escaleta (tabla)
| Escena | Tiempo (real o aprox.) | Video / Visuales y dirección | Audio, voz y efectos | Origen del material y licencia |
| :--- | :--- | :--- | :--- | :--- |
| **1 · Gancho** | 00:00–00:08 | **Plano/encuadre:** …<br>**Acción/movimiento:** …<br>**Texto en pantalla:** «…» (exacto)<br>**Pattern interrupt:** … | **Voz:** «locución exacta o su inicio»<br>**SFX:** …<br>**Música:** pista y nivel | Animación propia · imagen M0x (ficha) · captura, etc. |

- Una fila por cambio de escena, de modo que **ningún tramo supere el límite de 15–30 s sin cambio visual**.
- **Columna de origen y licencia (obligatoria):** cada imagen real remite a su fila del registro de licencias; cada cifra en pantalla remite a su fila de la hoja de verificación; lo animado «propio (código)».
- **Columna opcional «Prompt de generación IA»** (solo si el estilo incluye IA): en inglés, con la forma `[Entorno] + [Sujeto y acción] + [Encuadre y ángulo] + [Iluminación y estilo] --ar 16:9|9:16`. Reglas: **solo para fondos o ilustraciones abstractas**, nunca para presentar algo como foto real, ni personas reales, ni logos, ni marcas; todo lo generado con IA se **rotula** y se **declara** en Studio.

### 4.3 Checklist de postproducción y control de retención
- [ ] **Variación de planos:** alternancia entre abiertos y cerrados; no hay tramos largos sin cambio.
- [ ] **Sincronía audio/visual:** cada rótulo entra en la palabra que lo nombra (tiempos reales).
- [ ] **Comprensión muda:** los textos y gráficos transmiten la idea sin audio.
- [ ] **Ritmo de sonido:** puntos de cambio de música, silencio antes de las revelaciones, bajada de música bajo la voz; cortes en J o en L cuando haya imagen en directo.
- [ ] **Licencias:** toda imagen y pista con fila ✅ en el registro; créditos y atribuciones (p. ej. CC BY-SA) en pantalla y descripción.
- [ ] **Cifras:** cada rótulo coincide palabra por palabra con la hoja de verificación.
- [ ] **Veracidad visual:** nada que parezca real y no lo sea sin rótulo («Ilustración propia», «Esquema no a escala»).
- [ ] **Accesibilidad:** contraste, tamaño de texto legible en móvil, subtítulos.
- [ ] **Coherencia** con el título y la miniatura.

## 6. REGLAS DE COMPOSICIÓN (obligatorias; añadidas el 14-oct-2026 tras revisar el video 2)
1. **Nada se tapa con nada.** Ningún elemento de una escena (título, texto, gráfica, imagen, icono) puede quedar debajo ni encima de otro elemento que esté visible a la vez: rótulos «Dato verificado», créditos, tarjetas de capítulo, subtítulos o cualquier otro texto de la escena. Si dos cosas compiten por el mismo espacio, se reubica, se acorta o se retrasa una de ellas.
2. **Zonas fijas** (1920×1080): rótulo de dato abajo a la izquierda (la caja mide hasta ≈ 150 px de alto: ocupa desde ≈ y 765 hasta 912, y hasta ≈ 1180 px de ancho); créditos y tarjeta de capítulo arriba a la derecha (≈ y 46–216); subtítulos, si se queman, abajo centrados. **El contenido de la escena vive en la zona segura** (≈ y 150–745 y fuera de esas cajas) mientras haya un rótulo, crédito o tarjeta visible. Los títulos centrados no pasan de ≈ 800 px de ancho (≈ 34 caracteres a tamaño 44–50) para no chocar con la tarjeta de capítulo; **nunca se reubican en pleno video** (un cambio de posición se ve como un salto).
   Además, todo lo que se mueve lo hace de forma continua: posiciones y zooms con decimales (subpíxel), sin redondear a enteros.
3. **Texto dentro de su caja.** Si un texto no cabe, se agranda la caja o se divide el texto; nunca se sale ni se corta.
4. **Imágenes sin bordes duros.** Ninguna imagen real se muestra como rectángulo con esquinas vivas sobre el fondo: máscara elíptica o con esquinas redondeadas y borde difuminado; una imagen con fondo negro propio se recorta a su forma real.
5. **El fondo no debe delatar costuras.** Fondos que se mueven: movimiento continuo (subpíxel) y texturas periódicas sin cortes; nada que parezca «dos imágenes pegadas».
6. **Gráficas que se entienden solas:** ejes con nombre en lenguaje llano, sentido de lectura («más joven ← → más viejo»), una línea de explicación debajo y lo importante resaltado en el color del canal. Cada gráfica debe poder explicarse a alguien que no vio el resto del video.
7. **Ilustrar, no solo rotular.** Cuando se explica un mecanismo (por ejemplo, un método de medición), se dibuja la idea con una imagen o animación simple; no basta una caja con texto.
8. **Verificación automática antes de renderizar:** el script de montaje debe poder comprobar solapes (contenido frente a rótulos, créditos y tarjetas) en fotogramas cada ~1 s y listar los que fallen; no se renderiza el video completo con solapes sin resolver.

9. **Un solo estilo para toda caja de texto:** toda caja, etiqueta o chip de texto usa el estilo de los rótulos «Dato verificado» (cristal oscuro con esquina cortada, barra lateral de color e icono hexagonal). No se usan cápsulas redondeadas con borde ni otras variantes. En el código compartido, `ui.caja` y `ui.pastilla` ya lo cumplen; hay que usarlas siempre y no dibujar cajas por cuenta propia.

## 5. ENTREGA
Guarda la escaleta como archivo del video (p. ej. `03-escaleta/escaleta-audiovisual.md` dentro de la carpeta del video) y úsala como **fuente de verdad del montaje**: los nombres de escena de la tabla son los que se usan en el script de montaje.
