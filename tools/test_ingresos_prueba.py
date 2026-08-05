# -*- coding: utf-8 -*-
"""Los ensayos en sandbox no cuentan como ingresos.

    python3 tools/test_ingresos_prueba.py

El dueño: "en Revenue del panel admin sale que gané muchísimo dinero, imagino
que por las simulaciones; hay que dejar eso limpio porque no fueron ventas
reales". Y por otro lado: "¿por qué las compras de gussytrades nunca salieron
en el libro de ventas, es un bug?".

Las dos cosas tienen la misma raíz: la regla de "esto fue un ensayo" existía
SOLO en el libro de ventas (`record_sale_breakdown`), y el panel de ingresos
sumaba los pedidos sin mirar el entorno. Ahora decide un único sitio
(`es_pedido_de_prueba`) y el pedido queda SELLADO al pagarse — para que el día
que se pase a producción los ensayos de sandbox no se conviertan de golpe en
ingresos reales.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scalpel'))
import app as A  # noqa: E402


def revenue():
    """El contexto del panel. Necesita una petición viva porque lee el mes
    elegido de la query string, así que se le da una de mentira."""
    with A.app.test_request_context('/admin'):
        return A._build_revenue_context()

ok = fallos = 0
CLAVE = 'Zx8!kQ2mLp7w'


def check(cond, txt):
    global ok, fallos
    if cond:
        ok += 1
        print('  ok    ', txt)
    else:
        fallos += 1
        print('  FALLA ', txt)


def usuario(nombre, admin=False):
    u = A.User.query.filter_by(username=nombre).first()
    if u:
        for M in (A.KnownDevice, A.SaleBreakdown, A.PlanSubscription, A.Order):
            M.query.filter_by(user_id=u.id).delete()
        A.db.session.delete(u)
        A.db.session.commit()
    u = A.User(username=nombre, email=nombre + '@ej.com', plan='free',
               is_admin=admin)
    u.set_password(CLAVE)
    for c in ('email_verified', 'is_verified', 'verified'):
        if hasattr(u, c):
            setattr(u, c, True)
    A.db.session.add(u)
    A.db.session.commit()
    return u.id


def pagar(uid, plan='premium', metodo='paypal'):
    p = A.PLAN_PRICING[plan]['monthly']
    o = A.Order(user_id=uid, plan=plan, billing_cycle='monthly', base_price=p,
                discount_pct=0, final_price=p, status='paid',
                payment_method=metodo, paid_at=datetime.now(timezone.utc))
    A.db.session.add(o)
    A.db.session.commit()
    A._activate_plan_from_order(o)
    return o.id


def main():
    entorno = A.PAYPAL_ENV
    try:
        # ── 1 · en sandbox: se activa el plan, no cuenta como dinero ───────
        print('\n1 · una compra en SANDBOX')
        A.PAYPAL_ENV = 'sandbox'
        with A.app.app_context():
            A.db.create_all()
            A.Order.query.delete()
            A.SaleBreakdown.query.delete()
            A.db.session.commit()
            uid = usuario('ing_sandbox')
            oid = pagar(uid)
            o = A.db.session.get(A.Order, oid)
            check(o.is_test, '🔴 el pedido queda SELLADO como ensayo')
            check(A.db.session.get(A.User, uid).plan == 'premium',
                  'pero el plan SÍ se activa: se ensaya el circuito')
            check(A.SaleBreakdown.query.filter_by(order_id=oid).first() is None,
                  'y NO entra al libro de ventas (por eso nunca viste a '
                  'gussytrades ahí — no es un bug)')
            ctx = revenue()
            check(ctx['lifetime_total'] == 0.0,
                  '🔴 Revenue histórico se queda en $%.2f' % ctx['lifetime_total'])
            check(ctx['revenue_total'] == 0.0,
                  'y el del mes también ($%.2f)' % ctx['revenue_total'])
            check(ctx['pruebas_n'] == 1 and ctx['pruebas_total'] == 50.0,
                  'se avisa aparte: %d ensayo(s) por $%.2f'
                  % (ctx['pruebas_n'], ctx['pruebas_total']))

        # ── 2 · el sello NO se reescribe al pasar a producción ─────────────
        print('\n2 · el día que se pase a LIVE')
        A.PAYPAL_ENV = 'live'
        with A.app.app_context():
            ctx = revenue()
            check(ctx['lifetime_total'] == 0.0,
                  '🔴 los ensayos de ayer NO se vuelven ingresos ($%.2f)'
                  % ctx['lifetime_total'])
            o = A.db.session.get(A.Order, oid)
            check(o.is_test, 'siguen sellados como lo que fueron')

        # ── 3 · y una venta de verdad SÍ cuenta ────────────────────────────
        print('\n3 · una compra real, ya en producción')
        with A.app.app_context():
            uid2 = usuario('ing_real')
            oid2 = pagar(uid2)
            o2 = A.db.session.get(A.Order, oid2)
            check(not o2.is_test, 'no se marca como ensayo')
            ctx = revenue()
            check(ctx['lifetime_total'] == 50.0,
                  '🔴 y sí suma a Revenue ($%.2f)' % ctx['lifetime_total'])
            check(A.SaleBreakdown.query.filter_by(order_id=oid2).first() is not None,
                  'y entra al libro de ventas')
            check(ctx['pruebas_n'] == 1,
                  'el ensayo viejo sigue contado aparte, no mezclado')

        # ── 4 · USDT y los pagos a mano nunca son ensayos ──────────────────
        print('\n4 · un pago que no es de PayPal')
        A.PAYPAL_ENV = 'sandbox'
        with A.app.app_context():
            uid3 = usuario('ing_usdt')
            oid3 = pagar(uid3, metodo='usdt-binance')
            check(not A.db.session.get(A.Order, oid3).is_test,
                  'un pago en USDT cuenta aunque PayPal esté en sandbox')
    finally:
        A.PAYPAL_ENV = entorno

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
