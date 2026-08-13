# -*- coding: utf-8 -*-
"""El arreglo de zonas horarias, probado contra un POSTGRESQL REAL en Berlín.

    venv/bin/python3 tools/test_horas_pg.py

Por qué existe: el bug de las fechas (+2 h) SOLO ocurre en PostgreSQL — al
insertar un instante CON zona en una columna sin zona, PostgreSQL lo convierte
a la zona de la sesión. SQLite no convierte nada, así que TODA la batería de
tests del repo, que corre sobre SQLite, era ciega a este fallo. Esta suite
levanta un PostgreSQL de usar y tirar con el servidor configurado en
**Europe/Berlin — la configuración exacta del VPS** — y prueba contra él:

  1. el mecanismo del bug, rojo/verde: la misma escritura llega +2 h con la
     sesión en Berlín y exacta con la sesión en UTC;
  2. que el engine de la app abre sus sesiones en UTC aunque el servidor
     esté en Berlín;
  3. el caso del dueño tal cual: publicar en el foro descuenta el cupo
     (2 → 1 → 0 → 429) y la fila queda guardada en hora UTC;
  4. la cuota del analizador: ventana DESLIZANTE de 24 h — el análisis vuelve
     exactamente 24 h después de gastarse, sin importar la zona del cliente;
  5. la transición: una fila vieja escrita al estilo antiguo (desplazada +2 h,
     o sea "en el futuro") BLOQUEA de más, nunca regala cuota;
  6. que los dos helpers gemelos (_as_utc / _aware) convierten de verdad.
"""
from __future__ import print_function

import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PGBIN = '/usr/lib/postgresql/16/bin'
PUERTO = 5544
CLAVE = 'Zx9!wQ4mNp2r'

OK = FALLOS = 0


def check(cond, texto):
    global OK, FALLOS
    print(('  ✅ ' if cond else '  ❌ ') + texto)
    if cond:
        OK += 1
    else:
        FALLOS += 1


def como_nobody(*args, **kw):
    """initdb/postgres se niegan a correr como root: se degradan a nobody."""
    base = ['setpriv', '--reuid', 'nobody', '--regid', 'nogroup',
            '--clear-groups'] if os.geteuid() == 0 else []
    return subprocess.run(base + list(args), capture_output=True, text=True, **kw)


def arranca_pg(d):
    os.makedirs(d)
    if os.geteuid() == 0:
        # mkdtemp crea el padre 0700 de root: nobody no podría ni ENTRAR.
        os.chmod(os.path.dirname(d), 0o755)
        subprocess.run(['chown', '-R', 'nobody:nogroup', d], check=True)
    r = como_nobody(os.path.join(PGBIN, 'initdb'), '-D', os.path.join(d, 'data'),
                    '-U', 'scalpel', '--auth=trust', '--no-sync')
    assert r.returncode == 0, r.stderr[-800:]
    with open(os.path.join(d, 'data', 'postgresql.conf'), 'a') as f:
        # 🔑 El servidor entero en hora de BERLÍN, como el VPS. Es lo que hace
        # que esta suite pueda ver el bug que SQLite no puede ver.
        f.write("\ntimezone = 'Europe/Berlin'\nlog_timezone = 'Europe/Berlin'\n"
                "listen_addresses = ''\nunix_socket_directories = '%s'\n"
                "port = %d\n" % (d, PUERTO))
    if os.geteuid() == 0:
        subprocess.run(['chown', '-R', 'nobody:nogroup', d], check=True)
    r = como_nobody(os.path.join(PGBIN, 'pg_ctl'), '-D', os.path.join(d, 'data'),
                    '-l', os.path.join(d, 'pg.log'), '-w', 'start')
    assert r.returncode == 0, r.stderr[-800:]
    import psycopg2
    con = psycopg2.connect(dbname='postgres', user='scalpel', host=d, port=PUERTO)
    con.autocommit = True
    con.cursor().execute('CREATE DATABASE horas')
    con.close()


