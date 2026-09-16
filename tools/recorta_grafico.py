# -*- coding: utf-8 -*-
"""¿Por dónde hay que recortar una captura, sin preguntarle nada al cliente?

    python3 tools/recorta_grafico.py --imagen docs/capturas_prueba/mnq_5m.png

🔴 NO TOCA EL ANALIZADOR. Vive en tools/, no lo importa la app.

═══ QUÉ RESUELVE ═══
La regla de las 8 milésimas (ver CLAUDE.md): Gemini solo separa una vela de su
vecina si esa vela ocupa **más de ~8 milésimas del ancho de lo que le mandas**,
o sea si en la imagen caben menos de ~125 velas. La captura del dueño traía 255
y cada caja se comía dos o tres.

El arreglo NO es pedirle al cliente que acerque el gráfico — es **recortar
nosotros**. Pero para recortar hay que saber dos cosas que nadie nos dice: dónde
está el panel de velas y cuánto mide una vela. Las dos salen de la imagen.

🔑 **LA SEÑAL SON LOS BORDES VERTICALES, NO LA TINTA.** Contar "píxeles que no
son fondo" por columna no sirve en un gráfico entero: el fondo cambia también a
lo ANCHO (bandas de killzone, cajas de fib, sombreados), y la máscara sale
saturada — medido, daba 424 de 424 filas en todas las columnas. En cambio el
**cambio de color entre una columna y la siguiente** no depende de qué fondo
haya: el borde izquierdo y el derecho de cada cuerpo lo producen igual sobre
blanco, sobre negro o sobre un teal translúcido.

🔑 **EL PASO SE MIDE POR PERIODICIDAD, CON DESPLAZAMIENTOS FRACCIONARIOS.** Un
gráfico de velas es lo más regular que hay, así que se busca cada cuántas
columnas el perfil de bordes se parece a sí mismo. ⚠️ Y hay que permitir
**medios píxeles**: en la captura del MES el paso real es 5,5 y con lags enteros
el ganador salía 11 — el DOBLE, que habría hecho recortes con la mitad de velas
de las debidas. Por eso, tras encontrar el mejor, se prueba **la mitad**, y la
mitad de esa, mientras siga correlacionando casi igual de bien.

Medido sobre las tres capturas reales del dueño: 5,62 (real 5,5) · 8,25 (real 8)
· 10,50 (real 10,5).

🔑 **EL PANEL SE ENCUENTRA CON LA MISMA MEDIDA.** El eje de precios de la
derecha, la barra de herramientas y el eje de tiempo tienen bordes, pero **no
laten al paso de las velas**. Se recorre la imagen por ventanas y se conservan
las que sí. Nada de coordenadas fijas: cada cliente tiene su plataforma, su
resolución y sus barras.
"""
from __future__ import print_function

import argparse

import numpy as np
from PIL import Image

# Velas por recorte. Por debajo de ~125 el modelo las separa (regla de las 8
# milésimas); 80 deja margen porque el recorte no es exacto al píxel.
MAX_VELAS = 80
# Paso mínimo y máximo creíble entre velas, en píxeles.
PASO_MIN, PASO_MAX = 3.0, 40.0
# Cuánto tiene que cambiar el color entre dos columnas para contar como borde.
UMBRAL_BORDE = 60
# La mitad de un paso se acepta como paso verdadero si correlaciona al menos
# así de bien respecto del ganador. Con 0.80 se colaba un tercio espurio.
UMBRAL_MITAD = 0.85
# Cuánto tiene que hundirse la correlación ENTRE la mitad y el candidato para
# creer que son fundamental y armónica. Si no baja de esto, es una meseta.
UMBRAL_VALLE = 0.75
# Fuerza mínima del latido para dar una ventana por "panel de velas".
# ⚠️ Medido sobre las tres capturas: DENTRO del panel el latido baila entre 0,08
# y 0,58 (una ventana puede caer en un tramo lateral, con velas casi iguales, y
# hundirse); FUERA cae a 0,00 o negativo. Con 0,25 la cadena se partía y el
# panel salía a un tercio de su tamaño. El corte va bajo y se toleran huecos.
LATIDO_MIN = 0.10
# Fracción de la densidad máxima de bordes para que una ventana cuente como
# parte del panel de velas.
# ⚠️ Se eligió PASÁNDOSE, no quedándose corto. Medido en las cuatro capturas:
# con 0,25 el panel de la MNQ se cortaba y perdía ~56 velas reales; con 0,20 el
# de la del OTE se pasa 330 px hacia la zona vacía. Pasarse cuesta UNA llamada
# de más sobre un trozo sin velas, de la que el modelo devuelve poco o nada y
# que el juntado descarta solo. Quedarse corto pierde velas, y una vela que no
# está no se puede recuperar después.
DENSIDAD_MIN = 0.20
HUECOS = 1
VENTANA = 160
BANDA = 40


