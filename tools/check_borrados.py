# -*- coding: utf-8 -*-
"""¿Le queda a alguna cuenta BORRADA un cobro vivo en PayPal? Preguntándoselo.

    cd /var/www/TRADINGBOT2.0 && venv/bin/python3 tools/check_borrados.py

🔴 POR QUÉ EXISTE. Cuando alguien elimina su cuenta, el sitio le pide a PayPal
que cancele su permiso de cobro y lo verifica antes de borrar nada. Pero esa
comprobación ocurre UNA vez, en ese instante. Si algo saliera mal después —un
permiso que PayPal reactiva, una fila que se nos escapó, un cambio en su API—
nadie se enteraría: el dueño de la cuenta ya no está para quejarse y no tiene
dónde mirar.

Esto cierra ese hueco sin necesidad de poder ensayarlo antes: recorre TODAS las
cuentas borradas, le pregunta a PayPal por cada permiso de cobro que tuvieran y
grita si alguno sigue pudiendo cobrar. Correrlo una vez al día convierte un
fallo invisible en un correo.

    venv/bin/python3 tools/check_borrados.py            # solo mira e informa
    venv/bin/python3 tools/check_borrados.py --cortar   # y cancela lo que viva

Códigos de salida: 0 todo limpio · 2 hay algo vivo · 3 no se pudo comprobar.
NO imprime credenciales.
"""
from __future__ import print_function

import json
import os
import sys
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_subs as CS          # noqa: E402  (token/api/leer_env ya resueltos)

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print('\n⛔ Falta SQLAlchemy en este intérprete.\n'
          '   En el VPS va con el Python del entorno:\n\n'
          '       cd /var/www/TRADINGBOT2.0 && venv/bin/python3 '
          'tools/check_borrados.py\n')
    sys.exit(3)

# Los dos únicos estados que PayPal puede cobrar. Una SUSPENDED cuenta porque
# se puede reanudar y volver a cobrar.
COBRAN = ('ACTIVE', 'SUSPENDED')


def cancelar(base, tk, sub_id):
    """POST .../cancel. Devuelve (ok, detalle)."""
    req = urllib.request.Request(
        base + '/v1/billing/subscriptions/%s/cancel' % sub_id,
        data=json.dumps({'reason': 'Cuenta eliminada (barrido)'}).encode(),
        method='POST')
    req.add_header('Authorization', 'Bearer ' + tk)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status < 300, 'HTTP %s' % r.status
    except urllib.error.HTTPError as e:
        # 422 = PayPal dice que ya no estaba activa: el resultado es el mismo.
        return e.code == 422, 'HTTP %s' % e.code
    except Exception as exc:
        return False, str(exc)


def filas(env):
    """Cuentas borradas y sus permisos de cobro, de la base del sitio."""
    url = (env.get('DATABASE_URL') or '').strip()
    if not url:
        url = 'sqlite:///' + os.path.join(RAIZ, 'scalpel', 'scalpel.db')
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    eng = create_engine(url)
    # "user" es palabra reservada en PostgreSQL: va entrecomillada.
    sql = text('SELECT u.id, u.username, u.deleted_at, s.id, s.provider_ref, '
               '       s.status, s.price, s.plan '
               '  FROM "user" u '
               '  JOIN plan_subscription s ON s.user_id = u.id '
               ' WHERE u.deleted_at IS NOT NULL '
               '   AND s.provider_ref IS NOT NULL '
               ' ORDER BY u.deleted_at DESC, s.id DESC')
    with eng.connect() as con:
        return list(con.execute(sql))


def main():
    cortar = '--cortar' in sys.argv
    env = CS.leer_env()
    cid = (env.get('PAYPAL_CLIENT_ID') or '').strip()
    sec = (env.get('PAYPAL_SECRET') or '').strip()
    entorno = (env.get('PAYPAL_ENV') or 'live').strip().lower()
    base = ('https://api-m.sandbox.paypal.com' if entorno == 'sandbox'
            else 'https://api-m.paypal.com')
    print('\n  CUENTAS BORRADAS · ¿queda algún cobro vivo?   (entorno: %s)'
          % entorno)
    print('  ' + '─' * 62)

    if not (cid and sec):
        print('\n  ⛔ Sin credenciales de PayPal no se puede comprobar nada.')
        print('     Y eso NO significa que no haya cobros vivos: significa')
        print('     que no lo sabemos. Pon PAYPAL_CLIENT_ID y PAYPAL_SECRET.')
        return 3

    try:
        registros = filas(env)
    except Exception as exc:
        print('\n  ⛔ No se pudo leer la base: %s' % exc)
        return 3

    if not registros:
        print('\n  ✅ Ninguna cuenta borrada tiene permisos de cobro '
              'registrados.')
        print('     (Nada que comprobar — no es lo mismo que "está mal".)\n')
        return 0

    tk, err = CS.token(base, cid, sec)
    if not tk:
        print('\n  ⛔ PayPal no dio token: %s' % err)
        return 3

    vivos, revisados, mudos = [], 0, 0
    ultimo = None
    for uid, quien, borrada, sid, ref, estado_local, precio, plan in registros:
        if ultimo != uid:
            fecha = str(borrada)[:19] if borrada else '—'
            print('\n  Cuenta #%s (%s) · borrada el %s' % (uid, quien, fecha))
            ultimo = uid
        revisados += 1
        code, data = CS.api(base, tk, '/v1/billing/subscriptions/%s' % ref)
        if code == 404:
            print('     ✅ %s · PayPal no la conoce (nunca se aprobó)' % ref)
            continue
        if code >= 300 or not data:
            mudos += 1
            print('     ⚠️  %s · PayPal no contestó (HTTP %s). NO se puede '
                  'dar por cortada.' % (ref, code))
            continue
        real = (data.get('status') or '?').upper()
        if real in COBRAN:
            vivos.append((uid, quien, sid, ref, real, precio, plan))
            print('     🔴 %s · SIGUE %s — $%.2f/mes (%s)'
                  % (ref, real, float(precio or 0), plan))
            if cortar:
                hecho, detalle = cancelar(base, tk, ref)
                print('        %s cancelación: %s'
                      % ('✅' if hecho else '⛔', detalle))
                if hecho:
                    vivos.pop()
        else:
            print('     ✅ %s · %s (no puede cobrar)' % (ref, real))

    print('\n  ' + '─' * 62)
    print('  Revisados %d permisos de %d cuentas borradas.'
          % (revisados, len({r[0] for r in registros})))
    if vivos:
        print('\n  🔴 %d SIGUEN PUDIENDO COBRAR. Eso es dinero saliendo de la'
              % len(vivos))
        print('     tarjeta de alguien que ya no puede ni entrar a quejarse.')
        for uid, quien, sid, ref, real, precio, plan in vivos:
            print('       · cuenta #%s (%s) → %s [%s]' % (uid, quien, ref, real))
        print('\n     Arreglarlo: volver a correr esto con --cortar, o')
        print('     cancelarlas a mano en el panel de PayPal.\n')
        return 2
    if mudos:
        print('\n  ⚠️  %d no se pudieron comprobar (PayPal no contestó).' % mudos)
        print('     Volver a correrlo más tarde: "no lo sé" no es "está bien".\n')
        return 3
    print('\n  ✅ Ninguna cuenta borrada puede recibir un cobro.\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
