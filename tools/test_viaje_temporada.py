# -*- coding: utf-8 -*-
"""El VIAJE EN EL TIEMPO de la ruleta (`/admin/demo` scenario=season).

    python3 tools/test_viaje_temporada.py

Existe porque la tienda esconde las temporadas futuras a propósito ("una
sorpresa, no un spoiler") y eso también dejaba al dueño sin poder revisar un
camo, marco o cursor ANTES de estrenarlo. El viaje vive en `_current_season()`
— la fuente del mes — para que tanda, giro, tienda y etiquetas se muevan todos
juntos; un parche por pantalla habría dejado alguna sin viajar, que es justo
el bug que este mecanismo debe permitir cazar.

Lo que se vigila:
  · que el salto mueva la tanda Y la tienda (coherencia entre las dos)
  · que sea SOLO-ADMIN y que no escriba nada en la base
  · que un mes inventado se rechace (el valor acaba en consulta y en pantalla)
  · que fuera de una petición el mes siga siendo el REAL (arranque, publicadores)
"""
from __future__ import print_function

import os
import sys
import tempfile

os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'v.db')
os.environ.setdefault('SECRET_KEY', 'test-viaje')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'scalpel'))
import app as A  # noqa: E402

OK, MAL = 0, []


def caso(nombre, cond, extra=''):
    global OK
    if cond:
        OK += 1
        print('  ✅ %s' % nombre)
    else:
        MAL.append(nombre)
        print('  🔴 %s %s' % (nombre, extra))


def cliente(usuario, clave):
    # ⚠️ Flask-Login cachea el usuario en `g`, que es del contexto de APP: con
    #    un solo app_context() abierto todo el script, la petición del SEGUNDO
    #    usuario corre como el PRIMERO. Hay que soltar ese caché antes de
    #    autenticar a otro — si no, el test de permisos miente en verde.
    from flask import g as _g
    _g.pop('_login_user', None)
    c = A.app.test_client()
    c.post('/login', data={'identifier': usuario, 'password': clave})
    _g.pop('_login_user', None)
    return c


with A.app.app_context():
    A.init_db()
    CLAVE = 'Zx9!wQ4mNp2r'
    jefe = A.User(username='jefe', email='j@x.com', email_verified=True,
                  is_admin=True, plan='premium')
    jefe.set_password(CLAVE)
    jefe.email_canonical = jefe.email
    pepe = A.User(username='pepe', email='p@x.com', email_verified=True,
                  plan='premium')
    pepe.set_password(CLAVE)
    pepe.email_canonical = pepe.email
    A.db.session.add_all([jefe, pepe])
    A.db.session.commit()

    print('── fuera de una petición, el mes es el REAL ──')
    import datetime as _dt
    real = _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m')
    caso('_current_season() sin contexto = mes de calendario',
         A._current_season() == real, A._current_season())

    print('── el admin viaja y TODO se mueve junto ──')
    c = cliente('jefe', CLAVE)
    r = c.post('/admin/demo/set', data={'scenario': 'season',
                                        'season': '2026-11'})
    caso('el salto a noviembre se acepta (redirige a /app)',
         r.status_code in (302, 303), r.status_code)

    h = c.get('/cosmetics').data.decode('utf-8')
    caso('la tienda ya pinta la TARJETA del marco Nile (antes escondida)',
         'plates/nile.svg' in h)
    caso('y el camo Nile aparece en el estante de ruleta',
         'camo_skin_nile' in h)
    caso('Colosseum (diciembre) SIGUE escondido — solo se adelanta un mes',
         'plates/colosseum.svg' not in h)

    j = c.get('/api/daily/tanda').get_json()
    caso('la API de la tanda responde el mes viajado',
         j.get('season') == '2026-11', j.get('season'))
    slugs = {i['slug'] for i in j.get('items', [])}
    caso('y entrega EXACTAMENTE el lote de Nile',
         slugs == {'nile', 'terminal', 'cur-nile', 'cur-chart',
                   'cur-compass', 'nile'}, str(slugs))

    print('── el viaje no escribe nada en la base ──')
    antes = A.CosmeticItem.query.count(), A.UserCosmetic.query.count()
    c.get('/cosmetics')
    c.get('/api/daily/tanda')
    caso('ni una fila nueva tras navegar viajando',
         (A.CosmeticItem.query.count(), A.UserCosmetic.query.count()) == antes)

    print('── volver al presente ──')
    c.post('/admin/demo/clear')
    h = c.get('/cosmetics').data.decode('utf-8')
    caso('al salir del demo, Nile vuelve a estar escondido',
         'plates/nile.svg' not in h)

    print('── candados ──')
    r = c.post('/admin/demo/set', data={'scenario': 'season',
                                        'season': '2026-13'})
    caso('un mes imposible (2026-13) se rechaza', r.status_code == 400,
         r.status_code)
    r = c.post('/admin/demo/set', data={'scenario': 'season',
                                        'season': "2026-11'; DROP--"})
    caso('un mes con basura se rechaza', r.status_code == 400, r.status_code)

    from flask import g as _g
    cp = cliente('pepe', CLAVE)
    _g.pop('_login_user', None)
    r = cp.post('/admin/demo/set', data={'scenario': 'season',
                                         'season': '2026-11'})
    _g.pop('_login_user', None)
    caso('un usuario NORMAL no puede viajar (403)', r.status_code == 403,
         r.status_code)
    _g.pop('_login_user', None)
    hp = cp.get('/cosmetics').data.decode('utf-8')
    caso('y su tienda sigue en el presente, sin Nile',
         'plates/nile.svg' not in hp)

print()
print('%d/%d' % (OK, OK + len(MAL)))
if MAL:
    print('FALLAN:', MAL)
    sys.exit(1)
