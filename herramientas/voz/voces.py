#!/usr/bin/env python3
"""
Lista las voces configuradas (voces.json) y muestra los comandos para generar la de un video.

  python herramientas/voz/voces.py                              # lista las voces y su costo
  python herramientas/voz/voces.py polly-raul "<canal>/3"    # comandos con las rutas de ese video
  python herramientas/voz/voces.py --video "<canal>/3"       # los de la voz de la identidad de ese video

No genera audio ni usa claves: solo imprime lo que hay que ejecutar. Claude pregunta al usuario cuál voz usar
antes de este paso (regla del CLAUDE.md); para añadir una voz, editar voces.json.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
from _comun import identidad_efectiva, resolver_video  # noqa: E402


def cargar():
    with open(os.path.join(AQUI, 'voces.json'), encoding='utf-8') as f:
        return json.load(f)['voces']


def listar(voces):
    for v in voces:
        print('%-15s %s' % (v['id'], v['nombre']))
        print('                Costo: %s' % v['costo'])
        print('                Usada en: %s' % (', '.join(v.get('usada_en', [])) or '—'))


def comandos(voz, video):
    carpeta = resolver_video(video)
    guion = os.path.join(carpeta, 'Guion.md')
    salida = os.path.join(carpeta, 'Voz')
    def sustituir(txt):
        return txt.replace('{guion}', guion).replace('{voz}', salida).replace('{video}', carpeta)

    print('Voz: %s' % voz['nombre'])
    print('Clave necesaria: %s' % voz['clave'])
    print('Costo: %s' % voz['costo'])
    print('')
    for i, paso in enumerate(voz['pasos'], 1):
        print('%d) %s' % (i, sustituir(paso)))
    print('')
    print('Notas: %s' % sustituir(voz['notas']))
    print('Al terminar, anota la voz usada en Voz/ajustes.txt.')


def main():
    voces = cargar()
    if len(sys.argv) == 3 and sys.argv[1] == '--video':
        voz_id = identidad_efectiva(resolver_video(sys.argv[2]))[0]['voz']
        if not voz_id:
            print('Ni el canal ni el video tienen voz definida. Usa: python herramientas/identidad.py canal|video "<destino>" --voz <id>')
            return 1
        comandos([v for v in voces if v['id'] == voz_id][0], sys.argv[2])
        return 0
    if len(sys.argv) == 1:
        listar(voces)
        return 0
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    elegida = [v for v in voces if v['id'] == sys.argv[1]]
    if not elegida:
        print('No existe la voz «%s». Disponibles: %s' % (sys.argv[1], ', '.join(v['id'] for v in voces)))
        return 1
    comandos(elegida[0], sys.argv[2])
    return 0


if __name__ == '__main__':
    sys.exit(main())
