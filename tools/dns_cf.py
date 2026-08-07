# -*- coding: utf-8 -*-
"""Crea o actualiza registros DNS en Cloudflare desde la terminal.

Existe para no tener que entrar al panel por cada registro del correo (A, MX,
SPF, DKIM, DMARC) y, sobre todo, para no repetir el error clásico: **el registro
del correo debe ir con la nube GRIS**. Cloudflare no hace proxy de SMTP; con el
proxy encendido el correo sencillamente no llega. Este script pone `proxied` en
falso salvo que se le pida lo contrario, y avisa si detecta la combinación mala.

Uso — primero MIRA lo que haría, y solo entonces aplícalo:

    export CF_API_TOKEN='...'              # el token, NUNCA en el repo
    python3 tools/dns_cf.py listar
    python3 tools/dns_cf.py correo          # muestra el plan del correo
    python3 tools/dns_cf.py correo --aplicar

    # sueltos:
    python3 tools/dns_cf.py poner TXT @ 'v=spf1 include:...' --aplicar
    python3 tools/dns_cf.py poner A mail 62.171.180.22 --aplicar

Sin `--aplicar` NO escribe nada: solo enseña lo que cambiaría.

El token se saca en Cloudflare → Mi perfil → Tokens de API → Crear token →
plantilla **"Editar DNS de zona"**, limitado a la zona tradeable.academy.
NUNCA se imprime aquí.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = 'https://api.cloudflare.com/client/v4'
ZONA = os.environ.get('CF_ZONE', 'tradeable.academy')
IP = os.environ.get('CF_IP', '62.171.180.22')


def _tok():
    t = os.environ.get('CF_API_TOKEN', '').strip()
    if not t:
        print('✗ Falta CF_API_TOKEN.')
        print("  export CF_API_TOKEN='...'   (no queda en el historial si "
              "antepones un espacio)")
        sys.exit(1)
    return t


def api(metodo, ruta, cuerpo=None):
    req = urllib.request.Request(
        API + ruta, method=metodo,
        data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
        headers={'Authorization': 'Bearer ' + _tok(),
                 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            d = json.loads(e.read().decode())
            msg = '; '.join(x.get('message', '') for x in d.get('errors', []))
        except Exception:
            msg = ''
        print('✗ Cloudflare respondió HTTP %s %s' % (e.code, msg))
        sys.exit(1)
    except Exception as e:
        print('✗ No se pudo conectar con Cloudflare (%s)' % e.__class__.__name__)
        sys.exit(1)


def zona_id():
    d = api('GET', '/zones?name=%s' % ZONA)
    res = d.get('result') or []
    if not res:
        print('✗ El token no ve la zona %s (¿le diste permiso a esa zona?)' % ZONA)
        sys.exit(1)
    return res[0]['id']


def registros(zid):
    return (api('GET', '/zones/%s/dns_records?per_page=200' % zid).get('result')
            or [])


def nombre_completo(n):
    return ZONA if n in ('@', '', ZONA) else '%s.%s' % (n.rstrip('.'), ZONA)


def poner(zid, tipo, nombre, contenido, prio=None, proxied=False, aplicar=False):
    """Crea el registro, o lo actualiza si ya existe uno igual de tipo+nombre."""
    fqdn = nombre_completo(nombre)
    actual = [r for r in registros(zid)
              if r['type'] == tipo and r['name'] == fqdn]
    cuerpo = {'type': tipo, 'name': fqdn, 'content': contenido,
              'ttl': 1, 'proxied': bool(proxied)}
    if prio is not None:
        cuerpo['priority'] = int(prio)
    if tipo in ('MX', 'TXT'):
        cuerpo.pop('proxied', None)          # no aplican proxy

    if actual:
        r = actual[0]
        igual = (r.get('content') == contenido
                 and bool(r.get('proxied')) == bool(proxied)
                 and (prio is None or r.get('priority') == int(prio)))
        if igual:
            print('  = %-5s %-34s ya está como debe' % (tipo, fqdn))
            return
        print('  ~ %-5s %-34s %s  →  %s' % (tipo, fqdn,
                                            (r.get('content') or '')[:38], contenido[:38]))
        if aplicar:
            api('PUT', '/zones/%s/dns_records/%s' % (zid, r['id']), cuerpo)
    else:
        extra = '' if tipo in ('MX', 'TXT') else (
            '  [nube %s]' % ('NARANJA' if proxied else 'gris'))
        print('  + %-5s %-34s %s%s' % (tipo, fqdn, contenido[:38], extra))
        if aplicar:
            api('POST', '/zones/%s/dns_records' % zid, cuerpo)


def main():
    args = [a for a in sys.argv[1:] if a != '--aplicar']
    aplicar = '--aplicar' in sys.argv
    if not args:
        print(__doc__)
        return 0
    cmd = args[0]
    zid = zona_id()

    if cmd == 'listar':
        print('Registros de %s:' % ZONA)
        for r in sorted(registros(zid), key=lambda x: (x['type'], x['name'])):
            nube = ''
            if r['type'] in ('A', 'AAAA', 'CNAME'):
                nube = '  [nube %s]' % ('NARANJA' if r.get('proxied') else 'gris')
            pri = ('  prio %s' % r['priority']) if r.get('priority') is not None else ''
            print('  %-5s %-34s %s%s%s'
                  % (r['type'], r['name'], (r.get('content') or '')[:44], pri, nube))
            if r['type'] == 'A' and r['name'].startswith('mail.') and r.get('proxied'):
                print('       ⚠️  ESTE debe ir en GRIS o el correo no funciona.')
        return 0

    if cmd == 'correo':
        print('Plan para el correo en %s%s:'
              % (ZONA, '' if aplicar else '   (simulación — añade --aplicar)'))
        poner(zid, 'A', 'mail', IP, proxied=False, aplicar=aplicar)
        poner(zid, 'MX', '@', 'mail.%s' % ZONA, prio=10, aplicar=aplicar)
        print('\nSPF, DKIM y DMARC se publican DESPUÉS: el SPF depende del relay '
              'que elijas y\nel DKIM lo genera Mailcow. Se ponen con "poner TXT".')
        if not aplicar:
            print('\nNada se escribió. Repite con --aplicar cuando lo veas bien.')
        return 0

    if cmd == 'poner':
        if len(args) < 4:
            print('uso: poner <TIPO> <nombre> <contenido> [prioridad]')
            return 1
        tipo, nombre, contenido = args[1].upper(), args[2], args[3]
        prio = args[4] if len(args) > 4 else (10 if tipo == 'MX' else None)
        if not aplicar:
            print('(simulación — añade --aplicar)')
        poner(zid, tipo, nombre, contenido, prio=prio, proxied=False,
              aplicar=aplicar)
        return 0

    print('Órdenes: listar · correo · poner')
    return 1


if __name__ == '__main__':
    sys.exit(main())
