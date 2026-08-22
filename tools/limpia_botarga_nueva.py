# -*- coding: utf-8 -*-
"""Deja una botarga recién encargada lista para el sitio: fondo fuera.

    python3 tools/limpia_botarga_nueva.py mirar  <entrada.png>
    python3 tools/limpia_botarga_nueva.py cortar <entrada.png> <salida.png> [ids]

POR QUÉ EXISTE. `scalpel/tools_camo_cut.py` ya hace el recorte bueno, pero
asume **fondo blanco plano**. Las botargas que llegan de un generador de
imágenes vienen de dos formas y ninguna es transparente de verdad:
  · fondo BLANCO (las de bienvenida), o
  · un **cuadriculado gris HORNEADO en el píxel** — el visor del generador
    pinta el tablero de "transparencia" y luego exporta esa vista. Medido en
    las de agosto de 2026: cuadros de 29 px alternando gris ~213 y blanco
    ~253, y el PNG llega en RGB, sin canal alfa.
Este script normaliza las dos formas a lo mismo (fondo fuera) y deja el resto
del proceso —bolsas cerradas, variante oscura— en manos del cortador de siempre.

🔴 LA REGLA QUE NO SE ROMPE. El fondo se quita por **inundación desde el
   borde**: solo desaparece lo que se alcanza caminando desde fuera. Una bolsa
   blanca ENCERRADA por el contorno (axila, hueco entre las piernas) no se
   toca sola — la lista `ids` la decide un humano mirando el mapa que imprime
   `mirar`. Un borrado automático de "blancos encerrados" se comió llamas,
   humo y velas en julio de 2026 (ver CLAUDE.md); no se repite.

🔑 LA SOMBRA DEL SUELO NO SE BORRA, SE RECONSTRUYE. Las botargas del sitio
   llevan una sombra suave bajo los pies (mírese `logo3_naval.png`), y aquí
   llega pintada SEMITRANSPARENTE ENCIMA del tablero: si se quita, la botarga
   queda flotando; si se deja tal cual, se ven los cuadros grises dentro de la
   elipse. Por eso hay dos pasos antes del recorte:
     1. `_destablero()` — sube cada píxel del fondo hasta el **techo local**,
        con tope de un escalón. Deja la lámina como si se hubiera pintado
        sobre BLANCO, con la sombra intacta (ver la nota de la función: la vía
        geométrica se probó y NO sirve).
     2. el exterior se convierte con la regla de multiplicar: un gris G sobre
        blanco **es** tinta negra al alfa `255-G`. Blanco → invisible; gris de
        sombra → sombra de verdad, con su degradado intacto.

⚠️ El tablero se detecta por COLOR + CONEXIÓN, no solo por color: la suela
   gris de un zapato y el poste gris de la portería están en el mismo rango de
   tono que el cuadriculado, y sobreviven porque el contorno negro del dibujo
   corta la inundación antes de llegar a ellos.
"""
from __future__ import print_function

import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

BLANCO = 236        # a partir de aquí es "casi blanco"
# ⚠️ El tope llega hasta BLANCO a propósito: con (185,232) quedaba un hueco
#    en 233-235 y por ahí sobrevivían cuadros sueltos del tablero.
TABLERO = (140, BLANCO)  # rango de gris del cuadriculado horneado
FEATHER_LO, FEATHER_HI = 165, 246
MIN_AREA = 150      # bolsas más chicas que esto no se listan (motas)

VENTANA = 33        # ventana del techo local: mayor que un cuadro (29 px)
NEUTRO = 14         # separación máxima entre canales para llamarlo "gris"
HOLGURA = 8         # margen sobre el escalón medido (el gris no es plano)


