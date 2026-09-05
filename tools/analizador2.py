# -*- coding: utf-8 -*-
"""ANALIZADOR 2.0 — la cadena entera, de una captura a HECHOS VERIFICADOS.

    # completo, en el VPS (necesita la clave):
    python3 tools/analizador2.py --imagen docs/capturas_prueba/mnq_5m_zoom.png \\
        --modelo gemini:gemini-flash-latest
    # sin red, con columnas ya obtenidas (para probar el resto de la cadena):
    python3 tools/analizador2.py --imagen ... --columnas 760-767:503-525,...

🔴 NO TOCA EL ANALIZADOR DEL SITIO. Vive en tools/, la app no lo importa, y no
   sustituye a nada. Produce un BLOQUE DE HECHOS; qué se hace con él es una
   decisión del dueño, y hasta que la tome no se enchufa a ninguna parte.

═══ QUÉ ES ESTO Y QUÉ NO ═══
NO es una IA que mira un gráfico y opina. Es una cadena donde **cada eslabón
hace solo lo que sabe hacer**, medido:

  1. `recorta_grafico`  encuentra el panel y el paso entre velas   (píxeles)
  2. `cajas_ia`         dice EN QUÉ COLUMNA está cada vela         (modelo)
  3. `afina_velas`      mide máximo, mínimo y cuerpo de cada una   (píxeles)
  4. `afina_velas`      decide alcista/bajista sin conocer paleta  (píxeles)
  5. `eje_precio`       convierte altura en precio                 (modelo + píxeles)
  6. `hechos_grafico`   deduce BOS, barridas, FVG y order blocks   (aritmética)

🔑 **EL PATRÓN QUE SE REPITIÓ CUATRO VECES, y que gobierna este diseño:** el
modelo **lee y reconoce muy bien, y sitúa mal**. Falló al dar el borde de la
vela (3-8 px de mediana, con casos de 30), al separar velas en una imagen ancha
(cada caja se comía 2-3), y al colocar las etiquetas del eje (177 px). Las tres
veces la solución fue la misma: **que el modelo diga QUÉ y aproximadamente
DÓNDE, y que los píxeles digan EXACTAMENTE dónde.** Aquí no se le pide nunca
una medida ni una comparación.

═══ QUÉ SE AFIRMA Y QUÉ NO ═══
Cada familia de hechos lleva su precisión MEDIDA (banco de 24 láminas, 1.436
velas). Solo entran en el bloque las que pasan de `MIN_PRECISION`, porque el
propósito de todo esto es **no mentirle a un cliente**:
  BOS 99,8% ✅ · barrida 93,7% ✅ · FVG 86,8% 🔴 · order block 81,8% 🔴
Las que no pasan se calculan igual y se enseñan aparte, marcadas, para poder
seguir midiéndolas — pero NO se afirman.

⚠️ Y si el eje no da consenso, el bloque sale **sin precios**: dirá "cerró por
debajo del swing" en vez de inventarse una cifra.
"""
from __future__ import print_function

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

import afina_velas as AF          # noqa: E402
import eje_precio as EP           # noqa: E402
import hechos_grafico as HG       # noqa: E402
import recorta_grafico as RG      # noqa: E402

# Precisión mínima MEDIDA para que una familia de hechos se pueda AFIRMAR.
MIN_PRECISION = 90.0
PRECISION = {'bos': 99.8, 'barrida': 93.7, 'fvg': 86.8, 'ob': 81.8}
NOMBRE = {'bos': 'BOS', 'barrida': 'barrida de liquidez',
          'fvg': 'FVG', 'ob': 'order block'}
# Cuántas velas de giro a cada lado para que un extremo cuente como swing.
# Con k=2 el mismo tramo produce demasiados swings menores y los BOS se
# multiplican; con k=3 el primer evento coincidió con la marca del indicador
# del dueño. Ver CLAUDE.md.
K_SWING = 3
# Una vela no puede medir más de esto por la mediana de su propio gráfico.
TOPE_ALTO = 3.0


