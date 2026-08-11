# -*- coding: utf-8 -*-
"""Monta un reel de verdad a partir de la grabación del sitio.

Una grabación de pantalla cruda NO es un reel. Esto la monta: entrada con
efecto, cortes, cámara lenta en el momento bueno, zoom, rótulos que entran y
salen, y cierre de marca.

CÓMO ESTÁ HECHO — el montaje entero es UNA PÁGINA HTML: un `<video>` con la
grabación y encima el rotulado en DOM. Así el zoom es un `transform`, la
transición es un `clip-path` (el mismo barrido del título de la landing) y los
textos son CSS. Después se fotografía fotograma a fotograma.

  · El tiempo del vídeo NO avanza solo: para cada fotograma se calcula qué
    segundo de la grabación toca (`fuenteEn`) y se hace `seek`. Por eso se
    puede ir a cámara lenta en las paredes y normal en el resto — y por eso el
    render es repetible.
  · 🔑 Para saber DÓNDE empieza lo bueno, la grabación se marca a propósito:
    justo antes de pulsar el cubo la página pega un fogonazo blanco de 2
    fotogramas. Luego se busca el fotograma más brillante y ese es el cero.
    Sin marca habría que recortar a ojo y cada regrabación saldría distinta.

    python3 tools/edita_reel.py              # graba y monta
    python3 tools/edita_reel.py --solo-montar  # reusa la grabación anterior
"""
from __future__ import print_function

import base64
import glob
import io
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
# 🔴 WebM, no MP4: el Chromium sin cabeza NO trae H.264 (los codecs
# propietarios se dejan fuera de las compilaciones de Chromium), asi que
# el <video> del montaje daba DEMUXER_ERROR_NO_SUPPORTED_STREAMS. Se deja
# tal cual sale de Playwright —VP8— y no se re-codifica: el escalado a
# 1080x1920 lo hace el propio montaje por CSS.
CRUDO = os.path.join(SALIDA, '_crudo-camara.webm')
PUERTO = 5093
CL = 'Zx9!wQ4mNp2r'
ANCHO, ALTO = 900, 1600          # se graba ya en vertical
W, H = 1080, 1920
FPS = 30
DUR = 11.6
AZUL = '#004feb'
ORO = '#c9a227'
GRAFITO = '#0b0d12'


# ── 1 · grabar ────────────────────────────────────────────────────────────
def graba():
    tmp = tempfile.mkdtemp()
    os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tmp, 'r.db')
    os.environ.setdefault('SECRET_KEY', 'edita-reel')
    sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
    import app as A
    with A.app.app_context():
        A.db.create_all()
        u = A.User.query.filter_by(username='camara').first()
        if u is None:
            u = A.User(username='camara', email='k@demo.invalid',
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
            break
        except Exception:
            pass
    URL = 'http://127.0.0.1:%d' % PUERTO
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')
           or [None])[0]
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'],
                              **({'executable_path': exe} if exe else {}))
        # el login va en un contexto SIN grabar: así el vídeo empieza en la app
        prev = b.new_context(viewport={'width': ANCHO, 'height': ALTO})
        pp = prev.new_page()
        pp.route('**/*', lambda r: r.continue_()
                 if '127.0.0.1' in r.request.url else r.abort())
        pp.goto(URL + '/login', wait_until='domcontentloaded')
        pp.fill('input[name=identifier]', 'camara')
        pp.fill('input[name=password]', CL)
        pp.click('button[type=submit]')
        pp.wait_for_timeout(800)
        pp.evaluate("localStorage.setItem('scalpel_lang','es')")
        sesion = prev.storage_state()
        prev.close()

        ctx = b.new_context(viewport={'width': ANCHO, 'height': ALTO},
                            storage_state=sesion, record_video_dir=tmp,
                            record_video_size={'width': ANCHO, 'height': ALTO})
        pg = ctx.new_page()
        pg.route('**/*', lambda r: r.continue_()
                 if '127.0.0.1' in r.request.url else r.abort())
        pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                                 'url': URL + '/'}])
        pg.goto(URL + '/app', wait_until='domcontentloaded')
        pg.wait_for_timeout(2600)
        # ── la marca: fogonazo blanco de ~2 fotogramas ──
        pg.evaluate("""() => {
          const d = document.createElement('div');
          d.id = '_marca';
          d.style.cssText = 'position:fixed;inset:0;background:#f0f;z-index:2147483647';
          document.body.appendChild(d);
        }""")
        pg.wait_for_timeout(80)
        pg.evaluate("document.getElementById('_marca').remove()")
        pg.evaluate("document.getElementById('nx-cube').click()")
        pg.wait_for_timeout(4200)              # paredes + constelación
        pg.evaluate("document.querySelectorAll('.nx-nd')[0].click()")
        pg.wait_for_timeout(2000)
        ctx.close()
        b.close()

    webm = sorted(glob.glob(os.path.join(tmp, '*.webm')))
    if not webm:
        sys.exit('Playwright no dejó vídeo')
    os.makedirs(SALIDA, exist_ok=True)
    shutil.copy(webm[0], CRUDO)
    shutil.rmtree(tmp, ignore_errors=True)
    print('grabación:', CRUDO)


