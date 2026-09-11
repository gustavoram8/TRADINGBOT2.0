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


# ══════════════════════════════════════════════════════════════════════════
# LIQUIDEZ — el mapa completo (2026-09-09, pedido por el dueño)
# ══════════════════════════════════════════════════════════════════════════
# 🔑 POR QUÉ ESTO NO ES "MÁS DE LO MISMO" QUE `piscinas`. `piscinas` contesta
# *dónde hay dos máximos iguales*. Un trader de ICT no pregunta eso: pregunta
# **qué liquidez sigue ahí arriba sin recoger**, cuál ya se llevaron, cuál es
# de las que caen solas y cuál hay que pelearla. Son cuatro preguntas y las
# cuatro son aritmética; lo que faltaba era escribirlas.
#
# El vocabulario, tal cual lo usa él, y qué significa cada pieza AQUÍ:
#     BSL   liquidez del lado de las compras — la que duerme ARRIBA
#     SSL   la del lado de las ventas — ABAJO
#     EQH   dos o más máximos de giro IGUALES (dentro de `tol_eq`)
#     EQL   lo mismo con mínimos
#     REQH  máximos "relativamente" iguales: parecidos, no clavados
#     REQL  ídem con mínimos
#     LRL   liquidez de BAJA resistencia: nada se interpone en el camino
#     HRL   liquidez de ALTA resistencia: hay que atravesar zonas contrarias
#     DOL   los candidatos a "draw on liquidity": lo que queda SIN tomar
#
# ⚠️ DOS TOLERANCIAS, NO UNA, Y EN FRACCIÓN DEL RANGO MEDIANO DE LA VELA. Un
#    número en puntos no sirve: 5 puntos son dos velas en el MES y un cuarto de
#    vela en el NQ. Y hacen falta dos porque "iguales" y "relativamente
#    iguales" son dos etiquetas distintas en su vocabulario, no un matiz.
TOL_EQ = 0.10
TOL_REQ = 0.35


def obstaculos(ohlc, nivel, lado, ref=None):
    """Qué hay EN MEDIO entre el precio y ese nivel. Es lo que separa LRL de HRL.

    🔑 LA DEFINICIÓN QUE SE USA AQUÍ, dicha en voz alta porque es una elección
    y no un hecho de la naturaleza: son obstáculos las zonas de sentido
    CONTRARIO al camino —FVG sin rellenar y order blocks— cuyo rango se cruza
    con la franja que va del cierre actual hasta el nivel. Para subir a buscar
    un BSL estorban las zonas bajistas; para bajar a por un SSL, las alcistas.
    Cero obstáculos = LRL (el precio llega de una tirada). Uno o más = HRL.

    ⚠️ SE MIRA SOLO HASTA `ref`, nunca después. Si se preguntara sobre el
    gráfico entero para juzgar la vela de entrada de alguien, se estaría usando
    información que en ese momento no existía — y el análisis de un trade
    tomado ayer con datos de hoy no vale nada.

    ⚠️ Hereda la precisión de FVG y order block, que son las dos familias más
    flojas del catálogo. Eso NO se disimula: el banco lo mide aparte."""
    if ref is None:
        ref = len(ohlc) - 1
    sub = ohlc[:ref + 1]
    if not sub:
        return []
    g = fvgs(sub)
    c = _c(sub[ref])
    lo, hi = (c, nivel) if nivel > c else (nivel, c)
    contra = 'bajista' if lado == 'alto' else 'alcista'
    out = []
    for e in estado_fvgs(sub, g):
        if e['tipo'] != contra or e['estado'] in ('lleno', 'invertido'):
            continue
        if e['suelo'] <= hi and e['techo'] >= lo:
            out.append({'que': 'FVG', 'i': e['i'],
                        'suelo': e['suelo'], 'techo': e['techo']})
    # ⚠️ Un mismo order block sale UNA VEZ aunque lo hayan parido dos FVG
    #    solapados. Es el mismo error que `_sin_repetir` ya cazó en el bloque:
    #    un obstáculo contado dos veces convierte un LRL flojo en un HRL duro.
    vistos = set()
    for o in order_blocks(sub, g):
        if o['tipo'] != contra or o['i'] in vistos:
            continue
        if o['suelo'] <= hi and o['techo'] >= lo:
            # 🔑 UN ORDER BLOCK ATRAVESADO YA NO ESTORBA, igual que un FVG
            # invalidado. `order_blocks` no lleva estado —a diferencia de
            # `estado_fvgs`— así que se calcula aquí con la misma regla que usa
            # `invertidos`: hace falta un CIERRE al otro lado, no una mecha.
            # Sin esto, un order block de hace cien velas que el precio se pasó
            # por encima hace noventa seguía contando, y cualquier gráfico con
            # recorrido salía HRL — o sea que la etiqueta dejaba de distinguir.
            if _atravesado(sub, o):
                continue
            vistos.add(o['i'])
            out.append({'que': 'OB', 'i': o['i'],
                        'suelo': o['suelo'], 'techo': o['techo']})
    return sorted(out, key=lambda x: x['i'])


