# -*- coding: utf-8 -*-
"""Reel #1 — EL TOUR: las herramientas del sitio, en uso, cortadas rápido.

Encargo del dueño, textual: enseñar toda o la gran mayoría del website, lo más
importante, "sus herramientas, y no solo mostrándolas sino utilizándolas",
picando entre usos con transiciones, y al final una transición DISTINTA hacia
una pantalla oscura con el logo.

CÓMO FUNCIONA — dos pasos, como `edita_reel.py`:

  1. GRABAR. Se conduce la app de verdad escena por escena (se pulsan pills,
     se marcan checks, se dibuja en la pizarra, se gira el 3D…). Antes de cada
     escena la página pega un fogonazo MAGENTA de ~2 fotogramas.
     🔑 Ese fogonazo es la clave del montaje: luego se buscan los picos de
     croma en el vídeo y ahí están los cortes, al fotograma exacto. Sin marcas
     habría que recortar a ojo y cada regrabación saldría distinta.
     Se busca por CROMA y no por brillo porque la app tiene tema claro: un
     fogonazo blanco no destaca sobre su propio fondo.

  2. MONTAR. El montaje entero es UNA página HTML con un `<video>` y el
     rotulado en DOM encima; se fotografía fotograma a fotograma calculando
     para cada uno qué segundo de la grabación toca. De ahí salen los cortes
     secos, el zoom y el cierre.

⚠️ El vídeo intermedio va en WebM: el Chromium sin cabeza no trae H.264 y el
   `<video>` del montaje daría DEMUXER_ERROR_NO_SUPPORTED_STREAMS.
⚠️ Cada escena se graba dentro de un try/except: si un selector cambia, esa
   escena se salta y el reel se monta con las demás en vez de morirse entero.

    python3 tools/reel_tour.py                 # graba y monta
    python3 tools/reel_tour.py --solo-montar   # reusa la grabación
"""
from __future__ import print_function

import base64
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTES_DIR = os.path.join(RAIZ, 'tools', '.fuentes')
SALIDA = os.path.join(RAIZ, 'out', 'reels')
CRUDO = os.path.join(SALIDA, '_crudo-tour.webm')
BEATS = os.path.join(SALIDA, '_beats-tour.json')
PUERTO = 5088
CL = 'Zx9!wQ4mNp2r'
ANCHO, ALTO = 900, 1600        # se graba ya en vertical
W, H = 1080, 1920
FPS = 30
ORO = '#c9a227'
AZUL = '#004feb'
GRAFITO = '#0b0d12'


# ══ 1 · GRABAR ═══════════════════════════════════════════════════════════
def arranca_servidor(tmp):
    os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tmp, 'r.db')
    os.environ.setdefault('SECRET_KEY', 'reel-tour')
    sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
    import app as A
    with A.app.app_context():
        A.db.create_all()
        u = A.User.query.filter_by(username='tour').first()
        if u is None:
            u = A.User(username='tour', email='t@demo.invalid',
                       plan='premium', email_verified=True)
            A.db.session.add(u)
        u.set_password(CL)
        u.email_canonical = u.email
        u.plan = 'premium'
        A.db.session.commit()
        if not A.PreflightChecklist.query.filter_by(user_id=u.id).count():
            A.db.session.add(A.PreflightChecklist(
                user_id=u.id, name='ICT — London session',
                config={'confluences': [
                    {'id': 'c1', 'label': 'HTF bias aligned'},
                    {'id': 'c2', 'label': 'Liquidity swept'},
                    {'id': 'c3', 'label': 'Displacement + BOS'},
                    {'id': 'c4', 'label': 'FVG in premium/discount'},
                    {'id': 'c5', 'label': 'Inside the kill zone'},
                    {'id': 'c6', 'label': 'Stop below the swept low'}],
                    'min_go': 5, 'min_caution': 3}))
            A.db.session.commit()
    threading.Thread(target=lambda: A.app.run(port=PUERTO, threaded=True,
                                              use_reloader=False),
                     daemon=True).start()
    for _ in range(80):
        time.sleep(.25)
        try:
            urllib.request.urlopen('http://127.0.0.1:%d/health' % PUERTO,
                                   timeout=1)
            return
        except Exception:
            pass
    sys.exit('el servidor no arrancó')


MARCA = """() => {
  const d = document.createElement('div');
  d.id = '_marca';
  d.style.cssText = 'position:fixed;inset:0;background:#f0f;z-index:2147483647';
  document.body.appendChild(d);
}"""


