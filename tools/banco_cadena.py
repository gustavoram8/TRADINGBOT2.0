# -*- coding: utf-8 -*-
"""La CADENA ENTERA, medida contra verdad por construcción.

    python3 tools/banco_cadena.py --laminas 24

🔴 NO TOCA EL ANALIZADOR. Vive en tools/, no lo importa la app.

═══ QUÉ SE MIDE, Y POR QUÉ ASÍ ═══
El dueño no preguntó "¿te gustan los recuadros?". Preguntó si al final el
analizador puede decir *"efectivamente rompió X a la baja"* sin inventárselo.
Eso solo se responde con un porcentaje, y el porcentaje solo vale si la verdad
es EXACTA. Aquí lo es: los gráficos los dibuja este mismo archivo, así que de
cada vela se sabe su máximo, su mínimo y su cuerpo AL PÍXEL, sin medir nada.

La cadena tiene tres eslabones y se miden POR SEPARADO, porque si el resultado
final sale mal hay que saber cuál falló:

  A · localizar    ¿en qué columna está cada vela?      → Gemini (se mide en el VPS)
  B · medir        ¿de dónde a dónde se extiende?       → píxeles, aquí
  C · concluir     ¿eso es un FVG, un BOS, una barrida? → aritmética, aquí

Este archivo mide **B y C**, que es lo que se puede correr gratis y sin red.
Para A se usa `cajas_ia.py --recorte` en el VPS: pasándole `--columnas-ia` a
este programa, se sustituye el eslabón B de partida por las columnas reales que
devolvió el modelo y sale la cadena completa.

═══ POR QUÉ LOS GRÁFICOS SON ALEATORIOS Y FEOS A PROPÓSITO ═══
Cada lámina sortea fondo claro u oscuro, dos colores de vela cualesquiera
(rosados, dorados, morados: la queja literal del dueño), cuerpos rellenos o
huecos, ancho y separación de vela, rejilla sí o no, y encima le pinta la
basura que rompió al lector de píxeles en la captura real: una **zona
translúcida** por detrás, **líneas horizontales** de nivel, una **discontinua**
y **etiquetas** de texto; **la marca de agua de la sesión**, en letras enormes
del color de las velas y por detrás de ellas; y **líneas VERTICALES**, que son
el borde de una caja de sesión. Un método que solo funciona con velas verdes y
rojas sobre fondo negro no sirve para nada: los clientes usan lo que les da la
gana.

🔴 LAS DOS ÚLTIMAS SE AÑADIERON EL 09-sep Y LAS DOS DESTAPARON AGUJEROS QUE
LLEVABAN MESES ABIERTOS con el control de calidad en verde:

    máximo y mínimo exactos      sin nada    solo marca    marca + verticales
                                   96,3%        85,8%            82,9%

⚠️ El 2,9 de las verticales ENGAÑA por poco. En el banco caen al azar y tocan
una o dos velas de cada 60; cuando tocan, **destruyen la vela entera**. Y en el
mundo real no caen al azar: el borde de una caja de sesión cae en la APERTURA
DE LA KILLZONE, que es exactamente donde entra un trader de ICT. En la cuarta
captura del dueño cruza las columnas de su entrada y de su stop, y la tinta
oscura de esas columnas mide 295 y 441 px en un gráfico de vela mediana 41.

⚠️ La comparación se hace contra DOS verdades a propósito:
  · contra la serie de PRECIO original → el resultado honesto de punta a punta,
    con el redondeo a píxeles incluido (una captura tiene la precisión que
    tiene, y un FVG de medio píxel no se puede leer de ninguna manera);
  · contra la misma serie YA REDONDEADA a píxeles → aísla lo que falla por
    culpa del extractor, sin cobrarle el redondeo.
Si la primera sale mal y la segunda bien, el límite es la captura, no el código.
"""
from __future__ import print_function

import argparse
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

import afina_velas as AF          # noqa: E402
import hechos_grafico as HG       # noqa: E402
import rejilla_velas as RV        # noqa: E402

AN, AL = 1400, 800
# Interruptor de la marca de agua, para medir el ANTES y el DESPUES.
MARCA_AGUA = [True]
# Interruptor de las lineas verticales (bordes de caja de sesion).
VERTICALES = [True]
# Interruptor de los dibujos del trader (flechas, fibs).
DIBUJOS = [True]
DIB_FLECHAS = [True]
DIB_FIBS = [True]
# Una vela no puede medir más de esto por la MEDIANA de su propio gráfico.
TOPE_ALTO = 3.0
MARGEN_X, MARGEN_Y = 60, 70


