# -*- coding: utf-8 -*-
"""¿El vigilante de cuentas borradas ve lo que tiene que ver?

Se le pone delante una base con tres cuentas borradas —una con la suscripcion
ya cancelada, otra que PayPal no conoce, y una TERCERA que sigue ACTIVE— y se
comprueba que solo grita por la tercera, que el codigo de salida sirve para un
cron, y que --cortar la cancela de verdad.

    python3 tools/test_check_borrados.py
"""
from __future__ import print_function

import os
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RAIZ, 'tools', 'borrados.db')
if os.path.exists(DB):
    os.remove(DB)
os.environ['DATABASE_URL'] = 'sqlite:///' + DB
os.environ['PAYPAL_CLIENT_ID'] = 'ID-DE-MENTIRA-9f2a'
# secreto con una forma reconocible: si se colara en la salida,
# se veria. Con 'y' a secas el check no probaba nada (esa letra
# aparece en cada frase en espanol).
os.environ['PAYPAL_SECRET'] = 'SECRETO-DE-MENTIRA-7c41'
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

import app as A                  # noqa: E402
import check_subs as CS          # noqa: E402
import check_borrados as CB      # noqa: E402

ok = fallas = 0
ESTADO = {'I-MUERTA': 'CANCELLED', 'I-VIVA': 'ACTIVE',
          'I-SUSPENDIDA': 'SUSPENDED'}
canceladas = []


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


# ── PayPal simulado ───────────────────────────────────────────────────────
CS.token = lambda base, cid, sec: ('tok', None)


def falsa_api(base, tk, path):
    ref = path.rsplit('/', 1)[-1]
    if ref == 'I-DESCONOCIDA':
        return 404, {}
    if ref == 'I-MUDA':
        return 500, {}
    return 200, {'status': ESTADO.get(ref, 'ACTIVE')}


CS.api = falsa_api
CB.CS = CS


def falsa_cancel(base, tk, sub_id):
    canceladas.append(sub_id)
    ESTADO[sub_id] = 'CANCELLED'
    return True, 'HTTP 204'


CB.cancelar = falsa_cancel

# el aviso al dueno: se simula para no mandar correos de verdad
avisos = []
CB.gritar = lambda env, vivos: avisos.append(len(vivos)) or True

# ── la base ───────────────────────────────────────────────────────────────
with A.app.app_context():
    A.db.create_all()
    casos = [('muerta', 'I-MUERTA'), ('desconocida', 'I-DESCONOCIDA'),
             ('viva', 'I-VIVA'), ('suspendida', 'I-SUSPENDIDA'),
             ('muda', 'I-MUDA')]
    for nombre, ref in casos:
        u = A.User(username='del-' + nombre, email=nombre + '@x.invalid',
                   plan='free', email_verified=True,
                   deleted_at=datetime.now(timezone.utc))
        u.set_password('Zx9!wQ4mNp2r')
        A.db.session.add(u)
        A.db.session.flush()
        A.db.session.add(A.PlanSubscription(user_id=u.id, plan='premium',
                                            price=50, status='cancelled',
                                            provider_ref=ref))
    # y una cuenta VIVA con suscripcion activa: no debe aparecer nunca
    v = A.User(username='cliente-normal', email='n@x.invalid', plan='premium',
               email_verified=True)
    v.set_password('Zx9!wQ4mNp2r')
    A.db.session.add(v)
    A.db.session.flush()
    A.db.session.add(A.PlanSubscription(user_id=v.id, plan='premium',
                                        price=50, status='active',
                                        provider_ref='I-CLIENTE'))
    A.db.session.commit()

print('== solo mirar ==')
import io                                    # noqa: E402
from contextlib import redirect_stdout       # noqa: E402

buf = io.StringIO()
with redirect_stdout(buf):
    code = CB.main()
salida = buf.getvalue()
print(salida)

check('el código de salida avisa de que hay algo vivo (2, para el cron)',
      code == 2, code)
check('🔴 señala la suscripción ACTIVE', 'I-VIVA' in salida)
check('🔴 y también la SUSPENDED (se puede reanudar y cobrar)',
      'I-SUSPENDIDA' in salida)
check('da por buena la ya cancelada',
      'I-MUERTA' in salida and 'CANCELLED' in salida)
check('da por buena la que PayPal no conoce',
      'I-DESCONOCIDA' in salida and 'nunca se aprob' in salida)
check('avisa de la que no pudo comprobar, sin darla por cortada',
      'I-MUDA' in salida and 'NO se puede' in salida)
check('🔴 NO se mete con la suscripción de un cliente VIVO',
      'I-CLIENTE' not in salida)
check('🔴 al encontrar algo, AVISA al dueño (no solo lo escribe en el log)',
      avisos == [2], avisos)
check('no imprime credenciales',
      os.environ['PAYPAL_SECRET'] not in salida
      and os.environ['PAYPAL_CLIENT_ID'] not in salida)

print('== y ahora --cortar ==')
sys.argv = ['check_borrados.py', '--cortar']
buf = io.StringIO()
with redirect_stdout(buf):
    code2 = CB.main()
salida2 = buf.getvalue()
check('cancela las dos que podían cobrar',
      sorted(canceladas) == ['I-SUSPENDIDA', 'I-VIVA'], canceladas)
check('y al terminar ya no queda ninguna viva (solo la muda sin comprobar)',
      code2 == 3, code2)
check('con --cortar no vuelve a avisar (ya las apagó él mismo)',
      avisos == [2], avisos)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
if os.path.exists(DB):
    os.remove(DB)
sys.exit(1 if fallas else 0)
