# -*- coding: utf-8 -*-
"""El código de verificación que "no sirve": cada login lo mataba por detrás.

    venv/bin/python3 tools/test_codigo_verificacion.py

Lo cazó el dueño verificando la cuenta de su papá: el código llegaba al buzón
del padre, y cada intento de login del hijo (cuenta aún sin verificar)
REGENERABA el código e invalidaba el que el padre le había dictado. "Código
incorrecto" con el código perfectamente bien tecleado. Es letal justo cuando
el buzón es de otra persona — el caso de cualquier padre/hijo/pareja — y
también para el que abre el correo en el teléfono y el sitio en la PC.

Regla nueva: el login solo genera código si NO hay uno vigente. Pedir uno
nuevo a propósito sigue existiendo: el botón "reenviar código".
"""
from __future__ import print_function

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'cv.db')
os.environ.setdefault('SECRET_KEY', 'cod-verif')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                           # noqa: E402

OK = FALLOS = 0
ENVIADOS = []          # cada correo de verificación que el sistema "manda"


def check(cond, texto):
    global OK, FALLOS
    print(('  ✅ ' if cond else '  ❌ ') + texto)
    if cond:
        OK += 1
    else:
        FALLOS += 1


def main():
    global OK, FALLOS
    A.send_verification_email = lambda email, code: ENVIADOS.append(code) or True
    with A.app.app_context():
        A.db.create_all()

    CL = 'Fuerte99Zk'
    c = A.app.test_client()

    print('\n══ 1 · la secuencia del dueño, con reloj ══')
    r = c.post('/register', data={'username': 'papa', 'email': 'papa@d.invalid',
                                  'password': CL, 'birth_date': '1960-01-15',
                                  'accept_terms': '1'}, follow_redirects=False)
    check(r.status_code == 302 and len(ENVIADOS) == 1,
          'el registro manda el código #1 (correos enviados: %d)' % len(ENVIADOS))
    codigo1 = ENVIADOS[-1]

    # …el hijo, atascado, prueba el login DOS veces desde otra pestaña:
    c2 = A.app.test_client()
    for _ in range(2):
        c2.post('/login', data={'identifier': 'papa', 'password': CL},
                follow_redirects=False)
    check(len(ENVIADOS) == 1,
          '🔑 dos logins con código vigente: NO se regenera ni se manda nada '
          '(correos: %d — antes iban 3, y el #1 estaba muerto)' % len(ENVIADOS))
    with A.app.app_context():
        vivo = A.User.query.filter_by(username='papa').first().verification_code
    check(vivo == codigo1, 'el código del buzón del padre SIGUE siendo el válido')

    # …y el código dictado ahora entra:
    r = c2.post('/verify-email', data={'code': codigo1}, follow_redirects=False)
    check(r.status_code == 302, '🔑 el código #1 verifica la cuenta '
          '(el caso del dueño: antes daba "incorrecto")')
    with A.app.app_context():
        check(A.User.query.filter_by(username='papa').first().email_verified,
              'la cuenta queda verificada y logueada')

    print('\n══ 2 · el código CADUCADO sí se repone en el login ══')
    r = c.post('/register', data={'username': 'lenta', 'email': 'lenta@d.invalid',
                                  'password': CL, 'birth_date': '1990-02-02',
                                  'accept_terms': '1'}, follow_redirects=False)
    viejo = ENVIADOS[-1]
    with A.app.app_context():
        u = A.User.query.filter_by(username='lenta').first()
        u.verification_expires = datetime.now(timezone.utc) - timedelta(minutes=1)
        A.db.session.commit()
    antes = len(ENVIADOS)
    c3 = A.app.test_client()
    c3.post('/login', data={'identifier': 'lenta', 'password': CL},
            follow_redirects=False)
    check(len(ENVIADOS) == antes + 1,
          'login con código caducado → manda uno nuevo')
    nuevo = ENVIADOS[-1]
    r = c3.post('/verify-email', data={'code': viejo}, follow_redirects=False)
    check(r.status_code == 200, 'el caducado ya no vale')
    r = c3.post('/verify-email', data={'code': nuevo}, follow_redirects=False)
    check(r.status_code == 302, 'el nuevo sí')

    print('\n══ 3 · "reenviar código" sigue siendo la vía explícita ══')
    c.post('/register', data={'username': 'rein', 'email': 'rein@d.invalid',
                              'password': CL, 'birth_date': '1991-03-03',
                              'accept_terms': '1'}, follow_redirects=False)
    primero = ENVIADOS[-1]
    antes = len(ENVIADOS)
    c.post('/resend-code', follow_redirects=False)
    check(len(ENVIADOS) == antes + 1, 'el botón reenvía uno nuevo')
    segundo = ENVIADOS[-1]
    check(primero != segundo, 'y ES nuevo (el reenvío sí rota a propósito)')
    r = c.post('/verify-email', data={'code': segundo}, follow_redirects=False)
    check(r.status_code == 302, 'el reenviado verifica')

    print('\n══ 4 · un código equivocado sigue siendo equivocado ══')
    # ⚠️ cliente NUEVO: `c` quedó LOGUEADO al verificar en la sección 3, y a
    # un usuario con sesión /register lo redirige a /welcome sin crear nada.
    c = A.app.test_client()
    c.post('/register', data={'username': 'mal', 'email': 'mal@d.invalid',
                              'password': CL, 'birth_date': '1992-04-04',
                              'accept_terms': '1'}, follow_redirects=False)
    r = c.post('/verify-email', data={'code': '000000'}, follow_redirects=False)
    cuerpo = r.get_data(as_text=True)
    check(r.status_code == 200 and 've.errInvalid' in cuerpo,
          'código falso → error, sin verificar')
    r = c.post('/verify-email', data={'code': ENVIADOS[-1]}, follow_redirects=False)
    check(r.status_code == 302, 'y el bueno entra después del fallo')

    print('\nRESULTADO: %d/%d' % (OK, OK + FALLOS))
    return 0 if FALLOS == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
