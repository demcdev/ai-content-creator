#!/usr/bin/env python3
"""
Alinea cada frase del guion con el audio real usando los silencios (programación dinámica) y escribe tiempos.json.

  python herramientas/montaje/alinear.py "Hace Eones/Video 03"
  python herramientas/montaje/alinear.py "Hace Eones/3" --ver 10          # además imprime las 10 primeras frases
  python herramientas/montaje/alinear.py "Hace Eones/3" --salida prueba.json

Entradas (dentro de la carpeta del video):
  Voz/*.wav                 el audio completo (si hay varios, el más grande)
  Texto para subtitulos.txt el texto mostrado; los párrafos se separan con una línea en blanco
Salida: Montaje/tiempos.json  {"total": s, "frases": [{"par", "texto", "ini", "fin"}]}

Cómo se pesa cada frase según la voz (se detecta sola):
  Polly   si existe Voz/polly/parte-NN.txt: el peso sale del texto realmente hablado (cifras en letras), emparejado
          1 a 1 con el texto mostrado, y las uniones de partes salen de las duraciones de parte-NN.mp3.
  Google  si no: el peso sale del texto mostrado con las sustituciones de herramientas/voz/sustituciones.json, y las
          uniones salen de Voz/partes/*.wav (si existe).
Ajustes opcionales en Montaje/montaje.json: "kmax" (frases por silencio, 3 por defecto) y
"correcciones": {"<número de frase>": [ini, fin]} para tramos donde dos frases seguidas no tienen silencio.
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
from _comun import resolver_video  # noqa: E402

RUIDO = '-38dB'
DURACION_MIN_SILENCIO = '0.25'
PAUSA_UNION = 0.6      # pausa que añade la herramienta de voz entre partes al unirlas


def silencios(audio):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', audio, '-af', 'silencedetect=noise=%s:d=%s' % (RUIDO, DURACION_MIN_SILENCIO), '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    ini = [float(x) for x in re.findall(r'silence_start: ([0-9.]+)', r)]
    fin = [float(x) for x in re.findall(r'silence_end: ([0-9.]+)', r)]
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r)
    total = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return list(zip(ini, fin[:len(ini)])), total


def dividir(texto, base=0):
    out = []
    for p, par in enumerate(texto.strip().split('\n\n')):
        for fr in re.split(r'(?<=[.?!])\s+(?=[A-ZÁÉÍÓÚ¿¡«])', par.strip()):
            out.append((base + p, fr.strip()))
    return out


def duracion(ruta):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', ruta], capture_output=True, text=True).stdout.strip())


def peso(texto, subs):
    for k, v in subs.items():
        if not k.startswith('_'):
            texto = texto.replace(k, v)
    w = 0.0
    for ch in texto:
        w += 2.6 if ch.isdigit() else (0.25 if not ch.isalnum() and ch != ' ' else (0.5 if ch == ' ' else 1.0))
    return w


class Entrada:
    """Audio, frases, textos para el peso y archivos de partes de un video."""

    def __init__(self, video):
        self.video = video
        voz = os.path.join(video, 'Voz')
        wavs = [os.path.join(voz, f) for f in os.listdir(voz) if f.lower().endswith('.wav')] if os.path.isdir(voz) else []
        if not wavs:
            sys.exit('No hay ningún .wav en %s' % voz)
        self.audio = max(wavs, key=os.path.getsize)
        texto = os.path.join(video, 'Texto para subtitulos.txt')
        if not os.path.exists(texto):
            sys.exit('Falta %s' % texto)
        self.mostrado = dividir(open(texto, encoding='utf8').read())
        self.polly = os.path.join(voz, 'polly')
        self.modo = 'polly' if os.path.exists(os.path.join(self.polly, 'parte-01.txt')) else 'google'
        if self.modo == 'polly':
            hablado = []
            for i in range(1, 99):
                ruta = os.path.join(self.polly, 'parte-%02d.txt' % i)
                if not os.path.exists(ruta):
                    break
                hablado += dividir(open(ruta, encoding='utf8').read(), 1000 * i)
            if len(self.mostrado) != len(hablado):
                sys.exit('El texto mostrado tiene %d frases y el hablado %d: no se pueden emparejar.' % (len(self.mostrado), len(hablado)))
            self.pesos = [peso(t, {}) for _, t in hablado]
        else:
            ruta = os.path.join(os.path.dirname(os.path.dirname(AQUI)), 'herramientas', 'voz', 'sustituciones.json')
            subs = json.load(open(ruta, encoding='utf8')) if os.path.exists(ruta) else {}
            self.pesos = [peso(t, subs) for _, t in self.mostrado]
        self.voz = voz

    def fronteras_partes(self, sil):
        """Índices de silencio que coinciden con la unión de las partes del audio (ahí siempre cae una frontera de frase)."""
        if self.modo == 'polly':
            carpeta = self.polly
            archivos = sorted(f for f in os.listdir(carpeta) if re.match(r'^parte-\d+\.mp3$', f))
        else:
            carpeta = os.path.join(self.voz, 'partes')
            if not os.path.isdir(carpeta):
                return []
            archivos = sorted(f for f in os.listdir(carpeta) if f.endswith('.wav'))
        acum, out = 0.0, []
        for f in archivos[:-1]:
            acum += duracion(os.path.join(carpeta, f))
            j = min(range(len(sil)), key=lambda q: abs(sil[q][0] - acum))
            out.append(j)
            acum += PAUSA_UNION
        return out


def alinear(entrada, kmax=3, correcciones=None):
    correcciones = correcciones or {}
    sil, total = silencios(entrada.audio)
    fr = entrada.mostrado
    N = len(fr)
    w = entrada.pesos
    forzadas = entrada.fronteras_partes(sil)
    fin_parrafo = [i + 1 < N and fr[i + 1][0] != fr[i][0] for i in range(N)]
    M = len(sil)
    habla = total - sum(b - a for a, b in sil)
    r = habla / sum(w)
    INF = 1e18

    def t_ini(a):
        return 0.0 if a < 0 else sil[a][1]

    def t_fin(b):
        return total if b >= M else sil[b][0]

    best = [[INF] * (M + 2) for _ in range(N + 1)]
    prev = [[None] * (M + 2) for _ in range(N + 1)]
    best[0][0] = 0.0                                  # j = a + 1 (a = -1 -> 0)
    for i in range(N):
        for j in range(M + 1):
            if best[i][j] >= INF:
                continue
            a = j - 1
            for k in range(1, kmax + 1):              # nº de frases que caben entre dos silencios
                if i + k > N:
                    break
                ws = sum(w[i:i + k])
                esp = ws * r
                for b in range(max(a + 1, 0), min(M, a + 12) + 1):
                    if i + k < N and b >= M:
                        continue
                    if i + k == N and b != M:
                        continue
                    if any(a < pf < b for pf in forzadas):
                        continue
                    d = t_fin(b) - t_ini(a)
                    if d <= 0.05:
                        continue
                    c = ((d / esp) - 1) ** 2 * ws + (k - 1) * 6.0
                    if b < M:
                        lon = sil[b][1] - sil[b][0]
                        c -= 3.0 * min(lon, 1.0)                              # una frase suele acabar en un silencio largo
                        if fin_parrafo[i + k - 1] and lon < 0.6:
                            c += 3.0                                          # y un cambio de párrafo, en uno de los largos
                    if best[i][j] + c < best[i + k][b + 1]:
                        best[i + k][b + 1] = best[i][j] + c
                        prev[i + k][b + 1] = (j, k)
    j = M + 1
    i = N
    trozos = []
    while i > 0:
        pj, k = prev[i][j]
        trozos.append((pj - 1, j - 1, i - k, i))
        j = pj
        i -= k
    trozos.reverse()
    cam = [None] * N
    for a, b, i0, i1 in trozos:
        t0, t1 = t_ini(a), t_fin(b)
        tot = sum(w[i0:i1])
        acc = 0.0
        for q in range(i0, i1):
            s = t0 + (t1 - t0) * acc / tot
            acc += w[q]
            e = t0 + (t1 - t0) * acc / tot
            cam[q] = (s, e)
    for q in range(N):
        if q in correcciones:
            cam[q] = tuple(correcciones[q])
    res = [{'par': p, 'texto': tx, 'ini': round(s, 3), 'fin': round(e, 3)} for (s, e), (p, tx) in zip(cam, fr)]
    return res, total, r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video')
    ap.add_argument('--salida', help='archivo de salida (por defecto Montaje/tiempos.json)')
    ap.add_argument('--ver', type=int, default=0, help='imprime las primeras N frases')
    a = ap.parse_args()
    video = resolver_video(a.video)
    cfg_ruta = os.path.join(video, 'Montaje', 'montaje.json')
    cfg = json.load(open(cfg_ruta, encoding='utf-8')) if os.path.exists(cfg_ruta) else {}
    corr = {int(k): v for k, v in cfg.get('correcciones', {}).items()}
    entrada = Entrada(video)
    res, total, r = alinear(entrada, cfg.get('kmax', 3), corr)
    salida = a.salida or os.path.join(video, 'Montaje', 'tiempos.json')
    os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
    json.dump({'total': total, 'frases': res}, open(salida, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print('voz %s · audio %s' % (entrada.modo, os.path.basename(entrada.audio)))
    print('total', round(total, 1), 's · frases', len(res), '· s/peso', round(r, 4), '->', salida)
    for f in res[:a.ver]:
        print('%7.2f–%7.2f  p%-2d %s' % (f['ini'], f['fin'], f['par'], f['texto'][:70]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
