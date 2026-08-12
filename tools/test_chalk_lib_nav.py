# -*- coding: utf-8 -*-
"""La biblioteca, usada con el ratón: guardar, empezar en blanco, reabrir.

`test_chalk_biblioteca.py` prueba el servidor (permisos, topes, propiedad).
Esto prueba lo otro: que el ciclo que describió el dueño funcione de verdad en
un navegador — *"una vez guardado que se te reinicien las diapositivas y te
quede solo una activa"* y *"que alguien pueda volver a editarlos"*.

    python3 tools/test_chalk_lib_nav.py
"""
from __future__ import print_function

import glob
import io as _io
import os
import sys
import tempfile
import threading
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp()
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tmp, 'lib.db')
os.environ.setdefault('SECRET_KEY', 'test-lib-nav')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                          # noqa: E402
from playwright.sync_api import sync_playwright          # noqa: E402
import numpy as _np                                      # noqa: E402
from PIL import Image as _Im                             # noqa: E402

CL = 'Zx9!wQ4mNp2r'
PUERTO = 5097
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
    u = A.User.query.filter_by(username='libnav').first()
    if u is None:
        u = A.User(username='libnav', email='l@demo.invalid', plan='premium',
                   email_verified=True)
        A.db.session.add(u)
    u.set_password(CL)
    u.email_canonical = u.email
    u.plan = 'premium'
    A.db.session.commit()
threading.Thread(target=lambda: A.app.run(port=PUERTO, threaded=True,
                                          use_reloader=False), daemon=True).start()
for _ in range(80):
    time.sleep(.25)
    try:
        urllib.request.urlopen('http://127.0.0.1:%d/health' % PUERTO, timeout=1)
        break
    except Exception:
        pass
URL = 'http://127.0.0.1:%d' % PUERTO
exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]

