# -*- coding: utf-8 -*-
"""Las velas que el modelo NO devolvió, recuperadas de la propia imagen.

🔴 NO TOCA EL ANALIZADOR DEL SITIO. Vive en tools/, la app no lo importa.

═══ POR QUÉ EXISTE ═══
Sobre la captura real del OTE el modelo devolvió **88 columnas donde hay ~102**:
se le cae una de cada siete, repartidas. Y una vela que falta no es un hueco
visible — la lista de velas se cierra sobre sí misma y todo lo que viene después
parece perfectamente razonable.

🔴 LO QUE ESO LE HACE A LOS HECHOS, medido en el banco (24 láminas, 1.436
velas, quitándoles el 14% al azar antes de medir):

                      con todas   faltando 14%   + rejilla
    acierta   BOS        99,8%        96,8%        99,0%
              barrida    93,7%        92,4%        95,2%
              FVG        86,8%        62,8%        84,7%
              OB         81,8%        63,8%        82,5%
    encuentra BOS        88,0%        77,1%        98,1%
              barrida    93,2%        68,4%        90,9%
              FVG        98,1%        72,3%        93,7%
              OB         91,4%        71,4%        93,7%

🔑 El daño NO se reparte por igual, y saberlo cambia qué hay que arreglar: la
**precisión** de BOS y barrida casi aguanta (un BOS que se ve sigue siendo un
BOS aunque falten velas alrededor), pero la de FVG y order block se hunde 20
puntos —se definen por TRES velas seguidas, y si falta la de en medio aparece un
hueco que no existe— y **lo que se pierde en todas es encontrarlas**. Con la
rejilla vuelve todo al listón de partida, y BOS incluso por encima.

⚠️ Y explica por qué el banco daba números tan buenos: `probar()` le entregaba
al extractor las columnas VERDADERAS de todas las velas, o sea que medía los
eslabones B y C dando por perfecto el A. **Aquellas precisiones valían solo si
no faltaba ninguna vela**, y en la cadena real faltaban. Ahora el banco quita
velas por defecto (`--faltan 0.14`).

🔴 **LA TRAMPA DE MEDIR ESTO, que casi se cuela:** los hechos NO se pueden
comparar por índice de vela. Si falta una, la vela nº 40 de la lista medida no
es la nº 40 del gráfico — todos los índices posteriores se corren y un BOS
perfectamente detectado cuenta como fallo. Con esa métrica el daño salía como
BOS 63,5% · FVG 12% · OB 4,6%, o sea el TRIPLE de lo real, y la mejora de la
rejilla salía igual de exagerada. Se emparejan por POSICIÓN en la imagen
(`banco_cadena._empareja`).

═══ LA IDEA ═══
Un gráfico de velas es una REJILLA: las velas caen a intervalos exactos. Así que
las columnas que devuelve el modelo no son 88 datos sueltos, son 88 muestras de
una recta `x = a + paso·k`. Con ajustarla se sabe dónde tendrían que estar las
que faltan, sin preguntarle nada más al modelo y sin gastar una sola llamada.

🔑 **PERO NO SE INVENTAN VELAS.** Una ranura vacía puede ser un hueco de sesión,
el final del gráfico, o el tramo en blanco que el detector de panel se pasa a
propósito. Cada ranura propuesta tiene que DEMOSTRAR que hay una vela ahí, y el
juez son los **bordes verticales**: el cuerpo de una vela pinta un borde a la
izquierda y otro a la derecha, y eso no lo hace ni una línea de fib, ni el
sombreado de una killzone, ni un texto. Lo importante es que el liston no es
absoluto — se calibra con las ranuras que el modelo SÍ marcó en esta misma
imagen, que ya sabemos que son velas.
"""
from __future__ import print_function

import numpy as np

import recorta_grafico as RG

# Una ranura propuesta se acepta si su señal de bordes llega a esta fracción de
# la MEDIANA de las ranuras que el modelo sí marcó.
# ⚠️ El liston va bajo a propósito: la vela que el modelo se dejó suele ser
# justo la pequeña o la tapada por un sombreado, o sea la de señal más débil de
# todo el gráfico. Pedirle la media la descartaría por el mismo motivo por el
# que el modelo la perdió.
FRACCION_BORDE = 0.35
# Listón para las ranuras que caen FUERA del tramo que marcó el modelo.
# 🔴 Va mucho más alto porque ahí no hay nada que respalde la propuesta: dentro
# del tramo, una ranura vacía está DEMOSTRADA por las velas de los dos lados
# (hay un hueco donde no puede haberlo); pasada la última vela no hay hueco que
# explicar, solo el borde del gráfico. Medido en el banco: con el liston normal,
# las 4 únicas velas inventadas de 99 estaban las 4 después de la última real.
FRACCION_BORDE_EXTREMO = 1.0
# Máximo de ranuras seguidas que se rellenan de golpe. Un hueco más largo que
# esto no es "se le cayeron unas velas": es un corte de sesión o el final del
# gráfico, y ahí no hay nada que recuperar.
HUECO_MAX = 6
# Ranuras que se prueban MÁS ALLÁ de la primera y la última que marcó el modelo.
# La vela que se pierde puede ser la del borde, y entonces no hay ningún hueco
# interior que delate su falta: la lista simplemente empieza una vela tarde.
BORDE_EXTRA = 3


