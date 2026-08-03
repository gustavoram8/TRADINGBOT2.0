# -*- coding: utf-8 -*-
"""Pulsar "Pasar a Premium" sin haber entrado tiene que llevarte AL PREMIUM,
tengas cuenta o no. Antes te dejaba en /register sin memoria del plan."""
import os, sys, tempfile
sys.path.insert(0, '/home/user/TRADINGBOT2.0/scalpel')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'n.db')
import app as A
from flask import g

A.send_verification_email = lambda to, code: True
A.send_security_email = lambda u, k, **kw: True

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('  %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

DEST = '/checkout?plan=premium&cycle=monthly'
with A.app.app_context():
    A.db.create_all()
    u = A.User(username='hermano', email='h@demo.invalid', plan='free', email_verified=True)
    u.set_password('ClaveDelHermano9!')
    A.db.session.add(u); A.db.session.commit()

print('— YA TIENE CUENTA: pulsa "Pasar a Premium" sin haber entrado —')
with A.app.test_client() as c:
    r = c.get(DEST)
    check('el checkout lo manda a identificarse', r.status_code == 302, r.status_code)
    destino = r.headers.get('Location', '')
    check('y el enlace se acuerda del plan', 'next=' in destino and 'premium' in destino, destino)
    r = c.get(destino)
    check('la pantalla de entrar carga', r.status_code == 200, r.status_code)
    check('lleva el destino escondido en el formulario', 'name="next"' in r.get_data(as_text=True))
    check('y el enlace de "crear cuenta" tambien', 'register?next=' in r.get_data(as_text=True))
    r = c.post('/login', data={'identifier': 'h@demo.invalid',
                               'password': 'ClaveDelHermano9!', 'next': DEST})
    check('al entrar aterriza EN EL PREMIUM', DEST in (r.headers.get('Location') or ''),
          r.headers.get('Location'))

print('— NO TIENE CUENTA: se registra desde ahi —')
with A.app.test_client() as c:
    with A.app.app_context():
        g.pop('_login_user', None)
    r = c.post('/register', data={'username': 'nuevo', 'email': 'n@demo.invalid',
                                  'password': 'Xk9!mQ2#pL5v', 'birth_date': '1995-04-12',
                                  'accept_terms': '1', 'next': DEST})
    check('lo manda a verificar el correo', '/verify-email' in (r.headers.get('Location') or ''),
          r.headers.get('Location'))
    with A.app.app_context():
        codigo = A.User.query.filter_by(email='n@demo.invalid').first().verification_code
    r = c.post('/verify-email', data={'code': codigo})
    check('tras verificar aterriza EN EL PREMIUM', DEST in (r.headers.get('Location') or ''),
          r.headers.get('Location'))

print('— y que nadie use esto para mandarte a otro sitio —')
with A.app.test_client() as c:
    with A.app.app_context():
        g.pop('_login_user', None)
    for malo in ('https://sitio-falso.com', '//sitio-falso.com', 'javascript:alert(1)'):
        r = c.post('/login', data={'identifier': 'h@demo.invalid',
                                   'password': 'ClaveDelHermano9!', 'next': malo})
        dest = r.headers.get('Location') or ''
        check('rechaza %-24s' % malo, 'sitio-falso' not in dest and 'javascript' not in dest, dest)
        c.get('/logout')
        with A.app.app_context():
            g.pop('_login_user', None)

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
