# -*- coding: utf-8 -*-
"""Crea en PayPal el producto y los dos planes mensuales. Se corre UNA vez.

    PAYPAL_CLIENT_ID=... PAYPAL_SECRET=... PAYPAL_ENV=sandbox \
        python3 tools/paypal_setup_subs.py

Imprime los dos ids que hay que pegar en la configuración del servidor:

    PAYPAL_PLAN_STANDARD=P-XXXXXXXXXXXX
    PAYPAL_PLAN_PREMIUM=P-XXXXXXXXXXXX

POR QUÉ EXISTE ESTO
-------------------
El papá del dueño tenía razón a medias: para las SUSCRIPCIONES sí hay que
crear productos en PayPal — un cobro que se repite necesita un plan con un id
fijo al que engancharse. Lo que no hacía falta era crearlos "uno por uno" para
todo: las compras sueltas (camos, marcos, cursores, carritos) no usan nada de
esto, se cobran con un importe y ya.

Y no hay que crearlos a mano en el panel: se crean por API, que es lo que hace
este archivo. Dos planes en total, no uno por precio — el descuento del socio
se manda al abrir cada suscripción (`pricing_scheme` sobrescrito), así un
cliente traído por un socio paga $40 cada mes sin que exista un plan "premium
con 20%" en PayPal.

ES IDEMPOTENTE
--------------
Busca antes de crear, por nombre. Correrlo dos veces no duplica nada: la
segunda vez reimprime los mismos ids. Eso importa porque un plan duplicado no
se puede borrar en PayPal, solo desactivar.

⚠️ SANDBOX Y LIVE SON DOS MUNDOS SEPARADOS. Los ids que salen con
`PAYPAL_ENV=sandbox` NO sirven en producción: hay que volver a correrlo con las
credenciales Live y pegar los ids nuevos. Es el mismo desajuste que ya cazó
`tools/check_paypal.py`.
"""
from __future__ import print_function

import base64
import json
import os
import sys
import urllib.error
import urllib.request

CLIENT = os.environ.get('PAYPAL_CLIENT_ID', '').strip()
SECRET = os.environ.get('PAYPAL_SECRET', '').strip()
ENV = os.environ.get('PAYPAL_ENV', 'live').strip().lower()
BASE = ('https://api-m.sandbox.paypal.com' if ENV == 'sandbox'
        else 'https://api-m.paypal.com')

PRODUCTO = 'Tradeable Academy — Membership'
# El precio de lista. Lo que se cobre de verdad puede ser menor (código de un
# socio), y eso se decide al abrir cada suscripción, no aquí.
IDS = {}          # se rellena al correr: {'PAYPAL_PLAN_STANDARD': 'P-…', …}

# ⚠️ El NOMBRE lleva versión a propósito. El script busca por nombre antes de
# crear, así que cambiar la estructura de los tramos exige un nombre nuevo: un
# plan de PayPal es INMUTABLE una vez creado. Los planes v1 (un solo tramo) se
# quedan donde están y las suscripciones abiertas con ellos siguen cobrando
# igual — no se toca ni una.
PLANES = [
    ('standard', 'Tradeable Academy — Standard (monthly) v2', '25.00',
     'PAYPAL_PLAN_STANDARD'),
    ('premium', 'Tradeable Academy — Premium (monthly) v2', '50.00',
     'PAYPAL_PLAN_PREMIUM'),
]


def token():
    creds = base64.b64encode(('%s:%s' % (CLIENT, SECRET)).encode()).decode()
    req = urllib.request.Request(BASE + '/v1/oauth2/token',
                                 data=b'grant_type=client_credentials',
                                 method='POST')
    req.add_header('Authorization', 'Basic ' + creds)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode())['access_token']


