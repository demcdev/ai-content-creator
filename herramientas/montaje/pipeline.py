"""
Tubería de montaje para un video: escenas -> fotogramas -> mp4 con voz, música y subtítulos.

Es la parte común de video01.py y video02.py, sin sus escenas propias. Un video nuevo solo necesita un script
de 10 líneas (ver plantilla_video.py) y estos archivos en su carpeta Montaje/:

  tiempos.json   {"total": s, "frases": [{"texto", "ini", "fin"}]}   (lo deja alinear.py)
  escenas.json   lista de {id, nombre, ini, fin, tipo, ...}          (lo deja herramientas/escaleta-a-escenas.py)
  montaje.json   opcional: rotulos, creditos, capitulos, musica, cola, nombre, audio

Uso (desde Montaje/):  python video.py --frame 60 f.png | --verificar | --rango 0 300 parte.mp4 | --solo-audio | [n_partes]
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

import estilo
from montar import IDENT, FPS, H, NEGRO, W, aparecer, clamp, envolver, reg, sprite_texto, ss, trocear_texto, HUESO, neg
from ui import _contenido_rotulo, capitulo, credito, rotulo
import escenas_base

XF = 0.7   # fundido entre escenas, en segundos


def _cargar(ruta, defecto):
    return json.load(open(ruta, encoding='utf-8')) if os.path.exists(ruta) else defecto


class Proyecto:
    def __init__(self, script):
        self.aqui = os.path.dirname(os.path.abspath(script))
        self.video = os.path.dirname(self.aqui)
        self.salida = os.path.join(self.aqui, 'salida')
        t = _cargar(os.path.join(self.aqui, 'tiempos.json'), {'total': 0.0, 'frases': []})
        self.frases = t['frases']
        cfg = _cargar(os.path.join(self.aqui, 'montaje.json'), {})
        self.cola = cfg.get('cola', 2.0)
        self.duracion = t['total'] + self.cola
        self.nombre = cfg.get('nombre', 'video-completo')
        self.creditos = [tuple(c) for c in cfg.get('creditos', [])]
        self.capitulos = [tuple(c) for c in cfg.get('capitulos', [])]
        self.musica = cfg.get('musica', {'pistas': [], 'cambio': 0})
        self.audio = cfg.get('audio') or self._buscar_audio()
        self.rotulos = [r for r in (self._rotulo(r) for r in cfg.get('rotulos', [])) if r[1] > r[0]]
        self.subs_quemados = os.environ.get('HE_SUBS', '0') == '1'
        self.animacion = cfg.get('animacion') or IDENT['animacion']
        self._revisar_animacion()
        self.fondo = estilo.base
        esc = _cargar(os.path.join(self.aqui, 'escenas.json'), [])
        for i, e in enumerate(esc):
            if i == len(esc) - 1 and self.duracion:
                e['fin'] = max(e['fin'], self.duracion)
        self.escenas_def = esc
        self.propias = {}
        self._escenas = None
        self.subs = self._construir_subtitulos()

    # ------------------------------------------------------------------ datos
    def _revisar_animacion(self):
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'animaciones.json')
        catalogo = {a['id']: a for a in _cargar(ruta, {'animaciones': []})['animaciones']}
        if not self.animacion:
            return
        if self.animacion not in catalogo:
            sys.exit('La animación «%s» no está en animaciones.json. Disponibles: %s' % (self.animacion, ', '.join(catalogo)))
        estado = catalogo[self.animacion]['estado']
        if estado != 'disponible':
            print('Aviso: la animación «%s» está en estado «%s»: las escenas pendientes salen en estilo espacial; diseña las propias con registrar().' % (self.animacion, estado), file=sys.stderr)

    def _buscar_audio(self):
        carpeta = os.path.join(self.video, 'Voz')
        wavs = [os.path.join(carpeta, f) for f in os.listdir(carpeta) if f.lower().endswith('.wav')] if os.path.isdir(carpeta) else []
        return max(wavs, key=os.path.getsize) if wavs else ''

    def tiempo(self, prefijo, n=0):
        """Instante de inicio de la n-ésima frase que empieza por `prefijo`."""
        k = 0
        for f in self.frases:
            if f['texto'].startswith(prefijo):
                if k == n:
                    return f['ini']
                k += 1
        raise KeyError(prefijo)

    def _rotulo(self, r):
        """{frase|ini, desde, dur, l1, l2, estilo} -> (ini, fin, l1, l2, estilo)."""
        ini = self.tiempo(r['frase']) + r.get('desde', 0.3) if 'frase' in r else r['ini']
        fin = ini + r['dur'] if 'dur' in r else r['fin']
        return (ini, fin, r['l1'], r.get('l2', ''), r.get('estilo', 'dato'))

    def registrar(self, id_, fn):
        """Reemplaza la escena `id_` de escenas.json por una función propia fn(t) -> fotograma."""
        self.propias[id_] = fn
        self._escenas = None

    def escenas(self):
        if self._escenas is None:
            lista = []
            for e in self.escenas_def:
                fn = self.propias.get(e['id']) or escenas_base.crear(e)
                lista.append((e['ini'], e['fin'], (lambda f: (lambda t: estilo.bloom(f(t), 0.28)))(fn)))
            self._escenas = lista
        return self._escenas

    def _construir_subtitulos(self):
        subs = []
        for f in self.frases:
            partes = trocear_texto(f['texto'])
            total = sum(len(p) for p in partes) or 1
            t0 = f['ini']
            for p in partes:
                d = (f['fin'] - f['ini']) * len(p) / total
                subs.append((p, t0, t0 + d))
                t0 += d
        return subs

    # ------------------------------------------------------------ fotogramas
    def escena_sin_overlays(self, t):
        escenas = self.escenas()
        if not escenas:
            return estilo.base(t)
        capas = []
        n = len(escenas)
        for i, (a, b, fn) in enumerate(escenas):
            ini = a - XF / 2 if i else -1e9
            fin = b - XF / 2 if i < n - 1 else 1e9
            al = clamp((t - ini) / XF) if i else 1.0
            if i < n - 1:
                al *= 1 - clamp((t - fin) / XF)
            if al > 0:
                capas.append((al, fn))
        fr = capas[0][1](t)
        for al, fn in capas[1:]:
            fr = Image.blend(fr, fn(t), al) if al < 1 else fn(t)
        return fr

    def fotograma(self, t):
        fr = self.escena_sin_overlays(t)
        vis = [c for c in self.creditos if aparecer(t, c[0] + 0.4, c[1] - 0.2, 0.5) > 0]
        for k, (a, b, texto) in enumerate(vis):
            credito(fr, texto, aparecer(t, a + 0.4, b - 0.2, 0.5), k)
        for r in self.rotulos:
            rotulo(fr, t, *r)
        for ini_c, num_c, tit_c in self.capitulos:
            capitulo(fr, t, ini_c + 0.4, num_c, tit_c)
        if self.subs_quemados:
            self._dibujar_subtitulo(fr, t)
        k = clamp((t - (self.duracion - 1.2)) / 1.2)
        if k > 0:
            fr = Image.blend(fr, NEGRO, k)
        return fr

    def _dibujar_subtitulo(self, fr, t):
        from estilo import _mascara
        from montar import pegar
        for txt_, a, b in self.subs:
            if a - 0.05 <= t <= b + 0.15:
                sp = [sprite_texto(l, reg(42), HUESO) for l in envolver(txt_)]
                ancho = max(s[1].size[0] for s in sp) + 60
                alto = sum(s[1].size[1] for s in sp) + 22
                y0 = 1080 - 52 - alto
                fr.paste(Image.new('RGB', (ancho, alto), (4, 6, 16)), ((W - ancho) // 2, y0), _mascara(ancho, alto, 16).point(lambda v: int(v * 0.62)))
                y = y0 + 9
                for s in sp:
                    pegar(fr, s, W // 2, y, 1.0, 'm')
                    y += s[1].size[1]
                return

    def escribir_srt(self, ruta):
        def f(s):
            ms = int(round(s * 1000))
            return '{:02d}:{:02d}:{:02d},{:03d}'.format(ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)
        with open(ruta, 'w', encoding='utf-8') as fh:
            for i, (tx, a, b) in enumerate(self.subs, 1):
                fh.write('{}\n{} --> {}\n{}\n\n'.format(i, f(a), f(b), '\n'.join(envolver(tx))))

    # ------------------------------------------- regla «nada se tapa con nada»
    def _cajas_overlay(self, t):
        cajas = []
        for r in self.rotulos:
            ini, fin = r[0], r[1]
            dur = fin - ini
            din, dout = min(1.3, 0.22 * dur), min(1.0, 0.18 * dur)
            p = ss((t - ini) / din) * (1 - ss((t - (fin - dout)) / dout))
            if p > 0.35:
                w, h = _contenido_rotulo(r[2], r[3], r[4])[:2]
                cajas.append(('rótulo', (96, 912 - h, 96 + w, 912)))
        vis = [c for c in self.creditos if aparecer(t, c[0] + 0.4, c[1] - 0.2, 0.5) > 0.35]
        for k, (a, b, texto) in enumerate(vis):
            w = sprite_texto(texto, reg(21), HUESO)[1].size[0] + 110
            cajas.append(('crédito', (W - 96 - w, 40 + 32 * k, W - 96, 76 + 32 * k)))
        for ini_c, num_c, tit_c in self.capitulos:
            p = ss((t - (ini_c + 0.4)) / 0.9) * (1 - ss((t - (ini_c + 0.4 + 4.8 - 0.7)) / 0.7))
            if p > 0.35:
                w = int(max(130, sprite_texto(tit_c, neg(30), HUESO)[1].size[0]) + 118)
                cajas.append(('capítulo', (W - 96 - w, 124, W - 96, 216)))
        return cajas

    def verificar(self, paso=1.0, umbral=140):
        malos = []
        t = 1.0
        while t < self.duracion - 1:
            cajas = self._cajas_overlay(t)
            if cajas:
                esc = np.asarray(self.escena_sin_overlays(t), np.int16)
                bg = np.asarray(self.fondo(t), np.int16)
                tinta = np.abs(esc - bg).max(axis=2) > 70
                for nombre, (x0, y0, x1, y1) in cajas:
                    x0, y0, x1, y1 = max(0, int(x0) - 8), max(0, int(y0) - 8), min(W, int(x1) + 8), min(H, int(y1) + 8)
                    n = int(tinta[y0:y1, x0:x1].sum())
                    if n > umbral:
                        malos.append((round(t, 1), nombre, n, (x0, y0, x1, y1)))
            t += paso
        return malos

    # ------------------------------------------------------------------ render
    def render_rango(self, f0, f1, salida):
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '{}x{}'.format(W, H), '-r', str(FPS), '-i', '-',
               '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', '-threads', '2', '-g', '30', salida]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(f0, f1):
            p.stdin.write(np.asarray(self.fotograma(f / FPS)).tobytes())
            if (f - f0) % 600 == 0:
                print('  parte {}-{}: {:.0f} %'.format(f0, f1, 100.0 * (f - f0) / max(1, f1 - f0)), flush=True)
        p.stdin.close()
        p.wait()

    def preparar_voz(self):
        wav = os.path.join(self.salida, '_audio-completo.wav')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', self.audio, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,apad=pad_dur={}'.format(self.cola),
                        '-t', str(self.duracion), '-ac', '1', wav], check=True)
        return wav

    def mezclar_musica(self, wav):
        """Música bajo la voz (baja sola cuando se habla). Si faltan las pistas, deja solo la voz."""
        nombres = self.musica.get('pistas', [])
        carpeta = os.path.join(self.aqui, 'musica')
        pistas = []
        for n in nombres:
            hallado = [f for f in sorted(os.listdir(carpeta)) if f.lower().startswith(n.lower()) and f.lower().endswith(('.mp3', '.wav', '.m4a', '.aac'))] if os.path.isdir(carpeta) else []
            if hallado:
                pistas.append(os.path.join(carpeta, hallado[0]))
        if not nombres or len(pistas) < len(nombres) or len(pistas) > 2:
            print('Sin música (indica 1 o 2 pistas en montaje.json y guárdalas en {}): el video lleva solo la voz.'.format(carpeta))
            return wav
        d = self.duracion
        cambio = self.musica.get('cambio', d / 2)
        ent = ['-i', wav] + sum((['-i', x] for x in pistas), [])
        if len(pistas) == 1:
            cadena = '[1:a]aresample=48000,aloop=loop=-1:size=2e9,atrim=0:{d:.2f}[m12];'.format(d=d)
        else:
            cadena = '[1:a]aresample=48000,aloop=loop=-1:size=2e9,atrim=0:{a:.2f}[m1];'.format(a=cambio + 4)
            cadena += '[2:a]aresample=48000,aloop=loop=-1:size=2e9,atrim=0:{b:.2f}[m2];'.format(b=d - cambio + 4)
            cadena += '[m1][m2]acrossfade=d=4:c1=tri:c2=tri[m12];'
        cadena += '[m12]loudnorm=I=-24:TP=-3:LRA=7,atrim=0:{d:.2f},afade=t=in:d=3,afade=t=out:st={s:.2f}:d=4[mus];'.format(d=d, s=d - 4)
        cadena += '[0:a]aresample=48000,asplit=2[voz1][voz2];[mus][voz1]sidechaincompress=threshold=0.015:ratio=6:attack=30:release=600[duck];'
        cadena += '[duck][voz2]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-16:TP=-1.5:LRA=11[out]'
        salida = os.path.join(self.salida, '_audio-con-musica.wav')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + ent + ['-filter_complex', cadena, '-map', '[out]', '-ac', '2', salida], check=True)
        return salida

    def _unir(self, lista, wav, final):
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lista, '-i', wav, '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', final], check=True)

    def main(self, script):
        os.makedirs(self.salida, exist_ok=True)
        a = sys.argv[1:]
        if len(a) >= 3 and a[0] == '--frame':
            self.fotograma(float(a[1])).save(a[2])
            return
        tmp = os.path.join(self.salida, '_partes')
        if a and a[0] == '--verificar':
            malos = self.verificar(float(a[1]) if len(a) > 1 else 1.0)
            for m in malos:
                print('SOLAPE', m)
            print('total solapes:', len(malos))
            return
        if len(a) >= 4 and a[0] == '--rango':
            self.render_rango(int(a[1]), int(a[2]), a[3])
            return
        if not self.audio:
            raise SystemExit('No hay audio en Voz/ (o indica "audio" en montaje.json).')
        if IDENT['base'] not in ('canal', 'propia'):
            raise SystemExit('Falta elegir la identidad del video (la del canal o una propia): python herramientas/identidad.py video "<video>" --base canal|propia')
        if not self.animacion:
            raise SystemExit('Ni el canal ni el video tienen animación. Defínela con: python herramientas/identidad.py canal|video "<destino>" --animacion <id> (opciones: python herramientas/montaje/animaciones.py)')
        lista = os.path.join(tmp, 'lista.txt')
        final = os.path.join(self.salida, self.nombre + '.mp4')
        if a and a[0] == '--solo-audio':
            self._unir(lista, self.mezclar_musica(self.preparar_voz()), final)
            print('listo:', final)
            return
        total = int(self.duracion * FPS)
        partes = int(a[0]) if a else 4
        paso = -(-total // partes)
        os.makedirs(tmp, exist_ok=True)
        procs, archivos = [], []
        for k in range(partes):
            f0, f1 = k * paso, min(total, (k + 1) * paso)
            out = os.path.join(tmp, 'parte_{:02d}.mp4'.format(k))
            archivos.append(out)
            procs.append(subprocess.Popen([sys.executable, os.path.abspath(script), '--rango', str(f0), str(f1), out]))
        for p in procs:
            p.wait()
            if p.returncode:
                raise SystemExit('Falló una parte del render')
        open(lista, 'w', encoding='utf-8').write(''.join("file '{}'\n".format(x.replace(os.sep, '/')) for x in archivos))
        self._unir(lista, self.mezclar_musica(self.preparar_voz()), final)
        self.escribir_srt(os.path.join(self.salida, self.nombre + '.srt'))
        print('listo:', final)
