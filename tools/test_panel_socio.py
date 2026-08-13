# -*- coding: utf-8 -*-
"""El panel del colaborador: quién entra, qué ve y la billetera del 4.4.

    venv/bin/python3 tools/test_panel_socio.py

Punto 16 de la lista del dueño. Reglas que vigila:
  · un usuario COMÚN no tiene ni panel ni entrada de menú (404 seco);
  · el colaborador (dueño de un código) ve SU panel y escribe SU billetera;
  · el ADMIN ve el panel de todos (antes recibía 404: el dueño no podía ver
    lo que iba a entregar) pero NO edita billeteras ajenas;
  · guardar la billetera deja fila de auditoría — el "por escrito" del 4.4;
  · el panel dice lo que el acuerdo promete: día 15, USDT, fechas del
    acuerdo (5.1–5.3) y qué NO genera comisión (2.5).
"""
from __future__ import print_function

import os
import sys
import tempfile
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'ps.db')
os.environ.setdefault('SECRET_KEY', 'panel-socio')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                           # noqa: E402

OK = FALLOS = 0
CL = 'Zx9!wQ4mNp2r'


def check(cond, texto):
    global OK, FALLOS
    print(('  ✅ ' if cond else '  ❌ ') + texto)
    if cond:
        OK += 1
    else:
        FALLOS += 1


def sesion(n):
    c = A.app.test_client()
    c.post('/login', data={'identifier': n, 'password': CL},
           follow_redirects=True)
    return c


