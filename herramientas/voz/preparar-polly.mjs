#!/usr/bin/env node
/**
 * Prepara el guion para pegarlo en la consola de Amazon Polly (Long-Form, Raul): sin claves ni llamadas a la red.
 *
 *   node preparar-polly.mjs "..\..\02-canales\<canal>\videos\NN-nombre\01-guion\guion.md" --salida "..\..\02-canales\<canal>\videos\NN-nombre\04-voz\polly"
 *
 * Crea en la carpeta de salida:
 *   parte-01.txt, parte-02.txt …       texto limpio para pegar (sin marcas de pausa), con las sustituciones aplicadas
 *   parte-01-ssml.txt, …               lo mismo en SSML, con {pausa} convertidas a <break/> (probar primero con una parte)
 *   resumen.txt                        caracteres de cada parte y total (para el cupo gratis de Polly)
 * Reutiliza la lectura del guion y `sustituciones.json` del sintetizador de Google, y añade `--sustituciones-extra` (JSON propio del video).
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { extraerNarracion, aplicarSustituciones } from './sintetizar.mjs'

const aqui = path.dirname(fileURLToPath(import.meta.url))
const LIMITE = 2800 // caracteres por parte (Polly admite ~3000 facturables por petición; margen de seguridad)
const BREAK_MS = { pausa: 600, 'pausa corta': 350, 'pausa larga': 1000 }

function leerJson(ruta) {
  if (!ruta || !fs.existsSync(ruta)) return []
  const j = JSON.parse(fs.readFileSync(ruta, 'utf-8'))
  return Object.entries(j).filter(([k]) => !k.startsWith('_'))
}


const UNI = ['cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciséis', 'diecisiete', 'dieciocho', 'diecinueve', 'veinte', 'veintiuno', 'veintidós', 'veintitrés', 'veinticuatro', 'veinticinco', 'veintiséis', 'veintisiete', 'veintiocho', 'veintinueve']
const DEC = ['', '', '', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa']
const CEN = ['', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos', 'seiscientos', 'setecientos', 'ochocientos', 'novecientos']

/** Entero 0–999 999 en letras (español). */
export function enteroALetras(n) {
  if (n < 30) return UNI[n]
  if (n < 100) return DEC[Math.floor(n / 10)] + (n % 10 ? ' y ' + UNI[n % 10] : '')
  if (n === 100) return 'cien'
  if (n < 1000) return CEN[Math.floor(n / 100)] + (n % 100 ? ' ' + enteroALetras(n % 100) : '')
  const miles = Math.floor(n / 1000)
  const resto = n % 1000
  return (miles === 1 ? 'mil' : enteroALetras(miles) + ' mil') + (resto ? ' ' + enteroALetras(resto) : '')
}

/** «59» → «cincuenta y nueve»; «1,22» → «uno coma veintidós»; «1,04» → «uno coma cero cuatro». */
export function numeroALetras(s) {
  const [ent, dec] = s.split(',')
  let r = enteroALetras(parseInt(ent, 10))
  if (dec !== undefined) r += ' coma ' + (dec.startsWith('0') ? dec.split('').map((d) => UNI[+d]).join(' ') : enteroALetras(parseInt(dec, 10)))
  return r
}

/** Cifras y signos que Polly leería mal: «13 797» → «13797», «0,17 %» → «0,17 por ciento», rangos con raya. */
export function normalizarCifras(t) {
  let s = t
  s = s.replace(/(\d)\s(\d{3})(?!\d)/g, '$1$2')              // separador de miles con espacio
  s = s.replace(/(\d)\s(\d{3})(?!\d)/g, '$1$2')              // (segunda pasada para 1 234 567)
  s = s.replace(/(\d)\s?%/g, '$1 por ciento')
  s = s.replace(/(\d)\s?[–-]\s?(\d)/g, '$1 a $2')            // 12700–12900 → 12700 a 12900
  // «± N»: Polly lee mal las cifras tras el signo (decía «cinco nueve» por 59): se escriben con letras
  s = s.replace(/\s?±\s?(\d+(?:,\d+)?)/g, (_, n) => ' más o menos ' + numeroALetras(n))
  s = s.replace(/\s?÷\s?/g, ' dividido entre ')
  // Todas las cifras (hasta 999 999) con letras: «13797» → «trece mil setecientos noventa y siete», «73,04» → «setenta y tres coma cero cuatro»
  s = s.replace(/\d+(?:,\d+)?/g, (m) => (parseInt(m.split(',')[0], 10) <= 999999 ? numeroALetras(m) : m))
  return s.replace(/[ \t]{2,}/g, ' ')
}

function principal(argv) {
  const a = { archivo: '', salida: '', extra: '' }
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--salida') a.salida = argv[++i]
    else if (argv[i] === '--sustituciones-extra') a.extra = argv[++i]
    else if (!a.archivo) a.archivo = argv[i]
  }
  if (!a.archivo || !a.salida) {
    console.log('Uso: node preparar-polly.mjs <guion.md> --salida <carpeta> [--sustituciones-extra <json>]')
    return 1
  }
  const md = fs.readFileSync(a.archivo, 'utf-8')
  const subs = [...leerJson(path.join(aqui, 'sustituciones.json')), ...leerJson(a.extra)]
  // 1) sustituciones; 2) cifras; las marcas {pausa…} se conservan hasta el final para el SSML
  const parrafos = aplicarSustituciones(extraerNarracion(md), subs).map(normalizarCifras)

  // Partes: se juntan párrafos hasta el límite de caracteres (sin pausas, que no cuentan como texto hablado)
  const largo = (p) => p.replace(/\{[^}]*\}/g, '').length
  const partes = []
  let actual = []
  let n = 0
  for (const p of parrafos) {
    if (actual.length && n + largo(p) > LIMITE) { partes.push(actual); actual = []; n = 0 }
    actual.push(p); n += largo(p)
  }
  if (actual.length) partes.push(actual)

  fs.mkdirSync(a.salida, { recursive: true })
  const escapar = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const lineas = []
  let total = 0
  partes.forEach((ps, i) => {
    const id = String(i + 1).padStart(2, '0')
    const plano = ps.map((p) => p.replace(/\{[^}]*\}/g, '').replace(/\s{2,}/g, ' ').replace(/\s+([.,;:!?»])/g, '$1').trim()).filter(Boolean).join('\n\n')
    const ssml = '<speak>\n' + ps.map((p) => escapar(p).replace(/\{([^{}]*)\}/g, (_, nombre) => {
      const ms = BREAK_MS[nombre.trim().toLowerCase().replace(/\s+/g, ' ')]
      if (!ms) throw new Error(`Marca desconocida en el guion: {${nombre}}`)
      return `<break time="${ms}ms"/>`
    }).replace(/\s{2,}/g, ' ').trim()).join('\n') + '\n</speak>\n'
    fs.writeFileSync(path.join(a.salida, `parte-${id}.txt`), plano + '\n', 'utf-8')
    fs.writeFileSync(path.join(a.salida, `parte-${id}-ssml.txt`), ssml, 'utf-8')
    lineas.push(`parte-${id}: ${plano.length} caracteres`)
    total += plano.length
  })
  lineas.push(`TOTAL: ${total} caracteres en ${partes.length} partes (cupo gratis Polly Long-Form: 500 000 al mes durante los primeros 12 meses)`)
  fs.writeFileSync(path.join(a.salida, 'resumen.txt'), lineas.join('\n') + '\n', 'utf-8')
  console.log(lineas.join('\n'))
  return 0
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exit(principal(process.argv.slice(2)))