def _tema(rnd):
    """Un tema cualquiera. Nada de 'verde sube, rojo baja'."""
    oscuro = rnd.random() < 0.5
    if oscuro:
        fondo = (rnd.randint(8, 34), rnd.randint(8, 34), rnd.randint(12, 44))
        rejilla = tuple(min(255, c + rnd.randint(14, 30)) for c in fondo)
    else:
        fondo = (rnd.randint(232, 255),) * 2 + (rnd.randint(238, 255),)
        rejilla = tuple(max(0, c - rnd.randint(14, 30)) for c in fondo)

    def tinta():
        # cualquier color con contraste suficiente contra el fondo
        for _ in range(60):
            c = (rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255))
            if sum(abs(c[i] - fondo[i]) for i in range(3)) > 200:
                return c
        return (255, 0, 128)

    a = tinta()
    for _ in range(60):
        b = tinta()
        if sum(abs(a[i] - b[i]) for i in range(3)) > 150:
            break
    return {'fondo': fondo, 'rejilla': rejilla, 'sube': a, 'baja': b,
            'hueco_cuerpo': rnd.random() < 0.35,
            'con_rejilla': rnd.random() < 0.7,
            'ancho': rnd.choice([9, 11, 13, 15, 17]),
            'sep': rnd.choice([3, 4, 5, 6])}


def _serie(n, rnd, desplazamientos=True):
    """Un paseo aleatorio CON VELAS DE DESPLAZAMIENTO.

    🔴 TERCER AGUJERO DE FÁBRICA (2026-09-09). El generador hacía velas de
    tamaño uniforme, así que en el banco **nunca aparecía una vela gigante** —
    y son justo las que decide un análisis de ICT: el desplazamiento que abre un
    FVG, la vela que rompe estructura, la que barre liquidez.

    Consecuencia medida: `TOPE_ALTO`, el tope de altura creíble para una vela,
    daba EXACTAMENTE el mismo resultado en 3,0 · 5,0 · 6,0. O sea que el banco
    no podía opinar sobre ese parámetro, y mientras tanto en la cuarta captura
    del dueño ese tope estaba **descartando sus velas de entrada y de salida**
    por medir 4-5 veces la mediana: se quedaban fuera de la votación y ganaba un
    fragmento de 4 px en un sitio absurdo.

    Un parámetro que el banco no puede mover es un parámetro elegido a ojo.
    """
    p, out = 100.0, []
    for _ in range(n):
        o = p
        # ~1 de cada 12 es un desplazamiento de 3 a 6 veces el tamaño normal
        k = rnd.uniform(3.0, 6.0) if (desplazamientos and rnd.random() < 0.08) \
            else 1.0
        c = o + rnd.uniform(-2.4, 2.4) * k
        h = max(o, c) + rnd.uniform(0.02, 1.7) * k
        l = min(o, c) - rnd.uniform(0.02, 1.7) * k
        out.append((o, h, l, c))
        p = c
    return out


def _mezcla(im, caja, color, alfa):
    """Zona translúcida POR DETRÁS de las velas, como una caja de sesión."""
    a = np.asarray(im).astype(float)
    x0, y0, x1, y1 = caja
    reg = a[y0:y1, x0:x1]
    a[y0:y1, x0:x1] = reg * (1 - alfa) + np.array(color, float) * alfa
    return Image.fromarray(a.astype('uint8'))


MARCAS = ('NY AM', 'LONDON', 'ASIA', 'NY PM', 'LUNCH', 'SILVER BULLET')
_FUENTES = ('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')


def _marca_de_agua(im, t, rnd):
    """La MARCA DE AGUA de la sesión: texto enorme, semitransparente y **del
    color de las velas**, por DETRÁS de ellas.

    🔴 ESTA ES LA TRAMPA QUE LA FÁBRICA NO PROBABA, y por eso el defecto salía
    por la puerta con el control de calidad en verde. En la captura real del
    dueño, su indicador de killzones pinta "NY AM" en letras gigantes de un
    verde azulado **idéntico al de sus velas**. Resultado medido en la fila que
    cruza su entrada: el color más repetido de la ventana pasa a ser el de las
    velas, el extractor lo toma por FONDO, y la vela desaparece. 6 de sus 102
    velas salieron con altura CERO, cinco pegadas a su entrada.

    🔑 Va ANTES de dibujar las velas, que es como lo pinta la plataforma: las
    velas tapan la marca, así que la lámina sigue siendo legible para una
    persona. Lo que envenena no es tapar las velas — es que el FONDO entre
    velas deje de ser fondo y pase a tener el color de la tinta.

    ⚠️ El color se mezcla con el fondo, no se usa el de la vela a pelo: una
    marca opaca del color exacto de la vela sería un caso que ninguna
    plataforma pinta, y volveríamos a cobrarle al extractor una lámina
    imposible en vez de una difícil."""
    try:
        for f in _FUENTES:
            if os.path.exists(f):
                fuente = ImageFont.truetype(f, rnd.randint(70, 150))
                break
        else:
            return im
    except Exception:
        return im
    capa = Image.new('RGB', im.size)
    capa.paste(im)
    d = ImageDraw.Draw(capa)
    for _ in range(rnd.randint(1, 2)):
        base = rnd.choice([t['sube'], t['baja']])
        alfa = rnd.uniform(0.35, 0.70)
        col = tuple(int(round(t['fondo'][i] * (1 - alfa) + base[i] * alfa))
                    for i in range(3))
        d.text((rnd.randint(MARGEN_X, AN - 420),
                rnd.randint(MARGEN_Y, AL - 220)),
               rnd.choice(MARCAS), font=fuente, fill=col)
    return capa


