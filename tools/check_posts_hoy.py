# -*- coding: utf-8 -*-
"""¿Cuántas publicaciones ha gastado hoy esta cuenta, y por qué?

    venv/bin/python3 tools/check_posts_hoy.py maurotradesve gussytrades

Existe porque "el contador dice 2 y yo publiqué dos" tiene varias causas que
desde la pantalla se ven igual: que las publicaciones fueran BLOQUEADAS por
moderación (entonces nunca existieron y el cupo sigue intacto), que el día
UTC haya cambiado, o que la pantalla se hubiera quedado con una cifra vieja.
Esto imprime lo que cuenta el servidor, que es lo único que manda.

🔑 Borrar NO devuelve cupo, a propósito: el contador cuenta también las
borradas. Si no, borrar y republicar sería un límite infinito.

No escribe nada. Solo lee.
"""
from __future__ import print_function

import os
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

try:
    import app as A
except Exception as e:                                    # pragma: no cover
    sys.exit('no se pudo cargar la app: %s' % e)


def main():
    cuentas = [a for a in sys.argv[1:] if not a.startswith('-')]
    if not cuentas:
        sys.exit('uso: tools/check_posts_hoy.py <usuario> [usuario…]')

    ahora = datetime.now(timezone.utc)
    print('\n  ahora en UTC : %s   (el cupo se reinicia a las 00:00 UTC)'
          % ahora.strftime('%Y-%m-%d %H:%M'))
    print('  tope diario  : %d publicaciones por cuenta' % A.DAILY_POST_LIMIT)

    with A.app.app_context():
        for nombre in cuentas:
            u = (A.User.query.filter_by(username=nombre).first()
                 or A.User.query.filter_by(email=nombre).first())
            print('\n  ── %s ──' % nombre)
            if u is None:
                print('     🔴 no existe esa cuenta')
                continue
            hoy = ahora.date()
            todas = (A.ForumPost.query.filter_by(user_id=u.id)
                     .order_by(A.ForumPost.created_at.desc()).limit(20).all())
            de_hoy = [p for p in todas if A._as_utc(p.created_at).date() == hoy]
            gastadas = len(de_hoy)
            print('     plan %s%s' % (u.plan, ' (admin)' if u.is_admin else ''))
            print('     publicaciones creadas HOY : %d' % gastadas)
            for p in de_hoy:
                print('        · #%-4d %s  %s  %s'
                      % (p.id, A._as_utc(p.created_at).strftime('%H:%M UTC'),
                         'BORRADA' if p.is_deleted else 'visible ',
                         (p.title or '')[:40]))
            print('     le quedan HOY             : %d'
                  % max(0, A.DAILY_POST_LIMIT - gastadas))
            if gastadas == 0 and todas:
                ult = A._as_utc(todas[0].created_at)
                print('     ⚠️ Su última publicación es del %s (otro día UTC): por eso'
                      % ult.strftime('%Y-%m-%d %H:%M'))
                print('        el cupo aparece entero. Si creía haber publicado hoy, es')
                print('        que esos intentos fueron BLOQUEADOS y nunca se crearon.')
            elif gastadas == 0:
                print('     ⚠️ No tiene NINGUNA publicación. Si intentó publicar, esos')
                print('        intentos fueron bloqueados por moderación (o por el')
                print('        aviso de texto demasiado corto) y no gastan cupo.')
    print('')
    return 0


if __name__ == '__main__':
    sys.exit(main())
