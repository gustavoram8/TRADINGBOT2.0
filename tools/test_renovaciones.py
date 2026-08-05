# -*- coding: utf-8 -*-
"""Las renovaciones mensuales: la fecha que se le enseña y el corte de la baja.

    python3 tools/test_renovaciones.py

Tres preguntas del dueño, cada una con su comprobación:

  · "¿Dónde ve alguien la fecha de su renovación?" → en Ajustes, y tiene que
    ser la de PAYPAL (`next_billing_at`), no el vencimiento del acceso. No
    coinciden: comprar dos meses seguidos APILA acceso (60 días) mientras
    PayPal sigue cobrando cada 30. Por eso su pantalla decía "3 de noviembre"
    estando en agosto — tres compras de prueba apiladas.

  · "¿Sirven de verdad las renovaciones?" → se simula el aviso mensual de
    PayPal y se comprueba que extiende el plan, deja su fila en el libro y no
    regala meses si el aviso llega dos veces.

  · Y el hueco que apareció mirando esto: darse de baja cortaba solo la
    suscripción que teníamos por ACTIVA. Una que se quedara en 'pending'
    —aprobada en PayPal pero sin sincronizar— seguía cobrando mientras la
    pantalla decía "cancelado".
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scalpel'))
import app as A  # noqa: E402

ok = fallos = 0
CLAVE = 'Zx8!kQ2mLp7w'
cortadas = []


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


def entrar(c, nombre):
    c.post('/login', data={'identifier': nombre, 'password': CLAVE},
           follow_redirects=True)


def main():
    global cortadas
    with A.app.app_context():
        A.db.create_all()
        uid = usuario('ren_cliente', plan='premium')
        u = A.db.session.get(A.User, uid)
        # acceso pagado hasta dentro de 3 meses (tres compras apiladas, como
        # las pruebas del dueño), pero PayPal cobra el mes que viene
        u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=90)
        u.plan_cycle = 'monthly'
        A.db.session.commit()
        sub = A.PlanSubscription(
            user_id=uid, provider='paypal', plan='premium',
            billing_cycle='monthly', price=50.0, status='active',
            provider_ref='I-PRUEBA1',
            activated_at=datetime.now(timezone.utc),
            next_billing_at=datetime.now(timezone.utc) + timedelta(days=30))
        A.db.session.add(sub)
        A.db.session.commit()
        sid = sub.id
        cobro = sub.next_billing_at.strftime('%b %d, %Y')
        acceso = u.plan_expires_at.strftime('%b %d, %Y')

    # ── 1 · la fecha que se le enseña ─────────────────────────────────────
    print('\n1 · Ajustes enseña la fecha del COBRO, no la del acceso')
    c = A.app.test_client()
    entrar(c, 'ren_cliente')
    pag = c.get('/settings').get_data(as_text=True)
    check('settings.renewsAuto' in pag, 'dice "se renueva sola"')
    check(cobro in pag, '🔴 con la fecha de PayPal (%s)' % cobro)
    check('$50.00' in pag, 'y el importe exacto')
    check('settings.paidThrough' in pag and acceso in pag,
          'y aclara hasta cuándo está pagado el acceso (%s)' % acceso)

    # ── 2 · el cobro del mes siguiente ────────────────────────────────────
    print('\n2 · llega el aviso del cobro mensual')
    with A.app.app_context():
        u = A.db.session.get(A.User, uid)
        antes = A._aware(u.plan_expires_at)
        sub = A.db.session.get(A.PlanSubscription, sid)
        orden = A._sub_cobro(sub, 50.0, fee=2.0, referencia='VENTA-1')
        check(orden is not None and orden.status == 'paid',
              'queda un pedido pagado (#%s)' % (orden.id if orden else '—'))
        check(orden and orden.plan == 'premium' and orden.final_price == 50.0,
              'del plan y el importe correctos')
        u = A.db.session.get(A.User, uid)
        ahora = A._aware(u.plan_expires_at)
        check((ahora - antes).days == 30,
              'el acceso se estira 30 días más (%d)' % (ahora - antes).days)
        check(orden.celebrated_at is not None,
              'sin sacarle el "UNLOCKED" otra vez')

    # ── 3 · el mismo aviso dos veces no regala un mes ─────────────────────
    print('\n3 · PayPal reintenta el aviso')
    with A.app.app_context():
        u = A.db.session.get(A.User, uid)
        antes = A._aware(u.plan_expires_at)
        sub = A.db.session.get(A.PlanSubscription, sid)
        repe = A._sub_cobro(sub, 50.0, referencia='VENTA-1')
        check(repe is None, 'el segundo aviso se ignora')
        u = A.db.session.get(A.User, uid)
        check(A._aware(u.plan_expires_at) == antes, 'y la fecha no se mueve')

    # ── 4 · darse de baja corta TODO lo que PayPal podría cobrar ──────────
    print('\n4 · la baja corta también una suscripción "pending"')
    with A.app.app_context():
        # una segunda, aprobada en PayPal pero sin sincronizar de nuestro lado
        A.db.session.add(A.PlanSubscription(
            user_id=uid, provider='paypal', plan='premium',
            billing_cycle='monthly', price=50.0, status='pending',
            provider_ref='I-PENDIENTE'))
        A.db.session.commit()
        check(len(A.subs_por_cortar(A.db.session.get(A.User, uid))) == 2,
              'hay 2 permisos de cobro en pie')

    real = A._paypal_sub_cancel

    def finge_cancelar(sub, motivo='x'):
        cortadas.append(sub.provider_ref)
        sub.status = 'cancelled'
        sub.cancelled_at = datetime.now(timezone.utc)
        A.db.session.commit()
        return True
    A._paypal_sub_cancel = finge_cancelar
    try:
        c = A.app.test_client()
        entrar(c, 'ren_cliente')
        r = c.post('/account/cancel-plan', follow_redirects=False)
        check(r.status_code in (302, 303), 'la baja se acepta')
    finally:
        A._paypal_sub_cancel = real
    check(sorted(cortadas) == ['I-PENDIENTE', 'I-PRUEBA1'],
          '🔴 se cortaron LAS DOS en PayPal (%s)' % sorted(cortadas))
    with A.app.app_context():
        u = A.db.session.get(A.User, uid)
        check(u.cancel_at_period_end, 'queda marcada la baja')
        check(u.plan == 'premium', 'y conserva el acceso ya pagado')
        check(not A.subs_por_cortar(u), 'no queda ningún permiso de cobro')

    # ── 5 · si PayPal no responde, NO se le miente ────────────────────────
    print('\n5 · PayPal no contesta al cancelar')
    with A.app.app_context():
        uid2 = usuario('ren_fallo', plan='premium')
        u = A.db.session.get(A.User, uid2)
        u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=10)
        A.db.session.commit()
        A.db.session.add(A.PlanSubscription(
            user_id=uid2, provider='paypal', plan='premium',
            billing_cycle='monthly', price=50.0, status='active',
            provider_ref='I-TERCA'))
        A.db.session.commit()
    A._paypal_sub_cancel = lambda sub, motivo='x': False
    try:
        c = A.app.test_client()
        entrar(c, 'ren_fallo')
        r = c.post('/account/cancel-plan', follow_redirects=False)
        check('cancel_failed' in (r.headers.get('Location') or ''),
              'se le avisa de que NO se pudo cancelar')
    finally:
        A._paypal_sub_cancel = real
    with A.app.app_context():
        u = A.db.session.get(A.User, uid2)
        check(not u.cancel_at_period_end,
              '🔴 y NO se marca como cancelado (sería prometer sin cumplir)')

    # ── 6 · una suscripción que nunca llegó a PayPal no bloquea la baja ───
    print('\n6 · suscripción que nunca llegó a existir en PayPal')
    with A.app.app_context():
        uid3 = usuario('ren_huerfana', plan='standard')
        u = A.db.session.get(A.User, uid3)
        u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=10)
        A.db.session.commit()
        A.db.session.add(A.PlanSubscription(
            user_id=uid3, provider='paypal', plan='standard',
            billing_cycle='monthly', price=25.0, status='pending',
            provider_ref=None))
        A.db.session.commit()
    c = A.app.test_client()
    entrar(c, 'ren_huerfana')
    r = c.post('/account/cancel-plan', follow_redirects=False)
    check('cancelled=1' in (r.headers.get('Location') or ''),
          'la baja sale adelante igual')
    with A.app.app_context():
        check(not A.subs_por_cortar(A.db.session.get(A.User, uid3)),
              'y la fila huérfana queda cerrada')

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
