import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import test from 'node:test'
import {
  aplicarSustituciones, convertirPausas, crearWav, duracionWav, extraerNarracion, leerArgumentos, leerPronunciaciones,
  leerWav, listarVoces, prepararTrozo, principal, sintetizar, trocear, unirWav,
} from './sintetizar.mjs'

const GUION = `# Titulo
> nota
## Packaging
**Títulos:** no se leen
## Guion
### 0:00 · Gancho
[Pantalla: mapa. «≈ 25 900 millones de km» **[✔ 1]**.]

En 1977 lanzamos una nave con unos 69 kilobytes **[✔ 12]**. Hoy sigue funcionando **[REVISAR: dato]**.

### 1:30 · Acto 1
- **Comprobado:** sus instrumentos miden el medio.
---
## Qué se ve en pantalla
| tabla | no se lee |
`

test('extrae solo la narración: sin pantalla, marcas, encabezados ni otras secciones', () => {
  const p = extraerNarracion(GUION)
  assert.deepEqual(p, [
    'En 1977 lanzamos una nave con unos 69 kilobytes. Hoy sigue funcionando.',
    'Comprobado: sus instrumentos miden el medio.',
  ])
})

test('quita corchetes anidados y deja la puntuación limpia', () => {
  const p = extraerNarracion('## Guion\nHola [Pantalla: «x» **[✔ 3]**.] mundo **[REVISAR]**.\n')
  assert.deepEqual(p, ['Hola mundo.'])
})

test('aplica sustituciones de texto', () => {
  assert.deepEqual(aplicarSustituciones(['Pasa por AC +79 3888.'], [['AC +79 3888', 'A C']]), ['Pasa por A C.'])
})

test('trocea sin pasar del límite de bytes y sin perder texto', () => {
  const parrafos = Array.from({ length: 30 }, (_, i) => `Esta es la frase número ${i} del guion con acentos: ñandú y corazón.`.repeat(3))
  const trozos = trocear(parrafos, 600)
  assert.ok(trozos.length > 1)
  for (const t of trozos) assert.ok(Buffer.byteLength(t, 'utf8') <= 600)
  const unido = trozos.join(' ').replace(/\s+/g, ' ')
  assert.equal(unido.replace(/\s/g, '').length, parrafos.join(' ').replace(/\s/g, '').length)
})

test('un párrafo larguísimo sin puntos también se parte', () => {
  const trozos = trocear(['palabra '.repeat(900)], 500)
  assert.ok(trozos.length > 5)
  for (const t of trozos) assert.ok(Buffer.byteLength(t, 'utf8') <= 500)
})

test('WAV: leer, crear y unir con pausa', () => {
  const rate = 24000
  const a = crearWav(Buffer.alloc(rate * 2), rate) // 1 s
  const b = crearWav(Buffer.alloc(rate * 2 * 2), rate) // 2 s
  assert.equal(leerWav(a).rate, rate)
  const u = unirWav([a, b], 0.5)
  assert.ok(Math.abs(duracionWav(u) - 3.5) < 0.01)
  assert.throws(() => unirWav([a, crearWav(Buffer.alloc(100), 16000)]), /distinto formato/)
  assert.throws(() => leerWav(Buffer.from('nada')), /WAV válido/)
})

const respuestaOk = (buf) => ({ ok: true, status: 200, json: async () => ({ audioContent: buf.toString('base64') }) })

test('sintetizar envía la petición correcta y la clave por cabecera (no en la URL)', async () => {
  let llamada
  const fetchFalso = async (url, init) => { llamada = { url, init }; return respuestaOk(crearWav(Buffer.alloc(48000), 24000)) }
  const audio = await sintetizar({ texto: 'Hola', voz: 'es-US-Chirp3-HD-Kore', ritmo: 0.95, clave: 'CLAVE_FALSA' }, fetchFalso)
  assert.ok(audio.length > 44)
  assert.ok(!llamada.url.includes('CLAVE_FALSA'))
  assert.equal(llamada.init.headers['X-Goog-Api-Key'], 'CLAVE_FALSA')
  const cuerpo = JSON.parse(llamada.init.body)
  assert.equal(cuerpo.voice.name, 'es-US-Chirp3-HD-Kore')
  assert.equal(cuerpo.voice.languageCode, 'es-US')
  assert.equal(cuerpo.audioConfig.speakingRate, 0.95)
  assert.equal(cuerpo.audioConfig.audioEncoding, 'LINEAR16')
})

test('sintetizar reintenta en 429 y explica los errores sin mostrar la clave', async () => {
  let n = 0
  const f1 = async () => (++n < 3 ? { ok: false, status: 429, json: async () => ({}) } : respuestaOk(crearWav(Buffer.alloc(100), 24000)))
  await sintetizar({ texto: 'x', voz: 'es-US-Chirp3-HD-Kore', clave: 'K' }, f1, [1, 1, 1])
  assert.equal(n, 3)
  const f2 = async () => ({ ok: false, status: 403, json: async () => ({ error: { message: 'Cloud Text-to-Speech API has not been used in project 123' } }) })
  await assert.rejects(sintetizar({ texto: 'x', voz: 'es-US-Chirp3-HD-Kore', clave: 'SECRETA' }, f2), (e) => /Habilita/.test(e.message) && !e.message.includes('SECRETA'))
  await assert.rejects(sintetizar({ texto: 'x', voz: 'v', clave: '' }), /GOOGLE_TTS_API_KEY/)
})

