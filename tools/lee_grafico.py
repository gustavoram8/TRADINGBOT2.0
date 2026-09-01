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
from scipy import ndimage

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'out', 'lee_grafico')

# ── v3: ni colores fijos, NI SUPONER QUE LAS VELAS SON VERDES Y ROJAS ────
# 🔴 La v1 daba por hecho fondo oscuro y velas saturadas. La v2 aprendió el
#    tono pero seguía asumiendo familias verde/rojo. La primera captura real
#    tumbó las dos: es tema CLARO (fondo rgb(238,243,255)) y **las velas son
#    NEGRAS y GRISES** — rgb(0,0,0) y rgb(74,74,74). Lo verde y lo rojo que yo
#    perseguía era el cajetín de TP/SL de la operación y las cajas de sesión.
#    Lección: cualquier regla de color escrita a mano se rompe con el primer
#    tema distinto. Aquí no se supone NINGÚN color: se miden.
UMBRAL_FONDO = 30   # cuánto tiene que separarse del fondo para ser "algo"
DIB_ANCHO = 26      # ancho a partir del cual una mancha plana es un dibujo
DIB_RAZON = 5.0     # ancho/alto por encima de esto = línea, no vela
MAX_VELA = 30       # ninguna vela es más ancha: lo que lo sea es interfaz
REL_AREA = 2500     # mancha así de grande con UN color dominante = zona
REL_FRAC = 0.45
ANCHO_MIN = 2
FRAC_CUERPO = 0.55


def _area_grafico(a):
    """(fondo, recorte) — el color de fondo del panel y dónde está el panel.

    🔑 No se puede usar el color más repetido de la imagen entera: en la
    captura real ese era el BLANCO de la interfaz, no el rgb(238,243,255) del
    panel, y entonces el gráfico completo contaba como 'algo'. Se busca el
    color plano que cubre el rectángulo más grande — eso es el panel."""
    # ⚠️ TOLERANCIA ANCHA A PROPÓSITO. La captura real venía REESCALADA (778 px
    #    de ancho para un gráfico de TradingView), y el antialiasing descompone
    #    el fondo en muchos tonos casi iguales: 238,243,255 · 247,249,255 · …
    #    Con tolerancia 10 ningún candidato llegaba al 45% de relleno y la
    #    detección del panel fallaba entera. Nada en una captura de pantalla
    #    reescalada es de un solo color.
    cols, cnt = np.unique(a.reshape(-1, 3), axis=0, return_counts=True)
    orden = np.argsort(cnt)[::-1][:8]
    mejor = None
    for k in orden:
        m = (np.abs(a - cols[k]).sum(2) <= 45)
        ys, xs = np.where(m)
        if not len(ys):
            continue
        alto = ys.max() - ys.min() + 1
        ancho = xs.max() - xs.min() + 1
        area = alto * ancho
        # relleno: si el color solo salpica, su caja no representa un panel
        if m.sum() < 0.35 * area or area < 0.10 * a.shape[0] * a.shape[1]:
            continue
        if mejor is None or area > mejor[0]:
            mejor = (area, cols[k], (slice(ys.min(), ys.max() + 1),
                                     slice(xs.min(), xs.max() + 1)))
    if mejor is None:
        return a.reshape(-1, 3)[np.argmax(cnt)], (slice(None), slice(None))
    return mejor[1], mejor[2]


def _quita_rellenos(m, a):
    """Borra las ZONAS de relleno (cajas de sesión, bloques pintados) dejando
    VIVAS las velas de dentro.

    🔴 Una caja translúcida y las velas que cubre forman UNA SOLA mancha
    conectada: borrarla entera se lleva las velas, dejarla la lee como una vela
    gigante. 🔑 La caja tiene UN color plano y las velas otro, así que se borran
    solo los píxeles del color dominante de la mancha."""
    lbl, n = ndimage.label(m)
    if not n:
        return m
    out = m.copy()
    for i, corte in enumerate(ndimage.find_objects(lbl), start=1):
        sy, sx = corte
        alto, ancho = sy.stop - sy.start, sx.stop - sx.start
        if alto * ancho < REL_AREA or ancho <= MAX_VELA or alto < 20:
            continue
        dentro = (lbl[corte] == i)
        pix = a[corte][dentro]
        if not len(pix):
            continue
        cols, cnt = np.unique(pix.reshape(-1, 3), axis=0, return_counts=True)
        j = int(np.argmax(cnt))
        if cnt[j] < REL_FRAC * len(pix):
            continue
        igual = (np.abs(a[corte] - cols[j]).sum(2) <= 12) & dentro
        sub = out[corte]
        sub[igual] = False
        out[corte] = sub
    return out