with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'],
                          **({'executable_path': exe} if exe else {}))
    pg = b.new_context(viewport={'width': 1440, 'height': 900}).new_page()
    errores = []
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.on('dialog', lambda d: d.accept())          # confirm() de reemplazo/borrado
    pg.route('**/*', lambda r: r.continue_()
             if '127.0.0.1' in r.request.url else r.abort())
    pg.goto(URL + '/login', wait_until='domcontentloaded')
    pg.fill('input[name=identifier]', 'libnav')
    pg.fill('input[name=password]', CL)
    pg.click('button[type=submit]')
    pg.wait_for_timeout(700)
    pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                             'url': URL + '/'}])
    pg.goto(URL + '/app', wait_until='domcontentloaded')
    pg.wait_for_timeout(2000)
    pg.evaluate("""() => { const e =
        document.querySelector('.tab[data-tab="scalper"]'); if (e) e.click(); }""")
    pg.wait_for_timeout(3600)

    caja = pg.evaluate("""() => { const r =
        document.querySelector('#sk-canvas').getBoundingClientRect();
        return {x: r.x, y: r.y}; }""")

    def pintado():
        """Píxeles dibujados, leídos DEL LIENZO y no de una captura.

        ⚠️ `locator.screenshot()` fotografía la zona de la pantalla donde está
        el elemento, o sea que incluye lo que haya pintado ENCIMA. El aviso de
        "Guardada" cae justo sobre el lienzo, así que medir por captura contaba
        el texto del aviso como si fuera dibujo: una pizarra recién vaciada
        marcaba 3.754 px y parecía que no se había limpiado.
        """
        return pg.evaluate("""() => {
            const c = document.querySelector('#sk-canvas-wrap canvas.lower-canvas') ||
                      document.querySelector('#sk-canvas');
            const g = c.getContext('2d');
            const d = g.getImageData(0, 0, c.width, c.height).data;
            let n = 0;
            for (let i = 0; i < d.length; i += 4) {
              if ((d[i] * 0.299 + d[i+1] * 0.587 + d[i+2] * 0.114) > 40) n++;
            }
            return n; }""")

    def herramienta(t):
        pg.evaluate("""t => { const x = [...document.querySelectorAll('#sk-tools .tool-btn')]
            .find(e => e.dataset.tool === t); if (x) x.click(); }""", t)
        pg.wait_for_timeout(150)

    def dibuja(x0, y0, x1, y1):
        pg.mouse.move(caja['x'] + x0, caja['y'] + y0)
        pg.mouse.down()
        pg.mouse.move(caja['x'] + x1, caja['y'] + y1, steps=6)
        pg.mouse.up()
        pg.wait_for_timeout(250)

    # ── biblioteca vacía: tiene que EXPLICARSE, no salir en blanco ──
    pg.click('#sk-lib-btn')
    pg.wait_for_timeout(900)
    vacia = pg.evaluate("""() => { const e = document.querySelector('#sk-lib-body .sk-lib-empty');
        return e ? e.textContent.trim() : ''; }""")
    check('la biblioteca vacía explica qué hacer (%d caracteres)' % len(vacia),
          len(vacia) > 40 and not vacia.startswith('scalper.'), vacia[:60])
    pg.click('#sk-lib-x')
    pg.wait_for_timeout(300)

    # ── dibujar en 3 diapositivas y guardar ──
    herramienta('rect')
    dibuja(60, 60, 200, 160)
    pg.click('.slide-add')
    pg.wait_for_timeout(500)
    dibuja(80, 80, 260, 200)
    pg.click('.slide-add')
    pg.wait_for_timeout(500)
    dibuja(100, 100, 300, 240)
    def suelta():
        herramienta('select')
        pg.mouse.click(caja['x'] + 700, caja['y'] + 400)
        pg.wait_for_timeout(350)
    suelta()
    antes = pintado()
    # 🔑 Para "¿se perdió algo?" se compara EL ESTADO, no los píxeles. Contar
    #    píxeles sirve para "¿está en blanco?" (0 vs miles), pero no para "¿es
    #    lo mismo?": al recargar, el trazo cae medio píxel corrido y el
    #    antialiasing cambia su color (medido: 91,142,240 → 75,117,198), así
    #    que un dibujo intacto marca un 25% menos y parece perdido.
    estado_antes = pg.evaluate("() => localStorage.getItem('scalperBoard')")
    nslides = pg.evaluate("() => document.querySelectorAll('#sk-thumbs > *').length")
    check('hay 3 diapositivas dibujadas antes de guardar', nslides == 3, nslides)

    pg.click('#sk-save-btn')
    pg.wait_for_timeout(500)
    # ⚠️ el nombre propuesto tiene que describir UNA PIZARRA. La primera
    #    versión reusaba la clave 'library' y proponía "Biblioteca 2026-08-12"
    propuesto = pg.input_value('#sk-save-name')
    check('el diálogo de guardar propone un nombre de PIZARRA, con fecha',
          len(propuesto) > 3 and propuesto[:1].isalpha()
          and 'ibrar' not in propuesto and 'ibliot' not in propuesto
          and propuesto[-4:].isdigit() is False and '-' in propuesto, propuesto)
    pg.fill('#sk-save-name', 'Plan NQ · lunes')
    pg.click('#sk-save-go')
    pg.wait_for_timeout(2500)

    # ── lo que pidió: al guardar, queda UNA diapositiva en blanco ──
    n2 = pg.evaluate("() => document.querySelectorAll('#sk-thumbs > *').length")
    check('tras guardar queda UNA sola diapositiva', n2 == 1, n2)
    check('…y está en blanco', pintado() < max(60, antes * 0.06), (antes, pintado()))
    check('…y se avisa de que se guardó',
          pg.evaluate("""() => { const e = document.getElementById('sk-aviso');
              return !!e && e.classList.contains('show') &&
                     !e.textContent.startsWith('scalper.'); }"""))

    # ── el deshacer que acompaña al aviso ──
    check('el aviso trae un botón para recuperarla',
          pg.evaluate("() => !!document.querySelector('#sk-aviso .sk-aviso-btn')"))
    pg.click('#sk-aviso .sk-aviso-btn')
    pg.wait_for_timeout(1800)
    n3 = pg.evaluate("() => document.querySelectorAll('#sk-thumbs > *').length")
    check('pulsarlo devuelve las 3 diapositivas a la pizarra', n3 == 3, n3)
    vuelto = pintado()
    estado_vuelto = pg.evaluate("() => localStorage.getItem('scalperBoard')")
    check('…con el contenido EXACTAMENTE igual al de antes de guardar',
          estado_vuelto == estado_antes,
          (len(estado_antes or ''), len(estado_vuelto or '')))
    check('…y con dibujo en pantalla, no una pizarra vacía (%d px)' % vuelto,
          vuelto > 400, vuelto)

    # ── reabrirla desde la biblioteca ──
    pg.evaluate("""() => { const b = document.getElementById('sk-add-slide'); b.click(); }""")
    pg.wait_for_timeout(600)
    pg.click('#sk-lib-btn')
    pg.wait_for_timeout(1200)
    tarjetas = pg.evaluate("() => document.querySelectorAll('#sk-lib-body .sk-lib-card').length")
    check('la pizarra guardada aparece en la biblioteca', tarjetas == 1, tarjetas)
    nombre = pg.evaluate("""() => { const e = document.querySelector('.sk-lib-name');
        return e ? e.textContent : ''; }""")
    check('…con el nombre que le puso', nombre == 'Plan NQ · lunes', nombre)
    check('…y con miniatura de verdad, no un hueco gris',
          pg.evaluate("""() => { const e = document.querySelector('.sk-lib-thumb');
              return !!e && (e.style.backgroundImage || '').indexOf('data:image') > 0; }"""))
    meta = pg.evaluate("""() => { const e = document.querySelector('.sk-lib-meta');
        return e ? e.textContent : ''; }""")
    check('…y dice cuántas diapositivas tiene, traducido', '3' in meta and
          not meta.startswith('scalper.'), meta)

    pg.click('#sk-lib-body .sk-lib-btn.go')
    pg.wait_for_timeout(2500)
    n4 = pg.evaluate("() => document.querySelectorAll('#sk-thumbs > *').length")
    check('abrirla trae de vuelta sus 3 diapositivas', n4 == 3, n4)
    check('…y el panel se cierra solo al abrirla',
          pg.evaluate("""() => !document.getElementById('sk-lib').classList.contains('show')"""))

    # ── sobrevive a recargar (que es el punto de guardarlo en el servidor) ──
    pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                             'url': URL + '/'}])
    pg.evaluate("() => localStorage.removeItem('scalperBoard')")   # simula otro equipo
    pg.goto(URL + '/app', wait_until='domcontentloaded')
    pg.wait_for_timeout(2200)
    pg.evaluate("""() => { const e =
        document.querySelector('.tab[data-tab="scalper"]'); if (e) e.click(); }""")
    pg.wait_for_timeout(3200)
    pg.click('#sk-lib-btn')
    pg.wait_for_timeout(1400)
    check('sigue ahí desde un navegador SIN el guardado local (otro equipo)',
          pg.evaluate("() => document.querySelectorAll('.sk-lib-card').length") == 1)

    # ── borrar ──
    pg.click('#sk-lib-body .sk-lib-btn:nth-child(3)')
    pg.wait_for_timeout(1500)
    check('borrarla la quita de la biblioteca',
          pg.evaluate("() => document.querySelectorAll('.sk-lib-card').length") == 0)

    check('ningún error de JavaScript en toda la sesión', not errores, errores[:3])
    b.close()

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