# ── 2 · encontrar el fogonazo ─────────────────────────────────────────────
def cero():
    """Segundo del fogonazo MAGENTA = el instante del clic.

    Se busca por CROMA, no por brillo: el magenta dispara VAVG muy alto y no
    hay nada magenta en la interfaz. Con un fogonazo blanco no funcionaba —
    la app tiene tema claro y su propio fondo competia en brillo.
    """
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    r = subprocess.run(
        [ff, '-i', CRUDO, '-vf',
         'signalstats,metadata=print:key=lavfi.signalstats.VAVG',
         '-f', 'null', '-'], capture_output=True, text=True)
    t, mejor, mejor_t = None, -1, 0
    for ln in r.stderr.splitlines():
        m = re.search(r'pts_time:([0-9.]+)', ln)
        if m:
            t = float(m.group(1))
        m = re.search(r'VAVG=([0-9.]+)', ln)
        if m and t is not None and float(m.group(1)) > mejor:
            mejor, mejor_t = float(m.group(1)), t
    print('marca en %.2f s (croma %.0f)' % (mejor_t, mejor))
    if mejor < 150:
        sys.exit('no se encontró el fogonazo — ¿se grabó con la marca puesta?')
    return mejor_t + 0.10


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


# ── 3 · el montaje ────────────────────────────────────────────────────────
PAGINA = """<!doctype html><meta charset=utf-8><style>@@FUENTES@@
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:@@W@@px;height:@@H@@px;background:@@GRAF@@;overflow:hidden;
  font-family:Inter,sans-serif;color:#fff}
#capa{position:absolute;inset:0;overflow:hidden}
video{position:absolute;left:50%;top:50%;width:@@W@@px;height:@@H@@px;
  transform-origin:center center;translate:-50% -50%}
#rej{position:absolute;inset:0;pointer-events:none;
  background:
    linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px) 0 0/100% 64px,
    linear-gradient(90deg,rgba(255,255,255,.05) 1px,transparent 1px) 0 0/64px 100%}
#vig{position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 86% 70% at 50% 46%,transparent 52%,rgba(0,0,0,.34))}
#intro{position:absolute;inset:0;background:@@GRAF@@;display:flex;
  flex-direction:column;justify-content:center;padding:0 92px}
#intro .eq{font:700 27px 'JetBrains Mono',monospace;letter-spacing:.4em;
  color:@@ORO@@;text-transform:uppercase;margin-bottom:34px}
#intro h1{font:900 108px/0.98 Inter,sans-serif;letter-spacing:-.035em}
#intro h1 em{font-style:normal;color:@@ORO@@}
#scrim{position:absolute;left:0;right:0;bottom:0;height:54%;pointer-events:none;
  background:linear-gradient(transparent,rgba(0,0,0,.30) 34%,rgba(0,0,0,.86) 78%)}
#rot{position:absolute;left:76px;right:76px;bottom:300px}
#rot .g{font:900 76px/1.02 Inter,sans-serif;letter-spacing:-.03em;
  text-shadow:0 8px 40px rgba(0,0,0,.9)}
#rot .p{margin-top:20px;font:500 33px/1.35 Inter,sans-serif;
  color:rgba(255,255,255,.78);text-shadow:0 4px 24px rgba(0,0,0,.9)}
#out{position:absolute;inset:0;background:@@GRAF@@;display:flex;
  flex-direction:column;align-items:center;justify-content:center;gap:26px}
#out .m{font:900 82px Inter,sans-serif;letter-spacing:-.03em}
#out .s{font:700 27px 'JetBrains Mono',monospace;letter-spacing:.34em;
  color:@@ORO@@;text-transform:uppercase}
#out .a{margin-top:16px;font:600 34px Inter,sans-serif;color:rgba(255,255,255,.62)}
#out .l{position:absolute;bottom:150px;font:400 23px Inter,sans-serif;
  color:rgba(255,255,255,.34)}
#bar{position:absolute;left:0;bottom:0;height:7px;background:@@ORO@@}
</style><body>
<div id=capa><video id=v src="@@SRC@@" muted preload=auto></video>
  <div id=rej></div><div id=vig></div></div>
<div id=scrim></div>
<div id=rot></div>
<div id=intro><div class=eq>Tradeable Academy</div>
  <h1 id=ih></h1></div>
<div id=out><div class=s>Tradeable Academy</div>
  <div class=m>Abriendo pronto</div>
  <div class=a>@tradeableacademy</div>
  <div class=l>Contenido educativo · No es asesoría financiera</div></div>
<div id=bar></div>
<script>
const V=document.getElementById('v'), S0=@@S0@@, DUR=@@DUR@@;
const suav = t => t<0?0:t>1?1:t*t*(3-2*t);
const tr = (t,a,b) => suav((t-a)/(b-a));

/* De segundo del REEL a segundo de la GRABACIÓN. Aquí es donde se decide la
   cámara lenta: el tramo de las paredes ocupa 3,8 s de reel para 2,1 s de
   grabación (0,55x), y la constelación 2,7 s para 1,9 s (0,70x). */
const TRAMOS=[[2.00,3.50,-1.35,0.00],
              [3.50,6.20, 0.00,2.10],
              [6.20,10.1, 2.10,4.20]];
function fuenteEn(t){
  if(t<TRAMOS[0][0]) return S0+TRAMOS[0][2];
  for(const [a,b,x,y] of TRAMOS)
    if(t<=b) return S0 + x + (y-x)*((t-a)/(b-a));
  return S0+4.00;
}

const ROTULOS=[
  [2.25,3.45,'Tradeable Academy','El ecosistema educativo para traders'],
  [4.20,6.60,'Cinco puertas.','Asistente · guía · teletransportador · soporte'],
  [6.90,9.90,'Una sala propia.','Con identidad, no un menú más']];

window.enCuadre = async function(t){
  // 1 · intro
  const fin = tr(t,1.85,2.15);
  const intro=document.getElementById('intro');
  intro.style.opacity = 1;
  intro.style.clipPath = 'inset(0 0 '+(fin*100)+'% 0)';
  const ih=document.getElementById('ih');
  ih.innerHTML = t<1.05 ? 'No es una<br>herramienta.' : 'Es un<br><em>ecosistema</em>.';
  const e1 = t<1.05 ? tr(t,.25,.75) : tr(t,1.10,1.45);
  ih.style.opacity = e1;
  ih.style.transform = 'translateY('+(30*(1-e1))+'px)';
  document.querySelector('#intro .eq').style.opacity = tr(t,.1,.5);

  // 2 · el vídeo: se busca el fotograma que toca y se le da zoom lento
  const s = fuenteEn(t);
  if (Math.abs(V.currentTime - s) > 0.005){
    V.currentTime = s;
    await new Promise(r => { let ok=false;
      V.onseeked = () => { if(!ok){ok=true; r();} };
      setTimeout(() => { if(!ok){ok=true; r();} }, 350); });
  }
  const cerca = tr(t,3.30,4.60);          // 1 mientras se ve la Cámara
  const z = 1.00 + 0.10*suav((t-2.0)/8.0) + 0.52*cerca;
  V.style.scale = z;
  V.style.filter = 'brightness('+(1+0.42*cerca)+') contrast('+(1+0.10*cerca)
                 + ') saturate('+(1+0.18*cerca)+')';

  // 3 · rótulos
  const rot=document.getElementById('rot');
  let html='', op=0;
  for(const [a,b,g,p] of ROTULOS){
    const v = tr(t,a,a+.4)*(1-tr(t,b,b+.35));
    if(v>op){ op=v; html='<div class=g>'+g+'</div><div class=p>'+p+'</div>'; }
  }
  rot.innerHTML=html; rot.style.opacity=op;
  document.getElementById('scrim').style.opacity=op;
  rot.style.transform='translateY('+(26*(1-op))+'px)';

  // 4 · cierre
  const o=tr(t,10.05,10.45);
  document.getElementById('out').style.opacity=o;
  document.getElementById('out').style.clipPath='inset('+((1-o)*100)+'% 0 0 0)';

  // 5 · barra de progreso (retiene: se ve cuánto queda)
  document.getElementById('bar').style.width=(100*t/DUR)+'%';
};
</script></body>"""


def monta():
    s0 = cero()
    import imageio_ffmpeg
    from playwright.sync_api import sync_playwright
    doc = PAGINA
    for marca, valor in (('@@FUENTES@@', fuentes_css()), ('@@W@@', str(W)),
                         ('@@H@@', str(H)), ('@@GRAF@@', GRAFITO),
                         ('@@ORO@@', ORO), ('@@SRC@@', os.path.basename(CRUDO)),
                         ('@@S0@@', '%.3f' % s0), ('@@DUR@@', '%.2f' % DUR)):
        doc = doc.replace(marca, valor)
    ruta = os.path.join(SALIDA, '_montaje.html')
    io.open(ruta, 'w', encoding='utf-8').write(doc)
    carpeta = tempfile.mkdtemp()
    n = int(DUR * FPS)
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')
           or [None])[0]
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required',
                                    '--allow-file-access-from-files'],
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
    dest = os.path.join(SALIDA, 'reel-camara-montado.mp4')
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
