# -*- coding: utf-8 -*-
"""ANALIZADOR 2.0 — la cadena entera, de una captura a HECHOS VERIFICADOS.

    # completo, en el VPS (necesita la clave):
    python3 tools/analizador2.py --imagen docs/capturas_prueba/mnq_5m_zoom.png \\
        --modelo gemini:gemini-3.6-flash
    # sin red ni cuota, reusando las columnas que dejó la corrida anterior:
    python3 tools/analizador2.py --imagen ... \\
        --columnas @out/analizador2/columnas_mes_ote_perdedor.txt

🔴 NO TOCA EL ANALIZADOR DEL SITIO. Vive en tools/, la app no lo importa, y no
   sustituye a nada. Produce un BLOQUE DE HECHOS; qué se hace con él es una
   decisión del dueño, y hasta que la tome no se enchufa a ninguna parte.

═══ QUÉ ES ESTO Y QUÉ NO ═══
NO es una IA que mira un gráfico y opina. Es una cadena donde **cada eslabón
hace solo lo que sabe hacer**, medido:

  1. `recorta_grafico`  encuentra el panel y el paso entre velas   (píxeles)
  2. `cajas_ia`         dice EN QUÉ COLUMNA está cada vela         (modelo)
  3. `rejilla_velas`    recupera las velas que el modelo se dejó   (píxeles)
  4. `afina_velas`      mide máximo, mínimo y cuerpo de cada una   (píxeles)
  5. `afina_velas`      decide alcista/bajista sin conocer paleta  (píxeles)
  6. `eje_precio`       convierte altura en precio                 (modelo + píxeles)
  7. `hechos_grafico`   deduce los HECHOS                          (aritmética)

🔑 **EL PATRÓN QUE SE REPITIÓ CUATRO VECES, y que gobierna este diseño:** el
modelo **lee y reconoce muy bien, y sitúa mal**. Falló al dar el borde de la
vela (3-8 px de mediana, con casos de 30), al separar velas en una imagen ancha
(cada caja se comía 2-3), y al colocar las etiquetas del eje (177 px). Las tres
veces la solución fue la misma: **que el modelo diga QUÉ y aproximadamente
DÓNDE, y que los píxeles digan EXACTAMENTE dónde.** Aquí no se le pide nunca
una medida ni una comparación.

🔴 **Y UN QUINTO FALLO, DISTINTO DE LOS DEMÁS: se deja velas sin devolver.** No
es que las sitúe mal, es que no están. Sobre la captura del OTE devolvió 88
columnas donde hay ~102. Eso no lo arregla la precisión de los píxeles, porque
una vela que nadie señaló no se mide: se pierde. Por eso el paso 3 —la rejilla—
va ANTES de medir, y por eso es el eslabón del que dependen todos los números
de abajo. Ver `rejilla_velas`.

═══ QUÉ SE AFIRMA Y QUÉ NO ═══
Cada familia lleva su precisión MEDIDA (banco de 24 láminas, 1.420 velas, EN
CONDICIONES REALES: con el 14% de las velas fuera y recuperadas). El bloque
tiene TRES niveles, no dos, y el nivel lo decide el banco, no yo:

    se AFIRMA en seco   BOS 96,9% · acumulación (zona) 94,5% · barrida 93,1%
    se dice CON su      piscina BSL/SSL 76,9% · FVG+estado 67,7%
    tasa de acierto     order block 68,9% · manipulación 69,2%
    no se escribe       cualquier cosa por debajo de MIN_MENCION

🔴 POR QUÉ TRES Y NO DOS (2026-09-06). Con dos niveles el bloque solo podía
hablar de BOS y de barridas, y **jamás de un FVG, de un order block ni de
liquidez**: o sea que un analizador que vende ICT no podía nombrar ni una sola
pieza de ICT. El dueño lo dijo con estas palabras al leer una respuesta —«¿por
qué no ve los FVG si están dibujados?»—. Callarlos no era prudencia: era
entregar media herramienta.

⚠️ La diferencia con la lista "sin verificar" que se probó y fracasó (prueba C,
donde el modelo se inventó dos referencias) es de fondo: allí se daba una lista
NO comprobada pidiendo desconfianza. Aquí TODO está medido; lo único que cambia
entre niveles es con cuánta seguridad se afirma, y ese número sale del banco.
La auditoría de velas citadas que no estaban en el bloque sigue siendo
obligatoria de todos modos.

⚠️ Y si el eje no da consenso, el bloque sale **sin precios**: dirá "cerró por
debajo del swing" en vez de inventarse una cifra.
"""
from __future__ import print_function

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

import afina_velas as AF          # noqa: E402
import eje_precio as EP           # noqa: E402
import hechos_grafico as HG       # noqa: E402
import recorta_grafico as RG      # noqa: E402
import rejilla_velas as RV        # noqa: E402

# Precisión mínima MEDIDA para que una familia de hechos se pueda AFIRMAR.
MIN_PRECISION = 90.0
# 🔴 NÚMEROS BAJADOS A PROPÓSITO EL 09-sep, Y NO ES QUE EL CÓDIGO EMPEORE: es
# que la FÁBRICA ahora prueba un defecto que antes no probaba. Las láminas del
# banco llevan la marca de agua de sesión —el "NY AM" gigante del color de las
# velas— que rompía la captura real del dueño. Los números viejos (FVG 84,7 ·
# OB 82,6) estaban medidos en un mundo sin esa basura, o sea que eran
# optimistas: prometían al cliente una precisión que no tenían delante de un
# gráfico de verdad con indicadores encima.
# El arreglo del mismo día (`afina_velas._recorta_tinta_ajena`) sube el extenso
# de 85,8 a 92,0% CON la marca, y de 96,3 a 97,1% sin ella. Estos son los
# números honestos de la cadena en el mundo real, no un retroceso.
# ⚠️ Medidas además EN CONDICIONES REALES: quitándole el 14% de las velas (lo
# que el modelo se deja de verdad) y recuperándolas con la rejilla.
PRECISION = {'bos': 96.9, 'barrida': 93.1, 'fvg': 71.9, 'ob': 68.9,
             'piscina': 76.9, 'manip': 69.2, 'acum': 94.5}
