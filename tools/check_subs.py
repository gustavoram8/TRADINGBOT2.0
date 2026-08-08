# -*- coding: utf-8 -*-
"""¿Se van a cobrar solos los planes mensuales? Respuesta con pruebas.

    cd /var/www/TRADINGBOT2.0 && python3 tools/check_subs.py

Existe porque la pregunta "¿sirven de verdad las renovaciones?" no se puede
contestar esperando un mes a ver qué pasa. Lo que sí se puede es comprobar las
tres piezas de las que depende cada cobro, preguntándoselas a PayPal:

  1. las credenciales autentican, y en QUÉ entorno;
  2. los dos planes (Standard y Premium) existen ahí, están ACTIVOS y son
     mensuales sin límite de ciclos. Desde 2026-08 el plan bueno es el "v2"
     de DOS tramos (mes 1 sobrescribible + renovación sin fin): es lo que
     hace que una promo general caduque sola tras el primer mes. Un plan
     v1 (un solo tramo) sigue cobrando, pero convierte cualquier descuento
     en precio de por vida — este archivo lo distingue y lo avisa;
  3. el webhook apunta a este sitio por HTTPS y trae los eventos que hacen
     falta — sobre todo `PAYMENT.SALE.COMPLETED`, que es por donde llega cada
     cobro mensual. 🔴 En una renovación NADIE vuelve a la web, así que si ese
     aviso no llega, se cobra y el plan no se extiende. En silencio.

NO imprime credenciales. Se puede correr en sandbox y en live sin cambiar nada.

⚠️ SANDBOX Y LIVE SON DOS MUNDOS. Los ids de plan y el webhook de sandbox NO
sirven en producción: al pasar a live hay que volver a correr
`tools/set_paypal.py` y `tools/paypal_setup_webhook.py` con las credenciales
Live, y después ESTE archivo otra vez. El código no cambia; cambia la config.
"""
from __future__ import print_function

import base64
import json
import os
import sys
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Los que se necesitan para que un cobro mensual llegue y se aplique.
NECESARIOS_SUBS = [
    'PAYMENT.SALE.COMPLETED',
    'BILLING.SUBSCRIPTION.ACTIVATED',
    'BILLING.SUBSCRIPTION.CANCELLED',
    'BILLING.SUBSCRIPTION.PAYMENT.FAILED',
]

ok = avisos = fallos = 0


def bien(t):
    global ok
    ok += 1
    print('  ✅ %s' % t)


def ojo(t):
    global avisos
    avisos += 1
    print('  ⚠️  %s' % t)


def mal(t):
    global fallos
    fallos += 1
    print('  ⛔ %s' % t)


def leer_env():
    """Variables del shell + las que dejó escritas `set_paypal.py`."""
    datos = {}
    ruta = os.path.join(RAIZ, 'scalpel', '.env')
    try:
        with open(ruta, encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith('#') or '=' not in linea:
                    continue
                k, v = linea.split('=', 1)
                datos[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    datos.update({k: v for k, v in os.environ.items() if v})
    return datos


def api(base, tk, path):
    req = urllib.request.Request(base + path, method='GET')
    req.add_header('Authorization', 'Bearer ' + tk)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or '{}')
        except ValueError:
            return e.code, {}
    except Exception as exc:
        return 0, {'_error': str(exc)}


def token(base, cid, secret):
    creds = base64.b64encode(('%s:%s' % (cid, secret)).encode()).decode()
    req = urllib.request.Request(base + '/v1/oauth2/token',
                                 data=b'grant_type=client_credentials',
                                 method='POST')
    req.add_header('Authorization', 'Basic ' + creds)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode())['access_token'], None
    except Exception as exc:
        return None, str(exc)


