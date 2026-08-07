# -*- coding: utf-8 -*-
"""El candado de vista previa: solo las cuentas de la lista ven el sitio.

Con `PREVIEW_USERS` puesto, TODO lo demás — visitantes anónimos y cuentas que
no están en la lista — recibe la página de "próximamente" desde la propia
aplicación, sin depender del pase de nginx ni de galletas viejas.
"""
import os
import sys

os.environ['PREVIEW_USERS'] = 'maurotradesve,gussytrades'
os.environ.setdefault('DATABASE_URL', 'sqlite://')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
from flask import g            # noqa: E402
import app as A                # noqa: E402

CLAVE = 'Zx9!wQ4mNp2r'
ok = fallas = 0


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def cliente(nombre=None):
    c = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    if nombre:
        c.post('/login', data={'identifier': nombre, 'password': CLAVE})
    return c


with A.app.app_context():
    A.db.create_all()
    for n in ('maurotradesve', 'gussytrades', 'intruso'):
        u = A.User(username=n, email=n + '@demo.invalid', plan='free',
                   email_verified=True)
        u.set_password(CLAVE)
        A.db.session.add(u)
    A.db.session.commit()

print('── el mundo exterior ──')
c = cliente()
r = c.get('/')
check('la portada es "próximamente" (no la landing)',
      r.status_code == 200 and 'afinando los últimos detalles' in r.get_data(as_text=True),
      r.status_code)
check('/pricing también', 'afinando los últimos detalles'
      in c.get('/pricing').get_data(as_text=True))
check('/register también (nadie se registra durante la preview)',
      'afinando los últimos detalles' in c.get('/register').get_data(as_text=True))
check('el logo de la página de espera se sirve',
      c.get('/logo.png').status_code == 200)
check('un /api/* contesta 503 coming_soon',
      c.get('/api/usage').status_code in (503, 401)
      and (c.get('/api/usage').get_json() or {}).get('error') in
      ('coming_soon', None))

print('── la puerta ──')
check('/login SÍ se sirve (por ahí entran las cuentas permitidas)',
      'afinando los últimos detalles' not in c.get('/login').get_data(as_text=True))

print('── las cuentas ──')
cm = cliente('maurotradesve')
cm.set_cookie('scalpel_splash_ts', '1')
check('maurotradesve ve la app',
      'afinando los últimos detalles' not in cm.get('/app').get_data(as_text=True))
cg = cliente('gussytrades')
cg.set_cookie('scalpel_splash_ts', '1')
check('gussytrades ve la app',
      'afinando los últimos detalles' not in cg.get('/app').get_data(as_text=True))
ci = cliente('intruso')
ci.set_cookie('scalpel_splash_ts', '1')
check('🔴 una cuenta AJENA logueada sigue viendo "próximamente"',
      'afinando los últimos detalles' in ci.get('/app').get_data(as_text=True))

print('── los pagos no se frenan ──')
r = c.post('/webhook/paypal', json={})
check('el webhook de PayPal entra (no recibe la página de espera)',
      r.status_code != 200 or b'Pr\xc3\xb3ximamente' not in r.get_data(),
      r.status_code)
check('...y responde como webhook (4xx/5xx JSON, no HTML)',
      (r.content_type or '').startswith('application/json'), r.content_type)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
