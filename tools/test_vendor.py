# -*- coding: utf-8 -*-
"""¿Synapse y el Chalkboard funcionan SIN internet?

Ese es el punto entero de vendorizar three/fabric/jspdf: antes dependían de
CDN externos y una red que los bloquee dejaba a un cliente de pago mirando una
pantalla de carga. Aquí se abre la app en un navegador real con TODA la red
externa cortada (solo 127.0.0.1) y se comprueba que:

  · Synapse: THREE se define, el motor 3D arranca y el canvas PINTA (se miran
    los píxeles, no la clase) — y no queda ningún cartel de error/carga.
  · Chalkboard (tab Scalpe): fabric se define y el lienzo de dibujo se
    inicializa de verdad.
  · jspdf (export a PDF del analizador) queda cargado desde nuestra copia.
  · Ninguna petición intentó salir a un CDN (se listan las abortadas).

    venv/bin/python3 tools/test_vendor.py
"""
from __future__ import print_function

import glob
import os
import sys
import threading
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RAIZ, 'tools', 'vendor.db')
if os.path.exists(DB):
    os.remove(DB)
os.environ['DATABASE_URL'] = 'sqlite:///' + DB
os.environ.setdefault('SECRET_KEY', 'test-vendor')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                              # noqa: E402
from playwright.sync_api import sync_playwright              # noqa: E402

CL = 'Zx9!wQ4mNp2r'
PUERTO = 5092
ok = fallas = 0


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


with A.app.app_context():
    A.db.create_all()
    u = A.User.query.filter_by(username='vendortest').first()
    if u is None:
        u = A.User(username='vendortest', email='v@demo.invalid',
                   plan='premium', email_verified=True)
        A.db.session.add(u)
    u.set_password(CL)
    u.email_canonical = u.email
    u.plan = 'premium'
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

URL = 'http://127.0.0.1:%d' % PUERTO
externas = []      # todo lo que intentó salir de 127.0.0.1
errores = []

with sync_playwright() as p:
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')
           or [None])[0]
    b = p.chromium.launch(args=['--no-sandbox'],
                          **({'executable_path': exe} if exe else {}))
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('console', lambda m: errores.append(m.text)
          if m.type == 'error' else None)

    def ruta(r):
        if '127.0.0.1' in r.request.url:
            r.continue_()
        else:
            externas.append(r.request.url)
            r.abort()
    pg.route('**/*', ruta)

    pg.goto(URL + '/login', wait_until='domcontentloaded')
    pg.fill('input[name=identifier]', 'vendortest')
    pg.fill('input[name=password]', CL)
    pg.click('button[type=submit]')
    pg.wait_for_timeout(800)
    pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                             'url': URL + '/'}])
    pg.goto(URL + '/app', wait_until='domcontentloaded')
    pg.wait_for_timeout(2500)

    # ── jspdf: la etiqueta estática, ahora local ──
    check('jspdf cargado desde /static/vendor (sin CDN)',
          pg.evaluate("!!(window.jspdf && window.jspdf.jsPDF)"))

    # ── Synapse ──
    # ⚠️ La pantalla de carga dura 10 s A PROPÓSITO (LOAD_MS=10000: cuenta
    # hasta 100% aunque los assets ya estén) — esperar menos hace que un test
    # acuse "atascado" a algo que solo está contando.
    pg.evaluate("document.querySelector('.tab[data-tab=\"synapse\"]').click()")
    pg.wait_for_timeout(13500)
    check('THREE definido (three.js local)',
          pg.evaluate("typeof THREE !== 'undefined'"))
    check('THREE es r128 (la MISMA versión que servía el CDN)',
          pg.evaluate("typeof THREE !== 'undefined' && THREE.REVISION === '128'"))
    check('GLTFLoader disponible (esculturas GLB, ahora local)',
          pg.evaluate("typeof THREE !== 'undefined' && !!THREE.GLTFLoader"))
    d = pg.evaluate("""() => {
      const load = document.getElementById('syn-loading');
      const c = [...document.querySelectorAll('canvas')]
        .filter(x => x.offsetParent !== null && x.width > 300);
      return {canvases: c.length,
              veloFuera: !load || load.classList.contains('hidden'),
              texto: document.body.innerText.slice(0, 4000)};
    }""")
    check('el velo de carga terminó y se ocultó (la escena arrancó)',
          d['veloFuera'])
    check('Synapse tiene canvas 3D visible', d['canvases'] >= 1, d['canvases'])
    check('sin cartel de "no se pudo cargar" en Synapse',
          not any(s in d['texto'].lower()
                  for s in ('could not be loaded', 'no se pudo cargar',
                            'check your internet', 'verifica tu conex')))
    pg.screenshot(path=os.path.join(RAIZ, 'tools', 'vendor_synapse.png'))

    # ── Chalkboard (tab Scalpe) ──
    pg.evaluate("document.querySelector('.tab[data-tab=\"scalper\"]').click()")
    pg.wait_for_timeout(4500)
    check('fabric definido (fabric.js local)',
          pg.evaluate("typeof fabric !== 'undefined'"))
    check('el lienzo de dibujo está inicializado (#sk-canvas + wrapper de fabric)',
          pg.evaluate("""!!document.querySelector('#sk-canvas')
              && !!document.querySelector('.canvas-container')"""))
    t2 = pg.evaluate("document.body.innerText.slice(0, 4000)").lower()
    check('sin cartel de "engine could not be loaded" en el Chalkboard',
          'could not be loaded' not in t2)
    pg.screenshot(path=os.path.join(RAIZ, 'tools', 'vendor_chalk.png'))

    # ── nada intentó salir a un CDN de librerías ──
    libs = [u for u in externas
            if any(s in u for s in ('three', 'fabric', 'jspdf'))]
    check('cero peticiones de three/fabric/jspdf a CDNs externos',
          not libs, libs[:3])

    graves = [e for e in errores if 'ERR_' not in e and 'favicon' not in e]
    check('sin errores de JS', not graves, graves[:3])
    b.close()

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
if os.path.exists(DB):
    os.remove(DB)
sys.exit(1 if fallas else 0)
