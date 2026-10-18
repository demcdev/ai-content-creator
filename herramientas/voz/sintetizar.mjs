#!/usr/bin/env node
/**
 * Convierte el guion de un video (Markdown) en audio con Google Cloud Text-to-Speech (voces Chirp 3: HD).
 *
 *   node sintetizar.mjs "<ruta>/guion.md" --solo-texto      (no usa red ni clave)
 *   node sintetizar.mjs "<ruta>/guion.md" --voz es-US-Chirp3-HD-Kore
 *   node sintetizar.mjs "<guion>" --solo 7                                              (repite solo la parte 7)
 *   node sintetizar.mjs --voces                                                         (lista las voces de español)
 *   node sintetizar.mjs "<guion>" --pausa-parrafo corta --pronunciaciones mis-palabras.json
 *
 * En el guion, {pausa}, {pausa corta} y {pausa larga} insertan pausas (solo voces HD). Las pronunciaciones propias
 * (IPA o X-SAMPA) se definen en pronunciaciones.json.
 *
 * La clave de API va en la variable de entorno GOOGLE_TTS_API_KEY. Nunca se escribe en archivos ni en pantalla.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

export const LIMITE_BYTES = 4000 // margen bajo el límite de la API por petición
export const GRATIS_MENSUAL = 1_000_000 // caracteres gratis al mes con voces Chirp 3: HD
export const AVISO_MENSUAL = 800_000
const URL_SINTESIS = 'https://texttospeech.googleapis.com/v1/text:synthesize'
const URL_VOCES = 'https://texttospeech.googleapis.com/v1/voices'
const aqui = path.dirname(fileURLToPath(import.meta.url))

const bytes = (s) => Buffer.byteLength(s, 'utf8')

/* ---------------- 1. Extraer la narración del guion ---------------- */

function quitarCorchetes(s) {
  let prev
  do { prev = s; s = s.replace(/\[[^[\]]*\]/g, '') } while (s !== prev)
  return s
}

/**
 * Devuelve los párrafos que se leen en voz alta. Solo se toma la sección «## Guion» hasta el siguiente «## ».
 * Se quitan: encabezados, citas, lo que va entre [corchetes] (indicaciones de pantalla y marcas [✔ n] / [REVISAR]),
 * el énfasis de Markdown y las viñetas.
 */
