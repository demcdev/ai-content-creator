"""
Crea la carpeta de un video nuevo con la estructura estándar de un canal (sirve para todos los canales).

  python herramientas/video/nuevo-video.py "<canal>" 3 "Nombre corto del video"
  -> 02-canales/<canal>/videos/03-nombre-corto-del-video/

El canal debe existir como carpeta dentro de 02-canales/ (no se crea aquí). Nomenclatura: ver
00-contexto/produccion/convencion-de-nombres.md.

Dentro, una carpeta por etapa: 01-guion (guion, verificacion-de-cifras, texto-para-subtitulos), 02-revision,
03-escaleta (escaleta-audiovisual con su planilla), 04-voz, 05-licencias (registro-de-licencias y originales, fichas,
musica, capturas-musica), 06-montaje, 07-miniaturas, 08-entregables, 09-publicacion (capitulos-y-descripcion,
metricas-y-seguimiento) e identidad (identidad.json); en la raíz solo el LEEME.md.
No pisa nada: si algo ya existe, lo deja como está.
"""
"""
Crea la carpeta de un video nuevo con la estructura estándar de un canal (sirve para todos los canales).

  python herramientas/video/nuevo-video.py "<canal>" 3 "Nombre corto del video"
  -> 02-canales/<canal>/videos/03-nombre-corto-del-video/

El canal debe existir como carpeta dentro de 02-canales/ (no se crea aquí). Nomenclatura: ver
00-contexto/produccion/convencion-de-nombres.md.

Dentro, una carpeta por etapa: 01-guion (guion, verificacion-de-cifras, texto-para-subtitulos), 02-revision,
03-escaleta (escaleta-audiovisual con su planilla), 04-voz, 05-licencias (registro-de-licencias y originales, fichas,
musica, capturas-musica), 06-montaje, 07-miniaturas, 08-entregables, 09-publicacion (capitulos-y-descripcion,
metricas-y-seguimiento) e identidad (identidad.json); en la raíz solo el LEEME.md.
No pisa nada: si algo ya existe, lo deja como está.
"""
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nucleo'))
from _comun import (CANALES, ENTREGABLES, ESCALETA, F_CAPITULOS, F_CIFRAS, F_ESCALETA, F_GUION, F_IDENTIDAD, F_LICENCIAS, F_METRICAS,
                    F_SUBTITULOS, GUION, LICENCIAS, MINIATURAS, MONTAJE, PUBLICACION, REVISION, VOZ, resolver_canal, ruta, slug,
                    listar_canales)

HERRAMIENTAS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHECKLIST = '../../../../../00-contexto/produccion/checklist-escritura-guion.md'
DOCS = {
    F_GUION: '# {t}\n\n> Estado: borrador · Duración objetivo: 10–12 min\n> Antes de pedir revisión: repasar la [checklist de escritura](' + CHECKLIST + ').\n\n## Guion\n\n',
    F_CIFRAS: '# Verificación de cifras · {t}\n\n| N.º | Dato | Fuente (enlace) | Fecha de consulta | Estado |\n|---|---|---|---|---|\n',
    F_CAPITULOS: '# Capítulos y descripción · {t}\n\n## Descripción\n\n## Capítulos\n\n## Miniatura (encargo)\nVariantes, texto, imagen base y elegida.\n\n## Fuentes\n\n## Transparencia (voz con IA, imágenes, música)\n',
    F_ESCALETA: '# Escaleta audiovisual · {t}\n\n## Planilla de producción (3 columnas)\n\n> Fase 1: se hace con la skill `guionista-retencion` a partir del guion.\n\n| Tiempo / Bloque | Diálogo (locución) | Visual & B-roll | Audio & Tipografía |\n| :--- | :--- | :--- | :--- |\n\n## 1. Escaleta técnica\n\n> Fase 3: se hace con la skill `escaleta-audiovisual` después del guion y antes del montaje.\n\n| Escena | Tiempo | Video / Visuales y dirección | Audio, voz y efectos | Origen y licencia |\n| :--- | :--- | :--- | :--- | :--- |\n',
    F_SUBTITULOS: '',
    F_LICENCIAS: '# Registro de licencias · {t}\n\nUna fila por material (imágenes, voz, música, tipografía). Capturas en esta carpeta (`05-licencias/`). Reglas 3 y 6 del proyecto.\n\n| Código | Material | Fuente / ficha | Licencia | Captura | Estado |\n|---|---|---|---|---|---|\n',
    F_METRICAS: '# Métricas y seguimiento · {t}\n\nFechas de revisión: 2–3 días, 7 días, 28 días. Se anota CTR, retención, fuentes de tráfico y qué se cambia.\n\n| Fecha | Vistas | CTR | Retención media | Notas / decisión |\n|---|---|---|---|---|\n',
    'LEEME.md': '# {t}\n\nCarpeta del video. Una carpeta por etapa, en orden: `01-guion` → `02-revision` → `03-escaleta` → `04-voz` → `05-licencias` → `06-montaje` → `07-miniaturas` → `08-entregables` → `09-publicacion`; `identidad/` guarda la identidad propia del video.\n\nEstado: `python herramientas/video/estado-video.py "<canal>/{n}"` (con `--escribir` lo guarda aquí).\n',
}
CARPETAS = [REVISION, VOZ, MONTAJE, ENTREGABLES, MINIATURAS, GUION, ESCALETA, PUBLICACION, 'identidad',
            LICENCIAS + '/originales', LICENCIAS + '/fichas', LICENCIAS + '/musica', LICENCIAS + '/capturas-musica']


