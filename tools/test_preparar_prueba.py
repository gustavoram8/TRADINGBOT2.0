# -*- coding: utf-8 -*-
"""La preparación del ensayo: que mire sin tocar, y que al aplicar CORTE.

Lo que de verdad se prueba aquí: que bajar el plan a Free **no se dé por
bueno sin haber cortado el permiso de cobro en PayPal**. Ese es el fallo que
dejaría a su hermano pagando cada mes una cuenta que el sitio muestra como
gratuita.
"""
import io
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = ('sqlite:///'
                              + os.path.join(tempfile.mkdtemp(), 'p.db'))
os.environ['PREVIEW_USERS'] = 'maurotradesve,gussytrades'
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

import app as A                    # noqa: E402
import preparar_prueba as P        # noqa: E402

ok = fallas = 0
CORTA = {'ok': True}


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


A._paypal_sub_cancel = lambda sub, motivo='': CORTA['ok']


def corre(*argv):
    sys.argv = ['preparar_prueba.py'] + list(argv)
    buf, real = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        rc = P.main()
    finally:
        sys.stdout = real
    return rc, buf.getvalue()


def siembra(nombre, plan='premium'):
    with A.app.app_context():
        u = A.User(username=nombre, email=nombre + '@demo.invalid', plan=plan,
                   email_verified=True)
        u.set_password('Zx9!wQ4mNp2r')
        A.db.session.add(u)
        A.db.session.commit()
        o = A.Order(user_id=u.id, plan='premium', billing_cycle='monthly',
                    base_price=50.0, final_price=50.0, status='pending')
        A.db.session.add(o)
        s = A.PlanSubscription(user_id=u.id, provider='paypal',
                               provider_ref='I-VIVA', plan='premium',
                               billing_cycle='monthly', price=50.0,
                               status='active')
        A.db.session.add(s)
        A.db.session.commit()
        return u.id


with A.app.app_context():
    A.db.create_all()
UID = siembra('gussytrades')

print('── mirar no toca nada ──')
rc, sal = corre('gussytrades')
check('rc=0', rc == 0, rc)
check('avisa del permiso de cobro vivo', 'permiso(s) de cobro VIVOS' in sal)
check('ve el pedido pendiente', 'pedido(s) pendientes' in sal)
check('confirma que puede entrar (preview)', 'puede entrar al sitio' in sal)
with A.app.app_context():
    u = A.db.session.get(A.User, UID)
    check('🔴 el plan NO se tocó', u.plan == 'premium', u.plan)
    check('la suscripción sigue activa',
          A.PlanSubscription.query.first().status == 'active')

print('── 🔴 si PayPal no corta, NO se miente ni se sigue ──')
CORTA['ok'] = False
rc, sal = corre('gussytrades', '--aplicar')
check('sale con error', rc == 1, rc)
check('lo dice claramente', 'NO se pudo cortar en PayPal' in sal)
check('🔴 se DETIENE en vez de seguir', 'ME DETENGO' in sal)
with A.app.app_context():
    u = A.db.session.get(A.User, UID)
    check('y la deja como activa (no la marca cancelada en falso)',
          A.PlanSubscription.query.first().status == 'active')
    check('🔴 el plan NO baja a Free con un cobro vivo detrás',
          u.plan == 'premium', u.plan)

print('── aplicar de verdad ──')
CORTA['ok'] = True
rc, sal = corre('gussytrades', '--aplicar')
check('rc=0', rc == 0, rc)
with A.app.app_context():
    u = A.db.session.get(A.User, UID)
    s = A.PlanSubscription.query.first()
    o = A.Order.query.filter_by(user_id=UID).first()
    pc = A.PromoCode.query.filter_by(code='PRUEBA90').first()
    check('🔴 la suscripción quedó cortada', s.status == 'cancelled', s.status)
    check('el pedido pendiente se soltó', o.status == 'cancelled', o.status)
    check('el plan quedó en free', u.plan == 'free', u.plan)
    check('sin fecha de vencimiento colgando', u.plan_expires_at is None)
    check('el cupón se creó general y de un solo uso',
          pc and pc.kind == 'discount' and pc.max_uses == 1 and pc.active)
    check('con el 90%', pc.discount_pct == 90, pc.discount_pct)
check('le dice los dos importes del carrito',
      'Primer mes $2.50' in sal and '$25.00/mes' in sal, sal[-400:])
check('y que cierre PayPal sin aprobar', 'CIERRA esa pantalla sin' in sal)

print('── correrlo dos veces no rompe nada ──')
rc, sal = corre('gussytrades', '--aplicar')
check('rc=0 e idempotente', rc == 0 and 'ya estaba en free' in sal)

print('── una cuenta que no existe ──')
rc, sal = corre('nadie')
check('lo dice y no revienta', rc == 1 and 'No existe' in sal)

print('── una cuenta fuera del candado de preview ──')
siembra('ajeno', plan='free')
rc, sal = corre('ajeno')
check('avisa de que ni vería el sitio', 'NO está en PREVIEW_USERS' in sal)
check('y da el arreglo exacto', 'set_env.py PREVIEW_USERS=' in sal)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
