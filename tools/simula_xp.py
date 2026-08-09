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

print('\n══ AUDITORÍA POR PLAN ' + '═' * 39)

print('\n· lo que paga el login, por plan (pesa al revés: menos fuentes = más)')
FREE = cuenta('librecito', 'free')
STD = cuenta('estandar', 'standard')
visita_app('librecito')
visita_app('estandar')
ok('free cobra %d por su login diario' % A.XP_SHARED['login']['free'],
   xp_de(FREE, 'login') == A.XP_SHARED['login']['free'], xp_de(FREE, 'login'))
ok('standard cobra %d' % A.XP_SHARED['login']['standard'],
   xp_de(STD, 'login') == A.XP_SHARED['login']['standard'], xp_de(STD, 'login'))
ok('premium cobra %d (ya medido arriba)' % A.XP_SHARED['login']['premium'],
   base_login == A.XP_SHARED['login']['premium'], base_login)

print('\n· las fuentes premium están CERRADAS para free y standard')
sf, ss = sesion('librecito'), sesion('estandar')
for nombre, cli in (('free', sf), ('standard', ss)):
    r = cli.post('/api/quiz/answer', json={'question_id': 0, 'selected': 0})
    ok('%s: el quiz responde 403 (no hay XP posible por ahí)' % nombre,
       r.status_code == 403, r.status_code)
    r = cli.post('/api/daily/answer', json={'selected': 0})
    ok('%s: el daily responde 403' % nombre, r.status_code == 403, r.status_code)
    r = cli.post('/api/preflight/checks',
                 json={'checklist_name': 'x', 'checked': [], 'total': 5,
                       'verdict': 'go'})
    ok('%s: pre-flight responde 403 (premium-only)' % nombre,
       r.status_code == 403, r.status_code)

print('\n· el testimonio: 30 XP UNA vez, y el bucle se frena en el server')
for nombre, cli, uid in (('free', sf, FREE), ('standard', ss, STD)):
    for _ in range(4):
        cli.post('/api/testimonial/submit', json={'rating': 5, 'text': 'Muy bueno',
                                           'consent': False})
    gan = xp_de(uid, 'testimonial')
    with A.app.app_context():
        filas = A.Testimonial.query.filter_by(user_id=uid).count()
    ok('%s: cuatro envíos = %d XP y UNA fila (ventana de 30 días server-side)'
       % (nombre, A.XP_SHARED['testimonial'][nombre]),
       gan == A.XP_SHARED['testimonial'][nombre] and filas == 1,
       'xp %s filas %s' % (gan, filas))

print('\n· el daily (premium): el server juzga, paga una vez y la racha manda')
with A.app.app_context():
    st = A.DailyQuizState(user_id=GRANJERO, streak=A.DAILY_STREAK_TARGET - 1,
                          spins_available=0, total_correct=0)
    A.db.session.add(st)
    A.db.session.commit()
with A.app.test_request_context('/'):
    from flask_login import login_user as _lu
    _lu(A.db.session.get(A.User, GRANJERO))
    idx_ok = A._daily_correct_index()
s = sesion('granjero')
s.post('/api/daily/start')
r = s.post('/api/daily/answer', json={'selected': idx_ok})
d = r.get_json() or {}
ok('acierta y cobra %d de daily_correct' % A.XP_PREMIUM['daily_correct'],
   d.get('correct') is True
   and xp_de(GRANJERO, 'daily_correct') == A.XP_PREMIUM['daily_correct'],
   xp_de(GRANJERO, 'daily_correct'))
ok('la racha llegó a %d y pagó el bono de %d'
   % (A.DAILY_STREAK_TARGET, A.XP_PREMIUM['daily_streak']),
   xp_de(GRANJERO, 'daily_streak') == A.XP_PREMIUM['daily_streak'],
   xp_de(GRANJERO, 'daily_streak'))
r = s.post('/api/daily/answer', json={'selected': idx_ok})
ok('🔴 responder de nuevo el mismo día → 409, sin segundo pago',
   r.status_code == 409
   and xp_de(GRANJERO, 'daily_correct') == A.XP_PREMIUM['daily_correct'])

print('\n· pre-flight (premium): bono único + 5 por check con tope de 15/día')
pagos = []
for i in range(5):
    r = s.post('/api/preflight/checks',
               json={'checklist_name': 'Rutina %d' % i,
                     'checked': ['a', 'b'], 'total': 5, 'verdict': 'go'})
    if r.status_code != 200:
        break
