"""
Genera la voz de un video con Amazon Polly (motor Long-Form, voz Raul) a partir de las partes que crea `preparar-polly.mjs`.

Una vez por sesión de PowerShell (las claves son tuyas; nunca van en el chat ni en un archivo):
  $env:AWS_ACCESS_KEY_ID = "..."
  $env:AWS_SECRET_ACCESS_KEY = "..."
  $env:AWS_DEFAULT_REGION = "us-east-1"

1) Preparar el texto (sin red):
  node preparar-polly.mjs "..\\..\\02_canales\\<canal>\\Video NN - Nombre\\Guion.md" --salida "..\\..\\02_canales\\<canal>\\Video NN - Nombre\\Voz\\polly" --sustituciones-extra "..\\..\\02_canales\\<canal>\\Video NN - Nombre\\Voz\\sustituciones-video2.json"
2) Ver qué se enviaría y cuánto consume (sin red ni claves):
  python sintetizar-polly.py "..\\..\\02_canales\\<canal>\\Video NN - Nombre\\Voz\\polly" --solo-texto
3) Generar todo y unirlo:
  python sintetizar-polly.py "..\\..\\02_canales\\<canal>\\Video NN - Nombre\\Voz\\polly" --salida "..\\..\\02_canales\\<canal>\\Video NN - Nombre\\Voz\\voz-polly.wav"
4) Repetir solo una parte (después se vuelve a unir con todas):  --solo 3

Opciones: --ssml (usa parte-NN-ssml.txt), --voz Raul, --motor long-form, --pausa 0.6, --permitir-pago.
El script cuenta los caracteres del mes en `.uso-polly.json` y se detiene antes de pasar del nivel gratuito de Long-Form
(500 000 al mes, solo los primeros 12 meses desde que se creó la cuenta de AWS). Guarda `ajustes.txt` con lo usado.
"""
import importlib.util
import json
import os
import re
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
GRATIS_MENSUAL = 500_000
AVISO_MENSUAL = 400_000
LIMITE_PARTE = 3000          # caracteres facturables por petición en Polly
IDIOMA = 'es-ES'


class ErrorPolly(Exception):
    pass


def leer_partes(carpeta, ssml=False):
    patron = re.compile(r'^parte-(\d+)-ssml\.txt$' if ssml else r'^parte-(\d+)\.txt$')
    partes = {}
    for f in os.listdir(carpeta):
        m = patron.match(f)
        if m:
            with open(os.path.join(carpeta, f), encoding='utf-8') as fh:
                partes[int(m.group(1))] = fh.read().strip()
    if not partes:
        raise ErrorPolly('No hay archivos parte-NN%s.txt en %s. Ejecuta antes preparar-polly.mjs.' % ('-ssml' if ssml else '', carpeta))
    return dict(sorted(partes.items()))


def caracteres_facturables(texto):
    """Polly no factura las etiquetas SSML."""
    return len(re.sub(r'<[^>]+>', '', texto))


def mes_actual(ahora=None):
    t = ahora or time.localtime()
    return '%04d-%02d' % (t.tm_year, t.tm_mon)


