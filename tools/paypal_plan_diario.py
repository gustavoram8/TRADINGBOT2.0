# -*- coding: utf-8 -*-
"""Un plan de PRUEBA que se cobra cada DÍA, para ver una renovación de verdad.

    PAYPAL_ENV=sandbox python3 tools/paypal_plan_diario.py crear
    PAYPAL_ENV=sandbox python3 tools/paypal_plan_diario.py apagar

POR QUÉ EXISTE
--------------
"¿Funcionan de verdad las renovaciones?" no se puede contestar del todo con
avisos simulados: eso prueba NUESTRA mitad (que al llegar el aviso el plan se
extiende, que un aviso repetido no regala un mes, que la fecha que se enseña
es la de PayPal). La otra mitad —que PayPal cobre solo cuando toca y que su
aviso llegue firmado hasta nuestro servidor— solo se ve ocurriendo.

Y ocurre una vez al mes. Con un plan de ciclo DIARIO ocurre mañana: se compra
hoy, y en ~24 h PayPal cobra por su cuenta y manda `PAYMENT.SALE.COMPLETED`
sin que nadie toque el navegador. Que es exactamente lo que hay que probar,
porque en una renovación NADIE vuelve a la web.

CÓMO SE USA
-----------
 1. `crear` → imprime un id de plan de prueba (ciclo diario, $1).
 2. Poner ese id en `PAYPAL_PLAN_STANDARD` (supervisor + scalpel/.env) y
    reiniciar. Ojo: a partir de ahí, comprar Standard usa el plan de prueba.
 3. Comprar Standard con una cuenta sandbox de comprador.
 4. Al día siguiente, mirar:
        grep -i "subscription_charge" en /admin → pestaña Audit
        o: python3 tools/diagnostico_compra.py <usuario>
    Debe haber un pedido NUEVO, pagado, sin que nadie volviera al sitio.
 5. `apagar` desactiva el plan de prueba, y se devuelve `PAYPAL_PLAN_STANDARD`
    a su id real (`tools/paypal_setup_subs.py` lo reimprime).

⚠️ SOLO EN SANDBOX. El script se niega a correr con `PAYPAL_ENV=live`: un plan
diario en producción le cobraría a un cliente todos los días.
⚠️ El importe del cobro lo fija NUESTRO servidor al abrir la suscripción
(`pricing_scheme` sobrescrito), así que el cliente de prueba pagará los $25 de
Standard, no el $1 del plan. Lo que cambia es el RELOJ, que es lo que se quiere
acelerar.
⚠️ Nuestro código sumará 30 días de acceso por cada cobro (el pedido dice
'monthly'). Es lo esperado: lo que se está probando es que el cobro llegue y se
aplique, no la aritmética del calendario.
"""
from __future__ import print_function

import base64
import json
import os
import sys
import urllib.error
import urllib.request

NOMBRE_PRODUCTO = 'Tradeable Academy — Membership'
NOMBRE_PLAN = 'PRUEBA DIARIA — no vender (Tradeable Academy)'


def leer_env():
    datos = {}
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(raiz, 'scalpel', '.env'), encoding='utf-8') as f:
            for l in f:
                l = l.strip()
                if l and not l.startswith('#') and '=' in l:
                    k, v = l.split('=', 1)
                    datos[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    datos.update({k: v for k, v in os.environ.items() if v})
    return datos


ENV = leer_env()
ENTORNO = ENV.get('PAYPAL_ENV', 'live').strip().lower()
BASE = ('https://api-m.sandbox.paypal.com' if ENTORNO == 'sandbox'
        else 'https://api-m.paypal.com')


def token():
    creds = base64.b64encode(('%s:%s' % (ENV.get('PAYPAL_CLIENT_ID', ''),
                                         ENV.get('PAYPAL_SECRET', ''))).encode()).decode()
    req = urllib.request.Request(BASE + '/v1/oauth2/token',
                                 data=b'grant_type=client_credentials', method='POST')
    req.add_header('Authorization', 'Basic ' + creds)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode())['access_token']


def api(tk, metodo, ruta, cuerpo=None):
    req = urllib.request.Request(
        BASE + ruta,
        data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
        method=metodo)
    req.add_header('Authorization', 'Bearer ' + tk)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            cruda = r.read().decode()
            return r.status, (json.loads(cruda) if cruda else {})
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or '{}')
        except ValueError:
            return e.code, {}


