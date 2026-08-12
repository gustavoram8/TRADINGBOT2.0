# -*- coding: utf-8 -*-
"""Mete la demo de Pre-Flight en una cuenta REAL, para poder mirarla en pantalla.

    venv/bin/python3 tools/demo_a_mi_cuenta.py maurotradesve             # mira
    venv/bin/python3 tools/demo_a_mi_cuenta.py maurotradesve --aplicar   # hace
    venv/bin/python3 tools/demo_a_mi_cuenta.py maurotradesve --borrar    # deshace

Sin `--aplicar` no toca nada: solo dice qué haría. Son los MISMOS proyectos y
los mismos trades de `tools/demo_preflight.py` (comparten generador en
`pf_demo_datos.py`), así que los números en pantalla coinciden con los del
informe.

⚠️ Esto escribe en la base de PRODUCCIÓN. Tres decisiones para que no haga daño:

  1. **No pasa por la API, escribe con el modelo.** Registrar 92 chequeos por
     `/api/preflight/checks` regalaría XP de Pre-Flight y podría subir de rango
     a la cuenta por unos datos de mentira. Escribiendo el modelo directamente,
     el XP no se toca.
  2. **Se puede deshacer entero.** `--borrar` elimina exactamente las 3
     pizarras y sus chequeos, y nada más — se identifican por nombre.
  3. **Ocupan 3 de las 10 pizarras** que permite Premium. Se avisa antes.

Los trades se fechan hacia atrás desde hoy, así que en pantalla se ven como
actividad reciente.
"""
from __future__ import print_function

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

try:
    import app as A
except Exception as e:                                   # pragma: no cover
    sys.exit('no se pudo cargar la app: %s' % e)

import pf_demo_datos as D                                # noqa: E402

NOMBRES = [p['nombre'] for p in D.PROYECTOS]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    aplicar = '--aplicar' in sys.argv
    borrar = '--borrar' in sys.argv
    if not args:
        sys.exit('falta el usuario: tools/demo_a_mi_cuenta.py <usuario> [--aplicar|--borrar]')
    usuario = args[0]

    with A.app.app_context():
        u = A.User.query.filter_by(username=usuario).first()
        if u is None:
            u = A.User.query.filter_by(email=usuario).first()
        if u is None:
            sys.exit('no existe ninguna cuenta "%s"' % usuario)
        print('cuenta: %s (id %d) · plan %s' % (u.username, u.id, u.plan))
        if u.plan != 'premium' and not u.is_admin:
            print('⚠️  Pre-Flight es solo de Premium: esta cuenta no vería el panel.')

        ya = (A.PreflightChecklist.query
              .filter(A.PreflightChecklist.user_id == u.id,
                      A.PreflightChecklist.name.in_(NOMBRES)).all())
        total_pizarras = A.PreflightChecklist.query.filter_by(user_id=u.id).count()

        if borrar:
            if not ya:
                print('no hay nada de la demo que borrar.')
                return
            n = 0
            for cl in ya:
                n += (A.PreflightCheck.query
                      .filter_by(user_id=u.id, checklist_id=cl.id).delete())
                A.db.session.delete(cl)
            # los chequeos huérfanos (por nombre) que hubieran quedado sueltos
            n += (A.PreflightCheck.query
                  .filter(A.PreflightCheck.user_id == u.id,
                          A.PreflightCheck.checklist_name.in_(NOMBRES),
                          A.PreflightCheck.checklist_id.is_(None)).delete(
                              synchronize_session=False))
            if not aplicar:
                A.db.session.rollback()
                print('(mirando) borraría %d pizarras y %d chequeos. Repite con --aplicar.'
                      % (len(ya), n))
                return
            A.db.session.commit()
            print('borradas %d pizarras y %d chequeos.' % (len(ya), n))
            return

        if ya:
            sys.exit('esa cuenta YA tiene la demo (%s). Bórrala primero con --borrar.'
                     % ', '.join(c.name for c in ya))
        libres = A.PROJECT_LIMITS.get('premium', 10) - total_pizarras
        print('pizarras que ya tiene: %d · la demo añade 3 (quedan %d libres)'
              % (total_pizarras, libres - 3))
        if libres < 3:
            sys.exit('no caben 3 pizarras más (tope %d).' % A.PROJECT_LIMITS.get('premium', 10))

        datos = D.genera()
        for p, cfg, trades, res in datos:
            print('  %-24s %d trades · %dW %dL %d no tomados · P&L %s'
                  % (res['proyecto'], res['registrados'], res['ganados'],
                     res['perdidos'], res['no_tomados'], res['pnl']))
            if not aplicar:
                continue
            cl = A.PreflightChecklist(user_id=u.id, name=p['nombre'],
                                      config=A._sanitize_checklist_config(cfg))
            A.db.session.add(cl)
            A.db.session.flush()
            for t in trades:
                A.db.session.add(A.PreflightCheck(
                    user_id=u.id, checklist_id=cl.id,
                    checklist_name=t['checklist_name'], checked=t['checked'],
                    total=t['total'], score=len(t['checked']),
                    verdict=t['verdict'], outcome=t['outcome'],
                    trade_date=t['trade_date'], instrument=t['instrument'],
                    direction=t['direction'], entry_price=t['entry_price'],
                    exit_price=t['exit_price'], rr=t['rr'],
                    position_size=t['position_size'], pnl=t['pnl'],
                ))
        if not aplicar:
            print('\n(mirando) no se escribió nada. Repite con --aplicar.')
            return
        A.db.session.commit()
        print('\nlisto: 3 pizarras y %d trades en la cuenta de %s.'
              % (sum(len(t) for _, _, t, _ in datos), u.username))
        print('Para deshacerlo: tools/demo_a_mi_cuenta.py %s --borrar --aplicar' % usuario)


if __name__ == '__main__':
    main()
