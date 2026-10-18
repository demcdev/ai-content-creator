# animaciones/
Un estilo de animación por carpeta; el nombre de la carpeta es el id del estilo en `catalogo/animaciones.json`.

- `espacial/`: fondo de nebulosa y estrellas, paneles de cristal, planetas, globo terrestre. Es el estilo de los videos 1 y 2.
- `papel-recortado/`: piezas de papel en capas con cámara multiplano. Estado «parcial»: solo librerías.

Un estilo es utilizable por la tubería cuando tiene `estilo.py` (con `base`, `bloom`, `_mascara`) y `escenas_base.py` (con `crear`).