def paginado(tk, ruta, clave):
    salida, pagina = [], 1
    while True:
        sep = '&' if '?' in ruta else '?'
        code, data = api(tk, 'GET', '%s%spage_size=20&page=%d' % (ruta, sep, pagina))
        if code >= 300:
            return salida
        lote = data.get(clave) or []
        salida.extend(lote)
        if len(lote) < 20:
            return salida
        pagina += 1


def main():
    accion = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
    if accion not in ('crear', 'apagar'):
        print(__doc__.split('CÓMO SE USA')[0])
        return 1
    if ENTORNO != 'sandbox':
        print('⛔ PAYPAL_ENV=%s. Esto SOLO se hace en sandbox: un plan diario '
              'en producción\n   le cobraría a un cliente todos los días.' % ENTORNO)
        return 1
    if not (ENV.get('PAYPAL_CLIENT_ID') and ENV.get('PAYPAL_SECRET')):
        print('⛔ Faltan las credenciales de PayPal.')
        return 1
    tk = token()

    prod = None
    for p in paginado(tk, '/v1/catalogs/products', 'products'):
        if p.get('name') == NOMBRE_PRODUCTO:
            prod = p.get('id')
            break
    if not prod:
        print('⛔ No encuentro el producto. Corré antes tools/paypal_setup_subs.py')
        return 1

    existente = None
    for pl in paginado(tk, '/v1/billing/plans?product_id=' + prod, 'plans'):
        if pl.get('name') == NOMBRE_PLAN:
            existente = pl
            break

    if accion == 'apagar':
        if not existente:
            print('No hay ningún plan de prueba que apagar.')
            return 0
        code, _ = api(tk, 'POST',
                      '/v1/billing/plans/%s/deactivate' % existente['id'])
        print('Plan de prueba %s → %s'
              % (existente['id'], 'desactivado' if code < 300 else 'HTTP %s' % code))
        print('\nAcordate de devolver PAYPAL_PLAN_STANDARD a su id real:')
        print('   python3 tools/paypal_setup_subs.py')
        return 0 if code < 300 else 1

    if existente:
        print('Ya existía: %s (estado %s)' % (existente['id'], existente.get('status')))
        pid = existente['id']
        if (existente.get('status') or '').upper() != 'ACTIVE':
            api(tk, 'POST', '/v1/billing/plans/%s/activate' % pid)
            print('Reactivado.')
    else:
        code, data = api(tk, 'POST', '/v1/billing/plans', {
            'product_id': prod,
            'name': NOMBRE_PLAN,
            'description': 'Ciclo diario. Solo para verificar renovaciones.',
            'status': 'ACTIVE',
            'billing_cycles': [{
                'frequency': {'interval_unit': 'DAY', 'interval_count': 1},
                'tenure_type': 'REGULAR', 'sequence': 1, 'total_cycles': 0,
                'pricing_scheme': {'fixed_price': {
                    'currency_code': 'USD', 'value': '1.00'}},
            }],
            'payment_preferences': {'auto_bill_outstanding': True,
                                    'setup_fee_failure_action': 'CANCEL',
                                    'payment_failure_threshold': 3},
        })
        if code >= 300:
            print('⛔ No se pudo crear: %s %s' % (code, data))
            return 1
        pid = data['id']
        print('Plan de prueba creado: %s' % pid)

    print("""
─────────────────────────────────────────────────────────────────────
QUÉ HACER AHORA

 1 · Poné este id en la línea environment= de supervisor Y en
     scalpel/.env, en lugar del de Standard:

        PAYPAL_PLAN_STANDARD=%s

     supervisorctl reread && supervisorctl update   (SIN restart: `update` ya reinicia)

 2 · Comprá Standard con una cuenta sandbox de COMPRADOR (no la del
     comercio). El primer cobro ocurre al aprobar.

 3 · MAÑANA, sin tocar nada ni volver al sitio:

        python3 tools/diagnostico_compra.py <tu-usuario>

     Tiene que aparecer un pedido NUEVO, pagado, con la nota
     "Renovación automática". Eso es la prueba: PayPal cobró solo y su
     aviso llegó hasta el servidor.

 4 · Al terminar:

        PAYPAL_ENV=sandbox python3 tools/paypal_plan_diario.py apagar
        python3 tools/paypal_setup_subs.py    (reimprime el id real)
─────────────────────────────────────────────────────────────────────""" % pid)
    return 0


if __name__ == '__main__':
    sys.exit(main())