def _atravesado(ohlc, ob):
    """¿Algún cierre posterior dejó este order block del todo atrás?"""
    for j in range(ob['i'] + 1, len(ohlc)):
        if (_c(ohlc[j]) > ob['techo'] if ob['tipo'] == 'bajista'
                else _c(ohlc[j]) < ob['suelo']):
            return True
    return False


def _nivel_liq(ohlc, grupo, lado, sigla, teq, ref):
    niveles = [n for n, _i in grupo]
    velas = sorted(i for _n, i in grupo)
    dispersion = max(niveles) - min(niveles)
    # 🔴 EL NIVEL ES EL EXTREMO DEL GRUPO, NO SU MEDIA (y aquí se separa de
    #    `piscinas`, que promedia). Los stops no duermen en el promedio de dos
    #    máximos: duermen por encima del MÁS ALTO. Con la media, una vela que
    #    asoma entre los dos máximos ya contaría la liquidez como tomada
    #    cuando no ha tocado ni uno de los dos.
    nivel = max(niveles) if lado == 'alto' else min(niveles)
    if len(grupo) == 1:
        forma = 'swing'
    elif dispersion <= teq:
        forma = 'EQH' if lado == 'alto' else 'EQL'
    else:
        forma = 'REQH' if lado == 'alto' else 'REQL'
    tomada = None
    for j in range(velas[-1] + 1, len(ohlc)):
        if (_h(ohlc[j]) > nivel) if lado == 'alto' else (_l(ohlc[j]) < nivel):
            tomada = j
            break
    d = {'i': velas[-1], 'lado': lado, 'sigla': sigla, 'forma': forma,
         'nivel': nivel, 'dispersion': dispersion, 'velas': velas,
         'toques': len(velas), 'tomada_en': tomada,
         'estado': 'tomada' if tomada is not None else 'sin tomar',
         'obstaculos': [], 'resistencia': None}
    if tomada is None and velas[-1] <= ref:
        d['obstaculos'] = obstaculos(ohlc, nivel, lado, ref)
        d['resistencia'] = 'LRL' if not d['obstaculos'] else 'HRL'
    return d


def liquidez(ohlc, k=2, tol_eq=TOL_EQ, tol_req=TOL_REQ, ref=None):
    """EL MAPA DE LIQUIDEZ: cada nivel, cómo se llama y en qué quedó.

    Devuelve **todos** los niveles, tomados y sin tomar, porque las dos cosas
    se preguntan: la tomada explica lo que ya pasó, la que sigue ahí explica a
    dónde puede ir el precio.

    Cada entrada trae:
        sigla   BSL / SSL      — de qué lado duerme
        forma   swing / EQH / EQL / REQH / REQL   — de qué está hecha
        estado  tomada / sin tomar   (+ `tomada_en`, la vela que se la llevó)
        resistencia  LRL / HRL  (+ `obstaculos`), solo si sigue sin tomar

    🔑 UN SWING SUELTO TAMBIÉN ES LIQUIDEZ, y esto es lo que `piscinas` no
    daba. Exigir dos toques dejaba fuera el caso más común del gráfico —un
    máximo de giro cualquiera— y justamente ese fue el nivel que sirvió para la
    segunda verificación externa del proyecto: nuestro mínimo sin barrer salió
    en 29.334,12 y la línea SS del indicador del dueño estaba en 29.333,00,
    **1,1 puntos**. Con `piscinas` ese nivel no existía.

    ⚠️ SE AGRUPA CONTRA EL PRIMERO DEL GRUPO, no contra el anterior — misma
    trampa que documenta `piscinas`: encadenando, una deriva larga se traga el
    gráfico y el 'nivel' resultante no está en ninguna parte.

    ⚠️ Esto es una lectura RETROSPECTIVA de la serie que se le pase: `tomada_en`
    mira hasta el final. Para saber qué se veía en un instante concreto —la
    vela en la que alguien entró— hay que pasarle la serie CORTADA ahí, que es
    lo que hace `dol`. `ref` solo decide desde dónde se miden los obstáculos."""
    rm = _rango_mediano(ohlc)
    teq, treq = tol_eq * rm, tol_req * rm
    if ref is None:
        ref = len(ohlc) - 1
    sw = swings(ohlc, k)
    out = []
    for lado, sigla in (('alto', 'BSL'), ('bajo', 'SSL')):
        pts = sorted((niv, i) for (i, t, niv) in sw if t == lado)
        grupo = []
        for niv, i in pts:
            if grupo and (niv - grupo[0][0]) > treq:
                out.append(_nivel_liq(ohlc, grupo, lado, sigla, teq, ref))
                grupo = []
            grupo.append((niv, i))
        if grupo:
            out.append(_nivel_liq(ohlc, grupo, lado, sigla, teq, ref))
    return sorted(out, key=lambda n: n['i'])


