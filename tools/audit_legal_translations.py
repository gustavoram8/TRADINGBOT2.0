# -*- coding: utf-8 -*-
"""¿Dice cada traducción lo mismo que el inglés?

Los Términos se redactan en inglés y se traducen. Un error de traducción en
una cláusula de dinero no es un matiz: si el español dice noventa días donde
el inglés dice noventa, bien; si dice nueve, el cliente puede exigir lo que
diga su idioma. Esto compara, cláusula por cláusula:

  · los números — plazos, montos, cantidades: deben coincidir exactamente;
  · el tamaño — una traducción mucho más corta suele ser un párrafo perdido.

No juzga estilo ni matices: marca lo que cambia una obligación. Correr después
de tocar terms.html, privacy.html o legal_i18n.js:

    python3 tools/audit_legal_translations.py
"""
import io, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _legal_extract import english_bodies          # noqa: E402

JS = 'scalpel/static/legal_i18n.js'
LANGS = ('es', 'fr', 'pt')


def _strip(html):
    t = re.sub(r'<[^>]+>', ' ', html)
    for a, b in (('&amp;', '&'), ('&nbsp;', ' '), ('&quot;', '"'),
                 ('&#39;', "'"), ('&lt;', '<'), ('&gt;', '>')):
        t = t.replace(a, b)
    return re.sub(r'\s+', ' ', t).strip()


def translated_bodies():
    """Cada traducción, leyendo los strings del diccionario tal cual."""
    s = io.open(JS, encoding='utf-8').read()
    out = {}
    for lang in LANGS:
        i = s.index('\n    %s: {' % lang)
        block = s[i:s.index('\n    }', i)]
        d = {}
        for m in re.finditer(r"'((?:terms|priv)\.[a-z0-9]+)':\s*(['\"])", block):
            key, quote = m.group(1), m.group(2)
            k, buf = m.end(), []
            while k < len(block):
                ch = block[k]
                if ch == '\\':                    # comilla escapada dentro del texto
                    buf.append(block[k + 1]); k += 2; continue
                if ch == quote:
                    break
                buf.append(ch); k += 1
            d[key] = _strip(''.join(buf))
        out[lang] = d
    return out


def numbers(text):
    """Cifras y montos. El decimal europeo (100,00 vs $100.00) se normaliza:
    es la misma cantidad escrita con la puntuación de cada idioma."""
    found = []
    for raw in re.findall(r'\$?\s?\d[\d.,]*\s?%?', text):
        n = raw.strip().lstrip('$').strip().rstrip('.,')
        n = n.replace('.', '').replace(',', '')       # 100,00 y 100.00 → 10000
        found.append(n.rstrip('0').rstrip() if n.endswith('00') and len(n) > 3 else n)
    return sorted(found)


def main():
    en, tr = english_bodies(), translated_bodies()
    problems, checked = [], 0
    for key in sorted(en):
        english = en[key]
        if len(english) < 40:                 # títulos e índices: nada que interpretar
            continue
        for lang in LANGS:
            text = tr[lang].get(key)
            if not text:
                problems.append((lang, key, 'FALTA la traducción', ''))
                continue
            checked += 1
            a, b = numbers(english), numbers(text)
            if a != b:
                problems.append((lang, key, 'NÚMEROS distintos',
                                 'solo EN %s · solo %s %s'
                                 % ([x for x in a if x not in b], lang.upper(),
                                    [x for x in b if x not in a])))
            ratio = len(text) / max(1, len(english))
            if ratio < 0.75 or ratio > 1.6:
                problems.append((lang, key, 'LARGO sospechoso',
                                 'ratio %.2f (EN %d, %s %d)'
                                 % (ratio, len(english), lang, len(text))))
    print('Cláusulas de fondo comparadas: %d' % checked)
    if not problems:
        print('✅ Números y estructura coinciden en los tres idiomas.')
        return 0
    print('\n%d hallazgo(s):' % len(problems))
    for lang, key, kind, detail in problems:
        print('  [%s] %-18s %s%s' % (lang.upper(), key, kind, ' — ' + detail if detail else ''))
    return 1


if __name__ == '__main__':
    sys.exit(main())
