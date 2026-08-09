# -*- coding: utf-8 -*-
"""Reproduce la caída de producción del 2026-08-02.

Simula una base que YA EXISTE sin las columnas nuevas (que es lo que pasa en
prod y nunca pasa en local, donde create_all() nace completa) y comprueba que
la app arranca igual.
"""
import os, sys, sqlite3, subprocess, textwrap

SCRATCH = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(SCRATCH, 'boot.db')
NUEVAS = ['birth_date', 'totp_secret', 'totp_confirmed_at', 'totp_backup',
          'referred_by_code', 'referred_at', 'active_camo', 'owned_camos',
          'active_frame', 'active_cursor', 'email_canonical']
# Columnas nuevas en OTRAS tablas: (tabla, columna, valor_de_backfill_esperado)
NUEVAS_OTRAS = [('daily_quiz_state', 'best_streak', None),
                # cambio de plan programado (2026-08-05)
                ('plan_subscription', 'pending_plan', None),
                ('plan_subscription', 'pending_price', None),
                ('plan_subscription', 'pending_at', None),
                # ensayos de sandbox fuera de Revenue (2026-08-05)
                ('order', 'is_test', None),
                # comunidades privadas (2026-08-09)
                ('forum_community_member', 'status', None)]

if os.path.exists(DB):
    os.remove(DB)

def arrancar(etiqueta):
    """Importa la app como lo hace gunicorn (init_db corre al importar)."""
    r = subprocess.run(
        [sys.executable, '-c',
         'import sys; sys.path.insert(0, "scalpel"); import app; print("BOOT_OK")'],
        capture_output=True, text=True, cwd=os.getcwd(),
        env={**os.environ, 'DATABASE_URL': 'sqlite:///' + DB})
    ok = 'BOOT_OK' in r.stdout
    print('  %s  %s' % ('ok  ' if ok else 'FALLA', etiqueta))
    if not ok:
        cola = (r.stderr or '').strip().splitlines()[-6:]
        print('      ' + '\n      '.join(cola))
    return ok

print('\n1 · base nueva (el caso local, el que siempre funcionó)')
paso1 = arrancar('la app arranca y crea la base desde cero')

print('\n2 · simulo PRODUCCIÓN: le quito a "user" las columnas del último release')
con = sqlite3.connect(DB)
quitadas = []
for idx in ('ix_user_referred_by_code', 'ix_user_email_canonical'):
    con.execute('DROP INDEX IF EXISTS %s' % idx)
for c in NUEVAS:
    try:
        con.execute('ALTER TABLE user DROP COLUMN %s' % c)
        quitadas.append(c)
    except Exception as e:
        print('      (no se pudo quitar %s: %s)' % (c, e))
con.commit()
cols = {r[1] for r in con.execute('PRAGMA table_info(user)')}
con.execute("INSERT INTO user (username, email, password_hash, plan, is_admin, "
            "email_verified, is_banned, xp, rank, rank_celebrated, "
            "first_preflight_xp, cancel_at_period_end, terms_version) "
            "VALUES ('viejo','viejo@t.local','x','free',0,1,0,0,1,0,0,0,1)")
con.commit()
quitadas_otras = []
for tabla, col, _ in NUEVAS_OTRAS:
    try:
        # ⚠️ `order` es palabra reservada: sin comillas el ALTER falla y el
        # test se salta ese caso EN SILENCIO — o sea que pasa sin probar nada.
        # SQLite tampoco deja soltar una columna INDEXADA: fuera el índice
        # primero, o el DROP falla y el caso se salta sin probarse.
        con.execute('DROP INDEX IF EXISTS ix_%s_%s' % (tabla, col))
        con.execute('ALTER TABLE "%s" DROP COLUMN %s' % (tabla, col))
        quitadas_otras.append((tabla, col))
    except Exception as e:
        print('      (no se pudo quitar %s.%s: %s)' % (tabla, col, e))
# una fila vieja con racha viva: el backfill debe copiarla a best_streak
uid = con.execute("SELECT id FROM user WHERE username='viejo'").fetchone()[0]
con.execute("INSERT INTO daily_quiz_state (user_id, streak, spins_available, "
            "total_correct) VALUES (?, 5, 0, 9)", (uid,))
con.commit()
con.close()
print('  ok    columnas quitadas: %s' % ', '.join(quitadas))
print('  ok    y de otras tablas: %s' % ', '.join('%s.%s' % t for t in quitadas_otras))
print('  ok    y hay 1 usuario preexistente SIN alt_id (dispara el backfill)')
assert 'birth_date' not in cols

print('\n3 · arranco de nuevo contra esa base vieja  ← AQUÍ MORÍA PRODUCCIÓN')
paso3 = arrancar('la app arranca sobre una base sin las columnas nuevas')

print('\n4 · verifico que la migración las repuso y rellenó el alt_id')
con = sqlite3.connect(DB)
cols = {r[1] for r in con.execute('PRAGMA table_info(user)')}
faltan = [c for c in quitadas if c not in cols]
alt = con.execute("SELECT alt_id FROM user WHERE username='viejo'").fetchone()
faltan_otras = []
for tabla, col in quitadas_otras:
    c2 = {r[1] for r in con.execute('PRAGMA table_info("%s")' % tabla)}
    if col not in c2:
        faltan_otras.append('%s.%s' % (tabla, col))