def main():
    if not os.path.exists(os.path.join(PGBIN, 'initdb')):
        print('SKIP: no hay binarios de PostgreSQL en %s' % PGBIN)
        return 0
    d = os.path.join(tempfile.mkdtemp(), 'pg')
    arranca_pg(d)
    try:
        return corre(d)
    finally:
        como_nobody(os.path.join(PGBIN, 'pg_ctl'), '-D', os.path.join(d, 'data'),
                    '-m', 'immediate', 'stop')
        shutil.rmtree(os.path.dirname(d), ignore_errors=True)


def corre(d):
    import psycopg2

    print('\n══ 1 · el MECANISMO del bug, rojo/verde ════════════════════')
    ahora = datetime.now(timezone.utc)
    for opciones, nombre, espera_desfase in (
            (None, 'sesión en Berlín (código VIEJO)', 2 * 3600),
            ('-c timezone=utc', 'sesión en UTC (el arreglo)', 0)):
        kw = {'dbname': 'horas', 'user': 'scalpel', 'host': d, 'port': PUERTO}
        if opciones:
            kw['options'] = opciones
        con = psycopg2.connect(**kw)
        cur = con.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS demo (t timestamp)')
        cur.execute('DELETE FROM demo')
        cur.execute('INSERT INTO demo VALUES (%s)', (ahora,))
        cur.execute('SELECT t FROM demo')
        leido = cur.fetchone()[0].replace(tzinfo=timezone.utc)
        con.commit(); con.close()
        desfase = (leido - ahora).total_seconds()
        # Berlín es +2 en verano y +1 en invierno: se acepta cualquiera de los
        # dos para que la suite no caduque con el cambio de hora.
        bien = (abs(desfase - espera_desfase) < 5 or
                (espera_desfase and abs(desfase - 3600) < 5))
        check(bien, '%s → la escritura llega %+d min' % (nombre, desfase / 60))

    # ── la app, contra este PostgreSQL ──
    os.environ['DATABASE_URL'] = (
        'postgresql+psycopg2://scalpel@/horas?host=%s&port=%d' % (d, PUERTO))
    os.environ.setdefault('SECRET_KEY', 'horas-pg')
    sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
    import app as A
    A.moderate_forum_text = lambda t, kind='post': {'ok': True, 'category': 'ok', 'reason': ''}

    print('\n══ 2 · la sesión del ENGINE de la app ══════════════════════')
    with A.app.app_context():
        A.db.create_all()
        from sqlalchemy import text
        with A.db.engine.connect() as con:
            zona = con.execute(text('SHOW TimeZone')).scalar()
            servidor = con.execute(text(
                "SELECT setting FROM pg_settings WHERE name='TimeZone' "
                "AND source='configuration file'")).scalar()
        check(str(zona).upper() == 'UTC',
              'la sesión de la app va en UTC (sesión=%s)' % zona)
        print('     (el conf del servidor sigue diciendo Berlín: el arreglo es '
              'por sesión, no toca el servidor)')

        for n, plan in (('fori', 'standard'), ('prem', 'premium')):
            u = A.User(username=n, email=n + '@d.invalid', email_verified=True)
            u.set_password(CLAVE); u.email_canonical = u.email; u.plan = plan
            A.db.session.add(u)
        A.db.session.commit()
        uid_std = A.User.query.filter_by(username='fori').first().id
        uid_prem = A.User.query.filter_by(username='prem').first().id

    def sesion(n):
        c = A.app.test_client()
        c.post('/login', data={'identifier': n, 'password': CLAVE},
               follow_redirects=True)
        return c

    print('\n══ 3 · el caso del dueño: el cupo del foro, en PG ══════════')
    c = sesion('fori')
    restantes = lambda: (c.get('/forum/feed?page=1').get_json() or {}).get('posts_left_today')
    check(restantes() == 2, 'arranca con 2 restantes')
    valores = []
    for i in (1, 2):
        r = c.post('/forum/post', data={
            'title': 'Publicacion %d en postgres' % i,
            'body': 'Cuerpo suficientemente largo para el minimo.'},
            content_type='multipart/form-data')
        valores.append((r.get_json() or {}).get('posts_left_today'))
    check(valores == [1, 0], 'publicar descuenta 2 → 1 → 0 (respuestas: %s)' % valores)
    check(restantes() == 0, 'el feed también dice 0')
    r = c.post('/forum/post', data={'title': 'La tercera del dia',
                                    'body': 'Cuerpo suficientemente largo tambien.'},
               content_type='multipart/form-data')
    check(r.status_code == 429, 'la tercera da 429 (%s)' % r.status_code)
    with A.app.app_context():
        from sqlalchemy import text
        with A.db.engine.connect() as con:
            crudo = con.execute(text(
                'SELECT created_at FROM forum_post ORDER BY id DESC LIMIT 1')).scalar()
        desfase = abs((crudo.replace(tzinfo=timezone.utc)
                       - datetime.now(timezone.utc)).total_seconds())
        check(desfase < 120,
              'la fila queda guardada en hora UTC (desfase %d s) — antes '
              'llegaba +2 h' % desfase)

    print('\n══ 4 · la cuota del analizador: ventana DESLIZANTE de 24 h ══')
    def usage(cli):
        return cli.get('/api/usage').get_json() or {}

    with A.app.app_context():
        # standard: 1 análisis / 24 h
        A.db.session.add(A.UsageLog(
            user_id=uid_std,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=30)))
        A.db.session.commit()
    u = usage(c)
    check(u.get('used') == 1 and not u.get('allowed'),
          'standard con 1 análisis hace 30 min: bloqueado (used=%s)' % u.get('used'))
    resto = u.get('remaining_seconds') or 0
    check(abs(resto - (24 * 3600 - 30 * 60)) < 180,
          'y vuelve EXACTAMENTE a las 24 h del gasto: faltan %.1f h (esperado '
          '23.5) — da igual la zona del cliente' % (resto / 3600.0))
    with A.app.app_context():
        A.UsageLog.query.filter_by(user_id=uid_std).delete()
        A.db.session.add(A.UsageLog(
            user_id=uid_std,
            created_at=datetime.now(timezone.utc) - timedelta(hours=25)))
        A.db.session.commit()
    u = usage(c)
    check(u.get('allowed') and u.get('used') == 0,
          'el mismo análisis, con 25 h: ya no cuenta (fuera de la ventana)')

    cp = sesion('prem')
    with A.app.app_context():
        for k in range(5):
            A.db.session.add(A.UsageLog(
                user_id=uid_prem,
                created_at=datetime.now(timezone.utc) - timedelta(hours=k * 4)))
        A.db.session.commit()
    u = usage(cp)
    check(u.get('used') == 5 and not u.get('allowed'),
          'premium con 5 en la ventana: bloqueado')
    resto = u.get('remaining_seconds') or 0
    check(abs(resto - 8 * 3600) < 300,
          'y su próximo hueco abre cuando el MÁS VIEJO cumple 24 h '
          '(faltan %.1f h, esperado 8)' % (resto / 3600.0))

    print('\n══ 5 · transición: una fila VIEJA (estilo Berlín) nunca regala ══')
    # Se escribe como lo hacía el código viejo: sesión en Berlín → queda +2 h
    # adelantada y hoy se lee como "futuro".
    con = psycopg2.connect(dbname='horas', user='scalpel', host=d, port=PUERTO)
    cur = con.cursor()
    cur.execute('DELETE FROM usage_log WHERE user_id = %s', (uid_std,))
    cur.execute('INSERT INTO usage_log (user_id, created_at) VALUES (%s, %s)',
                (uid_std, datetime.now(timezone.utc)))
    con.commit(); con.close()
    u = usage(c)
    check(not u.get('allowed'),
          'la fila desplazada BLOQUEA (el error de transición nunca da '
          'cuota gratis; se paga con hasta 2 h extra de espera, una vez)')

    print('\n══ 6 · los helpers gemelos convierten de verdad ════════════')
    from datetime import timedelta as td
    berlin = timezone(td(hours=2))
    instante = datetime(2026, 8, 13, 1, 21, tzinfo=berlin)   # 23:21 UTC
    for nombre, fn in (('_as_utc', A._as_utc), ('_aware', A._aware)):
        v = fn(instante)
        check(v.hour == 23 and v.utcoffset() == td(0),
              '%s(01:21+02:00) → 23:21 UTC (antes devolvía la zona ajena '
              'tal cual)' % nombre)

    print('\nRESULTADO: %d/%d' % (OK, OK + FALLOS))
    return 0 if FALLOS == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