def perfil_bordes(a, y0=None, y1=None):
    """Cuántos cambios de color hay entre cada columna y la siguiente."""
    H = a.shape[0]
    if y0 is None:
        y0, y1 = int(H * 0.20), int(H * 0.90)
    z = a[y0:y1]
    return (np.abs(z[:, 1:] - z[:, :-1]).sum(2) > UMBRAL_BORDE).sum(0).astype(float)


def _latido(p, paso):
    """Parecido del perfil consigo mismo desplazado `paso` columnas.

    ⚠️ `paso` puede ser fraccionario: se interpola entre columnas. Sin eso, un
    gráfico con paso 5,5 se mide como 11."""
    n = len(p)
    m = int(np.floor(n - paso))
    if m < 20:
        return 0.0
    j = np.arange(m) + paso
    j0 = np.floor(j).astype(int)
    fr = j - j0
    b = p[j0] * (1 - fr) + p[np.minimum(j0 + 1, n - 1)] * fr
    a_ = p[:m] - p[:m].mean()
    b = b - b.mean()
    d = float(np.sqrt((a_ * a_).sum() * (b * b).sum()))
    return float((a_ * b).sum() / d) if d > 1e-9 else 0.0


def _arranques(z, min_run):
    """Donde empieza cada trozo de vela en una franja horizontal.

    Una columna "tiene vela" si trae un trozo VERTICAL de al menos `min_run`
    pixeles distintos del fondo. Asi una punteada horizontal —un pixel suelto—
    no cuenta, que es lo que contamino tres medidas caseras el 13-sep.
    """
    pl = z.reshape(-1, 3)
    v, n = np.unique(pl[:, 0] * 65536 + pl[:, 1] * 256 + pl[:, 2],
                     return_counts=True)
    c = int(v[n.argmax()])
    fondo = np.array([c >> 16, (c >> 8) & 255, c & 255])
    tinta = np.abs(z - fondo).sum(2) > 60
    runs = np.zeros(tinta.shape[1], int)
    cur = np.zeros(tinta.shape[1], int)
    for fila in tinta:
        cur = np.where(fila, cur + 1, 0)
        runs = np.maximum(runs, cur)
    hay = runs >= min_run
    if hay.mean() > 0.95 or hay.mean() < 0.05:
        return None            # todo lleno o todo vacio: esa franja no sirve
    arr = np.array([i for i in range(len(hay))
                    if hay[i] and (i == 0 or not hay[i - 1])], float)
    return arr if len(arr) >= 6 else None


def _corte_bimodal(todas):
    """Donde separar "trozos de la misma vela" de "velas distintas".

    🔴 POR QUE HACE FALTA. Una vela HUECA —en las laminas del banco; las
    capturas del dueno son de velas rellenas con borde— deja TRES trozos de
    tinta: borde izquierdo, mecha del centro y borde derecho, porque el interior
    del cuerpo es fondo. Contando de trozo a trozo, el paso salia un TERCIO del
    real. Medido: de 27 laminas mal, las 27 tenian velas huecas.

    🔑 Dentro de una vela los trozos van MUY juntos y entre velas hay un salto
    mayor, asi que las distancias son bimodales. El corte se busca donde mas se
    separan los valores que DE VERDAD se repiten (los sueltos son ruido).

    ⛔ Se probo taparlo por pixeles —rellenar el hueco corto si sus columnas
    tenian algo de tinta— y el banco dijo que EMPEORA (53/80 -> 43/80): una
    punteada o la rejilla meten tinta en el hueco de ENTRE velas y las funde.
    Agrupar por distancias no mira la tinta, solo la geometria, y por eso no se
    deja enganar por lo que haya pintado de fondo.
    """
    vals, cnt = np.unique(todas, return_counts=True)
    usados = vals[cnt >= max(2, int(0.1 * cnt.max()))]
    if len(usados) < 2:
        return None
    saltos = np.diff(usados)
    k = int(saltos.argmax())
    return (usados[k] + usados[k + 1]) / 2.0 if saltos[k] >= 2 else None


