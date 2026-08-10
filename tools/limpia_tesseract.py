# -*- coding: utf-8 -*-
"""Recorta el cubo de Tessera por su hexagono REAL, no por un umbral.

EL PROBLEMA (medido, no supuesto): el alfa de `tesseract.png` era estrictamente
binario —0 o 255, CERO valores intermedios—, la firma de un recorte hecho con
umbral. Con eso, cada pixel del borde que en el original era una mezcla de cubo
y fondo NEGRO sobrevive al 100% de opacidad: ese anillo oscuro es el "residuo"
que se ve alrededor de la figura. Medido: de los 383 pixeles del contorno, 196
eran practicamente negros, y la mascara tenia ~300 px mas que la silueta real.

POR QUE SE ARREGLA CON GEOMETRIA Y NO CON COLOR: el borde propio del cubo es
granate muy oscuro, asi que por color es INDISTINGUIBLE del fondo negro que
sobro — cualquier limpieza "por tono" se comeria el contorno del dibujo. Pero
la silueta de un cubo isometrico es un HEXAGONO, o sea seis rectas: se ajusta
el hexagono al casco convexo de la mascara, se mete hacia dentro unos pocos
pixeles (INSET, ahi vive el residuo), y se rasteriza a 8x para que al bajar de
tamano el borde tenga alfa PARCIAL de verdad.

Y a los pixeles del borde se les quita el negro con el que venian mezclados:
si el original estaba compuesto sobre negro, entonces obs = color*a, luego
color = obs/a. Es aritmetica exacta, no un retoque a ojo.

    python3 tools/limpia_tesseract.py            # solo informa
    python3 tools/limpia_tesseract.py --aplicar  # escribe el PNG

⚠️ NO es idempotente: correrlo dos veces recortaria dos veces. Por eso se niega
a trabajar sobre un archivo que YA tenga alfa suave (= ya limpio). El original
siempre se puede recuperar del historial de git.
⚠️ Al cambiar el PNG hay que subir el `?v=` de su URL en index.html, o
Cloudflare seguira sirviendo el viejo.
"""
from __future__ import print_function

import os
import sys

from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNG = os.path.join(RAIZ, 'scalpel', 'static', 'tesseract.png')
INSET = 2.0        # px hacia dentro; a ojo sobre blanco, 1.5-2 limpia sin
                   # comerse el contorno granate del cubo (3+ ya lo muerde)
SUPER = 8          # rasterizado a 8x -> alfa parcial real al bajar


def casco_convexo(p):
    p = sorted(set(p))

    def giro(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    bajo = []
    for q in p:
        while len(bajo) >= 2 and giro(bajo[-2], bajo[-1], q) <= 0:
            bajo.pop()
        bajo.append(q)
    alto = []
    for q in reversed(p):
        while len(alto) >= 2 and giro(alto[-2], alto[-1], q) <= 0:
            alto.pop()
        alto.append(q)
    return bajo[:-1] + alto[:-1]


def area(poly):
    s = 0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def hexagono(mascara):
    c = casco_convexo(mascara)
    while len(c) > 6:          # se cae el vertice que menos area aporta
        peor = min(range(len(c)), key=lambda i: area(c) - area(c[:i] + c[i + 1:]))
        c.pop(peor)
    return c


def main():
    aplicar = '--aplicar' in sys.argv
    im = Image.open(PNG).convert('RGBA')
    w, h = im.size
    px = im.load()

    alfas = im.split()[3].histogram()
    suaves = sum(alfas[1:255])
    print('%s · %dx%d' % (os.path.relpath(PNG, RAIZ), w, h))
    print('  alfa intermedio (borde suave): %d px' % suaves)
    if suaves:
        print('  → este archivo YA tiene borde suave: no se toca.')
        return 0

    solidos = [(x, y) for y in range(h) for x in range(w) if px[x, y][3] == 255]
    hx = hexagono(solidos)
    print('  máscara actual: %d px · hexágono ajustado: %.0f px'
          % (len(solidos), area(hx)))
    print('  sobra fuera de la silueta: %d px  ← el residuo' % (len(solidos) - area(hx)))

    cx = sum(p[0] for p in hx) / 6.0
    cy = sum(p[1] for p in hx) / 6.0
    poly = []
    for x, y in hx:
        dx, dy = x - cx, y - cy
        d = (dx * dx + dy * dy) ** .5 or 1
        poly.append(((x - dx / d * INSET) * SUPER, (y - dy / d * INSET) * SUPER))
    m = Image.new('L', (w * SUPER, h * SUPER), 0)
    ImageDraw.Draw(m).polygon(poly, fill=255)
    m = m.resize((w, h), Image.LANCZOS)

    out = im.copy()
    o = out.load()
    mm = m.load()
    borde = 0
    for y in range(h):
        for x in range(w):
            a = mm[x, y]
            if a == 0:
                o[x, y] = (0, 0, 0, 0)
                continue
            r, g, b, _ = o[x, y]
            if a < 255:        # obs = color*a  ->  color = obs/a
                borde += 1
                f = 255.0 / a
                r, g, b = (min(255, int(r * f)), min(255, int(g * f)),
                           min(255, int(b * f)))
            o[x, y] = (r, g, b, a)
    print('  borde nuevo con alfa parcial: %d px (antes: 0)' % borde)

    if not aplicar:
        print('\n  (solo informe — pasa --aplicar para escribirlo)')
        return 0
    out.save(PNG)
    print('\n  escrito. ⚠️ subir el ?v= de /static/tesseract.png en index.html')
    return 0


if __name__ == '__main__':
    sys.exit(main())
