# -*- coding: utf-8 -*-
"""Reel animado 1080x1920 — el concepto de Order Block, dibujado solo.

PRUEBA DE QUE SE PUEDE: el video se genera por codigo. Cada fotograma se pinta
en Chromium sin cabeza (el mismo motor que dibuja los camos y las placas), se
captura, y ffmpeg los cose en un .mp4 que Instagram acepta tal cual.

  · Nada de animaciones CSS por tiempo: el estado de CADA fotograma se calcula
    a partir de t (0..1). Asi el render es DETERMINISTA y repetible — con
    animaciones por reloj, la captura llega tarde o pronto y el video tiembla.
  · Las velas salen de precios OHLC reales del ejemplo, no dibujadas a ojo: el
    order block es la ULTIMA vela bajista antes del desplazamiento, y tiene que
    seguir siendolo en el video.
  · Sin audio: eso se le pone en Instagram, que es donde vive el audio de moda.

    python3 tools/reel_order_block.py                 # ~8 s de video
    python3 tools/reel_order_block.py --rapido        # 12 fps, para revisar
"""
from __future__ import print_function

import base64
import io
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTES_DIR = os.path.join(RAIZ, 'tools', '.fuentes')
SALIDA = os.path.join(RAIZ, 'out', 'reels')

AZUL = '#004feb'
ORO = '#c9a227'
GRAFITO = '#0d0f14'

W, H = 1080, 1920
FPS = 30
DUR = 8.0                      # segundos

# OHLC del ejemplo (el mismo del post 04): la vela 2 es la ultima bajista
# antes del desplazamiento de la vela 3.
VELAS = [(50, 52, 53, 49), (52, 51, 53, 50), (51, 48, 52, 47),
         (48, 58, 60, 47), (58, 66, 68, 57), (66, 64, 69, 62),
         (64, 71, 73, 63)]
OB = 2                          # indice del order block
DESPL = 3                       # la vela del desplazamiento


def fuentes_css():
    """Las fuentes van EMBEBIDAS: Chromium sin cabeza no siempre alcanza la
    red, y una fuente que no carga cambia el video entero."""
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