def graba():
    tmp = tempfile.mkdtemp()
    arranca_servidor(tmp)
    URL = 'http://127.0.0.1:%d' % PUERTO
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')
           or [None])[0]
    hechas = []

    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'],
                              **({'executable_path': exe} if exe else {}))
        prev = b.new_context(viewport={'width': ANCHO, 'height': ALTO})
        pp = prev.new_page()
        pp.route('**/*', lambda r: r.continue_()
                 if '127.0.0.1' in r.request.url else r.abort())
        pp.goto(URL + '/login', wait_until='domcontentloaded')
        pp.fill('input[name=identifier]', 'tour')
        pp.fill('input[name=password]', CL)
        pp.click('button[type=submit]')
        pp.wait_for_timeout(800)
        pp.evaluate("localStorage.setItem('scalpel_lang','%s')" % IDIOMA)
        pp.evaluate("localStorage.setItem('scalpel_theme','dark')")
        sesion = prev.storage_state()
        prev.close()

        ctx = b.new_context(viewport={'width': ANCHO, 'height': ALTO},
                            storage_state=sesion, record_video_dir=tmp,
                            record_video_size={'width': ANCHO, 'height': ALTO})
        pg = ctx.new_page()
        pg.route('**/*', lambda r: r.continue_()
                 if '127.0.0.1' in r.request.url else r.abort())

        def a_la_app():
            # ⚠️ /app BORRA el cookie del splash al servirse (un solo uso)
            pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                                     'url': URL + '/'}])
            pg.goto(URL + '/app', wait_until='domcontentloaded')
            pg.wait_for_timeout(2200)

        def tab(nombre):
            pg.evaluate("""t => { const e =
                document.querySelector('.tab[data-tab="' + t + '"]');
                if (e) e.click(); }""", nombre)

        def marca(indice):
            """Fogonazo magenta cuya DURACIÓN codifica el número de escena.

            🔑 Emparejar marcas con escenas por ORDEN es frágil: basta que una
            se pierda o que aparezca un pico de más para que TODOS los rótulos
            queden sobre la herramienta equivocada (pasó dos veces). Con la
            duración dentro de la propia marca, cada corte dice quién es y un
            fallo aislado no arrastra a los demás.
            ⚠️ Base 300 ms y paso 350: el grabador va a ~25 fps, así que la
            duración medida se cuantiza de 40 en 40 ms. Con paso de 200 ms
            una marca se leyó como la anterior; 350 deja margen de sobra.
            """
            pg.evaluate(MARCA)
            pg.wait_for_timeout(300 + 350 * indice)
            pg.evaluate("document.getElementById('_marca').remove()")

        def escena(nombre, fn, preparar=None):
            """Prepara en silencio, marca, y ENTONCES ejecuta lo que se ve."""
            idx = escena.siguiente
            try:
                if preparar:
                    preparar()
                marca(idx)
                fn()
                # 🔑 Reposo garantizado DESPUÉS de la acción: la ventana de
                # cada escena va de su marca a la siguiente, y la preparación
                # de la escena que viene (cambiar de pestaña, esperar a que
                # cargue) cae DENTRO de esa ventana. Sin este colchón, el final
                # del tramo ya enseña la herramienta siguiente — con Pre-Flight
                # se veía la mascota del quiz, porque su acción duraba 0,6 s.
                pg.wait_for_timeout(2700)
                hechas.append({'n': nombre, 'i': idx})
                escena.siguiente += 1
                print('  ok   %s (marca #%d)' % (nombre, idx))
            except Exception as e:
                print('  ---  %s (saltada: %s)' % (nombre, str(e)[:70]))

        escena.siguiente = 0
        a_la_app()

        # 1 · ANALIZADOR: se DESGLOSA el trade pulsando grupo por grupo, que
        #     es lo que hace entender el producto: activo → dirección →
        #     sesión → metodología → confluencias, y recién ahí la captura.
        def analizador():
            def grupo(g, texto):
                pg.evaluate("""([g, t]) => {
                  const c = document.querySelector('[data-group="' + g + '"]');
                  if (!c) return;
                  const b = [...c.querySelectorAll('.pill')]
                    .find(x => x.textContent.trim().startsWith(t));
                  if (b) { b.scrollIntoView({block:'center'}); b.click(); }
                }""", [g, texto])
                pg.wait_for_timeout(620)
            grupo('instrument', 'NQ')
            grupo('direction', 'Long')
            grupo('session', 'NY Morning')
            grupo('approach', 'ICT')
            grupo('confluences', 'Liquidity')
            grupo('confluences', 'FVG')
            pg.wait_for_timeout(600)
        escena('analizador', analizador, lambda: (tab('analyze'),
                                                  pg.wait_for_timeout(1500)))

        # 2 · PRE-FLIGHT: el encargo del dueño era ver cómo se ARMA la lista y
        #     cómo se van marcando las confluencias, así que la escena hace las
        #     dos: constructor → nombre → preset → guardar → tildar.
        #     ⚠️ `.pf-box` NO existe hasta que hay una lista ABIERTA (el tablero
        #     nace con `display:none`), por eso la versión anterior no tildaba
        #     nada: el bucle salía en la primera vuelta.
        def preflight():
            def clic(sel, i=0, espera=700):
                ok = pg.evaluate("""([s, i]) => {
                  const e = [...document.querySelectorAll(s)]
                    .filter(x => x.offsetParent)[i];
                  if (!e) return false;
                  e.scrollIntoView({block: 'center'}); e.click(); return true;
                }""", [sel, i])
                pg.wait_for_timeout(espera if ok else 120)
                return ok

            clic('.proj-tile.tile-new', 0, 900)           # + nueva lista
            pg.click('#pf-builder-name')
            pg.type('#pf-builder-name', 'NY Open — long', delay=52)
            pg.wait_for_timeout(450)
            clic('#pf-template-btns .proj-btn', 2, 950)   # un preset la rellena
            clic('#pf-builder-save', 0, 1300)             # y queda guardada
            for i in range(5):                            # ahora sí, a tildar
                if not clic('.pf-row', i, 440):
                    break
            pg.wait_for_timeout(900)
        escena('preflight', preflight, lambda: (tab('preflight'),
                                                pg.wait_for_timeout(2400)))

        # 3 · QUIZ: el camino REAL hasta responder.
        #     ⚠️ La opción (a) de la bienvenida es "test what I studied in
        #     Synapse" y lleva a una pantalla VACÍA con un botón "Go to
        #     Synapse" — era la que salía en la versión anterior. La buena es
        #     la (b), "verify the knowledge I already have".
        def quiz():
            def pulsa(sel, i=0, espera=1700):
                ok = pg.evaluate("""([s, i]) => {
                  const e = [...document.querySelectorAll(s)]
                    .filter(x => x.offsetParent)[i];
                  if (!e) return false;
                  e.scrollIntoView({block: 'center'}); e.click(); return true;
                }""", [sel, i])
                pg.wait_for_timeout(espera if ok else 120)
                return ok
            pulsa('.quiz-welcome-opt', 1, 1200)      # (b), no la (a)
            pulsa('.quiz-method-card', 0, 1000)      # ICT
            pulsa('.quiz-topic-card', 0, 1100)       # Order Blocks
            pulsa('.quiz-placement-cta', 0, 2000)    # arranca el test
            pg.wait_for_timeout(1400)                # se lee la pregunta
            # ⚠️ Las opciones se barajan (es la defensa anti-trampa), así que
            # pulsar "la segunda" acierta o falla según el día. Se pulsa la
            # BUENA, que el propio DOM marca con data-ok, y así el reel siempre
            # remata con el "Correct!" verde y su explicación.
            pulsa('.quiz-opt[data-ok="true"]', 0, 2100)
            pg.wait_for_timeout(700)

        def a_quiz():
            tab('quiz')
            pg.wait_for_timeout(2300)
            # 🔑 El quiz ocupa el tercio superior de una pantalla de 1600 px y
            # el resto queda vacío: encuadrado así, el reel enseñaría sobre todo
            # el pie de página. Se amplía LA PÁGINA (nítido, se re-renderiza)
            # en vez de ampliar el vídeo en el montaje (borroso, es reescalado).
            pg.evaluate("document.documentElement.style.zoom = '1.55'")
            pg.wait_for_timeout(600)
        escena('quiz', quiz, a_quiz)
        pg.evaluate("document.documentElement.style.zoom = ''")
        pg.wait_for_timeout(400)

        # 4 · CHALKBOARD: con la herramienta LÍNEA DE TENDENCIA, trazada
        #     tramo a tramo — no el rectángulo de antes
        def pizarra():
            caja = pg.evaluate("""() => { const c =
                document.querySelector('#sk-canvas'); if (!c) return null;
                const r = c.getBoundingClientRect();
                return {x: r.x, y: r.y, w: r.width, h: r.height}; }""")
            if not caja:
                raise RuntimeError('sin lienzo')
            pg.evaluate("""() => { const b =
                document.querySelector('.tool-btn[data-tool="trendline"]');
                if (b) b.click(); }""")
            pg.wait_for_timeout(500)
            # tres tramos de una tendencia alcista, dibujados uno a uno
            tramos = [(.14, .78, .42, .52), (.42, .52, .66, .62), (.66, .62, .88, .28)]
            for x0, y0, x1, y1 in tramos:
                pg.mouse.move(caja['x'] + caja['w'] * x0, caja['y'] + caja['h'] * y0)
                pg.mouse.down()
                for k in range(1, 13):
                    pg.mouse.move(caja['x'] + caja['w'] * (x0 + (x1 - x0) * k / 12.0),
                                  caja['y'] + caja['h'] * (y0 + (y1 - y0) * k / 12.0))
                    pg.wait_for_timeout(26)
                pg.mouse.up()
                pg.wait_for_timeout(320)
            pg.wait_for_timeout(700)
        escena('chalkboard', pizarra, lambda: (tab('scalper'),
                                               pg.wait_for_timeout(4500)))

        # 5 · SYNAPSE: disparar → entrar a una metodología → ABRIR un
        #     concepto, que es lo que enseña qué hay dentro de la biblioteca
        def synapse():
            pg.mouse.click(ANCHO * .5, ALTO * .42)          # dispara la sinapsis
            pg.wait_for_timeout(2100)
            pg.evaluate("""() => { const p =
                document.querySelector('.syn-fire-prompt');
                if (p) p.style.opacity = '0'; }""")
            pg.evaluate("""() => {
              const n = [...document.querySelectorAll('.syn-node-label')]
                .find(e => /SMC|ICT/i.test(e.textContent))
                || document.querySelector('.syn-node-label');
              if (n) n.click();
            }""")
            pg.wait_for_timeout(2600)                       # se abre la biblioteca
            # y se abre una NEURONA concreta: ahí está el dossier del concepto.
            # ⚠️ Dos trampas encadenadas aquí. Un clic a ciegas en el centro de
            # `.syn-lib-stage` cae en el vacío entre nodos y no abre nada (era
            # lo que pasaba antes). Y apuntar al centro del `<g>.syn-neuron`
            # TAMPOCO sirve: el grupo contiene el cuerpo y su etiqueta 24px más
            # abajo, así que el centro de su caja cae justo en el hueco entre
            # los dos — y en SVG solo hay impacto sobre geometría pintada, no
            # sobre la caja. Se apunta al cuerpo (`.syn-soma`).
            caja = pg.evaluate("""() => {
                const s = document.querySelectorAll('.syn-neuron .syn-soma');
                if (!s.length) return null;
                const r = s[Math.min(4, s.length - 1)].getBoundingClientRect();
                return {x: r.x + r.width / 2, y: r.y + r.height / 2}; }""")
            if caja:
                pg.mouse.move(caja['x'], caja['y'])
                pg.wait_for_timeout(500)
                pg.mouse.click(caja['x'], caja['y'])
                pg.wait_for_timeout(1700)                  # el dossier, abierto
                # y se pasa una página: los 4 puntos del pie dejan claro que
                # cada concepto es un cuadernillo, no una ficha suelta
                pg.evaluate("""() => { const b =
                    document.getElementById('syn-book-next');
                    if (b) b.click(); }""")
                pg.wait_for_timeout(1800)
            pg.wait_for_timeout(700)
        escena('synapse', synapse, lambda: (tab('synapse'),
                                            pg.wait_for_timeout(14500)))

        # 6 · FORO
        def foro():
            for i in range(8):
                pg.mouse.wheel(0, 190)
                pg.wait_for_timeout(150)
            pg.wait_for_timeout(900)
        escena('foro', foro, lambda: (tab('forum'), pg.wait_for_timeout(2600)))

        # 7 · COSMÉTICOS: se recorren camo, marco y cursor, no solo scroll
        def cosmeticos():
            for anc in ('.camo-swatch', '.cm-plate-strip', '.cp-art'):
                el = pg.query_selector(anc)
                if el:
                    try:
                        el.scroll_into_view_if_needed()
                        pg.wait_for_timeout(280)
                        el.hover()
                        pg.wait_for_timeout(900)
                    except Exception:
                        pass
            for i in range(4):
                pg.mouse.wheel(0, 240)
                pg.wait_for_timeout(200)
            pg.wait_for_timeout(700)

        def ir_cosmeticos():
            pg.goto(URL + '/cosmetics', wait_until='domcontentloaded')
            pg.wait_for_timeout(2500)
        escena('cosmeticos', cosmeticos, ir_cosmeticos)

        # 8 · TESSERA: más aire, que las paredes tardan ~2 s en subir
        def tessera():
            pg.evaluate("document.getElementById('nx-cube').click()")
            pg.wait_for_timeout(5200)
        escena('tessera', tessera, a_la_app)

        ctx.close()
        b.close()

    webm = sorted(glob.glob(os.path.join(tmp, '*.webm')))
    if not webm:
        sys.exit('Playwright no dejó vídeo')
    os.makedirs(SALIDA, exist_ok=True)
    shutil.copy(webm[0], CRUDO)
    io.open(BEATS, 'w', encoding='utf-8').write(json.dumps(hechas))
    shutil.rmtree(tmp, ignore_errors=True)
    print('grabación:', CRUDO, '·', len(hechas), 'escenas')


