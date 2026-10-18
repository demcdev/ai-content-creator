#!/usr/bin/env python3
"""
Catálogo de tipos de escena (escenas.json): listar, explicar uno y validar el escenas.json de un video.

  python herramientas/montaje/catalogo/escenas.py                       # lista los tipos
  python herramientas/montaje/catalogo/escenas.py cifra                 # parámetros y ejemplo de un tipo
  python herramientas/montaje/catalogo/escenas.py --validar "<canal>/3" # revisa 06-montaje/escenas.json de un video

Lo usan también la tubería (pipeline.py) y escaleta-a-escenas.py para avisar de tipos o parámetros que no existen.
No genera video ni usa IA.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))


def cargar():
    with open(os.path.join(AQUI, 'escenas.json'), encoding='utf-8') as f:
        return json.load(f)


def revisar(esc, catalogo=None):
    """Lista de problemas de una escena de escenas.json (vacía si está bien)."""
    cat = catalogo or cargar()
    tipo = esc.get('tipo', 'placeholder')
    id_ = esc.get('id', '?')
    if tipo not in cat['tipos']:
        return ['%s: el tipo «%s» no existe (tipos: %s)' % (id_, tipo, ', '.join(cat['tipos']))]
    d = cat['tipos'][tipo]
    malos = []
    for k in ('id', 'ini', 'fin'):
        if k not in esc:
            malos.append('%s: falta «%s»' % (id_, k))
    for k in d['requeridos']:
        if esc.get(k) in (None, '', []):
            malos.append('%s (%s): falta el parámetro «%s»' % (id_, tipo, k))
    validas = set(cat['comunes']) | set(d['requeridos']) | set(d['opcionales'])
    for k in esc:
        if k not in validas:
            malos.append('%s (%s): el parámetro «%s» no existe en este tipo' % (id_, tipo, k))
    return malos


def listar(cat):
    for nombre, d in cat['tipos'].items():
        req = ', '.join(d['requeridos']) or '—'
        print('%-13s %s' % (nombre, d['descripcion']))
        print('%-13s requeridos: %s' % ('', req))


def explicar(cat, nombre):
    d = cat['tipos'][nombre]
    print('%s: %s' % (nombre, d['descripcion']))
    print('Requeridos:')
    for k, v in d['requeridos'].items() or [('—', '')]:
        print('  %-12s %s' % (k, v))
    print('Opcionales:')
    for k, v in d['opcionales'].items():
        print('  %-12s %s' % (k, v))
    print('Comunes a todos los tipos: %s' % ', '.join(cat['comunes']))
    print('Ejemplo:')
    print(json.dumps(d['ejemplo'], ensure_ascii=False, indent=1))


def main():
    cat = cargar()
    a = sys.argv[1:]
    if not a:
        listar(cat)
        return 0
    if a[0] == '--validar':
        if len(a) < 2:
            print(__doc__)
            return 1
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(AQUI)), 'nucleo'))
        from _comun import MONTAJE, resolver_video
        ruta = os.path.join(resolver_video(a[1]), MONTAJE, 'escenas.json')
        escenas = json.load(open(ruta, encoding='utf-8'))
        malos = [m for e in escenas for m in revisar(e, cat)]
        for m in malos:
            print('ERROR', m)
        print('%d escenas, %d problemas' % (len(escenas), len(malos)))
        return 1 if malos else 0
    if a[0] not in cat['tipos']:
        print('No existe el tipo «%s». Tipos: %s' % (a[0], ', '.join(cat['tipos'])))
        return 1
    explicar(cat, a[0])
    return 0


if __name__ == '__main__':
    sys.exit(main())
