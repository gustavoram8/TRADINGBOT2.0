# -*- coding: utf-8 -*-
"""Recorrido COMPLETO de una cuenta: registro → verificación → sesión →
recuperación de contraseña → compra de plan → renovación → caducidad.

Existe para responder una pregunta concreta del dueño antes de conectar el
cobro real: *¿está bien cableado todo lo que hay ANTES del dinero?* Cada
comprobación ejecuta el camino que haría una persona, no una función suelta.

    cd /var/www/TRADINGBOT2.0 && python3 tools/test_circuito_completo.py
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scalpel'))
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'c.db'))
# Hace falta ALGUNA forma de cobrar, o el checkout responde "el cobro abre
# pronto" y no crea pedido — que es justo lo que debe hacer en produccion
# hoy. Aqui se enciende la via manual para poder recorrer la compra entera.
os.environ['MANUAL_USDT_ENABLED'] = '1'
import app as A                                                  # noqa: E402
from flask import g                                              # noqa: E402

# El correo no se envía de verdad: se intercepta para poder AFIRMAR qué salió
# y qué no. Media investigación de esta semana fue exactamente eso.
BUZON = []
A.send_verification_email = lambda to, code: (BUZON.append(('verificacion', to, code)), True)[1]
A.send_reset_email = lambda to, url: (BUZON.append(('reseteo', to, url)), True)[1]
A.send_security_email = lambda u, k, **kw: (BUZON.append(('seguridad', u.email, k)), True)[1]
A.send_payment_alert_email = lambda *a, **k: True

PASS = FAIL = 0
CLAVE = 'Xk9!mQ2#pL5v'


def seccion(t):
    print('\n\033[1m── %s\033[0m' % t)


def check(nombre, cond, detalle=''):
    global PASS, FAIL
    ok = bool(cond)
    PASS += ok
    FAIL += (not ok)
    print('   %s %s%s' % ('ok   ' if ok else 'FALLA', nombre,
                          '' if ok else '   → %s' % detalle))


def limpiar_sesion():
    """Flask-Login cachea el usuario en `g` (contexto de APP): sin esto, la
    segunda petición del script corre como el primer usuario."""
    with A.app.app_context():
        g.pop('_login_user', None)


def registrar(c, usuario, correo, **extra):
    limpiar_sesion()
    datos = dict(username=usuario, email=correo, password=CLAVE,
                 birth_date='1995-04-12', accept_terms='1')
    datos.update(extra)
    return c.post('/register', data=datos)


def entrar(c, ident, clave=CLAVE, **extra):
    limpiar_sesion()
    return c.post('/login', data=dict(identifier=ident, password=clave, **extra))


def usuario(correo):
    with A.app.app_context():
        return A.User.query.filter_by(email=correo).first()


with A.app.app_context():
    A.db.create_all()

# ══════════════════════════════════════════════════════════════════════
seccion('REGISTRO — lo que debe aceptar y lo que debe rechazar')
with A.app.test_client() as c:
    BUZON.clear()
    r = registrar(c, 'lucia', 'lucia@demo.invalid')
    check('un registro correcto pide verificar el correo',
          '/verify-email' in (r.headers.get('Location') or ''), r.headers.get('Location'))
    check('y le llega el código', BUZON and BUZON[0][0] == 'verificacion', BUZON)
    check('la cuenta nace SIN verificar', usuario('lucia@demo.invalid').email_verified is False)

    codigo = usuario('lucia@demo.invalid').verification_code
    r = c.post('/verify-email', data={'code': '000000'})
    check('un código equivocado no la activa', usuario('lucia@demo.invalid').email_verified is False)
    r = c.post('/verify-email', data={'code': codigo})
    check('el código bueno la activa y entra', usuario('lucia@demo.invalid').email_verified is True)
    check('y queda con plan free', usuario('lucia@demo.invalid').plan == 'free')

RECHAZOS = [
    ('correo ya registrado',      dict(usuario='otra', correo='lucia@demo.invalid')),
    ('usuario ya registrado',     dict(usuario='lucia', correo='otra@demo.invalid')),
    ('contraseña floja',          dict(usuario='pepe', correo='pepe@demo.invalid', password='password1')),
    ('contraseña corta',          dict(usuario='pepe', correo='pepe@demo.invalid', password='abc')),
    ('menor de edad',             dict(usuario='pepe', correo='pepe@demo.invalid', birth_date='2015-01-01')),
    ('sin aceptar los términos',  dict(usuario='pepe', correo='pepe@demo.invalid', accept_terms='')),
    ('usuario con espacios',      dict(usuario='pe pe', correo='pepe@demo.invalid')),
]
for nombre, kw in RECHAZOS:
    with A.app.test_client() as c:
        BUZON.clear()
        u_, e_ = kw.pop('usuario'), kw.pop('correo')
        r = registrar(c, u_, e_, **kw)
        creada = usuario(e_) is not None and e_ != 'lucia@demo.invalid'
        check('rechaza: %-24s' % nombre, r.status_code == 200 and not creada and not BUZON,
              'HTTP %s · creada=%s · correos=%s' % (r.status_code, creada, BUZON))

# ══════════════════════════════════════════════════════════════════════
seccion('SESIÓN — entrar, fallar, salir')
with A.app.test_client() as c:
    r = entrar(c, 'lucia@demo.invalid')
    check('entra con el correo', r.status_code == 302 and '/welcome' in (r.headers.get('Location') or ''),
          r.headers.get('Location'))
    r = c.get('/app')
    check('y llega a la aplicación', r.status_code in (200, 302), r.status_code)
    c.get('/logout')
    r = c.get('/app')
    check('al salir, la aplicación deja de abrirse', r.status_code == 302, r.status_code)
with A.app.test_client() as c:
    r = entrar(c, 'lucia', CLAVE)
    check('entra también con el nombre de usuario', r.status_code == 302, r.status_code)
with A.app.test_client() as c:
    BUZON.clear()
    r = entrar(c, 'lucia@demo.invalid', 'claveequivocada')
    check('rechaza la contraseña equivocada', r.status_code == 200, r.status_code)
    check('y no manda ningún correo', not BUZON, BUZON)

with A.app.app_context():
    u = A.User.query.filter_by(email='lucia@demo.invalid').first()
    u.is_banned = True
    A.db.session.commit()
with A.app.test_client() as c:
    r = entrar(c, 'lucia@demo.invalid')
    # Se comprueba lo que importa —que NO quede dentro— y de paso que se lo
    # digan. Buscar la palabra "banned" en el HTML no vale: el aviso viaja como
    # clave de traducción (login.errBanned) y el texto lo pone el navegador.
    limpiar_sesion()
    dentro = c.get('/app').status_code == 200
    check('una cuenta baneada no entra',
          r.status_code == 200 and not dentro
          and 'login.errBanned' in r.get_data(as_text=True),
          'HTTP %s · dentro=%s' % (r.status_code, dentro))
with A.app.app_context():
    u = A.User.query.filter_by(email='lucia@demo.invalid').first()
    u.is_banned = False
    A.db.session.commit()

# ══════════════════════════════════════════════════════════════════════
seccion('CONTRASEÑA OLVIDADA — el enlace tiene que funcionar de verdad')
with A.app.test_client() as c:
    BUZON.clear()
    c.post('/forgot-password', data={'email': 'lucia@demo.invalid'})
    check('manda el enlace', BUZON and BUZON[0][0] == 'reseteo', BUZON)
    url = BUZON[0][2] if BUZON else ''
    ruta = '/' + url.split('/', 3)[-1] if url.startswith('http') else url
    r = c.get(ruta)
    check('el enlace abre la pantalla de cambio', r.status_code == 200 and 'invalid' not in r.get_data(as_text=True)[:400])
    NUEVA = 'Zq7$vB4!nR8w'
    r = c.post(ruta, data={'password': NUEVA})
    check('cambia la contraseña', r.status_code in (200, 302), r.status_code)
with A.app.test_client() as c:
    r = entrar(c, 'lucia@demo.invalid', 'Zq7$vB4!nR8w')
    check('entra con la NUEVA', r.status_code == 302, r.status_code)
with A.app.test_client() as c:
    r = entrar(c, 'lucia@demo.invalid', CLAVE)
    check('y la vieja ya NO sirve', r.status_code == 200, r.status_code)
with A.app.test_client() as c:
    r = c.get('/reset-password/token-inventado')
    check('un enlace inventado no abre nada', 'invalid' in r.get_data(as_text=True).lower())
CLAVE_LUCIA = 'Zq7$vB4!nR8w'

# ══════════════════════════════════════════════════════════════════════
seccion('COMPRA DE PLAN — de free a premium')
with A.app.app_context():
    A.db.session.add(A.PromoCode(code='SOCIO20', discount_pct=20, kind='creator',
                                 creator_name='Gabriel', valid_for='both', active=True))
    A.db.session.commit()
with A.app.test_client() as c:
    entrar(c, 'lucia@demo.invalid', CLAVE_LUCIA)
    r = c.get('/checkout?plan=premium&cycle=monthly')
    check('el carrito de premium abre', r.status_code == 200, r.status_code)
    r = c.get('/checkout?plan=free&cycle=monthly')
    check('no se puede "comprar" el plan free', r.status_code == 302, r.status_code)
    r = c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                         'promo_code': 'SOCIO20'})
    with A.app.app_context():
        o = A.Order.query.filter_by(plan='premium').order_by(A.Order.id.desc()).first()
    check('crea el pedido con el descuento aplicado', o and abs(o.final_price - 40.0) < .01,
          o.final_price if o else None)
    check('y NO entrega el plan sin pagar', usuario('lucia@demo.invalid').plan == 'free')
    r = c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly'})
    with A.app.app_context():
        n = A.Order.query.filter_by(user_id=o.user_id, status='pending').count()
    check('un segundo intento no apila pedidos', n == 1, '%d pendientes' % n)

with A.app.app_context():
    o = A.db.session.get(A.Order, o.id)
    o.status = 'paid'
    A.db.session.commit()
    A._activate_plan_from_order(o)
    u = A.User.query.filter_by(email='lucia@demo.invalid').first()
    check('al pagar, el plan queda activo', u.plan == 'premium', u.plan)
    check('con vencimiento a 30 días',
          25 < (A._aware(u.plan_expires_at) - datetime.now(timezone.utc)).days < 31)
    check('entrega el camo del plan', 'premium' in (u.owned_camos or ''), u.owned_camos)
    check('y se lo pone', u.active_camo == 'premium', u.active_camo)
    check('ata la cuenta al socio', u.referred_by_code == 'SOCIO20', u.referred_by_code)
    sb = A.SaleBreakdown.query.filter_by(order_id=o.id).first()
    check('anota la venta en el libro', sb is not None)
    check('con la comisión del primer tramo (30%)', sb and abs(sb.commission_amt - 12.0) < .01,
          sb.commission_amt if sb else None)
    check('y aparta la reserva anti-contracargo', sb and sb.reserve_amt > 0,
          sb.reserve_amt if sb else None)
    aplicado = o.applied_at
    A._activate_plan_from_order(o)
    check('activar dos veces no estira la vigencia', A.db.session.get(A.Order, o.id).applied_at == aplicado)

seccion('LO QUE ABRE EL PLAN')
with A.app.test_client() as c:
    entrar(c, 'lucia@demo.invalid', CLAVE_LUCIA)
    check('premium entra al foro', c.get('/forum/feed').status_code == 200)
    check('premium ve su cuota de análisis', c.get('/api/usage').status_code == 200)
    r = c.get('/checkout?plan=standard&cycle=monthly')
    check('no puede "bajar" a standard estando en premium', r.status_code == 302, r.status_code)

seccion('RENOVACIÓN Y CADUCIDAD')
with A.app.app_context():
    u = A.User.query.filter_by(email='lucia@demo.invalid').first()
    antes = A._aware(u.plan_expires_at)
    o2 = A.Order(user_id=u.id, plan='premium', billing_cycle='monthly',
                 base_price=50.0, final_price=40.0, status='paid',
                 promo_code='SOCIO20', payment_method='paypal')
    A.db.session.add(o2)
    A.db.session.commit()
    A._activate_plan_from_order(o2)
    u = A.User.query.filter_by(email='lucia@demo.invalid').first()
    check('renovar SUMA sobre lo que quedaba',
          (A._aware(u.plan_expires_at) - antes).days >= 29,
          (A._aware(u.plan_expires_at) - antes).days)
    check('y el socio cobra también la renovación', A.SaleBreakdown.query.count() == 2)
    clientes = A.partner_active_customers('Gabriel')
    check('pero cuenta UN cliente, no dos pagos', clientes == 1, clientes)

    u.plan_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    A.db.session.commit()
with A.app.test_client() as c:
    entrar(c, 'lucia@demo.invalid', CLAVE_LUCIA)
    c.get('/app')
    u = usuario('lucia@demo.invalid')
    check('un plan vencido cae a free solo', u.plan == 'free', u.plan)
    check('pero el camo comprado NO se le quita', 'premium' in (u.owned_camos or ''), u.owned_camos)
with A.app.test_client() as c:
    entrar(c, 'lucia@demo.invalid', CLAVE_LUCIA)
    check('y ya no entra al foro', c.get('/forum/feed').status_code in (302, 403))

print('\n' + '═' * 60)
print('RESULTADO: %d correctas, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