def _junta(arr, corte):
    """Los trozos de una franja, agrupados en velas."""
    if corte is None:
        return arr
    g = [arr[0]]
    for i in range(1, len(arr)):
        if arr[i] - arr[i - 1] > corte:
            g.append(arr[i])
    return np.array(g, float)


def paso_por_huecos(a, x0, x1, y0=None, y1=None, min_run=3, franjas=9,
                    devuelve=False):
    """El paso entre velas, contando de una a la siguiente. Sin periodicidad.

    🔑 Es lo que hace una persona: ver donde empieza cada vela y medir hasta la
    siguiente. El metodo viejo (`paso_velas`) lo hacia por periodicidad y luego
    BAJABA A LA MITAD mientras el parecido aguantara, que en una senal de peine
    es la direccion equivocada: si las velas van cada 7, doblar sobre 3,5 encaja
    igual de bien. De ahi salia 3,25 donde el paso real era 8.

    🔴 SE JUNTAN TODAS LAS FRANJAS, NO SE ELIGE UNA. Antes ganaba la franja con
    la moda mas clara, y esa eleccion era el punto fragil de todo: en
    `mnq_5m_zoom` gano una con CATORCE manchas en 1574 px —distancias de 32, 57,
    184, 329— que no eran velas de ninguna clase, y el paso salio 10,69 en vez
    de 10,50. El numero no era impreciso: venia de otra cosa.
    🔑 Una franja sin velas da distancias cualesquiera, distintas en cada
    franja; el paso de verdad sale IGUAL en todas las que tocan velas. Asi que
    se echan todas a un mismo saco y gana lo que se repite. Sin elecciones que
    puedan salir mal.

    ⚠️ Va por franjas porque `panel()` devuelve la altura ENTERA a proposito
    (para no cortar velas), y con la barra de herramientas y el eje de tiempo
    dentro, "esta columna tiene vela" sale que si en el 100% de las columnas.
    """
    H = a.shape[0]
    if y0 is None:
        y0, y1 = 0, H - 1
    alto = y1 - y0 + 1
    crudos = []
    for k in range(franjas):
        for frac in (0.5, 0.3, 0.2):
            h = int(alto * frac)
            ini = y0 + int(k * (alto - h) / max(1, franjas - 1))
            arr = _arranques(a[ini:ini + h, x0:x1 + 1], min_run)
            if arr is not None:
                crudos.append(arr)
    if not crudos:
        return (None, 0.0, None) if devuelve else (None, 0.0)

    def saco(lista):
        d = []
        for arr in lista:
            x = np.diff(arr)
            x = x[(x >= 2) & (x <= 60)]
            if len(x):
                d.append(x)
        return np.concatenate(d) if d else None

    todas = saco(crudos)
    if todas is None or len(todas) < 5:
        return (None, 0.0, None) if devuelve else (None, 0.0)
    # 🔴 EL CORTE SE CALCULA FRANJA POR FRANJA, Y LA MODA SOBRE EL SACO COMUN.
    #    Las dos cosas por separado y en ese orden. Calcular el corte sobre el
    #    saco junto lo rompe: cada franja tiene su propio ruido, y el salto mas
    #    grande del histograma mezclado cae en cualquier sitio — salieron pasos
    #    de 45, 29 y 18 px donde los reales son 6,7, 5,5 y 7,4.
    #    Agrupar es una decision LOCAL (que trozos son de la misma vela, en esta
    #    franja); quedarse con lo que se repite es una decision GLOBAL.
    velas = []
    for arr in crudos:
        x = np.diff(arr)
        x = x[(x >= 2) & (x <= 60)]
        if len(x) < 5:
            continue
        g = _junta(arr, _corte_bimodal(x))
        if len(g) >= 6:
            velas.append(g)
    juntas = saco(velas) if velas else None
    if juntas is None or len(juntas) < 5:
        juntas, velas = todas, crudos
    vg, cg = np.unique(juntas, return_counts=True)
    m = float(vg[cg.argmax()])
    cerca = juntas[np.abs(juntas - m) <= 1]
    base = float(cerca.mean())
    conf = float(len(cerca)) / len(juntas)
    # 🔴 PARA AFINAR SE ELIGE LA FRANJA QUE MEJOR CONCUERDA CON EL PASO, no la
    #    que mas arranques tiene. Cogia `max(velas, key=len)` — o sea la mas
    #    POBLADA, que es la mas RUIDOSA: en `mnq_5m_zoom` daba 188 arranques con
    #    distancias de 3, 4, 5, 7 y 9 px sobre un paso real de 10,5. Eso no son
    #    velas, son trozos, y ajustar la recta sobre ellos devolvia 10,69.
    # 🔑 El paso ya lo decidio el saco comun; ahora solo hay que afinarlo sobre
    #    la franja que mas de acuerdo esta con el, que es la que de verdad ve
    #    velas enteras.
    def _acuerdo(g):
        x = np.diff(g)
        x = x[(x >= 2) & (x <= 60)]
        if len(x) < 5:
            return -1.0
        return float((np.abs(x - base) <= 1).mean())
    arr = max(velas, key=_acuerdo)
    fino = _afina_sobre(arr, base)
    if devuelve:
        return fino, conf, arr
    return fino, conf


