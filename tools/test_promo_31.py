# -*- coding: utf-8 -*-
"""Cláusula 3.1/3.2 del acuerdo de socios, ejecutada de verdad.

La promesa del papel: un cliente atado a un creador puede acogerse a una
promoción GENERAL mejor (nunca a un código de otro creador), y hacerlo NO le
quita el cliente al socio — la comisión sigue fluyendo, calculada sobre lo que
el cliente pagó de verdad. Antes de este cableado el código atado ganaba
siempre: el cliente quedaba atrapado en el peor precio y el 3.1 era mentira.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scalpel'))
os.environ.setdefault('PAYPAL_CLIENT_ID', 'x')
os.environ.setdefault('PAYPAL_SECRET', 'y')
os.environ.setdefault('PAYPAL_ENV', 'sandbox')

import app as A  # noqa: E402

ok = fallos = 0


def check(cond, txt):
    global ok, fallos
    if cond:
        ok += 1
        print('  ok  ', txt)
    else:
        fallos += 1
        print('  FALLA', txt)


def entrar(c, u):
    c.post('/login', data={'identifier': u, 'password': 'Zx8!kQ2mLp7w'},
           follow_redirects=True)


def valida(c, code, plan='premium', cycle='monthly'):
    r = c.post('/api/checkout/validate-code',
               json={'plan': plan, 'cycle': cycle, 'code': code})
    return r.get_json()


def paga(uid, code=None, precio_final=None):
    """Crea y paga un pedido por dentro (el circuito PayPal ya tiene su E2E)."""
    from datetime import datetime, timezone
    with A.app.app_context():
        o = A.Order(user_id=uid, plan='premium', billing_cycle='monthly',
                    base_price=50.0, discount_pct=0, final_price=precio_final or 50.0,
                    promo_code=code, status='paid', payment_method='manual',
                    paid_at=datetime.now(timezone.utc))
        A.db.session.add(o)
        A.db.session.commit()
        A._activate_plan_from_order(o)
        return o.id


def main():
    with A.app.app_context():
        A.db.create_all()
        # limpiar restos de corridas anteriores
        for code in ('SOCIO20', 'RIVAL25', 'VERANO50', 'FLOJO10'):
            pc = A.PromoCode.query.filter(A.db.func.lower(A.PromoCode.code) == code.lower()).first()
            if pc:
                A.db.session.delete(pc)
        u = A.User.query.filter_by(username='cli31').first()
        if u:
            # las filas hijas primero: borrar el User hace que SQLAlchemy anule
            # sus FKs y known_device.user_id es NOT NULL
            A.KnownDevice.query.filter_by(user_id=u.id).delete()
            A.SaleBreakdown.query.filter_by(user_id=u.id).delete()
            A.Order.query.filter_by(user_id=u.id).delete()
            A.db.session.delete(u)
        A.db.session.commit()

        u = A.User(username='cli31', email='cli31@ej.com')
        u.set_password('Zx8!kQ2mLp7w')
        for campo in ('email_verified', 'is_verified', 'verified'):
            if hasattr(u, campo):
                setattr(u, campo, True)
        A.db.session.add(u)
        A.db.session.add_all([
            A.PromoCode(code='SOCIO20', discount_pct=20, kind='creator',
                        creator_name='El Socio', valid_for='monthly'),
            A.PromoCode(code='RIVAL25', discount_pct=25, kind='creator',
                        creator_name='Otro Creador', valid_for='monthly'),
            A.PromoCode(code='VERANO50', discount_pct=50, kind='discount',
                        valid_for='monthly'),
            A.PromoCode(code='FLOJO10', discount_pct=10, kind='discount',
                        valid_for='monthly'),
        ])
        A.db.session.commit()
        uid = u.id

    # ── 1 · primera compra con el código del socio: ata ────────────────────
    paga(uid, 'SOCIO20', 40.0)
    with A.app.app_context():
        u = A.db.session.get(A.User, uid)
        check(u.referred_by_code == 'SOCIO20', 'primer pago con SOCIO20 ata la cuenta')

    # ── 2 · la casilla, con la cuenta atada ────────────────────────────────
    with A.app.test_client() as c:
        entrar(c, 'cli31')
        d = valida(c, 'VERANO50')
        check(d.get('ok') and d.get('final_price') == 25.0,
              'promo GENERAL mejor (50%%): entra, $%.2f' % d.get('final_price', -1))
        d = valida(c, 'FLOJO10')
        check(not d.get('ok') and d.get('error') == 'worse',
              'promo general PEOR (10%): rechazada con "worse"')
        d = valida(c, 'RIVAL25')
        check(not d.get('ok') and d.get('error') == 'locked',
              'código de OTRO creador: bloqueado aunque sea mejor (3.2)')
        d = valida(c, 'SOCIO20')
        check(d.get('ok') and d.get('locked'),
              'su propio código: ok informativo, nada cambia')

        # ── 3 · compra de renovación acogiéndose al 50% ────────────────────
        r = c.post('/checkout/create',
                   data={'plan': 'premium', 'cycle': 'monthly',
                         'promo_code': 'VERANO50', 'method': 'manual'},
                   follow_redirects=False)
        check(r.status_code == 200, 'checkout con VERANO50 responde')

    with A.app.app_context():
        o = A.Order.query.filter_by(user_id=uid, status='pending').first()
        check(o is not None and o.promo_code == 'VERANO50' and o.final_price == 25.0,
              'el pedido lleva VERANO50 y cuesta $25 (%s $%s)'
              % (o and o.promo_code, o and o.final_price))
        u = A.db.session.get(A.User, uid)
        check(u.referred_by_code == 'SOCIO20',
              'la ATRIBUCIÓN no se movió: sigue siendo cliente del socio')
        v = A.PromoCode.query.filter_by(code='VERANO50').first()
        s = A.PromoCode.query.filter_by(code='SOCIO20').first()
        check((v.uses_count or 0) == 1, 'VERANO50 consumió su uso')
        check((s.uses_count or 0) == 0, 'SOCIO20 no sumó uso por la renovación')

        # pagar ese pedido y mirar el libro: la comisión debe ir al socio
        from datetime import datetime, timezone
        o.status = 'paid'
        o.paid_at = datetime.now(timezone.utc)
        A.db.session.commit()
        A._activate_plan_from_order(o)
        fila = A.SaleBreakdown.query.filter_by(order_id=o.id).first()
        check(fila is not None, 'la venta entró al libro')
        check(fila and fila.partner == 'El Socio',
              'comisión atribuida al SOCIO aunque el pedido llevó cupón general (%s)'
              % (fila and fila.partner))
        esperado = round(25.0 * A.partner_tier_pct(fila.position) / 100.0, 2) if fila else 0
        check(fila and abs(fila.commission_amt - esperado) < 0.01,
              'comisión sobre lo PAGADO de verdad: $%.2f (%s%% de $25)'
              % (fila.commission_amt if fila else -1, A.partner_tier_pct(fila.position) if fila else 0))

        # ── 4 · la renovación de siempre, sin teclear nada ─────────────────
        A.SaleBreakdown.query.filter_by(user_id=uid).delete()
        A.Order.query.filter_by(user_id=uid).delete()
        # el plan tiene que estar VENCIDO: /checkout bloquea comprar el plan
        # que ya se tiene (con premium activo redirige a /pricing)
        A.db.session.get(A.User, uid).plan = 'free'
        A.db.session.commit()

    with A.app.test_client() as c:
        entrar(c, 'cli31')
        # ya sin pedidos; sigue atada — probar que sin código el precio vuelve
        # al permanente del socio (auto-aplicado)
        r = c.get('/checkout?plan=premium&cycle=monthly')
        cuerpo = r.get_data(as_text=True)
        check('40.00' in cuerpo and 'SOCIO20' in cuerpo,
              'sin teclear nada, la renovación vuelve a su $40 permanente')
        check('promo-input' in cuerpo,
              'la casilla de código SIGUE visible en la cuenta atada (3.1)')

    print('\n%d/%d' % (ok, ok + fallos))
    return 1 if fallos else 0


sys.exit(main())
