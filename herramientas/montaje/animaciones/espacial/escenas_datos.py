"""
Escenas por datos (estilo espacial): cada fábrica recibe una entrada de escenas.json y devuelve fn(t) -> fotograma.

Tipos: cifra, comparacion, barras, linea_tiempo, lista, cita, mapa y la variante con marco de imagen. Sus parámetros están en
herramientas/montaje/catalogo/escenas.json (se ven con `python herramientas/montaje/catalogo/escenas.py <tipo>`).

Reglas de composición que cumplen todas: contenido en la zona segura (y ≈ 150–745), texto ajustado a su caja (si no cabe, baja de
tamaño), cajas con `ui.caja`, imágenes con esquinas redondeadas y borde suave, movimiento continuo y nada encima del rótulo de
abajo a la izquierda ni del crédito de arriba a la derecha (los pone la tubería a partir de `rotulo`, `fuente` y `credito`).
"""
import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import aa as trazo
import estilo
import globo
from montar import (AMBAR, BG, H, HUESO, W, blk, brillo, cargar, clamp, escena_imagen, lerp, mezcla, neg, pegar, punto, reg,
                    sprite_texto, ss)
from ui import HIELO, ROJO, VERDE, anillo_arco, caja, ease_out, etiqueta_esquema, icono_cta, icono_hex, sl, titulo as ui_titulo

CX, CY = W // 2, 470
GRIS = mezcla(BG, HUESO, 0.55)
COLORES = {'ambar': AMBAR, 'hielo': HIELO, 'verde': VERDE, 'rojo': ROJO, 'hueso': HUESO}
_cache = {}

# ----------------------------------------------------------------------------- utilidades


def color(c, defecto=AMBAR):
    if c is None:
        return defecto
    if isinstance(c, str):
        if c.lower() not in COLORES:
            raise ValueError('color «%s» desconocido (usa %s o [r, g, b])' % (c, ', '.join(COLORES)))
        return COLORES[c.lower()]
    return tuple(int(v) for v in c)


def num(v):
    """Número con formato español: 13797 -> «13 797», 73.04 -> «73,04». Un texto se deja tal cual."""
    if isinstance(v, str):
        return v
    s = ('%.10g' % v)
    ent, _, dec = s.partition('.')
    neg_ = ent.startswith('-')
    ent = ent.lstrip('-')
    if len(ent) > 3:
        ent = ' '.join([ent[max(0, i - 3):i] for i in range(len(ent), 0, -3)][::-1])
    return ('-' if neg_ else '') + ent + (',' + dec if dec else '')


def ajustar(texto, fab, tam, ancho, minimo=18):
    """Fuente de `fab(tam)` o la mayor menor que quepa en `ancho` px: el texto nunca se sale de su caja."""
    while tam > minimo and fab(tam).getlength(texto) > ancho:
        tam -= 2
    return fab(tam)


def partir(texto, fnt, ancho):
    """Divide el texto en líneas que caben en `ancho` px."""
    lineas, actual = [], ''
    for p in texto.split():
        prueba = (actual + ' ' + p).strip()
        if actual and fnt.getlength(prueba) > ancho:
            lineas.append(actual)
            actual = p
        else:
            actual = prueba
    if actual:
        lineas.append(actual)
    return lineas


def partir_ajustado(texto, fab, tam, ancho, max_lineas, minimo=20):
    """Baja el tamaño hasta que el texto quepa en `max_lineas` líneas. Devuelve (fuente, líneas)."""
    while True:
        f = fab(tam)
        ls = partir(texto, f, ancho)
        if len(ls) <= max_lineas or tam <= minimo:
            return f, ls
        tam -= 2


def tiempos(items, ini, fin, lead=0.8, tail=1.6):
    """Instante absoluto en que aparece cada elemento: el `t` (relativo a la escena) que traiga o un reparto parejo."""
    n = max(1, len(items))
    paso = max(0.5, (fin - ini - lead - tail) / n)
    return [ini + (it['t'] if isinstance(it, dict) and 't' in it else lead + i * paso) for i, it in enumerate(items)]


def entra(t, t0, d=0.7):
    return ease_out((t - t0) / d)


def texto(fr, s, fnt, c, x, y, a=1.0, ax='m', ay='m'):
    if a > 0.004:
        pegar(fr, sprite_texto(s, fnt, c), x, y, a, ax, ay)


