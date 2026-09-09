# -*- coding: utf-8 -*-
"""LAS FLECHAS DE ENTRADA Y SALIDA que el trader dibuja en su captura.

    python3 tools/flechas.py --imagen docs/capturas_prueba/mes_ote_perdedor.png
    python3 tools/flechas.py --probar

🔴 NO TOCA EL ANALIZADOR DEL SITIO. Vive en tools/, la app no lo importa.

═══ POR QUÉ EXISTE ═══
El sitio YA le pide al trader que marque su entrada y su salida con flechas, y
el dueño las había puesto. Nuestra cadena las tiraba a la basura: lee solo
geometría de velas, así que el bloque de hechos no sabía dónde entró nadie.

Eso hundía el análisis entero y no se veía. Sin la entrada, **ningún hecho es
más relevante que otro**: el modelo recibía 53 líneas ordenadas de la vela 1 a
la 101, cogía las tres primeras y escribía en genérico. Con la entrada, la
lista se ordena sola — lo que pasó JUSTO ANTES y JUSTO DESPUÉS de entrar es el
análisis, y el resto es contexto.

Medido sobre la captura real del dueño: flecha roja en x=612,5 → **vela 81**;
flecha azul en x=703,5 → **vela 93**. En esa ventana los hechos ya calculados
dicen acumulación en 70-78, pierna de manipulación alcista en la 77 y BOS
alcista en la 83 — o sea, exactamente lo que él dijo que faltaba.

═══ CÓMO SE DISTINGUE UNA FLECHA DE TODO LO DEMÁS ═══
Una flecha es una mancha de color VIVO, COMPACTA y PEQUEÑA. Eso la separa de
las cuatro cosas que hay alrededor y que también son rojas o azules:

  · las líneas de fib y de nivel  → miden cientos de px de ancho y 1-2 de alto
  · la marca de agua de la sesión ("London")  → letras de 30x40, más grandes
  · las cajas translúcidas de killzone  → enormes
  · el logo y los iconos de la plataforma  → viven FUERA del panel de velas

⚠️ TRAMPA MEDIDA, y por poco deja el detector inservible: **la flecha roja de
   la captura real cae encima de una caja translúcida y sale LAVADA** — su
   color es (171,84,87), no un rojo puro. Un umbral de saturación pensado para
   colores limpios la pierde. Por eso el listón va bajo y la criba de verdad la
   hacen el TAMAÑO y la FORMA, no el color.

⚠️ SEGUNDA TRAMPA: filtrar por "las manchas más grandes" es exactamente al
   revés. Las letras de la marca de agua tienen 600-800 px y la flecha 44. Si
   se ordena por tamaño, la flecha no entra ni en las diez primeras.

🔑 CUÁL ES LA ENTRADA Y CUÁL LA SALIDA: **la de más a la izquierda es la
   entrada**. No se decide por el color ni por hacia dónde apunta — un corto se
   marca con flecha roja hacia abajo en una plataforma y con otra cosa en la
   siguiente, pero el tiempo va siempre de izquierda a derecha.
"""
from __future__ import print_function

import argparse
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

# Una flecha, en píxeles. Generosos a propósito: sobra con la forma.
ANCHO = (6, 34)
ALTO = (8, 44)
AREA = (25, 260)
# Alto/ancho. Una flecha es más o menos cuadrada; una línea de nivel no.
PROPORCION = (0.5, 3.0)
# Cuánto tiene que destacar el color sobre su propio gris.
SATURACION = 55
# Qué parte del recuadro llena la mancha. Una flecha llena poco (es un
# triángulo sobre un palo); un cuadrado de color lleno, casi todo.
LLENADO_MAX = 0.72


