# -*- coding: utf-8 -*-
"""Cerrar una comunidad del foro: quién puede, y qué se lleva por delante.

    venv/bin/python3 tools/test_borrar_comunidad.py

🔴 Existe porque el borrado NO EXISTÍA: una comunidad creada era eterna, no se
podía abandonar (`creator_cannot_leave`) y su nombre —único en todo el sitio—
quedaba bloqueado para siempre además de gastar uno de los 3 cupos de la
cuenta. Tres pruebas dejaban a esa cuenta sin poder crear ninguna más.

Lo que de verdad importa aquí no es "el botón borra", es:
  · que NADIE ajeno pueda cerrar la comunidad de otro;
  · que las publicaciones NO acaben en el foro general (eso publicaría ante
    todo el mundo lo escrito en un espacio privado);
  · que el borrado no reviente por CLAVE AJENA cuando hay comentarios y
    reacciones de OTRAS personas colgando de esos posts — el fallo del
    2026-08-10, que SQLite se traga y PostgreSQL no. Por eso el test enciende
    `PRAGMA foreign_keys=ON`.
"""
from __future__ import print_function
import os, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'c.db')
os.environ.setdefault('SECRET_KEY', 'comm')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
try:
    import app as A
except Exception as e:
    sys.exit('no se pudo cargar la app: %s' % e)
from datetime import datetime, timedelta, timezone
from sqlalchemy import event

# PostgreSQL SÍ impone las claves ajenas; SQLite solo si se le pide.
def _exigir_fks(dbapi_con, _):
    cur = dbapi_con.cursor()
    cur.execute('PRAGMA foreign_keys=ON')
    cur.close()

with A.app.app_context():
    event.listen(A.db.engine, 'connect', _exigir_fks)
    A.db.engine.dispose()          # que las conexiones nuevas lo cojan

# El moderador de IA no pinta nada en esta prueba y además saldría a la red:
# se sustituye por un "pasa" determinista (falla abierto igual en producción).
A.moderate_forum_text = lambda texto, kind='post': {'ok': True, 'category': None, 'reason': ''}

OK = FALLOS = 0
def check(t, c, extra=''):
    global OK, FALLOS
    print(('  ✅ ' if c else '  ❌ ') + t + (('  → %s' % extra) if extra and not c else ''))
    if c: OK += 1
    else: FALLOS += 1


def crear(username, admin=False):
    u = A.User(username=username, email=username + '@t.invalid',
               email_verified=True, is_admin=admin)
    u.set_password('Zx9!wQ4mNp2r')
    u.email_canonical = u.email
    u.plan = 'premium'
    u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    A.db.session.add(u)
    A.db.session.commit()
    return u


def cli(username):
    """Cliente NUEVO por usuario: `with test_client()` conserva el contexto de
    la última petición (y con él la caché de objetos de SQLAlchemy)."""
    c = A.app.test_client()
    c.post('/login', data={'identifier': username, 'password': 'Zx9!wQ4mNp2r'})
    return c