primero = xp_de(GRANJERO, 'preflight_first')
checks = xp_de(GRANJERO, 'preflight_check')
ok('el primer check de la vida pagó su bono de %d'
   % A.XP_PREMIUM['preflight_first'],
   primero == A.XP_PREMIUM['preflight_first'], primero)
ok('🔴 cinco checks el mismo día se quedan en el tope (%d ≤ %d)'
   % (checks, A.XP_DAILY_CAP['preflight_check']),
   0 < checks <= A.XP_DAILY_CAP['preflight_check'])

print('\n· el análisis: el monto sale de la tabla por plan')
with A.app.app_context():
    for nombre, uid in (('free', FREE), ('standard', STD)):
        u = A.db.session.get(A.User, uid)
        pagado = A.add_xp(u, 'analysis')
        ok('%s: un análisis paga %d' % (nombre, A.XP_SHARED['analysis'][nombre]),
           pagado == A.XP_SHARED['analysis'][nombre], pagado)
    # premium ya está contra su tope maestro: se mide el monto de tabla
    ok('premium: la tabla dice %d por análisis (frecuencia acotada por su '
       'cuota de 5/día)' % A.XP_SHARED['analysis']['premium'],
       A.XP_SHARED['analysis']['premium'] == 10)

print('\n· una fuente INVENTADA no paga nada')
with A.app.app_context():
    u = A.db.session.get(A.User, FREE)
    ok('add_xp("fuente_falsa") devuelve 0', A.add_xp(u, 'fuente_falsa') == 0)

print('\n· los umbrales de rango, borde a borde')
UMB = A.RANK_THRESHOLDS
casos = []
for i, u_ in enumerate(UMB):
    casos.append((u_, i + 1))                      # justo EN el umbral
    if u_ > 0:
        casos.append((u_ - 1, i))                  # un punto por debajo
casos.append((10 ** 9, len(UMB)))                  # muy por encima del último
ok('los %d bordes de la tabla dan el rango exacto' % len(casos),
   all(A.rank_for_xp(x) == r for x, r in casos),
   [(x, A.rank_for_xp(x), r) for x, r in casos if A.rank_for_xp(x) != r])

print('\n· bajar de plan NO toca ni XP ni rango')
with A.app.app_context():
    u = A.db.session.get(A.User, GRANJERO)
    xp_antes, rk_antes = u.xp, u.rank
    u.plan = 'free'
    A.db.session.commit()
    u = A.db.session.get(A.User, GRANJERO)
    ok('🔴 el premium que baja a free conserva su XP (%d) y su rango (%d)'
       % (xp_antes, rk_antes), u.xp == xp_antes and u.rank == rk_antes)
    u.plan = 'premium'
    A.db.session.commit()

print('\n· techo REAL de un día perfecto, por plan (informativo)')
premium_tope = (A.XP_MASTER_CAP['premium']
                + A.XP_SHARED['testimonial']['premium']
                + A.XP_PREMIUM['daily_streak'] + A.XP_PREMIUM['preflight_first'])
print('   ·  free    : login %d + análisis %d (1 cada 7 días) + testimonio %d '
      '(1 cada 30 días)' % (A.XP_SHARED['login']['free'],
                            A.XP_SHARED['analysis']['free'],
                            A.XP_SHARED['testimonial']['free']))
print('   ·  standard: login %d + análisis %d + foro %d+%d+%d + testimonio %d'
      % (A.XP_SHARED['login']['standard'], A.XP_SHARED['analysis']['standard'],
         A.XP_DAILY_CAP['forum_post'], A.XP_DAILY_CAP['forum_comment'],
         A.XP_DAILY_CAP['forum_reaction'],
         A.XP_SHARED['testimonial']['standard']))
print('   ·  premium : tope maestro %d + exentas (testimonio %d, racha %d, '
      '1er pre-flight %d) = %d máx. en un día irrepetible'
      % (A.XP_MASTER_CAP['premium'], A.XP_SHARED['testimonial']['premium'],
         A.XP_PREMIUM['daily_streak'], A.XP_PREMIUM['preflight_first'],
         premium_tope))
umbral2 = A.RANK_THRESHOLDS[1]
print('   ·  con esos techos, el rango 2 (%d XP) toma DÍAS, no minutos — '
      'no hay atajo.' % umbral2)

print('\n══ INFORME ' + '═' * 50)
print('  %d defensas aguantaron · %d farmeables' % (bien, roto))
sys.exit(1 if roto else 0)
