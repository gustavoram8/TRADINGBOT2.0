# -*- coding: utf-8 -*-
"""Borra los datos de PRUEBA antes de abrir el cobro de verdad.

Por qué existe fuera de /admin: dentro de la aplicación una venta real NO se
puede borrar, solo revertir, y eso está bien — un libro de ventas del que se
pueden hacer desaparecer filas no sirve como libro. Pero mientras no exista ni
un solo cliente real, lo que hay dentro son ensayos, y arrastrarlos tachados
para siempre ensucia la contabilidad desde el primer día y distorsiona la
escalera del socio. Esta herramienta es la excepción explícita, se corre a mano
en el servidor y no toca nada sin confirmación.

    cd /var/www/TRADINGBOT2.0
    python3 tools/limpiar_pruebas.py                 # solo mira y lista
    python3 tools/limpiar_pruebas.py --borrar 3,7    # borra esas ventas
    python3 tools/limpiar_pruebas.py --borrar-todo   # vacía ventas y pedidos
"""
import glob
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))


def _reintentar_con_el_venv():
    """La app vive en un entorno virtual; el python3 del sistema no tiene Flask.

    En vez de obligar a recordar la ruta del venv, se busca y el script se
    vuelve a lanzar con ese intérprete. Se mira primero el `command=` de
    supervisor, que es la verdad sobre con qué python corre la app de verdad.
    """
    if os.environ.get('_YA_REINTENTADO'):
        return False
    candidatos = []
    for conf in glob.glob('/etc/supervisor/conf.d/*trader*.conf'):
        try:
            with open(conf, encoding='utf-8') as f:
                m = re.search(r'^\s*command\s*=\s*(\S+)', f.read(), re.M)
            if m:
                candidatos.append(os.path.join(os.path.dirname(m.group(1)), 'python'))
        except OSError:
            pass
    candidatos += [os.path.join(RAIZ, v, 'bin', 'python')
                   for v in ('venv', '.venv', 'env')]
    for py in candidatos:
        if os.path.isfile(py) and os.access(py, os.X_OK):
            print('(usando el intérprete de la app: %s)\n' % py)
            os.environ['_YA_REINTENTADO'] = '1'
            os.execv(py, [py] + sys.argv)
    return False


try:
    import app as A                                                # noqa: E402
except ModuleNotFoundError as e:
    if 'flask' not in str(e).lower() and 'sqlalchemy' not in str(e).lower():
        raise
    _reintentar_con_el_venv()
    print('⛔ No encontré el entorno virtual de la aplicación, así que no puedo\n'
          '   leer la base de datos. Mirá con qué python arranca la app:\n'
          '     grep -n "^command=" /etc/supervisor/conf.d/*trader*.conf\n'
          '   y usá ese mismo, por ejemplo:\n'
          '     /ruta/al/venv/bin/python tools/limpiar_pruebas.py')
    sys.exit(1)


def linea(c='─'):
    print(c * 78)


def listar():
    ventas = A.SaleBreakdown.query.order_by(A.SaleBreakdown.id).all()
    pedidos = A.Order.query.order_by(A.Order.id).all()
    print('\n\033[1mLIBRO DE VENTAS\033[0m')
    linea()
    if not ventas:
        print('  (vacío)')
    for v in ventas:
        print('  #%-3s %-9s %-10s pagado $%-8.2f socio %-12s %s%s'
              % (v.id, v.plan, (v.username or '—')[:10], v.net_paid or 0,
                 (v.partner or '—')[:12],
                 'MANUAL' if v.is_manual else 'pedido #%s' % v.order_id,
                 '  ← REVERTIDA' if v.reversed_at else ''))
    print('\n\033[1mPEDIDOS\033[0m')
    linea()
    if not pedidos:
        print('  (ninguno)')
    for o in pedidos:
        u = A.db.session.get(A.User, o.user_id)
        print('  #%-3s %-9s %-9s $%-8.2f %-14s %s'
              % (o.id, o.plan, o.status, o.final_price or 0,
                 o.payment_method or '—', u.username if u else '?'))
    print()
    return ventas, pedidos


def borrar(ids):
    n = 0
    for i in ids:
        v = A.db.session.get(A.SaleBreakdown, i)
        if not v:
            print('  · #%s no existe' % i)
            continue
        print('  · borrando venta #%s (%s, $%.2f)' % (v.id, v.plan, v.net_paid or 0))
        A.db.session.delete(v)
        n += 1
    A.db.session.commit()
    print('\n✅ %d fila(s) borradas del libro.' % n)


def borrar_todo():
    nv = A.SaleBreakdown.query.delete()
    no = A.Order.query.delete()
    A.db.session.commit()
    print('\n✅ Libro vaciado: %d ventas y %d pedidos borrados.' % (nv, no))
    print('   Los PLANES de los usuarios NO se han tocado: si alguien quedó con\n'
          '   premium de una prueba, se le quita desde /admin → Users.')


def main():
    with A.app.app_context():
        ventas, pedidos = listar()

        if '--borrar-todo' in sys.argv:
            if not ventas and not pedidos:
                print('No hay nada que borrar.')
                return 0
            print('\033[1m⚠️  Se van a borrar TODAS las ventas y TODOS los pedidos '
                  'de arriba.\033[0m')
            print('   Esto no se puede deshacer. Solo tiene sentido ANTES de tener\n'
                  '   clientes reales.')
            if input('\n   Escribe BORRAR para confirmar: ').strip() != 'BORRAR':
                print('\nCancelado. No se tocó nada.')
                return 1
            borrar_todo()
            return 0

        if '--borrar' in sys.argv:
            try:
                crudo = sys.argv[sys.argv.index('--borrar') + 1]
                ids = [int(x) for x in crudo.replace(' ', '').split(',') if x]
            except (IndexError, ValueError):
                print('⛔ Uso: --borrar 3,7,9')
                return 1
            print('Se van a borrar las ventas: %s' % ids)
            if input('   Escribe SI para confirmar: ').strip().upper() != 'SI':
                print('\nCancelado. No se tocó nada.')
                return 1
            borrar(ids)
            return 0

        print('Nada se ha tocado. Para borrar:')
        print('   python3 tools/limpiar_pruebas.py --borrar 3,7')
        print('   python3 tools/limpiar_pruebas.py --borrar-todo')
        print('\nLos códigos de descuento se borran desde /admin → Revenue → '
              'sección de códigos (botón Delete).')
        return 0


if __name__ == '__main__':
    sys.exit(main())
