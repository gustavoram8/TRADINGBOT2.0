#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crea (o reutiliza) el webhook de PayPal y deja su id puesto en la config.

    python3 tools/paypal_setup_webhook.py

POR QUÉ EXISTE
--------------
El webhook es el paso más fácil de equivocar de toda la configuración, y el
único cuyo fallo NO se nota: hay que elegir a mano quince eventos concretos de
una lista de más de cien, y si falta uno, ese aviso simplemente no llega nunca.
El caso peor es `PAYMENT.SALE.COMPLETED`: sin él se le cobra al cliente todos
los meses y su plan no se extiende, en silencio, sin error en ninguna parte.

Así que se hace por API y no con el ratón. Es idempotente: si ya existe un
webhook con esa misma URL, no crea otro — le actualiza los eventos y devuelve
el id que ya tenía.

Lee las credenciales de `scalpel/.env`, que es donde las dejó `set_paypal.py`,
así que no hay que volver a escribirlas ni exportarlas a mano.
"""
from __future__ import print_function

import base64
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(RAIZ, 'scalpel', '.env')

# Los quince avisos que el sitio sabe atender. Cada uno tiene un porqué:
EVENTOS = [
    # — compras sueltas (planes pagados de una vez, camos, marcos, cursores) —
    'CHECKOUT.ORDER.APPROVED',          # aprobó pero no capturamos: capturar
    'PAYMENT.CAPTURE.COMPLETED',        # el dinero es nuestro
    'PAYMENT.CAPTURE.DENIED',
    'PAYMENT.CAPTURE.REFUNDED',
    'PAYMENT.CAPTURE.REVERSED',
    'CUSTOMER.DISPUTE.CREATED',         # contracargo: avisa, nunca revoca solo
    # — suscripciones (los planes mensuales) —
    'BILLING.SUBSCRIPTION.ACTIVATED',
    'BILLING.SUBSCRIPTION.CANCELLED',
    'BILLING.SUBSCRIPTION.SUSPENDED',
    'BILLING.SUBSCRIPTION.EXPIRED',
    'BILLING.SUBSCRIPTION.PAYMENT.FAILED',   # el único fallo que nadie ve
    # — cada cobro mensual llega como una "sale", no como una "capture" —
    'PAYMENT.SALE.COMPLETED',           # 🔴 sin este, las renovaciones no valen
    'PAYMENT.SALE.DENIED',
    'PAYMENT.SALE.REFUNDED',
    'PAYMENT.SALE.REVERSED',
]


def leer_env():
    """Lo que dejó escrito `set_paypal.py`, sin tener que exportar nada."""
    datos = {}
    if os.path.exists(ENV):
        with open(ENV, encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith('#') and '=' in linea:
                    k, v = linea.split('=', 1)
                    datos[k.strip()] = v.strip().strip('"').strip("'")
    # Lo que venga por el entorno manda sobre el archivo.
    for k in ('PAYPAL_CLIENT_ID', 'PAYPAL_SECRET', 'PAYPAL_ENV', 'SITE_URL'):
        if os.environ.get(k):
            datos[k] = os.environ[k].strip()
    return datos


def api(base, tk, method, path, payload=None):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method)
    req.add_header('Authorization', 'Bearer ' + tk)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or '{}')
        except ValueError:
            return e.code, {}


def token(base, cid, secret):
    creds = base64.b64encode(('%s:%s' % (cid, secret)).encode()).decode()
    req = urllib.request.Request(base + '/v1/oauth2/token',
                                 data=b'grant_type=client_credentials',
                                 method='POST')
    req.add_header('Authorization', 'Basic ' + creds)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode())['access_token']


def main(argv):
    cfg = leer_env()
    cid, secret = cfg.get('PAYPAL_CLIENT_ID', ''), cfg.get('PAYPAL_SECRET', '')
    entorno = (cfg.get('PAYPAL_ENV') or 'live').lower()
    base = ('https://api-m.sandbox.paypal.com' if entorno == 'sandbox'
            else 'https://api-m.paypal.com')

    if not (cid and secret):
        sys.exit('No encuentro las credenciales de PayPal.\n'
                 'Corré antes:  python3 tools/set_paypal.py')

    sitio = (argv[0] if argv else cfg.get('SITE_URL', '')).rstrip('/')
    if not sitio.startswith('https://'):
        sys.exit('Hace falta la dirección pública con HTTPS.\n'
                 'Ponela con:  python3 tools/set_env.py SITE_URL=https://tu-dominio\n'
                 'o pasala aquí:  python3 tools/paypal_setup_webhook.py https://tu-dominio')
    url = sitio + '/webhook/paypal'

    print('Entorno: %s' % entorno.upper())
    print('Webhook: %s\n' % url)
    tk = token(base, cid, secret)

    # ¿Ya existe uno para esta misma URL? PayPal no deja dos con la misma
    # dirección, y además duplicarlos haría que cada aviso llegara dos veces.
    code, data = api(base, tk, 'GET', '/v1/notifications/webhooks')
    existente = None
    for w in (data.get('webhooks') or []):
        if (w.get('url') or '').rstrip('/') == url:
            existente = w
            break

    if existente:
        wid = existente['id']
        tenia = {e.get('name') for e in (existente.get('event_types') or [])}
        faltan = [e for e in EVENTOS if e not in tenia]
        if faltan:
            print('Ya existía, pero le faltaban %d eventos: %s'
                  % (len(faltan), ', '.join(faltan)))
            code, _ = api(base, tk, 'PATCH', '/v1/notifications/webhooks/' + wid,
                          [{'op': 'replace', 'path': '/event_types',
                            'value': [{'name': e} for e in EVENTOS]}])
            print('   %s' % ('corregidos' if code < 300 else
                             '⚠️ no se pudieron corregir (código %s)' % code))
        else:
            print('Ya existía y está completo.')
    else:
        code, data = api(base, tk, 'POST', '/v1/notifications/webhooks', {
            'url': url,
            'event_types': [{'name': e} for e in EVENTOS],
        })
        if code >= 300 or not data.get('id'):
            sys.exit('PayPal rechazó la creación del webhook: %s\n%s'
                     % (code, json.dumps(data, indent=2)[:800]))
        wid = data['id']
        print('Creado con los %d eventos.' % len(EVENTOS))

    print('\nWEBHOOK ID: %s' % wid)

    # Y se deja puesto donde la app lo lee, que es la mitad que se olvida.
    try:
        spec = importlib.util.spec_from_file_location(
            'se', os.path.join(RAIZ, 'tools', 'set_env.py'))
        se = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(se)
        se.main(['PAYPAL_WEBHOOK_ID=' + wid])
    except SystemExit:
        pass
    except Exception as exc:
        print('\n⚠️  No pude escribirlo solo (%s). Ponelo a mano con:' % exc)
        print('    python3 tools/set_env.py PAYPAL_WEBHOOK_ID=%s' % wid)

    # SIN `restart` detrás: al cambiar el conf, `update` ya reinicia el
    # proceso, y el segundo reinicio deja el sitio en 502 unos 40 s.
    print('\nPara que la app lo tome (SIN restart detrás — `update` ya reinicia):')
    print('  supervisorctl reread && supervisorctl update')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
