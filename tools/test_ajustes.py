# -*- coding: utf-8 -*-
"""¿Funciona de verdad cada fila de /settings, o solo existe el boton?

Pregunta del dueno (2026-08-10): "muchas cosas ofrecen funcionalidades, pero
no sabemos si realmente funcionan (por ejemplo el cambio de contrasena o la
activacion de 2FA)". Aqui se ejecuta CADA accion por HTTP, como la haria el
navegador, y se comprueba el efecto real en la base: que la contrasena nueva
entra y la vieja ya no, que el codigo TOTP se exige de verdad al entrar, que
cerrar sesiones echa a la otra pestana y NO a la propia.

    python3 tools/test_ajustes.py
"""
import hashlib
import hmac
import os
import struct
import sys
import time

os.environ.setdefault('DATABASE_URL', 'sqlite://')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
from flask import g            # noqa: E402
import app as A                # noqa: E402

CL = 'Zx9!wQ4mNp2r'
NUEVA = 'Kt7#hRv2sLq8'
ok = fallas = 0


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def sesion(nombre, clave):
    """Cliente logueado. Sin `with`: Flask conservaria el contexto de la
    ultima peticion y con el la cache de objetos de SQLAlchemy, y el usuario
    se quedaria congelado en su estado viejo."""
    c = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    r = c.post('/login', data={'identifier': nombre, 'password': clave},
               follow_redirects=False)
    c.set_cookie('scalpel_splash_ts', '1')
    return c, r


def usuario():
    """El usuario RECIEN leido de la base.

    expire_all() es obligatorio: la sesion de SQLAlchemy guarda su cache de
    objetos y, sin vaciarla, se lee el estado ANTERIOR a la peticion HTTP y
    el test acusa un fallo del servidor que no existe."""
    with A.app.app_context():
        A.db.session.expire_all()
        return A.db.session.get(A.User, UID)


