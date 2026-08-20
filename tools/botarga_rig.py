# -*- coding: utf-8 -*-
"""Despieza la botarga común para poder ANIMARLA (animación de recortes).

Qué es esto: la botarga del sitio es un PNG plano. Para que mueva un brazo hay
que cortarla en piezas —cuerpo, brazos, piernas— y girar cada pieza sobre su
articulación. Es lo mismo que hacen Cartoon Animator o Synfig; aquí se hace con
las piezas del propio dibujo, sin redibujar nada.

🔑 POR QUÉ ESTA BOTARGA ES FÁCIL DE RIGEAR: brazos y piernas son tubos negros
   de grosor uniforme, con guante y zapato aparte (diseño *rubber hose*). Un
   tubo uniforme se puede girar desde el hombro sin que se rompa la anatomía,
   porque no hay anatomía. Con un personaje dibujado con hombros y codos esto
   no saldría bien.

🔴 EL CUERPO DE ESPALDAS, que es lo que pidió el dueño (la botarga sentada de
   espaldas frente al PC). De espaldas NO se ve la cara — y eso lo vuelve más
   fácil, no más difícil: la cara es justo lo que no se puede redibujar. Se
   quita así:
     1. máscara del naranja del cuerpo (el color se MIDE del archivo, no se
        escribe a mano: es (221,145,0));
     2. se rellenan los huecos → desaparecen boca y ojos que caen DENTRO;
     3. los ojos también MUERDEN el filo de arriba, y eso un relleno de huecos
        no lo arregla. Se repara con la **envolvente inferior** de la frontera
        superior: una mordida solo puede empujar el borde hacia abajo, así que
        la envolvente devuelve el filo recto exacto.
   ⚠️ La envolvente se aplica SOLO hasta x<520. En x=550 hay un salto de 111 px
      que NO es un ojo: es el escalón de la punta de la flecha, un rasgo real
      del dibujo. Con la envolvente global se rellenaba y la flecha perdía su
      forma (probado: parecía otra cosa).
   ⚠️ Se descartó la morfología (cierre) para esto: las mordidas son tan
      profundas que ni con radio 70 se cerraban, y un radio así ya redondea la
      punta de la flecha.

    python3 tools/botarga_rig.py          # exporta las piezas a out/rig/
"""
from __future__ import print_function

import io
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage as nd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE = os.path.join(RAIZ, 'scalpel', 'static', 'logo2_dark.png')
SALIDA = os.path.join(RAIZ, 'out', 'rig')
CONTORNO = 13          # grosor del contorno negro, medido del dibujo
CORTE_ENVOLVENTE = 520  # ver el ⚠️ de arriba


def _naranja(a):
    # 🔴 `.astype(int)` NO es decorativo: con uint8, `abs(r - 221)` DESBORDA
    #    para todo r < 221 y la máscara sale mutilada (medido: 126k px en vez
    #    de 181k, y la boca sin rellenar). Silencioso y muy fácil de repetir.
    a = a.astype(int)
    r, g, b, al = a[:, :, 0], a[:, :, 1], a[:, :, 2], a[:, :, 3]
    return (al > 120) & (abs(r - 221) < 45) & (abs(g - 145) < 45) & (b < 70)


def cuerpo_sin_cara(a):
    sil = nd.binary_fill_holes(_naranja(a))
    H, W = sil.shape
    top = np.full(W, -1)
    for x in range(W):
        c = np.where(sil[:, x])[0]
        if len(c):
            top[x] = c[0]
    pts = [(x, int(top[x])) for x in range(W)
           if top[x] >= 0 and x < CORTE_ENVOLVENTE]
    h = []
    for p in pts:                       # envolvente inferior (casco convexo)
        while len(h) >= 2:
            (x1, y1), (x2, y2) = h[-2], h[-1]
            if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) <= 0:
                h.pop()
            else:
                break
        h.append(p)
    for i in range(len(h) - 1):
        (x1, y1), (x2, y2) = h[i], h[i + 1]
        for x in range(x1, x2 + 1):
            y = int(round(y1 + (y2 - y1) * (x - x1) / float(x2 - x1)))
            if y < top[x]:
                sil[y:top[x], x] = True
    lab, n = nd.label(sil)              # fuera restos de cejas y pelusas
    if n > 1:
        sil = lab == int(np.argmax(nd.sum(sil, lab, range(1, n + 1)))) + 1
    return nd.binary_closing(sil, np.ones((5, 5)))


def pinta(sil):
    """Devuelve la pieza con el naranja y el contorno negro del dibujo."""
    H, W = sil.shape
    d = nd.binary_dilation(sil, np.ones((3, 3)), iterations=CONTORNO)
    out = np.zeros((H, W, 4), 'uint8')
    out[d] = (20, 20, 22, 255)
    out[sil] = (221, 145, 0, 255)
    return Image.fromarray(out)


def recorta(a, mascara, margen=6):
    ys, xs = np.where(mascara)
    x0, x1 = max(0, xs.min() - margen), min(a.shape[1], xs.max() + margen + 1)
    y0, y1 = max(0, ys.min() - margen), min(a.shape[0], ys.max() + margen + 1)
    tro = a[y0:y1, x0:x1].copy()
    tro[~mascara[y0:y1, x0:x1]] = 0
    return Image.fromarray(tro), (int(x0), int(y0))


def main():
    os.makedirs(SALIDA, exist_ok=True)
    a = np.array(Image.open(FUENTE).convert('RGBA'))
    sil = cuerpo_sin_cara(a)

    cuerpo = pinta(sil)
    cuerpo.save(os.path.join(SALIDA, 'cuerpo_frente.png'))
    cuerpo.transpose(Image.FLIP_LEFT_RIGHT).save(
        os.path.join(SALIDA, 'cuerpo_espalda.png'))

    # las extremidades son lo que queda fuera del cuerpo YA dilatado
    fuera = (a[:, :, 3] > 40) & (~nd.binary_dilation(
        sil, np.ones((3, 3)), iterations=CONTORNO + 2))
    lab, n = nd.label(fuera, np.ones((3, 3)))
    piezas = []
    for i in range(1, n + 1):
        m = lab == i
        if m.sum() < 15000:      # cejas, ojos asomados y rayas de movimiento
            continue
        ys, xs = np.where(m)
        piezas.append((i, m.sum(), xs.min(), xs.max(), ys.min(), ys.max()))
    # de arriba abajo y de izquierda a derecha: brazos primero, piernas después
    piezas.sort(key=lambda p: (p[4], p[2]))
    nombres = ['brazo_der', 'brazo_izq', 'pierna_der', 'pierna_izq']
    manifiesto = {}
    for (idx, tam, x0, x1, y0, y1), nom in zip(piezas, nombres):
        img, org = recorta(a, lab == idx)
        img.save(os.path.join(SALIDA, nom + '.png'))
        manifiesto[nom] = {'origen': org, 'tam': list(img.size), 'px': int(tam)}
        print('  %-11s %4dx%-4d en (%d,%d)  %6d px'
              % (nom, img.size[0], img.size[1], org[0], org[1], tam))
    manifiesto['cuerpo'] = {'origen': [0, 0], 'tam': list(cuerpo.size)}
    manifiesto['fuente'] = os.path.relpath(FUENTE, RAIZ)
    with io.open(os.path.join(SALIDA, 'rig.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps(manifiesto, indent=1))
    print('piezas en %s' % os.path.relpath(SALIDA, RAIZ))


if __name__ == '__main__':
    main()
