# -*- coding: utf-8 -*-
"""Pruebas de la recuperación de velas por rejilla.

    python3 tools/test_rejilla.py

🔑 Lo que se prueba no es que sepa dividir: es que **no invente velas**. Meter
una vela donde no la hay es peor que perderla — la perdida deja un hueco que
tarde o temprano se ve, la inventada entra en la aritmética como cualquier otra
y sale afirmada en el bloque de hechos con la misma cara de seguridad."""
from __future__ import print_function

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rejilla_velas as RV  # noqa: E402

FONDO = (250, 250, 252)
VELA = (20, 120, 200)


def lamina(x_velas, ancho=6, alto=(200, 400), an=800, al=600, extras=()):
    """Un gráfico de mentira: cuerpos rellenos en las columnas que se digan."""
    a = np.zeros((al, an, 3), int)
    a[:, :] = FONDO
    for x in x_velas:
        a[alto[0]:alto[1], int(x):int(x) + ancho] = VELA
    for (y, col) in extras:                      # líneas horizontales
        a[y:y + 1, :] = col
    return a


def main():
    hechos, mal = [0], []

    def caso(n, cond, extra=''):
        hechos[0] += 1
        print(('  ✅ ' if cond else '  🔴 ') + n + ('' if cond else ' %s' % extra))
        if not cond:
            mal.append(n)

    print('── la rejilla que se ajusta a los centros ──')
    centros = [100 + 7.5 * k for k in range(20)]
    r = RV.ajusta_rejilla(centros, 7.4)
    caso('encuentra la recta', r is not None)
    if r:
        a, p, ks = r
        caso('paso 7,50 (le dieron 7,40)', abs(p - 7.5) < 0.05, p)
        caso('las ranuras son 0..19', list(ks) == list(range(20)), list(ks))
    # con velas faltando, las ranuras tienen que SALTAR
    huecos = [100 + 7.5 * k for k in (0, 1, 2, 5, 6, 9, 10, 11, 12, 13, 14)]
    r2 = RV.ajusta_rejilla(huecos, 7.5)
    caso('con huecos, las ranuras saltan igual que las velas',
         r2 and list(r2[2]) == [0, 1, 2, 5, 6, 9, 10, 11, 12, 13, 14],
         r2 and list(r2[2]))
    caso('con menos de 4 centros no se fía',
         RV.ajusta_rejilla([10.0, 20.0, 30.0], 10.0) is None)

    print('── recupera las que faltan ──')
    xs = [100 + 15 * k for k in range(20)]
    a = lamina(xs)
    # el modelo se dejó las ranuras 4, 9 y 10
    faltan = {4, 9, 10}
    cajas = [(int(x), int(x) + 5, 200, 400)
             for k, x in enumerate(xs) if k not in faltan]
    todas, nuevas = RV.completa(cajas, 15.0, a, (150, 450))
    caso('recupera las 3', len(nuevas) == 3, len(nuevas))
    caso('y quedan las 20', len(todas) == 20, len(todas))
    cent = sorted(round((c[0] + c[1]) / 2.0) for c in nuevas)
    caso('en las columnas correctas',
         cent == [round(xs[k] + 2.5) for k in sorted(faltan)], cent)

    print('── 🔴 NO inventa velas donde no las hay ──')
    # el gráfico se acaba en la ranura 19; la rejilla no puede seguir sola
    caso('nada más allá de la última vela',
         all((c[0] + c[1]) / 2.0 < xs[-1] + 15 for c in nuevas))
    # un hueco LARGO es un corte de sesión, no velas perdidas
    cajas2 = [(int(x), int(x) + 5, 200, 400)
              for k, x in enumerate(xs) if k < 5 or k > 14]
    _t2, n2 = RV.completa(cajas2, 15.0, a, (150, 450))
    caso('un hueco de 10 ranuras NO se rellena (tope %d)' % RV.HUECO_MAX,
         len(n2) == 0, len(n2))
    # una imagen donde en el hueco NO hay vela, solo una línea horizontal
    a3 = lamina([x for k, x in enumerate(xs) if k not in faltan],
                extras=[(300, (200, 40, 40))])
    _t3, n3 = RV.completa(cajas, 15.0, a3, (150, 450))
    caso('sin vela en la ranura, no se añade nada', len(n3) == 0, len(n3))

    print('── las dos paredes distinguen una vela de un canto ──')
    perfil = np.zeros(400)
    perfil[100] = 90.0                       # una sola pared (canto de caja)
    caso('una pared sola da casi cero',
         RV.senal_de_cuerpo(perfil, 100, 6) < 1.0,
         RV.senal_de_cuerpo(perfil, 100, 6))
    perfil2 = np.zeros(400)
    perfil2[98] = 90.0; perfil2[104] = 90.0  # las dos del cuerpo
    caso('las dos paredes sí puntúan',
         RV.senal_de_cuerpo(perfil2, 101, 6) == 90.0,
         RV.senal_de_cuerpo(perfil2, 101, 6))

    print('── la guía de la añadida se interpola, no se copia ──')
    xs2 = [100 + 15 * k for k in range(6)]
    a4 = lamina(xs2, alto=(200, 400))
    # guías que bajan 20 px por vela; falta la ranura 3
    cajas3 = [(int(x), int(x) + 5, 200 + 20 * k, 400 + 20 * k)
              for k, x in enumerate(xs2) if k != 3]
    _t4, n4 = RV.completa(cajas3, 15.0, a4, (100, 600))
    caso('se añade la que falta', len(n4) == 1, len(n4))
    if len(n4) == 1:
        c = list(n4)[0]
        caso('su guía es la del medio (260), no la de un vecino',
             c[2] == 260, c[2])

    print()
    print('%d/%d' % (hechos[0] - len(mal), hechos[0]))
    if mal:
        print('FALLAN:', mal)
    return not mal


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
