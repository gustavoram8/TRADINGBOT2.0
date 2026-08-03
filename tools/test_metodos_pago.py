# -*- coding: utf-8 -*-
"""Con PayPal encendido, el comprador tiene que PODER ELEGIR entre PayPal y
USDT. Sin nada encendido, va directo a las instrucciones manuales."""
import os, sys, tempfile, importlib

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('   %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

def arranca(paypal):
    for m in [m for m in list(sys.modules) if m == 'app' or m.startswith('app.')]:
        del sys.modules[m]
    os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'r.db')
    for k in ('PAYPAL_CLIENT_ID', 'PAYPAL_SECRET', 'CRYPTO_API_KEY'):
        os.environ.pop(k, None)
    if paypal:
        os.environ.update(PAYPAL_CLIENT_ID='x', PAYPAL_SECRET='y', PAYPAL_ENV='live',
                          CRYPTO_API_KEY='z')
    sys.path.insert(0, '/home/user/TRADINGBOT2.0/scalpel')
    A = importlib.import_module('app')
    with A.app.app_context():
        A.db.create_all()
        u = A.User(username='ana', email='a@demo.invalid', plan='free', email_verified=True)
        u.set_password('Xk9!mQ2#pL5v'); A.db.session.add(u); A.db.session.commit()
    return A

print('── HOY: ninguna pasarela encendida')
A = arranca(False)
print('   vias:', A.available_payment_rails())
with A.app.test_client() as c:
    c.post('/login', data={'identifier': 'a@demo.invalid', 'password': 'Xk9!mQ2#pL5v'})
    r = c.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly'})
    cuerpo = r.get_data(as_text=True)
    check('avisa que el cobro abre pronto y no crea pedido',
          r.status_code == 200 and 'csoon.title' in cuerpo, r.status_code)

print('\n── CON PAYPAL Y NOWPAYMENTS ENCENDIDOS')
A = arranca(True)
print('   vias:', A.available_payment_rails())
check('PayPal y USDT automatico conviven',
      A.available_payment_rails() == ['paypal', 'crypto'], A.available_payment_rails())
with A.app.test_client() as c:
    c.post('/login', data={'identifier': 'a@demo.invalid', 'password': 'Xk9!mQ2#pL5v'})
    r = c.post('/checkout/create', data={'plan': 'standard', 'cycle': 'monthly'})
    check('manda a ELEGIR metodo', '/checkout/pay/' in (r.headers.get('Location') or ''),
          r.headers.get('Location'))
    r = c.get(r.headers.get('Location'))
    cuerpo = r.get_data(as_text=True)
    check('la pantalla ofrece PayPal', 'value="paypal"' in cuerpo)
    check('y ofrece USDT (NOWPayments)', 'value="crypto"' in cuerpo)
    check('sin ofrecer el cobro a mano', 'value="manual"' not in cuerpo)

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
