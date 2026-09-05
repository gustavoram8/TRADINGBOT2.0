# -*- coding: utf-8 -*-
"""PRUEBA BACKSTAGE (2/2) — los HECHOS de ICT/SMC, calculados sobre el OHLC.

    python3 tools/hechos_grafico.py --probar

🔴 NO TOCA EL ANALIZADOR. Igual que `lee_grafico.py`: vive en tools/, nadie lo
   importa, y el sitio sigue funcionando exactamente igual.

`lee_grafico.py` saca la serie OHLC del píxel. Este archivo demuestra la otra
mitad de la tesis: **con el OHLC, todo lo que hoy el modelo no puede juzgar
pasa a ser aritmética**. Nada de esto es percepción ni opinión — son
definiciones, y una definición se calcula.

    ruptura de nivel      →  cierre > nivel
    midpoint (CE) tocado  →  mínimo <= CE <= máximo
    liquidez tomada       →  mínimo < mínimo previo  Y  cierre por encima
    FVG                   →  mínimo[i] > máximo[i-2]
    order block           →  última vela opuesta antes del desplazamiento
    BOS                   →  cierre más allá del swing anterior

⚠️ LA VERDAD ES POR CONSTRUCCIÓN. Cada escenario se ARMA sabiendo dónde está
   el FVG, la barrida o el order block, y después se comprueba que el detector
   los encuentra **en ese índice exacto**. No vale "encontró algún FVG": tiene
   que ser EL de la vela que se construyó.

⚠️ Esto NO mide robustez ante screenshots reales — eso es `lee_grafico.py` con
   capturas de verdad, y no hay forma de sustituirlo dibujando uno mismo.
"""
from __future__ import print_function

import argparse
import sys

# Una vela es (apertura, máximo, mínimo, cierre). En PRECIO, no en píxeles.


def _o(v): return v[0]
def _h(v): return v[1]
def _l(v): return v[2]
def _c(v): return v[3]


def swings(ohlc, k=2):
    """Máximos y mínimos de giro: una vela cuyo extremo supera a las `k` de
    cada lado. Es la base de todo lo demás — sin swings no hay ni BOS ni
    liquidez que barrer.

    ⚠️ Las `k` primeras y últimas velas NO pueden ser swing: les falta un lado.
    Contarlas es el error clásico que inventa rupturas al borde del gráfico."""
    out = []
    for i in range(k, len(ohlc) - k):
        vec = ohlc[i - k:i] + ohlc[i + 1:i + k + 1]
        if all(_h(ohlc[i]) > _h(v) for v in vec):
            out.append((i, 'alto', _h(ohlc[i])))
        if all(_l(ohlc[i]) < _l(v) for v in vec):
            out.append((i, 'bajo', _l(ohlc[i])))
    return out


def fvgs(ohlc):
    """Fair Value Gaps: el hueco de tres velas que el precio no negoció.

    Alcista: el mínimo de la 3ª queda POR ENCIMA del máximo de la 1ª. El hueco
    es esa franja, y su CE (consequent encroachment) es la mitad exacta."""
    out = []
    for i in range(2, len(ohlc)):
        a, c = ohlc[i - 2], ohlc[i]
        if _l(c) > _h(a):
            out.append({'i': i, 'tipo': 'alcista', 'suelo': _h(a), 'techo': _l(c)})
        elif _h(c) < _l(a):
            out.append({'i': i, 'tipo': 'bajista', 'suelo': _h(c), 'techo': _l(a)})
    for g in out:
        g['ce'] = (g['suelo'] + g['techo']) / 2.0
        g['tamano'] = g['techo'] - g['suelo']
    return out


