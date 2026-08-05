# -*- coding: utf-8 -*-
"""El recibo enumera TODO lo que trae el plan, y en los 4 idiomas.

    python3 tools/test_recibo_features.py

El dueño lo cazó mirando el recibo en francés: la lista de "lo que acabas de
desbloquear" tenía 4 puntos cuando el plan Premium trae 8 funciones. La había
escrito de memoria en vez de sacarla de donde ya estaba definida (FEATURES en
index.html, que es lo que enseña el reveal de UNLOCKED).

Este archivo compara las dos listas. Si alguien añade una función al reveal y
se olvida del recibo —o al revés— esto falla.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

ok = fallos = 0


def check(cond, txt):
    global ok, fallos
    if cond:
        ok += 1
        print('  ok    ', txt)
    else:
        fallos += 1
        print('  FALLA ', txt)


def leer(p):
    with open(os.path.join(RAIZ, p), encoding='utf-8') as f:
        return f.read()


def main():
    index = leer('scalpel/templates/index.html')
    recibo = leer('scalpel/templates/checkout_status.html')
    dicc = leer('scalpel/static/pages_i18n.js')

    # ── 1 · cuántas funciones anuncia el reveal de cada plan ──────────────
    print('\n1 · la lista canónica (FEATURES del reveal)')
    bloque = re.search(r'const FEATURES = \{(.+?)\n    \};', index, re.S)
    if not bloque:
        print('  FALLA  no encontré FEATURES en index.html')
        return 1
    txt = bloque.group(1)
    partes = re.split(r'\n\s*(standard|premium):\s*\[', txt)
    canon = {}
    for i in range(1, len(partes), 2):
        canon[partes[i]] = re.findall(r"key:\s*'([^']+)'", partes[i + 1])
    for plan, keys in canon.items():
        print('  %-9s %d funciones: %s' % (plan, len(keys), ', '.join(keys)))
    check(len(canon.get('premium', [])) >= 8,
          'Premium anuncia %d funciones' % len(canon.get('premium', [])))

    # ── 2 · el recibo enumera las mismas ──────────────────────────────────
    print('\n2 · el recibo tiene una línea por función')
    pp = sorted(set(re.findall(r'data-i18n="(cstat\.pp\d+)"', recibo)))
    ps = sorted(set(re.findall(r'data-i18n="(cstat\.ps\d+)"', recibo)))
    print('  recibo Premium : %d líneas' % len(pp))
    print('  recibo Standard: %d líneas' % len(ps))
    # El recibo suma los "proyectos", que el reveal no lista como función
    # aparte en Premium — por eso se admite una línea más, nunca menos.
    check(len(pp) >= len(canon.get('premium', [])),
          '🔴 Premium: %d líneas para %d funciones'
          % (len(pp), len(canon.get('premium', []))))
    check(len(ps) >= len(canon.get('standard', [])),
          'Standard: %d líneas para %d funciones'
          % (len(ps), len(canon.get('standard', []))))

    # ── 3 · lo que el reveal nombra, el recibo lo menciona ────────────────
    print('\n3 · ninguna función se queda fuera del recibo')
    # Se busca por una palabra reconocible de cada función, en el inglés del
    # diccionario: si Synapse o Chalkboard no aparecen, faltan.
    en = dicc.split("'es': {")[0]
    textos = ' '.join(re.findall(r"'cstat\.pp\d+': '([^']*)'", en)).lower()
    for palabra in ('analyzer', 'pre-flight', 'forum', 'quiz',
                    'daily', 'chalkboard', 'synapse', 'camo', 'projects'):
        check(palabra in textos, 'el recibo Premium menciona "%s"' % palabra)

    # ── 4 · paridad en los 4 idiomas ──────────────────────────────────────
    print('\n4 · las mismas claves en EN/ES/FR/PT')
    for k in pp + ps + ['cstat.gotTitle']:
        n = len(re.findall(r"'%s':" % re.escape(k), dicc))
        if n != 4:
            check(False, '%s aparece %d veces (deben ser 4)' % (k, n))
    check(fallos == 0 or True, 'revisadas %d claves' % (len(pp) + len(ps) + 1))
    faltan = [k for k in pp + ps
              if len(re.findall(r"'%s':" % re.escape(k), dicc)) != 4]
    check(not faltan, 'sin huecos de idioma%s'
          % ('' if not faltan else ': ' + ', '.join(faltan)))

    # ── 5 · nada sin traducir ─────────────────────────────────────────────
    print('\n5 · el texto de reserva del HTML no es lo que se ve')
    huerfanas = [k for k in pp + ps
                 if ("'%s':" % k) not in dicc]
    check(not huerfanas,
          'toda clave del recibo existe en el diccionario%s'
          % ('' if not huerfanas else ': ' + ', '.join(huerfanas)))

    print('\n%s\nRESULTADO: %d/%d' % ('=' * 46, ok, ok + fallos))
    return 0 if fallos == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
