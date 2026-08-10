# -*- coding: utf-8 -*-
"""El borrado de cuenta contra una base que SI exige las claves foraneas.

🔴 Por que existe este test. El primer test del borrado corria sobre SQLite,
que por defecto NO comprueba las claves foraneas. Produccion es PostgreSQL, y
alli si: borrar una publicacion del foro que tiene comentarios, reacciones o
guardados de OTRA gente es un FK violation y tumba el borrado entero con un
500 — con el cobro ya cancelado y la cuenta sin borrar.

Es exactamente la leccion del 2026-08-02 ("probarlo sobre SQLite creada desde
cero no prueba NADA sobre un deploy"), repitiendose en otro sitio.

Aqui se enciende `PRAGMA foreign_keys=ON` para que SQLite se comporte como
PostgreSQL, y se monta el caso realista: alguien que publico en el foro y
recibio comentarios, reacciones y guardados de otros.

    python3 tools/test_borrado_fk.py
"""
import os
import sys
from datetime import datetime, timezone

RUTA_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fk.db')
if os.path.exists(RUTA_DB):
    os.remove(RUTA_DB)
os.environ['DATABASE_URL'] = 'sqlite:///' + RUTA_DB
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
from flask import g                     # noqa: E402
from sqlalchemy import event            # noqa: E402
import app as A                         # noqa: E402


def _exigir_fks(dbapi_con, _):
    """Que SQLite se porte como PostgreSQL."""
    cur = dbapi_con.cursor()
    cur.execute('PRAGMA foreign_keys=ON')
    cur.close()


with A.app.app_context():
    event.listen(A.db.engine, 'connect', _exigir_fks)
    A.db.engine.dispose()          # que las conexiones nuevas lo cojan


CL = 'Zx9!wQ4mNp2r'
ok = fallas = 0
viva = {}


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def sesion(nombre):
    c = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    c.post('/login', data={'identifier': nombre, 'password': CL})
    c.set_cookie('scalpel_splash_ts', '1')
    return c


def leer(uid):
    with A.app.app_context():
        A.db.session.expire_all()
        return A.db.session.get(A.User, uid)


A._paypal_sub_cancel = lambda sub, motivo='': viva.__setitem__(
    sub.provider_ref, False) or True
A._sub_puede_cobrar = lambda sub: viva.get(sub.provider_ref, True)
A.PAYPAL_ENABLED = True

with A.app.app_context():
    A.db.create_all()
    con = A.db.session.execute(A.db.text('PRAGMA foreign_keys')).scalar()
    print('SQLite exige claves foráneas: %s' % ('SÍ' if con else 'NO'))
    for n in ('autora', 'vecino', 'okupa'):
        u = A.User(username=n, email=n + '@demo.invalid', plan='premium',
                   email_verified=True)
        u.email_canonical = u.email
        u.set_password(CL)
        A.db.session.add(u)
    A.db.session.commit()
    AID = A.User.query.filter_by(username='autora').first().id
    VID = A.User.query.filter_by(username='vecino').first().id

    # La autora publica; el vecino le comenta, reacciona y la guarda.
    p = A.ForumPost(user_id=AID, title='Mi análisis', body='cuerpo')
    A.db.session.add(p)
    A.db.session.flush()
    PID = p.id
    A.db.session.add(A.ForumComment(post_id=PID, user_id=VID, body='muy bueno'))
    A.db.session.add(A.ForumReaction(user_id=VID, post_id=PID, emoji='fire'))
    A.db.session.add(A.SavedPost(user_id=VID, post_id=PID))
    # y ella comenta en su propio hilo, con una respuesta del vecino debajo
    ca = A.ForumComment(post_id=PID, user_id=AID, body='gracias')
    A.db.session.add(ca)
    A.db.session.flush()
    A.db.session.add(A.ForumComment(post_id=PID, user_id=VID,
                                    parent_id=ca.id, body='de nada'))
    A.db.session.add(A.PlanSubscription(user_id=AID, plan='premium', price=50,
                                        status='active', provider_ref='I-FK'))
    A.db.session.commit()
    CID = ca.id

print('\n== la autora se da de baja y luego borra su cuenta ==')
c = sesion('autora')
r = c.post('/account/delete', data={'password': CL, 'confirm': 'CONFIRMAR'})
check('con la suscripción viva, borrar se niega (cancela primero)',
      leer(AID).deleted_at is None)
c.post('/account/cancel-plan')
r = c.post('/account/delete', data={'password': CL, 'confirm': 'CONFIRMAR'})
check('el borrado NO revienta (sin 500)', r.status_code in (302, 303),
      r.status_code)
u = leer(AID)
check('la cuenta queda eliminada', u is not None and u.deleted_at is not None,
      u and u.deleted_at)

print('\n== y el hilo del vecino sigue en pie ==')
with A.app.app_context():
    A.db.session.expire_all()
    post = A.db.session.get(A.ForumPost, PID)
    check('la publicación sigue existiendo (marcada como borrada)',
          post is not None and post.is_deleted, post and post.is_deleted)
    check('🔴 pero su texto SÍ desapareció (es lo que promete el aviso)',
          post is not None and not (post.body or '').strip()
          and not (post.title or '').strip(),
          post and (post.title, post.body))
    check('el comentario del VECINO sigue intacto',
          A.ForumComment.query.filter_by(user_id=VID, parent_id=None)
          .filter(A.ForumComment.body == 'muy bueno').count() == 1)
    check('su reacción sigue ahí',
          A.ForumReaction.query.filter_by(user_id=VID).count() == 1)
    check('y lo que había guardado no se le rompió',
          A.SavedPost.query.filter_by(user_id=VID).count() == 1)
    com = A.db.session.get(A.ForumComment, CID)
    check('el comentario de ELLA queda vacío y marcado',
          com is not None and com.is_deleted and not (com.body or '').strip(),
          com and com.body)
    check('y la respuesta que colgaba de él no se perdió',
          A.ForumComment.query.filter_by(parent_id=CID).count() == 1)

print('\n== el foro se sigue pudiendo abrir ==')
cv = sesion('vecino')
r = cv.get('/forum/feed')
check('el feed responde 200 después del borrado', r.status_code == 200,
      r.status_code)
r = cv.get('/forum/post/%d' % PID)
check('el hilo vaciado queda OCULTO (404), igual que cuando moderación '
      'retira una publicación — no revienta',
      r.status_code == 404, r.status_code)
r = cv.get('/forum/feed?feed=saved')
check('la lista de GUARDADOS del vecino se abre sin romperse',
      r.status_code == 200, r.status_code)
d = r.get_json() or {}
check('...y ya no le muestra el contenido borrado',
      not any((x.get('body') or '') == 'cuerpo'
              for x in (d.get('posts') or [])), d.get('posts'))

print('\n== el nombre "deleted_N" no puede secuestrarse ==')
with A.app.app_context():
    marca = A.db.session.get(A.User, AID).username
    print('   (marca usada: %r)' % marca)
    check('lleva un carácter que el registro NO permite, así que nadie '
          'puede ocuparlo de antemano',
          not A.USERNAME_RE.match(marca), marca)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
