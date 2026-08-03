# -*- coding: utf-8 -*-
"""El candado de /analyze: cerrado para desconocidos, abierto para clientes."""
import os, sys, io, tempfile
sys.path.insert(0, '/home/user/TRADINGBOT2.0/scalpel')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 's.db')
import app as A

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('  %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

with A.app.app_context():
    A.db.create_all()
    u = A.User(username='cliente', email='c@demo.invalid', plan='premium',
               email_verified=True)
    u.set_password('Xk9!mQ2#pL5v')
    A.db.session.add(u); A.db.session.commit()

png = (b'\x89PNG\r\n\x1a\n' + b'\x00' * 64)

print('— un desconocido —')
with A.app.test_client() as c:
    r = c.post('/analyze')
    check('sin nada: 401', r.status_code == 401, r.status_code)
    c.set_cookie('scalpel_anon', 'inventado-123')
    r = c.post('/analyze')
    check('con el cookie muerto inventado: sigue 401', r.status_code == 401, r.status_code)
    r = c.post('/validate')
    check('/validate tambien 401', r.status_code == 401, r.status_code)
    r = c.get('/api/usage')
    check('/api/usage tambien 401', r.status_code == 401, r.status_code)

print('— un cliente de verdad —')
with A.app.test_client() as c:
    r = c.post('/login', data={'identifier': 'cliente', 'password': 'Xk9!mQ2#pL5v'},
               follow_redirects=False)
    check('inicia sesion', r.status_code in (302, 303), r.status_code)
    r = c.get('/api/usage')
    check('/api/usage le responde', r.status_code == 200, r.status_code)
    # No se llama a la IA de verdad: basta con ver que PASA el candado y llega
    # a la validacion de la imagen (401 = puerta cerrada, otra cosa = paso).
    r = c.post('/analyze', data={'screenshot': (io.BytesIO(png), 'c.png')},
               content_type='multipart/form-data')
    check('/analyze le deja pasar el candado', r.status_code != 401, r.status_code)

print('— cabeceras de seguridad —')
with A.app.test_client() as c:
    h = c.get('/').headers
    for k, v in (('X-Content-Type-Options', 'nosniff'), ('X-Frame-Options', 'DENY'),
                 ('Referrer-Policy', 'strict-origin-when-cross-origin')):
        check(k, h.get(k) == v, h.get(k))

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