def api(tk, method, path, payload=None):
    req = urllib.request.Request(
        BASE + path,
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


def paginado(tk, path, clave):
    """Recorre TODAS las páginas. PayPal devuelve 10 por página por defecto, y
    quedarse con la primera es lo que hace que un script 'idempotente' cree un
    duplicado en cuanto hay unos cuantos elementos."""
    salida, pagina = [], 1
    while True:
        sep = '&' if '?' in path else '?'
        code, data = api(tk, 'GET', '%s%spage_size=20&page=%d' % (path, sep, pagina))
        if code >= 300:
            return salida
        lote = data.get(clave) or []
        salida.extend(lote)
        if len(lote) < 20:
            return salida
        pagina += 1


def main():
    if not (CLIENT and SECRET):
        sys.exit('Faltan PAYPAL_CLIENT_ID y PAYPAL_SECRET en el entorno.')
    print('Entorno: %s  (%s)' % (ENV.upper(), BASE))
    tk = token()

    prod_id = None
    for p in paginado(tk, '/v1/catalogs/products', 'products'):
        if p.get('name') == PRODUCTO:
            prod_id = p.get('id')
            print('Producto ya existía: %s' % prod_id)
            break
    if not prod_id:
        code, data = api(tk, 'POST', '/v1/catalogs/products', {
            'name': PRODUCTO,
            'description': 'Acceso mensual a la plataforma educativa.',
            'type': 'SERVICE',
            'category': 'EDUCATIONAL_AND_TEXTBOOKS',
        })
        if code >= 300:
            sys.exit('No se pudo crear el producto: %s %s' % (code, data))
        prod_id = data['id']
        print('Producto creado: %s' % prod_id)

    existentes = {pl.get('name'): pl.get('id')
                  for pl in paginado(tk, '/v1/billing/plans?product_id=' + prod_id,
                                     'plans')}

    resultado = []
    for _slug, nombre, precio, var in PLANES:
        if nombre in existentes:
            print('Plan ya existía: %s → %s' % (nombre, existentes[nombre]))
            resultado.append((var, existentes[nombre]))
            continue
        code, data = api(tk, 'POST', '/v1/billing/plans', {
            'product_id': prod_id,
            'name': nombre,
            'status': 'ACTIVE',
            # DOS tramos, y esta es la pieza que hace que un descuento pueda
            # CADUCAR. El primero es un ciclo suelto cuyo precio se sobrescribe
            # al abrir cada suscripción; el segundo es el precio de lista, para
            # siempre. Sin promoción los dos valen igual y el cliente no nota
            # nada. Con una promo general, el primer mes va rebajado y a partir
            # del segundo se cobra la tarifa normal — y el cliente lo aprobó
            # así desde el principio, que es lo que permite subirle el precio
            # sin pedirle permiso otra vez.
            'billing_cycles': [{
                'frequency': {'interval_unit': 'MONTH', 'interval_count': 1},
                'tenure_type': 'TRIAL',
                'sequence': 1,
                'total_cycles': 1,
                'pricing_scheme': {'fixed_price': {
                    'currency_code': 'USD', 'value': precio}},
            }, {
                'frequency': {'interval_unit': 'MONTH', 'interval_count': 1},
                'tenure_type': 'REGULAR',
                'sequence': 2,
                # 0 = para siempre, hasta que el cliente se dé de baja. Es
                # justo lo que se prometió: se renueva solo y él lo corta.
                'total_cycles': 0,
                'pricing_scheme': {'fixed_price': {
                    'currency_code': 'USD', 'value': precio}},
            }],
            'payment_preferences': {
                'auto_bill_outstanding': True,
                'setup_fee_failure_action': 'CANCEL',
                # Tras 3 intentos fallidos PayPal suspende la suscripción. Sin
                # tope reintentaría indefinidamente y el cliente vería cargos
                # rechazados en su banco durante semanas.
                'payment_failure_threshold': 3,
            },
            # Impuestos: no se declara ninguno. Si algún día hay que cobrarlos,
            # se añade aquí y NO en el precio, o el importe deja de coincidir
            # con lo que anuncia la web.
        })
        if code >= 300:
            sys.exit('No se pudo crear el plan %s: %s %s' % (nombre, code, data))
        print('Plan creado: %s → %s' % (nombre, data['id']))
        resultado.append((var, data['id']))

    # Se deja a la vista para quien importe este archivo (lo hace
    # `set_paypal.py`, para que configurar PayPal sea UN solo comando).
    global IDS
    IDS = dict(resultado)

    print('\n' + '=' * 60)
    print('Pegá estas dos líneas en la config del servidor (supervisor y .env):')
    print('=' * 60)
    for var, pid in resultado:
        print('%s=%s' % (var, pid))
    print('\nY acordate de PAYPAL_WEBHOOK_ID: sin él las renovaciones se cobran')
    print('pero el plan NO se extiende, porque el aviso del mes 2 en adelante')
    print('es lo único que llega (nadie vuelve a la web en una renovación).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
else:
    # Importado desde `set_paypal.py`: se corre igual, para que configurar
    # PayPal siga siendo un solo comando de cara al dueño.
    main()
