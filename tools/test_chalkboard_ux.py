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

    # Las velas tienen que subir a lo largo del recorrido: una tendencia
    # dibujada al revés se detectaría aquí.
    # ⚠️ Se miden TODAS las velas, verdes Y rojas. La primera versión miraba
    #    solo el verde y era inestable entre ejecuciones —las velas se generan
    #    con azar— porque un retroceso al final desplaza la media del verde sin
    #    que la tendencia haya cambiado. El conjunto de la serie sí sube
    #    siempre: en un tramo alcista las rojas suben igual que las verdes.
    png = pg.locator('#sk-canvas').screenshot()
    a = _np.asarray(_Im.open(_io.BytesIO(png)).convert('RGB'), dtype=int)
    r_, g_, b_ = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    m = (((g_ > 90) & (g_ - r_ > 35)) | ((r_ > 90) & (r_ - g_ > 35))) & (b_ < 200)
    ys, xs = _np.nonzero(m)
    if len(xs) > 50:
        mitad = xs.mean()
        alto_izq = ys[xs < mitad].mean()
        alto_der = ys[xs >= mitad].mean()
        check('la tendencia SUBE de izquierda a derecha (y %.0f → %.0f)'
              % (alto_izq, alto_der), alto_der < alto_izq - 5,
              (alto_izq, alto_der))

    # ── 📈 posición (TP/SL) y Fibonacci ──
    # Pedido del dueño: *"Hay que incluir más herramientas tipo la de conjunto
    # de velas: ejemplo las de Take profit y SL"*.
    # 🔑 Lo que se comprueba no es que "dibuje algo", sino la SEMÁNTICA: que el
    #    sentido del arrastre decida compra/venta y que el objetivo salga a 2R.
    #    Un dibujo bonito con el TP del lado equivocado enseña mal.
    def zonas():
        """(alto del verde, alto del rojo, y de su centro) leído del lienzo"""
        return pg.evaluate("""() => {
            const c = document.querySelector('#sk-canvas-wrap canvas.lower-canvas') ||
                      document.querySelector('#sk-canvas');
            const g = c.getContext('2d');
            const d = g.getImageData(0, 0, c.width, c.height).data;
            let gy = [], ry = [];
            for (let y = 0; y < c.height; y++) {
              let nv = 0, nr = 0;
              for (let x = 0; x < c.width; x++) {
                const i = (y * c.width + x) * 4;
                const R = d[i], G = d[i+1], B = d[i+2];
                // ⚠️ umbrales MEDIDOS sobre el color que queda de verdad al
                //    mezclar el relleno translúcido con el fondo oscuro:
                //    verde rgb(15,38,30) → G-R=23 pero G-B solo 8; rojo
                //    rgb(42,21,26) → R-G=21, R-B=16. Exigir 12 en las dos
                //    diferencias descartaba la zona verde entera.
                if (G - R > 12 && G - B > 4) nv++;
                if (R - G > 12 && R - B > 8) nr++;
              }
              if (nv > 30) gy.push(y);
              if (nr > 30) ry.push(y);
            }
            const med = a => a.length ? a.reduce((s,v)=>s+v,0)/a.length : -1;
            return {verde: gy.length, rojo: ry.length,
                    yVerde: med(gy), yRojo: med(ry)}; }""")

    def posicion(xe, ye, xs, ys, yObj):
        """entrada→stop arrastrando, y el objetivo con el clic siguiente"""
        pulsa('trade')
        pg.mouse.move(caja['x'] + xe, caja['y'] + ye)
        pg.mouse.down()
        pg.mouse.move(caja['x'] + xs, caja['y'] + ys, steps=6)
        pg.mouse.up()
        pg.wait_for_timeout(280)
        pg.mouse.move(caja['x'] + xs, caja['y'] + yObj, steps=8)
        pg.wait_for_timeout(280)
        pg.mouse.click(caja['x'] + xs, caja['y'] + yObj)
        pg.wait_for_timeout(380)

    def limpia():
        pulsa('select')
        pg.evaluate("""() => document.getElementById('sk-clear').click()""")
        pg.wait_for_timeout(450)

    pg.keyboard.press('Escape')
    limpia()
    # riesgo de 60 px, objetivo a 60 → 1R
    posicion(120, 240, 380, 300, 180)
    z = zonas()
    check('la posición dibuja zona verde y zona roja', z['verde'] > 20 and z['rojo'] > 10, z)
    check('arrastrando hacia ABAJO el TP queda ARRIBA y el SL abajo (compra)',
          z['yVerde'] < z['yRojo'], z)
    # 🔑 EL R:R SE MIDE: con el objetivo a 1R el verde tiene que medir lo MISMO
    #    que el rojo. Antes iba escrito un 2 fijo y esto habría fallado.
    check('objetivo a 1R → verde y rojo miden igual (%d vs %d px)'
          % (z['verde'], z['rojo']),
          abs(z['verde'] - z['rojo']) <= max(10, z['rojo'] * 0.2), z)
    # …y la herramienta se apaga sola (petición expresa del dueño)
    check('tras colocar una posición la herramienta se SUELTA',
          pg.evaluate(HERRAMIENTA) == 'select', pg.evaluate(HERRAMIENTA))

    limpia()
    # mismo riesgo, objetivo a 180 px → 3R
    posicion(120, 240, 380, 300, 60)
    z3 = zonas()
    check('objetivo a 3R → el verde mide el TRIPLE que el rojo (%d vs %d px)'
          % (z3['verde'], z3['rojo']),
          abs(z3['verde'] - 3 * z3['rojo']) <= max(14, z3['rojo'] * 0.3), z3)

    limpia()
    posicion(120, 300, 380, 250, 400)     # arrastre HACIA ARRIBA = venta
    z2 = zonas()
    check('arrastrando hacia ARRIBA el SL queda arriba y el TP abajo (venta)',
          z2['yVerde'] > z2['yRojo'], z2)

    # una posición a medio colocar se cancela con el clic derecho y no deja nada
    limpia()
    vacio, _ = dibujado()
    pulsa('trade')
    pg.mouse.move(caja['x'] + 120, caja['y'] + 240)
    pg.mouse.down()
    pg.mouse.move(caja['x'] + 380, caja['y'] + 300, steps=6)
    pg.mouse.up()
    pg.wait_for_timeout(300)
    pg.mouse.move(caja['x'] + 380, caja['y'] + 150, steps=6)
    pg.wait_for_timeout(250)
    a_medias, _ = dibujado()
    check('mientras se coloca, el objetivo ya se ve siguiendo al ratón',
          a_medias > vacio + 300, (vacio, a_medias))
    pg.mouse.click(caja['x'] + 380, caja['y'] + 150, button='right')
    pg.wait_for_timeout(400)
    tras, _ = dibujado()
    check('el clic derecho cancela la posición a medias y no deja rastro',
          abs(tras - vacio) < 250, (vacio, a_medias, tras))

    limpia()
    pulsa('fib')
    dibuja(120, 380, 520, 120)
    fib = pg.evaluate("""() => {
        const c = document.querySelector('#sk-canvas-wrap canvas.lower-canvas') ||
                  document.querySelector('#sk-canvas');
        const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
        let lineas = 0, ote = 0;
        for (let y = 0; y < c.height; y++) {
          let n = 0, v = 0;
          for (let x = 0; x < c.width; x++) {
            const i = (y * c.width + x) * 4;
            const R = d[i], G = d[i+1], B = d[i+2];
            if (B - R > 40 && B > 90) n++;               // azul = las líneas
            if (G - R > 12 && G - B > 4) v++;            // verde = la banda OTE
          }
          if (n > 60) lineas++;
          if (v > 60) ote++;
        }
        return {lineas: lineas, ote: ote}; }""")
    check('el Fibonacci pinta sus niveles (%d filas de línea)' % fib['lineas'],
          fib['lineas'] >= 6, fib)
    # la banda OTE (0,62-0,79) es lo que ata la herramienta a lo que enseña el
    # sitio; sin ella son ocho rayas
    check('…y sombrea la banda OTE (%d px de alto)' % fib['ote'], fib['ote'] > 15, fib)
    limpia()

    # ── 🖱️ clic derecho = dejar de colocar ──
    # Queja del dueño: "si solo quieres colocar tres palitos no puedes, tienes
    # que terminar la tendencia como de 5 líneas".
    pg.keyboard.press('Escape')
    pg.wait_for_timeout(150)
    # 🔑 diapositiva NUEVA: sobre el lienzo vacío los píxeles se pueden contar
    #    y comparar; sobre lo ya dibujado, cualquier delta se pierde en el ruido
    pg.click('.slide-add')
    pg.wait_for_timeout(700)
    vacio, _ = dibujado()
    pulsa('polyline')
    pg.mouse.click(caja['x'] + 80, caja['y'] + 300)
    pg.wait_for_timeout(420)                             # lento: no es doble clic
    pg.mouse.click(caja['x'] + 170, caja['y'] + 240)
    pg.wait_for_timeout(420)
    un_tramo, _ = dibujado()
    pg.mouse.click(caja['x'] + 260, caja['y'] + 280)     # 3 puntos = 2 tramos
    pg.wait_for_timeout(420)
    dos_tramos, _ = dibujado()
    coste = dos_tramos - un_tramo                        # lo que cuesta UN tramo
    pg.mouse.move(caja['x'] + 340, caja['y'] + 220)      # el previo sigue al ratón
    pg.wait_for_timeout(200)
    pg.mouse.click(caja['x'] + 340, caja['y'] + 220, button='right')
    pg.wait_for_timeout(350)
    n_tras, _ = dibujado()
    check('el clic derecho cierra la polilínea SIN colocar un punto más '
          '(un tramo cuesta %d px, el cierre movió %d)' % (coste, n_tras - dos_tramos),
          coste > 120 and (n_tras - dos_tramos) < coste * 0.4,
          (un_tramo, dos_tramos, n_tras))
    check('…y lo ya trazado sigue ahí (cerrar no borra la tendencia)',
          n_tras > vacio + coste, (vacio, n_tras))
    # el siguiente clic izquierdo empieza una línea NUEVA, no continúa la
    # anterior: si siguiera abierta, uniría con el punto de antes
    pg.mouse.click(caja['x'] + 460, caja['y'] + 320)
    pg.wait_for_timeout(350)
    n_nueva, _ = dibujado()
    check('…y de verdad quedó cerrada (el clic siguiente no la continúa)',
          (n_nueva - n_tras) < coste * 0.4, (n_tras, n_nueva, coste))
    # sin nada en curso, el clic derecho suelta la herramienta
    pg.mouse.click(caja['x'] + 500, caja['y'] + 300, button='right')
    pg.wait_for_timeout(250)
    pg.mouse.click(caja['x'] + 520, caja['y'] + 260, button='right')
    pg.wait_for_timeout(250)
    check('sin nada en curso, el clic derecho suelta la herramienta',
          pg.evaluate(HERRAMIENTA) == 'select', pg.evaluate(HERRAMIENTA))
    check('el menú del navegador no se abre sobre la pizarra',
          pg.evaluate("""() => {
              const c = document.querySelector('#sk-canvas').parentNode
                        .querySelector('canvas.upper-canvas') ||
                        document.querySelector('canvas.upper-canvas');
              let visto = false;
              const h = e => { visto = !e.defaultPrevented; };
              c.addEventListener('contextmenu', h);
              c.dispatchEvent(new MouseEvent('contextmenu', {bubbles: true, cancelable: true}));
              c.removeEventListener('contextmenu', h);
              return !visto; }"""))
    # una figura a medio arrastrar se descarta y no deja nada
    pulsa('rect')
    n0r, _ = dibujado()
    pg.mouse.move(caja['x'] + 600, caja['y'] + 120)
    pg.mouse.down()
    pg.mouse.move(caja['x'] + 720, caja['y'] + 220, steps=8)
    pg.mouse.click(caja['x'] + 720, caja['y'] + 220, button='right')
    pg.mouse.up()
    pg.wait_for_timeout(300)
    n1r, _ = dibujado()
    check('una figura a medio arrastrar se descarta con el clic derecho',
          abs(n1r - n0r) < 250, (n0r, n1r))

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
    pg.wait_for_timeout(500)                      # el desplegable abre a los 150 ms
    abierto = pg.evaluate("""() => {
        const f = document.querySelector('.tool-group[data-familia="lineas"] .tool-flyout');
        const r = f.getBoundingClientRect();
        return getComputedStyle(f).display !== 'none' && r.width > 60 &&
               r.right < innerWidth && r.left > 0; }""")
    check('posar el ratón abre el desplegable, y cabe en pantalla', abierto)
    # 🔴 EL CASO QUE EL DUEÑO REPORTÓ, y que el test anterior NO cazaba:
    #    `page.click()` teletransporta el puntero al destino, así que nunca
    #    cruzaba los 8 px de aire entre la cabecera y el panel — justo donde el
    #    navegador dispara `mouseleave` y el desplegable se cerraba. Hay que
    #    mover el ratón POR PASOS, como una mano.
    destino = pg.locator(
        '.tool-group[data-familia="lineas"] .tool-btn[data-tool="hray"]')
    d = destino.bounding_box()
    h = pg.locator(cabecera).bounding_box()
    pg.mouse.move(h['x'] + h['width'] / 2, h['y'] + h['height'] / 2)
    pg.wait_for_timeout(400)
    pg.mouse.move(d['x'] + d['width'] / 2, d['y'] + d['height'] / 2, steps=25)
    pg.wait_for_timeout(120)
    check('el panel SIGUE abierto al cruzar el hueco hasta él (era el fallo)',
          pg.evaluate("""() => document.querySelector(
              '.tool-group[data-familia="lineas"]').classList.contains('open')"""))
    pg.mouse.down()
    pg.mouse.up()
    pg.wait_for_timeout(220)
    check('se puede elegir una herramienta del desplegable con el ratón',
          pg.evaluate(HERRAMIENTA) == 'hray', pg.evaluate(HERRAMIENTA))
    check('…y el desplegable se cierra solo al elegir',
          pg.evaluate("""() => getComputedStyle(document.querySelector(
              '.tool-group[data-familia="lineas"] .tool-flyout')).display === 'none'"""))
    # …y recorrer la lista por dentro tampoco lo cierra
    pg.hover(cabecera)
    pg.wait_for_timeout(400)
    ult = pg.locator(
        '.tool-group[data-familia="lineas"] .tool-btn[data-tool="arrow"]').bounding_box()
    pg.mouse.move(ult['x'] + ult['width'] / 2, ult['y'] + ult['height'] / 2, steps=30)
    pg.wait_for_timeout(150)
    check('bajar hasta el último nombre de la lista no cierra el panel',
          pg.evaluate("""() => document.querySelector(
              '.tool-group[data-familia="lineas"]').classList.contains('open')"""))
    pg.mouse.move(caja['x'] + 400, caja['y'] + 300, steps=10)
    pg.wait_for_timeout(500)
    check('sacar el ratón del grupo SÍ lo cierra',
          pg.evaluate("""() => !document.querySelector(
              '.tool-group[data-familia="lineas"]').classList.contains('open')"""))
    # ⚠️ el puente que mantiene abierto el panel va por ENCIMA (z-index 80): si
    #    se pasara de ancho, se comería el borde derecho del botón cabecera
    hh = pg.locator(cabecera).bounding_box()
    pg.keyboard.press('Escape')
    pg.wait_for_timeout(160)
    pg.mouse.click(hh['x'] + hh['width'] - 3, hh['y'] + hh['height'] / 2)
    pg.wait_for_timeout(220)
    check('el botón cabecera responde hasta su borde derecho (el puente no lo tapa)',
          pg.evaluate(HERRAMIENTA) == 'hray', pg.evaluate(HERRAMIENTA))
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

    # ── 💾 lo que ocupa una pizarra y el tope de diapositivas ──
    # 🔴 MEDIDO antes del arreglo: una diapositiva con fondo de REJILLA pesaba
    #    32,3 KB porque `canvas.toJSON()` hornea el fondo como una imagen
    #    base64 del lienzo entero, y se guardaba una copia idéntica por
    #    diapositiva. Con el cupo de ~5 MB del navegador, ~155 diapositivas y
    #    a partir de ahí guardar fallaba EN SILENCIO.
    pg.evaluate("""() => { localStorage.removeItem('scalperBoard'); }""")
    # ⚠️ /app BORRA el cookie del splash al servirse (es de un solo uso): sin
    #    volver a ponerlo, recargar rebota a /welcome y no hay ni pizarra
    pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                             'url': URL + '/'}])
    pg.goto(URL + '/app', wait_until='domcontentloaded')
    pg.wait_for_timeout(2200)
    pg.evaluate("""() => { const e =
        document.querySelector('.tab[data-tab="scalper"]'); if (e) e.click(); }""")
    pg.wait_for_timeout(3000)
    pg.evaluate("""() => { const b = document.querySelector('[data-bg="grid"]'); if (b) b.click(); }""")
    pg.wait_for_timeout(800)
    for _ in range(9):
        pg.click('.slide-add')
        pg.wait_for_timeout(180)
    pg.wait_for_timeout(600)
    peso = pg.evaluate("() => (localStorage.getItem('scalperBoard')||'').length")
    kb = peso / 1024.0 / 10
    check('10 diapositivas con rejilla ocupan %.1f KB c/u (antes 32,3)' % kb,
          kb < 3.0, peso)
    # el fondo tiene que SEGUIR viéndose, y sobrevivir a deshacer
    pinta = pg.evaluate("""() => {
        const c = document.querySelector('#sk-canvas-wrap canvas.lower-canvas') ||
                  document.querySelector('#sk-canvas');
        const g = c.getContext('2d'); const d = g.getImageData(4, 4, 1, 1).data;
        return [d[0], d[1], d[2]]; }""")
    check('la rejilla se sigue pintando sin guardarla en cada copia', sum(pinta) > 12,
          pinta)
    pulsa('rect')
    dibuja(60, 60, 180, 140)
    pg.evaluate("""() => document.getElementById('sk-undo').click()""")
    pg.wait_for_timeout(700)
    tras = pg.evaluate("""() => {
        const c = document.querySelector('#sk-canvas-wrap canvas.lower-canvas') ||
                  document.querySelector('#sk-canvas');
        const g = c.getContext('2d'); const d = g.getImageData(4, 4, 1, 1).data;
        return [d[0], d[1], d[2]]; }""")
    check('deshacer NO deja la diapositiva sin fondo', tras == pinta, (pinta, tras))

    # el tope: ni una diapositiva más, y se dice por qué
    # ⚠️ el número va escrito aquí a propósito: `MAX_SLIDES` es una const del
    #    módulo y no llega a `window`, así que preguntárselo a la página daría
    #    siempre el valor de reserva y el test no probaría nada
    tope = 20
    pg.evaluate("""() => { const b = document.getElementById('sk-add-slide');
        for (let i = 0; i < 80; i++) b.click(); }""")
    pg.wait_for_timeout(1200)
    n = pg.evaluate("""() => document.querySelectorAll('#sk-thumbs > *').length""")
    check('la pizarra se planta en el tope de %d diapositivas (quedaron %d)'
          % (tope, n), n == tope, n)
    # ⚠️ Un clic MÁS, justo antes de mirar. Llenar la pizarra deja al navegador
    #    renderizando 60 miniaturas durante bastante más de los 6 s que dura el
    #    aviso, así que mirarlo después de los 80 clics medía uno ya desvanecido
    #    (y parecía que no salía).
    pg.evaluate("""() => document.getElementById('sk-add-slide').click()""")
    pg.wait_for_timeout(250)
    # ⚠️ se comprueba el TEXTO traducido, no que "haya algo": la primera
    #    versión pintaba la clave cruda `scalper.maxSlides` porque el
    #    diccionario vive en otro <script> y `const` no llega a `window`
    aviso = pg.evaluate("""() => { const e = document.getElementById('sk-aviso');
        return e ? {ve: e.classList.contains('show'), txt: e.textContent} : null; }""")
    check('…y lo dice, en vez de ignorar el clic en silencio',
          aviso and aviso['ve'] and str(tope) in aviso['txt']
          and ' ' in aviso['txt'].strip()
          and not aviso['txt'].startswith('scalper.'), aviso)

    check('ningún error de JavaScript en toda la sesión', not errores, errores[:3])
    b.close()

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
