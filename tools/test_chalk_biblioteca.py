# -*- coding: utf-8 -*-
"""La biblioteca de pizarras: guardar, reabrir, y lo que NO se puede hacer.

Pedido del dueño (2026-08-12): *"debería de haber algo para poder guardar tus
proyectos… alguna especie de biblioteca o de archivos en donde vayan esos
proyectos, y que alguien pueda volver a editarlos, exportarlos a PDF,
presentar"*. Decisiones suyas: **20 pizarras** por cuenta y guardar = archivar
y empezar en blanco.

Lo que se comprueba aquí es sobre todo lo que NO debe pasar: que una cuenta no
vea ni toque las pizarras de otra, que el tope se imponga EN EL SERVIDOR (no
escondiendo un botón) y que un envío gigante se rechace.

    python3 tools/test_chalk_biblioteca.py
"""
from __future__ import print_function

import json
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp()
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tmp, 'chalk.db')
os.environ.setdefault('SECRET_KEY', 'test-chalk-lib')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                          # noqa: E402

CL = 'Zx9!wQ4mNp2r'
ok = fallas = 0


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def crea(nombre, plan):
    u = A.User.query.filter_by(username=nombre).first()
    if u is None:
        u = A.User(username=nombre, email='%s@demo.invalid' % nombre,
                   email_verified=True)
        A.db.session.add(u)
    u.set_password(CL)
    u.email_canonical = u.email
    u.plan = plan
    A.db.session.commit()
    return u.id


def entra(nombre):
    """⚠️ Cliente SIN `with`: con `with` Flask conserva el contexto de la
    última petición y su sesión de SQLAlchemy, y el usuario se queda congelado
    en su estado viejo (trampa ya documentada en CLAUDE.md)."""
    c = A.app.test_client()
    c.post('/login', data={'identifier': nombre, 'password': CL},
           follow_redirects=True)
    return c


with A.app.app_context():
    A.db.create_all()
    crea('chalkprem', 'premium')
    crea('chalkotro', 'premium')
    crea('chalkfree', 'free')

pre = entra('chalkprem')
otro = entra('chalkotro')
libre = entra('chalkfree')

TABLERO = json.dumps({'slides': [{'json': '{"objects":[]}', 'bg': 'dark'}], 'cur': 0})

# ── guardar y recuperar ──
r = pre.post('/api/chalk/boards', json={'name': 'Mi plan NQ', 'data': TABLERO,
                                        'slides': 3, 'thumb': 'data:image/png;base64,AAA'})
check('una cuenta premium puede guardar una pizarra', r.status_code == 200, r.status_code)
bid = (r.get_json() or {}).get('board', {}).get('id')

r = pre.get('/api/chalk/boards')
js = r.get_json() or {}
check('…y le aparece en su biblioteca con nombre y nº de diapositivas',
      len(js.get('boards', [])) == 1 and js['boards'][0]['name'] == 'Mi plan NQ'
      and js['boards'][0]['slides'] == 3, js)
check('la lista NO arrastra el contenido entero de cada pizarra',
      'data' not in js['boards'][0], js['boards'][0].keys())

r = pre.get('/api/chalk/boards/%d' % bid)
check('al abrirla vuelve EXACTAMENTE el mismo estado que se guardó',
      (r.get_json() or {}).get('board', {}).get('data') == TABLERO)

# ── de nadie más ──
check('otra cuenta no la ve en su biblioteca',
      len(((otro.get('/api/chalk/boards').get_json()) or {}).get('boards', [])) == 0)
check('otra cuenta no puede ABRIRLA (404, ni siquiera confirma que existe)',
      otro.get('/api/chalk/boards/%d' % bid).status_code == 404)
check('otra cuenta no puede BORRARLA',
      otro.delete('/api/chalk/boards/%d' % bid).status_code == 404)
check('otra cuenta no puede RENOMBRARLA',
      otro.post('/api/chalk/boards/%d/rename' % bid,
                json={'name': 'mía'}).status_code == 404)
