# -*- coding: utf-8 -*-
"""La botarga EN SU PC, animada — los planos de personaje del reel 2.

Historia del dueño: la botarga hace un trade, lo pierde y se molesta; después
busca Tradeable Academy y aparece el analizador.

🔴 POR QUÉ DE FRENTE Y NO DE ESPALDAS. El primer intento fue el plano que él
   describió —la botarga sentada de espaldas frente al monitor— y NO SE LEE.
   Probados tres encuadres. La causa es del propio personaje: es una flecha
   plana cuyo carácter vive ENTERO en la cara; sin cara queda una figura
   geométrica, y ni espejada ni rotada parece una espalda. Se resuelve con
   MONTAJE en vez de con cámara: la botarga siempre de frente (con su cara) y
   la pantalla siempre a plano completo, alternando. De paso, así la grabación
   real del sitio entra sin costura y se lee en un teléfono.
   El despiece de espaldas se conserva en botarga_rig.py por si algún día el
   dueño encarga las poses dibujadas.

🔑 QUÉ SE ANIMA. Las piezas de `tools/botarga_rig.py` giran sobre su
   articulación REAL (calculada como el centro de los píxeles que tocan el
   cuerpo, no puesta a ojo). El torso respira y se inclina; los brazos teclean
   y hacen clic. Nada se redibuja.

🔑 LA RABIA NO SE ANIMA: SE CAMBIA DE POSE. `logo4_dark` ya es la botarga
   frustrada, dibujada y aprobada. Cambiar de dibujo + sacudida es más honesto
   —y se ve mucho mejor— que intentar deformar la cara alegre.

    python3 tools/escena_pc.py --fija     # una imagen para revisar
    python3 tools/escena_pc.py            # el clip de prueba (7 s)
"""
from __future__ import print_function

import glob
import io
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIG = os.path.join(RAIZ, 'out', 'rig')
EST = os.path.join(RAIZ, 'scalpel', 'static')
SALIDA = os.path.join(RAIZ, 'out', 'reels')
W, H, FPS = 1080, 1920, 30

T_OPERA = (0.00, 4.20)     # teclea y hace clic
T_GOLPE = (4.20, 7.40)     # pierde: cambia de pose y se sacude
TOTAL = 7.40


def url(p):
    return 'file://' + p


PAGINA = u"""<!doctype html><meta charset=utf-8>
<style>
 *{margin:0;padding:0;box-sizing:border-box}
 html,body{width:@@W@@px;height:@@H@@px;overflow:hidden;background:#07080b}
 #e{position:relative;width:@@W@@px;height:@@H@@px}
 #pared{position:absolute;inset:0;
   background:radial-gradient(84% 48% at 50% 74%,#1b2030,#0d1018 54%,#07080b)}
 /* el resplandor del monitor: es la única fuente de luz del cuarto, así que
    también es lo que tiñe la escena cuando el trade se pierde */
 #glow{position:absolute;left:50%;top:1080px;width:1700px;height:1000px;
   margin-left:-850px;pointer-events:none;
   background:radial-gradient(closest-side,rgba(96,158,242,.42),transparent 72%)}
 #rojo{position:absolute;inset:0;pointer-events:none;opacity:0;
   background:radial-gradient(105% 60% at 50% 78%,rgba(229,72,77,.60),
              rgba(150,30,36,.30) 58%,transparent 82%)}
 /* el monitor visto POR DETRÁS: no hace falta la pantalla, el corte siguiente
    la enseña a plano completo */
 #mesa{position:absolute;left:-160px;right:-160px;top:1400px;height:560px;
   background:linear-gradient(#2a3140 0%,#1b2029 38%,#0f1219 100%);
   box-shadow:0 -3px 0 rgba(140,180,240,.16) inset, 0 -30px 70px rgba(0,0,0,.5)}
 #tec{position:absolute;left:50%;top:1490px;width:700px;height:190px;
   margin-left:-350px;border-radius:16px;
   background:linear-gradient(#333b4b,#20262f);
   box-shadow:0 20px 40px rgba(0,0,0,.6), 0 -2px 0 rgba(255,255,255,.07) inset}
 #tec i{position:absolute;inset:18px;border-radius:9px;display:block;
   background:repeating-linear-gradient(90deg,#414a5e 0 40px,transparent 40px 49px),
              repeating-linear-gradient(0deg,#414a5e 0 26px,transparent 26px 35px)}
 /* ── la botarga ── */
 /* el contenedor tiene las proporciones del PNG de origen; dentro, cada
    pieza va en su sitio exacto (ver @@PIEZAS@@, calculado de rig.json) */
 #bot{position:absolute;left:50%;top:@@BTOP@@px;width:@@BW@@px;
   margin-left:-@@BW2@@px;height:@@BH@@px;transform-origin:50% 100%}
 #bot img{position:absolute;display:block}
@@PIEZAS@@
 #enojo{position:absolute;left:50%;top:640px;width:1010px;margin-left:-505px;
   opacity:0}
 #enojo img{width:100%;display:block}
 #vin{position:absolute;inset:0;pointer-events:none;
   background:radial-gradient(122% 74% at 50% 52%,transparent 44%,rgba(0,0,0,.70))}
</style>
<div id=e>
 <div id=pared></div><div id=glow></div>
 <div id=bot>
   <img id=bi src="@@BI@@"><img id=bd src="@@BD@@">
   <img id=torso src="@@TORSO@@">
 </div>
 <div id=enojo><img src="@@ENOJO@@"></div>
 <div id=mesa></div><div id=tec><i></i></div>
 <div id=rojo></div>
 <div id=vin></div>
</div>
<script>
const E=id=>document.getElementById(id);
const cl=(v,a,b)=>Math.max(a,Math.min(b,v));
const tr=(t,a,b)=>{const x=cl((t-a)/(b-a),0,1);return x*x*(3-2*x);};
const G0=@@G0@@;

function pinta(t){
  const enojado = t >= G0;

  // ── mientras opera ──
  // el torso respira; el brazo izquierdo teclea (giros cortos y desiguales,
  // que es lo que distingue teclear de saludar) y el derecho hace clic
  const resp = Math.sin(t*2.1)*1.1;
  const tec  = Math.sin(t*13.0)*2.2 + Math.sin(t*7.3)*1.4;
  const clic = (t>2.55 && t<2.78) ? 6 : 0;
  E('bot').style.opacity = enojado ? 0 : 1;
  if (!enojado){
    E('bot').style.transform = 'rotate('+(resp*0.35)+'deg) translateY('+(resp*3)+'px)';
    E('bi').style.transform  = 'rotate('+(-6+tec)+'deg)';
    E('bd').style.transform  = 'rotate('+(4+clic+Math.sin(t*2.7)*1.6)+'deg)';
  }

  // ── el golpe ──
  // cambio de dibujo + sacudida que se amortigua, y el cuarto se pone rojo
  const en=E('enojo');
  if (enojado){
    const u = t - G0;
    const amort = Math.exp(-u*2.6);
    const sac = Math.sin(u*26)*13*amort;
    const gi  = Math.sin(u*23)*3.4*amort;
    en.style.opacity = tr(t,G0,G0+0.10);
    en.style.transform = 'translateX('+sac+'px) rotate('+gi+'deg) scale('+(1+0.05*amort)+')';
    E('rojo').style.opacity = 0.85*Math.exp(-u*1.5) + 0.18;
  } else { en.style.opacity=0; E('rojo').style.opacity=0; }
}
window.pinta = pinta;
</script>"""