# ══ 2 · LOS CORTES ═══════════════════════════════════════════════════════
def marcas():
    """Devuelve [(indice_de_escena, segundo_de_inicio, segundo_de_fin)].

    Cada fogonazo dura 260 + 200*indice ms, así que midiendo cuánto dura el
    pico de croma se sabe QUÉ escena empieza — no hace falta fiarse del orden.
    """
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    r = subprocess.run(
        [ff, '-i', CRUDO, '-vf',
         'signalstats,metadata=print:key=lavfi.signalstats.VAVG',
         '-f', 'null', '-'], capture_output=True, text=True)
    serie, t = [], None
    for ln in r.stderr.splitlines():
        m = re.search(r'pts_time:([0-9.]+)', ln)
        if m:
            t = float(m.group(1))
        m = re.search(r'VAVG=([0-9.]+)', ln)
        if m and t is not None:
            serie.append((t, float(m.group(1))))
    picos, dentro, ini, fin = [], False, 0, 0
    for tt, v in serie:
        alto = v > 185
        if alto and not dentro:
            dentro, ini, fin = True, tt, tt
        elif alto:
            fin = tt
        elif dentro and tt - fin > 0.12:      # se cerró el fogonazo
            dentro = False
            picos.append((fin - ini, ini, fin))
    if dentro:
        picos.append((fin - ini, ini, fin))
    # 🔑 El índice sale del ORDEN de las duraciones, no de su valor absoluto:
    # `wait_for_timeout` se pasa cada vez más según crece la espera (pedí
    # 2050 ms y midió 2280), así que decodificar por valor emparejaba dos
    # marcas con el mismo número. Lo que SÍ se conserva es que cada marca dura
    # más que la anterior, y de ahí sale el índice sin margen de error.
    orden = sorted(range(len(picos)), key=lambda k: picos[k][0])
    salida = [None] * len(picos)
    for idx, k in enumerate(orden):
        salida[k] = (idx, picos[k][1], picos[k][2])
    dur = serie[-1][0] if serie else 0
    return salida, dur