def invertidos(ohlc, gaps):
    """IFVG — un FVG que el precio ATRAVESÓ por completo y que, a partir de
    ahí, actúa al revés (el alcista pasa a ser resistencia).

    🔑 No basta con que el precio lo toque: tiene que CERRAR al otro lado. Un
    FVG perforado por una mecha sigue vivo; ese matiz es justo lo que separa
    'zona respetada' de 'zona invalidada', y es una comparación, no una
    impresión."""
    out = []
    for g in gaps:
        for j in range(g['i'] + 1, len(ohlc)):
            roto = (_c(ohlc[j]) < g['suelo'] if g['tipo'] == 'alcista'
                    else _c(ohlc[j]) > g['techo'])
            if roto:
                out.append(dict(g, invertido_en=j,
                                tipo_nuevo=('bajista' if g['tipo'] == 'alcista'
                                            else 'alcista')))
                break
    return out


def barridas(ohlc, k=2):
    """Liquidez tomada: la mecha pasa por debajo de un mínimo de giro anterior
    y la vela CIERRA otra vez por encima. Mecha fuera, cuerpo dentro.

    ⚠️ Si el cierre también queda fuera, eso NO es una barrida: es una
    ruptura. Confundirlas invierte por completo la lectura del trade."""
    out = []
    sw = swings(ohlc, k)
    for i in range(len(ohlc)):
        for (j, tipo, nivel) in sw:
            if j >= i:
                continue
            if tipo == 'bajo' and _l(ohlc[i]) < nivel <= _c(ohlc[i]):
                out.append({'i': i, 'tipo': 'bajo', 'nivel': nivel, 'swing': j})
            elif tipo == 'alto' and _h(ohlc[i]) > nivel >= _c(ohlc[i]):
                out.append({'i': i, 'tipo': 'alto', 'nivel': nivel, 'swing': j})
    return out


def bos(ohlc, k=2):
    """Break of Structure: un CIERRE más allá del swing previo."""
    out, sw = [], swings(ohlc, k)
    for i in range(len(ohlc)):
        for (j, tipo, nivel) in sw:
            if j >= i:
                continue
            if tipo == 'alto' and _c(ohlc[i]) > nivel:
                out.append({'i': i, 'tipo': 'alcista', 'nivel': nivel, 'swing': j})
            elif tipo == 'bajo' and _c(ohlc[i]) < nivel:
                out.append({'i': i, 'tipo': 'bajista', 'nivel': nivel, 'swing': j})
    return out


def bos_eventos(ohlc, k=2):
    """Los BOS como EVENTOS: uno por swing roto, en el instante de la ruptura.

    🔴 POR QUÉ HACE FALTA (medido sobre la captura real del dueño, 2026-09-05).
    `bos()` devuelve todos los pares (vela, swing anterior) que cumplen la
    definición, y eso incluye a la vela que rompe **y a todas las que siguen
    cerrando al otro lado**. Sobre su gráfico salían las velas x=886, 897 y 908
    como tres BOS distintos cuando son **la misma ruptura contada tres veces**.
    Su indicador dibujó UNA marca; nosotros 17.

    Con esto, y con `k=3`, quedan 3 eventos en el recorte y el primero cae en
    x=886 — **la misma vela exacta** donde su indicador puso su etiqueta.

    ⚠️ No sustituye a `bos()`: para preguntar "¿este cierre está más allá de
    aquel swing?" sigue haciendo falta la lista completa. Esto es lo que se le
    enseña a una persona."""
    vistos = {}
    for b in sorted(bos(ohlc, k), key=lambda b: b['i']):
        clave = (b['swing'], b['tipo'])
        if clave not in vistos:
            vistos[clave] = b
    return sorted(vistos.values(), key=lambda b: b['i'])


def order_blocks(ohlc, gaps):
    """El OB se califica por su ORIGEN, no por ser 'la última vela roja'.

    Se busca la última vela de dirección CONTRARIA justo antes del
    desplazamiento que abrió el FVG. Sin FVG detrás no hay desplazamiento, y
    sin desplazamiento eso es una vela cualquiera."""
    out = []
    for g in gaps:
        quiere_alcista = (g['tipo'] == 'alcista')
        for j in range(g['i'] - 1, -1, -1):
            v = ohlc[j]
            opuesta = (_c(v) < _o(v)) if quiere_alcista else (_c(v) > _o(v))
            if opuesta:
                out.append({'i': j, 'tipo': g['tipo'], 'fvg': g['i'],
                            'techo': max(_o(v), _c(v)), 'suelo': min(_o(v), _c(v))})
                break
    return out