def leer_uso(ruta):
    try:
        with open(ruta, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def sumar_uso(ruta, caracteres, mes=None):
    uso = leer_uso(ruta)
    mes = mes or mes_actual()
    uso[mes] = uso.get(mes, 0) + caracteres
    with open(ruta, 'w', encoding='utf-8') as fh:
        json.dump(uso, fh)
    return uso[mes]


def comprobar_cupo(usado, nuevos, permitir_pago=False, aviso=print):
    if usado + nuevos > GRATIS_MENSUAL and not permitir_pago:
        raise ErrorPolly('Con esto llevarías %d de %d caracteres gratuitos este mes. Para continuar pagando, usa --permitir-pago.' % (usado + nuevos, GRATIS_MENSUAL))
    if usado + nuevos > AVISO_MENSUAL:
        aviso('Aviso: con esto llevarías %d de %d caracteres gratuitos este mes.' % (usado + nuevos, GRATIS_MENSUAL))


def crear_cliente():
    try:
        import boto3
    except ImportError:
        raise ErrorPolly('Falta la librería boto3. Instálala con: pip install boto3')
    if not (os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY')):
        raise ErrorPolly('Faltan AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY en el entorno (ver las instrucciones al inicio del script).')
    return boto3.client('polly', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))


def sintetizar_parte(cliente, texto, voz, motor, ssml=False):
    r = cliente.synthesize_speech(Text=texto, TextType='ssml' if ssml else 'text', VoiceId=voz, Engine=motor, LanguageCode=IDIOMA, OutputFormat='mp3')
    return r['AudioStream'].read()


def cargar_unir():
    spec = importlib.util.spec_from_file_location('unir_partes', os.path.join(AQUI, 'unir-partes.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def leer_argumentos(argv):
    o = {'carpeta': '', 'salida': '', 'solo': 0, 'solo_texto': False, 'ssml': False, 'voz': 'Raul', 'motor': 'long-form', 'pausa': 0.6, 'permitir_pago': False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--salida':
            i += 1; o['salida'] = argv[i]
        elif a == '--solo':
            i += 1; o['solo'] = int(argv[i])
        elif a == '--solo-texto':
            o['solo_texto'] = True
        elif a == '--ssml':
            o['ssml'] = True
        elif a == '--voz':
            i += 1; o['voz'] = argv[i]
        elif a == '--motor':
            i += 1; o['motor'] = argv[i]
        elif a == '--pausa':
            i += 1; o['pausa'] = float(argv[i])
        elif a == '--permitir-pago':
            o['permitir_pago'] = True
        elif not o['carpeta']:
            o['carpeta'] = a
        else:
            raise ErrorPolly('Opción desconocida: ' + a)
        i += 1
    if not o['carpeta']:
        raise ErrorPolly('Falta la carpeta con las partes (Voz\\polly).')
    return o


def principal(argv, cliente=None, salida=print):
    o = leer_argumentos(argv)
    partes = leer_partes(o['carpeta'], o['ssml'])
    elegidas = {n: t for n, t in partes.items() if not o['solo'] or n == o['solo']}
    if not elegidas:
        raise ErrorPolly('No existe la parte %d.' % o['solo'])
    total = 0
    for n, t in elegidas.items():
        c = caracteres_facturables(t)
        if c > LIMITE_PARTE:
            raise ErrorPolly('La parte %d tiene %d caracteres (máximo %d). Vuelve a ejecutar preparar-polly.mjs.' % (n, c, LIMITE_PARTE))
        total += c
        salida('parte-%02d: %d caracteres' % (n, c))
    ruta_uso = os.path.join(AQUI, '.uso-polly.json')
    usado = leer_uso(ruta_uso).get(mes_actual(), 0)
    salida('Total a enviar: %d caracteres · uso del mes (según este script): %d de %d gratuitos' % (total, usado, GRATIS_MENSUAL))
    if o['solo_texto']:
        for n, t in elegidas.items():
            salida('\n[parte %02d]\n%s' % (n, t))
        return 0
    comprobar_cupo(usado, total, o['permitir_pago'], salida)
    cliente = cliente or crear_cliente()
    for n, t in elegidas.items():
        audio = sintetizar_parte(cliente, t, o['voz'], o['motor'], o['ssml'])
        with open(os.path.join(o['carpeta'], 'parte-%02d.mp3' % n), 'wb') as fh:
            fh.write(audio)
        sumar_uso(ruta_uso, caracteres_facturables(t))
        salida('Parte %02d lista' % n)
    with open(os.path.join(o['carpeta'], 'ajustes.txt'), 'w', encoding='utf-8') as fh:
        fh.write('Amazon Polly · motor %s · voz %s · idioma %s · formato mp3 · SSML: %s · generado: %s\n' % (o['motor'], o['voz'], IDIOMA, 'sí' if o['ssml'] else 'no', time.strftime('%Y-%m-%d %H:%M')))
    if o['salida']:
        if o['solo'] and len([f for f in os.listdir(o['carpeta']) if re.match(r'^parte-\d+\.mp3$', f)]) < len(partes):
            salida('Faltan partes por generar: no se une todavía.')
            return 0
        unir = cargar_unir()
        return unir.principal([o['carpeta'], o['salida'], '--pausa', str(o['pausa'])])
    return 0


if __name__ == '__main__':
    try:
        sys.exit(principal(sys.argv[1:]))
    except ErrorPolly as e:
        print('Error:', e)
        sys.exit(1)
