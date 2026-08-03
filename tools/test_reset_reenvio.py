# -*- coding: utf-8 -*-
"""El reenvio del enlace de recuperacion: que funcione y que no se convierta en
una herramienta para inundar el buzon de otro."""
import os, sys, tempfile
sys.path.insert(0, '/home/user/TRADINGBOT2.0/scalpel')
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'r.db')
import app as A
from datetime import datetime, timezone, timedelta

ENVIADOS = []
A.send_reset_email = lambda to, url: (ENVIADOS.append(to), True)[1]

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('  %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

with A.app.app_context():
    A.db.create_all()
    u = A.User(username='ana', email='ana@demo.invalid', plan='free', email_verified=True)
    u.set_password('Xk9!mQ2#pL5v'); A.db.session.add(u); A.db.session.commit()

def sin_espera(c):
    """Viaja en el tiempo: mueve los intentos 61s atras para saltarse el minuto."""
    with c.session_transaction() as ses:
        ses['reset_tries'] = [(datetime.fromisoformat(t) - timedelta(seconds=61)).isoformat()
                              for t in ses.get('reset_tries', [])]

with A.app.test_client() as c:
    r = c.post('/forgot-password', data={'email': 'ana@demo.invalid'})
    cuerpo = r.get_data(as_text=True)
    check('envia el enlace', ENVIADOS == ['ana@demo.invalid'], ENVIADOS)
    check('ofrece reenviar', 'fp.again' in cuerpo)
    check('recuerda el correo para el reenvio', 'value="ana@demo.invalid"' in cuerpo)
    check('aclara que es un ENLACE, no un codigo', 'fp.hint' in cuerpo)

    ENVIADOS.clear()
    r = c.post('/forgot-password', data={'email': 'ana@demo.invalid'})
    check('un reenvio inmediato NO manda otro correo', ENVIADOS == [], ENVIADOS)
    check('y lo dice', 'fp.wait' in r.get_data(as_text=True))

    sin_espera(c)
    r = c.post('/forgot-password', data={'email': 'ana@demo.invalid'})
    check('pasado el minuto SI reenvia', ENVIADOS == ['ana@demo.invalid'], ENVIADOS)

    for _ in range(6):
        sin_espera(c)
        r = c.post('/forgot-password', data={'email': 'ana@demo.invalid'})
    check('a los 5 por hora corta', 'fp.throttled' in r.get_data(as_text=True))

    ENVIADOS.clear()
    with A.app.test_client() as c2:
        r = c2.post('/forgot-password', data={'email': 'noexiste@demo.invalid'})
        check('un correo que NO existe no manda nada', ENVIADOS == [], ENVIADOS)
        check('pero responde igual (no revela quien tiene cuenta)',
              'fp.sent' in r.get_data(as_text=True))

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
