# -*- coding: utf-8 -*-
"""MARGINAL (el del acuerdo) vs RETROACTIVO (la propuesta del papá).

    venv/bin/python3 tools/compara_esquemas.py

El papá propuso: "si tiene 25 clientes activos, cobra 35% por LOS 25". El
acuerdo actual dice: cada cliente cobra el tramo en el que entró (los 24
primeros al 30%, el 25 al 35%).

Este script no opina: coge las constantes REALES del sitio (tramos, precios,
descuento de socio, comisión de PayPal, coste operativo, reserva) y calcula
las dos liquidaciones del día 15 sobre la misma cartera.

Todo sale de `app.py`; si mañana cambian los precios o los tramos, las tablas
cambian solas.
"""
from __future__ import print_function

import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DATABASE_URL',
                      'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'cmp.db'))
os.environ.setdefault('SECRET_KEY', 'comparar')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

try:
    import app as A
except Exception as e:                                    # pragma: no cover
    sys.exit('no se pudo cargar la app: %s%s' % (
        e, ('\n\n👉 Usa el intérprete del entorno:\n'
            '   venv/bin/python3 %s' % os.path.relpath(__file__, RAIZ))
        if 'No module named' in str(e) else ''))

DESC_SOCIO = 20          # el descuento perpetuo del código de creador
# Mezcla observada como razonable para una academia: 6 de cada 10 eligen el
# plan caro. Se puede cambiar aquí y todo se recalcula.
MEZCLA_PREMIUM = 0.6


def precio(plan):
    """Lo que paga de verdad un cliente traído por el socio (20% menos)."""
    return round(A.PLAN_PRICING[plan]['monthly'] * (1 - DESC_SOCIO / 100.0), 2)


def cartera(n):
    """n clientes con la mezcla de planes: [(plan, lo que paga), …]."""
    prem = int(round(n * MEZCLA_PREMIUM))
    return ([('premium', precio('premium'))] * prem
            + [('standard', precio('standard'))] * (n - prem))


def pct_marginal(i):
    """% del cliente que ocupa el puesto i (1-based)."""
    return A.partner_tier_pct(i)


def pct_retroactivo(n):
    """% que se aplica a TODOS cuando la cartera tiene n clientes."""
    return A.partner_tier_pct(n)


def liquidacion(n, retro):
    """Las cuentas del mes para una cartera de n clientes."""
    c = cartera(n)
    ingreso = sum(p for _, p in c)
    fees = sum(A.estimated_processor_fee(p) for _, p in c)
    op = sum(A.PLAN_OP_COST[pl]['monthly'] for pl, _ in c)
    reserva = sum(round(p * A.CHARGEBACK_RESERVE_PCT / 100.0, 2) for _, p in c)
    if retro:
        pc = pct_retroactivo(n)
        comision = sum(round(p * pc / 100.0, 2) for _, p in c)
        efectivo = pc
    else:
        comision = sum(round(p * pct_marginal(i + 1) / 100.0, 2)
                       for i, (_, p) in enumerate(c))
        efectivo = round(comision / ingreso * 100, 1) if ingreso else 0
    tuyo = ingreso - fees - op - comision
    return {'n': n, 'ingreso': ingreso, 'fees': fees, 'op': op,
            'comision': comision, 'efectivo': efectivo, 'tuyo': tuyo,
            'reserva': reserva, 'disponible': tuyo - reserva}


def money(x):
    return '$%s' % format(round(x, 2), ',.2f')


def tabla(ns):
    print('\n%-6s │ %-11s │ %-19s │ %-19s │ %s'
          % ('', '', '  MARGINAL (acuerdo)', ' RETROACTIVO (papá)', ''))
    print('%-6s │ %-11s │ %9s %9s │ %9s %9s │ %11s'
          % ('client', 'ingreso', 'comisión', '%efec', 'comisión', '%efec',
             'te cuesta'))
    print('─' * 88)
    for n in ns:
        m = liquidacion(n, retro=False)
        r = liquidacion(n, retro=True)
        dif = r['comision'] - m['comision']
        marca = '  ←' if n in (25, 75) else ''
        print('%-6d │ %11s │ %9s %8.1f%% │ %9s %8.1f%% │ %11s%s'
              % (n, money(m['ingreso']), money(m['comision']), m['efectivo'],
                 money(r['comision']), r['efectivo'], money(dif), marca))


