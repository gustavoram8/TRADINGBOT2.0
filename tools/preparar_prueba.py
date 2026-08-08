# -*- coding: utf-8 -*-
"""Deja una cuenta lista para el ensayo de compra, y el cupón creado.

    venv/bin/python3 tools/preparar_prueba.py gussytrades              # mira
    venv/bin/python3 tools/preparar_prueba.py gussytrades --aplicar    # hace

Sin `--aplicar` NO toca nada: solo informa de cómo está la cuenta. Se lee
primero, se aplica después.

Qué hace falta para que el ensayo sirva, y por qué cada cosa:

  1. **Que la cuenta esté en Free.** El sitio prohíbe comprar el plan que ya
     tienes, y comprar uno más barato es un cambio PROGRAMADO (no abre una
     suscripción nueva). Desde Free, la compra es la de un cliente de verdad.
  2. **Que no le quede ninguna suscripción viva.** Es lo más importante de
     todo: bajar el plan en la base NO corta el permiso de cobro que PayPal
     tiene guardado. Si queda una viva, a tu hermano le siguen cobrando cada
     mes aunque en el sitio figure como Free. Aquí se cortan EN PAYPAL, que es
     donde vive el permiso.
  3. **Que no arrastre pedidos pendientes.** Un pendiente viejo se puede pagar
     desde su enlace antiguo y entrega el plan de entonces, no el del ensayo.
  4. **El cupón.** Uno general (`kind='discount'`), de un solo uso, para que
     el descuento CADUQUE tras el primer mes — que es justo lo que se quiere
     comprobar. Un código de creador no sirve: ese descuento es permanente a
     propósito, y no probaría nada.

⚠️ Esto corre contra la base de PRODUCCIÓN y contra PayPal LIVE. Por eso el
modo de mirar es el de por defecto.
"""
from __future__ import print_function

import os
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

try:
    import app as A
except ImportError as exc:
    print('\n⛔ Falta una dependencia (%s).\n'
          '   En el VPS este archivo se corre con el Python del entorno:\n\n'
          '       cd /var/www/TRADINGBOT2.0 && venv/bin/python3 '
          'tools/preparar_prueba.py gussytrades\n' % exc)
    sys.exit(2)


def _codigo_viejo_en_marcha():
    """¿El sitio que atiende a los clientes es más antiguo que el código?

    Existe porque este archivo importa el código FRESCO del disco, mientras que
    quien atiende la web es gunicorn, que se quedó con el que tenía al
    arrancar. Sin reiniciar, un arreglo pusheado no existe para el comprador —
    y el síntoma es desconcertante: la herramienta dice que lo dejó todo bien y
    el navegador sigue comportándose como antes.

    Devuelve (hay_proceso_viejo, minutos_de_desfase) o (False, 0) si no se
    puede saber (otro sistema operativo, sin /proc, permisos).
    """
    try:
        codigo = max(os.path.getmtime(os.path.join(RAIZ, 'scalpel', f))
                     for f in ('app.py',))
        viejo = False
        desfase = 0.0
        for pid in os.listdir('/proc'):
            if not pid.isdigit():
                continue
            try:
                with open('/proc/%s/cmdline' % pid, 'rb') as f:
                    cmd = f.read().decode('utf-8', 'replace')
                if 'gunicorn' not in cmd:
                    continue
                arranque = os.stat('/proc/%s' % pid).st_mtime
            except OSError:
                continue
            if arranque < codigo:
                viejo = True
                desfase = max(desfase, (codigo - arranque) / 60.0)
        return viejo, desfase
    except Exception:
        return False, 0.0


