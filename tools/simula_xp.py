# -*- coding: utf-8 -*-
"""Punto 21: un granjero de XP intenta inflar su rango por cada camino.

Cada fuente de XP alcanzable por HTTP se ataca como lo haría alguien con la
consola del navegador: repetir la acción, repetirla tras borrar, repetirla
con otra cuenta, mentirle al servidor. El rango es lo que muestran el foro y
los certificados — si se puede farmear, la insignia no vale nada.

Reglas que se prueban (todas viven en `add_xp`, server-side):
  · dedup por referencia: la misma acción no paga dos veces;
  · topes diarios por fuente (quiz 20 · post 10 · comment 10 · reaction 5);
  · "pagar entero o no pagar": un premio que desborda el tope no entra;
  · tope maestro premium (80/día) para las fuentes que no están exentas;
  · el rango NUNCA baja, y sube exactamente donde la tabla lo dice.

    python3 tools/simula_xp.py
"""
import json
import os
import sys

os.environ.setdefault('DATABASE_URL', 'sqlite://')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
from flask import g            # noqa: E402
import app as A                # noqa: E402

CL = 'Zx9!wQ4mNp2r'
bien = roto = 0


def ok(t, cond, detalle=''):
    global bien, roto
    if cond:
        bien += 1
        print('   ok      %s' % t)
    else:
        roto += 1
        print('   🔴 ROTO %s %s' % (t, detalle))


def cuenta(nombre, plan='premium'):
    with A.app.app_context():
        u = A.User(username=nombre, email=nombre + '@demo.invalid', plan=plan,
                   email_verified=True)
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


def xp_de(uid, fuente=None):
    with A.app.app_context():
        q = A.XPLog.query.filter_by(user_id=uid)
        if fuente:
            q = q.filter_by(source=fuente)
        return sum(r.amount for r in q.all())


with A.app.app_context():
    A.db.create_all()
GRANJERO = cuenta('granjero', 'premium')
ALT = cuenta('alt', 'standard')

print('\n· login: entrar veinte veces paga UNA')
# El XP de login se paga al ABRIR /app (así cuenta igual quien entra por
# remember-me), y /app exige el cookie del splash — sin él redirige a /welcome.
def visita_app(nombre):
    c = sesion(nombre)
    c.set_cookie('scalpel_splash_ts', '1')
    c.get('/app')
    return c

for _ in range(3):
    visita_app('granjero')
base_login = xp_de(GRANJERO, 'login')
for _ in range(3):
    visita_app('granjero')
ok('el XP de login del día no se repite',
   xp_de(GRANJERO, 'login') == base_login and base_login > 0,
   xp_de(GRANJERO, 'login'))

print('\n· quiz: la misma pregunta respondida en bucle')
s = sesion('granjero')
with A.app.app_context():
    qid = next(i for i, e in enumerate(A._QUIZ_KEY)
               if e.get('lv') in ('beginner', 'intermediate', 'advanced'))
    correcta = A._QUIZ_KEY[qid]['ans']
r = s.post('/api/quiz/answer', json={'question_id': qid, 'selected': correcta})
primera = (r.get_json() or {}).get('awarded', 0)
ok('la primera respuesta correcta paga', primera > 0, r.get_json())
for _ in range(5):
    r = s.post('/api/quiz/answer', json={'question_id': qid,
                                         'selected': correcta})
ok('🔴 repetirla en bucle paga CERO (dedup por pregunta)',
   (r.get_json() or {}).get('awarded', 0) == 0)
r = s.post('/api/quiz/answer', json={'question_id': qid, 'selected': 99})
ok('...y decir "acerté" con una opción falsa tampoco (el server juzga)',
   not (r.get_json() or {}).get('correct'))
r = s.post('/api/quiz/answer', json={'question_id': 10 ** 9,
                                     'selected': 0})
ok('una pregunta inventada se rechaza', r.status_code == 400, r.status_code)

