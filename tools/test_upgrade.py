# -*- coding: utf-8 -*-
"""Subir de Standard a Premium: ¿te cobran uno o los dos?

    python3 tools/test_upgrade.py

La pregunta del dueño, literal: "Compro hoy el plan standard pero más tarde
decido upgradear a premium. A la hora de renovarse mi servicio, ¿me cobran
solo el último adquirido, o me cargan standard y premium también?"

Un cobro doble es de los peores fallos posibles: el cliente lo ve en su
extracto, no en la web, y lo primero que hace es pedir el contracargo.

Aquí se recorre el camino entero con un PayPal simulado — incluido el caso
feo, que es cuando el aviso de PayPal se pierde y las dos quedan vivas.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scalpel'))
import app as A  # noqa: E402

ok = fallos = 0
CLAVE = 'Zx8!kQ2mLp7w'
cortadas = []
avisos = []


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


def pedido(uid, plan):
    p = A.PLAN_PRICING[plan]['monthly']
    o = A.Order(user_id=uid, plan=plan, billing_cycle='monthly', base_price=p,
                discount_pct=0, final_price=p, status='pending',
                payment_method='paypal')
    A.db.session.add(o)
    A.db.session.commit()
    return o


def suscripcion(uid, plan, orden, ref, estado='pending'):
    s = A.PlanSubscription(user_id=uid, provider='paypal', plan=plan,
                           billing_cycle='monthly',
                           price=A.PLAN_PRICING[plan]['monthly'],
                           status=estado, provider_ref=ref,
                           first_order_id=orden.id)
    A.db.session.add(s)
    A.db.session.commit()
    return s


def parchear():
    """PayPal de mentira: cancelar funciona y anota; sincronizar dice ACTIVE."""
    A._paypal_sub_cancel = _cancela
    A._paypal_sub_sync = _sync
    A._avisar_doble_cobro = _aviso


def _cancela(sub, motivo='x'):
    cortadas.append((sub.id, sub.plan))
    sub.status = 'cancelled'
    sub.cancelled_at = datetime.now(timezone.utc)
    A.db.session.commit()
    return True


def _sync(sub, data=None):
    if sub.status == 'pending':          # PayPal dice que sí quedó activa
        sub.status = 'active'
        sub.activated_at = datetime.now(timezone.utc)
        A.db.session.commit()
    return sub.status


def _aviso(vieja, nueva):
    avisos.append((vieja.id, nueva.id))
    return True


def main():
    global cortadas, avisos
    orig = (A._paypal_sub_cancel, A._paypal_sub_sync, A._avisar_doble_cobro)
    parchear()
    try:
        # ── 1 · el camino normal ──────────────────────────────────────────
        print('\n1 · compra Standard y luego sube a Premium (camino normal)')
        with A.app.app_context():
            A.db.create_all()
            uid = usuario('upg_cliente')
            o1 = pedido(uid, 'standard')
            s1 = suscripcion(uid, 'standard', o1, 'I-STD')
            A._sub_activada(s1)          # aprueba y vuelve al sitio
            u = A.db.session.get(A.User, uid)
            check(u.plan == 'standard', 'queda en Standard (%s)' % u.plan)
            check(A.db.session.get(A.PlanSubscription, s1.id).status == 'active',
                  'con su suscripción activa')

            # unas horas después decide subir
            cortadas = []
            o2 = pedido(uid, 'premium')
            s2 = suscripcion(uid, 'premium', o2, 'I-PRE')
            A._sub_activada(s2)
            u = A.db.session.get(A.User, uid)
            check(u.plan == 'premium', 'pasa a Premium (%s)' % u.plan)
            check((s1.id, 'standard') in cortadas,
                  '🔴 la suscripción de Standard se CORTA en PayPal %s' % cortadas)
            vivas = A.subs_por_cortar(u)
            check(len(vivas) == 1 and vivas[0].id == s2.id,
                  'queda UNA sola viva, la de Premium (%d)' % len(vivas))

        # ── 2 · y el mes que viene, ¿cuánto se cobra? ──────────────────────
        print('\n2 · llega la renovación')
        with A.app.app_context():
            u = A.db.session.get(A.User, uid)
            antes = A._aware(u.plan_expires_at)
            s2 = (A.PlanSubscription.query.filter_by(user_id=uid, plan='premium')
                  .order_by(A.PlanSubscription.id.desc()).first())
            o = A._sub_cobro(s2, 50.0, referencia='SALE-PRE-1')
            check(o and o.final_price == 50.0 and o.plan == 'premium',
                  'un solo cobro, de $%.2f por Premium' % (o.final_price if o else 0))
            cobrado = sum(x.final_price for x in
                          A.Order.query.filter_by(user_id=uid, status='paid').all())
            check(abs(cobrado - (25.0 + 50.0 + 50.0)) < 0.01,
                  'total pagado en toda la historia: $%.2f (25 alta + 50 upgrade '
                  '+ 50 renovación)' % cobrado)
            s1v = A.db.session.get(A.PlanSubscription, s1.id)
            check(s1v.status == 'cancelled',
                  'la de Standard sigue cancelada: no cobra nunca más')
            u = A.db.session.get(A.User, uid)
            check((A._aware(u.plan_expires_at) - antes).days == 30,
                  'y suma 30 días de acceso')

        # ── 3 · EL CASO FEO: el aviso se pierde y quedan las dos vivas ─────
        print('\n3 · sube de plan, se pierde el aviso, y las dos quedan vivas')
        with A.app.app_context():
            uid2 = usuario('upg_perdido')
            oa = pedido(uid2, 'standard')
            sa = suscripcion(uid2, 'standard', oa, 'I-STD2')
            A._sub_activada(sa)
            # aprueba Premium en PayPal pero cierra la pestaña; el aviso se
            # pierde → de nuestro lado sigue 'pending' y la vieja sigue activa
            ob = pedido(uid2, 'premium')
            sb = suscripcion(uid2, 'premium', ob, 'I-PRE2', estado='pending')
            vivas = A.subs_por_cortar(A.db.session.get(A.User, uid2))
            check(len(vivas) == 2, '🔴 hay DOS permisos de cobro en pie (%d)'
                  % len(vivas))

            # y llega el cobro mensual de la VIEJA — el doble cargo
            cortadas, avisos = [], []
            sobra = A._sobra_esta_suscripcion(sa)
            check(sobra, 'el sistema detecta que la vieja sobra')
            check((sa.id, 'standard') in cortadas,
                  '🔴 y la corta en el acto: no habrá un segundo cargo %s' % cortadas)
            check(avisos and avisos[0] == (sa.id, sb.id),
                  'se avisa al dueño para que decida el reembolso %s' % avisos)
            o = A._sub_cobro(sa, 25.0, referencia='SALE-STD2-1')
            check(o is not None and o.status == 'paid',
                  'el dinero que YA se movió se le acredita igual')
            vivas = A.subs_por_cortar(A.db.session.get(A.User, uid2))
            check(len(vivas) == 1 and vivas[0].plan == 'premium',
                  'y queda solo la de Premium (%s)'
                  % [(v.plan, v.status) for v in vivas])

        # ── 4 · bajar de plan es lo mismo ─────────────────────────────────
        print('\n4 · y al revés: de Premium a Standard')
        with A.app.app_context():
            uid3 = usuario('upg_baja')
            op = pedido(uid3, 'premium')
            sp = suscripcion(uid3, 'premium', op, 'I-PRE3')
            A._sub_activada(sp)
            cortadas = []
            os_ = pedido(uid3, 'standard')
            ss = suscripcion(uid3, 'standard', os_, 'I-STD3')
            A._sub_activada(ss)
            check((sp.id, 'premium') in cortadas,
                  'se corta la de Premium %s' % cortadas)
            vivas = A.subs_por_cortar(A.db.session.get(A.User, uid3))
            check(len(vivas) == 1 and vivas[0].plan == 'standard',
                  'queda solo Standard (%s)' % [(v.plan, v.status) for v in vivas])
            check(A.db.session.get(A.User, uid3).plan == 'standard',
                  'y el plan de la cuenta lo refleja')
    finally:
        (A._paypal_sub_cancel, A._paypal_sub_sync,
         A._avisar_doble_cobro) = orig

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