def brillo_texto(fr, s, fnt, c, x, y, a=1.0, ax='m', ay='m'):
    if a > 0.004:
        estilo.txt_glow(fr, s, fnt, c, x, y, a, ax, ay)


def cabecera(fr, e, t0, t, y=96):
    """Título de la escena (con etiqueta pequeña si hay `eyebrow`), centrado arriba. Si no hay título, no dibuja nada."""
    tit = e.get('titulo')
    if not tit:
        return
    a = entra(t, t0, 0.8)
    f = ajustar(tit, neg, 46, 1000, 30)
    if e.get('eyebrow'):
        ui_titulo(fr, str(e['eyebrow']).upper(), tit, CX, y, a, 'm', f.size)
    else:
        texto(fr, tit, f, HUESO, CX, y + 30, a)


def ayuda(fr, e, t0, t, y=722):
    if e.get('ayuda'):
        f = ajustar(e['ayuda'], reg, 30, 1500, 20)
        texto(fr, e['ayuda'], f, GRIS, CX, y, entra(t, t0, 0.8))


def inicio(e):
    return e['ini'] + e.get('t', 0.4)


# ----------------------------------------------------------------------------- cifra


def cifra(e):
    ini, fin = e['ini'], e['fin']
    c = color(e.get('color'))
    valor = num(e['valor'])
    unidad, etiqueta, detalle = e.get('unidad', ''), e.get('etiqueta', ''), e.get('detalle', '')
    t0 = inicio(e)
    fv = ajustar(valor, blk, 260, 1560, 80)
    fu = ajustar(unidad, reg, 50, 1500, 24) if unidad else None
    fe = ajustar(etiqueta, neg, 42, 1500, 24) if etiqueta else None
    fd = ajustar(detalle, sl, 34, 1500, 22) if detalle else None
    y_val = CY - 30

    def fn(t):
        fr = estilo.base(t)
        cabecera(fr, e, ini + 0.2, t)
        if fe:
            texto(fr, etiqueta, fe, HUESO, CX, 250, entra(t, t0))
        pulso = 0.62 + 0.18 * math.sin((t - t0) * 2.2)
        brillo_texto(fr, valor, fv, c, CX, y_val, entra(t, t0 + 0.4, 0.9) * min(1.0, pulso + 0.38))
        if fu:
            texto(fr, unidad, fu, HUESO, CX, y_val + fv.size * 0.62 + 24, entra(t, t0 + 1.1))
        if fd:
            texto(fr, detalle, fd, GRIS, CX, y_val + fv.size * 0.62 + 86, entra(t, t0 + 1.8))
        ayuda(fr, e, t0 + 2.2, t)
        return fr
    return fn


# ----------------------------------------------------------------------------- comparación


