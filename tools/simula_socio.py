# -*- coding: utf-8 -*-
"""Da de alta un colaborador DE PRUEBA para ver el panel /partner lleno.

    venv/bin/python3 tools/simula_socio.py             # mira, no toca nada
    venv/bin/python3 tools/simula_socio.py --aplicar   # lo crea
    venv/bin/python3 tools/simula_socio.py --borrar --aplicar   # lo deshace

Existe porque el panel vacío no deja verificar nada: el dueño necesita VER
las tarjetas, los tramos y la billetera funcionando antes de enseñárselo a un
colaborador real. Crea exactamente lo que crearía el alta real:

  · la cuenta `demo_colab` (contraseña impresa abajo — para entrar COMO él);
  · su código de creador `DEMO20` (20%, nombre "Demo Colaborador");
  · la conexión Owner + fecha de inicio del acuerdo (hace 20 días, así la
    revisión de los 30 días se ve en el futuro cercano);
  · 6 ventas MANUALES en el libro (5 clientes → 5 puestos al 30%, con una
    renovación, una pagada y una pendiente) — mismas filas que la carga
    manual de /admin, marcadas is_manual, sin tocar ningún pedido real.

La billetera se deja VACÍA a propósito: así se ve el aviso rojo del 4.4 y se
prueba guardarla desde la página, que es lo que hará el colaborador real.

⚠️ Escribe en la base a la que apunte DATABASE_URL (en el VPS: producción).
Todo lo que crea se identifica por nombre y `--borrar` lo quita entero.
`record_sale_breakdown` de las ventas reales NO se ve afectado: estas filas
son manuales (order_id NULL), el mismo tipo que la pestaña Ventas borra.
"""
from __future__ import print_function

import os
import sys
from datetime import datetime, timedelta, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

try:
    import app as A
except Exception as e:                                    # pragma: no cover
    falta = 'No module named' in str(e)
    sys.exit('no se pudo cargar la app: %s%s' % (
        e, ('\n\n👉 Usa el intérprete del entorno:\n'
            '   venv/bin/python3 %s' % os.path.relpath(__file__, RAIZ))
        if falta else ''))

USUARIO = 'demo_colab'
CLAVE = 'DemoColab26!x'
CODIGO = 'DEMO20'
NOMBRE = 'Demo Colaborador'


