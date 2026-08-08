# -*- coding: utf-8 -*-
"""¿Qué le va a cobrar PayPal a ESTE cliente, y cuándo? Preguntándoselo a PayPal.

    cd /var/www/TRADINGBOT2.0 && venv/bin/python3 tools/check_suscripcion.py

Existe por una razón concreta: `check_subs.py` comprueba los PLANES (el molde),
y este comprueba una SUSCRIPCIÓN de verdad (lo que se le cobrará a una persona
con nombre y apellido). Son cosas distintas, y la que puede acabar en una queja
o en una disputa es la segunda.

🔑 Lo importante: **no hace falta que nadie pague ni apruebe nada.** PayPal
registra la suscripción con sus importes en el momento en que el comprador
llega a la pantalla de aprobación — antes de mover un dólar. Así que se puede
hacer que alguien empiece una compra con un cupón, que CIERRE la pantalla de
PayPal sin aprobar, y este archivo dirá exactamente qué tenía PayPal anotado:
cuánto el primer mes y cuánto cada renovación. Coste: cero.

Compara tres cosas que TIENEN que coincidir:
  · lo que el carrito le cobró (el pedido)      ↔ el 1er tramo de PayPal
  · lo que Ajustes le anuncia como renovación   ↔ el tramo recurrente de PayPal
  · que ese tramo recurrente sea mensual y sin fecha de fin

Uso:
    venv/bin/python3 tools/check_suscripcion.py              # las 5 últimas
    venv/bin/python3 tools/check_suscripcion.py gussytrades  # las de esa cuenta
    venv/bin/python3 tools/check_suscripcion.py I-ABC123     # una concreta
    venv/bin/python3 tools/check_suscripcion.py --todas

NO imprime credenciales.
"""
from __future__ import print_function

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_subs as CS          # noqa: E402  (token/api/leer_env ya resueltos)

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print('\n⛔ Falta SQLAlchemy en este intérprete de Python.\n'
          '   En el VPS este archivo se corre con el Python del entorno:\n\n'
          '       cd /var/www/TRADINGBOT2.0 && venv/bin/python3 '
          'tools/check_suscripcion.py\n')
    sys.exit(2)

ok = avisos = fallos = 0
LEIDAS = []          # las que PayPal sí reconoce, para el titular del final


def bien(t):
    global ok
    ok += 1
    print('     ✅ %s' % t)


def ojo(t):
    global avisos
    avisos += 1
    print('     ⚠️  %s' % t)


def mal(t):
    global fallos
    fallos += 1
    print('     ⛔ %s' % t)


