# -*- coding: utf-8 -*-
"""Qué pasó de verdad con las compras de una cuenta. SOLO LECTURA.

    python3 tools/diagnostico_compra.py <usuario-o-correo>
    python3 tools/diagnostico_compra.py            # las últimas compras de todos

Se corre EN EL VPS, donde está la base de producción. No escribe nada, no
imprime contraseñas ni claves, y no toca PayPal: solo lee las filas y las pone
en orden cronológico para poder responder una pregunta concreta —

    ¿el pedido que se pagó nació cuando el comprador pulsó "pagar",
     o ya estaba ahí de un intento anterior?

Que es la diferencia entre "el carrito creó el pedido equivocado" y "el sitio
te mandó a pagar un pedido viejo". Son dos bugs distintos y se arreglan en
sitios distintos.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scalpel'))
import app as A  # noqa: E402


def h(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else '—'


def cuenta(u):
    print('\n' + '=' * 78)
    print('CUENTA  %s  <%s>   id=%d' % (u.username, u.email, u.id))
    print('  plan actual: %s · vence %s · ciclo %s · cancelado=%s'
          % (u.plan, h(u.plan_expires_at), u.plan_cycle,
             getattr(u, 'cancel_at_period_end', None)))

    pedidos = (A.Order.query.filter_by(user_id=u.id)
               .order_by(A.Order.id).all())
    print('\nPEDIDOS (%d)' % len(pedidos))
    if not pedidos:
        print('  — ninguno')
    for o in pedidos:
        print('  #%-4d %-8s %-8s $%-7.2f %-10s método=%-14s'
              % (o.id, o.plan, o.billing_cycle, o.final_price or 0,
                 o.status, o.payment_method or '—'))
        print('        creado %s   pagado %s   aplicado %s'
              % (h(o.created_at), h(o.paid_at), h(o.applied_at)))
        extra = []
        if o.promo_code:
            extra.append('cupón=%s' % o.promo_code)
        if o.provider_ref:
            extra.append('ref=%s' % o.provider_ref)
        if o.pay_status:
            extra.append('estado_pago=%s' % o.pay_status)
        if o.paid_amount is not None:
            extra.append('cobrado=%.2f %s' % (o.paid_amount, o.pay_currency or ''))
        if o.note:
            extra.append('nota=%s' % o.note)
        if extra:
            print('        ' + ' · '.join(extra))

    subs = (A.PlanSubscription.query.filter_by(user_id=u.id)
            .order_by(A.PlanSubscription.id).all())
    print('\nSUSCRIPCIONES (%d)' % len(subs))
    if not subs:
        print('  — ninguna')
    for s in subs:
        print('  #%-4d %-8s $%-7.2f %-10s ref=%s'
              % (s.id, s.plan, s.price or 0, s.status, s.provider_ref or '—'))
        print('        pedido inicial=#%s   creada %s   activada %s   '
              'último cobro %s   próximo %s   cancelada %s'
              % (s.first_order_id, h(s.created_at), h(s.activated_at),
                 h(s.last_payment_at), h(s.next_billing_at), h(s.cancelled_at)))
        if s.note:
            print('        nota=%s' % s.note)

    tipos = ('order_created', 'order_cancelled', 'order_free_activated',
             'order_paid', 'plan_activated', 'plan_cancelled',
             'subscription_charge', 'admin_set_plan')
    ev = (A.AuditEvent.query
          .filter(A.AuditEvent.user_id == u.id,
                  A.AuditEvent.event_type.in_(tipos))
          .order_by(A.AuditEvent.id).all())
    print('\nRASTRO (%d eventos)' % len(ev))
    for e in ev:
        print('  %s  %-22s %s' % (h(e.created_at), e.event_type, e.detail or ''))

    # ¿De dónde salen los días de acceso que tiene hoy?
    aplicados = [o for o in pedidos if o.applied_at]
    if aplicados:
        print('\nDE DÓNDE SALEN SUS DÍAS DE ACCESO')
        total = 0
        for o in aplicados:
            dias = 365 if o.billing_cycle == 'annual' else 30
            total += dias
            print('  +%-4d días  pedido #%-4d %-8s aplicado %s'
                  % (dias, o.id, o.plan, h(o.applied_at)))
        print('  %s' % ('─' * 52))
        print('  %d días comprados en total, en %d pedido(s).' % (total, len(aplicados)))
        if len(aplicados) > 1:
            print('  ⚠️ Más de un pedido aplicado: si son del MISMO plan y se')
            print('     compraron sin que venciera el anterior, se apilaron. Eso')
            print('     ya no puede volver a pasar (el candado nuevo lo impide),')
            print('     pero los días viejos siguen ahí: se limpian poniendo la')
            print('     cuenta en Free y devolviéndole el plan desde /admin.')

    # La lectura que interesa, dicha en una línea.
    pagados = [o for o in pedidos if o.status == 'paid']
    if pagados:
        ult = pagados[-1]
        antes = [o for o in pedidos
                 if o.id != ult.id and o.created_at and ult.created_at
                 and o.created_at < ult.created_at]
        print('\nLECTURA')
        print('  El último pedido PAGADO es #%d (%s, $%.2f), creado el %s.'
              % (ult.id, ult.plan, ult.final_price or 0, h(ult.created_at)))
        if antes:
            print('  Antes de él ya existían %d pedido(s): %s'
                  % (len(antes), ', '.join('#%d %s/%s' % (o.id, o.plan, o.status)
                                           for o in antes)))
            print('  → Si el comprador pidió OTRO plan y aun así se pagó éste,')
            print('    fue el guard de pedidos pendientes (arreglado el 2026-08-05).')
        else:
            print('  No había ningún pedido anterior.')
            print('  → El pedido nació en ese momento: si el plan no es el que')
            print('    pulsó, el fallo está en el carrito, NO en el guard.')


def main():
    with A.app.app_context():
        arg = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
        if arg:
            u = (A.User.query.filter(
                (A.db.func.lower(A.User.username) == arg.lower())
                | (A.db.func.lower(A.User.email) == arg.lower())).first())
            if not u:
                print('No hay ninguna cuenta con "%s".' % arg)
                return 1
            cuenta(u)
            return 0
        ids = [o.user_id for o in (A.Order.query
                                   .order_by(A.Order.id.desc()).limit(40).all())]
        vistos = []
        for i in ids:
            if i not in vistos:
                vistos.append(i)
        if not vistos:
            print('No hay ningún pedido en la base.')
            return 0
        for i in vistos[:8]:
            u = A.db.session.get(A.User, i)
            if u:
                cuenta(u)
        return 0


if __name__ == '__main__':
    sys.exit(main())