def main():
    from playwright.sync_api import sync_playwright
    falta = [n for n in ('torso_frente', 'brazo_izq', 'brazo_der')
             if not os.path.exists(os.path.join(RIG, n + '.png'))]
    if falta:
        sys.exit('faltan piezas %s — corre antes tools/botarga_rig.py' % falta)
    import json
    rig = json.load(io.open(os.path.join(RIG, 'rig.json'), encoding='utf-8'))
    ORIG_W, ORIG_H = 960, 850          # el PNG del que salió el despiece
    BW = 980                            # ancho del muñeco en el encuadre
    k = BW / float(ORIG_W)
    css = []
    for nom, ident in (('torso_frente', 'torso'), ('brazo_izq', 'bi'),
                       ('brazo_der', 'bd')):
        p = rig[nom]
        ox, oy = p['origen']
        pw, ph = p['tam']
        piv = p.get('pivote', [0.5, 0.5])
        css.append(' #%s{left:%.1fpx;top:%.1fpx;width:%.1fpx;'
                   'transform-origin:%.1f%% %.1f%%}'
                   % (ident, ox * k, oy * k, pw * k, piv[0] * 100, piv[1] * 100))
    doc = PAGINA
    for k2, v in [('@@PIEZAS@@', '\n'.join(css)),
                  ('@@BW@@', '%d' % BW), ('@@BW2@@', '%d' % (BW // 2)),
                  ('@@BH@@', '%d' % int(ORIG_H * k)), ('@@BTOP@@', '760'),
                  ('@@W@@', str(W)), ('@@H@@', str(H)),
                 ('@@G0@@', '%.2f' % T_GOLPE[0]),
                 ('@@TORSO@@', url(os.path.join(RIG, 'torso_frente.png'))),
                 ('@@BI@@', url(os.path.join(RIG, 'brazo_izq.png'))),
                 ('@@BD@@', url(os.path.join(RIG, 'brazo_der.png'))),
                  ('@@ENOJO@@', url(os.path.join(EST, 'logo4_dark.png')))]:
        doc = doc.replace(k2, v)
    ruta = os.path.join(SALIDA, '_escena_pc.html')
    with io.open(ruta, 'w', encoding='utf-8') as f:
        f.write(doc)

    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    fija = '--fija' in sys.argv
    carpeta = os.path.join(SALIDA, '_pcf')
    shutil.rmtree(carpeta, ignore_errors=True)
    os.makedirs(carpeta)
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox', '--allow-file-access-from-files',
                                    '--hide-scrollbars'],
                              **({'executable_path': exe} if exe else {}))
        pg = b.new_page(viewport={'width': W, 'height': H})
        errores = []
        pg.on('pageerror', lambda e: errores.append(str(e)))
        pg.goto('file://' + ruta, wait_until='load')
        pg.wait_for_timeout(1200)
        if fija:
            for t in (1.6, 4.45, 5.6):
                pg.evaluate('t => window.pinta(t)', t)
                pg.screenshot(path=os.path.join(SALIDA, '_pc_%.2f.png' % t))
            b.close()
            if errores:
                print('🔴 errores JS:', errores[:3])
            print('fijas en', SALIDA)
            return
        n = int(TOTAL * FPS)
        for i in range(n):
            pg.evaluate('t => window.pinta(t)', i / float(FPS))
            pg.screenshot(path=os.path.join(carpeta, '%04d.png' % i))
            if i % 60 == 0:
                print('  fotograma %d/%d' % (i, n))
        b.close()
    if errores:
        print('🔴 errores JS:', errores[:3])
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    dest = os.path.join(SALIDA, 'prueba-botarga-pc.mp4')
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(FPS),
                    '-i', os.path.join(carpeta, '%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18',
                    '-movflags', '+faststart', dest], check=True)
    shutil.rmtree(carpeta, ignore_errors=True)
    print('listo:', dest, '· %.1f MB' % (os.path.getsize(dest) / 1e6))


if __name__ == '__main__':
    main()