def comparacion(e):
    ini, fin = e['ini'], e['fin']
    items = e['items']
    n = len(items)
    if n not in (2, 3):
        raise ValueError('«comparacion» pide 2 o 3 elementos en items (hay %d)' % n)
    ts = tiempos(items, ini, fin, 1.0, 1.8)
    w, sep = (700, 150) if n == 2 else (520, 60)
    x0 = CX - (n * w + (n - 1) * sep) // 2
    y0, h = 220, 400
    simbolo = e.get('separador', 'vs')

    def fn(t):
        fr = estilo.base(t)
        cabecera(fr, e, ini + 0.2, t)
        for i, it in enumerate(items):
            c = color(it.get('color'), (AMBAR, HIELO, VERDE)[i % 3])
            p = entra(t, ts[i], 0.8)
            if p <= 0.01:
                continue
            x = x0 + i * (w + sep)
            caja(fr, x, y0, w, h, c, 1.0, p, c=22, oscuro=0.6)
            tx = clamp((p - 0.35) / 0.55)
            if tx <= 0:
                continue
            cx = x + w // 2
            texto(fr, it['rotulo'], ajustar(it['rotulo'], neg, 36, w - 90, 22), c, cx, y0 + 56, tx)
            v = num(it['valor'])
            brillo_texto(fr, v, ajustar(v, blk, 130, w - 90, 40), HUESO, cx, y0 + 180, tx)
            if it.get('unidad'):
                texto(fr, it['unidad'], ajustar(it['unidad'], reg, 32, w - 90, 20), HUESO, cx, y0 + 280, tx)
            if it.get('detalle'):
                f, ls = partir_ajustado(it['detalle'], sl, 28, w - 90, 2, 20)
                for j, ln in enumerate(ls):
                    texto(fr, ln, f, GRIS, cx, y0 + 336 + j * 34, tx)
        if n == 2 and simbolo:
            texto(fr, simbolo, blk(46), GRIS, CX, y0 + h // 2, min(entra(t, ts[1], 0.8), 1.0) * 0.9)
        ayuda(fr, e, ts[-1] + 1.0, t)
        return fr
    return fn


# ----------------------------------------------------------------------------- barras


def barras(e):
    ini, fin = e['ini'], e['fin']
    items = e['items']
    n = len(items)
    if not 2 <= n <= 8:
        raise ValueError('«barras» pide de 2 a 8 elementos en items (hay %d)' % n)
    ts = tiempos(items, ini, fin, 1.0, 2.0)
    maximo = float(e.get('maximo') or max(float(it['valor']) for it in items))
    sufijo = e.get('sufijo', '')
    fila = min(84.0, 400.0 / n)
    y_top = max(190, int(CY - 30 - fila * n / 2))
    y_bot = int(y_top + fila * n)
    x_eje = 600
    ancho_v = max(neg(32).getlength(num(it['valor']) + (' ' + sufijo if sufijo else '')) for it in items)
    largo = int(max(300, min(860, W - 96 - x_eje - 3 - 18 - ancho_v - 6)))      # el texto del valor más largo cabe a la derecha de su barra
    alto = fila * 0.52

    def fn(t):
        fr = estilo.base(t)
        cabecera(fr, e, ini + 0.2, t)
        pe = entra(t, ini + 0.5, 0.8)
        trazo.linea(fr, [(x_eje, y_top - 10), (x_eje, y_top - 10 + (y_bot - y_top + 20) * pe)], GRIS, 2, 0.8, ss=3)
        for i, it in enumerate(items):
            c = color(it.get('color'), (AMBAR, HIELO, VERDE, ROJO)[i % 4])
            g = entra(t, ts[i], 1.1)
            if g <= 0.01:
                continue
            yc = y_top + fila * (i + 0.5)
            texto(fr, it['rotulo'], ajustar(it['rotulo'], neg, 30, x_eje - 96 - 34, 18), HUESO, x_eje - 24, yc, clamp(g * 2), 'r')
            L = max(2.0, largo * float(it['valor']) / maximo * g)
            trazo.rrect(fr, (x_eje + 3, yc - alto / 2, x_eje + 3 + L, yc + alto / 2), alto / 2, c, 2, 0.95, cache=False)
            trazo.rrect(fr, (x_eje + 3, yc - alto / 2, x_eje + 3 + L, yc + alto / 2), alto / 2, c, 1, 0.38, relleno=True, cache=False)
            texto(fr, num(it['valor']) + (' ' + sufijo if sufijo else ''), neg(32), c, x_eje + 3 + L + 18, yc, clamp((g - 0.4) * 2), 'l')
        pt = entra(t, ts[-1] + 0.8, 0.8)
        if pt > 0:
            texto(fr, '0', reg(24), GRIS, x_eje, y_bot + 24, pt)
            texto(fr, num(maximo), reg(24), GRIS, x_eje + largo, y_bot + 24, pt)
            if e.get('unidad'):
                texto(fr, e['unidad'], ajustar(e['unidad'], reg, 28, 1300, 18), GRIS, CX, y_bot + 62, pt)
        ayuda(fr, e, ts[-1] + 1.4, t, 732)
        return fr
    return fn


# ----------------------------------------------------------------------------- línea de tiempo


def linea_tiempo(e):
    ini, fin = e['ini'], e['fin']
    ev = e['eventos']
    n = len(ev)
    if not 2 <= n <= 7:
        raise ValueError('«linea_tiempo» pide de 2 a 7 eventos (hay %d)' % n)
    ts = tiempos(ev, ini, fin, 1.0, 1.8)
    x0, x1, y = 260, W - 260, 450
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)]
    sp = (x1 - x0) / (n - 1)
    ancho_max = int(min(2 * sp - 36, 440))
    etiqueta = e.get('con_etiqueta_escala', True)

    def fn(t):
        fr = estilo.base(t)
        cabecera(fr, e, ini + 0.2, t)
        revelado = [entra(t, ts[i], 0.7) for i in range(n)]
        # el trazo avanza con continuidad hasta el último hito visible
        hasta = x0
        for i in range(n):
            if revelado[i] > 0:
                hasta = lerp(xs[i - 1] if i else x0, xs[i], clamp(revelado[i] * 1.4)) if i else x0
        trazo.linea(fr, [(x0 - 30, y), (max(x0 - 30, hasta), y)], GRIS, 3, 0.9, ss=3)
        for i, it in enumerate(ev):
            p = revelado[i]
            if p <= 0.01:
                continue
            c = color(it.get('color'))
            x = xs[i]
            arriba = i % 2 == 0
            punto(fr, x, y, 11, c, p, 2.6)
            sentido = -1 if arriba else 1
            trazo.linea(fr, [(x, y + sentido * 18), (x, y + sentido * (18 + 34 * clamp(p * 1.5)))], c, 2, 0.8 * p, ss=3)
            ancho = int(min(ancho_max, 2 * (x - 96), 2 * (W - 96 - x)))          # la etiqueta no se sale de los márgenes
            f, ls = partir_ajustado(it['texto'], reg, 30, ancho, 3, 22)
            bloque = 44 + len(ls) * (f.size + 6)
            if arriba:
                yb = y - 60 - bloque
            else:
                yb = y + 60
            texto(fr, str(it['fecha']), ajustar(str(it['fecha']), blk, 40, ancho, 24), c, x, yb + 20, p)
            for j, ln in enumerate(ls):
                texto(fr, ln, f, HUESO, x, yb + 62 + j * (f.size + 6), p)
        if etiqueta:
            etiqueta_esquema(fr, 'ESQUEMA · SIN ESCALA', clamp((t - ini - 0.6) / 0.6))
        ayuda(fr, e, ts[-1] + 1.0, t)
        return fr
    return fn


