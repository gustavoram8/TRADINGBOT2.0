# -*- coding: utf-8 -*-
"""La tira de siluetas de la botarga para la banda azul de `/creators`.

    python3 tools/gen_tira_botarga.py

Escribe `scalpel/static/tira-botarga.png` — regenerar y commitear tras
cualquier cambio del muñeco de origen.

LA IDEA, EN PALABRAS DEL DUEÑO: dos foamis, uno azul de la marca y uno blanco.
En el azul dibujas la silueta de la botarga de bienvenida, la recortas, y pones
el blanco detrás: por el hueco se asoma el muñeco entero relleno de blanco. Eso
es un ESTARCIDO, y es literalmente lo que hace este script.

CÓMO SE SACA LA SILUETA
-----------------------
Del canal alfa de `logo2_dark.png`, no de sus colores: el muñeco ya viene
recortado sobre fondo transparente, así que el alfa ES la figura.

🔴 **LOS HUECOS INTERIORES SE QUEDAN ABIERTOS — probado mirándolo.** La primera
   versión los rellenaba (la lectura literal del foami: recortas el contorno y
   sale la figura maciza) y a 46 px **se leía como un bulto, no como el muñeco**.
   Lo que hace que una silueta se lea como un personaje es el hueco entre el
   brazo y el cuerpo y el hueco entre las piernas; sin ellos queda una mancha
   con patas. Y no traiciona la idea del estarcido: un estarcido de verdad
   conserva PUENTES — es lo mismo que hace que la "O" de una plantilla no se
   caiga. Comparadas las dos a 46 y 64 px, gana la abierta sin discusión.
   ⚠️ NO confundir con la regla del 25-jul de CLAUDE.md, que prohíbe borrar
   bolsas blancas encerradas en las botargas: aquella prohibición es sobre
   MODIFICAR el arte original (se comió llamas, humo y velas). Aquí no se toca
   ningún `logo*.png`: se DERIVA un archivo nuevo.

⚠️ Y se dibuja mirándolo. A 28 px de alto una silueta puede quedarse en un
   borrón: el script imprime la `densidad` para cazar el caso "manchón" sin
   abrir la imagen, pero la comprobación de verdad es mirar el PNG sobre el
   azul de la marca.
"""
from __future__ import print_function

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN = os.path.join(RAIZ, 'scalpel', 'static', 'logo2_dark.png')
DESTINO = os.path.join(RAIZ, 'scalpel', 'static', 'tira-botarga.png')

# Medidas de PANTALLA (la banda mide 48 px en escritorio y 85 en móvil, medido
# en navegador). El mosaico se genera a ESCALA×, así en un teléfono retina no
# sale borroso, y el CSS lo pinta a `PASO_CSS × ALTO_CSS`.
# ⚠️ Medidas elegidas MIRÁNDOLO, no a ojo: a 28 px con 42 de paso los muñecos
#    iban tan juntos que la banda se leía como una textura y no como el
#    personaje. Con 34 de alto y 60 de paso caben menos y cada uno se lee.
ALTO_CSS = 34       # alto del muñeco tal como se ve (la banda mide 48)
PASO_CSS = 60       # de un muñeco al siguiente — ES el recorrido de la animación
ESCALA = 3
ALFA_MIN = 90       # por debajo de esto es borde suavizado, no figura


def silueta(ruta):
    """Máscara del muñeco recortada a su caja, con los huecos ABIERTOS.

    El muñeco ya viene sobre fondo transparente, así que su canal alfa ES la
    figura: basta umbralizar para quitar el borde suavizado."""
    from PIL import Image
    im = Image.open(ruta).convert('RGBA')
    im = im.crop(im.getchannel('A').getbbox())
    return im.getchannel('A').point(lambda v: 255 if v >= ALFA_MIN else 0)


def main():
    try:
        from PIL import Image
    except ImportError:
        sys.exit('falta Pillow')
    if not os.path.exists(ORIGEN):
        sys.exit('no está %s' % ORIGEN)

    m = silueta(ORIGEN)
    an, al = m.size
    alto_px = ALTO_CSS * ESCALA
    ancho_px = max(1, int(round(an * alto_px / float(al))))
    # ⚠️ se reduce con LANCZOS sobre la MÁSCARA y no sobre el color: así el
    #    borde queda con alfa parcial de verdad y el muñeco no sale dentado
    m = m.resize((ancho_px, alto_px), Image.LANCZOS)

    huella = PASO_CSS * ESCALA
    if ancho_px > huella - 6 * ESCALA:
        sys.exit('PASO_CSS=%d es muy corto: el muñeco mide %d px de ancho a esa '
                 'altura y los mosaicos se tocarían.'
                 % (PASO_CSS, ancho_px / float(ESCALA)))
    tira = Image.new('RGBA', (huella, alto_px), (0, 0, 0, 0))
    blanco = Image.new('RGBA', m.size, (255, 255, 255, 255))
    tira.paste(blanco, ((huella - ancho_px) // 2, 0), m)
    tira.save(DESTINO)

    llenos = sum(1 for v in m.getdata() if v > 20)
    dens = llenos / float(ancho_px * alto_px)
    print('silueta %dx%d px reales · mosaico %dx%d · densidad %.0f%%'
          % (ancho_px, alto_px, huella, alto_px, dens * 100))
    if dens > .74:
        print('⚠️  densidad muy alta: a tamaño pequeño esto se va a leer como '
              'un manchón, no como el muñeco. MÍRALO antes de publicarlo.')
    print('escrito %s (%.1f KB)'
          % (os.path.relpath(DESTINO, RAIZ), os.path.getsize(DESTINO) / 1024.0))
    print()
    print('CSS que tiene que coincidir con esto:')
    print('  background-size: %dpx %dpx;' % (PASO_CSS, ALTO_CSS))
    print('  y la animación recorre EXACTAMENTE %dpx — si no, el bucle salta.'
          % PASO_CSS)


if __name__ == '__main__':
    main()
