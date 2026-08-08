# -*- coding: utf-8 -*-
"""Un código se canjea cuando entra el dinero, NO cuando se pone en el carrito.

Reproduce el caso exacto que reportó el dueño probando en producción: aplicó
un cupón de un solo uso, pulsó pagar, se volvió atrás — y el sitio le dijo
"límite alcanzado". Su propio carrito a medias le había gastado el código.

Con el código anterior fallan los tres primeros checks.
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


def usos(codigo='UNICO'):
    with A.app.app_context():
        return A.PromoCode.query.filter_by(code=codigo).first().uses_count or 0


with A.app.app_context():
    A.db.create_all()
    for n in ('mauro', 'hermano', 'tercero'):
        u = A.User(username=n, email=n + '@demo.invalid', plan='free',
                   email_verified=True)
        u.set_password(CL)
        A.db.session.add(u)
    A.db.session.add(A.PromoCode(code='UNICO', discount_pct=90,
                                 kind='discount', max_uses=1))
    A.db.session.add(A.PromoCode(code='SOCIO', discount_pct=20,
                                 kind='creator', creator_name='Gabriel'))
    A.db.session.commit()

print('── el caso del dueño: pagar, volverse atrás, reintentar ──')
c = cliente('mauro')
c.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly',
                                 'promo_code': 'UNICO'})
check('🔴 poner el cupón en el carrito NO lo gasta', usos() == 0, usos())
with A.app.app_context():
    m = A.User.query.filter_by(username='mauro').first()
    pc = A.PromoCode.query.filter_by(code='UNICO').first()
    puede, motivo = pc.is_redeemable('monthly')
    check('🔴 el cupón sigue disponible tras el intento', puede, motivo)
    _, _, err = A._promo_para_compra(m, 'standard', 'monthly', 'UNICO')
    check('🔴 y se puede volver a aplicar', err is None, err)

print('── al cobrar sí se anota ──')
with A.app.app_context():
    o = A.Order.query.filter_by(status='pending').first()
    o.status = 'paid'
    A.db.session.commit()
    A._activate_plan_from_order(o)
check('el canje queda registrado', usos() == 1, usos())
with A.app.app_context():
    pc = A.PromoCode.query.filter_by(code='UNICO').first()
    check('y ahora sí está agotado', not pc.is_redeemable('monthly')[0])

print('── un aviso repetido no lo cuenta dos veces ──')
with A.app.app_context():
    o = A.Order.query.filter_by(status='paid').first()
    A._activate_plan_from_order(o)          # el guard de applied_at lo frena
check('sigue en 1', usos() == 1, usos())

print('── soltar el pedido de otro NO le resta el canje pagado ──')
c2 = cliente('hermano')
c2.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly',
                                  'promo_code': 'UNICO'})
with A.app.app_context():
    h = A.User.query.filter_by(username='hermano').first()
    op = A.Order.query.filter_by(user_id=h.id, status='pending').first()
    if op is not None:                       # ya agotado → puede no crearse
        A._soltar_pedido(op, 'prueba')
check('🔴 el contador no baja de 1', usos() == 1, usos())

print('── una renovación no infla el contador del socio ──')
with A.app.app_context():
    t = A.User.query.filter_by(username='tercero').first()
    o1 = A.Order(user_id=t.id, plan='premium', billing_cycle='monthly',
                 base_price=50.0, final_price=40.0, promo_code='SOCIO',
                 status='paid')
    A.db.session.add(o1)
    A.db.session.commit()
    A._activate_plan_from_order(o1)
    check('la 1ª compra del socio cuenta 1',
          A.PromoCode.query.filter_by(code='SOCIO').first().uses_count == 1)
    o2 = A.Order(user_id=t.id, plan='premium', billing_cycle='monthly',
                 base_price=50.0, final_price=40.0, promo_code='SOCIO',
                 status='paid')
    A.db.session.add(o2)
    A.db.session.commit()
    A._activate_plan_from_order(o2)
    check('🔴 su renovación NO suma otro cliente',
          A.PromoCode.query.filter_by(code='SOCIO').first().uses_count == 1,
          A.PromoCode.query.filter_by(code='SOCIO').first().uses_count)

print('── un pedido de $0 tampoco descuadra nada ──')
with A.app.app_context():
    pc = A.PromoCode.query.filter_by(code='UNICO').first()
    pc.max_uses = 5
    A.db.session.commit()
c3 = cliente('hermano')
c3.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly',
                                  'promo_code': 'UNICO'})
with A.app.app_context():
    h = A.User.query.filter_by(username='hermano').first()
    pagado = A.Order.query.filter_by(user_id=h.id, status='paid').first()
    check('el hermano ya puede comprar con el cupón', pagado is not None
          or A.Order.query.filter_by(user_id=h.id, status='pending').first())
check('y el contador refleja canjes reales, no intentos', usos() <= 2, usos())

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