test('listarVoces filtra las Chirp 3: HD', async () => {
  const f = async () => ({ ok: true, json: async () => ({ voices: [{ name: 'es-US-Chirp3-HD-Kore' }, { name: 'es-US-Standard-A' }, { name: 'es-ES-Chirp3-HD-Aoede' }] }) })
  assert.deepEqual(await listarVoces('K', f), ['es-ES-Chirp3-HD-Aoede', 'es-US-Chirp3-HD-Kore'])
})

test('argumentos: valores por defecto, validación y opciones desconocidas', () => {
  const o = leerArgumentos(['guion.md'])
  assert.equal(o.voz, 'es-US-Chirp3-HD-Iapetus')
  assert.equal(o.ritmo, 1.0)
  assert.equal(o.formato, 'wav')
  assert.throws(() => leerArgumentos(['g.md', '--ritmo', '5']), /ritmo/)
  assert.throws(() => leerArgumentos(['g.md', '--formato', 'ogg']), /formato/)
  assert.throws(() => leerArgumentos(['g.md', '--raro']), /desconocida/)
})

test('flujo completo con YouTube-Google simulado: genera partes, une y permite repetir una parte', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'voz-'))
  const guion = path.join(dir, 'g.md')
  const largo = Array.from({ length: 12 }, (_, i) => `Párrafo ${i}: ` + 'frase de prueba con tildes y ñ. '.repeat(40)).join('\n\n')
  fs.writeFileSync(guion, '## Guion\n\n' + largo + '\n')
  const salida = path.join(dir, 'out')
  const llamadas = []
  const f = async (_u, init) => { llamadas.push(JSON.parse(init.body).input.text); return respuestaOk(crearWav(Buffer.alloc(24000 * 2), 24000)) }
  const log = []
  await principal([guion, '--salida', salida, '--pausa', '0'], { GOOGLE_TTS_API_KEY: 'K', VOZ_USO_ARCHIVO: path.join(dir, 'uso.json') }, f, (t) => log.push(t))
  const partes = fs.readdirSync(path.join(salida, 'partes'))
  assert.equal(partes.length, llamadas.length)
  assert.ok(llamadas.length >= 2)
  assert.ok(fs.existsSync(path.join(salida, 'g.wav')))
  const antes = llamadas.length
  await principal([guion, '--salida', salida, '--solo', '1'], { GOOGLE_TTS_API_KEY: 'K', VOZ_USO_ARCHIVO: path.join(dir, 'uso.json') }, f, () => {})
  assert.equal(llamadas.length, antes + 1)
  await assert.rejects(principal([guion, '--salida', salida, '--solo', '99'], { GOOGLE_TTS_API_KEY: 'K', VOZ_USO_ARCHIVO: path.join(dir, 'uso.json') }, f, () => {}), /--solo/)
  fs.rmSync(dir, { recursive: true, force: true })
})

test('--solo-texto no usa red ni clave', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'voz-'))
  const guion = path.join(dir, 'g.md')
  fs.writeFileSync(guion, '## Guion\nHola mundo.\n')
  const f = async () => { throw new Error('no debe llamar a la red') }
  const log = []
  assert.equal(await principal([guion, '--solo-texto'], { VOZ_USO_ARCHIVO: path.join(dir, 'uso.json') }, f, (t) => log.push(t)), 0)
  assert.ok(log.join('\n').includes('Hola mundo.'))
  fs.rmSync(dir, { recursive: true, force: true })
})

test('las marcas {pausa…} sobreviven a la extracción y se convierten en etiquetas de Google', () => {
  const p = extraerNarracion('## Guion\nLo dijo así. {pausa larga} Y luego [Pantalla: x] siguió {Pausa corta} otra vez {pausa}.\n')
  assert.deepEqual(p, ['Lo dijo así. {pausa larga} Y luego siguió {Pausa corta} otra vez {pausa}.'])
  const c = convertirPausas(p[0])
  assert.equal(c.usaPausas, true)
  assert.equal(c.texto, 'Lo dijo así. [pause long] Y luego siguió [pause short] otra vez [pause].')
  assert.equal(convertirPausas('Sin marcas.').usaPausas, false)
  assert.throws(() => convertirPausas('Hola {pausa media} mundo'), /Marca desconocida/)
})

test('pausa entre párrafos: solo si se pide, y obliga a usar markup', () => {
  const t = 'Uno.\n\nDos.'
  assert.deepEqual(prepararTrozo(t), { texto: t, markup: false, pronunciaciones: [], caracteres: t.length })
  const p = prepararTrozo(t, { pausaParrafo: 'corta' })
  assert.equal(p.texto, 'Uno. [pause short] Dos.')
  assert.equal(p.markup, true)
  assert.throws(() => prepararTrozo(t, { pausaParrafo: 'enorme' }), /--pausa-parrafo/)
})

