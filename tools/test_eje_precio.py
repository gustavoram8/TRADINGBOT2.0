# -*- coding: utf-8 -*-
"""Pruebas del ajuste de escala del eje de precios.

    python3 tools/test_eje_precio.py

🔑 Lo que de verdad se prueba no es que sepa dividir: es que **una etiqueta mal
leída no envenene la escala**. Ese es el fallo peligroso, porque no se nota —
leer 29.550 como 29.556 mueve todos los precios del gráfico y el resultado sigue
pareciendo razonable. Y el caso contrario: con lecturas incoherentes tiene que
**negarse a dar una escala**, no inventarse una."""
from __future__ import print_function

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import eje_precio as E  # noqa: E402


def main():
    hechos, mal = [0], []

    def caso(n, cond, extra=''):
        hechos[0] += 1
        print(('  ✅ ' if cond else '  🔴 ') + n + ('' if cond else ' %s' % extra))
        if not cond:
            mal.append(n)

    print('── formatos de número (coma o punto decimal, miles con lo otro) ──')
    for t, v in (('29.550,75', 29550.75), ('29,550.75', 29550.75),
                 ('7676', 7676.0), ('7.700,00', 7700.0),
                 ('29.428,50', 29428.50), ('1.234', 1234.0)):
        caso('%s → %s' % (t, v), E._numero(t) == v, E._numero(t))
    caso('un texto que no es precio se ignora', E._numero('BE') is None)

    print('── escala limpia ──')
    et = [(100, 7700.0), (200, 7690.0), (300, 7680.0), (400, 7670.0),
          (500, 7660.0)]
    r = E.ajusta(et)
    caso('encuentra escala', r is not None)
    if r:
        caso('-0,1 por píxel', abs(r['por_px'] + 0.1) < 1e-9, r['por_px'])
        caso('las 5 de acuerdo', r['apoyos'] == 5, r['apoyos'])
        caso('precio en y=250 = 7685', abs(r['precio'](250) - 7685) < 1e-6)

    print('── UNA etiqueta mal leída (7690 → 7996) ──')
    et2 = [(100, 7700.0), (200, 7996.0), (300, 7680.0), (400, 7670.0),
           (500, 7660.0)]
    r2 = E.ajusta(et2)
    caso('la escala buena sobrevive',
         r2 and abs(r2['por_px'] + 0.1) < 1e-9, r2 and r2['por_px'])
    caso('y la mala queda descartada', r2 and r2['apoyos'] == 4,
         r2 and r2['apoyos'])

    print('── DOS malas de cinco ──')
    r3 = E.ajusta([(100, 7700.0), (200, 7996.0), (300, 7680.0),
                   (400, 1670.0), (500, 7660.0)])
    caso('aguanta con las 3 que quedan', r3 and r3['apoyos'] == 3,
         r3 and r3['apoyos'])

    print('── cuando NO se puede saber, no se inventa ──')
    r4 = E.ajusta([(100, 7700.0), (200, 1.0), (300, 55.0)])
    caso('lecturas incoherentes → sin escala fiable',
         r4 is None or r4['apoyos'] >= 3, r4)
    caso('con solo 2 etiquetas NO se fía',
         E.ajusta([(100, 7700.0), (200, 7690.0)]) is None)

    print()
    print('%d/%d' % (hechos[0] - len(mal), hechos[0]))
    if mal:
        print('FALLAN:', mal)
    return not mal


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
