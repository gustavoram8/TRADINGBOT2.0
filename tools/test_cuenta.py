# -*- coding: utf-8 -*-
"""Cambio de correo y borrado de cuenta: las dos filas que decian "muy pronto".

Lo que tiene que ser verdad:
  · el correo NO cambia hasta que alguien demuestra que lee el buzon nuevo;
  · el alias no cuela (juan+2@gmail = juan@gmail, la regla del 2026-08-09);
  · borrar la cuenta CORTA el cobro antes de borrar nada, y si PayPal no
    contesta no se borra — una cuenta borrada con el cobro vivo seguiria
    cobrando sin nadie a quien avisar;
  · el borrado se lleva el contenido personal y CONSERVA los registros de
    cobro, que es exactamente lo que promete el aviso de privacidad (Secc. 8)
    y lo que necesitan el libro de ventas y la comision del socio.

    python3 tools/test_cuenta.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault('DATABASE_URL', 'sqlite://')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
from flask import g            # noqa: E402
import app as A                # noqa: E402

CL = 'Zx9!wQ4mNp2r'
ok = fallas = 0
cortadas = []


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def sesion(nombre, clave=CL):
    c = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    c.post('/login', data={'identifier': nombre, 'password': clave})
    c.set_cookie('scalpel_splash_ts', '1')
    return c


def leer(uid):
    with A.app.app_context():
        A.db.session.expire_all()
        return A.db.session.get(A.User, uid)


# PayPal simulado. `viva` = lo que PayPal contestaria si le preguntan si ese
# permiso todavia puede cobrar; cancelar lo apaga.
viva = {}


def falso_cancel(sub, motivo=''):
    cortadas.append(sub.id)
    viva[sub.provider_ref] = False
    return True


A._paypal_sub_cancel = falso_cancel
A._sub_puede_cobrar = lambda sub: viva.get(sub.provider_ref, True)
A.PAYPAL_ENABLED = True

with A.app.app_context():
    A.db.create_all()
    for n, correo in (('cambia', 'viejo@demo.invalid'),
                      ('vecina', 'ocupado@gmail.com'),
                      ('borrame', 'b@demo.invalid')):
        u = A.User(username=n, email=correo, plan='premium',
                   email_verified=True)
        u.email_canonical = A._correo_canonico(correo)
        u.set_password(CL)
        A.db.session.add(u)
    A.db.session.commit()
    UID = A.User.query.filter_by(username='cambia').first().id
    BID = A.User.query.filter_by(username='borrame').first().id

print('== CAMBIO DE CORREO ==')
c = sesion('cambia')
c.post('/account/email', data={'email': 'nuevo@demo.invalid',
                               'password': 'la-que-no-es'})
check('sin la contraseña no arranca el cambio',
      not leer(UID).pending_email, leer(UID).pending_email)
c.post('/account/email', data={'email': 'esto-no-es-un-correo',
                               'password': CL})
check('un correo mal escrito se rechaza', not leer(UID).pending_email)
c.post('/account/email', data={'email': 'ocupado+etiqueta@gmail.com',
                               'password': CL})
check('🔴 el ALIAS de un correo ya registrado no cuela '
      '(ocupado+etiqueta@gmail = ocupado@gmail)',
      not leer(UID).pending_email, leer(UID).pending_email)

r = c.post('/account/email', data={'email': 'nuevo@demo.invalid',
                                   'password': CL})
u = leer(UID)
check('con los datos correctos queda PENDIENTE',
      u.pending_email == 'nuevo@demo.invalid' and bool(u.pending_email_code))
check('🔴 pero el correo de la cuenta NO ha cambiado todavía',
      u.email == 'viejo@demo.invalid', u.email)
check('...y aún se entra con el correo viejo',
      sesion('viejo@demo.invalid').get('/settings').status_code == 200)

c = sesion('cambia')
c.post('/account/email/confirm', data={'code': '000000'})
check('un código inventado no cambia nada',
      leer(UID).email == 'viejo@demo.invalid')
codigo = leer(UID).pending_email_code
c.post('/account/email/confirm', data={'code': codigo})
u = leer(UID)
check('el código correcto SÍ lo cambia', u.email == 'nuevo@demo.invalid',
      u.email)
check('y deja el canónico al día (la regla del alias sigue en pie)',
      u.email_canonical == A._correo_canonico('nuevo@demo.invalid'))
check('se limpia lo pendiente', not u.pending_email and not u.pending_email_code)
check('se entra con el correo NUEVO',
      sesion('nuevo@demo.invalid').get('/settings').status_code == 200)
check('y el viejo ya no sirve para entrar',
      sesion('viejo@demo.invalid').get('/settings').status_code in (302, 401))

print('\n   -- un código caducado no vale --')
c = sesion('cambia')
c.post('/account/email', data={'email': 'tarde@demo.invalid', 'password': CL})
with A.app.app_context():
    u = A.db.session.get(A.User, UID)
    codigo = u.pending_email_code
    u.pending_email_at = datetime.now(timezone.utc) - timedelta(minutes=31)
    A.db.session.commit()
c.post('/account/email/confirm', data={'code': codigo})
check('pasados 30 minutos el código ya no sirve',
      leer(UID).email == 'nuevo@demo.invalid', leer(UID).email)

print('\n== BORRADO DE CUENTA ==')
with A.app.app_context():
    u = A.db.session.get(A.User, BID)
    # contenido personal
    A.db.session.add(A.ForumPost(user_id=BID, body='hola foro', title='t'))
    A.db.session.add(A.XPLog(user_id=BID, amount=10, source='login',
                             ref='x', day='2026-08-10'))
    # y un registro de cobro, que NO se puede borrar
    o = A.Order(user_id=BID, plan='premium', billing_cycle='monthly',
                base_price=50, final_price=50, status='paid',
                paid_at=datetime.now(timezone.utc))
    A.db.session.add(o)
    A.db.session.flush()
    A.db.session.add(A.SaleBreakdown(order_id=o.id, user_id=BID,
                                     username='borrame', plan='premium',
                                     billing_cycle='monthly', partner='Gabriel',
                                     gross=50, net_paid=50, position=1,
                                     commission_pct=30, commission_amt=15))
    sub = A.PlanSubscription(user_id=BID, plan='premium', price=50,
                             status='active', provider_ref='I-VIVA')
    A.db.session.add(sub)
    A.db.session.commit()
    SUB = sub.id

cb = sesion('borrame')
cb.post('/account/delete', data={'password': 'mala', 'confirm': 'CONFIRMAR'})
check('sin la contraseña no borra', leer(BID).deleted_at is None)
cb.post('/account/delete', data={'password': CL, 'confirm': 'borrame'})
check('sin escribir la palabra, tampoco (ni con su nombre de usuario)',
      leer(BID).deleted_at is None)

print('   -- con las claves de PayPal APAGADAS tampoco se borra --')
A.PAYPAL_ENABLED = False
cb.post('/account/delete', data={'password': CL, 'confirm': 'CONFIRMAR'})
check('🔴 sin claves no se puede ni preguntar ni cortar, y el permiso sigue '
      'vivo en PayPal: no se borra',
      leer(BID).deleted_at is None)
A.PAYPAL_ENABLED = True

print('   -- si PayPal no contesta, NO se borra --')
A._paypal_sub_cancel = lambda sub, motivo='': False
cb.post('/account/delete', data={'password': CL, 'confirm': 'CONFIRMAR'})
check('🔴 PayPal mudo = la cuenta sigue entera (borrar dejando el cobro vivo '
      'sería cobrarle a alguien que ya no existe)',
      leer(BID).deleted_at is None)
with A.app.app_context():
    A.db.session.expire_all()
    check('...y su suscripción sigue activa, no a medio cancelar',
          A.db.session.get(A.PlanSubscription, SUB).status == 'active')

print('   -- PayPal dice OK pero la suscripcion SIGUE viva --')
A._paypal_sub_cancel = lambda sub, motivo='': True     # miente: dice que si
cb.post('/account/delete', data={'password': CL, 'confirm': 'CONFIRMAR'})
check('🔴 se VERIFICA contra PayPal: si al preguntar sigue pudiendo cobrar, '
      'no se borra (cancelar y creerse el ok no basta)',
      leer(BID).deleted_at is None)

print('   -- una fila que aqui figura CANCELADA pero vive en PayPal --')
with A.app.app_context():
    zombi = A.PlanSubscription(user_id=BID, plan='premium', price=50,
                               status='cancelled', provider_ref='I-ZOMBI')
    A.db.session.add(zombi)
    A.db.session.commit()
    ZID = zombi.id
viva['I-ZOMBI'] = True

print('   -- con PayPal respondiendo de verdad --')
A._paypal_sub_cancel = falso_cancel
cb.post('/account/delete', data={'password': CL, 'confirm': 'CONFIRMAR'})
u = leer(BID)
check('la cuenta queda marcada como eliminada', u.deleted_at is not None)
check('🔴 el cobro se cortó ANTES de borrar', SUB in cortadas, cortadas)
check('🔴 y TAMBIÉN la fila que figuraba cancelada aquí pero seguía viva '
      'en PayPal (por eso se miran todas, no solo las activas)',
      ZID in cortadas, cortadas)
check('al terminar, PayPal ya no puede cobrar por ninguna',
      not any(viva.values()), viva)
check('sin identidad: el nombre pasa a deleted#%d (con "#", que el registro '
      'no admite, para que nadie pueda ocuparlo antes)' % BID,
      u.username == 'deleted#%d' % BID, u.username)
check('sin correo real', u.email.endswith('@deleted.invalid'), u.email)
check('y no puede entrar con su contraseña de siempre',
      sesion('borrame').get('/settings').status_code in (302, 401))
with A.app.app_context():
    A.db.session.expire_all()
    post = A.ForumPost.query.filter_by(user_id=BID).first()
    check('su publicación del foro queda VACÍA y marcada como borrada '
          '(borrarla reventaría las claves foráneas en PostgreSQL)',
          post is not None and post.is_deleted and not (post.body or '')
          and not (post.title or ''), post and (post.title, post.body))
    check('se borró su historial de XP',
          A.XPLog.query.filter_by(user_id=BID).count() == 0)
    check('🔴 SE CONSERVA el pedido pagado (obligación legal)',
          A.Order.query.filter_by(user_id=BID).count() == 1)
    fila = A.SaleBreakdown.query.filter_by(user_id=BID).first()
    check('🔴 y la comisión del socio sigue en el libro de ventas',
          fila is not None and fila.partner == 'Gabriel')

print('\n== LA ÚLTIMA RED: un cobro que llega DESPUÉS del borrado ==')
# No deberia pasar nunca (el borrado corta y verifica), pero es el unico
# fallo que nadie notaria: el cliente ya no esta para quejarse.
avisos = []
A._avisar_cobro_a_borrada = lambda u, sub, imp: avisos.append((u.id, imp))
with A.app.app_context():
    A.db.session.expire_all()
    sub = A.db.session.get(A.PlanSubscription, SUB)
    viva[sub.provider_ref] = True          # PayPal la revive por lo que sea
    antes_pedidos = A.Order.query.filter_by(user_id=BID).count()
    antes_ventas = A.SaleBreakdown.query.filter_by(user_id=BID).count()
    A._sub_cobro(sub, 50.0, referencia='VENTA-FANTASMA')
    A.db.session.expire_all()
    check('🔴 NO se le devuelve el plan a la cuenta borrada',
          A.db.session.get(A.User, BID).plan == 'free',
          A.db.session.get(A.User, BID).plan)
    check('🔴 NO se crea un pedido (ese dinero hay que devolverlo)',
          A.Order.query.filter_by(user_id=BID).count() == antes_pedidos)
    check('🔴 NO se anota una comisión sobre un dinero a reembolsar',
          A.SaleBreakdown.query.filter_by(user_id=BID).count() == antes_ventas)
check('se avisa al dueño con importe y todo', avisos == [(BID, 50.0)], avisos)
check('y se reintenta cortar la suscripción en PayPal',
      viva.get('I-VIVA') is False, viva)
with A.app.app_context():
    ev = A.AuditEvent.query.filter_by(
        event_type='cobro_sobre_cuenta_borrada').first()
    check('queda registrado en la auditoría', ev is not None)

print('\n== y por CUALQUIER otro camino que active un plan ==')
# _activate_plan_from_order es la puerta comun de los 6 caminos (vuelta de
# PayPal, 3 ramas del webhook, barrido de /admin y renovacion).
with A.app.app_context():
    A.db.session.expire_all()
    o2 = A.Order(user_id=BID, plan='premium', billing_cycle='monthly',
                 base_price=50, final_price=50, status='paid',
                 paid_at=datetime.now(timezone.utc))
    A.db.session.add(o2)
    A.db.session.commit()
    aplicado = A._activate_plan_from_order(o2)
    A.db.session.expire_all()
    check('🔴 un pedido pagado NO le devuelve el plan a una cuenta borrada',
          aplicado is False, aplicado)
    check('...y la cuenta sigue en free',
          A.db.session.get(A.User, BID).plan == 'free')
    check('queda registrado en la auditoría',
          A.AuditEvent.query.filter_by(
              event_type='pago_sobre_cuenta_borrada').first() is not None)

print('\n== la palabra se acepta en minúsculas y en los 4 idiomas ==')
for nombre, palabra in (('mini', 'confirmar'), ('eng', 'Confirm'),
                        ('fra', 'CONFIRMER')):
    with A.app.app_context():
        n = A.User(username=nombre, email=nombre + '@demo.invalid',
                   plan='free', email_verified=True)
        n.email_canonical = n.email
        n.set_password(CL)
        A.db.session.add(n)
        A.db.session.commit()
        NID = n.id
    cn = sesion(nombre)
    cn.post('/account/delete', data={'password': CL, 'confirm': palabra})
    check('"%s" sirve para confirmar' % palabra,
          leer(NID).deleted_at is not None, palabra)

print('\n== un admin no se borra a sí mismo desde aquí ==')
with A.app.app_context():
    adm = A.User.query.filter_by(is_admin=True).first()
    adm.set_password(CL)
    A.db.session.commit()
    ADM, AID = adm.username, adm.id
ca = sesion(ADM)
ca.post('/account/delete', data={'password': CL, 'confirm': 'CONFIRMAR'})
check('la cuenta de administrador sobrevive', leer(AID).deleted_at is None)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
