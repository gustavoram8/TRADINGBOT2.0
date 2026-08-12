# -*- coding: utf-8 -*-
"""Gráfico DIBUJADO POR NOSOTROS para el post de ejemplo del foro.

🔴 POR QUÉ EXISTE. El dueño mandó una captura de TradingView de una operación
fallida para meterla en el reel, y preguntó si era legal. La respuesta corta es
que la captura NO se usa, y el motivo no es solo TradingView:

  1. Sus condiciones permiten compartir capturas **conservando su logo**. O sea
     que "recortarla o maquillarla" para quitar la marca es justo lo que sí
     incumple — lo contrario de lo que parece intuitivo.
  2. Aunque se conservara el logo, meter la interfaz de otra empresa en el reel
     promocional de la nuestra sugiere una asociación que no existe.
  3. En esa captura se leen los nombres de indicadores de terceros y de sus
     autores (LuxAlgo, Nephew_Sam_). Son trabajos con dueño y con nombre.

Dibujarlo nosotros elimina los tres problemas de golpe, y además sale en la
paleta de la marca en vez de en la de otro. La operación que se representa es
la que él describió: comprar la ruptura del máximo de la sesión, que resultó
ser una barrida.

⚠️ Los precios NO son inventados a ojo: se construye una serie coherente (cada
vela abre donde cerró la anterior, las mechas contienen al cuerpo) para que
cualquiera que sepa leer un gráfico no vea un dibujo falso. Un gráfico bonito
pero imposible cuesta credibilidad justo con el público que queremos.

    python3 tools/gen_chart_foro.py
"""
from __future__ import print_function

import os

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTES = os.path.join(RAIZ, 'tools', '.fuentes')
DEST = os.path.join(RAIZ, 'scalpel', 'static', 'foro_ejemplo.png')

W, H = 1280, 720
FONDO = (11, 13, 18)
REJILLA = (28, 33, 43)
TEXTO = (150, 160, 176)
ALCISTA = (34, 197, 94)
BAJISTA = (239, 68, 68)
ORO = (201, 162, 39)
AZUL = (0, 79, 235)


def fuente(px, mono=False, peso='400'):
    n = 'JetBrainsMono-%s.ttf' % ('700' if peso != '400' else '400') if mono \
        else 'Inter-%s.ttf' % peso
    try:
        return ImageFont.truetype(os.path.join(FUENTES, n), px)
    except Exception:
        return ImageFont.load_default()


def serie():
    """La historia en velas de 5 minutos, contada de principio a fin.

    Tramo 1  caída con desplazamiento (el vendedor manda)
    Tramo 2  suelo y rebote lento (el retroceso, no un cambio de tendencia)
    Tramo 3  🔴 BARRIDA del máximo de la sesión: una mecha por encima que
             cierra por debajo — ahí es donde entra el comprador de ruptura
    Tramo 4  el rechazo, que es lo que convierte la entrada en pérdida
    """
    v = []                                   # (apertura, cierre, máximo, mínimo)

    def añade(pasos):
        p = v[-1][1] if v else 7504.0
        for d, mecha_a, mecha_b in pasos:
            c = p + d
            alto = max(p, c) + mecha_a
            bajo = min(p, c) - mecha_b
            v.append((p, c, alto, bajo))
            p = c

    # el techo se fija PRONTO y con dos toques, para que exista como nivel
    añade([(1.6, 2.4, .6), (-1.2, .5, 1.0), (1.0, 2.2, .5), (-2.0, .4, 1.4)])
    añade([(-2.6, .5, 1.6), (1.0, 1.2, .6), (-3.4, .4, 2.0), (-2.2, .6, 1.8),
           (1.4, 1.4, .5), (-4.0, .3, 2.4), (-2.4, .5, 1.5)])
    añade([(.9, 1.0, 1.2), (-1.0, .9, 1.4), (1.8, 1.2, .6), (2.4, 1.0, .8),
           (-.7, 1.1, 1.0), (2.8, .9, .5), (2.0, 1.3, .7), (2.6, .8, .6)])
    # 🔴 LA BARRIDA: la mecha pasa CLARAMENTE por encima del techo y el cuerpo
    #    cierra por debajo. Es la vela que hay que poder señalar con el dedo.
    añade([(1.8, 1.0, .6), (-1.6, 5.8, .4)])
    añade([(-3.6, .6, 1.8), (-4.4, .4, 2.2), (-2.8, .8, 1.6), (-3.2, .5, 2.0),
           (1.2, 1.4, .8), (-3.8, .6, 1.9), (-2.4, .7, 1.5)])
    return v


