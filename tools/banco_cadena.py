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
y **etiquetas** de texto. Un método que solo funciona con velas verdes y rojas
sobre fondo negro no sirve para nada: los clientes usan lo que les da la gana.

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
from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

import afina_velas as AF          # noqa: E402
import hechos_grafico as HG       # noqa: E402

AN, AL = 1400, 800
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


def _serie(n, rnd):
    p, out = 100.0, []
    for _ in range(n):
        o = p
        c = o + rnd.uniform(-2.4, 2.4)
        h = max(o, c) + rnd.uniform(0.02, 1.7)
        l = min(o, c) - rnd.uniform(0.02, 1.7)
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


def lamina(ruta, rnd, n=60):
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


def mide(ruta, columnas, guias=None):
    """De columnas a velas medidas. `columnas` = [(x0,x1)]."""
    a = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
    H, W, _ = a.shape
    out = []
    for i, (x0, x1) in enumerate(columnas):
        # ventana ~5× la vela. Medido (2026-09-05): con ×3 el extremo sale al
        # 94,3% y con ×5 al 96,2%; a partir de ahí no mejora. Cuanto más ancha,
        # más filas de fondo limpio entran en la paleta.
        margen = max(4, 2 * (x1 - x0 + 1))
        guia = guias[i] if guias else None
        r = AF.afina(a, x0, x1, 0, H, margen, False, guia)
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
    from lee_grafico import _direccion
    velas = _direccion([v for v in velas if v])
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


def probar(n_laminas, semilla, salida, tolerancia=1, con_guia=True):
    if not os.path.isdir(salida):
        os.makedirs(salida)
    rnd = random.Random(semilla)
    tot = dict(velas=0, ext=0, cue=0, dir=0)
    prec_p, exh_p, prec_q, exh_q = [], [], [], []
    import collections
    por_familia = collections.defaultdict(lambda: [0, 0, 0])  # ok, dichos, reales
    for i in range(n_laminas):
        ruta = os.path.join(salida, 'lam_%02d.png' % i)
        v = lamina(ruta, rnd)
        cols = [(c['x0'], c['x1']) for c in v['velas']]
        med = mide(ruta, cols, _guias(v['velas'], rnd) if con_guia else None)

        for real, m in zip(v['velas'], med):
            tot['velas'] += 1
            if m is None:
                continue
            if (abs(m['max'] - real['max']) <= tolerancia and
                    abs(m['min'] - real['min']) <= tolerancia):
                tot['ext'] += 1
            if (abs(m['cuerpo_alto'] - real['cuerpo_alto']) <= tolerancia and
                    abs(m['cuerpo_bajo'] - real['cuerpo_bajo']) <= tolerancia):
                tot['cue'] += 1

        ohlc_med, con_dir = _a_ohlc(med)
        for real, m in zip(v['velas'], con_dir):
            if m.get('alcista') == real['alcista']:
                tot['dir'] += 1

        h_precio = _hechos(v['ohlc'])              # verdad de PRECIO
        h_pixel = _hechos(_verdad_ohlc(v))         # verdad ya redondeada
        h_med = _hechos(ohlc_med)
        p, e = _f1(h_precio, h_med); prec_p.append(p); exh_p.append(e)
        p, e = _f1(h_pixel, h_med); prec_q.append(p); exh_q.append(e)
        for fam in ('fvg', 'bos', 'barrida', 'ob'):
            V = set(x for x in h_precio if x[0] == fam)
            M = set(x for x in h_med if x[0] == fam)
            fa = por_familia[fam]
            fa[0] += len(V & M); fa[1] += len(M); fa[2] += len(V)

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
    nombres = {'fvg': 'FVG', 'bos': 'BOS', 'barrida': 'barrida de liquidez',
               'ob': 'order block'}
    for fam in ('fvg', 'bos', 'barrida', 'ob'):
        ok, dichos, reales = por_familia[fam]
        pa = 100.0 * ok / dichos if dichos else 0.0
        ea = 100.0 * ok / reales if reales else 0.0
        print('   %-20s acierta %5.1f%% · encuentra %5.1f%%   (%d reales)'
              % (nombres[fam], pa, ea, reales))
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
    a = ap.parse_args()
    probar(a.laminas, a.semilla, a.salida, a.tolerancia, not a.sin_guia)
