#!/usr/bin/env python3
"""
Parte mecánica del verificador de cifras (no usa IA, no gasta tokens). Se corre ANTES del agente «verificador»,
que después revisa solo lo que este script deja pendiente.

  python herramientas/video/verificar-cifras.py "hace-eones/2"                         # coherencia y cálculos
  python herramientas/video/verificar-cifras.py "hace-eones/2" --web                   # además abre las fuentes (con caché)
  python herramientas/video/verificar-cifras.py "hace-eones/2" --pendientes            # imprime solo lo que no es OK
  python herramientas/video/verificar-cifras.py "hace-eones/2" --cambios verificador   # solo líneas cambiadas desde el sello

Qué hace con cada marca [✔ n] de la sección «## Guion» (y con cada [cálculo propio: …]):
  1. Coherencia: saca de la frase los números (en cifras o en palabras) con su unidad, «millones / mil millones», rangos,
     fechas y años, y los compara con la fila n de 01-guion/verificacion-de-cifras.md (columna «Valor» y la del dato; los
     años, también en «Fuente»). Acepta redondeos razonables: «unos 70» por 69,63; «2,7» por 2,726; «13 800 millones» por 13,8.
  2. Cálculos: rehace las cuentas de la tabla («Cálculos propios» y celdas con operaciones) y de las marcas
     [cálculo propio: …] y las compara con su resultado. Formato simple para una cuenta nueva, en cualquier celda:
         = 13800 * 0,05 → 690
     (operadores × x * ÷ / + − ^ √( ), exponentes ² ⁶, unidades conocidas: km, km/s, h, días, MB, bit/s…).
     Sin «→ resultado», el valor se compara con los números de la frase del guion que cita esa fila.
  3. Con --web: comprueba que cada enlace de la fila responde y busca en el texto de la página los números usados.
     Caché en <video>/.estado/cache-web/ (30 días; 24 h si la cifra es volátil). Los PDF solo se comprueban como enlace.
  4. Salida: una tabla por cifra con OK / DUDOSA / DISCREPANCIA / NO VERIFICABLE y <video>/.estado/cifras-pendientes.json
     con solo las que no son OK: es lo único que necesita leer el agente.

Volátil = la fila lleva ⏰, habla de estado, distancia, velocidad, «hoy»…, una nota de la hoja dice «filas N y M» junto a
«el día de grabar/publicar», o la marca del guion dice «comprobar». Una cifra volátil queda DUDOSA hasta que --web la
encuentre en su fuente.

Códigos de salida: 0 = todo OK · 1 = hay alguna DISCREPANCIA · 2 = hay dudosas o no verificables (sin discrepancias).
"""
import argparse
import sys
sys.dont_write_bytecode = True  # no dejar __pycache__ en la carpeta
import datetime
import difflib
import hashlib
import html
import json
import math
import os
import re
import unicodedata
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nucleo'))
from _comun import RAIZ, F_CIFRAS, F_GUION, SEPARADOR, consola, leer, resolver_video, ruta

OK, NOVER, DUDOSA, DISC = 'OK', 'NO VERIFICABLE', 'DUDOSA', 'DISCREPANCIA'
GRAVEDAD = {OK: 0, NOVER: 1, DUDOSA: 2, DISC: 3}
CALIDAD_OK = ('exacto', 'redondeo', 'cota', 'aprox')
CADUCIDAD_DIAS = 30
BLOQUEO = (401, 403, 405, 429)  # el sitio no deja leer a un script: no es un enlace roto
CADUCIDAD_VOLATIL_HORAS = 24

# ------------------------------------------------------------------ vocabulario
MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
         'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
MESES_CORTOS = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sept': 9, 'sep': 9,
                'set': 9, 'oct': 10, 'nov': 11, 'dic': 12}
_ML = '|'.join(MESES)
_MC = '|'.join(MESES_CORTOS)
FECHAS = [  # (patrón, grupos día/mes/año) — se prueban en este orden en cada posición
    (re.compile(r'(\d{1,2})-(%s)\.?-(\d{4})(?!\d)' % _MC, re.I), 'corta'),                     # 5-sep-1977
    (re.compile(r'(\d{1,2})\s+de\s+(%s)(?:\s+(?:de|del)\s+(\d{4}|este\s+año|ese\s+(?:mismo\s+)?año))?(?![\w])' % _ML, re.I), 'larga'),
    (re.compile(r'(%s)\s+(?:de|del)\s+(\d{4})(?!\d)' % _ML, re.I), 'mes-año'),                 # marzo de 2024
    (re.compile(r'(%s)\.?-(\d{4})(?!\d)' % _MC, re.I), 'mes-año-corta'),                       # nov-2035
    (re.compile(r'(%s)(?![\w])' % _ML, re.I), 'mes'),                                          # en agosto
]

PALABRAS_NUM = {
    'un': 1, 'una': 1, 'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9,
    'diez': 10, 'once': 11, 'doce': 12, 'trece': 13, 'catorce': 14, 'quince': 15, 'dieciséis': 16, 'dieciseis': 16,
    'diecisiete': 17, 'dieciocho': 18, 'diecinueve': 19, 'veinte': 20, 'veintiuno': 21, 'veintiún': 21, 'veintidós': 22,
    'veintidos': 22, 'veintitrés': 23, 'veintitres': 23, 'veinticuatro': 24, 'veinticinco': 25, 'veintiséis': 26,
    'veintiseis': 26, 'veintisiete': 27, 'veintiocho': 28, 'veintinueve': 29, 'treinta': 30, 'cuarenta': 40,
    'cincuenta': 50, 'sesenta': 60, 'setenta': 70, 'ochenta': 80, 'noventa': 90, 'cien': 100, 'ciento': 100,
    'doscientos': 200, 'doscientas': 200, 'trescientos': 300, 'trescientas': 300, 'cuatrocientos': 400,
    'cuatrocientas': 400, 'quinientos': 500, 'quinientas': 500, 'seiscientos': 600, 'seiscientas': 600,
    'setecientos': 700, 'setecientas': 700, 'ochocientos': 800, 'ochocientas': 800, 'novecientos': 900,
    'novecientas': 900, 'mil': 1000, 'millón': 10 ** 6, 'millon': 10 ** 6, 'millones': 10 ** 6}