# ----------------------------------------------------------------------------- lista por puntos


def lista(e):
    ini, fin = e['ini'], e['fin']
    puntos = [p if isinstance(p, dict) else {'texto': p} for p in e['puntos']]
    n = len(puntos)
    if not 2 <= n <= 6:
        raise ValueError('«lista» pide de 2 a 6 puntos (hay %d)' % n)
    ts = tiempos(puntos, ini, fin, 1.4, 1.6)
    numerada = e.get('numerada', True)
    f_it = [ajustar(p['texto'], neg, 38, 1180, 24) for p in puntos]
    ancho_txt = max(f.getlength(p['texto']) for f, p in zip(f_it, puntos))
    ancho = int(min(1560, max(ancho_txt + 330, 900)))
    dy = int(min(86, 470 / n))
    cab = 150 if (e.get('titulo') or e.get('eyebrow')) else 70
    alto = cab + n * dy + 40
    py = max(150, int(CY - alto / 2 - 20))
    px = (W - ancho) // 2

    def fn(t):
        fr = estilo.base(t)
        p = entra(t, ini + 0.2, 0.9)
        caja(fr, px, py, ancho, alto, AMBAR, 1.0, p, c=26, oscuro=0.58, blur=16)
        a = entra(t, ini + 0.7, 0.6) * clamp(p * 2)
        if e.get('titulo') or e.get('eyebrow'):
            f = ajustar(e.get('titulo', ''), neg, 44, ancho - 160, 26)
            ui_titulo(fr, str(e.get('eyebrow', 'EN ESTE VIDEO')).upper(), e.get('titulo', ''), px + 64, py + 34, a, 'l', f.size)
        x0 = px + 96
        y0 = py + cab + dy // 2
        for i, pt in enumerate(puntos):
            aa_ = entra(t, ts[i], 0.6)
            if aa_ <= 0.01:
                continue
            y = y0 + i * dy
            if i > 0:
                ya = y0 + (i - 1) * dy
                trazo.linea(fr, [(x0, ya + 28), (x0, ya + 28 + (dy - 56) * aa_)], AMBAR, 2, 0.6, ss=2)
            sig = ts[i + 1] if i + 1 < n else 1e9
            foco = ss((t - ts[i]) / 0.4) * (1 - ss((t - sig) / 0.5))
            if numerada:
                anillo_arco(fr, x0, y, 24, AMBAR, 1.0, aa_, 3, -90, 0.45)
                if foco > 0.02:
                    punto(fr, x0, y, 20 * foco, AMBAR, foco, 1.7)
                texto(fr, str(i + 1), neg(26), mezcla(AMBAR, BG, foco), x0, y, aa_)
            else:
                icono_hex(fr, x0, y, 20, AMBAR, aa_, 'check', 3)
            col = mezcla(mezcla(BG, HUESO, 0.72), HUESO, foco)
            texto(fr, pt['texto'], f_it[i], col, x0 + 52 + (1 - aa_) * 18, y, aa_, 'l')
        return fr
    return fn


