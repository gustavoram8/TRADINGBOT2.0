# -*- coding: utf-8 -*-
"""El comando guiado: borra lo que se le dice, respeta lo que no, y NUNCA
borra una cuenta admin ni deja filas huerfanas."""
import os, subprocess, sys, tempfile

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('   %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

DB = os.path.join(tempfile.mkdtemp(), 'q.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + DB
env = dict(os.environ)
sys.path.insert(0, '/home/user/TRADINGBOT2.0/scalpel')
import app as A

with A.app.app_context():
    A.db.create_all()
    jefe = A.User(username='jefe', email='j@demo.invalid', plan='premium',
                  email_verified=True, is_admin=True)
    jefe.set_password('Xk9!mQ2#pL5v')
    fake = A.User(username='falso', email='f@demo.invalid', plan='premium', email_verified=True)
    fake.set_password('Xk9!mQ2#pL5v')
    real = A.User(username='clienta', email='c@demo.invalid', plan='standard', email_verified=True)
    real.set_password('Xk9!mQ2#pL5v')
    A.db.session.add_all([jefe, fake, real])
    A.db.session.add(A.PromoCode(code='GABO', discount_pct=20, kind='creator',
                                 creator_name='Gabriel', valid_for='both', active=True))
    A.db.session.add(A.PromoCode(code='BASURA', discount_pct=100, kind='discount',
                                 valid_for='both', active=True))
    A.db.session.commit()
    # cosas colgando del usuario falso
    A.db.session.add(A.XPLog(user_id=fake.id, source='login', amount=18, day='2026-08-01'))
    o = A.Order(user_id=fake.id, plan='premium', billing_cycle='monthly', base_price=50.0,
                final_price=50.0, status='paid', payment_method='paypal')
    A.db.session.add(o); A.db.session.commit()
    A.db.session.add(A.SaleBreakdown(order_id=o.id, user_id=fake.id, username='falso',
                                     plan='premium', billing_cycle='monthly', gross=50.0,
                                     net_paid=50.0, is_manual=False))
    A.db.session.commit()
    FID = fake.id

def correr(entrada):
    return subprocess.run([sys.executable, '/home/user/TRADINGBOT2.0/tools/limpiar_pruebas.py',
                           '--limpiar'], input=entrada, capture_output=True, text=True,
                          env=env, timeout=120)

def estado():
    # Se cuentan POR NOMBRE, no por total: init_db() siembra una cuenta admin
    # y contar totales hacia fallar el test por algo que no es el codigo.
    with A.app.app_context():
        return (A.SaleBreakdown.query.count(), A.Order.query.count(),
                A.PromoCode.query.count(),
                sorted(u.username for u in A.User.query
                       if u.username in ('jefe', 'falso', 'clienta')))

print('── Decir que NO a todo no borra nada')
r = correr('no\n\n\n')
check('todo intacto', estado() == (1, 1, 2, ['clienta','falso','jefe']), estado())

print('\n── Borrar libro + un codigo + la cuenta falsa')
# 1) BORRAR  2) BASURA  3) falso + BORRAR
r = correr('BORRAR\nBASURA\nfalso\nBORRAR\n')
v, o_, c, u = estado()
check('libro vacio', (v, o_) == (0, 0), (v, o_))
check('borro solo el codigo indicado', c == 1, c)
with A.app.app_context():
    check('y GABO sigue vivo', A.PromoCode.query.first().code == 'GABO')
check('borro la cuenta falsa', 'falso' not in u, u)
with A.app.app_context():
    check('sin dejar XP huerfano', A.XPLog.query.filter_by(user_id=FID).count() == 0)
    check('el admin sigue', A.User.query.filter_by(username='jefe').first() is not None)
    check('y la clienta tambien', A.User.query.filter_by(username='clienta').first() is not None)

print('\n── Una cuenta ADMIN no se borra ni pidiendolo')
# El libro ya esta vacio, asi que la 1a pregunta no aparece: la secuencia es
# codigos (Enter) y luego cuentas.
r = correr('\njefe\nBORRAR\n')
with A.app.app_context():
    check('sigue ahi', A.User.query.filter_by(username='jefe').first() is not None)
check('y lo dice', 'es ADMIN' in r.stdout, r.stdout[-200:])

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
