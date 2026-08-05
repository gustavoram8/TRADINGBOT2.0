# -*- coding: utf-8 -*-
"""Bajar de plan se PROGRAMA: no se cobra hoy y no se pierden días.

    python3 tools/test_cambio_plan.py

Decisión del dueño (2026-08-05), después de plantearle las dos opciones:

  · Subir de plan → inmediato. Pagas hoy, empieza un mes nuevo, y los días que
    te quedaban del plan barato se pierden (se te avisa en el carrito).
  · Bajar de plan → programado. No pagas nada hoy, conservas lo que tienes
    hasta la fecha que ya pagaste, y ese día empieza el plan más barato.

La razón de fondo es la misma que la de los meses apilados: nadie paga dos
veces el mismo período. Cobrar $25 el día que bajas y tirar los 27 días de
Premium que quedaban significa pagar $75 por un mes de Standard — y además
contradecía la Sección 5 de los T&C, que promete acceso hasta el final del
período pagado.

Se apoya en el endpoint `revise` de PayPal, que aplica el plan nuevo a partir
del SIGUIENTE ciclo de cobro. Aquí PayPal va simulado.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scalpel'))
import app as A  # noqa: E402

ok = fallos = 0
CLAVE = 'Zx8!kQ2mLp7w'
revisiones = []


def check(cond, txt):
    global ok, fallos
    if cond:
        ok += 1
        print('  ok    ', txt)
    else:
        fallos += 1
        print('  FALLA ', txt)


def usuario(nombre, plan='premium'):
    u = A.User.query.filter_by(username=nombre).first()
    if u:
        for M in (A.KnownDevice, A.SaleBreakdown, A.PlanSubscription, A.Order):
            M.query.filter_by(user_id=u.id).delete()
        A.db.session.delete(u)
        A.db.session.commit()
    u = A.User(username=nombre, email=nombre + '@ej.com', plan=plan)
    u.set_password(CLAVE)
    for c in ('email_verified', 'is_verified', 'verified'):
        if hasattr(u, c):
            setattr(u, c, True)
    u.plan_cycle = 'monthly'
    u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=27)
    A.db.session.add(u)
    A.db.session.commit()
    return u.id


def suscripcion(uid, plan='premium', precio=50.0, dias=27):
    s = A.PlanSubscription(
        user_id=uid, provider='paypal', plan=plan, billing_cycle='monthly',
        price=precio, status='active', provider_ref='I-CAMBIO',
        activated_at=datetime.now(timezone.utc),
        next_billing_at=datetime.now(timezone.utc) + timedelta(days=dias))
    A.db.session.add(s)
    A.db.session.commit()
    return s.id


def cliente(nombre):
    c = A.app.test_client()
    c.post('/login', data={'identifier': nombre, 'password': CLAVE},
           follow_redirects=True)
    return c


def main():
    global revisiones
    real = A._paypal_sub_revise

    def finge_revisar(sub, nuevo, precio):
        revisiones.append((sub.id, sub.plan, nuevo, round(precio, 2)))
        return 'https://paypal.example/aprobar'
    A._paypal_sub_revise = finge_revisar
    try:
        with A.app.app_context():
            A.db.create_all()
            uid = usuario('cam_cliente')
            sid = suscripcion(uid)
            venc = A._aware(A.db.session.get(A.User, uid).plan_expires_at)

        # ── 1 · el carrito de bajar NO es un carrito ──────────────────────
        print('\n1 · un Premium abre "Cambiar a Standard"')
        c = cliente('cam_cliente')
        r = c.get('/checkout?plan=standard&cycle=monthly')
        cuerpo = r.get_data(as_text=True)
        check(r.status_code == 200, 'la pantalla abre (%s)' % r.status_code)
        check('swap.confirm' in cuerpo,
              '🔴 es la pantalla de CAMBIO, no la de pago')
        check('swap.nothing' in cuerpo, 'dice que hoy no se cobra nada')
        check('pcta' in cuerpo and '/account/switch-plan' in cuerpo,
              'y el botón programa el cambio')
        check('$25.00' in cuerpo, 'con el precio que pagará después')

        # ── 2 · programarlo ───────────────────────────────────────────────
        print('\n2 · lo programa')
        r = c.post('/account/switch-plan', data={'plan': 'standard'},
                   follow_redirects=False)
        check(r.status_code in (302, 303), 'se acepta (%s)' % r.status_code)
        check('paypal.example' in (r.headers.get('Location') or ''),
              'y manda a PayPal a aprobarlo')
        check(revisiones == [(sid, 'premium', 'standard', 25.0)],
              'se le pide a PayPal el plan nuevo al precio nuevo %s' % revisiones)
        with A.app.app_context():
            s = A.db.session.get(A.PlanSubscription, sid)
            u = A.db.session.get(A.User, uid)
            check(s.pending_plan == 'standard', 'queda anotado el cambio')
            check(abs((s.pending_price or 0) - 25.0) < 0.01, 'con su importe')
            check(u.plan == 'premium',
                  '🔴 SIGUE siendo Premium hoy (%s)' % u.plan)
            check(A._aware(u.plan_expires_at) == venc,
                  '🔴 y NO pierde ni un día (vence igual)')
            check(A.Order.query.filter_by(user_id=uid).count() == 0,
                  '🔴 no se creó ningún cobro (%d pedidos)'
                  % A.Order.query.filter_by(user_id=uid).count())

        # ── 3 · lo ve en Ajustes ──────────────────────────────────────────
        print('\n3 · Ajustes se lo cuenta')
        pag = cliente('cam_cliente').get('/settings').get_data(as_text=True)
        check('settings.switchTo' in pag, 'dice a qué plan cambia')
        check('settings.switchUndo' in pag, 'y ofrece cancelar el cambio')

        # ── 4 · llega el cobro del mes: ya es del plan nuevo ──────────────
        print('\n4 · llega la fecha y PayPal cobra')
        with A.app.app_context():
            s = A.db.session.get(A.PlanSubscription, sid)
            s.pending_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            A.db.session.commit()
            A._aplicar_cambio_si_toca(s, 25.0)
            s = A.db.session.get(A.PlanSubscription, sid)
            check(s.plan == 'standard', 'la suscripción pasa a Standard (%s)' % s.plan)
            check(abs(s.price - 25.0) < 0.01, 'y a $%.2f' % s.price)
            check(not s.pending_plan, 'sin cambio pendiente ya')
            orden = A._sub_cobro(s, 25.0, referencia='VENTA-CAMBIO')
            check(orden and orden.plan == 'standard' and orden.final_price == 25.0,
                  '🔴 el cobro es de Standard por $%.2f'
                  % (orden.final_price if orden else -1))
            u = A.db.session.get(A.User, uid)
            check(u.plan == 'standard', 'y la cuenta queda en Standard (%s)' % u.plan)
            d = (A._aware(u.plan_expires_at) - datetime.now(timezone.utc)).days
            check(29 <= d <= 30, 'con su mes completo (%d días)' % d)

        # ── 5 · deshacerlo antes de la fecha ──────────────────────────────
        print('\n5 · cancelar un cambio programado')
        with A.app.app_context():
            uid2 = usuario('cam_arrepentido')
            sid2 = suscripcion(uid2)
        c2 = cliente('cam_arrepentido')
        revisiones = []
        c2.post('/account/switch-plan', data={'plan': 'standard'})
        r = c2.post('/account/switch-plan/cancel', follow_redirects=False)
        check(r.status_code in (302, 303), 'se acepta (%s)' % r.status_code)
        check(len(revisiones) == 2 and revisiones[1][2] == 'premium',
              'se le pide a PayPal volver a Premium %s' % revisiones)
        with A.app.app_context():
            s = A.db.session.get(A.PlanSubscription, sid2)
            check(not s.pending_plan, 'no queda cambio pendiente')
            check(A.db.session.get(A.User, uid2).plan == 'premium',
                  'y sigue en Premium')

        # ── 6 · SUBIR de plan sigue siendo inmediato ──────────────────────
        print('\n6 · subir de plan no se programa')
        with A.app.app_context():
            uid3 = usuario('cam_sube', plan='standard')
            suscripcion(uid3, plan='standard', precio=25.0)
        c3 = cliente('cam_sube')
        cuerpo = c3.get('/checkout?plan=premium&cycle=monthly').get_data(as_text=True)
        check('swap.confirm' not in cuerpo, 'NO sale la pantalla de cambio')
        check('checkout.swapBody' in cuerpo,
              'sale el carrito normal, avisando de los días que pierde')

        # ── 7 · sin cobro automático detrás, al carrito de siempre ────────
        print('\n7 · un Premium sin suscripción (pagó en USDT)')
        with A.app.app_context():
            uid4 = usuario('cam_usdt')          # sin suscripción ninguna
        c4 = cliente('cam_usdt')
        cuerpo = c4.get('/checkout?plan=standard&cycle=monthly').get_data(as_text=True)
        check('swap.confirm' not in cuerpo,
              'no hay nada que reprogramar: carrito normal')
    finally:
        A._paypal_sub_revise = real

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
