# -*- coding: utf-8 -*-
"""El atasco que reporto el dueno: un pedido pendiente viejo bloquea cualquier
compra nueva, incluido aplicar un cupon, y el comprador no tenia forma de
soltarlo."""
import os, sys, tempfile
sys.path.insert(0, '/home/user/TRADINGBOT2.0/scalpel')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'a.db')

import app as A
from flask import g

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('   %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

CLAVE = 'Xk9!mQ2#pL5v'
with A.app.app_context():
    A.db.create_all()
    u = A.User(username='hermano', email='h@demo.invalid', plan='free', email_verified=True)
    u.set_password(CLAVE); A.db.session.add(u)
    A.db.session.add(A.PromoCode(code='PRUEBA100', discount_pct=100, kind='discount',
                                 valid_for='both', active=True))
    A.db.session.commit(); uid = u.id

def entrar(c):
    with A.app.app_context(): g.pop('_login_user', None)
    c.post('/login', data={'identifier': 'h@demo.invalid', 'password': CLAVE})

print('── Se queda con un pedido pendiente (lo que te pasó)')
with A.app.test_client() as c:
    entrar(c)
    c.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly'})
    with A.app.app_context():
        o = A.Order.query.filter_by(user_id=uid, status='pending').first()
    check('queda un pedido de $25 pendiente', o and o.final_price == 25.0, o.final_price if o else None)

    # Estas dos comprobaciones documentaban el atasco: el cupón se ignoraba y
    # lo único que se ofrecía era cancelar a mano. Desde el arreglo del cambiazo
    # de plan (tools/test_pedido_pendiente.py) el pedido viejo se suelta solo
    # cuando lo que se pide AHORA es distinto — y un cupón que cambia el precio
    # lo es. El comprador ya no tiene que cancelar nada.
    c.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly',
                                     'promo_code': 'PRUEBA100'})
    with A.app.app_context():
        viejo = A.db.session.get(A.Order, o.id)
        nuevo = (A.Order.query.filter(A.Order.user_id == uid,
                                      A.Order.id != o.id)
                 .order_by(A.Order.id.desc()).first())
        check('el cupón SÍ se aplica: el pedido viejo se suelta',
              viejo.status == 'cancelled', viejo.status)
        check('y el nuevo sale a $0 con el cupón puesto',
              nuevo and nuevo.final_price == 0.0 and nuevo.promo_code,
              (nuevo.final_price, nuevo.promo_code) if nuevo else None)
        # Se entregó en el acto, así que el resto del guion (cancelar a mano y
        # volver a comprar) necesita al usuario otra vez en Free.
        us = A.db.session.get(A.User, uid)
        us.plan = 'free'; us.plan_expires_at = None
        A.db.session.commit()

print('\n── Lo cancela él mismo y vuelve a intentarlo')
with A.app.test_client() as c:
    entrar(c)
    r = c.post('/checkout/cancel/%d' % o.id)
    check('cancelar lo manda de vuelta a los planes', '/pricing' in (r.headers.get('Location') or ''),
          r.headers.get('Location'))
    with A.app.app_context():
        check('el pedido queda cancelado', A.db.session.get(A.Order, o.id).status == 'cancelled')
        check('sin pendientes que estorben',
              A.Order.query.filter_by(user_id=uid, status='pending').count() == 0)

    r = c.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly',
                                         'promo_code': 'PRUEBA100'})
    check('ahora sí entrega el plan al instante',
          '/checkout/status/' in (r.headers.get('Location') or ''), r.headers.get('Location'))
    with A.app.app_context():
        u = A.db.session.get(A.User, uid)
        check('el plan queda activo', u.plan == 'standard', u.plan)
        check('con su camo puesto', u.active_camo == 'standard', u.active_camo)
        check('y sin ensuciar el libro de ventas', A.SaleBreakdown.query.count() == 0)

print('\n── Y que nadie cancele el pedido de otro')
with A.app.app_context():
    otro = A.User(username='ajeno', email='x@demo.invalid', plan='free', email_verified=True)
    otro.set_password(CLAVE); A.db.session.add(otro); A.db.session.commit()
    o2 = A.Order(user_id=uid, plan='premium', billing_cycle='monthly', base_price=50.0,
                 final_price=50.0, status='pending', payment_method='usdt-binance')
    A.db.session.add(o2); A.db.session.commit(); oid2 = o2.id
with A.app.test_client() as c:
    with A.app.app_context(): g.pop('_login_user', None)
    c.post('/login', data={'identifier': 'x@demo.invalid', 'password': CLAVE})
    r = c.post('/checkout/cancel/%d' % oid2)
    check('un extraño recibe 404', r.status_code == 404, r.status_code)
    with A.app.app_context():
        check('y el pedido sigue intacto', A.db.session.get(A.Order, oid2).status == 'pending')

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
