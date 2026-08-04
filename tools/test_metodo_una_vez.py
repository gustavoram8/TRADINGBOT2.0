# -*- coding: utf-8 -*-
"""Al comprador NUNCA se le pregunta el método dos veces.

Lo reportó el dueño: "ya en la primera pantalla estás eligiendo el método, por
qué en la segunda volverías a preguntar". Tenía razón y había dos agujeros:

  1. Si ya tenía un pedido colgando, la rama de "pedido duplicado" tiraba a la
     basura el método que acababa de marcar y lo mandaba a elegirlo otra vez.
  2. El método no se guardaba en ningún sitio, así que volver a un pedido de
     hace días obligaba a decidir de nuevo.

La pantalla de elegir método sigue existiendo, pero solo para lo que tiene
sentido: cuando nadie ha elegido todavía, o cuando él pide cambiar.
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


def main():
    with A.app.app_context():
        A.db.create_all()
        u = A.User.query.filter_by(username='dobleprg').first()
        if not u:
            u = A.User(username='dobleprg', email='dobleprg@ej.com')
            u.set_password('Zx8!kQ2mLp7w')
            A.db.session.add(u)
        u.plan = 'free'
        for campo in ('email_verified', 'is_verified', 'verified'):
            if hasattr(u, campo):
                setattr(u, campo, True)
        A.Order.query.filter_by(user_id=u.id).delete()
        A.db.session.commit()
        uid = u.id

    rieles = A.available_payment_rails()
    print('rieles encendidos:', rieles)
    check(len(rieles) > 1, 'hay mas de un riel (si no, la prueba no prueba nada)')

    # ── 1 · compra normal: elige USDT y NO se le vuelve a preguntar ────────
    with A.app.test_client() as c:
        entrar(c, 'dobleprg')
        r = c.post('/checkout/create',
                   data={'plan': 'premium', 'cycle': 'monthly', 'method': 'manual'},
                   follow_redirects=False)
        check(r.status_code == 200, 'compra con USDT: responde la pagina, no un salto')
        cuerpo = r.get_data(as_text=True)
        check('cdone.title' in cuerpo or 'Order received' in cuerpo,
              'compra con USDT: aterriza en las instrucciones de USDT')
        check('cpay.title' not in cuerpo,
              'compra con USDT: NO se le vuelve a preguntar el metodo')

    with A.app.app_context():
        o = A.Order.query.filter_by(user_id=uid, status='pending').first()
        check(o is not None, 'quedo un pedido pendiente')
        check(o.payment_method == 'manual',
              'el pedido RECUERDA el metodo elegido (%r)' % (o and o.payment_method))
        oid = o.id

    # ── 2 · vuelve al carrito con el pedido colgando ───────────────────────
    # Esta es la rama que el dueño pisó: antes tiraba el método y preguntaba.
    with A.app.test_client() as c:
        entrar(c, 'dobleprg')
        r = c.post('/checkout/create',
                   data={'plan': 'premium', 'cycle': 'monthly', 'method': 'manual'},
                   follow_redirects=False)
        check(r.status_code == 200 and '/checkout/pay/' not in r.headers.get('Location', ''),
              'pedido ya abierto + metodo marcado: NO manda a elegir otra vez')
        check('Order received' in r.get_data(as_text=True) or 'cdone.title' in r.get_data(as_text=True),
              'pedido ya abierto: vuelve a las instrucciones de su metodo')

    # ── 3 · retoma el pedido sin decir nada: se reutiliza lo que eligio ────
    with A.app.test_client() as c:
        entrar(c, 'dobleprg')
        r = c.post('/checkout/create',
                   data={'plan': 'premium', 'cycle': 'monthly'},   # sin method
                   follow_redirects=False)
        check(r.status_code == 200,
              'retomar sin decir metodo: usa el que ya habia elegido, no pregunta')

    # ── 4 · un metodo inventado por el navegador no cuela ──────────────────
    with A.app.app_context():
        o = A.db.session.get(A.Order, oid)
        o.payment_method = 'usdt-binance'      # como nace un pedido
        A.db.session.commit()
    with A.app.test_client() as c:
        entrar(c, 'dobleprg')
        r = c.post('/checkout/create',
                   data={'plan': 'premium', 'cycle': 'monthly', 'method': 'gratis-total'},
                   follow_redirects=False)
        check(r.status_code in (302, 303) and '/checkout/pay/' in r.headers.get('Location', ''),
              'metodo inventado: se ignora y se le pregunta (no se cobra por ahi)')
    with A.app.app_context():
        o = A.db.session.get(A.Order, oid)
        check(o.payment_method != 'gratis-total',
              'metodo inventado: NO se guarda en el pedido')

    # ── 5 · la pantalla de elegir sigue existiendo para cambiar de idea ────
    with A.app.test_client() as c:
        entrar(c, 'dobleprg')
        r = c.get('/checkout/pay/%d' % oid)
        check(r.status_code == 200, 'la pantalla de elegir metodo sigue accesible')
        cuerpo = r.get_data(as_text=True)
        check(cuerpo.count('name="method"') == len(rieles),
              'ofrece exactamente los rieles encendidos (%d)' % len(rieles))

    # ── 6 · y elegir ahi tambien queda recordado ───────────────────────────
    with A.app.test_client() as c:
        entrar(c, 'dobleprg')
        c.post('/checkout/pay/%d' % oid, data={'method': 'manual'},
               follow_redirects=False)
    with A.app.app_context():
        o = A.db.session.get(A.Order, oid)
        check(o.payment_method == 'manual',
              'cambiar de metodo en esa pantalla tambien se recuerda')
        A.Order.query.filter_by(user_id=uid).delete()
        A.db.session.commit()

    print('\n%d/%d' % (ok, ok + fallos))
    return 1 if fallos else 0


sys.exit(main())