def _neutro(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    return (mx - mn) < NEUTRO, mx


def _niveles(a, fuera):
    """Los dos grises del tablero de ESTA lámina: (claro, escalón).

    🔴 No se pueden escribir a mano. Medido en las seis de agosto de 2026, el
    mismo generador exportó tres pares distintos: 253/213 (escalón 40),
    255/205 (50) y 255/201 (**54**). Con un escalón fijo de 45 la tercera se
    quedaba 9 niveles corta y el fondo salía con un velo de cuadros — que es
    justo lo que el dueño vio en el PASS de Nile. `claro` sirve además de
    "blanco del papel" al calcular la tinta: así el fondo cae a alfa 0 solo,
    valga 253 o 255.
    """
    _, mx = _neutro(a)
    v = mx[fuera]
    if v.size < 1000:
        return 255, 0
    h = np.bincount(np.clip(v, 0, 255), minlength=256).astype(float)
    # ⚠️ El "papel" se busca desde 235, no desde 200: en una lámina muy tapada
    #    los cuadros OSCUROS (213) pueden ser más que los claros y ganarían el
    #    pico, con lo que el escalón saldría 0 y el tablero se quedaría entero.
    claro = int(np.argmax(h[235:])) + 235
    lo, hi = max(TABLERO[0], claro - 90), claro - 12
    if hi <= lo:
        return claro, 0
    oscuro = int(np.argmax(h[lo:hi])) + lo
    if h[oscuro] < 0.10 * h[claro]:      # fondo blanco plano, sin tablero
        return claro, 0
    return claro, claro - oscuro


def _destablero(a, fuera, paso):
    """Devuelve la lámina como si se hubiera pintado sobre BLANCO.

    ⚠️ Se intentó primero por GEOMETRÍA (medir período y fase del tablero y
    corregir los cuadros oscuros). NO funciona: la lámina viene reescalada, así
    que los cuadros miden 29 px "de media" y la rejilla se desfasa a lo largo
    del ancho — una fase global acierta el 52%, o sea nada, y el resultado es
    un tablero fantasma en el alfa. Aquí se hace SIN geometría: cada píxel del
    exterior se sube hasta el **techo local** (el valor más claro del fondo a
    menos de media ventana), con tope de un escalón. Un cuadro oscuro sube sus
    40 niveles; un cuadro claro ya está en el techo y no se mueve; bajo la
    sombra el techo es la propia sombra, así que su degradado se conserva.

    🔑 El techo se mide SOLO sobre `fuera` (el fondo alcanzable desde el
    borde). Si se midiera sobre todo, un zapato blanco pegado a la sombra
    subiría la sombra hasta 253 y se la comería.
    """
    if paso <= 0:
        return a
    _, mx = _neutro(a)
    vis = np.where(fuera, mx, 0).astype(np.int16)
    techo = ndimage.maximum_filter(vis, size=VENTANA)
    sube = np.clip(techo - mx, 0, paso + HOLGURA)
    sube[~fuera] = 0
    out = a.copy()
    for c in range(3):
        ch = out[..., c]
        out[..., c] = np.clip(ch + sube, 0, 255)
    return out


def _fondo_probable(a):
    """Máscara de 'esto PODRÍA ser fondo': casi blanco, o gris de sombra."""
    gris, mx = _neutro(a)
    return (mx > BLANCO) | (gris & (mx >= TABLERO[0]))


def _componentes(a):
    m = _fondo_probable(a)
    lbl, n = ndimage.label(m)                     # 4-conexo
    borde = set(lbl[0, :]) | set(lbl[-1, :]) | set(lbl[:, 0]) | set(lbl[:, -1])
    borde.discard(0)
    return m, lbl, n, borde


def _preparar(ruta):
    """Lámina lista para recortar: sin tablero y con su fondo ya localizado.

    Devuelve (lámina, blanco_del_papel)."""
    a = np.asarray(Image.open(ruta).convert('RGB')).astype(np.int16)
    _, lbl, _, borde = _componentes(a)
    fuera = np.isin(lbl, list(borde))
    claro, paso = _niveles(a, fuera)
    return _destablero(a, fuera, paso), claro


def mirar(ruta):
    a, _ = _preparar(ruta)
    m, lbl, n, borde = _componentes(a)
    fuera = np.isin(lbl, list(borde))
    print('%s  %dx%d' % (os.path.basename(ruta), a.shape[1], a.shape[0]))
    print('  fondo exterior      : %d px (%.1f%%)'
          % (fuera.sum(), 100.0 * fuera.sum() / fuera.size))
    tam = ndimage.sum(m, lbl, range(1, n + 1))
    dentro = [(int(i + 1), int(t)) for i, t in enumerate(tam)
              if (i + 1) not in borde and t >= MIN_AREA]
    dentro.sort(key=lambda x: -x[1])
    print('  bolsas CERRADAS (las decide un humano):')
    if not dentro:
        print('    — ninguna: el recorte es directo, sin ids')
    for i, t in dentro[:14]:
        ys, xs = np.where(lbl == i)
        print('    id %-4d %7d px   centro ~(%d,%d)'
              % (i, t, int(xs.mean()), int(ys.mean())))
    return dentro


def cortar(ruta, salida, ids=()):
    a, claro = _preparar(ruta)
    m, lbl, n, borde = _componentes(a)
    quitar = np.isin(lbl, list(borde) + [int(i) for i in ids])

    br = a[..., :3].max(axis=2)
    alfa = np.full(br.shape, 255, dtype=np.int16)
    rgb = a[..., :3].astype(np.int16)

    # Suavizado del borde: un recorte por umbral deja escalones y halo, así
    # que el alfa baja de forma gradual en la ORILLA.
    # 🔴 Solo en la orilla: la primera versión graduaba TODO píxel blanquecino
    #    y dejaba medio transparentes los ojos, los zapatos y el número de la
    #    camiseta — blancos legítimos que están lejos del fondo.
    orilla = ndimage.binary_dilation(quitar, iterations=2) & (~quitar)
    borde_suave = orilla & (br > FEATHER_LO)
    grad = 255 - (br - FEATHER_LO) * 255 // max(1, FEATHER_HI - FEATHER_LO)
    alfa[borde_suave] = np.clip(grad[borde_suave], 0, 255)

    # El exterior no se borra a secas: un gris G sobre blanco ES tinta negra
    # al alfa `claro - G`, así que la sombra del suelo sobrevive con su
    # degradado y el fondo desaparece solo. ⚠️ El blanco de referencia es el
    # MEDIDO en la lámina (253 en unas, 255 en otras), no un 255 a mano: con
    # el número equivocado el fondo se queda en alfa 2-9 y se ve un velo.
    tinta = np.clip(claro - br, 0, 255)
    tinta[tinta < 8] = 0
    alfa[quitar] = tinta[quitar]
    for c in range(3):
        ch = rgb[..., c]
        ch[quitar] = 0
        rgb[..., c] = ch

    out = np.dstack([rgb.astype(np.uint8), alfa.astype(np.uint8)])
    Image.fromarray(out, 'RGBA').save(salida)
    op = (alfa > 20).sum()
    print('%s -> %s  |  figura %d px (%.1f%% del lienzo)'
          % (os.path.basename(ruta), os.path.basename(salida), op,
             100.0 * op / alfa.size))
    return op


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    modo = sys.argv[1]
    if modo == 'mirar':
        mirar(sys.argv[2])
    elif modo == 'cortar':
        ids = [int(x) for x in sys.argv[4:]] if len(sys.argv) > 4 else []
        cortar(sys.argv[2], sys.argv[3], ids)
    else:
        sys.exit(__doc__)
