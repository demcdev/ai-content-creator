# Video 1 · Capítulos, descripción y datos de subida (v2, 13-oct-2026)

> Se corresponde con el guion v3 ([Guion](../01-guion/guion.md)) y con la hoja de cifras ([Verificacion de cifras](../01-guion/verificacion-de-cifras.md)). Los tiempos de los capítulos son los del **video final de 12:36** (voz Iapetus a ritmo 1,0), calculados con el mismo montaje, frase a frase (`videos/01-voyager-1/06-montaje/capitulos.py`). Compruébalos en el reproductor al subir (margen ≈ ±2 s).
> Todo lo que está entre `[CORCHETES]` en el texto para pegar es algo que **solo tú puedes completar** el día de subir.

## 1. Capítulos (para pegar en la descripción)

Reglas de YouTube para que se activen: el primero debe ser **0:00**, mínimo **3 capítulos**, cada uno de **10 s o más**, en orden creciente y con el formato `m:ss`.

| Tiempo en el video final (12:36, ±2 s) | Capítulo (título que verá el espectador) | Sección del guion |
|---|---|---|
| 0:00 | La nave que está a un día luz | Gancho |
| 0:51 | Qué es Voyager 1 | Qué es y por qué importa |
| 1:47 | El gran viaje: Júpiter, Saturno y Titán | Acto 1 |
| 3:52 | El punto azul pálido | Acto 2 |
| 5:07 | ¿Cómo sabemos que cruzó la frontera del Sol? | Acto 3 |
| 7:20 | Cómo se habla con una nave a casi 26 000 millones de km | Acto 4 |
| 8:35 | Energía, un fallo y una reparación a distancia | Acto 5 |
| 10:13 | Lo que NO sabemos (y la frase que no es cierta) | Lo que no sabemos |
| 11:35 | El disco de oro y el próximo destino | Cierre |

> **Paso 1 — comprobar los tiempos:** al subir el video, mueve el cursor a cada tiempo y confirma que cae al inicio de la sección. Si renderizas otra vez (otra voz, otra música con distinta duración o cambios de guion), corre `python capitulos.py` y pega la lista nueva aquí y en la descripción.
> Los títulos de capítulo son **honestos y descriptivos** (regla 9): no adelantan nada que el video no entregue.

## 2. Descripción final (copiar y pegar)

> Límite de YouTube: 5 000 caracteres. Este texto ocupa unos 4 600 (comprobado el 13-oct-2026; deja margen si añades algo). Las **dos primeras líneas** son las que se ven antes de «Mostrar más», por eso llevan lo esencial.
> Usa la **variante A** si publicas **antes del 18-nov-2026**. Si publicas después, usa la **variante B** (cambia solo el primer párrafo).

### Variante A (antes del 18-nov-2026)

```
En 1977 se lanzó una nave con apenas 69 kilobytes de memoria (menos que una sola foto de móvil) y hoy es lo más lejano que ha construido la humanidad. Voyager 1 está a punto de estar a un día luz de la Tierra: la NASA lo calcula para el 18 de noviembre de 2026, a las 2:16 a. m. (hora del Pacífico).
```

### Variante B (después del 18-nov-2026)

```
En 1977 se lanzó una nave con apenas 69 kilobytes de memoria (menos que una sola foto de móvil) y hoy es lo más lejano que ha construido la humanidad. El 18 de noviembre de 2026 (2:16 a. m., hora del Pacífico, según la NASA) Voyager 1 llegó a un día luz de la Tierra: una orden de radio tarda ya 24 horas en alcanzarla.
```

> Si usas la B, **comprueba** primero en la página de la NASA que el hito ocurrió como se anunció.

### Resto de la descripción (igual para A y B)