def ajusta_rejilla(centros, paso):
    """`x = a + paso·k` a partir de los centros que devolvió el modelo.

    Devuelve (a, paso_afinado, ks) donde `ks` es la ranura de cada centro.

    🔑 El paso que trae `recorta_grafico` sale de una autocorrelación y es bueno
    al 2-3%, pero sobre 100 velas un 3% son TRES velas de desfase acumulado. Los
    centros del modelo son mejores para afinarlo: hay ~90 repartidos por todo el
    gráfico, así que la recta se apoya en una base muy larga."""
    c = np.asarray(sorted(centros), float)
    if len(c) < 4:
        return None
    k = np.round((c - c[0]) / float(paso))
    # dos vueltas: con el paso afinado las ranuras lejanas pueden cambiar
    for _ in range(3):
        A = np.vstack([np.ones(len(k)), k]).T
        a, p = np.linalg.lstsq(A, c, rcond=None)[0]
        if not (RG.PASO_MIN <= p <= RG.PASO_MAX):
            return None
        nk = np.round((c - a) / p)
        if np.array_equal(nk, k):
            k = nk
            break
        k = nk
    return a, p, k.astype(int)


def _ventana(x, ancho):
    """Índices del perfil que cubren la columna centrada en `x`.

    ⚠️ `perfil[i]` es el cambio de color entre la columna i y la i+1, así que
    el borde IZQUIERDO de un cuerpo que empieza en la columna c está en el
    índice c-1, no en c. Sin ese -1 la mitad izquierda no veía nunca su pared y
    `senal_de_cuerpo` daba cero para todas las velas — con lo que el listón de
    los extremos salía a cero y dejaba pasar cualquier cosa."""
    lo = int(np.floor(x - ancho / 2.0)) - 1
    hi = int(np.ceil(x + ancho / 2.0))
    return lo, int(round(x)), hi


def senal_de_bordes(perfil, x, ancho):
    """Cuánta 'pared vertical' hay en la columna centrada en `x`."""
    lo, _m, hi = _ventana(x, ancho)
    lo = max(0, lo); hi = min(len(perfil), hi + 1)
    if hi <= lo:
        return 0.0
    return float(perfil[lo:hi].max())


def senal_de_cuerpo(perfil, x, ancho):
    """Como la anterior, pero exigiendo las DOS paredes del cuerpo.

    🔑 Es la señal que separa una vela de cualquier otra cosa vertical del
    gráfico. El cuerpo de una vela tiene borde izquierdo Y borde derecho a unos
    pocos píxeles uno del otro; el canto de una caja de sesión, el final de un
    sombreado o el marco del panel tienen UNO SOLO. Como se devuelve el menor de
    los dos, una sola pared da casi cero por muy marcada que esté.

    ⚠️ Esto importa solo en los EXTREMOS. Dentro del tramo que marcó el modelo,
    una ranura vacía ya está avalada por las velas de los dos lados; pasada la
    última vela no hay nada que avale nada, y ahí es donde se colaban las
    únicas velas inventadas que dio el banco.

    ⚠️ Las dos mitades NO pueden solaparse. Con el píxel central contando para
    las dos, un canto perfectamente centrado en la ranura aparecía en ambas y
    puntuaba como si fuera un cuerpo entero — que es justo lo contrario de lo
    que esta función existe para detectar."""
    lo, m, hi = _ventana(x, ancho)
    izq = perfil[max(0, lo):max(0, m)]
    der = perfil[max(0, m):min(len(perfil), hi + 1)]
    if not len(izq) or not len(der):
        return 0.0
    return float(min(izq.max(), der.max()))


