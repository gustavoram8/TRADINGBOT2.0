# -*- coding: utf-8 -*-
"""El verificador de una suscripción concreta, con un PayPal de mentira.

Prueba lo que de verdad importa: que CACE el caso en el que PayPal tiene
anotado un importe distinto del que el sitio le prometió al cliente. Ese
descuadre es el que acaba en una queja o en una disputa, y es invisible desde
la web — solo se ve preguntándole a PayPal.
"""
import io
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

BD = os.path.join(tempfile.mkdtemp(), 'prueba.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + BD
os.environ.update({'PAYPAL_CLIENT_ID': 'x', 'PAYPAL_SECRET': 'y',
                   'PAYPAL_ENV': 'live'})

sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
import app as A                      # noqa: E402
import check_subs as CS              # noqa: E402
import check_suscripcion as CX       # noqa: E402

ok = fallas = 0


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def ciclo(tenure, importe, total, unidad='MONTH', cuenta=1):
    return {'tenure_type': tenure, 'total_cycles': total,
            'frequency': {'interval_unit': unidad, 'interval_count': cuenta},
            'pricing_scheme': {'fixed_price': {'value': str(importe),
                                               'currency_code': 'USD'}}}


with A.app.app_context():
    A.db.create_all()
    u = A.User(username='hermano', email='h@demo.invalid', plan='premium',
               email_verified=True)
    u.set_password('Zx9!wQ4mNp2r')
    A.db.session.add(u)
    A.db.session.commit()
    o = A.Order(user_id=u.id, plan='premium', billing_cycle='monthly',
                base_price=50.0, final_price=5.0, promo_code='PRUEBA90',
                status='paid')
    A.db.session.add(o)
    A.db.session.commit()
    s = A.PlanSubscription(user_id=u.id, provider='paypal',
                           provider_ref='I-TEST', plan='premium',
                           billing_cycle='monthly', price=50.0,
                           promo_code='PRUEBA90', status='active',
                           first_order_id=o.id)
    A.db.session.add(s)
    A.db.session.commit()

CS.token = lambda base, cid, secret: ('tok', None)
RESP = {}


def api(base, tk, path):
    return 200, RESP


CS.api = api


def corre():
    CX.ok = CX.avisos = CX.fallos = 0
    buf, real = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        rc = CX.main()
    finally:
        sys.stdout = real
    return rc, buf.getvalue()


print('── el caso bueno: PayPal coincide con lo prometido ──')
RESP = {'status': 'ACTIVE',
        'billing_info': {'next_billing_time': '2026-09-08T10:00:00Z'},
        'plan': {'billing_cycles': [ciclo('TRIAL', 5.0, 1),
                                    ciclo('REGULAR', 50.0, 0)]}}
rc, sal = corre()
check('veredicto verde', rc == 0, rc)
check('confirma el 1er mes ($5, lo del carrito)', '1er mes: PayPal cobrará $5.0' in sal)
check('confirma la renovación ($50, lo de Ajustes)',
      'renovación: PayPal cobrará $50.0' in sal)
check('enseña la fecha del próximo cobro', '2026-09-08' in sal)

print('── 🔴 PayPal renovaría a un importe distinto del anunciado ──')
RESP = {'status': 'ACTIVE', 'billing_info': {},
        'plan': {'billing_cycles': [ciclo('TRIAL', 5.0, 1),
                                    ciclo('REGULAR', 60.0, 0)]}}
rc, sal = corre()
check('lo marca como GRAVE', rc == 1, rc)
check('dice los dos importes', '$50.0' in sal and '$60.0' in sal)
check('avisa de que ahí es donde nace una disputa', 'disputa' in sal)

print('── 🔴 el descuento se quedó pegado como precio de por vida ──')
RESP = {'status': 'ACTIVE', 'billing_info': {},
        'plan': {'billing_cycles': [ciclo('REGULAR', 5.0, 0)]}}
rc, sal = corre()
check('lo marca como GRAVE', rc == 1, rc)
check('lo explica en cristiano', 'TODOS los meses' in sal)

print('── el tramo del 1er mes se repetiría ──')
RESP = {'status': 'ACTIVE', 'billing_info': {},
        'plan': {'billing_cycles': [ciclo('TRIAL', 5.0, 3),
                                    ciclo('REGULAR', 50.0, 0)]}}
rc, sal = corre()
check('lo caza', rc == 1 and 'no 1: el descuento se repetiría' in sal)

print('── sin aprobar todavía (lo que se puede probar GRATIS) ──')
RESP = {'status': 'APPROVAL_PENDING', 'billing_info': {},
        'plan': {'billing_cycles': [ciclo('TRIAL', 5.0, 1),
                                    ciclo('REGULAR', 50.0, 0)]}}
rc, sal = corre()
check('🔴 se puede verificar SIN que nadie pague', rc == 0, rc)
check('lo dice explícitamente', 'no se ha cobrado nada' in sal)

print('── una suscripción de otro entorno ──')
CS.api = lambda base, tk, path: (404, {})
rc, sal = corre()
check('lo marca como GRAVE y sugiere el motivo',
      rc == 1 and 'sandbox vs live' in sal)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
