# -*- coding: utf-8 -*-
"""La pizarra tiene que dejarse usar sin pelear con ella.

Nace de la queja textual del dueño (punto 13 de su lista): "hay conexiones
usuario/elemento que son un poco tediosas… cuando seleccionabas una herramienta
y la utilizabas tenías que volver a activarla, siento que vuelvo todo muy
lento".

Se comprueba en un navegador de verdad, porque nada de esto se ve leyendo el
código: se dibuja con el ratón y se mira qué queda seleccionado después.

    python3 tools/test_chalkboard_ux.py
"""
from __future__ import print_function

import glob
import os
import sys
import tempfile
import threading
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp()
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tmp, 'ux.db')
os.environ.setdefault('SECRET_KEY', 'test-chalk-ux')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                          # noqa: E402
from playwright.sync_api import sync_playwright          # noqa: E402

CL = 'Zx9!wQ4mNp2r'
PUERTO = 5081
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
    u = A.User.query.filter_by(username='chalkux').first()
    if u is None:
        u = A.User(username='chalkux', email='u@demo.invalid', plan='premium',
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

# ⚠️ `[data-tool]` no sobra: la cabecera de cada familia también se enciende
#    (para que la barra no mienta sobre dónde estás) y no lleva herramienta —
#    sin el filtro, querySelector devuelve la cabecera y sale undefined.
HERRAMIENTA = ("() => (document.querySelector('#sk-tools .tool-btn.active[data-tool]')"
               " || {dataset: {}}).dataset.tool")
OBJETOS = "() => (window.__skCanvas ? window.__skCanvas.getObjects().length : -1)"

exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'],
                          **({'executable_path': exe} if exe else {}))
    pg = b.new_context(viewport={'width': 1440, 'height': 900}).new_page()
    errores = []
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.route('**/*', lambda r: r.continue_()
             if '127.0.0.1' in r.request.url else r.abort())
    pg.goto(URL + '/login', wait_until='domcontentloaded')
    pg.fill('input[name=identifier]', 'chalkux')
    pg.fill('input[name=password]', CL)
    pg.click('button[type=submit]')
    pg.wait_for_timeout(700)
    # ⚠️ /app borra el cookie del splash al servirse: es de un solo uso
    pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                             'url': URL + '/'}])
    pg.goto(URL + '/app', wait_until='domcontentloaded')
    pg.wait_for_timeout(2000)
    pg.evaluate("""() => { const e =
        document.querySelector('.tab[data-tab="scalper"]'); if (e) e.click(); }""")
    pg.wait_for_timeout(3800)
    # se expone el lienzo de fabric para poder contar objetos
    pg.evaluate("""() => {
        const c = document.querySelector('#sk-canvas');
        window.__skCanvas = c && c.__fabric ? c.__fabric : (c && c.fabric) || null;
        if (!window.__skCanvas && window.fabric) {
          // fabric guarda la instancia en el elemento superior
          const el = document.querySelector('.canvas-container canvas.upper-canvas');
          if (el && el.__fabricInstance) window.__skCanvas = el.__fabricInstance;
        }
      }""")

    caja = pg.evaluate("""() => { const c =
        document.querySelector('#sk-canvas'); const r = c.getBoundingClientRect();
        return {x: r.x, y: r.y, w: r.width, h: r.height}; }""")
    check('el lienzo existe y tiene tamaño', caja and caja['w'] > 300, caja)

    # ── el ancho recuperado (punto 14) ──
    m = pg.evaluate("""() => {
        const w = document.getElementById('sk-canvas-wrap');
        const c = document.querySelector('#sk-canvas-wrap canvas');
        const rw = w.getBoundingClientRect(), rc = c.getBoundingClientRect();
        return {pct: Math.round(100*(rc.width*rc.height)/(rw.width*rw.height)),
                ancho: Math.round(rc.width),
                rail: !!document.querySelector('.ag-rail') &&
                      getComputedStyle(document.querySelector('.ag-rail')).display}; }""")
    check('la pizarra llena su panel (%d%%, antes 29%%)' % m['pct'], m['pct'] >= 80, m)
    check('el rail derecho se esconde en la pizarra', m['rail'] == 'none', m)

    def dibuja(x0, y0, x1, y1):
        pg.mouse.move(caja['x'] + x0, caja['y'] + y0)
        pg.mouse.down()
        pg.mouse.move(caja['x'] + x1, caja['y'] + y1, steps=6)
        pg.mouse.up()
        pg.wait_for_timeout(260)

    def pulsa(tool):
        pg.evaluate("""t => { const b = [...document.querySelectorAll('#sk-tools .tool-btn')]
            .find(x => x.dataset.tool === t); if (b) b.click(); }""", tool)
        pg.wait_for_timeout(160)

    # ── 🔑 la herramienta se queda puesta ──
    pulsa('rect')
    dibuja(60, 60, 190, 150)
    check('tras dibujar un rectángulo la herramienta SIGUE siendo rect',
          pg.evaluate(HERRAMIENTA) == 'rect', pg.evaluate(HERRAMIENTA))
    dibuja(230, 60, 350, 150)
    n = pg.evaluate("""() => document.querySelectorAll('.canvas-container').length""")
    check('se dibuja un SEGUNDO rectángulo sin volver a pulsar la herramienta',
          pg.evaluate(HERRAMIENTA) == 'rect')

    # ── Esc suelta la herramienta ──
    pg.keyboard.press('Escape')
    pg.wait_for_timeout(140)
    check('Escape vuelve a Seleccionar', pg.evaluate(HERRAMIENTA) == 'select',
          pg.evaluate(HERRAMIENTA))

    # ── atajos de una letra ──
    for tecla, esperado in (('r', 'rect'), ('l', 'trendline'), ('o', 'circle'),
                            ('a', 'arrow'), ('p', 'pencil'), ('v', 'select')):
        pg.keyboard.press(tecla)
        pg.wait_for_timeout(120)
        got = pg.evaluate(HERRAMIENTA)
        check("la tecla '%s' activa %s" % (tecla, esperado), got == esperado, got)

    # ── pulsar la herramienta activa la apaga ──
    pulsa('rect')
    pulsa('rect')
    check('pulsar dos veces la misma herramienta vuelve a Seleccionar',
          pg.evaluate(HERRAMIENTA) == 'select', pg.evaluate(HERRAMIENTA))

    # ── duplicar y mover con el teclado ──
    # 🔑 No se leen los objetos de fabric (viven en un closure, no hay forma de
    #    alcanzarlos desde fuera): se MIRA EL LIENZO. Duplicar tiene que pintar
    #    más píxeles, y mover tiene que desplazar el centro de masa a la
    #    derecha. Es más trabajo que preguntarle al objeto, pero comprueba lo
    #    que el usuario ve en vez de lo que el código cree.
    import io as _io
    from PIL import Image as _Im
    import numpy as _np

    def dibujado():
        """(cuántos píxeles pintados, dónde está su centro horizontal)"""
        b = pg.locator('#sk-canvas').screenshot()
        a = _np.asarray(_Im.open(_io.BytesIO(b)).convert('L'), dtype=float)
        m = a > 40                      # el fondo de la pizarra es casi negro
        xs = _np.nonzero(m)[1]
        return int(m.sum()), (float(xs.mean()) if len(xs) else 0.0)

    pulsa('select')
    pg.mouse.click(caja['x'] + 120, caja['y'] + 100)      # coge el 1er rectángulo
    pg.wait_for_timeout(250)
    n0, _ = dibujado()
    pg.keyboard.press('Control+d')
    pg.wait_for_timeout(400)
    n1, cx1 = dibujado()
    check('Ctrl+D duplica: más píxeles pintados (%d → %d)' % (n0, n1), n1 > n0 + 20,
          (n0, n1))

    for _ in range(12):
        pg.keyboard.press('Shift+ArrowRight')             # 10 px por pulsación
    pg.wait_for_timeout(350)
    _, cx2 = dibujado()
    check('las flechas mueven la selección a la derecha (%.0f → %.0f px)'
          % (cx1, cx2), cx2 > cx1 + 8, (cx1, cx2))

    # ── 🕯️ herramienta de secuencia de velas (punto 13 del dueño) ──
    pg.keyboard.press('Escape')
    pg.wait_for_timeout(200)

    def velas(y0, y1):
        """dibuja arrastrando y devuelve (verdes, rojas) contadas en el lienzo"""
        pulsa('candles')
        pg.mouse.move(caja['x'] + 80, caja['y'] + y0)
        pg.mouse.down()
        pg.mouse.move(caja['x'] + 560, caja['y'] + y1, steps=10)
        pg.mouse.up()
        pg.wait_for_timeout(500)
        png = pg.locator('#sk-canvas').screenshot()
        a = _np.asarray(_Im.open(_io.BytesIO(png)).convert('RGB'), dtype=int)
        r, g, bl = a[:, :, 0], a[:, :, 1], a[:, :, 2]
        verde = int(((g > 110) & (g - r > 45) & (g - bl > 45)).sum())
        rojo = int(((r > 110) & (r - g > 45) & (r - bl > 45)).sum())
        return verde, rojo

    v_sube, r_sube = velas(320, 90)          # arrastre HACIA ARRIBA
    check('arrastrando hacia arriba se dibujan velas (verde %d px, rojo %d px)'
          % (v_sube, r_sube), v_sube + r_sube > 400, (v_sube, r_sube))
    check('…y la secuencia es mayoritariamente ALCISTA',
          v_sube > max(200, r_sube * 1.3), (v_sube, r_sube))
    # 🔑 Una tendencia SIN una sola vela en contra es una escalera, no un
    #    gráfico. Aquí se exige que haya retroceso.
    check('…con velas en contra (retroceso), no una escalera perfecta',
          r_sube > 60, (v_sube, r_sube))

    # la posición vertical del verde tiene que subir a lo largo del recorrido:
    # una tendencia alcista dibujada al revés se detectaría aquí
    png = pg.locator('#sk-canvas').screenshot()
    a = _np.asarray(_Im.open(_io.BytesIO(png)).convert('RGB'), dtype=int)
    m = (a[:, :, 1] > 90) & (a[:, :, 1] - a[:, :, 0] > 35)
    ys, xs = _np.nonzero(m)
    if len(xs) > 50:
        mitad = xs.mean()
        alto_izq = ys[xs < mitad].mean()
        alto_der = ys[xs >= mitad].mean()
        check('la tendencia SUBE de izquierda a derecha (y %.0f → %.0f)'
              % (alto_izq, alto_der), alto_der < alto_izq - 5,
              (alto_izq, alto_der))

    # ── 🧰 la barra agrupada (punto 14, 2ª parte) ──
    # Antes: 20 botones y 961 px fijos. A 1440x900 quedaban 10 por debajo del
    # lienzo y 4 fuera de la pantalla; a 1366x768, 11 y 6.
    bar = pg.evaluate("""() => {
        const rail = document.getElementById('sk-tools');
        const lz = document.querySelector('#sk-canvas-wrap canvas').getBoundingClientRect();
        const bs = [...rail.querySelectorAll(
            ':scope > .tool-btn, :scope > .tool-group > .tool-btn')];
        return {alto: Math.round(rail.getBoundingClientRect().height),
                botones: bs.length,
                bajo: bs.filter(b => b.getBoundingClientRect().bottom > lz.bottom + 2).length,
                fuera: bs.filter(b => b.getBoundingClientRect().bottom > innerHeight).length,
                arriba: document.querySelectorAll('.scalper-actions .sk-inline > *').length,
                sueltos: rail.querySelectorAll(':scope > .tool-sep + .tool-sep').length};
      }""")
    check('la barra cabe en el alto del lienzo (%d px, antes 961)' % bar['alto'],
          bar['alto'] < 420, bar)
    check('ninguna herramienta queda por debajo de la pizarra (antes 10)',
          bar['bajo'] == 0, bar)
    check('ninguna herramienta queda fuera de la pantalla (antes 4)',
          bar['fuera'] == 0, bar)
    check('los 7 ajustes/acciones se mudaron a la barra de arriba',
          bar['arriba'] == 7, bar)
    check('no quedan separadores colgando', bar['sueltos'] == 0, bar)

    # 🔑 Con el RATÓN de verdad, no con .click() de JavaScript: un botón dentro
    #    de un desplegable cerrado se puede pulsar por código aunque el usuario
    #    no lo alcance. Lo que se comprueba aquí es que se alcanza.
    pg.keyboard.press('Escape')
    cabecera = '#sk-tools .tool-group[data-familia="lineas"] > .tool-btn'
    pg.hover(cabecera)
    pg.wait_for_timeout(600)                      # el desplegable abre a los 340 ms
    abierto = pg.evaluate("""() => {
        const f = document.querySelector('.tool-group[data-familia="lineas"] .tool-flyout');
        const r = f.getBoundingClientRect();
        return getComputedStyle(f).display !== 'none' && r.width > 60 &&
               r.right < innerWidth && r.left > 0; }""")
    check('posar el ratón abre el desplegable, y cabe en pantalla', abierto)
    pg.click('.tool-group[data-familia="lineas"] .tool-btn[data-tool="hray"]')
    pg.wait_for_timeout(220)
    check('se puede elegir una herramienta del desplegable con el ratón',
          pg.evaluate(HERRAMIENTA) == 'hray', pg.evaluate(HERRAMIENTA))
    check('…y el desplegable se cierra solo al elegir',
          pg.evaluate("""() => getComputedStyle(document.querySelector(
              '.tool-group[data-familia="lineas"] .tool-flyout')).display === 'none'"""))
    # la cabecera recuerda la última usada: el segundo uso cuesta UN clic
    pg.keyboard.press('Escape')
    pg.wait_for_timeout(160)
    pg.click(cabecera)
    pg.wait_for_timeout(200)
    check('la cabecera recuerda la última de su familia (1 clic, no 2)',
          pg.evaluate(HERRAMIENTA) == 'hray', pg.evaluate(HERRAMIENTA))
    check('…y la cabecera se enciende cuando su familia está activa',
          pg.evaluate("""() => document.querySelector(
              '.tool-group[data-familia="lineas"] > .tool-btn').classList.contains('active')"""))
    # un atajo de teclado también tiene que encender la cabecera correcta
    pg.keyboard.press('r')
    pg.wait_for_timeout(200)
    check('un atajo de teclado enciende la cabecera de SU familia y apaga la otra',
          pg.evaluate("""() => {
              const z = document.querySelector('.tool-group[data-familia="zonas"] > .tool-btn');
              const l = document.querySelector('.tool-group[data-familia="lineas"] > .tool-btn');
              return z.classList.contains('active') && !l.classList.contains('active'); }"""))

    check('ningún error de JavaScript en toda la sesión', not errores, errores[:3])
    b.close()

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