def lamina(ruta, rnd, n=60, marca_de_agua=True, verticales=True,
           dibujos=True):
    """Dibuja una lámina y devuelve su VERDAD (píxeles y precio)."""
    t = _tema(rnd)
    ohlc = _serie(n, rnd)
    lo = min(v[2] for v in ohlc)
    hi = max(v[1] for v in ohlc)
    pad = (hi - lo) * 0.10
    p0, p1 = lo - pad, hi + pad
    y0, y1 = AL - MARGEN_Y, MARGEN_Y
    py = lambda pr: int(round(y0 + (pr - p0) * (y1 - y0) / float(p1 - p0)))

    im = Image.new('RGB', (AN, AL), t['fondo'])
    d = ImageDraw.Draw(im)
    if t['con_rejilla']:
        for y in range(0, AL, 80):
            d.line([(0, y), (AN, y)], fill=t['rejilla'])
        for x in range(0, AN, 110):
            d.line([(x, 0), (x, AL)], fill=t['rejilla'])

    # Zona translúcida detrás — la que fundía velas y caja en una sola mancha.
    # ⚠️ El COLOR de la zona no puede ser cualquiera: al mezclarlo con el fondo
    # puede acabar siendo el mismo color que una de las velas, y entonces esa
    # vela deja de existir en la imagen. Eso no es un caso real que haya que
    # aguantar (ninguna plataforma pinta un sombreado que borra las velas), es
    # un defecto del generador: hacía láminas ILEGIBLES y luego le cobraba al
    # extractor no leerlas. Se exige que las dos velas sigan destacando sobre
    # el fondo YA MEZCLADO.
    zx = rnd.randint(MARGEN_X, AN // 2)
    zona = (zx, rnd.randint(80, 300), zx + rnd.randint(150, 420),
            rnd.randint(450, AL - 40))
    alfa = rnd.uniform(0.08, 0.22)
    for _ in range(40):
        zc = (rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255))
        mez = tuple(t['fondo'][i] * (1 - alfa) + zc[i] * alfa for i in range(3))
        ok = all(sum(abs(col[i] - mez[i]) for i in range(3)) > 150
                 for col in (t['sube'], t['baja']))
        if ok:
            break
    im = _mezcla(im, zona, zc, alfa)
    # 🔴 LA MARCA DE AGUA VA AQUÍ: después del fondo y de la caja de sesión,
    #    ANTES de las velas. Ver `_marca_de_agua`.
    if marca_de_agua:
        im = _marca_de_agua(im, t, rnd)
    d = ImageDraw.Draw(im)

    paso = t['ancho'] + t['sep']
    verdad, x = [], MARGEN_X
    usadas = []
    for (o, h, l, c) in ohlc:
        if x + t['ancho'] > AN - MARGEN_X:
            break
        alc = c >= o
        col = t['sube'] if alc else t['baja']
        cx = x + t['ancho'] // 2
        yo, yc, yh, yl = py(o), py(c), py(h), py(l)
        ct, cb = min(yo, yc), max(yo, yc)
        d.line([(cx, yh), (cx, yl)], fill=col)
        if t['hueco_cuerpo'] and alc:
            d.rectangle([x, ct, x + t['ancho'] - 1, cb], outline=col)
        else:
            d.rectangle([x, ct, x + t['ancho'] - 1, cb], fill=col)
        verdad.append({'x0': x, 'x1': x + t['ancho'] - 1, 'max': yh, 'min': yl,
                       'cuerpo_alto': ct, 'cuerpo_bajo': cb, 'alcista': alc})
        usadas.append((o, h, l, c))
        x += paso

    # 🔴 LÍNEAS VERTICALES — el borde de una caja de sesión (2026-09-09).
    # LA FÁBRICA NO PROBABA ESTO y es el defecto más destructivo encontrado
    # hasta ahora. En la cuarta captura del dueño, el borde vertical de la caja
    # de killzone cruza de arriba abajo las columnas de las velas de su
    # entrada: la tinta oscura de esas columnas mide 295 y 441 px en un gráfico
    # cuya vela mediana mide 41. El extractor no puede separar la vela de la
    # línea, se pasa del tope de credibilidad, vuelve a medir con límite y
    # devuelve fragmentos de 5 y 8 px en sitios absurdos.
    # 🔑 Y es GENERAL, no de su indicador: cualquier caja de sesión, cualquier
    #    rayo vertical, la línea de la hora actual. Todas hacen lo mismo.
    # ⚠️ Se dibujan ENCIMA de las velas, que es el caso duro y el que se ve en
    #    su captura. Y de un color oscuro que contrasta, como un borde de caja.
    if verticales:
        for _ in range(rnd.randint(1, 2)):
            vx = rnd.randint(MARGEN_X + 40, AN - MARGEN_X - 40)
            col = tuple(max(0, c - rnd.randint(60, 140)) for c in t['fondo']) \
                if sum(t['fondo']) > 380 else \
                tuple(min(255, c + rnd.randint(60, 140)) for c in t['fondo'])
            d.line([(vx, 0), (vx, AL)], fill=col, width=rnd.choice([1, 1, 2]))

    # 🔴 LOS DIBUJOS DEL TRADER (2026-09-09). Cuarto agujero de fábrica, y el
    # que más gente afecta: **el sitio le PIDE al cliente que marque su entrada
    # y su salida**, y encima casi todos traen fibs, cajas y niveles propios.
    # Todo eso se estaba contando como tinta de vela.
    # Medido en la cuarta captura del dueño, columna x=610: lo que yo tomaba
    # por "una mecha rota en tres trozos" eran su flecha azul (41,98,255) en
    # y=361-363, una marca roja (178,40,51) en y=391-392 y una línea gris. La
    # vela de verdad medía 5 px.
    # 🔑 Van ENCIMA de las velas y PEGADAS a ellas, que es como las pinta un
    #    trader: una flecha marcando la vela de entrada toca la vela.
    if dibujos and DIB_FLECHAS[0]:
        for _ in range(rnd.randint(1, 3)):
            if not verdad:
                break
            vv = verdad[rnd.randrange(len(verdad))]
            cx = (vv['x0'] + vv['x1']) // 2
            col = (rnd.randint(0, 90), rnd.randint(60, 160), rnd.randint(180, 255)) \
                if rnd.random() < 0.5 else \
                (rnd.randint(180, 255), rnd.randint(20, 90), rnd.randint(20, 90))
            arr = rnd.random() < 0.5
            yy = (vv['max'] - rnd.randint(2, 26)) if arr else \
                 (vv['min'] + rnd.randint(2, 26))
            h = rnd.randint(10, 18)
            d.rectangle([cx - 2, yy - h if arr else yy, cx + 2,
                         yy if arr else yy + h], fill=col)
            pta = yy - h - 8 if arr else yy + h + 8
            d.polygon([(cx - 7, yy - h if arr else yy + h), (cx + 7,
                       yy - h if arr else yy + h), (cx, pta)], fill=col)
    # un racimo de fibs: varias horizontales del mismo color con etiqueta
    if dibujos and DIB_FIBS[0] and rnd.random() < 0.7:
        # 🔴 EL RACIMO DE FIBS, BIEN DIBUJADO — Y POR QUÉ IMPORTA (2026-09-10).
        # La primera versión llamaba a `rnd.randint(70, 130)` DENTRO del bucle,
        # así que cada nivel se multiplicaba por una altura distinta y los siete
        # se apelotonaban: en una lámina taparon una vela durante ~15 filas
        # SEGUIDAS. Diagnosticado mirando la fila 530 de la vela 47: la ventana
        # entera valía (186,54,102) —el color del fib— y el color de la vela
        # (5,190,236) NO APARECÍA. La vela no estaba en la imagen.
        #
        # 🔑 Y ese es el punto: esos "2,7 puntos que cuestan los fibs" eran en
        # buena parte el generador haciendo láminas donde la vela no se ve, y
        # cobrándole al extractor no leer lo que no está. Es exactamente el
        # error que ya se cometió con la zona translúcida y que está anotado
        # arriba. Un banco que dibuja lo imposible mide mentiras.
        # ⚠️ La altura del racimo se sortea UNA vez, fuera del bucle, y los
        #    niveles guardan su proporción real de un fib.
        fy = rnd.randint(MARGEN_Y + 40, AL - MARGEN_Y - 200)
        alto = rnd.randint(120, 260)
        fc = (rnd.randint(120, 220), rnd.randint(20, 80), rnd.randint(20, 80))
        for frac in (0.0, .25, .5, .62, .705, .79, 1.0):
            d.line([(rnd.randint(0, AN // 2), int(fy + frac * alto)),
                    (AN, int(fy + frac * alto))], fill=fc)

    # basura ENCIMA: niveles, una discontinua y un par de etiquetas
    for _ in range(rnd.randint(3, 6)):
        yy = rnd.randint(MARGEN_Y, AL - MARGEN_Y)
        d.line([(0, yy), (AN, yy)],
               fill=(rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)))
    yy = rnd.randint(MARGEN_Y, AL - MARGEN_Y)
    for xx in range(0, AN, 14):
        d.line([(xx, yy), (xx + 7, yy)], fill=t['rejilla'])
    for _ in range(rnd.randint(1, 2)):
        ex, ey = rnd.randint(MARGEN_X, AN - 160), rnd.randint(MARGEN_Y, AL - 120)
        d.rectangle([ex, ey, ex + rnd.randint(34, 60), ey + 14],
                    fill=(rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)))
    im.save(ruta)
    return {'tema': t, 'velas': verdad, 'ohlc': usadas,
            'py': (y0, p0, y1, p1)}