def rompe(vela, nivel, arriba=True):
    return _c(vela) > nivel if arriba else _c(vela) < nivel


def toca(vela, nivel):
    return _l(vela) <= nivel <= _h(vela)


# ══════════════════════════════════════════════════════════════════════════
# ESCENARIOS con verdad por construcción
# ══════════════════════════════════════════════════════════════════════════
def _v(o, h, l, c):
    return (o, h, l, c)


def esc_fvg_respetado():
    """FVG alcista, el precio vuelve, toca el CE y rebota sin invalidarlo."""
    o = [_v(100, 101, 99, 100), _v(100, 101, 99.5, 100.5),
         _v(100.5, 104, 100.4, 103.8),          # desplazamiento
         _v(103.8, 106, 103.5, 105.5),          # i=3: mínimo 103.5 > máximo 101 → FVG
         _v(105.5, 105.8, 102.0, 103.0),        # vuelve al hueco y rebota
         _v(103.0, 107, 102.9, 106.5)]
    # el hueco va de 101 (máximo de i=1... ojo: se compara i con i-2) a 103.5
    return o, {'fvg_i': 3, 'fvg_tipo': 'alcista', 'ce': (101 + 103.5) / 2.0,
               'ce_tocado_en': 4, 'invalidado': False}


def esc_fvg_invalidado():
    """El mismo FVG, pero el precio CIERRA por debajo: pasa a ser IFVG."""
    o, _ = esc_fvg_respetado()
    o = o[:4] + [_v(105.5, 105.8, 100.0, 100.4),   # cierra bajo el suelo (101)
                 _v(100.4, 102.5, 100.0, 100.8)]
    return o, {'fvg_i': 3, 'invertido_en': 4, 'tipo_nuevo': 'bajista'}


def esc_barrida():
    """Mecha por debajo del mínimo de giro y cierre otra vez arriba."""
    o = [_v(100, 101, 99.0, 100.5), _v(100.5, 101, 99.8, 100.2),
         _v(100.2, 100.5, 98.0, 98.4),        # i=2: mínimo de giro en 98.0
         _v(98.4, 100.0, 98.3, 99.8), _v(99.8, 100.6, 99.5, 100.2),
         _v(100.2, 100.4, 97.2, 100.1),       # i=5: mecha a 97.2, cierra en 100.1
         _v(100.1, 102.0, 100.0, 101.8)]
    return o, {'barrida_i': 5, 'nivel': 98.0}


def esc_bos():
    """Cierre por encima del máximo de giro: ruptura, no barrida."""
    o = [_v(100, 101.0, 99.5, 100.4), _v(100.4, 102.5, 100.2, 102.2),
         _v(102.2, 103.0, 101.0, 101.3),      # i=2: máximo de giro en 103.0
         _v(101.3, 101.8, 100.0, 100.4), _v(100.4, 101.2, 100.1, 101.0),
         _v(101.0, 104.5, 100.9, 104.2),      # i=5: CIERRA en 104.2 > 103.0
         _v(104.2, 105.0, 103.8, 104.6)]
    return o, {'bos_i': 5, 'nivel': 103.0}


def esc_order_block():
    """La última vela bajista antes del desplazamiento que abre el FVG."""
    o = [_v(100, 100.8, 99.6, 100.2),
         _v(100.2, 100.4, 99.0, 99.2),        # i=1: BAJISTA → este es el OB
         _v(99.2, 103.5, 99.1, 103.2),        # desplazamiento
         _v(103.2, 105, 101.0, 104.5),        # i=3: mínimo 101.0 > máximo 100.4 → FVG
         _v(104.5, 106, 104.0, 105.6)]
    return o, {'ob_i': 1, 'fvg_i': 3}


