# -*- coding: utf-8 -*-
"""¿La base guarda las fechas en UTC, o en la hora del servidor?

    venv/bin/python3 tools/check_horas.py

Existe por un fallo real: el VPS está en Europa/Berlín, y al guardar un
instante CON zona en una columna SIN zona, PostgreSQL lo convierte a la zona
de la sesión. Una publicación de las 23:21 UTC quedaba fechada a las 01:21 del
día siguiente, así que no contaba para el cupo diario y el contador de
"publicaciones restantes" no bajaba nunca. Lo reportó el dueño y costó varias
vueltas verlo, porque el síntoma (un contador que no se mueve) no se parece en
nada a la causa (un desfase de zona horaria).

Compara tres relojes que TIENEN que coincidir:
  · la hora del proceso de Python
  · la hora de la base de datos
  · la fecha que quedó escrita en la última fila creada

Si la tercera va por delante de las otras dos, las fechas se están guardando
mal. No escribe nada: solo lee, y además ESCRIBE Y BORRA una fila de prueba
únicamente si se le pasa `--probar`.
"""
from __future__ import print_function

import os
import sys
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

try:
    import app as A
except Exception as e:                                    # pragma: no cover
    falta = 'No module named' in str(e)
    sys.exit('no se pudo cargar la app: %s%s' % (
        e, ('\n\n👉 Usa el intérprete del entorno:\n'
            '   venv/bin/python3 %s' % os.path.relpath(__file__, RAIZ))
        if falta else ''))

OK = FALLOS = 0


def check(cond, texto):
    global OK, FALLOS
    print(('  ✅ ' if cond else '  🔴 ') + texto)
    if cond:
        OK += 1
    else:
        FALLOS += 1


def main():
    ahora = datetime.now(timezone.utc)
    print('\n══ los relojes ═════════════════════════════════════════════')
    print('  proceso (UTC)   : %s' % ahora.strftime('%Y-%m-%d %H:%M:%S'))
    print('  proceso (local) : %s  [%s]'
          % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
             datetime.now().astimezone().tzname()))

    with A.app.app_context():
        motor = A.db.engine.url.get_backend_name()
        print('  base de datos   : %s' % motor)
        if motor.startswith('postgres'):
            from sqlalchemy import text
            with A.db.engine.connect() as con:
                zona = con.execute(text("SHOW TimeZone")).scalar()
                bd_ahora = con.execute(text("SELECT now()")).scalar()
                bd_naive = con.execute(
                    text("SELECT now()::timestamp without time zone")).scalar()
            print('  zona de la sesión: %s' % zona)
            print('  now() de la base : %s' % bd_ahora)
            print('  y sin zona       : %s' % bd_naive)
            check(str(zona).lower() in ('utc', 'etc/utc'),
                  'la sesión de la base va en UTC (es lo que asume el código)')
            desfase = abs((bd_naive.replace(tzinfo=timezone.utc) - ahora).total_seconds())
            check(desfase < 120,
                  'lo que la base escribiría en una columna sin zona coincide '
                  'con UTC (desfase %d s)' % desfase)
        else:
            print('  (SQLite no convierte zonas: este fallo solo se da en PostgreSQL)')

        print('\n══ la última fila escrita de verdad ════════════════════════')
        ultimo = (A.ForumPost.query.order_by(A.ForumPost.created_at.desc())
                  .first())
        if ultimo is None:
            print('  (no hay ninguna publicación en el foro todavía)')
        else:
            crudo = ultimo.created_at
            leido = A._as_utc(crudo)
            print('  publicación #%d' % ultimo.id)
            print('    guardado crudo : %s  (tzinfo=%s)' % (crudo, crudo.tzinfo))
            print('    leído como UTC : %s' % leido.strftime('%Y-%m-%d %H:%M:%S'))
            print('    ahora en UTC   : %s' % ahora.strftime('%Y-%m-%d %H:%M:%S'))
            futuro = (leido - ahora).total_seconds()
            check(futuro < 60,
                  'no está en el futuro (va %+d min respecto a ahora)'
                  % (futuro / 60))
            if futuro >= 60:
                print('       👉 Ese adelanto es la zona horaria del servidor. Mientras')
                print('          exista, las publicaciones de las últimas horas del día')
                print('          UTC cuentan para el día siguiente y no gastan cupo.')

        if '--probar' in sys.argv:
            print('\n══ prueba de escritura (crea y borra una fila) ═════════════')
            u = A.User.query.filter_by(is_admin=True).first()
            if u is None:
                print('  (no hay ninguna cuenta admin con la que probar)')
            else:
                p = A.ForumPost(user_id=u.id, title='__prueba de zona horaria__',
                                body='fila temporal de tools/check_horas.py')
                A.db.session.add(p)
                A.db.session.commit()
                A.db.session.refresh(p)
                leido = A._as_utc(p.created_at)
                d = abs((leido - datetime.now(timezone.utc)).total_seconds())
                print('    escrita y releída: %s (desfase %d s)'
                      % (leido.strftime('%Y-%m-%d %H:%M:%S'), d))
                check(d < 120, 'una fila NUEVA se guarda y se lee en UTC')
                A.db.session.delete(p)
                A.db.session.commit()
                print('    fila de prueba borrada.')

    print('\n%s' % ('  TODO EN ORDEN' if FALLOS == 0
                    else '  🔴 %d problema(s) de zona horaria' % FALLOS))
    print('')
    return 0 if FALLOS == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
