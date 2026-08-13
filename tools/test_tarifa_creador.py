# -*- coding: utf-8 -*-
"""La tarifa del cliente de un socio no puede quedarse en la de LANZAMIENTO.

    venv/bin/python3 tools/test_tarifa_creador.py

Salió de una pregunta del dueño ("¿cómo diferencia PayPal que el descuento de
creador SÍ es perpetuo?") mientras la oferta pública del 30% estaba encendida.

🔴 El fallo: `_tramos` calculaba la "tarifa permanente" del cliente atado con
`_quote()`, que aplica `max(oferta_de_lanzamiento, código)`. Con la oferta al
30% y un socio al 20%, la renovación quedaba en $35 en vez de $40 — el gancho
temporal convertido en precio perpetuo, y contra la cláusula 3.1 del acuerdo
("terminado ese período, su tarifa de creador vuelve a aplicarse sola").
Coste: $5/mes por cliente, para siempre, por cada cliente de socio captado
durante la ventana de lanzamiento.

Lo que se prueba, con la oferta ENCENDIDA y APAGADA:
  · el primer mes siempre cobra el MEJOR precio de los dos (no se acumulan);
  · la renovación de un cliente atado es SIEMPRE su tarifa de creador;
  · un cliente sin socio vuelve a precio de lista;
  · un código de creador usado directamente es perpetuo en los dos tramos;
  · dos creadores distintos con % distintos no se contaminan entre sí.
"""
from __future__ import print_function

import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'tc.db')
os.environ.setdefault('SECRET_KEY', 'tarifa')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                           # noqa: E402

OK = FALLOS = 0


def check(cond, texto):
    global OK, FALLOS
    print(('  ✅ ' if cond else '  ❌ ') + texto)
    if cond:
        OK += 1
    else:
        FALLOS += 1


def main():
    global OK, FALLOS
    with A.app.app_context():
        A.db.create_all()
        for n, cod in (('de_gabriel', 'GABRIEL20'), ('de_lucia', 'LUCIA25'),
                       ('sin_socio', None)):
            u = A.User(username=n, email=n + '@d.invalid', email_verified=True)
            u.set_password('Zx9!wQ4mNp2r'); u.email_canonical = u.email
            u.plan = 'free'; u.referred_by_code = cod
            A.db.session.add(u)
        A.db.session.add(A.PromoCode(code='GABRIEL20', discount_pct=20,
                                     creator_name='Gabriel', kind='creator',
                                     valid_for='monthly'))
        A.db.session.add(A.PromoCode(code='LUCIA25', discount_pct=25,
                                     creator_name='Lucia', kind='creator',
                                     valid_for='monthly'))
        A.db.session.add(A.PromoCode(code='VERANO30', discount_pct=30,
                                     kind='discount', valid_for='monthly'))
        A.db.session.commit()

        def tramos(usuario, code):
            u = (A.User.query.filter_by(username=usuario).first()
                 if usuario else None)
            pc = (A.PromoCode.query.filter(
                A.db.func.lower(A.PromoCode.code) == code.lower()).first()
                if code else None)
            q = A._quote('premium', 'monthly', pc)
            return A._tramos(u, 'premium', 'monthly', code, q['final_price'])

        for pct in (30, 0):
            A.LAUNCH_DISCOUNT_PCT = pct
            estado = 'ENCENDIDA al 30%%' if pct else 'APAGADA'
            print('\n══ oferta de lanzamiento %s ══' % estado)

            pr, re_ = tramos('de_gabriel', 'VERANO30')
            check(re_ == 40.0,
                  'cliente de Gabriel usa VERANO30 → renueva a SU tarifa '
                  '$40 (sale $%.2f)' % re_)
            check(pr == (35.0 if pct else 35.0),
                  'y el primer mes cobra el mejor precio: $%.2f' % pr)

            pr, re_ = tramos('de_lucia', 'VERANO30')
            check(re_ == 37.5,
                  'la de Lucía es del 25%% → su cliente renueva a $37.50 '
                  '(sale $%.2f) — no se contaminan entre socios' % re_)

            pr, re_ = tramos('de_gabriel', 'GABRIEL20')
            # El primer mes cobra el MEJOR de los dos descuentos (con la oferta
            # al 30% gana la oferta: $35); la renovación vuelve SIEMPRE a la
            # tarifa del socio, que es lo perpetuo.
            check(pr == (35.0 if pct else 40.0) and re_ == 40.0,
                  'con SU propio código: primer mes el mejor precio, '
                  'renovación su tarifa $40 (sale %.2f/%.2f)' % (pr, re_))

            pr, re_ = tramos('sin_socio', 'VERANO30')
            check(re_ == 50.0,
                  'sin socio detrás → la renovación vuelve a lista $50 '
                  '(sale $%.2f)' % re_)

            pr, re_ = tramos('sin_socio', '')
            esperado = 35.0 if pct else 50.0
            check(pr == esperado,
                  'sin código: primer mes $%.2f%s' % (
                      pr, ' (la oferta pública)' if pct else ''))
            check(re_ == 50.0, 'y renueva a lista $%.2f' % re_)

        A.LAUNCH_DISCOUNT_PCT = 30
        print('\n══ el candado de siempre: nada se acumula ══')
        pr, re_ = tramos('de_gabriel', 'GABRIEL20')
        check(pr == 35.0,
              'oferta 30%% + código 20%% NO dan 50%% ($25): se cobra el mejor '
              'de los dos por separado ($%.2f)' % pr)
        check(re_ == 40.0,
              'y el gancho NO se queda: la renovación es la tarifa del socio '
              '($%.2f), no el $35 de lanzamiento' % re_)

    print('\nRESULTADO: %d/%d' % (OK, OK + FALLOS))
    return 0 if FALLOS == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
