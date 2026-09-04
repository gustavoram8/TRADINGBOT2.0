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

Aquí el fondo se calcula **fila por fila, dentro de una ventana estrecha
alrededor de la propia vela**: el color más repetido de esa ventana ES el fondo,
sea blanco, negro, o el teal translúcido de una caja de sesión. Todo lo que se
aparta de él es tinta.

⚠️ Y sale gratis un efecto que importa: una línea horizontal (un fib, un nivel,
la rejilla) cruza la ventana ENTERA, así que en su fila el color más repetido es
el de la línea → la línea pasa a contar como fondo y desaparece sola. La vela,
que ocupa 5 de 15 columnas, nunca puede ser el color más repetido.

⚠️ La ventana tiene que ser ANCHA respecto de la vela (por defecto ±5 px sobre
un cuerpo de ~5) pero no tanto como para tragarse dos velas vecinas enteras: si
la vela pasa de la mitad de la ventana, ella misma se convierte en "el fondo" y
el resultado sale vacío.
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
# Filas con al menos esta tinta a lo ancho de la vela = CUERPO; menos = mecha.
ANCHO_CUERPO = 3
# Una columna con tinta en más de esta fracción del panel no es una vela: es
# una línea vertical de interfaz (borde de caja de sesión, separador de día).
VERT_INTERFAZ = 0.60


def _fondo_por_fila(vent):
    """El color más repetido de cada fila de la ventana."""
    h, w, _ = vent.shape
    plano = (vent[:, :, 0] * 65536 + vent[:, :, 1] * 256 + vent[:, :, 2])
    fondo = np.zeros((h, 3), int)
    for y in range(h):
        val, cnt = np.unique(plano[y], return_counts=True)
        c = int(val[cnt.argmax()])
        fondo[y] = (c >> 16, (c >> 8) & 255, c & 255)
    return fondo


def afina(a, x0, x1, y0, y1, margen=5, deslizar=False):
    """Extenso real de la vela que vive entre las columnas x0..x1.

    Devuelve (alto, bajo, cuerpo_alto, cuerpo_bajo) en píxeles, o None si en esa
    franja no hay ninguna vela. `a` es la imagen como array RGB."""
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

    # solo las columnas de la vela, no las de la ventana de referencia
    prop = tinta[:, x0 - vx0:x1 - vx0 + 1]
    filas = np.nonzero(prop.any(1))[0]
    if len(filas) == 0:
        return None
    # 🔑 el bloque contiguo MÁS LARGO: si un texto o una flecha rozan la
    #    columna, quedan como un bloque suelto y pierden contra la vela.
    grupos = []
    g = [filas[0]]
    for v in filas[1:]:
        if v - g[-1] <= HUECO:
            g.append(v)
        else:
            grupos.append(g); g = [v]
    grupos.append(g)
    g = max(grupos, key=len)
    alto, bajo = g[0], g[-1]
    anchos = prop[alto:bajo + 1].sum(1)
    cu = np.nonzero(anchos >= ANCHO_CUERPO)[0]
    if len(cu):
        ct, cb = alto + cu[0], alto + cu[-1]
    else:                      # vela sin cuerpo visible (doji de 1 px)
        ct, cb = alto, bajo
    return (y0 + alto, y0 + bajo, y0 + ct, y0 + cb, x0, x1)


def dibuja(ruta, columnas, salida, banda=None, margen=5, deslizar=False):
    """Pinta el recuadro AJUSTADO de cada vela y devuelve las medidas."""
    im = Image.open(ruta).convert('RGB')
    a = np.asarray(im).astype(int)
    H, W, _ = a.shape
    y0, y1 = banda if banda else (0, H)
    d = ImageDraw.Draw(im)
    out = []
    for x0, x1 in columnas:
        r = afina(a, x0, x1, y0, y1, margen, deslizar)
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
    out = []
    for p in txt.split(','):
        a, _, b = p.strip().partition('-')
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
    for (x0, x1), m in zip(_columnas(a.columnas), med):
        if m is None:
            print(' %3d-%3d  sin vela' % (x0, x1)); continue
        alto, bajo, ct, cb = m
        print(' %3d-%3d  %4d %4d | %4d-%4d | %6d px %8d px'
              % (x0, x1, alto, bajo, ct, cb, ct - alto, bajo - cb))
    print('\ndibujado en', a.salida)
    print('verde = vela completa (mecha a mecha) · naranja = solo el cuerpo')
