"""
Une en un solo WAV los audios que descargaste de la consola de Amazon Polly (un archivo por parte).

  python unir-partes.py "..\\..\\02_canales\\Hace Eones\\Video 02 - Edad del universo\\Voz\\polly" "..\\..\\02_canales\\Hace Eones\\Video 02 - Edad del universo\\Voz\\video2-raul.wav"

- Toma los archivos .mp3 / .wav / .ogg de la carpeta, en orden alfabético (parte-01…, parte-02…; renómbralos así al descargar).
- Entre partes deja una pausa de 0,6 s (cámbiala con --pausa 0.8).
- Salida: WAV mono a 48 kHz, como espera el montaje. Necesita ffmpeg en el PATH.
No usa claves ni red.
"""
import os
import subprocess
import sys
import tempfile

EXT = ('.mp3', '.wav', '.ogg', '.m4a')


def principal(argv):
    pausa = 0.6
    if '--pausa' in argv:
        i = argv.index('--pausa')
        pausa = float(argv[i + 1])
        del argv[i:i + 2]
    if len(argv) != 2:
        print(__doc__)
        return 1
    carpeta, salida = argv
    archivos = sorted(f for f in os.listdir(carpeta) if f.lower().endswith(EXT) and not f.startswith('_'))
    if not archivos:
        print('No hay audios (.mp3/.wav/.ogg) en', carpeta)
        return 1
    print('Partes encontradas:')
    for f in archivos:
        print('  ', f)
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        silencio = os.path.join(tmp, 'silencio.wav')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono', '-t', str(pausa), silencio], check=True)
        normalizados = []
        for i, f in enumerate(archivos):
            destino = os.path.join(tmp, 'p%02d.wav' % i)
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', os.path.join(carpeta, f), '-ac', '1', '-ar', '48000', '-c:a', 'pcm_s16le', destino], check=True)
            normalizados.append(destino)
        lista = os.path.join(tmp, 'lista.txt')
        with open(lista, 'w', encoding='utf-8') as fh:
            for i, p in enumerate(normalizados):
                fh.write("file '%s'\n" % p.replace('\\', '/'))
                if i < len(normalizados) - 1:
                    fh.write("file '%s'\n" % silencio.replace('\\', '/'))
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lista, '-c:a', 'pcm_s16le', salida], check=True)
    dur = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', salida], capture_output=True, text=True).stdout.strip()
    print('Listo: %s · duración %.1f s (%.1f min)' % (salida, float(dur), float(dur) / 60))
    return 0


if __name__ == '__main__':
    sys.exit(principal(sys.argv[1:]))
