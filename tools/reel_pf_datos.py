# -*- coding: utf-8 -*-
"""Los datos del reel de Pre-Flight. El generador se declara ANTES de mirar.

Existe aparte de `pf_demo_datos.py` a propósito: aquel es la prueba con la que
se AUDITÓ el panel y sus resultados están citados en el código y en las notas;
tocarlo para que un reel quede bonito invalidaría la auditoría.

🔑 QUÉ CAMBIA Y QUÉ NO, respecto al de la auditoría:

  · NO cambia el modelo de probabilidad. Cada proyecto conserva su regla:
      - ICT — SÍ hay señal:      P = 0.32 + 0.055 · nº de confluencias, y
        "Barrida de liquidez" suma otro +0.10.
      - Wyckoff — NO hay señal:  P = 0.50 siempre, marques lo que marques.
        Se queda a propósito: en la comparación del reel se ve un proyecto que
        NO funciona. Un panel que solo enseña ganadores no lo cree nadie.
      - Chartismo — win rate bajo, R alto: P = 0.38, ganadoras a 3-5R.
  · SÍ cambia CUÁNTOS trades toma el trader contra su propio veredicto:

        TOMA = {'go': 1.00, 'caution': 0.85, 'no-go': 0.55}

    En la auditoría era 1.00 / 0.65 / 0.25 — un trader disciplinado. Aquí el
    personaje es el contrario, y es el personaje del que trata el reel: el que
    se salta su lista. 🔴 Esa cifra es una propiedad del TRADER, no del
    resultado: la probabilidad de ganar de cada trade sigue saliendo del mismo
    modelo. Lo que cambia es cuántos de esos trades llegan a existir.

    Sin este cambio el reel no se puede hacer con verdad: con 0.25 el panel
    escribía `33% (3)` en el tramo NO-GO — el propio panel avisa de que tres
    trades no son una muestra, y montar un titular encima de tres trades sería
    justo lo que el panel fue rediseñado para NO hacer (regla MIN_MUESTRA=10).

  · Volumen mayor (90/70/60 = 220 trades sobre ~7 meses, unos 2 al día) para
    que los tramos pasen del listón de muestra por sí solos. Con este volumen
    se enciende además `pf.sConf`, que exige 10 trades A CADA LADO.

🔴 LO QUE SE MIDIÓ ANTES DE ESCRIBIR EL GUION, y por qué el titular no es el
   que se propuso primero ("tu win rate cuando NO seguiste tu plan"):

     con 5 semillas distintas × 3 proyectos = 15 casos, la escalera limpia
     GO > CAUTION > NO-GO salió en 3. CAUTION es el tramo más flaco y baila.

   O sea: para enseñar una escalera bonita habría que ir probando semillas
   hasta que saliera, que es exactamente lo que el panel fue rediseñado para
   NO hacer. Lo que SÍ aguanta las 5 semillas es (a) el hueco GO vs NO-GO en
   el proyecto que sí tiene ventaja, (b) la adherencia ~50% y (c) que Wyckoff
   —el proyecto sin señal— no ordena nada. El guion se apoya solo en eso.

⚠️ Lo que salga, sale. Este archivo no elige resultados; los reporta
   `tools/reel_pf_datos.py --ver`.
"""
from __future__ import print_function

import datetime
import random

SEMILLA = 20260820
RIESGO = 200.0

TOMA = {'go': 1.00, 'caution': 0.85, 'no-go': 0.55}

PROYECTOS = [
    {
        'nombre': 'ICT — NY AM',
        'conf': ['Kill zone NY AM', 'Barrida de liquidez', 'FVG H1',
                 'Order block M15', 'Estructura HTF a favor', 'Riesgo <= 1%'],
        'instrumentos': ['NQ', 'ES'],
        'n': 90,
        'base': 0.32, 'peso': 0.055, 'clave': 'Barrida de liquidez', 'extra': 0.10,
        'r_gana': (1.6, 2.8),
    },
    {
        'nombre': 'Wyckoff — Acumulación',
        'conf': ['Fase C identificada', 'Spring con volumen', 'Test seco',
                 'LPS confirmado', 'SOS previo', 'Volumen decreciente'],
        'instrumentos': ['XAUUSD', 'EURUSD'],
        'n': 70,
        'base': 0.50, 'peso': 0.0, 'clave': None, 'extra': 0.0,
        'r_gana': (1.4, 2.4),
    },
    {
        'nombre': 'Chartismo — Rupturas',
        'conf': ['Triángulo válido', 'Ruptura con volumen', 'Retest',
                 'Objetivo medido >= 2R', 'Sin noticias de alto impacto'],
        'instrumentos': ['BTCUSD', 'ES'],
        'n': 60,
        'base': 0.38, 'peso': 0.0, 'clave': None, 'extra': 0.0,
        'r_gana': (3.0, 5.0),
    },
]

# El reel se monta en español (es el idioma del guion aprobado), pero el mismo
# generador tiene que poder servir una versión en inglés sin mover un número:
# se traducen SOLO las cadenas, nunca el orden ni la cantidad.
EN = {
    'ICT — NY AM': 'ICT — NY AM',
    'Wyckoff — Acumulación': 'Wyckoff — Accumulation',
    'Chartismo — Rupturas': 'Chart patterns — Breakouts',
    'Kill zone NY AM': 'NY AM kill zone', 'Barrida de liquidez': 'Liquidity swept',
    'FVG H1': 'H1 FVG', 'Order block M15': 'M15 order block',
    'Estructura HTF a favor': 'HTF structure aligned', 'Riesgo <= 1%': 'Risk <= 1%',
    'Fase C identificada': 'Phase C identified', 'Spring con volumen': 'Spring on volume',
    'Test seco': 'Dry test', 'LPS confirmado': 'LPS confirmed', 'SOS previo': 'Prior SOS',
    'Volumen decreciente': 'Volume drying up',
    'Triángulo válido': 'Valid triangle', 'Ruptura con volumen': 'Break on volume',
    'Retest': 'Retest', 'Objetivo medido >= 2R': 'Measured target >= 2R',
    'Sin noticias de alto impacto': 'No high-impact news',
}


