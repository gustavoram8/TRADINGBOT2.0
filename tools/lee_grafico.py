# -*- coding: utf-8 -*-
"""PRUEBA BACKSTAGE — reconstruir la serie OHLC desde el PÍXEL de un gráfico.

    python3 tools/lee_grafico.py --probar          # contra gráficos sintéticos
    python3 tools/lee_grafico.py --leer captura.png --pintar salida.png

🔴 NO TOCA EL ANALIZADOR. Vive entero en tools/, no lo importa nadie, y el
   sitio funciona hoy exactamente igual que ayer. Si la prueba sale mal, se
   borra este archivo y no queda rastro.

═══ POR QUÉ EXISTE ═══
Medimos (ver CLAUDE.md, "VISIÓN DEL ANALIZADOR") que GPT-4o detecta elementos
de 2 px y lee texto desde 9 px, pero **no juzga orden vertical a ningún
tamaño**: no sabe si un cierre quedó por encima de un nivel, ni si el RSI está
bajo 30. Ni ampliando la región 4× (`--zoom`) mejora.

🔑 La salida no es buscar un modelo que "vea mejor": es **dejar de pedirle a un
   modelo de lenguaje que mida**. Un screenshot de un gráfico NO es una foto —
   es una imagen sintética de colores planos y rectángulos. Las velas se
   extraen con aritmética de píxeles, exacta y sin opinión.

   Con la serie OHLC reconstruida, todo lo que hoy falla pasa a ser cálculo:
   ruptura = `cierre > nivel`; midpoint tocado = `mínimo <= CE <= máximo`;
   liquidez tomada = `máximo > máximo previo`; y FVG, order blocks, BOS/CHoCH,
   barridas y premium/discount son algoritmos sobre OHLC, no percepciones.
   La IA dejaría de ser el ojo para ser la voz: interpreta hechos ya ciertos.

═══ CÓMO SE SEPARAN CUERPO Y MECHA (la única parte con truco) ═══
Todas las columnas de una vela tienen píxeles de cuerpo; solo las del CENTRO
tienen además mecha. Así que se mide, fila por fila, **cuántas columnas están
pintadas**: las filas del cuerpo ocupan el ancho entero de la vela, las de la
mecha ocupan 1-3 px. El corte va en el 60% del ancho.
⚠️ No sirve buscar "el rectángulo más grande": un doji tiene el cuerpo de 1 px
   de alto y aun así ocupa el ancho completo.
"""
from __future__ import print_function

import argparse
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'out', 'lee_grafico')

# Umbrales de "esto es color de vela". Un gráfico usa verdes y rojos MUY
# saturados; los grises del fondo, la rejilla y el texto del eje no pasan.
DOM = 28          # cuánto tiene que dominar el canal sobre los otros dos
MIN_LUZ = 45      # por debajo es sombra del fondo, no vela
ANCHO_MIN = 3     # una columna suelta es ruido, no una vela
FRAC_CUERPO = 0.60


