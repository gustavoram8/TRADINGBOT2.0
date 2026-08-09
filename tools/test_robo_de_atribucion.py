# -*- coding: utf-8 -*-
"""¿Un cliente atado puede pasarse al código de OTRO creador dándose de baja?

La pregunta del dueño (2026-08-09): la regla dice que una cuenta atribuida no
puede migrar a otro creador... ¿pero sigue siendo verdad DESPUÉS de darse de
baja y con el plan ya vencido?

Importa porque es el caso realista: nadie intenta cambiar de código estando
suscrito — lo intenta cuando vuelve a comprar. Si el candado colgara del plan
activo en vez de la CUENTA, el influencer B se llevaría la cartera del A con
solo decirle a la gente "date de baja y usa mi código".
"""
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault('DATABASE_URL', 'sqlite://')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
from flask import g            # noqa: E402
import app as A                # noqa: E402

CL = 'Zx9!wQ4mNp2r'
ok = fallas = 0


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def sesion(nombre):
    c = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    c.post('/login', data={'identifier': nombre, 'password': CL})
    c.set_cookie('scalpel_splash_ts', '1')
    return c


with A.app.app_context():
    A.db.create_all()
    u = A.User(username='cliente', email='c@demo.invalid', plan='free',
               email_verified=True)
    u.set_password(CL)
    A.db.session.add(u)
    # A: el socio que lo trajo. B: el rival que quiere robárselo.
    A.db.session.add(A.PromoCode(code='SOCIOA', discount_pct=20,
                                 kind='creator', creator_name='Socio A'))
    A.db.session.add(A.PromoCode(code='SOCIOB', discount_pct=20,
                                 kind='creator', creator_name='Socio B'))
    # Y un rival GENEROSO: cede parte de su comisión para dar más descuento.
    A.db.session.add(A.PromoCode(code='SOCIOB30', discount_pct=30,
                                 kind='creator', creator_name='Socio B'))
    A.db.session.commit()
    UID = u.id

print('── el cliente llega por el Socio A y compra ──')
c = sesion('cliente')
c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                 'promo_code': 'SOCIOA', 'method': 'manual'})
with A.app.app_context():
    o = A.Order.query.filter_by(user_id=UID, status='pending').first()
    o.status = 'paid'
    o.paid_at = datetime.now(timezone.utc)
    A.db.session.commit()
    A._activate_plan_from_order(o)
    check('queda atado al Socio A',
          A.db.session.get(A.User, UID).referred_by_code == 'SOCIOA')

print('── se da de baja y DEJA VENCER el plan (ya es free otra vez) ──')
c.post('/account/cancel-plan')
with A.app.app_context():
    u = A.db.session.get(A.User, UID)
    u.plan_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    A.db.session.commit()
c.get('/app')
with A.app.app_context():
    check('el plan venció: la cuenta es free',
          A.db.session.get(A.User, UID).plan == 'free')

print('── 🔴 AHORA intenta comprar con el código del Socio B ──')
r = c.post('/api/checkout/validate-code',
           json={'code': 'SOCIOB', 'plan': 'premium', 'cycle': 'monthly'})
d = r.get_json() or {}
check('la casilla lo rechaza con "locked"',
      not d.get('ok') and d.get('error') == 'locked', d)
c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                 'promo_code': 'SOCIOB', 'method': 'manual'})
with A.app.app_context():
    o2 = (A.Order.query.filter_by(user_id=UID, status='pending')
          .order_by(A.Order.id.desc()).first())
    check('🔴 ni forzando el formulario: el pedido NO lleva el código del rival',
          o2 is not None and o2.promo_code == 'SOCIOA', o2 and o2.promo_code)
    check('...y sigue pagando su $40 de siempre (su código se auto-aplica)',
          abs(o2.final_price - 40.0) < 0.01, o2.final_price)
    o2.status = 'paid'
    o2.paid_at = datetime.now(timezone.utc)
    A.db.session.commit()
    A._activate_plan_from_order(o2)
    u = A.db.session.get(A.User, UID)
    check('🔴 la atribución NO se movió: sigue siendo del Socio A',
          u.referred_by_code == 'SOCIOA', u.referred_by_code)
    fila = (A.SaleBreakdown.query.filter_by(order_id=o2.id).first())
    check('y la comisión de esa venta va al Socio A, no al B',
          fila is not None and fila.partner == 'Socio A',
          fila and fila.partner)

print('── el caso peor: un rival que ofrece MÁS descuento (30% vs 20%) ──')
with A.app.app_context():
    u = A.db.session.get(A.User, UID)
    u.plan = 'free'
    u.plan_expires_at = None
    A.db.session.commit()
r = c.post('/api/checkout/validate-code',
           json={'code': 'SOCIOB30', 'plan': 'premium', 'cycle': 'monthly'})
d = r.get_json() or {}
check('🔴 tampoco entra aunque el precio sea MEJOR (es de creador: locked)',
      not d.get('ok') and d.get('error') == 'locked', d)

print('── y una cuenta NUEVA sí puede elegir al Socio B libremente ──')
with A.app.app_context():
    n = A.User(username='nueva', email='n@demo.invalid', plan='free',
               email_verified=True)
    n.set_password(CL)
    A.db.session.add(n)
    A.db.session.commit()
c2 = sesion('nueva')
r = c2.post('/api/checkout/validate-code',
            json={'code': 'SOCIOB30', 'plan': 'premium', 'cycle': 'monthly'})
d = r.get_json() or {}
check('sin atadura previa, el código del B se aplica normal (30%)',
      bool(d.get('ok')) and d.get('discount_pct') == 30, d)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