def _columnas_del_modelo(ruta, prov, modelo, max_velas, callback=None):
    """Llama al modelo una vez por tira y junta las columnas.

    ⚠️ Las tiras se SOLAPAN a propósito, así que la misma vela sale en dos.
    Se juntan por posición: dos cajas cuyo centro dista menos de medio paso son
    la misma vela. Sin esto, la vela de la costura entraría dos veces y todos
    los índices posteriores quedarían corridos."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'ci', os.path.join(RAIZ, 'tools', 'cajas_ia.py'))
    ci = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ci)
    im = Image.open(ruta)
    W, H = im.size
    p = RG.panel(ruta)
    if not p:
        raise SystemExit('no se encontró un panel de velas en esa imagen.')
    clave = ci._clave(prov)
    carpeta = os.path.join(RAIZ, 'out', 'analizador2')
    if not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    todas = []
    tiras = RG.tiras(ruta, max_velas)
    for i, (x0, y0, x1, y1) in enumerate(tiras):
        if callback:
            callback(i + 1, len(tiras), (x0, y0, x1, y1))
        parte = os.path.join(carpeta, '_tira_%d.png' % i)
        im.crop((x0, y0, x1, y1)).save(parte)
        txt = ci._pregunta(prov, modelo, clave, parte, todas=True)
        for c in ci._cajas(txt):
            ym, xm, yM, xM = c
            px0 = x0 + xm / 1000.0 * (x1 - x0)
            px1 = x0 + xM / 1000.0 * (x1 - x0)
            py0 = y0 + ym / 1000.0 * (y1 - y0)
            py1 = y0 + yM / 1000.0 * (y1 - y0)
            if px1 < px0:
                px0, px1 = px1, px0
            if py1 < py0:
                py0, py1 = py1, py0
            todas.append((int(round(px0)), int(round(px1)),
                          int(round(py0)), int(round(py1))))
    return _junta(todas, p['paso']), p


def _junta(cajas, paso):
    """Una caja por vela: se funden las que caen en la misma columna."""
    cajas = sorted(cajas, key=lambda c: (c[0] + c[1]) / 2.0)
    out = []
    for c in cajas:
        cx = (c[0] + c[1]) / 2.0
        if out and abs(cx - (out[-1][0] + out[-1][1]) / 2.0) < paso / 2.0:
            a = out[-1]
            out[-1] = (min(a[0], c[0]), max(a[1], c[1]),
                       min(a[2], c[2]), max(a[3], c[3]))
        else:
            out.append(c)
    return out


def banda_de_las_guias(cajas, H):
    """La franja vertical donde de verdad hay gráfico, sacada de las guías.

    🔴 POR QUÉ NO SE MIDE SOBRE LA IMAGEN ENTERA (cazado al encadenar, 2026-09-05).
    `afina` calcula la paleta de fondos con las filas de su ventana. Si en la
    ventana entran la barra de herramientas de arriba y el eje de tiempo de
    abajo —llenos de texto e iconos—, esos colores desplazan a los fondos de
    verdad fuera de la paleta y la medición cambia. Medido sobre la captura del
    dueño: con la imagen entera el BOS validado contra su indicador (x=886)
    DESAPARECÍA y salían otros tres; con la franja del gráfico vuelve a salir.

    🔑 La franja no se adivina ni se fija a mano: la dicen las guías del modelo,
    que ya sabemos dónde caen. Se les da un margen ANCHO (dos veces la altura
    típica de una vela) para que no puedan recortar ninguna: el error de la guía
    es de 3-8 px de mediana y 30-40 en el peor caso, muy por debajo del margen.

    ⚠️ Esto es solo para MEDIR. Lo que se le manda al modelo sigue yendo con
    toda la altura: recortar ahí sí cortaría velas."""
    if not cajas:
        return 0, H
    alto = np.median([c[3] - c[2] for c in cajas])
    margen = max(40, int(2 * alto))
    y0 = max(0, int(min(c[2] for c in cajas)) - margen)
    y1 = min(H, int(max(c[3] for c in cajas)) + margen)
    return y0, y1


def mide(ruta, cajas):
    """De columnas a velas medidas, EN DOS PASADAS.

    🔑 La segunda pasada nació de la captura real: dos velas pegadas al borde
    vertical de la banda de killzone se midieron de 425 px con una mediana de
    70 — se habían enganchado al borde. La altura creíble de una vela no es un
    número fijo: la dice el propio gráfico."""
    a = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
    H, W, _ = a.shape
    by0, by1 = banda_de_las_guias(cajas, H)

    def pasada(tope):
        out = []
        for (x0, x1, gy0, gy1) in cajas:
            margen = max(4, 2 * (x1 - x0 + 1))
            r = AF.afina(a, x0, x1, by0, by1, margen, False, (gy0, gy1), tope)
            if r is None:
                out.append(None)
                continue
            alto, bajo, ct, cb, sx0, sx1 = r
            reg = a[ct:cb + 1, sx0:sx1 + 1].reshape(-1, 3)
            pl = reg[:, 0] * 65536 + reg[:, 1] * 256 + reg[:, 2]
            v, n = np.unique(pl, return_counts=True)
            col = int(v[n.argmax()])
            out.append({'x0': sx0, 'x1': sx1, 'max': alto, 'min': bajo,
                        'cuerpo_alto': ct, 'cuerpo_bajo': cb,
                        'color': (col >> 16, (col >> 8) & 255, col & 255)})
        return out

    prim = pasada(None)
    alturas = [v['min'] - v['max'] for v in prim if v]
    if len(alturas) >= 5:
        tope = int(round(TOPE_ALTO * np.median(alturas)))
        sosp = [i for i, v in enumerate(prim)
                if v and (v['min'] - v['max']) > tope]
        if sosp:
            seg = pasada(tope)
            for i in sosp:
                if seg[i]:
                    prim[i] = seg[i]
    return [v for v in prim if v]


def serie(velas):
    """Velas medidas → OHLC en unidades de -y.

    🔑 El precio no hace falta para deducir los hechos: TODOS son comparaciones,
    y una comparación no cambia al multiplicar por una constante positiva. La
    escala solo se usa para ESCRIBIR el resultado."""
    AF.direccion(velas)
    out = []
    for v in velas:
        h, l = -v['max'], -v['min']
        if v['alcista']:
            o, c = -v['cuerpo_bajo'], -v['cuerpo_alto']
        else:
            o, c = -v['cuerpo_alto'], -v['cuerpo_bajo']
        out.append((o, h, l, c))
    return out


def hechos(ohlc):
    """Los hechos, por familia, con el índice de la vela."""
    g = HG.fvgs(ohlc)
    out = {'bos': [], 'barrida': [], 'fvg': [], 'ob': []}
    for b in HG.bos_eventos(ohlc, K_SWING):
        out['bos'].append({'i': b['i'], 'tipo': b['tipo'],
                           'nivel': b['nivel'], 'swing': b['swing']})
    vistas = set()
    for b in HG.barridas(ohlc, K_SWING):
        if (b['swing'], b['tipo']) in vistas:
            continue
        vistas.add((b['swing'], b['tipo']))
        out['barrida'].append({'i': b['i'], 'tipo': b['tipo'],
                               'nivel': b['nivel'], 'swing': b['swing']})
    for f in g:
        out['fvg'].append({'i': f['i'], 'tipo': f['tipo'],
                           'suelo': f['suelo'], 'techo': f['techo']})
    for o in HG.order_blocks(ohlc, g):
        out['ob'].append({'i': o['i'], 'tipo': o['tipo'],
                          'suelo': o['suelo'], 'techo': o['techo']})
    return out


def _pre(valor, escala):
    """Un valor de la serie (-y) a precio, si hay escala."""
    if not escala:
        return None
    return escala['precio'](-valor)


def bloque(velas, hs, escala, minimo=MIN_PRECISION):
    """El BLOQUE DE HECHOS: lo único que se le entregaría a una IA.

    🔴 Solo entran las familias cuya precisión MEDIDA pasa el mínimo. Las demás
    se devuelven aparte y marcadas: se siguen calculando para poder medirlas,
    pero afirmarlas sería mentirle a un cliente una de cada cinco veces."""
    def linea(fam, h):
        x = velas[h['i']]['x0']
        n = 'vela %d (x=%d)' % (h['i'], x)
        if fam == 'bos':
            p = _pre(h['nivel'], escala)
            return ('%s · BOS %s: el CIERRE atravesó el swing de la vela %d%s'
                    % (n, h['tipo'], h['swing'],
                       '' if p is None else ' en %s' % _fmt(p)))
        if fam == 'barrida':
            p = _pre(h['nivel'], escala)
            return ('%s · barrida %s: la mecha pasó el swing de la vela %d%s '
                    'y el cuerpo cerró DENTRO — no es ruptura'
                    % (n, h['tipo'], h['swing'],
                       '' if p is None else ' en %s' % _fmt(p)))
        a, b = _pre(h['techo'], escala), _pre(h['suelo'], escala)
        etiqueta = 'FVG' if fam == 'fvg' else 'order block'
        return ('%s · %s %s%s' % (n, etiqueta, h['tipo'],
                '' if a is None else ' entre %s y %s' % (_fmt(b), _fmt(a))))

    firmes, marcados = [], []
    for fam in ('bos', 'barrida', 'fvg', 'ob'):
        destino = firmes if PRECISION[fam] >= minimo else marcados
        for h in hs[fam]:
            destino.append((fam, linea(fam, h)))
    return firmes, marcados


def _fmt(p):
    return ('%,.2f' % p).replace(',', '@').replace('.', ',').replace('@', '.')


def analiza(ruta, prov=None, modelo=None, cajas=None, max_velas=80,
            verboso=True):
    def aviso(i, n, r):
        if verboso:
            print('   tira %d/%d  %s' % (i, n, r))
    if cajas is None:
        if not (prov and modelo):
            raise SystemExit('hace falta --modelo, o --columnas ya obtenidas.')
        cajas, p = _columnas_del_modelo(ruta, prov, modelo, max_velas, aviso)
    else:
        p = RG.panel(ruta)
    velas = mide(ruta, cajas)
    if len(velas) < 5:
        raise SystemExit('solo se pudieron medir %d velas.' % len(velas))
    ohlc = serie(velas)
    escala = None
    if prov and modelo:
        try:
            et, _crudo = EP.lee(prov, modelo, ruta)
            escala = EP.ajusta(et)
        except SystemExit:
            escala = None
    return {'panel': p, 'velas': velas, 'ohlc': ohlc, 'escala': escala,
            'hechos': hechos(ohlc)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--imagen', required=True)
    ap.add_argument('--modelo', metavar='PROVEEDOR:MODELO')
    ap.add_argument('--columnas', help='x0-x1:y0-y1,... ya obtenidas, para '
                                       'probar la cadena sin llamar al modelo')
    ap.add_argument('--max-velas', type=int, default=80)
    ap.add_argument('--json', help='guarda el resultado completo ahí')
    a = ap.parse_args()
    prov = modelo = None
    if a.modelo:
        prov, _, modelo = a.modelo.partition(':')
    cajas = None
    if a.columnas:
        cajas = []
        for t in a.columnas.split(','):
            xs, _, ys = t.strip().partition(':')
            x0, _, x1 = xs.partition('-')
            y0, _, y1 = ys.partition('-')
            cajas.append((int(x0), int(x1), int(y0), int(y1)))

    r = analiza(a.imagen, prov, modelo, cajas, a.max_velas)
    p, velas, escala = r['panel'], r['velas'], r['escala']
    print('\npanel x %d-%d · paso %.2f px · %d velas medidas'
          % (p['x0'], p['x1'], p['paso'], len(velas)))
    if escala:
        print('escala del eje: %.4f puntos/px · %d de %d etiquetas de acuerdo'
              % (escala['por_px'], escala['apoyos'], escala['total']))
    else:
        print('🔴 sin escala fiable: el bloque sale SIN precios (correcto).')

    firmes, marcados = bloque(velas, r['hechos'], escala)
    print('\n═══ HECHOS VERIFICADOS (%d) ═══' % len(firmes))
    print('   familias que superan el %.0f%% de precisión medida: %s'
          % (MIN_PRECISION, ', '.join(
              NOMBRE[f] for f in PRECISION if PRECISION[f] >= MIN_PRECISION)))
    for _fam, l in firmes:
        print('   · ' + l)
    print('\n─── NO se afirman todavía (%d) ───' % len(marcados))
    for fam in ('fvg', 'ob'):
        if PRECISION[fam] < MIN_PRECISION:
            print('   %s: %.1f%% de precisión medida' % (NOMBRE[fam], PRECISION[fam]))
    for _fam, l in marcados:
        print('   · ' + l)
    if a.json:
        with open(a.json, 'w') as f:
            json.dump({'panel': p, 'escala': None if not escala else
                       {'por_px': escala['por_px'], 'base': escala['base'],
                        'apoyos': escala['apoyos'], 'total': escala['total']},
                       'velas': velas, 'hechos': r['hechos']}, f,
                      indent=1, default=float)
        print('\nguardado en', a.json)
