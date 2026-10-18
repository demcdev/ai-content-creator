#!/usr/bin/env python3
"""
Prueba de generar-miniaturas.py en una copia temporal (no toca tus videos): validaciones, paletas, contraste, diversidad,
composiciones, motivos, medidas y zona libre.

  python herramientas/video/probar-generar-miniaturas.py                       # sale 0 si todo pasa
  python herramientas/video/probar-generar-miniaturas.py --guardar-muestras DIR   # además deja las miniaturas de ejemplo en DIR
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw  # noqa: E402

fallos = []


def comprobar(nombre, condicion, detalle=''):
    print(('OK    ' if condicion else 'FALLA ') + nombre + ('' if condicion else '  -> ' + str(detalle)[:400]))
    if not condicion:
        fallos.append(nombre)


def correr(tmp, *args):
    p = subprocess.run([sys.executable, os.path.join(tmp, 'herramientas', 'video', 'generar-miniaturas.py'), 'canal-prueba/1', *args],
                       cwd=tmp, capture_output=True, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    return p.returncode, (p.stdout + p.stderr).decode('utf-8', 'replace')


A = {'id': 'A', 'concepto': 'el objeto: el agujero negro y su anillo', 'texto': ['AGUJERO', 'NEGRO'],
     'paleta': {'fondo': '#0A0A0F', 'texto': '#FFF2DC', 'acento': '#FF8A1F'}, 'composicion': 'texto-izquierda',
     'motivo': {'tipo': 'anillo', 'tamano': 0.24, 'posicion': [0.76, 0.45]}, 'fondo': 'estrellas', 'fuente': 'montserrat', 'estilo_texto': 'brillo'}
B = {'id': 'B', 'concepto': 'la pregunta: ¿se puede fotografiar?', 'texto': ['¿LO VISTE?'],
     'paleta': {'fondo': '#F4EFE6', 'texto': '#14213D', 'acento': '#E4572E'}, 'composicion': 'centrado',
     'motivo': {'tipo': 'ondas', 'tamano': 0.34}, 'fondo': 'solido', 'fuente': 'inter', 'estilo_texto': 'plano'}
C = {'id': 'C', 'concepto': 'el dato: la distancia en años luz', 'texto': ['55 MILLONES', 'AÑOS LUZ'], 'subtexto': 'hasta M87',
     'paleta': {'fondo': '#0E2A47', 'texto': '#FFFFFF', 'acento': '#FFD23F'}, 'composicion': 'texto-abajo',
     'motivo': {'tipo': 'esfera', 'detalle': 'bandas', 'tamano': 0.26}, 'fondo': 'radial', 'fuente': 'space', 'estilo_texto': 'caja'}


def principal():
    for f in (sys.stdout, sys.stderr):
        f.reconfigure(encoding='utf-8', errors='replace')
    muestras = sys.argv[sys.argv.index('--guardar-muestras') + 1] if '--guardar-muestras' in sys.argv else None
    tmp = tempfile.mkdtemp(prefix='mp-')
    try:
        shutil.copytree(HERR, os.path.join(tmp, 'herramientas'), ignore=shutil.ignore_patterns('__pycache__', 'node_modules'))
        video = os.path.join(tmp, '02-canales', 'canal-prueba', 'videos', '01-prueba')
        for sub in ('07-miniaturas', '05-licencias/originales', 'identidad', '01-guion'):
            os.makedirs(os.path.join(video, *sub.split('/')))
        os.makedirs(os.path.join(tmp, '02-canales', 'canal-prueba', 'identidad'))
        with open(os.path.join(tmp, '02-canales', 'canal-prueba', 'identidad', 'identidad.json'), 'w', encoding='utf-8') as f:
            json.dump({'fuente': 'montserrat', 'colores': {'BG': [11, 16, 38], 'AMBAR': [242, 184, 75], 'HUESO': [245, 241, 232]}}, f)
        with open(os.path.join(video, 'identidad', 'identidad.json'), 'w', encoding='utf-8') as f:
            json.dump({'base': 'canal'}, f)
        foto = Image.new('RGB', (1600, 900), (20, 40, 90))
        ImageDraw.Draw(foto).ellipse((600, 250, 1100, 650), fill=(240, 160, 60))
        foto.save(os.path.join(video, '05-licencias', 'originales', 'agujero.jpg'))
        foto.save(os.path.join(video, '05-licencias', 'originales', 'sin-registro.jpg'))
        with open(os.path.join(video, '05-licencias', 'registro-de-licencias.md'), 'w', encoding='utf-8') as f:
            f.write('| Código | Material | Fuente | Licencia |\n|---|---|---|---|\n| L01 | agujero.jpg | ESO | CC BY 4.0 |\n')
        spec = os.path.join(video, '07-miniaturas', 'miniaturas.json')

        def escribir(variantes):
            with open(spec, 'w', encoding='utf-8') as f:
                json.dump({'variantes': variantes}, f, ensure_ascii=False)

        def cambia(base, **kw):
            v = copy.deepcopy(base)
            for k, val in kw.items():
                if k == 'paleta':
                    v['paleta'].update(val)
                else:
                    v[k] = val
            return v

        def invalido(nombre, variantes, esperado):
            escribir(variantes)
            c, s = correr(tmp, '--validar')
            comprobar('rechaza: ' + nombre, c == 1 and esperado.lower() in s.lower(), (c, s))

        c, s = correr(tmp)
        comprobar('sin miniaturas.json avisa y falla', c == 1 and 'no existe' in s.lower(), (c, s))
        invalido('más de 4 palabras', [cambia(A, texto=['UNO DOS TRES', 'CUATRO CINCO'])], '5 palabras')
        invalido('línea demasiado larga', [cambia(A, texto=['ABCDEFGHIJKLMNOPQRS'])], '18 letras')
        invalido('id con caracteres raros', [cambia(A, id='A/../B')], '«id»')
        invalido('id repetido', [A, cambia(B, id='A')], 'repetido')
        invalido('fondo desconocido', [cambia(A, fondo='neon')], '«fondo»')
        invalido('composición desconocida', [cambia(A, composicion='diagonal')], '«composicion»')
        invalido('motivo desconocido', [cambia(A, motivo={'tipo': 'dragon'})], '«motivo.tipo»')
        invalido('posición del motivo fuera de rango', [cambia(A, motivo={'tipo': 'anillo', 'posicion': [1.5, 0.2]})], '«motivo.posicion»')
        invalido('falta el concepto', [{k: v for k, v in A.items() if k != 'concepto'}], 'concepto')
        invalido('falta la paleta', [{k: v for k, v in A.items() if k != 'paleta'}], '«paleta»')
        invalido('color con formato malo', [cambia(A, paleta={'acento': 'naranja'})], '«paleta»')
        invalido('contraste del texto insuficiente (gris sobre gris)', [cambia(A, paleta={'fondo': '#777777', 'texto': '#888888'})], 'contraste')
        invalido('contraste insuficiente en estilo caja (acento sobre fondo)', [cambia(C, paleta={'acento': '#1F4E79'})], 'contraste')
        invalido('imagen fuera de originales', [cambia(A, imagen='../../../../herramientas/video/generar-miniaturas.py')], 'debe estar en')
        invalido('imagen que no figura en el registro de licencias', [cambia(A, imagen='05-licencias/originales/sin-registro.jpg')], 'no figura en')
        invalido('imagen inexistente', [cambia(A, imagen='05-licencias/originales/nada.jpg')], 'no existe')
        invalido('más de 6 variantes', [cambia(A, id=str(i), concepto='concepto %d' % i) for i in range(7)], '1 a 6')
        invalido('variantes demasiado parecidas', [A, cambia(A, id='A2', concepto='otra idea', texto=['OTRO', 'TEXTO'])], 'se parecen demasiado')
        invalido('conceptos repetidos', [A, cambia(B, concepto=A['concepto'])], 'conceptos repetidos')

        escribir([A, B, C])
        c, s = correr(tmp, '--validar')
        comprobar('acepta tres variantes distintas', c == 0 and '3 variante' in s, s)
        escribir([cambia(A, paleta={'texto': '#FF1010', 'acento': '#FF1010'}, fondo='solido')])
        c, s = correr(tmp, '--validar')
        comprobar('avisa del rojo sobre fondo muy oscuro', c in (0, 1) and ('daltonismo' in s.lower() or 'contraste' in s.lower()), s)

        t0 = time.time()
        escribir([A, B, C])
        c, s = correr(tmp, '--alto', '720')
        comprobar('dibuja las tres variantes (borrador 720)', c == 0 and s.count('OK miniatura-') == 3, s)
        salida = os.path.join(video, '07-miniaturas')
        medias = {}
        for vid in 'ABC':
            png = Image.open(os.path.join(salida, 'miniatura-%s.png' % vid.lower())).convert('RGB')
            chica = Image.open(os.path.join(salida, 'miniatura-%s-320x180.png' % vid.lower()))
            diminuta = Image.open(os.path.join(salida, 'miniatura-%s-160x90.png' % vid.lower()))
            comprobar('miniatura %s: 1280×720 (borrador), vistas 320×180 y 160×90' % vid, png.size == (1280, 720) and chica.size == (320, 180) and diminuta.size == (160, 90), (png.size, chica.size, diminuta.size))
            jpg = os.path.join(salida, 'miniatura-%s-movil.jpg' % vid.lower())
            comprobar('miniatura %s: el JPG para móvil existe y pesa menos de 2 MB' % vid, os.path.exists(jpg) and os.path.getsize(jpg) < 2_000_000)
            medias[vid] = tuple(sum(c) / (png.width * png.height) for c in zip(*png.resize((64, 36)).getdata())) if False else tuple(sum(ch) / 2304 for ch in zip(*png.resize((64, 36)).getdata()))
        comprobar('cada variante usa SU paleta: B (fondo crema) es mucho más clara que A y C', sum(medias['B']) > sum(medias['A']) + 250 and sum(medias['B']) > sum(medias['C']) + 200, medias)
        comprobar('A y C tienen fondos distintos (negro vs azul)', abs(medias['A'][2] - medias['C'][2]) > 20, medias)
        # zona libre: la esquina inferior derecha (15 % × 15 %) sin color de texto ni de caja
        def hay_color(vid, objetivo, tolerancia=40):
            im = Image.open(os.path.join(salida, 'miniatura-%s.png' % vid.lower())).convert('RGB')
            esq = im.crop((int(im.width * 0.85), int(im.height * 0.85), im.width, im.height))
            return sum(1 for p in esq.getdata() if all(abs(p[i] - objetivo[i]) < tolerancia for i in range(3)))
        comprobar('A deja libre la esquina inferior derecha (sin texto crema)', hay_color('A', (255, 242, 220)) == 0)
        comprobar('C deja libre la esquina inferior derecha (sin caja amarilla)', hay_color('C', (255, 210, 63)) == 0)
        comprobar('B deja libre la esquina inferior derecha (sin texto azul oscuro)', hay_color('B', (20, 33, 61), 25) == 0)
        # el texto se dibuja con el color de la paleta: A crema en la mitad izquierda; C sobre caja amarilla
        izq = Image.open(os.path.join(salida, 'miniatura-a.png')).convert('RGB').crop((0, 0, 640, 720))
        comprobar('A: hay texto crema a la izquierda', sum(1 for p in izq.getdata() if p[0] > 235 and p[1] > 225 and p[2] > 200) > 4000)
        caja = Image.open(os.path.join(salida, 'miniatura-c.png')).convert('RGB')
        comprobar('C: hay una caja amarilla bajo el texto', sum(1 for p in caja.getdata() if abs(p[0] - 255) < 6 and abs(p[1] - 210) < 8 and abs(p[2] - 63) < 10) > 20000)
        # salida informativa
        comprobar('imprime contraste, brillo, colorido y elementos por variante', 'contraste' in s and 'brillo' in s and 'colorido' in s and 'motivo:anillo' in s, s)

        # el motivo no tapa el texto: aviso si se solapan, y el texto se achica para dejarle sitio
        escribir([cambia(A, motivo={'tipo': 'anillo', 'tamano': 0.30, 'posicion': [0.50, 0.45]})])
        c, s = correr(tmp, '--alto', '360')
        comprobar('avisa cuando el motivo tapa el texto', 'tapa el' in s, s)
        escribir([cambia(A, texto=['AGUJERO', 'NEGRO'], motivo={'tipo': 'anillo', 'tamano': 0.24, 'posicion': [0.76, 0.45]})])
        c, s = correr(tmp, '--alto', '360')
        comprobar('sin choque no hay aviso de solape', c == 0 and 'tapa el' not in s, s)

        # imagen con licencia en las tres composiciones con imagen
        for comp in ('texto-izquierda', 'texto-derecha', 'centrado', 'texto-abajo'):
            escribir([cambia(B, composicion=comp, imagen='05-licencias/originales/agujero.jpg', motivo={'tipo': 'ninguno'}, texto=['AGUJERO'],
                              paleta={'fondo': '#0A1020', 'texto': '#FFFFFF', 'acento': '#FF8A1F'})])
            c, s = correr(tmp, '--alto', '540')
            comprobar('imagen con licencia en composición «%s»' % comp, c == 0 and 'OK miniatura-b' in s and 'imagen' in s, s)

        # cada motivo y cada fondo se dibuja
        for mot in ('anillo', 'esfera', 'orbitas', 'ondas', 'ninguno'):
            for fondo in ('estrellas', 'degradado', 'solido', 'radial'):
                escribir([cambia(A, motivo={'tipo': mot, 'tamano': 0.2, 'posicion': [0.80, 0.45]}, fondo=fondo)])
                c, s = correr(tmp, '--alto', '360')
                if c != 0:
                    comprobar('motivo %s con fondo %s' % (mot, fondo), False, s)
                    break
        comprobar('todos los motivos y fondos se dibujan', all(x != 'FALLA motivo' for x in fallos))

        # tamaño completo: 3840×2160
        escribir([A])
        t1 = time.time()
        c, s = correr(tmp)
        im4k = Image.open(os.path.join(salida, 'miniatura-a.png'))
        comprobar('tamaño completo 3840×2160', c == 0 and im4k.size == (3840, 2160), (c, im4k.size, s))
        jpg = os.path.join(salida, 'miniatura-a-movil.jpg')
        comprobar('el JPG móvil de la versión completa pesa menos de 2 MB', os.path.getsize(jpg) < 2_000_000, os.path.getsize(jpg))
        print('      (tiempo de una miniatura 4K: %.0f s)' % (time.time() - t1))
        comprobar('repetir es idempotente', correr(tmp, '--alto', '360')[0] == 0)

        if muestras:
            os.makedirs(muestras, exist_ok=True)
            escribir([A, B, C])
            correr(tmp, '--alto', '1080')
            for vid in 'ABC':
                shutil.copyfile(os.path.join(salida, 'miniatura-%s.png' % vid.lower()), os.path.join(muestras, 'muestra-%s.png' % vid))
                shutil.copyfile(os.path.join(salida, 'miniatura-%s-160x90.png' % vid.lower()), os.path.join(muestras, 'muestra-%s-160x90.png' % vid))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('\n%s' % ('TODO OK' if not fallos else 'FALLARON %d: %s' % (len(fallos), '; '.join(fallos))))
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(principal())