# ══════════════════════════════════════════════════════════════════════════
# Eslabón B — medir el extenso, sabiendo solo la columna
# ══════════════════════════════════════════════════════════════════════════

def _color_cuerpo(a, x0, x1, ct, cb):
    """Color más repetido dentro del cuerpo — para decidir alcista/bajista."""
    reg = a[ct:cb + 1, x0:x1 + 1].reshape(-1, 3)
    if not len(reg):
        return (0, 0, 0)
    pl = reg[:, 0] * 65536 + reg[:, 1] * 256 + reg[:, 2]
    v, n = np.unique(pl, return_counts=True)
    c = int(v[n.argmax()])
    return (c >> 16, (c >> 8) & 255, c & 255)


def mide(ruta, columnas, guias=None, banda=None):
    """De columnas a velas medidas, EN DOS PASADAS.

    🔑 La segunda pasada existe por un defecto que solo apareció sobre la
    captura real: dos velas pegadas al borde vertical de la banda de killzone
    se midieron de 425 px cuando la mediana del gráfico era 70 — se habían
    enganchado al borde. La altura creíble de una vela no es un número fijo,
    depende del gráfico, así que se mide primero todo, se toma la MEDIANA y se
    vuelven a medir las que se disparan, prohibiéndoles pasar de 3 veces esa
    mediana. El propio gráfico dice cuál es su escala."""
    prim = _mide1(ruta, columnas, guias, banda)
    alturas = [v['min'] - v['max'] for v in prim if v]
    if len(alturas) < 5:
        return prim
    tope = int(round(TOPE_ALTO * np.median(alturas)))
    sospechosas = [i for i, v in enumerate(prim)
                   if v and (v['min'] - v['max']) > tope]
    if not sospechosas:
        return prim
    seg = _mide1(ruta, columnas, guias, banda, tope)
    for i in sospechosas:
        if seg[i]:
            prim[i] = seg[i]
    return prim


