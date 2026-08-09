# -*- coding: utf-8 -*-
"""Punto 17: tráfico simulado en el foro, y un intento serio de romperlo.

Levanta un foro con gente dentro —free, standard, premium, un silenciado, un
baneado y el admin—, les hace publicar, comentar, reaccionar, seguirse,
mandarse mensajes y crear comunidades, y después **intenta saltarse todas las
reglas una por una**.

No es una suite de "todo verde": es un INFORME. Cada regla se prueba desde
fuera, por HTTP, como lo haría un usuario con las herramientas del navegador
abiertas. Lo que aparezca en rojo es una regla evadible de verdad.

⚠️ El moderador por IA falla ABIERTO por diseño (sin clave, aprueba todo). Eso
es deliberado en la app —una caída del proveedor no puede dejar el foro
inservible— así que aquí se prueba lo que SÍ es local y determinista: el
prefiltro de groserías/spam, los contadores de intentos y el auto-silencio.

    python3 tools/simula_foro.py
"""
import os
import sys

os.environ.setdefault('DATABASE_URL', 'sqlite://')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
from flask import g            # noqa: E402
import app as A                # noqa: E402

CL = 'Zx9!wQ4mNp2r'
bien = roto = 0
HALLAZGOS = []


def ok(t, cond, detalle=''):
    """cond True = la regla aguantó. False = se pudo evadir."""
    global bien, roto
    if cond:
        bien += 1
        print('   ok      %s' % t)
    else:
        roto += 1
        print('   🔴 ROTO %s %s' % (t, detalle))
        HALLAZGOS.append('%s %s' % (t, detalle))


def cuenta(nombre, plan='standard', **kw):
    with A.app.app_context():
        u = A.User(username=nombre, email=nombre + '@demo.invalid', plan=plan,
                   email_verified=True, **kw)
        u.set_password(CL)
        A.db.session.add(u)
        A.db.session.commit()
        return u.id


def sesion(nombre):
    c = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    c.post('/login', data={'identifier': nombre, 'password': CL})
    return c


def publicar(c, titulo, cuerpo, community_id=None):
    d = {'title': titulo, 'body': cuerpo}
    if community_id:
        d['community_id'] = str(community_id)
    return c.post('/forum/post', data=d)


with A.app.app_context():
    A.db.create_all()

print('\n══ 1 · la gente entra ' + '═' * 40)
UID = {n: cuenta(n, p) for n, p in [
    ('ana', 'premium'), ('beto', 'standard'), ('caro', 'standard'),
    ('dani', 'free'), ('evo', 'standard')]}
UID['zulo'] = cuenta('zulo', 'standard', is_banned=True)
S = {n: sesion(n) for n in ('ana', 'beto', 'caro', 'dani', 'evo')}

r = A.app.test_client().post('/login', data={'identifier': 'zulo',
                                             'password': CL})
ok('un BANEADO no puede iniciar sesión',
   b'banned' in r.data or r.status_code == 200 and b'error' in r.data)

print('\n══ 2 · la puerta: quién puede entrar al foro ' + '═' * 18)
anon = A.app.test_client()
ok('sin sesión, el feed responde 401',
   anon.get('/forum/feed').status_code == 401)
ok('sin sesión, no se puede publicar',
   anon.post('/forum/post', data={'title': 'x' * 6, 'body': 'y' * 20})
   .status_code == 401)
for ruta, metodo in [('/forum/feed', 'get'), ('/forum/communities', 'get'),
                     ('/forum/dm/threads', 'get')]:
    r = getattr(S['dani'], metodo)(ruta)
    ok('un usuario FREE no entra a %s (403)' % ruta, r.status_code == 403,
       r.status_code)
ok('un usuario FREE no puede publicar',
   publicar(S['dani'], 'Mi primer post', 'Cuerpo suficientemente largo')
   .status_code == 403)
ok('...ni reaccionar',
   S['dani'].post('/forum/react', data={'emoji': 'fire', 'post_id': '1'})
   .status_code == 403)
ok('...ni mandar mensajes privados',
   S['dani'].post('/forum/dm/with/ana', json={'body': 'hola'}).status_code == 403)

print('\n══ 3 · tráfico normal ' + '═' * 40)
r = publicar(S['ana'], 'Order block en NQ',
             'Barrida de mínimos y desplazamiento; la zona de origen queda arriba.')
ok('un premium publica', r.status_code == 200, r.status_code)
PID = (r.get_json() or {}).get('post', {}).get('id')

r = S['beto'].post('/forum/post/%d/comment' % PID,
                   data={'body': 'Yo esperaría el retest antes de entrar.'})