def probar():
    # ⚠️ El total se CUENTA, no se escribe a mano: lo tenía fijo en 17 cuando
    #    las comprobaciones eran 15, y un test que se inventa su propio marcador
    #    no sirve para nada.
    hechos, mal = [0], []

    def caso(n, cond, extra=''):
        hechos[0] += 1
        if cond:
            print('  ✅ %s' % n)
        else:
            print('  🔴 %s %s' % (n, extra))
            mal.append(n)
        return cond

    print('── FVG alcista respetado ──')
    o, t = esc_fvg_respetado()
    g = fvgs(o)
    caso('detecta exactamente 1 FVG', len(g) == 1, len(g))
    if g:
        caso('en la vela %d' % t['fvg_i'], g[0]['i'] == t['fvg_i'], g[0]['i'])
        caso('alcista', g[0]['tipo'] == t['fvg_tipo'], g[0]['tipo'])
        caso('CE = %.2f' % t['ce'], abs(g[0]['ce'] - t['ce']) < 1e-6, g[0]['ce'])
        caso('el CE se toca en la vela %d' % t['ce_tocado_en'],
             toca(o[t['ce_tocado_en']], g[0]['ce']))
        caso('NO queda invalidado', not invertidos(o, g))

    print('── el mismo FVG, invalidado (IFVG) ──')
    o, t = esc_fvg_invalidado()
    g = fvgs(o)
    inv = invertidos(o, g)
    caso('lo marca como invertido', len(inv) == 1, len(inv))
    if inv:
        caso('en la vela %d' % t['invertido_en'],
             inv[0]['invertido_en'] == t['invertido_en'], inv[0]['invertido_en'])
        caso('pasa a %s' % t['tipo_nuevo'], inv[0]['tipo_nuevo'] == t['tipo_nuevo'])

    print('── barrida de liquidez ──')
    o, t = esc_barrida()
    b = barridas(o)
    caso('encuentra la barrida', any(x['i'] == t['barrida_i'] and
                                     abs(x['nivel'] - t['nivel']) < 1e-6 for x in b),
         [(x['i'], x['nivel']) for x in b])
    caso('y NO la llama ruptura',
         not any(x['i'] == t['barrida_i'] and x['tipo'] == 'bajista' for x in bos(o)))

    print('── BOS (ruptura de verdad) ──')
    o, t = esc_bos()
    br = bos(o)
    caso('encuentra el BOS en la vela %d' % t['bos_i'],
         any(x['i'] == t['bos_i'] and abs(x['nivel'] - t['nivel']) < 1e-6
             for x in br), [(x['i'], x['nivel']) for x in br])
    caso('y NO lo llama barrida',
         not any(x['i'] == t['bos_i'] and x['tipo'] == 'alto' for x in barridas(o)))
    # 🔑 El mismo swing roto no puede contarse dos veces. Sobre el gráfico real
    # del dueño, tres velas seguidas cerraban al otro lado del mismo swing y
    # salían como tres BOS; su indicador dibujó UNA marca.
    ev = bos_eventos(o)
    caso('un solo EVENTO por swing roto',
         len(ev) == len({(x['swing'], x['tipo']) for x in bos(o)}), len(ev))
    caso('el evento cae en la PRIMERA vela que rompe',
         all(x['i'] == min(y['i'] for y in bos(o)
                           if (y['swing'], y['tipo']) == (x['swing'], x['tipo']))
             for x in ev))

    print('── order block ──')
    o, t = esc_order_block()
    g = fvgs(o)
    obs = order_blocks(o, g)
    caso('hay FVG en la vela %d' % t['fvg_i'], any(x['i'] == t['fvg_i'] for x in g),
         [x['i'] for x in g])
    caso('el OB es la vela %d' % t['ob_i'], any(x['i'] == t['ob_i'] for x in obs),
         [x['i'] for x in obs])

    print()
    print('%d/%d' % (hechos[0] - len(mal), hechos[0]))
    if mal:
        print('FALLAN:', mal)
    return not mal


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--probar', action='store_true')
    a = ap.parse_args()
    if a.probar:
        sys.exit(0 if probar() else 1)
    ap.print_help()
