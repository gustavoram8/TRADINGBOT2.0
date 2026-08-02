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
          'referred_by_code', 'referred_at', 'active_camo', 'owned_camos']

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
for idx in ('ix_user_referred_by_code',):
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
con.close()
print('  ok    columnas quitadas: %s' % ', '.join(quitadas))
print('  ok    y hay 1 usuario preexistente SIN alt_id (dispara el backfill)')
assert 'birth_date' not in cols

print('\n3 · arranco de nuevo contra esa base vieja  ← AQUÍ MORÍA PRODUCCIÓN')
paso3 = arrancar('la app arranca sobre una base sin las columnas nuevas')

print('\n4 · verifico que la migración las repuso y rellenó el alt_id')
con = sqlite3.connect(DB)
cols = {r[1] for r in con.execute('PRAGMA table_info(user)')}
faltan = [c for c in quitadas if c not in cols]
alt = con.execute("SELECT alt_id FROM user WHERE username='viejo'").fetchone()
con.close()
paso4a = not faltan
paso4b = bool(alt and alt[0])
print('  %s  las %d columnas volvieron%s' % ('ok  ' if paso4a else 'FALLA',
      len(quitadas), '' if paso4a else ' (faltan: %s)' % faltan))
print('  %s  el usuario viejo recibió su alt_id (%s)'
      % ('ok  ' if paso4b else 'FALLA', (alt[0][:12] + '…') if paso4b else 'vacío'))

print('\n5 · arranco una tercera vez (la migración tiene que ser idempotente)')
paso5 = arrancar('arranca de nuevo sin reventar ni duplicar columnas')

os.remove(DB)
todos = [paso1, paso3, paso4a, paso4b, paso5]
print('\n' + '=' * 60)
print('RESULTADO: %d de %d' % (sum(todos), len(todos)))
sys.exit(0 if all(todos) else 1)
