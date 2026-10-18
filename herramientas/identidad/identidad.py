#!/usr/bin/env python3
"""
Identidad de cada canal (colores, voz, animación, nombre, logo, fuente) y la de cada video (la del canal o una propia).

  python herramientas/identidad/identidad.py mostrar "<canal>"                 # identidad del canal
  python herramientas/identidad/identidad.py mostrar "hace-eones/3"        # la que vale para ese video y de dónde sale cada valor
  python herramientas/identidad/identidad.py canal "<canal>" --voz polly-raul --animacion espacial --color AMBAR=242,184,75
  python herramientas/identidad/identidad.py video "<canal>/3" --base canal    # el video usa la identidad del canal
  python herramientas/identidad/identidad.py video "<canal>/3" --base propia --voz google-iapetus --animacion papel-recortado

Archivos: <canal>/identidad/identidad.json (la del canal) y <video>/identidad/identidad.json ({"base": "canal"} o {"base": "propia", ...lo que cambia}).
Con base «propia» solo se cambian los valores indicados; el resto sigue siendo el del canal.
Opciones válidas de --voz: ids de herramientas/voz/voces.json. De --animacion: ids de herramientas/montaje/catalogo/animaciones.json.
--fuente: inter, montserrat o space (las tres con licencia abierta). --musica: nombres de pista separados por coma («Singularity,Event Horizon»; se buscan en
06-montaje/musica/ de cada video). --efectos: si o no (los efectos de sonido aún no los mezcla la tubería: solo quedan declarados).
`resumen <canal|video>` imprime una frase con voz, animación, fuente, colores (en hex), música y efectos: es el texto que Claude usa
al preguntar «¿identidad del canal o propia?». Nunca nombra la marca del canal.
Claude pregunta «¿identidad del canal o propia?» al crear cada video (regla del CLAUDE.md) y después ejecuta esto.
No usa IA ni claves.
"""
import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
HERR = os.path.dirname(AQUI)                       # herramientas/
sys.path.insert(0, os.path.join(HERR, 'nucleo'))
from _comun import (CANALES, CLAVES_IDENTIDAD, COLORES_DEFECTO, F_IDENTIDAD, _json, identidad_efectiva, listar_canales, resolver_canal,  # noqa: E402
                    resolver_video, ruta)


def ids(ruta, clave):
    return [x['id'] for x in _json(ruta).get(clave, [])]


FUENTES = ['inter', 'montserrat', 'space']
VOCES = ids(os.path.join(HERR, 'voz', 'voces.json'), 'voces')
ANIMACIONES = ids(os.path.join(HERR, 'montaje', 'catalogo', 'animaciones.json'), 'animaciones')


def buscar_canal(nombre):
    canal = resolver_canal(nombre)
    if canal:
        return canal
    sys.exit('No existe el canal «%s». Canales: %s' % (nombre, ', '.join(listar_canales())))


def valores(a):
    """Valores indicados en la línea de comandos, ya validados."""
    out = {}
    for k in CLAVES_IDENTIDAD:
        v = getattr(a, k, None)
        if v:
            out[k] = v
    if out.get('fuente') and out['fuente'] not in FUENTES:
        sys.exit('Fuente «%s» no válida. Opciones: %s' % (out['fuente'], ', '.join(FUENTES)))
    if getattr(a, 'musica', None):
        out['musica'] = {'pistas': [x.strip() for x in a.musica.split(',') if x.strip()]}
    if getattr(a, 'efectos', None):
        out['efectos'] = {'usar': a.efectos == 'si'}
    if out.get('voz') and out['voz'] not in VOCES:
        sys.exit('Voz «%s» no existe en voces.json. Opciones: %s' % (out['voz'], ', '.join(VOCES)))
    if out.get('animacion') and out['animacion'] not in ANIMACIONES:
        sys.exit('Animación «%s» no existe en animaciones.json. Opciones: %s' % (out['animacion'], ', '.join(ANIMACIONES)))
    colores = {}
    for c in a.color or []:
        try:
            k, rgb = c.split('=')
            r, g, b = (int(x) for x in rgb.split(','))
            assert k in COLORES_DEFECTO and all(0 <= x <= 255 for x in (r, g, b))
            colores[k] = [r, g, b]
        except Exception:
            sys.exit('Color mal escrito: «%s». Formato: BG=11,16,38 (claves: %s)' % (c, ', '.join(COLORES_DEFECTO)))
    if colores:
        out['colores'] = colores
    return out


