# -*- coding: utf-8 -*-
"""Punto 3: "Mis cupones" condicional + emisor de códigos personales en /admin.

Las dos reglas nuevas:
  · la entrada del menú aparece SOLO si la cuenta tiene algún código personal,
    y SIN filtro de plan — el cupón es de la cuenta y sobrevive al downgrade
    ("nada se revoca jamás"); el free con cupón es justo el comprador al que
    no hay que esconderle su descuento;
  · /admin puede emitir un código atado a una cuenta concreta (premio de un
    sorteo, una compensación) que solo esa cuenta puede canjear.
"""
import os
import sys

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


def sesion(nombre, clave=CL):
    c = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    c.post('/login', data={'identifier': nombre, 'password': clave})
    c.set_cookie('scalpel_splash_ts', '1')
    return c


with A.app.app_context():
    A.db.create_all()
    for n, p in (('ganadora', 'free'), ('vecino', 'premium'),
                 ('exdueno', 'free')):
        u = A.User(username=n, email=n + '@demo.invalid', plan=p,
                   email_verified=True)
        u.set_password(CL)
        A.db.session.add(u)
    A.db.session.commit()
    GAN = A.User.query.filter_by(username='ganadora').first().id
    EX = A.User.query.filter_by(username='exdueno').first().id
    # un SPIN viejo, de cuando la ruleta daba descuentos: quedó en una cuenta
    # que hoy es FREE (bajó de plan después de ganarlo)
    A.db.session.add(A.PromoCode(code='SPIN-VIEJO', discount_pct=25,
                                 kind='discount', valid_for='monthly',
                                 max_uses=1, restrict_user_id=EX))
    A.db.session.commit()

print('── el cupón sobrevive al plan: un FREE ve el suyo ──')
c = sesion('exdueno')
r = c.get('/api/daily/coupons')
check('🔴 la API responde 200 a un usuario free (antes: 403 premium)',
      r.status_code == 200, r.status_code)
cps = (r.get_json() or {}).get('coupons', [])
check('y lista su SPIN viejo como activo',
      len(cps) == 1 and cps[0]['code'] == 'SPIN-VIEJO'
      and cps[0]['status'] == 'active', cps)
html = c.get('/app').get_data(as_text=True)
check('el menú se lo enseña (hasCoupons: true)', 'hasCoupons: true' in html)

print('── sin cupones, la entrada no existe ──')
c2 = sesion('vecino')
html = c2.get('/app').get_data(as_text=True)
check('un premium SIN cupones no ve la entrada (hasCoupons: false)',
      'hasCoupons: false' in html)
r = c2.get('/api/daily/coupons')
check('su lista viene vacía', (r.get_json() or {}).get('coupons') == [])

print('── el código personal es SOLO de su dueño ──')
r = c2.post('/api/checkout/validate-code', json={'code': 'SPIN-VIEJO',
                                        'plan': 'premium', 'cycle': 'monthly'})
d = r.get_json() or {}
check('🔴 otra cuenta no puede canjearlo (para ella "no existe")',
      not d.get('ok') and d.get('error') == 'not_found', d)
r = c.post('/api/checkout/validate-code', json={'code': 'SPIN-VIEJO',
                                       'plan': 'premium', 'cycle': 'monthly'})
d = r.get_json() or {}
check('el dueño sí puede (25% aplicado)',
      bool(d.get('ok')) and d.get('discount_pct') == 25, d)

print('── /admin emite un código personal (el premio de un sorteo) ──')
with A.app.app_context():
    adm = A.User.query.filter_by(is_admin=True).first()
    adm.set_password(CL)
    A.db.session.commit()
    ADMIN = adm.username
ca = sesion(ADMIN)
ca.post('/admin/promo/create', data={'code': 'PREMIO-SORTEO',
                                     'discount_pct': 50, 'kind': 'discount',
                                     'valid_for': 'monthly', 'max_uses': 1,
                                     'restrict_to': 'GANADORA'})
with A.app.app_context():
    p = A.PromoCode.query.filter_by(code='PREMIO-SORTEO').first()
    check('el código nace atado a la ganadora (aunque se teclee en mayúsculas)',
          p is not None and p.restrict_user_id == GAN,
          p and p.restrict_user_id)
cg = sesion('ganadora')
r = cg.get('/api/daily/coupons')
cps = (r.get_json() or {}).get('coupons', [])
check('...y a ella le aparece en "Mis cupones"',
      any(x['code'] == 'PREMIO-SORTEO' for x in cps), cps)
html = cg.get('/app').get_data(as_text=True)
check('con la entrada del menú encendida', 'hasCoupons: true' in html)

print('── un ganador INEXISTENTE no crea un código suelto ──')
ca.post('/admin/promo/create', data={'code': 'HUERFANO', 'discount_pct': 90,
                                     'kind': 'discount', 'valid_for': 'monthly',
                                     'restrict_to': 'nadie-con-este-nombre'})
with A.app.app_context():
    check('🔴 el código NO se creó (un 90% general en silencio sería peor)',
          A.PromoCode.query.filter_by(code='HUERFANO').first() is None)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
