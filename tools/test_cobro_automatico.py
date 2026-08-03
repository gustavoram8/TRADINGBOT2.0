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
    for k in ('PAYPAL_CLIENT_ID','PAYPAL_SECRET','CRYPTO_API_KEY','MANUAL_USDT_ENABLED'):
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

print('── HOY: sin ninguna pasarela')
A = arranca()
check('no se ofrece ninguna via', A.available_payment_rails() == [], A.available_payment_rails())
r = compra(A)
cuerpo = r.get_data(as_text=True)
check('avisa que el cobro abre pronto', 'csoon.title' in cuerpo)
check('y NO manda a las instrucciones de Binance', 'cdone.step3a' not in cuerpo)
with A.app.app_context():
    n = A.Order.query.count()
check('sobre todo: NO crea un pedido que nadie puede pagar', n == 0, '%d pedidos' % n)
r = compra(A, promo_code='REGALO100')
check('pero un cupón del 100% SÍ entrega el plan',
      '/checkout/status/' in (r.headers.get('Location') or ''), r.headers.get('Location'))

print('\n── CON PAYPAL Y USDT AUTOMÁTICO')
A = arranca(PAYPAL_CLIENT_ID='x', PAYPAL_SECRET='y', PAYPAL_ENV='live',
            CRYPTO_API_KEY='z')
check('las dos vías, sin la manual',
      A.available_payment_rails() == ['paypal', 'crypto'], A.available_payment_rails())
r = compra(A)
check('manda a elegir entre las dos', '/checkout/pay/' in (r.headers.get('Location') or ''),
      r.headers.get('Location'))

print('\n── Y si algún día hace falta cobrar a mano')
A = arranca(MANUAL_USDT_ENABLED='1')
check('la vía manual se puede reencender',
      A.available_payment_rails() == ['manual'], A.available_payment_rails())

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
