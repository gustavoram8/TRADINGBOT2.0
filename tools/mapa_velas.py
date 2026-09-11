# -*- coding: utf-8 -*-
"""EL MAPA DE VELAS — pone el número de cada vela sobre la captura real.

    python3 tools/mapa_velas.py --imagen docs/capturas_prueba/mnq_long_ote.png \
        --columnas @docs/columnas/columnas_mnq_long_ote.txt \
        --marca 149:ENTRADA --marca 162:SALIDA --marca 145 --marca 131 \
        --salida out/mapa.png

🔴 POR QUÉ EXISTE. El bloque de hechos habla de "la vela 149", "la vela 145",
"HH en la vela 114". El dueño lo leyó y dijo lo único que se podía decir:
*"me gustaría saber exactamente a qué velas se refiere"*. Y tiene toda la
razón — **un número de vela que no se puede señalar en el gráfico no es
verificable, y lo que no se puede verificar no se puede creer.**

Todo el proyecto se apoya en que él pueda comprobarnos. Sin esta imagen, la
única forma de auditar un informe es fiarse, que es justo lo que no queremos.

🔑 NO INVENTA NADA: usa las MISMAS columnas y la MISMA numeración que
`analizador2`, así que si aquí la vela 149 cae donde está su flecha de entrada,
entonces el informe hablaba de esa vela. Y si no cae, hemos encontrado un fallo
de numeración, que es igual de valioso.

⚠️ Se etiqueta una de cada `--cada` velas (10 por defecto) más las marcadas a
mano: numerarlas todas sobre 163 velas de 5 px deja una mancha ilegible.
"""
from __future__ import print_function

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

import analizador2 as A2          # noqa: E402


def _fuente(px):
    for ruta in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(ruta):
            return ImageFont.truetype(ruta, px)
    return ImageFont.load_default()


def dibuja(imagen, cajas, marcas, cada=10, salida='out/mapa.png',
           desde=None, hasta=None):
    r = A2.analiza(imagen, cajas=cajas, verboso=False)
    velas = r['velas']
    base = Image.open(imagen).convert('RGB')
    W, H = base.size
    # 🔑 Una BANDA BLANCA debajo del gráfico para los números. Escribirlos
    #    encima de las velas tapa justo lo que se quiere mirar — y el fondo de
    #    un gráfico es impredecible, así que no hay color de texto que funcione
    #    siempre (la lección del punto 10 de la checklist: contra una
    #    ilustración no hay número de contraste que valga).
    alto_banda = 54
    lienzo = Image.new('RGB', (W, H + alto_banda), (255, 255, 255))
    lienzo.paste(base, (0, 0))
    d = ImageDraw.Draw(lienzo)
    f = _fuente(12)
    fg = _fuente(15)

    marcadas = dict(marcas)
    for i, v in enumerate(velas):
        cx = (v['x0'] + v['x1']) // 2
        etiqueta = marcadas.get(i)
        rutina = (i % cada == 0)
        if not etiqueta and not rutina:
            continue
        col = (200, 0, 0) if etiqueta else (110, 110, 110)
        # la línea guía baja desde la vela hasta su número
        d.line([cx, v['min'] + 2, cx, H + 6], fill=col,
               width=2 if etiqueta else 1)
        t = str(i)
        an = d.textlength(t, font=fg if etiqueta else f)
        d.text((cx - an / 2, H + 8), t, fill=col, font=fg if etiqueta else f)
        if etiqueta:
            # el nombre va GIRADO: en horizontal, dos marcas cercanas se pisan
            # y con 163 velas de 5 px eso pasa siempre.
            tmp = Image.new('RGBA', (int(d.textlength(etiqueta, font=f)) + 4, 16),
                            (0, 0, 0, 0))
            ImageDraw.Draw(tmp).text((0, 0), etiqueta, fill=(200, 0, 0), font=f)
            tmp = tmp.rotate(90, expand=True)
            lienzo.paste(tmp, (cx - 7, H + 26), tmp)
            # 🔴 EL RECUADRO VA EXACTO, SIN UN PÍXEL DE MARGEN. Lo cazó el
            #    dueño: llevaba 2 px por lado y con las velas cada 5,5 px el
            #    recuadro de la 145 (802-806) llegaba a 808 y se comía el
            #    arranque de la 146 (807). Él lo leyó como "englobaste dos
            #    velas" y era exactamente eso.
            #    ⚠️ En una rejilla apretada NINGÚN margen es seguro: el margen
            #    que hace visible una marca es el que la hace mentir.
            d.rectangle([v['x0'], v['max'], v['x1'], v['min']],
                        outline=(200, 0, 0), width=1)
            # Para que se vea sin margen, la marca se refuerza FUERA de la vela:
            # un acento justo encima y otro justo debajo, del ancho exacto.
            for y in (v['max'] - 4, v['min'] + 4):
                d.line([v['x0'], y, v['x1'], y], fill=(200, 0, 0), width=2)
    # 🔑 EL ACERCAMIENTO NO ES UN EXTRA. Con 163 velas de 5 px, los números del
    #    tramo que interesa quedan pegados unos a otros y "verificar" se vuelve
    #    adivinar. Es la misma lección que ya dejó escrita `analizador2 --dibuja`:
    #    a ese tamaño no es que esté mal marcado, es que NADIE puede saberlo.
    if desde is not None or hasta is not None:
        a0 = max(0, desde if desde is not None else 0)
        a1 = min(len(velas) - 1, hasta if hasta is not None else len(velas) - 1)
        x0 = max(0, velas[a0]['x0'] - 12)
        x1 = min(W, velas[a1]['x1'] + 12)
        lienzo = lienzo.crop((x0, 0, x1, H + alto_banda))
        esc = max(1, min(8, int(round(1200.0 / max(1, x1 - x0)))))
        lienzo = lienzo.resize((lienzo.width * esc, lienzo.height * esc),
                               Image.NEAREST)
    carpeta = os.path.dirname(salida)
    if carpeta and not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    lienzo.save(salida)
    return salida, len(velas)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--imagen', required=True)
    ap.add_argument('--columnas', required=True)
    ap.add_argument('--cada', type=int, default=10,
                    help='cada cuántas velas se pone un número de rutina')
    ap.add_argument('--marca', action='append', default=[],
                    metavar='N[:NOMBRE]',
                    help='vela a resaltar, con nombre opcional. Repetible.')
    ap.add_argument('--desde', type=int, help='primera vela del acercamiento')
    ap.add_argument('--hasta', type=int, help='última vela del acercamiento')
    ap.add_argument('--salida', default=os.path.join(RAIZ, 'out', 'mapa.png'))
    a = ap.parse_args()
    marcas = []
    for m in a.marca:
        n, _, nom = m.partition(':')
        marcas.append((int(n), nom or ''))
    ruta, n = dibuja(a.imagen, A2.lee_columnas(a.columnas), marcas,
                     a.cada, a.salida, a.desde, a.hasta)
    print('%d velas numeradas → %s' % (n, ruta))
    for i, nom in sorted(marcas):
        print('   vela %d%s' % (i, ' = %s' % nom if nom else ''))