```
En este video: qué descubrió en Júpiter, Saturno y Titán, cómo sabemos que cruzó la frontera de la burbuja del Sol, cómo se le habla a casi 26 000 millones de kilómetros, qué le queda de energía y qué NO sabemos todavía, incluida una frase que se repite mucho y no es del todo cierta.

CAPÍTULOS
0:00 La nave que está a un día luz
0:51 Qué es Voyager 1
1:47 El gran viaje: Júpiter, Saturno y Titán
3:52 El punto azul pálido
5:07 ¿Cómo sabemos que cruzó la frontera del Sol?
7:20 Cómo se habla con una nave a casi 26 000 millones de km
8:35 Energía, un fallo y una reparación a distancia
10:13 Lo que NO sabemos (y la frase que no es cierta)
11:35 El disco de oro y el próximo destino

FUENTES (consultadas el 12 y 13-oct-2026)
• NASA: Voyager 1 — https://science.nasa.gov/mission/voyager/voyager-1/
• NASA: ¿Qué es un día luz? (fecha del hito) — https://science.nasa.gov/mission/voyager/voyager-1/voyager-1-what-is-a-light-day/
• NASA: la nave (antena, transmisor, energía) — https://science.nasa.gov/mission/voyager/spacecraft/
• NASA: preguntas frecuentes (nube de Oort y próxima estrella) — https://science.nasa.gov/mission/voyager/frequently-asked-questions/
• NASA: el «punto azul pálido» — https://science.nasa.gov/mission/voyager/voyager-1s-pale-blue-dot/
• NASA: contenido del disco de oro — https://science.nasa.gov/mission/voyager/golden-record-contents/
• NASA: apagado de un instrumento, 17-abr-2026 — https://science.nasa.gov/blogs/voyager/2026/04/17/nasa-shuts-off-instrument-on-voyager-1-to-keep-spacecraft-operating/
• NASA Space Place: la Red de Espacio Profundo — https://spaceplace.nasa.gov/dsn-antennas/
• JPL: cómo sabemos cuándo se llega al espacio interestelar (2013) — https://www.jpl.nasa.gov/news/how-do-we-know-when-voyager-reaches-interstellar-space/
• JPL: Voyager 2 llega al espacio interestelar — https://www.jpl.nasa.gov/edu/resources/teachable-moment/then-there-were-two-voyager-2-reaches-interstellar-space/
• JPL: el fallo de 2023 y su reparación (abril de 2024) — https://www.jpl.nasa.gov/news/nasas-voyager-1-resumes-sending-engineering-updates-to-earth/
• JPL: el volcán de Ío — https://www.jpl.nasa.gov/images/pia00379-volcanic-eruptions-on-io/
• NASA: instrumentos científicos de la sonda (diagrama) — https://science.nasa.gov/mission/voyager/instruments/
• MuckRock (2016): respuesta de la NASA a una solicitud de información pública (FOIA) sobre la memoria de a bordo, 69,63 kilobytes — https://www.muckrock.com/foi/united-states-of-america-10/nasa-voyager-computer-24583/
• NASA (historia): «Voyager: The Grand Tour of Big Science» — https://www.nasa.gov/history/SP-4219/Chapter11.html
• NASA NTRS: «Voyager's Grand Tour» (alineación de planetas) — https://ntrs.nasa.gov/citations/20170009181
• Universidad de Cornell: el «zumbido» del gas interestelar (2021) — https://astro.cornell.edu/news/emptiness-space-voyager-1-detects-plasma-hum
• Nature Astronomy: «Persistent plasma waves in interstellar space detected by Voyager 1» — https://www.nature.com/articles/s41550-021-01363-7

CÁLCULOS PROPIOS (con cifras de las fuentes de arriba)
• Distancia que se aleja por día: 17 km/s × 86 400 s ≈ 1,47 millones de km.
• Una foto de 3 MB a 160 bits por segundo: 3 × 8 × 10⁶ ÷ 160 ≈ 150 000 s ≈ 42 horas (el tamaño de 3 MB es solo un ejemplo).
• Ida y vuelta de una orden: 2 × 23 h ≈ 46 horas.
• Memoria frente a un móvil y un portátil: una foto de móvil de 3 MB ÷ 69 KB ≈ 43 veces; un portátil con 8 GB ÷ 69 KB ≈ 116 000 veces (tamaños de ejemplo, no datos de la NASA).

TRANSPARENCIA
• La narración de este video usa una voz generada con inteligencia artificial.
• Imágenes: NASA/JPL, NASA/JPL-Caltech, NASA/JPL/University of Arizona (Ío, sonda Galileo) y NASA/CSIRO/Canberra Deep Space Communication Complex. Contornos de los continentes: Natural Earth (dominio público). Animaciones y esquemas: propios de Hace Eones.
• Este canal no está afiliado a la NASA ni cuenta con su respaldo.
• Música: «False Vacuum Decay», «Rapid Unscheduled Disassembly» y «Spaghettification», de The Grey Room / Density & Time — Biblioteca de audio de YouTube.

¿Viste un error o una cifra que quieras que revisemos? Escríbelo en los comentarios: lo comprobamos, lo corregimos y lo anotamos aquí.

PRÓXIMO VIDEO: cómo sabemos la edad del universo sin que nadie estuviera allí.

#Voyager1 #Astronomía #Espacio
```

