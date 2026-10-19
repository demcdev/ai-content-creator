#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera los subagentes (y copia las skills) de cada herramienta de IA desde una sola fuente.

Fuente (se edita a mano):  .agents/subagents/<nombre>.md  y  .agents/skills/<skill>/SKILL.md
Generado (no se edita):    .claude/agents/<nombre>.md  .gemini/agents/<nombre>.md  .claude/skills/<skill>/

Uso, desde la raíz del proyecto:
  python herramientas/sync/sync-agentes.py            # genera lo que falte o haya cambiado
  python herramientas/sync/sync-agentes.py --seco     # dice qué cambiaría, sin escribir
  python herramientas/sync/sync-agentes.py --revisar  # solo comprueba; código 1 si algo está desactualizado (lo usa el pre-commit)

El formato de un subagente fuente está en herramientas/sync/LEEME.md.
"""
import argparse
import json
import os
import re
import shutil
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SUBAGENTES = os.path.join(RAIZ, '.agents', 'subagents')
SKILLS = os.path.join(RAIZ, '.agents', 'skills')
SKILLS_CLAUDE = os.path.join(RAIZ, '.claude', 'skills')
DESTINOS = {'claude': os.path.join(RAIZ, '.claude', 'agents'), 'gemini': os.path.join(RAIZ, '.gemini', 'agents')}

# nombre neutro -> (Claude Code, Gemini CLI). Los de Gemini están comprobados en geminicli.com/docs/reference/tools
HERRAMIENTAS = {
    'read': ('Read', 'read_file'),
    'search': ('Grep', 'grep_search'),
    'find': ('Glob', 'glob'),
    'shell': ('Bash', 'run_shell_command'),
    'write': ('Write', 'write_file'),
    'edit': ('Edit', 'replace'),
    'web_fetch': ('WebFetch', 'web_fetch'),
    'web_search': ('WebSearch', 'google_web_search'),
}


def leer_fuente(ruta):
    """Devuelve (datos, cuerpo, salto_de_linea). El cuerpo se copia tal cual a cada destino."""
    crudo = open(ruta, 'rb').read().decode('utf-8')
    # Siempre se genera con LF (como se guarda en git), sin importar cómo Windows haya dejado el archivo fuente al
    # clonar o cambiar de rama (autocrlf). Si no, un checkout con CRLF haría que los archivos generados parezcan distintos.
    nl = '\n'
    m = re.match(r'---\n(.*?)\n---\n(.*)\Z', crudo.replace('\r\n', '\n'), re.S)
    if not m:
        raise ValueError('debe empezar con un bloque --- ... ---')
    datos = {'claude': [], 'gemini': []}
    bloque = None
    for linea in m.group(1).split('\n'):
        if not linea.strip():
            continue
        if linea.startswith('  ') and bloque:
            datos[bloque].append(linea[2:])
            continue
        clave, _, valor = linea.partition(':')
        clave, valor = clave.strip(), valor.strip()
        if clave in ('claude', 'gemini') and not valor:
            bloque = clave
            continue
        bloque = None
        datos[clave] = valor
    for clave in ('name', 'description', 'tools'):
        if not datos.get(clave):
            raise ValueError('falta «%s» en el bloque inicial' % clave)
    datos['herr'] = [h.strip() for h in datos['tools'].split(',') if h.strip()]
    for h in datos['herr']:
        if h not in HERRAMIENTAS:
            raise ValueError('herramienta desconocida «%s» (válidas: %s)' % (h, ', '.join(HERRAMIENTAS)))
    return datos, m.group(2), nl


def generar_claude(d, cuerpo, nl):
    fm = ['name: ' + d['name'], 'description: ' + d['description'],
          'tools: ' + ', '.join(HERRAMIENTAS[h][0] for h in d['herr'])] + d['claude']
    return ('---\n' + '\n'.join(fm) + '\n---\n' + cuerpo).replace('\n', nl)


def generar_gemini(d, cuerpo, nl):
    fm = ['name: ' + d['name'], 'description: ' + json.dumps(d['description'], ensure_ascii=False), 'kind: local', 'tools:']
    fm += ['  - ' + HERRAMIENTAS[h][1] for h in d['herr']] + d['gemini']
    equiv = ', '.join('%s = `%s`' % (HERRAMIENTAS[h][0], HERRAMIENTAS[h][1]) for h in d['herr'])
    nota = '\n## Herramientas en Gemini CLI\nEste texto nombra las herramientas como en Claude Code. En Gemini CLI: %s.\n' % equiv
    return ('---\n' + '\n'.join(fm) + '\n---\n' + cuerpo.rstrip('\n') + '\n' + nota).replace('\n', nl)


GENERADORES = {'claude': generar_claude, 'gemini': generar_gemini}


def estado(ruta, contenido):
    if not os.path.exists(ruta):
        return 'nuevo'
    # Se comparan sin distinguir CRLF de LF: el archivo del disco puede haberlo convertido Windows al hacer checkout.
    actual = open(ruta, 'rb').read().replace(b'\r\n', b'\n')
    return 'igual' if actual == contenido.encode('utf-8') else 'distinto'


def archivos(base):
    for d, _, fs in os.walk(base):
        if '__pycache__' in d:
            continue
        for f in fs:
            yield os.path.relpath(os.path.join(d, f), base)


def plan_skills():
    """Copias de .agents/skills/ a .claude/skills/ (Claude Code solo lee la suya). Si es un enlace, ya está al día."""
    acciones = []
    if not os.path.isdir(SKILLS) or os.path.islink(SKILLS_CLAUDE):
        return acciones
    for nombre in sorted(os.listdir(SKILLS)):
        base = os.path.join(SKILLS, nombre)
        if not os.path.isfile(os.path.join(base, 'SKILL.md')):
            continue
        for rel in sorted(archivos(base)):
            origen, destino = os.path.join(base, rel), os.path.join(SKILLS_CLAUDE, nombre, rel)
            if not os.path.exists(destino):
                acciones.append(('nuevo', origen, destino))
            elif open(origen, 'rb').read() != open(destino, 'rb').read():
                acciones.append(('distinto', origen, destino))
    return acciones


def rel(p):
    return os.path.relpath(p, RAIZ).replace('\\', '/')


def main():
    ap = argparse.ArgumentParser(description='Genera los subagentes de Claude Code y Gemini CLI desde .agents/')
    ap.add_argument('--seco', action='store_true', help='dice qué cambiaría, sin escribir')
    ap.add_argument('--revisar', action='store_true', help='solo comprueba (código 1 si algo está desactualizado)')
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    if not os.path.isdir(SUBAGENTES):
        print('ERROR: no existe .agents/subagents/')
        return 1
    pendientes, errores, avisos = [], [], []
    fuentes = sorted(f for f in os.listdir(SUBAGENTES) if f.endswith('.md'))
    for f in fuentes:
        try:
            d, cuerpo, nl = leer_fuente(os.path.join(SUBAGENTES, f))
            if d['name'] + '.md' != f:
                raise ValueError('«name: %s» no coincide con el nombre del archivo' % d['name'])
        except ValueError as e:
            errores.append('%s: %s' % (rel(os.path.join(SUBAGENTES, f)), e))
            continue
        for destino, gen in GENERADORES.items():
            ruta = os.path.join(DESTINOS[destino], f)
            contenido = gen(d, cuerpo, nl)
            e = estado(ruta, contenido)
            if e != 'igual':
                pendientes.append((e, ruta, contenido))
    for destino, carpeta in DESTINOS.items():
        if os.path.isdir(carpeta):
            for f in sorted(os.listdir(carpeta)):
                if f.endswith('.md') and f not in fuentes:
                    avisos.append('%s no tiene fuente en .agents/subagents/ (no se toca)' % rel(os.path.join(carpeta, f)))
    skills = plan_skills()

    for e in errores:
        print('ERROR  ' + e)
    for av in avisos:
        print('AVISO  ' + av)
    for e, ruta, _ in pendientes:
        print('%-8s %s' % (e.upper(), rel(ruta)))
    for e, _, destino in skills:
        print('%-8s %s' % (e.upper(), rel(destino)))
    total = len(pendientes) + len(skills)
    if errores:
        print('ESTADO: ERROR (%d)' % len(errores))
        return 1
    if a.revisar:
        print('ESTADO: OK' if not total else 'ESTADO: DESACTUALIZADO (%d). Corre: python herramientas/sync/sync-agentes.py' % total)
        return 1 if total else 0
    if a.seco:
        print('ESTADO: SECO, no se escribió nada (%d cambios pendientes)' % total)
        return 0
    for _, ruta, contenido in pendientes:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        open(ruta, 'wb').write(contenido.encode('utf-8'))
    for _, origen, destino in skills:
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.copy2(origen, destino)
    print('ESTADO: OK (%d archivos escritos)' % total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