def detalle(n):
    """La liquidación completa del día 15, lado a lado."""
    m = liquidacion(n, retro=False)
    r = liquidacion(n, retro=True)
    c = cartera(n)
    prem = sum(1 for pl, _ in c if pl == 'premium')
    print('\n\n╔══ LIQUIDACIÓN DEL DÍA 15 · %d clientes activos ══' % n)
    print('║  %d Premium a %s  +  %d Standard a %s   (ya con su 20%% de descuento)'
          % (prem, money(precio('premium')), n - prem, money(precio('standard'))))
    print('╠' + '─' * 62)
    filas = [
        ('Cobrado a los clientes', m['ingreso'], r['ingreso']),
        ('− Comisión de PayPal',  -m['fees'],   -r['fees']),
        ('− Coste operativo (IA, etc.)', -m['op'], -r['op']),
        ('− COMISIÓN DEL COLABORADOR', -m['comision'], -r['comision']),
    ]
    for et, a, b in filas:
        print('║ %-32s %12s  %12s' % (et, money(a), money(b)))
    print('╠' + '─' * 62)
    print('║ %-32s %12s  %12s' % ('= TE QUEDA', money(m['tuyo']), money(r['tuyo'])))
    print('║ %-32s %12s  %12s' % ('  (menos reserva 25%)',
                                money(-m['reserva']), money(-r['reserva'])))
    print('║ %-32s %12s  %12s' % ('= DISPONIBLE DE VERDAD',
                                money(m['disponible']), money(r['disponible'])))
    print('╚' + '─' * 62)
    print('   El colaborador cobra %s con el acuerdo · %s con la propuesta'
          % (money(m['comision']), money(r['comision'])))
    dif = r['comision'] - m['comision']
    if abs(dif) > 0.005:
        print('   Diferencia: %s al mes  (%s al año)' % (money(dif), money(dif * 12)))


def frontera(n_antes):
    """Qué aporta el cliente que cruza el umbral, en cada esquema."""
    n = n_antes + 1
    for retro, et in ((False, 'MARGINAL '), (True, 'RETROACT.')):
        a = liquidacion(n_antes, retro)
        b = liquidacion(n, retro)
        ingreso_extra = b['ingreso'] - a['ingreso']
        com_extra = b['comision'] - a['comision']
        tuyo_extra = b['tuyo'] - a['tuyo']
        print('   %s  cliente %d → +%s de ingreso, +%s de comisión, '
              'a ti %s%s'
              % (et, n, money(ingreso_extra), money(com_extra),
                 '+' if tuyo_extra >= 0 else '', money(tuyo_extra)))


def main():
    print('Constantes REALES del sitio')
    print('  tramos       : %s' % ' · '.join(
        'desde %d cliente%s → %d%%' % (t, 's' if t > 1 else '', p)
        for t, p in A.PARTNER_TIERS))
    print('  precios      : premium %s (lista $%s) · standard %s (lista $%s)'
          % (money(precio('premium')), A.PLAN_PRICING['premium']['monthly'],
             money(precio('standard')), A.PLAN_PRICING['standard']['monthly']))
    print('  PayPal       : %.1f%% + $%.2f por cobro'
          % (A.PAYPAL_FEE_PCT, A.PAYPAL_FEE_FIXED))
    print('  coste op.    : premium $%s/mes · standard $%s/mes'
          % (A.PLAN_OP_COST['premium']['monthly'],
             A.PLAN_OP_COST['standard']['monthly']))
    print('  reserva      : %d%% de cada cobro' % A.CHARGEBACK_RESERVE_PCT)
    print('  mezcla usada : %d%% premium / %d%% standard'
          % (MEZCLA_PREMIUM * 100, 100 - MEZCLA_PREMIUM * 100))

    print('\n\n══ 1 · LA COMISIÓN MES A MES, SEGÚN EL TAMAÑO DE SU CARTERA ══')
    tabla([5, 10, 24, 25, 30, 50, 74, 75, 100, 150])

    print('\n\n══ 2 · EL SALTO: qué aporta el cliente que CRUZA el umbral ══')
    print('\n  Del cliente 24 al 25 (umbral del 35%):')
    frontera(24)
    print('\n  Del cliente 74 al 75 (umbral del 40%):')
    frontera(74)

    for n in (24, 25, 75):
        detalle(n)

    print('\n\n══ 3 · EL AÑO COMPLETO, si crece de 10 a 100 clientes ══')
    print('  (un mes por cada tamaño de cartera, sumado)')
    curva = [10, 18, 25, 33, 41, 50, 58, 66, 74, 82, 91, 100]
    tm = sum(liquidacion(n, False)['comision'] for n in curva)
    tr = sum(liquidacion(n, True)['comision'] for n in curva)
    ym = sum(liquidacion(n, False)['tuyo'] for n in curva)
    yr = sum(liquidacion(n, True)['tuyo'] for n in curva)
    print('  colaborador cobra : %11s (acuerdo)   %11s (propuesta)'
          % (money(tm), money(tr)))
    print('  a ti te queda     : %11s (acuerdo)   %11s (propuesta)'
          % (money(ym), money(yr)))
    print('  DIFERENCIA EN EL AÑO: %s de tu bolsillo' % money(tr - tm))
    return 0


if __name__ == '__main__':
    sys.exit(main())