def genera(idioma='es', hasta=None):
    """[(proyecto, config, [trades…], resumen)] — mismo azar, misma semilla."""
    tr = (lambda s: EN.get(s, s)) if idioma == 'en' else (lambda s: s)
    rnd = random.Random(SEMILLA)
    fin = hasta or datetime.date.today()
    salida = []
    for p in PROYECTOS:
        cfg = {'confluences': [{'id': 'c%d' % (i + 1), 'label': tr(l)}
                               for i, l in enumerate(p['conf'])],
               'min_go': len(p['conf']) - 1,
               'min_caution': len(p['conf']) // 2 + 1}
        trades = []
        ganados = perdidos = saltados = 0
        pnl_total = 0.0
        d, dias = fin, []
        for _ in range(p['n']):
            d = d - datetime.timedelta(days=rnd.randint(1, 3))
            while d.weekday() >= 5:
                d = d - datetime.timedelta(days=1)
            dias.append(d)
        dias.reverse()

        for i in range(p['n']):
            k = rnd.randint(2, len(p['conf']))
            marcadas = rnd.sample(p['conf'], k)
            verdict = ('go' if k >= cfg['min_go']
                       else 'caution' if k >= cfg['min_caution'] else 'no-go')
            pg = p['base'] + p['peso'] * k
            if p['clave'] and p['clave'] in marcadas:
                pg += p['extra']
            pg = max(0.05, min(0.95, pg))

            tomado = rnd.random() < TOMA[verdict]
            gana = rnd.random() < pg
            rr = round(rnd.uniform(*p['r_gana']), 1)
            instrumento = rnd.choice(p['instrumentos'])
            direccion = 'long' if rnd.random() < 0.55 else 'short'
            entrada = round(rnd.uniform(100, 20000), 2)
            tam = rnd.choice([1, 2, 3])
            if tomado:
                if gana:
                    pnl = round(RIESGO * rr, 2)
                    ganados += 1
                else:
                    pnl = -round(RIESGO * rnd.uniform(0.85, 1.05), 2)
                    perdidos += 1
                pnl_total += pnl
                salida_p = round(entrada * (1 + (0.004 if gana else -0.002) *
                                            (1 if direccion == 'long' else -1)), 2)
                resultado = 'win' if gana else 'loss'
            else:
                saltados += 1
                pnl, salida_p, resultado = None, None, 'skipped'

            trades.append({
                'checklist_name': tr(p['nombre']), 'checked': [tr(m) for m in marcadas],
                'total': len(p['conf']), 'verdict': verdict,
                'trade_date': dias[i], 'instrument': instrumento,
                'direction': direccion, 'entry_price': entrada,
                'exit_price': salida_p, 'rr': rr, 'position_size': tam,
                'pnl': pnl, 'outcome': resultado,
            })
        salida.append(({'nombre': tr(p['nombre'])}, cfg, trades, {
            'proyecto': tr(p['nombre']), 'registrados': p['n'],
            'ganados': ganados, 'perdidos': perdidos, 'no_tomados': saltados,
            'pnl': round(pnl_total, 2),
        }))
    return salida


def _informe():
    """Lo que el panel va a escribir, calculado igual que `computeStats`."""
    from collections import Counter
    glob_t, glob_w = Counter(), Counter()
    for p, cfg, trades, res in genera():
        dec = [t for t in trades if t['outcome'] in ('win', 'loss')]
        print('\n%s  ·  %d registrados · %d decididos · %d no tomados'
              % (res['proyecto'], len(trades), len(dec), res['no_tomados']))
        tramos = []
        for v in ('go', 'caution', 'no-go'):
            sub = [t for t in dec if t['verdict'] == v]
            w = len([t for t in sub if t['outcome'] == 'win'])
            glob_t[v] += len(sub)
            glob_w[v] += w
            tramos.append('%s (%d)' % (('%.1f%%' % (100.0 * w / len(sub))) if sub else '—',
                                       len(sub)))
        print('   veredicto : %s' % ' · '.join(tramos))
        go = [t for t in dec if t['verdict'] == 'go']
        print('   adherencia: %.1f%% (%d/%d)'
              % (100.0 * len(go) / len(dec), len(go), len(dec)))
        print('   GOs falsos: %.1f%% (%d)'
              % (100.0 * len([t for t in go if t['outcome'] == 'loss']) / len(go), len(go)))
        conrr = [t for t in dec if t['rr']]
        expr = sum((t['rr'] if t['outcome'] == 'win' else -1) for t in conrr) / len(conrr)
        print('   expectativa: %+.2fR (%d)   ·   P&L %.2f' % (expr, len(conrr), res['pnl']))
    print('\nGLOBAL veredicto: %s' % ' · '.join(
        '%.1f%% (%d)' % (100.0 * glob_w[v] / glob_t[v], glob_t[v])
        for v in ('go', 'caution', 'no-go')))


if __name__ == '__main__':
    _informe()
