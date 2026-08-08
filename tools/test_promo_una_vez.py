# -*- coding: utf-8 -*-
"""Una promoción general se canjea UNA vez por cuenta; la del socio, siempre.

El agujero que cierra: `max_uses` solo ponía un techo GLOBAL, así que la misma
persona podía gastar la promo de lanzamiento en Standard, darse de baja y
volver a gastarla en Premium — un descuento pensado para captarla una vez se
convertía en su tarifa recurrente por la puerta de atrás.
"""
import os
import sys

os.environ.setdefault('DATABASE_URL', 'sqlite://')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
from flask import g            # noqa: E402
import app as A                # noqa: E402

CL = 'Zx9!wQ4mNp2r'
ok = fallas = 0


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def cliente(nombre):
    c = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    c.post('/login', data={'identifier': nombre, 'password': CL})
    return c


with A.app.app_context():
    A.db.create_all()
    for n in ('ana', 'beto'):
        u = A.User(username=n, email=n + '@demo.invalid', plan='free',
                   email_verified=True)
        u.set_password(CL)
        A.db.session.add(u)
    A.db.session.add(A.PromoCode(code='LANZAMIENTO', discount_pct=20,
                                 kind='discount', max_uses=100))
    A.db.session.add(A.PromoCode(code='GABRIEL', discount_pct=20,
                                 kind='creator', creator_name='Gabriel'))
    A.db.session.commit()
    ANA = A.User.query.filter_by(username='ana').first().id

print('── el primer canje ──')
ca = cliente('ana')
r = ca.post('/checkout/create',
            data={'plan': 'standard', 'cycle': 'monthly', 'promo_code': 'LANZAMIENTO'})
with A.app.app_context():
    o = A.Order.query.filter_by(user_id=ANA).first()
    check('el descuento se aplica ($25 → $20)',
          o and abs(o.final_price - 20.0) < 0.01, o.final_price if o else None)
    ana = A.db.session.get(A.User, ANA)
    promo = A.PromoCode.query.filter_by(code='LANZAMIENTO').first()
    check('🔴 mientras NO paga, su carrito abandonado no le quema el código',
          not A.promo_ya_usado(promo, ana))
    _, _, err = A._promo_para_compra(ana, 'standard', 'monthly', 'LANZAMIENTO')
    check('...y al volver al día siguiente lo puede reaplicar',
          err is None, err)
    # ahora sí paga: a partir de aquí queda gastado
    o.status = 'paid'
    A.db.session.commit()

print('── el segundo intento, misma cuenta ──')
with A.app.app_context():
    promo = A.PromoCode.query.filter_by(code='LANZAMIENTO').first()
    ana = A.db.session.get(A.User, ANA)
    check('🔴 el sistema lo reconoce como ya usado',
          A.promo_ya_usado(promo, ana))
    _, _, err = A._promo_para_compra(ana, 'premium', 'monthly', 'LANZAMIENTO')
    check('y el decisor lo rechaza con "already_used"',
          err == 'already_used', err)

print('── OTRA cuenta sí puede usarlo ──')
with A.app.app_context():
    beto = A.User.query.filter_by(username='beto').first()
    check('a Beto no le afecta lo que gastó Ana',
          not A.promo_ya_usado(promo, beto))
    p, nuevo, err = A._promo_para_compra(beto, 'standard', 'monthly',
                                         'LANZAMIENTO')
    check('y se le aplica normal', p is not None and err is None, err)

print('── el código de SOCIO no se gasta nunca ──')
with A.app.app_context():
    soc = A.PromoCode.query.filter_by(code='GABRIEL').first()
    ana = A.db.session.get(A.User, ANA)
    check('🔴 nunca se marca como usado (su descuento es permanente)',
          not A.promo_ya_usado(soc, ana))
    A.db.session.add(A.Order(user_id=ANA, plan='premium',
                             billing_cycle='monthly', base_price=50.0,
                             final_price=40.0, promo_code='GABRIEL',
                             status='paid'))
    A.db.session.commit()
    check('...ni aunque ya tenga compras pagadas con él',
          not A.promo_ya_usado(soc, ana))

print('── un pedido cancelado nunca cuenta ──')
with A.app.app_context():
    beto = A.User.query.filter_by(username='beto').first()
    ob = A.Order(user_id=beto.id, plan='standard', billing_cycle='monthly',
                 base_price=25.0, final_price=20.0, promo_code='LANZAMIENTO',
                 status='cancelled')
    A.db.session.add(ob)
    A.db.session.commit()
    check('🔴 un pedido cancelado no le gasta el código',
          not A.promo_ya_usado(promo, beto))

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
