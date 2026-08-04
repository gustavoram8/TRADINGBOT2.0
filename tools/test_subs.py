# -*- coding: utf-8 -*-
"""Suscripciones que se renuevan solas, ejecutadas de verdad.

    python3 tools/test_subs.py

Con PayPal SIMULADO: se sustituye `_paypal_api` por una función que responde lo
que respondería PayPal, y se comprueba el circuito completo por dentro.

Lo que de verdad se está probando aquí no es "que funcione el camino feliz",
sino las cuatro formas conocidas de que un cobro recurrente salga caro:

  1. Que el segundo mes se cobre y el plan NO se extienda. Es el fallo
     silencioso del sistema: en una renovación no hay nadie mirando la
     pantalla, así que si el aviso se pierde nadie se entera hasta la queja.
  2. Que un aviso repetido regale un mes. PayPal reintenta sus avisos.
  3. Que "cancelar" no cancele. El cargo del mes siguiente sobre alguien que
     pulsó el botón de baja es un contracargo garantizado.
  4. Que el descuento del socio no sobreviva a la renovación — que es
     exactamente la promesa del acuerdo comercial.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scalpel'))
# Se ponen ANTES de importar: la configuración se lee al importar el módulo.
os.environ['PAYPAL_CLIENT_ID'] = 'cid'
os.environ['PAYPAL_SECRET'] = 'sec'
os.environ['PAYPAL_WEBHOOK_ID'] = 'whid'
os.environ['PAYPAL_ENV'] = 'live'          # para que el libro de ventas anote
os.environ['PAYPAL_PLAN_STANDARD'] = 'P-STD'
os.environ['PAYPAL_PLAN_PREMIUM'] = 'P-PRM'
os.environ['SITE_URL'] = 'https://tradeable.academy'
os.environ.setdefault('ANNUAL_PLANS_ENABLED', '1')   # para poder probar el anual

import app as A  # noqa: E402

ok = fallos = 0
LLAMADAS = []          # todo lo que se le mandó a PayPal
ESTADO_SUB = {'valor': 'ACTIVE'}
CANCELA_FALLA = {'valor': False}


def check(cond, txt):
    global ok, fallos
    if cond:
        ok += 1
        print('  ok   ', txt)
    else:
        fallos += 1
        print('  FALLA ', txt)


def falso_api(method, path, payload=None, request_id=None):
    """PayPal de mentira. Devuelve lo mismo que el de verdad, en forma."""
    LLAMADAS.append((method, path, payload))
    if path.endswith('/verify-webhook-signature'):
        return 200, {'verification_status': 'SUCCESS'}
    if path == '/v1/billing/subscriptions' and method == 'POST':
        return 201, {'id': 'I-SUB%03d' % len(LLAMADAS), 'status': 'APPROVAL_PENDING',
                     'links': [{'rel': 'approve', 'href': 'https://paypal/aprobar'}]}
    if path.startswith('/v1/billing/subscriptions/') and path.endswith('/cancel'):
        return (500, {}) if CANCELA_FALLA['valor'] else (204, {})
    if path.startswith('/v1/billing/subscriptions/'):
        prox = (datetime.now(timezone.utc) + timedelta(days=30))
        return 200, {'id': path.rsplit('/', 1)[1], 'status': ESTADO_SUB['valor'],
                     'billing_info': {'next_billing_time':
                                      prox.strftime('%Y-%m-%dT%H:%M:%SZ')}}
    if path == '/v2/checkout/orders' and method == 'POST':
        return 201, {'id': 'PAGO-SUELTO',
                     'links': [{'rel': 'approve', 'href': 'https://paypal/suelto'}]}
    return 200, {}


A._paypal_api = falso_api


def entrar(c, u):
    c.post('/login', data={'identifier': u, 'password': 'Zx8!kQ2mLp7w'},
           follow_redirects=True)


def crear_usuario(nombre):
    with A.app.app_context():
        u = A.User.query.filter_by(username=nombre).first()
        if u:
            A.KnownDevice.query.filter_by(user_id=u.id).delete()
            A.SaleBreakdown.query.filter_by(user_id=u.id).delete()
            A.PlanSubscription.query.filter_by(user_id=u.id).delete()
            A.Order.query.filter_by(user_id=u.id).delete()
            A.db.session.delete(u)
            A.db.session.commit()
        u = A.User(username=nombre, email=nombre + '@ej.com')
        u.set_password('Zx8!kQ2mLp7w')
        for campo in ('email_verified', 'is_verified', 'verified'):
            if hasattr(u, campo):
                setattr(u, campo, True)
        A.db.session.add(u)
        A.db.session.commit()
        return u.id


def webhook(tipo, recurso):
    """Manda un aviso al endpoint real, con la firma ya dada por buena."""
    with A.app.test_client() as c:
        return c.post('/webhook/paypal',
                      json={'event_type': tipo, 'resource': recurso})


def main():
    with A.app.app_context():
        A.db.create_all()
        for code in ('SOCIOSUB',):
            pc = A.PromoCode.query.filter(
                A.db.func.lower(A.PromoCode.code) == code.lower()).first()
            if pc:
                A.db.session.delete(pc)
        # ⚠️ El commit va AQUÍ, no al final: SQLAlchemy agrupa por tipo de
        # operación y emite el INSERT antes que el DELETE, así que borrar y
        # volver a crear en la misma tanda choca contra la clave única.
        A.db.session.commit()
        A.db.session.add(A.PromoCode(code='SOCIOSUB', discount_pct=20, kind='creator',
                                     creator_name='El Socio', valid_for='both'))
        A.db.session.commit()

    check(A.PAYPAL_SUBS_ENABLED, 'las suscripciones quedan encendidas con sus dos planes')

    # ═══ 1 · Alta: mensual + PayPal = suscripción, no pago suelto ═══════════
    print('\n1 · el alta')
    uid = crear_usuario('subs1')
    with A.app.test_client() as c:
        entrar(c, 'subs1')
        r = c.post('/checkout/create',
                   data={'plan': 'premium', 'cycle': 'monthly', 'method': 'paypal'},
                   follow_redirects=False)
        check(r.status_code == 303 and 'paypal/aprobar' in (r.headers.get('Location') or ''),
              'el comprador sale hacia PayPal (%s)' % r.status_code)

    creaciones = [c for c in LLAMADAS if c[1] == '/v1/billing/subscriptions']
    check(len(creaciones) == 1, 'se abrió UNA suscripción')
    check(not any(c[1] == '/v2/checkout/orders' for c in LLAMADAS),
          'NO se creó un pago suelto en paralelo')
    cuerpo = creaciones[0][2]
    check(cuerpo.get('plan_id') == 'P-PRM', 'usa el plan de Premium')
    precio = cuerpo['plan']['billing_cycles'][0]['pricing_scheme']['fixed_price']['value']
    check(precio == '50.00', 'el importe mensual que se manda es $50.00 (%s)' % precio)
    vuelta = cuerpo['application_context']['return_url']
    check(vuelta.startswith('https://tradeable.academy/'),
          'la vuelta apunta al dominio con HTTPS (%s)' % vuelta)

    with A.app.app_context():
        sub = A.PlanSubscription.query.filter_by(user_id=uid).first()
        check(sub is not None and sub.status == 'pending',
              'la suscripción nace "pending": aprobada no es cobrada')
        u = A.db.session.get(A.User, uid)
        check(u.plan == 'free', 'el plan NO se entrega antes de que PayPal cobre')
        sub_id, sub_ref = sub.id, sub.provider_ref
        primera_orden = sub.first_order_id

    # ═══ 2 · La vuelta del comprador entrega el plan ════════════════════════
    print('\n2 · la vuelta')
    with A.app.test_client() as c:
        entrar(c, 'subs1')
        c.get('/checkout/paypal/subscription/%d' % sub_id, follow_redirects=False)
    with A.app.app_context():
        u = A.db.session.get(A.User, uid)
        o = A.db.session.get(A.Order, primera_orden)
        sub = A.db.session.get(A.PlanSubscription, sub_id)
        check(u.plan == 'premium', 'el plan queda entregado (%s)' % u.plan)
        check(o.status == 'paid', 'el pedido de alta queda pagado')
        check(sub.status == 'active', 'la suscripción pasa a activa')
        check(sub.next_billing_at is not None, 'se guarda cuándo toca el próximo cobro')
        vence1 = A._aware(u.plan_expires_at)
        sb = A.SaleBreakdown.query.filter_by(order_id=o.id).first()
        check(sb is not None, 'la venta entra en el libro')

    # ═══ 3 · La renovación: el cobro del mes 2 ══════════════════════════════
    print('\n3 · la renovación')
    r = webhook('PAYMENT.SALE.COMPLETED',
                {'id': 'VENTA-2', 'billing_agreement_id': sub_ref,
                 'amount': {'total': '50.00'},
                 'transaction_fee': {'value': '2.99'}})
    check(r.status_code == 200, 'el aviso de cobro se acepta')
    with A.app.app_context():
        u = A.db.session.get(A.User, uid)
        vence2 = A._aware(u.plan_expires_at)
        check(vence2 > vence1, 'el plan se extiende (%s → %s)'
              % (vence1.date(), vence2.date()))
        check(abs((vence2 - vence1).days - 30) <= 1,
              'se extiende 30 días, ni más ni menos (%d)' % (vence2 - vence1).days)
        nuevos = A.Order.query.filter_by(user_id=uid, provider_ref='VENTA-2').all()
        check(len(nuevos) == 1, 'la renovación deja UN pedido nuevo')
        sb = A.SaleBreakdown.query.filter_by(order_id=nuevos[0].id).first()
        check(sb is not None, 'la renovación también entra en el libro de ventas')
        check(sb is not None and abs(sb.processor_fee - 2.99) < 0.01,
              'se guarda la comisión REAL de PayPal, no una estimación')

    # ═══ 4 · El mismo aviso otra vez no regala un mes ═══════════════════════
    print('\n4 · el aviso repetido')
    webhook('PAYMENT.SALE.COMPLETED',
            {'id': 'VENTA-2', 'billing_agreement_id': sub_ref,
             'amount': {'total': '50.00'}})
    with A.app.app_context():
        u = A.db.session.get(A.User, uid)
        check(A._aware(u.plan_expires_at) == vence2,
              'el plan no se movió con el aviso repetido')
        check(A.Order.query.filter_by(user_id=uid, provider_ref='VENTA-2').count() == 1,
              'no se creó un pedido duplicado')

    # ═══ 5 · La baja ════════════════════════════════════════════════════════
    print('\n5 · la baja')
    antes = len(LLAMADAS)
    with A.app.test_client() as c:
        entrar(c, 'subs1')
        c.post('/account/cancel-plan', follow_redirects=False)
    cancelaciones = [x for x in LLAMADAS[antes:] if x[1].endswith('/cancel')]
    check(len(cancelaciones) == 1, 'el botón de baja SÍ llama a PayPal para cortar el cobro')
    with A.app.app_context():
        u = A.db.session.get(A.User, uid)
        sub = A.db.session.get(A.PlanSubscription, sub_id)
        check(sub.status == 'cancelled', 'la suscripción queda cancelada')
        check(u.cancel_at_period_end, 'la cuenta queda marcada como "termina al vencer"')
        check(u.plan == 'premium', 'el plan NO se le quita: conserva lo pagado')
        check(A._aware(u.plan_expires_at) == vence2, 'la fecha de vencimiento no se toca')

    # ═══ 6 · Si PayPal no responde, NO se le promete la baja ════════════════
    print('\n6 · la baja que falla')
    uid2 = crear_usuario('subs2')
    with A.app.app_context():
        s = A.PlanSubscription(user_id=uid2, plan='premium', price=50.0,
                               provider_ref='I-OTRA', status='active')
        A.db.session.add(s)
        u = A.db.session.get(A.User, uid2)
        u.plan = 'premium'
        u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=20)
        A.db.session.commit()
    CANCELA_FALLA['valor'] = True
    with A.app.test_client() as c:
        entrar(c, 'subs2')
        r = c.post('/account/cancel-plan', follow_redirects=False)
    CANCELA_FALLA['valor'] = False
    check('cancel_failed' in (r.headers.get('Location') or ''),
          'se le dice que no se pudo, no que ya está cancelado')
    with A.app.app_context():
        u = A.db.session.get(A.User, uid2)
        check(not u.cancel_at_period_end,
              'NO se marca como cancelado: prometerlo sin cortarlo produce el cargo sorpresa')

    # ═══ 7 · El descuento del socio sobrevive a la renovación ═══════════════
    print('\n7 · el descuento del socio')
    uid3 = crear_usuario('subs3')
    with A.app.test_client() as c:
        entrar(c, 'subs3')
        c.post('/checkout/create',
               data={'plan': 'premium', 'cycle': 'monthly',
                     'promo_code': 'SOCIOSUB', 'method': 'paypal'},
               follow_redirects=False)
    ult = [x for x in LLAMADAS if x[1] == '/v1/billing/subscriptions'][-1][2]
    p = ult['plan']['billing_cycles'][0]['pricing_scheme']['fixed_price']['value']
    check(p == '40.00', 'a PayPal se le manda $40.00, no el precio de lista (%s)' % p)
    with A.app.app_context():
        s3 = A.PlanSubscription.query.filter_by(user_id=uid3).first()
        check(s3.price == 40.0 and s3.promo_code == 'SOCIOSUB',
              'la suscripción guarda el precio y el código del socio')
        ref3, id3 = s3.provider_ref, s3.id
    with A.app.test_client() as c:
        entrar(c, 'subs3')
        c.get('/checkout/paypal/subscription/%d' % id3)
    webhook('PAYMENT.SALE.COMPLETED',
            {'id': 'VENTA-S3', 'billing_agreement_id': ref3,
             'amount': {'total': '40.00'}})
    with A.app.app_context():
        ren = A.Order.query.filter_by(user_id=uid3, provider_ref='VENTA-S3').first()
        check(ren is not None and ren.final_price == 40.0 and ren.promo_code == 'SOCIOSUB',
              'la renovación cuesta $40 y CONSERVA el código: el socio cobra otra vez')
        sb = A.SaleBreakdown.query.filter_by(order_id=ren.id).first()
        check(sb is not None and sb.partner == 'El Socio' and (sb.commission_amt or 0) > 0,
              'el libro le apunta comisión al socio en la renovación (%s, $%.2f)'
              % (sb.partner if sb else '—', (sb.commission_amt or 0) if sb else 0))

    # ═══ 8 · Subir de plan cierra la suscripción anterior ═══════════════════
    print('\n8 · la subida de plan')
    uid4 = crear_usuario('subs4')
    with A.app.app_context():
        vieja = A.PlanSubscription(user_id=uid4, plan='standard', price=25.0,
                                   provider_ref='I-VIEJA', status='active')
        A.db.session.add(vieja)
        A.db.session.commit()
        vieja_id = vieja.id
    with A.app.test_client() as c:
        entrar(c, 'subs4')
        c.post('/checkout/create',
               data={'plan': 'premium', 'cycle': 'monthly', 'method': 'paypal'},
               follow_redirects=False)
    with A.app.app_context():
        nueva = A.PlanSubscription.query.filter_by(
            user_id=uid4, plan='premium').first()
        nid = nueva.id
    with A.app.test_client() as c:
        entrar(c, 'subs4')
        c.get('/checkout/paypal/subscription/%d' % nid)
    with A.app.app_context():
        check(A.db.session.get(A.PlanSubscription, vieja_id).status == 'cancelled',
              'la suscripción de Standard se corta sola: no se cobran las dos')
        check(A.db.session.get(A.PlanSubscription, nid).status == 'active',
              'la de Premium queda activa')

    # ═══ 9 · Lo que NO se convierte en suscripción ══════════════════════════
    print('\n9 · lo que se queda en pago suelto')
    with A.app.app_context():
        anual = A.Order(user_id=uid4, plan='premium', billing_cycle='annual',
                        base_price=480.0, discount_pct=0, final_price=480.0,
                        status='pending')
        check(not A._subs_ok_for(anual),
              'un ANUAL nunca se renueva solo (el contracargo de $408 no se cubre)')
        gratis = A.Order(user_id=uid4, plan='premium', billing_cycle='monthly',
                         base_price=50.0, discount_pct=100, final_price=0.0,
                         status='pending')
        check(not A._subs_ok_for(gratis), 'un pedido de $0 no abre suscripción')

    # ═══ 10 · Un cobro rechazado no quita el plan ═══════════════════════════
    print('\n10 · el cobro rechazado')
    with A.app.app_context():
        u = A.db.session.get(A.User, uid3)
        plan_antes, vence_antes = u.plan, A._aware(u.plan_expires_at)
    r = webhook('BILLING.SUBSCRIPTION.PAYMENT.FAILED', {'id': ref3})
    check(r.status_code == 200, 'el aviso de cobro fallido se acepta')
    with A.app.app_context():
        u = A.db.session.get(A.User, uid3)
        check(u.plan == plan_antes and A._aware(u.plan_expires_at) == vence_antes,
              'no se le toca el plan: PayPal aún va a reintentar el cobro')
        s = A.db.session.get(A.PlanSubscription, id3)
        check((s.note or '').startswith('Cobro rechazado'), 'queda anotado para el dueño')

    # ═══ 11 · Un aviso de una suscripción desconocida no rompe nada ═════════
    print('\n11 · el aviso huérfano')
    r = webhook('PAYMENT.SALE.COMPLETED',
                {'id': 'X', 'billing_agreement_id': 'I-QUE-NO-EXISTE',
                 'amount': {'total': '50.00'}})
    check(r.status_code == 200 and (r.get_json() or {}).get('ignored'),
          'se ignora sin dar error (PayPal reintentaría un 500 para siempre)')

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 52, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
