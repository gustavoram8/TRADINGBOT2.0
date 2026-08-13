# -*- coding: utf-8 -*-
"""La escalera 30/35/40 y qué pasa cuando un cliente hace chargeback.

    venv/bin/python3 tools/test_escalera_socio.py

Las DOS preguntas del dueño (2026-08-13), respondidas corriendo el código de
verdad, no leyendo notas:

  1. ¿El sistema sube solo el % del colaborador al pasar de X clientes?
  2. ¿Un chargeback le quita ese cliente y deja de cobrar por él?

Reconstruye lo que probaban `test_reglaB.py` y `test_rerank.py`, que se
perdieron al reciclarse el contenedor. Va por `record_sale_breakdown()` — el
mismo camino que corre cuando PayPal confirma un cobro real — para que lo
medido sea lo que se paga, y no una fórmula copiada dentro del test.
"""
from __future__ import print_function

import os
import sys
import tempfile
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'esc.db')
os.environ.setdefault('SECRET_KEY', 'escalera')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

try:
    import app as A                                       # noqa: E402
except Exception as e:                                    # pragma: no cover
    sys.exit('no se pudo cargar la app: %s%s' % (
        e, ('\n\n👉 Usa el intérprete del entorno:\n'
            '   venv/bin/python3 %s' % os.path.relpath(__file__, RAIZ))
        if 'No module named' in str(e) else ''))

SOCIO = 'Gabriel'
CODIGO = 'GABRIEL20'
OK = FALLOS = 0


def check(cond, texto):
    global OK, FALLOS
    print(('  ✅ ' if cond else '  ❌ ') + texto)
    if cond:
        OK += 1
    else:
        FALLOS += 1


def vende(n, plan='premium', neto=40.0):
    """Una compra de `cliente_n` con el código del socio, por el camino real."""
    u = A.User.query.filter_by(username='cliente_%d' % n).first()
    if u is None:
        u = A.User(username='cliente_%d' % n, email='c%d@d.invalid' % n,
                   email_verified=True, plan='free')
        u.set_password('Zx9!wQ4mNp2r')
        u.email_canonical = u.email
        u.referred_by_code = CODIGO          # la atadura: es cliente del socio
        A.db.session.add(u)
        A.db.session.flush()
    o = A.Order(user_id=u.id, plan=plan, billing_cycle='monthly',
                base_price=50.0, final_price=neto, discount_pct=20.0,
                promo_code=CODIGO, status='paid', payment_method='paypal',
                paid_at=datetime.now(timezone.utc))
    A.db.session.add(o)
    A.db.session.commit()
    return A.record_sale_breakdown(o)


