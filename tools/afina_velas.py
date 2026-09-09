# -*- coding: utf-8 -*-
"""Del recuadro APROXIMADO de la IA al extenso EXACTO de la vela.

    python3 tools/afina_velas.py --imagen docs/capturas_prueba/mes_5m.png \\
        --columnas 274-278,280-284,285-290 --salida out/afinado.png

🔴 NO TOCA EL ANALIZADOR. Vive en tools/, no lo importa la app.

═══ POR QUÉ EXISTE ═══
La prueba del 2026-09-04 midió que Gemini acierta la COLUMNA de cada vela al
píxel (centro a ≤1 px) pero falla el borde vertical por 3,5-8 px de mediana, y
a veces encierra la mecha superior dejando fuera el cuerpo. El dueño lo vio a
ojo antes de que se lo dijera: *"pareciera saber en dónde está la vela, lo que
pareciera no saber es de dónde a dónde se extiende"*.

🔑 **Las coordenadas VERTICALES de la IA se tiran a la basura.** De su recuadro
solo se conserva el rango de columnas. El máximo, el mínimo y el cuerpo salen
de contar píxeles dentro de esa franja, que es aritmética y no percepción.

═══ EL TRUCO QUE HACE QUE FUNCIONE CON CUALQUIER PALETA ═══
No se busca "lo oscuro" ni "lo verde": eso fue lo que hundió a `lee_grafico.py`
sobre una captura real (velas gris claro y negras, no verdes y rojas; cajas de
sesión translúcidas que forman una sola mancha con las velas que tapan).

Aquí el fondo se calcula **dentro de una ventana alrededor de la propia vela**,
eligiendo de una PALETA de los pocos fondos que tiene el gráfico (el del panel
y, si la hay, el teñido de una caja de sesión). Todo lo que se aparta del fondo
de su fila es tinta. Sirve igual con fondo blanco, negro o teal translúcido.
Ver `_fondo_por_fila` para el porqué de la paleta — sin ella, una fila con
muchas velas se inventa un fondo y borra la que estamos midiendo.

⚠️ Y sale gratis un efecto que importa: una línea horizontal (un fib, un nivel,
la rejilla) cruza la ventana ENTERA, así que en su fila el color más repetido es
el de la línea → la línea pasa a contar como fondo y desaparece sola.

⚠️ La ventana quiere ser ANCHA: ~5 veces la vela. Medido (2026-09-05) con
`banco_cadena`: a ×3 el extremo sale al 94,3% y a ×5 al 96,2%; de ahí en
adelante no mejora. Cuantas más columnas, más filas de fondo limpio entran en
la paleta.
"""
from __future__ import print_function

import argparse
import os

import numpy as np
from PIL import Image, ImageDraw

# Cuánto se tiene que apartar un píxel del fondo de su fila para contar como
# tinta. Suma de las tres diferencias RGB: 60 ≈ un gris apenas distinto.
UMBRAL_TINTA = 60
# Hueco vertical que se tolera dentro de una misma vela. Una mecha fina puede
# perder un píxel por el suavizado de la captura; con 0 se partiría en dos.
# Cuántas filas seguidas sin tinta se toleran DENTRO de una misma vela.
# 🔴 BAJADO DE 4 A 2 EL 09-sep, con el banco midiéndolo por primera vez (hasta
# que la fábrica no tuvo marcas de agua, verticales y desplazamientos, este
# parámetro daba lo mismo pusieras lo que pusieras).
# Es el mismo número tirando en dos direcciones opuestas, y el dueño describió
# las dos caras sobre su cuarta captura sin saberlo:
#   · demasiado grande → FUSIONA objetos distintos. Su vela 134: tinta en
#     316-379 y en 382-439, separadas por 3 px, y salía un recuadro 316-439
#     que «va mucho más abajo del low del wick y toma fondo blanco».
#   · demasiado pequeño → PIERDE la mecha, que llega rota. Su vela 135: tinta
#     en 342-346, 361-363, 384-388, 417-422, con huecos de 15 a 29 px; salía
#     solo el cuerpo, «la mecha superior e inferior no se marcó».
# Medido: 2 → 92,3% · 4 → 92,0% · 6 y 8 → 91,6% · 12 → 90,6%, y el BOS
# verificado del x=886 aguanta en todos. Gana el más pequeño: fusionar dos
# objetos hace más daño que perder una mecha, porque inventa una vela que no
# existe en vez de acortar una que sí.
# ⚠️ Y NO arregla el caso de la mecha rota: 29 px de hueco no se cierran con
#    ningún valor sensato. Eso es otro fallo y necesita otra cura.
HUECO = 2
# 🔴 CUERPO vs MECHA. Antes era un número fijo de píxeles (3) y ESO ESTABA MAL:
# el dueño lo cazó mirando el dibujo — *"hay algunas mechas que coloreaste como
# cuerpo"*. Un umbral fijo depende del tamaño de la captura, y en una imagen
# encogida la mecha de 2 px y el cuerpo de 4 px quedan del mismo lado.
# Ahora es RELATIVO a la propia vela: el cuerpo es su parte ANCHA. Se mide el
# ancho máximo de tinta de esa vela y se llama cuerpo a las filas que llegan a
# esta fracción de él. Una mecha es ~1 px contra un cuerpo de 5-15: no hay duda
# a ninguna resolución.
# ⚠️ Importa más que la estética: un FVG, un BOS y un order block se definen con
# CIERRES, o sea con el borde del cuerpo. Confundir mecha con cuerpo cambia el
# veredicto de "rompió" a "solo lo tocó", que es justo la distinción que el
# analizador tiene que acertar.
FRACCION_CUERPO = 0.60
# Huecos de hasta tantas filas se cierran antes de elegir el cuerpo. Ver la
# explicación larga en `afina`: por encima de 2 se vuelve a tragar la mecha.
HUECO_CUERPO = 2
# Una fila cuya tinta ocupa casi toda la ventana no es la vela: es un objeto
# ANCHO pasando por encima (la flecha de entrada, una etiqueta, un icono).
FILA_ANCHA = 0.80
# Una columna con tinta en más de esta fracción del panel no es una vela: es
# una línea vertical de interfaz (borde de caja de sesión, separador de día).
VERT_INTERFAZ = 0.60
# Qué parte del panel tiene que recorrer un tramo del mismo color para ser una
# LÍNEA y no velas. Ver `filas_de_linea`.
FRAC_LINEA = 0.35
# Cuántos píxeles seguidos del mismo color, a lo ancho, hacen una LÍNEA. La
# vela más ancha del banco mide 17 px. Ver `pixeles_de_linea`.
LARGO_LINEA = 24
# Cuántos colores distintos tiene una vela: cuerpo alcista, bajista y borde.
COLORES_VELA = 3
# Cuánto puede alejarse un píxel de un color de vela y seguir siéndolo (suma
# de las tres diferencias RGB). Holgado, para no perder la mecha de 1 px, que
# llega mezclada con el fondo.
TOL_COLOR_VELA = 150
# Cuántas veces la altura que anuncia la GUÍA puede medir la vela de verdad.
# 🔑 El recuadro del modelo se queda CORTO: en la cuarta captura del dueño su
# vela de entrada mide 243 px y la guía decía 146. Con 1,0 el bloque bueno se
# quedaba fuera igual. Medido —BOS verificado del x=886 / velas suyas bien /
# banco—:  1,0 → ✅ 2/6 91,9%   ·   1,5 → ✅ 4/6 92,0%   ·   2,0 → 🔴 4/6 92,0%
# A partir de 2 se pierde el BOS contrastado y no se gana nada. Se queda en 1,5.
TOPE_GUIA = 1.5
# Cuánto puede alejarse un píxel del color de la línea de interfaz y seguir
# contando como parte de ella. Ver el bloque "FUERA LAS LÍNEAS VERTICALES".
TOL_LINEA = 90
# Cuántos fondos distintos puede tener un gráfico: el del panel, el de una caja
# de sesión, a lo sumo el de una segunda caja. Con más, una vela densa se cuela
# en la paleta y volvemos al fallo que esto arregla.
PALETA_FONDOS = 4
# Cuántos anchos de vela a cada lado se miran para estimar el fondo LOCAL.
# Bastante estrecho a propósito: el borde de una caja de sesión tiene que
# quedar respetado con un margen de una vela. Ver `_fondo_local`.
SPAN_FONDO = 4
# Cuántas velas a cada lado entran en la ventana de la que sale la PALETA (no
# la de medir, que sigue en ×5). Ver `_paleta`.



