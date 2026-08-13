# -*- coding: utf-8 -*-
"""El doble envío del registro: "tu usuario ya está tomado"… por ti mismo.

    venv/bin/python3 tools/test_registro_doble.py

Lo cazó el dueño creando la cuenta de su papá. El POST del registro envía el
correo de verificación por SMTP DENTRO de la petición (2-6 s con el botón
vivo); pulsó otra vez, el primer envío creó la cuenta y el segundo chocó
contra ella: "ese usuario ya está tomado" — con la cuenta perfectamente
creada por debajo. Solo se descubría intentando loguear.

El arreglo tiene dos capas y aquí se prueban las dos:
  · servidor: un reenvío del MISMO creador (mismo buzón canónico + la
    contraseña correcta) no es un conflicto — se le lleva a la pantalla del
    código, donde el primer envío lo habría dejado;
  · la prueba de identidad es la contraseña: un extraño con el username o el
    correo de otro sigue viendo el error de siempre;
  · cliente: el botón se deshabilita al primer clic (se comprueba que el
    template lleve el guard y las claves ×4).
"""
from __future__ import print_function

import io
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'rd.db')
os.environ.setdefault('SECRET_KEY', 'reg-doble')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                           # noqa: E402

OK = FALLOS = 0


def check(cond, texto):
    global OK, FALLOS
    print(('  ✅ ' if cond else '  ❌ ') + texto)
    if cond:
        OK += 1
    else:
        FALLOS += 1


FORM = {'birth_date': '1988-03-03', 'accept_terms': '1'}


def registra(c, usuario, correo, clave):
    d = dict(FORM, username=usuario, email=correo, password=clave)
    return c.post('/register', data=d, follow_redirects=False)


def main():
    global OK, FALLOS
    with A.app.app_context():
        A.db.create_all()
    with A.app.app_context():
        usuarios = A.User.query.count()

    print('\n══ 1 · la secuencia del dueño, tal cual ══')
    c = A.app.test_client()
    r = registra(c, 'papa', 'papa@gmail.com', 'debil')
    check(r.status_code == 200 and 'errPassword' in r.get_data(as_text=True),
          'contraseña corta → error, sin cuenta')
    r = registra(c, 'papa', 'papa@gmail.com', 'password1')
    check(r.status_code == 200 and 'errWeak' in r.get_data(as_text=True),
          'contraseña común → error, sin cuenta')
    r = registra(c, 'papa', 'papa@gmail.com', 'Fuerte99Zk')
    check(r.status_code == 302 and '/verify-email' in (r.headers.get('Location') or ''),
          'contraseña buena → a la pantalla del código')
    # …y el SEGUNDO clic (mismo formulario, la cuenta ya existe):
    r = registra(c, 'papa', 'papa@gmail.com', 'Fuerte99Zk')
    check(r.status_code == 302 and '/verify-email' in (r.headers.get('Location') or ''),
          '🔑 el doble clic ya NO dice "usuario tomado": vuelve al código')
    with A.app.app_context():
        check(A.User.query.count() == usuarios + 1,
              'y sigue habiendo UNA sola cuenta (no se duplicó nada)')

    print('\n══ 2 · el reintento vale aunque cambie el detalle ══')
    c2 = A.app.test_client()
    # mismo buzón (alias de Gmail = mismo canónico) y la contraseña correcta,
    # pero probó OTRO username: es la misma persona → al código de SU cuenta.
    r = registra(c2, 'papa2', 'p.a.pa@gmail.com', 'Fuerte99Zk')
    check(r.status_code == 302 and '/verify-email' in (r.headers.get('Location') or ''),
          'mismo buzón (alias) + su contraseña, otro username → a SU código')
    with A.app.app_context():
        check(A.User.query.filter_by(username='papa2').first() is None,
              'sin crear ninguna cuenta nueva por el camino')

    print('\n══ 3 · un EXTRAÑO sigue viendo los errores de siempre ══')
    c3 = A.app.test_client()
    r = registra(c3, 'papa', 'otro@correo.invalid', 'Cualquiera77')
    check(r.status_code == 200 and 'reg.errUser"' in r.get_data(as_text=True),
          'username ajeno + otro buzón → "usuario tomado"')
    r = registra(c3, 'intruso', 'papa@gmail.com', 'Adivino1234')
    check(r.status_code == 200 and 'reg.errEmail"' in r.get_data(as_text=True),
          'buzón ajeno + contraseña equivocada → "correo registrado"')
    r = registra(c3, 'papa', 'papa@gmail.com', 'NoEsLaClave9')
    check(r.status_code == 200 and 'reg.errUser"' in r.get_data(as_text=True),
          'mismo usuario y buzón pero SIN la contraseña → error (la contraseña '
          'es la prueba de identidad)')
    with A.app.app_context():
        check(A.User.query.count() == usuarios + 1, 'y ninguna cuenta más')

    print('\n══ 4 · verificada en otra pestaña → el reintento loguea ══')
    with A.app.app_context():
        u = A.User.query.filter_by(username='papa').first()
        u.email_verified = True
        A.db.session.commit()
    c4 = A.app.test_client()
    r = registra(c4, 'papa', 'papa@gmail.com', 'Fuerte99Zk')
    check(r.status_code == 302, 'reintento tras verificar → redirige')
    r = c4.get('/verify-email', follow_redirects=False)
    check(r.status_code == 302 and 'verify' not in (r.headers.get('Location') or ''),
          'y /verify-email lo pasa de largo: sesión iniciada')

    print('\n══ 5 · el cliente: un solo envío por clic ══')
    html = io.open(os.path.join(RAIZ, 'scalpel', 'templates', 'register.html'),
                   encoding='utf-8').read()
    check('enviado = true' in html and 'btn.disabled = true' in html,
          'el botón se deshabilita en el primer envío')
    check('checkValidity' in html,
          'pero NO se deshabilita si el navegador rechaza el formulario '
          '(required/minlength): sin POST no puede quedarse muerto')
    js = io.open(os.path.join(RAIZ, 'scalpel', 'static', 'auth.js'),
                 encoding='utf-8').read()
    check(js.count("'reg.creating':") == 4, "clave 'reg.creating' en los 4 idiomas")
    check('window.AuthI18n' in js, 'auth.js expone el traductor para el botón')

    print('\nRESULTADO: %d/%d' % (OK, OK + FALLOS))
    return 0 if FALLOS == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
