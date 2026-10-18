# Voz IA: comparativa de herramientas (consultado el 12-oct-2026)

> Criterio principal: **licencia que permita usar la voz en un canal monetizado** (regla 3), después calidad en español, costo y esfuerzo. Los precios y condiciones cambian: **guarda una captura de la licencia y del plan** el día que elijas (regla 3 y registro de licencias).
> Medida de consumo: un video de ~12 min ≈ 1 800 palabras ≈ **~11 000 caracteres**. Con 4–5 videos al mes y alguna repetición: **~50 000–70 000 caracteres/mes**.

## Resumen

| Herramienta | ¿Licencia comercial / YouTube? | Costo para ~5 videos/mes | Español | Veredicto |
|---|---|---|---|---|
| **Google Cloud Text-to-Speech · Chirp 3: HD** | Sin requisito de atribución (según respuesta de la comunidad de Google; **leer los términos de Cloud al activarlo**) | **0 USD**: **1 000 000 de caracteres gratis al mes** (≈ 90 videos), después 30 USD por millón | ✅ es-ES y es-US, 30 voces | ⭐ **Recomendada para empezar** (gratis, controlable). Requiere activar facturación (tarjeta) y un pequeño script |
| **ElevenLabs** | **Solo planes de pago.** El plan gratis NO tiene licencia comercial y exige atribución | Starter **6 USD** (30 k créditos ≈ 2–3 videos) · **Creator 22 USD** (121 k ≈ 10 videos) | ✅ Muy natural | 🥈 La mejor calidad. Usar **Creator** si quieres 1 video por semana |
| **Gemini TTS** (AI Studio / API de Gemini) | **Zona gris:** Google no reclama la propiedad del contenido, pero los términos dicen que AI Studio/Gemini API es «para desarrolladores… no para uso de consumidores»; el soporte no dio un «sí» explícito para YouTube. Modelos en *Preview* | Gratis en AI Studio (sin facturación, con tus textos usados para mejorar productos); de pago: ≈ 0,18 USD por video | ✅ Buena, con control de estilo por texto | 🟡 Evitar para un canal monetizado hasta tener una confirmación clara |
| **GenAI Pro** | Su web dice «Commercial License» incluso en el plan gratis (10 000 caracteres/mes); **no leí sus términos** | Pro **14,99 USD/mes** (1 M de caracteres). El video citaba ~8 USD: **ya no coincide** | ✅ (dice 100+ idiomas) | 🟡 Solo si lees y guardas sus términos. La web no identifica claramente a la empresa; hay dos sitios (`genaipro.co` y `genaipro.io`) |

## Detalle y por qué

### 1. Google Cloud Text-to-Speech (Chirp 3: HD) — opción recomendada
- **Gratis:** 0 a 1 millón de caracteres al mes con voces Chirp 3: HD; luego 30 USD por millón. Con un canal de 4–5 videos al mes eso equivale a cero costo.
- **Español:** `es-ES` (España) y `es-US` (español de EE. UU., más neutro para Latinoamérica). Voces de ejemplo: `es-US-Chirp3-HD-Kore`, `…-Charon`, `…-Aoede`, etc.
- **Control útil para un canal de ciencia:**
  - **Ritmo** (`speaking_rate` de 0,25 a 2).
  - **Pausas** (`[pause short]`, `[pause]`, `[pause long]`).
  - **Pronunciaciones propias** con IPA/X-SAMPA para nombres difíciles: *Voyager, heliopausa, Morabito, Ío, Titán, AC +79 3888*.
- **Formatos:** MP3, OGG_OPUS, PCM en lote.
- **Lo que hay que hacer:** crear una cuenta de Google Cloud y **activar facturación** (pide tarjeta; solo se cobra si pasas del límite gratuito), habilitar la API y generar el audio con un script o desde la consola. **Pon una alerta de presupuesto** (p. ej., 1 USD).
- **Licencia:** una respuesta en el foro de desarrolladores de Google dice que Text-to-Speech **no tiene requisitos de atribución** y que puedes usar los audios en tus aplicaciones. Es una fuente secundaria: **confirma en los Términos de Google Cloud** y guarda captura.
- **Límite que no verifiqué:** el tamaño máximo por petición (hay que enviar el guion en trozos). El script lo resuelve.

