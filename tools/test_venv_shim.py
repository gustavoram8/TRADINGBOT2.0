# -*- coding: utf-8 -*-
"""Que el script se relance con el interprete de la app cuando el del sistema
no tiene Flask — sin quedarse en bucle."""
import os, subprocess, sys, tempfile, textwrap

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('   %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

tmp = tempfile.mkdtemp()
# Un "python del sistema" de mentira que NO tiene flask: se consigue con un
# PYTHONPATH vacio? No — se simula un interprete que falla al importar app.
falso_venv = os.path.join(tmp, 'venv', 'bin')
os.makedirs(falso_venv)
py = os.path.join(falso_venv, 'python')
open(py, 'w').write('#!/bin/sh\necho "VENV-USADO $@"\n')
os.chmod(py, 0o755)

src = open('/home/user/TRADINGBOT2.0/tools/limpiar_pruebas.py', encoding='utf-8').read()
print('── El buscador de intérprete')
check('mira primero el command= de supervisor', "conf.d/*trader*.conf" in src)
check('y luego venv/.venv/env dentro del repo', "('venv', '.venv', 'env')" in src)
check('con guardia anti-bucle', "_YA_REINTENTADO" in src)
check('y un mensaje util si no lo encuentra', 'grep -n "^command="' in src)

print('\n── Se relanza de verdad')
mod = os.path.join(tmp, 'limpiar.py')
open(mod, 'w').write(src.replace("RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))",
                                 "RAIZ = %r" % tmp)
                        .replace("import app as A                                                # noqa: E402",
                                 "raise ModuleNotFoundError(\"No module named 'flask'\")"))
r = subprocess.run([sys.executable, mod], capture_output=True, text=True, timeout=60,
                   env={k: v for k, v in os.environ.items() if k != '_YA_REINTENTADO'})
check('se relanza con el python del venv', 'VENV-USADO' in r.stdout, r.stdout[:120] + r.stderr[:120])

print('\n── Si no hay venv, no entra en bucle')
os.remove(py)
r = subprocess.run([sys.executable, mod], capture_output=True, text=True, timeout=60,
                   env={k: v for k, v in os.environ.items() if k != '_YA_REINTENTADO'})
check('sale con un aviso claro', 'No encontré el entorno virtual' in r.stdout, r.stdout[:150])
check('y con codigo de error', r.returncode == 1, r.returncode)

import shutil; shutil.rmtree(tmp)
print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
