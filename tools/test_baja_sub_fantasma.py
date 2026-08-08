# -*- coding: utf-8 -*-
"""Una suscripción que el comprador nunca aprobó no puede bloquear su baja.

El caso real, visto en producción: el comprador llega a la pantalla de PayPal
y la cierra. De nuestro lado queda una suscripción 'pending' con su id; en
PayPal esa suscripción nunca se activó, así que el endpoint de cancelar
responde 404. El código anterior leía ese 404 como "no se pudo cortar" y
devolvía al cliente a Ajustes con `cancel_failed` — o sea que pulsar "darme de
baja" no cancelaba NADA, ni siquiera la suscripción de verdad que sí tenía
detrás. Ese es un cargo que él creía cancelado.

Regla: solo bloquea la baja una suscripción que PayPal confirme que TODAVÍA
puede cobrar (ACTIVE o SUSPENDED). Ante una API muda, se bloquea igual.
"""
import os
import sys

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ['PAYPAL_CLIENT_ID'] = 'x'
os.environ['PAYPAL_SECRET'] = 'y'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
from flask import g            # noqa: E402
import app as A                # noqa: E402

CL = 'Zx9!wQ4mNp2r'
ok = fallas = 0
RESP = {}


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def falso_api(metodo, ruta, payload=None, request_id=None):
    if ruta.endswith('/cancel'):
        return RESP.get('cancel', (204, {}))
    return RESP.get('get', (200, {'status': 'ACTIVE'}))


A._paypal_api = falso_api
A.PAYPAL_ENABLED = True


def nueva_sub(uid, ref='I-FANTASMA', estado='pending'):
    with A.app.app_context():
        A.PlanSubscription.query.filter_by(user_id=uid).delete()
        s = A.PlanSubscription(user_id=uid, provider='paypal',
                               provider_ref=ref, plan='standard',
                               billing_cycle='monthly', price=25.0,
                               status=estado)
        A.db.session.add(s)
        A.db.session.commit()
        return s.id


with A.app.app_context():
    A.db.create_all()
    u = A.User(username='comprador', email='c@demo.invalid', plan='standard',
               email_verified=True)
    u.set_password(CL)
    A.db.session.add(u)
    A.db.session.commit()
    UID = u.id

print('── la suscripción abandonada en la pantalla de PayPal ──')
RESP = {'cancel': (404, {'name': 'RESOURCE_NOT_FOUND'}), 'get': (404, {})}
sid = nueva_sub(UID)
with A.app.app_context():
    s = A.db.session.get(A.PlanSubscription, sid)
    check('🔴 se da por cortada: no puede cobrar nada',
          A._paypal_sub_cancel(s) is True)
    check('y queda cerrada de nuestro lado',
          A.db.session.get(A.PlanSubscription, sid).status == 'cancelled')

print('── PayPal la conoce pero nunca se aprobó ──')
RESP = {'cancel': (422, {}), 'get': (200, {'status': 'APPROVAL_PENDING'})}
sid = nueva_sub(UID)
with A.app.app_context():
    s = A.db.session.get(A.PlanSubscription, sid)
    check('tampoco bloquea', A._paypal_sub_cancel(s) is True)

print('── 🔴 una que SÍ puede cobrar y no se deja cortar ──')
RESP = {'cancel': (500, {}), 'get': (200, {'status': 'ACTIVE'})}
sid = nueva_sub(UID, estado='active')
with A.app.app_context():
    s = A.db.session.get(A.PlanSubscription, sid)
    check('se sigue considerando FALLO (no se miente)',
          A._paypal_sub_cancel(s) is False)
    check('y NO se marca cancelada',
          A.db.session.get(A.PlanSubscription, sid).status == 'active')

print('── PayPal mudo: ante la duda, se bloquea ──')
RESP = {'cancel': (500, {}), 'get': (500, {})}
sid = nueva_sub(UID, estado='active')
with A.app.app_context():
    s = A.db.session.get(A.PlanSubscription, sid)
    check('🔴 no se da por cortada lo que no se pudo comprobar',
          A._paypal_sub_cancel(s) is False)

print('── el botón de baja del cliente, de punta a punta ──')
RESP = {'cancel': (404, {}), 'get': (404, {})}
sid = nueva_sub(UID)
c = A.app.test_client()
with A.app.app_context():
    g.pop('_login_user', None)
c.post('/login', data={'identifier': 'comprador', 'password': CL})
r = c.post('/account/cancel-plan')
destino = r.headers.get('Location', '')
check('🔴 la baja NO falla por una suscripción fantasma',
      'cancel_failed' not in destino, destino)
with A.app.app_context():
    usr = A.User.query.filter_by(username='comprador').first()
    check('y queda registrada de verdad', usr.cancel_at_period_end is True)
    check('el plan pagado NO se le quita', usr.plan == 'standard', usr.plan)

print('── con una suscripción real que no se corta, sí avisa ──')
RESP = {'cancel': (500, {}), 'get': (200, {'status': 'ACTIVE'})}
nueva_sub(UID, estado='active')
with A.app.app_context():
    usr = A.User.query.filter_by(username='comprador').first()
    usr.cancel_at_period_end = False
    A.db.session.commit()
r = c.post('/account/cancel-plan')
check('🔴 ahí sí se le dice que no se pudo',
      'cancel_failed' in r.headers.get('Location', ''),
      r.headers.get('Location'))

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