best = con.execute('SELECT best_streak FROM daily_quiz_state').fetchone()
canon = con.execute("SELECT email_canonical FROM user "
                    "WHERE username='viejo'").fetchone()
con.close()
paso4a = not faltan and not faltan_otras
paso4b = bool(alt and alt[0])
paso4c = bool(best and best[0] == 5)
# el backfill del correo canónico: sin él, el alias de una cuenta ANTERIOR
# al cambio no chocaría con nada (justo el caso del baneado con cuenta vieja)
paso4d = bool(canon and canon[0] == 'viejo@t.local')
print('  %s  las %d+%d columnas volvieron%s' % ('ok  ' if paso4a else 'FALLA',
      len(quitadas), len(quitadas_otras),
      '' if paso4a else ' (faltan: %s)' % (faltan + faltan_otras)))
print('  %s  el usuario viejo recibió su alt_id (%s)'
      % ('ok  ' if paso4b else 'FALLA', (alt[0][:12] + '…') if paso4b else 'vacío'))
print('  %s  la racha viva (5) quedó copiada a best_streak (%s)'
      % ('ok  ' if paso4c else 'FALLA', best[0] if best else '—'))
print('  %s  el correo canónico del usuario viejo quedó rellenado (%s)'
      % ('ok  ' if paso4d else 'FALLA', canon[0] if canon else '—'))

print('\n5 · arranco una tercera vez (la migración tiene que ser idempotente)')
paso5 = arrancar('arranca de nuevo sin reventar ni duplicar columnas')

# ── 6 · LOS 4 WORKERS A LA VEZ ────────────────────────────────────────────
# 🔴 Esto tumbó producción el 2026-08-09. gunicorn levanta 4 workers en
# paralelo y los cuatro corren init_db(): todos leen "la columna no existe",
# uno gana la carrera y hace el ALTER, y los otros tres lo repiten contra una
# tabla que ya la tiene. Sin try/except esa excepción sale de init_db() —que
# corre al IMPORTAR— y mata a los cuatro: 502 con la migración ya aplicada.
print("\n6 · el worker que PIERDE la carrera del ALTER (lo de anoche)")
con = sqlite3.connect(DB)
for idx in ('ix_user_email_canonical',):
    con.execute('DROP INDEX IF EXISTS %s' % idx)
soltadas = []
for tabla, col in (('user', 'email_canonical'),
                   ('forum_community_member', 'status')):
    try:
        con.execute('ALTER TABLE "%s" DROP COLUMN %s' % (tabla, col))
        soltadas.append('%s.%s' % (tabla, col))
    except Exception as e:
        print('      (no se pudo quitar %s.%s: %s)' % (tabla, col, e))
con.commit()
con.close()
print('  ok    columnas quitadas otra vez: %s' % ', '.join(soltadas))

# ⚠️ Lanzar 4 procesos y esperar que choquen NO reproduce nada: el arranque
# de Python tarda más que la migración, así que llegan en fila y el fallo no
# aparece. Se reproduce el estado EXACTO del worker perdedor: cree que la
# columna no existe (leyó antes) y la base ya la tiene.
guion = textwrap.dedent('''
    import sys
    sys.path.insert(0, "scalpel")
    import app
    from sqlalchemy import inspect as _insp_real
    for fn, tabla, col in (
            (app._migrate_forum_member_status_column,
             "forum_community_member", "status"),
            (app._migrate_user_email_canonical_column, "user", "email_canonical")):
        with app.app.app_context():
            class Ciego:
                """Un inspector que MIENTE: dice que la columna no está."""
                def __init__(s, real): s.r = real
                def get_table_names(s): return s.r.get_table_names()
                def get_columns(s, t):
                    cols = s.r.get_columns(t)
                    return [c for c in cols if not (t == tabla and c["name"] == col)]
            import sqlalchemy
            orig = sqlalchemy.inspect
            sqlalchemy.inspect = lambda x: Ciego(orig(x))
            try:
                fn()          # el worker perdedor repite el ALTER
            finally:
                sqlalchemy.inspect = orig
    print("PERDEDOR_SOBREVIVE")
''')
r6 = subprocess.run([sys.executable, '-c', guion], capture_output=True,
                    text=True, cwd=os.getcwd(),
                    env={**os.environ, 'DATABASE_URL': 'sqlite:///' + DB})
paso6 = 'PERDEDOR_SOBREVIVE' in r6.stdout
print('  %s  el worker que repite el ALTER NO se muere'
      % ('ok  ' if paso6 else 'FALLA'))
if not paso6:
    print('      ' + '\n      '.join((r6.stderr or '').strip().splitlines()[-5:]))

os.remove(DB)
todos = [paso1, paso3, paso4a, paso4b, paso4c, paso4d, paso5, paso6]
print('\n' + '=' * 60)
print('RESULTADO: %d de %d' % (sum(todos), len(todos)))
sys.exit(0 if all(todos) else 1)