ok('otro usuario comenta', r.status_code == 200, r.status_code)
CID = (r.get_json() or {}).get('comment', {}).get('id')

ok('reaccionar a un post ajeno funciona',
   S['caro'].post('/forum/react', data={'emoji': 'fire',
                                        'post_id': str(PID)}).status_code == 200)
ok('seguir a alguien funciona',
   S['beto'].post('/forum/follow', json={'username': 'ana', 'on': True})
   .status_code == 200)
ok('mandar un privado funciona',
   S['beto'].post('/forum/dm/with/ana', json={'body': '¿Tienes el gráfico?'})
   .status_code == 200)
r = S['ana'].post('/forum/communities', json={'name': 'Futuros NQ',
                                              'emoji': '📈'})
ok('crear una comunidad funciona', r.status_code == 200, r.status_code)
COM = (r.get_json() or {}).get('community', {}).get('id')

print('\n══ 4 · ahora INTENTO romperlo ' + '═' * 32)

print('\n· límites de publicación')
publicar(S['ana'], 'Segundo post del día', 'Cuerpo largo de prueba número dos.')
r = publicar(S['ana'], 'Tercer post del día', 'Cuerpo largo de prueba número tres.')
ok('el límite de %d posts/día aguanta' % A.DAILY_POST_LIMIT,
   r.status_code == 429, r.status_code)
r = publicar(S['beto'], 'ab', 'corto')
ok('un post demasiado corto se rechaza', r.status_code == 400, r.status_code)
r = publicar(S['beto'], 'T' * 400, 'B' * 20000)
ok('un post gigante NO revienta el servidor (se recorta)',
   r.status_code in (200, 400, 422, 429), r.status_code)
if r.status_code == 200:
    with A.app.app_context():
        p = A.ForumPost.query.order_by(A.ForumPost.id.desc()).first()
        ok('...y queda recortado en la base (título ≤160, cuerpo ≤8000)',
           len(p.title) <= 160 and len(p.body) <= 8000,
           '%d/%d' % (len(p.title), len(p.body)))

print('\n· el prefiltro local (el que no cuesta dinero)')
r = publicar(S['caro'], 'Titulo normal', 'aaaaaaaaaaaaaaaaaaaaaaa')
ok('el machaque de teclado se bloquea', r.status_code == 422, r.status_code)
r = publicar(S['caro'], 'Otro titulo', 'Mira esto !!!!!!!!!!!!!!!!!!!!')
ok('el spam de signos se bloquea', r.status_code == 422, r.status_code)

print('\n· propiedad del contenido')
r = S['beto'].post('/forum/post/%d/delete' % PID)
ok('nadie puede borrar el post de otro', r.status_code == 403, r.status_code)
r = S['beto'].post('/forum/comment/%d/delete' % CID)
ok('el autor SÍ puede borrar su propio comentario',
   r.status_code == 200, r.status_code)

print('\n· comunidades')
r = S['beto'].post('/forum/communities', json={'name': 'futuros nq'})
ok('un nombre repetido (en otras mayúsculas) se rechaza',
   r.status_code == 409, r.status_code)
r = S['beto'].post('/forum/communities', json={'name': 'ab'})
ok('un nombre demasiado corto se rechaza', r.status_code == 400, r.status_code)
r = publicar(S['beto'], 'Colandome en tu comunidad',
             'Publico aqui sin ser miembro, a ver si cuela.', community_id=COM)
ok('🔴 publicar en una comunidad SIN ser miembro se rechaza',
   r.status_code == 403, r.status_code)
r = S['ana'].post('/forum/community/%d/membership' % COM, json={'join': False})
ok('el creador no puede abandonar su propia comunidad',
   r.status_code == 400, r.status_code)
for i in range(4):
    r = S['evo'].post('/forum/communities', json={'name': 'Sala numero %d' % i})
ok('el tope de %d comunidades por usuario aguanta'
   % A.MAX_COMMUNITIES_PER_USER, r.status_code == 429, r.status_code)

print('\n· seguir y mensajes')
ok('nadie puede seguirse a sí mismo',
   S['beto'].post('/forum/follow', json={'username': 'beto', 'on': True})
   .status_code == 404)
ok('no se puede seguir a un fantasma',
   S['beto'].post('/forum/follow', json={'username': 'nadie', 'on': True})
   .status_code == 404)
ok('nadie puede mandarse un privado a sí mismo',
   S['beto'].post('/forum/dm/with/beto', json={'body': 'hola'}).status_code == 404)