def logo_oscuro(destino):
    """Logo para fondo oscuro: logotipo BLANCO conservando la 'a' AZUL.

    🔴 Antes se resolvía con `filter:brightness(0) invert(1)` en CSS, y eso
    pinta de blanco TODO — incluida la 'a', que es la única pieza de color de
    la marca. Aquí se recolorea píxel a píxel: lo azul se queda azul.
    """
    from PIL import Image
    im = Image.open(os.path.join(RAIZ, 'scalpel', 'static',
                                 'logo_t.png')).convert('RGBA')
    im = im.crop(im.getchannel('A').getbbox())
    px = im.load()
    W, Hh = im.size
    for y in range(Hh):
        for x in range(W):
            r, g, bb, a = px[x, y]
            if not a:
                continue
            # el mismo criterio que usa el generador de posts para hallar la 'a'
            if bb > 90 and bb - r > 45 and bb - g > 35:
                px[x, y] = (0, 79, 235, a)          # azul de marca medido
            else:
                px[x, y] = (255, 255, 255, a)
    im.save(destino)


def fuentes_css():
    css = []
    for arch in sorted(os.listdir(FUENTES_DIR)):
        if not arch.endswith('.ttf'):
            continue
        fam, peso = arch[:-4].rsplit('-', 1)
        fam = {'JetBrainsMono': 'JetBrains Mono'}.get(fam, fam)
        b64 = base64.b64encode(
            io.open(os.path.join(FUENTES_DIR, arch), 'rb').read()).decode()
        css.append("@font-face{font-family:'%s';font-weight:%s;"
                   "src:url(data:font/ttf;base64,%s) format('truetype')}"
                   % (fam, peso, b64))
    return ''.join(css)


