# -*- coding: utf-8 -*-
"""¿Por qué esta cuenta ve (o no ve) la oferta de bienvenida?

    venv/bin/python3 tools/check_oferta.py                 # el estado general
    venv/bin/python3 tools/check_oferta.py maurotradesve gussytrades

Existe porque "el descuento no sale" tiene CINCO causas posibles y desde fuera
se parecen todas: que la variable no esté puesta, que el proceso no se haya
reiniciado, que el ciclo no sea mensual, que la cuenta ya haya pagado alguna
vez, o que de verdad haya un fallo. Adivinar cuál es cuesta media hora de ida
y vuelta; preguntárselo al servidor cuesta cinco segundos.

🔑 Lo importante que casi nadie tiene en la cabeza: **"tener el plan Free" NO
es lo mismo que "no haber pagado nunca"**. La oferta mira si la cuenta tiene
ALGÚN pedido pagado en su historia — una compra de prueba de hace meses, o un
plan que caducó, la dejan fuera para siempre. Por eso este informe enseña los
pedidos pagados que encuentra: es la respuesta, no una pista.

No escribe nada. Solo lee.
"""
from __future__ import print_function

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

try:
    import app as A
except Exception as e:                                    # pragma: no cover
    sys.exit('no se pudo cargar la app: %s' % e)


def money(v):
    return '$%.2f' % float(v or 0)


def main():
    cuentas = [a for a in sys.argv[1:] if not a.startswith('-')]

    print('\n══ 1 · la oferta, tal y como la ve el servidor ═════════════')
    pct = A.LAUNCH_DISCOUNT_PCT
    if pct <= 0:
        print('  ⛔ APAGADA (LAUNCH_DISCOUNT_PCT=%s)' % pct)
        print('     Se enciende con: python3 tools/set_env.py LAUNCH_DISCOUNT_PCT=30')
        print('     y luego: supervisorctl reread && supervisorctl update')
    else:
        print('  ✅ ENCENDIDA al %d%%' % pct)
        for p, v in sorted(A.PLAN_PRICING.items()):
            base = v.get('monthly')
            if base:
                print('     %-9s lista %s → primer mes %s'
                      % (p, money(base), money(round(base * (1 - pct / 100.0), 2))))
    print('  ciclos con oferta : %s' % ', '.join(A.LAUNCH_DISCOUNT_CYCLES))
    print('  ciclos a la venta : %s' % ', '.join(A.allowed_cycles()))
    if 'monthly' not in A.allowed_cycles():
        print('  🔴 el mensual no está a la venta: la oferta no puede aplicarse a nada')

    print('\n══ 2 · lo que ve un VISITANTE que no ha entrado ════════════')
    with A.app.test_request_context('/'):
        anon = A.launch_discount_for('monthly')
    print('  descuento: %d%%  %s' % (anon, '✅' if anon == pct else '🔴 NO coincide con el %d%%' % pct))
    if pct > 0 and anon == pct:
        print('  → las tarjetas de la landing salen rebajadas y con el precio viejo tachado')

    if not cuentas:
        print('\n(pásame nombres de usuario para revisarlos: '
              'tools/check_oferta.py maurotradesve gussytrades)\n')
        return 0

    print('\n══ 3 · cuenta por cuenta ═══════════════════════════════════')
    with A.app.app_context():
        for nombre in cuentas:
            u = (A.User.query.filter_by(username=nombre).first()
                 or A.User.query.filter_by(email=nombre).first())
            print('\n  ── %s ──' % nombre)
            if u is None:
                print('     🔴 no existe ninguna cuenta con ese nombre ni ese correo')
                continue
            pagados = (A.Order.query
                       .filter(A.Order.user_id == u.id, A.Order.status == 'paid')
                       .order_by(A.Order.id.desc()).all())
            print('     plan de HOY : %s%s' % (u.plan, ' (admin)' if u.is_admin else ''))
            print('     ha pagado   : %s' % ('SÍ, %d pedido(s)' % len(pagados)
                                             if pagados else 'nunca'))
            for o in pagados[:5]:
                print('        · pedido #%d  %s/%s  %s  %s'
                      % (o.id, o.plan, o.billing_cycle, money(o.final_price),
                         o.paid_at.strftime('%Y-%m-%d') if o.paid_at else 'sin fecha'))
            if len(pagados) > 5:
                print('        · … y %d más' % (len(pagados) - 5))

            visto = A.launch_discount_for('monthly', user=u)
            if visto > 0:
                print('     👉 VE la oferta: %d%% en su primer mes' % visto)
            else:
                por = ('la oferta está apagada' if pct <= 0
                       else 'ya tiene un pedido PAGADO en su historial')
                print('     👉 NO ve la oferta — %s' % por)
                if pct > 0 and pagados:
                    print('        ⚠️ Tener el plan Free HOY no cuenta: la oferta mira')
                    print('           si la cuenta pagó ALGUNA VEZ, y ésta pagó.')
                    print('           Para probar como un cliente real hace falta una')
                    print('           cuenta nueva, o borrar esos pedidos de prueba.')
            for plan in ('standard', 'premium'):
                q = A._quote_para(u, plan) if hasattr(A, '_quote_para') else None
                if q is None:
                    base = A.PLAN_PRICING[plan]['monthly']
                    final = round(base * (1 - visto / 100.0), 2)
                    q = {'base_price': base, 'final_price': final}
                print('     %-9s le cobraría %s (lista %s)'
                      % (plan, money(q['final_price']), money(q['base_price'])))
    print('')
    return 0


if __name__ == '__main__':
    sys.exit(main())
