"""
Ejecutor de pasos de IA del panel: lanza Claude Code sin pantalla (`claude -p`) para UN paso de UN video, con permisos
mínimos, y guarda lo que va pasando para mostrarlo en vivo, cancelarlo y dejar el historial en el propio video.

- Un solo trabajo a la vez (evita gasto doble y que dos sesiones se pisen los archivos).
- El texto y los permisos salen de pasos.json (nunca de la interfaz): la interfaz solo dice «paso + video».
- Permisos: --permission-mode dontAsk (lo que no está en la lista se niega, nadie tiene que aprobar) + lista cerrada
  por paso + sin servidores MCP + sin git. El texto de la página web que Claude lea no puede ampliar esos permisos.
- Historial: <video>/.estado/ejecuciones/<fecha>-<paso>.jsonl (la instrucción enviada y cada evento): prueba de
  producción propia (regla 6).
- El programa se busca en la variable CLAUDE_BIN o en el PATH; las pruebas usan uno falso con la misma salida.
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import threading
import time

MAX_EVENTOS = 2000
MAX_TEXTO = 700


def _corto(texto, n=MAX_TEXTO):
    texto = str(texto).strip()
    return texto if len(texto) <= n else texto[:n].rstrip() + '…'


def _sin_raiz(texto, raiz):
    """Quita la ruta del proyecto de un texto (y usa «/»): las rutas del registro se leen mejor relativas."""
    if not raiz:
        return texto
    return texto.replace('\\', '/').replace(raiz.replace('\\', '/').rstrip('/') + '/', '')


def _resumen_entrada(entrada, raiz=''):
    """Una línea legible de lo que hace una herramienta (ruta, comando, búsqueda…)."""
    if not isinstance(entrada, dict):
        return ''
    for clave in ('file_path', 'path', 'command', 'pattern', 'query', 'url', 'description'):
        if entrada.get(clave):
            return _corto(_sin_raiz(str(entrada[clave]), raiz), 200)
    return ''


def eventos_de(linea, raiz=''):
    """Convierte una línea de `--output-format stream-json` en eventos legibles: [{t, texto}]. Lo desconocido se ignora."""
    try:
        e = json.loads(linea)
    except ValueError:
        return []
    tipo = e.get('type')
    salida = []
    if tipo == 'assistant':
        for b in (e.get('message') or {}).get('content') or []:
            if b.get('type') == 'text' and (b.get('text') or '').strip():
                salida.append({'t': 'texto', 'texto': _corto(b['text'])})
            elif b.get('type') == 'tool_use':
                salida.append({'t': 'herramienta', 'texto': '%s %s' % (b.get('name', '?'), _resumen_entrada(b.get('input'), raiz))})
    elif tipo == 'user':
        contenido = (e.get('message') or {}).get('content')
        for b in contenido if isinstance(contenido, list) else []:
            if b.get('type') == 'tool_result' and b.get('is_error'):
                c = b.get('content')
                if isinstance(c, list):
                    c = ' '.join(x.get('text', '') for x in c if isinstance(x, dict))
                if 'has been denied' in str(c):      # los permisos negados se resumen al final: aquí sería ruido
                    continue
                salida.append({'t': 'aviso', 'texto': 'Falló: ' + _corto(c or '', 300)})
    elif tipo == 'result':
        for d in e.get('permission_denials') or []:
            salida.append({'t': 'aviso', 'texto': 'Permiso negado (no está en la lista del paso): %s %s' % (d.get('tool_name', '?'), _resumen_entrada(d.get('tool_input'), raiz))})
        salida.append({'t': 'fin', 'texto': _corto(e.get('result') or e.get('subtype') or '', 900),
                       'error': bool(e.get('is_error')), 'costo': e.get('total_cost_usd'), 'sesion': e.get('session_id')})
    return salida


def rellenar(plantilla, **valores):
    """Sustituye solo los marcadores conocidos ({ref}, {carpeta}…); el resto de llaves (como {pausa}) se queda igual."""
    for k, v in valores.items():
        plantilla = plantilla.replace('{%s}' % k, str(v))
    return plantilla


class Trabajo:
    def __init__(self, canal, video, paso, instruccion):
        self.id = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        self.canal, self.video, self.paso, self.instruccion = canal, video, paso, instruccion
        self.estado = 'corriendo'            # corriendo | terminado | error | cancelado
        self.inicio = time.time()
        self.fin = None
        self.eventos = []
        self.costo = None
        self.sesion = None
        self.motivo = ''
        self.cancelado = False
        self.proc = None
        self.registro = None

    def agregar(self, ev):
        if len(self.eventos) < MAX_EVENTOS:
            self.eventos.append(ev)

    def a_dict(self, desde=0):
        return {'id': self.id, 'estado': self.estado, 'canal': self.canal, 'video': self.video, 'paso': self.paso,
                'inicio': self.inicio, 'fin': self.fin, 'segundos': round((self.fin or time.time()) - self.inicio),
                'costo': self.costo, 'sesion': self.sesion, 'motivo': self.motivo,
                'n': len(self.eventos), 'eventos': self.eventos[desde:],
                'registro': self.registro}


class Ejecutor:
    def __init__(self, raiz, secretos=lambda: ()):
        self.raiz = raiz
        self.secretos = secretos          # nombres de variables de entorno con claves: Claude Code nunca las recibe
        self.actual = None
        self.cerrojo = threading.Lock()

    @staticmethod
    def programa():
        return os.environ.get('CLAUDE_BIN') or shutil.which('claude')

    def ocupado(self):
        return self.actual is not None and self.actual.estado == 'corriendo'

    def iniciar(self, carpeta_video, canal, paso, instruccion, cfg):
        """cfg = el bloque «ejecutable» de pasos.json. Lanza el proceso y devuelve el Trabajo (o lanza ValueError con el motivo)."""
        exe = self.programa()
        if not exe:
            raise ValueError('No encuentro Claude Code (comando «claude»). Instálalo o define CLAUDE_BIN.')
        video = os.path.basename(carpeta_video)
        permitidas = [p.replace('{canal}', canal).replace('{video}', video) for p in cfg.get('permitidas', [])]
        cmd = [exe, '-p', '--output-format', 'stream-json', '--verbose', '--permission-mode', 'dontAsk',
               '--strict-mcp-config', '--model', cfg.get('modelo', 'sonnet')]
        if cfg.get('prohibidas'):
            cmd += ['--disallowedTools', *cfg['prohibidas']]
        if permitidas:
            cmd += ['--allowedTools', *permitidas]       # variadico: va al final
        with self.cerrojo:
            if self.ocupado():
                raise ValueError('Ya hay un paso ejecutándose (%s · %s). Espera a que termine o cancélalo.' % (self.actual.video, self.actual.paso))
            t = Trabajo(canal, video, paso, instruccion)
            carpeta_reg = os.path.join(carpeta_video, '.estado', 'ejecuciones')
            os.makedirs(carpeta_reg, exist_ok=True)
            t.registro = os.path.relpath(os.path.join(carpeta_reg, '%s-%s.jsonl' % (t.id, paso)), self.raiz).replace('\\', '/')
            ocultas = set(self.secretos()) | {'CLAUDECODE'}
            entorno = {k: v for k, v in os.environ.items() if k not in ocultas}
            entorno['PYTHONIOENCODING'] = 'utf-8'
            banderas = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            try:
                t.proc = subprocess.Popen(cmd, cwd=self.raiz, env=entorno, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, creationflags=banderas)
            except OSError as e:
                raise ValueError('No pude lanzar Claude Code: %s' % e)
            self.actual = t
        with open(os.path.join(self.raiz, *t.registro.split('/')), 'w', encoding='utf-8') as f:
            f.write(json.dumps({'inicio': t.id, 'paso': paso, 'video': video, 'modelo': cfg.get('modelo'), 'permitidas': permitidas,
                                'prohibidas': cfg.get('prohibidas', []), 'instruccion': instruccion}, ensure_ascii=False) + '\n')
        try:
            t.proc.stdin.write(instruccion.encode('utf-8'))
            t.proc.stdin.close()
        except OSError:
            pass
        threading.Thread(target=self._leer, args=(t,), daemon=True).start()
        threading.Thread(target=self._esperar_tope, args=(t, int(cfg.get('minutos', 20)) * 60), daemon=True).start()
        return t

    def iniciar_comandos(self, carpeta_video, canal, paso, comandos, minutos):
        """Ejecuta, uno tras otro y SIN IA, programas del proyecto. comandos = [(texto_para_mostrar, argv)]; el servidor ya
        validó que sean `python`/`node` de herramientas/. Se detiene en el primero que falle."""
        with self.cerrojo:
            if self.ocupado():
                raise ValueError('Ya hay un paso ejecutándose (%s · %s). Espera a que termine o cancélalo.' % (self.actual.video, self.actual.paso))
            t = Trabajo(canal, os.path.basename(carpeta_video), paso, '\n'.join(c[0] for c in comandos))
            carpeta_reg = os.path.join(carpeta_video, '.estado', 'ejecuciones')
            os.makedirs(carpeta_reg, exist_ok=True)
            t.registro = os.path.relpath(os.path.join(carpeta_reg, '%s-%s.jsonl' % (t.id, paso)), self.raiz).replace('\\', '/')
            self.actual = t
        threading.Thread(target=self._correr_comandos, args=(t, comandos), daemon=True).start()
        threading.Thread(target=self._esperar_tope, args=(t, int(minutos) * 60), daemon=True).start()
        return t

    def _correr_comandos(self, t, comandos):
        entorno = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')      # las claves viajan por el entorno, nunca se registran
        banderas = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        with open(os.path.join(self.raiz, *t.registro.split('/')), 'w', encoding='utf-8') as reg:
            reg.write(json.dumps({'inicio': t.id, 'paso': t.paso, 'video': t.video, 'tipo': 'comandos', 'comandos': [c[0] for c in comandos]}, ensure_ascii=False) + '\n')
            for mostrar, argv in comandos:
                if t.cancelado:
                    break
                t.agregar({'t': 'comando', 'texto': '$ ' + mostrar})
                try:
                    t.proc = subprocess.Popen(argv, cwd=self.raiz, env=entorno, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=banderas)
                except OSError as e:
                    t.motivo = 'No pude lanzar el comando: %s' % e
                    break
                for crudo in t.proc.stdout:
                    linea = crudo.decode('utf-8', 'replace').rstrip()
                    if linea.strip():
                        reg.write(json.dumps({'salida': linea}, ensure_ascii=False) + '\n')
                        reg.flush()
                        t.agregar({'t': 'salida', 'texto': _corto(linea, 300)})
                codigo = t.proc.wait()
                if t.cancelado:
                    break
                if codigo != 0:
                    t.motivo = 'El comando terminó con código %s: %s' % (codigo, mostrar)
                    break
        t.fin = time.time()
        if t.cancelado:
            t.estado = 'cancelado'
        elif t.motivo:
            t.estado = 'error'
            t.agregar({'t': 'aviso', 'texto': t.motivo})
        else:
            t.estado = 'terminado'
            t.agregar({'t': 'fin', 'texto': 'Terminó sin errores.'})

    def _leer(self, t):
        errores = []
        hilo_err = threading.Thread(target=lambda: errores.append(t.proc.stderr.read().decode('utf-8', 'replace')), daemon=True)
        hilo_err.start()
        ruta = os.path.join(self.raiz, *t.registro.split('/'))
        with open(ruta, 'a', encoding='utf-8') as reg:
            for crudo in t.proc.stdout:
                linea = crudo.decode('utf-8', 'replace').strip()
                if not linea:
                    continue
                reg.write(linea + '\n')
                reg.flush()
                for ev in eventos_de(linea, self.raiz):
                    t.agregar(ev)
                    if ev['t'] == 'fin':
                        t.costo, t.sesion = ev.get('costo'), ev.get('sesion')
                        if ev.get('error'):
                            t.motivo = ev['texto']
        codigo = t.proc.wait()
        hilo_err.join(timeout=2)
        t.fin = time.time()
        if t.cancelado:
            t.estado = 'cancelado'
        elif codigo != 0 or t.motivo:
            t.estado = 'error'
            t.motivo = t.motivo or _corto(''.join(errores), 500) or 'Claude Code terminó con código %s' % codigo
            t.agregar({'t': 'aviso', 'texto': t.motivo})
        else:
            t.estado = 'terminado'

    def _esperar_tope(self, t, segundos):
        for _ in range(segundos):
            if t.estado != 'corriendo':
                return
            time.sleep(1)
        if t.estado == 'corriendo':
            t.agregar({'t': 'aviso', 'texto': 'Se agotó el tiempo máximo del paso (%d min): se cancela.' % (segundos // 60)})
            self.cancelar()

    def cancelar(self):
        t = self.actual
        if not t or t.estado != 'corriendo':
            return False
        t.cancelado = True
        t.agregar({'t': 'aviso', 'texto': 'Cancelado por ti.'})
        proc = t.proc
        if proc is not None:
            try:
                if os.name == 'nt':   # mata también a los procesos hijos (Claude Code y los renders lanzan varios)
                    subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True, timeout=15)
                else:
                    proc.terminate()
            except Exception:
                proc.kill()
        return True

    def estado(self, desde=0):
        return self.actual.a_dict(desde) if self.actual else {'estado': 'ninguno', 'n': 0, 'eventos': []}
