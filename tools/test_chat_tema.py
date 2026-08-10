# -*- coding: utf-8 -*-
"""El fondo del chat de Tessera NO puede depender del camo.

El dueno lo vio con Rising Sun: sitio en modo OSCURO y el asistente pintado en
BLANCO. La causa no es el camo en si, es que la regla miraba `body.light`, y
hay camos que la fuerzan:

  · LIGHT_ALWAYS (rising-sun, blackflag): suelo crema en los DOS modos, asi que
    body SIEMPRE lleva .light; la preferencia oscura se marca con .camo-night.
  · DARK_ALWAYS (premium): body NUNCA lleva .light; la preferencia clara se
    marca con .camo-day.  ← el fallo ESPEJO: chat negro en modo claro.

Aqui se abre el chat con CADA camo listo x los dos modos y se mide el color
REAL que pinta el navegador (fondo del overlay y pixel del canvas), no la clase
que deberia estar puesta.

    venv/bin/python3 tools/test_chat_tema.py
"""
from __future__ import print_function

import os
import sys
import threading
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RAIZ, 'tools', 'chattema.db')
if os.path.exists(DB):
    os.remove(DB)
os.environ['DATABASE_URL'] = 'sqlite:///' + DB
os.environ.setdefault('SECRET_KEY', 'test-chat-tema')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                              # noqa: E402
from playwright.sync_api import sync_playwright              # noqa: E402

CAMOS = sorted(A.CAMO_READY)
CL = 'Zx9!wQ4mNp2r'
PUERTO = 5099
ok = fallas = 0


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def luminancia(css):
    """0 = negro, 1 = blanco. Sirve para decir 'esto es un fondo oscuro'."""
    n = [int(x) for x in css[css.index('(') + 1:css.index(')')].split(',')[:3]]
    return (0.2126 * n[0] + 0.7152 * n[1] + 0.0722 * n[2]) / 255.0


with A.app.app_context():
    A.db.create_all()
    u = A.User.query.filter_by(username='camotest').first()
    if u is None:
        u = A.User(username='camotest', email='c@demo.invalid', plan='premium',
                   email_verified=True)
        A.db.session.add(u)
    u.set_password(CL)
    u.email_canonical = u.email
    u.plan = 'premium'
    A.db.session.commit()

hilo = threading.Thread(
    target=lambda: A.app.run(port=PUERTO, threaded=True, use_reloader=False),
    daemon=True)
hilo.start()
for _ in range(60):
    time.sleep(.25)
    try:
        import urllib.request
        urllib.request.urlopen('http://127.0.0.1:%d/health' % PUERTO, timeout=1)
        break
    except Exception:
        pass

URL = 'http://127.0.0.1:%d' % PUERTO
errores = []
with sync_playwright() as p:
    import glob
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    b = p.chromium.launch(args=['--no-sandbox'],
                          **({'executable_path': exe} if exe else {}))
    pg = b.new_page(viewport={'width': 1280, 'height': 860})
    pg.on('console', lambda m: errores.append(m.text)
          if m.type == 'error' else None)
    pg.route('**/*', lambda r: r.continue_()
             if '127.0.0.1' in r.request.url else r.abort())
    pg.goto(URL + '/login', wait_until='domcontentloaded')
    pg.fill('input[name=identifier]', 'camotest')
    pg.fill('input[name=password]', CL)
    pg.click('button[type=submit]')
    pg.wait_for_timeout(700)
    pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '9999999999',
                             'url': URL + '/'}])

    for camo in [''] + CAMOS:
        # el camo lo decide el SERVIDOR (active_camo -> clase del <body>), asi
        # que se cambia en la cuenta, no en el navegador
        with A.app.app_context():
            uu = A.User.query.filter_by(username='camotest').first()
            uu.active_camo = camo or None
            A.db.session.commit()
        for tema in ('dark', 'light'):
            pg.evaluate("t => localStorage.setItem('scalpel_theme', t)", tema)
            # ⚠️ /app BORRA el cookie del splash al servirse (es de un solo
            # uso): sin volver a ponerlo, la siguiente visita rebota a /welcome
            # y el cubo no existe.
            pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                                     'url': URL + '/'}])
            pg.goto(URL + '/app', wait_until='domcontentloaded')
            pg.wait_for_timeout(1100)
            pg.evaluate("document.getElementById('nx-cube').click()")
            pg.wait_for_timeout(2400)
            pg.evaluate("document.querySelectorAll('.nx-nd')[0].click()")
            pg.wait_for_timeout(700)
            d = pg.evaluate("""() => {
              const cv = document.querySelector('#nxc-ov');
              const c = cv.querySelector('#nxc-bg');
              const px = c.getContext('2d').getImageData(4, 4, 1, 1).data;
              return {abierto: cv.classList.contains('show'),
                      fondo: getComputedStyle(cv).backgroundColor,
                      lienzo: 'rgb(' + px[0] + ',' + px[1] + ',' + px[2] + ')',
                      texto: getComputedStyle(cv.querySelector('.nxc-title')).color};
            }""")
            etq = (camo or 'sin camo') + ' · ' + tema
            lf, ll = luminancia(d['fondo']), luminancia(d['lienzo'])
            if tema == 'dark':
                check('%-22s fondo OSCURO (lum %.2f / lienzo %.2f)'
                      % (etq, lf, ll), lf < .25 and ll < .25, d)
            else:
                check('%-22s fondo CLARO  (lum %.2f / lienzo %.2f)'
                      % (etq, lf, ll), lf > .75 and ll > .75, d)
            pg.evaluate("document.querySelector('.nxc-exit').click()")
            pg.wait_for_timeout(200)

    check('sin errores de JS en ninguna combinación',
          not [e for e in errores if 'ERR_' not in e],
          [e for e in errores if 'ERR_' not in e][:3])
    b.close()

print('\n%d camos x 2 modos + sin camo = %d combinaciones' % (len(CAMOS), ok + fallas - 1))
print('RESULTADO: %d ok, %d fallas' % (ok, fallas))
if os.path.exists(DB):
    os.remove(DB)
sys.exit(1 if fallas else 0)
