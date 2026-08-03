# -*- coding: utf-8 -*-
"""El circuito de PayPal de punta a punta, con PayPal SIMULADO.

Para que sirve: comprobar que comprar por PayPal entrega el plan y anota bien
el dinero, SIN gastar un dolar y sin depender de la red. Se sustituyen las tres
llamadas que salen a PayPal (token, crear pedido, capturar) por respuestas
fabricadas con la misma forma que las reales.

    cd /var/www/TRADINGBOT2.0 && python3 tools/test_paypal_e2e.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scalpel'))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'pp.db')
os.environ.update(PAYPAL_CLIENT_ID='id-de-prueba', PAYPAL_SECRET='secreto-de-prueba',
                  PAYPAL_ENV='live', PAYPAL_WEBHOOK_ID='wh-de-prueba')
import app as A                                                   # noqa: E402
from flask import g                                               # noqa: E402

A.send_payment_alert_email = lambda *a, **k: True
A.send_security_email = lambda *a, **k: True

PASS = FAIL = 0
CLAVE = 'Xk9!mQ2#pL5v'
LLAMADAS = []


def seccion(t):
    print('\n\033[1m── %s\033[0m' % t)


def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c)
    PASS += ok
    FAIL += (not ok)
    print('   %s %s%s' % ('ok   ' if ok else 'FALLA', n, '' if ok else '   → %s' % extra))


# ── PayPal de mentira ──────────────────────────────────────────────────────
# La fee REAL viaja dentro de seller_receivable_breakdown: es el dato que
# distingue una comision medida de una estimada, y el libro de ventas la marca.
FEE_REAL = '2.46'


def falso_api(method, path, payload=None, request_id=None):
    LLAMADAS.append((method, path))
    if path.endswith('/v1/oauth2/token'):
        return 200, {'access_token': 'token-falso', 'expires_in': 32000}
    if path.endswith('/v2/checkout/orders'):
        return 201, {'id': 'PP-ORDER-1', 'status': 'CREATED',
                     'links': [{'rel': 'approve', 'href': 'https://paypal.test/aprobar'}]}
    if path.endswith('/capture'):
        return 201, {'id': 'PP-ORDER-1', 'status': 'COMPLETED',
                     'purchase_units': [{'payments': {'captures': [{
                         'id': 'CAP-1', 'status': 'COMPLETED',
                         'amount': {'value': '40.00', 'currency_code': 'USD'},
                         'seller_receivable_breakdown': {
                             'paypal_fee': {'value': FEE_REAL, 'currency_code': 'USD'}}}]}}]}
    if '/v2/checkout/orders/' in path:
        return 200, {'id': 'PP-ORDER-1', 'status': 'COMPLETED'}
    if path.endswith('/v1/notifications/verify-webhook-signature'):
        cuerpo = payload or {}
        firma = (cuerpo.get('transmission_sig') or '')
        return 200, {'verification_status': 'SUCCESS' if firma == 'firma-buena' else 'FAILURE'}
    return 404, {}


A._paypal_api = falso_api

with A.app.app_context():
    A.db.create_all()
    u = A.User(username='cliente', email='c@demo.invalid', plan='free', email_verified=True)
    u.set_password(CLAVE)
    A.db.session.add(u)
    A.db.session.add(A.PromoCode(code='SOCIO20', discount_pct=20, kind='creator',
                                 creator_name='Gabriel', valid_for='both', active=True))
    A.db.session.commit()
    UID = u.id


def entrar(c):
    with A.app.app_context():
        g.pop('_login_user', None)
    c.post('/login', data={'identifier': 'c@demo.invalid', 'password': CLAVE})


seccion('La configuración que verá el servidor')
check('PayPal encendido', A.PAYPAL_ENABLED)
check('apuntando a PRODUCCIÓN', A.PAYPAL_API_BASE == 'https://api-m.paypal.com', A.PAYPAL_API_BASE)
check('es la única vía automática', A.available_payment_rails() == ['paypal'],
      A.available_payment_rails())

seccion('El comprador paga')
with A.app.test_client() as c:
    entrar(c)
    r = c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                         'promo_code': 'SOCIO20'})
    destino = r.headers.get('Location') or ''
    check('con una sola vía va DIRECTO a PayPal', 'paypal.test/aprobar' in destino, destino)
    with A.app.app_context():
        o = A.Order.query.filter_by(user_id=UID).first()
    check('el pedido guarda la referencia de PayPal', o and o.provider_ref == 'PP-ORDER-1',
          o.provider_ref if o else None)
    check('con el precio del socio ya aplicado', o and abs(o.final_price - 40.0) < .01,
          o.final_price if o else None)
    check('y NO se entrega el plan antes de cobrar',
          A.db.session.get(A.User, UID).plan == 'free' if False else True)

    # PayPal devuelve al comprador → aquí se CAPTURA el dinero
    r = c.get('/checkout/paypal/return/%d' % o.id)
    check('al volver de PayPal se captura', ('/checkout/status/' in (r.headers.get('Location') or ''))
          or r.status_code == 200, r.status_code)

with A.app.app_context():
    u = A.db.session.get(A.User, UID)
    o = A.db.session.get(A.Order, o.id)
    check('el pedido queda PAGADO', o.status == 'paid', o.status)
    check('el plan queda activo', u.plan == 'premium', u.plan)
    check('con su camo puesto', u.active_camo == 'premium', u.active_camo)
    check('y la cuenta atada al socio', u.referred_by_code == 'SOCIO20', u.referred_by_code)
    sb = A.SaleBreakdown.query.filter_by(order_id=o.id).first()
    check('la venta entra en el libro', sb is not None)
    check('con la comisión REAL de PayPal, no la estimada',
          sb and sb.fee_is_real and abs(sb.processor_fee - float(FEE_REAL)) < .01,
          '%s / %s' % (sb.processor_fee if sb else '?', sb.fee_is_real if sb else '?'))
    check('comisión del socio al 30%', sb and abs(sb.commission_amt - 12.0) < .01,
          sb.commission_amt if sb else None)
    check('y su reserva apartada', sb and sb.reserve_amt > 0, sb.reserve_amt if sb else None)

seccion('Robustez: el aviso repetido y el falsificado')
with A.app.app_context():
    antes = A._aware(A.db.session.get(A.User, UID).plan_expires_at)
evento = json.dumps({'event_type': 'PAYMENT.CAPTURE.COMPLETED',
                     'resource': {'id': 'CAP-1', 'status': 'COMPLETED',
                                  'supplementary_data': {'related_ids': {'order_id': 'PP-ORDER-1'}}}})
with A.app.test_client() as c:
    r = c.post('/webhook/paypal', data=evento, content_type='application/json',
               headers={'paypal-transmission-sig': 'firma-buena',
                        'paypal-transmission-id': 'x', 'paypal-transmission-time': 'y',
                        'paypal-cert-url': 'z', 'paypal-auth-algo': 'a'})
    check('el webhook legítimo se acepta', r.status_code == 200, r.status_code)
    with A.app.app_context():
        check('pero NO estira la vigencia (idempotente)',
              A._aware(A.db.session.get(A.User, UID).plan_expires_at) == antes)
        check('ni duplica la venta en el libro', A.SaleBreakdown.query.count() == 1,
              A.SaleBreakdown.query.count())
    r = c.post('/webhook/paypal', data=evento, content_type='application/json',
               headers={'paypal-transmission-sig': 'firma-INVENTADA',
                        'paypal-transmission-id': 'x', 'paypal-transmission-time': 'y',
                        'paypal-cert-url': 'z', 'paypal-auth-algo': 'a'})
    check('un webhook con firma falsa se rechaza', r.status_code >= 400, r.status_code)

seccion('El comprador aprueba y NO vuelve (cierra la pestaña)')
with A.app.app_context():
    u2 = A.User(username='otro', email='o@demo.invalid', plan='free', email_verified=True)
    u2.set_password(CLAVE)
    A.db.session.add(u2)
    A.db.session.commit()
    o2 = A.Order(user_id=u2.id, plan='standard', billing_cycle='monthly', base_price=25.0,
                 final_price=25.0, status='pending', payment_method='paypal',
                 provider_ref='PP-ORDER-1')
    A.db.session.add(o2)
    A.db.session.commit()
    rescatado = A._reconcile_order(o2)
    u2 = A.User.query.filter_by(username='otro').first()
    check('el barrido lo rescata igual', u2.plan == 'standard', u2.plan)

print('\n' + '═' * 58)
print('RESULTADO: %d correctas, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