check('…y sigue intacta tras los intentos',
      (pre.get('/api/chalk/boards/%d' % bid).get_json() or {})
      .get('board', {}).get('name') == 'Mi plan NQ')

# ── el Chalkboard es premium ──
check('una cuenta free no puede listar', libre.get('/api/chalk/boards').status_code == 403)
check('una cuenta free no puede guardar',
      libre.post('/api/chalk/boards', json={'data': TABLERO}).status_code == 403)
check('sin sesión tampoco (401)',
      A.app.test_client().get('/api/chalk/boards').status_code == 401)

# ── sobrescribir no crea una segunda ──
pre.post('/api/chalk/boards', json={'id': bid, 'name': 'Mi plan NQ v2',
                                    'data': TABLERO, 'slides': 5})
js = pre.get('/api/chalk/boards').get_json() or {}
check('guardar sobre una existente la ACTUALIZA, no la duplica',
      len(js['boards']) == 1 and js['boards'][0]['name'] == 'Mi plan NQ v2'
      and js['boards'][0]['slides'] == 5, js)

# ── el tope, impuesto en el SERVIDOR ──
for i in range(A.CHALK_MAX_BOARDS - 1):
    pre.post('/api/chalk/boards', json={'name': 'p%d' % i, 'data': TABLERO})
js = pre.get('/api/chalk/boards').get_json() or {}
check('caben exactamente %d pizarras' % A.CHALK_MAX_BOARDS,
      len(js['boards']) == A.CHALK_MAX_BOARDS, len(js['boards']))
r = pre.post('/api/chalk/boards', json={'name': 'una más', 'data': TABLERO})
check('la %d+1 se rechaza en el servidor, no escondiendo un botón'
      % A.CHALK_MAX_BOARDS,
      r.status_code == 409 and (r.get_json() or {}).get('error') == 'full',
      (r.status_code, r.get_json()))
check('…y el rechazo dice cuál es el tope, para poder explicarlo en pantalla',
      (r.get_json() or {}).get('max') == A.CHALK_MAX_BOARDS)
# 🔑 con la biblioteca llena, SOBRESCRIBIR una que ya es tuya tiene que seguir
#    funcionando: si no, llenarla te dejaría sin poder guardar tu trabajo
r = pre.post('/api/chalk/boards', json={'id': bid, 'name': 'sigo trabajando',
                                        'data': TABLERO})
check('con la biblioteca llena todavía se puede guardar SOBRE una existente',
      r.status_code == 200, r.status_code)

# ── borrar libera sitio ──
pre.delete('/api/chalk/boards/%d' % bid)
js = pre.get('/api/chalk/boards').get_json() or {}
check('borrar una deja hueco para otra', len(js['boards']) == A.CHALK_MAX_BOARDS - 1)
check('y la borrada ya no se puede abrir',
      pre.get('/api/chalk/boards/%d' % bid).status_code == 404)

# ── envíos absurdos ──
r = pre.post('/api/chalk/boards', json={'name': 'gigante',
                                        'data': 'x' * (A.CHALK_MAX_BYTES + 10)})
check('un envío por encima del tope de tamaño se rechaza (413)',
      r.status_code == 413, r.status_code)
r = pre.post('/api/chalk/boards', json={'name': 'vacía', 'data': ''})
check('una pizarra sin contenido se rechaza (400)', r.status_code == 400, r.status_code)
r = pre.post('/api/chalk/boards', json={'data': TABLERO})
check('sin nombre se guarda igual, con uno por defecto',
      r.status_code == 200 and (r.get_json() or {})['board']['name'] == 'Untitled',
      r.get_json())
# la miniatura no puede crecer sin freno
r = pre.post('/api/chalk/boards', json={'id': (r.get_json() or {})['board']['id'],
                                        'data': TABLERO, 'thumb': 'z' * 400000})
check('una miniatura enorme se recorta en vez de guardarse entera',
      len((r.get_json() or {})['board']['thumb']) <= A.CHALK_MAX_THUMB,
      len((r.get_json() or {})['board']['thumb']))

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