def _afina_sobre(arr, base):
    """Ajusta `x = origen + k * paso` sobre los arranques de vela, por minimos
    cuadrados, para que el error NO se acumule a lo largo del panel.

    🔴 Hace falta porque la moda da un paso aproximado —10,68 donde el real es
    10,50— y ese 0,18 px parece inofensivo pero se ACUMULA: sobre 46 velas son
    8 px, casi una vela entera, y eso movia el BOS de x=886, el unico hecho de
    toda la cadena verificado contra una fuente independiente.

    ⚠️ Se descartan los arranques que no caen cerca de una ranura (dos velas
    pegadas que salieron como una sola racha), o el ajuste lo arrastran ellos.
    """
    if arr is None or len(arr) < 6 or not base or base < 2.5:
        return base
    paso = float(base)
    for _ in range(5):
        k = np.round((arr - arr[0]) / paso)
        cerca = np.abs(arr - (arr[0] + k * paso)) <= paso * 0.25
        if cerca.sum() < 5:
            break
        A = np.vstack([k[cerca], np.ones(int(cerca.sum()))]).T
        sol, *_ = np.linalg.lstsq(A, arr[cerca], rcond=None)
        if not (2.5 <= sol[0] <= 60):
            break
        paso = float(sol[0])
    return paso


