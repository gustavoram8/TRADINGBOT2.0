# -*- coding: utf-8 -*-
"""Cambio de plan desde /admin y baja del cliente: lo que ve cada uno.

    python3 tools/test_plan_en_vivo.py

Dos cosas reportadas por el dueño:

  1. "Bajé a Free a mi hermano y siguió con su plan hasta que refrescó."
     La pantalla se pinta al cargar. Lo que NO puede pasar es que además
     conserve el ACCESO: el servidor decide en cada petición, y eso es lo que
     se comprueba aquí (que el permiso caiga al instante, sin refrescar).

  2. "El botón de darse de baja no funciona: sigo siendo premium."
     Darse de baja NO revoca el plan pagado — corta la renovación y deja el
     acceso hasta la fecha. Pero un plan puesto a mano desde /admin no tenía
     fecha de vencimiento, así que no había NADA que terminara y el botón
     parecía no hacer nada para siempre. Eso sí era un fallo.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scalpel'))
import app as A  # noqa: E402

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


def usuario(nombre, admin=False, plan='free'):
    u = A.User.query.filter_by(username=nombre).first()
    if u:
        A.KnownDevice.query.filter_by(user_id=u.id).delete()
        A.SaleBreakdown.query.filter_by(user_id=u.id).delete()
        A.PlanSubscription.query.filter_by(user_id=u.id).delete()
        A.Order.query.filter_by(user_id=u.id).delete()
        A.db.session.delete(u)
        A.db.session.commit()
    u = A.User(username=nombre, email=nombre + '@ej.com', plan=plan, is_admin=admin)
    u.set_password(CLAVE)
    for c in ('email_verified', 'is_verified', 'verified'):
        if hasattr(u, c):
            setattr(u, c, True)
    A.db.session.add(u)
    A.db.session.commit()
    return u.id


def entrar(c, nombre):
    c.post('/login', data={'identifier': nombre, 'password': CLAVE},
           follow_redirects=True)


def main():
    with A.app.app_context():
        A.db.create_all()
        jefe = usuario('adm_vivo', admin=True, plan='premium')
        cli = usuario('gussy_prueba', admin=False, plan='free')

    # ── 1 · el admin sube a alguien: el permiso vale ya ───────────────────
    print('\n1 · subir un plan desde /admin')
    with A.app.test_client() as c:
        entrar(c, 'adm_vivo')
        c.post('/admin/set-plan', data={'user_id': cli, 'plan': 'premium'})
    with A.app.app_context():
        u = A.db.session.get(A.User, cli)
        check(u.plan == 'premium', 'queda en Premium (%s)' % u.plan)
        check(u.plan_expires_at is not None,
              '🔴 y CON fecha de vencimiento (%s)' % u.plan_expires_at)
        check(u.plan_cycle == 'monthly', 'con ciclo mensual (%s)' % u.plan_cycle)
        venc = A._aware(u.plan_expires_at)
        dias = (venc - datetime.now(timezone.utc)).days
        check(29 <= dias <= 30, 'de un mes (%d días)' % dias)

    # ── 2 · pulsar el botón otra vez no regala meses ──────────────────────
    print('\n2 · repetir el mismo plan no estira la fecha')
    with A.app.app_context():
        antes = A._aware(A.db.session.get(A.User, cli).plan_expires_at)
    with A.app.test_client() as c:
        entrar(c, 'adm_vivo')
        c.post('/admin/set-plan', data={'user_id': cli, 'plan': 'premium'})
    with A.app.app_context():
        ahora = A._aware(A.db.session.get(A.User, cli).plan_expires_at)
        check(abs((ahora - antes).total_seconds()) < 2,
              'la fecha no se mueve (%s)' % ahora)

    # ── 3 · la baja: corta el cobro, NO el acceso ya pagado ───────────────
    print('\n3 · el cliente se da de baja')
    with A.app.test_client() as c:
        entrar(c, 'gussy_prueba')
        r = c.post('/account/cancel-plan', follow_redirects=False)
        check(r.status_code in (302, 303), 'la baja se acepta (%s)' % r.status_code)
        check('cancelled=1' in (r.headers.get('Location') or ''),
              'y avisa de que quedó hecha')
        pag = c.get('/settings').get_data(as_text=True)
        check('settings.cancelling' in pag, 'Ajustes muestra "Cancelando"')
        check('settings.accessEnds' in pag,
              'y la fecha en que termina el acceso')
    with A.app.app_context():
        u = A.db.session.get(A.User, cli)
        check(u.cancel_at_period_end, 'queda marcada la baja')
        check(u.plan == 'premium',
              'y CONSERVA el plan pagado hasta la fecha (%s) — es lo pactado'
              % u.plan)

    # ── 4 · y cuando llega la fecha, cae solo ─────────────────────────────
    print('\n4 · al vencer, cae a Free sin que nadie haga nada')
    with A.app.app_context():
        u = A.db.session.get(A.User, cli)
        u.plan_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        A.db.session.commit()
    with A.app.test_client() as c:
        entrar(c, 'gussy_prueba')
        c.get('/settings')
    with A.app.app_context():
        u = A.db.session.get(A.User, cli)
        check(u.plan == 'free', 'ya es Free (%s)' % u.plan)
        check(not u.cancel_at_period_end, 'y la marca de baja se limpia')

    # ── 5 · bajar a Free desde /admin corta el acceso EN EL ACTO ──────────
    # ⚠️ Los clientes van SIN `with`. Con `with`, Flask conserva el contexto de
    # la última petición, y con él la sesión de SQLAlchemy — o sea su caché de
    # objetos: el usuario se queda congelado en el plan viejo y el test acusa
    # un fallo del servidor que no existe. En producción cada petición estrena
    # contexto y sesión. Costó un rato entenderlo; que quede escrito.
    print('\n5 · bajar a Free mientras el usuario tiene la app abierta')
    adm = A.app.test_client()
    entrar(adm, 'adm_vivo')
    adm.post('/admin/set-plan', data={'user_id': cli, 'plan': 'premium'})

    cli_c = A.app.test_client()
    entrar(cli_c, 'gussy_prueba')
    d = cli_c.get('/api/usage').get_json()
    check(d and d.get('plan') == 'premium',
          'el cliente ve Premium (%s)' % (d or {}).get('plan'))
    check(d and d.get('max') == 5,
          'con su cuota de Premium (%s)' % (d or {}).get('max'))
    # el dueño lo baja desde OTRA sesión, sin tocar la del cliente
    adm.post('/admin/set-plan', data={'user_id': cli, 'plan': 'free'})
    # la MISMA sesión del cliente, sin refrescar ni volver a entrar
    d = cli_c.get('/api/usage').get_json()
    check(d and d.get('plan') == 'free',
          '🔴 su sesión ya reporta Free sin refrescar (%s)'
          % (d or {}).get('plan'))
    check(d and d.get('max') == 1,
          'y la cuota de Free (%s)' % (d or {}).get('max'))
    r = cli_c.get('/forum/feed')
    check(r.status_code in (401, 403),
          'el foro (de pago) se le cierra al instante (%s)' % r.status_code)

    # ── 6 · el vigilante está en la página ────────────────────────────────
    print('\n6 · la pantalla se entera sola')
    c = A.app.test_client()
    entrar(c, 'gussy_prueba')
    c.get('/welcome')          # /app exige el pase del splash
    pag = c.get('/app').get_data(as_text=True)
    check('nx-plan-watch' in pag, 'el vigilante de plan viaja en /app')
    check('visibilitychange' in pag,
          'y mira al volver a la pestaña, no solo por reloj')

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
