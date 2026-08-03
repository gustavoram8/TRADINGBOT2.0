# -*- coding: utf-8 -*-
"""¿Se puede regalar un plan con un código del 100% y que llegue solo?

Ejecuta el camino REAL de un usuario: entra, aplica el código, pasa por caja y
vemos exactamente qué recibe y qué NO. Sin tocar PayPal ni dinero.
"""
import os, sys, tempfile
sys.path.insert(0, '/home/user/TRADINGBOT2.0/scalpel')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'g.db')
import app as A
from flask import g

def paso(t): print('\n── %s' % t)
def dato(k, v): print('   %-34s %s' % (k, v))

with A.app.app_context():
    A.db.create_all()
    admin = A.User(username='jefe', email='j@demo.invalid', plan='premium',
                   email_verified=True, is_admin=True)
    admin.set_password('Xk9!mQ2#pL5v')
    cli = A.User(username='regalado', email='r@demo.invalid', plan='free',
                 email_verified=True)
    cli.set_password('Xk9!mQ2#pL5v')
    A.db.session.add_all([admin, cli])
    # Código del 100% — el que usaria el dueno para regalar un plan de prueba
    pc = A.PromoCode(code='PRUEBA100', discount_pct=100, kind='creator',
                     creator_name='Prueba interna', valid_for='both', active=True)
    A.db.session.add(pc); A.db.session.commit()
    cid = cli.id

def como(c, u, p='Xk9!mQ2#pL5v'):
    # Flask-Login cachea el usuario en `g` (contexto de APP), asi que sin
    # limpiarlo la segunda peticion corre como el primer usuario.
    with A.app.app_context():
        g.pop('_login_user', None)
    return c.post('/login', data={'identifier': u, 'password': p})

paso('El cliente compra Premium con el código del 100%')
with A.app.test_client() as c:
    como(c, 'regalado')
    r = c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                         'promo_code': 'PRUEBA100'},
               follow_redirects=False)
    dato('respuesta del checkout', '%s → %s' % (r.status_code, r.headers.get('Location') or 'pagina de instrucciones'))

with A.app.app_context():
    o = A.Order.query.filter_by(user_id=cid).first()
    dato('pedido creado', 'id=%s plan=%s' % (o.id, o.plan) if o else 'NINGUNO')
    dato('precio final', '$%.2f' % o.final_price)
    dato('estado del pedido', o.status)
    u = A.db.session.get(A.User, cid)
    dato('PLAN DEL USUARIO', u.plan)
    dato('camo entregado', u.owned_camos or '(ninguno)')
    dato('fila en el libro de ventas', A.SaleBreakdown.query.count())
    oid = o.id

paso('¿Hizo falta que el dueño lo activara a mano?')
with A.app.test_client() as c:
    como(c, 'jefe')
    r = c.post('/admin/order/mark-paid', data={'order_id': oid}, follow_redirects=False)
    dato('respuesta', r.status_code)

with A.app.app_context():
    u = A.db.session.get(A.User, cid)
    o = A.db.session.get(A.Order, oid)
    dato('estado del pedido', o.status)
    dato('PLAN DEL USUARIO', u.plan)
    dato('vence el', u.plan_expires_at)
    dato('camo entregado', u.owned_camos or '(ninguno)')
    dato('camo puesto', u.active_camo or '(ninguno)')
    dato('atribucion al socio', u.referred_by_code or '(ninguna)')
    sb = A.SaleBreakdown.query.first()
    dato('fila en el libro de ventas', 'si · bruto $%.2f · pagado $%.2f · comision $%.2f (puesto %s del socio %s)' % (sb.gross, sb.net_paid, sb.commission_amt, sb.position, sb.partner) if sb else 'NO')
    dato('reveal de compra pendiente', bool(A.Order.query.filter_by(user_id=cid, status='paid', celebrated_at=None).first()))

paso('CONTRASTE — una compra DE PAGO tiene que seguir haciendo todo')
with A.app.app_context():
    pago = A.User(username='pagador', email='p@demo.invalid', plan='free',
                  email_verified=True)
    pago.set_password('Xk9!mQ2#pL5v')
    A.db.session.add(pago)
    A.db.session.add(A.PromoCode(code='SOCIO20', discount_pct=20, kind='creator',
                                 creator_name='Gabriel', valid_for='both', active=True))
    A.db.session.commit()
    pid = pago.id

with A.app.test_client() as c:
    como(c, 'pagador')
    c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                     'promo_code': 'SOCIO20'})
with A.app.app_context():
    o = A.Order.query.filter_by(user_id=pid).first()
    dato('precio final', '$%.2f' % o.final_price)
    dato('estado (debe seguir pendiente)', o.status)
    dato('PLAN (no se entrega sin pagar)', A.db.session.get(A.User, pid).plan)
    o.status = 'paid'; A.db.session.commit()
    A._activate_plan_from_order(o)
    u = A.db.session.get(A.User, pid)
    dato('tras pagar → plan', u.plan)
    dato('atribucion al socio', u.referred_by_code or '(NINGUNA ⛔)')
    sb = A.SaleBreakdown.query.filter_by(order_id=o.id).first()
    dato('libro de ventas', 'si · pagado $%.2f · comision $%.2f al %s%% (%s)'
         % (sb.net_paid, sb.commission_amt, sb.commission_pct, sb.partner) if sb else 'NO ⛔')