def main():
    v = serie()
    im = Image.new('RGB', (W, H), FONDO)
    d = ImageDraw.Draw(im, 'RGBA')

    L, R, T, B = 78, W - 132, 92, H - 62
    hi = max(x[2] for x in v) + 4.5      # aire arriba: ahí van stop y etiquetas
    lo = min(x[3] for x in v) - 2.0

    def Y(p):
        return T + (hi - p) / (hi - lo) * (B - T)

    paso = (R - L) / float(len(v))
    ancho = paso * .62

    # ── rejilla y escala de precios ──
    f_esc = fuente(13, mono=True)
    p0 = int(lo / 4) * 4
    while p0 < hi:
        if lo < p0 < hi:
            y = Y(p0)
            d.line([(L, y), (R, y)], fill=REJILLA, width=1)
            d.text((R + 12, y - 8), '%.2f' % p0, font=f_esc, fill=TEXTO)
        p0 += 4

    # ── franja de la sesión (la kill zone) ──
    i0, i1 = 15, 23
    d.rectangle([L + i0 * paso, T, L + i1 * paso, B], fill=(0, 79, 235, 26))
    d.text((L + i0 * paso + 8, T + 8), 'NY AM  ·  09:30 – 11:00',
           font=fuente(13, mono=True, peso='700'), fill=(120, 160, 255))

    # ── el máximo de la sesión, que es lo que se barre ──
    # ⚠️ se mide sobre el tramo ANTERIOR a la barrida: es el nivel que ya
    #    existía cuando el comprador decidió entrar
    techo = max(x[2] for x in v[:20])
    yt = Y(techo)
    for x in range(L, R, 14):
        d.line([(x, yt), (x + 7, yt)], fill=(201, 162, 39, 190), width=2)
    # ⚠️ esta etiqueta va a la DERECHA y la de la entrada a la izquierda: el
    #    nivel de entrada está medio punto por encima del techo, así que en el
    #    mismo lado se pisaban una a otra.
    _f = fuente(12, mono=True, peso='700')
    _t = 'MÁXIMO DE LA SESIÓN'
    _an = d.textlength(_t, font=_f)
    d.rectangle([R - 20 - _an, yt - 10, R - 8, yt + 9], fill=FONDO)
    d.text((R - 14 - _an, yt - 8), _t, font=_f, fill=ORO)

    # ── velas ──
    for i, (ap, ci, al, ba) in enumerate(v):
        cx = L + i * paso + paso / 2
        col = ALCISTA if ci >= ap else BAJISTA
        d.line([(cx, Y(al)), (cx, Y(ba))], fill=col, width=2)
        y1, y2 = Y(max(ap, ci)), Y(min(ap, ci))
        d.rectangle([cx - ancho / 2, y1, cx + ancho / 2, max(y2, y1 + 2)], fill=col)

    # ── la entrada equivocada y su stop ──
    ib = 21                                   # la vela de la barrida
    cxb = L + ib * paso + paso / 2
    yent = Y(techo + 0.5)                     # se compra al romper el techo
    d.line([(L, yent), (R, yent)], fill=(239, 68, 68, 165), width=2)
    # flecha hacia ARRIBA pegada a la vela: es una compra
    d.polygon([(cxb, yent - 30), (cxb - 10, yent - 12), (cxb + 10, yent - 12)],
              fill=BAJISTA)
    d.line([(cxb, yent - 12), (cxb, yent + 4)], fill=BAJISTA, width=3)
    ystop = Y(max(x[2] for x in v) + 1.2)
    for x in range(L, R, 12):
        d.line([(x, ystop), (x + 6, ystop)], fill=(150, 160, 176, 150), width=1)

    # 🔑 las etiquetas van DENTRO del gráfico, a la izquierda: en el margen
    #    derecho chocaban con la escala de precios y se leía "STOP7506.00"
    def etiqueta(y, txt, col):
        f = fuente(12, mono=True, peso='700')
        an = d.textlength(txt, font=f)
        d.rectangle([L + 8, y - 10, L + 20 + an, y + 9], fill=FONDO)
        d.text((L + 14, y - 8), txt, font=f, fill=col)
    etiqueta(yent, 'ENTRADA — ruptura', BAJISTA)
    etiqueta(ystop, 'STOP', TEXTO)

    # ── marco y cabecera ──
    d.rectangle([L, T, R, B], outline=(45, 52, 66), width=1)
    d.text((L, 34), 'MES · 5 min', font=fuente(26, peso='700'), fill=(226, 232, 240))
    d.text((L, 66), 'Compré la ruptura del máximo de la sesión. Era una barrida.',
           font=fuente(15), fill=TEXTO)
    d.text((R - 190, 40), 'TRADEABLE ACADEMY',
           font=fuente(12, mono=True, peso='700'), fill=(70, 78, 94))

    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    im.save(DEST)
    print('%s · %dx%d · %.0f KB' % (DEST, W, H, os.path.getsize(DEST) / 1024))


if __name__ == '__main__':
    main()