def mascara_huecos(W, columnas):
    """Qu\u00e9 columnas de la imagen NO pueden contener una vela.

    Se construye sobre la REJILLA COMPLETA \u2014paso y fase deducidos de las
    columnas recibidas\u2014, no sobre las columnas en s\u00ed.

    \u26a0\ufe0f Hecha con las columnas recibidas mide PEOR que no hacer nada: al
    extractor le faltan velas \u2014al modelo se le escapa entre el 14 y el 27%\u2014 y
    el sitio de cada vela ausente quedar\u00eda marcado como hueco, as\u00ed que el fondo
    se muestrear\u00eda JUSTO ENCIMA DE UNA VELA."""
    hueco = np.ones(W, bool)
    if not len(columnas):
        return hueco
    cen = sorted((c[0] + c[1]) / 2.0 for c in columnas)
    ancho = int(round(np.median([c[1] - c[0] + 1 for c in columnas])))
    if len(cen) > 2:
        dif = np.diff(cen)
        paso = float(np.median(dif[dif > 0])) if (dif > 0).any() else ancho + 1
    else:
        paso = ancho + 1
    x = cen[0] - int(np.floor(cen[0] / paso)) * paso
    while x < W:
        a = int(round(x - ancho / 2.0)) - 1
        hueco[max(0, a):min(W, a + ancho + 3)] = False
        x += paso
    return hueco


def fondo_por_columna(a, y0, y1):
    """El color que MANDA en cada columna del panel, de arriba abajo.

    \U0001f511 LA OTRA MITAD DEL FONDO. `_fondo_por_fila` da el fondo a lo alto y
    mata las l\u00edneas HORIZONTALES; esto da el fondo a lo ancho y mata lo que
    var\u00eda por COLUMNAS: la caja de sesi\u00f3n, el sombreado de una killzone, una
    banda de color. Juntos son el fondo en dos dimensiones.

    \u26a0\ufe0f Y no necesita huecos entre velas, que es por lo que hubo que llegar
    aqu\u00ed: en la cuarta captura del due\u00f1o las velas miden 3 px y van cada 4,5, o
    sea que entre una y otra queda **1,5 px** \u2014 no hay fondo limpio que
    muestrear en ninguna parte. En cambio una columna de 740 filas con una vela
    de 100 px sigue teniendo 640 filas de fondo, y su color m\u00e1s repetido ES el
    fondo de esa zona, sea blanco, negro, amarillo o verde te\u00f1ido. No se
    presupone ning\u00fan color: se lee el que haya."""
    sub = a[y0:y1]
    plano = (sub[:, :, 0] * 65536 + sub[:, :, 1] * 256 + sub[:, :, 2])
    out = np.zeros((plano.shape[1], 3), int)
    for x in range(plano.shape[1]):
        val, cnt = np.unique(plano[:, x], return_counts=True)
        c = int(val[cnt.argmax()])
        out[x] = (c >> 16, (c >> 8) & 255, c & 255)
    return out


def mascara_lineas(a, y0, y1, fcol, largo=None):
    """Los píxeles del PANEL que forman una línea horizontal larga.

    \u26a0\ufe0f SE CALCULA SOBRE EL PANEL, no sobre la ventana de cada vela, y esa es
    la diferencia entre que funcione y no. La ventana mide 13-30 px de ancho:
    un tramo de línea de 24 px casi nunca cabe entera dentro, así que mirándola
    ahí el filtro no encuentra casi nada (+0,1 puntos medido). Vista sobre el
    panel, una línea de fib recorre cientos de píxeles y es inconfundible."""
    sub = a[y0:y1]
    tin = np.abs(sub - fcol[None, :, :]).sum(2) > UMBRAL_TINTA
    return pixeles_de_linea(sub, tin, largo or LARGO_LINEA)


def pixeles_de_linea(vent, tinta, largo=None):
    """Qué píxeles de tinta pertenecen a una LÍNEA HORIZONTAL larga.

    \U0001f534 TERCER INTENTO CONTRA EL MISMO AGUJERO, y lo que aprendí de los dos
    anteriores es qué NO hacer:
      · por COLOR (85,6 → 72,0%): borraba todos los píxeles de un color, y con
        ellos las mechas, que llegan mezcladas con el fondo.
      · por FILAS (85,6 → 67,3%): borraba la fila entera, y con ella la vela que
        esa fila contenía.
    Los dos quitaban DE MÁS. Aquí se quita solo lo que forma parte del objeto:
    si un fib cruza una vela, desaparece la línea y la vela se queda.

    \U0001f511 La regla es de forma pura: **un píxel de tinta que vive dentro de un
    tramo seguido de `largo` píxeles del MISMO color, a lo ancho, es una línea**.
    La vela más ancha del banco mide 17 px y las de una captura real 3 a 17; un
    fib recorre cientos. Y como solo se miran píxeles que YA son tinta, el fondo
    de la derecha del gráfico —el que hundió el intento 2— ni se considera.

    \u26a0\ufe0f El tramo se mide sobre la ventana de referencia, no sobre el panel:
    basta con que la línea la cruce entera para saber que no es una vela."""
    if not tinta.any():
        return np.zeros(tinta.shape, bool)
    n = largo or LARGO_LINEA
    if tinta.shape[1] < n:
        return np.zeros(tinta.shape, bool)
    plano = (vent[:, :, 0] * 65536 + vent[:, :, 1] * 256 + vent[:, :, 2])
    # ¿el píxel y los n-1 siguientes son del mismo color y son tinta?
    ok = tinta.copy()
    for k in range(1, n):
        ok[:, :-k] &= tinta[:, k:] & (plano[:, :-k] == plano[:, k:])
        ok[:, -k:] = False
    # marcar los n píxeles de cada tramo encontrado
    fuera = np.zeros(tinta.shape, bool)
    for k in range(n):
        fuera[:, k:] |= ok[:, :tinta.shape[1] - k]
    return fuera


