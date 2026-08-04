# -*- coding: utf-8 -*-
"""Quita la baranda de la botarga (logo7) sin tocarle un dedo al personaje.

    python3 tools/quita_baranda.py

Entrada:  scalpel/static/logo7.jpeg   (JPEG, fondo blanco, con baranda)
Salida:   scalpel/static/logo7_sin_baranda.png   (PNG con transparencia)
          out/posts_ig/_baranda_diag.png         (diagnóstico ampliado)

POR QUÉ NO SE RECORTA, SE BORRA
-------------------------------
Recortar por rectángulo se llevaría una pierna. Y seleccionar "todo lo gris"
tampoco vale: el contorno negro del personaje tiene bordes suavizados que
también son grises, y el JPEG añade suciedad alrededor de cada línea.

Lo que se hace es una **inundación desde el borde de la imagen**: se entra por
las cuatro esquinas y se avanza solo por píxeles que NO son ni azules ni negros.
El fondo blanco y la baranda están conectados entre sí y con el borde, así que
se inundan enteros. El personaje NO: sus blancos (guantes, zapatos, ojos) están
ENCERRADOS por su propio contorno negro, y la inundación se detiene ahí. Por eso
no hay forma de que se coma un brazo.

LA PARTE QUE SÍ ES DELICADA
---------------------------
La barra horizontal pasa POR DELANTE de la cola azul de la flecha. Al quitarla
queda una ranura vacía atravesando el cuerpo. Eso no es un borrado: hay que
REPINTARLO. Se rellena columna a columna, y solo donde arriba y abajo del hueco
hay azul del personaje — así se reconstruye el cuerpo sin inventar nada donde no
lo había.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRADA = os.path.join(RAIZ, 'scalpel', 'static', 'logo7.jpeg')
SALIDA = os.path.join(RAIZ, 'scalpel', 'static', 'logo7_sin_baranda.png')
DIAG = os.path.join(RAIZ, 'out', 'posts_ig', '_baranda_diag.png')


def main():
    im = Image.open(ENTRADA).convert('RGB')
    a = np.asarray(im).astype(np.int16)
    H, W, _ = a.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(2), a.min(2)

    azul = (b - r > 45) & (b - g > 30) & (b > 90)
    negro = mx < 100

    # ⚠️ La baranda NO tiene contorno negro (se midió: cero trazos oscuros en la
    # franja donde no hay personaje) — es gris puro. Lo que sí tiene es una
    # LÍNEA DE SOMBRA de 3-4 px bajo la barra y a los lados de los postes, y esa
    # línea sí es oscura. Tomarla por contorno del personaje era lo que frenaba
    # la inundación y dejaba la baranda entera.
    # El trazo del personaje mide 8-15 px, el de la baranda 3-4. Una apertura
    # morfológica con radio 3 borra lo fino y respeta lo grueso, así que la
    # barrera queda siendo solo el personaje.
    # ¿Hay baranda? Se busca una estructura gris LARGA y horizontal en la franja
    # donde no hay personaje. Si no la hay, la imagen ya viene limpia y aplicarle
    # el tratamiento (apertura + reconstrucción) sería maltratarla para nada.
    gris0 = (mx - mn < 34) & (mx > 90) & (mx < 246)
    hay_baranda = bool(ndimage.binary_opening(
        gris0, structure=np.ones((1, 200), bool)).any())
    print('baranda detectada: %s' % ('SI' if hay_baranda else 'no, imagen limpia'))

    if hay_baranda:
        yy, xx = np.mgrid[-2:3, -2:3]
        disco = (xx ** 2 + yy ** 2) <= 4
        negro_grueso = ndimage.binary_opening(negro, structure=disco)
        print('trazo negro: %d px totales, %d tras quitar lo fino'
              % (negro.sum(), negro_grueso.sum()))
    else:
        negro_grueso = negro
    barrera = azul | negro_grueso

    # ── inundación desde el borde ────────────────────────────────────────
    libre = ~barrera
    etiq, _ = ndimage.label(libre)                    # 4-conectividad
    bordes = np.concatenate([etiq[0, :], etiq[-1, :], etiq[:, 0], etiq[:, -1]])
    fuera = np.isin(etiq, np.unique(bordes[bordes > 0]))
    print('fondo+baranda: %.1f%% de la imagen' % (100.0 * fuera.mean()))

    # Red de seguridad: la apertura puede comerse algun trazo FINO del propio
    # personaje (con radio 3 salian las suelas punteadas). Se devuelve lo oscuro
    # que esté pegado a el.
    # ⚠️ UNA SOLA PASADA. Repitiéndolo, el rescate CAMINA por la línea de sombra
    # de la baranda —cada vuelta avanza un par de píxeles— y acaba resucitándola
    # a trozos. Se probó con tres vueltas y salieron guiones por toda la imagen.
    # ⚠️ El rescate se hace SOLO donde el trazo oscuro NO forma una recta larga.
    # Sin ese filtro revivía los tramos de la sombra de la baranda que pasan a
    # dos píxeles del personaje (bajo la barriga negra y junto a los zapatos), y
    # quedaban guiones sueltos por toda la imagen.
    largo_h = ndimage.binary_opening(negro, structure=np.ones((1, 25), bool))
    largo_v = ndimage.binary_opening(negro, structure=np.ones((25, 1), bool))
    recta = ndimage.binary_dilation(largo_h | largo_v, iterations=2)

    if hay_baranda:
        vecino = ndimage.binary_dilation(~fuera, iterations=2)
        rescate = fuera & negro & vecino & ~recta
        fuera &= ~rescate
        print('trazo rescatado del personaje: %d px' % rescate.sum())

    # ── los huecos que deja la baranda al cruzar el personaje ────────────
    # No es solo la barra de arriba: el travesaño de ABAJO cruza por delante de
    # las botas, y al quitarlo se llevaba un trozo de bota. (Lo cazó el dueño:
    # "le borraste las botas".)
    #
    # El discriminador es el color ORIGINAL: si un píxel que acabamos de quitar
    # era GRIS, era baranda; si era blanco, era fondo. Y si además tiene
    # personaje cerca por arriba y por abajo —o por los dos lados—, es que la
    # baranda estaba tapando el cuerpo ahí.
    #
    # ⚠️ La ventana es corta (30 px) a propósito: con una ventana larga, un
    # poste que pasa ENTRE las piernas también quedaría "entre personaje" y se
    # rellenaría el hueco de las piernas.
    gris = (mx - mn < 34) & (mx > 90) & (mx < 246)
    dentro = ~fuera
    V, Hh = np.ones((31, 1), bool), np.ones((1, 31), bool)
    arr = ndimage.binary_dilation(dentro, structure=V, origin=(15, 0))
    aba = ndimage.binary_dilation(dentro, structure=V, origin=(-15, 0))
    izq = ndimage.binary_dilation(dentro, structure=Hh, origin=(0, 15))
    der = ndimage.binary_dilation(dentro, structure=Hh, origin=(0, -15))
    tapado = (fuera & gris & ((arr & aba) | (izq & der))
              if hay_baranda else np.zeros_like(fuera))
    print('pixeles a reconstruir: %d' % tapado.sum())
    fuera &= ~tapado          # pasan a ser personaje ya, no al final

    # ── esquirlas sueltas de la baranda ──────────────────────────────────
    # Donde la sombra de la barra se cruza con un poste queda un trozo mas
    # grueso que sobrevive a la apertura. Son piezas SUELTAS, sin contacto con
    # el personaje, asi que se descartan por tamano.
    # ⚠️ Ojo: las CEJAS tambien son piezas sueltas. Por eso se mide antes de
    # elegir el umbral en vez de quedarse solo con la pieza mas grande.
    dentro = ~fuera
    et, ncomp = ndimage.label(dentro)
    tam = ndimage.sum(dentro, et, range(1, ncomp + 1))
    print('piezas sueltas (px):', sorted(tam.astype(int), reverse=True)[:12])
    UMBRAL = 900
    for i, t in enumerate(tam, start=1):
        if t < UMBRAL:
            fuera[et == i] = True
    print('descartadas %d esquirlas' % int((tam < UMBRAL).sum()))

    # ── construir el PNG ─────────────────────────────────────────────────
    rgba = np.dstack([a.astype(np.uint8),
                      np.where(fuera, 0, 255).astype(np.uint8)])
    # Reconstruir con el color del pixel de PERSONAJE mas cercano. Rellenar con
    # un azul fijo dejaba una cicatriz recta donde la barra cruzaba el contorno
    # negro; asi el trazo tambien se reconstruye solo.
    if tapado.any():
        _, idx = ndimage.distance_transform_edt(~dentro, return_indices=True)
        fuente = a[idx[0], idx[1]].astype(np.uint8)
        rgba[..., :3][tapado] = fuente[tapado]
        rgba[..., 3][tapado] = 255

    salida = Image.fromarray(rgba, 'RGBA')
    salida = salida.crop(salida.getchannel('A').getbbox())
    salida.save(SALIDA)
    print('escrito %s  %s' % (SALIDA, salida.size))

    # ── diagnóstico: el recorte sobre damero, para juzgar los bordes ─────
    os.makedirs(os.path.dirname(DIAG), exist_ok=True)
    w, h = salida.size
    dam = Image.new('RGB', (w, h))
    d = np.asarray(dam).copy()
    yy, xx = np.mgrid[0:h, 0:w]
    tablero = (((xx // 24) + (yy // 24)) % 2) * 40 + 205
    d[..., 0] = d[..., 1] = d[..., 2] = tablero
    dam = Image.fromarray(d.astype(np.uint8))
    dam.paste(salida, (0, 0), salida)
    dam.save(DIAG)
    print('diagnóstico en %s' % DIAG)
    return 0


sys.exit(main())
