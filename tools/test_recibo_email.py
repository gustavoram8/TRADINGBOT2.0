# -*- coding: utf-8 -*-
"""El recibo del comprador: se manda al activarse la compra, una sola vez.

El aviso de venta al dueño ya existía; esto prueba el correo NUEVO al cliente:
contenido correcto (producto, importe, nº de pedido), idioma por cookie, y que
un webhook repetido no manda recibos duplicados (guard de applied_at).
"""
import os
import sys

os.environ.setdefault('DATABASE_URL', 'sqlite://')
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


enviados = []
A.app.config['MAIL_PASSWORD'] = 'x'          # el envío "está configurado"
A.mail.send = lambda msg: enviados.append(msg)

with A.app.app_context():
    A.db.create_all()
    u = A.User(username='compradora', email='compradora@demo.invalid',
               plan='free', email_verified=True)
    u.set_password('Zx9!wQ4mNp2r')
    A.db.session.add(u)
    A.db.session.commit()

    print('── compra de plan ──')
    o = A.Order(user_id=u.id, plan='premium', billing_cycle='monthly',
                base_price=50.0, final_price=50.0, status='paid')
    A.db.session.add(o)
    A.db.session.commit()
    A._activate_plan_from_order(o)
    check('el comprador recibe SU recibo', len(enviados) == 1, len(enviados))
    if enviados:
        m = enviados[0]
        check('va a su correo', m.recipients == ['compradora@demo.invalid'],
              m.recipients)
        check('asunto con nº de pedido', ('plan-%d' % o.id) in m.subject,
              m.subject)
        check('cuerpo con producto e importe',
              'Premium' in m.body and '$50.00' in m.body)
        check('y con la nota del plan (baja/renovación)',
              'Settings' in m.body or 'Ajustes' in m.body)
    check('🔴 el webhook repetido NO duplica el recibo',
          (A._activate_plan_from_order(o), len(enviados))[1] == 1,
          len(enviados))

    print('── compra de camo ──')
    del enviados[:]
    co = A.CamoOrder(user_id=u.id, slug='pole', label='F1 Blueprint',
                     price=1.99, status='paid')
    A.db.session.add(co)
    A.db.session.commit()
    A._activate_camo_from_order(co)
    check('el recibo del camo llega', len(enviados) == 1, len(enviados))
    if enviados:
        check('con su importe', '$1.99' in enviados[0].body,
              enviados[0].body[:80])
        check('sin la nota de plan (no es una suscripción)',
              'renueva' not in enviados[0].body
              and 'renews' not in enviados[0].body)

    print('── el PDF de Synapse ──')
    del enviados[:]
    so = A.SynapseOrder(user_id=u.id, lang='es',
                        label='Synapse Library PDF (ES)',
                        price=15.0, status='paid')
    A.db.session.add(so)
    A.db.session.commit()
    A._activate_synapse_from_order(so)
    check('el recibo del PDF llega', len(enviados) == 1, len(enviados))
    if enviados:
        check('con el producto', 'Synapse' in enviados[0].body)

    print('── el idioma ──')
    del enviados[:]
    with A.app.test_request_context('/', headers={
            'Cookie': 'scalpel_lang=es'}):
        A.send_receipt_email('compradora@demo.invalid', 'Premium', 50.0,
                             'plan-99', es_plan=True)
    check('con cookie es → recibo en español',
          enviados and 'Gracias por tu compra' in enviados[0].body)
    del enviados[:]
    A.send_receipt_email('compradora@demo.invalid', 'Premium', 50.0, 'plan-99')
    check('sin petición (webhook) → cae a inglés',
          enviados and 'Thanks for your purchase' in enviados[0].body)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