PAGINA = """<!doctype html><meta charset=utf-8><style>%(fuentes)s
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:%(W)dpx;height:%(H)dpx;background:%(graf)s;overflow:hidden;
  font-family:Inter,sans-serif;color:#eef1f7}
#esc{position:absolute;inset:0;
  background:
    radial-gradient(ellipse 70%% 45%% at 50%% 38%%,rgba(0,79,235,.18),transparent 70%%),
    linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px) 0 0/100%% 60px,
    linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px) 0 0/60px 100%%,
    %(graf)s}
#etq{position:absolute;left:70px;top:150px;font:700 26px 'JetBrains Mono',monospace;
  letter-spacing:.34em;color:%(oro)s;text-transform:uppercase}
#tit{position:absolute;left:70px;top:200px;font:900 104px Inter,sans-serif;
  letter-spacing:-.03em;line-height:.95}
#graf{position:absolute;left:70px;right:70px;top:470px;height:760px}
#pie{position:absolute;left:70px;right:70px;top:1290px}
.frase{font:700 46px/1.25 Inter,sans-serif;letter-spacing:-.02em}
.frase em{font-style:normal;color:%(oro)s}
.sub{margin-top:22px;font:400 31px/1.45 Inter,sans-serif;color:rgba(238,241,247,.62)}
#marca{position:absolute;left:0;right:0;bottom:96px;text-align:center;
  font:800 34px Inter,sans-serif;letter-spacing:.02em}
#marca span{display:block;margin-top:12px;font:400 24px 'JetBrains Mono',monospace;
  letter-spacing:.26em;color:rgba(238,241,247,.45);text-transform:uppercase}
</style><body>
<div id=esc></div><div id=etq>Concepto</div><div id=tit></div>
<svg id=graf viewBox="0 0 940 760" preserveAspectRatio="none"></svg>
<div id=pie></div><div id=marca></div>
<script>
const V=%(velas)s, OB=%(ob)d, DE=%(despl)d, ORO='%(oro)s', AZUL='%(azul)s';
const NS='http://www.w3.org/2000/svg';
const lo=44, hi=76, MX=940, MY=760, PAD=40;
const yy = p => MY-PAD - (p-lo)/(hi-lo)*(MY-2*PAD);
const xx = i => 70 + i*(MX-140)/(V.length-1);
const suav = t => t<0 ? 0 : t>1 ? 1 : t*t*(3-2*t);
const tramo = (t,a,b) => suav((t-a)/(b-a));

function el(n,at){const e=document.createElementNS(NS,n);
  for(const k in at) e.setAttribute(k,at[k]); return e;}

window.pintar = function(t){                 // t en segundos
  const g=document.getElementById('graf'); g.innerHTML='';
  // 1 · titulo
  const ap=tramo(t,.15,.8);
  const tit=document.getElementById('tit');
  tit.textContent='Order Block';
  tit.style.opacity=ap; tit.style.transform='translateY('+(26*(1-ap))+'px)';
  document.getElementById('etq').style.opacity=tramo(t,0,.5);

  // 2 · las velas se dibujan una a una
  V.forEach((v,i)=>{
    const [o,c,h,l]=v;
    const nace=tramo(t, .9+i*.14, 1.15+i*.14);
    if(nace<=0) return;
    const sube=c>=o, col=sube?'#3fb27f':'#e0455f';
    const cx=xx(i), an=64*nace;
    g.appendChild(el('line',{x1:cx,y1:yy(l),x2:cx,y2:yy(h),
      stroke:col,'stroke-width':4,opacity:nace}));
    const y1=yy(Math.max(o,c)), y2=yy(Math.min(o,c));
    g.appendChild(el('rect',{x:cx-an/2,y:y1,width:an,height:Math.max(3,y2-y1),
      fill:col,opacity:.92*nace,rx:3}));
  });

  // 3 · el error: cajas sobre CUALQUIER vela bajista, que parpadean y se van
  const err=tramo(t,2.5,2.9)*(1-tramo(t,3.5,3.9));
  if(err>0.01) V.forEach((v,i)=>{
    if(v[1]>=v[0]) return;
    g.appendChild(el('rect',{x:xx(i)-46,y:yy(Math.max(v[0],v[1]))-14,
      width:92,height:Math.abs(yy(v[0])-yy(v[1]))+28,fill:'none',
      stroke:'#e0455f','stroke-width':3,'stroke-dasharray':'10 8',
      opacity:.85*err,rx:6}));
  });

  // 4 · el desplazamiento: flecha y estela sobre la vela que rompe
  const dsp=tramo(t,4.0,4.6);
  if(dsp>0.01){
    const x=xx(DE);
    g.appendChild(el('rect',{x:x-52,y:yy(V[DE][1])-10,width:104,
      height:yy(V[DE][0])-yy(V[DE][1])+20,fill:AZUL,opacity:.22*dsp,rx:8}));
    const y0=yy(V[DE][0]), y1=yy(V[DE][1])-34;
    g.appendChild(el('path',{d:'M'+x+' '+y0+' L'+x+' '+(y0+(y1-y0)*dsp),
      stroke:AZUL,'stroke-width':7,'stroke-linecap':'round',opacity:.9}));
  }

  // 5 · la caja CORRECTA cae sobre el order block y se queda
  const ok=tramo(t,5.0,5.7);
  if(ok>0.01){
    const v=V[OB], x=xx(OB);
    const yA=yy(Math.max(v[0],v[1])), yB=yy(Math.min(v[0],v[1]));
    const cae=(1-ok)*-70;
    g.appendChild(el('rect',{x:x-58,y:yA-18+cae,width:116,height:(yB-yA)+36,
      fill:ORO,opacity:.16*ok,rx:8}));
    g.appendChild(el('rect',{x:x-58,y:yA-18+cae,width:116,height:(yB-yA)+36,
      fill:'none',stroke:ORO,'stroke-width':5,opacity:ok,rx:8}));
    const et=el('text',{x:x,y:yA-38+cae,fill:ORO,'text-anchor':'middle',
      'font-family':'JetBrains Mono','font-size':26,'font-weight':700,
      'letter-spacing':2,opacity:ok});
    et.textContent='OB'; g.appendChild(et);
  }

  // 6 · el pie va contando la historia
  const pie=document.getElementById('pie');
  const guion=[
    [1.0, 2.4, 'Siete velas.', 'Una sola es el order block.'],
    [2.6, 3.9, 'Casi todo el mundo<br>marca <em>cualquier vela roja</em>.',
               'Y el gráfico acaba lleno de cajas que no dicen nada.'],
    [4.1, 4.9, 'El precio se <em>desplaza</em>.', 'Rompe estructura y no deja volver.'],
    [5.1, 7.2, 'El válido es <em>la última bajista</em><br>antes de ese arranque.',
               'Una zona con una razón detrás.']];
  let html='', op=0;
  guion.forEach(([a,b,f,s])=>{
    const v=tramo(t,a,a+.35)*(1-tramo(t,b,b+.35));
    if(v>op){op=v; html='<div class=frase>'+f+'</div><div class=sub>'+s+'</div>';}
  });
  pie.innerHTML=html; pie.style.opacity=op;
  pie.style.transform='translateY('+(18*(1-op))+'px)';

  // 7 · cierre de marca
  const fin=tramo(t,7.0,7.5);
  const m=document.getElementById('marca');
  m.innerHTML='Tradeable Academy<span>Contenido educativo</span>';
  m.style.opacity=fin;
};
</script></body>"""


def main():
    rapido = '--rapido' in sys.argv
    fps = 12 if rapido else FPS
    os.makedirs(SALIDA, exist_ok=True)
    from playwright.sync_api import sync_playwright
    import glob
    import imageio_ffmpeg

    doc = PAGINA % {'fuentes': fuentes_css(), 'W': W, 'H': H, 'graf': GRAFITO,
                    'oro': ORO, 'azul': AZUL,
                    'velas': str([list(v) for v in VELAS]), 'ob': OB,
                    'despl': DESPL}
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False,
                                     encoding='utf-8') as fh:
        fh.write(doc)
        ruta = fh.name

    n = int(DUR * fps)
    carpeta = tempfile.mkdtemp()
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'],
                              **({'executable_path': exe} if exe else {}))
        pg = b.new_page(viewport={'width': W, 'height': H})
        pg.goto('file://' + ruta, wait_until='load')
        for i in range(n):
            pg.evaluate('pintar(%f)' % (i / float(fps)))
            pg.screenshot(path=os.path.join(carpeta, '%04d.png' % i))
            if i % 30 == 0:
                print('  fotograma %d/%d' % (i, n))
        b.close()

    dest = os.path.join(SALIDA, 'reel-order-block.mp4')
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(fps),
                    '-i', os.path.join(carpeta, '%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-profile:v', 'high', '-crf', '18',
                    '-movflags', '+faststart', dest], check=True)
    print('listo:', dest, '(%.1f s, %d fps)' % (DUR, fps))
    print('tamaño: %.1f MB' % (os.path.getsize(dest) / 1e6))


if __name__ == '__main__':
    main()
