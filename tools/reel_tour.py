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
        pp.evaluate("localStorage.setItem('scalpel_lang','es')")
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

        # 1 · ANALIZADOR: se rellena el setup pulsando pills de verdad
        def analizador():
            for sel in ('[data-group="instrument"] .pill, .pill',):
                pass
            pills = pg.query_selector_all('#analyze-container .pill')
            for i in (2, 14, 26, 33):
                if i < len(pills):
                    pills[i].click()
                    pg.wait_for_timeout(520)
            pg.wait_for_timeout(700)
        escena('analizador', analizador, lambda: (tab('analyze'),
                                                  pg.wait_for_timeout(1400)))

        # 2 · PRE-FLIGHT: se marcan comprobaciones
        def preflight():
            cajas = pg.query_selector_all('.pf-box, .pf-check, .pf-row input')
            for c in cajas[:5]:
                try:
                    c.click()
                    pg.wait_for_timeout(430)
                except Exception:
                    pass
            pg.wait_for_timeout(600)
        escena('preflight', preflight, lambda: (tab('preflight'),
                                                pg.wait_for_timeout(1800)))

        # 3 · QUIZ: se responde una pregunta
        def quiz():
            pg.wait_for_timeout(900)
            for sel in ('.quiz-intent', '.quiz-start', '.quiz-topic',
                        '.quiz-opt'):
                el = pg.query_selector(sel)
                if el:
                    el.click()
                    pg.wait_for_timeout(1100)
            pg.wait_for_timeout(900)
        escena('quiz', quiz, lambda: (tab('quiz'), pg.wait_for_timeout(2000)))

        # 4 · CHALKBOARD: se dibuja de verdad sobre el lienzo
        def pizarra():
            caja = pg.evaluate("""() => { const c =
                document.querySelector('#sk-canvas'); if (!c) return null;
                const r = c.getBoundingClientRect();
                return {x: r.x, y: r.y, w: r.width, h: r.height}; }""")
            if not caja:
                raise RuntimeError('sin lienzo')
            lapiz = pg.query_selector('.sk-tool[data-tool="draw"], .sk-tool')
            if lapiz:
                lapiz.click()
                pg.wait_for_timeout(400)
            x0, y0 = caja['x'] + caja['w'] * .18, caja['y'] + caja['h'] * .70
            pg.mouse.move(x0, y0)
            pg.mouse.down()
            for i in range(1, 26):
                pg.mouse.move(x0 + i * (caja['w'] * .026),
                              y0 - i * (caja['h'] * .018)
                              + (18 if i % 6 < 3 else -18))
                pg.wait_for_timeout(24)
            pg.mouse.up()
            pg.wait_for_timeout(900)
        escena('chalkboard', pizarra, lambda: (tab('scalper'),
                                               pg.wait_for_timeout(4200)))

        # 5 · SYNAPSE: el velo dura 10 s A PROPÓSITO, así que se marca DESPUÉS
        def synapse():
            pg.mouse.move(ANCHO * .5, ALTO * .45)
            for i in range(22):
                pg.mouse.move(ANCHO * (.5 + .012 * i), ALTO * (.45 - .004 * i))
                pg.wait_for_timeout(45)
            pg.wait_for_timeout(1500)
        escena('synapse', synapse, lambda: (tab('synapse'),
                                            pg.wait_for_timeout(14500)))

        # 6 · FORO: se recorre el feed
        def foro():
            for i in range(8):
                pg.mouse.wheel(0, 190)
                pg.wait_for_timeout(150)
            pg.wait_for_timeout(800)
        escena('foro', foro, lambda: (tab('forum'), pg.wait_for_timeout(2600)))

        # 7 · COSMÉTICOS: la tienda, que es puro color
        def cosmeticos():
            for i in range(7):
                pg.mouse.wheel(0, 220)
                pg.wait_for_timeout(150)
            pg.wait_for_timeout(700)

        def ir_cosmeticos():
            pg.goto(URL + '/cosmetics', wait_until='domcontentloaded')
            pg.wait_for_timeout(2400)
        escena('cosmeticos', cosmeticos, ir_cosmeticos)

        # 8 · TESSERA: la Cámara abriéndose, como remate antes del logo
        def tessera():
            pg.evaluate("document.getElementById('nx-cube').click()")
            pg.wait_for_timeout(4200)
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
ROTULOS = {
    'analizador': ('Subes tu gráfico.', 'Te corrige en TU metodología'),
    'preflight': ('¿Te sirven tus confluencias?', 'Checklists con estadísticas reales'),
    'quiz': ('De básico a ultrahardcore', 'Quizzes de casi todas las metodologías'),
    'chalkboard': ('Tu pizarra.', 'Estudia, crea, graba tus clases'),
    'synapse': ('41 temas. Un solo mapa.', 'La biblioteca, en 3D'),
    'foro': ('Comunidad, sin señales.', 'Foro moderado de traders'),
    'cosmeticos': ('Y hasta se personaliza.', 'Camos, marcos y cursores'),
    'tessera': ('Ayuda dentro del sitio.', 'Tessera, tu asistente'),
}

