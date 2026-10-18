# Voz del video con Google Cloud Text-to-Speech (Chirp 3: HD)

Convierte el guion (`.md`) en un audio WAV listo para editar. Solo usa Node (sin instalar nada). Cuesta **0 USD** mientras no pases de **1 000 000 de caracteres al mes** (un video de este canal gasta ~6 000–12 000). Comparativa y motivos: [../../00_contexto/Voz-IA-comparativa.md](../../00_contexto/Voz-IA-comparativa.md).

## Una sola vez: preparar Google Cloud (15 min)
> Los nombres de los menús pueden variar un poco. Haz estos pasos tú: la clave es tuya y no debe pegarse en el chat.
1. Entra a `console.cloud.google.com` con tu cuenta, crea un proyecto (p. ej. «mi-canal») y **activa la facturación** (pide tarjeta; solo cobra si pasas del límite gratuito).
2. **Pon una alerta de presupuesto** de 1 USD (Facturación → Presupuestos y alertas).
3. **APIs y servicios → Biblioteca** → busca **«Cloud Text-to-Speech API»** → **Habilitar**.
4. **APIs y servicios → Credenciales → Crear credenciales → Clave de API.** En «Restricciones de API» elige **Cloud Text-to-Speech API**. Copia la clave.
5. **Guarda captura** de los términos del servicio y de esta página de precios con la fecha (registro de licencias, regla 3).

## Cada vez que lo uses
En PowerShell, en esta carpeta (la clave dura solo mientras la ventana esté abierta):
```powershell
$env:GOOGLE_TTS_API_KEY = "TU_CLAVE"
```

