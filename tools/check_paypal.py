# -*- coding: utf-8 -*-
"""Comprueba las credenciales de PayPal ANTES de intentar cobrar.

Para qué sirve: le pide un token a PayPal con el par Client ID + Secret y dice
si funcionan y, sobre todo, **a qué entorno pertenecen** — porque el mismo par
no vale en los dos, y `PAYPAL_ENV` cae en 'live' por defecto: unas credenciales
de sandbox contra el servidor de producción fallan con un 401 pelado que no
explica el motivo.

NO imprime ni el Client ID ni el Secret. Solo si están, si autentican y dónde.

Se corre EN EL VPS, donde viven las variables:

    cd /var/www/TRADINGBOT2.0
    python3 tools/check_paypal.py

Si las variables están en supervisor y no en el entorno de tu shell, se le
pueden pasar en la misma línea (así no quedan en el historial si antepones un
espacio):

     PAYPAL_CLIENT_ID='...' PAYPAL_SECRET='...' python3 tools/check_paypal.py
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

HOSTS = [('live', 'https://api-m.paypal.com'),
         ('sandbox', 'https://api-m.sandbox.paypal.com')]


def _dotenv(path='scalpel/.env'):
    """Lee el .env sin depender de python-dotenv (en el VPS puede no estar en
    el intérprete del sistema)."""
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


def pedir_token(base, cid, secret):
    """True si PayPal entrega un token; si no, el motivo."""
    auth = base64.b64encode(('%s:%s' % (cid, secret)).encode()).decode()
    req = urllib.request.Request(
        base + '/v1/oauth2/token',
        data=b'grant_type=client_credentials',
        headers={'Authorization': 'Basic ' + auth,
                 'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode())
            return True, 'token ok (caduca en %ss)' % d.get('expires_in', '?')
    except urllib.error.HTTPError as e:
        cuerpo = ''
        try:
            cuerpo = json.loads(e.read().decode()).get('error_description', '')
        except Exception:
            pass
        return False, 'HTTP %s %s' % (e.code, cuerpo)
    except Exception as e:                      # red, DNS, proxy…
        return None, 'no se pudo conectar (%s)' % e.__class__.__name__


def main():
    env_file = _dotenv()
    cid = os.environ.get('PAYPAL_CLIENT_ID') or env_file.get('PAYPAL_CLIENT_ID', '')
    secret = os.environ.get('PAYPAL_SECRET') or env_file.get('PAYPAL_SECRET', '')
    declarado = (os.environ.get('PAYPAL_ENV')
                 or env_file.get('PAYPAL_ENV', 'live')).strip().lower()

    print('Client ID : %s' % ('presente (%d caracteres)' % len(cid) if cid else 'FALTA'))
    print('Secret    : %s' % ('presente (%d caracteres)' % len(secret) if secret else 'FALTA'))
    print('PAYPAL_ENV: %s' % declarado)
    if not (cid and secret):
        print('\n⛔ Faltan credenciales. Ponelas en la línea `environment=` de '
              'supervisor y en scalpel/.env, y volvé a correr esto.')
        return 1

    print('\nProbando el par contra los dos entornos de PayPal…')
    validos, sin_red = [], 0
    for nombre, base in HOSTS:
        ok, detalle = pedir_token(base, cid, secret)
        icono = {True: '✅', False: '❌', None: '⚠️ '}[ok]
        print('  %s %-8s %s' % (icono, nombre, detalle))
        if ok:
            validos.append(nombre)
        elif ok is None:
            sin_red += 1

    print()
    # No confundir "PayPal las rechazó" con "no llegué a PayPal": el primero es
    # un problema de credenciales, el segundo de red/firewall.
    if sin_red == len(HOSTS):
        print('⚠️  No se pudo hablar con PayPal desde esta máquina, así que las '
              'credenciales quedan SIN comprobar.\n'
              '    Revisá salida a internet / DNS y volvé a correrlo en el VPS.')
        return 2
    if not validos:
        print('⛔ El par NO autentica en ninguno de los dos. Revisá que el '
              'Secret sea el de ESA app (PayPal solo lo muestra al crearlo; si '
              'se perdió, se genera uno nuevo) y que no se haya colado un '
              'espacio al copiar.')
        return 1
    real = validos[0]
    print('✅ Credenciales válidas — son de **%s**.' % real.upper())
    if real != declarado:
        print('\n⚠️  Pero PAYPAL_ENV dice "%s". Con esa combinación PayPal '
              'rechaza todo.\n    Corregí a:  PAYPAL_ENV=%s' % (declarado, real))
        return 1
    print('   Y PAYPAL_ENV coincide. Listo para %s.'
          % ('cobrar de verdad' if real == 'live' else 'ensayar sin dinero real'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
