# -*- coding: utf-8 -*-
"""Los datos de la demo de Pre-Flight, sin tocar Flask ni ninguna base.

Vive aparte porque lo usan DOS scripts y tienen que producir exactamente los
mismos números: `demo_preflight.py` (que monta una base de usar y tirar para
auditar el panel) y `demo_a_mi_cuenta.py` (que los mete en una cuenta real
para poder mirarlos en pantalla). Si el generador estuviera duplicado, un día
darían resultados distintos y la comparación dejaría de valer.

🔑 EL GENERADOR SE DECLARA AQUÍ, ANTES DE MIRAR NADA. Cada proyecto tiene una
regla FIJA y un azar con semilla; los resultados no se eligen a mano:

  · ICT — SÍ hay señal:      P(ganar) = 0.34 + 0.055 · nº de confluencias, y
    "Barrida de liquidez" suma otro +0.10.
  · Wyckoff — NO hay señal:  P(ganar) = 0.50 siempre, marques lo que marques.
  · Chartismo — win rate bajo, R alto: P(ganar) = 0.38 fija, ganadoras a 3-5R.
"""
from __future__ import print_function

import datetime
import random

SEMILLA = 20260812
RIESGO = 200.0            # dólares arriesgados por trade, fijo

PROYECTOS = [
    {
        'nombre': 'ICT — NY AM',
        'conf': ['Kill zone NY AM', 'Barrida de liquidez', 'FVG H1',
                 'Order block M15', 'Estructura HTF a favor', 'Riesgo <= 1%'],
        'instrumentos': ['NQ', 'ES'],
        'n': 34,
        'base': 0.34, 'peso': 0.055, 'clave': 'Barrida de liquidez', 'extra': 0.10,
        'r_gana': (1.6, 2.8), 'r_pierde': (1.0, 1.0),
    },
    {
        'nombre': 'Wyckoff — Acumulación',
        'conf': ['Fase C identificada', 'Spring con volumen', 'Test seco',
                 'LPS confirmado', 'SOS previo', 'Volumen decreciente'],
        'instrumentos': ['XAUUSD', 'EURUSD'],
        'n': 30,
        'base': 0.50, 'peso': 0.0, 'clave': None, 'extra': 0.0,
        'r_gana': (1.4, 2.4), 'r_pierde': (1.0, 1.0),
    },
    {
        'nombre': 'Chartismo — Rupturas',
        'conf': ['Triángulo válido', 'Ruptura con volumen', 'Retest',
                 'Objetivo medido >= 2R', 'Sin noticias de alto impacto'],
        'instrumentos': ['BTCUSD', 'ES'],
        'n': 28,
        'base': 0.38, 'peso': 0.0, 'clave': None, 'extra': 0.0,
        'r_gana': (3.0, 5.0), 'r_pierde': (1.0, 1.0),
    },
]

# Proyectos de relleno para la prueba de estrés del layout: Premium permite 10
# pizarras, así que la comparación tiene que aguantar 10 columnas. Nombres
# largos a propósito.
RELLENO = [
    ('SMC — Londres continuación', ['CHoCH M5', 'OB refinado', 'Liquidez interna']),
    ('Elliott — Onda 3 en NASDAQ', ['Onda 2 respetada', 'Impulso confirmado', 'Fibo 1.618']),
    ('Armónicos — Gartley diario', ['Punto B 0.618', 'PRZ definida', 'Divergencia RSI']),
    ('Rangos asiáticos y su barrida', ['Rango limpio', 'Barrida del alto', 'Vuelta al 50%']),
    ('Noticias — NFP y CPI (alto impacto)', ['Sin posición previa', 'Segundo movimiento', 'Spread normal']),
    ('Reversión a la media en oro', ['Banda tocada', 'RSI extremo', 'Sin tendencia diaria']),
    ('Swing semanal — acciones USA', ['Cierre semanal a favor', 'Volumen creciente', 'Sector fuerte']),
]


def lista_proyectos(extra=0):
    """Los 3 de siempre, más `extra` de relleno para la prueba de estrés."""
    ps = [dict(p) for p in PROYECTOS]
    for nombre, conf in RELLENO[:extra]:
        ps.append({'nombre': nombre, 'conf': conf, 'instrumentos': ['NQ', 'EURUSD'],
                   'n': 22, 'base': 0.45, 'peso': 0.02, 'clave': None, 'extra': 0.0,
                   'r_gana': (1.5, 3.0), 'r_pierde': (1.0, 1.0)})
    return ps


def genera(extra=0, hasta=None):
    """Devuelve [(proyecto, config, [trades…], resumen)] con la misma semilla.

    `hasta` es la fecha del último trade posible; por defecto, hoy. Los trades
    salen hacia atrás desde ahí para que en pantalla se vean recientes.
    """
    proyectos = lista_proyectos(extra)
    rnd = random.Random(SEMILLA)
    fin = hasta or datetime.date.today()
    salida = []
    for p in proyectos:
        cfg = {'confluences': [{'id': 'c%d' % (i + 1), 'label': l}
                               for i, l in enumerate(p['conf'])],
               'min_go': len(p['conf']) - 1,
               'min_caution': len(p['conf']) // 2 + 1}
        trades = []
        ganados = perdidos = saltados = 0
        pnl_total = 0.0
        # se sortean primero los días, hacia atrás desde `fin`
        d = fin
        dias = []
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

            # un trader disciplinado casi no toma los no-go
            tomado = True
            if verdict == 'no-go':
                tomado = rnd.random() < 0.25
            elif verdict == 'caution':
                tomado = rnd.random() < 0.65

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
                'checklist_name': p['nombre'], 'checked': marcadas,
                'total': len(p['conf']), 'verdict': verdict,
                'trade_date': dias[i], 'instrument': instrumento,
                'direction': direccion, 'entry_price': entrada,
                'exit_price': salida_p, 'rr': rr, 'position_size': tam,
                'pnl': pnl, 'outcome': resultado,
            })
        salida.append((p, cfg, trades, {
            'proyecto': p['nombre'], 'registrados': p['n'],
            'ganados': ganados, 'perdidos': perdidos, 'no_tomados': saltados,
            'pnl': round(pnl_total, 2),
            'win_rate_real': (round(100.0 * ganados / (ganados + perdidos), 1)
                              if (ganados + perdidos) else None),
        }))
    return salida