def main():
    aplicar = '--aplicar' in sys.argv
    borrar = '--borrar' in sys.argv

    with A.app.app_context():
        u = A.User.query.filter_by(username=USUARIO).first()
        pc = A.PromoCode.query.filter_by(code=CODIGO).first()
        ventas = A.SaleBreakdown.query.filter_by(partner=NOMBRE).all()

        if borrar:
            if not (u or pc or ventas):
                print('no hay nada de la demo que borrar.')
                return 0
            print('a borrar: cuenta=%s código=%s ventas=%d'
                  % (bool(u), bool(pc), len(ventas)))
            if not aplicar:
                print('(mirando) repite con --borrar --aplicar para ejecutarlo.')
                return 0
            for v in ventas:
                A.db.session.delete(v)
            if pc:
                A.db.session.delete(pc)
            if u:
                # 🔴 Borrar el User a secas REVIENTA en cuanto alguien ha usado
                # la cuenta: al entrar una vez se le crea un `known_device`, y
                # su `user_id` no admite nulo, así que PostgreSQL rechaza el
                # DELETE entero (pasó el 2026-08-13, con la demo ya usada).
                # Se reusa el MISMO barrido del borrado de cuenta real —
                # `BORRAR_AL_ELIMINAR` es la única lista que sabe qué cuelga de
                # un usuario, y repetirla a mano aquí es como se desincroniza.
                borradas = A._borrar_datos_personales(u)
                # Y lo que ese barrido CONSERVA a propósito (cobros y
                # auditoría, atados a la fila anonimizada): aquí la fila
                # desaparece del todo, así que también tienen que irse.
                for nombre in A.CONSERVAR_AL_ELIMINAR:
                    modelo = getattr(A, nombre, None)
                    if modelo is None or not hasattr(modelo, 'user_id'):
                        continue
                    n = modelo.query.filter_by(user_id=u.id).delete(
                        synchronize_session=False)
                    if n:
                        borradas[nombre] = n
                if borradas:
                    print('   · filas dependientes: %s'
                          % ', '.join('%s×%d' % (k, v)
                                      for k, v in sorted(borradas.items())))
                A.db.session.delete(u)
            A.db.session.commit()
            print('demo del colaborador borrada entera.')
            return 0

        if u or pc or ventas:
            sys.exit('la demo YA existe (cuenta=%s, código=%s, ventas=%d). '
                     'Borra primero con --borrar --aplicar.'
                     % (bool(u), bool(pc), len(ventas)))

        hoy = datetime.now(timezone.utc)
        inicio = (hoy - timedelta(days=20)).date()
        # 5 clientes, todos en el tramo 1 (30%): una renovación (el cliente 1
        # paga dos veces = 6 ventas, 5 puestos), una comisión ya pagada y el
        # resto pendiente — así el panel enseña TODOS sus estados a la vez.
        VENTAS = [
            ('cliente_a', 1, 'premium', 40.0, 'paid', 18),
            ('cliente_b', 2, 'standard', 20.0, 'pending', 15),
            ('cliente_c', 3, 'premium', 40.0, 'pending', 11),
            ('cliente_a', 1, 'premium', 40.0, 'pending', 8),   # renovación
            ('cliente_d', 4, 'standard', 20.0, 'pending', 5),
            ('cliente_e', 5, 'premium', 40.0, 'pending', 2),
        ]
        print('crearía: cuenta %s · código %s (%s) · inicio %s · %d ventas'
              % (USUARIO, CODIGO, NOMBRE, inicio, len(VENTAS)))
        for quien, pos, plan, neto, st, hace in VENTAS:
            print('   · %-9s puesto %d  %-8s $%.2f → comisión $%.2f (30%%) %s'
                  % (quien, pos, plan, neto, neto * .3, st))
        if not aplicar:
            print('\n(mirando) no se escribió nada. Repite con --aplicar.')
            return 0

        u = A.User(username=USUARIO, email='demo_colab@tradeable.invalid',
                   email_verified=True, plan='free')
        u.set_password(CLAVE)
        u.email_canonical = u.email
        u.partner_since = inicio
        A.db.session.add(u)
        A.db.session.flush()
        A.db.session.add(A.PromoCode(
            code=CODIGO, discount_pct=20, creator_name=NOMBRE, kind='creator',
            owner_user_id=u.id, valid_for='monthly', active=True))
        for quien, pos, plan, neto, st, hace in VENTAS:
            A.db.session.add(A.SaleBreakdown(
                username=quien, plan=plan, billing_cycle='monthly',
                gross=round(neto / 0.8, 2), discount_pct=20.0,
                discount_amt=round(neto / 0.8 - neto, 2), net_paid=neto,
                processor='manual', processor_fee=0.0, fee_is_real=False,
                promo_code=CODIGO, partner=NOMBRE, position=pos,
                commission_pct=30.0, commission_amt=round(neto * .3, 2),
                commission_status=st,
                commission_paid_at=(hoy if st == 'paid' else None),
                sold_at=hoy - timedelta(days=hace), is_manual=True))
        A.db.session.commit()
        print('\n✅ listo. Para verlo:')
        print('   · como ADMIN: tu menú → Panel de colaborador (verás su bloque)')
        print('   · como ÉL: entra con  %s / %s' % (USUARIO, CLAVE))
        print('     ⚠️ con el candado PREVIEW_USERS activo, TODO el sitio (incluido')
        print('        /partner) le da "Próximamente": añade %s a la lista' % USUARIO)
        print('        mientras pruebas, y quítalo al borrar la demo.')
        print('   · prueba guardar su billetera desde su panel: es el flujo del 4.4')
        print('\nPara deshacerlo TODO: tools/simula_socio.py --borrar --aplicar')
        return 0


if __name__ == '__main__':
    sys.exit(main())
