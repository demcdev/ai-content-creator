#!/usr/bin/env python3
"""
Convierte la escaleta técnica de un video en 06-montaje/escenas.json (la lista de escenas que lee el montaje).

  python herramientas/video/escaleta-a-escenas.py "hace-eones/3"
  python herramientas/video/escaleta-a-escenas.py "<canal>/3" --forzar     # sobrescribe un escenas.json existente

Lee las filas de la parte «escaleta técnica» de `escaleta-audiovisual.md` (no la planilla) con el formato
`| **E07 · Nombre de la escena** | 03:12–03:40 | descripción | ... |` y deja, por escena:
{id, nombre, ini, fin, tipo: "placeholder", descripcion}.

Para que la escena salga ya diseñada (sin escribir código), añade a su fila una directiva entre comillas invertidas con el tipo
y los parámetros, separados por «;» (sin «|», que rompe la tabla):

  | **E03 · La cifra** | 00:16–00:28 | Cifra grande. `@cifra valor=13.797; unidad="miles de millones de años"; fuente="Planck 2018"; fila=1` | ... |

Cada valor se lee como JSON si lo es (números, true/false, listas «[...]» y objetos «{...}») y, si no, como texto (las comillas son
opcionales). Los tipos y sus parámetros: `python herramientas/montaje/catalogo/escenas.py` (y `... <tipo>`). Con --validar se
revisa un escenas.json ya escrito. Una escena sin directiva queda como placeholder (o registra una propia en 06-montaje/video.py).
No usa IA y no gasta tokens.
"""
import argparse
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nucleo'))
from _comun import F_ESCALETA, MONTAJE, leer, resolver_video, ruta, sin_seccion  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'montaje', 'catalogo'))
import escenas as catalogo  # noqa: E402

DIRECTIVA = re.compile(r'`@(\w+)\s*([^`]*)`')
FILA = re.compile(r'^\|\s*\*\*(E\d+\w*)\s*[·.:-]\s*(.+?)\*\*\s*\|\s*([\d:.]+)\s*[–-]\s*([\d:.]+)\s*\|(.*)$')


def segundos(txt):
    partes = [float(x) for x in txt.split(':')]
    s = 0.0
    for p in partes:
        s = s * 60 + p
    return round(s, 2)


def partir_directiva(texto):
    """'valor=1; unidad="x; y"; puntos=["a", "b"]' -> ['valor=1', 'unidad="x; y"', 'puntos=["a", "b"]'] (el «;» solo separa fuera de comillas y corchetes)."""
    partes, actual, prof, comillas, previo = [], '', 0, False, ''
    for ch in texto:
        if ch == '"' and previo != '\\':
            comillas = not comillas
        elif not comillas and ch in '[{':
            prof += 1
        elif not comillas and ch in ']}':
            prof -= 1
        if ch == ';' and not comillas and prof == 0:
            partes.append(actual)
            actual = ''
        else:
            actual += ch
        previo = ch
    partes.append(actual)
    return [p.strip() for p in partes if p.strip()]


def valor(txt):
    try:
        return json.loads(txt)
    except ValueError:
        return txt.strip().strip('"')


def leer_directiva(linea):
    """Devuelve (tipo, parámetros) de la directiva «`@tipo clave=valor; ...`» de la fila, o (None, {})."""
    m = DIRECTIVA.search(linea)
    if not m:
        return None, {}
    params = {}
    for trozo in partir_directiva(m.group(2)):
        clave, igual, v = trozo.partition('=')
        if not igual:
            sys.exit('Directiva «%s»: «%s» no tiene la forma clave=valor' % (m.group(1), trozo))
        params[clave.strip()] = valor(v.strip())
    return m.group(1), params


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video')
    ap.add_argument('--forzar', action='store_true')
    ap.add_argument('--validar', action='store_true', help='solo revisa el escenas.json existente contra el catálogo de tipos')
    a = ap.parse_args()
    carpeta = resolver_video(a.video)
    if a.validar:
        destino = os.path.join(carpeta, MONTAJE, 'escenas.json')
        malos = [m for e in json.load(open(destino, encoding='utf-8')) for m in catalogo.revisar(e)]
        for m in malos:
            print('ERROR', m)
        if malos:
            sys.exit('%d problemas' % len(malos))
        print('escenas.json correcto')
        return
    texto = sin_seccion(leer(ruta(carpeta, F_ESCALETA)), 'Planilla de producción')
    escenas, avisos = [], []
    for linea in texto.splitlines():
        m = FILA.match(linea)
        if not m:
            continue
        id_, nombre, ini, fin, resto = m.groups()
        tipo, params = leer_directiva(resto)
        desc = DIRECTIVA.sub('', resto).split('|')[0].strip()
        esc = {'id': id_, 'nombre': nombre.strip(), 'ini': segundos(ini), 'fin': segundos(fin), 'tipo': tipo or 'placeholder',
               'descripcion': re.sub(r'\*\*|`', '', desc)[:300]}
        esc.update(params)
        if tipo:
            esc.pop('descripcion')
            for problema in catalogo.revisar(esc):
                avisos.append(problema)
        escenas.append(esc)
    if not escenas:
        sys.exit('No encontré filas de escenas («| **E01 · Nombre** | 00:00–00:30 | ...») en la escaleta técnica.')
    os.makedirs(os.path.join(carpeta, MONTAJE), exist_ok=True)
    destino = os.path.join(carpeta, MONTAJE, 'escenas.json')
    if os.path.exists(destino) and not a.forzar:
        sys.exit('Ya existe %s. Usa --forzar para sobrescribirlo.' % destino)
    with open(destino, 'w', encoding='utf-8') as f:
        json.dump(escenas, f, ensure_ascii=False, indent=1)
    print('%d escenas -> %s (de %s a %s)' % (len(escenas), destino, escenas[0]['ini'], escenas[-1]['fin']))
    disenadas = sum(1 for e in escenas if e['tipo'] != 'placeholder')
    print('%d con diseño por datos, %d pendientes (placeholder)' % (disenadas, len(escenas) - disenadas))
    for av in avisos:
        print('AVISO', av)


if __name__ == '__main__':
    main()
