# -*- coding: utf-8 -*-
"""El admin puede cambiar SU propio plan (y solo el suyo entre admins).

    python3 tools/test_admin_plan_propio.py

Por qué existe: el dueño es el único administrador del sitio, y estando en
Premium el checkout le rechaza comprar cualquier plan (no se permite comprar
uno igual o inferior al actual). Sin poder bajarse a Free no hay manera de
ensayar el circuito de compra ni la suscripción de PayPal.

Lo que se comprueba es tanto lo que AHORA se permite como lo que se sigue
prohibiendo — la protección entre administradores no debe haberse aflojado.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scalpel'))
import app as A  # noqa: E402

ok = fallos = 0
CLAVE = 'Zx8!kQ2mLp7w'


def check(cond, txt):
    global ok, fallos
    if cond:
        ok += 1
        print('  ok    ', txt)
    else:
        fallos += 1
        print('  FALLA ', txt)


def usuario(nombre, admin=False, plan='free'):
    u = A.User.query.filter_by(username=nombre).first()
    if u:
        A.KnownDevice.query.filter_by(user_id=u.id).delete()
        A.SaleBreakdown.query.filter_by(user_id=u.id).delete()
        A.PlanSubscription.query.filter_by(user_id=u.id).delete()
        A.Order.query.filter_by(user_id=u.id).delete()
        A.db.session.delete(u)
        A.db.session.commit()
    u = A.User(username=nombre, email=nombre + '@ej.com', plan=plan, is_admin=admin)
    u.set_password(CLAVE)
    for c in ('email_verified', 'is_verified', 'verified'):
        if hasattr(u, c):
            setattr(u, c, True)
    A.db.session.add(u)
    A.db.session.commit()
    return u.id


def entrar(c, nombre):
    # No hace falta limpiar el cache de Flask-Login en `g`: aquí no se mantiene
    # ningún app_context abierto entre peticiones, que es cuando aparece esa
    # trampa (la 2ª petición correría como el 1er usuario).
    c.post('/login', data={'identifier': nombre, 'password': CLAVE},
           follow_redirects=True)


def main():
    with A.app.app_context():
        A.db.create_all()
        jefe = usuario('adm_jefe', admin=True, plan='premium')
        otro_adm = usuario('adm_otro', admin=True, plan='premium')
        cliente = usuario('cli_normal', admin=False, plan='free')
        # al jefe se le pone una vigencia futura, como la tendría de verdad
        u = A.db.session.get(A.User, jefe)
        u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=200)
        u.plan_cycle = 'monthly'
        u.cancel_at_period_end = True
        A.db.session.commit()

    # ── 1 · el admin se baja a Free ───────────────────────────────────────
    print('\n1 · bajarse el plan a uno mismo')
    with A.app.test_client() as c:
        entrar(c, 'adm_jefe')
        r = c.post('/admin/set-plan', data={'user_id': jefe, 'plan': 'free'},
                   follow_redirects=False)
        check(r.status_code in (302, 303), 'la petición se acepta (%s)' % r.status_code)
    with A.app.app_context():
        u = A.db.session.get(A.User, jefe)
        check(u.plan == 'free', 'queda en Free (%s)' % u.plan)
        check(u.plan_expires_at is None, 'se limpia la fecha de vencimiento')
        check(not u.cancel_at_period_end, 'se limpia la marca de cancelación')
        check(u.is_admin, 'SIGUE siendo admin — el plan no toca los permisos')

    # ── 2 · y ahora sí puede comprar ──────────────────────────────────────
    print('\n2 · el checkout ya no lo rechaza')
    with A.app.test_client() as c:
        entrar(c, 'adm_jefe')
        for plan in ('standard', 'premium'):
            r = c.get('/checkout?plan=%s&cycle=monthly' % plan)
            # 200 = le enseña el carrito; 302 = lo rebota a /pricing
            check(r.status_code == 200, 'puede abrir el carrito de %s (%s)'
                  % (plan, r.status_code))

    # ── 3 · lo que se sigue prohibiendo ───────────────────────────────────
    print('\n3 · la protección entre admins sigue en pie')
    with A.app.test_client() as c:
        entrar(c, 'adm_jefe')
        r = c.post('/admin/set-plan', data={'user_id': otro_adm, 'plan': 'free'},
                   follow_redirects=False)
        check(r.status_code == 403, 'no puede tocarle el plan a OTRO admin (%s)'
              % r.status_code)
    with A.app.app_context():
        check(A.db.session.get(A.User, otro_adm).plan == 'premium',
              'el otro admin conserva su plan')

    # ── 4 · los usuarios normales, como siempre ───────────────────────────
    print('\n4 · sin regresión con usuarios normales')
    with A.app.test_client() as c:
        entrar(c, 'adm_jefe')
        c.post('/admin/set-plan', data={'user_id': cliente, 'plan': 'premium'})
    with A.app.app_context():
        check(A.db.session.get(A.User, cliente).plan == 'premium',
              'el admin sigue pudiendo cambiar el plan de un cliente')

    # ── 5 · un NO admin no entra por esta puerta ──────────────────────────
    print('\n5 · la puerta sigue cerrada para quien no es admin')
    with A.app.test_client() as c:
        entrar(c, 'cli_normal')
        r = c.post('/admin/set-plan', data={'user_id': cliente, 'plan': 'free'},
                   follow_redirects=False)
        check(r.status_code == 403, 'un cliente no puede cambiarse el plan (%s)'
              % r.status_code)
    with A.app.app_context():
        check(A.db.session.get(A.User, cliente).plan == 'premium',
              'y su plan no se movió')

    # ── 6 · vuelta a Premium ──────────────────────────────────────────────
    print('\n6 · volver a subirse')
    with A.app.test_client() as c:
        entrar(c, 'adm_jefe')
        c.post('/admin/set-plan', data={'user_id': jefe, 'plan': 'premium'})
    with A.app.app_context():
        check(A.db.session.get(A.User, jefe).plan == 'premium',
              'el dueño puede devolverse a Premium cuando termine de probar')

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
