# -*- coding: utf-8 -*-
"""El inglés de cada cláusula, leído con un parser de verdad."""
from html.parser import HTMLParser
import io, re

VOID = {'br', 'img', 'input', 'hr', 'meta', 'link'}


class Grab(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = {}
        self.stack = []       # (tag, key_or_None)
        self.capturing = None  # (key, depth, [chunks])

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        d = dict(attrs)
        key = d.get('data-i18n-html') or d.get('data-i18n')
        self.stack.append(tag)
        if self.capturing is None and key and re.match(r'^(terms|priv)\.', key):
            self.capturing = (key, len(self.stack), [])

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.capturing and len(self.stack) == self.capturing[1]:
            key, _, chunks = self.capturing
            text = re.sub(r'\s+', ' ', ' '.join(chunks)).strip()
            if text and (key not in self.out or len(text) > len(self.out[key])):
                self.out[key] = text
            self.capturing = None
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.capturing:
            self.capturing[2].append(data)


def english_bodies():
    out = {}
    for path in ('scalpel/templates/terms.html', 'scalpel/templates/privacy.html'):
        src = io.open(path, encoding='utf-8').read()
        src = re.sub(r'\{%.*?%\}', ' ', src, flags=re.S)   # sin lógica de plantilla
        src = re.sub(r'<style.*?</style>', ' ', src, flags=re.S)
        src = re.sub(r'<script.*?</script>', ' ', src, flags=re.S)
        g = Grab(); g.feed(src)
        out.update(g.out)
    return out


if __name__ == '__main__':
    en = english_bodies()
    print('claves:', len(en))
    for k in ('terms.b5', 'terms.b7', 'terms.t5', 'priv.b2', 'terms.controlling'):
        print('%-18s %5d chars | %s' % (k, len(en.get(k, '')), en.get(k, '')[:90]))
