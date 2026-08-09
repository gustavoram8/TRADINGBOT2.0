# -*- coding: utf-8 -*-
"""Ida y vuelta: ¿puede un cliente atado saltar a una promo general y volver?

El ciclo exacto que preguntó el dueño (2026-08-09):
  compra con código de creador → baja → deja vencer → recompra con una promo
  general del 35% → disfruta ese mes → baja otra vez → vuelve a comprar con
  el código del creador.

Lo que tiene que ser verdad:
  · el ciclo NO está prohibido (cada compra es una compra legítima);
  · pero la promo general es de UN USO POR CUENTA, así que el salto solo
    ocurre una vez: al tercer intento ya no hay 35% al que volver;
  · la atribución sobrevive a todo el recorrido y el socio cobra SIEMPRE,
    incluso en el mes que el cliente pagó con la promo general;
  · volver al código del creador no es "volver": nunca dejó de estar atado,
    su tarifa se auto-aplica sin teclear nada.

El coste del baile para el cliente: pierde la continuidad (tiene que esperar
a que su mes venza, sin acumular nada) para ganar UN mes más barato, UNA vez.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

os.environ.setdefault('DATABASE_URL', 'sqlite://')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
from flask import g            # noqa: E402
import app as A                # noqa: E402

CL = 'Zx9!wQ4mNp2r'
ok = fallas = 0


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def sesion(nombre):
    c = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    c.post('/login', data={'identifier': nombre, 'password': CL})
    c.set_cookie('scalpel_splash_ts', '1')
    return c


def compra(cli, codigo=None):
    """Compra premium mensual y la da por pagada. Devuelve (precio, código)."""
    d = {'plan': 'premium', 'cycle': 'monthly', 'method': 'manual'}
    if codigo:
        d['promo_code'] = codigo
    cli.post('/checkout/create', data=d)
    with A.app.app_context():
        o = (A.Order.query.filter_by(user_id=UID, status='pending')
             .order_by(A.Order.id.desc()).first())
        if o is None:
            return None, None
        o.status = 'paid'
        o.paid_at = datetime.now(timezone.utc)
        A.db.session.commit()
        A._activate_plan_from_order(o)
        return o.final_price, o.promo_code


def caduca(cli):
    """Baja + el mes se acaba: la cuenta vuelve a free."""
    cli.post('/account/cancel-plan')
    with A.app.app_context():
        u = A.db.session.get(A.User, UID)
        u.plan_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        A.db.session.commit()
    cli.get('/app')                      # _expire_plan corre en la visita


with A.app.app_context():
    A.db.create_all()
    u = A.User(username='saltarin', email='s@demo.invalid', plan='free',
               email_verified=True)
    u.set_password(CL)
    A.db.session.add(u)
    A.db.session.add(A.PromoCode(code='GABRIEL', discount_pct=20,
                                 kind='creator', creator_name='Gabriel'))
    A.db.session.add(A.PromoCode(code='VERANO35', discount_pct=35,
                                 kind='discount', max_uses=500))
    A.db.session.commit()
    UID = u.id

c = sesion('saltarin')

print('── mes 1: llega por el código de Gabriel ──')
precio, cod = compra(c, 'GABRIEL')
check('paga $40 con el código del socio', precio == 40.0 and cod == 'GABRIEL',
      (precio, cod))
with A.app.app_context():
    check('queda atado a Gabriel',
          A.db.session.get(A.User, UID).referred_by_code == 'GABRIEL')

print('── se da de baja, deja vencer, y vuelve con la promo general del 35% ──')
caduca(c)
precio, cod = compra(c, 'VERANO35')
check('🔴 SÍ puede: paga $32.50 con la promo general',
      abs(precio - 32.5) < 0.01 and cod == 'VERANO35', (precio, cod))
with A.app.app_context():
    u = A.db.session.get(A.User, UID)
    check('...pero la atribución NO se movió: sigue siendo de Gabriel',
          u.referred_by_code == 'GABRIEL')
    fila = (A.SaleBreakdown.query.filter_by(user_id=UID)
            .order_by(A.SaleBreakdown.id.desc()).first())
    # ⚠️ `gross` es el precio de LISTA ($50); la comisión se calcula sobre
    # `net`, que es lo que el cliente pagó de verdad ($32.50).
    esperada = round(32.5 * A.partner_tier_pct(fila.position) / 100.0, 2)
    check('🔴 y Gabriel COBRA su comisión también en ese mes, sobre los '
          '$32.50 PAGADOS (no sobre los $50 de lista)',
          fila is not None and fila.partner == 'Gabriel'
          and abs(fila.net_paid - 32.5) < 0.01
          and abs(fila.commission_amt - esperada) < 0.01,
          (fila and fila.net_paid, fila and fila.commission_amt, esperada))

print('── se da de baja otra vez y vuelve "al código de Gabriel" ──')
caduca(c)
precio, cod = compra(c)          # sin teclear nada: su código se auto-aplica
check('vuelve a $40 sin escribir el código (se aplica solo)',
      precio == 40.0 and cod == 'GABRIEL', (precio, cod))

print('── y si intenta el salto UNA SEGUNDA VEZ ──')
caduca(c)
r = c.post('/api/checkout/validate-code',
           json={'code': 'VERANO35', 'plan': 'premium', 'cycle': 'monthly'})
d = r.get_json() or {}
check('🔴 la promo general ya está gastada para esta cuenta',
      not d.get('ok') and d.get('error') == 'already_used', d)
precio, cod = compra(c, 'VERANO35')
check('...y forzando el formulario cobra su $40 de socio, no $32.50',
      precio == 40.0 and cod == 'GABRIEL', (precio, cod))

print('── recuento: cuánto ganó Gabriel en todo el recorrido ──')
with A.app.app_context():
    filas = A.SaleBreakdown.query.filter_by(user_id=UID).all()
    check('las %d ventas del recorrido son TODAS de Gabriel' % len(filas),
          filas and all(f.partner == 'Gabriel' for f in filas),
          [f.partner for f in filas])
    check('y cuenta como UN solo cliente suyo, no como cuatro',
          A.partner_active_customers('Gabriel') == 1,
          A.partner_active_customers('Gabriel'))

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