def escribir(arch, datos):
    os.makedirs(os.path.dirname(arch), exist_ok=True)
    with open(arch, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
        f.write('\n')


def mostrar(arg):
    es_canal = resolver_canal(arg) is not None
    carpeta = None
    if not es_canal:
        try:
            carpeta = resolver_video(arg)
        except SystemExit:
            carpeta = None
    if carpeta:
        ident, origen = identidad_efectiva(carpeta)
        print('Video: %s · base: %s' % (os.path.basename(carpeta), ident['base'] or '(sin elegir)'))
        for k in CLAVES_IDENTIDAD + ('colores',):
            print('  %-10s %-40s (%s)' % (k, ident[k] if ident[k] != '' else '—', origen[k]))
        return
    canal = buscar_canal(arg)
    datos = _json(ruta(canal, F_IDENTIDAD))
    print('Canal: %s%s' % (os.path.basename(canal), '' if datos else ' · sin identidad/identidad.json (crea uno con: identidad.py canal "%s" --voz ... --animacion ...)' % os.path.basename(canal)))
    for k, v in datos.items():
        print('  %-10s %s' % (k, v))


def hexa(rgb):
    return '#%02X%02X%02X' % tuple(rgb)


def resumen(arg):
    """Frase de la identidad base (la del canal) para la pregunta de «¿canal o propia?»; sin el nombre de la marca."""
    es_canal = resolver_canal(arg) is not None
    carpeta = buscar_canal(arg) if es_canal else resolver_video(arg)
    video = carpeta if not es_canal else os.path.join(carpeta, 'videos', '00-resumen')
    ident, _ = identidad_efectiva(video)
    base = ident['colores']
    colores = ', '.join('%s %s' % (n, hexa(base[k])) for n, k in (('fondo', 'BG'), ('acento', 'AMBAR'), ('texto', 'HUESO'), ('apoyo', 'TIERRA')))
    nombres_voz = {x['id']: x['nombre'] for x in _json(os.path.join(HERR, 'voz', 'voces.json')).get('voces', [])}
    nombres_anim = {x['id']: x['nombre'] for x in _json(os.path.join(HERR, 'montaje', 'catalogo', 'animaciones.json')).get('animaciones', [])}
    voz = nombres_voz.get(ident['voz'], ident['voz']) or 'sin voz definida'
    anim = nombres_anim.get(ident['animacion'], ident['animacion']) or 'sin animación definida'
    pistas = ident['musica'].get('pistas', [])
    musica = 'música: %s' % (', '.join(pistas) if pistas else 'sin pistas definidas')
    efectos = 'con efectos de sonido' if ident['efectos'].get('usar') else 'sin efectos de sonido'
    etiqueta = 'los colores propios del video' if (not es_canal and ident['base'] == 'propia') else 'los colores base del canal'
    return 'Usa la voz %s, la animación %s, la fuente %s, %s (%s), %s y %s.' % (voz, anim, ident['fuente'].capitalize(), etiqueta, colores, musica, efectos)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='orden', required=True)
    for nombre in ('mostrar', 'resumen', 'canal', 'video'):
        p = sub.add_parser(nombre)
        p.add_argument('destino')
        if nombre not in ('mostrar', 'resumen'):
            p.add_argument('--nombre')
            p.add_argument('--logo')
            p.add_argument('--fuente')
            p.add_argument('--voz')
            p.add_argument('--animacion')
            p.add_argument('--musica', help='pistas separadas por coma')
            p.add_argument('--efectos', choices=['si', 'no'])
            p.add_argument('--color', action='append', help='BG=11,16,38 (se puede repetir)')
        if nombre == 'video':
            p.add_argument('--base', choices=['canal', 'propia'], required=True)
    a = ap.parse_args()
    if a.orden == 'mostrar':
        mostrar(a.destino)
        return 0
    if a.orden == 'resumen':
        print(resumen(a.destino))
        return 0
    nuevos = valores(a)
    if a.orden == 'canal':
        canal = buscar_canal(a.destino)
        arch = ruta(canal, F_IDENTIDAD)
        datos = _json(arch)
        colores = datos.get('colores', dict(COLORES_DEFECTO))
        colores.update(nuevos.pop('colores', {}))
        datos.update(nuevos)
        datos['colores'] = colores
        datos.setdefault('nombre', os.path.basename(canal).upper())
        escribir(arch, datos)
        print('Identidad del canal guardada en %s' % arch)
        return 0
    carpeta = resolver_video(a.destino)
    arch = ruta(carpeta, F_IDENTIDAD)
    if a.base == 'canal':
        escribir(arch, {'base': 'canal'})
    else:
        datos = _json(arch)
        colores = datos.get('colores', {})
        colores.update(nuevos.pop('colores', {}))
        datos.update(nuevos)
        if colores:
            datos['colores'] = colores
        datos['base'] = 'propia'
        escribir(arch, datos)
    print('Identidad del video guardada en %s (base: %s)' % (arch, a.base))
    mostrar(carpeta)
    return 0


if __name__ == '__main__':
    sys.exit(main())