def dol(ohlc, k=2, ref=None, tol_eq=TOL_EQ, tol_req=TOL_REQ):
    """DRAW ON LIQUIDITY — la liquidez que queda SIN TOMAR a cada lado.

    🔴 NO PREDICE NADA, Y ESO NO ES TIMIDEZ LEGAL: es que la aritmética no da
    para más. Lo que aquí se calcula es *qué hay sin recoger arriba y abajo, a
    qué distancia y con cuánto estorbo en el camino*. Decir cuál de los dos va
    a buscar el precio sería una señal, y el sitio no da señales.

    🔑 PERO CONTESTA LA PREGUNTA QUE DE VERDAD SE HACE. El dueño escribió, sobre
    un trade suyo: *«no veía motivos para que el precio se diera la vuelta ya
    que consideraba que había mucha más liquidez superior, aunque quizá pueda
    estarme equivocando»*. Eso no es una opinión: es contable. Se cuentan los
    niveles de cada lado, se miden las distancias y sale la respuesta.

    ⚠️ SE CORTA LA SERIE EN `ref`. Todo lo posterior deja de existir, así que
    `tomada_en` solo puede referirse a algo que ya había pasado. Sin este corte
    se juzgaría la entrada de alguien con el gráfico de después, que es la
    forma más fácil de parecer brillante y no servir para nada."""
    if ref is None:
        ref = len(ohlc) - 1
    sub = ohlc[:ref + 1]
    niveles = liquidez(sub, k, tol_eq, tol_req, ref)
    c = _c(sub[ref])
    arriba = sorted([n for n in niveles if n['lado'] == 'alto'
                     and n['tomada_en'] is None and n['nivel'] > c],
                    key=lambda n: n['nivel'])
    abajo = sorted([n for n in niveles if n['lado'] == 'bajo'
                    and n['tomada_en'] is None and n['nivel'] < c],
                   key=lambda n: -n['nivel'])
    da = (arriba[0]['nivel'] - c) if arriba else None
    db = (c - abajo[0]['nivel']) if abajo else None
    if da is None and db is None:
        cerca = None
    elif db is None:
        cerca = 'arriba'
    elif da is None:
        cerca = 'abajo'
    else:
        cerca = 'arriba' if da < db else ('abajo' if db < da else None)
    return {'ref': ref, 'cierre': c, 'arriba': arriba, 'abajo': abajo,
            'dist_arriba': da, 'dist_abajo': db, 'mas_cerca': cerca,
            'n_arriba': len(arriba), 'n_abajo': len(abajo)}


# ══════════════════════════════════════════════════════════════════════════
# ESTRUCTURA DE MERCADO — HH/HL/LH/LL, tendencia y MSS (2026-09-09)
# ══════════════════════════════════════════════════════════════════════════
# 🔴 POR QUÉ FALTABA ESTO Y POR QUÉ IMPORTA MÁS QUE NADA DE LO ANTERIOR.
# El dueño explicó su trade con estas palabras: *"mi confluencia fue haber
# tenido en 1H un cierre de vela que ocasionó un Structure Shift a alcista"*.
# O sea que su tesis entera era un MSS — y el catálogo **no sabía qué es un
# MSS**. Le estábamos pidiendo a la IA que juzgara su decisión con una lista
# de hechos que no contenía el hecho en el que se basó la decisión.
# Tampoco sabía decir si la tendencia era alcista o bajista, que es la primera
# pregunta que se hace cualquiera al abrir un gráfico.
#
# ⚠️ NO SE PUEDE VERIFICAR SU MSS DE 1H: nosotros vemos la captura de 5m y ahí
#    no está. Lo que sí se puede decir —y es lo útil— es qué hacía la estructura
#    de 5m en ese momento. Que no es lo mismo, y el bloque no debe confundirlo.