### 1. Ver qué leería la voz (no usa red ni clave)
```powershell
node sintetizar.mjs "..\..\02_canales\<canal>\Video NN - Nombre\Guion.md" --solo-texto
```
(Ejemplo con el video 2. Cada video tiene su carpeta `Video NN - Nombre\` con su `Guion.md` y su carpeta `Voz\`.)
Muestra los párrafos que se leerán, los caracteres, las partes y la duración estimada. **Solo se lee la sección «## Guion»**: se quitan los encabezados, las indicaciones `[Pantalla: …]` y las marcas `[✔ n]` / `[REVISAR]`.

### 2. Listar las voces de español
```powershell
node sintetizar.mjs --voces
```

### 3. Generar el audio
```powershell
node sintetizar.mjs "..\..\02_canales\<canal>\Video NN - Nombre\Guion.md" --salida "..\..\02_canales\<canal>\Video NN - Nombre\Voz"
```
Con `--salida` el resultado queda **dentro de la carpeta del video** (`Voz\`); sin ella iría a `herramientas\voz\salida\<nombre-del-guion>\` (solo para pruebas). Contenido:
- `…wav` → el audio completo (con 0,6 s de pausa entre partes; se cambia con `--pausa`).
- `partes\01.wav, 02.wav…` → cada parte por separado.
- `ajustes.txt` → voz y ritmo usados (para repetir lo mismo en todos los videos).

### 4. Repetir solo una parte
Si una parte suena mal, corrige el texto (o añade una línea en `sustituciones.json`) y repite solo esa:
```powershell
node sintetizar.mjs "..\..\02_canales\<canal>\Video NN - Nombre\Guion.md" --salida "..\..\02_canales\<canal>\Video NN - Nombre\Voz" --solo 3
```
Usa **la misma voz y el mismo ritmo** que en el resto (los valores por defecto ya son los del canal: no pongas `--voz` ni `--ritmo`). El script vuelve a unir todo.

## Opciones
| Opción | Qué hace |
|---|---|
| `--voz` | Nombre de la voz. **Por defecto la voz del canal: `es-US-Chirp3-HD-Iapetus`** (elegida el 13-oct-2026 tras comparar con Algenib, Sadachbia y Sadaltager). Para España: `es-ES-Chirp3-HD-…` |
| `--ritmo` | Velocidad de 0,25 a 2 (1 = normal). **Por defecto 1,0**, el ritmo elegido para el canal (13-oct-2026; antes se usó 0,95, y se probaron 0,85, 0,90, 0,93 y 1,05) |
| `--formato` | `wav` (por defecto, para editar) o `mp3` (las partes se pegan sin pausa) |
| `--pausa` | Segundos entre partes en WAV (0,6 por defecto) |
| `--salida` | Carpeta de salida |
| `--solo N` | Genera solo la parte N |
| `--solo-texto` | Muestra el texto y el consumo, sin llamar a Google |
| `--sustituciones` | Archivo JSON con cambios de texto (por defecto `sustituciones.json`) |
| `--pronunciaciones` | Archivo JSON con pronunciaciones IPA/X-SAMPA (por defecto `pronunciaciones.json`) |
| `--pausa-parrafo` | Pausa automática entre párrafos: `ninguna` (por defecto), `corta`, `normal` o `larga` |
| `--permitir-pago` | Permite pasar del millón gratuito (por defecto el script se **detiene** antes) |

## Pausas
Dentro de «## Guion» puedes escribir `{pausa corta}`, `{pausa}` o `{pausa larga}` donde quieras que la voz respire (por ejemplo, antes de una cifra importante o después de una pregunta). Se escriben con **llaves** porque los `[corchetes]` se descartan como indicaciones de pantalla. El script las convierte en `[pause short]`, `[pause]` y `[pause long]` y las envía en el campo `markup` de la API.
- Funcionan **solo con voces Chirp 3: HD**. Google dice que la duración no es fija (la ajusta el modelo según el contexto) y que a veces las ignora si están en un lugar poco natural. No abuses.
- Otra marca entre llaves (`{pausa media}`) da un error claro antes de gastar caracteres.
- `--pausa-parrafo corta` añade una pausa corta entre párrafos de una misma parte. Entre partes ya hay una pausa de `--pausa` segundos en el WAV.
- La puntuación también cuenta: el punto hace una pausa larga, la coma una corta, y los puntos suspensivos o el guion, una pausa dramática. Partir las frases largas ayuda más que añadir etiquetas.
- Las etiquetas cuentan como caracteres del consumo mensual.

## Pronunciaciones propias (`pronunciaciones.json`)
Para una palabra que suene mal (nombres propios, siglas), añade una entrada con su pronunciación en **IPA** o **X-SAMPA**:
```json
{ "Canberra": { "ipa": "kamˈbeɾa" } }
```
- La frase debe aparecer **idéntica** en el texto que se envía (después de `sustituciones.json`). Solo se envían las entradas cuya frase aparece en esa parte.
- `sustituciones.json` cambia el **texto** («kilobytes» → «kilobáits»); `pronunciaciones.json` cambia **cómo suena** sin tocar el texto. Usa primero la sustitución, que es más simple, y la pronunciación fonética cuando no baste.
- **Aviso:** la referencia de la API dice que las pronunciaciones empezaron solo para `en-US`; la guía de Chirp 3: HD (actualizada el 9-oct-2026) no excluye el español. Comprueba de oído y, si da error o no cambia nada, vacía el archivo y usa solo sustituciones.

## `sustituciones.json`: cómo arreglar pronunciaciones
Cada línea cambia un texto antes de enviarlo a la voz. Ejemplo: `"AC +79 3888": "A C más setenta y nueve tres ocho ocho ocho"`. Cuando algo suene raro (siglas, cifras, nombres), añade una línea y repite solo esa parte.

## Seguridad y consumo
- La clave **solo** se lee de la variable `GOOGLE_TTS_API_KEY`; viaja en una cabecera y nunca se imprime ni se guarda.
- El script **cuenta los caracteres del mes** en `.uso-mensual.json` y **se detiene antes de pasar del millón gratuito** (también avisa a los 800 000). Es un cálculo local: lo exacto está en la consola de Google Cloud.
- **No subas ni compartas** este archivo si en algún momento escribes una clave dentro de él (no hace falta).

## Reglas del canal (recuérdalas al publicar)
- **Declaración de IA (regla 4):** responde con honestidad la pregunta de «contenido alterado o sintético» en Studio. Si la voz suena real, declara.
- **Sin voces de personas reales ni modificadores para esquivar la detección** (reglas 7 y 19).
- Guarda en el registro de licencias: captura de los términos, la fecha, la voz y el ritmo.

## Pruebas del propio script
```powershell
node --test sintetizar.test.mjs
```
Comprueban la extracción del guion, el troceo, la unión de audios, los reintentos y que la clave no se filtra. **No llaman a Google.**
