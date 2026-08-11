# -*- coding: utf-8 -*-
"""El scroll de /app tiene que ir fluido, y las tarjetas seguir legibles.

CONTEXTO (medido 2026-08-10, lo reportó el dueño desde un iMac de 2011): 46
elementos con `backdrop-filter` obligaban a re-desenfocar su fondo en CADA
fotograma del scroll. Con el efecto puesto en todo: ~60 ms/fotograma (17 fps).
Quitándolo de lo que se desplaza: ~17 ms (60 fps).

⚠️ Este Chromium va por SOFTWARE (sin GPU), que es el peor caso y por eso los
números absolutos son pesimistas — pero es justo el escenario de una máquina
vieja, y la PROPORCIÓN entre estados es lo que importa.

Se comprueba:
  · el scroll de /app va fluido (mediana por debajo del umbral)
  · quitar lo que queda de backdrop-filter ya NO mejora nada (= no quedó
    ninguna capa cara escondida en lo que se desplaza)
  · el cristal SIGUE puesto en el sidebar (no se cargó el diseño entero)
  · las tarjetas son OPACAS en los dos temas y bajo camo — sin desenfoque, un
    fondo translúcido dejaría ver el arte del camo detrás del texto

    venv/bin/python3 tools/test_scroll_perf.py
"""
from __future__ import print_function

import glob
import os
import sys
import threading
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RAIZ, 'tools', 'scrollperf.db')
if os.path.exists(DB):
    os.remove(DB)
os.environ['DATABASE_URL'] = 'sqlite:///' + DB
os.environ.setdefault('SECRET_KEY', 'test-scroll')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                              # noqa: E402
from playwright.sync_api import sync_playwright              # noqa: E402

CL = 'Zx9!wQ4mNp2r'
PUERTO = 5090
UMBRAL = 30.0        # ms/fotograma; el estado anterior daba ~60
ok = fallas = 0

MEDIR = """async () => {
  const t = []; let prev = performance.now();
  for (let i = 0; i < 70; i++) {
    window.scrollTo(0, (i % 2) ? 300 + i * 26 : 80 + i * 18);
    await new Promise(r => requestAnimationFrame(r));
    const n = performance.now(); t.push(n - prev); prev = n;
  }
  t.sort((a, b) => a - b);
  return +(t[Math.floor(t.length / 2)]).toFixed(1);
}"""


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
    u = A.User.query.filter_by(username='scrolltest').first()
    if u is None:
        u = A.User(username='scrolltest', email='s@demo.invalid',
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


def entra(pg, camo=None, tema='light'):
    if camo is not None:
        with A.app.app_context():
            uu = A.User.query.filter_by(username='scrolltest').first()
            uu.active_camo = camo or None
            A.db.session.commit()
    pg.evaluate("t => localStorage.setItem('scalpel_theme', t)", tema)
    # ⚠️ /app borra el cookie del splash al servirse: es de un solo uso
    pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                             'url': URL + '/'}])
    pg.goto(URL + '/app', wait_until='domcontentloaded')
    pg.wait_for_timeout(2600)


with sync_playwright() as p:
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')
           or [None])[0]
    b = p.chromium.launch(args=['--no-sandbox'],
                          **({'executable_path': exe} if exe else {}))
    pg = b.new_page(viewport={'width': 1440, 'height': 900})
    pg.route('**/*', lambda r: r.continue_()
             if '127.0.0.1' in r.request.url else r.abort())
    pg.goto(URL + '/login', wait_until='domcontentloaded')
    pg.fill('input[name=identifier]', 'scrolltest')
    pg.fill('input[name=password]', CL)
    pg.click('button[type=submit]')
    pg.wait_for_timeout(800)
    entra(pg)

    ms = pg.evaluate(MEDIR)
    check('el scroll va fluido: %.1f ms/fotograma (%.0f fps), umbral %.0f'
          % (ms, 1000 / ms, UMBRAL), ms < UMBRAL, ms)

    # 🔴 La regla que de verdad importa y que nadie mira: un elemento
    # INVISIBLE no puede llevar backdrop-filter. El velo del PDF de Synapse
    # vive siempre en el árbol con opacity:0, y su desenfoque a pantalla
    # completa costaba el 20% del scroll de toda la app sin que se viera.
    fantasmas = pg.evaluate("""() => [...document.querySelectorAll('*')]
        .filter(e => (getComputedStyle(e).backdropFilter || 'none') !== 'none')
        .filter(e => { const s = getComputedStyle(e);
          return s.opacity === '0' || s.visibility === 'hidden'; })
        .map(e => e.tagName.toLowerCase() + '.' + [...e.classList][0])""")
    check('ninguna capa INVISIBLE arrastra desenfoque', not fantasmas, fantasmas)

    n = pg.evaluate("""() => [...document.querySelectorAll('*')].filter(e =>
        (getComputedStyle(e).backdropFilter || 'none') !== 'none').length""")
    check('quedan pocas capas de cristal (%d, antes 46)' % n, n <= 7, n)
    check('🔴 el sidebar CONSERVA su cristal (no se destruyó el diseño)',
          pg.evaluate("""() => {
            const s = document.querySelector('.ag-sidebar');
            return !!s && (getComputedStyle(s).backdropFilter || 'none') !== 'none';
          }"""))

    # Las tarjetas tienen que ser opacas en los dos temas y bajo camo, o el
    # arte del fondo se transparentaría detrás del texto.
    for camo, tema in (('', 'light'), ('', 'dark'),
                       ('chronicles', 'dark'), ('rising-sun', 'light')):
        entra(pg, camo, tema)
        d = pg.evaluate("""() => {
          const c = document.querySelector('.card');
          if (!c) return null;
          const b = getComputedStyle(c).backgroundImage;
          return {opaca: b.includes('gradient'),
                  blur: (getComputedStyle(c).backdropFilter || 'none')};
        }""")
        etq = (camo or 'sin camo') + ' · ' + tema
        check('%-24s tarjeta opaca y sin desenfoque' % etq,
              d and d['opaca'] and d['blur'] == 'none', d)

    b.close()

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
if os.path.exists(DB):
    os.remove(DB)
sys.exit(1 if fallas else 0)
