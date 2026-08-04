# -*- coding: utf-8 -*-
"""Convierte a PNG las páginas que dejó `gen_posts_ig.py`.

    python3 tools/gen_posts_ig.py && python3 tools/rasteriza_posts.py

Va aparte porque necesita Chromium (Playwright) y el generador no: así se puede
revisar el HTML en cualquier navegador sin instalar nada.

⚠️ `device_scale_factor=1`: el lienzo YA mide 1080 px de ancho, que es la
resolución que Instagram quiere. A densidad 2 saldrían 2160 px y la red los
recomprime, que es peor.
"""
import io
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'out', 'posts_ig')
CHROMIUM = os.environ.get('CHROMIUM_PATH', '/opt/pw-browsers/chromium')


def main():
    plan_p = os.path.join(SALIDA, 'plan.json')
    if not os.path.exists(plan_p):
        sys.exit('Falta %s — corre antes tools/gen_posts_ig.py' % plan_p)
    plan = json.load(io.open(plan_p))
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit('Falta playwright:  pip install playwright')

    with sync_playwright() as p:
        args = {'executable_path': CHROMIUM} if os.path.exists(CHROMIUM) else {}
        nav = p.chromium.launch(**args)
        for it in plan:
            pg = nav.new_page(viewport={'width': 1080, 'height': it['alto']},
                              device_scale_factor=1)
            # todo va embebido en la página: se corta la red para no esperar a
            # ningún CDN (y para que el resultado no dependa de que responda)
            pg.route('**/*', lambda r: r.abort()
                     if r.request.url.startswith('http') else r.continue_())
            pg.goto('file://' + os.path.join(SALIDA, it['archivo'] + '.html'),
                    wait_until='domcontentloaded')
            time.sleep(.45)
            pg.screenshot(path=os.path.join(SALIDA, it['archivo'] + '.png'))
            pg.close()
        nav.close()
    print('%d PNG en %s' % (len(plan), SALIDA))


if __name__ == '__main__':
    main()
