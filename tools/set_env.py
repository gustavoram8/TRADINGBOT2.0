#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escribe variables de entorno donde la app las lee de verdad.

    python3 tools/set_env.py SITE_URL=https://tradeable.academy

Las pone en LOS DOS sitios a la vez — `scalpel/.env` y la línea `environment=`
del conf de supervisor — porque en producción (gunicorn) el `.env` NO se lee:
editar solo uno es el error clásico que deja la variable "puesta" sin efecto.
Reusa las funciones ya probadas de `set_paypal.py` (conservan lo que hubiera,
hacen copia de respaldo, y parten la línea por comas solo fuera de comillas).

Después hay que recargar supervisor para que la app lo tome:
    supervisorctl reread && supervisorctl update && supervisorctl restart traderacelerator
"""
import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv):
    valores = {}
    for a in argv:
        if '=' not in a:
            sys.exit('Cada argumento debe ser CLAVE=valor (recibí %r)' % a)
        k, v = a.split('=', 1)
        valores[k.strip()] = v.strip()
    if not valores:
        sys.exit('Uso: python3 tools/set_env.py CLAVE=valor [CLAVE=valor ...]')

    spec = importlib.util.spec_from_file_location(
        'sp', os.path.join(RAIZ, 'tools', 'set_paypal.py'))
    sp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sp)          # main() está guardado: no pide nada

    sp.escribir_env(valores)
    print('✅ scalpel/.env — %s' % ', '.join(sorted(valores)))
    ruta, copia = sp.escribir_supervisor(valores)
    if ruta is None:
        print('⚠️  supervisor NO actualizado: %s' % copia)
        print('    (en una máquina local es normal; en el VPS hay que arreglarlo)')
        return 1
    print('✅ %s%s' % (ruta, ('  (copia: %s)' % os.path.basename(copia)) if copia else ''))
    print('\nFalta recargar para que la app lo tome:')
    print('  supervisorctl reread && supervisorctl update && supervisorctl restart traderacelerator')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