test('pronunciaciones: se leen de JSON, se validan y solo se envían las que aparecen tal cual', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'voz-'))
  const ruta = path.join(dir, 'p.json')
  fs.writeFileSync(ruta, JSON.stringify({ _ayuda: 'x', Canberra: { ipa: 'kamˈbeɾa' }, Goldstone: { xsampa: '"goldstoUn' } }))
  const lista = leerPronunciaciones(ruta)
  assert.deepEqual(lista.map((p) => [p.frase, p.codificacion]), [['Canberra', 'PHONETIC_ENCODING_IPA'], ['Goldstone', 'PHONETIC_ENCODING_X_SAMPA']])
  const p = prepararTrozo('Habla con Canberra hoy.', { pronunciaciones: lista })
  assert.deepEqual(p.pronunciaciones.map((x) => x.frase), ['Canberra'])
  assert.equal(p.markup, false)
  assert.deepEqual(leerPronunciaciones(path.join(dir, 'no-existe.json')), [])
  fs.writeFileSync(ruta, JSON.stringify({ Mal: { ipa: 'a', xsampa: 'b' } }))
  assert.throws(() => leerPronunciaciones(ruta), /Pronunciación inválida/)
  fs.writeFileSync(ruta, JSON.stringify({ Mal: 'texto' }))
  assert.throws(() => leerPronunciaciones(ruta), /Pronunciación inválida/)
  fs.rmSync(dir, { recursive: true, force: true })
})

test('sintetizar envía markup y customPronunciations con el formato de la API', async () => {
  let cuerpo
  const f = async (_u, init) => { cuerpo = JSON.parse(init.body); return respuestaOk(crearWav(Buffer.alloc(100), 24000)) }
  await sintetizar({ texto: 'Hola [pause long] Canberra', voz: 'es-US-Chirp3-HD-Iapetus', clave: 'K', markup: true, pronunciaciones: [{ frase: 'Canberra', codificacion: 'PHONETIC_ENCODING_IPA', pronunciacion: 'kamˈbeɾa' }] }, f)
  assert.deepEqual(cuerpo.input, { markup: 'Hola [pause long] Canberra', customPronunciations: { pronunciations: [{ phrase: 'Canberra', phoneticEncoding: 'PHONETIC_ENCODING_IPA', pronunciation: 'kamˈbeɾa' }] } })
  await sintetizar({ texto: 'Hola', voz: 'es-US-Chirp3-HD-Iapetus', clave: 'K' }, f)
  assert.deepEqual(cuerpo.input, { text: 'Hola' })
})

test('flujo completo con pausas y pronunciaciones; --solo-texto informa y no llama a la red', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'voz-'))
  const guion = path.join(dir, 'g.md')
  fs.writeFileSync(guion, '## Guion\n\nLlamó a Canberra. {pausa larga} Respondió.\n\nSegundo párrafo.\n')
  const pron = path.join(dir, 'p.json')
  fs.writeFileSync(pron, JSON.stringify({ Canberra: { ipa: 'kamˈbeɾa' }, Nunca: { ipa: 'x' } }))
  const env = { GOOGLE_TTS_API_KEY: 'K', VOZ_USO_ARCHIVO: path.join(dir, 'uso.json') }
  const log = []
  assert.equal(await principal([guion, '--solo-texto', '--pronunciaciones', pron, '--pausa-parrafo', 'corta'], env, async () => { throw new Error('sin red') }, (t) => log.push(t)), 0)
  const txt = log.join('\n')
  assert.match(txt, /Pausas marcadas en el guion: 1 · Pausa entre párrafos: corta/)
  assert.match(txt, /Pronunciaciones propias: 2 en el archivo, 1 presentes en este texto \(Canberra\)/)
  const enviados = []
  const f = async (_u, init) => { enviados.push(JSON.parse(init.body).input); return respuestaOk(crearWav(Buffer.alloc(24000 * 2), 24000)) }
  await principal([guion, '--salida', path.join(dir, 'out'), '--pronunciaciones', pron, '--pausa-parrafo', 'corta'], env, f, () => {})
  assert.equal(enviados.length, 1)
  assert.equal(enviados[0].markup, 'Llamó a Canberra. [pause long] Respondió. [pause short] Segundo párrafo.')
  assert.equal(enviados[0].customPronunciations.pronunciations.length, 1)
  assert.match(fs.readFileSync(path.join(dir, 'out', 'ajustes.txt'), 'utf-8'), /pausa-parrafo=corta/)
  fs.writeFileSync(guion, '## Guion\n\nHola {pausa rara} mundo.\n')
  await assert.rejects(principal([guion, '--solo-texto'], env, f, () => {}), /Marca desconocida/)
  fs.rmSync(dir, { recursive: true, force: true })
})
