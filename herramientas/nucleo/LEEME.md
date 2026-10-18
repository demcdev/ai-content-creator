# nucleo/
Biblioteca compartida (solo biblioteca estándar).

- `_comun.py`: nombres de carpetas y archivos de un video (`GUION`, `VOZ`, `F_GUION`, `F_LICENCIAS`…), resolución de canal y video (`resolver_video("hace-eones/2")`), identidad efectiva de un video y utilidades de lectura de tablas markdown. **Si cambia el nombre de una carpeta o archivo de un video, se cambia aquí** y en `00-contexto/produccion/convencion-de-nombres.md`.

- `requirements.txt`: paquetes de pip que usan las herramientas (Pillow, numpy, scipy, boto3) y los programas externos que deben estar en el PATH (ffmpeg, Node.js). Instalar con `pip install -r herramientas/nucleo/requirements.txt`.

Cada programa añade `herramientas/nucleo/` a su `sys.path` antes de `from _comun import …`.