def _canjes_pagados(pc):
    """Cuántas cuentas distintas compraron DE VERDAD con este código.

    Es lo que `uses_count` significa desde que el canje se anota al cobrar. Un
    número mayor solo puede venir de una reserva colgada del sistema anterior,
    que apuntaba el uso al poner el cupón en el carrito: agotaba el código sin
    que nadie hubiera pagado, y ni cancelando el pedido se soltaba.
    """
    if pc is None:
        return 0
    return (A.db.session.query(A.Order.user_id)
            .filter(A.db.func.lower(A.Order.promo_code) == pc.code.lower(),
                    A.Order.status == 'paid')
            .distinct().count())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    quien = args[0] if args else 'gussytrades'
    cupon = 'PRUEBA90'
    pct = 90
    for f in list(flags):
        if f.startswith('--cupon='):
            cupon = f.split('=', 1)[1].strip().upper()
            flags.discard(f)
        elif f.startswith('--pct='):
            pct = int(f.split('=', 1)[1])
            flags.discard(f)
    aplicar = '--aplicar' in flags

    with A.app.app_context():
        u = A.User.query.filter(A.db.func.lower(A.User.username)
                                == quien.lower()).first()
        if u is None:
            print('\n⛔ No existe ninguna cuenta llamada "%s".' % quien)
            return 1

        rancio, desfase = _codigo_viejo_en_marcha()
        if rancio:
            print('\n🔴 EL SITIO ESTÁ CORRIENDO CÓDIGO VIEJO')
            print('   Hay un proceso arrancado %d min ANTES del código que hay'
                  ' en disco.' % desfase)
            print('   Mientras no se reinicie, el arreglo del cupón no existe '
                  'para el comprador:\n   cada intento de pago se lo vuelve a '
                  'gastar, pase lo que pase aquí.')
            print('   Arréglalo antes de nada:  supervisorctl restart '
                  'traderacelerator')

        print('\n══ cuenta: %s ' % u.username + '═' * 44)
        print('  plan actual : %s%s' % (
            u.plan, '  (vence %s)' % u.plan_expires_at.strftime('%Y-%m-%d')
            if u.plan_expires_at else ''))

        # 1 · el candado de preview
        if A.PREVIEW_USERS and u.username.lower() not in A.PREVIEW_USERS:
            print('  ⛔ NO está en PREVIEW_USERS: ni siquiera vería el sitio.')
            print('     Arreglo: python3 tools/set_env.py PREVIEW_USERS=%s,%s'
                  % (','.join(sorted(A.PREVIEW_USERS)), u.username.lower()))
        else:
            print('  ✅ puede entrar al sitio (candado de preview)')

        # 2 · permisos de cobro vivos en PayPal
        subs = A.subs_por_cortar(u)
        if subs:
            print('\n  🔴 %d permiso(s) de cobro VIVOS — a esta cuenta le '
                  'pueden seguir cobrando:' % len(subs))
            for s in subs:
                print('     · #%s %s $%s/%s · %s · PayPal %s'
                      % (s.id, s.plan, s.price, s.billing_cycle, s.status,
                         s.provider_ref or '(sin id)'))
        else:
            print('  ✅ sin suscripciones vivas: nadie le va a cobrar nada')

        # 3 · pedidos pendientes
        pend = (A.Order.query
                .filter(A.Order.user_id == u.id, A.Order.status == 'pending')
                .order_by(A.Order.id.desc()).all())
        if pend:
            print('\n  ⚠️  %d pedido(s) pendientes (pagables desde su enlace '
                  'viejo):' % len(pend))
            for o in pend:
                print('     · #%s %s/%s $%.2f%s'
                      % (o.id, o.plan, o.billing_cycle, o.final_price or 0,
                         ' cupón=%s' % o.promo_code if o.promo_code else ''))
        else:
            print('  ✅ sin pedidos pendientes')

        # 4 · el cupón
        pc = A.PromoCode.query.filter(A.db.func.lower(A.PromoCode.code)
                                      == cupon.lower()).first()
        canjes = _canjes_pagados(pc) if pc else 0
        if pc:
            print('\n  cupón %s: ya existe · %s%% · tipo=%s · usos=%s/%s · %s'
                  % (pc.code, pc.discount_pct, pc.kind, pc.uses_count or 0,
                     pc.max_uses if pc.max_uses is not None else '∞',
                     'activo' if pc.active else 'desactivado'))
            if pc.kind == 'creator':
                print('     ⛔ es de CREADOR: su descuento es permanente a '
                      'propósito. Para este ensayo hace falta uno general.')
            if (pc.uses_count or 0) > canjes:
                # Reserva colgada del sistema viejo (el uso se apuntaba al
                # PONER el cupón en el carrito, no al cobrar): agota el cupón
                # sin que nadie haya pagado nunca.
                print('     ⚠️  contador inflado: marca %s usos pero solo hay '
                      '%s compra(s) pagada(s).' % (pc.uses_count or 0, canjes))
                print('        Con --aplicar se corrige a %s.' % canjes)
        else:
            print('\n  cupón %s: no existe todavía (%s%%, un solo uso)'
                  % (cupon, pct))

        if not aplicar:
            print('\n── esto es solo la foto. Para dejarlo listo: ' + '─' * 14)
            print('   venv/bin/python3 tools/preparar_prueba.py %s --aplicar\n'
                  % u.username)
            return 0

        # ── aplicar ──────────────────────────────────────────────────────
        print('\n══ aplicando ' + '═' * 47)
        sin_cortar = []
        for s in subs:
            cortada = False
            try:
                cortada = A._paypal_sub_cancel(s, 'Preparación de ensayo')
            except Exception as exc:
                print('  ⚠️  #%s: PayPal no respondió (%s)' % (s.id, exc))
            if cortada or not s.provider_ref:
                s.status = 'cancelled'
                s.cancelled_at = datetime.now(timezone.utc)
                print('  ✅ suscripción #%s cortada%s'
                      % (s.id, '' if s.provider_ref else ' (nunca llegó a PayPal)'))
            else:
                # No se marca como cancelada lo que PayPal sigue teniendo viva:
                # decir "cortado" sin haberlo cortado es cómo se acaba cobrando
                # a alguien que cree que se dio de baja.
                sin_cortar.append(s)
                print('  ⛔ suscripción #%s NO se pudo cortar en PayPal' % s.id)
        A.db.session.commit()

        if sin_cortar:
            # 🔴 Se PARA aquí a propósito. Bajar el plan dejando vivo el permiso
            # de cobro produce lo peor de los dos mundos: la cuenta figura
            # gratuita en el sitio y PayPal le sigue cobrando cada mes. Mientras
            # no se corte, es preferible que el plan y el cobro sigan
            # coincidiendo.
            print('\n  ⛔ ME DETENGO: el plan NO se ha tocado.')
            print('     Con un permiso de cobro vivo, dejar la cuenta en Free '
                  'sería\n     mostrarla como gratuita mientras le siguen '
                  'cobrando.')
            print('     Córtala en paypal.com (Actividad → Suscripciones) o '
                  'desde\n     Ajustes de la propia cuenta, y vuelve a correr '
                  'esto.')
            return 1

        for o in pend:
            A._soltar_pedido(o, 'preparación de ensayo')
            print('  ✅ pedido #%s soltado' % o.id)

        if u.plan != 'free':
            viejo = u.plan
            u.plan = 'free'
            u.plan_cycle = None
            u.plan_started_at = None
            u.plan_expires_at = None
            u.cancel_at_period_end = False
            A.db.session.commit()
            A.record_audit_event('plan_set_manual', user_id=u.id,
                                 detail='%s -> free (preparación de ensayo)'
                                        % viejo)
            print('  ✅ plan %s → free' % viejo)
            print('     (los camos y el XP NO se tocan: nada se revoca jamás)')
        else:
            print('  · el plan ya estaba en free')

        if pc is None:
            pc = A.PromoCode(code=cupon, discount_pct=pct, kind='discount',
                             valid_for='monthly', max_uses=1, active=True)
            A.db.session.add(pc)
            A.db.session.commit()
            print('  ✅ cupón %s creado: %s%% · general · un solo uso'
                  % (cupon, pct))
        else:
            if not pc.active:
                pc.active = True
                print('  ✅ cupón %s reactivado' % cupon)
            if (pc.uses_count or 0) > canjes:
                viejo = pc.uses_count or 0
                pc.uses_count = canjes
                print('  ✅ contador del cupón saneado: %s → %s (nadie había '
                      'pagado con él)' % (viejo, canjes))
            A.db.session.commit()
        puede, motivo = pc.is_redeemable('monthly')
        if not puede:
            print('  ⛔ el cupón SIGUE sin poder aplicarse (motivo: %s)' % motivo)
            if motivo == 'maxed':
                print('     Hay %s compra(s) PAGADA(S) con él, así que su tope '
                      'está\n     legítimamente gastado. Usa un código nuevo:'
                      % canjes)
                print('     venv/bin/python3 tools/preparar_prueba.py %s '
                      '--aplicar --cupon=PRUEBA90B' % u.username)
            return 1

        base = float(A._plan_base_price('standard', 'monthly') or 25.0)
        print('\n  estado final del cupón: %s · %s%% · usos %s/%s · '
              'aplicable=%s'
              % (pc.code, pc.discount_pct, pc.uses_count or 0,
                 pc.max_uses if pc.max_uses is not None else '∞',
                 'SÍ' if puede else 'NO'))
        if rancio:
            print('\n  🔴 PERO EL SITIO SIGUE CON CÓDIGO VIEJO: reinícialo o el '
                  'primer\n     intento de pago volverá a agotar el cupón.')
            print('     supervisorctl restart traderacelerator')
        print('\n══ ahora, desde la cuenta %s ' % u.username + '═' * 26)
        print('  1. Entra a /pricing y elige Standard mensual.')
        print('  2. Aplica el cupón %s → el carrito debe decir:' % cupon)
        print('     «Primer mes $%.2f. Desde el mes 2 se renueva a $%.2f/mes»'
              % (round(base * (100 - pc.discount_pct) / 100.0, 2), base))
        print('  3. Pulsa pagar, llega a PayPal y CIERRA esa pantalla sin '
              'aprobar.')
        print('     (no hace falta pagar nada: PayPal ya anotó los importes)')
        print('  4. Vuelve aquí y corre:')
        print('     venv/bin/python3 tools/check_suscripcion.py %s\n'
              % u.username)
        return 0


if __name__ == '__main__':
    sys.exit(main())