def estructura(ohlc, k=2):
    """Cada giro, etiquetado contra el anterior DE SU MISMO TIPO.

        HH  máximo más alto que el máximo anterior
        LH  máximo más BAJO que el anterior  → la subida pierde fuerza
        HL  mínimo más alto que el anterior  → la caída pierde fuerza
        LL  mínimo más bajo que el anterior

    🔑 Se compara alto con alto y bajo con bajo, NUNCA alternando. Comparar un
    máximo contra el mínimo que le precede da una secuencia que sube y baja sin
    significar nada: la estructura son dos escaleras paralelas, no una.

    ⚠️ El PRIMER giro de cada tipo no lleva etiqueta: no hay contra qué
    compararlo. Ponerle una es inventarse el pasado del gráfico."""
    out = []
    ult = {'alto': None, 'bajo': None}
    for (i, t, niv) in swings(ohlc, k):
        prev = ult[t]
        if prev is not None:
            if t == 'alto':
                et = 'HH' if niv > prev else 'LH'
            else:
                et = 'HL' if niv > prev else 'LL'
            out.append({'i': i, 'tipo': et, 'nivel': niv, 'previo': prev})
        ult[t] = niv
    return out


def tendencia(ohlc, k=2, hasta=None):
    """En qué estado está la estructura: el ÚLTIMO máximo contra el ÚLTIMO
    mínimo. Dos escaleras, una pregunta a cada una.

        máximos subiendo (HH) + mínimos subiendo (HL)  →  ALCISTA
        máximos bajando  (LH) + mínimos bajando  (LL)  →  BAJISTA
        una sube y la otra baja                        →  MIXTA

    🔴 CÓMO SE HACÍA ANTES Y POR QUÉ ESTABA MAL — lo cazó el dueño leyendo un
    informe, que es exactamente para lo que sirve que él revise. La versión
    vieja CONTABA las últimas 4 etiquetas y declaraba 'mixta' en cuanto hubiera
    una de cada signo. Sobre su gráfico, en su vela de entrada las etiquetas
    eran HH(114) · LL(120) · HL(131) · HH(145): el informe dijo *"estructura
    mixta"* y él contestó, con razón, que **ahí la estructura era claramente
    alcista**. Y lo era: el último máximo era HH y el último mínimo HL — las dos
    escaleras subiendo. Lo que arrastraba el veredicto era un LL de **29 velas
    antes**, ya superado por el HL que vino después.
    🔑 Una etiqueta vieja no describe la estructura vigente: la describe **la
    última de cada tipo**. Un mínimo más bajo deja de contar en cuanto llega
    uno más alto — eso es lo que significa que la estructura se recuperó.

    🔴 'mixta' SIGUE SIN SER UNA EVASIVA, pero ahora nombra algo concreto:
    máximos subiendo con mínimos bajando (rango que se abre) o máximos bajando
    con mínimos subiendo (que se cierra). Son las dos formas en que un gráfico
    se queda sin dirección, y las dos son avisos reales.

    ⚠️ Hacen falta las DOS escaleras. Con solo máximos etiquetados no se puede
    decir nada: un HH sin saber qué hacen los mínimos no es una tendencia.

    ⚠️ `hasta` corta el futuro: para juzgar una entrada hay que preguntar por
    la estructura que existía ENTONCES."""
    e = [x for x in estructura(ohlc, k) if hasta is None or x['i'] <= hasta]
    alto = next((x for x in reversed(e) if x['tipo'] in ('HH', 'LH')), None)
    bajo = next((x for x in reversed(e) if x['tipo'] in ('HL', 'LL')), None)
    if alto is None or bajo is None:
        return {'estado': 'indefinida', 'etiquetas': [], 'alto': None,
                'bajo': None}
    sube_a, sube_b = alto['tipo'] == 'HH', bajo['tipo'] == 'HL'
    estado = ('alcista' if sube_a and sube_b else
              'bajista' if not sube_a and not sube_b else 'mixta')
    return {'estado': estado, 'alto': (alto['i'], alto['tipo']),
            'bajo': (bajo['i'], bajo['tipo']),
            'etiquetas': [(alto['i'], alto['tipo']), (bajo['i'], bajo['tipo'])]}


def mss(ohlc, k=2):
    """MSS / CHoCH — el BOS que le da la VUELTA a la estructura.

    🔑 La diferencia con un BOS cualquiera es la única que importa: un BOS *a
    favor* confirma lo que ya estaba pasando; el que va en CONTRA del anterior
    avisa de que el control cambió de manos. Se calcula comparando cada evento
    de ruptura con el anterior — si cambia de signo, es un MSS.

    ⚠️ El PRIMER BOS del gráfico nunca es un MSS: no hay nada que voltear."""
    out, prev = [], None
    for b in bos_eventos(ohlc, k):
        if prev is not None and b['tipo'] != prev:
            out.append(dict(b, mss=True))
        prev = b['tipo']
    return out


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


