#!/usr/bin/env python3
"""
Respaldo de lo que git NO versiona (videos finales, voz, música con licencia) más el historial de git.

  python herramientas/respaldar.py                       # copia a ../Respaldos-canal
  python herramientas/respaldar.py --destino "D:/Respaldo" # otra carpeta (un disco o la carpeta sincronizada con Drive)
  python herramientas/respaldar.py --simular             # solo lista lo que copiaría

Qué copia: los archivos que .gitignore deja fuera, salvo renders intermedios y cachés (Montaje/salida,
cache*, __pycache__, Voz/partes, Voz/polly), que se regeneran. Es incremental: solo copia lo nuevo o
distinto (tamaño y fecha). Además deja repo.bundle (todo el historial de git en un archivo) y
MANIFIESTO.txt con el SHA-256 de cada archivo, que sirve de prueba de autoría (regla 6).
No borra nada del destino.
"""
import argparse
import datetime
import hashlib
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OMITIR = ('/Montaje/salida/', '/Montaje/cache', '/__pycache__/', '/Voz/partes/', '/Voz/polly/', '/.estado/')


def git(*args):
    r = subprocess.run(['git'] + list(args), cwd=RAIZ, capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        sys.exit('git falló: ' + r.stderr.strip())
    return r.stdout


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, 'rb') as f:
        for bloque in iter(lambda: f.read(1 << 20), b''):
            h.update(bloque)
    return h.hexdigest()


def archivos_a_copiar():
    salida = git('ls-files', '--others', '--ignored', '--exclude-standard', '-z')
    lista = []
    for rel in salida.split('\0'):
        if not rel:
            continue
        marca = '/' + rel.replace('\\', '/')
        if any(o in marca for o in OMITIR):
            continue
        lista.append(rel)
    return sorted(lista)


def principal():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--destino', default=os.path.join(os.path.dirname(RAIZ), 'Respaldos-canal'))
    ap.add_argument('--simular', action='store_true')
    a = ap.parse_args()
    destino = os.path.abspath(a.destino)
    if os.path.commonpath([destino, RAIZ]) == RAIZ:
        sys.exit('El destino no puede estar dentro del proyecto.')
    lista = archivos_a_copiar()
    copiados = omitidos = 0
    total = 0
    manifiesto = []
    for rel in lista:
        origen = os.path.join(RAIZ, rel)
        if not os.path.isfile(origen):
            continue
        dst = os.path.join(destino, 'medios', rel)
        tam = os.path.getsize(origen)
        total += tam
        igual = os.path.exists(dst) and os.path.getsize(dst) == tam and int(os.path.getmtime(dst)) >= int(os.path.getmtime(origen))
        if igual:
            omitidos += 1
        else:
            copiados += 1
            if a.simular:
                print('copiaría: %s (%.1f MB)' % (rel, tam / 1048576))
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(origen, dst)
        if not a.simular:
            manifiesto.append('%s  %s' % (sha256(dst if os.path.exists(dst) else origen), rel.replace('\\', '/')))
    if a.simular:
        print('Simulación: %d archivos nuevos o cambiados, %d ya están al día, %.0f MB en total.' % (copiados, omitidos, total / 1048576))
        return 0
    os.makedirs(destino, exist_ok=True)
    git('bundle', 'create', os.path.join(destino, 'repo.bundle'), '--all')
    with open(os.path.join(destino, 'MANIFIESTO.txt'), 'w', encoding='utf-8') as f:
        f.write('Respaldo del %s\nCommit: %s\n\n' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), git('rev-parse', 'HEAD').strip()))
        f.write('\n'.join(manifiesto) + '\n')
    print('Respaldo en %s: %d copiados, %d ya al día, %.0f MB. Historial en repo.bundle.' % (destino, copiados, omitidos, total / 1048576))
    return 0


if __name__ == '__main__':
    sys.exit(principal())
