# -*- coding: utf-8 -*-
"""Reproduce el fallo del 2026-08-13: borrar la demo de un colaborador YA USADO."""
import os, sys, subprocess, tempfile

RAIZ = '/home/user/TRADINGBOT2.0'
DB = os.path.join(tempfile.mkdtemp(), 'demo.db')
ENV = {**os.environ, 'DATABASE_URL': 'sqlite:///' + DB, 'SECRET_KEY': 'demo'}

def corre(args):
    return subprocess.run([sys.executable, 'tools/simula_socio.py'] + args,
                          capture_output=True, text=True, cwd=RAIZ, env=ENV)

ok = fallos = 0
def check(c, t):
    global ok, fallos
    print(('  ✅ ' if c else '  ❌ ') + t)
    if c: ok += 1
    else: fallos += 1

r = corre(['--aplicar'])
check('listo' in r.stdout, 'la demo se crea')

# Simulo lo que pasó: alguien ENTRA con la cuenta → se le registra el
# dispositivo (y de paso un evento de auditoría y un registro de uso).
sim = '''
import sys; sys.path.insert(0, "scalpel")
import app as A
from datetime import datetime, timezone
with A.app.app_context():
    u = A.User.query.filter_by(username="demo_colab").first()
    A.db.session.add(A.KnownDevice(user_id=u.id, token_hash="x"*64,
                                   ua="Mozilla/5.0 (Macintosh)"))
    A.db.session.add(A.XPLog(user_id=u.id, amount=5, source="login", day=datetime.now(timezone.utc).date()))
    A.db.session.add(A.AuditEvent(user_id=u.id, event_type="login", detail="x"))
    A.db.session.commit()
    print("USADA")
'''
r = subprocess.run([sys.executable, '-c', sim], capture_output=True, text=True,
                   cwd=RAIZ, env=ENV)
check('USADA' in r.stdout, 'se simula que alguien la usó (dispositivo + XP + auditoría)')
if 'USADA' not in r.stdout:
    print(r.stderr[-800:])

r = corre(['--borrar', '--aplicar'])
check('borrada entera' in r.stdout, 'y AHORA se borra sin reventar  ← aquí fallaba')
if 'borrada entera' not in r.stdout:
    print(r.stdout[-500:]); print(r.stderr[-900:])
else:
    dep = [l for l in r.stdout.splitlines() if 'dependientes' in l]
    print('     ' + (dep[0].strip() if dep else '(sin dependientes)'))

ver = '''
import sys; sys.path.insert(0, "scalpel")
import app as A
with A.app.app_context():
    print("QUEDA",
          A.User.query.filter_by(username="demo_colab").count(),
          A.PromoCode.query.filter_by(code="DEMO20").count(),
          A.SaleBreakdown.query.filter_by(partner="Demo Colaborador").count(),
          A.KnownDevice.query.count(), A.XPLog.query.count())
'''
r = subprocess.run([sys.executable, '-c', ver], capture_output=True, text=True,
                   cwd=RAIZ, env=ENV)
linea = [l for l in r.stdout.splitlines() if l.startswith('QUEDA')]
check(bool(linea) and linea[0] == 'QUEDA 0 0 0 0 0',
      'no queda ni rastro: cuenta, código, ventas, dispositivo ni XP (%s)'
      % (linea[0] if linea else '?'))

r = corre(['--borrar', '--aplicar'])
check('no hay nada' in r.stdout, 'repetir el borrado no revienta')

print('\nRESULTADO: %d/%d' % (ok, ok + fallos))
sys.exit(0 if not fallos else 1)