def main():
    global OK, FALLOS
    with A.app.app_context():
        A.db.create_all()
        for n, adm in (('gabriel', False), ('comun', False), ('jefe', True)):
            u = A.User(username=n, email=n + '@d.invalid', email_verified=True)
            u.set_password(CL); u.email_canonical = u.email
            u.plan = 'free'; u.is_admin = adm
            A.db.session.add(u)
        A.db.session.commit()
        gid = A.User.query.filter_by(username='gabriel').first().id
        A.db.session.add(A.PromoCode(code='GABRIEL20', discount_pct=20,
                                     creator_name='Gabriel', kind='creator',
                                     owner_user_id=gid, valid_for='monthly'))
        A.db.session.commit()

    print('\n══ 1 · el candado, por los tres perfiles ══')
    c_comun = sesion('comun')
    r = c_comun.get('/partner')
    check(r.status_code == 404, 'usuario común → 404 (para él no existe)')
    r = c_comun.post('/partner/wallet', data={'address': 'T' * 34})
    check(r.status_code == 404, 'y tampoco puede escribir billetera (404)')

    c_socio = sesion('gabriel')
    r = c_socio.get('/partner')
    check(r.status_code == 200 and 'GABRIEL20' in r.get_data(as_text=True),
          'el colaborador ve SU panel con su código')

    c_jefe = sesion('jefe')
    r = c_jefe.get('/partner')
    h = r.get_data(as_text=True)
    check(r.status_code == 200 and 'GABRIEL20' in h,
          '🔑 el ADMIN también entra y ve el panel del colaborador (antes 404)')
    check('partner.adminView' in h, 'con el aviso de vista de administrador')
    check('name="address"' not in h,
          'pero SIN formulario de billetera: la escribe cada colaborador')

    print('\n══ 2 · la entrada del menú, solo para quien corresponde ══')
    for quien, cli, espera in (('común', c_comun, False),
                               ('colaborador', c_socio, True),
                               ('admin', c_jefe, True)):
        cli.set_cookie('scalpel_splash_ts', '1')
        h = cli.get('/app').get_data(as_text=True)
        tiene = 'isPartner: true' in h
        check(tiene == espera, '%s → isPartner=%s' % (quien, tiene))

    print('\n══ 3 · la billetera (punto 4.4) ══')
    r = c_socio.post('/partner/wallet',
                     data={'address': 'TXa9b8c7d6e5f4g3h2j1k0mnpqrstuvwxy',
                           'network': 'TRC-20'}, follow_redirects=False)
    check(r.status_code == 302 and 'wallet=ok' in (r.headers.get('Location') or ''),
          'el colaborador guarda su billetera')
    with A.app.app_context():
        u = A.User.query.filter_by(username='gabriel').first()
        check(u.partner_wallet.startswith('TXa9') and u.partner_wallet_net == 'TRC-20',
              'y queda en su cuenta (dirección + red)')
        ev = (A.AuditEvent.query.filter_by(event_type='partner_wallet_set')
              .order_by(A.AuditEvent.id.desc()).first())
        check(ev is not None and 'TXa9' in (ev.detail or ''),
              'con fila de auditoría: ese es el "por escrito" del acuerdo')
    h = c_socio.get('/partner').get_data(as_text=True)
    check('TXa9b8c7d6e5f4g3h2j1k0mnpqrstuvwxy' in h,
          'el panel la enseña')
    h = c_jefe.get('/partner').get_data(as_text=True)
    check('TXa9b8c7d6e5f4g3h2j1k0mnpqrstuvwxy' in h,
          'el admin la VE (solo lectura)')

    for mala, motivo in (('corta123', 'demasiado corta'),
                         ('TXa9 b8c7 d6e5 f4g3 h2j1 k0mn pqrs', 'con espacios')):
        r = c_socio.post('/partner/wallet', data={'address': mala},
                         follow_redirects=False)
        bien = 'wallet=err' in (r.headers.get('Location') or '')
        with A.app.app_context():
            u = A.User.query.filter_by(username='gabriel').first()
            bien = bien and u.partner_wallet.startswith('TXa9')
        check(bien, 'dirección %s → rechazada sin tocar la guardada' % motivo)

    print('\n══ 4 · las fechas del acuerdo (5.1–5.3) ══')
    with A.app.app_context():
        u = A.User.query.filter_by(username='gabriel').first()
        check(u.partner_since is None, 'sin conectar desde /admin, aún sin fecha')
    r = c_jefe.post('/admin/promo/owner', data={'id': 1, 'owner': 'gabriel',
                                                'since': '2026-08-10'})
    with A.app.app_context():
        u = A.User.query.filter_by(username='gabriel').first()
        check(u.partner_since == date(2026, 8, 10),
              'el admin fija la fecha de entrada en vigor al conectar')
    h = c_socio.get('/partner').get_data(as_text=True)
    check('2026-08-10' in h and '2026-09-09' in h and '2026-11-10' in h,
          'el panel calcula: inicio, revisión de 30 días y fin del período de '
          '3 meses')
    r = c_jefe.post('/admin/promo/owner', data={'id': 1, 'owner': 'gabriel'})
    with A.app.app_context():
        u = A.User.query.filter_by(username='gabriel').first()
        check(u.partner_since == date(2026, 8, 10),
              'reconectar SIN fecha no pisa la que ya estaba')

    print('\n══ 5 · lo que el acuerdo promete decir, dicho ══')
    h = c_socio.get('/partner').get_data(as_text=True)
    for clave, que in (('partner.liq', 'día 15 + USDT con fecha concreta'),
                       ('partner.noCommission', 'qué NO genera comisión (2.5)'),
                       ('partner.privacy', 'ventas sin identidad del cliente'),
                       ('partner.dRenew', 'renovación automática (5.3)')):
        check(clave in h, que)
    from datetime import datetime, timezone
    hoy = datetime.now(timezone.utc).date()
    liq = A._proxima_liquidacion(hoy)
    check(liq.day == 15 and (liq >= hoy), 'la próxima liquidación es un 15 futuro')

    print('\n══ 5b · TRES colaboradores: cada uno ve SOLO lo suyo ══')
    # La pregunta del dueño tal cual: "imagina que tengo 3 asociados — al
    # activarse su interruptor, ¿uno puede ver el apartado de los demás?".
    # El filtro es owner_user_id == la cuenta logueada: no hay parámetro en la
    # URL que un curioso pueda cambiar, así que no hay nada que adivinar.
    with A.app.app_context():
        for n, cod in (('lucia', 'LUCIA20'), ('pedro', 'PEDRO20')):
            u = A.User(username=n, email=n + '@d.invalid', email_verified=True)
            u.set_password(CL); u.email_canonical = u.email; u.plan = 'free'
            A.db.session.add(u); A.db.session.flush()
            A.db.session.add(A.PromoCode(
                code=cod, discount_pct=20, creator_name=n.capitalize(),
                kind='creator', owner_user_id=u.id, valid_for='monthly'))
        A.db.session.commit()
    vistas = {}
    for n in ('gabriel', 'lucia', 'pedro'):
        h = sesion(n).get('/partner').get_data(as_text=True)
        vistas[n] = h
    check('GABRIEL20' in vistas['gabriel'] and 'LUCIA20' not in vistas['gabriel']
          and 'PEDRO20' not in vistas['gabriel'],
          'Gabriel ve su código y NO los de Lucía ni Pedro')
    check('LUCIA20' in vistas['lucia'] and 'GABRIEL20' not in vistas['lucia'],
          'Lucía ve el suyo y NO el de Gabriel')
    check('TXa9b8c7d6e5f4g3h2j1k0mnpqrstuvwxy' not in vistas['lucia']
          and 'TXa9b8c7d6e5f4g3h2j1k0mnpqrstuvwxy' not in vistas['pedro'],
          'y NADIE ve la billetera de otro')
    h = c_jefe.get('/partner').get_data(as_text=True)
    check(all(c in h for c in ('GABRIEL20', 'LUCIA20', 'PEDRO20')),
          'el admin sí ve los tres bloques, cada uno separado')

    print('\n══ 6 · i18n ══')
    import io
    js = io.open(os.path.join(RAIZ, 'scalpel', 'static', 'pages_i18n.js'),
                 encoding='utf-8').read()
    for k in ('adminView', 'liq', 'walletTitle', 'walletBody', 'walletSave',
              'dSince', 'dRenew', 'noCommission'):
        check(js.count("'partner.%s':" % k) == 4, "clave partner.%s ×4" % k)
    idx = io.open(os.path.join(RAIZ, 'scalpel', 'templates', 'index.html'),
                  encoding='utf-8').read()
    check(idx.count("'account.partner':") == 4, 'entrada del menú ×4 idiomas')

    print('\nRESULTADO: %d/%d' % (OK, OK + FALLOS))
    return 0 if FALLOS == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