def filas_de_linea(a, y0, y1, x0, x1, frac=None):
    """Qué filas del panel son una LÍNEA HORIZONTAL, no velas.

    \U0001f534 Un fib, un nivel, el borde de una caja: todos son una fila con un
    TRAMO SEGUIDO DEL MISMO COLOR de cientos de píxeles. Ninguna vela hace eso:
    la más ancha mide 17 px. Es la separación por FORMA que el filtro por color
    no supo dar — y que fracasó tres veces (ver más abajo).

    Medido en la fábrica: los racimos de fib le cuestan 2,7 puntos de máximo y
    mínimo exactos (91,9 → 89,2%).

    \u26a0\ufe0f Se mide el tramo SEGUIDO, no cuántos píxeles de ese color hay en la
    fila. Veinte velas del mismo color en una fila suman mucho y son veinte
    manchas con huecos; una línea es una sola tirada. Confundirlos borraría la
    fila donde más velas hay, que es justo la del medio del gráfico."""
    sub = a[y0:y1, x0:x1]
    W = sub.shape[1]
    if W < 20:
        return np.zeros(sub.shape[0], bool)
    minimo = int((frac or FRAC_LINEA) * W)
    plano = (sub[:, :, 0] * 65536 + sub[:, :, 1] * 256 + sub[:, :, 2])
    # tramo seguido más largo del mismo color, fila a fila
    igual = plano[:, 1:] == plano[:, :-1]
    out = np.zeros(sub.shape[0], bool)
    for y in range(sub.shape[0]):
        n = mejor = 1
        fila = igual[y]
        for v in fila:
            if v:
                n += 1
                if n > mejor:
                    mejor = n
            else:
                n = 1
        if mejor >= minimo:
            out[y] = True
    return out


def colores_de_vela(a, y0, y1, fcol, cuantos=None):
    """Los pocos colores con los que están pintadas LAS VELAS de este gráfico.

    \U0001f534 EL CUARTO AGUJERO DE FÁBRICA, y el que más clientes afecta porque el
    sitio se lo PIDE: **los dibujos del trader se contaban como tinta de vela**.
    Sus flechas de entrada y salida, sus fibs, sus cajas. Medido en la cuarta
    captura del dueño, columna x=610: lo que parecía "una mecha rota en tres
    trozos" era su flecha azul (41,98,255) en y=361-363, una marca roja
    (178,40,51) en y=391-392 y una línea gris. La vela medía 5 px.
    En la fábrica, con dibujos encima: 91,9 → 85,6% de máximos y mínimos.

    \U0001f511 LA REGLA, y no presupone ningún color: **un gráfico tiene DOS O TRES
    colores de vela** —sube, baja y el borde— y con ellos pinta cientos de
    velas. Un dibujo del trader es de otro color y aparece cuatro veces. Así que
    se cuentan los colores de toda la tinta del panel y los que mandan son las
    velas; lo demás, no. El fondo del cliente puede ser blanco, negro o amarillo
    y sus velas rosadas: aquí no se decide nada de antemano, se cuenta.

    \u26a0\ufe0f Y POR ESO SE MIRA EL PANEL ENTERO Y NO LA COLUMNA. Probado por columna
    el 09-sep y midió PEOR (80,3%): cuando el dibujo ocupa más columna que la
    vela, el color que gana la votación es el del DIBUJO y se filtra la vela.
    En el panel entero eso no puede pasar: hay cientos de velas y cuatro
    flechas."""
    sub = a[y0:y1]
    dif = np.abs(sub - fcol[None, :, :]).sum(2)
    tin = sub[dif > UMBRAL_TINTA]
    if len(tin) < 50:
        return None
    pl = tin[:, 0] * 65536 + tin[:, 1] * 256 + tin[:, 2]
    val, cnt = np.unique(pl, return_counts=True)
    orden = np.argsort(-cnt)[:(cuantos or COLORES_VELA)]
    return np.array([[int(v) >> 16, (int(v) >> 8) & 255, int(v) & 255]
                     for v in val[orden]])


def _fondo_local(a, y0, y1, cx, hueco, span):
    """EL FONDO EN DOS DIMENSIONES: por fila **y por zona de columnas**.

    \U0001f534 LA RA\u00cdZ DE LOS DOS FALLOS DE ESTOS D\u00cdAS (2026-09-09). Este archivo
    asum\u00eda **un color de fondo por FILA**, y un gr\u00e1fico real tiene VARIOS dentro
    de la misma fila:

        x=0 \u2500\u2500\u2500\u2500\u2500\u2500\u2500 x=640 \u2500\u2500\u2500\u2500\u2500\u2500\u2500 x=690 \u2500\u2500\u2500\u2500\u2500\u2500\u2500 x=1040
          fondo normal    CAJA DE KILLZONE   fondo normal

    Al elegir uno solo \u2014el que m\u00e1s se repite, el de fuera\u2014 **todo lo que hay
    dentro de la caja se aparta del fondo y cuenta como tinta**. Medido en la
    cuarta captura del due\u00f1o: la columna de la vela de su ENTRADA daba 0,67 de
    tinta, el filtro de l\u00edneas verticales la tom\u00f3 por un borde de interfaz y
    **borr\u00f3 su vela**. Cuatro velas bajistas seguidas salieron alcistas.
    La marca de agua de sesi\u00f3n es el mismo fallo por la otra puerta: dentro de
    las letras el fondo es otro, y ah\u00ed las velas DESAPARECÍAN.

    \U0001f511 C\u00f3mo se estima sin saber ning\u00fan color de antemano \u2014el fondo de un
    cliente puede ser blanco, negro o amarillo, y sus velas de cualquier
    color\u2014: **en los HUECOS entre velas**, que es donde por construcci\u00f3n no
    puede haber vela. Lo que se lea ah\u00ed ES el fondo de esa zona; si el hueco cae
    dentro de la caja de sesi\u00f3n, sale el te\u00f1ido, que es justo lo que hace falta.

    \u26a0\ufe0f Y LOCAL, que es lo que fall\u00f3 en el intento del 08-sep: aquel muestreaba
    los huecos de toda la ventana ancha (\u00b110 velas), que CRUZA el borde de la
    caja y vuelve a mezclar los dos fondos. Con \u00b1`span` p\u00edxeles alrededor de la
    vela, el borde queda respetado con un margen de una vela."""
    x0 = max(0, cx - span)
    x1 = min(a.shape[1], cx + span + 1)
    h = hueco[x0:x1]
    if h.sum() < 4:
        return None
    return np.median(a[y0:y1, x0:x1][:, h], axis=1).astype(int)


