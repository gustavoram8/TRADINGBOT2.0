# -*- coding: utf-8 -*-
"""Cuándo sale el "UNLOCKED" del plan — y, sobre todo, cuándo NO.

    python3 tools/test_unlocks.py

Pedido del dueño tras ver uno saltar sin venir a cuento (compró cosméticos
siendo Premium y le salió el unlock de Standard):

    "El unlock solo tiene sentido cuando haces upgrade de plan / cambias de
     plan o cuando pagas alguno por primera vez."

La causa era que la celebración se guardaba en cola hasta el siguiente /app,
sin comprobar si seguía describiendo la situación de la cuenta. Aquí se
recorren todas las formas en que puede dispararse.
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


def usuario(nombre, plan='free', admin=False):
    u = A.User.query.filter_by(username=nombre).first()
    if u:
        for M in (A.KnownDevice, A.SaleBreakdown, A.PlanSubscription, A.Order):
            M.query.filter_by(user_id=u.id).delete()
        A.CosmeticOrder.query.filter_by(user_id=u.id).delete()
        A.CamoOrder.query.filter_by(user_id=u.id).delete()
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


def comprar(uid, plan, cycle='monthly', precio=None):
    """Un pedido pagado que se activa por el camino de siempre."""
    p = precio if precio is not None else A.PLAN_PRICING[plan][cycle]
    o = A.Order(user_id=uid, plan=plan, billing_cycle=cycle, base_price=p,
                discount_pct=0, final_price=p, status='paid',
                payment_method='manual',
                paid_at=datetime.now(timezone.utc))
    A.db.session.add(o)
    A.db.session.commit()
    A._activate_plan_from_order(o)
    return o.id


def abrir_app(nombre):
    """Devuelve el plan que celebra /app, o '' si no celebra nada."""
    c = A.app.test_client()
    c.post('/login', data={'identifier': nombre, 'password': CLAVE},
           follow_redirects=True)
    c.get('/welcome')                 # /app exige el pase del splash
    html = c.get('/app').get_data(as_text=True)
    import re
    m = re.search(r'unlockPlan:\s*"([^"]*)"', html)
    return m.group(1) if m else '(no se pudo leer)'


def main():
    # ── 1 · primera compra ────────────────────────────────────────────────
    print('\n1 · primera compra de la vida')
    with A.app.app_context():
        A.db.create_all()
        uid = usuario('unl_uno')
        comprar(uid, 'standard')
    check(abrir_app('unl_uno') == 'standard', 'celebra Standard')
    check(abrir_app('unl_uno') == '', 'y NO se repite al recargar')

    # ── 2 · subir de plan ─────────────────────────────────────────────────
    print('\n2 · subir de Standard a Premium')
    with A.app.app_context():
        comprar(uid, 'premium')
    check(abrir_app('unl_uno') == 'premium', 'celebra Premium')

    # ── 3 · RENOVAR el mismo plan ─────────────────────────────────────────
    print('\n3 · renovar el mismo plan (lo que hace el cobro automático)')
    with A.app.app_context():
        oid = comprar(uid, 'premium')
        o = A.db.session.get(A.Order, oid)
        check(o.applied_at is not None, 'la renovación se aplica')
        check(o.celebrated_at is not None,
              '🔴 y nace ya sellada: no hay nada que estrenar')
    check(abrir_app('unl_uno') == '',
          'no sale ningún unlock por renovar')

    # ── 4 · EL CASO DEL DUEÑO ─────────────────────────────────────────────
    print('\n4 · pedido viejo en cola que ya no describe la cuenta')
    with A.app.app_context():
        uid2 = usuario('unl_hermano')
        # compra Standard y NO abre la app
        comprar(uid2, 'standard')
        # más tarde pasa a Premium por otra vía (el dueño desde /admin)
        u = A.db.session.get(A.User, uid2)
        u.plan = 'premium'
        u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        A.db.session.commit()
        # y compra cosméticos, que NO son un pedido de plan
        co = A.CosmeticOrder(user_id=uid2, slugs='item:santa', label='1 cosmetic',
                             price=3.99, status='paid', payment_method='paypal',
                             paid_at=datetime.now(timezone.utc))
        A.db.session.add(co)
        A.db.session.commit()
    check(abrir_app('unl_hermano') == '',
          '🔴 NO salta el "UNLOCKED Standard" siendo Premium')
    with A.app.app_context():
        pend = A.Order.query.filter_by(user_id=uid2, celebrated_at=None).count()
        check(pend == 0, 'y la cola queda sellada, no acechando (%d)' % pend)

    # ── 5 · varios pedidos en cola: uno solo, el que toca ─────────────────
    print('\n5 · dos pedidos sin celebrar a la vez')
    with A.app.app_context():
        uid3 = usuario('unl_cola')
        comprar(uid3, 'standard')     # queda en cola
        comprar(uid3, 'premium')      # y este también
        pend = A.Order.query.filter_by(user_id=uid3, celebrated_at=None).count()
        check(pend == 2, 'hay 2 esperando (%d)' % pend)
    check(abrir_app('unl_cola') == 'premium',
          'celebra el último, que es el plan de hoy')
    check(abrir_app('unl_cola') == '',
          'y el otro NO asoma después (antes salía en la visita siguiente)')

    # ── 6 · cosméticos a secas ────────────────────────────────────────────
    print('\n6 · comprar cosméticos, sin nada de planes por medio')
    with A.app.app_context():
        uid4 = usuario('unl_cosm', plan='premium')
        u = A.db.session.get(A.User, uid4)
        u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=20)
        A.db.session.commit()
        for M, kw in ((A.CosmeticOrder, dict(slugs='item:cur-santa',
                                             label='1 cosmetic', price=2.99)),
                      (A.CamoOrder, dict(slug='naval', label='Naval', price=4.99))):
            A.db.session.add(M(user_id=uid4, status='paid',
                               payment_method='paypal',
                               paid_at=datetime.now(timezone.utc), **kw))
        A.db.session.commit()
    check(abrir_app('unl_cosm') == '',
          'ningún unlock de plan (los cosméticos no son un plan)')

    # ── 7 · el admin cambia el plan a mano ────────────────────────────────
    print('\n7 · plan puesto desde /admin, sin compra')
    with A.app.app_context():
        uid5 = usuario('unl_admin')
        jefe = usuario('unl_jefe', plan='premium', admin=True)
    c = A.app.test_client()
    c.post('/login', data={'identifier': 'unl_jefe', 'password': CLAVE},
           follow_redirects=True)
    c.post('/admin/set-plan', data={'user_id': uid5, 'plan': 'premium'})
    check(abrir_app('unl_admin') == '',
          'no se celebra un plan que nadie compró')

    # ── 8 · plan vencido: la cola muere con él ────────────────────────────
    print('\n8 · compra, no entra en semanas, y el plan vence')
    with A.app.app_context():
        uid6 = usuario('unl_vencido')
        comprar(uid6, 'standard')
        u = A.db.session.get(A.User, uid6)
        u.plan_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        A.db.session.commit()
    check(abrir_app('unl_vencido') == '',
          'no le celebra un Standard que ya no tiene')

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    with A.app.app_context():
        A.db.create_all()
    sys.exit(main())