def main():
    env = leer_env()
    cid = env.get('PAYPAL_CLIENT_ID', '').strip()
    secret = env.get('PAYPAL_SECRET', '').strip()
    entorno = env.get('PAYPAL_ENV', 'live').strip().lower()
    base = ('https://api-m.sandbox.paypal.com' if entorno == 'sandbox'
            else 'https://api-m.paypal.com')
    sitio = env.get('SITE_URL', '').strip().rstrip('/')

    print('\n══ 1 · credenciales ' + '═' * 40)
    print('  entorno declarado : %s' % entorno.upper())
    if not (cid and secret):
        mal('faltan PAYPAL_CLIENT_ID / PAYPAL_SECRET — sin esto no hay cobros')
        print('\nNada más que comprobar hasta que estén.')
        return 1
    tk, err = token(base, cid, secret)
    if not tk:
        mal('el par NO autentica contra %s (%s)' % (entorno, (err or '')[:80]))
        print('     Suele ser mezclar credenciales de un entorno con el otro.')
        print('     Diagnóstico fino: python3 tools/check_paypal.py')
        return 1
    bien('autentican en %s' % entorno.upper())

    print('\n══ 2 · los dos planes mensuales ' + '═' * 28)
    planes = {'Standard': env.get('PAYPAL_PLAN_STANDARD', '').strip(),
              'Premium': env.get('PAYPAL_PLAN_PREMIUM', '').strip()}
    vivos = {}
    for nombre, pid in planes.items():
        if not pid:
            mal('%s: sin id de plan → se venderá como PAGO ÚNICO, sin renovar'
                % nombre)
            continue
        code, data = api(base, tk, '/v1/billing/plans/' + pid)
        if code >= 300:
            mal('%s: PayPal no reconoce ese id en %s (HTTP %s) — ¿es de otro '
                'entorno?' % (nombre, entorno, code))
            continue
        estado = (data.get('status') or '').upper()

        def _tramo(c):
            freq = c.get('frequency') or {}
            return {'tenure': (c.get('tenure_type') or '').upper(),
                    'unidad': (freq.get('interval_unit') or '').upper(),
                    'cuenta': freq.get('interval_count'),
                    'total': c.get('total_cycles'),
                    'precio': ((c.get('pricing_scheme') or {})
                               .get('fixed_price') or {}).get('value')}

        info = [_tramo(c) for c in (data.get('billing_cycles') or [])]
        resumen = ' + '.join('%s %s×%s ciclos=%s $%s'
                             % (t['tenure'] or '?', t['cuenta'], t['unidad'],
                                t['total'], t['precio']) for t in info) or 'sin ciclos'
        if estado != 'ACTIVE':
            mal('%s: el plan NO está activo (%s · %s)' % (nombre, estado, resumen))
            continue
        mensual = lambda t: t['unidad'] == 'MONTH' and t['cuenta'] == 1  # noqa: E731

        if (len(info) == 2 and info[0]['tenure'] == 'TRIAL'
                and info[1]['tenure'] == 'REGULAR'):
            # v2: mes 1 (sobrescribible por suscripción) + renovación sin fin.
            t1, t2 = info
            malo = None
            if not (mensual(t1) and t1['total'] == 1):
                malo = 'el 1er tramo no es "un solo mes"'
            elif not (mensual(t2) and t2['total'] in (0, None)):
                malo = 'la renovación no es "mensual sin fin"'
            elif t1['precio'] != t2['precio']:
                # En el PLAN ambos tramos llevan el precio de lista; los
                # descuentos se sobrescriben al abrir cada suscripción.
                malo = 'los dos tramos del plan traen precios distintos'
            if malo:
                mal('%s: %s (%s)' % (nombre, malo, resumen))
                continue
            bien('%s: activo, v2 de DOS tramos (%s) — una promo general '
                 'caduca sola tras el mes 1' % (nombre, resumen))
        elif len(info) == 1 and mensual(info[0]) \
                and info[0]['total'] in (0, None):
            ojo('%s: plan v1 de UN tramo (%s) — cobra bien, pero cualquier '
                'descuento se vuelve precio DE POR VIDA. Arreglo: python3 '
                'tools/paypal_setup_subs.py (crea los v2 y guarda los ids '
                'solo)' % (nombre, resumen))
        else:
            mal('%s: estructura de ciclos que el sitio no espera (%s)'
                % (nombre, resumen))
            continue
        vivos[nombre] = pid
    if len(set(planes.values())) < len([v for v in planes.values() if v]):
        mal('¡los dos planes apuntan al MISMO id! Standard cobraría lo de '
            'Premium o al revés')

    print('\n══ 3 · el aviso de cada cobro (webhook) ' + '═' * 20)
    wid = env.get('PAYPAL_WEBHOOK_ID', '').strip()
    if not wid:
        mal('sin PAYPAL_WEBHOOK_ID: las suscripciones quedan APAGADAS a '
            'propósito (el sitio cae a pago único)')
    else:
        code, data = api(base, tk, '/v1/notifications/webhooks/' + wid)
        if code >= 300:
            mal('PayPal no reconoce ese webhook en %s (HTTP %s)' % (entorno, code))
        else:
            url = data.get('url') or ''
            print('     apunta a: %s' % url)
            if not url.startswith('https://'):
                mal('no es HTTPS — PayPal no entrega avisos por http')
            elif sitio and not url.startswith(sitio):
                ojo('no coincide con SITE_URL (%s): los avisos irían a otro '
                    'sitio' % sitio)
            else:
                bien('URL correcta y por HTTPS')
            tiene = {e.get('name') for e in (data.get('event_types') or [])}
            if '*' in tiene:
                bien('suscrito a TODOS los eventos')
            else:
                faltan = [e for e in NECESARIOS_SUBS if e not in tiene]
                if faltan:
                    mal('le faltan eventos: %s' % ', '.join(faltan))
                    print('     Arreglo: python3 tools/paypal_setup_webhook.py')
                else:
                    bien('trae los %d eventos que necesitan las renovaciones'
                         % len(NECESARIOS_SUBS))

    print('\n══ VEREDICTO ' + '═' * 47)
    subs_on = bool(vivos) and bool(wid) and fallos == 0
    for nombre in ('Standard', 'Premium'):
        if nombre in vivos and wid and fallos == 0:
            print('  %-9s se cobrará SOLO cada mes hasta que el cliente se dé '
                  'de baja.' % nombre)
        elif nombre in vivos and not wid:
            print('  %-9s abriría la suscripción, pero SIN webhook el cobro '
                  'del mes 2 no extendería el plan.' % nombre)
        else:
            print('  %-9s se vendería como un pago único, sin renovación.' % nombre)
    print('\n  %d bien · %d avisos · %d bloqueantes' % (ok, avisos, fallos))
    if entorno != 'live':
        print('\n  ⚠️  Esto es SANDBOX: dinero de mentira. Al pasar a Live hay '
              'que repetir\n      set_paypal.py y paypal_setup_webhook.py con '
              'las credenciales Live\n      (los ids de plan y el webhook NO '
              'cruzan de un entorno al otro) y\n      volver a correr este '
              'archivo. El código es el mismo.')
    return 0 if (fallos == 0 and subs_on) else 1


if __name__ == '__main__':
    sys.exit(main())