def _fondo_por_fila(vent, paleta=None, sin=None):
    """El fondo de cada fila, ELIGIENDO DE UNA PALETA en vez de fila a fila.

    🔴 EL FALLO QUE ESTO ARREGLA (2026-09-05, era el 73% de las velas mal
    medidas). Antes el fondo de una fila era, sin más, su color más repetido.
    En una fila donde las velas VECINAS ocupan más de media ventana, el color
    más repetido pasa a ser **el color de las velas** — y entonces la mecha de
    la vela que estamos midiendo, que es de ese mismo color, cuenta como fondo
    y DESAPARECE. En el perfil de tinta se veía clarísimo: seis filas de mecha,
    quince filas vacías, y el cuerpo debajo. El hueco partía la vela en dos y
    nos quedábamos con el trozo de abajo.

    🔑 La idea: un gráfico tiene MUY POCOS fondos (el del panel y, si hay caja
    de sesión, el teñido) y esos son los que salen ganadores en la inmensa
    mayoría de las filas. Las velas ganan en unas pocas. Así que primero se
    reúnen los candidatos de todas las filas, se **construye una paleta con los
    que mandan en más filas**, y luego cada fila elige de ESA paleta el que más
    píxeles tenga en ella. Una fila densa de velas ya no puede inventarse un
    fondo nuevo: tiene que escoger entre los de la casa.

    ⚠️ Si en una fila no hay NI UN píxel de la paleta (una línea de nivel que
    cruza la ventana entera), se deja su color más repetido — esa fila queda
    entera como tinta y la caza el filtro de filas anchas."""
    h, w, _ = vent.shape
    plano = (vent[:, :, 0] * 65536 + vent[:, :, 1] * 256 + vent[:, :, 2])
    crudo = np.zeros(h, dtype=np.int64)
    for y in range(h):
        fila = plano[y]
        # ⚠️ Los píxeles que forman una LÍNEA no votan al fondo de su fila: si
        #    votaran, un fib que cruza la ventana entera ganaría, y entonces el
        #    fondo de verdad pasaría a contar como tinta.
        if sin is not None and not sin[y].all():
            fila = fila[~sin[y]]
        val, cnt = np.unique(fila, return_counts=True)
        crudo[y] = val[cnt.argmax()]
    if paleta is None:
        val, cnt = np.unique(crudo, return_counts=True)
        paleta = val[np.argsort(-cnt)[:PALETA_FONDOS]]

    # ⛔ PROBADO Y DESCARTADO (2026-09-09): RECORTAR LA TINTA AJENA POR COLOR.
    # Es el intento que más cerca estuvo y el que mejor enseña por qué el banco
    # solo no basta. Idea: una vela es de un color, la letra de la marca de agua
    # es de otro; elegido ya el bloque por geometría, se recorta la tinta que no
    # se parece al color que manda dentro de la columna. MEDIDO:
    #     con marca de agua   85,8 → 92,0%   (y el cuerpo 89,8 → 92,9)
    #     sin marca de agua   96,3 → 97,1%
    # o sea que ganaba en las 1.420 velas de la fábrica, en las dos condiciones.
    # 🔴 Y AUN ASÍ SE REVIERTE, porque rompía `test_analizador2`: el BOS de la
    # vela x=886, que es el ÚNICO hecho de toda la cadena verificado contra una
    # fuente independiente —la marca que dibuja el indicador BoS/ChoCh del
    # propio dueño—. La causa, mirando los píxeles de SU captura: sus velas son
    # cuerpo GRIS (74,74,74) con borde NEGRO (0,0,0), y la mecha va del color
    # del borde. Quedarse con el color dominante borraba borde y mecha, y el
    # extenso se encogía hasta el cuerpo. Él ya lo había avisado: «aunque sea
    # hueca, las velas necesitan tener bordes».
    # Admitir DOS colores (cuerpo + borde) tampoco: el banco cayó a 86,4% y la
    # prueba del x=886 siguió fallando.
    # 🔑 LA LECCIÓN, que vale más que el arreglo: el banco dibuja las mechas con
    # UN color sólido, así que premia un filtro por color que en una captura de
    # verdad borra la mecha. Antes de reintentar esto hay que hacer que la
    # fábrica dibuje velas CON BORDE de otro color, y solo entonces medir.
    # ⛔ PROBADO Y DESCARTADO (2026-09-09), DOS intentos más, los dos sobre la
    # premisa equivocada de que el culpable era el FONDO:
    #   · paleta desde una ventana ×20 en vez de ×5 → 85,8 → 86,7% (+0,9, nada)
    #   · muestrear el fondo en los HUECOS entre columnas, que es donde no puede
    #     haber vela → 85,6%, PEOR. (Y ojo: la máscara hay que construirla sobre
    #     la rejilla COMPLETA; hecha con las columnas recibidas, el sitio de cada
    #     vela que falta se marca como hueco y se muestrea el fondo encima de una
    #     vela.)
    # Con el arreglo bueno puesto (`_recorta_tinta_ajena`), las dos variantes
    # miden PEOR que dejar el fondo como estaba: 90,9% contra 92,0%. El fondo
    # nunca fue el problema.
    # ⛔ PROBADO Y DESCARTADO (2026-09-08): sacar la paleta del PANEL ENTERO en
    # vez de la ventana ×5. La idea era buena y el diagnóstico que la motivó es
    # CIERTO: sobre la captura del dueño, en la fila y=340 de su entrada, el
    # color más repetido de la ventana era **(2,46,39), el color de sus velas**,
    # con solo 5 de 30 píxeles — ahí no domina nada y el fondo se elige por
    # ruido. Un color de vela no puede dominar una fila de mil píxeles; un fondo
    # sí. Med
    # ido: en su captura bajó las velas de altura CERO de 6 a 4… y en el
    # banco hundió todo lo demás — extremo 96,3→95,3 · FVG 84,7→78,7 · order
    # block 82,6→80,5 · estado del FVG 80,1→73,9 · manipulación 83,3→79,8.
    # Arreglaba dos velas de una captura y rompía seis puntos en 1.420. El fondo
    # de VERDAD cambia a lo largo del gráfico (cajas de sesión, bandas), así que
    # una paleta global le impone a cada zona los fondos de otra.
    # 🔴 EL PROBLEMA SIGUE ABIERTO: en la zona de su entrada, con la killzone,
    # la marca de agua "NY AM" —del mismo color que sus velas— y cuatro fibs
    # apiladas, 5 de 102 velas se miden con altura CERO. Los hechos de esa zona
    # se calculan sobre eso, y no valen.
    # ⛔ PROBADO Y DESCARTADO (2026-09-05): desempatar por VECINDARIO VERTICAL
    # —usar el fondo que manda en las 50 filas de arriba y las 50 de abajo, que
    # es sólido porque un fondo dura cientos de filas y un tramo denso de velas
    # solo decenas—. Suena mejor y mide PEOR: FVG 86,8 → 86,3%, order block
    # 81,8 → 81,4%. Se deja anotado para que nadie lo reintente creyendo que es
    # una mejora evidente.
    fondo = np.zeros((h, 3), int)
    for y in range(h):
        fila = plano[y]
        mejor, cuantos = int(crudo[y]), -1
        for c in paleta:
            n = int((fila == c).sum())
            if n > cuantos:
                mejor, cuantos = int(c), n
        if cuantos <= 0:
            mejor = int(crudo[y])
        fondo[y] = (mejor >> 16, (mejor >> 8) & 255, mejor & 255)
    return fondo