# ----------------------------------------------------------------------------- imagen (con marco)


def _mascara_redondeada(w, h, radio, pluma):
    k = ('mk', w, h, radio, pluma)
    if k not in _cache:
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle((pluma, pluma, w - pluma, h - pluma), radio, fill=255)
        _cache[k] = m.filter(ImageFilter.GaussianBlur(pluma * 0.7))
    return _cache[k]


def _fondo_desenfocado(archivo):
    k = ('bg', archivo)
    if k not in _cache:
        im = cargar(archivo)
        s = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.BICUBIC)
        x0, y0 = (im.width - W) // 2, (im.height - H) // 2
        im = im.crop((x0, y0, x0 + W, y0 + H)).filter(ImageFilter.GaussianBlur(26))
        _cache[k] = Image.blend(im, Image.new('RGB', (W, H), BG), 0.9)
    return _cache[k]


def imagen_marco(e):
    ini, fin = e['ini'], e['fin']
    archivo = e['archivo']
    z0, z1 = float(e.get('zoom0', 1.0)), float(e.get('zoom1', 1.12))
    c0, c1 = e.get('centro0', [0.5, 0.5]), e.get('centro1', [0.5, 0.5])
    pie = e.get('pie', '')
    alto = 480
    cy = 440

    def fn(t):
        im = cargar_cache(archivo)
        fr = ImageChops.screen(_fondo_desenfocado(archivo), estilo.base(t))
        estilo.FONDO_ULT['bg'] = fr
        aspecto = im.width / im.height
        h = alto
        w = int(min(1560, h * aspecto))
        h = int(w / aspecto)
        u = ss((t - ini) / max(0.1, fin - ini))
        z = lerp(z0, z1, u)
        cx_, cy_ = lerp(c0[0], c1[0], u), lerp(c0[1], c1[1], u)
        bw, bh = im.width / z, im.height / z
        bx = clamp(cx_ * im.width - bw / 2, 0, im.width - bw)
        by = clamp(cy_ * im.height - bh / 2, 0, im.height - bh)
        recorte = im.resize((w, h), Image.BICUBIC, box=(bx, by, bx + bw, by + bh))
        a = entra(t, ini + 0.1, 0.9)
        mk = _mascara_redondeada(w, h, 36, 7)
        x0, y0 = CX - w // 2, cy - h // 2
        pegar(fr, brillo(int(max(w, h) * 0.55), HIELO), CX, cy, 0.10 * a, 'm', 'm')
        fr.paste(recorte, (x0, y0), mk.point(lambda q: int(q * a)) if a < 1 else mk)
        trazo.rrect(fr, (x0 + 7, y0 + 7, x0 + w - 7, y0 + h - 7), 36, HUESO, 1, 0.25 * a, cache=False)
        if pie:
            f = ajustar(pie, reg, 28, 1300, 18)
            ancho_p = int(f.getlength(pie)) + 80
            caja(fr, CX - ancho_p // 2, y0 + h + 22, ancho_p, 46, AMBAR, entra(t, ini + 0.8), 1.0, c=10, oscuro=0.62, barra=True)
            texto(fr, pie, f, HUESO, CX, y0 + h + 45, entra(t, ini + 1.0))
        return fr
    return fn


def cargar_cache(archivo):
    k = ('im', archivo)
    if k not in _cache:
        _cache[k] = cargar(archivo)
    return _cache[k]


def imagen_completa(e):
    ini, fin = e['ini'], e['fin']
    archivo = e['archivo']
    z0, z1 = float(e.get('zoom0', 1.0)), float(e.get('zoom1', 1.1))
    c0, c1 = e.get('centro0', [0.5, 0.5]), e.get('centro1', [0.5, 0.5])
    pie = e.get('pie', '')

    def fn(t):
        fr = escena_imagen(archivo, t, ini, fin, z0, z1, tuple(c0), tuple(c1), oscuro=0.15)
        if pie:
            f = ajustar(pie, reg, 28, 1300, 18)
            ancho_p = int(f.getlength(pie)) + 80
            caja(fr, CX - ancho_p // 2, 690, ancho_p, 46, AMBAR, entra(t, ini + 0.8), 1.0, c=10, oscuro=0.62, barra=True)
            texto(fr, pie, f, HUESO, CX, 713, entra(t, ini + 1.0))
        return fr
    return fn


# ----------------------------------------------------------------------------- cita


def cita(e):
    ini, fin = e['ini'], e['fin']
    c = color(e.get('color'))
    txt = e['texto'].strip()
    if not txt.startswith('«'):
        txt = '«' + txt + '»'
    f, ls = partir_ajustado(txt, blk, 60, 1180, 5, 34)
    lh = int(f.size * 1.28)
    autor = '— ' + e['autor']
    fa = ajustar(autor, neg, 38, 1100, 24)
    fs = ajustar(e.get('fuente', ''), sl, 28, 1100, 20) if e.get('fuente') else None
    h = 70 + len(ls) * lh + 40 + 56 + (44 if fs else 0) + 40
    h = min(h, 560)
    ancho = 1480
    x = CX - ancho // 2
    y = max(160, int(CY - h / 2) + (30 if e.get('titulo') else 0))
    t0 = inicio(e)

    def fn(t):
        fr = estilo.base(t)
        cabecera(fr, e, ini + 0.2, t)
        p = entra(t, t0, 0.9)
        caja(fr, x, y, ancho, h, c, 1.0, p, c=26, oscuro=0.6)
        tx = clamp((p - 0.35) / 0.55)
        if tx <= 0:
            return fr
        yy = y + 70 + lh // 2
        for i, ln in enumerate(ls):
            texto(fr, ln, f, HUESO, CX, yy + i * lh, entra(t, t0 + 0.6 + 0.35 * i, 0.6))
        ya = yy + len(ls) * lh + 20
        texto(fr, autor, fa, c, CX, ya + 20, entra(t, t0 + 0.8 + 0.35 * len(ls), 0.7))
        if fs:
            texto(fr, e['fuente'], fs, GRIS, CX, ya + 70, entra(t, t0 + 1.1 + 0.35 * len(ls), 0.7))
        return fr
    return fn


# ----------------------------------------------------------------------------- mapa / globo


def _giro_centrado(puntos):
    """Giro del globo (rad) con el que la mayor parte de los puntos mira al espectador."""
    mejor, fi_mejor = -1e9, 0.0
    for g in range(0, 360, 3):
        fi = math.radians(g)
        s = sum(max(0.0, float(globo.vec_estacion(p['lat'], p['lon'], fi)[2])) for p in puntos)
        if s > mejor:
            mejor, fi_mejor = s, fi
    return fi_mejor


def mapa(e):
    ini, fin = e['ini'], e['fin']
    puntos = e['puntos']
    n = len(puntos)
    if not 1 <= n <= 5:
        raise ValueError('«mapa» pide de 1 a 5 puntos (hay %d)' % n)
    ts = tiempos(puntos, ini, fin, 1.4, 1.6)
    giro = math.radians(float(e.get('giro', 4)))
    fi0 = _giro_centrado(puntos)
    cx, cy, R = 600, 455, 285
    x_l, w_l = 1090, 730
    dy = int(min(118, 470 / n))
    alto_c = dy - 18
    sin_titulo = not e.get('titulo')

    def fn(t):
        fr = estilo.base(t)
        cabecera(fr, e, ini + 0.2, t)
        fi = fi0 + giro * ((t - ini) - (fin - ini) / 2)
        ga = entra(t, ini + 0.2, 1.0)
        globo.dibujar_globo(fr, cx, cy, R, fi, ga)
        y0 = (CY - dy * n / 2 + 8) if n > 1 else CY - alto_c / 2
        for i, pt in enumerate(puntos):
            p = entra(t, ts[i], 0.8)
            v = globo.vec_estacion(pt['lat'], pt['lon'], fi)
            vis = clamp((float(v[2]) - 0.2) / 0.2) * clamp(p * 1.5)
            x, y = globo.punto_pantalla(cx, cy, R, float(v[0]), -float(v[1]))
            if vis > 0.02:
                trazo.elipse(fr, (x - 17, y - 17, x + 17, y + 17), AMBAR, 3, 0.95 * vis, glow=0.5, ss=3)
                texto(fr, str(i + 1), neg(20), HUESO, x, y, vis)
            if p > 0.01:
                yc = y0 + i * dy
                caja(fr, x_l, int(yc), w_l, alto_c, AMBAR, 1.0, p, c=14, oscuro=0.6)
                tx = clamp((p - 0.35) / 0.6)
                if tx > 0:
                    anillo_arco(fr, x_l + 52, yc + alto_c / 2, 22, AMBAR, 1.0, tx, 3, -90, 0.45)
                    texto(fr, str(i + 1), neg(22), AMBAR, x_l + 52, yc + alto_c / 2, tx)
                    f = ajustar(pt['nombre'], neg, 32, w_l - 130, 22)
                    if pt.get('detalle'):
                        texto(fr, pt['nombre'], f, HUESO, x_l + 96, yc + alto_c * 0.34, tx, 'l')
                        texto(fr, pt['detalle'], ajustar(pt['detalle'], sl, 25, w_l - 130, 18), GRIS, x_l + 96, yc + alto_c * 0.70, tx, 'l')
                    else:
                        texto(fr, pt['nombre'], f, HUESO, x_l + 96, yc + alto_c / 2, tx, 'l')
        return fr
    return fn


# ----------------------------------------------------------------------------- cierre


def cierre(e):
    ini, fin = e['ini'], e['fin']
    fuentes = list(e.get('fuentes') or [])[:8]
    tit = e.get('titulo') or ('Fuentes' if fuentes else 'Gracias por ver')
    ftit = ajustar(tit, blk, 72, 1500, 36)
    sub = e.get('subtitulo', '')
    msg = e.get('mensaje', 'Cada semana, una pregunta, con sus datos y de dónde salen')
    botones = (('campana', 'SUSCRÍBETE', True, 1.0), ('like', 'ME GUSTA', False, 2.6), ('campana', 'ACTIVA LA CAMPANITA', False, 4.0))
    anchos = [360, 300, 500]
    x_ini = CX - (sum(anchos) + 30 * (len(anchos) - 1)) // 2
    yb = 590 if fuentes else 540

    def fn(t):
        fr = estilo.base(t)
        if fuentes:
            ui_titulo(fr, 'REFERENCIAS', tit, CX, 60, entra(t, ini, 0.8), 'm', 46)
            for i, s in enumerate(fuentes):
                p = entra(t, ini + 0.8 + i * 0.25, 0.5)
                if p <= 0.01:
                    continue
                y = 190 + i * 44
                f = ajustar(s, neg, 22, 740, 16)
                caja(fr, 560, y, 800, 38, AMBAR, 1.0, p, c=9, oscuro=0.6, barra=False)
                tx = clamp((p - 0.3) / 0.6)
                icono_hex(fr, 590, y + 19, 7, AMBAR, tx, 'check', 2)
                texto(fr, s, f, HUESO, 614, y + 19, tx, 'l')
            texto(fr, 'Los enlaces están en la descripción', sl(26), GRIS, CX, yb - 30, entra(t, ini + 2.0, 0.8))
        else:
            texto(fr, tit, ftit, HUESO, CX, 280, entra(t, ini, 0.8))
            if sub:
                texto(fr, sub, ajustar(sub, reg, 40, 1500, 22), AMBAR, CX, 360, entra(t, ini + 0.8, 0.8))
        x = x_ini
        for (tipo, txt, prim, d), wd in zip(botones, anchos):
            a = entra(t, ini + d, 0.5)
            if a > 0.01:
                c = AMBAR if prim else HUESO
                caja(fr, x, yb, wd, 86, c, 1.0, a, c=16, oscuro=0.6, barra=False)
                icono_cta(fr, tipo, x + 46, yb + 43, 1.3, c, a)
                texto(fr, txt, blk(28), c, x + 82, yb + 43, a, 'l')
            x += wd + 30
        if msg:
            texto(fr, msg, ajustar(msg, reg, 30, 1500, 20), HUESO, CX, yb + 122, entra(t, ini + 1.0, 0.8))
        return fr
    return fn