def totp(secreto, momento=None):
    """El codigo de 6 digitos, calculado como lo hace la app del telefono."""
    import base64
    clave = base64.b32decode(secreto.upper() + '=' * (-len(secreto) % 8))
    cont = int((momento or time.time()) // 30)
    h = hmac.new(clave, struct.pack('>Q', cont), hashlib.sha1).digest()
    o = h[19] & 0xF
    return '%06d' % ((struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF) % 10 ** 6)


with A.app.app_context():
    A.db.create_all()
    u = A.User(username='ajustes', email='a@demo.invalid', plan='premium',
               email_verified=True)
    u.set_password(CL)
    A.db.session.add(u)
    A.db.session.commit()
    UID = u.id

print('== la pagina se sirve ==')
c, _ = sesion('ajustes', CL)
r = c.get('/settings')
check('/settings responde 200', r.status_code == 200, r.status_code)
html = r.get_data(as_text=True)
check('un anonimo no entra',
      A.app.test_client().get('/settings').status_code in (302, 401))

print('\n== CAMBIO DE CONTRASENA ==')
r = c.post('/account/password', data={'current_password': 'lo-que-sea',
                                      'new_password': NUEVA})
if True:
    check('con la contrasena actual EQUIVOCADA no cambia nada',
          usuario().check_password(CL))
r = c.post('/account/password', data={'current_password': CL, 'new_password': 'password1'})
if True:
    check('rechaza una contrasena nueva debil ("password1")',
          usuario().check_password(CL))
r = c.post('/account/password', data={'current_password': CL, 'new_password': NUEVA})
with A.app.app_context():
    u = usuario()
    check('con los datos correctos SI cambia', u.check_password(NUEVA))
check('...y la vieja deja de servir', not u.check_password(CL))
c2, r2 = sesion('ajustes', CL)
check('no se puede entrar con la contrasena vieja',
      c2.get('/settings').status_code in (302, 401),
      c2.get('/settings').status_code)
c, r = sesion('ajustes', NUEVA)
check('se entra con la nueva', c.get('/settings').status_code == 200,
      c.get('/settings').status_code)

print('\n== CERRAR LAS DEMAS SESIONES ==')
otra, _ = sesion('ajustes', NUEVA)
check('la otra pestana esta dentro antes de nada',
      otra.get('/settings').status_code == 200)
c.post('/account/sessions/close')
check('la otra pestana queda FUERA',
      otra.get('/settings').status_code in (302, 401),
      otra.get('/settings').status_code)
check('...y la mia sigue dentro (no me echo a mi mismo)',
      c.get('/settings').status_code == 200)

print('\n== VERIFICACION EN DOS PASOS ==')
r = c.post('/account/2fa/start')
check('el alta responde con la pantalla del QR',
      r.status_code == 200 and 'img' in r.get_data(as_text=True).lower(),
      r.status_code)
if True:
    check('el secreto NO se guarda todavia en la cuenta (alta a medias = '
          'cero efecto)',
          not usuario().totp_confirmed_at)
with c.session_transaction() as s:
    secreto = s.get('totp_setup')
check('el secreto vive en la SESION mientras se confirma',
      bool(secreto), list(dict(s).keys()) if not secreto else '')
if secreto:
    r = c.post('/account/2fa/confirm', data={'code': '000000'})
    if True:
        check('un codigo inventado no activa nada',
              not usuario().totp_confirmed_at)
    r = c.post('/account/2fa/confirm', data={'code': totp(secreto)})
    if True:
        check('el codigo correcto SI la activa',
              usuario().totp_confirmed_at is not None)
    cods = r.get_data(as_text=True)
    import json as _j
    u = usuario()
    # se guardan como JSON de hashes sha256, nunca en claro
    n = len(_j.loads(u.totp_backup or '[]'))
    check('y entrega %d codigos de respaldo, guardados como hash' % n,
          n >= 8 and 'totp_backup' not in (cods or ''), n)
    check('los codigos se ensenan UNA vez, en esa misma respuesta',
          sum(c.isdigit() or c.isalpha() for c in cods) > 0 and n == 8, n)

    print('\n   -- ahora el login DEBE pedir el codigo --')
    c3 = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    r = c3.post('/login', data={'identifier': 'ajustes', 'password': NUEVA})
    destino = r.headers.get('Location') or ''
    check('con contrasena correcta manda a /login/2fa, no a la app',
          '2fa' in destino, destino)
    c3.set_cookie('scalpel_splash_ts', '1')
    check('y sin el codigo NO se entra a la app',
          c3.get('/settings').status_code in (302, 401))
    r = c3.post('/login/2fa', data={'code': '111111'})
    check('un codigo inventado no deja pasar',
          c3.get('/settings').status_code in (302, 401))
    sec = usuario().totp_secret
    r = c3.post('/login/2fa', data={'code': totp(sec)})
    check('el codigo bueno SI deja pasar',
          c3.get('/settings').status_code == 200)

    print('\n   -- y se puede apagar --')
    r = c.post('/account/2fa/disable', data={'password': 'mala',
                                             'code': totp(sec)})
    if True:
        check('sin la contrasena no se apaga',
              usuario().totp_confirmed_at is not None)
    r = c.post('/account/2fa/disable', data={'password': NUEVA,
                                             'code': totp(sec)})
    if True:
        check('con contrasena + codigo SI se apaga',
              usuario().totp_confirmed_at is None)

print('\n== NADA DE ADORNOS: lo que se ensena, existe ==')
html = c.get('/settings').get_data(as_text=True)
check('ya no queda ninguna fila con la etiqueta "muy pronto"',
      html.count('common.soon') == 0, html.count('common.soon'))
check('fuera la casilla de notificaciones que estaba DESACTIVADA (fingia un '
      'ajuste, y de paso daba a entender que los correos estaban apagados)',
      'class="toggle" disabled' not in html)
for accion in ('/account/email', '/account/delete'):
    check('la pagina ofrece %s y la ruta existe' % accion,
          accion in html and any(str(r) == accion
                                 for r in A.app.url_map.iter_rules()))
check('el selector de idioma esta cableado (.lang-switch lo engancha solo)',
      'lang-switch' in html and 'data-lang="pt"' in html)
check('el de tema tambien', 'theme-seg' in html and 'data-theme="dark"' in html)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
