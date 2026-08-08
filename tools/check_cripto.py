# -*- coding: utf-8 -*-
"""Comprueba el cobro en cripto (NOWPayments) ANTES de intentar cobrar.

Para qué sirve: pregunta al procesador si la API key funciona, si la moneda
configurada (`CRYPTO_PAY_CURRENCY`, por defecto USDT-TRON) está realmente
disponible en tu cuenta, y si el aviso instantáneo (IPN) podrá verificarse.

Por qué hace falta: un cobro en cripto **no falla de forma ruidosa**. Sin el
IPN secret el aviso llega y se rechaza por firma inválida, y el plan se
entregaría tarde — por la reconciliación de la página del pedido o por el
barrido de /admin. Se ve igual que "todavía no lo he encendido", así que sin
esta comprobación te enteras con una venta real.

NUNCA imprime la API key ni el secreto. Solo si están y si sirven.

Se corre EN EL VPS, donde viven las variables:

    cd /var/www/TRADINGBOT2.0
    python3 tools/check_cripto.py

Si las variables están en supervisor y no en tu shell, se pueden pasar en la
misma línea (antepón un espacio y no quedan en el historial):

     CRYPTO_API_KEY='...' python3 tools/check_cripto.py
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE_DEF = 'https://api.nowpayments.io/v1'


def _dotenv(path='scalpel/.env'):
    """Lee el .env sin depender de python-dotenv (en el VPS puede no estar)."""
    out = {}
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def _get(base, ruta, api_key=None):
    req = urllib.request.Request(base + ruta)
    if api_key:
        req.add_header('x-api-key', api_key)
    req.add_header('Accept', 'application/json')
    # Mismo User-Agent que usa la app. Sin él, el CDN que protege la API
    # responde 403 con una página HTML y el diagnóstico acusa a la clave de
    # ser inválida cuando el problema es que ni siquiera llegó a la API.
    req.add_header('User-Agent',
                   'TradeableAcademy/1.0 (+https://tradeable.academy)')
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return True, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        crudo = ''
        try:
            crudo = e.read().decode(errors='replace')
        except Exception:
            pass
        if crudo.lstrip()[:1] in ('<',):
            # Respuesta HTML = no contestó la API, contestó su muro de entrada.
            return False, ('HTTP %s — respuesta HTML, no JSON: la petición la '
                           'frenó el CDN ANTES de llegar a la API (no es la '
                           'clave)' % e.code)
        # ⚠️ El cuerpo ya se leyó arriba: `e.read()` es un flujo y una segunda
        # lectura devuelve vacío — por eso el 403 salía sin explicación.
        cuerpo = ''
        try:
            cuerpo = (json.loads(crudo).get('message') or '')[:120]
        except Exception:
            cuerpo = crudo.strip()[:120]
        return False, 'HTTP %s %s' % (e.code, cuerpo)
    except Exception as e:                      # red, DNS, proxy…
        return None, 'no se pudo conectar (%s)' % e.__class__.__name__


def main():
    envf = _dotenv()
    def var(n, d=''):
        return os.environ.get(n) or envf.get(n, d)

    api_key = var('CRYPTO_API_KEY')
    ipn = var('CRYPTO_IPN_SECRET')
    base = var('CRYPTO_API_BASE', BASE_DEF)
    moneda = (var('CRYPTO_PAY_CURRENCY', 'usdttrc20') or '').lower()
    site = var('SITE_URL')

    print('── Cobro en cripto (NOWPayments) ──')
    print('  API key   : %s' % ('presente' if api_key else 'FALTA'))
    print('  IPN secret: %s' % ('presente' if ipn else 'FALTA'))
    print('  Moneda    : %s' % moneda)
    print('  API       : %s' % base)
    print()

    problemas, avisos = [], []

    if not api_key:
        print('✗ Sin CRYPTO_API_KEY el cobro en cripto está APAGADO.')
        print('  El sitio sigue funcionando: cae al flujo manual de USDT.')
        return 1

    # 1) ¿responde el servicio?
    ok, d = _get(base, '/status')
    if ok:
        print('✓ El servicio responde (%s)' % (d.get('message') or 'ok'))
    elif ok is None:
        print('⚠️  No se pudo consultar el servicio: %s' % d)
        avisos.append('sin red hacia el procesador')
    else:
        print('✗ El servicio contestó con error: %s' % d)
        problemas.append('servicio inalcanzable')

    # 2) ¿la API key autentica?
    # ⚠️ Con `/payment` (listar pagos) NO se puede comprobar: ese endpoint se
    # autentica con un token JWT de sesión (usuario y contraseña), no con la
    # API key, y responde 401 aunque la clave sea perfecta. Acusaba de
    # inválida una clave que funcionaba. Se usa `/estimate`, que sí es de los
    # que exigen la API key y no crea nada.
    ok, d = _get(base, '/estimate?amount=25&currency_from=usd&currency_to=%s'
                 % moneda, api_key)
    if ok:
        print('✓ La API key autentica')
    elif ok is None:
        print('⚠️  No se pudo verificar la API key: %s' % d)
        avisos.append('no se verificó la API key')
    elif 'JWT' in str(d) or 'Bearer' in str(d):
        print('⚠️  Ese endpoint pide un token de sesión, no la API key: %s' % d)
        avisos.append('no se pudo comprobar la clave por esa vía')
    else:
        print('✗ La API key NO autentica: %s' % d)
        print('  Revisa que sea la clave de la MISMA cuenta y esté activa.')
        problemas.append('API key inválida')

    # 3) ¿la moneda que vas a cobrar está disponible?
    ok, d = _get(base, '/currencies', api_key)
    if ok:
        lista = [str(c).lower() for c in (d.get('currencies') or [])]
        if moneda in lista:
            print('✓ La moneda %s está disponible' % moneda)
        else:
            print('✗ La moneda %s NO aparece disponible en tu cuenta.' % moneda)
            print('  Cada factura la pediría en una moneda que el procesador no'
                  ' acepta → el comprador se queda sin poder pagar.')
            cerca = [c for c in lista if c.startswith('usdt')][:6]
            if cerca:
                print('  Parecidas disponibles: %s' % ', '.join(cerca))
            problemas.append('moneda no disponible')
    elif ok is None:
        avisos.append('no se pudo listar monedas')
    else:
        avisos.append('no se pudieron listar las monedas (%s)' % d)

    # 3b) el MÍNIMO que el procesador acepta cobrar en esa moneda
    # Importa porque una factura por debajo del mínimo la rechaza el procesador
    # y el comprador cae en las instrucciones manuales sin entender por qué.
    # Hoy solo los PLANES pueden pagarse en cripto ($25 el más barato), pero el
    # mínimo lo fija el procesador y puede subir cuando suben las comisiones de
    # la red — así que se comprueba contra el precio real, no contra un supuesto.
    ok, d = _get(base, '/min-amount?currency_from=usd&currency_to=%s'
                 '&fiat_equivalent=usd' % moneda, api_key)
    if ok:
        try:
            minimo = float(d.get('fiat_equivalent')
                           or d.get('min_amount') or 0)
        except (TypeError, ValueError):
            minimo = 0.0
        barato = 25.0            # Standard mensual: el plan más barato
        if minimo and minimo > barato:
            print('✗ El mínimo del procesador ($%.2f) supera el plan más '
                  'barato ($%.2f): esa compra no se podría pagar en cripto.'
                  % (minimo, barato))
            problemas.append('mínimo por encima del precio')
        elif minimo:
            print('✓ Mínimo del procesador: $%.2f (por debajo del plan más '
                  'barato, $%.2f)' % (minimo, barato))
        else:
            avisos.append('el procesador no informó de un mínimo')
    elif ok is None:
        avisos.append('no se pudo consultar el mínimo')
    else:
        avisos.append('no se pudo consultar el mínimo (%s)' % d)

    # 4) el aviso instantáneo
    if not ipn:
        print('✗ Falta CRYPTO_IPN_SECRET: el aviso del procesador llega SIN poder'
              ' verificarse y se rechaza.')
        print('  El pago no se pierde (lo rescatan la página del pedido y el'
              ' barrido de /admin), pero el plan se entrega tarde.')
        problemas.append('sin IPN secret')
    else:
        print('✓ El aviso instantáneo podrá verificarse (IPN secret presente)')

    # 5) la URL a la que el procesador debe avisar
    if not site:
        print('⚠️  SITE_URL vacío: la factura se crearía con la URL del host de'
              ' cada petición. Si alguien entra por la IP cruda, el aviso'
              ' apuntaría ahí.')
        avisos.append('SITE_URL sin fijar')
    elif not site.startswith('https://'):
        print('⚠️  SITE_URL no es HTTPS (%s): muchos procesadores no envían el'
              ' aviso a un destino sin cifrar.' % site)
        avisos.append('SITE_URL sin HTTPS')
    else:
        print('✓ El aviso irá a %s/webhook/crypto' % site.rstrip('/'))

    print()
    if problemas:
        print('RESULTADO: %d bloqueante(s) — %s' % (len(problemas),
                                                    '; '.join(problemas)))
        return 1
    print('RESULTADO: todo en orden%s'
          % (' (con %d aviso/s)' % len(avisos) if avisos else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