export function extraerNarracion(md) {
  const inicio = md.search(/^## Guion\s*$/m)
  let t = inicio >= 0 ? md.slice(inicio).replace(/^## Guion\s*$/m, '') : md
  const fin = t.search(/^## /m)
  if (fin >= 0) t = t.slice(0, fin)
  const parrafos = []
  for (const linea of t.split(/\r?\n/)) {
    const l = linea.trim()
    if (!l || l.startsWith('#') || l.startsWith('>') || /^-{3,}$/.test(l)) continue
    let s = quitarCorchetes(l).replace(/^[-*]\s+/, '').replace(/\*\*/g, '').replace(/\*/g, '')
    s = s.replace(/\s+([.,;:!?»])/g, '$1').replace(/\s{2,}/g, ' ').trim()
    if (s && /[\p{L}\p{N}]/u.test(s)) parrafos.push(s)
  }
  return parrafos
}

export function aplicarSustituciones(parrafos, sustituciones = []) {
  return parrafos.map((p) => sustituciones.reduce((acc, [de, a]) => acc.split(de).join(a), p))
}

/* ---------------- 1b. Pausas y pronunciaciones propias (solo voces HD) ---------------- */

// En el guion se escriben con llaves porque los [corchetes] se descartan como indicaciones de pantalla.
export const ETIQUETAS_PAUSA = { pausa: '[pause]', 'pausa corta': '[pause short]', 'pausa larga': '[pause long]' }
export const PAUSAS_PARRAFO = { ninguna: '', corta: '[pause short]', normal: '[pause]', larga: '[pause long]' }

/** Convierte {pausa}, {pausa corta} y {pausa larga} en las etiquetas de Google. Cualquier otra {marca} es un error. */
export function convertirPausas(texto) {
  let usaPausas = false
  const salida = texto.replace(/\{([^{}]*)\}/g, (_, nombre) => {
    const etiqueta = ETIQUETAS_PAUSA[nombre.trim().toLowerCase().replace(/\s+/g, ' ')]
    if (!etiqueta) throw new Error(`Marca desconocida en el guion: {${nombre}}. Usa {pausa}, {pausa corta} o {pausa larga}.`)
    usaPausas = true
    return etiqueta
  })
  return { texto: salida.replace(/[ \t]{2,}/g, ' '), usaPausas }
}

/** Lee el archivo de pronunciaciones: { "frase": { "ipa": "…" } } o { "frase": { "xsampa": "…" } }. Las claves con «_» se ignoran. */
export function leerPronunciaciones(ruta) {
  if (!ruta || !fs.existsSync(ruta)) return []
  const j = JSON.parse(fs.readFileSync(ruta, 'utf-8'))
  const lista = []
  for (const [frase, v] of Object.entries(j)) {
    if (frase.startsWith('_')) continue
    if (!v || typeof v !== 'object' || (!v.ipa && !v.xsampa) || (v.ipa && v.xsampa)) throw new Error(`Pronunciación inválida para «${frase}»: usa { "ipa": "…" } o { "xsampa": "…" } (solo una).`)
    lista.push({ frase, codificacion: v.ipa ? 'PHONETIC_ENCODING_IPA' : 'PHONETIC_ENCODING_X_SAMPA', pronunciacion: v.ipa || v.xsampa })
  }
  return lista
}

/**
 * Deja un trozo listo para enviar: convierte las pausas, añade la pausa entre párrafos si se pidió y se queda con las
 * pronunciaciones cuya frase aparece tal cual (la API exige coincidencia exacta). Las pausas solo funcionan en `markup`.
 */
export function prepararTrozo(trozo, { pausaParrafo = 'ninguna', pronunciaciones = [] } = {}) {
  const conv = convertirPausas(trozo)
  const etiqueta = PAUSAS_PARRAFO[pausaParrafo]
  if (etiqueta === undefined) throw new Error('--pausa-parrafo debe ser ninguna, corta, normal o larga')
  const texto = etiqueta ? conv.texto.replace(/\n\n/g, ` ${etiqueta} `) : conv.texto
  return { texto, markup: conv.usaPausas || texto !== conv.texto, pronunciaciones: pronunciaciones.filter((p) => texto.includes(p.frase)), caracteres: texto.length }
}

/* ---------------- 2. Trocear respetando el límite de la API ---------------- */

function partirLargo(texto, limite) {
  const frases = texto.split(/(?<=[.!?…])\s+/)
  const piezas = []
  let actual = ''
  for (const f of frases) {
    if (bytes(f) > limite) {
      if (actual) { piezas.push(actual); actual = '' }
      let resto = f
      while (bytes(resto) > limite) {
        let corte = resto.lastIndexOf(' ', Math.floor(limite / 2))
        if (corte <= 0) corte = Math.floor(limite / 2)
        piezas.push(resto.slice(0, corte).trim())
        resto = resto.slice(corte).trim()
      }
      actual = resto
    } else if (actual && bytes(actual + ' ' + f) > limite) {
      piezas.push(actual)
      actual = f
    } else actual = actual ? actual + ' ' + f : f
  }
  if (actual) piezas.push(actual)
  return piezas
}

export function trocear(parrafos, limite = LIMITE_BYTES) {
  const trozos = []
  let actual = ''
  const cerrar = () => { if (actual) { trozos.push(actual); actual = '' } }
  for (const p of parrafos) {
    for (const pieza of bytes(p) > limite ? partirLargo(p, limite) : [p]) {
      if (actual && bytes(actual + '\n\n' + pieza) > limite) cerrar()
      actual = actual ? actual + '\n\n' + pieza : pieza
    }
  }
  cerrar()
  return trozos
}

/* ---------------- 3. WAV (para unir las partes sin perder calidad) ---------------- */

export function leerWav(buf) {
  if (buf.length < 44 || buf.toString('ascii', 0, 4) !== 'RIFF' || buf.toString('ascii', 8, 12) !== 'WAVE') throw new Error('El audio recibido no es un WAV válido')
  let pos = 12
  let fmt = null
  while (pos + 8 <= buf.length) {
    const id = buf.toString('ascii', pos, pos + 4)
    const tam = buf.readUInt32LE(pos + 4)
    if (id === 'fmt ') fmt = { canales: buf.readUInt16LE(pos + 10), rate: buf.readUInt32LE(pos + 12), bits: buf.readUInt16LE(pos + 22) }
    if (id === 'data') {
      if (!fmt) throw new Error('WAV sin bloque fmt')
      const fin = Math.min(buf.length, pos + 8 + tam)
      return { ...fmt, pcm: buf.subarray(pos + 8, fin) }
    }
    pos += 8 + tam + (tam % 2)
  }
  throw new Error('WAV sin bloque data')
}

export function crearWav(pcm, rate, canales = 1, bits = 16) {
  const enc = Buffer.alloc(44)
  enc.write('RIFF', 0, 'ascii')
  enc.writeUInt32LE(36 + pcm.length, 4)
  enc.write('WAVE', 8, 'ascii')
  enc.write('fmt ', 12, 'ascii')
  enc.writeUInt32LE(16, 16)
  enc.writeUInt16LE(1, 20)
  enc.writeUInt16LE(canales, 22)
  enc.writeUInt32LE(rate, 24)
  enc.writeUInt32LE((rate * canales * bits) / 8, 28)
  enc.writeUInt16LE((canales * bits) / 8, 32)
  enc.writeUInt16LE(bits, 34)
  enc.write('data', 36, 'ascii')
  enc.writeUInt32LE(pcm.length, 40)
  return Buffer.concat([enc, pcm])
}

export function unirWav(partes, pausaSeg = 0.6) {
  const lecturas = partes.map(leerWav)
  const { rate, canales, bits } = lecturas[0]
  for (const l of lecturas) if (l.rate !== rate || l.canales !== canales || l.bits !== bits) throw new Error('Las partes tienen distinto formato de audio')
  const pausa = Buffer.alloc(Math.round(pausaSeg * rate) * canales * (bits / 8))
  const trozos = []
  lecturas.forEach((l, i) => { if (i) trozos.push(pausa); trozos.push(l.pcm) })
  return crearWav(Buffer.concat(trozos), rate, canales, bits)
}

export function duracionWav(buf) {
  const l = leerWav(buf)
  return l.pcm.length / (l.rate * l.canales * (l.bits / 8))
}

/* ---------------- 4. Llamada a la API ---------------- */

export class ErrorTTS extends Error {}

export async function sintetizar({ texto, voz, ritmo = 1, clave, formato = 'LINEAR16', markup = false, pronunciaciones = [] }, fetchFn = fetch, esperas = [1000, 3000, 8000]) {
  if (!clave) throw new ErrorTTS('Falta la clave: define la variable de entorno GOOGLE_TTS_API_KEY.')
  const idioma = voz.split('-').slice(0, 2).join('-')
  const input = markup ? { markup: texto } : { text: texto }
  if (pronunciaciones.length) {
    input.customPronunciations = { pronunciations: pronunciaciones.map((p) => ({ phrase: p.frase, phoneticEncoding: p.codificacion, pronunciation: p.pronunciacion })) }
  }
  const cuerpo = { input, voice: { languageCode: idioma, name: voz }, audioConfig: { audioEncoding: formato, speakingRate: ritmo } }
  let ultimo = ''
  for (let intento = 0; intento <= esperas.length; intento++) {
    const r = await fetchFn(URL_SINTESIS, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Goog-Api-Key': clave }, body: JSON.stringify(cuerpo) })
    if (r.ok) {
      const j = await r.json()
      if (!j.audioContent) throw new ErrorTTS('La respuesta no trajo audio.')
      return Buffer.from(j.audioContent, 'base64')
    }
    let msg = ''
    try { const j = await r.json(); msg = (j.error && j.error.message) || '' } catch { /* cuerpo vacío */ }
    ultimo = `HTTP ${r.status}${msg ? ': ' + msg : ''}`
    if (![429, 500, 502, 503, 504].includes(r.status) || intento === esperas.length) break
    await new Promise((res) => setTimeout(res, esperas[intento]))
  }
  throw new ErrorTTS(ultimo + pistaDeError(ultimo))
}

export function pistaDeError(m) {
  if (/API key not valid|API_KEY_INVALID/i.test(m)) return ' → La clave no es válida o no está permitida para Cloud Text-to-Speech API.'
  if (/has not been used|disabled|SERVICE_DISABLED/i.test(m)) return ' → Habilita «Cloud Text-to-Speech API» en tu proyecto de Google Cloud.'
  if (/billing/i.test(m)) return ' → Activa la facturación del proyecto (no se cobra mientras no pases del límite gratuito).'
  if (/pronunciation/i.test(m)) return ' → Puede que este idioma no admita pronunciaciones propias, o que una frase/pronunciación no sea válida: vacía pronunciaciones.json y repite.'
  if (/markup|pause/i.test(m)) return ' → Las pausas solo funcionan con voces Chirp 3: HD. Quita las marcas {pausa…} o cambia de voz.'
  if (/does not exist|voice/i.test(m)) return ' → Revisa el nombre de la voz con: node sintetizar.mjs --voces'
  return ''
}

export async function listarVoces(clave, fetchFn = fetch, idioma = 'es') {
  if (!clave) throw new ErrorTTS('Falta la clave: define la variable de entorno GOOGLE_TTS_API_KEY.')
  const r = await fetchFn(`${URL_VOCES}?languageCode=${idioma}`, { headers: { 'X-Goog-Api-Key': clave } })
  if (!r.ok) throw new ErrorTTS('HTTP ' + r.status)
  const j = await r.json()
  return (j.voices || []).map((v) => v.name).filter((n) => /Chirp3-HD/i.test(n)).sort()
}

/* ---------------- 5. Control de consumo mensual (para no pasar del límite gratuito) ---------------- */

export function mesActual(f = new Date()) {
  return f.toISOString().slice(0, 7)
}

export function leerUso(ruta) {
  try { return JSON.parse(fs.readFileSync(ruta, 'utf-8')) } catch { return {} }
}

export function sumarUso(ruta, caracteres, mes = mesActual()) {
  const u = leerUso(ruta)
  u[mes] = (u[mes] || 0) + caracteres
  fs.writeFileSync(ruta, JSON.stringify(u, null, 2))
  return u[mes]
}

/* ---------------- 6. Línea de comandos ---------------- */

export function leerArgumentos(argv) {
  const o = { archivo: '', voz: 'es-US-Chirp3-HD-Iapetus', ritmo: 1.0, formato: 'wav', pausa: 0.6, salida: '', soloTexto: false, solo: 0, voces: false, permitirPago: false, sustituciones: '', pronunciaciones: '', pausaParrafo: 'ninguna' }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    const sig = () => argv[++i]
    if (a === '--voz') o.voz = sig()
    else if (a === '--pausa-parrafo') o.pausaParrafo = sig()
    else if (a === '--pronunciaciones') o.pronunciaciones = sig()
    else if (a === '--ritmo') o.ritmo = Number(sig())
    else if (a === '--formato') o.formato = sig()
    else if (a === '--pausa') o.pausa = Number(sig())
    else if (a === '--salida') o.salida = sig()
    else if (a === '--solo') o.solo = Number(sig())
    else if (a === '--sustituciones') o.sustituciones = sig()
    else if (a === '--solo-texto') o.soloTexto = true
    else if (a === '--voces') o.voces = true
    else if (a === '--permitir-pago') o.permitirPago = true
    else if (!a.startsWith('--') && !o.archivo) o.archivo = a
    else throw new Error('Opción desconocida: ' + a)
  }
  if (!(o.ritmo >= 0.25 && o.ritmo <= 2)) throw new Error('--ritmo debe estar entre 0,25 y 2')
  if (!['wav', 'mp3'].includes(o.formato)) throw new Error('--formato debe ser wav o mp3')
  if (!(o.pausaParrafo in PAUSAS_PARRAFO)) throw new Error('--pausa-parrafo debe ser ninguna, corta, normal o larga')
  return o
}

function cargarSustituciones(ruta) {
  const r = ruta || path.join(aqui, 'sustituciones.json')
  if (!fs.existsSync(r)) return []
  const j = JSON.parse(fs.readFileSync(r, 'utf-8'))
  return Object.entries(j).filter(([k]) => !k.startsWith('_'))
}

export async function principal(argv, entorno = process.env, fetchFn = fetch, salidaTxt = console.log) {
  const o = leerArgumentos(argv)
  const clave = entorno.GOOGLE_TTS_API_KEY || ''
  if (o.voces) {
    for (const v of await listarVoces(clave, fetchFn)) salidaTxt(v)
    return 0
  }
  if (!o.archivo) throw new Error('Indica el archivo del guion. Ejemplo: node sintetizar.mjs "<ruta>/guion.md" --solo-texto')
  const md = fs.readFileSync(o.archivo, 'utf-8')
  const parrafos = aplicarSustituciones(extraerNarracion(md), cargarSustituciones(o.sustituciones))
  const trozos = trocear(parrafos)
  const pronunciaciones = leerPronunciaciones(o.pronunciaciones || path.join(aqui, 'pronunciaciones.json'))
  const preparados = trozos.map((t) => prepararTrozo(t, { pausaParrafo: o.pausaParrafo, pronunciaciones }))
  const caracteres = preparados.reduce((a, t) => a + t.caracteres, 0)
  const palabras = parrafos.join(' ').replace(/\{[^{}]*\}/g, ' ').split(/\s+/).filter(Boolean).length
  const nPausas = (parrafos.join(' ').match(/\{[^{}]*\}/g) || []).length
  const rutaUso = entorno.VOZ_USO_ARCHIVO || path.join(aqui, '.uso-mensual.json')
  const usado = leerUso(rutaUso)[mesActual()] || 0

  salidaTxt(`Párrafos: ${parrafos.length} · Palabras: ${palabras} · Caracteres: ${caracteres} · Partes: ${trozos.length}`)
  salidaTxt(`Duración estimada: ~${(palabras / 150).toFixed(1)} min (150 palabras/min; las pausas añaden algo más)`)
  const enUso = pronunciaciones.filter((p) => preparados.some((t) => t.pronunciaciones.includes(p)))
  salidaTxt(`Pausas marcadas en el guion: ${nPausas}` + (o.pausaParrafo !== 'ninguna' ? ` · Pausa entre párrafos: ${o.pausaParrafo}` : ''))
  salidaTxt(`Pronunciaciones propias: ${pronunciaciones.length} en el archivo, ${enUso.length} presentes en este texto` + (enUso.length ? ` (${enUso.map((p) => p.frase).join(', ')})` : ''))
  salidaTxt(`Uso este mes (según este script): ${usado} de ${GRATIS_MENSUAL} caracteres gratuitos; esta locución gastaría ${caracteres}.`)
  if (o.soloTexto) {
    parrafos.forEach((p, i) => salidaTxt(`\n[${i + 1}] ${p}`))
    return 0
  }

  const base = path.basename(o.archivo).replace(/\.md$/i, '').replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '')
  const dir = o.salida ? path.resolve(o.salida) : path.join(aqui, 'salida', base)
  const dirPartes = path.join(dir, 'partes')
  fs.mkdirSync(dirPartes, { recursive: true })
  const ext = o.formato === 'mp3' ? 'mp3' : 'wav'
  const formatoApi = o.formato === 'mp3' ? 'MP3' : 'LINEAR16'
  const aGenerar = o.solo ? [o.solo] : trozos.map((_, i) => i + 1)
  if (o.solo && (o.solo < 1 || o.solo > trozos.length)) throw new Error(`--solo debe estar entre 1 y ${trozos.length}`)

  const nuevos = aGenerar.reduce((a, n) => a + preparados[n - 1].caracteres, 0)
  if (usado + nuevos > GRATIS_MENSUAL && !o.permitirPago) {
    throw new Error(`Pasarías del millón de caracteres gratuitos de este mes (${usado} + ${nuevos}). Se cobrarían unos 30 USD por millón. Usa --permitir-pago si estás de acuerdo.`)
  }
  if (usado + nuevos > AVISO_MENSUAL) salidaTxt(`⚠️ Con esto llevarías ${usado + nuevos} de ${GRATIS_MENSUAL} caracteres gratuitos este mes.`)

  for (const n of aGenerar) {
    const archivoParte = path.join(dirPartes, String(n).padStart(2, '0') + '.' + ext)
    const p = preparados[n - 1]
    const audio = await sintetizar({ texto: p.texto, voz: o.voz, ritmo: o.ritmo, clave, formato: formatoApi, markup: p.markup, pronunciaciones: p.pronunciaciones }, fetchFn)
    fs.writeFileSync(archivoParte, audio)
    sumarUso(rutaUso, p.caracteres)
    salidaTxt(`Parte ${n}/${trozos.length} lista (${p.caracteres} caracteres)`)
  }

  const partes = trozos.map((_, i) => path.join(dirPartes, String(i + 1).padStart(2, '0') + '.' + ext))
  const faltan = partes.filter((p) => !fs.existsSync(p))
  if (faltan.length) { salidaTxt(`Faltan ${faltan.length} partes: genera todas antes de unirlas.`); return 0 }
  const buffers = partes.map((p) => fs.readFileSync(p))
  const final = ext === 'wav' ? unirWav(buffers, o.pausa) : Buffer.concat(buffers)
  const destino = path.join(dir, base + '.' + ext)
  fs.writeFileSync(destino, final)
  fs.writeFileSync(path.join(dir, 'ajustes.txt'), `voz=${o.voz}\nritmo=${o.ritmo}\nformato=${o.formato}\npausa=${o.pausa}\npausa-parrafo=${o.pausaParrafo}\npronunciaciones=${pronunciaciones.length}\nfecha=${new Date().toISOString()}\n`)
  salidaTxt(`\nAudio final: ${destino}` + (ext === 'wav' ? ` (${duracionWav(final).toFixed(0)} s)` : ''))
  salidaTxt('Recuerda: guarda captura de los términos/licencia y declara el contenido sintético en Studio (regla 4).')
  return 0
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  principal(process.argv.slice(2)).then((c) => process.exit(c), (e) => { console.error('Error: ' + e.message); process.exit(1) })
}
