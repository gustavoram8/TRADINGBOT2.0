# -*- coding: utf-8 -*-
"""Datos de DEMO para mirar el panel de temporada lleno, y borrarlos después.

    python3 tools/demo_temporada.py sembrar
    python3 tools/demo_temporada.py limpiar

Es una herramienta de vista previa, NO una semilla de producción:

  * Las cuentas se reconocen por su correo en `@demo.invalid` — un dominio que
    por norma (RFC 2606) no existe ni puede existir, así que ningún correo de
    la aplicación puede salir hacia una de ellas ni por accidente.
  * `limpiar` borra por ese dominio, de modo que ninguna cuenta real puede
    quedar atrapada en el barrido por mucho que se parezca el nombre.
  * Las respuestas del daily se siembran a lo largo del mes EN CURSO, algunas
    con fecha posterior a hoy, porque el mes acaba de empezar y con dos días
    reales la tabla no se puede juzgar. Son fechas inventadas: por eso esto se
    limpia ANTES de que entre gente de verdad.
  * Los usuarios quedan en plan free y sin permisos: el ranking se calcula
    leyendo el registro de respuestas, así que el plan no cambia lo que se ve,
    y de paso no tocan ninguna métrica de ingresos ni reciben camos de plan.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scalpel'))
import app as A  # noqa: E402

DOMINIO = '@demo.invalid'

# (usuario, rango, mejor_racha, racha_viva, aciertos_del_mes, segundos_por_acierto)
# Marcus va en rango 8 a propósito: es la prueba de que el nombre encendido del
# salón de la fama (fuego) convive con la medalla dorada del rango sin chocar.
PERFILES = [
    ('marcus_dw',   8, 34, 12, 19, 11.2),
    ('valentina_r', 6, 21,  5, 19, 14.8),
    ('kenji_ito',   7, 15,  3, 15,  9.0),
    ('sofia_mv',    4,  9,  2, 11, 13.3),
    ('diego_ac',    3,  4,  0,  6, 20.1),
    ('nina_ost',    2,  2,  2,  4, 17.6),
]


def sembrar():
    ahora = datetime.now(timezone.utc)
    mes = ahora.strftime('%Y-%m')
    ayer = (ahora - timedelta(days=1)).strftime('%Y-%m-%d')
    creados = []
    for nombre, rango, mejor, viva, aciertos, seg in PERFILES:
        if A.User.query.filter_by(email=nombre + DOMINIO).first():
            print('  (ya existía: %s)' % nombre)
            continue
        u = A.User(username=nombre, email=nombre + DOMINIO, password_hash='x',
                   plan='free', email_verified=True, rank=rango,
                   xp=A.RANK_THRESHOLDS[rango - 1])
        A.db.session.add(u)
        A.db.session.flush()
        A.db.session.add(A.DailyQuizState(
            user_id=u.id, streak=viva, best_streak=mejor,
            best_streak_at=ahora - timedelta(days=mejor),
            last_played=ayer, total_correct=aciertos))
        for i in range(aciertos):
            A.db.session.add(A.DailyAnswerLog(
                user_id=u.id, day='%s-%02d' % (mes, i + 1), correct=True,
                seconds=seg, streak_after=i + 1))
        creados.append(nombre)
    A.db.session.commit()

    # Un post y un comentario: es la única forma de ver el chip de racha y el
    # nombre encendido, que viven en el foro y no en el panel.
    m = A.User.query.filter_by(email='marcus_dw' + DOMINIO).first()
    s = A.User.query.filter_by(email='sofia_mv' + DOMINIO).first()
    if m and not A.ForumPost.query.filter_by(user_id=m.id).first():
        p = A.ForumPost(
            user_id=m.id, title='[DEMO] Sweep del PDL y reclaim en la apertura',
            body='Post de demostración para revisar el diseño. Se borra con '
                 '"python3 tools/demo_temporada.py limpiar".')
        A.db.session.add(p)
        A.db.session.flush()
        if s:
            A.db.session.add(A.ForumComment(
                post_id=p.id, user_id=s.id,
                body='[DEMO] Comentario de prueba para ver el chip de racha.'))
        A.db.session.commit()

    print('\nSembrados: %s' % (', '.join(creados) or 'nada nuevo'))
    print('Mirá el panel 🏆 en el Daily, y el foro para el chip y el nombre encendido.')
    print('\n⚠️  Para borrar TODO esto:  python3 tools/demo_temporada.py limpiar')


def limpiar():
    users = A.User.query.filter(A.User.email.like('%' + DOMINIO)).all()
    if not users:
        print('No hay cuentas de demo que borrar.')
        return
    ids = [u.id for u in users]
    posts = A.ForumPost.query.filter(A.ForumPost.user_id.in_(ids)).all()
    for p in posts:
        A.ForumComment.query.filter_by(post_id=p.id).delete()
    A.ForumComment.query.filter(A.ForumComment.user_id.in_(ids)).delete(
        synchronize_session=False)
    for p in posts:
        A.db.session.delete(p)
    A.DailyAnswerLog.query.filter(A.DailyAnswerLog.user_id.in_(ids)).delete(
        synchronize_session=False)
    A.DailyQuizState.query.filter(A.DailyQuizState.user_id.in_(ids)).delete(
        synchronize_session=False)
    A.XPLog.query.filter(A.XPLog.user_id.in_(ids)).delete(synchronize_session=False)
    for u in users:
        A.db.session.delete(u)
    A.db.session.commit()
    # El caché del top-3 vive 60s en memoria del worker; se vacía solo.
    print('Borradas %d cuentas de demo y todo lo que colgaba de ellas.' % len(users))
    print('(El nombre encendido puede tardar hasta 1 minuto en apagarse: el '
          'podio se cachea 60 segundos.)')


if __name__ == '__main__':
    accion = sys.argv[1] if len(sys.argv) > 1 else ''
    if accion not in ('sembrar', 'limpiar'):
        print(__doc__)
        sys.exit(1)
    with A.app.app_context():
        (sembrar if accion == 'sembrar' else limpiar)()
