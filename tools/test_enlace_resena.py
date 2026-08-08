# -*- coding: utf-8 -*-
"""El enlace "deja tu reseña" del correo del recibo.

Lo que prueba, y por qué: la intención NO puede viajar en la URL. `/app`
desvía a `/welcome` cuando falta el pase del splash, y una redirección se lleva
por delante cualquier `?parametro` — que es exactamente por qué la primera
versión (`/app?review=1`) llevaba al sitio sin abrir nada. Va en la SESIÓN.
"""
import os
import sys

os.environ.setdefault('DATABASE_URL', 'sqlite://')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
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


with A.app.app_context():
    A.db.create_all()
    u = A.User(username='resenadora', email='r@demo.invalid', plan='premium',
               email_verified=True)
    u.set_password(CL)
    A.db.session.add(u)
    A.db.session.commit()

c = A.app.test_client()
c.post('/login', data={'identifier': 'resenadora', 'password': CL})

print('── el enlace del correo ──')
r = c.get('/review')
check('/review manda a la app',
      r.status_code == 302 and '/app' in r.headers['Location'],
      '%s %s' % (r.status_code, r.headers.get('Location')))

# El caso que ROMPÍA la versión anterior: sin pase de splash, /app desvía.
r = c.get('/app')
check('sin pase de splash, /app desvía a /welcome',
      r.status_code == 302 and 'welcome' in r.headers['Location'])

c.set_cookie('scalpel_splash_ts', '1')
html = c.get('/app').get_data(as_text=True)
check('🔴 la intención SOBREVIVE al desvío — el modal se abre',
      'reviewNow: true' in html)

# Y se consume: la siguiente visita ya no lo reabre.
c.set_cookie('scalpel_splash_ts', '1')
html2 = c.get('/app').get_data(as_text=True)
check('se consume: al volver a entrar ya no se reabre',
      'reviewNow: false' in html2)

print('── sin enlace, los tiempos de siempre mandan ──')
c2 = A.app.test_client()
c2.post('/login', data={'identifier': 'resenadora', 'password': CL})
c2.set_cookie('scalpel_splash_ts', '1')
html3 = c2.get('/app').get_data(as_text=True)
check('una visita normal NO fuerza el modal',
      'reviewNow: false' in html3)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
