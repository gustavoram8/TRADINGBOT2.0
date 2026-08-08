# -*- coding: utf-8 -*-
"""Un descuento de promoción CADUCA; el de un socio no.

El fallo que corrige: la suscripción se abría con un único tramo infinito al
precio ya rebajado, así que cualquier promoción —aunque durase una semana— se
convertía en la tarifa de por vida de quien pasara por ahí ese día. Y no se
puede subir después: una autorización recurrente es por un importe concreto.

La solución son DOS tramos: el primer mes (sobrescribible) y la renovación.
"""
import os
import sys

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ['PAYPAL_CLIENT_ID'] = 'x'
os.environ['PAYPAL_SECRET'] = 'y'
os.environ['PAYPAL_PLAN_PREMIUM'] = 'P-PREM'
os.environ['PAYPAL_PLAN_STANDARD'] = 'P-STD'
os.environ['SITE_URL'] = 'https://tradeable.academy'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
import app as A                # noqa: E402

ok = fallas = 0
enviado = {}


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


MODO = {'v1': False}          # True = la cuenta aún tiene los planes viejos
LLAMADAS = []


def falso_api(metodo, ruta, payload=None, request_id=None):
    """PayPal de mentira: guarda lo que se le mandó. En modo v1 rechaza el
    payload de DOS tramos, como haría el PayPal real contra un plan viejo."""
    if ruta.endswith('/subscriptions'):
        LLAMADAS.append(payload)
        ciclos = (payload or {}).get('plan', {}).get('billing_cycles', [])
        if MODO['v1'] and len(ciclos) > 1:
            return 422, {'name': 'INVALID_REQUEST',
                         'message': 'billing_cycles do not match plan'}
        enviado.clear()
        enviado.update(payload or {})
        return 201, {'id': 'I-FAKE',
                     'links': [{'rel': 'approve', 'href': 'https://paypal.test/ok'}]}
    return 200, {}


A._paypal_api = falso_api
A.PAYPAL_ENABLED = True
A.PAYPAL_SUBS_ENABLED = True


def tramos(order):
    # url_for necesita contexto de petición para armar los return_url
    with A.app.test_request_context('/'):
        A._paypal_create_subscription(order)
    ciclos = enviado['plan']['billing_cycles']
    return (float(ciclos[0]['pricing_scheme']['fixed_price']['value']),
            float(ciclos[1]['pricing_scheme']['fixed_price']['value']))


with A.app.app_context():
    A.db.create_all()
    u = A.User(username='cliente', email='c@demo.invalid', plan='free',
               email_verified=True)
    u.set_password('Zx9!wQ4mNp2r')
    A.db.session.add(u)
    A.db.session.add(A.PromoCode(code='LANZAMIENTO', discount_pct=20,
                                 kind='discount'))
    A.db.session.add(A.PromoCode(code='GABRIEL', discount_pct=20,
                                 kind='creator', creator_name='Gabriel'))
    A.db.session.commit()

    def pedido(promo=None, final=50.0):
        o = A.Order(user_id=u.id, plan='premium', billing_cycle='monthly',
                    base_price=50.0, final_price=final, promo_code=promo,
                    status='pending')
        A.db.session.add(o)
        A.db.session.commit()
        return o

    print('── sin promoción ──')
    p, r = tramos(pedido())
    check('los dos tramos al precio de lista ($50 y $50)',
          (p, r) == (50.0, 50.0), (p, r))

    print('── promoción GENERAL (lanzamiento, 20%) ──')
    p, r = tramos(pedido('LANZAMIENTO', 40.0))
    check('🔴 primer mes $40 y la RENOVACIÓN vuelve a $50',
          (p, r) == (40.0, 50.0), (p, r))

    print('── código de SOCIO (Gabriel, 20%) ──')
    p, r = tramos(pedido('GABRIEL', 40.0))
    check('el descuento del socio SÍ es permanente ($40 y $40)',
          (p, r) == (40.0, 40.0), (p, r))
    check('...y el socio cobra comisión sobre cada renovación',
          A.descuento_permanente('GABRIEL'))
    check('mientras que la promo general no ata nada',
          not A.descuento_permanente('LANZAMIENTO'))

    print('── lo que se le anuncia en Ajustes ──')
    o = pedido('LANZAMIENTO', 40.0)
    with A.app.test_request_context('/'):
        A._paypal_create_subscription(o)
    sub = A.PlanSubscription.query.order_by(A.PlanSubscription.id.desc()).first()
    check('🔴 la suscripción guarda el precio de la RENOVACIÓN ($50), '
          'no el del primer mes', abs(sub.price - 50.0) < 0.01, sub.price)

    print('── un código inventado no rompe nada ──')
    p, r = tramos(pedido('NOEXISTE', 40.0))
    check('se trata como promo general (caduca)', (p, r) == (40.0, 50.0), (p, r))

    print('── cuenta ATADA a un socio que usa una promo general mejor ──')
    A.db.session.add(A.PromoCode(code='LANZA30', discount_pct=30,
                                 kind='discount'))
    atada = A.User(username='atada', email='at@demo.invalid', plan='free',
                   email_verified=True, referred_by_code='GABRIEL')
    atada.set_password('Zx9!wQ4mNp2r')
    A.db.session.add(atada)
    A.db.session.commit()
    oa = A.Order(user_id=atada.id, plan='premium', billing_cycle='monthly',
                 base_price=50.0, final_price=35.0, promo_code='LANZA30',
                 status='pending')
    A.db.session.add(oa)
    A.db.session.commit()
    p, r = tramos(oa)
    check('🔴 primer mes con la promo ($35) y la renovación vuelve a SU '
          'tarifa de socio ($40), no a lista', (p, r) == (35.0, 40.0), (p, r))

    print('── la cuenta aún tiene los planes VIEJOS de un tramo ──')
    MODO['v1'] = True
    del LLAMADAS[:]
    ov = pedido('LANZAMIENTO', 40.0)
    with A.app.test_request_context('/'):
        url = A._paypal_create_subscription(ov)
    check('🔴 la compra NO falla: se reintenta y sale la URL de aprobación',
          url == 'https://paypal.test/ok', url)
    check('el reintento fue con UN tramo',
          len(LLAMADAS) == 2
          and len(LLAMADAS[1]['plan']['billing_cycles']) == 1,
          len(LLAMADAS))
    check('...al precio del PRIMER mes ($40): lo autorizado es lo que se '
          'cobrará',
          float(LLAMADAS[1]['plan']['billing_cycles'][0]['pricing_scheme']
                ['fixed_price']['value']) == 40.0)
    subv = A.PlanSubscription.query.order_by(
        A.PlanSubscription.id.desc()).first()
    check('y la ficha dice $40 (no un importe que nunca se cobrará)',
          abs(subv.price - 40.0) < 0.01, subv.price)
    MODO['v1'] = False

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