def completa(cajas, paso, a_img, banda, ancho_col=None):
    """Devuelve las cajas del modelo MÁS las ranuras vacías que sí tienen vela.

    `cajas` = [(x0, x1, gy0, gy1)] tal y como las junta el analizador.
    `banda` = (y0, y1), la franja donde hay gráfico (la de las guías).

    🔑 La guía de una caja añadida se INTERPOLA entre el vecino de la izquierda
    y el de la derecha, no se copia del más cercano. La guía solo sirve para
    elegir cuál de los bloques de tinta de la franja es la vela, pero en un
    tramo con pendiente la vela de al lado ya está 20-30 px más arriba, y con la
    copia el bloque elegido puede ser el equivocado. Interpolar cuesta lo mismo
    y sigue el movimiento del precio.

    Devuelve (cajas_completas, conjunto_de_las_añadidas). El conjunto sirve para
    DIBUJARLAS de otro color: una vela recuperada por rejilla no tiene el mismo
    respaldo que una que el modelo señaló, y quien mire el dibujo tiene que
    poder distinguirlas."""
    if len(cajas) < 4:
        return list(cajas), set()
    cajas = sorted(cajas, key=lambda c: (c[0] + c[1]) / 2.0)
    centros = [(c[0] + c[1]) / 2.0 for c in cajas]
    aj = ajusta_rejilla(centros, paso)
    if aj is None:
        return list(cajas), set()
    a, p, ks = aj
    if ancho_col is None:
        ancho_col = int(np.median([c[1] - c[0] + 1 for c in cajas]))
    ancho_col = max(2, int(ancho_col))

    y0, y1 = banda
    perfil = np.asarray(RG.perfil_bordes(a_img, y0, y1), float)
    tengo = {}
    for k, c in zip(ks, cajas):
        tengo[int(k)] = c
    # el liston lo ponen las ranuras que el modelo SÍ marcó
    ref = [senal_de_bordes(perfil, a + p * k, ancho_col) for k in tengo]
    if not ref:
        return list(cajas), set()
    mediana_ref = float(np.median(ref))
    minimo = FRACCION_BORDE * mediana_ref
    # el listón de los extremos se calibra con SU propia medida: la de las dos
    # paredes, que en una vela de verdad es bastante menor que la de una sola.
    ref2 = [senal_de_cuerpo(perfil, a + p * k, ancho_col) for k in tengo]
    minimo_extremo = FRACCION_BORDE_EXTREMO * float(np.median(ref2))
    k_min, k_max = int(ks.min()), int(ks.max())

    W = a_img.shape[1]
    nuevas = []
    faltan = [k for k in range(int(ks.min()) - BORDE_EXTRA,
                               int(ks.max()) + BORDE_EXTRA + 1)
              if k not in tengo]
    # agrupar las que faltan en tramos seguidos, para poder descartar los huecos
    # largos enteros (un corte de sesión no se rellena vela a vela)
    tramos, cur = [], []
    for k in faltan:
        if cur and k == cur[-1] + 1:
            cur.append(k)
        else:
            if cur:
                tramos.append(cur)
            cur = [k]
    if cur:
        tramos.append(cur)

    conocidas = sorted(tengo)

    def guia(k):
        """Guía interpolada entre las dos cajas del modelo que rodean a `k`."""
        izq = [q for q in conocidas if q < k]
        der = [q for q in conocidas if q > k]
        if not izq:
            c = tengo[der[0]]
            return c[2], c[3]
        if not der:
            c = tengo[izq[-1]]
            return c[2], c[3]
        ka, kb = izq[-1], der[0]
        ca, cb = tengo[ka], tengo[kb]
        t = (k - ka) / float(kb - ka)
        return (int(round(ca[2] + t * (cb[2] - ca[2]))),
                int(round(ca[3] + t * (cb[3] - ca[3]))))

    for tramo in tramos:
        if len(tramo) > HUECO_MAX:
            continue
        for k in tramo:
            x = a + p * k
            if x < 0 or x >= W:
                continue
            if k_min <= k <= k_max:
                if senal_de_bordes(perfil, x, ancho_col) < minimo:
                    continue
            elif senal_de_cuerpo(perfil, x, ancho_col) < minimo_extremo:
                continue
            gy0, gy1 = guia(k)
            # 🔑 x0..x1 son AMBOS inclusive, así que su centro es
            # x0 + (ancho-1)/2, no x0 + ancho/2. Con la versión de más se
            # colocaba media columna a la izquierda y, con anchos pares, la
            # caja añadida caía 1 px fuera de su vela.
            x0 = int(round(x - (ancho_col - 1) / 2.0))
            nuevas.append((x0, x0 + ancho_col - 1, gy0, gy1))

    todas = sorted(list(cajas) + nuevas, key=lambda c: (c[0] + c[1]) / 2.0)
    return todas, set(nuevas)
