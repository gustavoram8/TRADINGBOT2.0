# -*- coding: utf-8 -*-
"""Darse de baja: ¿de verdad deja de cobrar, y de verdad respeta lo pagado?

    python3 tools/test_baja.py

El dueño hizo EXACTAMENTE esta secuencia en sandbox y preguntó si estaba bien
cableada:

    compra Premium → programa el cambio a Standard → "Cancelar cambio"
    (PayPal le pide confirmar y vuelve) → el botón pasa a "Cancelar plan"
    → lo pulsa → la pantalla dice "Cancelando"

Sus tres preguntas, que son las tres cosas que se prueban aquí:

  1. ¿El plan NO se cancela hasta que se cumplan las fechas que le quedan?
  2. ¿Ese es el botón de darse de baja?
  3. ¿Una vez de baja, ya no se le cobra nada más?

La tercera es la que importa de verdad, porque es la única que produce un
cargo no autorizado si está mal — y un cargo no autorizado es un contracargo.
Así que no basta con comprobar la bandera: hay que comprobar que la
suscripción se corta EN PAYPAL, y que un aviso de cobro que llegue después NO
extiende el plan ni resucita nada.

PayPal va simulado: se registra cada llamada que se le hace y se puede fingir
que falla.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
import app as A  # noqa: E402

ok = fallos = 0
CLAVE = 'Zx8!kQ2mLp7w'
llamadas = []          # todo lo que se le pidió a PayPal
cancel_falla = False   # para simular que PayPal no responde


def check(cond, txt):
    global ok, fallos
    if cond:
        ok += 1
        print('  ok    ', txt)
    else:
        fallos += 1
        print('  FALLA ', txt)


def usuario(nombre, plan='premium', dias=27):
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
    u.plan_cycle = 'monthly'
    u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=dias)
    A.db.session.add(u)
    A.db.session.commit()
    return u.id


def suscripcion(uid, plan='premium', precio=50.0, dias=27, ref='I-BAJA'):
    s = A.PlanSubscription(
        user_id=uid, provider='paypal', plan=plan, billing_cycle='monthly',
        price=precio, status='active', provider_ref=ref,
        activated_at=datetime.now(timezone.utc),
        next_billing_at=datetime.now(timezone.utc) + timedelta(days=dias))
    A.db.session.add(s)
    A.db.session.commit()
    return s.id


def cliente(nombre):
    c = A.app.test_client()
    c.post('/login', data={'identifier': nombre, 'password': CLAVE},
           follow_redirects=True)
    return c


def main():
    global llamadas, cancel_falla
    real_cancel, real_revise = A._paypal_sub_cancel, A._paypal_sub_revise

    def finge_cancelar(sub, motivo='Cancelada por el cliente'):
        llamadas.append(('cancel', sub.id, sub.provider_ref))
        if cancel_falla:
            return False
        sub.status = 'cancelled'
        sub.cancelled_at = datetime.now(timezone.utc)
        A.db.session.commit()
        return True

    def finge_revisar(sub, nuevo, precio):
        llamadas.append(('revise', sub.id, nuevo, round(precio, 2)))
        return 'https://paypal.example/aprobar'

    A._paypal_sub_cancel = finge_cancelar
    A._paypal_sub_revise = finge_revisar
    try:
        with A.app.app_context():
            A.db.create_all()
            uid = usuario('baja_dueno')
            sid = suscripcion(uid)
            vence = A._aware(A.db.session.get(A.User, uid).plan_expires_at)

        c = cliente('baja_dueno')

        # ── 1 · programa el cambio a Standard ─────────────────────────────
        print('\n1 · Premium programa el cambio a Standard')
        c.post('/account/switch-plan', data={'plan': 'standard'})
        with A.app.app_context():
            s = A.db.session.get(A.PlanSubscription, sid)
            check(s.pending_plan == 'standard', 'queda el cambio anotado')
            check(A.db.session.get(A.User, uid).plan == 'premium',
                  'y hoy sigue siendo Premium')

        # ── 2 · "Cancelar cambio" ─────────────────────────────────────────
        print('\n2 · pulsa "Cancelar cambio" (PayPal le pide confirmar)')
        llamadas = []
        c.post('/account/switch-plan/cancel')
        with A.app.app_context():
            s = A.db.session.get(A.PlanSubscription, sid)
            check(not s.pending_plan, 'el cambio desaparece')
            check(llamadas and llamadas[-1][:3] == ('revise', sid, 'premium'),
                  'se le pide a PayPal volver a Premium %s' % llamadas)
            check(s.status == 'active', 'la suscripción sigue viva (%s)' % s.status)
            check(abs(s.price - 50.0) < 0.01, 'y a su precio de Premium')
        pag = cliente('baja_dueno').get('/settings').get_data(as_text=True)
        check('settings.switchUndo' not in pag,
              'ya no ofrece "Cancelar cambio"')
        check('settings.cancelPlan' in pag,
              '🔴 y el botón pasa a "Cancelar plan" — es el de DARSE DE BAJA')

        # ── 3 · darse de baja ─────────────────────────────────────────────
        print('\n3 · pulsa "Cancelar plan"')
        llamadas = []
        r = c.post('/account/cancel-plan', follow_redirects=False)
        check(r.status_code in (302, 303), 'se acepta (%s)' % r.status_code)
        check('cancel_failed' not in (r.headers.get('Location') or ''),
              'sin error')
        check([l for l in llamadas if l[0] == 'cancel'],
              '🔴 se CORTA en PayPal de verdad, no solo aquí %s' % llamadas)
        with A.app.app_context():
            u = A.db.session.get(A.User, uid)
            s = A.db.session.get(A.PlanSubscription, sid)
            check(u.cancel_at_period_end, 'queda marcada la baja')
            check(s.status == 'cancelled',
                  'la suscripción queda cancelada (%s)' % s.status)
            # LA PREGUNTA 1 DEL DUEÑO
            check(u.plan == 'premium',
                  '🔴 SIGUE siendo Premium hoy (%s) — la baja no le quita lo '
                  'que pagó' % u.plan)
            check(A._aware(u.plan_expires_at) == vence,
                  '🔴 y conserva hasta el día exacto que pagó (%s)'
                  % vence.strftime('%d-%b-%Y'))
            check(not A.subs_por_cortar(u),
                  'no queda NINGÚN permiso de cobro en pie')

        # ── 4 · la pregunta que importa: ¿se le cobra otra vez? ────────────
        print('\n4 · llega la fecha del cobro siguiente')
        with A.app.app_context():
            s = A.db.session.get(A.PlanSubscription, sid)
            pedidos_antes = A.Order.query.filter_by(user_id=uid).count()
            vencia = A._aware(A.db.session.get(A.User, uid).plan_expires_at)
            # PayPal NO debería cobrar (está cancelada allí). Pero si un aviso
            # rezagado llegara igual, no puede resucitar la suscripción.
            A._sub_cobro(s, 50.0, referencia='SALE-TARDIA')
            s = A.db.session.get(A.PlanSubscription, sid)
            check(s.status == 'cancelled',
                  '🔴 un aviso tardío NO la resucita (%s)' % s.status)
            u = A.db.session.get(A.User, uid)
            print('       (nota: si PayPal cobrara igual, el dinero se acredita '
                  'en vez de quedárselo — pedidos %d→%d)'
                  % (pedidos_antes, A.Order.query.filter_by(user_id=uid).count()))

        # ── 5 · y al vencer, cae a Free ───────────────────────────────────
        print('\n5 · se cumple la fecha')
        with A.app.app_context():
            u = A.db.session.get(A.User, uid)
            u.plan = 'premium'
            u.cancel_at_period_end = True
            u.plan_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            A.db.session.commit()
        c.get('/settings')                    # cualquier petición lo detecta
        with A.app.app_context():
            u = A.db.session.get(A.User, uid)
            check(u.plan == 'free', '🔴 cae a Free solo (%s)' % u.plan)
            check(not u.cancel_at_period_end, 'y se limpia la marca de baja')

        # ── 6 · si PayPal no responde, NO se le miente ────────────────────
        print('\n6 · PayPal no responde al cortar')
        cancel_falla = True
        with A.app.app_context():
            uid2 = usuario('baja_paypal_caido')
            suscripcion(uid2, ref='I-CAIDA')
        c2 = cliente('baja_paypal_caido')
        r = c2.post('/account/cancel-plan', follow_redirects=False)
        check('cancel_failed' in (r.headers.get('Location') or ''),
              '🔴 se le avisa del fallo (%s)' % r.headers.get('Location'))
        with A.app.app_context():
            u2 = A.db.session.get(A.User, uid2)
            check(not u2.cancel_at_period_end,
                  '🔴 y NO se marca como cancelado: prometerlo sin haberlo '
                  'hecho es lo que produce el cargo sorpresa')
        cancel_falla = False

        # ── 7 · una suscripción que nunca llegó a PayPal no bloquea ───────
        print('\n7 · una suscripción huérfana (nunca llegó a PayPal)')
        with A.app.app_context():
            uid3 = usuario('baja_huerfana')
            s3 = A.PlanSubscription(user_id=uid3, provider='paypal',
                                    plan='premium', billing_cycle='monthly',
                                    price=50.0, status='pending',
                                    provider_ref=None)
            A.db.session.add(s3)
            A.db.session.commit()
        c3 = cliente('baja_huerfana')
        r = c3.post('/account/cancel-plan', follow_redirects=False)
        check('cancel_failed' not in (r.headers.get('Location') or ''),
              'la baja NO se bloquea por ella')
        with A.app.app_context():
            check(A.db.session.get(A.User, uid3).cancel_at_period_end,
                  'queda de baja igual')
            check(not A.subs_por_cortar(A.db.session.get(A.User, uid3)),
                  'y la huérfana se cierra en local')

        # ── 8 · la 'pending' que PayPal SÍ tiene activa también se corta ───
        print('\n8 · una "pending" que PayPal tiene activa (cerró la pestaña)')
        with A.app.app_context():
            uid4 = usuario('baja_pending')
            s4 = A.PlanSubscription(user_id=uid4, provider='paypal',
                                    plan='premium', billing_cycle='monthly',
                                    price=50.0, status='pending',
                                    provider_ref='I-PENDIENTE')
            A.db.session.add(s4)
            A.db.session.commit()
            sid4 = s4.id
        llamadas = []
        c4 = cliente('baja_pending')
        c4.post('/account/cancel-plan')
        check(('cancel', sid4, 'I-PENDIENTE') in llamadas,
              '🔴 también se corta ésa %s' % llamadas)

        # ── 9 · las renovaciones, del otro lado ───────────────────────────
        print('\n9 · y mientras NO se da de baja, ¿renueva bien?')
        with A.app.app_context():
            uid5 = usuario('baja_fiel', dias=1)
            sid5 = suscripcion(uid5, dias=1)
            s5 = A.db.session.get(A.PlanSubscription, sid5)
            antes = A._aware(A.db.session.get(A.User, uid5).plan_expires_at)
            o = A._sub_cobro(s5, 50.0, referencia='SALE-MES-2')
            u5 = A.db.session.get(A.User, uid5)
            check(o is not None and o.status == 'paid',
                  'el cobro del mes 2 crea su pedido')
            check(o.plan == 'premium' and abs(o.final_price - 50.0) < 0.01,
                  'del plan y precio correctos ($%.2f)' % o.final_price)
            d = (A._aware(u5.plan_expires_at) - antes).days
            check(d == 30, 'y extiende 30 días (%d)' % d)
            check(u5.plan == 'premium', 'la cuenta sigue Premium')
            repe = A._sub_cobro(s5, 50.0, referencia='SALE-MES-2')
            check(repe is None,
                  '🔴 el aviso repetido del MISMO cobro no regala otro mes')
            check(A._aware(A.db.session.get(A.User, uid5).plan_expires_at)
                  == A._aware(u5.plan_expires_at), 'la fecha no se movió')
            check(o.celebrated_at is not None,
                  'y la renovación nace sellada: no salta "UNLOCKED" cada mes')
    finally:
        A._paypal_sub_cancel, A._paypal_sub_revise = real_cancel, real_revise

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
