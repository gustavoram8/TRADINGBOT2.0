# -*- coding: utf-8 -*-
"""Nadie paga un mes que ya tiene pagado.

    python3 tools/test_meses_apilados.py

El dueño, literal: "si yo pago por ejemplo 4 premiums por adelantado, ¿qué
sentido tiene que al cabo de un mes me cobren de nuevo la mensualidad? Estás
cobrando una mensualidad que en teoría ya pagó 5 veces por adelantado."

Tiene razón, y no era solo un número raro en la pantalla:

  · cada compra suelta SUMA 30 días al vencimiento (eso está bien: es lo que
    hace que una renovación no te quite el tiempo que te queda);
  · pero el cobro automático de PayPal corre por su cuenta cada 30 días.

Juntas las dos cosas, quien pagara tres meses de golpe acumulaba 90 días Y
seguía pagando cada 30. La regla es simple: un plan mensual se paga mes a
mes. Quien quiera pagar varios meses por adelantado, para eso está el anual.

El control existía SOLO en la pantalla del carrito (un GET). La ruta que crea
el pedido —el POST— no lo repetía, así que un formulario viejo o el botón
atrás bastaban para colarse. Aquí se comprueban las dos puertas.
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


def usuario(nombre, plan='free'):
    u = A.User.query.filter_by(username=nombre).first()
    if u:
        for M in (A.KnownDevice, A.SaleBreakdown, A.PlanSubscription, A.Order):
            M.query.filter_by(user_id=u.id).delete()
        A.db.session.delete(u)
        A.db.session.commit()
    u = A.User(username=nombre, email=nombre + '@ej.com', plan=plan)
    u.set_password(CLAVE)
    for c in ('email_verified', 'is_verified', 'verified'):
        if hasattr(u, c):
            setattr(u, c, True)
    A.db.session.add(u)
    A.db.session.commit()
    return u.id


def cliente(nombre):
    c = A.app.test_client()
    c.post('/login', data={'identifier': nombre, 'password': CLAVE},
           follow_redirects=True)
    return c


def pedidos(uid):
    return A.Order.query.filter_by(user_id=uid).count()


def main():
    with A.app.app_context():
        A.db.create_all()
        uid = usuario('apila_uno')

    # ── 1 · la primera compra sí, la segunda NO ───────────────────────────
    print('\n1 · comprar Premium dos veces seguidas')
    c = cliente('apila_uno')
    r = c.get('/checkout?plan=premium&cycle=monthly')
    check(r.status_code == 200, 'el carrito se abre la primera vez (%s)'
          % r.status_code)
    c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                     'method': 'manual'})
    with A.app.app_context():
        o = A.Order.query.filter_by(user_id=uid).order_by(A.Order.id.desc()).first()
        o.status = 'paid'
        o.paid_at = datetime.now(timezone.utc)
        A.db.session.commit()
        A._activate_plan_from_order(o)
        u = A.db.session.get(A.User, uid)
        venc1 = A._aware(u.plan_expires_at)
        check(u.plan == 'premium', 'queda en Premium')
        check(28 <= (venc1 - datetime.now(timezone.utc)).days <= 30,
              'con 30 días (%d)' % (venc1 - datetime.now(timezone.utc)).days)
        antes = pedidos(uid)

    c = cliente('apila_uno')
    r = c.get('/checkout?plan=premium&cycle=monthly', follow_redirects=False)
    check(r.status_code in (301, 302) and 'pricing' in (r.headers.get('Location') or ''),
          'la pantalla del carrito ya no lo deja (%s)' % r.status_code)
    # 🔴 y la puerta de atrás: el POST directo, que es lo que se colaba
    r = c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                         'method': 'manual'},
               follow_redirects=False)
    check(r.status_code in (301, 302) and 'pricing' in (r.headers.get('Location') or ''),
          '🔴 y el POST directo TAMPOCO (%s)' % r.status_code)
    with A.app.app_context():
        check(pedidos(uid) == antes,
              'no se creó ningún pedido nuevo (%d)' % (pedidos(uid) - antes))
        u = A.db.session.get(A.User, uid)
        check(A._aware(u.plan_expires_at) == venc1,
              '🔴 y el vencimiento NO se movió: sigue siendo un mes')

    # ── 2 · tres de golpe, que es el caso que planteó ─────────────────────
    print('\n2 · intentar pagar TRES meses de golpe')
    with A.app.app_context():
        uid2 = usuario('apila_tres')
    c = cliente('apila_tres')
    creados = 0
    for i in range(3):
        r = c.post('/checkout/create', data={'plan': 'standard',
                                             'cycle': 'monthly',
                                             'method': 'manual'},
                   follow_redirects=False)
        with A.app.app_context():
            o = (A.Order.query.filter_by(user_id=uid2, status='pending')
                 .order_by(A.Order.id.desc()).first())
            if o:
                creados += 1
                o.status = 'paid'
                o.paid_at = datetime.now(timezone.utc)
                A.db.session.commit()
                A._activate_plan_from_order(o)
    with A.app.app_context():
        u = A.db.session.get(A.User, uid2)
        dias = (A._aware(u.plan_expires_at) - datetime.now(timezone.utc)).days
        check(creados == 1, 'solo se dejó pagar UNA vez (%d de 3)' % creados)
        check(28 <= dias <= 30,
              '🔴 tiene 30 días de acceso, no 90 (%d)' % dias)
        pagado = sum(x.final_price for x in
                     A.Order.query.filter_by(user_id=uid2, status='paid').all())
        check(abs(pagado - 25.0) < 0.01,
              'y pagó $%.2f, no $75.00' % pagado)

    # ── 3 · subir de plan SIGUE permitido ─────────────────────────────────
    print('\n3 · pero subir de plan no se bloquea')
    c = cliente('apila_tres')
    r = c.get('/checkout?plan=premium&cycle=monthly')
    check(r.status_code == 200, 'un Standard puede abrir el carrito de Premium')
    r = c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                         'method': 'manual'},
               follow_redirects=False)
    with A.app.app_context():
        o = (A.Order.query.filter_by(user_id=uid2, status='pending')
             .order_by(A.Order.id.desc()).first())
        check(o is not None and o.plan == 'premium',
              'y el pedido de la subida se crea (%s)' % (o.plan if o else '—'))

    # ── 4 · el cinturón: suscripción viva aunque el plan no lo diga ───────
    print('\n4 · hay una suscripción viva de ese plan aunque `plan` no lo diga')
    with A.app.app_context():
        uid3 = usuario('apila_desfase', plan='free')
        A.db.session.add(A.PlanSubscription(
            user_id=uid3, provider='paypal', plan='premium',
            billing_cycle='monthly', price=50.0, status='active',
            provider_ref='I-VIVA'))
        A.db.session.commit()
        u = A.db.session.get(A.User, uid3)
        se_puede, motivo = A.puede_comprar(u, 'premium')
        check(not se_puede and motivo == 'ya_suscrito',
              'se rechaza por suscripción viva (%s)' % motivo)
    c = cliente('apila_desfase')
    r = c.post('/checkout/create', data={'plan': 'premium', 'cycle': 'monthly',
                                         'method': 'manual'},
               follow_redirects=False)
    with A.app.app_context():
        check(pedidos(uid3) == 0,
              'y no se le crea el pedido (%d)' % pedidos(uid3))

    # ── 5 · la renovación automática SÍ suma su mes ───────────────────────
    print('\n5 · lo que sí debe apilar: la renovación del propio cobro')
    with A.app.app_context():
        uid4 = usuario('apila_renueva', plan='premium')
        u = A.db.session.get(A.User, uid4)
        u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=3)
        u.plan_cycle = 'monthly'
        A.db.session.commit()
        antes = A._aware(u.plan_expires_at)
        sub = A.PlanSubscription(user_id=uid4, provider='paypal', plan='premium',
                                 billing_cycle='monthly', price=50.0,
                                 status='active', provider_ref='I-REN')
        A.db.session.add(sub)
        A.db.session.commit()
        A._sub_cobro(sub, 50.0, referencia='SALE-REN-1')
        u = A.db.session.get(A.User, uid4)
        d = (A._aware(u.plan_expires_at) - antes).days
        check(d == 30, 'suma 30 días sobre lo que le quedaba (%d)' % d)

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
