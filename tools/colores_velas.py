# -*- coding: utf-8 -*-
"""DE QUÉ COLOR SON LAS VELAS DE ESTA CAPTURA. Se mide, no se opina.

    python3 tools/colores_velas.py --imagen docs/capturas_prueba/nq_5m_oct.png

🔴 POR QUÉ EXISTE, Y ES UNA REGLA DE CONDUCTA, NO UNA UTILIDAD.
El dueño ha tenido que corregirme **más de cinco veces, a lo largo de meses**,
la misma afirmación: *"mis velas NO son huecas"*. Cada vez la acepté, cada vez
la arreglé, y a las pocas semanas —con una captura nueva— volví a escribir que
eran huecas. Sus palabras: *"eres como un laberinto sin salida"*. Tiene razón:
el fallo no es de análisis, es de **método**. Yo miraba un corte de píxeles, veía
un interior más claro que el borde y lo llamaba "hueco" sin comprobar nada.

🔑 LA REGLA: **NUNCA se afirma nada sobre el color, el relleno o la forma de las
velas de una captura sin haber corrido ESTE programa y pegado su salida.** Si no
se ha corrido, no se dice. Ni "parecen huecas", ni "el interior es el fondo", ni
"son de dos colores". Nada.

═══ LO QUE DE VERDAD PASABA (medido el 17-oct sobre `nq_5m_oct.png`) ═══
Sus velas son **gris claro** (alcistas) y **negro/gris oscuro** (bajistas), las
dos RELLENAS, con un borde negro de 1 px. Lo que yo leía como "interior hueco"
era el relleno gris claro de una vela alcista.

🔴 Y AQUÍ ESTÁ LA TRAMPA DE VERDAD, que explica por qué esto reincide: en esa
captura **la caja de sesión de NY PM está pintada en EXACTAMENTE el mismo RGB
que su vela alcista** — `(206,208,213)` las dos. No se parecen: son el mismo
número. Así que *ninguna regla basada en el color puede separarlas*, y cualquier
intento de decidir "esto es fondo" mirando la paleta global va a borrarle las
velas alcistas o a tragarse la caja. Lo que las separa es la FORMA: la vela son
tiras de 3-5 px de ancho con borde negro; la caja es una mancha de 293 px.

Por eso este programa mide el ANCHO de cada mancha de color dentro del panel, y
no su frecuencia. Un color que solo aparece en tiras estrechas es vela; uno que
alguna vez forma una mancha ancha es (también) fondo.
"""
from __future__ import print_function

import argparse
import collections
import os
import sys

import numpy as np
from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

# Un cuerpo de vela nunca es más ancho que esto en una captura normal.
MAX_ANCHO_VELA = 20
# Por debajo de esta fracción del panel un color no merece línea en el informe.
MIN_FRAC = 0.004


def anchos_de(mask):
    """Los anchos de las rachas horizontales de ese color, fila a fila."""
    out = []
    for fila in mask:
        run = 0
        for v in fila:
            if v:
                run += 1
            elif run:
                out.append(run)
                run = 0
        if run:
            out.append(run)
    return out


def analiza(ruta, x0=None, x1=None, y0=None, y1=None):
    a = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
    H, W, _ = a.shape
    if x1 is None:
        try:
            import recorta_grafico as RG
            p = RG.panel(ruta)
            x0, x1 = p['x0'], p['x1']
        except Exception:
            x0, x1 = 0, W - 1
    if y1 is None:
        y0, y1 = 0, H - 1
    z = a[y0:y1 + 1, x0:x1 + 1]
    pl = z.reshape(-1, 3)
    v, n = np.unique(pl[:, 0] * 65536 + pl[:, 1] * 256 + pl[:, 2],
                     return_counts=True)
    tot = float(n.sum())
    filas = []
    for c, k in sorted(zip(v, n), key=lambda t: -t[1]):
        if k / tot < MIN_FRAC:
            break
        col = np.array([c >> 16, (c >> 8) & 255, c & 255])
        m = np.abs(z - col).sum(2) < 12
        an = anchos_de(m)
        if not an:
            continue
        cnt = collections.Counter(an)
        mx = max(an)
        # ¿cuántos píxeles de este color viven en tiras ESTRECHAS?
        # 🔑 SE CUENTAN RACHAS, NO PÍXELES. Contando píxeles, una sola mancha
        #    de 293 px pesa tanto como cien cuerpos de vela de 3 px y el color
        #    sale clasificado como "fondo" — que es EXACTAMENTE el error que
        #    borra las velas alcistas del dueño. Lo que delata a una vela es
        #    que haya MUCHAS tiras del ancho de un cuerpo, no cuánta
        #    superficie suman.
        cuerpos = sum(c2 for w, c2 in cnt.items() if 2 <= w <= MAX_ANCHO_VELA)
        filas.append({'rgb': tuple(int(x) for x in col), 'frac': k / tot,
                      'max': mx, 'modas': cnt.most_common(3),
                      'cuerpos': cuerpos})
    return filas


def veredicto(f):
    """⛔ ESTE PROGRAMA NO DECIDE QUÉ ES VELA Y QUÉ ES FONDO, Y ESO ES A
    PROPÓSITO.

    Se intentaron dos reglas automáticas el 17-oct y las dos fallaron **en
    direcciones opuestas**, lo cual es la prueba de que el problema no es de
    calibrar un umbral:
      · por SUPERFICIE (cuántos píxeles caen en tiras estrechas) → clasificó
        como "fondo" el gris que es la vela alcista del dueño;
      · por NÚMERO DE TIRAS del ancho de un cuerpo → marcó TODOS los colores
        como vela, incluido el papel blanco.
    La razón de fondo: con las velas a ~6 px de paso, **el fondo que queda
    entre dos velas es una tira de 3 px**, exactamente igual de ancha que el
    cuerpo de una vela. La geometría no los distingue, y el color tampoco: en
    `nq_5m_oct` la caja de NY PM y la vela alcista son el MISMO `(206,208,213)`.

    🔑 Así que el veredicto lo pone el DUEÑO, una vez por captura, en
    `docs/capturas_prueba/velas.md`. La máquina mide; la persona decide. Es más
    lento y es lo único que ha dejado de fallar.
    """
    return 'medir no basta — ver docs/capturas_prueba/velas.md'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--imagen', required=True)
    ap.add_argument('--x0', type=int)
    ap.add_argument('--x1', type=int)
    ap.add_argument('--y0', type=int)
    ap.add_argument('--y1', type=int)
    a = ap.parse_args()
    filas = analiza(a.imagen, a.x0, a.x1, a.y0, a.y1)
    print('%-20s %7s %9s %-22s %s'
          % ('color', '% panel', 'racha max', 'anchos más comunes', 'qué es'))
    print('-' * 104)
    for f in filas:
        modas = ' '.join('%dpx×%d' % (w, c) for w, c in f['modas'])
        print('rgb%-17s %6.1f%% %7d px %-22s %s'
              % (str(f['rgb']), 100 * f['frac'], f['max'], modas, veredicto(f)))
    print()
    print('🔴 NO afirmar NADA sobre el color o el relleno de las velas sin esta')
    print('   salida delante. El historial de este proyecto dice que si se')
    print('   adivina, se adivina mal — y siempre en la misma dirección.')