def esc_equal_highs(alto2=105.0, cola=()):
    """Dos máximos de GIRO a la misma altura y nadie los toca después.

    `alto2` mueve el segundo máximo: con 105.0 son EQH (iguales), con 105.5
    quedan REQH (relativamente iguales). Es la MISMA lámina — lo único que
    cambia es medio punto, que es exactamente lo que separa las dos etiquetas
    en el vocabulario del dueño."""
    o = [_v(100.0, 101.0, 99.0, 100.5), _v(100.5, 102.0, 100.0, 101.5),
         _v(101.5, 105.0, 101.0, 104.0),         # i=2: giro alto en 105.0
         _v(104.0, 104.2, 102.0, 102.5), _v(102.5, 103.0, 101.0, 101.5),
         _v(101.5, 103.5, 101.0, 103.0),
         _v(103.0, alto2, 102.5, 104.0),         # i=6: el segundo giro alto
         _v(104.0, 104.5, 102.0, 102.5), _v(102.5, 103.0, 101.0, 101.5),
         _v(101.5, 102.5, 100.5, 102.0)]
    return list(o) + list(cola)


def esc_liquidez_tomada():
    """Los mismos EQH, y una vela que se los lleva por delante."""
    return esc_equal_highs(cola=[_v(102.0, 106.0, 101.8, 105.5)]), \
        {'nivel': 105.0, 'tomada_en': 10}


def esc_dol():
    """Un BSL sin tomar arriba y un SSL sin tomar abajo, a distinta distancia.

    Es la lámina que contesta literalmente la pregunta del dueño sobre su MNQ:
    *¿había más liquidez arriba que abajo?*. Aquí la verdad se conoce porque
    los dos niveles están puestos a mano."""
    o = [_v(100.0, 101.0, 99.0, 100.5), _v(100.5, 102.0, 100.0, 101.5),
         _v(101.5, 105.0, 101.0, 104.5),         # i=2: BSL en 105.0
         _v(104.5, 104.7, 103.0, 103.5), _v(103.5, 104.0, 102.0, 102.5),
         _v(102.5, 103.0, 98.0, 98.5),           # i=5: SSL en 98.0
         _v(98.5, 100.0, 98.2, 99.5), _v(99.5, 101.0, 99.0, 100.5),
         _v(100.5, 102.0, 100.0, 101.5),
         _v(101.5, 102.5, 101.0, 102.0)]         # i=9: referencia, cierre 102
    return o, {'arriba': 105.0, 'abajo': 98.0, 'dist_arriba': 3.0,
               'dist_abajo': 4.0, 'mas_cerca': 'arriba'}


def esc_hrl():
    """ALTA resistencia: para llegar al BSL hay que atravesar zonas bajistas."""
    o = [_v(100.0, 101.0, 99.0, 100.5), _v(100.5, 108.0, 100.0, 107.5),
         _v(107.5, 110.0, 107.0, 109.0),         # i=2: BSL en 110, sin tomar
         _v(109.0, 109.2, 105.0, 105.5),
         _v(105.5, 106.0, 103.0, 103.5),         # i=4: FVG bajista 106,0-107,0
         _v(103.5, 104.0, 102.0, 102.5),         # i=5: FVG bajista 104,0-105,0
         _v(102.5, 103.5, 101.5, 103.0), _v(103.0, 104.0, 102.5, 103.5)]
    return o, {'nivel': 110.0, 'resistencia': 'HRL'}


def esc_lrl():
    """BAJA resistencia: el camino hasta el BSL está limpio."""
    o = [_v(100.0, 101.0, 99.0, 100.5), _v(100.5, 102.0, 100.0, 101.5),
         _v(101.5, 106.0, 101.0, 105.5),         # i=2: BSL en 106, sin tomar
         _v(105.5, 105.8, 104.0, 104.5), _v(104.5, 105.0, 103.5, 104.0),
         _v(104.0, 104.8, 103.0, 104.5),         # i=5: SSL en 103, sin tomar
         _v(104.5, 105.2, 104.0, 105.0), _v(105.0, 105.5, 104.5, 105.2)]
    return o, {'nivel': 106.0, 'resistencia': 'LRL'}


