# -*- coding: utf-8 -*-
"""Pone (o quita) variables de entorno en los DOS sitios, de un solo comando.

En producción la aplicación lee la línea `environment=` de supervisor, no el
`.env` — pero conviene mantener los dos en sync. Este script escribe en ambos,
sin abrir ningún editor, y **conservando lo que ya hubiera**.

    python3 tools/set_env.py PREVIEW_USERS=maurotradesve,gussytrades
    python3 tools/set_env.py CRYPTO_API_KEY=xxx CRYPTO_IPN_SECRET=yyy
    python3 tools/set_env.py --quitar PREVIEW_USERS

NUNCA imprime los valores (podrían ser claves): solo los nombres. Hace copia de
seguridad de los dos archivos antes de tocarlos.

Después hay que aplicar los cambios:
    supervisorctl reread && supervisorctl update

⚠️ NO encadenar `restart` detrás de `update`. Al cambiar el conf, `update` YA
reinicia el proceso; gunicorn tarda ~30 s en cerrar con elegancia, así que el
segundo reinicio lo mata a mitad del arranque y el sitio devuelve **502 durante
~40 s**. Pasó en producción el 2026-08-07 con este mismo comando escrito aquí.
"""
import glob
import os
import re
import shutil
import sys
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(RAIZ, 'scalpel', '.env')
# valores que sí se pueden enseñar: no son secretos y verlos ayuda a confirmar
NO_SECRETO = {'PREVIEW_USERS', 'PAYPAL_ENV', 'SITE_URL', 'CRYPTO_PAY_CURRENCY',
              'CRYPTO_API_BASE', 'MAIL_SERVER', 'MAIL_PORT', 'MAIL_FROM',
              'MAIL_USERNAME', 'ADMIN_EMAIL', 'PUBLIC_HTTPS', 'ASSISTANT_MODEL',
              # El % de la oferta de bienvenida NO es un secreto y verlo
              # confirmado evita el peor error posible con él: creer que quedó
              # puesto en 30 cuando quedó en 3.
              'LAUNCH_DISCOUNT_PCT'}


def muestra(k, v):
    return v if k in NO_SECRETO else '(oculto, %d caracteres)' % len(v)


def respaldo(ruta):
    if os.path.exists(ruta):
        copia = '%s.bak-%s' % (ruta, datetime.now().strftime('%Y%m%d-%H%M%S'))
        shutil.copy2(ruta, copia)
        return copia
    return None


def escribir_env(valores, quitar):
    lineas = []
    if os.path.exists(ENV):
        with open(ENV, encoding='utf-8') as f:
            lineas = f.read().splitlines()
    copia = respaldo(ENV)
    puestas, salida = set(), []
    for l in lineas:
        k = (l.split('=', 1)[0].strip()
             if '=' in l and not l.lstrip().startswith('#') else None)
        if k and k in quitar:
            continue
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
    os.chmod(ENV, 0o600)
    return copia


def _partir_environment(linea):
    """Parte `environment=A="1",B="2"` conservando lo que ya hubiera.

    Se separa por comas SOLO fuera de comillas: un valor con una coma dentro
    (una lista de usuarios, una contraseña) partiría la línea y dejaría el
    proceso sin arrancar."""
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


def escribir_supervisor(valores, quitar):
    confs = glob.glob('/etc/supervisor/conf.d/*trader*.conf')
    if not confs:
        return None, ('no encontré ningún conf en '
                      '/etc/supervisor/conf.d/*trader*.conf')
    ruta = confs[0]
    try:
        with open(ruta, encoding='utf-8') as f:
            lineas = f.read().splitlines()
    except PermissionError:
        return None, 'sin permiso para leer %s — usa sudo' % ruta

    idx = next((i for i, l in enumerate(lineas)
                if re.match(r'\s*environment\s*=', l)), None)
    if idx is None:
        prog = next((i for i, l in enumerate(lineas)
                     if l.strip().startswith('[program:')), None)
        if prog is None:
            return None, 'el conf no tiene sección [program:...]; no lo toco'
        actuales = {}
        idx = prog + 1
        lineas.insert(idx, '')
    else:
        actuales = _partir_environment(lineas[idx])
    for k in quitar:
        actuales.pop(k, None)
    actuales.update(valores)
    lineas[idx] = ('environment='
                   + ','.join('%s="%s"' % (k, v) for k, v in actuales.items()))
    copia = respaldo(ruta)
    try:
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lineas).rstrip() + '\n')
    except PermissionError:
        return None, 'sin permiso para escribir %s — usa sudo' % ruta
    return ruta, copia


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    quitar_modo = '--quitar' in args
    args = [a for a in args if a != '--quitar']

    valores, quitar = {}, set()
    for a in args:
        if quitar_modo and '=' not in a:
            quitar.add(a.strip())
        elif '=' in a:
            k, v = a.split('=', 1)
            valores[k.strip()] = v
        else:
            print('✗ No entiendo «%s». Usa NOMBRE=valor, o --quitar NOMBRE' % a)
            return 1
    if not valores and not quitar:
        print('✗ Nada que hacer.')
        return 1

    for k, v in valores.items():
        print('  · %s = %s' % (k, muestra(k, v)))
    for k in sorted(quitar):
        print('  · %s → SE QUITA' % k)

    c1 = escribir_env(valores, quitar)
    print('✓ scalpel/.env actualizado%s' % (' (copia: %s)' % os.path.basename(c1)
                                            if c1 else ''))
    ruta, c2 = escribir_supervisor(valores, quitar)
    if not ruta:
        print('⚠️  supervisor NO actualizado: %s' % c2)
        print('   OJO: en producción manda supervisor, no el .env.')
        return 1
    print('✓ %s actualizado%s' % (ruta, (' (copia: %s)' % os.path.basename(c2))
                                  if c2 else ''))
    print('\nAhora aplica los cambios:')
    print('  supervisorctl reread && supervisorctl update && '
          'supervisorctl restart traderacelerator')
    return 0


if __name__ == '__main__':
    sys.exit(main())