def _dinero(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _tramos_de_paypal(data):
    """Los importes que PayPal tiene ANOTADOS para esta suscripción.

    Ojo: cuando la suscripción sobrescribe el precio (que es lo normal aquí,
    porque así viajan los descuentos), PayPal devuelve el plan ya sobrescrito
    dentro de la propia suscripción — o sea, esto NO es el precio del molde,
    es lo que se le va a cobrar a esta persona.
    """
    ciclos = ((data.get('plan') or {}).get('billing_cycles') or [])
    fuera = []
    for c in ciclos:
        freq = c.get('frequency') or {}
        precio = ((c.get('pricing_scheme') or {}).get('fixed_price') or {})
        fuera.append({
            'tenure': (c.get('tenure_type') or '').upper(),
            'unidad': (freq.get('interval_unit') or '').upper(),
            'cuenta': freq.get('interval_count'),
            'total': c.get('total_cycles'),
            'importe': _dinero(precio.get('value')),
            'moneda': precio.get('currency_code') or '',
        })
    return fuera


def filas(env, arg):
    """Las suscripciones a mirar, sacadas de la base del sitio."""
    url = (env.get('DATABASE_URL') or '').strip()
    if not url:
        url = 'sqlite:///' + os.path.join(RAIZ, 'scalpel', 'scalpel.db')
    if url.startswith('postgres://'):          # forma vieja que SQLAlchemy 2 no acepta
        url = url.replace('postgres://', 'postgresql://', 1)
    eng = create_engine(url)
    cond, params = 's.provider_ref IS NOT NULL', {}
    limite = 'LIMIT 5'
    if arg == '--todas':
        limite = ''
    elif arg:
        cond += ' AND u.username = :quien'
        params['quien'] = arg
        limite = ''
    # "user" y "order" son palabras reservadas en PostgreSQL: van entrecomilladas.
    sql = text(
        'SELECT s.id, s.provider_ref, s.plan, s.price, s.status, s.promo_code,'
        '       s.first_order_id, s.next_billing_at, u.username '
        'FROM plan_subscription s JOIN "user" u ON u.id = s.user_id '
        'WHERE %s ORDER BY s.id DESC %s' % (cond, limite))
    with eng.connect() as cx:
        subs = [dict(r._mapping) for r in cx.execute(sql, params)]
        for s in subs:
            s['pedido'] = None
            if s['first_order_id']:
                r = cx.execute(text('SELECT final_price, promo_code, plan, '
                                    'billing_cycle, status FROM "order" '
                                    'WHERE id = :i'),
                               {'i': s['first_order_id']}).first()
                if r:
                    s['pedido'] = dict(r._mapping)
    return subs


def revisa(base, tk, s):
    print('\n── suscripción #%s · %s · %s ' % (s['id'], s['username'],
                                               s['plan']) + '─' * 22)
    print('     PayPal id  : %s' % s['provider_ref'])
    code, data = CS.api(base, tk,
                        '/v1/billing/subscriptions/%s?fields=plan'
                        % s['provider_ref'])
    if code == 404:
        # 🔑 Un 404 NO es un problema: significa que para PayPal esa
        # suscripción no existe, o sea que jamás podrá ejecutar un cargo. Es lo
        # normal en un intento que el comprador abandonó en la pantalla de
        # aprobación, y en todo lo creado cuando la cuenta estaba en sandbox
        # (los ids no cruzan de un entorno al otro). Marcarlo como grave era
        # asustar por lo que precisamente NO puede cobrarle a nadie.
        if s['status'] in ('cancelled', 'expired'):
            print('     · PayPal ya no la conoce y de nuestro lado está '
                  'cerrada: no puede cobrar nada')
        else:
            ojo('PayPal no la conoce (nunca se aprobó, o se creó en sandbox): '
                'no puede cobrar, pero la ficha local sigue como "%s"'
                % s['status'])
        return
    if code >= 300:
        mal('PayPal no respondió por esta suscripción (HTTP %s)' % code)
        return
    estado = (data.get('status') or '?').upper()
    print('     estado     : %s%s' % (
        estado, '  (aún sin aprobar — no se ha cobrado nada)'
        if estado == 'APPROVAL_PENDING' else ''))
    prox = ((data.get('billing_info') or {}).get('next_billing_time') or '')
    if prox:
        print('     próx. cobro: %s' % prox)

    tramos = _tramos_de_paypal(data)
    if not tramos:
        mal('PayPal no devolvió los importes de esta suscripción')
        return
    for t in tramos:
        print('     tramo %-8s: $%s %s · %s×%s · ciclos=%s'
              % (t['tenure'] or '?', t['importe'], t['moneda'],
                 t['cuenta'], t['unidad'], t['total']))

    esperado_1 = _dinero((s['pedido'] or {}).get('final_price'))
    esperado_r = _dinero(s['price'])
    reg = [t for t in tramos if t['tenure'] == 'REGULAR']
    tri = [t for t in tramos if t['tenure'] == 'TRIAL']

    if len(tramos) == 1 and reg:
        # Formato viejo de un solo tramo: lo que se autorizó se cobra SIEMPRE.
        unico = reg[0]['importe']
        if esperado_r is not None and abs(unico - esperado_r) > 0.005:
            mal('🔴 se le cobrará $%s TODOS los meses, pero el sitio le anuncia '
                '$%s de renovación. Eso es cobrar algo distinto de lo dicho.'
                % (unico, esperado_r))
        else:
            ojo('abierta con el formato de UN tramo: $%s cada mes. Correcto si '
                'ese es su precio permanente (socio o sin descuento); MAL si el '
                'descuento era de una sola vez.' % unico)
    elif tri and reg:
        LEIDAS.append((s['id'], estado, tri[0]['importe'], reg[0]['importe']))
        if esperado_1 is not None and abs(tri[0]['importe'] - esperado_1) > 0.005:
            mal('🔴 el 1er mes: el carrito le cobró $%s y PayPal tiene anotado '
                '$%s' % (esperado_1, tri[0]['importe']))
        else:
            bien('1er mes: PayPal cobrará $%s, lo mismo que dijo el carrito'
                 % tri[0]['importe'])
        if esperado_r is not None and abs(reg[0]['importe'] - esperado_r) > 0.005:
            mal('🔴 la renovación: Ajustes le anuncia $%s y PayPal tiene anotado '
                '$%s — ESTE es el que acaba en disputa'
                % (esperado_r, reg[0]['importe']))
        else:
            bien('renovación: PayPal cobrará $%s, lo mismo que anuncia Ajustes'
                 % reg[0]['importe'])
        if tri[0]['total'] != 1:
            mal('el tramo del 1er mes dura %s ciclos, no 1: el descuento se '
                'repetiría' % tri[0]['total'])
        if reg[0]['unidad'] != 'MONTH' or reg[0]['cuenta'] != 1:
            mal('la renovación no es mensual (%s×%s)'
                % (reg[0]['cuenta'], reg[0]['unidad']))
        if reg[0]['total'] not in (0, None):
            ojo('la renovación se detiene tras %s ciclos' % reg[0]['total'])
    else:
        mal('estructura de tramos inesperada: %s'
            % ', '.join(t['tenure'] or '?' for t in tramos))

    if s['promo_code']:
        print('     cupón      : %s' % s['promo_code'])
    equivalente = {'ACTIVE': 'active', 'APPROVAL_PENDING': 'pending',
                   'CANCELLED': 'cancelled', 'SUSPENDED': 'suspended',
                   'EXPIRED': 'expired'}.get(estado, s['status'])
    if s['status'] != equivalente:
        if estado == 'APPROVAL_PENDING' and s['status'] == 'cancelled':
            # A propósito: una que nunca se aprobó no puede cobrar, así que se
            # cierra de nuestro lado sin esperar a PayPal (que la dejará
            # caducar por su cuenta). No es un descuadre que haya que vigilar.
            print('     · cerrada de nuestro lado por no haberse aprobado '
                  'nunca; PayPal la caduca sola')
        else:
            ojo('el sitio la tiene como "%s" y PayPal como "%s" — se '
                'sincroniza sola al siguiente aviso, pero anótalo'
                % (s['status'], estado))


def main():
    env = CS.leer_env()
    cid = env.get('PAYPAL_CLIENT_ID', '').strip()
    secret = env.get('PAYPAL_SECRET', '').strip()
    entorno = env.get('PAYPAL_ENV', 'live').strip().lower()
    base = ('https://api-m.sandbox.paypal.com' if entorno == 'sandbox'
            else 'https://api-m.paypal.com')
    if not (cid and secret):
        print('⛔ faltan PAYPAL_CLIENT_ID / PAYPAL_SECRET')
        return 1
    tk, err = CS.token(base, cid, secret)
    if not tk:
        print('⛔ las credenciales no autentican en %s (%s)'
              % (entorno, (err or '')[:80]))
        return 1

    arg = sys.argv[1] if len(sys.argv) > 1 else ''
    if arg.startswith('I-'):
        subs = [{'id': '?', 'provider_ref': arg, 'plan': '?', 'price': None,
                 'status': '?', 'promo_code': None, 'first_order_id': None,
                 'next_billing_at': None, 'username': '(por id)',
                 'pedido': None}]
    else:
        subs = filas(env, arg)

    print('\n══ suscripciones en %s ' % entorno.upper() + '═' * 34)
    if not subs:
        print('\n  (todavía no hay ninguna suscripción abierta)\n'
              '  Para crear una sin gastar dinero: que una cuenta empiece la '
              'compra\n  de un plan y CIERRE la pantalla de PayPal sin '
              'aprobar. La suscripción\n  queda registrada en PayPal y este '
              'archivo ya puede leerla.')
        return 0
    for s in subs:
        revisa(base, tk, s)

    print('\n══ RESUMEN ' + '═' * 49)
    for sid, estado, primero, recurrente in LEIDAS:
        print('  #%s · PayPal cobrará $%s el 1er mes y $%s/mes desde el 2º%s'
              % (sid, primero, recurrente,
                 '  (pendiente de aprobar)'
                 if estado == 'APPROVAL_PENDING' else ''))
    print('  %d bien · %d avisos · %d graves' % (ok, avisos, fallos))
    if not fallos:
        print('  Lo que PayPal tiene anotado coincide con lo que el sitio le '
              'dijo al cliente.')
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