ok('un privado vacío se rechaza',
   S['beto'].post('/forum/dm/with/ana', json={'body': '   '}).status_code == 400)
ult = None
for i in range(35):
    ult = S['caro'].post('/forum/dm/with/ana', json={'body': 'spam %d' % i})
ok('la avalancha de privados se corta (30/min)',
   ult.status_code == 429, ult.status_code)

print('\n· reacciones y XP')
ok('un emoji inventado se rechaza',
   S['beto'].post('/forum/react', data={'emoji': 'cohete', 'post_id': str(PID)})
   .status_code == 400)
ok('reaccionar sin decir a qué se rechaza',
   S['beto'].post('/forum/react', data={'emoji': 'fire'}).status_code == 400)

with A.app.app_context():
    antes = A.XPLog.query.filter_by(user_id=UID['ana'],
                                    source='forum_reaction').count()
# la MISMA persona quita y vuelve a poner la reacción muchas veces
for _ in range(6):
    S['caro'].post('/forum/react', data={'emoji': 'fire', 'post_id': str(PID)})
with A.app.app_context():
    despues = A.XPLog.query.filter_by(user_id=UID['ana'],
                                      source='forum_reaction').count()
ok('🔴 quitar y poner la reacción NO farmea XP al autor',
   despues == antes, 'antes %d, después %d' % (antes, despues))

with A.app.app_context():
    mio = A.XPLog.query.filter_by(user_id=UID['ana']).count()
S['ana'].post('/forum/react', data={'emoji': 'fire', 'post_id': str(PID)})
with A.app.app_context():
    ok('reaccionar a tu PROPIO post no te da XP',
       A.XPLog.query.filter_by(user_id=UID['ana']).count() == mio)

print('\n· el silenciado')
UID['muto'] = cuenta('muto', 'standard')
with A.app.app_context():
    from datetime import datetime, timezone, timedelta
    u = A.db.session.get(A.User, UID['muto'])
    u.muted_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    A.db.session.commit()
sm = sesion('muto')
ok('un silenciado no puede publicar',
   publicar(sm, 'Titulo valido', 'Cuerpo valido y suficientemente largo.')
   .status_code == 403)
ok('...ni mandar privados',
   sm.post('/forum/dm/with/ana', json={'body': 'hola'}).status_code == 403)
ok('...ni crear comunidades',
   sm.post('/forum/communities', json={'name': 'Sala del mudo'})
   .status_code == 403)
ok('pero SÍ puede leer el feed (no es una expulsión)',
   sm.get('/forum/feed').status_code == 200)

print('\n· qué se puede hacer SIN ser miembro de una comunidad')
# Esto NO se marca como roto: es una decisión de diseño. Las comunidades se
# presentan como salas públicas ("Join", "Open", "members") y en ningún texto
# se promete privacidad. Se deja medido para que el dueño lo confirme.
r = S['beto'].get('/forum/feed?community=%d' % COM)
leible = r.status_code == 200
r2 = S['caro'].post('/forum/post/%d/comment' % PID,
                    data={'body': 'Comento sin ser miembro de la sala.'})
print('   ·  leer el feed de una comunidad ajena: %s'
      % ('SÍ se puede' if leible else 'bloqueado'))
print('   ·  comentar en un post de esa comunidad: %s'
      % ('SÍ se puede' if r2.status_code == 200 else 'bloqueado'))
print('      (unirse hace falta solo para PUBLICAR. Nada en la interfaz')
print('       promete que sean privadas — decisión tuya si debe cambiar.)')

print('\n· inyección de HTML')
r = publicar(S['beto'], '<script>alert(1)</script>',
             'Cuerpo con <img src=x onerror=alert(1)> dentro del texto.')
if r.status_code == 200:
    with A.app.app_context():
        p = A.ForumPost.query.order_by(A.ForumPost.id.desc()).first()
        ok('el HTML se guarda TAL CUAL (no se destroza el texto del usuario)',
           '<script>' in p.title)
idx = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                        'scalpel', 'templates', 'index.html'),
           encoding='utf-8').read()
ok('🔴 y el cliente lo pinta con textContent, no con innerHTML',
   "body.textContent = p.body" in idx and "title.textContent = p.title" in idx)

print('\n══ INFORME ' + '═' * 50)
print('  %d reglas aguantaron · %d evadibles' % (bien, roto))
if HALLAZGOS:
    print('\n  Lo que hay que arreglar:')
    for h in HALLAZGOS:
        print('   · %s' % h)
else:
    print('  Ninguna regla se pudo evadir en esta pasada.')
sys.exit(1 if roto else 0)
