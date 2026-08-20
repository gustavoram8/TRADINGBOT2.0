# -*- coding: utf-8 -*-
"""Prueba en navegador REAL: usuario con camo 'standard' puesto -> la
bienvenida del quiz y los mascotas pass/fail deben servir los archivos
NUEVOS, en claro Y en oscuro. El camo lo pinta el SERVIDOR (active_camo),
asi que se fija en la cuenta, no en el navegador."""
import glob, os, sys, tempfile, threading, time, urllib.request

RAIZ = '/home/user/TRADINGBOT2.0'
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'b.db')
os.environ.setdefault('SECRET_KEY', 'botstd')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
import app as A

CL = 'Zx9!wQ4mNp2r'; PUERTO = 5566
with A.app.app_context():
    A.db.create_all()
    u = A.User(username='fer_std', email='f@demo.invalid', plan='standard',
               email_verified=True)
    u.set_password(CL); u.email_canonical = u.email
    u.active_camo = 'standard'
    u.owned_camos = 'standard'
    A.db.session.add(u); A.db.session.commit()
threading.Thread(target=lambda: A.app.run(port=PUERTO, threaded=True,
                                          use_reloader=False), daemon=True).start()
for _ in range(80):
    time.sleep(.25)
    try:
        urllib.request.urlopen('http://127.0.0.1:%d/health' % PUERTO, timeout=1)
        break
    except Exception:
        pass

from playwright.sync_api import sync_playwright
exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or
       ['/opt/pw-browsers/chromium'])[0]
URL = 'http://127.0.0.1:%d' % PUERTO
ok = fallos = 0
def chk(c, m):
    global ok, fallos
    if c: ok += 1
    else:
        fallos += 1; print('  FALLO:', m)

with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'], executable_path=exe)
    ctx = b.new_context(viewport={'width': 1440, 'height': 900})
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('**/*', lambda r: r.continue_() if '127.0.0.1' in r.request.url else r.abort())
    pg.goto(URL + '/login', wait_until='domcontentloaded')
    pg.fill('input[name=identifier]', 'fer_std'); pg.fill('input[name=password]', CL)
    pg.click('button[type=submit]'); pg.wait_for_timeout(900)

    for tema, esperado in (('dark', '_dark'), ('light', '')):
        pg.evaluate("t => localStorage.setItem('scalpel_theme', t)", tema)
        ctx.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1', 'url': URL + '/'}])
        pg.goto(URL + '/app', wait_until='domcontentloaded')
        pg.wait_for_timeout(2500)
        clases = pg.evaluate("document.body.className")
        chk('camo-standard' in clases, 'body sin camo-standard (%s)' % clases[:60])
        pg.evaluate("""() => { const e = document.querySelector('.tab[data-tab="quiz"]');
                               if (e) e.click(); }""")
        pg.wait_for_timeout(2200)
        src = pg.evaluate("""() => { const e = document.querySelector('.quiz-welcome-logo');
            return e ? getComputedStyle(e).content : 'sin-elemento'; }""")
        quiere = 'logo2_standard%s.png' % esperado
        chk(quiere in src, '[%s] welcome sirve %s (esperaba %s)' % (tema, src[:70], quiere))
        print('  [%s] welcome ->' % tema, src[:80])
        pg.screenshot(path='bot_std_%s.png' % tema)

    chk(not errs, 'errores JS: %s' % errs[:2])
    b.close()

# ── los 6 archivos: RGBA, borde SUAVE y sin cerco blanco ──
# ⚠️ Existe porque el primer recorte se comio el vertice de la flecha y un
# dedo del PASS: la banda de desvanecido tocaba pixeles CLAROS del dibujo.
# La regla que quedo: minc<235 es tinta y su alfa es 1, siempre.
from PIL import Image as _I
import numpy as _np
EST = os.path.join(RAIZ, 'scalpel', 'static')
for _b in ('logo2_standard', 'logo3_standard', 'logo4_standard'):
    for _suf in ('', '_dark'):
        _r = os.path.join(EST, _b + _suf + '.png')
        chk(os.path.exists(_r), 'falta ' + _r)
        _im = _I.open(_r)
        chk(_im.mode == 'RGBA', '%s no es RGBA' % _b)
        _a = _np.asarray(_im).astype(int)
        _al = _a[:, :, 3]
        chk(((_al > 10) & (_al < 245)).sum() > 500,
            '%s%s sin borde suave (recorte binario)' % (_b, _suf))
        # cerco: pixel casi opaco y casi blanco NEUTRO tocando transparencia
        _blanco = (_a[:, :, :3].min(2) > 246) & (abs(_a[:, :, 0] - _a[:, :, 2]) < 8)
        _borde = _np.zeros_like(_al, bool)
        _borde[1:-1, 1:-1] = (_al[1:-1, 1:-1] > 200) & (
            (_al[:-2, 1:-1] < 30) | (_al[2:, 1:-1] < 30) |
            (_al[1:-1, :-2] < 30) | (_al[1:-1, 2:] < 30))
        chk((_blanco & _borde).sum() < 400,
            '%s%s tiene cerco blanco (%d px)' % (_b, _suf, (_blanco & _borde).sum()))

print('%d bien, %d fallos' % (ok, fallos))
sys.exit(1 if fallos else 0)
