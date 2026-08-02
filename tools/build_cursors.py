# -*- coding: utf-8 -*-
"""Publica el catálogo de cursores como PNGs de 32x32 + manifiesto.

Los cursores se DIBUJAN en tools/cursors_preview.py, pero `cursor: url(...)`
solo acepta PNG en Chrome/Safari, así que aquí se rasterizan: cada figura se
captura a 128px con Chromium (fondo transparente) y se reduce a 32px con
LANCZOS — a 32 directo los bordes salen dentados.

Por cada cursor salen DOS archivos: el normal y el `_hot` (la figura
encendida, para lo clickeable). El slug publicado lleva el prefijo `cur-`
porque `CosmeticItem.slug` es único y los cursores comparten nombre con los
marcos y camos de su misma temática/festividad (chronicles, santa...) — el
prefijo evita el choque y `festivity_of()` en app.py lo quita para que el
cursor herede la ventana de 24h de su festividad.

    python3 tools/build_cursors.py     # regenera TODO (idempotente)

Correr tras CUALQUIER cambio en cursors_preview.py y commitear lo generado.
"""
import base64
import io
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cursors_preview import CHISPAS, CURSORS, cursor_svg  # noqa: E402

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'scalpel', 'static', 'cursors')
HOTSPOT = (2, 2)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # Una sola página con todas las figuras a 128px; se captura cada <img>
    # con fondo transparente y se reduce.
    entries = []       # (archivo, indice en la página)
    imgs = []
    for slug, name, fam, defs, body, extra in CURSORS:
        hot = body + (extra or CHISPAS)
        for suffix, markup in (('', body), ('_hot', hot)):
            svg = cursor_svg(markup, defs)
            uri = ('data:image/svg+xml;base64,'
                   + base64.b64encode(svg.encode()).decode())
            entries.append('cur-%s%s.png' % (slug, suffix))
            imgs.append('<img width="128" height="128" src="%s">' % uri)
    html = ('<!doctype html><meta charset="utf-8">'
            '<body style="margin:0;display:flex;flex-wrap:wrap;">'
            + ''.join(imgs) + '</body>')
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False) as fh:
        fh.write(html)
        page_path = fh.name
    raw_dir = tempfile.mkdtemp()
    script = f'''
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path={CHROME!r})
    pg = b.new_page(viewport={{'width': 1400, 'height': 1200}})
    pg.goto('file://{page_path}')
    pg.wait_for_timeout(600)
    for i, el in enumerate(pg.query_selector_all('img')):
        el.screenshot(path='{raw_dir}/%d.png' % i, omit_background=True)
    b.close()
'''
    subprocess.run([sys.executable, '-c', script], check=True)
    os.unlink(page_path)

    from PIL import Image
    for i, fname in enumerate(entries):
        img = Image.open(os.path.join(raw_dir, '%d.png' % i)).convert('RGBA')
        img = img.resize((32, 32), Image.LANCZOS)
        img.save(os.path.join(OUT_DIR, fname), optimize=True)

    manifest = {'cur-%s' % slug: {'name': name, 'hot': HOTSPOT}
                for slug, name, fam, defs, body, extra in CURSORS}
    with open(os.path.join(OUT_DIR, 'cursors.json'), 'w') as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    print('escritos %d PNGs (%d cursores) + cursors.json en %s'
          % (len(entries), len(manifest), os.path.relpath(OUT_DIR)))


if __name__ == '__main__':
    main()
