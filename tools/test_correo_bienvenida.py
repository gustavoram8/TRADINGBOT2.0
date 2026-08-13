# -*- coding: utf-8 -*-
"""El correo de bienvenida no puede venderle humo a una cuenta Free.

    venv/bin/python3 tools/test_correo_bienvenida.py

Lo cazó el dueño: la bienvenida listaba el Quiz, el Reto Diario y la pizarra
como "por dónde empezar" — y son Premium (`@premium_required`). Un correo que
manda al recién llegado a puertas cerradas es peor que no mandar nada.

Regla que este archivo vigila, en los 4 idiomas:
  · la sección de arranque solo nombra lo que una cuenta FREE puede usar
    (analizador + guía);
  · las herramientas de pago aparecen DESPUÉS del marcador de planes, con el
    Quiz, el Reto Diario, Chalkboard, Synapse y Pre-Flight nombrados;
  · el foro aparece en STANDARD (no solo "planes de pago" a secas);
  · la nota legal-honesta y el {name} siguen ahí.
"""
from __future__ import print_function

import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'wb.db')
os.environ.setdefault('SECRET_KEY', 'welcome')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                           # noqa: E402

OK = FALLOS = 0


def check(cond, texto):
    global OK, FALLOS
    print(('  ✅ ' if cond else '  ❌ ') + texto)
    if cond:
        OK += 1
    else:
        FALLOS += 1


# El punto donde el correo pasa de "tu cuenta gratuita" a "los planes":
MARCADOR = {'en': 'And when you want more', 'es': 'Y cuando quieras más',
            'fr': 'Et quand vous en voudrez plus', 'pt': 'E quando você quiser mais'}
QUIZ = {'en': 'Quiz', 'es': 'Quiz', 'fr': 'Quiz', 'pt': 'Quiz'}
DAILY = {'en': 'Daily Challenge', 'es': 'Reto Diario', 'fr': 'Défi quotidien',
         'pt': 'Desafio Diário'}
FORO = {'en': 'forum', 'es': 'foro', 'fr': 'forum', 'pt': 'fórum'}
LEGAL = {'en': 'never give investment advice',
         'es': 'Nunca damos consejos de inversión',
         'fr': 'jamais de conseils en investissement',
         'pt': 'Nunca damos conselhos de investimento'}


def main():
    global OK, FALLOS
    for lang in ('en', 'es', 'fr', 'pt'):
        print('\n══ %s ══' % lang)
        d = A.EMAIL_I18N['welcome'][lang]
        body = d['body']
        check('{name}' in body, 'lleva el {name}')
        m = body.find(MARCADOR[lang])
        check(m > 0, 'tiene el marcador de planes ("%s")' % MARCADOR[lang])
        gratis, pago = body[:max(m, 0)], body[m:]
        for herr in (QUIZ[lang], DAILY[lang], 'Chalkboard', 'Synapse', 'Pre-Flight'):
            check(herr not in gratis,
                  '"%s" NO se le vende a la cuenta free' % herr)
            check(herr in pago, '"%s" sí aparece en la parte de planes' % herr)
        check(FORO[lang] in pago and 'STANDARD' in pago.upper(),
              'el foro va con Standard, nombrado')
        check('PREMIUM' in pago.upper(), 'Premium descrito con sus herramientas')
        check(LEGAL[lang] in body, 'la nota honesta sigue ahí')
        check('support@tradeable.academy' in body, 'y el correo de soporte')
        try:
            body.format(name='Prueba')
            check(True, 'el .format(name=…) no revienta (sin llaves sueltas)')
        except (KeyError, IndexError, ValueError) as e:
            check(False, 'el .format revienta: %s' % e)

    print('\nRESULTADO: %d/%d' % (OK, OK + FALLOS))
    return 0 if FALLOS == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