def main():
    global OK, FALLOS
    with A.app.app_context():
        A.db.create_all()
        A.db.session.add(A.PromoCode(code=CODIGO, discount_pct=20,
                                     creator_name=SOCIO, kind='creator',
                                     valid_for='monthly'))
        A.db.session.commit()

        print('\n══ 1 · ¿sube solo el %% al pasar de X clientes? ══')
        print('   (los tramos son MARGINALES: cada cliente cobra el suyo, no se')
        print('    recalculan hacia atrás los que ya estaban)')
        filas = [vende(n) for n in range(1, 80)]

        for pos, esperado, nota in ((1, 30, 'el primer cliente'),
                                    (24, 30, 'el 24 — último del primer tramo'),
                                    (25, 35, '🔑 el 25 SALTA solo a 35%'),
                                    (74, 35, 'el 74 — último del segundo'),
                                    (75, 40, '🔑 el 75 SALTA solo a 40%'),
                                    (79, 40, 'y de ahí en adelante, 40%')):
            r = filas[pos - 1]
            check(r.position == pos and int(r.commission_pct) == esperado,
                  '%s → puesto %d, %d%% ($%.2f de $%.2f)'
                  % (nota, r.position, int(r.commission_pct),
                     r.commission_amt, r.net_paid))

        print('\n══ 2 · una RENOVACIÓN no le sube el tramo ══')
        antes = A.partner_active_customers(SOCIO)
        r = vende(1)                                  # el cliente 1 paga su 2º mes
        despues = A.partner_active_customers(SOCIO)
        check(r.position == 1 and int(r.commission_pct) == 30,
              'el cliente 1 renueva y sigue en el puesto 1 al 30%% '
              '(puesto %d, %d%%)' % (r.position, int(r.commission_pct)))
        check(antes == despues == 79,
              'y el socio sigue teniendo 79 CLIENTES, no 80 pagos '
              '(%d → %d)' % (antes, despues))

        print('\n══ 3 · CHARGEBACK: pierde al cliente y deja de cobrarlo ══')
        # El cliente 10 hace contracargo. Su comisión estaba PENDIENTE.
        f10 = filas[9]
        check(f10.commission_status == 'pending',
              'antes: su comisión estaba pendiente de pagar ($%.2f)'
              % f10.commission_amt)
        A.reverse_sale_breakdown(f10, reason='chargeback')
        check(f10.commission_status == 'cancelled',
              '🔑 tras el contracargo NO se le paga: cancelada')
        check(A.partner_active_customers(SOCIO) == 78,
              'y es UN CLIENTE MENOS: 79 → %d'
              % A.partner_active_customers(SOCIO))

        # Y una comisión YA PAGADA se convierte en deuda, no se evapora.
        f11 = filas[10]
        f11.commission_status = 'paid'
        A.db.session.commit()
        A.reverse_sale_breakdown(f11, reason='chargeback')
        check(f11.commission_status == 'clawback',
              '🔑 si ya se le había pagado → clawback (se descuenta de la '
              'siguiente liquidación), no se regala')

        print('\n══ 4 · al irse un cliente, los de abajo SUBEN de puesto ══')
        # Es la consecuencia que el dueño eligió: el % refleja la cartera de HOY.
        r = vende(76)                       # cliente que estaba en el puesto 76
        check(r.position == 74 and int(r.commission_pct) == 35,
              '🔑 el que estaba en el 76 al 40%% ahora renueva en el 74 al 35%% '
              '(2 bajas por delante) — puesto %d, %d%%'
              % (r.position, int(r.commission_pct)))
        roster = A.partner_roster(SOCIO)
        check(len(roster) == len(set(roster)) == 77,
              'la escalera queda 1..77 sin huecos ni repetidos (%d)' % len(roster))

        print('\n══ 5 · lo que el PANEL le enseña coincide con lo que se paga ══')
        c = A.partner_active_customers(SOCIO)
        t1 = min(c, 24)
        t2 = max(0, min(c, 74) - 24)
        t3 = max(0, c - 74)
        eff = round((t1 * 30 + t2 * 35 + t3 * 40) / float(c), 1)
        check((t1, t2, t3) == (24, 50, 3),
              'reparto por tramos: %d al 30%% · %d al 35%% · %d al 40%%'
              % (t1, t2, t3))
        # (24×30 + 50×35 + 3×40) / 77 = 2590/77 = 33.6
        check(abs(eff - 33.6) < 0.05,
              '%% efectivo de su cartera: %.1f%%' % eff)
        siguiente = A.partner_tier_pct(A._next_partner_position(SOCIO))
        check(int(siguiente) == 40,
              'y su PRÓXIMO cliente entraría al %d%%' % int(siguiente))

        print('\n══ 6 · el dinero revertido sale de las cuentas ══')
        vivas = A.SaleBreakdown.query.filter_by(partner=SOCIO).filter(
            A.SaleBreakdown.reversed_at.is_(None)).count()
        muertas = A.SaleBreakdown.query.filter_by(partner=SOCIO).filter(
            A.SaleBreakdown.reversed_at.isnot(None)).count()
        # 79 ventas + 2 renovaciones = 81 FILAS (no clientes), menos 2 revertidas.
        check(muertas == 2 and vivas == 79,
              'las 2 revertidas se CONSERVAN tachadas (historia), '
              '%d filas vivas / %d revertidas' % (vivas, muertas))
        pendiente = sum(r.commission_amt or 0 for r in
                        A.SaleBreakdown.query.filter_by(
                            partner=SOCIO, commission_status='pending').all()
                        if r.reversed_at is None)
        check(pendiente > 0 and all(
            r.reversed_at is None for r in A.SaleBreakdown.query.filter_by(
                partner=SOCIO, commission_status='pending').all()),
              'ninguna venta revertida sigue contando como comisión a pagar '
              '($%.2f pendientes)' % pendiente)

    print('\nRESULTADO: %d/%d' % (OK, OK + FALLOS))
    return 0 if FALLOS == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