def buscar_canal(nombre):
    canal = resolver_canal(nombre)
    if canal:
        return canal
    print('No existe el canal «%s». Canales disponibles: %s' % (nombre, ', '.join(listar_canales())))
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
    carpeta = os.path.join(raiz, 'videos', '%02d-%s' % (n, slug(nombre)))
    os.makedirs(carpeta, exist_ok=True)
    for c in CARPETAS:
        os.makedirs(os.path.join(carpeta, *c.split('/')), exist_ok=True)
    for f, plantilla in DOCS.items():
        destino_doc = ruta(carpeta, f)
        if not os.path.exists(destino_doc):
            with open(destino_doc, 'w', encoding='utf-8') as fh:
                fh.write(plantilla.format(t=titulo, n=n))
    plantilla = os.path.join(HERRAMIENTAS, 'montaje', 'plantillas', 'plantilla_video.py')
    destino = os.path.join(carpeta, MONTAJE, 'video.py')
    if os.path.exists(plantilla) and not os.path.exists(destino):
        shutil.copyfile(plantilla, destino)
    cfg = os.path.join(carpeta, MONTAJE, 'montaje.json')
    if not os.path.exists(cfg):
        with open(cfg, 'w', encoding='utf-8') as fh:
            json.dump({'nombre': 'video-%02d-completo' % n, 'rotulos': [], 'creditos': [], 'capitulos': [],
                       'musica': {'pistas': [], 'cambio': 0}}, fh, ensure_ascii=False, indent=1)
    ruta_id = ruta(carpeta, F_IDENTIDAD)
    if not os.path.exists(ruta_id):
        with open(ruta_id, 'w', encoding='utf-8') as fh:
            json.dump({'base': ''}, fh)
    if not os.path.exists(ruta(raiz, F_IDENTIDAD)):
        print('AVISO: el canal no tiene identidad/identidad.json (colores, voz, animación). Defínela antes de seguir: python herramientas/identidad/identidad.py canal "%s" --voz <id> --animacion <id>' % os.path.basename(raiz))
    rel = os.path.relpath(carpeta, os.path.dirname(HERRAMIENTAS))
    print('Listo:', carpeta)
    print('Siguiente: identidad del video (Claude pregunta: ¿la del canal o propia?), guion, voz, y luego:')
    print('  python herramientas/montaje/tuberia/alinear.py "%s"' % rel)
    print('  python herramientas/video/escaleta-a-escenas.py "%s"' % rel)
    print('  (cd "%s/06-montaje" && python video.py --frame 60 f.png)' % rel)
    return 0


if __name__ == '__main__':
    sys.exit(principal())