def main():
    with A.app.app_context():
        A.db.create_all()
        dueno = crear('duenio')
        otro = crear('otro')
        jefe = crear('jefe', admin=True)
        did, oid = dueno.id, otro.id

    cd, co, cj = cli('duenio'), cli('otro'), cli('jefe')

    print('\n══ 1 · quién puede cerrarla ══')
    r = cd.post('/forum/communities',
                json={'name': 'Sala de pruebas', 'description': 'd', 'emoji': '🧪'})
    cid = r.get_json()['community']['id']
    check('la comunidad se creó', r.status_code == 200)

    r = co.post('/forum/community/%d/delete' % cid, json={})
    check('un EXTRAÑO no puede cerrarla (403)', r.status_code == 403, r.status_code)
    with A.app.app_context():
        check('y sigue existiendo tras el intento',
              A.db.session.get(A.ForumCommunity, cid) is not None)

    r = cd.post('/forum/community/9999/delete', json={})
    check('una comunidad inexistente da 404', r.status_code == 404, r.status_code)

    print('\n══ 2 · se lleva sus publicaciones, y NO al foro general ══')
    # el dueño publica dentro; el otro entra y comenta y reacciona: así hay
    # filas de TERCEROS colgando, que es lo que rompía en PostgreSQL
    # ⚠️ /forum/post lee request.form, no JSON (lleva imagen adjunta)
    r = cd.post('/forum/post', data={'title': 'Mi idea privada',
                                     'body': 'texto que nadie de fuera debería ver',
                                     'community_id': str(cid)})
    check('el creador publica dentro', r.status_code == 200, r.get_data(as_text=True)[:120])
    pid = r.get_json()['post']['id']

    co.post('/forum/community/%d/membership' % cid, json={'join': True})
    cd.post('/forum/community/%d/requests' % cid, json={'username': 'otro', 'accept': True})
    r = co.post('/forum/post/%d/comment' % pid, data={'body': 'buen punto, gracias'})
    check('un tercero comenta dentro', r.status_code == 200)
    co.post('/forum/post/%d/react' % pid, json={'emoji': '🔥'})
    co.post('/forum/post/%d/save' % pid, json={})

    r = cd.post('/forum/community/%d/delete' % cid, json={})
    check('el creador SÍ la cierra (y no revienta por clave ajena)',
          r.status_code == 200, r.get_data(as_text=True)[:200])
    check('informa cuántas publicaciones se llevó',
          r.status_code == 200 and r.get_json().get('posts') == 1,
          r.get_json() if r.status_code == 200 else '')

    with A.app.app_context():
        check('la comunidad ya no existe',
              A.db.session.get(A.ForumCommunity, cid) is None)
        check('no quedan filas de miembros',
              A.ForumCommunityMember.query.filter_by(community_id=cid).count() == 0)
        p = A.db.session.get(A.ForumPost, pid)
        check('🔑 la publicación NO pasó al foro general', p.community_id is None
              and p.is_deleted)
        check('🔑 y su texto quedó VACÍO, no solo oculto',
              p.title == '' and p.body == '')

    r = cd.get('/forum/feed')
    cuerpo = r.get_data(as_text=True)
    check('el feed general no la enseña',
          'texto que nadie de fuera' not in cuerpo)

    print('\n══ 3 · el cupo y el nombre se liberan ══')
    ids = []
    for n in ('Uno', 'Dos', 'Tres'):
        rr = cd.post('/forum/communities', json={'name': n})
        ids.append(rr.get_json()['community']['id'])
    r = cd.post('/forum/communities', json={'name': 'Cuatro'})
    check('con 3 creadas, la cuarta se rechaza (429)', r.status_code == 429, r.status_code)

    cd.post('/forum/community/%d/delete' % ids[0], json={})   # cierra "Uno"
    r = cd.post('/forum/communities', json={'name': 'Cuatro'})
    check('🔑 tras cerrar una, vuelve a poder crear', r.status_code == 200, r.status_code)

    # y el nombre que quedó libre se puede volver a usar (en minúsculas, que
    # es como se compara: la unicidad no distingue mayúsculas)
    cd.post('/forum/community/%d/delete' % ids[1], json={})   # hueco para esta
    r = cd.post('/forum/communities', json={'name': 'uno'})
    check('🔑 y el nombre liberado se puede reutilizar', r.status_code == 200,
          r.get_data(as_text=True)[:120])

    print('\n══ 4 · el admin y el rastro ══')
    r = co.post('/forum/communities', json={'name': 'Del otro'})
    cid2 = r.get_json()['community']['id']
    r = cj.post('/forum/community/%d/delete' % cid2, json={})
    check('un admin puede cerrar la comunidad de otro', r.status_code == 200, r.status_code)
    with A.app.app_context():
        ev = A.AuditEvent.query.filter_by(event_type='forum_community_delete').all()
        check('queda rastro en la auditoría de cada cierre', len(ev) >= 2, len(ev))
        check('y el rastro dice de qué comunidad se trataba',
              any('Del otro' in (e.detail or '') for e in ev))

    print('\nRESULTADO: %d/%d' % (OK, OK + FALLOS))
    return 0 if not FALLOS else 1


if __name__ == '__main__':
    sys.exit(main())
