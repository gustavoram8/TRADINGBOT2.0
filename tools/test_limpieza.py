# -*- coding: utf-8 -*-
"""La herramienta de limpieza: que borre lo que se le pide y NADA mas, y que
sin confirmacion no toque nada."""
import os, subprocess, sys, tempfile

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('   %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

DB = os.path.join(tempfile.mkdtemp(), 'l.db')
env = dict(os.environ, DATABASE_URL='sqlite:///' + DB)
sys.path.insert(0, '/home/user/TRADINGBOT2.0/scalpel')
os.environ['DATABASE_URL'] = 'sqlite:///' + DB
import app as A

with A.app.app_context():
    A.db.create_all()
    u = A.User(username='ana', email='a@demo.invalid', plan='premium', email_verified=True)
    u.set_password('Xk9!mQ2#pL5v'); A.db.session.add(u); A.db.session.commit()
    for i in range(3):
        o = A.Order(user_id=u.id, plan='premium', billing_cycle='monthly', base_price=50.0,
                    final_price=50.0, status='paid', payment_method='paypal')
        A.db.session.add(o); A.db.session.commit()
        A.db.session.add(A.SaleBreakdown(order_id=o.id, user_id=u.id, username='ana',
                                         plan='premium', billing_cycle='monthly', gross=50.0,
                                         net_paid=50.0, is_manual=False))
    A.db.session.commit()

def correr(args, entrada=''):
    return subprocess.run([sys.executable, '/home/user/TRADINGBOT2.0/tools/limpiar_pruebas.py'] + args,
                          input=entrada, capture_output=True, text=True, env=env, timeout=120)

def cuantas():
    with A.app.app_context():
        return A.SaleBreakdown.query.count(), A.Order.query.count()

print('── Sin argumentos solo mira')
r = correr([])
check('lista las tres ventas', r.stdout.count('pedido #') == 3, r.stdout.count('pedido #'))
check('y no borra nada', cuantas() == (3, 3), cuantas())

print('\n── Borrar sin confirmar no hace nada')
r = correr(['--borrar', '1,2'], entrada='no\n')
check('cancela', 'Cancelado' in r.stdout)
check('todo intacto', cuantas() == (3, 3), cuantas())

print('\n── Borrar dos, confirmando')
r = correr(['--borrar', '1,2'], entrada='SI\n')
check('borra exactamente dos', cuantas() == (1, 3), cuantas())
with A.app.app_context():
    check('y deja la tercera', A.SaleBreakdown.query.first().id == 3)

print('\n── Vaciar todo pide la palabra exacta')
r = correr(['--borrar-todo'], entrada='si\n')
check('con "si" NO borra', cuantas() == (1, 3), cuantas())
r = correr(['--borrar-todo'], entrada='BORRAR\n')
check('con BORRAR sí vacía', cuantas() == (0, 0), cuantas())
with A.app.app_context():
    check('pero NO toca el plan del usuario',
          A.User.query.filter_by(username='ana').first().plan == 'premium')

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
