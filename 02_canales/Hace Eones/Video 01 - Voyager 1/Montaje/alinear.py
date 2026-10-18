#!/usr/bin/env python3
"""Alinea cada frase del guion con el audio real usando los silencios (programación dinámica). Escribe tiempos.json."""
import json, os, re, subprocess, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); VIDEO = os.path.abspath(os.path.join(AQUI, '..')); RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
AUDIO = os.path.join(VIDEO, 'Voz', '01-Video-1-Voyager-1-guion.wav')
TEXTO = os.path.join(VIDEO, 'Texto para subtitulos.txt')
SUBS = json.load(open(os.path.abspath(os.path.join(AQUI, '..', '..', '..', '..', 'herramientas', 'voz', 'sustituciones.json')), encoding='utf8'))

def silencios():
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', AUDIO, '-af', 'silencedetect=noise=-38dB:d=0.25', '-f', 'null', '-'], capture_output=True, text=True).stderr
    ini = [float(x) for x in re.findall(r'silence_start: ([0-9.]+)', r)]
    fin = [float(x) for x in re.findall(r'silence_end: ([0-9.]+)', r)]
    dur = float(re.search(r'Duration: (\d+):(\d+):([\d.]+)', r).expand(r'\1:\2:\3').split(':')[0]) * 3600 if False else None
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r)
    total = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return list(zip(ini, fin[:len(ini)])), total

def frases():
    out = []
    for p, par in enumerate(open(TEXTO, encoding='utf8').read().strip().split('\n\n')):
        for fr in re.split(r'(?<=[.?!])\s+(?=[A-ZÁÉÍÓÚ¿¡«])', par.strip()):
            out.append((p, fr.strip()))
    return out

KMAX = 3  # 1 = cada frase entre dos silencios (respeta las pausas reales); más de 1 desordena el principio
# Tramos donde dos o tres frases seguidas no tienen silencio entre ellas (medido a mano con los silencios):
CORRECCIONES = {}

def fronteras_partes(sil):
    """Índices de silencio que coinciden con la unión de las partes del audio (ahí siempre cae una frontera de frase)."""
    carpeta = os.path.join(os.path.dirname(AUDIO), 'partes')
    if not os.path.isdir(carpeta): return []
    acum, out = 0.0, []
    archivos = sorted(f for f in os.listdir(carpeta) if f.endswith('.wav'))
    for k, f in enumerate(archivos[:-1]):
        d = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', os.path.join(carpeta, f)], capture_output=True, text=True).stdout.strip())
        acum += d
        j = min(range(len(sil)), key=lambda q: abs(sil[q][0] - acum))
        out.append(j); acum += 0.6
    return out

def peso(t):
    for k, v in SUBS.items():
        if not k.startswith('_'): t = t.replace(k, v)
    w = 0.0
    for ch in t:
        w += 2.6 if ch.isdigit() else (0.25 if not ch.isalnum() and ch != ' ' else (0.5 if ch == ' ' else 1.0))
    return w

def alinear():
    sil, total = silencios()
    # el primer silencio (inicio) y el último (final) delimitan el habla
    fr = frases(); N = len(fr); w = [peso(t) for _, t in fr]
    forzadas = fronteras_partes(sil)
    fin_parrafo = [i + 1 < N and fr[i + 1][0] != fr[i][0] for i in range(N)]
    M = len(sil)
    habla = total - sum(b - a for a, b in sil)
    r = habla / sum(w)
    INF = 1e18
    # candidatos: posiciones de frontera = índice de silencio (0..M-1); frase i va de fin(sil[a]) a inicio(sil[b])
    t_ini = lambda a: 0.0 if a < 0 else sil[a][1]
    t_fin = lambda b: total if b >= M else sil[b][0]
    best = [[INF] * (M + 2) for _ in range(N + 1)]; prev = [[None] * (M + 2) for _ in range(N + 1)]
    best[0][0] = 0.0  # j = a+1 (a=-1 → 0)
    for i in range(N):
        for j in range(M + 1):
            if best[i][j] >= INF: continue
            a = j - 1
            for k in range(1, KMAX + 1):             # nº de frases que caben entre dos silencios
                if i + k > N: break
                ws = sum(w[i:i + k]); esp = ws * r
                for b in range(max(a + 1, 0), min(M, a + 12) + 1):
                    if i + k < N and b >= M: continue
                    if i + k == N and b != M: continue
                    if any(a < pf < b for pf in forzadas): continue
                    d = t_fin(b) - t_ini(a)
                    if d <= 0.05: continue
                    c = ((d / esp) - 1) ** 2 * ws + (k - 1) * 6.0
                    if b < M:
                        lon = sil[b][1] - sil[b][0]
                        c -= 3.0 * min(lon, 1.0)                       # una frase suele acabar en un silencio largo
                        if fin_parrafo[i + k - 1] and lon < 0.6: c += 3.0   # y un cambio de párrafo, en uno de los largos
                    if best[i][j] + c < best[i + k][b + 1]:
                        best[i + k][b + 1] = best[i][j] + c; prev[i + k][b + 1] = (j, k)
    j = M + 1; i = N; trozos = []
    while i > 0:
        pj, k = prev[i][j]; trozos.append((pj - 1, j - 1, i - k, i)); j = pj; i -= k
    trozos.reverse()
    cam = [None] * N
    for a, b, i0, i1 in trozos:
        t0, t1 = t_ini(a), t_fin(b); tot = sum(w[i0:i1]); acc = 0.0
        for q in range(i0, i1):
            s = t0 + (t1 - t0) * acc / tot; acc += w[q]; e = t0 + (t1 - t0) * acc / tot
            cam[q] = (s, e)
    res = []
    for q, (s, e) in enumerate(cam):
        if q in CORRECCIONES: cam[q] = CORRECCIONES[q]
    for (s, e), (p, tx) in zip(cam, fr):
        res.append({'par': p, 'texto': tx, 'ini': round(s, 3), 'fin': round(e, 3)})
    return res, total, r

if __name__ == '__main__':
    res, total, r = alinear()
    json.dump({'total': total, 'frases': res}, open(os.path.join(AQUI, 'tiempos.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print('total', round(total, 1), 's · frases', len(res), '· s/peso', round(r, 4))
    for k in range(int(sys.argv[1]) if len(sys.argv) > 1 else 0):
        f = res[k]; print('%7.2f–%7.2f  p%-2d %s' % (f['ini'], f['fin'], f['par'], f['texto'][:70]))
