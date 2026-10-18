"""
Validador global del proyecto: comprueba que nada se haya roto al renombrar, mover o editar archivos.
Solo biblioteca estándar; no gasta tokens. Configuración en herramientas/validacion/config.json.

  python herramientas/validacion/validar-proyecto.py                 # revisa todo el proyecto
  python herramientas/validacion/validar-proyecto.py --estricto      # los avisos también hacen fallar
  python herramientas/validacion/validar-proyecto.py --memoria       # incluye los .md de la memoria de Claude (avisos)
  python herramientas/validacion/validar-proyecto.py --vigilar       # se queda mirando y revalida a cada cambio o renombre
  python herramientas/validacion/validar-proyecto.py --hook          # modo hook de Claude Code (lee el JSON por stdin)
  python herramientas/validacion/validar-proyecto.py --instalar-git  # activa el pre-commit (.githooks/)

Qué revisa (ERROR = rompe algo; AVISO = conviene mirarlo):
  1. Enlaces markdown [texto](ruta): el destino existe (con mayúsculas exactas) y la ancla #título existe.
  2. Rutas entre comillas invertidas que empiezan por una carpeta del proyecto: existen. Otras rutas: AVISO.
  3. Comandos `python herramientas/...` y `node herramientas/...`: el script existe.
  4. Archivos .py: sintaxis correcta, rutas literales ('herramientas/...') que existen e imports locales que resuelven.
  5. Archivos .json: JSON válido.
  6. Rutas y nombres obsoletos (lista en config.json) y referencias a archivos que se acaban de renombrar o borrar (git).
  7. Convención de nombres (00-contexto/produccion/convencion-de-nombres.md): kebab-case, solo LEEME.md en la raíz de
     cada carpeta de contenido y carpetas por etapa en cada video. Todo esto son AVISOS.
Una línea con el texto «validar:ignorar» no se revisa (para citar a propósito un nombre antiguo).
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
# En un worktree de git (.claude/worktrees/<nombre>) los enlaces que salen del proyecto se resuelven contra la copia principal.
_WT = os.sep + os.path.join('.claude', 'worktrees') + os.sep
RAIZ_PRINCIPAL = RAIZ.split(_WT)[0] if _WT in RAIZ else RAIZ
MEMORIA = os.path.join(os.path.expanduser('~'), '.claude', 'projects', 'C--Users-USUARIO-Desktop-DemcDev-Proyectos-dev-Canal-de-youtube', 'memory')
CFG = json.load(open(os.path.join(AQUI, 'config.json'), encoding='utf-8'))
MARCA_IGNORAR = 'validar:ignorar'

ENLACE = re.compile(r'(?<!!)\[[^\]]*\]\((<[^>]+>|[^)\s]+)(?:\s+"[^"]*")?\)')
CODIGO = re.compile(r'`([^`\n]+)`')
CMD = re.compile(r'\b(?:python|node)\s+["\']?((?:herramientas|\.\.)[\w./\\-]*\.(?:py|mjs|js))')
RE_OBSOLETOS = [(re.compile(o['patron']), o['mensaje']) for o in CFG['obsoletos']]
EXCLUIR = set(CFG['excluir_carpetas'])
STD = set(getattr(sys, 'stdlib_module_names', ()))


class Resultado:
    def __init__(self):
        self.errores = []
        self.avisos = []

    def err(self, archivo, linea, texto):
        self.errores.append((archivo, linea, texto))

    def avi(self, archivo, linea, texto):
        self.avisos.append((archivo, linea, texto))


def rel(p):
    try:
        return os.path.relpath(p, RAIZ).replace('\\', '/')
    except ValueError:
        return p


def existe_exacto(ruta):
    """Existe y con las mayúsculas exactas (en Windows os.path.exists no distingue)."""
    ruta = os.path.abspath(ruta)
    if not os.path.exists(ruta):
        return False
    partes = ruta.split(os.sep)
    actual = partes[0] + os.sep
    for p in partes[1:]:
        try:
            if p not in os.listdir(actual):
                return False
        except OSError:
            return False
        actual = os.path.join(actual, p)
    return True


def recorrer(base=RAIZ):
    for d, dirs, fs in os.walk(base):
        dirs[:] = sorted(x for x in dirs if x not in EXCLUIR)
        r = rel(d)
        # la evidencia de licencias conserva sus nombres: solo se revisan su LEEME y su registro
        for f in sorted(fs):
            p = os.path.join(d, f)
            if '/05-licencias' in '/' + r and not r.endswith('05-licencias'):
                continue
            if rel(p) in CFG['excluir_archivos_de_validacion']:
                continue
            if '/05-licencias' in '/' + r and f not in ('LEEME.md', 'registro-de-licencias.md'):
                continue
            yield p


def leer(p):
    try:
        with open(p, encoding='utf-8') as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def slug_ancla(titulo):
    t = re.sub(r'`|\*|_', '', titulo.strip().lower())
    t = re.sub(r'[^\w\- ]', '', t, flags=re.UNICODE)
    return t.replace(' ', '-')


_anclas = {}


def anclas_de(p):
    if p not in _anclas:
        t = leer(p) or ''
        _anclas[p] = {slug_ancla(m.group(2)) for m in re.finditer(r'^(#{1,6})\s+(.*?)\s*#*\s*$', t, re.M)}
    return _anclas[p]


def lineas_de_texto(texto):
    """(n, linea, en_bloque_de_codigo) sin perder la numeración."""
    en = False
    for n, l in enumerate(texto.splitlines(), 1):
        if l.lstrip().startswith('```'):
            en = not en
            yield n, l, True
            continue
        yield n, l, en


# ------------------------------------------------------------------ resolución de rutas citadas
def candidatos(base_doc, token):
    """Lugares donde puede vivir una ruta citada en un documento (relativa al doc, a la raíz, al canal o al video)."""
    t = token.strip().rstrip('/\\').replace('\\\\', '/').replace('\\', '/')
    if t.startswith('./'):
        t = t[2:]
    lugares = [base_doc, RAIZ, os.path.join(RAIZ, 'herramientas'), os.path.join(RAIZ, 'herramientas', 'montaje')]
    # canal y video que contienen al documento
    partes = rel(base_doc).split('/')
    if len(partes) >= 3 and partes[0] == '02-canales':
        canal = os.path.join(RAIZ, partes[0], partes[1])
        lugares += [canal, os.path.join(canal, 'videos')]
        if len(partes) >= 4 and partes[2] == 'videos':
            lugares.append(os.path.join(canal, 'videos', partes[3]))
    else:
        for canal in _canales():
            lugares += [canal, os.path.join(canal, 'videos')]
            for v in _videos(canal):
                lugares.append(v)
    return [os.path.normpath(os.path.join(l, *t.split('/'))) for l in lugares]


_c = {}


def _canales():
    if 'c' not in _c:
        b = os.path.join(RAIZ, '02-canales')
        _c['c'] = [os.path.join(b, d) for d in sorted(os.listdir(b)) if os.path.isdir(os.path.join(b, d))] if os.path.isdir(b) else []
    return _c['c']


def _videos(canal):
    b = os.path.join(canal, 'videos')
    return [os.path.join(b, d) for d in sorted(os.listdir(b)) if os.path.isdir(os.path.join(b, d))] if os.path.isdir(b) else []


def es_plantilla(tok):
    return any(m in tok for m in CFG['marcadores_de_plantilla']) or ' ' in tok or tok.startswith(('http', '-', '@', '~', '/'))


def revisar_ruta_citada(res, archivo, n, doc_dir, tok, memoria=False):
    t = tok.strip()
    if es_plantilla(t) or not re.search(r'[/\\]', t) and '.' not in t:
        return
    base = t.replace('\\\\', '/').replace('\\', '/').strip('/')
    if any(s in base + '/' for s in CFG['ignorar_rutas_de_referencia']):
        return
    if re.match(r'\d\d-[a-z]', base) and '/videos/' not in '/' + rel(doc_dir) + '/':
        return                                  # carpeta de etapa citada en un documento general: es relativa a «un video»
    if os.path.splitext(base)[1].lower() in CFG['extensiones_medios_ignoradas']:
        return
    # una ruta sin barra (p. ej. `guion.md`) solo se valida si es un archivo que existe en alguna parte con ese nombre exacto
    primera = base.split('/')[0]
    if existe_alguno(doc_dir, base):
        return
    if '/' not in base:
        return                                  # nombre suelto: demasiado ambiguo para exigirlo
    if primera in CFG['raices_conocidas'] and not memoria:
        res.err(archivo, n, 'la ruta `%s` no existe' % tok)
    elif re.search(r'\.\w{1,5}$', base) or primera in ('videos', 'identidad', 'estrategia'):
        res.avi(archivo, n, 'la ruta `%s` no se encuentra' % tok)


def existe_alguno(doc_dir, base):
    return any(existe_exacto(c) for c in candidatos(doc_dir, base))


# ------------------------------------------------------------------ revisiones por tipo de archivo
def revisar_md(res, p, memoria=False):
    texto = leer(p)
    if texto is None:
        return
    archivo = rel(p) if not memoria else 'memoria/' + os.path.basename(p)
    d = os.path.dirname(p)
    sin_codigo = []
    for n, l, bloque in lineas_de_texto(texto):
        if MARCA_IGNORAR in l:
            continue
        if not bloque:
            for m in ENLACE.finditer(CODIGO.sub('', l)):
                u = m.group(1)
                crudo = u[1:-1] if u.startswith('<') else u
                if crudo.startswith(('http:', 'https:', 'mailto:', 'tel:')):
                    continue
                ruta, _, ancla = crudo.partition('#')
                ruta = ruta.replace('%20', ' ')
                if ruta == '':
                    destino = p
                else:
                    destino = os.path.normpath(os.path.join(d, ruta))
                    fuera = os.path.relpath(destino, RAIZ)
                    if fuera.startswith('..') and RAIZ_PRINCIPAL != RAIZ:
                        destino = os.path.normpath(os.path.join(RAIZ_PRINCIPAL, fuera))
                    if not existe_exacto(destino):
                        (res.avi if memoria else res.err)(archivo, n, 'enlace roto: %s' % crudo)
                        continue
                if ancla and os.path.isfile(destino) and destino.endswith('.md') and ancla.lower() not in anclas_de(destino):
                    res.avi(archivo, n, 'la ancla #%s no existe en %s' % (ancla, rel(destino)))
            for m in CODIGO.finditer(l):
                revisar_ruta_citada(res, archivo, n, d, m.group(1), memoria)
        for m in CMD.finditer(l):
            s = m.group(1).replace('\\\\', '/').replace('\\', '/')
            if '<' in s or '*' in s:
                continue
            if not any(existe_exacto(c) for c in (os.path.join(RAIZ, s), os.path.join(d, s))):
                (res.avi if memoria else res.err)(archivo, n, 'el comando apunta a un script que no existe: %s' % s)
        for rx, msg in RE_OBSOLETOS:
            if rx.search(l):
                res.avi(archivo, n, 'referencia obsoleta («%s»): %s' % (rx.search(l).group(0).strip()[:50], msg))
                break


def modulos_locales():
    nombres = set()
    for p in recorrer():
        if p.endswith('.py'):
            nombres.add(os.path.splitext(os.path.basename(p))[0])
    return nombres


def revisar_py(res, p, locales):
    texto = leer(p)
    if texto is None:
        return
    archivo = rel(p)
    try:
        arbol = ast.parse(texto, filename=p)
    except SyntaxError as e:
        res.err(archivo, e.lineno or 0, 'error de sintaxis: %s' % e.msg)
        return
    lineas = texto.splitlines()
    for nodo in ast.walk(arbol):
        n = getattr(nodo, 'lineno', 0)
        if n and n <= len(lineas) and MARCA_IGNORAR in lineas[n - 1]:
            continue
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            v = nodo.value
            if re.fullmatch(r'(?:herramientas|02-canales|00-contexto|01-nicho)/[\w./-]+', v) and not es_plantilla(v):
                if not existe_exacto(os.path.join(RAIZ, *v.split('/'))):
                    res.err(archivo, n, 'ruta literal inexistente: %s' % v)
        elif isinstance(nodo, (ast.Import, ast.ImportFrom)):
            nombres = [a.name for a in nodo.names] if isinstance(nodo, ast.Import) else ([nodo.module] if nodo.module and nodo.level == 0 else [])
            for nom in nombres:
                raiz = nom.split('.')[0]
                if raiz in STD or raiz in locales:
                    continue
                try:
                    import importlib.util
                    if importlib.util.find_spec(raiz) is not None:
                        continue
                except (ImportError, ValueError):
                    pass
                # los import dentro de try o de funciones opcionales no deben fallar el proyecto
                res.avi(archivo, n, 'módulo `%s` no encontrado (ni estándar, ni instalado, ni del proyecto)' % raiz)


def revisar_json(res, p):
    t = leer(p)
    if t is None:
        return
    try:
        json.loads(t)
    except ValueError as e:
        res.err(rel(p), 0, 'JSON inválido: %s' % e)


def revisar_obsoletos_codigo(res, p):
    texto = leer(p)
    if texto is None:
        return
    for n, l in enumerate(texto.splitlines(), 1):
        if MARCA_IGNORAR in l:
            continue
        for rx, msg in RE_OBSOLETOS:
            m = rx.search(l)
            if m:
                res.avi(rel(p), n, 'referencia obsoleta («%s»): %s' % (m.group(0).strip()[:50], msg))
                break


# ------------------------------------------------------------------ nombres y estructura
def kebab_ok(nombre):
    base = os.path.splitext(nombre)[0]
    return re.fullmatch(r'[a-z0-9]+(?:[-.][a-z0-9]+)*', base.lstrip('_')) is not None or (base.startswith('_') and re.fullmatch(r'_[a-z0-9_]+', base) is not None)


def py_ok(nombre):
    return re.fullmatch(r'_?[a-z0-9_]+(?:-[a-z0-9]+)*\.py', nombre) is not None


def revisar_nombres(res):
    libres = set(CFG['carpetas_con_nombres_libres'])
    for d, dirs, fs in os.walk(RAIZ):
        dirs[:] = sorted(x for x in dirs if x not in EXCLUIR and not x.startswith('.'))
        r = rel(d)
        partes = [] if r == '.' else r.split('/')
        if any(x in libres for x in partes):
            continue
        for x in dirs:
            if not kebab_ok(x) and not x.startswith('_'):
                res.avi(rel(os.path.join(d, x)), 0, 'nombre de carpeta fuera de la convención (minúsculas, sin tildes ni espacios, con guiones)')
        for f in fs:
            if f in CFG['nombres_permitidos'] or f.startswith('.'):
                continue
            if f.endswith('.py'):
                if not py_ok(f):
                    res.avi(rel(os.path.join(d, f)), 0, 'nombre de script fuera de la convención (kebab-case para programas, snake_case para módulos)')
            elif not kebab_ok(f):
                res.avi(rel(os.path.join(d, f)), 0, 'nombre de archivo fuera de la convención (minúsculas, sin tildes ni espacios, con guiones)')


def hijos_no_leeme(carpeta):
    if not os.path.isdir(carpeta):
        return []
    return sorted(f for f in os.listdir(carpeta)
                  if os.path.isfile(os.path.join(carpeta, f)) and f != 'LEEME.md' and not f.startswith('.') and f != '__pycache__')


def revisar_estructura(res):
    for sub in CFG['solo_leeme_en_la_raiz']:
        c = os.path.join(RAIZ, *sub.split('/'))
        for f in hijos_no_leeme(c):
            res.avi(rel(os.path.join(c, f)), 0, 'en la raíz de %s solo debe ir LEEME.md (mueve el archivo a una subcarpeta)' % sub)
    for canal in _canales():
        for sub in CFG['solo_leeme_en_cada_canal']:
            c = os.path.join(canal, *sub.split('/')) if sub else canal
            for f in hijos_no_leeme(c):
                res.avi(rel(os.path.join(c, f)), 0, 'en la raíz de %s solo debe ir LEEME.md' % rel(c))
        for v in _videos(canal):
            for f in hijos_no_leeme(v):
                res.avi(rel(os.path.join(v, f)), 0, 'en la raíz de un video solo debe ir LEEME.md')
            for carpeta in CFG['carpetas_obligatorias_de_video']:
                if not os.path.isdir(os.path.join(v, carpeta)):
                    res.avi(rel(v), 0, 'falta la carpeta de etapa %s/' % carpeta)
            if not os.path.isfile(os.path.join(v, '01-guion', 'guion.md')):
                res.avi(rel(v), 0, 'falta 01-guion/guion.md')


# ------------------------------------------------------------------ cambios de git (renombres y borrados)
def cambios_git():
    """Rutas que existían en HEAD y ya no están (renombradas o borradas): lista de rutas viejas."""
    try:
        s = subprocess.run(['git', '-c', 'core.quotepath=off', 'status', '--porcelain=v1', '-M'], cwd=RAIZ, capture_output=True, text=True, encoding='utf-8', timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    viejas = []
    for l in s.splitlines():
        est, ruta = l[:2], l[3:]
        if 'R' in est and ' -> ' in ruta:
            viejas.append(ruta.split(' -> ')[0].strip('"'))
        elif 'D' in est:
            viejas.append(ruta.strip('"'))
    return viejas


def revisar_renombres(res, textos):
    viejas = cambios_git()
    actuales = {os.path.basename(rel(p)) for p in recorrer()}
    for v in viejas:
        base = os.path.basename(v)
        genericos = {'LEEME.md', 'identidad.json', 'guion.md', 'montaje.json', 'tiempos.json', 'video.py', 'ajustes.txt'}
        claves = [v]
        if base not in genericos and base not in actuales and len(base) > 6:
            claves.append(base)
        for archivo, lineas in textos.items():
            for n, l in lineas:
                if MARCA_IGNORAR in l:
                    continue
                for k in claves:
                    if k in l:
                        res.err(archivo, n, 'sigue citando «%s», que se renombró o borró' % k)
                        break


# ------------------------------------------------------------------ principal
def validar(memoria=False):
    res = Resultado()
    locales = modulos_locales()
    textos = {}
    for p in recorrer():
        ext = os.path.splitext(p)[1].lower()
        if ext == '.md':
            revisar_md(res, p)
        elif ext == '.py':
            revisar_py(res, p, locales)
            revisar_obsoletos_codigo(res, p)
        elif ext == '.json':
            revisar_json(res, p)
        elif ext in ('.mjs', '.sh'):
            revisar_obsoletos_codigo(res, p)
        if ext in ('.md', '.py', '.json', '.mjs', '.sh'):
            t = leer(p)
            if t is not None:
                textos[rel(p)] = list(enumerate(t.splitlines(), 1))
    revisar_nombres(res)
    revisar_estructura(res)
    revisar_renombres(res, textos)
    if memoria and os.path.isdir(MEMORIA):
        for f in sorted(os.listdir(MEMORIA)):
            if f.endswith('.md'):
                revisar_md(res, os.path.join(MEMORIA, f), memoria=True)
    return res


def imprimir(res, estricto=False, salida=sys.stdout):
    def unico(lista):
        vistos, out = set(), []
        for x in lista:
            if x not in vistos:
                vistos.add(x)
                out.append(x)
        return out
    errores, avisos = unico(res.errores), unico(res.avisos)
    for etiqueta, lista in (('ERROR', errores), ('AVISO', avisos)):
        for archivo, n, txt in sorted(lista):
            print('[%s] %s%s  %s' % (etiqueta, archivo, (':%d' % n) if n else '', txt), file=salida)
    ok = not errores and not (estricto and avisos)
    print('%s · %d errores, %d avisos' % ('VALIDACIÓN OK' if ok else 'VALIDACIÓN FALLA', len(errores), len(avisos)), file=salida)
    return ok


def firma():
    """Huella barata del árbol: nombres, tamaños y fechas (detecta ediciones y renombres)."""
    h = []
    for d, dirs, fs in os.walk(RAIZ):
        dirs[:] = [x for x in dirs if x not in EXCLUIR]
        for f in fs:
            if f.endswith(('.md', '.py', '.json', '.mjs', '.sh')):
                p = os.path.join(d, f)
                try:
                    st = os.stat(p)
                    h.append((p, st.st_mtime_ns, st.st_size))
                except OSError:
                    pass
        for x in dirs:
            h.append((os.path.join(d, x), 0, 0))
    return hash(tuple(sorted(h)))


def vigilar(args):
    print('Vigilando %s (Ctrl+C para salir). Revalida a cada cambio o renombre.' % RAIZ)
    previa = None
    while True:
        actual = firma()
        if actual != previa:
            previa = actual
            print('\n[%s] cambio detectado, validando…' % time.strftime('%H:%M:%S'))
            imprimir(validar(args.memoria), args.estricto)
        time.sleep(2)


def modo_hook():
    """Hook de Claude Code (PostToolUse): valida si la herramienta tocó archivos del proyecto o movió/borró algo.
    Salida con código 2 y mensaje por stderr = Claude ve el problema y lo corrige."""
    try:
        datos = json.load(sys.stdin)
    except ValueError:
        return 0
    entrada = datos.get('tool_input') or {}
    herramienta = datos.get('tool_name', '')
    if herramienta in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        ruta = entrada.get('file_path', '')
        ext = os.path.splitext(ruta)[1].lower()
        if not ruta or ext not in ('.md', '.py', '.json', '.mjs', '.sh') or not os.path.abspath(ruta).startswith(RAIZ):
            return 0
    elif herramienta in ('Bash', 'PowerShell'):
        cmd = entrada.get('command', '')
        if not re.search(r'\b(mv|git\s+mv|git\s+rm|rm|Move-Item|Rename-Item|Remove-Item|move|ren|del|rmdir)\b', cmd):
            return 0
    else:
        return 0
    res = validar()
    if res.errores:
        imprimir(res, salida=sys.stderr)
        print('\nArregla las referencias rotas antes de seguir (herramientas/validacion/validar-proyecto.py).', file=sys.stderr)
        return 2
    return 0


def instalar_git():
    carpeta = os.path.join(RAIZ, '.githooks')
    os.makedirs(carpeta, exist_ok=True)
    gancho = os.path.join(carpeta, 'pre-commit')
    with open(gancho, 'w', encoding='utf-8', newline='\n') as f:
        f.write('#!/bin/sh\n# Valida referencias, enlaces y nombres antes de cada commit (herramientas/validacion/).\n'
                'cd "$(git rev-parse --show-toplevel)" || exit 1\n'
                'python herramientas/validacion/validar-proyecto.py || { echo "Commit cancelado: arregla lo anterior (o usa --no-verify bajo tu responsabilidad)."; exit 1; }\n')
    try:
        os.chmod(gancho, 0o755)
    except OSError:
        pass
    subprocess.run(['git', 'config', 'core.hooksPath', '.githooks'], cwd=RAIZ)
    print('Pre-commit instalado en .githooks/pre-commit y core.hooksPath configurado.')
    return 0


def main():
    ap = argparse.ArgumentParser(description='Valida enlaces, referencias, nombres y estructura del proyecto.')
    ap.add_argument('--estricto', action='store_true', help='los avisos también hacen fallar')
    ap.add_argument('--memoria', action='store_true', help='incluye los .md de la memoria de Claude (solo avisos)')
    ap.add_argument('--vigilar', action='store_true', help='revalida a cada cambio o renombre')
    ap.add_argument('--hook', action='store_true', help='modo hook de Claude Code (JSON por stdin)')
    ap.add_argument('--instalar-git', action='store_true', help='instala el hook pre-commit')
    ap.add_argument('--solo-errores', action='store_true', help='no imprime los avisos')
    args = ap.parse_args()
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    if args.hook:
        return modo_hook()
    if args.instalar_git:
        return instalar_git()
    if args.vigilar:
        try:
            vigilar(args)
        except KeyboardInterrupt:
            return 0
    res = validar(args.memoria)
    if args.solo_errores:
        res.avisos = []
    return 0 if imprimir(res, args.estricto) else 1


if __name__ == '__main__':
    sys.exit(main())