def _mide1(ruta, columnas, guias=None, banda=None, tope=None):
    a = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
    H, W, _ = a.shape
    if banda:
        Y0, Y1 = banda
    else:
        Y0, Y1 = 0, H
    # 🔑 Las columnas que NO son vela: ahí el fondo se puede LEER en vez de
    #    adivinarlo. Ver `afina_velas._fondo_de_los_huecos`.
    FCOL = AF.fondo_por_columna(a, Y0, Y1)
    CVELA = AF.colores_de_vela(a, Y0, Y1, FCOL)
    MLIN = AF.mascara_lineas(a, Y0, Y1, FCOL)
    import flechas as FL
    DIB = FL.mascara(a, (0, W), (Y0, Y1))
    out = []
    for i, (x0, x1) in enumerate(columnas):
        # ventana ~5× la vela. Medido (2026-09-05): con ×3 el extremo sale al
        # 94,3% y con ×5 al 96,2%; a partir de ahí no mejora. Cuanto más ancha,
        # más filas de fondo limpio entran en la paleta.
        margen = max(4, 2 * (x1 - x0 + 1))
        guia = guias[i] if guias else None
        r = AF.afina(a, x0, x1, Y0, Y1, margen, False, guia, tope, FCOL, CVELA,
                     None, MLIN, DIB)
        if r is None:
            out.append(None)
            continue
        alto, bajo, ct, cb, sx0, sx1 = r
        out.append({'x0': sx0, 'x1': sx1, 'max': alto, 'min': bajo,
                    'cuerpo_alto': ct, 'cuerpo_bajo': cb,
                    'color': _color_cuerpo(a, sx0, sx1, ct, cb)})
    return out


def _a_ohlc(velas):
    """Velas medidas → serie OHLC. El precio es -y: la escala real no hace
    falta, porque TODOS los hechos son comparaciones y una comparación no
    cambia al multiplicar por una constante positiva."""
    velas = AF.direccion([v for v in velas if v])
    out = []
    for v in velas:
        h, l = -v['max'], -v['min']
        if v['alcista']:
            o, c = -v['cuerpo_bajo'], -v['cuerpo_alto']
        else:
            o, c = -v['cuerpo_alto'], -v['cuerpo_bajo']
        out.append((o, h, l, c))
    return out, velas


def _verdad_ohlc(verdad):
    out = []
    for v in verdad['velas']:
        h, l = -v['max'], -v['min']
        if v['alcista']:
            o, c = -v['cuerpo_bajo'], -v['cuerpo_alto']
        else:
            o, c = -v['cuerpo_alto'], -v['cuerpo_bajo']
        out.append((o, h, l, c))
    return out


# ══════════════════════════════════════════════════════════════════════════
# Eslabón C — los hechos
# ══════════════════════════════════════════════════════════════════════════