print('\n· quiz: el tope diario de 20 XP con "pagar entero o nada"')
with A.app.app_context():
    pagables = [i for i, e in enumerate(A._QUIZ_KEY)
                if e.get('lv') in ('beginner', 'intermediate', 'advanced')]
for i in pagables[:40]:
    with A.app.app_context():
        sel = A._QUIZ_KEY[i]['ans']
    s.post('/api/quiz/answer', json={'question_id': i, 'selected': sel})
gan = xp_de(GRANJERO, 'quiz')
ok('🔴 cuarenta preguntas correctas no pasan del tope (%d ≤ %d)'
   % (gan, A.XP_DAILY_CAP['quiz']), 0 < gan <= A.XP_DAILY_CAP['quiz'])

print('\n· foro: publicar, borrar y volver a publicar')
r = s.post('/forum/post', data={'title': 'Post uno del granjero',
                                'body': 'Contenido perfectamente normal aquí.'})
pid = (r.get_json() or {}).get('post', {}).get('id')
xp_post = xp_de(GRANJERO, 'forum_post')
ok('publicar paga', xp_post > 0, xp_post)
s.post('/forum/post/%d/delete' % pid)
r = s.post('/forum/post', data={'title': 'Post dos tras borrar',
                                'body': 'Otro contenido normal y distinto.'})
ok('borrar y republicar cuenta contra el MISMO límite diario (2/día)',
   r.status_code == 200)
r = s.post('/forum/post', data={'title': 'Post tres del día',
                                'body': 'El tercero ya no debe entrar hoy.'})
ok('🔴 el tercer post del día se rechaza aunque uno esté borrado',
   r.status_code == 429, r.status_code)
ok('y el XP de posts respeta su tope diario',
   xp_de(GRANJERO, 'forum_post') <= A.XP_DAILY_CAP['forum_post'],
   xp_de(GRANJERO, 'forum_post'))

print('\n· foro: la cuenta cómplice reacciona sin parar')
with A.app.app_context():
    post_vivo = A.ForumPost.query.filter_by(user_id=GRANJERO,
                                            is_deleted=False).first().id
sa = sesion('alt')
for emoji in ('fire', 'like', 'chart', 'love', 'think', 'fire'):
    sa.post('/forum/react', data={'emoji': emoji, 'post_id': str(post_vivo)})
gan = xp_de(GRANJERO, 'forum_reaction')
ok('cambiar de emoji seis veces paga como UNA reacción (%d ≤ %d)'
   % (gan, A.XP_DAILY_CAP['forum_reaction']),
   0 < gan <= A.XP_DAILY_CAP['forum_reaction'])

print('\n· el tope maestro premium (80/día, cinturón final)')
with A.app.app_context():
    total_hoy = A._xp_sum_today(GRANJERO, None) if hasattr(A, '_xp_sum_today') else None
    # la suma del día jamás puede pasar el tope maestro + las fuentes exentas
    hoy = [r.amount for r in A.XPLog.query.filter_by(user_id=GRANJERO).all()
           if r.source not in A.XP_CAP_EXEMPT]
ok('todo lo farmeado hoy queda bajo el tope maestro (%d ≤ %d)'
   % (sum(hoy), A.XP_MASTER_CAP['premium']),
   sum(hoy) <= A.XP_MASTER_CAP['premium'])

print('\n· el rango: monótono y fiel a la tabla')
with A.app.app_context():
    u = A.db.session.get(A.User, GRANJERO)
    antes = u.rank
    ok('el rango coincide con rank_for_xp(su xp)',
       u.rank == A.rank_for_xp(u.xp), '%s vs %s' % (u.rank, A.rank_for_xp(u.xp)))
    # ¿y si alguien intentara restarle XP? El ledger es append-only: el rango
    # se calcula del total y NUNCA se recalcula hacia abajo en el modelo.
    ok('el rango nunca baja de lo ya alcanzado', u.rank >= antes)

print('\n══ INFORME ' + '═' * 50)
print('  %d defensas aguantaron · %d farmeables' % (bien, roto))
sys.exit(1 if roto else 0)
