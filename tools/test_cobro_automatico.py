# -*- coding: utf-8 -*-
"""Decision del dueno: PayPal y USDT van AUTOMATICOS — se paga y el plan se
enciende solo. La via manual (mandar comprobante y esperar) queda apagada.
Y sin ninguna pasarela, no se crea un pedido que nadie puede pagar."""
import os, sys, tempfile, importlib

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('   %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

CLAVE = 'Xk9!mQ2#pL5v'
def arranca(**env):
    for m in [m for m in list(sys.modules) if m == 'app' or m.startswith('app.')]:
        del sys.modules[m]
    for k in ('PAYPAL_CLIENT_ID','PAYPAL_SECRET','CRYPTO_API_KEY','USDT_ENABLED'):
        os.environ.pop(k, None)
    os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'x.db')
    os.environ.update(env)
    sys.path.insert(0, '/home/user/TRADINGBOT2.0/scalpel')
    A = importlib.import_module('app')
    with A.app.app_context():
        A.db.create_all()
        u = A.User(username='ana', email='a@demo.invalid', plan='free', email_verified=True)
        u.set_password(CLAVE); A.db.session.add(u)
        A.db.session.add(A.PromoCode(code='REGALO100', discount_pct=100, kind='discount',
                                     valid_for='both', active=True))
        A.db.session.commit()
    return A

def compra(A, **datos):
    with A.app.test_client() as c:
        c.post('/login', data={'identifier': 'a@demo.invalid', 'password': CLAVE})
        return c.post('/checkout/create',
                      data=dict(plan='standard', cycle='monthly', **datos))

print('── Sin PayPal: queda USDT, que siempre se ofrece')
A = arranca()
check('USDT sigue siendo una opcion', A.available_payment_rails() == ['manual'],
      A.available_payment_rails())
r = compra(A, promo_code='REGALO100')
check('un cupon del 100% entrega el plan sin pasar por caja',
      '/checkout/status/' in (r.headers.get('Location') or ''), r.headers.get('Location'))

print('\n── Con USDT_ENABLED=0 se puede esconder del todo')
A = arranca(USDT_ENABLED='0')
check('no queda ninguna via', A.available_payment_rails() == [], A.available_payment_rails())
r = compra(A)
cuerpo = r.get_data(as_text=True)
check('avisa que el cobro abre pronto', 'csoon.title' in cuerpo)
with A.app.app_context():
    n = A.Order.query.count()
check('y NO crea un pedido que nadie puede pagar', n == 0, '%d pedidos' % n)

print('\n── CON PAYPAL Y USDT AUTOMÁTICO')
A = arranca(PAYPAL_CLIENT_ID='x', PAYPAL_SECRET='y', PAYPAL_ENV='live',
            CRYPTO_API_KEY='z')
check('USDT pasa a ser la factura automatica',
      A.available_payment_rails() == ['paypal', 'crypto'], A.available_payment_rails())
r = compra(A)
check('manda a elegir entre las dos', '/checkout/pay/' in (r.headers.get('Location') or ''),
      r.headers.get('Location'))

print('\n── Y con PayPal pero sin NOWPayments, el comprador ELIGE igual')
A = arranca(PAYPAL_CLIENT_ID='x', PAYPAL_SECRET='y', PAYPAL_ENV='live')
check('PayPal y USDT conviven', A.available_payment_rails() == ['paypal', 'manual'],
      A.available_payment_rails())

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
