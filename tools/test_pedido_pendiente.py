# -*- coding: utf-8 -*-
"""Comprar el plan X teniendo un pedido a medias del plan Y.

    python3 tools/test_pedido_pendiente.py

Por qué existe: el dueño abandonó a medias una compra de Premium, volvió al
sitio a comprar Standard, y el sitio le cobró y le activó el PREMIUM. El
carrito decía una cosa y la pasarela cobró otra. La causa no tenía nada que
ver con el sandbox de PayPal: `checkout_create` devolvía el pedido pendiente
FUERA CUAL FUERA el plan que se acabara de pedir.

Lo que se comprueba aquí es tanto el arreglo (pedir otra cosa suelta el
intento viejo) como lo que NO debe cambiar: repetir la MISMA compra sigue
retomando el pedido que ya existe, en vez de apilar pendientes.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scalpel'))
import app as A  # noqa: E402

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


def usuario(nombre):
    u = A.User.query.filter_by(username=nombre).first()
    if u:
        A.KnownDevice.query.filter_by(user_id=u.id).delete()
        A.SaleBreakdown.query.filter_by(user_id=u.id).delete()
        A.PlanSubscription.query.filter_by(user_id=u.id).delete()
        A.Order.query.filter_by(user_id=u.id).delete()
        A.db.session.delete(u)
        A.db.session.commit()
    u = A.User(username=nombre, email=nombre + '@ej.com', plan='free')
    u.set_password(CLAVE)
    for c in ('email_verified', 'is_verified', 'verified'):
        if hasattr(u, c):
            setattr(u, c, True)
    A.db.session.add(u)
    A.db.session.commit()
    return u.id


def entrar(c, nombre):
    c.post('/login', data={'identifier': nombre, 'password': CLAVE},
           follow_redirects=True)


def pendientes(uid):
    return (A.Order.query.filter_by(user_id=uid, status='pending')
            .order_by(A.Order.id).all())


def main():
    global ok, fallos
    with A.app.app_context():
        A.db.create_all()
        uid = usuario('cli_pendiente')
        # Un riel de pago encendido pero SIN pasarela real: el manual. Así el
        # flujo llega hasta el final sin llamar a PayPal.
        A.USDT_ENABLED = True

    # ── 1 · el caso que reportó el dueño ──────────────────────────────────
    print('\n1 · dejar Premium a medias y volver a por Standard')
    with A.app.test_client() as c:
        entrar(c, 'cli_pendiente')
        c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                         'method': 'manual'})
        with A.app.app_context():
            p = pendientes(uid)
            check(len(p) == 1 and p[0].plan == 'premium',
                  'queda un pendiente de Premium (%s)'
                  % ([o.plan for o in p]))
            viejo = p[0].id
        c.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly',
                                         'method': 'manual'})
    with A.app.app_context():
        p = pendientes(uid)
        check(len(p) == 1, 'sigue habiendo UN solo pendiente (%d)' % len(p))
        check(p and p[0].plan == 'standard',
              '🔴 y es del plan que PIDIÓ: %s' % (p[0].plan if p else '—'))
        check(p and abs(p[0].final_price
                        - A.PLAN_PRICING['standard']['monthly']) < 0.005,
              'con el precio de Standard ($%.2f)'
              % (p[0].final_price if p else -1))
        anterior = A.db.session.get(A.Order, viejo)
        check(anterior.status == 'cancelled',
              'el intento de Premium queda cancelado (%s)' % anterior.status)
        nuevo = p[0].id if p else None

    # ── 2 · repetir la MISMA compra no apila pedidos ──────────────────────
    print('\n2 · volver a pulsar pagar por lo mismo')
    with A.app.test_client() as c:
        entrar(c, 'cli_pendiente')
        c.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly',
                                         'method': 'manual'})
    with A.app.app_context():
        p = pendientes(uid)
        check(len(p) == 1 and p[0].id == nuevo,
              'retoma el MISMO pedido, no crea otro (#%s)'
              % (p[0].id if p else '—'))

    # ── 3 · el cupón reservado se devuelve al soltar el pedido ────────────
    print('\n3 · el uso del cupón vuelve cuando el pedido se suelta')
    with A.app.app_context():
        for o in pendientes(uid):
            o.status = 'cancelled'
        A.PromoCode.query.filter(
            A.db.func.lower(A.PromoCode.code) == 'testcup').delete()
        A.db.session.commit()
        pc = A.PromoCode(code='TESTCUP', discount_pct=20, kind='promo',
                         valid_for='both', active=True, uses_count=0)
        A.db.session.add(pc)
        A.db.session.commit()
    with A.app.test_client() as c:
        entrar(c, 'cli_pendiente')
        c.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly',
                                         'promo_code': 'TESTCUP',
                                         'method': 'manual'})
        with A.app.app_context():
            pc = A.PromoCode.query.filter(
                A.db.func.lower(A.PromoCode.code) == 'testcup').first()
            check(pc.uses_count == 1, 'el cupón queda reservado (%d)' % pc.uses_count)
            p = pendientes(uid)
            check(p and p[0].promo_code and p[0].promo_code.lower() == 'testcup',
                  'el pedido lleva el cupón')
            check(p and p[0].final_price
                  < A.PLAN_PRICING['standard']['monthly'],
                  'y el precio con descuento ($%.2f)' % (p[0].final_price if p else -1))
        # cambia de plan → el pedido con cupón se suelta
        c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                         'method': 'manual'})
    with A.app.app_context():
        pc = A.PromoCode.query.filter(
            A.db.func.lower(A.PromoCode.code) == 'testcup').first()
        check(pc.uses_count == 0,
              'al soltarlo, el uso se devuelve (%d)' % pc.uses_count)
        p = pendientes(uid)
        check(len(p) == 1 and p[0].plan == 'premium',
              'y el pendiente es el nuevo, de Premium')

    # ── 4 · mismo plan pero AHORA con cupón: no se cobra el precio viejo ──
    print('\n4 · añadir un cupón a lo que ya estaba en el carrito')
    with A.app.app_context():
        for o in pendientes(uid):
            o.status = 'cancelled'
        A.db.session.commit()
    with A.app.test_client() as c:
        entrar(c, 'cli_pendiente')
        c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                         'method': 'manual'})
        c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                         'promo_code': 'TESTCUP',
                                         'method': 'manual'})
    with A.app.app_context():
        p = pendientes(uid)
        check(len(p) == 1, 'un solo pendiente (%d)' % len(p))
        check(p and p[0].promo_code and p[0].promo_code.lower() == 'testcup',
              'el pendiente lleva el cupón que acaba de escribir')
        check(p and p[0].final_price < A.PLAN_PRICING['premium']['monthly'],
              'y su precio es el descontado ($%.2f)' % (p[0].final_price if p else -1))

    # ── 5 · soltar un pedido corta su suscripción de PayPal ───────────────
    print('\n5 · el pedido suelto no deja una suscripción viva detrás')
    with A.app.app_context():
        p = pendientes(uid)
        sub = A.PlanSubscription(user_id=uid, provider='paypal', plan='premium',
                                 billing_cycle='monthly', price=p[0].final_price,
                                 status='pending', first_order_id=p[0].id)
        A.db.session.add(sub)
        A.db.session.commit()
        sid = sub.id
    with A.app.test_client() as c:
        entrar(c, 'cli_pendiente')
        c.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly',
                                         'method': 'manual'})
    with A.app.app_context():
        sub = A.db.session.get(A.PlanSubscription, sid)
        check(sub.status == 'cancelled',
              'la suscripción queda cancelada (%s)' % sub.status)
        check(sub.cancelled_at is not None, 'con su fecha de cancelación')

    # ── 6 · el ciclo también cuenta como "otra compra" ────────────────────
    print('\n6 · cambiar de ciclo')
    if 'annual' not in A.allowed_cycles():
        print('  (anuales apagados — no aplica)')
    else:
        with A.app.app_context():
            for o in pendientes(uid):
                o.status = 'cancelled'
            A.db.session.commit()
        with A.app.test_client() as c:
            entrar(c, 'cli_pendiente')
            c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                             'method': 'manual'})
            c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'annual',
                                             'method': 'manual'})
        with A.app.app_context():
            p = pendientes(uid)
            check(len(p) == 1 and p[0].billing_cycle == 'annual',
                  'el pendiente pasa a ser el anual')

    # ── 7 · el que se pagó hace un segundo NO se cancela ──────────────────
    print('\n7 · si el pendiente resulta estar pagado, no se suelta')
    with A.app.app_context():
        for o in pendientes(uid):
            o.status = 'cancelled'
        A.db.session.commit()
    with A.app.test_client() as c:
        entrar(c, 'cli_pendiente')
        c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                         'method': 'manual'})
        with A.app.app_context():
            o = pendientes(uid)[0]
            o.provider_ref = 'I-FALSA'      # como si ya estuviera en PayPal
            A.db.session.commit()
            oid = o.id

        # El comprador aprobó en PayPal y volvió al sitio antes de que llegara
        # el aviso. La reconciliación es la que se entera.
        original = A.__dict__['_reconcile_order']

        def finge(order):
            order.status = 'paid'
            order.paid_at = A.datetime.now(A.timezone.utc)
            A.db.session.commit()
            return True
        A._reconcile_order = finge
        try:
            c.post('/checkout/create', data={'plan': 'standard',
                                             'cycle': 'monthly',
                                             'method': 'manual'})
        finally:
            A._reconcile_order = original
    with A.app.app_context():
        o = A.db.session.get(A.Order, oid)
        check(o.status == 'paid',
              '🔴 el pedido pagado NO se cancela (%s)' % o.status)
        p = pendientes(uid)
        check(len(p) == 1 and p[0].plan == 'standard',
              'y la compra nueva sigue adelante por su cuenta')

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
