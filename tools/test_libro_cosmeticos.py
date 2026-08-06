# -*- coding: utf-8 -*-
"""El libro de cosméticos: aparte de los planes, por mes y por día.

    python3 tools/test_libro_cosmeticos.py

Pedido del dueño (2026-08-05): una tabla como la de ventas pero SOLO de
cosméticos — qué usuario compra, cuánto terminó pagando en el carrito, y el
dinero desglosado por mes y por día. Sin socios, sin reserva, sin mezclarse
con los planes.

Lo que se ataca aquí, en orden de gravedad:

  · que un ensayo de sandbox NO aparezca como dinero (el mismo engaño que ya
    hubo que arreglar en Revenue con los planes);
  · que el backfill selle los pedidos de sandbox viejos SIN tocar una compra
    real hecha después del paso a live — la regla es la FECHA en que las
    claves live entraron al VPS, no el entorno de hoy;
  · que una compra de cosméticos jamás pise el libro de ventas de planes;
  · y que los totales por mes y por día cuadren con las filas.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
import app as A  # noqa: E402
from sqlalchemy import text  # noqa: E402

ok = fallos = 0
CLAVE = 'Zx8!kQ2mLp7w'


def check(cond, txt):
    global ok, fallos
    if cond:
        ok += 1
        print('  ok    ', txt)
    else:
        fallos += 1
        print('  FALLA ', txt)


def usuario(nombre, admin=False):
    u = A.User.query.filter_by(username=nombre).first()
    if u:
        for M in (A.KnownDevice, A.SaleBreakdown, A.PlanSubscription,
                  A.CamoOrder, A.CosmeticOrder, A.Order):
            M.query.filter_by(user_id=u.id).delete()
        A.db.session.delete(u)
        A.db.session.commit()
    u = A.User(username=nombre, email=nombre + '@ej.com', plan='free',
               is_admin=admin)
    u.set_password(CLAVE)
    for c in ('email_verified', 'is_verified', 'verified'):
        if hasattr(u, c):
            setattr(u, c, True)
    A.db.session.add(u)
    A.db.session.commit()
    return u.id


def compra_suelta(uid, slug, precio, cuando, prueba=False, pagado=None):
    o = A.CamoOrder(user_id=uid, slug=slug, label=slug, price=precio,
                    status='paid', payment_method='paypal',
                    created_at=cuando, paid_at=cuando, is_test=prueba,
                    paid_amount=pagado)
    A.db.session.add(o)
    A.db.session.commit()
    return o.id


def carrito(uid, refs, total, cuando, prueba=False):
    o = A.CosmeticOrder(user_id=uid, slugs=','.join(refs),
                        label='%d cosmetics' % len(refs), price=total,
                        status='paid', payment_method='paypal',
                        created_at=cuando, paid_at=cuando, is_test=prueba)
    A.db.session.add(o)
    A.db.session.commit()
    return o.id


def contexto(mes=''):
    with A.app.test_request_context('/admin' + ('?cos_month=%s' % mes
                                                if mes else '')):
        return A._build_cosmetics_context()


def main():
    ahora = datetime.now(timezone.utc)
    este_mes = ahora.replace(day=15, hour=12, minute=0, second=0, microsecond=0)
    mes_pasado = (este_mes.replace(day=1) - timedelta(days=10)).replace(day=8)

    with A.app.app_context():
        A.db.create_all()
        A.CamoOrder.query.delete()
        A.CosmeticOrder.query.delete()
        A.db.session.commit()
        # Punto de partida del libro de PLANES: lo que haya dejado otra suite.
        ventas_antes = A.SaleBreakdown.query.count()
        with A.app.test_request_context('/admin'):
            revenue_antes = A._build_revenue_context()['lifetime_total']
        uid_a = usuario('cos_ana')
        uid_b = usuario('cos_beto')

        # ── 1 · compras reales: sueltas y carrito, en dos meses ───────────
        print('\n1 · el libro suma lo real, por mes')
        compra_suelta(uid_a, 'santa', 4.99, este_mes)
        carrito(uid_b, ['camo:santa', 'item:gambit', 'item:cur-rocket'],
                9.97, este_mes + timedelta(days=1))
        compra_suelta(uid_b, 'naval', 4.99, mes_pasado)
        ctx = contexto()
        check(ctx['cos_lifetime_total'] == 19.95,
              '🔴 histórico = $%.2f (4.99 + 9.97 + 4.99)'
              % ctx['cos_lifetime_total'])
        check(ctx['cos_view_total'] == 14.96 and ctx['cos_view_count'] == 2,
              'el mes actual: $%.2f en %d compra(s)'
              % (ctx['cos_view_total'], ctx['cos_view_count']))
        k_pasado = mes_pasado.strftime('%Y-%m')
        fila_mes = [m for m in ctx['cos_months'] if m['key'] == k_pasado][0]
        check(fila_mes['total'] == 4.99, 'y el mes pasado guarda su $4.99')
        ctx2 = contexto(mes=k_pasado)
        check(ctx2['cos_view_total'] == 4.99 and ctx2['cos_view_count'] == 1,
              'el selector de mes enseña ese mes')

        # ── 2 · por día ───────────────────────────────────────────────────
        print('\n2 · desglose por día')
        check(len(ctx['cos_days']) == 2, 'dos días con venta (%d)'
              % len(ctx['cos_days']))
        por_dia = {d['dia']: d for d in ctx['cos_days']}
        d1 = este_mes.strftime('%Y-%m-%d')
        d2 = (este_mes + timedelta(days=1)).strftime('%Y-%m-%d')
        check(por_dia[d1]['total'] == 4.99 and por_dia[d2]['total'] == 9.97,
              'cada día con su total exacto')
        check(sum(d['total'] for d in ctx['cos_days'])
              == ctx['cos_view_total'],
              '🔴 los días SUMAN el total del mes')

        # ── 3 · la fila dice quién, qué y cuánto pagó DE VERDAD ───────────
        print('\n3 · cada compra, legible')
        filas = {f['username']: f for f in ctx['cos_rows']}
        check(filas['cos_ana']['pagado'] == 4.99, 'la suelta: su precio')
        f = filas['cos_beto']
        check(f['pagado'] == 9.97 and f['n_piezas'] == 3,
              'el carrito: el TOTAL cobrado, con sus 3 piezas')
        check(all(':' not in p for p in f['piezas']),
              'los nombres son legibles, no refs (%s)' % ', '.join(f['piezas']))
        # Y lo cobrado manda sobre la etiqueta: si PayPal reporta otro importe,
        # el libro enseña lo que de verdad se cobró.
        compra_suelta(uid_a, 'pole', 4.99, este_mes + timedelta(days=2),
                      pagado=4.50)
        ctx = contexto()
        f2 = [x for x in ctx['cos_rows'] if x['pagado'] == 4.50]
        check(len(f2) == 1, '🔴 manda lo COBRADO ($4.50), no la etiqueta ($4.99)')

        # ── 4 · un ensayo de sandbox no es dinero ─────────────────────────
        print('\n4 · los ensayos, aparte')
        antes = contexto()['cos_lifetime_total']
        compra_suelta(uid_b, 'blackflag', 4.99, este_mes, prueba=True)
        ctx = contexto()
        check(ctx['cos_lifetime_total'] == antes,
              '🔴 el histórico NO se mueve ($%.2f)' % ctx['cos_lifetime_total'])
        check(ctx['cos_pruebas_n'] == 1 and ctx['cos_pruebas_total'] == 4.99,
              'pero el ensayo se VE aparte, no desaparece')
        check(all(x['username'] != 'cos_beto' or x['pagado'] != 4.99
                  or not x['es_prueba'] for x in ctx['cos_rows']),
              'y no se cuela en las filas del mes')

        # ── 5 · el sello se estampa solo al pagar en sandbox ──────────────
        print('\n5 · el sello automático de _paypal_apply_status')
        env = A.PAYPAL_ENV
        try:
            A.PAYPAL_ENV = 'sandbox'
            o = A.CamoOrder(user_id=uid_a, slug='mission', label='mission',
                            price=4.99, status='pending',
                            payment_method='paypal', created_at=ahora)
            A.db.session.add(o)
            A.db.session.commit()
            # ⚠️ minúsculas: PAYPAL_PAID_STATES es ('completed',) y los
            # llamadores reales normalizan antes de llegar aquí.
            A._paypal_apply_status(o, 'completed', 4.99, 'CAP-X', 'camo')
            check(o.status == 'paid' and o.is_test,
                  '🔴 pagado en sandbox → nace sellado como ensayo')
            A.PAYPAL_ENV = 'live'
            o2 = A.CamoOrder(user_id=uid_a, slug='fourth', label='fourth',
                             price=4.99, status='pending',
                             payment_method='paypal', created_at=ahora)
            A.db.session.add(o2)
            A.db.session.commit()
            A._paypal_apply_status(o2, 'completed', 4.99, 'CAP-Y', 'camo')
            check(o2.status == 'paid' and not o2.is_test,
                  'pagado en live → venta real')
            # y el sello viejo no se reescribe por estar hoy en live
            check(A.db.session.get(A.CamoOrder, o.id).is_test,
                  '🔴 el ensayo de ayer sigue siendo ensayo hoy')
        finally:
            A.PAYPAL_ENV = env

        # ── 6 · el backfill de la migración corta por FECHA, no por entorno ─
        print('\n6 · la migración sella lo viejo sin tocar lo nuevo')
        with A.db.engine.begin() as c:
            for t in ('camo_order', 'cosmetic_order'):
                c.execute(text('UPDATE %s SET is_test = FALSE' % t))
        # dos pedidos de PayPal: uno ANTERIOR al paso a live y uno posterior
        viejo = compra_suelta(uid_a, 'premium', 7.99,
                              datetime(2026, 8, 1, 12, 0, 0))
        nuevo = compra_suelta(uid_a, 'standard', 7.99,
                              datetime(2026, 8, 6, 12, 0, 0))
        # se simula la base de ANTES de la migración: sin la columna no se
        # puede (SQLite no la deja quitar con datos) — se ejecuta solo el
        # backfill, que es la parte con lógica
        with A.db.engine.begin() as c:
            c.execute(text(
                "UPDATE camo_order SET is_test = TRUE WHERE "
                "payment_method = 'paypal' AND created_at < '%s'"
                % A.PAYPAL_LIVE_DESDE))
        check(A.db.session.get(A.CamoOrder, viejo).is_test,
              '🔴 lo pagado ANTES de las claves live queda como ensayo')
        check(not A.db.session.get(A.CamoOrder, nuevo).is_test,
              '🔴 y una compra real posterior NO se toca, aunque el deploy '
              'llegue tarde')

        # ── 7 · cosméticos jamás pisan el libro de planes ─────────────────
        # ⚠️ Se mide el DELTA, no el total: las suites comparten el mismo
        # SQLite, así que exigir "cero filas" haría que este test solo pasara
        # si corre el primero — y un test que depende del orden es peor que no
        # tenerlo, porque falla el día equivocado.
        print('\n7 · aislamiento del libro de ventas')
        check(A.SaleBreakdown.query.count() == ventas_antes,
              '🔴 el libro de PLANES no ganó ni una fila (%d → %d)'
              % (ventas_antes, A.SaleBreakdown.query.count()))
        with A.app.test_request_context('/admin'):
            ctxr = A._build_revenue_context()
        check(ctxr['lifetime_total'] == revenue_antes,
              'y Revenue de planes no se movió ($%.2f)' % ctxr['lifetime_total'])

        # ── 8 · el panel se pinta ─────────────────────────────────────────
        print('\n8 · la pestaña en /admin')
        jefe = usuario('cos_jefe', admin=True)
    c = A.app.test_client()
    c.post('/login', data={'identifier': 'cos_jefe', 'password': CLAVE},
           follow_redirects=True)
    r = c.get('/admin')
    html = r.get_data(as_text=True)
    check(r.status_code == 200, '/admin responde (%s)' % r.status_code)
    check('data-pane="cosmeticos"' in html, 'la pestaña existe')
    check('Libro de cosméticos' in html, 'con su título')
    # A esta altura la sección 6 selló la compra de julio como ensayo, así que
    # solo queda UN mes real y el selector no tiene enlaces — se comprueba que
    # el mes en pantalla y los ensayos aparte sí se pintan.
    check('Mes:' in html and 'Compras del mes' in html,
          'el selector de mes y la tabla se pintan')
    check('ensayo(s) de sandbox' in html,
          'y los ensayos se enseñan aparte, no desaparecen')

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
