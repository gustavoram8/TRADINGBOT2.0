# -*- coding: utf-8 -*-
"""El comprador SIEMPRE elige: PayPal o USDT. Si elige PayPal se le abre
PayPal; si elige USDT se le abre la de USDT. El sitio no decide por él, ni la
primera vez ni al volver a un pedido ya empezado."""
import os, sys, tempfile, importlib

PASS=FAIL=0
def check(n,c,extra=''):
    global PASS,FAIL
    ok=bool(c); PASS+=ok; FAIL+=(not ok)
    print('   %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

CLAVE='Xk9!mQ2#pL5v'
def arranca(**env):
    for m in [m for m in list(sys.modules) if m=='app' or m.startswith('app.')]:
        del sys.modules[m]
    for k in ('PAYPAL_CLIENT_ID','PAYPAL_SECRET','CRYPTO_API_KEY','USDT_ENABLED'):
        os.environ.pop(k,None)
    os.environ['DATABASE_URL']='sqlite:///'+os.path.join(tempfile.mkdtemp(),'u.db')
    os.environ.update(env)
    sys.path.insert(0,'/home/user/TRADINGBOT2.0/scalpel')
    A=importlib.import_module('app')
    def falso(method,path,payload=None,request_id=None):
        if path.endswith('/v1/oauth2/token'): return 200,{'access_token':'t','expires_in':30000}
        if path.endswith('/v2/checkout/orders'):
            return 201,{'id':'PP1','status':'CREATED',
                        'links':[{'rel':'approve','href':'https://paypal.test/ir'}]}
        return 200,{'id':'PP1','status':'CREATED'}
    A._paypal_api=falso
    with A.app.app_context():
        A.db.create_all()
        u=A.User(username='ana',email='a@demo.invalid',plan='free',email_verified=True)
        u.set_password(CLAVE); A.db.session.add(u); A.db.session.commit()
    return A

def comprar(A):
    with A.app.test_client() as c:
        c.post('/login',data={'identifier':'a@demo.invalid','password':CLAVE})
        r1=c.post('/checkout/create',data={'plan':'standard','cycle':'monthly'})
        r2=c.post('/checkout/create',data={'plan':'standard','cycle':'monthly'})
        return r1,r2

print('── PayPal encendido, USDT todavía a mano (lo que hay hoy)')
A=arranca(PAYPAL_CLIENT_ID='x',PAYPAL_SECRET='y',PAYPAL_ENV='live')
check('se le ofrecen LAS DOS', A.available_payment_rails()==['paypal','manual'],
      A.available_payment_rails())
r1,r2=comprar(A)
check('la primera vez manda a ELEGIR', '/checkout/pay/' in (r1.headers.get('Location') or ''),
      r1.headers.get('Location'))
check('y al volver a pulsar pagar, TAMBIÉN manda a elegir',
      '/checkout/pay/' in (r2.headers.get('Location') or ''), r2.headers.get('Location'))
with A.app.test_client() as c:
    c.post('/login',data={'identifier':'a@demo.invalid','password':CLAVE})
    with A.app.app_context(): oid=A.Order.query.first().id
    cuerpo=c.get('/checkout/pay/%d'%oid).get_data(as_text=True)
    check('el selector ofrece PayPal', 'value="paypal"' in cuerpo)
    check('y ofrece USDT', 'value="manual"' in cuerpo)
    r=c.post('/checkout/pay/%d'%oid, data={'method':'paypal'})
    check('elegir PayPal abre PayPal', 'paypal.test' in (r.headers.get('Location') or ''),
          r.headers.get('Location'))
    r=c.post('/checkout/pay/%d'%oid, data={'method':'manual'})
    check('elegir USDT abre la pantalla de USDT',
          r.status_code==200 and 'cdone.step3a' in r.get_data(as_text=True), r.status_code)
check('y el idioma se le impone a PayPal', 'PAYPAL_LOCALES' in open('/home/user/TRADINGBOT2.0/scalpel/app.py').read())

print('\n── Con NOWPayments, USDT pasa a ser automático')
A=arranca(PAYPAL_CLIENT_ID='x',PAYPAL_SECRET='y',PAYPAL_ENV='live',CRYPTO_API_KEY='z')
check('las dos, y USDT ya es factura', A.available_payment_rails()==['paypal','crypto'],
      A.available_payment_rails())
r1,r2=comprar(A)
check('sigue mandando a elegir', '/checkout/pay/' in (r1.headers.get('Location') or ''),
      r1.headers.get('Location'))

print('\n── Si se esconde USDT y no hay PayPal, no se inventa un pedido')
A=arranca(USDT_ENABLED='0')
r1,_=comprar(A)
check('avisa que el cobro abre pronto', 'csoon.title' in r1.get_data(as_text=True))

print('\nRESULTADO: %d ok, %d fallas' % (PASS,FAIL))
sys.exit(1 if FAIL else 0)