def _sin_dibujos(m):
    """Fuera las manchas que son LÍNEAS o interfaz, no velas.

    ⚠️ El discriminante NO es el alto: un doji mide 2 px igual que una línea de
    fib. Es la FORMA — ancha y plana = dibujo; ancha a secas = interfaz."""
    lbl, n = ndimage.label(m)
    if not n:
        return m
    fuera = np.zeros(n + 1, dtype=bool)
    for i, (sy, sx) in enumerate(ndimage.find_objects(lbl), start=1):
        alto = sy.stop - sy.start
        ancho = sx.stop - sx.start
        if ancho >= DIB_ANCHO and ancho >= DIB_RAZON * alto:
            fuera[i] = True          # línea horizontal: fib, nivel, borde
        elif ancho > MAX_VELA:
            fuera[i] = True          # bloque de interfaz
        elif alto >= 0.55 * m.shape[0] and ancho <= 5:
            # 🔴 REJILLA VERTICAL. Es estrecha y alta, o sea idéntica a una
            #    vela por forma — pasaba los dos filtros anteriores y salía
            #    como velas con el cuerpo de 600 px. Lo que la delata es que
            #    cruza CASI TODO el alto del panel, cosa que ninguna vela hace.
            fuera[i] = True
    return m & ~fuera[lbl]


def _mascara(a):
    """Máscara de "esto no es el fondo del panel", ya limpia de zonas y
    dibujos. Devuelve también el recorte del panel."""
    fondo, corte = _area_grafico(a)
    sub = a[corte]
    m = np.abs(sub - fondo).max(2) > UMBRAL_FONDO
    m = _sin_dibujos(_quita_rellenos(m, sub))
    lleno = np.zeros(a.shape[:2], dtype=bool)
    lleno[corte] = m
    return lleno, corte


def extrae(ruta):
    """Las velas del gráfico, en PÍXELES:
       x0,x1 · cuerpo_alto/cuerpo_bajo · max/min · alcista

    La Y crece hacia abajo, así que `cuerpo_alto` es el número MENOR."""
    a = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
    vela, _corte = _mascara(a)

    ocup = vela.any(0)
    tramos, ini = [], None
    for x in range(len(ocup)):
        if ocup[x] and ini is None:
            ini = x
        elif not ocup[x] and ini is not None:
            tramos.append((ini, x - 1))
            ini = None
    if ini is not None:
        tramos.append((ini, len(ocup) - 1))

    # El PASO entre velas se mide, no se supone: es el ancho más repetido.
    # Sirve para partir bloques donde dos velas se tocan, que pasa siempre en
    # gráficos comprimidos.
    anchos = [x1 - x0 + 1 for x0, x1 in tramos]
    typ = 0
    if anchos:
        c = {}
        for w in anchos:
            c[w] = c.get(w, 0) + 1
        typ = max(c.items(), key=lambda kv: (kv[1], -kv[0]))[0]

    velas = []
    for x0, x1 in tramos:
        if x1 - x0 + 1 < ANCHO_MIN:
            continue
        trozos = [(x0, x1)]
        if typ >= ANCHO_MIN and (x1 - x0 + 1) >= 2 * typ + 2:
            trozos = [(c0, min(c0 + typ - 1, x1))
                      for c0 in range(x0, x1 + 1, typ)]
        for c0, c1 in trozos:
            w = c1 - c0 + 1
            if w < ANCHO_MIN:
                continue
            filas = vela[:, c0:c1 + 1].sum(1)
            con = np.where(filas > 0)[0]
            if not len(con):
                continue
            cuerpo = np.where(filas >= max(2, FRAC_CUERPO * w))[0]
            if not len(cuerpo):
                continue
            # color dominante DEL CUERPO: es lo que después separa alcistas de
            # bajistas, sea cual sea la paleta del tema.
            reg = a[cuerpo.min():cuerpo.max() + 1, c0:c1 + 1].reshape(-1, 3)
            msk = vela[cuerpo.min():cuerpo.max() + 1, c0:c1 + 1].reshape(-1)
            reg = reg[msk]
            if not len(reg):
                continue
            cols, cnt = np.unique(reg, axis=0, return_counts=True)
            velas.append({
                'x0': int(c0), 'x1': int(c1),
                'cuerpo_alto': int(cuerpo.min()), 'cuerpo_bajo': int(cuerpo.max()),
                'max': int(con.min()), 'min': int(con.max()),
                'color': tuple(int(v) for v in cols[int(np.argmax(cnt))]),
                'alcista': True,
            })
    return _direccion(_solo_la_serie(velas))