FAMILIAS = ('fvg', 'bos', 'barrida', 'ob', 'estado', 'piscina', 'manip', 'acum')
NOMBRES = {'fvg': 'FVG', 'bos': 'BOS', 'barrida': 'barrida de liquidez',
           'ob': 'order block', 'estado': 'estado del FVG',
           'piscina': 'piscina BSL/SSL', 'manip': 'pierna de manipulacion',
           'acum': 'acumulacion', 'acum±1': 'acumulacion (±1 vela)',
           'acum~': 'acumulacion (zona, no puntas)'}


def _hechos(ohlc):
    """Conjunto de hechos como (familia, índice, tipo). Sin precios: lo que se
    compara es SI el hecho está y en QUÉ vela, no su valor exacto."""
    g = HG.fvgs(ohlc)
    s = set()
    for f in g:
        s.add(('fvg', f['i'], f['tipo']))
    for b in HG.bos(ohlc):
        s.add(('bos', b['i'], b['tipo']))
    for b in HG.barridas(ohlc):
        s.add(('barrida', b['i'], b['tipo']))
    for o in HG.order_blocks(ohlc, g):
        s.add(('ob', o['i'], o['tipo']))
    # Familias nuevas (2026-09-06). Se miden igual que las otras: se calculan
    # sobre la verdad y sobre lo medido, y se comparan. No hace falta que el
    # generador las dibuje a propósito — se DEDUCEN del OHLC, así que su
    # precisión es la del OHLC pasada por su definición.
    for e in HG.estado_fvgs(ohlc, g):
        s.add(('estado', e['i'], e['estado']))
    for x in HG.piscinas(ohlc):
        s.add(('piscina', x['i'], x['tipo']))
    for x in HG.manipulacion(ohlc):
        s.add(('manip', x['i'], x['tipo']))
    for x in HG.acumulacion(ohlc):
        s.add(('acum', x['i'], x['fin']))
    return s


def _f1(verdad, medido):
    if not verdad and not medido:
        return 1.0, 1.0
    ok = len(verdad & medido)
    prec = ok / float(len(medido)) if medido else 0.0
    exh = ok / float(len(verdad)) if verdad else 0.0
    return prec, exh


def _guias(verdad, rnd):
    """La PISTA vertical que da el modelo, imitada con su error real.

    🔴 Sin esto el banco mide una cadena que no existe. En la cadena de verdad
    el recuadro de Gemini viene SIEMPRE, y el extractor lo usa para saber cuál
    de los bloques de tinta de la franja es la vela. Medir sin pista es medir
    otro programa, y castiga por un caso —el borde de una caja de sesión
    cruzando la vela— que en la cadena real está resuelto.

    ⚠️ Pero la pista no puede ser la verdad, o el banco se estaría haciendo
    trampa. Se le mete el error MEDIDO sobre la captura real del dueño:
    3,5 px de mediana arriba, 8 px abajo, y de vez en cuando un fallo gordo de
    30-40 px, que también los hubo (3 de 14)."""
    out = []
    for v in verdad:
        gordo = rnd.random() < 0.20
        da = rnd.gauss(0, 30 if gordo else 5)
        db = rnd.gauss(0, 30 if gordo else 9)
        out.append((int(v['max'] + da), int(v['min'] + db)))
    return out


def _quita_velas(velas, fraccion, rnd):
    """Se le caen velas al azar, como se le caen al modelo.

    🔴 SIN ESTO EL BANCO MIDE UNA CADENA QUE NO EXISTE. `probar` le entregaba al
    extractor las columnas VERDADERAS de TODAS las velas, o sea que medía los
    eslabones B y C dando por perfecto el A. Y el A no es perfecto: sobre la
    captura real del OTE el modelo devolvió 88 columnas donde hay ~102.

    Las precisiones que se publicaron (BOS 99,8% · barrida 93,7% · FVG 86,8% ·
    OB 81,8%) valen SOLO si no falta ninguna vela. Con el 14% fuera, lo que más
    se cae es ENCONTRARLAS (BOS 88,0 → 77,1% · FVG 98,1 → 72,3%) y la precisión
    de FVG y order block, que pierden 20 puntos. Por eso ahora el banco quita
    velas por defecto y deja que la rejilla las recupere: así el número que sale
    es el de la cadena que de verdad se correría. Tabla entera en
    `rejilla_velas`."""
    idx = list(range(len(velas)))
    if not fraccion:
        return idx
    fuera = set(rnd.sample(idx, int(round(fraccion * len(idx)))))
    return [j for j in idx if j not in fuera]


def paso_real(v):
    """Paso entre velas de una lámina, sacado de su propia verdad."""
    ve = v['velas']
    return float(np.median([ve[j + 1]['x0'] - ve[j]['x0']
                            for j in range(len(ve) - 1)]))


def _empareja(cols_med, velas_verdad, paso):
    """índice de la lista medida → índice de la vela REAL que le corresponde.

    🔴 Es lo que permite puntuar con velas faltando. Sin esto, quitar una vela
    corre todos los índices siguientes y el banco puntúa mal cosas que están
    perfectamente bien."""
    centros = np.array([(c['x0'] + c['x1']) / 2.0 for c in velas_verdad])
    out = []
    for (x0, x1) in cols_med:
        cx = (x0 + x1) / 2.0
        j = int(np.argmin(np.abs(centros - cx)))
        out.append(j if abs(cx - centros[j]) <= paso / 2.0 else None)
    return out