### 2. ElevenLabs — la más natural, de pago
- **Plan gratis:** 10 000 créditos al mes, **sin licencia comercial y con atribución obligatoria**. No sirve para el canal.
- **Regla clave:** lo que generes **antes o después** de una suscripción de pago **no se puede usar comercialmente**. Si pruebas en el plan gratis, **vuelve a generar** todo con el plan de pago.
- **Planes (precios de la página oficial):** Starter 6 USD (30 000 créditos; la web muestra una oferta de primer mes hasta el 18-oct) · **Creator 22 USD** (121 000; primer mes 11 USD) · Pro 99 USD.
- **Créditos:** 1 carácter = 1 crédito en los modelos multilingües; los no usados se acumulan hasta 2 meses si mantienes la suscripción.
- **Cuenta:** un video de ~11 000 caracteres usa ~11 000 créditos. Starter da para 2–3 videos al mes; **Creator** cubre 1 por semana con repeticiones.
- **Regla 21:** no abras cuentas gratuitas repetidas para conseguir más créditos.

### 3. Gemini TTS (Google AI Studio / API de Gemini)
- **A favor:** voces expresivas con instrucciones en texto, buena calidad, precio bajo si se paga: ≈ **0,015 USD por minuto** (modelo 2.5 Flash TTS: 10 USD por millón de tokens de audio, 25 tokens por segundo) → ≈ **0,18 USD por video**.
- **En contra:**
  - Los términos (vigentes desde el 23-mar-2026) dicen que AI Studio y la API de Gemini son «para desarrolladores que construyen con modelos de Google para fines profesionales o de negocio, **no para uso de consumidores**». No queda claro que un creador personal pueda monetizar un canal.
  - Un empleado de Google, ante la pregunta de si se puede usar en YouTube monetizado, respondió solo con un enlace a los términos y con que **los modelos *Preview* pueden cambiar**.
  - En AI Studio gratis, **tus textos y respuestas se usan para mejorar productos y pueden ser leídos por revisores**. En la versión de pago no se usan.
- **Veredicto:** no usarla para un canal monetizado hasta que haya una confirmación clara. Sí sirve para probar voces.

### 4. GenAI Pro
- La web dice que incluye **licencia comercial** hasta en el plan gratis. Pro cuesta **14,99 USD/mes** (1 M de caracteres). El video B1 la citaba a ~8 USD: el precio cambió.
- Hay **dos sitios** con el mismo nombre (`genaipro.co` y `genaipro.io`, este último con paquetes de créditos). **No leí sus términos** y la página no identifica con claridad quién es la empresa. Si la eliges, lee los términos, guarda captura y prueba primero el plan gratis con un párrafo.

## Mi recomendación
1. **Empieza con Google Cloud Text-to-Speech (Chirp 3: HD):** cuesta cero y te da control de ritmo, pausas y pronunciaciones. Si prefieres no tocar Google Cloud, entonces…
2. **…ElevenLabs Creator (22 USD, 11 USD el primer mes)** y empiezas **de pago desde el primer audio** para que la licencia cubra todo.
3. Descarta por ahora: ElevenLabs gratis, Gemini TTS en AI Studio y GenAI Pro sin leer sus términos.

## Prueba de 5 minutos (antes de decidir)
Genera con 2 o 3 voces **este mismo párrafo** del gancho del video 1:

> «En 1977 lanzamos una nave cuyos ordenadores tienen, en total, unos 69 kilobytes de memoria. Hoy, casi cincuenta años después, sigue funcionando, y una orden de radio, viajando a la velocidad de la luz, tarda unas 23 horas en llegar hasta ella. El 18 de noviembre de este año se convertirá en el primer objeto construido por humanos a un día luz de la Tierra.»

Elige con esta lista:
- [ ] Pronuncia bien: *Voyager, kilobytes, 1977, 18 de noviembre*.
- [ ] Español neutro, sin acento marcado ni cortes extraños.
- [ ] Ritmo natural; las pausas caen donde toca.
- [ ] Se puede escuchar 10 minutos sin cansarse.
- [ ] **Licencia:** captura de la página de términos o del plan (con fecha) guardada en el registro.
- [ ] Voz y ajustes elegidos y **fijos para todos los videos** (consistencia de marca).

## Reglas del proyecto sobre la voz (todos los canales)
- **Declaración de IA (regla 4):** responde con honestidad la pregunta de «contenido alterado o sintético». Si la voz suena real, **declara**.
- **Sin clonar voces de personas reales** (regla 19), ni imitar a Carl Sagan o a presentadores.
- **Sin modificadores para esquivar la detección** de IA (regla 7).
- Si algún día grabas tu propia voz, el canal gana personalidad: se puede añadir después.