DECENAS = {'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa'}
UNIDADES_SIMPLES = {'un', 'uno', 'una', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve'}

MULT = {'mil millones': 1e9, 'miles de millones': 1e9, 'millardo': 1e9, 'millardos': 1e9, 'millones': 1e6, 'millón': 1e6,
        'millon': 1e6, 'billones': 1e12, 'billón': 1e12, 'billon': 1e12, 'mil': 1e3,
        'thousand': 1e3, 'million': 1e6, 'billion': 1e9, 'trillion': 1e12}
R_MULT = re.compile(r'\s*(mil\s+millones|miles\s+de\s+millones|millardos?|millones|mill[oó]n|billones|bill[oó]n|mil)(?![\w])', re.I)
R_MULT_EN = re.compile(r'\s*(thousand|million|billion|trillion)s?(?![\w])', re.I)
R_PAREN_CORTO = re.compile(r'\s*\([^()]{0,15}\)')
R_MEDIO = re.compile(r'\s+y\s+medi[oa](?![\w])', re.I)
SUP = {'⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4', '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9'}
R_SUP = re.compile('[⁰¹²³⁴⁵⁶⁷⁸⁹]+')

# (patrón, unidad, familia, factor a la unidad base de la familia). El orden importa: lo más largo primero.
UNIDADES = [(re.compile(p), u, f, k) for p, u, f, k in [
    (r'km\s*/\s*s\s*/\s*Mpc|(?i:kil[oó]metros?\s+por\s+segundo\s+(?:y\s+)?por\s+megap[aá]rsecs?)', 'km/s/Mpc', 'H0', 1.0),
    (r'km\s*/\s*s(?![\w/])|(?i:kil[oó]metros?\s+por\s+segundo)', 'km/s', 'velocidad', 1e3),
    (r'(?i:bits?\s*/\s*s(?!\w)|bits?\s+por\s+segundo|bps(?!\w))', 'bit/s', 'tasa', 1.0),
    (r'(?i:mph(?!\w)|millas\s+por\s+hora)', 'mph', 'velocidad', 0.44704),
    (r'(?i:d[ií]as?[\s-]+luz)', 'día luz', 'longitud', 2.59020683712e13),
    (r'(?i:años?[\s-]+luz)', 'año luz', 'longitud', 9.4607304725808e15),
    (r'UA(?!\w)|(?i:unidades\s+astron[oó]micas)', 'UA', 'longitud', 1.495978707e11),
    (r'Mpc(?!\w)|(?i:megap[aá]rsecs?)', 'Mpc', 'longitud', 3.0856775814913673e22),
    (r'km(?!\w)|(?i:kil[oó]metros?(?!\w))', 'km', 'longitud', 1e3),
    (r'cm(?!\w)|(?i:cent[ií]metros?(?!\w))', 'cm', 'longitud', 1e-2),
    (r'mm(?!\w)|(?i:mil[ií]metros?(?!\w))', 'mm', 'longitud', 1e-3),
    (r'(?i:millas?(?!\w))', 'millas', 'longitud', 1609.344),
    (r'm(?![\w/.])|(?i:metros?(?!\w))', 'm', 'longitud', 1.0),
    (r'GB(?!\w)|(?i:gigas?(?!\w)|gigabytes?(?!\w))', 'GB', 'datos', 1e9),
    (r'MB(?!\w)|(?i:megas?(?!\w)|megabytes?(?!\w))', 'MB', 'datos', 1e6),
    (r'[kK]B(?!\w)|(?i:kilobytes?(?!\w))', 'KB', 'datos', 1e3),
    (r'(?i:bytes?(?!\w))', 'B', 'datos', 1.0),
    (r'(?i:bits?(?!\w))', 'bit', 'bits', 1.0),
    (r'We(?!\w)|W(?!\w)|(?i:vatios?(?!\w)|watts?(?!\w))', 'W', 'potencia', 1.0),
    (r'K(?!\w)|(?i:kelvin(?!\w))', 'K', 'temp-K', 1.0),
    (r'°\s*C|(?i:grados(?:\s+cent[ií]grados|\s+celsius)?(?!\w))', '°C', 'temp-C', 1.0),
    (r'%|(?i:por\s+ciento(?!\w))', '%', 'porcentaje', 1.0),
    (r'(?i:años?(?!\w))', 'años', 'tiempo', 31557600.0),
    (r'(?i:mes(?:es)?(?!\w))', 'meses', 'tiempo', 2629800.0),
    (r'(?i:semanas?(?!\w))', 'semanas', 'tiempo', 604800.0),
    (r'(?i:d[ií]as?(?!\w))', 'días', 'tiempo', 86400.0),
    (r'h(?!\w)|(?i:horas?(?!\w))', 'h', 'tiempo', 3600.0),
    (r'min(?!\w)|(?i:minutos?(?!\w))', 'min', 'tiempo', 60.0),
    (r's(?![\w/])|(?i:segundos?(?!\w))', 's', 'tiempo', 1.0),
    (r'(?i:veces(?!\w))', 'veces', 'factor', 1.0),
]]
R_DE_UNIDAD = re.compile(r'\s*(?:de\s+)?', re.I)
R_PALABRA_SIG = re.compile(r'\s+([a-záéíóúñü]{4,})(?![\w])')
NO_CONTEO = {'para', 'como', 'pero', 'desde', 'hasta', 'entre', 'sobre', 'antes', 'después', 'despues', 'cada', 'esas', 'esos',
             'estas', 'estos', 'muy', 'más', 'menos', 'tras', 'durante', 'según', 'segun', 'cuando', 'donde', 'porque',
             'aunque', 'también', 'tambien', 'solo', 'sólo', 'veces', 'hace', 'fueron', 'eran', 'están', 'estaban', 'tiene',
             'tienen', 'luego', 'antes', 'menor', 'mayor', 'nuevas', 'nuevos', 'sería', 'será', 'serán'} | set(MESES)

# Palabras con mayúscula que NO forman un nombre propio con el número que sigue («En 1977», «Hoy 3…»).
COMUNES = {'en', 'el', 'la', 'los', 'las', 'lo', 'un', 'una', 'unos', 'unas', 'desde', 'hasta', 'hacia', 'entre', 'con',
           'por', 'para', 'y', 'o', 'a', 'de', 'del', 'al', 'hoy', 'casi', 'más', 'menos', 'solo', 'sólo', 'tras', 'antes',
           'después', 'durante', 'sobre', 'cada', 'ya', 'fue', 'era', 'es', 'son', 'hace', 'sus', 'su', 'pero', 'aun', 'aunque',
           'si', 'cuando', 'sin', 'según', 'eso', 'esto', 'esa', 'ese', 'dentro', 'apenas', 'cerca', 'alrededor',
           'aproximadamente', 'entonces', 'así', 'también', 'año', 'años', 'otro', 'otra', 'otros', 'otras', 'tiene',
           'tienen', 'mide', 'dio', 'dieron', 'obtuvo', 'son', 'unos', 'como', 'mínimo'} | set(MESES)

R_APROX = re.compile(r'(?:\bunos|\bunas|\bcasi|\bcerca\s+de|\bcercan[oa]s?\s+a|\balrededor\s+de|\baproximadamente|\baprox\.?|'
                     r'\bapenas|\bdel\s+orden\s+de|\bpoco\s+m[aá]s\s+de|\balgo\s+m[aá]s\s+de|\ben\s+torno\s+a|'
                     r'\bm[aá]s\s+o\s+menos|≈|~|≃)\s*$', re.I)
R_MENOR = re.compile(r'(?:\bmenos\s+de|\bmenor(?:es)?\s+(?:de|que)|\bno\s+supera(?:n)?(?:\s+(?:los|las|el|la))?|'
                     r'\bninguna?\s+supera(?:\s+(?:los|las|el|la))?|\bpor\s+debajo\s+de|<|≤)\s*$', re.I)
R_MAYOR = re.compile(r'(?:\bm[aá]s\s+de|\bmayor(?:es)?\s+(?:de|que)|\bsupera(?:n|ba)?(?:\s+(?:los|las|el|la))?|'
                     r'\bal\s+menos|\bcomo\s+m[ií]nimo,?|\bpor\s+encima\s+de|>|≥)\s*$', re.I)
R_EXCLUIR = re.compile(r'(?:\bfilas?|\bminutos?|\bfichas?|\bactos?|\bcap[ií]tulos?|\bversi[oó]n|\breglas?)\s*'
                       r'(?:\d+\s*(?:,|y|e)\s*)*$', re.I)
R_NOMBRE = re.compile(r'([A-ZÁÉÍÓÚÑ][^\s\d,.;:()«»"“”\[\]]*)((?:\s+[+−-]?\d+)*)\s*[+−-]?$')
R_VOLATIL_FILA = re.compile(r'⏰|\b(?:estado|distancia|velocidad|quedan?|r[eé]cords?|precios?|cuenta\s+atr[aá]s)\b', re.I)
R_VOLATIL_NOTA = re.compile(r'⏰|d[ií]a\s+de\s+(?:grabar|publicar)|vol[aá]til|cambian?\s+con\s+el\s+tiempo', re.I)
R_URL = re.compile(r'https?://[^\s)\]»>,;|]+')
R_DOMINIO = re.compile(r'(?<![/\w.@])((?:[a-z0-9-]+\.)+(?:gov|org|com|edu|int|net|eu|es)(?:/[^\s)\]»,;|]*)?)', re.I)

R_TOKEN = re.compile(
    r'(?P<num>(?<![\w.,/])(?:\d{1,3}(?:[    ]\d{3})+(?!\d)(?:,\d+)?|[1-9]\d{0,2}(?:\.\d{3})+(?![\d,])|'
    r'\d+(?:,\d+)?(?:\.\d+)?))'
    r'|(?P<pal>[^\W\d_]+)'
    r'|(?P<op>[×÷*/+−^]|(?<=\s)-(?=\s))'
    r'|(?P<sqrt>√)|(?P<lp>\()|(?P<rp>\))|(?P<eq>=)|(?P<apx>[≈~→⇒≃])'
    r'|(?P<otro>\S)')


# ------------------------------------------------------------------ números
class Num:
    """Un número leído de un texto, con su unidad. mag = valor × multiplicador; base = mag × factor de la unidad."""
    def __init__(self, **k):
        self.tipo, self.mag, self.factor, self.fam, self.unidad = 'num', 0.0, 1.0, None, None
        self.dec, self.ceros, self.escala, self.cmp, self.anio, self.fecha = 0, 0, 1.0, None, False, None
        self.palabra, self.texto, self.ini, self.fin, self.col, self.mult_txt = False, '', 0, 0, '', False
        self.rango = None  # el otro extremo de «entre X y Y» o «X–Y»
        self.__dict__.update(k)

    @property
    def base(self):
        return self.mag * self.factor

    def paso(self, en_base=False):
        """Paso de redondeo: el de los decimales escritos (los enteros redondeados entran por «unos», «casi»… al 5 %)."""
        p = 10.0 ** -self.dec if self.dec else 1.0
        return p * self.escala * (self.factor if en_base else 1.0)


def plegar(t):
    return unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()


def raiz_palabra(p):
    p = plegar(p)
    if p.endswith('es') and len(p) > 5:
        p = p[:-2]
    elif p.endswith('s'):
        p = p[:-1]
    return p[:5]


def valor_de(s, ingles=False):
    """'25 902 068 356' -> (25902068356, 0); '69,63' -> (69.63, 2); '1.000' -> (1000, 0). Devuelve (valor, decimales)."""
    s = re.sub(r'[    ]', '', s)
    if ingles:
        s = s.replace(',', '')
    elif re.fullmatch(r'[1-9]\d{0,2}(?:\.\d{3})+', s):
        s = s.replace('.', '')
    else:
        s = s.replace(',', '.')
    dec = len(s.split('.')[1]) if '.' in s else 0
    return float(s), dec


def unidad_en(texto, pos):
    """Unidad que empieza en pos (tras espacios y un «de» opcional). Devuelve (unidad, familia, factor, fin) o None."""
    m = R_DE_UNIDAD.match(texto, pos)
    for inicio in ((m.end(),) if m.end() > pos and texto[pos:m.end()].strip() else ()) + (pos + len(texto[pos:]) - len(texto[pos:].lstrip()),):
        for patron, uni, fam, fac in UNIDADES:
            u = patron.match(texto, inicio)
            if u:
                return uni, fam, fac, u.end()
    return None


def conteo_en(texto, pos):
    """«115 imágenes» -> familia 'conteo:image' (la palabra que sigue, sin plural)."""
    m = R_PALABRA_SIG.match(texto, pos)
    if m and m.group(1).lower() not in NO_CONTEO and m.group(1).lower() not in PALABRAS_NUM:
        return 'conteo:' + raiz_palabra(m.group(1)), m.group(1)
    return None


def _completar(texto, n, fin, ingles=False):
    """Multiplicador, «y medio» y unidad detrás de un número. Devuelve el fin."""
    if not n.palabra:
        mm = (R_MULT_EN if ingles else R_MULT).match(texto, fin)
        if not mm and not ingles:
            par = R_PAREN_CORTO.match(texto, fin)
            mm = R_MULT.match(texto, par.end()) if par else None
        if mm:
            n.escala = MULT[re.sub(r'\s+', ' ', mm.group(1).lower()).rstrip('s') if ingles else re.sub(r'\s+', ' ', mm.group(1).lower())]
            n.mag *= n.escala
            n.mult_txt = True
            fin = mm.end()
    if ingles:
        return fin
    medio = R_MEDIO.match(texto, fin)
    if medio:
        n.mag += 0.5 * n.escala
        n.dec = max(n.dec, 1)
        fin = medio.end()
    u = unidad_en(texto, fin)
    anio = not n.palabra and n.escala == 1 and n.dec == 0 and 1000 <= n.mag <= 2100
    if u:
        n.unidad, n.fam, n.factor, fin = u
        medio = R_MEDIO.match(texto, fin)
        if medio:
            n.mag += 0.5 * n.escala
            n.dec = max(n.dec, 1)
            fin = medio.end()
    elif not anio:
        c = conteo_en(texto, fin)
        if c:
            n.fam, n.unidad = c
    n.anio = (not n.fam and not n.palabra and n.escala == 1 and n.dec == 0 and 1000 <= n.mag <= 2100)
    return fin


def _palabras_numero(texto, pos):
    """Número escrito en palabras desde pos: «trece mil ochocientos millones», «treinta y dos», «cien mil»."""
    palabras, fin, j = [], pos, pos
    while True:
        m = re.compile(r'\s*([^\W\d_]+)').match(texto, j) if palabras else re.compile(r'([^\W\d_]+)').match(texto, j)
        if not m:
            break
        w = m.group(1).lower()
        if w == 'y' and palabras and palabras[-1] in DECENAS:
            m2 = re.compile(r'\s+([^\W\d_]+)').match(texto, m.end())
            if m2 and m2.group(1).lower() in UNIDADES_SIMPLES:
                palabras.append(m2.group(1).lower())
                fin = j = m2.end()
                continue
            break
        if w not in PALABRAS_NUM:
            break
        palabras.append(w)
        fin = j = m.end()
    if not palabras:
        return None
    # «un/una/uno» solo cuentan delante de «mil», «millón» o «día luz»
    if palabras[0] in ('un', 'una', 'uno'):
        if len(palabras) == 1:
            if not re.match(r'\s+(?:d[ií]as?|años?)[\s-]+luz', texto[fin:], re.I):
                return None
        elif palabras[1] not in ('mil', 'millón', 'millon'):
            return None
    total = actual = 0
    for w in palabras:
        v = PALABRAS_NUM[w]
        if w == 'mil':
            actual = (actual or 1) * 1000
        elif v == 10 ** 6:
            total += (actual or 1) * 10 ** 6
            actual = 0
        else:
            actual += v
    valor = total + actual
    escala = 10 ** 6 if palabras[-1].startswith('mill') else (1000 if palabras[-1] == 'mil' else 1)
    ceros = len(str(int(valor))) - len(str(int(valor)).rstrip('0'))
    return Num(mag=float(valor), palabra=True, ceros=ceros, escala=float(escala) if escala > 1 else 1.0, ini=pos), fin


def tokenizar(texto, ingles=False):
    """Lista de tokens: Num (tipo 'num' o 'fecha') y objetos simples con tipo op/sqrt/lp/rp/eq/apx/pal/otro."""
    toks, pos, n = [], 0, len(texto)
    while pos < n:
        while pos < n and texto[pos].isspace():
            pos += 1
        if pos >= n:
            break
        hecho = False
        if not ingles:
            for patron, clase in FECHAS:
                m = patron.match(texto, pos)
                if m and (pos == 0 or not texto[pos - 1].isalnum()):
                    g = m.groups()
                    if clase in ('corta',):
                        f = (int(g[0]), MESES_CORTOS[g[1].lower()], int(g[2]))
                    elif clase == 'larga':
                        f = (int(g[0]), MESES[g[1].lower()], int(g[2]) if g[2] and g[2].isdigit() else None)
                    elif clase == 'mes-año':
                        f = (None, MESES[g[0].lower()], int(g[1]))
                    elif clase == 'mes-año-corta':
                        f = (None, MESES_CORTOS[g[0].lower()], int(g[1]))
                    else:
                        f = (None, MESES[g[0].lower()], None)
                    toks.append(Num(tipo='fecha', fecha=f, fam='fecha', texto=m.group(0), ini=pos, fin=m.end()))
                    pos, hecho = m.end(), True
                    break
        if hecho:
            continue
        m = R_TOKEN.match(texto, pos)
        if m.lastgroup == 'num':
            val, dec = valor_de(m.group('num'), ingles)
            s = re.sub(r'[    ]', '', m.group('num'))
            ceros = 0 if dec else len(s) - len(s.rstrip('0'))
            num = Num(mag=val, dec=dec, ceros=ceros, ini=pos)
            fin = m.end()
            e = R_SUP.match(texto, fin)
            if e:
                try:
                    num.mag = val ** int(''.join(SUP[c] for c in e.group()))
                except OverflowError:
                    pass
                num.dec, num.ceros, fin = 6, 0, e.end()
            fin = _completar(texto, num, fin, ingles)
            num.fin, num.texto = fin, texto[pos:fin].strip()
            toks.append(num)
            pos = fin
            continue
        if m.lastgroup == 'pal':
            w = m.group('pal')
            if not ingles and w.lower() in PALABRAS_NUM:
                r = _palabras_numero(texto, pos)
                if r:
                    num, fin = r
                    fin = _completar(texto, num, fin)
                    num.fin, num.texto = fin, texto[pos:fin].strip()
                    toks.append(num)
                    pos = fin
                    continue
            tipo = 'op' if w in ('x', 'X') else 'pal'
            toks.append(Num(tipo=tipo, texto='×' if tipo == 'op' else w, ini=pos, fin=m.end()))
            pos = m.end()
            continue
        toks.append(Num(tipo=m.lastgroup, texto=m.group(0), ini=pos, fin=m.end()))
        pos = m.end()
    return toks


def comparador(antes):
    cola = antes[-40:]
    if R_APROX.search(cola) and not re.search(r'm[aá]s\s+de\s*$', cola, re.I) or re.search(r'poco\s+m[aá]s\s+de\s*$', cola, re.I):
        return '≈'
    if R_MENOR.search(cola):
        return '<'
    if R_MAYOR.search(cola):
        return '>'
    if R_APROX.search(cola):
        return '≈'
    return None


def es_nombre(antes, num):
    """«Voyager 1», «Pioneer 10», «AC +79 3888»: el número es parte de un nombre, no una cifra."""
    if num.tipo != 'num' or num.palabra or num.dec or num.mult_txt or (num.fam and not num.fam.startswith('conteo')) or num.mag >= 10000             or 1000 <= num.mag <= 2100:
        return False
    m = R_NOMBRE.search(antes)
    if not m:
        return False
    previo = antes[:m.start(1)]
    if previo and not (previo[-1].isspace() or previo[-1] in '(«"“'):
        return False
    return m.group(1).lower().strip('*') not in COMUNES


def limpiar(texto):
    """Quita negritas, enlaces, URL, horas y referencias que no son cifras."""
    t = texto.replace('**', '').replace('`', '')
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    t = R_URL.sub(' ', t)
    t = re.sub(r'\bdoi:\s*\S+|\barXiv:?\s*[\d.]+(?:v\d)?', ' ', t, flags=re.I)
    t = re.sub(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', lambda m: ' ' * len(m.group()), t)
    t = re.sub(r'(?<!\w)\*(?!\s)|(?<=\S)\*(?!\w)', '', t)  # cursivas *texto*
    return t


def numeros(texto, columna=''):
    """Cifras de un texto en prosa, sin nombres propios ni referencias, con rangos y «±» completados."""
    toks = tokenizar(texto)
    salida = []
    for tk in toks:
        if tk.tipo not in ('num', 'fecha'):
            continue
        antes = texto[:tk.ini]
        if R_EXCLUIR.search(antes[-30:]) or es_nombre(antes, tk):
            continue
        if re.match(r'\s*[×÷*/^]', texto[tk.fin:]) or re.search(r'[×÷*/^]\s*$', antes):
            continue  # pieza de una fórmula escrita en la frase («1 ÷ H₀»): no es una cifra suelta
        tk.cmp = comparador(antes)
        tk.col = columna
        salida.append(tk)
    # «13 000 y 15 000 millones», «13,6 ± 1,0 (est.) ± 1,4 mil millones», «70–76 km/s»: el multiplicador y la unidad
    # del último valen para los anteriores.
    for i in range(len(salida) - 2, -1, -1):
        a, b = salida[i], salida[i + 1]
        if a.tipo != 'num' or b.tipo != 'num' or a.palabra:
            continue
        entre = re.sub(r'\([^)]*\)', ' ', texto[a.fin:b.ini])
        if not re.fullmatch(r'\s*(?:±|–|—|-|a|y|o|al|hasta)?\s*', entre, re.I):
            continue
        if re.fullmatch(r'\s*(?:–|—|-|a|al|hasta)\s*', entre) or (re.fullmatch(r'\s*y\s*', entre) and
                                                                  re.search(r'\bentre\s*$', texto[:a.ini], re.I)):
            a.rango, b.rango = b, a
        if a.escala == 1 and b.escala > 1 and not a.fam:
            a.escala, a.mult_txt = b.escala, True
            a.mag *= b.escala
        if not a.fam and b.fam:
            a.fam, a.unidad, a.factor = b.fam, b.unidad, b.factor
        a.anio = False if (a.escala > 1 or a.fam) else a.anio
    return salida


# ------------------------------------------------------------------ comparación
def _cmp_valores(g, gv, tv, paso):
    gv, tv = abs(gv), abs(tv)
    d, ref = abs(gv - tv), max(gv, tv, 1e-300)
    if d <= 1e-9 * ref:
        return 'exacto'
    if g.cmp == '>':
        return 'cota' if gv * (1 - 1e-9) <= tv <= gv * 3 else None
    if g.cmp == '<':
        return 'cota' if gv / 3 <= tv <= gv * (1 + 1e-9) else None
    if d <= paso / 2 * 1.0001:
        return 'redondeo'
    if g.cmp == '≈' and d / ref <= 0.05:
        return 'aprox'
    if d / ref <= 0.10:
        return 'cercano'
    return None


def con_unidad(n):
    """Unidad física (km, años, %…). El «conteo» (115 imágenes) y «veces» se comparan en crudo."""
    return bool(n.fam) and not n.fam.startswith('conteo') and n.fam != 'factor'


def fechas_ok(g, t):
    return g[1] == t[1] and (g[0] is None or g[0] == t[0]) and (g[2] is None or t[2] is None or g[2] == t[2])


def comparar(g, t):
    """Calidad de la coincidencia entre un número del guion (g) y uno de la tabla (t), o None."""
    if g.tipo == 'fecha' or t.tipo == 'fecha':
        if g.tipo == 'fecha' and t.tipo == 'fecha':
            return 'exacto' if fechas_ok(g.fecha, t.fecha) else None
        if g.anio and t.tipo == 'fecha':
            return 'exacto' if t.fecha[2] == g.mag else None
        return None
    if g.anio or t.anio:
        return 'exacto' if g.anio and (t.anio or not t.fam) and abs(t.mag - g.mag) < 1e-9 else None
    if con_unidad(g) and con_unidad(t):
        if g.fam != t.fam:
            return None
        gv, tv, paso = g.base, t.base, g.paso(True)
    else:
        gv, tv, paso = g.mag, t.mag, g.paso()
    q = _cmp_valores(g, gv, tv, paso)
    if q in CALIDAD_OK:
        return q
    for k in (1e3, 1e6, 1e9, 1e-3, 1e-6, 1e-9):
        if _cmp_valores(g, gv, tv * k, paso) in CALIDAD_OK:
            return 'escala'
    return q


ORDEN_CALIDAD = ['exacto', 'redondeo', 'escala', 'cota', 'aprox', 'cercano']


def mejor(g, candidatos, mult_en_contexto):
    """(calidad, candidato) de la mejor coincidencia, o (None, None)."""
    mejor_q, mejor_t = None, None
    for t in candidatos:
        q = comparar(g, t)
        if q == 'escala' and not (mult_en_contexto or g.mult_txt or t.mult_txt):
            q = 'cercano-escala'
        if q in ORDEN_CALIDAD and (mejor_q not in ORDEN_CALIDAD or ORDEN_CALIDAD.index(q) < ORDEN_CALIDAD.index(mejor_q)):
            mejor_q, mejor_t = q, t
        elif q == 'cercano-escala' and mejor_q is None:
            mejor_q, mejor_t = q, t
    return mejor_q, mejor_t


def coincide_calculo(r, base, crudo):
    """¿El número r (resultado escrito) coincide con el valor de la cuenta? Prueba unidades base, valor crudo y %."""
    pruebas = [(r.base, base, r.paso(True)), (r.mag, crudo, r.paso()), (r.mag, base, r.paso())]
    if r.unidad == '%':
        pruebas += [(r.mag, crudo * 100, r.paso()), (r.mag, base * 100, r.paso())]
    for k in (1e3, 1e6, 1e9):  # «63 millones» frente a una cuenta en miles de millones (0,063)
        if r.escala >= k:
            pruebas += [(r.mag / k, crudo, r.paso() / k), (r.mag / (k * 1e3), crudo, r.paso() / (k * 1e3))]
    calidades = [_cmp_valores(r, a, b, p) for a, b, p in pruebas if b is not None and not math.isnan(b)]
    for q in ORDEN_CALIDAD:
        if q in calidades:
            return q
    return None


# ------------------------------------------------------------------ cuentas
def _primario(s, k):
    if k >= len(s):
        return None
    t = s[k]
    if t.tipo == 'num':
        return t.base, t.mag, k + 1, 0
    if t.tipo == 'sqrt':
        r = _potencia(s, k + 1)
        if r and r[0] >= 0 and r[1] >= 0:
            return math.sqrt(r[0]), math.sqrt(r[1]), r[2], r[3] + 1
        return None
    if t.tipo == 'lp':
        r = _suma(s, k + 1)
        if r and r[2] < len(s) and s[r[2]].tipo == 'rp':
            return r[0], r[1], r[2] + 1, r[3]
    return None


def _potencia(s, k):
    r = _primario(s, k)
    if r and r[2] < len(s) and s[r[2]].tipo == 'op' and s[r[2]].texto == '^':
        e = _potencia(s, r[2] + 1)
        if e:
            try:
                return r[0] ** e[0], r[1] ** e[1], e[2], r[3] + e[3] + 1
            except (OverflowError, ValueError, ZeroDivisionError):
                return None
    return r


def _producto(s, k):
    r = _potencia(s, k)
    while r and r[2] < len(s) and s[r[2]].tipo == 'op' and s[r[2]].texto in '×*/÷':
        d = _potencia(s, r[2] + 1)
        if not d:
            break
        try:
            if s[r[2]].texto in '/÷':
                r = r[0] / d[0], r[1] / d[1], d[2], r[3] + d[3] + 1
            else:
                r = r[0] * d[0], r[1] * d[1], d[2], r[3] + d[3] + 1
        except ZeroDivisionError:
            break
    return r


def _suma(s, k):
    r = _producto(s, k)
    while r and r[2] < len(s) and s[r[2]].tipo == 'op' and s[r[2]].texto in '+−-':
        d = _producto(s, r[2] + 1)
        if not d:
            break
        signo = 1 if s[r[2]].texto == '+' else -1
        r = r[0] + signo * d[0], r[1] + signo * d[1], d[2], r[3] + d[3] + 1
    return r


def _fmt(v):
    if v is None or math.isnan(v):
        return '?'
    a = abs(v)
    if a and (a >= 1e7 or a < 1e-3):
        return '%.4g' % v
    return ('%.6g' % v).replace('.', ',')


def cuentas(texto):
    """Cuentas que hay en un texto y su comprobación.
    Devuelve una lista de dicts: expr, base, crudo, resultado (Num o None), calidad, previo (Num delante entre paréntesis)."""
    toks = tokenizar(texto)
    for t in toks:
        if t.tipo == 'num':
            t.cmp = comparador(texto[:t.ini])
    MATE = ('num', 'op', 'sqrt', 'lp', 'rp')
    # 1) agrupar en secuencias matemáticas y separadores
    items, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t.tipo in MATE and t.tipo != 'fecha':
            sec = []
            while i < len(toks) and (toks[i].tipo in MATE or (toks[i].tipo == 'apx' and sec and sec[-1].tipo == 'op'
                                                               and i + 1 < len(toks) and toks[i + 1].tipo == 'num')):
                if toks[i].tipo != 'apx':
                    sec.append(toks[i])
                i += 1
            # 2) dentro de la secuencia: expresiones (con al menos una operación) y números sueltos
            k = 0
            while k < len(sec):
                r = _suma(sec, k)
                if r and r[2] > k:
                    if r[3] > 0:
                        items.append({'tipo': 'expr', 'base': r[0], 'crudo': r[1], 'ini': sec[k].ini, 'fin': sec[r[2] - 1].fin,
                                      'parentesis': sec[k].tipo == 'lp'})
                    elif sec[k].tipo == 'num':
                        items.append({'tipo': 'num', 'num': sec[k]})
                    k = r[2]
                else:
                    k += 1
            continue
        items.append({'tipo': 'sep' if t.tipo in ('eq', 'apx') else 'brk', 'tok': t})
        i += 1
    # 3) cadenas «A = B ≈ C» y «≈ 43 veces (3 000 000 ÷ 69 000)»
    salida = []
    for j, it in enumerate(items):
        if it['tipo'] != 'expr':
            continue
        it['expr'] = texto[it['ini']:it['fin']].strip()
        it['resultado'] = it['calidad'] = None
        k = j + 1
        while k < len(items) and items[k]['tipo'] == 'sep':
            k += 1
        if k > j + 1 and k < len(items) and items[k]['tipo'] in ('num', 'expr'):
            sig = items[k]
            if sig['tipo'] == 'num':
                it['resultado'] = sig['num']
                it['calidad'] = coincide_calculo(sig['num'], it['base'], it['crudo'])
            else:
                it['resultado'] = Num(mag=sig['crudo'], dec=4, texto=texto[sig['ini']:sig['fin']].strip())
                d = abs(sig['base'] - it['base']) / max(abs(it['base']), 1e-300)
                it['calidad'] = 'exacto' if d < 1e-9 else ('redondeo' if d < 1e-3 else ('aprox' if d < 0.01 else ('cercano' if d < 0.1 else None)))
        elif it['parentesis'] and j > 0:
            p = j - 1
            while p >= 0 and items[p]['tipo'] == 'sep':
                p -= 1
            if p >= 0 and items[p]['tipo'] == 'num' and p >= j - 2:
                it['resultado'] = items[p]['num']
                it['calidad'] = coincide_calculo(items[p]['num'], it['base'], it['crudo'])
        salida.append(it)
    return salida


def describir_cuenta(c):
    s = '%s = %s' % (c['expr'], _fmt(c['crudo'] if c['crudo'] == c['base'] else c['base']))
    if c['resultado'] is not None:
        s += ' frente a %s (%s)' % (c['resultado'].texto, c['calidad'] or 'no coincide')
    return s


def estado_cuenta(c):
    if c['resultado'] is None:
        return None
    if c['calidad'] in CALIDAD_OK:
        return OK
    return DUDOSA if c['calidad'] == 'cercano' else DISC


# ------------------------------------------------------------------ hoja de cifras
def celdas(linea):
    return [c.strip() for c in linea.strip().strip('|').split('|')]


def leer_hoja(texto):
    """Filas numeradas de la tabla principal, cuentas de «Cálculos propios» y filas volátiles por notas."""
    filas, calculos, volatiles = {}, [], set()
    lineas = texto.splitlines()
    i = 0
    while i < len(lineas):
        l = lineas[i]
        if l.startswith('|') and i + 1 < len(lineas) and SEPARADOR.match(lineas[i + 1]):
            cab = [plegar(c.strip('* ')) for c in celdas(l)]
            principal = any('valor' in c for c in cab) and any('fuente' in c for c in cab)
            de_calculo = not principal and any('resultado' in c for c in cab)
            iv = next((k for k, c in enumerate(cab) if 'valor' in c), None)
            ifu = next((k for k, c in enumerate(cab) if 'fuente' in c), None)
            ie = next((k for k, c in enumerate(cab) if 'estado' in c), None)
            ir = next((k for k, c in enumerate(cab) if 'resultado' in c), None)
            ino = next((k for k, c in enumerate(cab) if 'nota' in c), None)
            j = i + 2
            while j < len(lineas) and lineas[j].startswith('|') and not SEPARADOR.match(lineas[j]):
                c = celdas(lineas[j])
                if principal:
                    m = re.match(r'^\**(\d+)\**$', c[0])
                    if m:
                        n = int(m.group(1))
                        get = lambda k: c[k] if k is not None and k < len(c) else ''
                        dato = c[1] if len(c) > 1 and iv != 1 else ''
                        filas[n] = {'n': n, 'linea': j + 1, 'dato': dato, 'valor': get(iv), 'fuente': get(ifu),
                                    'estado': get(ie) if ie is not None else (c[-1] if c else ''), 'texto': lineas[j]}
                elif de_calculo:
                    ident = c[0].strip('* ')
                    expr_txt = ' | '.join(x for k, x in enumerate(c) if k not in (ir, ino))
                    calculos.append({'id': ident, 'linea': j + 1, 'expr_txt': expr_txt,
                                     'resultado_txt': c[ir] if ir is not None and ir < len(c) else '', 'texto': lineas[j]})
                j += 1
            i = j
            continue
        if not l.startswith('|') and R_VOLATIL_NOTA.search(l):
            for grupo in re.findall(r'\bfilas?\s+((?:\d+\s*(?:,|y|e)?\s*)+)', l, re.I):
                volatiles.update(int(x) for x in re.findall(r'\d+', grupo))
        i += 1
    for n, f in filas.items():
        if R_VOLATIL_FILA.search(f['dato']) or '⏰' in f['texto']:
            volatiles.add(n)
        ref = f['valor']
        if re.search(r'ver\s+izquierda', ref, re.I) or not re.search(r'\d', ref):
            ref = f['dato'] + ' · ' + ref
        f['nums'] = numeros(limpiar(ref), 'valor') + [x for x in numeros(limpiar(f['dato']), 'dato')]
        f['anios_fuente'] = [x for x in numeros(limpiar(f['fuente']), 'fuente') if x.anio or x.tipo == 'fecha']
        f['mult'] = bool(re.search(r'\b(?:mil(?:es)?\s+(?:de\s+)?millones|millones|mill[oó]n|mil)\b', f['texto'], re.I))
        f['cuentas'] = cuentas(limpiar(f['valor']))
        f['urls'] = urls(f['fuente'])
        f['volatil'] = n in volatiles
    return filas, calculos


def urls(texto):
    completas = [u.rstrip('.') for u in R_URL.findall(texto)]
    resto = R_URL.sub(' ', texto)
    sueltas = ['https://' + d.rstrip('.') for d in R_DOMINIO.findall(resto)]
    vistos, salida = set(), []
    for u in completas + sueltas:
        if u not in vistos:
            vistos.add(u)
            salida.append(u)
    return salida


# ------------------------------------------------------------------ guion
R_MARCA = re.compile(r'\[✔[^\]]*\]|\[c[aá]lculo propio[^\]]*\]', re.I)


def seccion_guion(texto):
    """(número de la primera línea, líneas) de la sección «## Guion»."""
    lineas = texto.splitlines()
    for i, l in enumerate(lineas):
        if re.match(r'^##\s+Guion\b', l, re.I):
            j = i + 1
            while j < len(lineas) and not re.match(r'^##\s', lineas[j]):
                j += 1
            return i + 1, lineas[i + 1:j]
    return 0, []


def limpiar_segmento(seg):
    s = re.sub(r'\{[^{}]*\}', ' ', seg)                       # {pausa}, {Pantalla: …}
    s = re.sub(r'\[Pantalla[^\[\]]*\]', ' ', s, flags=re.I)   # [Pantalla: …] completos
    s = re.sub(r'\[Pantalla:?', ' ', s, flags=re.I)           # una pantalla que contiene la marca
    s = re.sub(r'\[(?:REVISAR)\]', ' ', s, flags=re.I)
    s = limpiar(s)
    return re.sub(r'\s+', ' ', s).strip(' .,;:')


def marcas(texto, lineas_cambiadas=None):
    """Cada marca del guion con su frase: lo que hay entre la marca anterior (o el inicio de la línea) y ella."""
    primera, cuerpo = seccion_guion(texto)
    salida = []
    for k, linea in enumerate(cuerpo):
        nlinea = primera + 1 + k
        if lineas_cambiadas is not None and nlinea not in lineas_cambiadas:
            continue
        previo = 0
        for m in R_MARCA.finditer(linea):
            contenido = m.group(0)[1:-1]
            calc = re.search(r'c[aá]lculo propio\s*[:,]?\s*(.*)$', contenido, re.I)
            parte_filas = contenido[:calc.start()] if calc else contenido
            filas = [int(x) for x in re.findall(r'\d+', parte_filas)] if contenido.startswith('✔') else []
            salida.append({'linea': nlinea, 'marca': m.group(0), 'filas': filas,
                           'calculo': calc is not None, 'expr': (calc.group(1).strip() if calc else ''),
                           'comprobar': bool(re.search(r'comprobar', contenido, re.I)),
                           'frase': limpiar_segmento(linea[previo:m.start()])})
            previo = m.end()
    return salida


# ------------------------------------------------------------------ web
def _texto_html(crudo):
    t = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', crudo)
    t = re.sub(r'(?s)<!--.*?-->', ' ', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', html.unescape(t)).strip()


def descargar(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (verificar-cifras.py; canal de divulgacion)',
                                               'Accept-Language': 'es,en;q=0.8'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            tipo = r.headers.get('Content-Type', '')
            datos = r.read(6_000_000)
            codigo = getattr(r, 'status', 200)
            charset = r.headers.get_content_charset() or 'utf-8'
    except urllib.error.HTTPError as e:
        return {'codigo': e.code, 'error': 'HTTP %d' % e.code}
    except Exception as e:  # red, DNS, SSL, tiempo de espera
        return {'codigo': 0, 'error': '%s: %s' % (type(e).__name__, str(e)[:120])}
    if 'pdf' in tipo.lower() or datos[:5] == b'%PDF-':
        return {'codigo': codigo, 'tipo': 'pdf', 'texto': ''}
    crudo = datos.decode(charset, errors='replace')
    lang = re.search(r'<html[^>]*\blang=["\']?([a-zA-Z]{2})', crudo[:5000])
    return {'codigo': codigo, 'tipo': 'html', 'idioma': lang.group(1).lower() if lang else '', 'texto': _texto_html(crudo)[:800_000]}


def pagina(url, carpeta, max_horas, sin_cache):
    cache_dir = os.path.join(carpeta, '.estado', 'cache-web')
    arch = os.path.join(cache_dir, hashlib.sha1(url.encode()).hexdigest()[:16] + '.json')
    if not sin_cache and os.path.exists(arch):
        try:
            with open(arch, encoding='utf-8') as fh:
                d = json.load(fh)
            edad = datetime.datetime.now() - datetime.datetime.fromisoformat(d['fecha'])
            if edad.total_seconds() <= max_horas * 3600 and not d.get('error'):
                d['de_cache'] = True
                return d
        except (OSError, ValueError, KeyError):
            pass
    d = descargar(url)
    d['url'], d['fecha'] = url, datetime.datetime.now().isoformat(timespec='seconds')
    os.makedirs(cache_dir, exist_ok=True)
    with open(arch, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, ensure_ascii=False)
    d['de_cache'] = False
    return d


def valores_pagina(d):
    """Magnitudes numéricas que aparecen en el texto de la página (con y sin multiplicador)."""
    if '_valores' in d:
        return d['_valores']
    texto = d.get('texto', '')
    vals = set()
    if d.get('idioma') == 'es':
        for t in tokenizar(texto):
            if t.tipo == 'num':
                vals.add(t.mag)
                vals.add(t.mag / t.escala)
    else:
        for m in re.finditer(r'(?<![\w.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?!\d)', texto):
            v, _ = valor_de(m.group(1), ingles=True)
            vals.add(v)
            mm = R_MULT_EN.match(texto, m.end())
            if mm:
                vals.add(v * MULT[mm.group(1).lower().rstrip('s')])
    d['_valores'] = sorted(vals)
    return d['_valores']


def en_pagina(t, vals):
    if t.tipo == 'fecha':
        return t.fecha[2] is None or float(t.fecha[2]) in vals
    objetivo = [t.mag, t.mag / t.escala] + [t.mag * k for k in (1e-3, 1e-6, 1e-9, 1e3, 1e6, 1e9)]
    tol = max(t.paso() / 2, 0.0)
    for x in objetivo:
        for v in vals:
            if abs(v - x) <= max(1e-9 * abs(x), tol if x == t.mag else 0, 0.002 * abs(x) if not t.anio else 0):
                return True
    return False


# ------------------------------------------------------------------ verificación
def peor(a, b):
    return a if GRAVEDAD[a] >= GRAVEDAD[b] else b


def significativo(g):
    return g.anio or g.tipo == 'fecha' or con_unidad(g) or g.mag >= 100 or g.dec > 0


def menor(g):
    """«dos», «tres»…: palabras pequeñas sin unidad física. Solo cuentan si contradicen la tabla."""
    return g.palabra and g.mag <= 10 and not con_unidad(g)


def compatible_otra(g, t):
    """Para buscar en filas no citadas hace falta la misma clase de cifra (no basta un «3» suelto)."""
    if g.tipo == 'fecha' or g.anio:
        return True
    especifico = t.dec > 0 or t.mag >= 100
    if con_unidad(g):
        return (con_unidad(t) and t.fam == g.fam) or (not con_unidad(t) and especifico and t.tipo == 'num' and not t.anio)
    return significativo(g)


def verificar_numero(g, citadas, otras, otras_cuentas):
    """(resultado, texto, número de la tabla) de un número del guion: primero sus filas citadas y las cuentas de esas
    filas; después las demás cuentas y el resto de la hoja. Resultado None = palabra pequeña sin comprobar."""
    cand = [t for f in citadas for t in f['nums']]
    mult = any(f['mult'] for f in citadas)
    q, t = mejor(g, cand, mult)
    if q in CALIDAD_OK or q == 'escala':
        return OK, '%s → %s (%s)' % (g.texto, t.texto, q), t
    if g.anio or g.tipo == 'fecha':
        q2, _ = mejor(g, [x for f in citadas for x in f['anios_fuente']], mult)
        if q2 in CALIDAD_OK:
            return OK, '%s → año de la fuente' % g.texto, None
        if g.tipo == 'fecha' and g.fecha[2] and any(x.anio and x.mag == g.fecha[2] for f in citadas for x in f['anios_fuente']):
            return DUDOSA, '«%s»: en la fila solo está el año (la fuente es de %d)' % (g.texto, g.fecha[2]), None
    if g.tipo == 'fecha' or g.anio:  # una fecha no se compara con resultados de cuentas
        otras_cuentas, cuentas_fila = [], False
    else:
        cuentas_fila = True
    for f in (citadas if cuentas_fila else []):
        for c in f['cuentas']:
            if coincide_calculo(g, c['base'], c['crudo']) in CALIDAD_OK:
                return OK, '%s → cuenta de la fila (%s)' % (g.texto, _fmt(c['crudo'])), None
    if significativo(g):
        for c in otras_cuentas:
            if coincide_calculo(g, c['base'], c['crudo']) in ('exacto', 'redondeo'):
                return OK, '%s → cuenta (%s)' % (g.texto, _fmt(c['crudo'])), None
    for f in otras:
        q3, _ = mejor(g, [x for x in f['nums'] if compatible_otra(g, x)], f['mult'])
        if q3 in CALIDAD_OK or q3 == 'escala':
            return OK, '%s → %s (%s)' % (g.texto, f['nombre'], q3), None
    if g.rango is not None:
        lo, hi = sorted((g.base, g.rango.base) if con_unidad(g) else (g.mag, g.rango.mag))
        for x in cand:
            if x.tipo == 'num' and not x.anio and (x.fam == g.fam or not con_unidad(x)):
                v = x.base if con_unidad(g) and con_unidad(x) else x.mag
                if lo <= v <= hi or any(lo <= v * k <= hi for k in (1e3, 1e6, 1e9)):
                    return OK, 'rango «%s–%s» contiene «%s»' % (min(g.texto, g.rango.texto), max(g.texto, g.rango.texto), x.texto), None
        return DUDOSA, 'rango «%s» / «%s»: ningún valor de la fila cae dentro' % (g.texto, g.rango.texto), None
    # contradicción con la fila citada: misma unidad, o la misma palabra contada («dos instrumentos» / «3 instrumentos»)
    if g.tipo != 'fecha' and g.fam and not g.anio:
        mismos = [x for x in cand if x.fam == g.fam and (con_unidad(g) or g.fam.startswith('conteo'))]
        if mismos:
            cerca = min(mismos, key=lambda x: abs(math.log10(max(abs(x.base), 1e-300)) - math.log10(max(abs(g.base), 1e-300))))
            return DISC, 'guion «%s» ≠ tabla «%s»' % (g.texto, cerca.texto), None
    if menor(g):
        return None, 'sin comprobar «%s» (palabra pequeña)' % g.texto, None
    if q in ('cercano', 'cercano-escala'):
        return DUDOSA, '«%s» parecido a «%s» de la tabla, pero no igual' % (g.texto, t.texto), None
    return DUDOSA, '«%s» no aparece en la fila %s' % (g.texto, ', '.join(str(f['n']) for f in citadas) or '—'), None


def verificar_marca(mk, filas, extra, otras_cuentas):
    res = {'id': ('%s · L%d' % (mk['marca'], mk['linea'])), 'tipo': 'cálculo' if not mk['filas'] else 'cifra',
           'linea': mk['linea'], 'filas': mk['filas'], 'frase': mk['frase'], 'detalle': [], 'motivos': [],
           'resultado': OK, 'volatil': mk['comprobar'], 'usados': {}}

    def motivo(estado, texto):
        res['resultado'] = peor(res['resultado'], estado)
        res['motivos'].append(texto)

    citadas = []
    for n in mk['filas']:
        if n not in filas:
            motivo(DISC, 'la fila %d no existe en la hoja de cifras' % n)
            continue
        f = filas[n]
        citadas.append(f)
        res['volatil'] = res['volatil'] or f['volatil']
        if '❌' in f['estado']:
            motivo(DISC, 'la fila %d está marcada ❌' % n)
        elif '✅' not in f['estado']:
            motivo(DUDOSA, 'fila %d con estado «%s»' % (n, re.sub(r'\s+', ' ', f['estado'])[:60]))
        for c in f['cuentas']:
            e = estado_cuenta(c)
            if e and e != OK:
                motivo(e, 'cuenta de la fila %d: %s' % (n, describir_cuenta(c)))
    # números de la frase (sin los de dentro de la cuenta de la marca)
    nums = numeros(mk['frase'])
    cuenta_marca = cuentas(limpiar(mk['expr'])) if mk['expr'] else []
    for c in cuenta_marca:
        e = estado_cuenta(c)
        if e is None:  # sin resultado escrito en la marca: se compara con la frase
            ok = any(coincide_calculo(g, c['base'], c['crudo']) in CALIDAD_OK for g in nums)
            e = OK if ok else DUDOSA
            res['detalle'].append('cuenta %s = %s%s' % (c['expr'], _fmt(c['crudo']), '' if ok else ' (no aparece en la frase)'))
            if not ok:
                motivo(DUDOSA, 'el resultado de la cuenta (%s = %s) no aparece en la frase' % (c['expr'], _fmt(c['crudo'])))
        else:
            res['detalle'].append('cuenta ' + describir_cuenta(c))
            if e != OK:
                motivo(e, 'cuenta de la marca: ' + describir_cuenta(c))
    if mk['calculo'] and not cuenta_marca and not any(f['cuentas'] for f in citadas):
        motivo(NOVER, 'marca de cálculo sin una cuenta que se pueda rehacer')
    ids = {f['n'] for f in citadas}
    otras = [dict(f, nombre='fila %d' % n) for n, f in sorted(filas.items()) if n not in ids] + extra
    comprobados = 0
    todas_cuentas = otras_cuentas + cuenta_marca
    for g in nums:
        if cuenta_marca and any(coincide_calculo(g, c['base'], c['crudo']) in CALIDAD_OK or
                                (c['resultado'] is not None and comparar(g, c['resultado']) in CALIDAD_OK)
                                for c in cuenta_marca):
            res['detalle'].append('%s → cuenta de la marca' % g.texto)
            comprobados += 1
            continue
        e, texto, t = verificar_numero(g, citadas, otras, todas_cuentas)
        res['detalle'].append(texto)
        if e is None:
            continue
        comprobados += 1
        if e != OK:
            motivo(e, texto)
        elif t is not None:
            for f in citadas:
                if t in f['nums']:
                    res['usados'].setdefault(f['n'], []).append(t)
    if not comprobados and not mk['calculo'] and res['resultado'] == OK:
        motivo(NOVER, 'la frase no tiene números: afirmación de texto, revisar a mano')
    return res


def verificar_calculo_hoja(c):
    res = {'id': 'cálculo %s · hoja L%d' % (c['id'], c['linea']), 'tipo': 'cálculo-hoja', 'linea': c['linea'], 'filas': [],
           'frase': re.sub(r'\s+', ' ', limpiar(c['expr_txt']))[:200], 'detalle': [], 'motivos': [], 'resultado': OK,
           'volatil': False, 'usados': {}}
    lista = cuentas(limpiar(c['expr_txt']))
    resultado = [x for x in numeros(limpiar(c['resultado_txt'])) if x.tipo == 'num']
    if not lista:
        res['resultado'] = NOVER
        res['motivos'].append('sin cuenta numérica que rehacer (fórmula con símbolos)')
        return res, lista
    for k, cu in enumerate(lista):
        e = estado_cuenta(cu)
        res['detalle'].append(describir_cuenta(cu))
        if e and e != OK:
            res['resultado'] = peor(res['resultado'], e)
            res['motivos'].append('cuenta: ' + describir_cuenta(cu))
    # el resultado de la columna «Resultado» se compara con el final de la última cuenta
    ultima = lista[-1]
    final_base, final_crudo = ultima['base'], ultima['crudo']
    if ultima['resultado'] is not None and ultima['calidad'] in CALIDAD_OK:
        final_base, final_crudo = ultima['resultado'].base, ultima['resultado'].mag
    if resultado:
        r = resultado[0]
        q = coincide_calculo(r, final_base, final_crudo) or coincide_calculo(r, ultima['base'], ultima['crudo'])
        if q in CALIDAD_OK:
            res['detalle'].append('resultado %s (%s)' % (r.texto, q))
        elif any(cu['resultado'] is not None for cu in lista):
            res['resultado'] = peor(res['resultado'], NOVER)
            res['motivos'].append('el resultado «%s» no sale de las cuentas escritas (fórmula con símbolos)' % r.texto)
        else:
            res['resultado'] = peor(res['resultado'], DUDOSA if q == 'cercano' else DISC)
            res['motivos'].append('la cuenta da %s y la tabla dice «%s»' % (_fmt(final_crudo), r.texto))
    return res, lista


def comprobar_web(resultados, filas, carpeta, sin_cache, max_urls):
    """Abre las fuentes de las filas citadas y busca en ellas los números usados."""
    por_fila = {}
    for r in resultados:
        for n in r['filas']:
            if n in filas:
                d = por_fila.setdefault(n, {'volatil': False, 'usados': []})
                d['volatil'] = d['volatil'] or r['volatil']
                d['usados'] += r['usados'].get(n, [])
    informe, abiertas = {}, 0
    for n in sorted(por_fila):
        f, d = filas[n], por_fila[n]
        if not f['urls']:
            informe[n] = {'estado': 'sin enlace'}
            continue
        horas = CADUCIDAD_VOLATIL_HORAS if d['volatil'] else CADUCIDAD_DIAS * 24
        responde, bloqueado, texto_vals, notas = False, False, [], []
        for u in f['urls'][:3]:
            if abiertas >= max_urls:
                notas.append('límite de %d enlaces' % max_urls)
                break
            p = pagina(u, carpeta, horas, sin_cache)
            abiertas += 0 if p.get('de_cache') else 1
            if p.get('error'):
                if p.get('codigo') in BLOQUEO:
                    bloqueado = True
                    notas.append('%s no deja leer a un script (%s): abrirla a mano' % (u, p['error']))
                else:
                    notas.append('%s no responde (%s)' % (u, p['error']))
                continue
            responde = True
            if p.get('tipo') == 'pdf':
                notas.append('%s es un PDF (solo se comprobó el enlace)' % u)
                continue
            texto_vals += valores_pagina(p)
        estado = 'responde' if responde else ('bloqueada' if bloqueado else 'no responde')
        informe[n] = {'estado': estado, 'notas': notas, 'vals': texto_vals, 'con_texto': bool(texto_vals)}
    for r in resultados:
        confirmadas = True
        for n in r['filas']:
            w = informe.get(n)
            if not w:
                confirmadas = False
                continue
            if w['estado'] == 'sin enlace':
                confirmadas = False
                r['detalle'].append('fila %d: sin enlace en «Fuente»' % n)
                continue
            if w['estado'] == 'no responde':
                confirmadas = False
                r['resultado'] = peor(r['resultado'], DUDOSA)
                r['motivos'].append('fila %d: ' % n + '; '.join(w['notas']))
                continue
            if w['estado'] == 'bloqueada':  # 403/405/429: el sitio rechaza scripts; no empeora la cifra
                confirmadas = False
                r['detalle'].append('fila %d: ' % n + '; '.join(w['notas']))
                continue
            usados = r['usados'].get(n, [])
            encontrados = [t.texto for t in usados if w['con_texto'] and en_pagina(t, w['vals'])]
            faltan = [t.texto for t in usados if not (w['con_texto'] and en_pagina(t, w['vals']))]
            if faltan and w['con_texto']:
                confirmadas = False
                r['resultado'] = peor(r['resultado'], DUDOSA)
                r['motivos'].append('fila %d: la fuente no muestra %s' % (n, ', '.join('«%s»' % x for x in faltan)))
            elif not w['con_texto'] or not usados:
                confirmadas = False
            r['detalle'].append('fila %d: fuente responde%s' % (n, ('; encontrados ' + ', '.join(encontrados)) if encontrados else ''))
        r['web_confirmada'] = confirmadas and bool(r['filas'])
    return informe


def lineas_cambiadas(carpeta, rol, texto):
    previa = os.path.join(carpeta, '.estado', rol + '.Guion.md')
    if not os.path.exists(previa):
        return None
    antes = (leer(previa) or '').splitlines()
    ahora = texto.splitlines()
    cambiadas = set()
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, antes, ahora, autojunk=False).get_opcodes():
        if op in ('replace', 'insert'):
            cambiadas.update(range(b1 + 1, b2 + 1))
    return cambiadas


def recortar(t, n):
    t = re.sub(r'\s+', ' ', t or '').strip()
    return t if len(t) <= n else t[:n - 1] + '…'


def principal():
    consola()
    ap = argparse.ArgumentParser(description='Parte mecánica del verificador de cifras')
    ap.add_argument('video')
    ap.add_argument('--web', action='store_true', help='abrir las fuentes y buscar los números (con caché)')
    ap.add_argument('--sin-cache', action='store_true', help='con --web, descargar de nuevo aunque haya caché')
    ap.add_argument('--max-enlaces', type=int, default=40, help='con --web, máximo de descargas nuevas (40)')
    ap.add_argument('--pendientes', action='store_true', help='imprimir solo las cifras que no son OK')
    ap.add_argument('--cambios', metavar='ROL', help='solo las líneas cambiadas desde el sello de ese rol (p. ej. verificador)')
    a = ap.parse_args()

    carpeta = resolver_video(a.video)
    guion = leer(ruta(carpeta, F_GUION)) or ''
    hoja = leer(ruta(carpeta, F_CIFRAS))
    if not guion or hoja is None:
        print('ESTADO: FALLA · falta %s' % (F_GUION if not guion else F_CIFRAS))
        return 1
    filas, calculos = leer_hoja(hoja)

    cambiadas, aviso_cambios = None, ''
    if a.cambios:
        cambiadas = lineas_cambiadas(carpeta, a.cambios, guion)
        aviso_cambios = (' · solo %d líneas cambiadas desde el sello de %s' % (len(cambiadas), a.cambios)) if cambiadas is not None \
            else ' · no hay copia sellada de %s: se revisa todo' % a.cambios

    resultados, cuentas_hoja = [], []
    extra = [{'n': c['id'], 'nombre': 'cálculo %s' % c['id'], 'nums': numeros(limpiar(c['texto'].strip('|'))),
              'mult': bool(re.search(r'\bmil(?:es)?\s+(?:de\s+)?millones|\bmillones', c['texto'], re.I))} for c in calculos]
    for c in calculos:
        r, lista = verificar_calculo_hoja(c)
        cuentas_hoja += lista
        resultados.append(r)
    for mk in marcas(guion, cambiadas):
        resultados.append(verificar_marca(mk, filas, extra, cuentas_hoja))

    web = {}
    if a.web:
        web = comprobar_web([r for r in resultados if r['filas']], filas, carpeta, a.sin_cache, a.max_enlaces)
    for r in resultados:
        if r['volatil'] and not r.get('web_confirmada'):
            r['resultado'] = peor(r['resultado'], DUDOSA)
            r['motivos'].append('cifra volátil: recomprobar la fuente el día de grabar' + ('' if a.web else ' (o correr con --web)'))
        elif r['volatil']:
            r['detalle'].append('volátil, pero confirmada hoy en la fuente')

    cuenta = {k: sum(1 for r in resultados if r['resultado'] == k) for k in (OK, DUDOSA, DISC, NOVER)}
    pendientes = [r for r in resultados if r['resultado'] != OK]
    rel = os.path.relpath(carpeta, RAIZ).replace('\\', '/')
    destino = os.path.join(carpeta, '.estado', 'cifras-pendientes.json')
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    citadas = sorted({n for r in pendientes for n in r['filas'] if n in filas})
    cabecera = {
        'video': rel, 'fecha': datetime.datetime.now().isoformat(timespec='seconds'), 'web': a.web,
        'cambios': a.cambios or '', 'resumen': {k.lower().replace(' ', '_'): v for k, v in cuenta.items()},
        'leyenda': 'cada pendiente cita filas; su valor, estado y fuentes están una sola vez en «filas»'}
    tabla = {str(n): {'valor': recortar(filas[n]['valor'], 400), 'estado': recortar(filas[n]['estado'], 80),
                      'fuentes': filas[n]['urls'] or [recortar(filas[n]['fuente'], 160)]} for n in citadas}
    lineas_json = [json.dumps({'id': r['id'], 'linea': r['linea'], 'filas': r['filas'], 'resultado': r['resultado'],
                               'volatil': r['volatil'], 'motivos': [recortar(m, 200) for m in r['motivos']],
                               'frase': recortar(r['frase'], 300)}, ensure_ascii=False) for r in pendientes]
    NL = '\n'
    with open(destino, 'w', encoding='utf-8') as fh:  # compacto: una línea por pendiente y por fila
        unir = lambda d: (',' + NL).join('"%s": %s' % (k, json.dumps(v, ensure_ascii=False)) for k, v in d.items())
        fh.write('{' + NL + unir(cabecera) + ',' + NL + '"pendientes": [' + NL + (',' + NL).join(lineas_json) + NL + '],' + NL)
        fh.write('"filas": {' + NL + unir(tabla) + NL + '}' + NL + '}' + NL)

    print('ESTADO: %d cifras · %d OK · %d DUDOSA · %d DISCREPANCIA · %d NO VERIFICABLE%s%s' % (
        len(resultados), cuenta[OK], cuenta[DUDOSA], cuenta[DISC], cuenta[NOVER], ' · con web' if a.web else '', aviso_cambios))
    print('| cifra | filas | resultado | detalle |')
    print('|---|---|---|---|')
    for r in resultados:
        if a.pendientes and r['resultado'] == OK:
            continue
        detalle = '; '.join(r['motivos']) if r['motivos'] else '; '.join(r['detalle'])
        print('| %s | %s | %s | %s |' % (r['id'], ', '.join(map(str, r['filas'])) or '—', r['resultado'],
                                         recortar(detalle, 220).replace('|', '/')))
    if web:
        sin = sorted(n for n, w in web.items() if w['estado'] != 'responde')
        print('web: %d filas comprobadas%s' % (len(web), (' · sin enlace o sin respuesta: ' + ', '.join(map(str, sin))) if sin else ''))
    print('Pendientes para el agente: %d → %s' % (len(pendientes), os.path.relpath(destino, RAIZ).replace('\\', '/')))
    return 1 if cuenta[DISC] else (2 if pendientes else 0)


if __name__ == '__main__':
    sys.exit(principal())