def _mascaras(a):
    """(alcista, bajista) — máscaras booleanas de píxel de vela."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    verde = (g > r + DOM) & (g > b + DOM // 2) & (g > MIN_LUZ)
    rojo = (r > g + DOM) & (r > b + DOM) & (r > MIN_LUZ)
    return verde, rojo


def extrae(ruta):
    """Las velas del gráfico, en PÍXELES. Cada una:
       x0,x1 · cuerpo_alto/cuerpo_bajo · max/min · alcista

    En píxeles la Y crece hacia abajo, así que `cuerpo_alto` es el número
    MENOR. La conversión a precio es un paso aparte (necesita el eje)."""
    a = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
    verde, rojo = _mascaras(a)
    vela = verde | rojo

    # ── 1. columnas con vela → tramos contiguos ──
    col = vela.any(0)
    tramos, ini = [], None
    for x in range(len(col)):
        if col[x] and ini is None:
            ini = x
        elif not col[x] and ini is not None:
            tramos.append((ini, x - 1))
            ini = None
    if ini is not None:
        tramos.append((ini, len(col) - 1))

    velas = []
    for x0, x1 in tramos:
        ancho = x1 - x0 + 1
        if ancho < ANCHO_MIN:
            continue
        sub = vela[:, x0:x1 + 1]
        filas = sub.sum(1)                    # columnas pintadas por fila
        con = np.where(filas > 0)[0]
        if not len(con):
            continue
        cuerpo = np.where(filas >= max(2, FRAC_CUERPO * ancho))[0]
        if not len(cuerpo):
            # todo mecha: no es una vela, es una línea vertical de otra cosa
            continue
        # el color se decide por MAYORÍA dentro del cuerpo: el borde de una
        # vela puede llevar píxeles de la vecina cuando se tocan.
        cv = verde[cuerpo.min():cuerpo.max() + 1, x0:x1 + 1].sum()
        cr = rojo[cuerpo.min():cuerpo.max() + 1, x0:x1 + 1].sum()
        velas.append({
            'x0': int(x0), 'x1': int(x1),
            'cuerpo_alto': int(cuerpo.min()), 'cuerpo_bajo': int(cuerpo.max()),
            'max': int(con.min()), 'min': int(con.max()),
            'alcista': bool(cv >= cr),
        })
    return velas


def a_precio(velas, y_a, precio_a, y_b, precio_b):
    """Píxeles → precio, con dos referencias del eje (las lee la IA, que en
    OCR acierta el 100% desde 12 px — ahí sí es la herramienta correcta).

    ⚠️ La Y del píxel crece hacia ABAJO y el precio hacia ARRIBA: la pendiente
    sale negativa y por eso `max` (menor Y) da el precio MAYOR."""
    if y_a == y_b:
        raise ValueError('las dos referencias del eje están a la misma altura')
    m = (precio_b - precio_a) / float(y_b - y_a)
    p = lambda y: precio_a + (y - y_a) * m
    fuera = []
    for v in velas:
        alto, bajo = p(v['cuerpo_alto']), p(v['cuerpo_bajo'])
        fuera.append({
            'apertura': bajo if v['alcista'] else alto,
            'cierre': alto if v['alcista'] else bajo,
            'maximo': p(v['max']), 'minimo': p(v['min']),
            'alcista': v['alcista'], 'x': (v['x0'] + v['x1']) / 2.0,
        })
    return fuera


# ══════════════════════════════════════════════════════════════════════════
# LA PRUEBA — gráficos con OHLC conocido por construcción
# ══════════════════════════════════════════════════════════════════════════
FONDO = (14, 17, 23)
REJILLA = (30, 35, 46)
SUBE = (38, 166, 109)
BAJA = (223, 74, 74)
AN, AL = 1600, 900


def _pinta(ohlc, ancho, hueco, y0, y1, p0, p1, ruta):
    """Dibuja la serie y devuelve la verdad en píxeles de cada vela."""
    im = Image.new('RGB', (AN, AL), FONDO)
    d = ImageDraw.Draw(im)
    for y in range(0, AL, 90):
        d.line([(0, y), (AN, y)], fill=REJILLA)
    for x in range(0, AN, 120):
        d.line([(x, 0), (x, AL)], fill=REJILLA)
    ay = (y1 - y0) / float(p1 - p0)
    py = lambda pr: int(round(y0 + (pr - p0) * ay))
    verdad, x = [], 40
    for (o, h, l, c) in ohlc:
        if x + ancho > AN - 200:
            break
        alc = c >= o
        col = SUBE if alc else BAJA
        cx = x + ancho // 2
        yo, yc, yh, yl = py(o), py(c), py(h), py(l)
        d.line([(cx, yh), (cx, yl)], fill=col)
        d.rectangle([x, min(yo, yc), x + ancho - 1, max(yo, yc)], fill=col)
        verdad.append({'x0': x, 'x1': x + ancho - 1,
                       'cuerpo_alto': min(yo, yc), 'cuerpo_bajo': max(yo, yc),
                       'max': yh, 'min': yl, 'alcista': alc})
        x += ancho + hueco
    im.save(ruta)
    return verdad


def _serie(n, semilla):
    rnd = random.Random(semilla)
    p, out = 100.0, []
    for _ in range(n):
        o = p
        c = o + rnd.uniform(-2.2, 2.2)
        h = max(o, c) + rnd.uniform(0.05, 1.6)
        l = min(o, c) - rnd.uniform(0.05, 1.6)
        out.append((o, h, l, c))
        p = c
    return out


def probar():
    if not os.path.isdir(SALIDA):
        os.makedirs(SALIDA)
    # Se varían ancho de vela, hueco y escala del eje: si el extractor solo
    # funciona con UNA geometría, no sirve para screenshots de gente distinta.
    # ⚠️ El margen se calcula DESDE LA SERIE, como hace cualquier gráfico real
    #    al autoescalar. En la primera versión el eje iba fijo (90-118) y la
    #    caminata aleatoria se salía: 2 de 5 gráficos dibujaban casi todas las
    #    velas FUERA del lienzo, y el extractor "fallaba" por leer lo que de
    #    verdad había. Era el test el que estaba mal, no el código.
    casos = [(11, 5, 0.04), (9, 3, 0.12), (13, 6, 0.02), (7, 3, 0.20), (15, 4, 0.08)]
    tot = dict(velas=0, cuerpo=0, mecha=0, color=0, cuenta_ok=0, casos=0)
    for i, (ancho, hueco, esc) in enumerate(casos):
        ohlc = _serie(120, 'g%d' % i)
        ruta = os.path.join(SALIDA, 'sint_%d.png' % i)
        lo = min(l for _o, _h, l, _c in ohlc)
        hi = max(h for _o, h, _l, _c in ohlc)
        mar = (hi - lo) * esc                       # `esc` = margen, 2%-20%
        p0, p1 = lo - mar, hi + mar
        verdad = _pinta(ohlc, ancho, hueco, 820, 120, p0, p1, ruta)
        leidas = extrae(ruta)
        tot['casos'] += 1
        igual = (len(leidas) == len(verdad))
        tot['cuenta_ok'] += igual
        print('caso %d  ancho=%2d hueco=%d  esperadas=%3d leidas=%3d %s'
              % (i, ancho, hueco, len(verdad), len(leidas),
                 '✅' if igual else '🔴'))
        if not igual:
            continue
        for v, l in zip(verdad, leidas):
            tot['velas'] += 1
            tot['cuerpo'] += (v['cuerpo_alto'] == l['cuerpo_alto'] and
                              v['cuerpo_bajo'] == l['cuerpo_bajo'])
            tot['mecha'] += (v['max'] == l['max'] and v['min'] == l['min'])
            tot['color'] += (v['alcista'] == l['alcista'])

    n = max(1, tot['velas'])
    print()
    print('gráficos con el número de velas correcto : %d/%d'
          % (tot['cuenta_ok'], tot['casos']))
    print('cuerpo exacto (apertura y cierre)        : %d/%d  (%.1f%%)'
          % (tot['cuerpo'], n, 100.0 * tot['cuerpo'] / n))
    print('mecha exacta (máximo y mínimo)           : %d/%d  (%.1f%%)'
          % (tot['mecha'], n, 100.0 * tot['mecha'] / n))
    print('dirección (alcista/bajista)              : %d/%d  (%.1f%%)'
          % (tot['color'], n, 100.0 * tot['color'] / n))
    print('\nimágenes en', SALIDA)
    # ⚠️ Esto mide el ALGORITMO, no la robustez. Que acierte al 100% aquí solo
    #    dice que la aritmética es correcta; con screenshots reales aparecen
    #    temas de color raros, indicadores encima de las velas y capturas de
    #    móvil, y ESE es el examen que decide si el camino sirve.
    return tot['cuerpo'] == n and tot['mecha'] == n and tot['color'] == n


def pintar_encima(ruta, salida):
    """Dibuja lo detectado sobre la imagen: la forma de MIRAR si acierta en un
    screenshot real, donde no hay verdad con la que comparar."""
    im = Image.open(ruta).convert('RGB')
    d = ImageDraw.Draw(im)
    for v in extrae(ruta):
        d.rectangle([v['x0'], v['cuerpo_alto'], v['x1'], v['cuerpo_bajo']],
                    outline=(0, 200, 255))
        cx = (v['x0'] + v['x1']) // 2
        d.line([(cx, v['max']), (cx, v['min'])], fill=(255, 0, 255))
    im.save(salida)
    return salida


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--probar', action='store_true')
    ap.add_argument('--leer', metavar='PNG')
    ap.add_argument('--pintar', metavar='PNG')
    a = ap.parse_args()
    if a.probar:
        sys.exit(0 if probar() else 1)
    if a.leer:
        vs = extrae(a.leer)
        print('%d velas detectadas' % len(vs))
        for v in vs[:8]:
            print('  x%4d-%4d  cuerpo %4d-%4d  mecha %4d-%4d  %s'
                  % (v['x0'], v['x1'], v['cuerpo_alto'], v['cuerpo_bajo'],
                     v['max'], v['min'], 'alcista' if v['alcista'] else 'bajista'))
        if a.pintar:
            print('marcado en', pintar_encima(a.leer, a.pintar))
    elif not a.probar:
        ap.print_help()