# 🔑 EL 92,6 DE LA ACUMULACIÓN ES UNA ZONA, NO UNAS PUNTAS, y por eso la línea
# se redacta con "en torno a". Medido en el banco con tres listones distintos:
#     puntas exactas          70,2%
#     puntas con ±1 vela      74,5%
#     el tramo pisa al real
#     en más de la mitad      92,6%   ← lo que se afirma
# Es el único hecho del catálogo que no es una vela sino un TRAMO, así que
# exigirle las dos puntas le cobra dos veces el mismo error de medición. Lo que
# de verdad falla NO es que se invente laterales —el 92,6 dice que casi siempre
# hay uno ahí— sino dónde los corta. Si algún día la línea pasa a dar las velas
# exactas como dato firme, el número que le corresponde vuelve a ser 70,2.
# El FVG se imprime CON su estado (intacto / tocado / CE / lleno / invertido),
# así que la línea vale lo que vale el más flojo de los dos: 84,7 y 80,1.
PRECISION_ESTADO = 67.7
NOMBRE = {'bos': 'BOS', 'barrida': 'barrida de liquidez',
          'fvg': 'FVG', 'ob': 'order block', 'piscina': 'piscina de liquidez',
          'manip': 'pierna de manipulación', 'acum': 'acumulación'}
# Por debajo de esto un hecho no se escribe en ninguna parte.
# 🔴 BAJADO DE 78 A 65 EL 09-sep, y es una decisión, no un ajuste. Con la
# fábrica midiendo el mundo real, FVG (71,9), order block (68,9) y pierna de
# manipulación (69,2) caen por debajo de 78. Dejarlas fuera devuelve el
# analizador a donde estaba: capaz de hablar de BOS y de barridas y de NINGUNA
# pieza de ICT, que es exactamente lo que el dueño rechazó. Entran, pero cada
# línea lleva su tasa de acierto MEDIDA al lado: "acierta 72% de las veces" no
# es un adorno, es lo que separa informar de mentir.
MIN_MENCION = 65.0
FAMILIAS = ('bos', 'barrida', 'fvg', 'ob', 'piscina', 'manip', 'acum')
# Cuántas velas de giro a cada lado para que un extremo cuente como swing.
# Con k=2 el mismo tramo produce demasiados swings menores y los BOS se
# multiplican; con k=3 el primer evento coincidió con la marca del indicador
# del dueño. Ver CLAUDE.md.
K_SWING = 3
# Una vela no puede medir más de esto por la mediana de su propio gráfico.
# ⚖️ SE QUEDA EN 3,0, Y ES UN EMPATE SIN RESOLVER (09-sep). Medido:
# Con 3,0 una vela de DESPLAZAMIENTO —la que abre un FVG, la que rompe
# estructura— se pasa del tope, queda fuera de la votación y gana un fragmento
# de 4 px en un sitio absurdo. Es lo que destruyó las velas de entrada y salida
# de la cuarta captura del dueño, que miden 4-5 veces la mediana de su gráfico.
# ⚠️ El banco no podía opinar sobre esto hasta el mismo día: su generador hacía
# velas de tamaño uniforme y NUNCA producía un desplazamiento, así que 3,0 · 5,0
# y 6,0 daban el mismo número clavado. Con desplazamientos dentro:
#     3,0 → 90,0%   ·   5,0 → 91,0%   ·   6,0 → 91,2%   ·   8,0 → 91,3%
# Pero subirlo ROMPE el BOS de la vela x=886, que es el único hecho de toda la
# cadena verificado contra una fuente independiente (la marca del indicador
# BoS/ChoCh del propio dueño). El reparto exacto:
#     tope ≤ 3,5 → BOS x=886 ✅ · velas de su cuarta captura 2 de 6 bien
#     tope ≥ 4,0 → BOS x=886 🔴 · velas de su cuarta captura 3 de 6 bien
# Ganar una vela a cambio del único hecho contrastado contra el mundo real no
# es una mejora, es un canje. Y el +1,2 del banco se midió en una fábrica que
# acababa de cambiar (los desplazamientos son nuevos), así que no es comparable
# con la que validó el 3,0.
# 🔴 QUEDA ABIERTO: hace falta un SEGUNDO punto de verdad externa —otra captura
# con la marca de un indicador que podamos contrastar— para desempatar. Hasta
# entonces, no se toca.
TOPE_ALTO = 3.0
# 🔴 NUNCA UN ALIAS `-latest` PARA TRABAJO MEDIBLE. Google apuntó
# `gemini-flash-latest` a un modelo nuevo con 20 peticiones gratis al día y la
# misma orden que llevaba semanas funcionando empezó a fallar sin que aquí
# cambiara nada. Peor que el corte: un alias cambia el modelo EN SILENCIO, así
# que dos corridas del mismo comando pueden medir cosas distintas y uno se lo
# atribuye al código. Se fija un nombre concreto, y cambiarlo es una decisión
# que se ve. `cajas_ia --modelos gemini` lista los que acepta la clave.
# 🔴 TERCERA VEZ QUE GOOGLE RETIRA EL MODELO BAJO LOS PIES (08-sep). Primero
# `gemini-2.5-flash-lite`, luego el alias `-latest`, y ahora `gemini-2.5-flash`
# con un 404 «no longer available to new users». El daño no fue quedarse sin
# modelo: fue que la corrida SIGUIÓ ADELANTE sin eje de precios y el resultado
# parecía una prueba válida cuando ya no lo era. Fijar el modelo no basta; hay
# que ver el fallo. `cajas_ia --modelos gemini` lista los que acepta la clave.
MODELO_POR_DEFECTO = 'gemini:gemini-3.6-flash'