# ══ 3 · EL MONTAJE ═══════════════════════════════════════════════════════
IDIOMA = os.environ.get('REEL_LANG', 'en')      # 'en' o 'es'

TEXTOS = {
 'en': {
  'intro1': 'This is not<br>a course.', 'intro2': "It's an<br><em>ecosystem</em>.",
  'eq': 'Tradeable Academy', 'cierre': 'Educational content · Not financial advice',
  # 🔑 En la tarjeta final va el LEMA, no el arroba: Instagram ya pinta el
  #    usuario encima del vídeo y el logo ya dice el nombre justo arriba — ese
  #    renglón estaba gastado. Y el lema dice qué ES la marca, no qué promete:
  #    un "reach your goals" en un sitio de trading se lee como "vas a ganar
  #    dinero" y contradice el descargo que sale DOS LÍNEAS más abajo.
  #    Recoge además el "stop trading on impulse" de la escena 02: aquello era
  #    la instrucción, esto es el principio.
  'lema': 'Process over impulse.',
  'analizador': ('Break down your trade.',
                 'Instrument, direction, session, methodology — then upload the chart'),
  'preflight': ('Build your confluence list.',
                'Stop trading on impulse. See which confluences actually hold up'),
  'quiz': ('400+ quizzes across every methodology',
           'From beginner to ultra-hardcore'),
  'chalkboard': ('Your own chalkboard.',
                 'Study, build, record your own lessons'),
  'synapse': ('41 topics. One map.',
              'The whole library, in 3D'),
  'foro': ('A community, not a signal group.',
           'Moderated trader forum'),
  'cosmeticos': ('Make the ecosystem yours.',
                 'Camos, profile plates and cursors'),
  'tessera': ('Help inside the site.', 'Tessera, your assistant'),
 },
 'es': {
  'intro1': 'Esto no<br>es un curso.', 'intro2': 'Es un<br><em>ecosistema</em>.',
  'eq': 'Tradeable Academy', 'cierre': 'Contenido educativo · No es asesoría financiera',
  'lema': 'Proceso antes que impulso.',
  'analizador': ('Desglosa tu operación.',
                 'Activo, dirección, sesión, metodología — y luego subes el gráfico'),
  'preflight': ('Arma tu lista de confluencias.',
                'Deja de operar por impulso. Mira cuáles te funcionan de verdad'),
  'quiz': ('400+ quizzes de todas las metodologías',
           'De principiante a ultrahardcore'),
  'chalkboard': ('Tu propio pizarrón.',
                 'Estudia, crea y graba tus clases'),
  'synapse': ('41 temas. Un solo mapa.', 'La biblioteca entera, en 3D'),
  'foro': ('Una comunidad, no un grupo de señales.', 'Foro moderado de traders'),
  'cosmeticos': ('Haz tuyo el ecosistema.', 'Camos, placas y cursores'),
  'tessera': ('Ayuda dentro del sitio.', 'Tessera, tu asistente'),
 },
}
T = TEXTOS[IDIOMA]
ROTULOS = {k: v for k, v in T.items() if isinstance(v, tuple)}