def _direccion(velas):
    """Quién es alcista y quién bajista, SIN saber la paleta del tema.

    🔑 Dos pasos. Primero se agrupan las velas por su color de cuerpo en los
    dos más repetidos (negro y gris en el tema claro de TradingView; verde y
    rojo en uno oscuro). Segundo, para decidir cuál de los dos grupos es el
    alcista, se usa una propiedad del propio gráfico: **la apertura de una vela
    cae cerca del cierre de la anterior**. Se prueban las dos asignaciones y
    gana la que hace esa cadena más continua.

    ⚠️ Sin este segundo paso habría que escribir a mano "el claro sube y el
    oscuro baja", que es exactamente la clase de suposición que ya nos rompió
    el detector tres veces."""
    if len(velas) < 4:
        return velas
    cuenta = {}
    for v in velas:
        cuenta[v['color']] = cuenta.get(v['color'], 0) + 1
    top = [c for c, _n in sorted(cuenta.items(), key=lambda kv: -kv[1])[:2]]
    if len(top) < 2:
        for v in velas:
            v['alcista'] = True
        return velas

    def cerca(c):
        d0 = sum((c[i] - top[0][i]) ** 2 for i in range(3))
        d1 = sum((c[i] - top[1][i]) ** 2 for i in range(3))
        return 0 if d0 <= d1 else 1

    grupo = [cerca(v['color']) for v in velas]

    def salto(alcista_es):
        # apertura de i+1 contra cierre de i, en píxeles
        tot = 0.0
        for i in range(len(velas) - 1):
            a_alc = (grupo[i] == alcista_es)
            b_alc = (grupo[i + 1] == alcista_es)
            cierre = velas[i]['cuerpo_alto'] if a_alc else velas[i]['cuerpo_bajo']
            apert = velas[i + 1]['cuerpo_bajo'] if b_alc else velas[i + 1]['cuerpo_alto']
            tot += abs(apert - cierre)
        return tot

    elegido = 0 if salto(0) <= salto(1) else 1
    for v, g in zip(velas, grupo):
        v['alcista'] = (g == elegido)
    return velas


def _solo_la_serie(velas):
    """Se queda con la RETÍCULA de velas y tira lo demás.

    🔴 Sin esto entra la interfaz: en la captura real colaban el botón rojo de
    VENDER, el logo y las etiquetas del eje de precios — 231 "velas" de las
    cuales ninguna lo era.

    🔑 Dos propiedades que un gráfico cumple y la interfaz no: todas las velas
    tienen el MISMO ancho, y están REGULARMENTE espaciadas. Se mide el ancho
    más repetido, se mide el paso más repetido entre vecinas, y se conserva la
    cadena más larga que respeta ese paso. Nada de coordenadas fijas ni de
    suponer dónde empieza el gráfico: sale de los propios datos."""
    if len(velas) < 5:
        return velas
    cuenta = {}
    for v in velas:
        w = v['x1'] - v['x0'] + 1
        cuenta[w] = cuenta.get(w, 0) + 1
    wmod = max(cuenta.items(), key=lambda kv: kv[1])[0]
    cand = sorted([v for v in velas if abs((v['x1'] - v['x0'] + 1) - wmod) <= 1],
                  key=lambda v: v['x0'])
    if len(cand) < 5:
        return velas
    pasos = {}
    for i in range(1, len(cand)):
        d = cand[i]['x0'] - cand[i - 1]['x0']
        if 0 < d <= 60:
            pasos[d] = pasos.get(d, 0) + 1
    if not pasos:
        return cand
    paso = max(pasos.items(), key=lambda kv: kv[1])[0]
    # cadena más larga cuyos saltos son múltiplos del paso (tolera huecos: una
    # vela puede faltar por quedar tapada, y la serie sigue siendo la misma)
    mejor, act = [], [cand[0]]
    for i in range(1, len(cand)):
        d = cand[i]['x0'] - act[-1]['x0']
        k = round(d / float(paso)) if paso else 0
        if k >= 1 and abs(d - k * paso) <= max(1, paso * 0.25) and k <= 4:
            act.append(cand[i])
        else:
            if len(act) > len(mejor):
                mejor = act
            act = [cand[i]]
    if len(act) > len(mejor):
        mejor = act
    return mejor if len(mejor) >= 5 else cand


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
