# -*- coding: utf-8 -*-
"""Con PayPal encendido, ¿se pueden comprar cosméticos de verdad?"""
import os, sys, tempfile
sys.path.insert(0,'/home/user/TRADINGBOT2.0/scalpel')
os.environ['DATABASE_URL']='sqlite:///'+os.path.join(tempfile.mkdtemp(),'cz.db')
os.environ.update(PAYPAL_CLIENT_ID='x', PAYPAL_SECRET='y', PAYPAL_ENV='live')
import app as A
from flask import g

PASS=FAIL=0
def check(n,c,extra=''):
    global PASS,FAIL
    ok=bool(c); PASS+=ok; FAIL+=(not ok)
    print('   %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

def falso_api(method, path, payload=None, request_id=None):
    if path.endswith('/v1/oauth2/token'): return 200,{'access_token':'t','expires_in':30000}
    if path.endswith('/v2/checkout/orders'):
        return 201,{'id':'PPC-1','status':'CREATED',
                    'links':[{'rel':'approve','href':'https://paypal.test/aprobar-cosmetico'}]}
    if path.endswith('/capture'):
        return 201,{'id':'PPC-1','status':'COMPLETED','purchase_units':[{'payments':{'captures':[{
            'id':'CAPC','status':'COMPLETED','amount':{'value':'7.98','currency_code':'USD'}}]}}]}
    return 200,{'id':'PPC-1','status':'COMPLETED'}
A._paypal_api = falso_api

with A.app.app_context():
    A.db.create_all()
    u=A.User(username='ana',email='a@demo.invalid',plan='premium',email_verified=True)
    u.set_password('Xk9!mQ2#pL5v'); A.db.session.add(u); A.db.session.commit(); UID=u.id
    # Marcos LIBRES: uno festivo fuera de su ventana de 24h lo rechaza el
    # servidor a proposito (window_closed), y eso esta bien.
    # Se eligen los que estan A LA VENTA HOY: un festivo fuera de su ventana de
    # 24h lo rechaza el servidor a proposito (window_closed), y eso esta bien.
    tienda=[i for i in A.CosmeticItem.query.filter_by(channel='store', kind='frame')
            if A.festive_window(i.slug)[0]][:2]
    refs=['item:%s'%i.slug for i in tienda]
    nombres=[i.slug for i in tienda]

print('── Carrito de dos marcos, pagando por PayPal')
with A.app.test_client() as c:
    with A.app.app_context(): g.pop('_login_user',None)
    c.post('/login',data={'identifier':'a@demo.invalid','password':'Xk9!mQ2#pL5v'})
    r=c.post('/api/cosmetics/checkout',json={'slugs':refs})
    j=r.get_json() or {}
    check('el checkout responde con la URL de PayPal',
          r.status_code==200 and 'paypal.test' in (j.get('url') or ''), '%s %s'%(r.status_code,j))
    with A.app.app_context():
        o=A.CosmeticOrder.query.first()
    check('crea el pedido de cosméticos', o is not None)
    check('con el total calculado en el SERVIDOR', o and o.price>0, o.price if o else None)
    check('y NO se entrega antes de pagar',
          not A.db.session.get(A.User,UID).owned_camos and
          A.UserCosmetic.query.filter_by(user_id=UID).count()==0)
    r=c.get('/cosmetics/paypal/return/%d'%o.id)
    check('al volver de PayPal se captura', r.status_code in (200,302), r.status_code)

with A.app.app_context():
    o=A.db.session.get(A.CosmeticOrder,o.id)
    check('el pedido queda pagado', o.status=='paid', o.status)
    tengo=[A.db.session.get(A.CosmeticItem, uc.item_id).slug
           for uc in A.UserCosmetic.query.filter_by(user_id=UID)]
    check('y los DOS marcos son suyos', sorted(tengo)==sorted(nombres), tengo)
    u=A.db.session.get(A.User,UID)
    check('y le pone uno solo', u.active_frame in nombres, u.active_frame)
    check('los cosméticos NO entran al libro de ventas', A.SaleBreakdown.query.count()==0)

print('\nRESULTADO: %d ok, %d fallas' % (PASS,FAIL))
sys.exit(1 if FAIL else 0)
