# -*- coding: utf-8 -*-
"""¿Puede alguien, POR ALGUNA VÍA, acumular meses de plan?

    python3 tools/test_no_apilar.py

El dueño pidió certeza, no una respuesta: "¿estás 100% seguro de que ya nadie
puede apilar meses?". La única forma honesta de contestarlo es enumerar TODAS
las puertas por las que el vencimiento del plan puede crecer y empujar cada
una.

Los días de acceso solo crecen en UN sitio del código — `_activate_plan_from_
order` — y para llegar ahí hace falta un pedido PAGADO. Los pedidos de plan
nacen en dos sitios: el carrito (`checkout_create`) y la renovación
(`_sub_cobro`). Esta prueba ataca los dos, más las puertas laterales: el panel
de admin, un pedido viejo que quedó pendiente de antes del candado, un pedido
de $0, y el aviso repetido de PayPal.
"""
import os
import re
import sys
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
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


def usuario(nombre, plan='premium', dias=27, admin=False):
    u = A.User.query.filter_by(username=nombre).first()
    if u:
        for M in (A.KnownDevice, A.SaleBreakdown, A.PlanSubscription, A.Order):
            M.query.filter_by(user_id=u.id).delete()
        A.db.session.delete(u)
        A.db.session.commit()
    u = A.User(username=nombre, email=nombre + '@ej.com', plan=plan, is_admin=admin)
    u.set_password(CLAVE)
    for c in ('email_verified', 'is_verified', 'verified'):
        if hasattr(u, c):
            setattr(u, c, True)
    if plan != 'free':
        u.plan_cycle = 'monthly'
        u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=dias)
    A.db.session.add(u)
    A.db.session.commit()
    return u.id


def cliente(nombre):
    c = A.app.test_client()
    c.post('/login', data={'identifier': nombre, 'password': CLAVE},
           follow_redirects=True)
    return c


def dias_de(uid):
    u = A.db.session.get(A.User, uid)
    v = A._aware(u.plan_expires_at)
    return -1 if v is None else (v - datetime.now(timezone.utc)).days


