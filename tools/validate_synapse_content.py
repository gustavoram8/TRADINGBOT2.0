# -*- coding: utf-8 -*-
"""Valida el contenido de Synapse (base EN + overrides ES/FR/PT).

    python3 tools/validate_synapse_content.py

Existe por el punto 12: el contenido de profundidad se escribe POR TANDAS
(como el DAILY_BANK), y un descuido de tanda no da ningún error — solo un PDF
más flaco en un idioma, o un enlace conectado que apunta a un tema que no
existe. Esto lo caza antes de commitear.

Qué comprueba:
  · Paridad de los campos de profundidad: si un tema tiene 'playbook'/'fails'/
    'drill'/'related' en EN, tiene que tenerlos en ES, FR y PT (y al revés:
    un idioma no puede traer lo que el EN no tiene).
  · Cada 'related' apunta a un slug REAL del catálogo, no se apunta a sí
    mismo, y trae entre 1 y 3 entradas con su 'why'.
  · Longitudes: la traducción de un campo no puede medir menos de la mitad ni
    más del doble que su original (un campo vacío o un pegote doblado se ven
    aquí).
  · El 'playbook' tiene entre 3 y 6 pasos, y 'fails' entre 1 y 4 puntos.
"""
import io
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMPOS = ('playbook', 'fails', 'drill', 'related')


def carga(nombre):
    with io.open(os.path.join(RAIZ, 'scalpel', 'static', nombre), encoding='utf-8') as f:
        return json.load(f)


def texto_de(v):
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return ' '.join(texto_de(x) for x in v)
    if isinstance(v, dict):
        return ' '.join(texto_de(x) for x in v.values())
    return ''


def main():
    base = carga('synapse_export.json')
    slugs = set(base)
    idiomas = {l: carga('synapse_content_%s.json' % l) for l in ('es', 'fr', 'pt')}
    errores = []
    con_profundidad = 0

    for slug, tema in sorted(base.items()):
        cont = tema.get('content') or {}
        tiene = {c for c in CAMPOS if cont.get(c)}
        if tiene and tiene != set(CAMPOS):
            errores.append('%s: EN tiene solo %s — la tanda va COMPLETA o no va'
                           % (slug, sorted(tiene)))
        if not tiene:
            # sin tanda: los idiomas tampoco deben traerla a medias
            for l, d in idiomas.items():
                extra = {c for c in CAMPOS if (d.get(slug) or {}).get(c)}
                if extra:
                    errores.append('%s [%s]: trae %s pero el EN no tiene tanda'
                                   % (slug, l, sorted(extra)))
            continue
        con_profundidad += 1

        rel = cont.get('related') or []
        if not (1 <= len(rel) <= 3):
            errores.append('%s: related trae %d entradas (1-3)' % (slug, len(rel)))
        for r in rel:
            s2 = (r or {}).get('slug', '')
            if s2 not in slugs:
                errores.append('%s: related apunta a "%s", que NO existe' % (slug, s2))
            if s2 == slug:
                errores.append('%s: related se apunta a sí mismo' % slug)
            if not (r or {}).get('why'):
                errores.append('%s: related "%s" sin why' % (slug, s2))
        pb = cont.get('playbook') or []
        if not (3 <= len(pb) <= 6):
            errores.append('%s: playbook con %d pasos (3-6)' % (slug, len(pb)))
        fl = cont.get('fails') or []
        fl = [fl] if isinstance(fl, str) else fl
        if not (1 <= len(fl) <= 4):
            errores.append('%s: fails con %d puntos (1-4)' % (slug, len(fl)))

        for l, d in idiomas.items():
            trad = d.get(slug) or {}
            for c in CAMPOS:
                if not trad.get(c):
                    errores.append('%s [%s]: falta %s' % (slug, l, c))
                    continue
                if c == 'related':
                    en_slugs = [x.get('slug') for x in rel]
                    tr_slugs = [x.get('slug') for x in (trad[c] or [])]
                    if en_slugs != tr_slugs:
                        errores.append('%s [%s]: related con slugs distintos al EN'
                                       % (slug, l))
                    continue
                a, b = len(texto_de(cont[c])), len(texto_de(trad[c]))
                if b < a * 0.5 or b > a * 2.0:
                    errores.append('%s [%s]: %s mide %d vs %d del EN (ratio raro)'
                                   % (slug, l, c, b, a))
                if c == 'playbook' and len(trad[c]) != len(pb):
                    errores.append('%s [%s]: playbook con %d pasos vs %d del EN'
                                   % (slug, l, len(trad[c]), len(pb)))

    print('temas: %d · con tanda de profundidad: %d · errores: %d'
          % (len(base), con_profundidad, len(errores)))
    for e in errores[:40]:
        print('  ✗', e)
    return 1 if errores else 0


if __name__ == '__main__':
    sys.exit(main())
