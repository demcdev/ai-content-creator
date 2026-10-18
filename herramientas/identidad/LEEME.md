# identidad/
- `identidad.py`: identidad de cada canal (`identidad/identidad.json`: nombre, colores, logo, fuente, voz, animación, música, efectos) y de cada video (`{"base": "canal"}` o `{"base": "propia", …}`).

```bash
python herramientas/identidad/identidad.py mostrar hace-eones
python herramientas/identidad/identidad.py video hace-eones/3 --base canal
python herramientas/identidad/identidad.py resumen hace-eones   # frase para la pregunta «¿canal o propia?»
```
Las opciones válidas de voz y animación salen de `voz/voces.json` y `montaje/catalogo/animaciones.json`.