def _elige(a, x0, x1, y0, y1, candidatos):
    """De varios pasos posibles, el que deja UNA vela por casilla.

    🔴 LA PRUEBA QUE SI DISCRIMINA. Se probo antes puntuar por "cuanta tinta
    cae dentro de la casilla" y NO sirve: con el paso doble cada casilla coge
    dos velas y dos huecos, asi que la tinta por columna sale parecida y ganaba
    el doble (13,33 donde el real era 6,7).

    🔑 Lo que si los separa: **cuantas velas hay DENTRO de una casilla**. Se
    dobla el perfil de tinta sobre una regla del largo del paso y se mira la
    forma resultante. Con el paso bueno queda UN monton; con el doble quedan
    DOS montones iguales separados medio paso — o sea que el perfil doblado se
    parece a si mismo corrido medio paso. Se elige el que MENOS se parece.
    """
    z = a[y0:y1 + 1, x0:x1 + 1]
    pl = z.reshape(-1, 3)
    v, n = np.unique(pl[:, 0] * 65536 + pl[:, 1] * 256 + pl[:, 2],
                     return_counts=True)
    c = int(v[n.argmax()])
    fondo = np.array([c >> 16, (c >> 8) & 255, c & 255])
    perfil = (np.abs(z - fondo).sum(2) > 60).sum(0).astype(float)
    mejor = None
    for paso in candidatos:
        if not paso or paso < 2.5 or paso > 60:
            continue
        m = int(round(paso * 4))          # 4 cubos por pixel, para medios px
        dob = np.zeros(m)
        for i, val in enumerate(perfil):
            dob[int(i * 4 / paso * paso / paso) % m if False else
                int(round(i * m / paso)) % m] += val
        if dob.sum() <= 0:
            continue
        d = dob - dob.mean()
        mitad = np.roll(d, m // 2)
        den = float(np.sqrt((d * d).sum() * (mitad * mitad).sum()))
        par = float((d * mitad).sum() / den) if den > 1e-9 else 1.0
        # `par` alto = dos montones iguales = el paso es el DOBLE del bueno
        if mejor is None or par < mejor[1]:
            mejor = (paso, par)
    return float(mejor[0]) if mejor else None


def paso_velas(perfil):
    """El paso entre velas, en píxeles (puede ser fraccionario).

    🔑 EL PROBLEMA DE LAS ARMÓNICAS. Si el paso real son 5,5 px, entonces 11 y
    16,5 también correlacionan bien, y a veces MEJOR. Quedarse con 11 haría
    recortes con la mitad de las velas debidas, así que hay que bajar a la
    fundamental. Pero bajar a lo bruto es peor todavía.

    ⛔ DOS CRITERIOS PROBADOS Y DESCARTADOS (2026-09-05, sobre 4 capturas reales):
    · "acepta la mitad si supera el 85% del mejor" → en la captura del OTE la
      curva es una MESETA (3,50 · 4,50 · 5,50 · 6,50 · 7,50 valen todas ~0,50),
      así que la mitad pasaba el umbral sin ser un paso real: 7,50 → 3,75, y el
      panel salió donde no hay ni una vela.
    · "acepta la mitad solo si es un pico local" → arregla la del OTE y rompe la
      del MES, donde la fundamental 5,50 no queda exactamente en p/2.

    🔑 EL CRITERIO QUE SÍ DISTINGUE: **el valle**. Entre una fundamental y su
    armónica la correlación se HUNDE (en la captura del MES cae a 0,13 entre
    5,5 y 11,25). En una meseta no se hunde: se queda en 0,42 de mínimo. Así que
    la mitad solo se acepta si entre ella y el candidato actual hay un valle de
    verdad. Medido sobre las cuatro capturas: 5,50 · 8,25 · 10,50 · 7,50, con
    reales 5,5 · 8 · 10,5 · 7,4."""
    paso_g = 0.25
    rej = np.arange(PASO_MIN, PASO_MAX + 0.01, paso_g)
    cur = np.array([_latido(perfil, float(p)) for p in rej])
    i = int(cur.argmax())
    fuerza = float(cur[i])
    while True:
        objetivo = rej[i] / 2.0
        if objetivo < PASO_MIN:
            break
        # el mejor de la vecindad de la mitad, no la mitad exacta
        cerca = np.nonzero(np.abs(rej - objetivo) <= 0.75)[0]
        if not len(cerca):
            break
        j = int(cerca[np.argmax(cur[cerca])])
        if cur[j] < UMBRAL_MITAD * fuerza:
            break
        valle = float(cur[j + 1:i].min()) if i > j + 1 else cur[j]
        if valle >= UMBRAL_VALLE * cur[j]:
            break                      # meseta: no es una armónica
        i, fuerza = j, float(cur[j])
    return float(rej[i]), fuerza


def _racha(marcas, huecos):
    """La racha más larga de `True`, tolerando `huecos` falsos seguidos."""
    mejor = None
    i = 0
    n = len(marcas)
    while i < n:
        if not marcas[i]:
            i += 1
            continue
        j = i
        k = i
        fallos = 0
        while j < n:
            if marcas[j]:
                k = j
                fallos = 0
            else:
                fallos += 1
                if fallos > huecos:
                    break
            j += 1
        if mejor is None or k - i > mejor[1] - mejor[0]:
            mejor = (i, k)
        i = j + 1
    return mejor


def panel(ruta):
    """(x0, x1, y0, y1) del panel de velas, y el paso entre velas."""
    a = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
    H, W, _ = a.shape
    perfil = perfil_bordes(a)
    # 🔴 EL PANEL SE ACOTA POR DENSIDAD DE BORDES, NO POR PERIODICIDAD.
    # Se probó con periodicidad y falla: una LÍNEA DISCONTINUA también es
    # periódica. En la captura del OTE, las ventanas de la zona vacía de la
    # derecha —solo cajas grises, fibs y punteadas— daban latidos de 0,48 y 0,68,
    # más altos que los de varias ventanas con velas de verdad, y el panel salió
    # en x 240-1440 cuando las velas están en 0-780.
    # 🔑 Lo que sí las separa es CUÁNTA tinta de borde hay: una vela es alta, así
    # que aporta decenas de cambios por columna; una raya aporta uno o dos.
    # Medido en esa captura: 8,6 a 38 donde hay velas, 0,7 a 4 donde no.
    paso_v = VENTANA // 2
    dens = [perfil[x:x + VENTANA].mean()
            for x in range(0, max(1, len(perfil) - VENTANA), paso_v)]
    tope = max(dens) if dens else 0.0
    marcas = [d >= DENSIDAD_MIN * tope for d in dens]
    tramo = _racha(marcas, HUECOS)
    if not tramo:
        return None
    x0 = tramo[0] * paso_v
    x1 = min(W, tramo[1] * paso_v + VENTANA)

    # 🔑 EL PASO SE MIDE AHORA, DENTRO DEL PANEL, Y NO ANTES. El orden importa
    # mas de lo que parece: el panel se acota por DENSIDAD de bordes, que no
    # necesita saber el paso, asi que no hay circularidad — y medir el paso
    # sobre la imagen entera metia el eje de precios y las barras dentro de la
    # cuenta, que es justo lo que impedia afinarlo (10,69 donde el real es
    # 10,50, y ese 0,19 acumulado sobre 46 velas mueve la rejilla casi una vela).
    # 🔴 `paso_por_huecos` cuenta de una vela a la siguiente; `paso_velas` lo
    # hacia por periodicidad y BAJABA A LA MITAD mientras el parecido aguantara,
    # que en una senal de peine es la direccion equivocada (si van cada 7,
    # doblar sobre 3,5 encaja igual de bien). Medido en el banco: 18 de 80
    # contra 54 de 80. El viejo se queda de reserva.
    paso = paso_por_huecos(a, int(x0), int(x1))[0]
    fuerza = 0.0
    if not paso:
        paso, fuerza = paso_velas(perfil[int(x0):int(x1) + 1])
    if not paso:
        return None

    # 🔴 EL ALTO NO SE RECORTA, A PROPÓSITO. Se probó detectarlo con la misma
    # medida de periodicidad por bandas horizontales, y en la captura zoomeada
    # devolvía y=240-640 sobre un panel que va de 200 a 800: **cortaba velas por
    # arriba y por abajo**, y una vela cortada se mide mal — que es justo el
    # fallo que llevamos días persiguiendo.
    # Y no hace falta: la regla de las 8 milésimas es sobre el ANCHO. Recortar
    # a lo alto no aporta nada y solo puede quitar información. La barra de
    # herramientas y el eje de tiempo se quedan dentro; medido sobre la captura
    # del MES, el modelo no encajonó ni un icono ni una etiqueta.
    y0, y1 = 0, H
    return {'x0': int(x0), 'x1': int(x1), 'y0': y0, 'y1': y1,
            'paso': round(paso, 2), 'fuerza': round(fuerza, 3),
            'velas': int((x1 - x0) / paso)}


def tiras(ruta, max_velas=MAX_VELAS, solape=6):
    """Los recortes que hay que mandarle al modelo.

    ⚠️ Se solapan unas velas a propósito: la que cae justo en la costura
    saldría partida entre dos tiras, y una vela a medias mide mal. Con solape
    aparece entera al menos en una, y luego se juntan por su posición."""
    p = panel(ruta)
    if not p:
        return []
    ancho = int(max_velas * p['paso'])
    salto = int(max(1, (max_velas - solape) * p['paso']))
    out, x = [], p['x1']
    while x > p['x0']:
        a = max(p['x0'], x - ancho)
        out.append((a, p['y0'], x, p['y1']))
        if a <= p['x0']:
            break
        x -= salto
    out.reverse()
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--imagen', required=True)
    ap.add_argument('--max-velas', type=int, default=MAX_VELAS)
    a = ap.parse_args()
    p = panel(a.imagen)
    if not p:
        raise SystemExit('no se encontró un panel de velas en esa imagen.')
    W, H = Image.open(a.imagen).size
    print('imagen %dx%d' % (W, H))
    print('panel  x %d-%d · y %d-%d · paso %.2f px (latido %.2f) · ~%d velas'
          % (p['x0'], p['x1'], p['y0'], p['y1'], p['paso'], p['fuerza'], p['velas']))
    ts = tiras(a.imagen, a.max_velas)
    print('%d recorte(s) de %d velas:' % (len(ts), a.max_velas))
    for (x0, y0, x1, y1) in ts:
        mil = p['paso'] / float(x1 - x0) * 1000
        print('   --recorte %d,%d,%d,%d   →  %.1f milésimas por vela %s'
              % (x0, y0, x1, y1, mil, '✅' if mil >= 8 else '🔴'))
