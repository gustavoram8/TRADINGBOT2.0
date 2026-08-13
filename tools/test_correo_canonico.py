# -*- coding: utf-8 -*-
"""Un buzón = una cuenta: los alias de Gmail ya no multiplican registros.

El agujero que cierra: Gmail entrega juan@, j.u.a.n@ y juan+2@gmail.com en LA
MISMA bandeja (documentado por Google), pero para la base eran tres cadenas
distintas — tres cuentas Free, o la vuelta de un baneado escribiendo "+2" en
su propio correo. Coste del truco: cero. Eso es lo que deja de funcionar.

Igual de importante es lo que NO hace: en un dominio corriente los puntos SÍ
distinguen personas (juan.perez@ ≠ juanperez@miempresa.com) y ahí no se toca
nada — el error caro sería negarle el registro a un cliente real.
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


def registra(usuario, correo):
    c = A.app.test_client()
    return c.post('/register', data={
        'username': usuario, 'email': correo, 'password': CL,
        'birth_date': '1999-05-05', 'accept_terms': '1'})


print('── la función canónica, contra las reglas documentadas ──')
f = A._correo_canonico
check('gmail: el "+etiqueta" se cae',
      f('juan+2@gmail.com') == 'juan@gmail.com', f('juan+2@gmail.com'))
check('gmail: los puntos se caen',
      f('j.u.a.n@gmail.com') == 'juan@gmail.com')
check('gmail: mayúsculas y combinaciones',
      f('J.uAn+tradeable@GMAIL.com') == 'juan@gmail.com')
check('outlook: el "+" se cae, los puntos SE QUEDAN',
      f('juan.p+x@outlook.com') == 'juan.p@outlook.com',
      f('juan.p+x@outlook.com'))
check('🔴 dominio corriente: NO se toca nada (los puntos distinguen personas)',
      f('juan.perez@miempresa.com') == 'juan.perez@miempresa.com')
check('dominio corriente: ni siquiera el "+" (regla no documentada ahí)',
      f('juan+2@miempresa.com') == 'juan+2@miempresa.com')
check('basura sin @: no revienta', f('no-es-correo') == 'no-es-correo')

print('── el registro: un buzón, una cuenta ──')
with A.app.app_context():
    A.db.create_all()
r = registra('juan', 'juan@gmail.com')
with A.app.app_context():
    u = A.User.query.filter_by(username='juan').first()
    check('la cuenta base se crea', u is not None)
    check('y nace con su canónico sellado',
          u.email_canonical == 'juan@gmail.com', u.email_canonical)
    check('el correo ORIGINAL no se toca (es a donde se escribe)',
          u.email == 'juan@gmail.com')

# ⚠️ REENCUADRADO (2026-08-13, arreglo del doble envío del registro): estas
# pruebas usaban LA MISMA contraseña que la cuenta base, y "mismo buzón + su
# contraseña" ahora significa "la misma persona reintentando" — se le lleva a
# la pantalla del código de SU cuenta en vez de decirle "ya registrado". La
# regla que este archivo vigila (UN buzón = UNA cuenta) no se movió: en ningún
# caso se crea una segunda cuenta, y un extraño sin la contraseña sigue viendo
# el rechazo. La plantilla renderiza la clave traducida (reg.errEmail), no el
# nombre interno del error: se comprueba lo que el USUARIO ve.
r = registra('juan2', 'juan+2@gmail.com')
check('🔴 el alias "+2" con SU contraseña: a la verificación de su cuenta',
      r.status_code == 302 and 'verify' in (r.headers.get('Location') or ''),
      r.status_code)
r = registra('juan3', 'J.u.a.n@gmail.com')
check('🔴 el alias con puntos, igual',
      r.status_code == 302 and 'verify' in (r.headers.get('Location') or ''))
c_intruso = A.app.test_client()
r = c_intruso.post('/register', data={
    'username': 'juan4', 'email': 'juan+9@gmail.com', 'password': 'OtraClave77z',
    'birth_date': '1999-05-05', 'accept_terms': '1'})
check('🔴 el alias SIN la contraseña (un extraño) se rechaza como ya registrado',
      r.status_code == 200 and 'reg.errEmail' in r.get_data(as_text=True),
      r.status_code)
with A.app.app_context():
    # init_db siembra un admin: se cuentan solo las cuentas del test
    check('y no se creó ninguna cuenta nueva',
          A.User.query.filter(A.User.username.like('juan%')).count() == 1,
          A.User.query.filter(A.User.username.like('juan%')).count())

print('── lo que debe seguir PASANDO ──')
r = registra('juanp', 'juan.perez@miempresa.com')
r = registra('juanp2', 'juanperez@miempresa.com')
with A.app.app_context():
    check('🔴 en un dominio corriente, juan.perez y juanperez son DOS cuentas',
          A.User.query.filter_by(username='juanp').first() is not None
          and A.User.query.filter_by(username='juanp2').first() is not None)
r = registra('otrojuan', 'juan@outlook.com')
with A.app.app_context():
    check('el mismo local en OTRO proveedor es otra cuenta',
          A.User.query.filter_by(username='otrojuan').first() is not None)

print('── la cuenta VIEJA sin canónico (anterior a la regla) ──')
with A.app.app_context():
    from sqlalchemy import text
    A.db.session.execute(text(
        "INSERT INTO user (username, email, email_canonical, password_hash, "
        "plan, is_admin, email_verified, is_banned, xp, rank, rank_celebrated, "
        "first_preflight_xp, cancel_at_period_end) "
        "VALUES ('veterano','vete.rano@gmail.com', NULL, 'x','free',0,1,0,0,1,"
        "0,0,0)"))
    A.db.session.commit()
    A._migrate_user_email_canonical_column()
    vet = A.User.query.filter_by(username='veterano').first()
    check('🔴 el backfill le calcula el canónico a la fila vieja',
          vet.email_canonical == 'veterano@gmail.com', vet.email_canonical)
r = registra('imitador', 'veterano+nuevo@gmail.com')
check('🔴 y su alias ya NO puede registrarse',
      'reg.errEmail' in r.get_data(as_text=True))

print('── correrla dos veces no duplica ni rompe (idempotente) ──')
with A.app.app_context():
    antes = A.User.query.count()
    A._migrate_user_email_canonical_column()
    check('sigue todo igual', A.User.query.count() == antes,
          A.User.query.count())

print('── 🔴 lo que NO puede romperse: que un cliente YA REGISTRADO entre ──')
# El riesgo caro de este cambio no es el registro, es dejar fuera a alguien
# que ya paga. Login y recuperación miran `email`/username, nunca el canónico.
with A.app.app_context():
    ya = A.User(username='conalias', email='pepe+work@gmail.com',
                email_canonical=A._correo_canonico('pepe+work@gmail.com'),
                plan='premium', email_verified=True)
    ya.set_password(CL)
    A.db.session.add(ya)
    antiguo = A.User(username='antiguo', email='vieja@hotmail.com',
                     plan='standard', email_verified=True)   # sin canónico
    antiguo.set_password(CL)
    A.db.session.add(antiguo)
    A.db.session.commit()

for etiqueta, ident in (('cuyo correo real LLEVA "+", por usuario', 'conalias'),
                        ('cuyo correo real LLEVA "+", por su correo',
                         'pepe+work@gmail.com'),
                        ('anterior al cambio, por usuario', 'antiguo'),
                        ('anterior al cambio, por correo', 'vieja@hotmail.com')):
    cli = A.app.test_client()
    resp = cli.post('/login', data={'identifier': ident, 'password': CL})
    check('entra el cliente %s' % etiqueta,
          resp.status_code == 302
          and 'login' not in (resp.headers.get('Location') or ''),
          '%s %s' % (resp.status_code, resp.headers.get('Location')))

cli = A.app.test_client()
resp = cli.post('/forgot-password', data={'email': 'pepe+work@gmail.com'})
check('y "olvidé mi contraseña" acepta su correo con "+"',
      resp.status_code in (200, 302), resp.status_code)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
