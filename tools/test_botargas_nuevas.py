# -*- coding: utf-8 -*-
"""Las botargas de los camos NUEVOS (gridiron y nile) en navegador REAL.

    python3 tools/test_botargas_nuevas.py

Existe por una trampa concreta: **los dos camos no keyean igual**. `nile`
tiene dos looks y va por `.light`, como naval; `gridiron` es DARK_ALWAYS (el
partido es de noche), su body NUNCA lleva `.light` y la preferencia clara se
marca con `.camo-day`. Copiar el bloque de un camo de dos looks sobre uno
DARK_ALWAYS no da error de ninguna clase: simplemente **la botarga se queda
clavada en la variante oscura** para siempre, y eso solo se ve mirando qué
archivo sirve el navegador. Por eso el test lee `getComputedStyle().content`
real y no el HTML.

Además vigila los 12 archivos: que existan, sean RGBA, tengan alfa de verdad
(un recorte fallido llega opaco de esquina a esquina) y que el `_dark` sea el
recolor —no una copia— del claro.

⚠️ `/app` BORRA el cookie `scalpel_splash_ts` al servirse: hay que volver a
   ponerlo antes de CADA visita o la siguiente rebota a `/welcome`.
"""
import glob
import os
import sys
import tempfile
import threading
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'b.db')
os.environ.setdefault('SECRET_KEY', 'botnuevas')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
import app as A  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

OK, MAL = 0, []


def caso(nombre, cond, extra=''):
    global OK
    if cond:
        OK += 1
        print('  ✅ %s' % nombre)
    else:
        MAL.append(nombre)
        print('  🔴 %s %s' % (nombre, extra))


# ── los 12 archivos ──
print('── los archivos ──')
for camo in ('gridiron', 'nile'):
    for n in (2, 3, 4):
        base = os.path.join(RAIZ, 'scalpel/static/logo%d_%s' % (n, camo))
        claro, oscuro = base + '.png', base + '_dark.png'
        if not (os.path.exists(claro) and os.path.exists(oscuro)):
            caso('logo%d_%s: existen los dos' % (n, camo), False)
            continue
        a = np.asarray(Image.open(claro).convert('RGBA')).astype(int)
        d = np.asarray(Image.open(oscuro).convert('RGBA')).astype(int)
        caso('logo%d_%s: mismo lienzo claro/oscuro' % (n, camo),
             a.shape == d.shape, '%s vs %s' % (a.shape, d.shape))
        if a.shape != d.shape:
            continue
        transp = (a[..., 3] < 20).mean()
        # Un recorte que falla deja el lienzo entero opaco; uno que se pasa
        # deja casi nada. Entre 8% y 85% es una botarga recortada de verdad.
        caso('logo%d_%s: tiene fondo recortado (%.0f%% transparente)'
             % (n, camo, 100 * transp), 0.08 < transp < 0.85)
        caso('logo%d_%s: el alfa es SUAVE, no binario' % (n, camo),
             ((a[..., 3] > 20) & (a[..., 3] < 235)).sum() > 500)
        # 🔴 El VELO del tablero: si el escalón del cuadriculado se corrige
        #    con un número fijo en vez del medido, el fondo no llega a alfa 0
        #    y queda una nube de píxeles casi transparentes con forma de
        #    cuadros. No rompe nada, no da error — solo se ve. Antes de
        #    medir el escalón por lámina, logo3_nile traía 4,3%.
        velo = ((a[..., 3] > 0) & (a[..., 3] < 20)).mean()
        caso('logo%d_%s: sin velo de cuadrícula (%.2f%% casi-transparente)'
             % (n, camo, 100 * velo), velo < 0.01)
        cambia = (np.abs(a[..., :3] - d[..., :3]).sum(2) > 20).mean()
        caso('logo%d_%s: el _dark recolorea (%.1f%% de píxeles)'
             % (n, camo, 100 * cambia), 0.02 < cambia < 0.60)
        # el naranja de la marca tiene que aparecer donde había azul
        naranja = ((d[..., 0] > 150) & (d[..., 1] > 90) & (d[..., 1] < 200) &
                   (d[..., 2] < 90) & (d[..., 3] > 200)).sum()
        caso('logo%d_%s: el _dark trae el naranja de la marca' % (n, camo),
             naranja > 1000, naranja)

# ── el navegador: qué archivo sirve cada tema ──
CL = 'Zx9!wQ4mNp2r'
PUERTO = 5573
with A.app.app_context():
    A.db.create_all()
    for u, camo in (('fer_grid', 'gridiron'), ('fer_nile', 'nile')):
        us = A.User(username=u, email=u + '@demo.invalid', plan='premium',
                    email_verified=True)
        us.set_password(CL)
        us.email_canonical = us.email
        us.active_camo = camo
        us.owned_camos = camo
        A.db.session.add(us)
    A.db.session.commit()

threading.Thread(target=lambda: A.app.run(port=PUERTO, threaded=True,
                                          use_reloader=False),
                 daemon=True).start()
for _ in range(80):
    time.sleep(.25)
    try:
        urllib.request.urlopen('http://127.0.0.1:%d/health' % PUERTO, timeout=1)
        break
    except Exception:
        pass

from playwright.sync_api import sync_playwright  # noqa: E402

exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or
       ['/opt/pw-browsers/chromium'])[0]
URL = 'http://127.0.0.1:%d' % PUERTO
CAPS = tempfile.mkdtemp(prefix='botnuevas-')

print('── el navegador ──')
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'], executable_path=exe)
    for usuario, camo in (('fer_grid', 'gridiron'), ('fer_nile', 'nile')):
        ctx = b.new_context(viewport={'width': 1440, 'height': 900})
        pg = ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.route('**/*', lambda r: (r.continue_() if '127.0.0.1' in r.request.url
                                    else r.abort()))
        pg.goto(URL + '/login', wait_until='domcontentloaded')
        pg.fill('input[name=identifier]', usuario)
        pg.fill('input[name=password]', CL)
        pg.click('button[type=submit]')
        pg.wait_for_timeout(900)

        for tema, sufijo in (('dark', '_dark'), ('light', '')):
            pg.evaluate("t => localStorage.setItem('scalpel_theme', t)", tema)
            ctx.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                              'url': URL + '/'}])
            pg.goto(URL + '/app', wait_until='domcontentloaded')
            pg.wait_for_timeout(2500)
            clases = pg.evaluate('document.body.className')
            caso('[%s/%s] el body lleva el camo' % (camo, tema),
                 'camo-' + camo in clases, clases[:70])
            pg.evaluate("""() => { const e =
                document.querySelector('.tab[data-tab="quiz"]');
                if (e) e.click(); }""")
            pg.wait_for_timeout(2200)
            src = pg.evaluate("""() => { const e =
                document.querySelector('.quiz-welcome-logo');
                return e ? getComputedStyle(e).content : 'sin-elemento'; }""")
            quiere = 'logo2_%s%s.png' % (camo, sufijo)
            caso('[%s/%s] la bienvenida sirve %s' % (camo, tema, quiere),
                 quiere in src, src[:80])
            pg.screenshot(path=os.path.join(CAPS, '%s_%s.png' % (camo, tema)))
        caso('[%s] sin errores JS' % camo, not errs, str(errs[:2]))
        ctx.close()
    b.close()

print()
print('capturas en', CAPS)
print('%d/%d' % (OK, OK + len(MAL)))
if MAL:
    print('FALLAN:', MAL)
    sys.exit(1)
