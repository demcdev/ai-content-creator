"""
Red de Espacio Profundo y dirección de Voyager 1 (parámetros de la escena `esc_mapa` del Video 01).

Usa el globo general del estilo espacial (animaciones/espacial/globo.py). La dirección de Voyager 1 es la real
aproximada (ascensión recta ≈ 17 h 14 m, declinación ≈ +12°): vista desde la Tierra, la sonda está en una dirección
fija del espacio; al girar el planeta, cada estación la ve salir y ponerse.
"""
import math

import numpy as np

from globo import A, _B, _C, E1, E2, vec_estacion

DEC_SONDA = math.radians(12.3)
_th = math.pi / 2 - DEC_SONDA                      # ángulo entre el eje y la dirección de la sonda
_psi = math.radians(355)
P = math.cos(_th) * A + math.sin(_th) * (math.cos(_psi) * _B + math.sin(_psi) * _C)
P = P / np.linalg.norm(P)

ESTACIONES = (('Goldstone', 35.4, -116.9, 'California, EE. UU.'), ('Madrid', 40.4, -4.2, 'España'), ('Canberra', -35.4, 149.0, 'Australia'))
ELEV_MIN = math.radians(6)                          # por debajo de ≈ 6° sobre el horizonte la antena no apunta


def estado(fi):
    """Para cada estación: (posición relativa en pantalla (x, y en radios), visible en la cara delantera, ve a la sonda)."""
    out = []
    for nombre, lat, lon, pais in ESTACIONES:
        v = vec_estacion(lat, lon, fi)
        elev = math.asin(max(-1, min(1, float(np.dot(v, P)))))
        out.append((nombre, v[0], -v[1], v[2] > 0.04, elev > ELEV_MIN, math.degrees(elev)))
    return out


def direccion_sonda():
    """Dirección de la sonda en pantalla (vector unitario x, y hacia abajo)."""
    d = np.array([P[0], -P[1]])
    return d / np.linalg.norm(d)