# Cada herramienta necesita su propio tiempo: el analizador enseña 4 pasos y
# la Cámara de Tessera tarda ~2 s solo en abrir las paredes.
DURACION = {'analizador': 3.2, 'preflight': 5.4, 'quiz': 4.4, 'chalkboard': 2.8,
            'synapse': 7.8, 'foro': 2.2, 'cosmeticos': 2.6, 'tessera': 4.8}

# 🔑 Desde qué segundo de SU grabación se mira cada escena.
# Por defecto se toma el trozo inicial, porque el final de la ventana lo ocupa
# la preparación de la escena siguiente. Pero en tres herramientas lo que hay
# que enseñar —el remate— pasa al final: el quiz tarda ~4 s en llegar a la
# pregunta y Synapse ~5 s en abrir el dossier. Sin este desfase el reel cortaba
# justo ANTES de lo que el dueño pidió ver.
# En Tessera la Cámara tarda ~2 s en levantar sus paredes. Se probó saltárselas
# (empezaba en negro y parecía un fallo), pero el dueño pidió justo lo
# contrario: que se VEA abrirse. Así que el tramo empieza en el clic y dura lo
# suficiente para las paredes MÁS la constelación ya montada — un reveal que
# empieza oscuro solo funciona si después se queda el tiempo del premio.
# ⚠️ Synapse va a 0 A PROPÓSITO: es la única escena que empieza por el
#    principio, porque su principio ES lo que hay que enseñar — la escultura 3D
#    girando y el "Fire a synapse" abriendo el mapa de metodologías. Pedido
#    expreso del dueño, y por eso su tramo dura casi 8 s.
DESDE = {'preflight': 1.0, 'quiz': 3.6, 'synapse': 0.0, 'tessera': 0.1}

