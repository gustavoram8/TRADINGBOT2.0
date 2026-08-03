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
    python3 tools/limpiar_pruebas.py              # solo mira y lista
    python3 tools/limpiar_pruebas.py --limpiar    # lo pregunta todo, paso a paso
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
    codigos = A.PromoCode.query.order_by(A.PromoCode.id).all()
    print('\n\033[1mCÓDIGOS DE DESCUENTO\033[0m')
    linea()
    if not codigos:
        print('  (ninguno)')
    for c in codigos:
        print('  %-14s %3s%%  %-12s usos: %-4s %s'
              % (c.code, c.discount_pct, (c.creator_name or '—')[:12],
                 c.uses_count or 0, 'activo' if c.active else 'apagado'))
    usuarios = A.User.query.order_by(A.User.id).all()
    print('\n\033[1mCUENTAS\033[0m')
    linea()
    for u in usuarios:
        print('  #%-3s %-16s %-26s %-9s%s'
              % (u.id, u.username, u.email, u.plan, '  ← ADMIN' if u.is_admin else ''))
    print()
    return ventas, pedidos, codigos, usuarios


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


def borrar_codigos(codigos):
    n = 0
    for c in codigos:
        pc = A.PromoCode.query.filter(
            A.db.func.lower(A.PromoCode.code) == c.strip().lower()).first()
        if not pc:
            print('  · "%s" no existe' % c)
            continue
        print('  · borrando código %s (%s%%)' % (pc.code, pc.discount_pct))
        A.db.session.delete(pc)
        n += 1
    A.db.session.commit()
    print('✅ %d código(s) borrados.' % n)


def _columnas_de_usuario():
    """Toda tabla que guarde algo colgando de un usuario.

    Se descubren solas recorriendo los modelos en vez de escribir una lista a
    mano: una tabla nueva que se añada mañana queda cubierta sin acordarse de
    esto, y borrar un usuario dejando filas huérfanas apuntando a su id es
    justo lo que rompe la base con una clave foránea.
    """
    fuera = []
    for mapper in A.db.Model.registry.mappers:
        cls = mapper.class_
        if cls is A.User:
            continue
        for col in mapper.columns:
            if col.key.endswith('user_id'):
                fuera.append((cls, col.key))
    return fuera


def borrar_usuarios(nombres):
    n = 0
    for nom in nombres:
        u = A.User.query.filter(
            (A.db.func.lower(A.User.username) == nom.strip().lower())
            | (A.db.func.lower(A.User.email) == nom.strip().lower())).first()
        if not u:
            print('  · "%s" no existe' % nom)
            continue
        if u.is_admin:
            print('  · "%s" es ADMIN — no se toca' % u.username)
            continue
        borradas = 0
        for cls, col in _columnas_de_usuario():
            borradas += cls.query.filter(getattr(cls, col) == u.id).delete(
                synchronize_session=False)
        print('  · borrando %s (%s) y %d fila(s) suyas' % (u.username, u.email, borradas))
        A.db.session.delete(u)
        n += 1
    A.db.session.commit()
    print('✅ %d cuenta(s) borradas.' % n)


def _si(pregunta, palabra='SI'):
    return input('   %s Escribe %s para confirmar: ' % (pregunta, palabra)).strip().upper() \
        == palabra


def main():
    with A.app.app_context():
        ventas, pedidos, codigos, usuarios = listar()

        # Un solo comando que deja la casa limpia, preguntando por cada cosa
        # POR SEPARADO: borrar el libro no tiene por qué llevarse el código del
        # socio ni una cuenta que sí quieras conservar.
        if '--limpiar' in sys.argv:
            print('\033[1m⚠️  Limpieza previa al lanzamiento.\033[0m Se pregunta por cada '
                  'grupo; puedes decir que no a cualquiera.\n')
            if ventas or pedidos:
                print('1) VENTAS Y PEDIDOS — %d y %d' % (len(ventas), len(pedidos)))
                if _si('¿Borrar TODO el libro de ventas y los pedidos?', 'BORRAR'):
                    borrar_todo()
                else:
                    print('   · se quedan como están')
            else:
                print('1) VENTAS Y PEDIDOS — ya está vacío')

            if codigos:
                print('\n2) CÓDIGOS — %s' % ', '.join(c.code for c in codigos))
                cual = input('   Escribe los que quieras borrar separados por coma\n'
                             '   (o TODOS, o Enter para no borrar ninguno): ').strip()
                if cual.upper() == 'TODOS':
                    borrar_codigos([c.code for c in codigos])
                elif cual:
                    borrar_codigos(cual.split(','))
                else:
                    print('   · se quedan todos')
            else:
                print('\n2) CÓDIGOS — no hay ninguno')

            noadmin = [u for u in usuarios if not u.is_admin]
            if noadmin:
                print('\n3) CUENTAS DE PRUEBA — %s' % ', '.join(u.username for u in noadmin))
                print('   (las cuentas ADMIN nunca se borran, aunque las escribas)')
                cual = input('   Escribe las que quieras borrar separadas por coma\n'
                             '   (o Enter para no borrar ninguna): ').strip()
                if cual:
                    print('   Se borrarán esas cuentas y TODO lo suyo: análisis, XP,\n'
                          '   mensajes del foro, cosméticos. No se puede deshacer.')
                    if _si('¿Seguro?', 'BORRAR'):
                        borrar_usuarios(cual.split(','))
                    else:
                        print('   · cancelado, no se borró ninguna cuenta')
                else:
                    print('   · se quedan todas')
            else:
                print('\n3) CUENTAS — solo hay administradores')
            print('\n\033[1mListo.\033[0m')
            return 0

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

        print('Nada se ha tocado. Para limpiarlo todo de una vez:')
        print('   \033[1mpython3 tools/limpiar_pruebas.py --limpiar\033[0m')
        print('\nY si prefieres ir a lo concreto:')
        print('   python3 tools/limpiar_pruebas.py --borrar 3,7        (ventas sueltas)')
        print('   python3 tools/limpiar_pruebas.py --borrar-todo       (libro entero)')
        return 0


if __name__ == '__main__':
    sys.exit(main())
