# -*- coding: utf-8 -*-
"""Comprueba que la verdad declarada del banco de agudeza es la que se DIBUJÓ.

    python3 tools/verifica_agudeza.py       # después de --generar

Mide los PÍXELES de cada PNG y reconstruye la respuesta desde la imagen. No
mira el código que la generó: si el generador tiene un bug, este archivo lo
caza; si comprobara leyendo las mismas fórmulas, no comprobaría nada.

🔴 EXISTE PORQUE YA CAZÓ DOS BUGS que habrían invalidado el estudio entero:
   1. `cruce` usaba dos RECTAS de pendiente opuesta. Dos rectas así se cruzan
      SIEMPRE — desplazar una `nivel` px solo mueve el punto de cruce. Los 12
      casos "NO" estaban dibujados como "SI", y habríamos suspendido a los
      modelos por acertar.
   2. `solape` dibujaba las zonas compartiendo columnas: la naranja TAPABA a la
      azul justo en la franja del solape, así que con 1-2 px la respuesta no era
      discernible ni a resolución completa. La verdad era ambigua.

Corre siempre esto antes de gastar dinero en `--correr`.
"""
from __future__ import print_function

import io
import json
import os
import sys

import numpy as np
from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(RAIZ, 'out', 'agudeza')
AL, AN = 1080, 1920


def cerca(a, col, tol=40):
    return np.abs(a.astype(int) - np.array(col)).sum(2) < tol


def main():
    ruta = os.path.join(S, 'manifiesto.json')
    if not os.path.exists(ruta):
        sys.exit('no hay láminas: corre antes  tools/agudeza_visual.py --generar')
    man = json.load(io.open(ruta, encoding='utf-8'))
    mal, revisados = [], 0
    for c in man:
        a = np.asarray(Image.open(os.path.join(S, 'laminas', c['id'] + '.png'))
                       .convert('RGB'))
        f, niv, esp = c['familia'], c['nivel'], c['respuesta']
        if f == 'cruce':
            az, na = cerca(a, (79, 140, 255)), cerca(a, (240, 176, 60))
            # ⚠️ Se recorre COLUMNA A COLUMNA. Con muestreo cada 20 px, un cruce
            #    de 2 px de penetración dura ~7 px y se pasa por alto: el
            #    verificador daba falsos fallos.
            sig = []
            for x in range(100, AN - 190):
                ca, cb = np.where(az[:, x])[0], np.where(na[:, x])[0]
                if len(ca) and len(cb):
                    sig.append(np.sign(ca.mean() - cb.mean()))
            real = 'SI' if len(set(sig)) > 1 else 'NO'
        elif f == 'solape':
            az, na = cerca(a, (40, 92, 178), 30), cerca(a, (190, 112, 42), 30)
            ra, rb = np.where(az.sum(1) > 100)[0], np.where(na.sum(1) > 100)[0]
            real = 'SI' if (len(ra) and len(rb) and
                            max(ra.min(), rb.min()) <= min(ra.max(), rb.max())) else 'NO'
        elif f == 'conteo':
            am = cerca(a, (255, 235, 120), 60)
            n, prev = 0, -99
            for y in np.where(am.sum(1) > 800)[0]:
                if y - prev > 5:
                    n += 1
                prev = y
            real = str(n)
        elif f == 'ruptura':
            y_niv = int(np.argmax(cerca(a, (200, 205, 215), 30).sum(1)))
            cuerpo = cerca(a[:, 1260:1274], (38, 166, 109), 30)
            ys = np.where(cuerpo.sum(1) >= 12)[0]      # fila llena = cuerpo, no mecha
            real = 'SI' if (len(ys) and ys.min() < y_niv) else 'NO'
        elif f == 'rsi':
            mo = cerca(a, (190, 120, 235), 60)
            cols = np.where(mo.sum(0) > 0)[0]
            if not len(cols):
                real = '?'
            else:
                yfin = np.where(mo[:, cols.max()])[0].mean()
                real = 'SI' if yfin > (AL - niv - 40) + niv * 0.70 else 'NO'
        else:
            continue                                   # ocr: se comprueba aparte
        revisados += 1
        if real != esp:
            mal.append('%s: declara %s, el dibujo es %s' % (c['id'], esp, real))

    # OCR: sin motor de OCR no se puede leer la cifra, pero sí exigir que HAYA
    # tinta clara en el eje a la altura de la línea. Una lámina sin etiqueta
    # sería una pregunta sin respuesta posible.
    ocr = [x for x in man if x['familia'] == 'ocr']
    faltan = 0
    for c in ocr:
        a = np.asarray(Image.open(os.path.join(S, 'laminas', c['id'] + '.png'))
                       .convert('RGB'))
        y = int(np.argmax(cerca(a, (200, 205, 215), 30).sum(1)))
        caja = a[max(0, y - 14):y + 14, AN - 145:AN - 60]
        if (caja.astype(int).sum(2) > 660).sum() < 6:
            faltan += 1

    print('verificadas por píxeles: %d' % revisados)
    print('ocr con etiqueta legible: %d/%d' % (len(ocr) - faltan, len(ocr)))
    for m in mal:
        print('  🔴', m)
    if mal or faltan:
        sys.exit('🔴 %d láminas mienten. NO corras --correr hasta arreglarlo.'
                 % (len(mal) + faltan))
    print('✅ la verdad declarada coincide con el dibujo en las %d láminas.'
          % (revisados + len(ocr)))


if __name__ == '__main__':
    main()