def direccion(velas):
    """Quién es alcista y quién bajista, SIN saber la paleta del tema.

    🔴 VIVE AQUÍ, no en `lee_grafico`. Estaba allí por historia, y la cadena
    nueva acababa importando al lector VIEJO —el que fallaba con capturas
    reales— solo para esto. Peor aún: `lee_grafico` arrastra **scipy**, que no
    está instalado en el VPS, así que el analizador 2.0 no arrancaba allí por
    una dependencia que no usa para nada.


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


def afina(a, x0, x1, y0, y1, margen=5, deslizar=False, guia=None,
          tope_alto=None, fcol=None, cvela=None, flin=None, mlin=None,
          dib=None):
    """Extenso real de la vela que vive entre las columnas x0..x1.

    Devuelve (alto, bajo, cuerpo_alto, cuerpo_bajo) en píxeles, o None si en esa
    franja no hay ninguna vela. `a` es la imagen como array RGB.

    🔑 `tope_alto` = altura máxima creíble para una vela DE ESTE gráfico. Se
    calcula en dos pasadas (medir todas → mediana → volver a medir las que se
    disparan) y ataca el defecto que apareció sobre la captura real del dueño:
    dos velas pegadas al borde vertical de la banda de killzone salieron de 425
    px cuando la mediana del gráfico era 70. La guía sola no bastaba, porque su
    tope es relativo a un recuadro que en esas velas venía grande."""
    H, W, _ = a.shape
    x0 = max(0, x0); x1 = min(W - 1, x1)
    ancho = x1 - x0 + 1
    vx0 = max(0, x0 - margen); vx1 = min(W, x1 + margen + 1)
    y0 = max(0, y0); y1 = min(H, y1)
    vent = a[y0:y1, vx0:vx1]
    # 🔑 EL FONDO, EN DOS DIMENSIONES. Ver `_fondo_local`.
    # ⛔ OCHO INTENTOS CONTRA LOS DIBUJOS DEL TRADER, LOS OCHO REVERTIDOS. El
    #    valor de este bloque no es el código —no hay— sino el DIAGNÓSTICO, que
    #    sí está medido y le ahorra el camino a quien lo retome:
    #
    # 🔴 EL DAÑO NO ESTÁ DONDE ESTÁ EL DIBUJO. Comparando la misma lámina con y
    #    sin flechas y mirando solo las velas que cambian, **cuatro de cada
    #    cinco víctimas son velas que la flecha NI SIQUIERA TOCA**:
    #        lám 3 vela 22 · verdad 301-343 · con flechas 301-329 · no la toca
    #        lám 3 vela 23 · verdad 292-345 · con flechas 292-319 · no la toca
    #        lám 6 vela 59 · verdad 255-305 · con flechas 255-301 · no la toca
    #    El dibujo entra en la VENTANA DE REFERENCIA de las velas vecinas y les
    #    envenena el cálculo del fondo. Por eso quitarlo de la tinta nunca sirvió
    #    de nada: el mal estaba hecho un paso antes.
    #
    # ⚠️ Y aun así, sacar sus píxeles del cálculo del fondo TAMBIÉN mide peor
    #    (89,8 → 88,8%), incluso con el modelo señalando dónde está el dibujo y
    #    filtrando por color de vela dentro del recuadro. O sea que quitar
    #    información del fondo cuesta más de lo que ahorra.
    #
    # 🔑 LO QUE QUEDA POR PROBAR, y en este orden: NO quitar, sino SUSTITUIR —
    #    rellenar los píxeles del dibujo con el fondo de sus vecinos (una
    #    interpolación simple) en vez de excluirlos del recuento. Así la ventana
    #    conserva su tamaño y su estadística, que es lo que parece estar
    #    costando caro.
    dv = None
    tapado = None
    fondo = _fondo_por_fila(vent)
    dif = np.abs(vent - fondo[:, None, :]).sum(2)
    tinta = dif > UMBRAL_TINTA
    # 🔑 LA SEGUNDA DIMENSIÓN DEL FONDO. Un píxel solo es tinta si se aparta de
    #    su fila **Y** del color que manda en su propia COLUMNA. Sin esto, una
    #    caja de sesión translúcida convierte todas sus columnas en tinta de
    #    arriba abajo, el filtro de verticales las toma por líneas de interfaz
    #    y BORRA las velas que hay dentro. Ver `fondo_por_columna`.
    if fcol is not None:
        tinta &= np.abs(vent - fcol[vx0:vx1][None, :, :]).sum(2) > UMBRAL_TINTA
    # ⛔ AQUÍ IBA EL FILTRO DE LÍNEAS HORIZONTALES POR FORMA, Y SE REVIRTIÓ:
    #    85,6 → 67,3%. La idea sigue siendo buena —un fib es un tramo seguido de
    #    cientos de píxeles y ninguna vela pasa de 17— pero la REGLA estaba mal
    #    escrita: marcaba como línea cualquier fila con un tramo largo del mismo
    #    color, y **a la derecha del gráfico, donde no hay velas, el fondo ES un
    #    tramo larguísimo**. Se marcaba casi todas las filas y se borraban con
    #    ellas las velas que contenían.
    #    🔑 Para reintentarlo hay que exigir dos cosas más: que el tramo sea de
    #    un color que NO sea el fondo de esa zona, y medirlo solo DENTRO del
    #    área que ocupan las velas, no del panel entero.
    #    → Hecho en `pixeles_de_linea`, que además quita SOLO los píxeles del
    #      tramo y no la fila entera.
    # ⛔ CUATRO INTENTOS CONTRA EL AGUJERO DE LOS DIBUJOS DEL TRADER, LOS CUATRO
    #    SIN MOVER EL NÚMERO (09-sep). Queda escrito con sus medidas porque el
    #    valor está en no repetirlos:
    #      1. filtrar la tinta por COLOR de vela ............ 85,6 → 72,0%
    #      2. borrar las FILAS que son una línea ............ 85,6 → 67,3%
    #      3. borrar los PÍXELES de la línea, en la ventana . 85,6 → 85,7%
    #      4. borrar los PÍXELES de la línea, en el PANEL ... 85,6 → 85,7%
    #      5. que esos píxeles no voten al FONDO de su fila . 85,6 → 85,6%
    #    Los dos primeros quitaban de más y se llevaban las velas por delante.
    #    Los tres últimos quitan lo correcto y **no cambia nada**, y eso es el
    #    dato importante: significa que los 2,7 puntos que cuestan los fibs NO
    #    salen de que sus píxeles se cuenten como vela.
    # 🔴 CONCLUSIÓN HONESTA: no sé de dónde sale ese daño. Antes de escribir un
    #    sexto intento hay que MEDIR el mecanismo — comparar vela a vela con y
    #    sin fibs en la misma lámina y mirar las que cambian— en vez de seguir
    #    proponiendo curas para una enfermedad que no está diagnosticada.
    #    `mascara_lineas` y `pixeles_de_linea` se conservan sin usar: funcionan,
    #    y servirán cuando se sepa dónde aplicarlas.
    # ⛔ AQUÍ IBA EL FILTRO POR COLOR DE VELA, Y SE REVIRTIÓ: 85,6 → 72,0%.
    #    Es la TERCERA vez que un filtro por color fracasa del mismo modo, así
    #    que la lección ya no es una sospecha: **filtrar la tinta por color mata
    #    las mechas**. Una mecha es de 1 px, llega mezclada con el fondo, y
    #    ningún umbral la separa de un dibujo sin llevársela por delante. El
    #    cuerpo sobrevive (la dirección subió 93,9 → 94,6) y el extenso se
    #    hunde: exactamente el perfil de "se pierden las mechas".
    #    Los tres intentos, para no repetirlos:
    #      · color dominante de la COLUMNA (09-sep)        → 80,3%
    #      · dos colores, cuerpo + borde (09-sep)          → 86,4%
    #      · los colores de vela del PANEL entero (09-sep) → 72,0%
    #    `colores_de_vela` se conserva porque el diagnóstico que la motivó es
    #    correcto y puede servir para OTRA cosa —decidir si un objeto es un
    #    dibujo, en vez de filtrar píxel a píxel—, pero no se usa para medir.

    # 🔴 FUERA LAS LÍNEAS VERTICALES. El fondo por fila mata las horizontales
    # solo (cruzan la ventana entera), pero el BORDE de una caja de sesión es
    # vertical: recorre el gráfico de arriba abajo y, metido en la franja de una
    # vela, la convierte en un recuadro de 300 px. Una vela nunca es alta y
    # estrecha a la vez en más del 60% del panel; una línea de interfaz, sí.
    alto_vent = tinta.shape[0]
    vertical = tinta.sum(0) > VERT_INTERFAZ * alto_vent
    # 🔴 NO SE BORRA LA COLUMNA: SE RESTA LA LÍNEA (2026-09-09).
    # Borrarla entera fue el fallo, y es de los que no dan ningún error. En la
    # cuarta captura del dueño el borde de la caja de killzone de NY AM cae
    # JUSTO en la columna de la vela de su entrada: el filtro veía 0,69 de
    # tinta, decía "esto es una línea de interfaz" y **borraba la vela con
    # ella**. Cuatro velas bajistas seguidas salieron como alcistas y el
    # analizador escribió, muy convencido, una película que no ocurrió.
    #
    # 🔑 Una línea de interfaz es de UN color, constante de arriba abajo. La
    # vela que comparte esa columna es de otro. Así que en las columnas
    # marcadas se quita SOLO la tinta del color de la línea y se conserva el
    # resto — que es la vela.
    #
    # 🔴 PERO OJO: ESTO NO ARREGLA EL CASO DE SU CAPTURA, Y LA RAZÓN IMPORTA.
    # Midiendo la columna x=651, donde el filtro veía 0,67 de tinta: solo hay
    # **109 píxeles negros**, en tramos de ~100 px. O sea que **NO HAY NINGUNA
    # LÍNEA VERTICAL AHÍ**. Lo que llena esa columna de "tinta" es la CAJA
    # VERDE TRANSLÚCIDA de la killzone: dentro de ella todos los píxeles se
    # apartan del fondo estimado —que se calcula mezclando lo de dentro con lo
    # de fuera de la caja— y la columna entera se declara tinta.
    #
    # 🔑 Y AHÍ ESTÁ LA RAÍZ COMÚN DE TODO LO DE ESTOS DOS DÍAS: este archivo
    # asume **un color de fondo por FILA**. Un gráfico real tiene VARIOS fondos
    # dentro de la misma fila — la marca de agua de la sesión y la caja de
    # killzone son dos. La marca de agua hacía desaparecer velas; la caja las
    # hace pasar por líneas de interfaz y las borra. Son el mismo fallo por dos
    # puertas, y ningún ajuste de umbral lo arregla: hace falta estimar el fondo
    # en DOS dimensiones, por fila **y por tramo de columnas**.
    #
    # ⚠️ Y no vale usar el color de la VELA para decidir (probado ese mismo día,
    #    ver `_recorta_tinta_ajena` más abajo): la vela tiene dos colores,
    #    cuerpo y borde, y la mecha va del color del borde. El color de la
    #    LÍNEA en cambio es uno solo y se mide sin ambigüedad, porque es lo que
    #    domina en una columna que va de un extremo al otro del panel.
    for c in np.nonzero(vertical)[0]:
        col = vent[:, c][tinta[:, c]]
        if not len(col):
            continue
        pl = col[:, 0] * 65536 + col[:, 1] * 256 + col[:, 2]
        val, cnt = np.unique(pl, return_counts=True)
        v = int(val[cnt.argmax()])
        linea = np.array([v >> 16, (v >> 8) & 255, v & 255])
        es_linea = np.abs(vent[:, c] - linea).sum(1) <= TOL_LINEA
        # Si al quitar la línea no queda casi nada, esa columna ERA solo línea.
        tinta[es_linea, c] = False

    # ⛔ ENCUADRAR DESLIZANDO LA FRANJA: PROBADO Y DESCARTADO (2026-09-04).
    # La idea era corregir el ~1 px de error del centro moviendo la franja ±3
    # columnas y quedándose con la posición de más tinta. Empeoró: en esta
    # captura las velas miden 5 px y van separadas 5,5, así que "más tinta"
    # premia a la VECINA cuando es más alta, y el recuadro salta de vela. Se
    # deja apagado — el centro que da la IA ya es mejor criterio que este.
    # Con velas anchas (captura de 1920 px) el problema no existe y no hace
    # falta ningún ajuste.
    if deslizar:
        mejor, mejor_x = -1, x0
        for dx in range(-3, 4):
            p = x0 + dx - vx0
            if p < 0 or p + ancho > tinta.shape[1]:
                continue
            n = int(tinta[:, p:p + ancho].sum())
            if n > mejor:
                mejor, mejor_x = n, x0 + dx
        x0, x1 = mejor_x, mejor_x + ancho - 1

    # 🔴 FUERA LOS OBJETOS ANCHOS. La flecha roja de entrada del trade se comía
    # la vela sobre la que estaba posada (lo cazó el dueño en el dibujo). Una
    # flecha, una etiqueta o un icono son MÁS ANCHOS que la vela: su tinta cruza
    # la ventana entera. La vela nunca lo hace, porque la ventana se eligió
    # justamente tres veces más ancha que ella.
    #
    # 🔴 PERO LO QUE MANDA ES QUE LA TINTA SEA SEGUIDA, NO CUÁNTA HAY. Contando
    # píxeles sueltos, en la zona densa de un gráfico —velas pegadas a 7,5 px—
    # una fila cualquiera cruza cuatro o cinco velas y también pasa del 80%. El
    # filtro borraba entonces LAS VELAS DE VERDAD, y en esa columna solo
    # sobrevivía el texto de la barra de herramientas: sobre la captura del
    # dueño salieron **cinco velas medidas en el menú** (y≈101-133) con la guía
    # apuntando correctamente al gráfico, y 33 de 105 con el cuerpo tragándose
    # las mechas. Una flecha es una mancha CONTINUA; cinco velas seguidas son
    # cinco manchas con hueco entre medias. Por eso se mide el tramo seguido más
    # largo de la fila y no su total.
    ancho_vent = tinta.shape[1]
    limite = FILA_ANCHA * ancho_vent
    for y in np.nonzero(tinta.sum(1) > limite)[0]:
        fila = tinta[y]
        mejor = actual = 0
        for v in fila:
            actual = actual + 1 if v else 0
            if actual > mejor:
                mejor = actual
        if mejor > limite:
            # 🔴 SE QUITA LA LÍNEA, NO LA FILA (2026-09-10). Borrar la fila
            #    entera borra también **el píxel de la vela que esa fila
            #    contiene**, y si la línea viene con antialias son 2-3 filas
            #    seguidas: la vela se PARTE EN DOS y la medición se queda con un
            #    trozo. Diagnosticado comparando la misma lámina con y sin fibs
            #    y mirando solo las velas que cambian:
            #        vela 47 · verdad 488-550 · con fibs 488-526  (−24 px)
            #        vela 48 · verdad 524-574 · con fibs 542-574  (+18 px)
            #    No se alargan: se acortan. Es un corte, no una invasión.
            #    Es el mismo error que tenía el filtro de líneas VERTICALES y se
            #    cura igual: fuera los píxeles del objeto, no los de la fila.
            if mlin is not None:
                tinta[y] &= ~mlin[y, vx0:vx1]
            else:
                tinta[y, :] = False

    # 🔴 LOS DIBUJOS DEL TRADER NO SON VELA — PERO TAMPOCO SON "NADA".
    #    Quitar sus píxeles a secas deja un AGUJERO en la vela que tapan, y
    #    entonces la vela se parte igual: cambias un error por otro. Lo correcto
    #    es tratarlos como DESCONOCIDO — no cuentan como tinta, pero un hueco
    #    cubierto por un dibujo no rompe la continuidad de la vela.
    #    Es la pieza que les faltaba a los cinco intentos anteriores, que
    #    borraban (por color, por fila o por objeto) sin reponer la continuidad.
    # ⛔ SEXTO Y ÚLTIMO INTENTO POR PÍXELES, TAMBIÉN REVERTIDO: 85,6 → 68,1%.
    #    Era el mejor razonado de los seis —quitar el OBJETO entero (que es lo
    #    que fallaba en los cinco anteriores) y además tratar sus píxeles como
    #    DESCONOCIDO en vez de "no es vela", para que el agujero que deja no
    #    parta la vela que tapa—. Y aun así se hundió, por una razón que cierra
    #    el asunto:
    #
    # 🔴 UNA FLECHA Y UNA VELA SON EL MISMO OBJETO. En el banco una vela mide
    #    13×30 px; una flecha de trader, 12×25. Mismo tamaño, misma proporción,
    #    misma compacidad, color vivo las dos. La máscara tapaba las velas.
    #    `flechas.py` ya lo decía de los iconos de la plataforma; resulta que
    #    vale también para las velas.
    #
    # 🔑 CONCLUSIÓN DE LOS SEIS INTENTOS: separar los dibujos del trader de las
    #    velas **no se puede hacer solo con píxeles**. No es cuestión de dar con
    #    el umbral: no existe la propiedad geométrica que los distinga. Y esa es
    #    exactamente la clase de pregunta —"¿qué ES esto?"— que en este proyecto
    #    resuelve el MODELO, cinco veces ya. El camino es preguntarle dónde
    #    dibujó el trader, y que los píxeles afinen el recorte; no al revés.

    # solo las columnas de la vela, no las de la ventana de referencia
    prop = tinta[:, x0 - vx0:x1 - vx0 + 1]
    filas = np.nonzero(prop.any(1))[0]
    if len(filas) == 0:
        return None
    grupos = []
    g = [filas[0]]
    for v in filas[1:]:
        # el hueco se cierra si es pequeño, O si lo que hay en medio está
        # TAPADO por un dibujo del trader (ver arriba)
        if v - g[-1] <= HUECO or (tapado is not None
                                  and tapado[g[-1] + 1:v].all()):
            g.append(v)
        else:
            grupos.append(g); g = [v]
    grupos.append(g)
    # 🔑 CUÁL DE LOS BLOQUES ES LA VELA. Antes se cogía el más largo y por eso
    # salía un recuadro de 120 px EN EL VACÍO, donde no hay ninguna vela: se
    # había enganchado al borde vertical entre dos cajas de sesión.
    # Ahora manda la GUÍA: el recuadro de la IA falla el borde por 3,5-8 px,
    # pero acierta de sobra para decir "la vela está por AQUÍ". Se usa como
    # pista, nunca como medida — se elige el bloque que más se solapa con ella
    # y sus números se descartan igual. Sin guía se vuelve al bloque más largo.
    if guia:
        ga, gb = guia[0] - y0, guia[1] - y0
        # ⚠️ La guía acota el TAMAÑO, no solo la posición. Un bloque tres veces
        # más alto que la vela que anunció el modelo no es esa vela: es el
        # borde de una caja de sesión recorriendo el panel. Sin este límite el
        # borde ganaba la votación cuando la guía venía con error grande.
        techo = 3 * (gb - ga) + 30
        if tope_alto:
            # 🔴 EL TOPE GLOBAL NUNCA POR DEBAJO DE LO QUE DICE LA GUÍA
            #    (2026-09-09). El tope existe para que una vela no se enganche
            #    al borde de una caja de sesión y salga de 400 px. Pero se
            #    aplicaba a ciegas, y en un gráfico con velas de desplazamiento
            #    acababa **descartando la vela que el propio modelo acababa de
            #    anunciar**: en la cuarta captura del dueño el tope valía 114 px
            #    (3 × la mediana de 38) y la guía de su vela de entrada decía
            #    417-563, o sea 146 px. El bloque bueno quedaba fuera de la
            #    votación, solo sobrevivían fragmentos del texto de la etiqueta
            #    "NYAM.H", y ganaba uno a 180 px de distancia.
            #    La mediana de un gráfico NO acota lo que mide un desplazamiento;
            #    la guía sí, porque es de esa vela. Se respeta la mayor de las
            #    dos, con margen.
            techo = min(techo, max(tope_alto, TOPE_GUIA * (gb - ga) + 30))
        cand = [b for b in grupos if b[-1] - b[0] <= techo] or grupos

        def solape(b):
            return max(0, min(b[-1], gb) - max(b[0], ga))

        # 🔴 SI NINGÚN BLOQUE TOCA LA GUÍA, GANA EL MÁS CERCANO — NO EL MÁS
        # LARGO. Cazado sobre la captura del dueño: cinco velas salieron
        # medidas EN LA BARRA DE HERRAMIENTAS (y≈101-133) con su guía
        # apuntando correctamente al gráfico (y≈250-295). En esa columna la
        # tinta de la vela se había perdido, no quedaba ningún bloque que
        # solapara, y el desempate por longitud premiaba al texto del menú
        # —que es largo— por encima de cualquier cosa cercana. El error de la
        # guía es de 3-8 px y en el peor caso 40: un bloque a 150 px no es esa
        # vela, mida lo que mida.
        def cerca(b):
            return -abs((b[0] + b[-1]) / 2.0 - (ga + gb) / 2.0)

        g = max(cand, key=lambda b: (solape(b), cerca(b), len(b)))
    else:
        cand = grupos
        if tope_alto:
            cand = [b for b in grupos if b[-1] - b[0] <= tope_alto] or grupos
        g = max(cand, key=len)
    alto, bajo = g[0], g[-1]

    # 🔑 CUERPO = las filas que tienen tinta en LOS DOS COSTADOS de la vela.
    # La mecha solo pinta la columna del centro; el cuerpo llega a los bordes,
    # esté relleno o sea un rectángulo hueco. Y sobrevive a que una línea de
    # nivel borre la fila del borde superior, que era lo que en una vela hueca
    # se llevaba por delante el cuerpo ENTERO (el 20% de los fallos).
    n = prop.shape[1]
    borde = max(1, int(round(0.30 * n)))
    izq = prop[alto:bajo + 1, :borde].any(1)
    der = prop[alto:bajo + 1, -borde:].any(1)
    # ⛔ SE PROBÓ MEDIR LA EXTENSIÓN DE LA TINTA (de dónde a dónde llega la
    # fila) EN VEZ DE CONTARLA, y se descartó por decisión del dueño. La idea
    # era que "el cuerpo es siempre un rectángulo, tenga relleno o no", así que
    # bastaría con ver si la fila llega de un borde al otro. Es cierto, pero él
    # señaló el riesgo: **una caja de FVG dibujada, una zona de sesión o un
    # recuadro de indicador también son rectángulos**, y con esa regla podrían
    # colarse como cuerpo.
    #
    # Y NO COMPENSA EL RIESGO: medido con las columnas ya encajadas en la
    # rejilla, extensión da 97,8% de cuerpo exacto en el banco y cuenta 97,6% —
    # y sobre la captura del dueño las dos dan exactamente lo mismo (12 velas
    # de 102 con el cuerpo tragándose la mecha). Dos décimas no pagan una
    # familia de falsos positivos nueva.
    #
    # ⚠️ Lo que de verdad arregló su captura NO fue esta regla: fue encajar las
    # columnas en la rejilla real (`analizador2.encaja_en_rejilla`), que
    # venían desplazadas media vela. Queda anotado porque yo mismo me confundí
    # aquí: llegué a escribir que sus velas eran huecas —no lo son, son macizas
    # con borde negro— porque muestreé una fila y vi «borde, fondo, borde», que
    # era mi columna cayendo ENTRE DOS VELAS. Aviso general: cuando una lectura
    # de píxeles diga algo raro del gráfico, sospechar primero del encuadre.
    anchos = prop[alto:bajo + 1].sum(1)

    # 🔴 LOS DOS COSTADOS NO BASTAN, Y SE VIO SOBRE LA CAPTURA REAL. Si la
    # columna es más ancha que la vela y la vela queda descentrada dentro, uno
    # de los costados cae en el FONDO y la fila no cuenta — aunque sea cuerpo
    # macizo. Medido en una vela del dueño (perfil de anchos por fila):
    #     anchos  114416661444444444444444
    #     cuerpo  .....###................
    # el cuerpo es la tira larga de 4, y se quedó con los tres 6.
    #
    # 🔑 Por eso ahora vale CUALQUIERA de las dos señales:
    #   · tinta en los dos costados  → sirve para la vela HUECA, cuyos lados
    #     son dos rayas de 1 px y no se distinguen de una mecha por ancho;
    #   · fila ANCHA respecto a la más ancha de esta vela → sirve para la vela
    #     maciza más estrecha que su columna, donde los costados fallan.
    # Ninguna de las dos sola cubre los dos casos, y una mecha falla las dos.
    # 🔴 EL SUELO ERA 2 Y ESO SE COMÍA LAS MECHAS. Con velas HUECAS —el tema
    # claro de TradingView, el del dueño— el cuerpo solo pinta sus dos bordes,
    # así que su ancho de tinta es 2, igual que el de una mecha gruesa. Y con
    # un máximo de 4, `round(0.60*4)` da 2: el umbral caía al suelo y CUALQUIER
    # fila de 2 píxeles pasaba por cuerpo. Sobre la captura del dueño eso
    # dejaba 31 velas de 105 con el cuerpo tragándose las mechas enteras.
    # El suelo sube a 3 para que esta rama nunca pueda dispararse con una
    # mecha; la vela hueca la cubre la OTRA rama, la de los dos costados, que
    # es justo el caso para el que se puso.
    umbral = max(3, int(round(FRACCION_CUERPO * int(anchos.max() or 0))))
    cu = np.nonzero((izq & der) | (anchos >= umbral))[0]

    # 🔴 EL CUERPO ES EL TRAMO SEGUIDO MÁS LARGO, PERO CERRANDO HUECOS
    # PEQUEÑOS. Las dos reglas ingenuas fallan por lados opuestos, y las dos se
    # midieron en el banco (24 láminas, cuerpo exacto):
    #   · `cu[0]..cu[-1]` (de la primera válida a la última) aguanta un agujero
    #     DENTRO del cuerpo —una fila que se pierde por una línea encima— pero
    #     se traga lo que haya fuera: en una vela real del dueño, tres filas de
    #     mecha entre dos filas anchas entraron enteras al cuerpo. 95,7%.
    #   · el tramo seguido más largo, a secas, no se traga la mecha pero se
    #     PARTE en cuanto hay un agujero interior. **76,0%** — 20 puntos.
    # Se queda con lo bueno de las dos: se cierran los huecos de hasta
    # HUECO_CUERPO filas y después se toma el tramo más largo. El hueco de la
    # mecha de aquella vela era de tres filas, así que el tope va por debajo.
    if len(cu):
        cerrado = [cu[0]]
        for v in cu[1:]:
            if v - cerrado[-1] <= HUECO_CUERPO + 1:
                cerrado.extend(range(cerrado[-1] + 1, v + 1))
            else:
                cerrado.append(v)
        mejor, actual = [cerrado[0]], [cerrado[0]]
        for v in cerrado[1:]:
            if v == actual[-1] + 1:
                actual.append(v)
            else:
                actual = [v]
            if len(actual) > len(mejor):
                mejor = actual
        ct, cb = alto + mejor[0], alto + mejor[-1]
    else:                      # vela sin cuerpo visible (doji de 1 px)
        ct, cb = alto, bajo
    return (y0 + alto, y0 + bajo, y0 + ct, y0 + cb, x0, x1)


def dibuja(ruta, columnas, salida, banda=None, margen=5, deslizar=False):
    """`columnas` = [(x0,x1)] o [(x0,x1,gy0,gy1)] si se tiene la guía de la IA."""
    """Pinta el recuadro AJUSTADO de cada vela y devuelve las medidas."""
    im = Image.open(ruta).convert('RGB')
    a = np.asarray(im).astype(int)
    H, W, _ = a.shape
    y0, y1 = banda if banda else (0, H)
    d = ImageDraw.Draw(im)
    out = []
    for c in columnas:
        x0, x1 = c[0], c[1]
        guia = (c[2], c[3]) if len(c) == 4 else None
        r = afina(a, x0, x1, y0, y1, margen, deslizar, guia)
        if r is None:
            out.append(None)
            continue
        alto, bajo, ct, cb, sx0, sx1 = r
        # verde = extenso completo (mecha a mecha); naranja = solo el cuerpo
        d.rectangle([sx0 - 1, alto, sx1 + 1, bajo], outline=(0, 230, 80))
        d.rectangle([sx0 - 1, ct, sx1 + 1, cb], outline=(255, 150, 0))
        out.append((alto, bajo, ct, cb))
    im.save(salida)
    return out


def _columnas(txt):
    """'274-278' o '274-278:417-489' (con la guía vertical de la IA)."""
    out = []
    for p in txt.split(','):
        xs, _, ys = p.strip().partition(':')
        a, _, b = xs.partition('-')
        if ys:
            c, _, d = ys.partition('-')
            out.append((int(a), int(b), int(c), int(d)))
        else:
            out.append((int(a), int(b)))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--imagen', required=True)
    ap.add_argument('--columnas', required=True,
                    help='rangos x de las velas: 274-278,280-284,...')
    ap.add_argument('--banda', help='y0-y1 del área del gráfico (opcional)')
    ap.add_argument('--salida', required=True)
    a = ap.parse_args()
    banda = None
    if a.banda:
        p, _, q = a.banda.partition('-')
        banda = (int(p), int(q))
    if not os.path.isdir(os.path.dirname(a.salida) or '.'):
        os.makedirs(os.path.dirname(a.salida))
    med = dibuja(a.imagen, _columnas(a.columnas), a.salida, banda)
    print(' x0-x1    máx  mín | cuerpo    | mecha sup  mecha inf')
    for c, m in zip(_columnas(a.columnas), med):
        x0, x1 = c[0], c[1]
        if m is None:
            print(' %3d-%3d  sin vela' % (x0, x1)); continue
        alto, bajo, ct, cb = m
        print(' %3d-%3d  %4d %4d | %4d-%4d | %6d px %8d px'
              % (x0, x1, alto, bajo, ct, cb, ct - alto, bajo - cb))
    print('\ndibujado en', a.salida)
    print('verde = vela completa (mecha a mecha) · naranja = solo el cuerpo')
