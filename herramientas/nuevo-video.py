"""
Crea la carpeta de un video nuevo con la estructura estándar de un canal (sirve para todos los canales).

  python herramientas/nuevo-video.py "Hace Eones" 3 "Nombre corto del video"
  -> 02_canales/Hace Eones/Video 03 - Nombre corto del video/

El canal debe existir como carpeta dentro de 02_canales/ (no se crea aquí).

Dentro: documentos de partida (Guion, Escaleta audiovisual con su planilla, Verificacion de cifras, Capitulos y descripcion,
Texto para subtitulos, Registro de licencias, Metricas y seguimiento) y las carpetas
Voz, Montaje, Licencias (originales, fichas, musica, capturas-musica), Miniaturas y Entregables.
No pisa nada: si algo ya existe, lo deja como está.
"""
import json
import os
import re
import shutil
import sys

HERRAMIENTAS = os.path.dirname(os.path.abspath(__file__))
CANALES = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '02_canales'))
NO_CANAL = set()

DOCS = {
    'Guion.md': '# {t}\n\n> Estado: borrador · Duración objetivo: 10–12 min\n> Antes de pedir revisión: repasar la [checklist de escritura](../../../00_contexto/Checklist-escritura-guion.md).\n\n## Guion\n\n',
    'Verificacion de cifras.md': '# Verificación de cifras · {t}\n\n| N.º | Dato | Fuente (enlace) | Fecha de consulta | Estado |\n|---|---|---|---|---|\n',
    'Capitulos y descripcion.md': '# Capítulos y descripción · {t}\n\n## Descripción\n\n## Capítulos\n\n## Miniatura (encargo)\nVariantes, texto, imagen base y elegida.\n\n## Fuentes\n\n## Transparencia (voz con IA, imágenes, música)\n',
    'Escaleta audiovisual.md': '# Escaleta audiovisual · {t}\n\n## Planilla de producción (3 columnas)\n\n> Fase 1: se hace con la skill `guionista-retencion` a partir del Guion.\n\n| Tiempo / Bloque | Diálogo (locución) | Visual & B-roll | Audio & Tipografía |\n| :--- | :--- | :--- | :--- |\n\n## 1. Escaleta técnica\n\n> Fase 3: se hace con la skill `escaleta-audiovisual` después del guion y antes del montaje.\n\n| Escena | Tiempo | Video / Visuales y dirección | Audio, voz y efectos | Origen y licencia |\n| :--- | :--- | :--- | :--- | :--- |\n',
    'Texto para subtitulos.txt': '',
    'Registro de licencias.md': '# Registro de licencias · {t}\n\nUna fila por material (imágenes, voz, música, tipografía). Capturas en `Licencias/`. Reglas 3 y 6 del proyecto.\n\n| Código | Material | Fuente / ficha | Licencia | Captura | Estado |\n|---|---|---|---|---|---|\n',
    'Metricas y seguimiento.md': '# Métricas y seguimiento · {t}\n\nFechas de revisión: 2–3 días, 7 días, 28 días. Se anota CTR, retención, fuentes de tráfico y qué se cambia.\n\n| Fecha | Vistas | CTR | Retención media | Notas / decisión |\n|---|---|---|---|---|\n',
}
CARPETAS = ['Revision', 'Voz', 'Montaje', 'Entregables', 'Miniaturas', 'Licencias/originales', 'Licencias/fichas', 'Licencias/musica', 'Licencias/capturas-musica']


def buscar_canal(nombre):
    existentes = [d for d in sorted(os.listdir(CANALES))
                  if os.path.isdir(os.path.join(CANALES, d)) and d not in NO_CANAL and not d.startswith('_')]
    for d in existentes:
        if d.lower() == nombre.strip().lower():
            return os.path.join(CANALES, d)
    print('No existe el canal «%s». Canales disponibles: %s' % (nombre, ', '.join(existentes)))
    return None


def principal():
    if len(sys.argv) < 4 or not sys.argv[2].isdigit():
        print(__doc__)
        return 1
    raiz = buscar_canal(sys.argv[1])
    if not raiz:
        return 1
    n = int(sys.argv[2])
    titulo = sys.argv[3].strip()
    nombre = re.sub(r'[\/:*?"<>|]', '', titulo)
    carpeta = os.path.join(raiz, 'Video %02d - %s' % (n, nombre))
    os.makedirs(carpeta, exist_ok=True)
    for c in CARPETAS:
        os.makedirs(os.path.join(carpeta, *c.split('/')), exist_ok=True)
    for f, plantilla in DOCS.items():
        ruta = os.path.join(carpeta, f)
        if not os.path.exists(ruta):
            with open(ruta, 'w', encoding='utf-8') as fh:
                fh.write(plantilla.format(t=titulo))
    plantilla = os.path.join(HERRAMIENTAS, 'montaje', 'plantilla_video.py')
    destino = os.path.join(carpeta, 'Montaje', 'video.py')
    if os.path.exists(plantilla) and not os.path.exists(destino):
        shutil.copyfile(plantilla, destino)
    cfg = os.path.join(carpeta, 'Montaje', 'montaje.json')
    if not os.path.exists(cfg):
        with open(cfg, 'w', encoding='utf-8') as fh:
            json.dump({'nombre': 'video-%02d-completo' % n, 'animacion': '', 'rotulos': [], 'creditos': [], 'capitulos': [],
                       'musica': {'pistas': [], 'cambio': 0}}, fh, ensure_ascii=False, indent=1)
    rel = os.path.relpath(carpeta, os.path.dirname(HERRAMIENTAS))
    print('Listo:', carpeta)
    print('Siguiente: guion, voz (Claude pregunta cuál), animación (Claude pregunta cuál), y luego:')
    print('  python herramientas/montaje/alinear.py "%s"' % rel)
    print('  python herramientas/escaleta-a-escenas.py "%s"' % rel)
    print('  (cd "%s/Montaje" && python video.py --frame 60 f.png)' % rel)
    return 0


if __name__ == '__main__':
    sys.exit(principal())