def _columnas_del_modelo(ruta, prov, modelo, max_velas, callback=None):
    """Llama al modelo una vez por tira y junta las columnas.

    ⚠️ Las tiras se SOLAPAN a propósito, así que la misma vela sale en dos.
    Se juntan por posición: dos cajas cuyo centro dista menos de medio paso son
    la misma vela. Sin esto, la vela de la costura entraría dos veces y todos
    los índices posteriores quedarían corridos."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'ci', os.path.join(RAIZ, 'tools', 'cajas_ia.py'))
    ci = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ci)
    im = Image.open(ruta)
    W, H = im.size
    p = RG.panel(ruta)
    if not p:
        raise SystemExit('no se encontró un panel de velas en esa imagen.')
    clave = ci._clave(prov)
    carpeta = os.path.join(RAIZ, 'out', 'analizador2')
    if not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    todas = []
    tiras = RG.tiras(ruta, max_velas)
    for i, (x0, y0, x1, y1) in enumerate(tiras):
        if callback:
            callback(i + 1, len(tiras), (x0, y0, x1, y1))
        parte = os.path.join(carpeta, '_tira_%d.png' % i)
        im.crop((x0, y0, x1, y1)).save(parte)
        txt = ci._pregunta(prov, modelo, clave, parte, todas=True)
        for c in ci._cajas(txt):
            ym, xm, yM, xM = c
            px0 = x0 + xm / 1000.0 * (x1 - x0)
            px1 = x0 + xM / 1000.0 * (x1 - x0)
            py0 = y0 + ym / 1000.0 * (y1 - y0)
            py1 = y0 + yM / 1000.0 * (y1 - y0)
            if px1 < px0:
                px0, px1 = px1, px0
            if py1 < py0:
                py0, py1 = py1, py0
            todas.append((int(round(px0)), int(round(px1)),
                          int(round(py0)), int(round(py1))))
    cajas = _junta(todas, p['paso'])
    # 🔑 SE GUARDAN EN CUANTO SE TIENEN. Son lo único de la cadena que cuesta
    # dinero y depende de que Google conteste; todo lo demás son píxeles y
    # aritmética. Con el archivo, cualquier prueba posterior sobre esta misma
    # captura se corre con `--columnas @<archivo>`, sin red y sin cuota.
    guarda_columnas(cajas, ruta)
    return cajas, p


def _archivo_columnas(ruta):
    base = os.path.splitext(os.path.basename(ruta))[0]
    return os.path.join(RAIZ, 'out', 'analizador2', 'columnas_%s.txt' % base)


def guarda_columnas(cajas, ruta):
    destino = _archivo_columnas(ruta)
    carpeta = os.path.dirname(destino)
    if not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    with open(destino, 'w') as f:
        f.write(','.join('%d-%d:%d-%d' % c for c in cajas))
    print('   columnas guardadas en %s' % destino)
    return destino


def lee_columnas(texto):
    """`--columnas` acepta la lista, o `@ruta` de un archivo con la lista."""
    if texto.startswith('@'):
        with open(texto[1:]) as f:
            texto = f.read().strip()
    cajas = []
    for t in texto.split(','):
        if not t.strip():
            continue
        xs, _, ys = t.strip().partition(':')
        x0, _, x1 = xs.partition('-')
        y0, _, y1 = ys.partition('-')
        cajas.append((int(x0), int(x1), int(y0), int(y1)))
    return cajas


def _junta(cajas, paso):
    """Una caja por vela: se funden las que caen en la misma columna."""
    cajas = sorted(cajas, key=lambda c: (c[0] + c[1]) / 2.0)
    out = []
    for c in cajas:
        cx = (c[0] + c[1]) / 2.0
        if out and abs(cx - (out[-1][0] + out[-1][1]) / 2.0) < paso / 2.0:
            a = out[-1]
            out[-1] = (min(a[0], c[0]), max(a[1], c[1]),
                       min(a[2], c[2]), max(a[3], c[3]))
        else:
            out.append(c)
    return out


def normaliza_ancho(cajas, paso):
    """Todas las columnas al MISMO ancho, centradas donde dijo el modelo.

    🔴 EL FALLO QUE ESTO ARREGLA, medido sobre la captura del dueño. El paso
    entre velas es 7,5 px y la vela mide ~6, pero las cajas que devolvió el
    modelo iban **de 5 a 12 px de ancho**, y **23 de 104 se solapaban con la
    siguiente**. Una columna de 12 px con las velas a 7,5 de distancia contiene
    por fuerza a la vecina: `afina` recibe una franja con DOS velas dentro y
    elige mal. De ahí los tres síntomas que él reportó una y otra vez — un
    recuadro que coge dos cuerpos, otro que coge fondo, otro que se queda a
    medias — y ninguno se arreglaba tocando la regla del cuerpo, porque el
    problema entraba antes.

    🔑 Es la misma doctrina que gobierna el resto de la cadena: **el modelo
    dice DÓNDE y los píxeles dicen CUÁNTO.** El ancho no hay que preguntárselo
    a nadie: lo dice el paso, que se mide de la propia imagen. Se conserva el
    CENTRO de su caja, que es lo único que hace bien.

    ⚠️ El ancho se corta por `paso - 1` para que dos columnas consecutivas no
    puedan tocarse ni con el redondeo. Y no se fuerza a ese valor: se toma la
    mediana de lo que dio el modelo si es más estrecha, porque hay gráficos con
    velas finas y separadas donde estirar la columna metería fondo dentro."""
    if not cajas:
        return cajas
    tope = max(2, int(round(paso)) - 1)
    ancho = int(min(np.median([c[1] - c[0] + 1 for c in cajas]), tope))
    ancho = max(2, ancho)
    out = []
    for (x0, x1, gy0, gy1) in cajas:
        cx = (x0 + x1) / 2.0
        nx0 = int(round(cx - (ancho - 1) / 2.0))
        out.append((nx0, nx0 + ancho - 1, gy0, gy1))
    return out


def encaja_en_rejilla(cajas, paso, a_img, banda, ancho=None):
    """Cada columna, ENCAJADA en la rejilla real de velas de la imagen.

    🔴 EL FALLO GORDO, y estuvo tapando a todos los demás durante una sesión
    entera. Medido sobre la captura del dueño comparando contra la posición
    REAL de sus velas (sacada del color de sus cuerpos):

        velas de verdad   198-200  206-208  213-215  221-223  228-230 …
        columnas usadas   200-205  208-213  215-220  223-228  230-235 …
        desplazamiento    +3,5 px  =  MEDIA VELA

    Cada columna caía **a caballo entre una vela y el hueco siguiente**. De ahí
    los cuatro síntomas que él repitió sin que yo diera con la causa: el
    recuadro del cuerpo pintando fondo, cogiendo trozos de dos velas, no
    llegando a cubrir el cuerpo, y mechas quedándose fuera de la medición.
    Y de ahí también que NINGUNA corrección a la regla del cuerpo sirviera:
    el error entra tres pasos antes, y a partir de ahí da igual lo fino que
    hiles.

    🔑 La rejilla no se le pregunta al modelo: se mide. Se conoce el paso (sale
    de la autocorrelación de `recorta_grafico`, verificado en tres capturas:
    5,62 · 8,25 · 10,50 contra 5,5 · 8 · 10,5) y la FASE se busca probando
    desplazamientos de 0,05 px y quedándose con el que más tinta recoge. Sobre
    la captura del dueño la rejilla así calculada da 196-201, 204-209, 211-216…
    contra sus velas reales en 197-201, 205-209, 212-216: **1 px**.

    ⚠️ Se conserva el ORDEN del modelo, no se inventan ranuras: cada caja se
    lleva a la ranura más cercana, y si dos caen en la misma se quedan en una.
    Rellenar los huecos sigue siendo trabajo de `rejilla_velas`, que además
    exige que la ranura demuestre tener una vela."""
    if not cajas:
        return cajas
    if ancho is None:
        tope = max(2, int(round(paso)) - 1)
        ancho = int(max(2, min(np.median([c[1] - c[0] + 1 for c in cajas]), tope)))
    vent = a_img[banda[0]:banda[1]]
    tinta = (np.abs(vent - AF._fondo_por_fila(vent)[:, None, :]).sum(2)
             > AF.UMBRAL_TINTA)
    col = tinta.sum(0).astype(float)
    xs0 = min(c[0] for c in cajas)
    xs1 = max(c[1] for c in cajas)
    mejor = None
    for f in np.arange(0, paso, 0.05):
        tot, cu, x = 0.0, 0, xs0 + f
        while x <= xs1:
            i0 = int(round(x))
            tot += col[max(0, i0):i0 + ancho].sum()
            cu += 1
            x += paso
        if cu and (mejor is None or tot / cu > mejor[1]):
            mejor = (f, tot / cu)
    if mejor is None:
        return cajas
    origen = xs0 + mejor[0]
    vistos, out = set(), []
    for (x0, x1, gy0, gy1) in sorted(cajas, key=lambda c: c[0] + c[1]):
        cx = (x0 + x1) / 2.0
        k = int(round((cx - (origen + (ancho - 1) / 2.0)) / paso))
        if k in vistos:
            continue
        vistos.add(k)
        nx0 = int(round(origen + k * paso))
        out.append((nx0, nx0 + ancho - 1, gy0, gy1))
    return out


def banda_de_las_guias(cajas, H):
    """La franja vertical donde de verdad hay gráfico, sacada de las guías.

    🔴 POR QUÉ NO SE MIDE SOBRE LA IMAGEN ENTERA (cazado al encadenar, 2026-09-05).
    `afina` calcula la paleta de fondos con las filas de su ventana. Si en la
    ventana entran la barra de herramientas de arriba y el eje de tiempo de
    abajo —llenos de texto e iconos—, esos colores desplazan a los fondos de
    verdad fuera de la paleta y la medición cambia. Medido sobre la captura del
    dueño: con la imagen entera el BOS validado contra su indicador (x=886)
    DESAPARECÍA y salían otros tres; con la franja del gráfico vuelve a salir.

    🔑 La franja no se adivina ni se fija a mano: la dicen las guías del modelo,
    que ya sabemos dónde caen. Se les da un margen ANCHO (dos veces la altura
    típica de una vela) para que no puedan recortar ninguna: el error de la guía
    es de 3-8 px de mediana y 30-40 en el peor caso, muy por debajo del margen.

    ⚠️ Esto es solo para MEDIR. Lo que se le manda al modelo sigue yendo con
    toda la altura: recortar ahí sí cortaría velas."""
    if not cajas:
        return 0, H
    alto = np.median([c[3] - c[2] for c in cajas])
    margen = max(40, int(2 * alto))
    y0 = max(0, int(min(c[2] for c in cajas)) - margen)
    y1 = min(H, int(max(c[3] for c in cajas)) + margen)
    return y0, y1


def mide(ruta, cajas, nuevas=None):
    """De columnas a velas medidas, EN DOS PASADAS.

    🔑 La segunda pasada nació de la captura real: dos velas pegadas al borde
    vertical de la banda de killzone se midieron de 425 px con una mediana de
    70 — se habían enganchado al borde. La altura creíble de una vela no es un
    número fijo: la dice el propio gráfico."""
    a = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
    H, W, _ = a.shape
    by0, by1 = banda_de_las_guias(cajas, H)

    FCOL = AF.fondo_por_columna(a, by0, by1)
    CVELA = AF.colores_de_vela(a, by0, by1, FCOL)
    FLIN = AF.filas_de_linea(a, by0, by1, 0, W)

    nuevas = nuevas or set()

    def pasada(tope):
        out = []
        for caja in cajas:
            x0, x1, gy0, gy1 = caja
            margen = max(4, 2 * (x1 - x0 + 1))
            r = AF.afina(a, x0, x1, by0, by1, margen, False, (gy0, gy1),
                         tope, FCOL, CVELA, FLIN)
            if r is None:
                out.append(None)
                continue
            alto, bajo, ct, cb, sx0, sx1 = r
            reg = a[ct:cb + 1, sx0:sx1 + 1].reshape(-1, 3)
            pl = reg[:, 0] * 65536 + reg[:, 1] * 256 + reg[:, 2]
            v, n = np.unique(pl, return_counts=True)
            col = int(v[n.argmax()])
            out.append({'x0': sx0, 'x1': sx1, 'max': alto, 'min': bajo,
                        'cuerpo_alto': ct, 'cuerpo_bajo': cb,
                        'rejilla': caja in nuevas,
                        'color': (col >> 16, (col >> 8) & 255, col & 255)})
        return out

    prim = pasada(None)
    alturas = [v['min'] - v['max'] for v in prim if v]
    if len(alturas) >= 5:
        tope = int(round(TOPE_ALTO * np.median(alturas)))
        sosp = [i for i, v in enumerate(prim)
                if v and (v['min'] - v['max']) > tope]
        if sosp:
            seg = pasada(tope)
            for i in sosp:
                if seg[i]:
                    prim[i] = seg[i]
    return [v for v in prim if v]


def serie(velas):
    """Velas medidas → OHLC en unidades de -y.

    🔑 El precio no hace falta para deducir los hechos: TODOS son comparaciones,
    y una comparación no cambia al multiplicar por una constante positiva. La
    escala solo se usa para ESCRIBIR el resultado."""
    AF.direccion(velas)
    out = []
    for v in velas:
        h, l = -v['max'], -v['min']
        if v['alcista']:
            o, c = -v['cuerpo_bajo'], -v['cuerpo_alto']
        else:
            o, c = -v['cuerpo_alto'], -v['cuerpo_bajo']
        out.append((o, h, l, c))
    return out


def hechos(ohlc):
    """Los hechos, por familia, con el índice de la vela."""
    g = HG.fvgs(ohlc)
    out = dict((f, []) for f in FAMILIAS)

    def _uno_por_vela(lista):
        """Una línea por vela, no una por swing roto.

        🔴 CAZADO EN LA PRIMERA CORRIDA SOBRE EL GRÁFICO ENTERO. Una vela que
        se lleva por delante TRES swings anteriores salía tres veces:
            vela 123 · BOS alcista: atravesó el swing de la vela 89
            vela 123 · BOS alcista: atravesó el swing de la vela 95
            vela 123 · BOS alcista: atravesó el swing de la vela 112
        No son tres rupturas: es UNA, y un trader la nombra una vez. Con 46
        velas casi no se notaba; con 162 el bloque se vuelve ilegible, y un
        bloque ilegible no lo lee nadie — ni una persona ni una IA.

        🔑 Se conserva el swing de índice MÁS ALTO, que es el más RECIENTE: ese
        es el que define la estructura vigente. Romper los de más atrás viene
        implícito en romper el último."""
        mejor = {}
        for b in lista:
            k = (b['i'], b['tipo'])
            if k not in mejor or b['swing'] > mejor[k]['swing']:
                mejor[k] = b
        return sorted(mejor.values(), key=lambda b: b['i'])

    for b in _uno_por_vela(HG.bos_eventos(ohlc, K_SWING)):
        out['bos'].append({'i': b['i'], 'tipo': b['tipo'],
                           'nivel': b['nivel'], 'swing': b['swing']})
    vistas = set()
    barridas = []
    for b in HG.barridas(ohlc, K_SWING):
        if (b['swing'], b['tipo']) in vistas:
            continue
        vistas.add((b['swing'], b['tipo']))
        barridas.append(b)
    for b in _uno_por_vela(barridas):
        out['barrida'].append({'i': b['i'], 'tipo': b['tipo'],
                               'nivel': b['nivel'], 'swing': b['swing']})
    def _sin_repetir(lista):
        """El mismo hecho, una sola vez.

        🔴 Cazado en la primera corrida completa sobre la captura del dueño:
        `vela 2 · order block alcista entre 7.716,80 y 7.717,57` salía DOS
        VECES, palabra por palabra, y con ella otras dos. La causa es de
        construcción: un order block se deriva de un FVG, y una misma vela
        puede ser el origen de dos FVG solapados —así que se emite una vez por
        cada uno. No son dos hechos: es uno contado dos veces.

        ⚠️ Importa más de lo que parece. Este bloque está pensado para que lo
        lea una IA además de una persona, y un hecho repetido se lee como
        confirmación: dos menciones del mismo order block sugieren que hay dos
        zonas ahí. Se repiten los CUATRO campos, así que dos zonas de verdad
        distintas (mismo índice, distinto rango) siguen saliendo las dos."""
        vistos, out = set(), []
        for h in lista:
            k = (h['i'], h['tipo'], h['suelo'], h['techo'])
            if k in vistos:
                continue
            vistos.add(k)
            out.append(h)
        return out

    # 🔑 El FVG sale CON SU ESTADO. Dónde hay un hueco es media respuesta; la
    #    otra media —y la que el dueño preguntó con estas palabras, "el FVG
    #    literal ni se ha tocado"— es en qué quedó. Van juntos en la misma
    #    línea porque separados invitan a leer dos hechos donde hay uno.
    out['fvg'] = _sin_repetir(
        [{'i': f['i'], 'tipo': f['tipo'], 'suelo': f['suelo'],
          'techo': f['techo'], 'estado': f['estado'],
          'tocado_en': f['tocado_en'], 'ce_en': f['ce_en'],
          'lleno_en': f['lleno_en'], 'invertido_en': f['invertido_en']}
         for f in HG.estado_fvgs(ohlc, g)])
    out['piscina'] = HG.piscinas(ohlc, K_SWING)
    out['manip'] = HG.manipulacion(ohlc, K_SWING)
    out['acum'] = HG.acumulacion(ohlc)
    out['ob'] = _sin_repetir(
        [{'i': o['i'], 'tipo': o['tipo'], 'suelo': o['suelo'],
          'techo': o['techo']} for o in HG.order_blocks(ohlc, g)])
    return out


def _pre(valor, escala):
    """Un valor de la serie (-y) a precio, si hay escala."""
    if not escala:
        return None
    return escala['precio'](-valor)


ESTADO_TXT = {
    'intacto': 'NO ha vuelto a tocarse',
    'tocado': 'el precio entró en él pero no llegó al 50%%, en la vela %s',
    'ce': 'el precio llegó a su 50%% (CE) en la vela %s',
    'lleno': 'se rellenó entero en la vela %s',
    'invertido': 'quedó INVALIDADO: un cierre lo atravesó en la vela %s',
}


def precision_de(fam):
    """La tasa de acierto que se le atribuye a la línea de esa familia."""
    if fam == 'fvg':
        return min(PRECISION['fvg'], PRECISION_ESTADO)
    return PRECISION[fam]


def bloque(velas, hs, escala, minimo=MIN_PRECISION, minimo_mencion=MIN_MENCION):
    """El BLOQUE DE HECHOS: lo único que se le entregaría a una IA.

    🔴 TRES NIVELES, NO DOS (2026-09-06). Antes solo entraban las familias por
    encima del mínimo y el resto se callaba entero. El efecto de eso, dicho por
    el dueño al leer una respuesta, es que el analizador podía hablar de BOS y
    de barridas y **jamás de un FVG, de un order block ni de liquidez** — o sea
    que no podía hablar de ICT, que es la metodología que vende el sitio.

        ≥ `minimo` (90%)        se afirma en seco
        ≥ `minimo_mencion`      se escribe CON su tasa de acierto medida al lado
        por debajo               no se escribe en ninguna parte

    🔑 La diferencia con lo que falló en la prueba C no es cosmética. Allí se
    le entregaba una lista SIN verificar pidiéndole que desconfiara, y se
    inventó dos referencias. Aquí todas las líneas están medidas; lo único que
    cambia entre los dos niveles es con cuánta seguridad se puede afirmar cada
    una, y ese número no lo pone el modelo: lo pone el banco.

    ⚠️ Que se escriba no garantiza que el modelo lo cite bien. La auditoría de
    `analizador_lab` (velas citadas que no estaban en el bloque) sigue siendo
    obligatoria."""
    def linea(fam, h):
        x = velas[h['i']]['x0']
        n = 'vela %d (x=%d)' % (h['i'], x)
        if fam == 'bos':
            p = _pre(h['nivel'], escala)
            return ('%s · BOS %s: el CIERRE atravesó el swing de la vela %d%s'
                    % (n, h['tipo'], h['swing'],
                       '' if p is None else ' en %s' % _fmt(p)))
        if fam == 'barrida':
            p = _pre(h['nivel'], escala)
            return ('%s · barrida %s: la mecha pasó el swing de la vela %d%s '
                    'y el cuerpo cerró DENTRO — no es ruptura'
                    % (n, h['tipo'], h['swing'],
                       '' if p is None else ' en %s' % _fmt(p)))
        if fam == 'piscina':
            p = _pre(h['nivel'], escala)
            return ('%s · %s: %d máximos%s de giro iguales%s (velas %s) — %s'
                    % (n, h['tipo'], h['toques'],
                       '' if h['lado'] == 'alto' else ' (mínimos)',
                       '' if p is None else ' en %s' % _fmt(p),
                       ', '.join(str(v) for v in h['velas']),
                       'liquidez SIN tomar todavía' if h['tomada_en'] is None
                       else 'tomada en la vela %d' % h['tomada_en']))
        if fam == 'manip':
            p = _pre(h['nivel'], escala)
            apoyo = ('FVG en la vela %d' % h['fvg']) if h['fvg'] is not None \
                else ('BOS en la vela %d' % h['bos'])
            return ('%s · pierna de manipulación %s: barrió el swing de la '
                    'vela %d%s y el precio se dio la vuelta (%s)'
                    % (n, h['tipo'], h['swing'],
                       '' if p is None else ' en %s' % _fmt(p), apoyo))
        if fam == 'acum':
            a, b = _pre(h['techo'], escala), _pre(h['suelo'], escala)
            return ('en torno a las velas %d-%d (extremos aproximados) · '
                    'acumulación: unas %d velas dentro de una franja%s '
                    '(se pisan entre sí: el tramo mide el %d%% de lo que suman '
                    'sus velas)'
                    % (h['i'], h['fin'], h['fin'] - h['i'] + 1,
                       '' if a is None else ' de %s a %s' % (_fmt(b), _fmt(a)),
                       int(round(100 * h['solape']))))
        a, b = _pre(h['techo'], escala), _pre(h['suelo'], escala)
        rango = '' if a is None else ' entre %s y %s' % (_fmt(b), _fmt(a))
        if fam == 'ob':
            return '%s · order block %s%s' % (n, h['tipo'], rango)
        est = ESTADO_TXT[h['estado']]
        if '%s' in est:
            est = est % (h['tocado_en'] if h['estado'] == 'tocado' else
                         h['ce_en'] if h['estado'] == 'ce' else
                         h['lleno_en'] if h['estado'] == 'lleno' else
                         h['invertido_en'])
        return '%s · FVG %s%s — %s' % (n, h['tipo'], rango, est)

    # 🔴 EN ORDEN CRONOLÓGICO, NO AGRUPADOS POR FAMILIA. Cazado en la primera
    # comparación real contra el analizador del sitio: con los hechos agrupados
    # —todos los BOS juntos, después todas las barridas— el modelo perdió la
    # secuencia y escribió «hubo un BOS bajista en la vela 44… el precio LUEGO
    # mostró un BOS alcista en la vela 25». La vela 25 va ANTES que la 44.
    # Un bloque que destruye el orden temporal es peor que no dar bloque,
    # porque el modelo se fía de él: le entregamos un informe con los párrafos
    # barajados y razonó sobre ese desorden.
    firmes, medidos = [], []
    for fam in FAMILIAS:
        pr = precision_de(fam)
        if pr < minimo_mencion:
            continue
        destino = firmes if pr >= minimo else medidos
        for h in hs[fam]:
            t = linea(fam, h)
            if destino is medidos:
                t = '%s  [medido: acierta %.0f%% de las veces]' % (t, pr)
            destino.append((h['i'], fam, t))
    firmes.sort(key=lambda t: t[0])
    medidos.sort(key=lambda t: t[0])
    return ([(f, t) for _i, f, t in firmes],
            [(f, t) for _i, f, t in medidos])


def _fmt(p):
    """29428.5 → '29.428,50'. 🔴 Antes usaba '%,.2f', que NO existe en Python:
    la coma como separador de miles solo la entiende `format`. Nunca había
    saltado porque hasta ahora el eje siempre venía sin escala y esta función
    no llegaba a ejecutarse — el primer gráfico con precios la reventó."""
    return '{:,.2f}'.format(p).replace(',', '@').replace('.', ',').replace('@', '.')


def analiza(ruta, prov=None, modelo=None, cajas=None, max_velas=80,
            verboso=True):
    def aviso(i, n, r):
        if verboso:
            print('   tira %d/%d  %s' % (i, n, r))
    if cajas is None:
        if not (prov and modelo):
            raise SystemExit('hace falta --modelo, o --columnas ya obtenidas.')
        cajas, p = _columnas_del_modelo(ruta, prov, modelo, max_velas, aviso)
    else:
        p = RG.panel(ruta)

    # 🔴 LAS VELAS QUE EL MODELO SE DEJÓ. Sobre la captura real devolvió 88 de
    # ~102, y una vela que falta no se nota: la lista se cierra sobre sí misma.
    # Medido en el banco, con el 14% de las velas fuera los hechos se caen
    # (BOS 100→63,5% · FVG 90,6→12% · OB 88,7→4,6%), así que esto no es un
    # retoque, es lo que sostiene todo lo demás. Ver `rejilla_velas`.
    # 🔴 ANTES DE NADA: todas las columnas al mismo ancho. Si entra una caja
    #    más ancha que el paso, arrastra a la vela vecina y todo lo que viene
    #    después mide sobre una franja con dos velas. Ver `normaliza_ancho`.
    cajas = normaliza_ancho(cajas, p['paso'])
    a_img = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
    banda = banda_de_las_guias(cajas, a_img.shape[0])
    # 🔴 Y AHORA A LA REJILLA REAL. Las columnas del modelo venían a media vela
    #    de donde están; ver `encaja_en_rejilla`.
    cajas = encaja_en_rejilla(cajas, p['paso'], a_img, banda)
    banda = banda_de_las_guias(cajas, a_img.shape[0])
    del_modelo = len(cajas)
    cajas, nuevas = RV.completa(cajas, p['paso'], a_img, banda)
    if verboso and nuevas:
        print('   rejilla: el modelo devolvió %d columnas, %d recuperadas'
              % (del_modelo, len(nuevas)))

    velas = mide(ruta, cajas, nuevas)
    if len(velas) < 5:
        raise SystemExit('solo se pudieron medir %d velas.' % len(velas))
    ohlc = serie(velas)
    escala = None
    if prov and modelo:
        try:
            et, _crudo = EP.lee(prov, modelo, ruta)
            escala = EP.ajusta(et)
        except SystemExit:
            escala = None
    return {'panel': p, 'velas': velas, 'ohlc': ohlc, 'escala': escala,
            'hechos': hechos(ohlc)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--imagen', required=True)
    ap.add_argument('--modelo', metavar='PROVEEDOR:MODELO',
                    default=MODELO_POR_DEFECTO)
    ap.add_argument('--columnas', help='x0-x1:y0-y1,... ya obtenidas, o '
                                       '@ruta del archivo que deja la corrida '
                                       'anterior. Corre la cadena entera SIN '
                                       'red y SIN cuota.')
    ap.add_argument('--max-velas', type=int, default=80)
    ap.add_argument('--json', help='guarda el resultado completo ahí')
    ap.add_argument('--dibuja', help='PNG con las velas medidas dibujadas encima')
    a = ap.parse_args()
    prov = modelo = None
    if a.modelo:
        prov, _, modelo = a.modelo.partition(':')
    cajas = lee_columnas(a.columnas) if a.columnas else None

    if not a.columnas:
        # 🔑 Queda ESCRITO en la salida qué modelo la produjo. Ahora que el
        # modelo se puede cambiar, una medición sin esa línea no se puede
        # comparar con otra.
        print('modelo: %s' % a.modelo)
    r = analiza(a.imagen, prov, modelo, cajas, a.max_velas)
    p, velas, escala = r['panel'], r['velas'], r['escala']
    print('\npanel x %d-%d · paso %.2f px · %d velas medidas'
          % (p['x0'], p['x1'], p['paso'], len(velas)))
    if escala:
        print('escala del eje: %.4f puntos/px · %d de %d etiquetas de acuerdo'
              % (escala['por_px'], escala['apoyos'], escala['total']))
    else:
        print('🔴 sin escala fiable: el bloque sale SIN precios (correcto).')

    firmes, marcados = bloque(velas, r['hechos'], escala)
    print('\n═══ HECHOS VERIFICADOS (%d) ═══' % len(firmes))
    print('   familias que superan el %.0f%% de precisión medida: %s'
          % (MIN_PRECISION, ', '.join(
              NOMBRE[f] for f in PRECISION if PRECISION[f] >= MIN_PRECISION)))
    for _fam, l in firmes:
        print('   · ' + l)
    print('\n─── NO se afirman todavía (%d) ───' % len(marcados))
    for fam in ('fvg', 'ob'):
        if PRECISION[fam] < MIN_PRECISION:
            print('   %s: %.1f%% de precisión medida' % (NOMBRE[fam], PRECISION[fam]))
    for _fam, l in marcados:
        print('   · ' + l)
    if a.dibuja:
        # 🔑 MIRAR ES PARTE DE MEDIR. Un bloque de hechos con velas que faltan
        # sigue pareciendo perfectamente razonable: los índices corren, los
        # precios salen, y nada avisa. La única forma de saber si la cadena vio
        # TODAS las velas es dibujarlas sobre el gráfico y mirarlo.
        # 🔴 UN DIBUJO QUE NO SE ENTIENDE NO SIRVE PARA AUDITAR NADA. La
        # primera versión pintaba CINCO colores y TRES de ellos eran
        # rectángulos alrededor de la misma vela: verde el extenso, naranja el
        # cuerpo y, encima, anillos magenta o azules en las velas con hecho. El
        # dueño lo miró y dijo, con razón, que no se sabía «qué es cuerpo y qué
        # es vela»: veía cuerpos en azul, mechas en naranja y cuadros verdes,
        # todo mezclado. Y eso contamina el juicio — le puso un 80-85% a una
        # medición que en parte no podía ni leer.
        #
        # 🔑 LAS TRES REGLAS DEL DIBUJO NUEVO:
        #   1. El extenso y el cuerpo se distinguen por FORMA, no por color:
        #      el extenso es un contorno fino, el cuerpo un bloque RELLENO
        #      translúcido. Dos contornos concéntricos siempre se confunden;
        #      relleno contra contorno, no.
        #   2. Los hechos NO se dibujan encima de la vela. Van fuera, arriba o
        #      abajo, como un triángulo. Un anillo alrededor de la vela compite
        #      con las dos marcas que ya hay ahí.
        #   3. La vela recuperada por rejilla no cambia de color: lleva un
        #      punto debajo. El color ya significa otra cosa.
        from PIL import ImageDraw
        base = Image.open(a.imagen).convert('RGBA')
        # dos capas: la MEDICIÓN por un lado y los HECHOS por otro, para que
        # los recortes de auditoría puedan salir sin marcas de hechos
        capa = Image.new('RGBA', base.size, (0, 0, 0, 0))
        capa_h = Image.new('RGBA', base.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        dh = ImageDraw.Draw(capa_h)
        VERDE, NARANJA = (0, 235, 120, 255), (255, 150, 0, 90)
        for v in velas:
            d.rectangle([v['x0'] - 1, v['max'], v['x1'] + 1, v['min']],
                        outline=VERDE)
            d.rectangle([v['x0'], v['cuerpo_alto'], v['x1'],
                         v['cuerpo_bajo']], fill=NARANJA)
            if v.get('rejilla'):
                cx = (v['x0'] + v['x1']) // 2
                d.ellipse([cx - 3, v['min'] + 5, cx + 3, v['min'] + 11],
                          fill=(0, 220, 220, 255))
        # 🔴 NADA DE TRIÁNGULOS. La primera versión marcaba los hechos con
        # triángulos flotando sobre y bajo la vela, y el dueño los leyó como
        # entradas y salidas de una operación — que es EXACTAMENTE lo que un
        # triángulo suelto significa en TradingView. Un símbolo no se elige por
        # lo que uno quiere que diga, sino por lo que ya dice en el sitio donde
        # se va a ver. Ahora es una BARRA vertical corta pegada a la vela, que
        # ahí no significa nada y por eso puede significar lo nuestro.
        for fam, col, arriba in (('bos', (255, 0, 255, 255), True),
                                 ('barrida', (0, 170, 255, 255), False)):
            for h in r['hechos'][fam]:
                v = velas[h['i']]
                cx = (v['x0'] + v['x1']) // 2
                y = (v['max'] - 6, v['max'] - 22) if arriba else \
                    (v['min'] + 6, v['min'] + 22)
                dh.rectangle([cx - 1, min(y), cx + 1, max(y)], fill=col)
        medido = Image.alpha_composite(base, capa)
        Image.alpha_composite(medido, capa_h).convert('RGB').save(a.dibuja)
        print('\ndibujado en', a.dibuja)
        print('   CONTORNO VERDE = la vela entera, de máximo a mínimo')
        print('   RELLENO NARANJA = su cuerpo (lo de fuera son las mechas)')
        print('   punto cian debajo = vela que recuperó la rejilla')
        print('   barrita MAGENTA arriba = BOS · AZUL abajo = barrida')

        # 🔴 Y LOS RECORTES AMPLIADOS, que es lo único con lo que se puede
        # juzgar de verdad. En la captura del dueño las velas miden 7 px: un
        # contorno de 1 px más un relleno encima, sobre 7 px de ancho, es una
        # mancha verde y naranja. Él la miró y dijo que no podía distinguir
        # cuerpo de mecha, y tenía razón — no es que estuviera mal medido, es
        # que a ese tamaño NADIE puede saberlo. Sin ampliar, "¿está bien
        # marcado?" no es una pregunta contestable.
        # ⚠️ Los recortes van SIN marcas de hechos: aquí se audita la MEDICIÓN,
        # y cualquier cosa de más vuelve a llenar de símbolos un espacio que ya
        # está apretado.
        limpia = medido
        xs0 = min(v['x0'] for v in velas)
        xs1 = max(v['x1'] for v in velas)
        # ⚠️ La escala se ELIGE, no se fija: con un ×4 fijo, una captura ancha
        #    da tiras larguísimas y estrechas que no se pueden mirar en un
        #    móvil. Se apunta a ~1300 px de ancho por recorte, que es lo que
        #    llena una pantalla sin obligar a desplazarse a lo largo.
        # ⚠️ NI el número de tiras NI la escala se fijan a ojo. Con un ×4 fijo
        #    y 3 tiras salían recortes de 768×2892 —una columna larguísima que
        #    no se puede mirar—, porque la altura de la banda de velas no tiene
        #    por qué parecerse al ancho de una tira. Se corta en tantas tiras
        #    como haga falta para que cada una sea CASI CUADRADA, y la escala
        #    se elige para llenar ~1300 px de ancho.
        ys0 = max(0, min(v['max'] for v in velas) - 30)
        ys1 = min(base.size[1], max(v['min'] for v in velas) + 30)
        alto_banda = max(1, ys1 - ys0)
        tiras = max(1, int(round((xs1 - xs0) / float(alto_banda))))
        raiz, ext = os.path.splitext(a.dibuja)
        # 🔴 Fuera los recortes de la corrida anterior. El número de tiras
        #    cambia con la imagen, así que si antes salieron 4 y ahora sale 1,
        #    los tres viejos se quedan en disco con el mismo nombre y uno acaba
        #    juzgando marcas de ayer sin enterarse.
        import glob as _glob
        for viejo in _glob.glob('%s_zoom*%s' % (raiz, ext)):
            os.remove(viejo)
        ancho = (xs1 - xs0) / float(tiras)
        esc = max(2, min(8, int(round(1300.0 / max(1.0, ancho)))))
        for k in range(tiras):
            cx0 = int(xs0 + k * ancho) - 4
            cx1 = int(xs0 + (k + 1) * ancho) + 4
            tr = limpia.crop((max(0, cx0), ys0, min(base.size[0], cx1), ys1))
            tr = tr.resize((tr.width * esc, tr.height * esc), Image.NEAREST)
            tr.convert('RGB').save('%s_zoom%d%s' % (raiz, k + 1, ext))
        print('   + %d recortes AMPLIADOS ×%d: %s_zoom1..%d%s'
              % (tiras, esc, raiz, tiras, ext))
        print('   👉 juzga con ESOS: en el grande las velas miden 7 px y no se '
              'puede ver nada.')
    if a.json:
        with open(a.json, 'w') as f:
            json.dump({'panel': p, 'escala': None if not escala else
                       {'por_px': escala['por_px'], 'base': escala['base'],
                        'apoyos': escala['apoyos'], 'total': escala['total']},
                       'velas': velas, 'hechos': r['hechos']}, f,
                      indent=1, default=float)
        print('\nguardado en', a.json)