> Notas sobre este texto:
> - **Hashtags:** YouTube muestra los **tres primeros** sobre el título; por eso son solo tres y describen lo que hay en el video.
> - **Música:** ya están los nombres reales (no exigen atribución; se citan por transparencia). Guarda en el registro de licencias la captura de cada pista en la Biblioteca de audio.
> - **Transparencia:** la línea de la voz IA es la misma respuesta que darás en Studio (ver abajo). Si al montar usas otro material, cambia las líneas de imágenes para que digan la verdad.
> - **Sin enlaces a tiendas ni afiliados:** el video no tiene patrocinio, producto gratis ni comisión; por eso no se marca «promoción de pago» (regla 20). Si algún día lo tiene, se declara.
> - Si añades más fuentes en el guion final, agrégalas aquí con su URL.

## 3. Datos de Studio al subir (resumen)

| Campo | Valor recomendado | Por qué |
|---|---|---|
| Título | El elegido en el test (ver Packaging del guion) | Regla 9: promete solo lo que entrega |
| Visibilidad al subir | **No listado** hasta revisar | Regla 17: esperar las comprobaciones de copyright y monetización |
| Idioma del video | Español | Idioma admitido (regla 22) |
| Categoría | Ciencia y tecnología | Es divulgación científica |
| ¿Es contenido para niños? | **No** | Público general (regla 18); responde según el contenido real |
| Contenido alterado o sintético | **Sí** (voz generada con IA) | Regla 4: ante la duda, declarar |
| Promoción de pago | No | Sin patrocinio ni afiliados (regla 20) |
| Subtítulos | El video **no lleva subtítulos incrustados**. En Studio → Subtítulos → Español → «Subir archivo»: (a) el texto `texto-para-subtitulos.txt` con **sincronización automática** (recomendado) o (b) `video-01-subtitulos.srt` | Accesibilidad, búsqueda y traducciones; el espectador los activa si quiere |
| Etiquetas | `Voyager 1`, `NASA`, `sonda espacial`, `espacio interestelar`, `heliosfera`, `punto azul pálido`, `Carl Sagan`, `nube de Oort`, `disco de oro`, `astronomía` | Pesan poco; sirven para ortografías alternativas. **Solo temas que el video trata** |
| Miniatura | **Elegida:** `videos/01-voyager-1/07-miniaturas/miniatura-FINAL-a-casi-1-dia-luz.png` («A CASI 1 DÍA LUZ»; si se publica después del hito del 18-nov, usar la variante sin «CASI»). Alternativas hechas: V1 a V4, A, B y C para un test A/B. Con el título 2 (el texto repite el título 1) | Complementa el título; A usa la ilustración PIA26353 de NASA/JPL-Caltech, rotulada en el video como concepto artístico |
| Pantalla final / tarjetas | Ninguna en el video 1 (aún no hay otro video al que enviar) | — |

## 4. Comentario fijado (publicarlo tú, con tu cuenta, justo después de publicar)

```
Las cifras que cambian con el tiempo (distancia, instrumentos que siguen encendidos) se pueden comprobar aquí:
• Dónde está cada Voyager ahora: https://science.nasa.gov/mission/voyager/where-are-they-now/
• Qué antena le habla hoy: https://eyes.nasa.gov/dsn/dsn.html

Todas las fuentes de este video están en la descripción. Si encuentras un dato que creas incorrecto, cuéntalo con la fuente y lo revisamos.
```

> Las dos direcciones salen de la página de la misión Voyager 1 de la NASA (consultada el 12-oct-2026). Antes de fijarlo, **ábrelas** para comprobar que siguen activas.

## 5. Plan de actualización del hito (opcional, recomendado)

- **18-nov-2026:** mira la página oficial; si el hito ocurre como se anunció, publica un **Short o un video breve propio** con la cuenta atrás y la cifra real (no reutilices el video 1), y añade a la descripción del video 1 una línea con el enlace.
- Si el video 1 se publica **después** del hito, cambia el primer párrafo a la variante B y actualiza el comentario fijado.
- Guarda esta versión de la descripción en el **historial de producción** (regla 6).

## 6. Revisión final antes de pulsar «Publicar»
- [ ] Tiempos de capítulos comprobados en el reproductor (primer capítulo en 0:00; los de arriba son los del video de 12:36)
- [ ] Variante A o B elegida según la fecha de publicación, y comprobada contra la página de la NASA
- [ ] Música: capturas de licencia de las tres pistas guardadas (nombres ya en la descripción)
- [ ] Subtítulos subidos (texto con sincronización automática o el .srt) y revisados en Studio
- [ ] Todas las URLs de la descripción abren (se comprobaron el 12-oct-2026; las páginas cambian)
- [ ] Cada cifra de pantalla coincide con la hoja de cifras; los `[REVISAR]` del guion están resueltos
- [ ] «Contenido alterado o sintético» y «para niños» respondidos según lo anterior
- [ ] Subido como **no listado**; esperar los avisos y recién entonces pasar a público