PAGINA = """<!doctype html><meta charset=utf-8><style>@@FUENTES@@
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:@@W@@px;height:@@H@@px;background:@@GRAF@@;overflow:hidden;
  font-family:Inter,sans-serif;color:#fff}
#capa{position:absolute;inset:0;overflow:hidden}
video{position:absolute;left:50%;top:50%;width:@@W@@px;height:@@H@@px;
  transform-origin:center center;translate:-50% -50%}
#vig{position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 88% 72% at 50% 46%,transparent 54%,rgba(0,0,0,.38))}
#scrim{position:absolute;left:0;right:0;bottom:0;height:50%;pointer-events:none;
  background:linear-gradient(transparent,rgba(0,0,0,.30) 32%,rgba(0,0,0,.88) 76%)}
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
#out img{width:520px;filter:brightness(0) invert(1)}
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
<div id=intro><div class=eq>Tradeable Academy</div><h1 id=ih></h1></div>
<div id=flash></div>
<div id=out><img src="@@LOGO@@" alt=""><div class=s>Tradeable Academy</div>
  <div class=a>@tradeableacademy</div>
  <div class=l>Contenido educativo · No es asesoría financiera</div></div>
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
  ih.innerHTML = t<1.15 ? 'Esto no<br>es un curso.' : 'Es un<br><em>ecosistema</em>.';
  const e1 = t<1.15 ? tr(t,.25,.8) : tr(t,1.20,1.55);
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

    INTRO, CIERRE, POR_ESCENA = 2.30, 2.60, 2.35
    orden = sorted(picos, key=lambda p: p[1])
    sig = {p[0]: (orden[k + 1][1] if k + 1 < len(orden) else dur_src)
           for k, p in enumerate(orden)}
    plan, r = [], INTRO
    for i, h in enumerate(hechas):
        nombre, idx = h['n'], h['i']
        v0 = porIdx[idx][2] + 0.16          # justo después de que acaba el flash
        tope = min(dur_src, sig[idx] - 0.25)
        if tope - v0 < 0.8:          # escena demasiado corta: se descarta
            continue
        # ⚠️ se toma el trozo INICIAL, no el central: el final de la ventana lo
        # ocupa la preparación de la escena siguiente
        v1 = min(tope, v0 + POR_ESCENA)
        g, p = ROTULOS.get(nombre, (nombre, ''))
        plan.append({'r0': round(r, 3), 'r1': round(r + POR_ESCENA, 3),
                     'v0': round(v0, 3), 'v1': round(v1, 3),
                     'g': g, 'p': p, 'n': '%02d' % (i + 1)})
        r += POR_ESCENA
    total = round(r + CIERRE, 2)
    print('reel de %.1f s con %d escenas' % (total, len(plan)))

    doc = PAGINA
    for marca, valor in (('@@FUENTES@@', fuentes_css()), ('@@W@@', str(W)),
                         ('@@H@@', str(H)), ('@@GRAF@@', GRAFITO),
                         ('@@ORO@@', ORO), ('@@SRC@@', os.path.basename(CRUDO)),
                         ('@@LOGO@@', 'logo_tour.png'),
                         ('@@PLAN@@', json.dumps(plan)),
                         ('@@DUR@@', '%.2f' % total),
                         ('@@I0@@', '%.2f' % (INTRO - 0.30)),
                         ('@@I1@@', '%.2f' % INTRO),
                         ('@@O0@@', '%.2f' % r)):
        doc = doc.replace(marca, valor)

    shutil.copy(os.path.join(RAIZ, 'scalpel', 'static', 'logo_t.png'),
                os.path.join(SALIDA, 'logo_tour.png'))
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
