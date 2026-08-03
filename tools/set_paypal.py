# -*- coding: utf-8 -*-
"""Deja PayPal configurado de una sola vez, sin editar archivos a mano.

    cd /var/www/TRADINGBOT2.0 && sudo python3 tools/set_paypal.py

Qué hace, en este orden:
  1. te pide el Client ID y el Secret (el Secret NO se ve al escribirlo);
  2. los PRUEBA contra PayPal antes de tocar nada — si no autentican, no
     escribe absolutamente nada y te dice por qué;
  3. los escribe en `scalpel/.env` (de donde leen los scripts);
  4. y en la línea `environment=` de supervisor (que es lo que de verdad ve la
     app: bajo gunicorn el .env NO se lee — esa trampa ya costó una sesión con
     la clave de OpenAI), conservando las variables que ya hubiera;
  5. deja copia de seguridad de los dos archivos antes de cambiarlos.

No imprime nunca el Secret, ni entero ni en trozos.
"""
import base64
import getpass
import glob
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(RAIZ, 'scalpel', '.env')
HOSTS = [('live', 'https://api-m.paypal.com'),
         ('sandbox', 'https://api-m.sandbox.paypal.com')]


def token(base, cid, secret):
    """True si PayPal entrega un token con ese par."""
    auth = base64.b64encode(('%s:%s' % (cid, secret)).encode()).decode()
    req = urllib.request.Request(
        base + '/v1/oauth2/token', data=b'grant_type=client_credentials',
        headers={'Authorization': 'Basic ' + auth,
                 'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=25):
            return True, ''
    except urllib.error.HTTPError as e:
        detalle = ''
        try:
            detalle = json.loads(e.read().decode()).get('error_description', '')
        except Exception:
            pass
        return False, 'HTTP %s %s' % (e.code, detalle)
    except Exception as e:
        return None, 'no se pudo conectar (%s)' % e.__class__.__name__


def respaldo(ruta):
    if os.path.exists(ruta):
        copia = '%s.bak-%s' % (ruta, datetime.now().strftime('%Y%m%d-%H%M%S'))
        shutil.copy2(ruta, copia)
        return copia
    return None


def escribir_env(valores):
    lineas = []
    if os.path.exists(ENV):
        with open(ENV, encoding='utf-8') as f:
            lineas = f.read().splitlines()
    puestas = set()
    salida = []
    for l in lineas:
        k = l.split('=', 1)[0].strip() if '=' in l and not l.lstrip().startswith('#') else None
        if k in valores:
            salida.append('%s=%s' % (k, valores[k]))
            puestas.add(k)
        else:
            salida.append(l)
    for k, v in valores.items():
        if k not in puestas:
            salida.append('%s=%s' % (k, v))
    os.makedirs(os.path.dirname(ENV), exist_ok=True)
    with open(ENV, 'w', encoding='utf-8') as f:
        f.write('\n'.join(salida).rstrip() + '\n')
    os.chmod(ENV, 0o600)          # el Secret no tiene por qué ser legible por todos


def _partir_environment(linea):
    """Parte `environment=A="1",B="2"` conservando lo que ya hubiera.

    Se separa por comas SOLO fuera de comillas: una contraseña con una coma
    dentro partiría la línea y dejaría el proceso sin arrancar.
    """
    cuerpo = linea.split('=', 1)[1].strip()
    pares, actual, dentro = [], '', False
    for ch in cuerpo:
        if ch == '"':
            dentro = not dentro
            actual += ch
        elif ch == ',' and not dentro:
            pares.append(actual)
            actual = ''
        else:
            actual += ch
    if actual.strip():
        pares.append(actual)
    out = {}
    for p in pares:
        if '=' in p:
            k, v = p.split('=', 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def escribir_supervisor(valores):
    confs = glob.glob('/etc/supervisor/conf.d/*trader*.conf')
    if not confs:
        return None, 'no encontré ningún conf de supervisor en /etc/supervisor/conf.d/*trader*.conf'
    ruta = confs[0]
    try:
        with open(ruta, encoding='utf-8') as f:
            lineas = f.read().splitlines()
    except PermissionError:
        return None, 'sin permiso para leer %s — corré esto con sudo' % ruta

    idx = next((i for i, l in enumerate(lineas)
                if re.match(r'\s*environment\s*=', l)), None)
    if idx is None:
        prog = next((i for i, l in enumerate(lineas) if l.strip().startswith('[program:')), None)
        if prog is None:
            return None, 'el conf no tiene sección [program:...]; no lo toco'
        actuales = {}
        idx = prog + 1
        lineas.insert(idx, '')
    else:
        actuales = _partir_environment(lineas[idx])
    actuales.update(valores)
    lineas[idx] = 'environment=' + ','.join('%s="%s"' % (k, v) for k, v in actuales.items())
    copia = respaldo(ruta)
    try:
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lineas).rstrip() + '\n')
    except PermissionError:
        return None, 'sin permiso para escribir %s — corré esto con sudo' % ruta
    return ruta, copia


def main():
    print('Configurar PayPal — las credenciales no se muestran ni se guardan en el historial.\n')
    cid = input('Client ID : ').strip()
    secret = getpass.getpass('Secret    : (no se verá al escribir) ').strip()
    if not cid or not secret:
        print('\n⛔ Faltó uno de los dos. No se tocó nada.')
        return 1
    for nombre, valor in (('Client ID', cid), ('Secret', secret)):
        if ' ' in valor or valor[0] in '\'"':
            print('\n⛔ El %s trae un espacio o una comilla — casi seguro se coló al copiar.\n'
                  '   Vuelve a copiarlo y ejecuta esto otra vez. No se tocó nada.' % nombre)
            return 1

    print('\nProbando el par contra PayPal…')
    validos, sin_red = [], 0
    for nombre, base in HOSTS:
        ok, detalle = token(base, cid, secret)
        print('  %s %-8s %s' % ({True: '✅', False: '❌', None: '⚠️ '}[ok], nombre, detalle))
        if ok:
            validos.append(nombre)
        elif ok is None:
            sin_red += 1
    if sin_red == len(HOSTS):
        print('\n⚠️  No se pudo hablar con PayPal desde este servidor, así que las\n'
              '    credenciales quedan SIN comprobar. No se escribió nada: revisá la\n'
              '    salida a internet y volvé a intentarlo.')
        return 2
    if not validos:
        print('\n⛔ PayPal RECHAZÓ el par. No se escribió nada.\n'
              '   Suele ser: (a) el Secret es de otra app, (b) se copió a medias, o\n'
              '   (c) la app está desactivada en el panel de PayPal.')
        return 1

    entorno = validos[0]
    print('\n✅ Credenciales válidas — son de **%s**.' % entorno.upper())
    if entorno == 'sandbox':
        print('   ⚠️  OJO: en sandbox el dinero es de mentira. Se configurará como\n'
              '       sandbox para que el circuito funcione, pero NO vas a cobrar.')

    valores = {'PAYPAL_CLIENT_ID': cid, 'PAYPAL_SECRET': secret, 'PAYPAL_ENV': entorno}
    copia_env = respaldo(ENV)
    escribir_env(valores)
    print('\n📄 scalpel/.env actualizado%s' % ('  (copia: %s)' % os.path.basename(copia_env)
                                              if copia_env else ''))
    ruta, copia = escribir_supervisor(valores)
    if ruta is None:
        print('⚠️  supervisor NO actualizado: %s' % copia)
        print('    La app NO verá las credenciales hasta arreglarlo: bajo gunicorn el\n'
              '    .env no se lee.')
        return 1
    print('⚙️  %s actualizado%s' % (ruta, '  (copia: %s)' % os.path.basename(copia) if copia else ''))
    print('\nAhora, para que la app las tome:\n'
          '   supervisorctl reread && supervisorctl update && supervisorctl restart traderacelerator\n'
          '\nY para confirmarlo:\n'
          '   tail -5 /var/log/*trader*.log  (o el log que uses) → línea [PayPal] enabled=True')
    return 0


if __name__ == '__main__':
    sys.exit(main())
