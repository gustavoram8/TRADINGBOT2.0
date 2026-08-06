# -*- coding: utf-8 -*-
"""El asistente de WhatsApp: ¿avisa de lo que importa y calla lo que no?

    python3 tools/test_asistente_wa.py

El dueño lleva el proyecto solo y pidió que "cada cosa importante que pase en
el website" le llegue por WhatsApp, que es lo que mira todo el día. Esta prueba
NO manda nada a su teléfono: sustituye la salida de CallMeBot por una lista y
comprueba el texto exacto que habría recibido.

Lo que se ataca, en orden de gravedad:

  · que un ENSAYO en sandbox no le haga sonar el teléfono (se pasó un día
    entero comprando con dinero de mentira);
  · que "pagué y no me llegó" se detecte y suba a urgente, escrito en
    cualquiera de los cuatro idiomas del sitio;
  · que un aviso NO pueda romper una venta aunque CallMeBot esté caído;
  · y que no viaje el correo del cliente a un tercero gratuito.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
import app as A  # noqa: E402

ok = fallos = 0
CLAVE = 'Zx8!kQ2mLp7w'
enviados = []


def check(cond, txt):
    global ok, fallos
    if cond:
        ok += 1
        print('  ok    ', txt)
    else:
        fallos += 1
        print('  FALLA ', txt)


def ultimo():
    return enviados[-1] if enviados else ''


def usuario(nombre, plan='free', admin=False):
    u = A.User.query.filter_by(username=nombre).first()
    if u:
        for M in (A.KnownDevice, A.SaleBreakdown, A.PlanSubscription,
                  A.CamoOrder, A.CosmeticOrder, A.BugReport, A.Order):
            M.query.filter_by(user_id=u.id).delete()
        A.db.session.delete(u)
        A.db.session.commit()
    u = A.User(username=nombre, email=nombre + '@correo-privado.com',
               plan=plan, is_admin=admin)
    u.set_password(CLAVE)
    for c in ('email_verified', 'is_verified', 'verified'):
        if hasattr(u, c):
            setattr(u, c, True)
    if plan != 'free':
        u.plan_cycle = 'monthly'
        u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=20)
    A.db.session.add(u)
    A.db.session.commit()
    return u.id


def cliente(nombre):
    c = A.app.test_client()
    c.post('/login', data={'identifier': nombre, 'password': CLAVE},
           follow_redirects=True)
    return c


def main():
    # CallMeBot sustituido por una lista. Nada sale a internet.
    A._wa_encolar = lambda texto: enviados.append(texto)
    A.WA_PHONE, A.WA_APIKEY = '+000', 'clave-falsa'
    entorno = A.PAYPAL_ENV

    try:
        with A.app.app_context():
            A.db.create_all()
            uid = usuario('wa_cliente', plan='premium')
            jefe = usuario('wa_jefe', admin=True)

            # ── 1 · una venta de plan ─────────────────────────────────────
            print('\n1 · venta de plan confirmada')
            A.PAYPAL_ENV = 'live'
            del enviados[:]
            o = A.Order(user_id=uid, plan='premium', billing_cycle='monthly',
                        base_price=50, discount_pct=0, final_price=50,
                        status='paid', payment_method='paypal',
                        paid_at=datetime.now(timezone.utc))
            A.db.session.add(o)
            A.db.session.commit()
            # ⚠️ El id se guarda como NÚMERO, no se lee del objeto más tarde:
            # al salir de este `app_context` la fila queda desligada de su
            # sesión y hasta leerle el `.id` revienta.
            oid = o.id
            A.send_payment_alert_email(o, 'sale')
            check(len(enviados) == 1, 'llega UN aviso (%d)' % len(enviados))
            m = ultimo()
            print('       ┌─ lo que llega al teléfono:')
            for l in m.split('\n'):
                print('       │ ' + l)
            check('VENTA confirmada' in m, 'dice que es una venta')
            check('$50.00' in m, 'con el monto')
            check('wa_cliente' in m, 'y el usuario')
            check('correo-privado' not in m,
                  '🔴 pero NO el correo del cliente: CallMeBot es un tercero')

            # ── 2 · un ensayo de sandbox NO suena ─────────────────────────
            print('\n2 · la misma venta, pero en sandbox')
            A.PAYPAL_ENV = 'sandbox'
            del enviados[:]
            o2 = A.Order(user_id=uid, plan='premium', billing_cycle='monthly',
                         base_price=50, discount_pct=0, final_price=50,
                         status='paid', payment_method='paypal',
                         paid_at=datetime.now(timezone.utc), is_test=True)
            A.db.session.add(o2)
            A.db.session.commit()
            A.send_payment_alert_email(o2, 'sale')
            check(not enviados,
                  '🔴 silencio absoluto (%d aviso(s)) — un día de pruebas no '
                  'puede ser un día de notificaciones' % len(enviados))
            A.PAYPAL_ENV = 'live'

            # ── 3 · pagó y NO se le entregó ───────────────────────────────
            print('\n3 · el peor caso: pagó y no recibió')
            del enviados[:]
            A.send_payment_alert_email(o, 'stuck')
            m = ultimo()
            check('🚨' in m, 'va con la marca de urgente')
            check('NO se le entregó' in m, 'y lo dice sin rodeos')
            check('requiere acción tuya' in m, 'pidiendo acción')
            check('/admin' in m, 'y diciendo dónde arreglarlo')

            # ── 4 · un contracargo ────────────────────────────────────────
            print('\n4 · un contracargo')
            del enviados[:]
            o.pay_status = 'disputed'
            A.db.session.commit()
            A.send_payment_alert_email(o, 'problem')
            m = ultimo()
            check('CONTRACARGO' in m, 'se llama por su nombre')
            check('/admin/trace' in m,
                  'y manda a la prueba de entrega, que es lo que se pelea')

            # ── 5 · una venta de cosméticos ───────────────────────────────
            print('\n5 · un carrito de cosméticos')
            del enviados[:]
            c = A.CosmeticOrder(user_id=uid, slugs='camo:santa,item:gambit',
                                label='2 cosmetics', price=8.98, status='paid',
                                payment_method='paypal', paid_amount=8.98,
                                paid_at=datetime.now(timezone.utc))
            A.db.session.add(c)
            A.db.session.commit()
            A.send_payment_alert_email(c, 'sale')
            m = ultimo()
            print('       ┌─ lo que llega al teléfono:')
            for l in m.split('\n'):
                print('       │ ' + l)
            check('8.98' in m, 'con el total REAL del carrito')
            check(':' not in m.split('Cosméticos (2):')[-1].split('\n')[0],
                  'y los nombres legibles, no las claves internas')

        # ── 6 · un bug de "pagué y no me llegó" ───────────────────────────
        print('\n6 · el cliente reporta que pagó y no le llegó')
        del enviados[:]
        cli = cliente('wa_cliente')
        cli.post('/api/bug/report', json={
            'description': 'Compré el camo de Santa y no me llegó nada, '
                           'sigue sin aparecer en mi cuenta.',
            'kind': 'data', 'url': '/cosmetics'})
        m = ultimo()
        print('       ┌─ lo que llega al teléfono:')
        for l in m.split('\n'):
            print('       │ ' + l)
        check('🚨' in m, '🔴 sube a URGENTE solo, sin que nadie lo clasifique')
        check('pagó y dice que no le llegó' in m, 'con el titular correcto')

        print('\n7 · un bug normal NO es urgente')
        del enviados[:]
        cli.post('/api/bug/report', json={
            'description': 'El botón de la pizarra se ve corrido en el móvil.',
            'kind': 'visual', 'url': '/app'})
        m = ultimo()
        check('🐛' in m and '🚨' not in m,
              'se avisa, pero sin alarma (%s)' % m.split('\n')[0])

        # ── 8 · el detector, en los cuatro idiomas ────────────────────────
        print('\n8 · el detector entiende a un cliente de cualquier idioma')
        casos = [
            ('ES', 'pagué el premium y no me llegó', True),
            ('EN', 'I paid for the plan but did not get it', True),
            ('FR', "j'ai payé et je n'ai pas reçu mon plan", True),
            ('PT', 'comprei o plano e não chegou nada', True),
            ('ruido', '¿cuánto cuesta el plan premium?', False),
            ('ruido', 'me encanta el analizador, gran trabajo', False),
        ]
        for etiqueta, texto, esperado in casos:
            r = A.parece_pago_no_entregado(texto)
            check(r == esperado, '%-6s %-46s → %s'
                  % (etiqueta, texto[:46], 'URGENTE' if r else 'normal'))

        # ── 9 · soporte ───────────────────────────────────────────────────
        print('\n9 · un mensaje de soporte')
        del enviados[:]
        A.app.test_client().post('/contact', data={
            'name': 'Ana', 'email': 'ana@ej.com', 'category': 'Billing',
            'message': 'Quisiera saber si hay descuento para estudiantes.'})
        m = ultimo()
        check('📬' in m, 'llega como informativo (%s)' % m.split('\n')[0])
        check('Ana' in m and 'descuento' in m, 'con quién escribe y qué dice')

        # ── 10 · una baja ─────────────────────────────────────────────────
        print('\n10 · un cliente se da de baja')
        del enviados[:]
        cliente('wa_cliente').post('/account/cancel-plan')
        m = ultimo()
        check('baja' in m.lower(),
              'se entera el mismo día, que es cuando aún puede retenerlo')

        # ── 11 · si CallMeBot está caído, la venta NO se rompe ─────────────
        print('\n11 · CallMeBot caído')

        def explota(texto):
            raise RuntimeError('CallMeBot no responde')
        A._wa_encolar = explota
        with A.app.app_context():
            try:
                A.avisar('venta', 'Prueba', [('x', 'y')])
                check(True, '🔴 avisar() se traga el fallo y sigue')
            except Exception as e:
                check(False, 'avisar() dejó escapar %s' % e)
            try:
                o3 = A.db.session.get(A.Order, oid)
                A.send_payment_alert_email(o3, 'sale')
                check(True, '🔴 y una venta se completa igual con el aviso roto')
            except Exception as e:
                check(False, 'la venta se rompió: %s' % e)

        # ── 12 · silenciar una categoría sin desplegar ────────────────────
        print('\n12 · el interruptor de silencio')
        del enviados[:]
        A._wa_encolar = lambda t: enviados.append(t)
        A.WA_MUTE = {'baja'}
        with A.app.app_context():
            A.avisar('baja', 'no debería sonar')
            A.avisar('venta', 'sí debería sonar')
        check(len(enviados) == 1 and 'sí debería' in enviados[0],
              'WA_MUTE apaga solo lo que se le dice (%d aviso)' % len(enviados))
        A.WA_MUTE = set()
    finally:
        A.PAYPAL_ENV = entorno

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
