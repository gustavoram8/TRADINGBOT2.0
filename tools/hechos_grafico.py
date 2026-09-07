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


def _rango_mediano(ohlc):
    r = sorted(_h(v) - _l(v) for v in ohlc)
    return r[len(r) // 2] if r else 0.0


def estado_fvgs(ohlc, gaps=None):
    """En qué quedó cada FVG. Esta es la pregunta que hace un trader.

    🔴 POR QUÉ EXISTE. `fvgs()` dice DÓNDE hay un hueco; `invertidos()` dice si
    murió. Faltaba lo de en medio, que es justo lo que se pregunta mirando el
    gráfico propio: *¿el mío se tocó siquiera?*. Cuatro estados, excluyentes y
    en orden de gravedad:

        intacto     el precio no volvió a entrar en la franja
        tocado      entró, pero no llegó al CE
        ce          llegó al midpoint (el 50% del hueco)
        lleno       lo recorrió entero (llegó al borde lejano)
        invertido   CERRÓ al otro lado — deja de ser soporte y pasa a techo

    ⚠️ Tocar NO es cerrar. Una mecha dentro del hueco lo deja vivo; el estado
    `invertido` exige cierre, igual que en `invertidos()`. Esa distinción es la
    diferencia entre 'la zona aguantó' y 'la zona falló', y confundirla da la
    vuelta al análisis entero."""
    if gaps is None:
        gaps = fvgs(ohlc)
    out = []
    for g in gaps:
        e = dict(g, estado='intacto', tocado_en=None, ce_en=None,
                 lleno_en=None, invertido_en=None)
        # borde LEJANO: el que el precio tiene que recorrer para llenarlo.
        lejano = g['suelo'] if g['tipo'] == 'alcista' else g['techo']
        for j in range(g['i'] + 1, len(ohlc)):
            v = ohlc[j]
            if e['tocado_en'] is None and _l(v) <= g['techo'] and _h(v) >= g['suelo']:
                e['tocado_en'] = j
                e['estado'] = 'tocado'
            if e['ce_en'] is None and _l(v) <= g['ce'] <= _h(v):
                e['ce_en'] = j
                e['estado'] = 'ce'
            if e['lleno_en'] is None and _l(v) <= lejano <= _h(v):
                e['lleno_en'] = j
                e['estado'] = 'lleno'
            roto = (_c(v) < g['suelo'] if g['tipo'] == 'alcista'
                    else _c(v) > g['techo'])
            if roto:
                e['invertido_en'] = j
                e['estado'] = 'invertido'
                break
        out.append(e)
    return out


def piscinas(ohlc, k=2, tol_frac=0.40, min_toques=2):
    """BSL / SSL — liquidez en reposo: máximos (o mínimos) IGUALES.

    Un nivel donde dos o más giros dejaron su extremo casi a la misma altura.
    Ahí duermen las órdenes de stop, y por eso el precio va a buscarlo.

    🔑 Se agrupan SWINGS, no todas las velas. Con todas las velas, un tramo
    lateral de veinte velas produce 'un nivel con 19 toques', que no es una
    piscina: es la propia lateralidad contada vela a vela. Medido sobre la
    captura real del dueño: con todos los máximos salían niveles de 19 toques;
    con giros, la lista se vuelve legible.

    ⚠️ EL ENCADENADO. Al agrupar por cercanía hay que comparar contra el PRIMER
    nivel del grupo, no contra el anterior: si cada uno está dentro de la
    tolerancia del que le precede, una deriva larga se traga el gráfico entero
    y el 'nivel' resultante no existe en ninguna parte.

    `tomada_en` = la primera vela POSTERIOR al último toque que atraviesa el
    nivel con su mecha. Mientras sea None, esa liquidez sigue arriba (o abajo)
    sin recoger — que es lo que se quiere saber ANTES de entrar."""
    tol = tol_frac * _rango_mediano(ohlc)
    sw = swings(ohlc, k)
    out = []
    for lado, etiqueta in (('alto', 'BSL'), ('bajo', 'SSL')):
        pts = sorted((niv, i) for (i, t, niv) in sw if t == lado)
        grupo = []
        for niv, i in pts:
            if grupo and (niv - grupo[0][0]) > tol:
                out.append(_piscina(ohlc, grupo, lado, etiqueta, min_toques))
                grupo = []
            grupo.append((niv, i))
        if grupo:
            out.append(_piscina(ohlc, grupo, lado, etiqueta, min_toques))
    return sorted([p for p in out if p], key=lambda p: p['i'])


def _piscina(ohlc, grupo, lado, etiqueta, min_toques):
    if len(grupo) < min_toques:
        return None
    velas = sorted(i for _n, i in grupo)
    nivel = sum(n for n, _i in grupo) / float(len(grupo))
    tomada = None
    for j in range(velas[-1] + 1, len(ohlc)):
        if (_h(ohlc[j]) > nivel) if lado == 'alto' else (_l(ohlc[j]) < nivel):
            tomada = j
            break
    return {'i': velas[-1], 'tipo': etiqueta, 'lado': lado, 'nivel': nivel,
            'velas': velas, 'toques': len(velas), 'tomada_en': tomada}


def manipulacion(ohlc, k=2, ventana=3):
    """La PIERNA DE MANIPULACIÓN: barrida + reacción contraria inmediata.

    No es una vela suelta ni una impresión. Son dos hechos encadenados:
      1. una vela se lleva por delante un extremo previo y CIERRA de vuelta
         dentro (eso ya lo da `barridas`), y
      2. en las `ventana` velas siguientes aparece un desplazamiento en
         sentido CONTRARIO — un FVG o un BOS al otro lado.

    🔑 El paso 2 es lo que la separa de una barrida cualquiera. Una barrida sin
    reacción es solo una mecha larga; lo que la convierte en manipulación es
    que el precio se dé la vuelta con fuerza justo después. Por eso se compone
    de piezas ya medidas en vez de inventar un detector nuevo."""
    gaps = fvgs(ohlc)
    ev = bos_eventos(ohlc, k)
    out, vistos = [], set()
    for b in sorted(barridas(ohlc, k), key=lambda x: x['i']):
        # 🔴 UNA PIERNA POR SWING BARRIDO, no una por vela. Sobre el gráfico
        #    real del dueño, las velas 44, 45 y 46 salían las tres como
        #    "manipulación que barrió el swing de la vela 29 y se dio la
        #    vuelta con el FVG de la 47": es UN movimiento contado tres veces.
        #    Mismo error, misma cura que en `bos_eventos`.
        if (b['swing'], b['tipo']) in vistos:
            continue
        contra = 'alcista' if b['tipo'] == 'bajo' else 'bajista'
        hasta = b['i'] + ventana
        g = [x['i'] for x in gaps if b['i'] < x['i'] <= hasta and x['tipo'] == contra]
        r = [x['i'] for x in ev if b['i'] < x['i'] <= hasta and x['tipo'] == contra]
        if g or r:
            vistos.add((b['swing'], b['tipo']))
            out.append({'i': b['i'], 'tipo': contra, 'nivel': b['nivel'],
                        'swing': b['swing'], 'fvg': g[0] if g else None,
                        'bos': r[0] if r else None})
    return sorted(out, key=lambda x: x['i'])


def acumulacion(ohlc, minimo=5, solape_max=0.40, crecimiento_max=0.15):
    """Rango / acumulación: un tramo donde las velas se pisan entre sí.

    🔑 LA MEDIDA ES ADIMENSIONAL, a propósito: el ancho total del tramo dividido
    entre la SUMA de los rangos de sus velas. Cinco velas de 30 px en tendencia
    abarcan ~150 px → 1,0. Las mismas cinco solapándose abarcan 55 → 0,37.

    Se eligió así en vez de 'el tramo mide menos que N velas medianas' porque
    esa versión depende de la mediana de TODO el gráfico: un gráfico con una
    zona tranquila y otra violenta declara lateral media pantalla.

    🔴 SEGUNDA CONDICIÓN, Y NO ES ADORNO: el ancho no puede crecer más de un
    `crecimiento_max` al añadir una vela. Sin ella el cociente DILUYE — cazado
    al construir el escenario de prueba: seis velas laterales seguidas de una
    tendencia limpia seguían dando 0,38 en la vela 7, porque la suma de rangos
    crece igual de rápido que el ancho. El tramo lateral se comía dos velas del
    impulso siguiente, que es justo la lectura contraria a la que interesa.
    Una vela que rompe el rango ENSANCHA el rango: eso es lo que se mide.

    ⚠️ Solo se devuelven tramos MAXIMALES. Si 5 velas cumplen, las 4 de dentro
    también cumplen, y sin filtrar salen cuatro 'acumulaciones' que son una."""
    n = len(ohlc)
    bruto = []
    for i in range(n):
        mejor, ancho_prev = None, None
        # 🔴 La ventana se construye vela a vela DESDE `minimo - 1`, no se salta
        #    de golpe a `minimo`. Si se salta, la primera ventana ya puede traer
        #    dentro la vela del impulso y no hay contra qué comparar su ancho:
        #    en el escenario de prueba salían DOS tramos, (0-5) y (2-6), y el
        #    segundo metía la primera vela de la tendencia.
        #    Se empieza en `minimo - 1` y no en 2 porque un rango puede abrirse
        #    con dos velas diminutas: exigirle desde el principio que no se
        #    ensanche mataría rangos legítimos.
        for j in range(i + minimo - 2, n):
            v = ohlc[i:j + 1]
            span = max(_h(x) for x in v) - min(_l(x) for x in v)
            suma = sum(_h(x) - _l(x) for x in v)
            if suma <= 0:
                break
            if ancho_prev is not None and span > ancho_prev * (1 + crecimiento_max):
                break
            ancho_prev = span
            if j - i + 1 < minimo:
                continue
            if span / suma > solape_max:
                break
            mejor = (j, span / suma, span)
        if mejor:
            bruto.append({'i': i, 'fin': mejor[0], 'solape': mejor[1],
                          'ancho': mejor[2],
                          'techo': max(_h(x) for x in ohlc[i:mejor[0] + 1]),
                          'suelo': min(_l(x) for x in ohlc[i:mejor[0] + 1])})
    # 🔴 NI SIQUIERA SE SOLAPAN. Quedarse con los maximales no basta: sobre el
    #    gráfico real salían «velas 1-10», «8-13» y «11-15» como tres
    #    acumulaciones, y ninguna contiene a otra. Un trader ve UN lateral ahí.
    #    Se eligen de forma codiciosa —primero el tramo más largo, y a igualdad
    #    el más temprano— y se descarta todo lo que pise a un ya elegido.
    out = []
    for t in sorted(bruto, key=lambda x: (-(x['fin'] - x['i']), x['i'])):
        if any(t['i'] <= o['fin'] and o['i'] <= t['fin'] for o in out):
            continue
        out.append(t)
    return sorted(out, key=lambda x: x['i'])


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


def esc_piscina():
    """Dos máximos de GIRO casi a la misma altura, y una vela que los barre."""
    o = [_v(100, 101.0, 99.5, 100.5), _v(100.5, 102.0, 100.0, 101.5),
         _v(101.5, 105.0, 101.0, 104.0),      # i=2: giro alto en 105.0
         _v(104.0, 104.2, 102.0, 102.5), _v(102.5, 103.0, 101.0, 101.5),
         _v(101.5, 103.5, 101.0, 103.0),
         _v(103.0, 105.2, 102.5, 104.0),      # i=6: giro alto en 105.2 → BSL
         _v(104.0, 104.5, 102.0, 102.5), _v(102.5, 103.0, 101.0, 101.5),
         _v(101.5, 102.5, 100.5, 102.0),
         _v(102.0, 106.0, 101.5, 105.5)]      # i=10: se lleva la piscina
    return o, {'nivel': 105.1, 'velas': [2, 6], 'tomada_en': 10}


def esc_manipulacion():
    """Barrida del mínimo + desplazamiento alcista inmediato."""
    o, _ = esc_barrida()
    o = o + [_v(101.8, 104.5, 101.0, 104.2)]   # i=7: FVG alcista (101.0 > 100.4)
    return o, {'i': 5, 'tipo': 'alcista', 'fvg': 7}


def esc_acumulacion():
    """Seis velas pisándose y después una tendencia limpia.

    ⚠️ La tendencia está puesta A PROPÓSITO justo detrás: es el caso que
    destapó la dilución del cociente (ver `acumulacion`)."""
    o = [_v(100, 101.0, 99.0, 100.2), _v(100.2, 101.2, 99.2, 99.8),
         _v(99.8, 100.8, 98.8, 100.5), _v(100.5, 101.1, 99.1, 99.4),
         _v(99.4, 100.9, 99.0, 100.6), _v(100.6, 101.0, 98.9, 99.5),
         _v(99.5, 103.0, 99.4, 102.8), _v(102.8, 106.0, 102.5, 105.8),
         _v(105.8, 109.0, 105.5, 108.8), _v(108.8, 112.0, 108.5, 111.8),
         _v(111.8, 115.0, 111.5, 114.8)]
    return o, {'i': 0, 'fin': 5}


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

    print('── estado del FVG (lo que pregunta un trader) ──')
    o, t = esc_fvg_respetado()
    e = estado_fvgs(o)
    caso('el respetado llega al CE y NO se llena',
         len(e) == 1 and e[0]['estado'] == 'ce' and e[0]['lleno_en'] is None,
         [x['estado'] for x in e])
    caso('y dice en qué vela se tocó',
         e and e[0]['tocado_en'] == t['ce_tocado_en'], e and e[0]['tocado_en'])
    o, t = esc_fvg_invalidado()
    # ⚠️ Ese escenario tiene DOS huecos: al desplomarse abre uno bajista. Se
    #    busca por índice, no por posición en la lista — el error que cometí al
    #    escribir el caso, y que el propio test cazó.
    e = [x for x in estado_fvgs(o) if x['i'] == t['fvg_i']]
    caso('el invalidado sale como invertido',
         len(e) == 1 and e[0]['estado'] == 'invertido',
         [(x['i'], x['estado']) for x in estado_fvgs(o)])
    # 🔑 Un FVG al que el precio nunca vuelve tiene que salir INTACTO, no
    #    'tocado'. Es la respuesta literal a "el FVG ni se ha tocado".
    o = esc_fvg_respetado()[0][:4] + [_v(105.5, 108.0, 105.2, 107.8),
                                      _v(107.8, 110.0, 107.5, 109.8)]
    e = estado_fvgs(o)
    caso('un FVG al que el precio no vuelve sale INTACTO',
         len(e) >= 1 and e[0]['estado'] == 'intacto', [x['estado'] for x in e])

    print('── piscinas de liquidez (BSL / SSL) ──')
    o, t = esc_piscina()
    ps = [p for p in piscinas(o) if p['tipo'] == 'BSL']
    caso('encuentra UNA piscina de compras', len(ps) == 1,
         [(p['toques'], round(p['nivel'], 2)) for p in ps])
    if ps:
        caso('con los dos giros %s' % t['velas'], ps[0]['velas'] == t['velas'],
             ps[0]['velas'])
        caso('al nivel %.2f' % t['nivel'], abs(ps[0]['nivel'] - t['nivel']) < 1e-6,
             ps[0]['nivel'])
        caso('y la marca tomada en la vela %d' % t['tomada_en'],
             ps[0]['tomada_en'] == t['tomada_en'], ps[0]['tomada_en'])
    # ⚠️ Sin agrupar por GIROS, un lateral entero se declara "una piscina de N
    #    toques". Se comprueba que un tramo lateral no dispara piscinas de más.
    lat = esc_acumulacion()[0]
    caso('un lateral no inventa una piscina por vela',
         all(p['toques'] <= 3 for p in piscinas(lat)),
         [p['toques'] for p in piscinas(lat)])

    print('── pierna de manipulación ──')
    o, t = esc_manipulacion()
    m = manipulacion(o)
    caso('la marca en la vela %d' % t['i'], any(x['i'] == t['i'] for x in m),
         [x['i'] for x in m])
    caso('en sentido %s' % t['tipo'],
         any(x['i'] == t['i'] and x['tipo'] == t['tipo'] for x in m))
    caso('apoyada en el FVG de la vela %d' % t['fvg'],
         any(x['i'] == t['i'] and x['fvg'] == t['fvg'] for x in m))
    # 🔑 Una barrida SIN reacción NO es manipulación: es una mecha larga.
    caso('una barrida sin reacción NO cuenta', not manipulacion(esc_barrida()[0]),
         manipulacion(esc_barrida()[0]))

    print('── acumulación ──')
    o, t = esc_acumulacion()
    ac = acumulacion(o)
    caso('encuentra UN tramo', len(ac) == 1, [(x['i'], x['fin']) for x in ac])
    if ac:
        caso('de la vela %d a la %d' % (t['i'], t['fin']),
             ac[0]['i'] == t['i'] and ac[0]['fin'] == t['fin'],
             (ac[0]['i'], ac[0]['fin']))
    # 🔴 El caso que destapó la dilución: la tendencia NO puede entrar.
    caso('la tendencia queda FUERA del tramo',
         all(x['fin'] <= t['fin'] for x in ac), [x['fin'] for x in ac])
    caso('una tendencia sola no es acumulación', not acumulacion(o[6:]),
         acumulacion(o[6:]))

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