def _traduce(hechos, mapa):
    """Hechos con índice de la lista medida → con índice de la vela real."""
    out = set()
    for fam, i, tipo in hechos:
        if not (0 <= i < len(mapa)) or mapa[i] is None:
            continue
        # 🔴 En `acum` el tercer campo NO es una etiqueta: es la vela donde
        #    TERMINA el tramo, o sea otro índice de la lista medida. Si se deja
        #    sin traducir, el hecho se compara contra la verdad con un final
        #    corrido tantas velas como se hayan perdido, y la familia sale con
        #    un 0% que no es suyo.
        if fam == 'acum':
            if not (0 <= tipo < len(mapa)) or mapa[tipo] is None:
                continue
            tipo = mapa[tipo]
        out.add((fam, mapa[i], tipo))
    return out


def probar(n_laminas, semilla, salida, tolerancia=1, con_guia=True,
           faltan=0.14, con_rejilla=True):
    if not os.path.isdir(salida):
        os.makedirs(salida)
    rnd = random.Random(semilla)
    tot = dict(velas=0, ext=0, cue=0, dir=0)
    prec_p, exh_p, prec_q, exh_q = [], [], [], []
    import collections
    por_familia = collections.defaultdict(lambda: [0, 0, 0])  # ok, dichos, reales
    recup = [0, 0]                                 # recuperadas, perdidas
    for i in range(n_laminas):
        ruta = os.path.join(salida, 'lam_%02d.png' % i)
        v = lamina(ruta, rnd, marca_de_agua=MARCA_AGUA[0],
                   verticales=VERTICALES[0], dibujos=DIBUJOS[0])
        vivos = _quita_velas(v['velas'], faltan, rnd)
        recup[1] += len(v['velas']) - len(vivos)
        vivas = [v['velas'][j] for j in vivos]
        cols = [(c['x0'], c['x1']) for c in vivas]
        gus = _guias(vivas, rnd) if con_guia else None

        if con_rejilla and gus:
            # la rejilla necesita las guías: es lo que le da la altura de una
            # columna añadida, interpolando entre sus dos vecinas
            a_img = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
            paso = paso_real(v)
            ys = [g[0] for g in gus] + [g[1] for g in gus]
            banda = (max(0, min(ys) - 40), min(a_img.shape[0], max(ys) + 40))
            cajas = [(c[0], c[1], g[0], g[1]) for c, g in zip(cols, gus)]
            cajas, nuevas = RV.completa(cajas, paso, a_img, banda)
            recup[0] += len(nuevas)
            cols = [(c[0], c[1]) for c in cajas]
            gus = [(c[2], c[3]) for c in cajas]

        med = mide(ruta, cols, gus)

        # 🔴 SE EMPAREJA POR POSICIÓN EN LA IMAGEN, NUNCA POR ÍNDICE. Si falta
        # una vela, la nº 40 de la lista medida NO es la nº 40 del gráfico:
        # todos los índices posteriores se corren y un BOS perfectamente
        # detectado contaría como fallo. Comparar por índice exagera el daño de
        # las velas que faltan y luego exagera la mejora de recuperarlas.
        vivos_med = [k for k, m in enumerate(med) if m]
        mapa = _empareja([cols[k] for k in vivos_med], v['velas'], paso_real(v))

        for k, j in zip(vivos_med, mapa):
            tot['velas'] += 1
            if j is None:
                continue
            m, real = med[k], v['velas'][j]
            if (abs(m['max'] - real['max']) <= tolerancia and
                    abs(m['min'] - real['min']) <= tolerancia):
                tot['ext'] += 1
            if (abs(m['cuerpo_alto'] - real['cuerpo_alto']) <= tolerancia and
                    abs(m['cuerpo_bajo'] - real['cuerpo_bajo']) <= tolerancia):
                tot['cue'] += 1

        ohlc_med, con_dir = _a_ohlc(med)
        for m, j in zip(con_dir, mapa):
            if j is not None and m.get('alcista') == v['velas'][j]['alcista']:
                tot['dir'] += 1

        h_precio = _hechos(v['ohlc'])              # verdad de PRECIO
        h_pixel = _hechos(_verdad_ohlc(v))         # verdad ya redondeada
        h_med = _traduce(_hechos(ohlc_med), mapa)
        p, e = _f1(h_precio, h_med); prec_p.append(p); exh_p.append(e)
        p, e = _f1(h_pixel, h_med); prec_q.append(p); exh_q.append(e)
        for fam in FAMILIAS:
            V = set(x for x in h_precio if x[0] == fam)
            M = set(x for x in h_med if x[0] == fam)
            fa = por_familia[fam]
            fa[0] += len(V & M); fa[1] += len(M); fa[2] += len(V)
        # 🔑 La acumulación es el ÚNICO hecho que no es una vela sino un TRAMO,
        #    y compararlo por igualdad exacta le exige acertar sus DOS puntas.
        #    Un trader no llama fallo a un lateral que empieza una vela antes.
        #    Se mide también con ±1 vela de holgura para saber cuánto del fallo
        #    es de verdad y cuánto es el listón.
        V = [x for x in h_precio if x[0] == 'acum']
        M = [x for x in h_med if x[0] == 'acum']
        ok = sum(1 for m in M if any(abs(m[1] - v[1]) <= 1 and
                                     abs(m[2] - v[2]) <= 1 for v in V))
        fa = por_familia['acum±1']
        fa[0] += ok; fa[1] += len(M); fa[2] += len(V)
        # ¿y cuando falla, se INVENTA un lateral o solo corre las puntas? Se
        # cuenta como acierto si el tramo dicho pisa a un tramo real en al
        # menos la mitad de sus velas. Es lo que decide si se puede decir
        # "aquí hubo acumulación" sin dar las velas exactas.
        ok = 0
        for m in M:
            for v in V:
                sol = min(m[2], v[2]) - max(m[1], v[1]) + 1
                if sol > 0 and sol >= 0.5 * (m[2] - m[1] + 1):
                    ok += 1
                    break
        fa = por_familia['acum~']
        fa[0] += ok; fa[1] += len(M); fa[2] += len(V)

    print('\n%d láminas · %d velas · temas, colores y basura al azar%s'
          % (n_laminas, tot['velas'],
             '' if con_guia else '  ·  SIN la pista de la IA'))
    print('─ ESLABÓN B · medir el extenso (tolerancia ±%d px)' % tolerancia)
    print('   máximo y mínimo exactos : %5.1f%%' % (100.0 * tot['ext'] / tot['velas']))
    print('   cuerpo exacto           : %5.1f%%' % (100.0 * tot['cue'] / tot['velas']))
    print('   alcista/bajista         : %5.1f%%' % (100.0 * tot['dir'] / tot['velas']))
    print('─ ESLABÓN C · los hechos (FVG · BOS · barrida · order block)')
    print('   contra la verdad de PRECIO  : acierta %5.1f%% · encuentra %5.1f%%'
          % (100 * np.mean(prec_p), 100 * np.mean(exh_p)))
    print('   contra la verdad EN PÍXELES : acierta %5.1f%% · encuentra %5.1f%%'
          % (100 * np.mean(prec_q), 100 * np.mean(exh_q)))
    print('   ── por familia (contra la verdad de PRECIO) ──')
    for fam in FAMILIAS + ('acum±1', 'acum~'):
        ok, dichos, reales = por_familia[fam]
        pa = 100.0 * ok / dichos if dichos else 0.0
        ea = 100.0 * ok / reales if reales else 0.0
        print('   %-20s acierta %5.1f%% · encuentra %5.1f%%   (%d reales)'
              % (NOMBRES[fam], pa, ea, reales))
    print('\n   "acierta" = de los hechos que dice, cuántos son ciertos.')
    print('   "encuentra" = de los hechos que hay, cuántos ve.')
    print('   Si la fila de PRECIO sale peor que la de PÍXELES, la diferencia')
    print('   es redondeo de la captura y no hay código que lo arregle.')
    return tot


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--laminas', type=int, default=24)
    ap.add_argument('--semilla', type=int, default=7)
    ap.add_argument('--tolerancia', type=int, default=1)
    ap.add_argument('--salida', default=os.path.join(RAIZ, 'out', 'banco_cadena'))
    ap.add_argument('--sin-guia', action='store_true',
                    help='mide sin la pista vertical del modelo, para ver '
                         'cuánto aporta ese eslabón')
    ap.add_argument('--faltan', type=float, default=0.14,
                    help='fracción de velas que el modelo NO devuelve. El 0,14 '
                         'por defecto es lo medido sobre la captura real '
                         '(88 columnas de ~102). Con 0 se mide la cadena '
                         'suponiendo el eslabón A perfecto, que es lo que '
                         'medía este banco antes y no es la realidad.')
    ap.add_argument('--sin-dibujos', action='store_true',
                    help='fabrica SIN dibujos del trader (flechas, fibs)')
    ap.add_argument('--sin-verticales', action='store_true',
                    help='fabrica SIN lineas verticales')
    ap.add_argument('--sin-marca', action='store_true',
                    help='fabrica SIN marcas de agua (la de antes del 09-sep)')
    ap.add_argument('--sin-rejilla', action='store_true',
                    help='no recupera las velas que faltan, para ver el daño '
                         'que hacen')
    a = ap.parse_args()
    MARCA_AGUA[0] = not a.sin_marca
    VERTICALES[0] = not a.sin_verticales
    DIBUJOS[0] = not a.sin_dibujos
    probar(a.laminas, a.semilla, a.salida, a.tolerancia, not a.sin_guia,
           a.faltan, not a.sin_rejilla)
