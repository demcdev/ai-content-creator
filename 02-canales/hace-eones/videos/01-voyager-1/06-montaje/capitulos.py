#!/usr/bin/env python3
"""Capítulos con los tiempos del video final.

Los capítulos se definieron sobre el primer audio (ritmo 0,95). Este script los traduce al audio definitivo con la misma
correspondencia que usa el montaje (frase a frase) y muestra la lista lista para pegar en YouTube Studio.
  python capitulos.py
"""
import video01

# (segundos en el primer audio, título)
CAPITULOS = [
    (0, 'La nave que está a un día luz'),
    (44, 'Qué es Voyager 1'),
    (105, 'El gran viaje: Júpiter, Saturno y Titán'),
    (239, 'El punto azul pálido'),
    (313, '¿Cómo sabemos que cruzó la frontera del Sol?'),
    (449, 'Cómo se habla con una nave a casi 26 000 millones de km'),
    (525, 'Energía, un fallo y una reparación a distancia'),
    (624, 'Lo que NO sabemos (y la frase que no es cierta)'),
    (714, 'El disco de oro y el próximo destino'),
]

if __name__ == '__main__':
    salida = []
    for to, titulo in CAPITULOS:
        tn = int(video01.t_nuevo(to)) if to else 0     # se redondea hacia abajo: el capítulo empieza justo antes de la frase
        salida.append('{}:{:02d} {}'.format(tn // 60, tn % 60, titulo))
    print('\n'.join(salida))
    print('\nDuración del video: {}:{:04.1f}'.format(int(video01.DURACION // 60), video01.DURACION % 60))
