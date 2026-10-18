#!/usr/bin/env python3
"""
Lint gratis de un video (no usa IA, no gasta tokens). Se corre ANTES de llamar a un agente revisor.

  python herramientas/validar-video.py "hace-eones/2"            # etapa guion (por defecto)
  python herramientas/validar-video.py "hace-eones/2" --etapa montaje
  python herramientas/validar-video.py "hace-eones/2" --etapa final

La primera línea de la salida es siempre «ESTADO: PASA ...» o «ESTADO: FALLA ...».
Códigos de salida: 0 = sin errores (puede haber avisos), 1 = hay errores.
Los avisos son heurísticas que merecen mirada; los errores bloquean la etapa.
"""
import argparse
import sys
sys.dont_write_bytecode = True  # no dejar __pycache__ en la carpeta
import os
import re
import sys

from _comun import (ENTREGABLES, F_CAPITULOS, F_CIFRAS, F_ESCALETA, F_GUION, F_LICENCIAS, F_SUBTITULOS, MINIATURAS, VOZ, archivos,
                    consola, filas_datos, leer, resolver_video, resumen_licencias, ruta, sin_seccion, tamano)

MARCA_CIFRA = re.compile(r'\[✔[^\]]*\]')          # también [✔ 15; ✔ 25]
NUMEROS = re.compile(r'\d+')
PALABRAS_POR_MIN = 150

# (patrón, motivo). Heurística mínima: solo frases que casi siempre chocan con las reglas del proyecto.
RIESGO = [
    (r'hazte rico|dinero f[aá]cil|ganancias? garantizad|retorno garantizado|sin riesgo alguno|100 ?% seguro',
     'promesa de dinero o resultado garantizado (regla 13)'),
    (r'haz clic en (los|el) anuncio|dale clic a los anuncios|mira los anuncios para apoyar',
     'pedir clics o vistas en anuncios (reglas 13 y 22)'),
    (r'compra(r|n)? (vistas|suscriptores|seguidores)|comprar likes',
     'compra o incentivo de métricas (reglas 13 y 21)'),
    (r'decapita|desmembr|\bgore\b',
     'contenido gráfico: el contexto educativo debe ir dentro del video (regla 12)'),
    (r'\bsuicid|autolesi[oó]n',
     'tema sensible: revisar contexto y recursos (reglas 8 y 12)'),
]


def seccion(texto, titulo_regex, nivel='##'):
    """Texto de la sección cuyo encabezado coincide, hasta el siguiente encabezado del mismo nivel o superior."""
    patron = r'^%s\s+(?:%s)[^\n]*\n(.*?)(?=^#{1,%d}\s|\Z)' % (nivel, titulo_regex, len(nivel))
    m = re.search(patron, texto, re.S | re.M | re.I)
    return m.group(1) if m else None


def lineas_de_narracion(cuerpo):
    """Líneas que realmente se locutan: sin pantalla, encabezados, citas, tablas ni separadores."""
    for crudo in cuerpo.splitlines():
        s = crudo.strip()
        if not s or s.startswith(('[Pantalla', '#', '>', '|', '---', '- [', '<')):
            continue
        yield crudo


def limpiar_narracion(linea):
    t = MARCA_CIFRA.sub('', linea)
    t = re.sub(r'\{pausa[^}]*\}', '', t)
    t = re.sub(r'\[(c[aá]lculo propio|REVISAR)\]', '', t, flags=re.I)
    t = re.sub(r'\[[^\]]*\]', '', t)          # indicaciones entre corchetes
    t = re.sub(r'\([^)]*\.md[^)]*\)', '', t)  # enlaces
    t = t.replace('*', '')
    return t


