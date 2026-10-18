"""
Escenas genéricas para un video nuevo. Cada fábrica devuelve una función fn(t) -> fotograma (Image 1920x1080).

Sirven para tener el video completo de punta a punta desde el primer día y reemplazarlas una a una por escenas
propias (con `Proyecto.registrar('E07', mi_funcion)`). Tipos que entiende `escenas.json`:

  placeholder  muestra el id, el nombre y la descripción de la escaleta (es el tipo por defecto)
  portada      titulo, subtitulo
  texto        lineas (lista de líneas grandes que aparecen una a una)
  imagen       archivo (en 05-licencias/originales/), zoom0, zoom1
  cierre       tarjeta de suscribirse, like y campanita
"""
import estilo
from montar import AMBAR, BG, H, HUESO, W, aparecer, blk, envolver, neg, pegar, reg, sprite_texto, ss, escena_imagen
from ui import cta

CX, CY = W // 2, 470


def _texto(fr, s, fnt, color, x, y, a=1.0, ax='m', ay='m'):
    if a > 0.004:
        pegar(fr, sprite_texto(s, fnt, color), x, y, a, ax, ay)


def placeholder(ini, fin, id_, nombre, descripcion=''):
    lineas = envolver(descripcion, 46)[:5] if descripcion else []

    def fn(t):
        fr = estilo.base(t)
        a = aparecer(t, ini, fin, 0.6)
        estilo.panel(fr, 220, 250, W - 220, 690, AMBAR, a)
        _texto(fr, '%s · %s' % (id_, nombre), blk(52), HUESO, CX, 330, a)
        for i, l in enumerate(lineas):
            _texto(fr, l, reg(32), HUESO, CX, 420 + 46 * i, a * 0.9)
        _texto(fr, 'Escena pendiente de diseñar', neg(24), AMBAR, CX, 650, a * 0.8)
        return fr
    return fn


def portada(ini, fin, titulo, subtitulo=''):
    def fn(t):
        fr = estilo.base(t)
        _texto(fr, titulo, blk(72), HUESO, CX, CY - 30, aparecer(t, ini, fin, 0.8))
        _texto(fr, subtitulo, reg(36), AMBAR, CX, CY + 60, aparecer(t, ini + 0.8, fin, 0.8))
        return fr
    return fn


def texto(ini, fin, lineas):
    lineas = list(lineas)
    paso = max(0.6, (fin - ini) / (len(lineas) + 1))

    def fn(t):
        fr = estilo.base(t)
        for i, l in enumerate(lineas):
            a = aparecer(t, ini + paso * i, fin, 0.7)
            _texto(fr, l, blk(64), AMBAR if i % 2 else HUESO, CX, 250 + 100 * i, a)
        return fr
    return fn


def imagen(ini, fin, archivo, zoom0=1.0, zoom1=1.1):
    def fn(t):
        return escena_imagen(archivo, t, ini, fin, zoom0, zoom1, (0.5, 0.5), (0.5, 0.5), oscuro=0.15)
    return fn


def cierre(ini, fin):
    def fn(t):
        fr = estilo.base(t)
        _texto(fr, 'Gracias por ver', blk(72), HUESO, CX, 300, aparecer(t, ini, fin, 0.8))
        cta(fr, t, ini + 1.0, fin)
        return fr
    return fn


def crear(esc):
    """Función de escena a partir de una entrada de escenas.json: {id, nombre, ini, fin, tipo, ...}."""
    ini, fin = esc['ini'], esc['fin']
    tipo = esc.get('tipo', 'placeholder')
    if tipo == 'portada':
        return portada(ini, fin, esc.get('titulo', esc['nombre']), esc.get('subtitulo', ''))
    if tipo == 'texto':
        return texto(ini, fin, esc.get('lineas', [esc['nombre']]))
    if tipo == 'imagen':
        return imagen(ini, fin, esc['archivo'], esc.get('zoom0', 1.0), esc.get('zoom1', 1.1))
    if tipo == 'cierre':
        return cierre(ini, fin)
    return placeholder(ini, fin, esc['id'], esc['nombre'], esc.get('descripcion', ''))
