# -*- coding: utf-8 -*-
"""El "baile del cupón": ¿puede un cliente atado colarle un código a su
renovación, o darse de baja y recomprar con una promo general mejor?

La pregunta exacta del dueño (2026-08-09). Lo que tiene que ser verdad:

  1. En una renovación NO existe carrito: PayPal cobra solo el importe que el
     cliente autorizó al abrir la suscripción. No hay dónde "meter" un código.
  2. Estando dentro del mes pagado tampoco puede recomprar su mismo plan
     (candado de meses apilados) — la única vía es darse de baja, ESPERAR a
     que venza lo pagado, y volver a comprar por el carrito.
  3. Si al volver usa una promo general mejor: paga ese primer mes con la
     promo (cláusula 3.1), pero la RENOVACIÓN vuelve a su tarifa de socio, la
     atribución no se mueve (el socio cobra comisión igual), y la promo queda
     GASTADA para esa cuenta (un solo uso). El baile funciona UNA vez y no
     roba nada: es exactamente el gancho que la promo ya era.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ['PAYPAL_CLIENT_ID'] = 'x'
os.environ['PAYPAL_SECRET'] = 'y'
os.environ['PAYPAL_PLAN_PREMIUM'] = 'P-PREM'
os.environ['PAYPAL_PLAN_STANDARD'] = 'P-STD'
os.environ['SITE_URL'] = 'https://tradeable.academy'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
from flask import g            # noqa: E402
import app as A                # noqa: E402

CL = 'Zx9!wQ4mNp2r'
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


def falso_api(metodo, ruta, payload=None, request_id=None):
    if ruta.endswith('/subscriptions'):
        enviado.clear()
        enviado.update(payload or {})
        return 201, {'id': 'I-BAILE-%d' % len(str(payload)),
                     'links': [{'rel': 'approve', 'href': 'https://paypal.test/ok'}]}
    if '/cancel' in ruta:
        return 204, {}
    return 200, {'status': 'CANCELLED'}


A._paypal_api = falso_api
A.PAYPAL_ENABLED = True
A.PAYPAL_SUBS_ENABLED = True


def sesion(nombre):
    c = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    c.post('/login', data={'identifier': nombre, 'password': CL})
    return c


def tramos_enviados():
    ciclos = enviado['plan']['billing_cycles']
    return (float(ciclos[0]['pricing_scheme']['fixed_price']['value']),
            float(ciclos[1]['pricing_scheme']['fixed_price']['value']))


with A.app.app_context():
    A.db.create_all()
    u = A.User(username='bailarin', email='b@demo.invalid', plan='free',
               email_verified=True)
    u.set_password(CL)
    A.db.session.add(u)
    A.db.session.add(A.PromoCode(code='GABRIEL', discount_pct=20,
                                 kind='creator', creator_name='Gabriel'))
    A.db.session.commit()
    UID = u.id

print('── mes 1: compra con el código del socio ──')
c = sesion('bailarin')
c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                 'promo_code': 'GABRIEL', 'method': 'paypal'})
p1, r1 = tramos_enviados()
check('paga $40 y la renovación queda autorizada en $40 (tarifa de socio)',
      (p1, r1) == (40.0, 40.0), (p1, r1))
with A.app.app_context():
    o = A.Order.query.filter_by(user_id=UID, status='pending').first()
    o.status = 'paid'
    o.paid_at = datetime.now(timezone.utc)
    A.db.session.commit()
    A._activate_plan_from_order(o)
    u = A.db.session.get(A.User, UID)
    check('la cuenta queda ATADA al socio', u.referred_by_code == 'GABRIEL')
    sub = A.PlanSubscription.query.filter_by(user_id=UID).first()
    sub.status = 'active'
    A.db.session.commit()

print('── sale la promo general del 50% y él la quiere para el mes 2 ──')
with A.app.app_context():
    A.db.session.add(A.PromoCode(code='LANZA50', discount_pct=50,
                                 kind='discount', max_uses=100))
    A.db.session.commit()

print('── intento A: colarla en la renovación → no existe esa puerta ──')
check('🔴 no hay NINGÚN endpoint que acepte un código sobre una '
      'suscripción viva (la renovación cobra lo autorizado y punto)',
      not any('renew' in str(r) and 'promo' in str(r)
              for r in A.app.url_map.iter_rules()))

print('── intento B: recomprar el plan estando dentro del mes pagado ──')
r = c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                     'promo_code': 'LANZA50',
                                     'method': 'paypal'})
check('🔴 rechazado: nadie paga un mes que ya tiene pagado',
      r.status_code == 302 and 'nocompra' in (r.headers.get('Location') or ''),
      r.headers.get('Location'))

print('── intento C: darse de baja, esperar el vencimiento, y recomprar ──')
r = c.post('/account/cancel-plan')
check('la baja corta la renovación sin quitarle el mes pagado',
      'cancel_failed' not in (r.headers.get('Location') or ''))
with A.app.app_context():
    u = A.db.session.get(A.User, UID)
    check('sigue premium hasta su fecha', u.plan == 'premium')
    # pasa el mes: el plan vence y cae a free
    u.plan_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    A.db.session.commit()
c.set_cookie('scalpel_splash_ts', '1')
c.get('/app')                       # _expire_plan corre en la visita
with A.app.app_context():
    check('vencido el mes, cae a free',
          A.db.session.get(A.User, UID).plan == 'free')

r = c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                     'promo_code': 'LANZA50',
                                     'method': 'paypal'})
p2, r2 = tramos_enviados()
check('ahora SÍ compra: primer mes $25 con la promo general (cláusula 3.1)',
      p2 == 25.0, (p2, r2))
check('🔴 pero la renovación vuelve a SU tarifa de socio ($40), no se '
      'queda en $25', r2 == 40.0, r2)
with A.app.app_context():
    o2 = (A.Order.query.filter_by(user_id=UID, status='pending')
          .order_by(A.Order.id.desc()).first())
    check('el pedido lleva la promo y cobra $25',
          o2.promo_code == 'LANZA50' and abs(o2.final_price - 25.0) < 0.01)
    o2.status = 'paid'
    o2.paid_at = datetime.now(timezone.utc)
    A.db.session.commit()
    A._activate_plan_from_order(o2)
    u = A.db.session.get(A.User, UID)
    check('🔴 la atribución NO se movió: sigue siendo cliente de Gabriel',
          u.referred_by_code == 'GABRIEL')
    fila = A.SaleBreakdown.query.filter_by(order_id=o2.id).first()
    check('y Gabriel cobra su comisión sobre los $25 pagados de verdad',
          fila is not None and fila.partner == 'Gabriel',
          fila and fila.partner)

print('── el baile NO se puede repetir ──')
with A.app.app_context():
    u = A.db.session.get(A.User, UID)
    _, _, err = A._promo_para_compra(u, 'premium', 'monthly', 'LANZA50')
    check('🔴 la promo quedó gastada para esta cuenta (already_used)',
          err == 'already_used', err)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
