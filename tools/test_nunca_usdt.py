# -*- coding: utf-8 -*-
"""Con PayPal encendido y el cobro manual APAGADO, la pantalla de USDT no debe
aparecer NUNCA — ni al comprar, ni al volver a un pedido ya empezado."""
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
    for k in ('PAYPAL_CLIENT_ID','PAYPAL_SECRET','CRYPTO_API_KEY','MANUAL_USDT_ENABLED'):
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

print('── Solo PayPal (lo que hay hoy en producción)')
A=arranca(PAYPAL_CLIENT_ID='x',PAYPAL_SECRET='y',PAYPAL_ENV='live')
check('la vía manual NO está entre las opciones', 'manual' not in A.available_payment_rails(),
      A.available_payment_rails())
r1,r2=comprar(A)
check('la primera vez va a PayPal', 'paypal.test' in (r1.headers.get('Location') or ''),
      r1.headers.get('Location'))
d2 = r2.headers.get('Location') or ''
cuerpo2 = r2.get_data(as_text=True)
check('y al volver a pulsar pagar, TAMBIÉN va a PayPal', 'paypal.test' in d2,
      d2 or cuerpo2[:120])
check('sin enseñar jamás las instrucciones de USDT',
      'cdone.step3a' not in cuerpo2 and 'Binance' not in cuerpo2)
check('y el idioma se le impone a PayPal', 'PAYPAL_LOCALES' in open('/home/user/TRADINGBOT2.0/scalpel/app.py').read())

print('\n── PayPal + USDT automático: ahí SÍ se elige')
A=arranca(PAYPAL_CLIENT_ID='x',PAYPAL_SECRET='y',PAYPAL_ENV='live',CRYPTO_API_KEY='z')
r1,r2=comprar(A)
check('la primera vez manda a ELEGIR', '/checkout/pay/' in (r1.headers.get('Location') or ''),
      r1.headers.get('Location'))
check('y la segunda también', '/checkout/pay/' in (r2.headers.get('Location') or ''),
      r2.headers.get('Location'))

print('\n── Sin nada encendido: ni pedido ni instrucciones')
A=arranca()
r1,_=comprar(A)
check('avisa que el cobro abre pronto', 'csoon.title' in r1.get_data(as_text=True))

print('\nRESULTADO: %d ok, %d fallas' % (PASS,FAIL))
sys.exit(1 if FAIL else 0)