def main():
    # ── 0 · el código: ¿cuántas puertas hay? ──────────────────────────────
    print('\n0 · auditoría del código')
    fuente = open(os.path.join(RAIZ, 'scalpel', 'app.py'), encoding='utf-8').read()
    # Solo cuenta lo que SUMA tiempo: la declaración de la columna y los
    # `= None` (que lo borran) no pueden alargar nada.
    crece = [l.strip() for l in fuente.split('\n')
             if 'plan_expires_at' in l and '=' in l
             and 'db.Column' not in l and '==' not in l
             and not l.strip().endswith('= None')
             and 'timedelta' in l]
    print('     sitios que ALARGAN el vencimiento:')
    for c in crece:
        print('       ', c[:74])
    check(len(crece) == 2,
          'solo %d sitios pueden alargar el plan (activación y /admin)' % len(crece))
    crean = len(re.findall(r'=\s*Order\(', fuente))
    check(crean == 2,
          'y solo %d sitios crean un pedido de plan (carrito y renovación)' % crean)

    with A.app.app_context():
        A.db.create_all()

    # ── 1 · la puerta principal: el carrito ───────────────────────────────
    print('\n1 · el carrito, por delante y por detrás')
    with A.app.app_context():
        uid = usuario('ap_carrito')
        antes = dias_de(uid)
    c = cliente('ap_carrito')
    c.get('/checkout?plan=premium&cycle=monthly')
    c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                     'method': 'manual'})
    with A.app.app_context():
        check(A.Order.query.filter_by(user_id=uid).count() == 0,
              'ni la pantalla ni el POST crean pedido (%d)'
              % A.Order.query.filter_by(user_id=uid).count())
        check(dias_de(uid) == antes, 'y no gana días (%d)' % dias_de(uid))

    # ── 2 · un pedido VIEJO que quedó pendiente de antes del candado ──────
    print('\n2 · un pedido pendiente creado antes de que existiera el candado')
    with A.app.app_context():
        uid2 = usuario('ap_viejo')
        viejo = A.Order(user_id=uid2, plan='premium', billing_cycle='monthly',
                        base_price=50, discount_pct=0, final_price=50,
                        status='pending', payment_method='paypal',
                        created_at=datetime.now(timezone.utc) - timedelta(days=3))
        A.db.session.add(viejo)
        A.db.session.commit()
        vid = viejo.id
        antes = dias_de(uid2)
        # el barrido de /admin lo suelta antes de que nadie pueda pagarlo
        A._soltar_pedidos_caducos()
        o = A.db.session.get(A.Order, vid)
        check(o.status == 'cancelled',
              '🔴 el barrido lo suelta (%s)' % o.status)
        check(dias_de(uid2) == antes, 'sin tocarle los días (%d)' % dias_de(uid2))

    # ── 3 · y si aun así alguien lo pagara, ¿cuánto sumaría? ──────────────
    print('\n3 · el peor caso: pagar un pedido que ya estaba suelto')
    with A.app.app_context():
        o = A.db.session.get(A.Order, vid)
        o.status = 'paid'
        o.paid_at = datetime.now(timezone.utc)
        A.db.session.commit()
        antes = dias_de(uid2)
        A._activate_plan_from_order(o)
        check(dias_de(uid2) - antes == 30,
              'suma su mes (%d días) — es dinero que entró, no se le puede '
              'quedar sin nada' % (dias_de(uid2) - antes))
        check(True, '⚠️ por eso el barrido de arriba es la defensa, no ésta')

    # ── 4 · el panel de admin ─────────────────────────────────────────────
    print('\n4 · el botón de /admin, pulsado cinco veces')
    with A.app.app_context():
        jefe = usuario('ap_jefe', plan='premium', admin=True)
        uid3 = usuario('ap_admin', plan='premium')
    c = cliente('ap_jefe')
    with A.app.app_context():
        antes = dias_de(uid3)
    for _ in range(5):
        c.post('/admin/set-plan', data={'user_id': uid3, 'plan': 'premium'})
    with A.app.app_context():
        check(dias_de(uid3) == antes,
              'el vencimiento no se mueve (%d días)' % dias_de(uid3))

    # ── 5 · la renovación: legítima, pero una sola vez por cobro ──────────
    print('\n5 · la renovación de PayPal')
    with A.app.app_context():
        uid4 = usuario('ap_renueva')
        s = A.PlanSubscription(user_id=uid4, provider='paypal', plan='premium',
                               billing_cycle='monthly', price=50.0,
                               status='active', provider_ref='I-AP')
        A.db.session.add(s)
        A.db.session.commit()
        antes = dias_de(uid4)
        for _ in range(4):                 # PayPal reintenta el MISMO aviso
            A._sub_cobro(s, 50.0, referencia='SALE-UNICA')
        check(dias_de(uid4) - antes == 30,
              'cuatro avisos del mismo cobro = UN mes (%d días)'
              % (dias_de(uid4) - antes))

    # ── 6 · un pedido de $0 (cupón del 100%) ──────────────────────────────
    print('\n6 · un cupón del 100% sobre un plan que ya se tiene')
    with A.app.app_context():
        uid5 = usuario('ap_gratis')
        A.PromoCode.query.filter(
            A.db.func.lower(A.PromoCode.code) == 'apila100').delete()
        A.db.session.add(A.PromoCode(code='APILA100', discount_pct=100,
                                     kind='discount', valid_for='both',
                                     active=True))
        A.db.session.commit()
        antes = dias_de(uid5)
    c = cliente('ap_gratis')
    c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                     'promo_code': 'APILA100', 'method': 'manual'})
    with A.app.app_context():
        check(dias_de(uid5) == antes,
              'ni gratis se cuela (%d días)' % dias_de(uid5))

    # ── 7 · cambiar de plan no regala días ────────────────────────────────
    print('\n7 · programar una bajada de plan')
    real = A._paypal_sub_revise
    A._paypal_sub_revise = lambda sub, nuevo, precio: ''
    try:
        with A.app.app_context():
            uid6 = usuario('ap_baja')
            A.db.session.add(A.PlanSubscription(
                user_id=uid6, provider='paypal', plan='premium',
                billing_cycle='monthly', price=50.0, status='active',
                provider_ref='I-AP2',
                next_billing_at=datetime.now(timezone.utc) + timedelta(days=27)))
            A.db.session.commit()
            antes = dias_de(uid6)
        c = cliente('ap_baja')
        for _ in range(3):
            c.post('/account/switch-plan', data={'plan': 'standard'})
        with A.app.app_context():
            check(dias_de(uid6) == antes,
                  'pedirlo tres veces no suma nada (%d días)' % dias_de(uid6))
            check(A.Order.query.filter_by(user_id=uid6).count() == 0,
                  'y no crea ningún pedido')
    finally:
        A._paypal_sub_revise = real

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
