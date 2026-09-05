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
HUECO = 4
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
# Una fila cuya tinta ocupa casi toda la ventana no es la vela: es un objeto
# ANCHO pasando por encima (la flecha de entrada, una etiqueta, un icono).
FILA_ANCHA = 0.80
# Una columna con tinta en más de esta fracción del panel no es una vela: es
# una línea vertical de interfaz (borde de caja de sesión, separador de día).
VERT_INTERFAZ = 0.60
# Cuántos fondos distintos puede tener un gráfico: el del panel, el de una caja
# de sesión, a lo sumo el de una segunda caja. Con más, una vela densa se cuela
# en la paleta y volvemos al fallo que esto arregla.
PALETA_FONDOS = 4


def _fondo_por_fila(vent):
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
        val, cnt = np.unique(plano[y], return_counts=True)
        crudo[y] = val[cnt.argmax()]
    val, cnt = np.unique(crudo, return_counts=True)
    paleta = val[np.argsort(-cnt)[:PALETA_FONDOS]]

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


def afina(a, x0, x1, y0, y1, margen=5, deslizar=False, guia=None,
          tope_alto=None):
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
    fondo = _fondo_por_fila(vent)
    dif = np.abs(vent - fondo[:, None, :]).sum(2)
    tinta = dif > UMBRAL_TINTA

    # 🔴 FUERA LAS LÍNEAS VERTICALES. El fondo por fila mata las horizontales
    # solo (cruzan la ventana entera), pero el BORDE de una caja de sesión es
    # vertical: recorre el gráfico de arriba abajo y, metido en la franja de una
    # vela, la convierte en un recuadro de 300 px. Una vela nunca es alta y
    # estrecha a la vez en más del 60% del panel; una línea de interfaz, sí.
    alto_vent = tinta.shape[0]
    vertical = tinta.sum(0) > VERT_INTERFAZ * alto_vent
    tinta[:, vertical] = False

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
    ancho_vent = tinta.shape[1]
    tinta[tinta.sum(1) > FILA_ANCHA * ancho_vent, :] = False

    # solo las columnas de la vela, no las de la ventana de referencia
    prop = tinta[:, x0 - vx0:x1 - vx0 + 1]
    filas = np.nonzero(prop.any(1))[0]
    if len(filas) == 0:
        return None
    grupos = []
    g = [filas[0]]
    for v in filas[1:]:
        if v - g[-1] <= HUECO:
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
            techo = min(techo, tope_alto)
        cand = [b for b in grupos if b[-1] - b[0] <= techo] or grupos

        def solape(b):
            return max(0, min(b[-1], gb) - max(b[0], ga))
        g = max(cand, key=lambda b: (solape(b), len(b)))
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
    cu = np.nonzero(izq & der)[0]
    if len(cu) == 0:
        # respaldo: la parte ancha (velas de 1-2 px de ancho, o costados rotos)
        anchos = prop[alto:bajo + 1].sum(1)
        minimo = max(2, int(round(FRACCION_CUERPO * int(anchos.max()))))
        cu = np.nonzero(anchos >= minimo)[0]
    if len(cu):
        ct, cb = alto + cu[0], alto + cu[-1]
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
