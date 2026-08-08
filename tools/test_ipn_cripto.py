# -*- coding: utf-8 -*-
"""El aviso de pago en cripto se acepta, lo firme quien lo firme.

El fallo que corrige, y que no habría dado la cara: el emisor firma el TEXTO
JSON que él mismo serializó. El `JSON.stringify` de JavaScript —el del ejemplo
oficial de NOWPayments— deja los caracteres no ASCII tal cual; el `json.dumps`
de Python los escapa a `\\uXXXX`. Con una sola raya (—) en la descripción del
pedido, las dos cadenas dejan de coincidir y TODOS los avisos se rechazan por
firma inválida.

Y lo peor es que no se nota: el pago se acaba entregando por la reconciliación
de la página del pedido o por el barrido de /admin, así que desde fuera se ve
igual que "el cripto todavía no está encendido". Se descubriría con un cliente
esperando su plan.
"""
import hashlib
import hmac
import json
import os
import sys

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ['CRYPTO_API_KEY'] = 'x'
os.environ['CRYPTO_IPN_SECRET'] = 'secreto-de-prueba'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
import app as A                # noqa: E402

ok = fallas = 0


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def firma(payload, como_js=True):
    """Firma como lo haría el emisor. `como_js` = sin escapar el unicode."""
    cuerpo = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                        ensure_ascii=not como_js)
    return hmac.new(b'secreto-de-prueba', cuerpo.encode(),
                    hashlib.sha512).hexdigest()


def avisa(payload, sig):
    return A.app.test_client().post(
        '/webhook/crypto', data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json',
                 'x-nowpayments-sig': sig})


with A.app.app_context():
    A.db.create_all()
    u = A.User(username='cripto', email='c@demo.invalid', plan='free',
               email_verified=True)
    u.set_password('Zx9!wQ4mNp2r')
    A.db.session.add(u)
    A.db.session.commit()
    o = A.Order(user_id=u.id, plan='premium', billing_cycle='monthly',
                base_price=50.0, final_price=50.0, status='pending',
                payment_method='crypto', provider_ref='inv-1')
    A.db.session.add(o)
    A.db.session.commit()
    OID = o.id

BASE = {'payment_id': 5099, 'payment_status': 'finished',
        'pay_address': 'TLPy9SccWovpZ4F2Gi9PC1ReVEyR5YQRJY',
        'price_amount': 50.0, 'price_currency': 'usd',
        'pay_currency': 'usdttrc20', 'order_id': 'plan-%d' % OID}

print('── 🔴 descripción con RAYA, firmada al estilo JavaScript ──')
con_raya = dict(BASE, order_description='Tradeable — Premium plan')
r = avisa(con_raya, firma(con_raya, como_js=True))
check('el aviso se ACEPTA (antes se rechazaba por firma)',
      r.status_code == 200, '%s %s' % (r.status_code, r.get_data(as_text=True)[:80]))
with A.app.app_context():
    check('y el pedido queda pagado',
          A.db.session.get(A.Order, OID).status == 'paid')

print('── la misma firma, pero escapando el unicode (estilo Python) ──')
with A.app.app_context():
    o2 = A.Order(user_id=1, plan='standard', billing_cycle='monthly',
                 base_price=25.0, final_price=25.0, status='pending',
                 payment_method='crypto', provider_ref='inv-2')
    A.db.session.add(o2)
    A.db.session.commit()
    OID2 = o2.id
p2 = dict(BASE, order_id='plan-%d' % OID2,
          order_description='Tradeable — Standard plan')
r = avisa(p2, firma(p2, como_js=False))
check('también se acepta (se toleran las dos formas)', r.status_code == 200,
      r.status_code)

print('── descripción ASCII: el caso normal desde ahora ──')
with A.app.app_context():
    o3 = A.Order(user_id=1, plan='premium', billing_cycle='monthly',
                 base_price=50.0, final_price=50.0, status='pending',
                 payment_method='crypto', provider_ref='inv-3')
    A.db.session.add(o3)
    A.db.session.commit()
    OID3 = o3.id
p3 = dict(BASE, order_id='plan-%d' % OID3,
          order_description='Tradeable - Premium plan')
check('la etiqueta que genera el sitio es ASCII pura',
      p3['order_description'].isascii())
r = avisa(p3, firma(p3, como_js=True))
check('se acepta', r.status_code == 200, r.status_code)

print('── 🔴 y una firma FALSA sigue rechazándose ──')
with A.app.app_context():
    o4 = A.Order(user_id=1, plan='premium', billing_cycle='monthly',
                 base_price=50.0, final_price=50.0, status='pending',
                 payment_method='crypto', provider_ref='inv-4')
    A.db.session.add(o4)
    A.db.session.commit()
    OID4 = o4.id
p4 = dict(BASE, order_id='plan-%d' % OID4, order_description='x')
r = avisa(p4, 'a' * 128)
check('firma inventada → 400', r.status_code == 400, r.status_code)
r = avisa(p4, firma(dict(p4, price_amount=1.0)))
check('🔴 firma de OTRO contenido (importe cambiado) → 400',
      r.status_code == 400, r.status_code)
with A.app.app_context():
    check('y ese pedido NO se entregó',
          A.db.session.get(A.Order, OID4).status == 'pending')

print('── el emisor manda los números como TEXTO (modo All-Strings) ──')
with A.app.app_context():
    o5 = A.Order(user_id=1, plan='standard', billing_cycle='monthly',
                 base_price=25.0, final_price=25.0, status='pending',
                 payment_method='crypto', provider_ref='inv-5')
    A.db.session.add(o5)
    A.db.session.commit()
    OID5 = o5.id
p5 = {'payment_id': '5100', 'payment_status': 'finished',
      'price_amount': '25.00', 'pay_amount': '25.00',
      'price_currency': 'usd', 'pay_currency': 'usdttrc20',
      'order_id': 'plan-%d' % OID5, 'order_description': 'Tradeable - Standard'}
r = avisa(p5, firma(p5))
check('🔴 se acepta: un "25.00" en texto se re-escribe idéntico',
      r.status_code == 200, r.status_code)
with A.app.app_context():
    check('y entrega el plan', A.db.session.get(A.Order, OID5).status == 'paid')

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
