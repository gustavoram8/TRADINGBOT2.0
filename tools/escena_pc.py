# -*- coding: utf-8 -*-
"""La botarga, de espaldas, sentada frente al PC — la escena del reel 2.

El dueño la describió así: *"en primer plano se viese a la botarga de welcome
original, sentada de espaldas frente a una computadora, haciendo un trade, ese
trade lo erra… y se pone molesta. Luego abre una pestaña, escribe Tradeable
Academy, googlea y le sale el analizador"*.

🔑 CÓMO SE HACE SIN REDIBUJAR AL PERSONAJE: se usan las piezas que corta
   `tools/botarga_rig.py` (cuerpo sin cara + brazos + piernas) y se MUEVEN.
   Girar un brazo funciona porque es un tubo negro de grosor uniforme con el
   guante aparte — no hay hombro ni codo que se rompa al rotar.
   El escritorio, la silla, el monitor, el teclado y el ratón se dibujan
   procedimentalmente: son OBJETOS, no criaturas. Ahí sí se puede dibujar.

⚠️ Orden de profundidad, que es lo que hace que la escena se lea: el monitor
   está al fondo, el escritorio delante de él, y la botarga DELANTE de todo
   (es la que está más cerca de la cámara). Los brazos salen de sus costados y
   van HACIA ARRIBA en el encuadre, que en esta perspectiva significa "hacia
   adelante", sobre el escritorio.

    python3 tools/escena_pc.py            # una imagen fija para revisar
"""
from __future__ import print_function

import glob
import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIG = os.path.join(RAIZ, 'out', 'rig')
SALIDA = os.path.join(RAIZ, 'out', 'reels')
W, H = 1080, 1920

ORO = '#c9a227'


def url(n):
    return 'file://' + os.path.join(RIG, n + '.png')