def principal():
    consola()
    ap = argparse.ArgumentParser(description='Lint gratis de un video')
    ap.add_argument('video')
    ap.add_argument('--etapa', choices=['guion', 'montaje', 'final'], default='guion')
    a = ap.parse_args()

    carpeta = resolver_video(a.video)
    errores, avisos, info = [], [], []

    def err(m): errores.append(m)
    def avi(m): avisos.append(m)

    # ---- Guion -------------------------------------------------------------------------
    texto = leer(ruta(carpeta, F_GUION))
    if not texto or tamano(ruta(carpeta, F_GUION)) < 1500:
        err('01-guion/guion.md no existe o sigue siendo la plantilla vacía.')
        texto = texto or ''
    cuerpo = seccion(texto, 'Guion', '##') or ''
    if texto and not cuerpo:
        err('No encuentro la sección «## Guion» en guion.md.')

    # Palabras de narración y duración
    palabras = 0
    for linea in lineas_de_narracion(cuerpo):
        palabras += len(re.findall(r'\w+', limpiar_narracion(linea), re.U))
    minutos = palabras / PALABRAS_POR_MIN
    objetivo = re.search(r'Duraci[oó]n objetivo:?\**\s*\**\s*(\d+)\s*[–-]\s*(\d+)\s*min', texto[:4000]) if texto else None
    if objetivo:
        lo, hi = int(objetivo.group(1)), int(objetivo.group(2))
        info.append('narración: %d palabras ≈ %.1f min a %d ppm (objetivo %d–%d min)' % (palabras, minutos, PALABRAS_POR_MIN, lo, hi))
        if minutos < lo * 0.9 or minutos > hi * 1.1:
            fuera = minutos < lo * 0.75 or minutos > hi * 1.25
            (err if fuera else avi)('Duración estimada %.1f min, fuera del objetivo %d–%d min.' % (minutos, lo, hi))
    else:
        info.append('narración: %d palabras ≈ %.1f min a %d ppm (el guion no declara «Duración objetivo»)' % (palabras, minutos, PALABRAS_POR_MIN))
        if texto:
            avi('El encabezado del guion no declara «Duración objetivo: N–M min».')

    # Cifras [✔ n] contra la tabla de verificación
    citadas = {int(n) for marca in MARCA_CIFRA.findall(cuerpo) for n in NUMEROS.findall(marca)}
    verif = leer(ruta(carpeta, F_CIFRAS)) or ''
    filas = {}
    for linea in verif.splitlines():
        m = re.match(r'^\|\s*\**(\d+)\**\s*\|', linea)
        if m:
            celdas = [c.strip() for c in linea.strip().strip('|').split('|')]
            filas[int(m.group(1))] = celdas[-1] if celdas else ''
    info.append('cifras: %d citadas en el guion, %d filas en verificacion-de-cifras.md' % (len(citadas), len(filas)))
    for n in sorted(citadas - set(filas)):
        err('La cifra [✔ %d] del guion no tiene fila en verificacion-de-cifras.md.' % n)
    for n in sorted(citadas & set(filas)):
        estado = filas[n]
        if '❌' in estado:
            err('La cifra [✔ %d] está marcada ❌ en la verificación.' % n)
        elif '✅' not in estado:
            avi('La cifra [✔ %d] no está en ✅ (estado: «%s»).' % (n, estado[:40]))
    sin_uso = sorted(set(filas) - citadas)
    if sin_uso:
        info.append('filas de la tabla que el guion no cita: %s' % ', '.join(map(str, sin_uso)))

    # Marcas pendientes
    for i, linea in enumerate(cuerpo.splitlines(), 1):
        if re.search(r'\bREVISAR\b', linea) and not linea.lstrip().startswith(('>', '- [')):
            avi('[REVISAR] pendiente en el cuerpo del guion (comprobar el día de grabar): «%s…»' % linea.strip()[:60])

    # Secciones y cierre
    if texto:
        if not re.search(r'^##\s+Packaging', texto, re.M | re.I):
            avi('No hay sección «Packaging» (título, miniatura, descripción) antes del guion.')
        if not re.search(r'no sabemos', texto, re.I):
            avi('No aparece una sección de «Lo que no sabemos» (checklist del canal).')
        cierre = seccion(cuerpo, r'[^\n]*Cierre', '###')
        if cierre is None:
            avi('No encuentro una sección «Cierre» dentro del guion.')
        else:
            falta = [n for n, p in (('suscribirse', r'suscr'), ('like', r'\blike|me gusta'), ('campanita', r'campan')) if not re.search(p, cierre, re.I)]
            if falta:
                avi('El cierre no invita a: %s (regla de composición).' % ', '.join(falta))

    # Frases de riesgo para las políticas
    for i, linea in enumerate(texto.splitlines(), 1):
        if linea.lstrip().startswith(('>', '- [')):
            continue
        for patron, motivo in RIESGO:
            if re.search(patron, linea, re.I):
                avi('guion.md línea %d: %s → «%s…»' % (i, motivo, linea.strip()[:60]))

    # ---- Etapas posteriores -----------------------------------------------------------
    if a.etapa in ('montaje', 'final'):
        esc = leer(ruta(carpeta, F_ESCALETA))
        if not esc or filas_datos(sin_seccion(esc, 'Planilla de producción')) == 0:
            err('La escaleta audiovisual no tiene escenas.')
        if not archivos(ruta(carpeta, VOZ), ('.mp3', '.wav', '.m4a', '.ogg', '.flac')):
            err('No hay audio de voz en 04-voz/.')
        lic = resumen_licencias(leer(ruta(carpeta, F_LICENCIAS)))
        if lic is None:
            err('El registro-de-licencias.md no tiene la tabla «0. Resumen de estado».')
        else:
            f, listas, pend = lic
            info.append('licencias (resumen manual del registro): %d filas, %d listas, %d pendientes' % (f, listas, pend))
            if f == 0:
                err('El registro de licencias no tiene filas.')
            elif pend > 0:
                err('Licencias pendientes: %d de %d (regla 3: sin registro completo no entra al montaje).' % (pend, f))
    if a.etapa == 'final':
        if not archivos(ruta(carpeta, ENTREGABLES), ('.mp4',), recursivo=False):
            err('No hay video final (.mp4) en 08-entregables/.')
        if not archivos(ruta(carpeta, MINIATURAS), ('.png', '.jpg', '.jpeg', '.webp'), ignorar_guion_bajo=True):
            err('No hay miniaturas en 07-miniaturas/.')
        if tamano(ruta(carpeta, F_CAPITULOS)) < 800:
            avi('capitulos-y-descripcion.md parece vacío (plantilla).')
        if not (tamano(ruta(carpeta, F_SUBTITULOS)) > 200
                or archivos(ruta(carpeta, ENTREGABLES), ('.srt',), recursivo=False)):
            avi('No hay subtítulos (ni .txt ni .srt).')

    veredicto = 'FALLA' if errores else 'PASA'
    print('ESTADO: %s (%d errores, %d avisos) · etapa: %s' % (veredicto, len(errores), len(avisos), a.etapa))
    print('Video: ' + os.path.relpath(carpeta, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    for i in info:
        print('  · ' + i)
    for e in errores:
        print('[ERROR] ' + e)
    for v in avisos:
        print('[AVISO] ' + v)
    return 1 if errores else 0


if __name__ == '__main__':
    sys.exit(principal())
