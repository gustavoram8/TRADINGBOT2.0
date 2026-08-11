# -*- coding: utf-8 -*-
"""Antes/después REAL del arreglo del scroll, medido píxel a píxel.

Se sirve el template viejo y el nuevo con el MISMO servidor, la misma cuenta y
el mismo viewport, y se comparan las capturas. El objetivo no es una opinión
("no se nota"), sino un número: cuántos píxeles cambian y cuánto.
"""
import glob
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

RAIZ = '/home/user/TRADINGBOT2.0'
OUT = ('/tmp/claude-0/-home-user-TRADINGBOT2-0/'
       '76bc4b43-7526-5346-b38c-f5b6471f49f5/scratchpad/')
TPL = os.path.join(RAIZ, 'scalpel', 'templates', 'index.html')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
os.environ['DATABASE_URL'] = 'sqlite:///' + OUT + 'tour.db'
os.environ.setdefault('SECRET_KEY', 'comp-visual')

from playwright.sync_api import sync_playwright   # noqa: E402
from PIL import Image, ImageChops, ImageDraw      # noqa: E402

CL = 'Zx9!wQ4mNp2r'
PUERTO = 5089
ESCENAS = [('sin camo', '', 'light'), ('sin camo', '', 'dark'),
           ('Chronicles', 'chronicles', 'dark'),
           ('Rising Sun', 'rising-sun', 'light')]


def captura(etiqueta):
    """Arranca el server con el template que esté puesto y fotografía todo."""
    # el server se arranca en un proceso aparte para que relea el template
    pr = subprocess.Popen([sys.executable, os.path.join(RAIZ, 'scalpel', 'app.py')],
                          env=dict(os.environ, FLASK_RUN_PORT=str(PUERTO)),
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        time.sleep(.25)
        try:
            urllib.request.urlopen('http://127.0.0.1:5001/health', timeout=1)
            break
        except Exception:
            pass
    U = 'http://127.0.0.1:5001'
    import app as A
    exe = glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')[0]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe, args=['--no-sandbox'])
        pg = b.new_page(viewport={'width': 1400, 'height': 1000})
        pg.route('**/*', lambda r: r.continue_()
                 if '127.0.0.1' in r.request.url else r.abort())
        pg.goto(U + '/login', wait_until='domcontentloaded')
        pg.fill('input[name=identifier]', 'tour')
        pg.fill('input[name=password]', CL)
        pg.click('button[type=submit]')
        pg.wait_for_timeout(800)
        for nombre, camo, tema in ESCENAS:
            with A.app.app_context():
                uu = A.User.query.filter_by(username='tour').first()
                uu.active_camo = camo or None
                A.db.session.commit()
            pg.evaluate("t => localStorage.setItem('scalpel_theme', t)", tema)
            pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                                     'url': U + '/'}])
            pg.goto(U + '/app', wait_until='domcontentloaded')
            pg.wait_for_timeout(2600)
            # ⚠️ sin esto las dos capturas salen desplazadas unos px y el
            # "% de píxeles distintos" mide desalineación, no cambio visual:
            # en el mapa de diferencias se ve el texto duplicado en fantasma.
            pg.evaluate("() => window.scrollTo(0, 0)")
            pg.evaluate("() => document.fonts.ready")
            pg.wait_for_timeout(1200)
            slug = (camo or 'nocamo') + '_' + tema
            pg.screenshot(path=OUT + '%s_%s.png' % (etiqueta, slug))
        b.close()
    pr.terminate()
    pr.wait(timeout=20)
    time.sleep(1)


subprocess.run(['pkill', '-f', 'scalpel/app.py'])
time.sleep(2)
shutil.copy(OUT + 'idx_ANTES.html', TPL)
captura('ANTES')
shutil.copy(OUT + 'idx_AHORA.html', TPL)
captura('AHORA')

print('%-14s %-7s %14s %12s' % ('escena', 'modo', 'píxeles distintos',
                                'dif. máxima'))
tiras = []
for nombre, camo, tema in ESCENAS:
    slug = (camo or 'nocamo') + '_' + tema
    a = Image.open(OUT + 'ANTES_%s.png' % slug).convert('RGB')
    d = Image.open(OUT + 'AHORA_%s.png' % slug).convert('RGB')
    dif = ImageChops.difference(a, d)
    caja = dif.getbbox()
    px = dif.convert('L').point(lambda v: 255 if v > 8 else 0)
    distintos = sum(px.histogram()[255:])
    total = a.size[0] * a.size[1]
    maxdif = max(dif.getextrema(), key=lambda t: t[1])[1]
    print('%-14s %-7s %8d (%4.1f%%) %12d/255' %
          (nombre, tema, distintos, 100.0 * distintos / total, maxdif))
    # imagen: antes | después | mapa de diferencias realzado
    mapa = ImageChops.multiply(dif, Image.new('RGB', a.size, (12, 12, 12)))
    tiras.append((nombre + ' · ' + tema, a, d, mapa, caja))

k = 0.30
w, h = tiras[0][1].size
lienzo = Image.new('RGB', (int(w * k) * 3 + 40, (int(h * k) + 34) * len(tiras)),
                   (236, 236, 241))
dr = ImageDraw.Draw(lienzo)
for i, (etq, a, d, mapa, caja) in enumerate(tiras):
    y = i * (int(h * k) + 34) + 26
    for j, im in enumerate((a, d, mapa)):
        lienzo.paste(im.resize((int(w * k), int(h * k))), (10 + j * (int(w * k) + 10), y))
    dr.text((10, y - 18), '%s      ANTES  |  AHORA  |  mapa de diferencias (realzado ×12)'
            % etq, fill=(20, 20, 30))
lienzo.save(OUT + 'comparativa_visual.jpg', quality=88)
print('\nguardado:', OUT + 'comparativa_visual.jpg')