PAGINA = u"""<!doctype html><meta charset=utf-8>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel=stylesheet>
<style>
 *{margin:0;padding:0;box-sizing:border-box}
 html,body{width:@@W@@px;height:@@H@@px;overflow:hidden;background:#07080b}
 #esc{position:relative;width:@@W@@px;height:@@H@@px;font-family:Inter,sans-serif}

 /* ── el cuarto: una pared oscura con una luz fría detrás del monitor ── */
 #pared{position:absolute;inset:0;
   background:radial-gradient(90% 55% at 50% 34%,#1b2030 0%,#0e1119 46%,#07080b 100%)}
 #brillo{position:absolute;left:50%;top:250px;width:1180px;height:900px;
   transform:translateX(-50%);pointer-events:none;
   background:radial-gradient(closest-side,rgba(90,140,220,.20),transparent 72%)}

 /* ── el monitor, al fondo ── */
 #mon{position:absolute;left:50%;top:180px;width:900px;height:620px;
   transform:translateX(-50%);border-radius:18px;background:#0c0e13;
   border:14px solid #1c2029;
   box-shadow:0 40px 90px rgba(0,0,0,.75), 0 0 0 2px rgba(255,255,255,.05)}
 #pant{position:absolute;inset:0;overflow:hidden;border-radius:6px;background:#0a0c11}
 #pie{position:absolute;left:50%;top:800px;width:120px;height:80px;
   transform:translateX(-50%);background:linear-gradient(#1c2029,#12151b)}
 #base{position:absolute;left:50%;top:872px;width:360px;height:22px;
   transform:translateX(-50%);border-radius:11px;
   background:linear-gradient(#222733,#141821)}

 /* ── el escritorio: una tabla en perspectiva ── */
 #mesa{position:absolute;left:-140px;right:-140px;top:905px;height:340px;
   background:linear-gradient(#232833 0%,#1a1e27 42%,#141821 100%);
   box-shadow:0 -2px 0 rgba(255,255,255,.07) inset, 0 26px 60px rgba(0,0,0,.6);
   clip-path:polygon(11% 0,89% 0,100% 100%,0 100%)}
 #teclado{position:absolute;left:50%;top:975px;width:520px;height:140px;
   transform:translateX(-50%) perspective(700px) rotateX(52deg);
   border-radius:12px;background:linear-gradient(#2b3140,#1d222c);
   box-shadow:0 14px 26px rgba(0,0,0,.55)}
 #teclas{position:absolute;inset:13px 14px;border-radius:6px;
   background:
    repeating-linear-gradient(90deg,#3a4152 0 30px,transparent 30px 36px),
    repeating-linear-gradient(0deg,#3a4152 0 18px,transparent 18px 24px)}
 #raton{position:absolute;left:812px;top:990px;width:86px;height:122px;
   border-radius:44px 44px 38px 38px;
   background:linear-gradient(#2f3646,#20252f);
   box-shadow:0 12px 22px rgba(0,0,0,.55)}

 /* ── la botarga, delante de todo ── */
 .pz{position:absolute;transform-origin:var(--ox,50%) var(--oy,50%)}
 #cuerpo{transform:rotate(-4deg);left:50%;top:1035px;width:940px;margin-left:-470px;
   filter:drop-shadow(0 -12px 40px rgba(0,0,0,.6))}
 #bi{left:196px;top:945px;width:196px}
 #bd{left:700px;top:930px;width:250px}
 img{display:block;width:100%}
 #silla{position:absolute;left:50%;top:1520px;width:900px;height:400px;
   transform:translateX(-50%);border-radius:70px 70px 0 0;
   background:linear-gradient(#191d26,#0d1015);
   box-shadow:0 0 0 3px rgba(255,255,255,.045) inset}
 #vin{position:absolute;inset:0;pointer-events:none;
   background:radial-gradient(120% 78% at 50% 40%,transparent 42%,rgba(0,0,0,.66))}
</style>
<div id=esc>
  <div id=pared></div><div id=brillo></div>
  <div id=mon><div id=pant><canvas id=cv width=872 height=612></canvas></div></div>
  <div id=pie></div><div id=base></div>
  <div id=mesa></div>
  <div id=teclado><div id=teclas></div></div>
  <div id=raton></div>
  <div id=silla></div>
  <img id=bi class=pz src="@@BI@@">
  <img id=bd class=pz src="@@BD@@">
  <img id=cuerpo class=pz src="@@CUERPO@@">
  <div id=vin></div>
</div>
<script>
// de espaldas los brazos van al revés: el que en el dibujo cae a la izquierda
// es el que aquí queda a la derecha
document.getElementById('bi').style.transform='scaleX(-1) rotate(-52deg)';
document.getElementById('bd').style.transform='scaleX(-1) rotate(46deg)';
const cx=document.getElementById('cv').getContext('2d');
cx.fillStyle='#0a0c11'; cx.fillRect(0,0,872,612);
cx.fillStyle='#39404f'; cx.font="700 26px 'JetBrains Mono',monospace";
cx.fillText('[ aquí va el gráfico ]', 250, 300);
</script>"""


def main():
    from playwright.sync_api import sync_playwright
    falta = [n for n in ('cuerpo_espalda', 'brazo_izq', 'brazo_der')
             if not os.path.exists(os.path.join(RIG, n + '.png'))]
    if falta:
        sys.exit('faltan piezas %s — corre antes tools/botarga_rig.py' % falta)
    doc = PAGINA
    for k, v in [('@@W@@', str(W)), ('@@H@@', str(H)),
                 ('@@CUERPO@@', url('cuerpo_espalda')),
                 ('@@BI@@', url('brazo_izq')), ('@@BD@@', url('brazo_der'))]:
        doc = doc.replace(k, v)
    ruta = os.path.join(SALIDA, '_escena_pc.html')
    with io.open(ruta, 'w', encoding='utf-8') as f:
        f.write(doc)
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox', '--allow-file-access-from-files',
                                    '--hide-scrollbars'],
                              **({'executable_path': exe} if exe else {}))
        pg = b.new_page(viewport={'width': W, 'height': H})
        errores = []
        pg.on('pageerror', lambda e: errores.append(str(e)))
        pg.goto('file://' + ruta, wait_until='load')
        pg.wait_for_timeout(1400)
        dest = os.path.join(SALIDA, '_escena_pc.png')
        pg.screenshot(path=dest)
        b.close()
    if errores:
        print('🔴 errores JS:', errores[:3])
    print('escena:', dest)


if __name__ == '__main__':
    main()