def esc_estructura():
    """Tendencia alcista limpia (HH/HL ×2), después un LH y una ruptura abajo.

    Es la forma exacta del trade del dueño contada al revés: la estructura
    sube, deja de subir, y solo DESPUÉS rompe. Lo que se quiere comprobar es
    que las tres fases se distinguen — porque entrar en la segunda creyendo que
    sigues en la primera es el error más caro que hay."""
    o = [_v(100.0, 101.0, 99.5, 100.5), _v(100.5, 101.5, 100.0, 101.0),
         _v(101.0, 102.0, 97.0, 98.0),        # i=2: primer giro (alto y bajo)
         _v(98.0, 100.0, 97.5, 99.5), _v(99.5, 101.0, 99.0, 100.5),
         _v(100.5, 105.0, 101.0, 104.5),      # i=5: HH  (105 > 102)
         _v(104.5, 104.8, 102.0, 102.5),
         _v(102.5, 103.0, 100.5, 101.0),      # i=7: HL  (100,5 > 97)
         _v(101.0, 103.5, 100.8, 103.0),
         _v(103.0, 110.0, 105.0, 109.5),      # i=9: HH  (110 > 105)
         _v(109.5, 109.8, 106.0, 106.5),
         _v(106.5, 107.0, 104.0, 104.5),      # i=11: HL (104 > 100,5)
         _v(104.5, 106.0, 104.2, 105.5),
         _v(105.5, 107.5, 105.0, 107.0),      # i=13: LH (107,5 < 110)
         # ⚠️ Esta vela CIERRA en 104,5, por encima del HL de 104,0. Iba a
         #    cerrar en 103,5 y el detector cantó el MSS una vela antes — tenía
         #    razón él y estaba mal la lámina. Se arregló la LÁMINA, no la
         #    comprobación: cuando el detector y tu intención discrepan, primero
         #    hay que mirar cuál de los dos se equivocó.
         _v(107.0, 107.2, 103.8, 104.5),
         _v(104.5, 104.6, 100.0, 100.2),      # i=15: CIERRA bajo el HL → MSS
         _v(100.2, 101.0, 98.5, 99.0), _v(99.0, 100.0, 98.0, 98.5)]
    return o, {'etiquetas': [(5, 'HH'), (7, 'HL'), (9, 'HH'), (11, 'HL'),
                             (13, 'LH')],
               'alcista_hasta': 12, 'mss_i': 15, 'mss_tipo': 'bajista'}