PAGINA = """<!doctype html><meta charset=utf-8><style>@@FUENTES@@
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:@@W@@px;height:@@H@@px;background:@@GRAF@@;overflow:hidden;
  font-family:Inter,sans-serif;color:#fff}
#capa{position:absolute;inset:0;overflow:hidden}
video{position:absolute;left:50%;top:50%;width:@@W@@px;height:@@H@@px;
  transform-origin:center center;translate:-50% -50%}
#vig{position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 88% 72% at 50% 46%,transparent 54%,rgba(0,0,0,.38))}
/* ⚠️ El velo tiene que aguantar una escena de fondo CLARO (la tienda de
   cosméticos no tiene modo oscuro): con el degradado suave de antes, el titular
   quedaba blanco sobre gris medio y no se leía. Se oscurece antes y más. */
#scrim{position:absolute;left:0;right:0;bottom:0;height:50%;pointer-events:none;
  background:linear-gradient(transparent,rgba(0,0,0,.34) 26%,rgba(0,0,0,.92) 62%)}
#rot{position:absolute;left:70px;right:70px;bottom:250px}
#rot .g{font:900 72px/1.02 Inter,sans-serif;letter-spacing:-.03em;
  text-shadow:0 8px 40px rgba(0,0,0,.9)}
#rot .p{margin-top:16px;font:500 31px/1.35 Inter,sans-serif;
  color:rgba(255,255,255,.80);text-shadow:0 4px 24px rgba(0,0,0,.9)}
#num{position:absolute;right:70px;top:120px;font:700 24px 'JetBrains Mono',monospace;
  letter-spacing:.24em;color:@@ORO@@;text-shadow:0 2px 18px rgba(0,0,0,.9)}
#intro{position:absolute;inset:0;background:@@GRAF@@;display:flex;
  flex-direction:column;justify-content:center;padding:0 88px}
#intro .eq{font:700 26px 'JetBrains Mono',monospace;letter-spacing:.4em;
  color:@@ORO@@;text-transform:uppercase;margin-bottom:30px}
#intro h1{font:900 116px/0.96 Inter,sans-serif;letter-spacing:-.04em}
#intro h1 em{font-style:normal;color:@@ORO@@}
#flash{position:absolute;inset:0;background:#fff;opacity:0;pointer-events:none}
#out{position:absolute;inset:0;background:#05060a;display:flex;
  flex-direction:column;align-items:center;justify-content:center;gap:30px}
#out img{width:520px}   /* sin filtro: el logo ya viene con su "a" azul */
#out .s{font:700 26px 'JetBrains Mono',monospace;letter-spacing:.34em;
  color:@@ORO@@;text-transform:uppercase}
#out .a{font:600 34px Inter,sans-serif;color:rgba(255,255,255,.66)}
#out .l{position:absolute;bottom:140px;font:400 22px Inter,sans-serif;
  color:rgba(255,255,255,.32)}
#bar{position:absolute;left:0;bottom:0;height:7px;background:@@ORO@@}
</style><body>
<div id=capa><video id=v src="@@SRC@@" muted preload=auto></video>
  <div id=vig></div><div id=scrim></div></div>
<div id=rot></div><div id=num></div>
<div id=intro><div class=eq>@@EQ@@</div><h1 id=ih></h1></div>
<div id=flash></div>
<div id=out><img src="@@LOGO@@" alt=""><div class=s>@@EQ@@</div>
  <div class=a>@@LEMA@@</div>
  <div class=l>@@CIERRE@@</div></div>
<div id=bar></div>
<script>
const V=document.getElementById('v'), PLAN=@@PLAN@@, DUR=@@DUR@@;
const suav = t => t<0?0:t>1?1:t*t*(3-2*t);
const tr = (t,a,b) => suav((t-a)/(b-a));

/* De segundo del REEL a segundo de la GRABACIÓN. PLAN trae, por escena,
   dónde empieza en el reel, cuánto dura, y qué trozo de grabación usa. */
function tramo(t){
  for(const s of PLAN) if(t >= s.r0 && t < s.r1) return s;
  return null;
}
window.enCuadre = async function(t){
  // 1 · intro
  const fin = tr(t,@@I0@@,@@I1@@);
  const intro=document.getElementById('intro');
  intro.style.clipPath = 'inset(0 0 '+(fin*100)+'% 0)';
  const ih=document.getElementById('ih');
  ih.innerHTML = t<2.45 ? @@I1TXT@@ : @@I2TXT@@;
  const e1 = t<2.45 ? tr(t,.30,.95)*(1-tr(t,2.15,2.45)) : tr(t,2.50,3.10);
  ih.style.opacity = e1;
  ih.style.transform = 'translateY('+(32*(1-e1))+'px)';
  document.querySelector('#intro .eq').style.opacity = tr(t,.1,.5);

  // 2 · el vídeo: qué escena toca y con cuánto zoom
  const s = tramo(t);
  if (s){
    const k = (t - s.r0) / (s.r1 - s.r0);
    const src = s.v0 + (s.v1 - s.v0) * k;
    if (Math.abs(V.currentTime - src) > 0.005){
      V.currentTime = src;
      await new Promise(r => { let ok=false;
        V.onseeked = () => { if(!ok){ok=true; r();} };
        setTimeout(() => { if(!ok){ok=true; r();} }, 350); });
    }
    /* zoom que ENTRA en cada escena: da sensación de cámara y disimula el
       corte seco entre herramientas */
    V.style.scale = 1.06 + 0.10*k;
    // 3 · rótulo de la escena
    const rot=document.getElementById('rot');
    const ap = tr(t,s.r0+.12,s.r0+.45) * (1 - tr(t,s.r1-.42,s.r1-.06));
    rot.innerHTML = '<div class=g>'+s.g+'</div><div class=p>'+s.p+'</div>';
    rot.style.opacity = ap;
    rot.style.transform = 'translateY('+(24*(1-ap))+'px)';
    document.getElementById('scrim').style.opacity = ap;
    const num=document.getElementById('num');
    num.textContent = s.n; num.style.opacity = ap;
  } else {
    document.getElementById('rot').style.opacity = 0;
    document.getElementById('num').style.opacity = 0;
    document.getElementById('scrim').style.opacity = 0;
  }

  /* 4 · el CORTE: un fogonazo blanco muy corto en cada cambio de escena.
     Es lo que hace que "pique" en vez de fundirse. */
  let fl = 0;
  for(const x of PLAN) fl = Math.max(fl, 1 - Math.min(1, Math.abs(t - x.r0)/0.09));
  document.getElementById('flash').style.opacity = fl*0.85;

  // 5 · cierre: transición DISTINTA (barrido vertical) a negro con el logo
  const o = tr(t,@@O0@@,@@O0@@+0.55);
  const out=document.getElementById('out');
  out.style.opacity = o>0 ? 1 : 0;
  out.style.clipPath = 'inset('+((1-o)*100)+'% 0 0 0)';

  document.getElementById('bar').style.width = (100*t/DUR)+'%';
};
</script></body>"""


