# -*- coding: utf-8 -*-
"""La variante de MODO OSCURO de una botarga: flecha azul → naranja.

    python3 tools/botarga_oscura.py <entrada.png> <salida_dark.png>

El sitio sirve dos archivos por botarga (`logoN_<camo>.png` y
`logoN_<camo>_dark.png`): en el tema oscuro la flecha del muñeco es naranja,
igual que la del muñeco por defecto. La conversión NO se inventa aquí — se
**muestreó de la pareja real** `logo2_standard` / `logo2_standard_dark` y se
comprobó que la reproduce con error 0 sobre sus 159.726 píxeles:

    donde manda el azul:  (r, g, b) → (b, 0.6561·b, r)

(0, 86, 223) sale (223, 146, 0) = el `#dd9100` de la marca.

⚠️ El contorno negro NO entra (`b >= 31`): es azul-dominante por el
   antialias y pintarlo de naranja deja la figura sin línea. El umbral, como
   el mapeo, sale de la pareja real: el azul más oscuro que aquélla convirtió
   tenía b=31.
"""
from __future__ import print_function

import sys

import numpy as np
from PIL import Image

MIN_AZUL = 31       # por debajo de esto es contorno, no flecha
DOM_R, DOM_G = 25, 15   # cuánto tiene que ganarle el azul a los otros canales
FACTOR_G = 0.6561       # medido, no elegido


def oscurecer(entrada, salida):
    a = np.asarray(Image.open(entrada).convert('RGBA')).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    sel = ((b > r + DOM_R) & (b > g + DOM_G) & (b >= MIN_AZUL) &
           (a[..., 3] > 0))
    out = a.copy()
    out[..., 0] = np.where(sel, b, r)
    out[..., 1] = np.where(sel, (FACTOR_G * b).astype(np.int16), g)
    out[..., 2] = np.where(sel, r, b)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA').save(salida)
    print('%s -> %s  |  %d px recoloreados' % (entrada, salida, int(sel.sum())))
    return int(sel.sum())


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    oscurecer(sys.argv[1], sys.argv[2])