def esc_minimo_viejo():
    """HH · LL · HL · HH — un mínimo más bajo SUPERADO por uno más alto.

    🔴 ES EL PATRÓN EXACTO DE SU GRÁFICO en la vela donde entró: HH(114),
    LL(120), HL(131), HH(145). El informe le dijo *"estructura mixta"* y él
    contestó que ahí la estructura era **claramente alcista** — y tenía razón:
    las dos escaleras suben, y lo único bajista era un LL de 29 velas antes,
    ya superado. La regla vieja lo declaraba mixto por contar etiquetas.
    Este caso existe para que eso no pueda volver."""
    o = [_v(100, 101, 99.5, 100.5), _v(100.5, 101.5, 100, 101),
         _v(101, 104, 100.5, 103.5),          # giro alto 104 (el primero)
         _v(103.5, 103.8, 101, 101.5),
         _v(101.5, 102, 99.0, 99.5),          # giro bajo 99,0 (el primero)
         _v(99.5, 101, 99.2, 100.8),
         _v(100.8, 106, 100.5, 105.5),        # i=6: HH  (106 > 104)
         _v(105.5, 105.8, 103, 103.5),
         _v(103.5, 104, 98.0, 98.5),          # i=8: LL  (98 < 99) ← el viejo
         _v(98.5, 101.0, 98.4, 100.5), _v(100.5, 102.5, 100.9, 102.0),
         _v(102.0, 103.0, 101.5, 102.5),
         _v(102.5, 103.0, 100.8, 101.2),      # i=12: HL (100,8 > 98) ← lo supera
         _v(101.2, 103.0, 101.0, 102.8),
         _v(102.8, 108.0, 102.5, 107.5),      # i=14: HH (108 > 106)
         _v(107.5, 107.8, 105, 105.5), _v(105.5, 106, 104, 104.5),
         _v(104.5, 105, 103.5, 104)]
    return o, {'etiquetas': [(6, 'HH'), (8, 'LL'), (12, 'HL'), (14, 'HH')],
               'estado': 'alcista'}


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

    print('── estructura de mercado: HH/HL/LH/LL, tendencia y MSS ──')
    o, t = esc_estructura()
    e = estructura(o)
    caso('etiqueta los 5 giros %s' % t['etiquetas'],
         [(x['i'], x['tipo']) for x in e] == t['etiquetas'],
         [(x['i'], x['tipo']) for x in e])
    # 🔑 El primer giro de cada tipo NO lleva etiqueta: no hay contra qué
    #    compararlo, y ponérsela es inventarse el pasado del gráfico.
    caso('el primer giro se queda SIN etiquetar',
         not any(x['i'] == 2 for x in e), [x['i'] for x in e])
    caso('hasta la vela %d la tendencia es ALCISTA' % t['alcista_hasta'],
         tendencia(o, hasta=t['alcista_hasta'])['estado'] == 'alcista',
         tendencia(o, hasta=t['alcista_hasta']))
    # 🔴 EL CASO QUE CAZÓ EL DUEÑO. Un mínimo más bajo YA SUPERADO por uno más
    #    alto no describe la estructura vigente. Contando etiquetas esto salía
    #    'mixta' (3 alcistas contra 1) y el informe se lo dijo a la cara sobre
    #    un tramo donde la estructura era claramente alcista.
    o2, t2 = esc_minimo_viejo()
    caso('las etiquetas son %s' % [x[1] for x in t2['etiquetas']],
         [(x['i'], x['tipo']) for x in estructura(o2)] == t2['etiquetas'],
         [(x['i'], x['tipo']) for x in estructura(o2)])
    caso('un LL viejo ya superado NO arrastra el veredicto a mixta',
         tendencia(o2)['estado'] == t2['estado'], tendencia(o2))
    # 🔑 Y lo que decide se puede SEÑALAR: el último de cada tipo, con su vela.
    #    Sin eso la línea dice "alcista" y no hay forma de comprobarla.
    caso('y dice de qué dos giros lo deduce',
         tendencia(o2)['alto'] == (14, 'HH') and tendencia(o2)['bajo'] == (12, 'HL'),
         (tendencia(o2)['alto'], tendencia(o2)['bajo']))
    # 🔴 Tras UN solo LH la estructura no es bajista todavía —no ha roto nada—
    #    pero ya no es limpiamente alcista. Ese hueco es donde se toman los
    #    peores trades; forzarlo a un bando le quitaría al trader el aviso.
    caso('tras el LH pasa a MIXTA, no a bajista',
         tendencia(o, hasta=14)['estado'] == 'mixta', tendencia(o, hasta=14))
    m = mss(o)
    caso('el MSS cae en la vela %d' % t['mss_i'],
         len(m) == 1 and m[0]['i'] == t['mss_i'],
         [(x['i'], x['tipo']) for x in m])
    caso('y es %s' % t['mss_tipo'],
         m and m[0]['tipo'] == t['mss_tipo'], m and m[0]['tipo'])
    # ⚠️ Un BOS A FAVOR no es un MSS. En esta lámina la vela 9 rompe al alza
    #    estando ya alcista: confirma, no voltea. Si esto entrara como MSS, la
    #    etiqueta perdería todo su valor — sería un sinónimo de BOS.
    caso('un BOS a favor NO es un MSS',
         not any(x['i'] == 9 for x in m), [x['i'] for x in m])

    print('── liquidez: EQH / REQH, tomada y sin tomar ──')
    o = esc_equal_highs()
    bsl = [n for n in liquidez(o) if n['lado'] == 'alto']
    caso('un solo nivel de BSL', len(bsl) == 1,
         [(n['forma'], n['nivel']) for n in bsl])
    if bsl:
        caso('etiquetado EQH', bsl[0]['forma'] == 'EQH', bsl[0]['forma'])
        caso('con los dos giros [2, 6]', bsl[0]['velas'] == [2, 6], bsl[0]['velas'])
        caso('y SIN TOMAR', bsl[0]['estado'] == 'sin tomar', bsl[0]['estado'])
    # 🔑 Medio punto separa "iguales" de "relativamente iguales". Si la misma
    #    lámina con el segundo máximo movido no cambia de etiqueta, es que la
    #    tolerancia no está haciendo nada y las dos siglas son decorativas.
    req = [n for n in liquidez(esc_equal_highs(alto2=105.5))
           if n['lado'] == 'alto']
    caso('el mismo nivel medio punto más arriba pasa a REQH',
         len(req) == 1 and req[0]['forma'] == 'REQH',
         [(n['forma'], n['nivel']) for n in req])
    o, t = esc_liquidez_tomada()
    bsl = [n for n in liquidez(o) if n['lado'] == 'alto']
    caso('cuando una vela se los lleva, sale TOMADA en la vela %d' % t['tomada_en'],
         len(bsl) == 1 and bsl[0]['tomada_en'] == t['tomada_en'],
         [(n['forma'], n['tomada_en']) for n in bsl])
    # 🔴 El nivel de un grupo es el EXTREMO, no la media. Con la media (105,25)
    #    una vela que asomara a 105,3 declararía tomada una liquidez que está
    #    en 105,5 y nadie ha tocado.
    o = esc_equal_highs(alto2=105.5, cola=[_v(102.0, 105.3, 101.8, 105.0)])
    bsl = [n for n in liquidez(o) if n['lado'] == 'alto']
    caso('una vela entre los dos máximos NO cuenta como tomarlos',
         len(bsl) == 1 and bsl[0]['tomada_en'] is None and bsl[0]['nivel'] == 105.5,
         [(n['nivel'], n['tomada_en']) for n in bsl])
    # 🔑 Un swing SUELTO también es liquidez. Es justo el nivel que sirvió para
    #    la segunda verificación externa del proyecto (29.334,12 contra la
    #    línea SS del indicador del dueño, 1,1 puntos) y `piscinas` no lo daba.
    o, t = esc_dol()
    uno = [n for n in liquidez(o) if n['forma'] == 'swing']
    caso('un giro suelto SIN pareja también cuenta como liquidez',
         len(uno) == 2, [(n['sigla'], n['nivel']) for n in uno])
    caso('y `piscinas` NO lo veía (por eso hacía falta esto)',
         not [p for p in piscinas(o) if abs(p['nivel'] - t['arriba']) < 1e-6],
         [p['nivel'] for p in piscinas(o)])

    print('── DOL: qué queda sin tomar a cada lado ──')
    o, t = esc_dol()
    d = dol(o)
    caso('un candidato arriba y uno abajo',
         d['n_arriba'] == 1 and d['n_abajo'] == 1,
         (d['n_arriba'], d['n_abajo']))
    caso('el de arriba en %.1f' % t['arriba'],
         d['arriba'] and abs(d['arriba'][0]['nivel'] - t['arriba']) < 1e-6,
         [n['nivel'] for n in d['arriba']])
    caso('el de abajo en %.1f' % t['abajo'],
         d['abajo'] and abs(d['abajo'][0]['nivel'] - t['abajo']) < 1e-6,
         [n['nivel'] for n in d['abajo']])
    caso('a %.1f y %.1f de distancia' % (t['dist_arriba'], t['dist_abajo']),
         abs(d['dist_arriba'] - t['dist_arriba']) < 1e-6 and
         abs(d['dist_abajo'] - t['dist_abajo']) < 1e-6,
         (d['dist_arriba'], d['dist_abajo']))
    caso('y el más cercano es el de %s' % t['mas_cerca'],
         d['mas_cerca'] == t['mas_cerca'], d['mas_cerca'])
    # 🔴 EL CORTE EN `ref`. Si se pregunta por la vela 5 —cuando el SSL acaba
    #    de formarse y el gráfico aún no ha seguido— la respuesta NO puede
    #    incluir nada de lo que pasó después. Un swing necesita k velas a cada
    #    lado, así que en la vela 5 ni siquiera está confirmado: la lista de
    #    arriba tiene que quedarse en el BSL y ya.
    d5 = dol(o, ref=5)
    caso('cortado en la vela 5, no se ve el futuro',
         all(n['i'] <= 5 for n in d5['arriba'] + d5['abajo']),
         [(n['i'], n['nivel']) for n in d5['arriba'] + d5['abajo']])
    # 🔴 Y LOS OBSTÁCULOS TAMBIÉN, que es por donde se escapa sin que se note:
    #    de la línea del DOL solo se imprime CUÁNTOS hay, así que un obstáculo
    #    del futuro no se ve en el texto — se ve en el número, y un número no
    #    delata nada. Sobre la captura real se comprobó a mano que ninguno pasa
    #    de la referencia; aquí queda atado para que siga siendo verdad.
    o2, _ = esc_hrl()
    d3 = dol(o2, ref=4)
    caso('y los OBSTÁCULOS tampoco son del futuro',
         all(x['i'] <= 4 for n in d3['arriba'] + d3['abajo']
             for x in n['obstaculos']),
         [(n['i'], [x['i'] for x in n['obstaculos']])
          for n in d3['arriba'] + d3['abajo']])

    print('── LRL / HRL: cuánto estorbo hay en el camino ──')
    o, t = esc_hrl()
    n = [x for x in liquidez(o) if abs(x['nivel'] - t['nivel']) < 1e-6]
    caso('el BSL de %.1f sigue sin tomar' % t['nivel'],
         len(n) == 1 and n[0]['estado'] == 'sin tomar',
         [(x['nivel'], x['estado']) for x in liquidez(o)])
    if n:
        caso('y se etiqueta HRL', n[0]['resistencia'] == 'HRL',
             (n[0]['resistencia'], len(n[0]['obstaculos'])))
        caso('nombrando los obstáculos que hay en medio',
             len(n[0]['obstaculos']) >= 2,
             [(x['que'], x['i']) for x in n[0]['obstaculos']])
    o, t = esc_lrl()
    n = [x for x in liquidez(o) if abs(x['nivel'] - t['nivel']) < 1e-6]
    caso('con el camino limpio, el mismo tipo de nivel sale LRL',
         len(n) == 1 and n[0]['resistencia'] == 'LRL',
         [(x['nivel'], x['resistencia']) for x in liquidez(o)])
    # ⚠️ Solo estorba lo del sentido CONTRARIO. Un FVG alcista debajo no impide
    #    subir: si se contara, cualquier gráfico con volatilidad sería todo HRL
    #    y la etiqueta dejaría de distinguir nada.
    caso('una zona a favor NO cuenta como obstáculo',
         not [x for x in obstaculos(o, t['nivel'], 'alto')
              if x['que'] == 'FVG' and x['i'] == 3],
         obstaculos(o, t['nivel'], 'alto'))

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