def _manchas(a, x0, x1, y0, y1):
    """Manchas de color vivo dentro del panel, por canal dominante."""
    sub = a[y0:y1, x0:x1]
    mx, mn = sub.max(2), sub.min(2)
    vivo = (mx - mn) > SATURACION
    out = []
    for canal in (0, 1, 2):
        m = vivo & (sub[:, :, canal] == mx) & (mx > 110)
        et, n = ndimage.label(m)
        if not n:
            continue
        for ys, xs in ((np.nonzero(et == i + 1)) for i in range(n)):
            w = xs.max() - xs.min() + 1
            h = ys.max() - ys.min() + 1
            if not (ANCHO[0] <= w <= ANCHO[1] and ALTO[0] <= h <= ALTO[1]):
                continue
            if not (AREA[0] <= len(xs) <= AREA[1]):
                continue
            if not (PROPORCION[0] <= h / float(w) <= PROPORCION[1]):
                continue
            if len(xs) / float(w * h) > LLENADO_MAX:
                continue
            anchos = np.array([(et[y] == et[ys[0], xs[0]]).sum()
                               for y in range(ys.min(), ys.max() + 1)])
            cabeza = ys.min() + int(np.argmax(anchos))
            arriba = cabeza < (ys.min() + ys.max()) / 2.0
            out.append({'x0': int(xs.min() + x0), 'x1': int(xs.max() + x0),
                        'y0': int(ys.min() + y0), 'y1': int(ys.max() + y0),
                        'cx': (int(xs.min()) + int(xs.max())) / 2.0 + x0,
                        'punta': int((ys.min() if arriba else ys.max()) + y0),
                        'apunta': 'arriba' if arriba else 'abajo',
                        'px': int(len(xs)),
                        'color': tuple(int(v) for v in
                                       sub[ys[len(ys) // 2], xs[len(xs) // 2]])})
    return out


def _sin_repetir(ms):
    """La misma flecha sale una vez por canal dominante. Se queda la mayor."""
    ms = sorted(ms, key=lambda m: -m['px'])
    out = []
    for m in ms:
        if any(abs(m['cx'] - o['cx']) < 12 and abs(m['punta'] - o['punta']) < 20
               for o in out):
            continue
        out.append(m)
    return out


def _sin_columnas_de_iconos(ms, minimo=3):
    """Fuera las MARCAS REPETIDAS de la interfaz.

    🔴 Cazado con los controles negativos, que es justo para lo que están. En
    dos capturas sin ninguna flecha salían seis manchas apiladas en la MISMA
    columna, todas de 28 px y del mismo color (187,66,76): son las etiquetas
    rojas de precio de la plataforma, no dibujos del trader.

    🔑 La regla que las separa no es el color ni el tamaño —son idénticos a los
    de una flecha— sino que **se REPITEN**. Un trader marca una entrada y una
    salida; no apila seis marcas iguales en la misma vertical."""
    fuera = set()
    for i, m in enumerate(ms):
        iguales = [j for j, o in enumerate(ms)
                   if abs(o['cx'] - m['cx']) <= 20
                   and abs(o['px'] - m['px']) <= 4
                   and sum(abs(o['color'][k] - m['color'][k])
                           for k in range(3)) <= 60]
        if len(iguales) >= minimo:
            fuera.update(iguales)
    return [m for i, m in enumerate(ms) if i not in fuera]


def mascara(a, panel=None, banda=None):
    """Los PÍXELES que ocupan los dibujos del trader (flechas y marcas).

    \U0001f511 SE DEVUELVE LA MANCHA ENTERA, no una lista de recuadros. El extractor
    de velas no necesita saber cuál es la entrada: necesita saber **qué píxeles
    no son vela**, y eso es el objeto completo.

    \u26a0\ufe0f Aquí NO importa que se cuelen falsos positivos —un icono de la
    plataforma, la etiqueta de un fib—. Al medir velas, tratar un icono como
    "no es vela" es CORRECTO. La precisión del detector solo importa cuando hay
    que decidir cuál de las manchas es la ENTRADA del trader, que es otro uso
    (ver `busca`)."""
    H, W = a.shape[:2]
    x0, x1 = (panel or (0, W))
    y0, y1 = (banda or (0, H))
    x0, x1 = max(0, x0), min(W, x1)
    y0, y1 = max(0, y0), min(H, y1)
    sub = a[y0:y1, x0:x1]
    mx, mn = sub.max(2), sub.min(2)
    vivo = (mx - mn) > SATURACION
    out = np.zeros((H, W), bool)
    for canal in (0, 1, 2):
        m = vivo & (sub[:, :, canal] == mx) & (mx > 110)
        et, n = ndimage.label(m)
        if not n:
            continue
        for i in range(n):
            ys, xs = np.nonzero(et == i + 1)
            w = xs.max() - xs.min() + 1
            h = ys.max() - ys.min() + 1
            if not (ANCHO[0] <= w <= ANCHO[1] and ALTO[0] <= h <= ALTO[1]):
                continue
            if not (AREA[0] <= len(xs) <= AREA[1]):
                continue
            if not (PROPORCION[0] <= h / float(w) <= PROPORCION[1]):
                continue
            out[ys + y0, xs + x0] = True
    return out


def candidatas(ruta, panel=None, banda=None):
    """Todas las manchas con FORMA de flecha dentro del panel.

    🔴 ESTO NO ES LA RESPUESTA, ES LA LISTA CORTA. Medido sobre las cuatro
    capturas de prueba: encuentra las dos flechas reales siempre, pero en la
    del due\u00f1o devuelve 6 candidatas y en capturas SIN ninguna flecha devuelve
    entre 1 y 5. Los p\u00edxeles saben decir "aqu\u00ed hay una mancha compacta de color
    con forma de flecha"; **no saben decir si es el dibujo del trader o un
    icono de la plataforma**, porque son id\u00e9nticos en tama\u00f1o, color y forma.

    \u26a0\ufe0f Estuve tres rondas apretando umbrales contra estas cuatro im\u00e1genes.
    Baj\u00f3 de 12 falsos a 5 y ah\u00ed se atasc\u00f3, que es la se\u00f1al de que el camino no
    da m\u00e1s: afinar m\u00e1s es memorizar estas capturas, no detectar flechas. Es el
    MISMO error que hundi\u00f3 a `lee_grafico.py` intentando separar velas de
    l\u00edneas de fib a base de p\u00edxeles."""
    a = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
    H, W = a.shape[:2]
    x0, x1 = (panel or (0, W))
    y0, y1 = (banda or (int(H * 0.12), int(H * 0.92)))
    ms = _sin_repetir(_manchas(a, max(0, x0), min(W, x1),
                               max(0, y0), min(H, y1)))
    return sorted(_sin_columnas_de_iconos(ms), key=lambda m: m['cx'])


def busca(ruta, pistas=None, panel=None, banda=None):
    """Las flechas de la captura, de izquierda a derecha.

    🔑 EL REPARTO DE SIEMPRE, y van cinco veces que sale el mismo: **el
    modelo dice cu\u00e1l es, los p\u00edxeles dicen d\u00f3nde exactamente.** `pistas` son las
    posiciones aproximadas que devuelve el modelo al preguntarle \u00abd\u00f3nde marc\u00f3 el
    trader su entrada y su salida\u00bb \u2014 una pregunta de reconocimiento, que es en
    lo que es bueno. Cada pista se ENGANCHA a la candidata m\u00e1s cercana, y esa
    candidata trae el p\u00edxel exacto.

    Sin `pistas` se devuelven las candidatas en crudo: \u00fatil para depurar, NO
    fiable como respuesta. Ver `candidatas`."""
    ms = candidatas(ruta, panel, banda)
    if not pistas:
        return ms
    eleg = []
    for (px, py) in pistas:
        cand = [m for m in ms if m not in eleg]
        if not cand:
            continue
        # \u26a0\ufe0f Se pesa M\u00c1S la x que la y: el modelo sit\u00faa mal en vertical (177 px
        #    de error midiendo el eje de precios) y bastante mejor en horizontal.
        #    Y lo que hace falta para anclar el an\u00e1lisis es la COLUMNA, o sea la
        #    vela: un error vertical no cambia de vela.
        eleg.append(min(cand, key=lambda m: (m['cx'] - px) ** 2
                        + ((m['y0'] + m['y1']) / 2.0 - py) ** 2 * 0.25))
    return sorted(eleg, key=lambda m: m['cx'])


def en_velas(flechas, velas):
    """Cada flecha, a número de vela. La primera es la ENTRADA."""
    if not velas:
        return []
    cx = np.array([(v['x0'] + v['x1']) / 2.0 for v in velas])
    out = []
    for i, f in enumerate(flechas):
        k = int(np.argmin(np.abs(cx - f['cx'])))
        out.append(dict(f, vela=k,
                        papel='entrada' if i == 0 else
                              ('salida' if i == len(flechas) - 1 else 'marca')))
    return out


def probar():
    """Verdad: la captura del dueño tiene DOS flechas, en las velas 81 y 93.

    ⚠️ Y las otras capturas de prueba NO tienen ninguna. Ese control negativo
    vale tanto como el positivo: un detector que encuentra flechas donde no las
    hay pondría la entrada del trader en una vela cualquiera, y todo el análisis
    se ordenaría alrededor de un punto inventado."""
    import analizador2 as A2
    hechos, mal = [0], []

    def caso(n, cond, extra=''):
        hechos[0] += 1
        print(('  ✅ %s' if cond else '  🔴 %s %s') % (n, extra) if not cond
              else '  ✅ %s' % n)
        if not cond:
            mal.append(n)

    d = os.path.join(RAIZ, 'docs', 'capturas_prueba')
    import recorta_grafico as RG
    def _panel(p):
        q = RG.panel(p)
        return (q['x0'], q['x1']) if q else None
    ruta = os.path.join(d, 'mes_ote_perdedor.png')
    fs = busca(ruta, panel=_panel(ruta))
    caso('encuentra exactamente 2 flechas', len(fs) == 2,
         [(f['x0'], f['y0'], f['apunta']) for f in fs])
    if len(fs) == 2:
        caso('la primera apunta abajo (corto)', fs[0]['apunta'] == 'abajo',
             fs[0]['apunta'])
        caso('la segunda apunta arriba', fs[1]['apunta'] == 'arriba',
             fs[1]['apunta'])
        caso('la primera está en x 608-617',
             608 <= fs[0]['x0'] <= 612 and 613 <= fs[0]['x1'] <= 620,
             (fs[0]['x0'], fs[0]['x1']))
        caso('la segunda está en x 698-709',
             696 <= fs[1]['x0'] <= 700 and 707 <= fs[1]['x1'] <= 712,
             (fs[1]['x0'], fs[1]['x1']))
        col = os.path.join(RAIZ, 'out', 'analizador2',
                           'columnas_mes_ote_perdedor.txt')
        if os.path.exists(col):
            r = A2.analiza(ruta, cajas=A2.lee_columnas('@' + col), verboso=False)
            ev = en_velas(fs, r['velas'])
            caso('la entrada cae en la vela 81', ev[0]['vela'] == 81,
                 ev[0]['vela'])
            caso('la salida cae en la vela 93', ev[1]['vela'] == 93,
                 ev[1]['vela'])
            caso('y la primera se marca como entrada',
                 ev[0]['papel'] == 'entrada' and ev[1]['papel'] == 'salida')

    for otra in ('mes_5m.png', 'mnq_5m.png', 'mnq_5m_zoom.png'):
        p = os.path.join(d, otra)
        if os.path.exists(p):
            f = busca(p, panel=_panel(p))
            caso('%s NO tiene flechas' % otra, not f,
                 [(x['x0'], x['y0'], x['px'], x['color']) for x in f])

    print()
    print('%d/%d' % (hechos[0] - len(mal), hechos[0]))
    if mal:
        print('FALLAN:', mal)
    return not mal


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--imagen')
    ap.add_argument('--probar', action='store_true')
    a = ap.parse_args()
    if a.probar:
        sys.exit(0 if probar() else 1)
    if not a.imagen:
        ap.print_help()
        sys.exit(0)
    for i, f in enumerate(busca(a.imagen)):
        print('flecha %d · x %d-%d · y %d-%d · apunta %s · punta en y=%d · %s'
              % (i + 1, f['x0'], f['x1'], f['y0'], f['y1'], f['apunta'],
                 f['punta'], 'ENTRADA' if i == 0 else 'salida'))