def monta():
    import imageio_ffmpeg
    from playwright.sync_api import sync_playwright
    picos, dur_src = marcas()
    hechas = json.loads(io.open(BEATS, encoding='utf-8').read())
    porIdx = {p[0]: p for p in picos}
    print('escenas grabadas: %d · marcas leídas: %s'
          % (len(hechas), [(p[0], round((p[2] - p[1]) * 1000)) for p in picos]))
    faltan = [h['n'] for h in hechas if h['i'] not in porIdx]
    if faltan:
        # 🔴 montar sin la marca de una escena desfasa su rótulo respecto a la
        # herramienta que se ve, que es peor que no tener reel.
        sys.exit('sin marca para: %s. Vuelve a grabar.' % ', '.join(faltan))

    # ⚠️ Intro de 4,8 s: con 2,3 s las dos frases pasaban tan rápido que
    # no daba tiempo a leerlas.
    # ⚠️ El cierre dura 4,30 y no 2,80 porque el logo tiene que seguir en
    # pantalla mientras suena la MARCA SONORA (tools/marca_sonora.py): una
    # firma de audio que termina sobre negro no la asocia nadie con la marca.
    # Si se acorta el sonido, acórtese también esto — van juntos.
    INTRO, CIERRE = 4.80, 4.30
    orden = sorted(picos, key=lambda p: p[1])
    sig = {p[0]: (orden[k + 1][1] if k + 1 < len(orden) else dur_src)
           for k, p in enumerate(orden)}
    plan, r = [], INTRO
    for i, h in enumerate(hechas):
        nombre, idx = h['n'], h['i']
        v0 = porIdx[idx][2] + 0.16          # justo después de que acaba el flash
        tope = min(dur_src, sig[idx] - 0.25)
        dur = DURACION.get(nombre, 2.6)
        # el desfase se recorta si no cabe: antes de dejar la escena fuera del
        # reel es preferible enseñarla desde donde se pueda
        v0 = min(v0 + DESDE.get(nombre, 0.0), max(v0, tope - dur))
        if tope - v0 < 0.8:          # escena demasiado corta: se descarta
            continue
        v1 = min(tope, v0 + dur)
        g, p = ROTULOS.get(nombre, (nombre, ''))
        plan.append({'r0': round(r, 3), 'r1': round(r + dur, 3),
                     'v0': round(v0, 3), 'v1': round(v1, 3),
                     'g': g, 'p': p, 'n': '%02d' % (i + 1)})
        r += dur
    total = round(r + CIERRE, 2)
    print('reel de %.1f s con %d escenas' % (total, len(plan)))

    doc = PAGINA
    for marca, valor in (('@@FUENTES@@', fuentes_css()), ('@@W@@', str(W)),
                         ('@@H@@', str(H)), ('@@GRAF@@', GRAFITO),
                         ('@@ORO@@', ORO), ('@@SRC@@', os.path.basename(CRUDO)),
                         ('@@LOGO@@', 'logo_tour.png'),
                         ('@@PLAN@@', json.dumps(plan)),
                         ('@@DUR@@', '%.2f' % total),
                         ('@@I1TXT@@', json.dumps(T['intro1'])),
                         ('@@I2TXT@@', json.dumps(T['intro2'])),
                         ('@@EQ@@', T['eq']), ('@@CIERRE@@', T['cierre']),
                         ('@@LEMA@@', T['lema']),
                         ('@@I0@@', '%.2f' % (INTRO - 0.30)),
                         ('@@I1@@', '%.2f' % INTRO),
                         ('@@O0@@', '%.2f' % r)):
        doc = doc.replace(marca, valor)

    logo_oscuro(os.path.join(SALIDA, 'logo_tour.png'))
    ruta = os.path.join(SALIDA, '_montaje_tour.html')
    io.open(ruta, 'w', encoding='utf-8').write(doc)

    carpeta = tempfile.mkdtemp()
    n = int(total * FPS)
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')
           or [None])[0]
    with sync_playwright() as p:
        b = p.chromium.launch(
            args=['--no-sandbox', '--allow-file-access-from-files',
                  '--autoplay-policy=no-user-gesture-required'],
            **({'executable_path': exe} if exe else {}))
        pg = b.new_page(viewport={'width': W, 'height': H})
        pg.goto('file://' + ruta, wait_until='load')
        pg.wait_for_function("document.getElementById('v').readyState >= 2",
                             timeout=30000)
        for i in range(n):
            pg.evaluate('enCuadre(%f)' % (i / float(FPS)))
            pg.screenshot(path=os.path.join(carpeta, '%04d.png' % i))
            if i % 60 == 0:
                print('  fotograma %d/%d' % (i, n))
        b.close()
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    dest = os.path.join(SALIDA, 'reel-tour.mp4')
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(FPS),
                    '-i', os.path.join(carpeta, '%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18',
                    '-movflags', '+faststart', dest], check=True)
    shutil.rmtree(carpeta, ignore_errors=True)
    print('listo:', dest, '· %.1f MB' % (os.path.getsize(dest) / 1e6))


if __name__ == '__main__':
    if '--solo-montar' not in sys.argv:
        graba()
    monta()
