# -*- coding: utf-8 -*-
"""Reel 3 — LOS QUIZZES. "¿Seguro que entendiste lo que estudiaste?"

Idea del dueño: enseñar que el quiz no es un test de juguete — metodología,
tema, nivel, y arriba del todo el hardcore con escenarios de gráfico.

🔑 TODO lo que sale es la pantalla REAL del quiz (`tools/capta_quiz.py`), y la
   pregunta, sus cuatro opciones, cuál es la correcta y la explicación salen de
   `leido.json`, o sea de lo que la app imprimió. Ni una palabra escrita a mano.

🔑 EL NÚMERO SE QUEDA CORTO A PROPÓSITO: 598 = 398 del QUESTION_BANK + 200 del
   DAILY_BANK, ambos contados desde `scalpel/quiz_answer_key.json`. Los 63
   escenarios hardcore van ADEMÁS, así que la cifra que se anuncia es menor que
   la real. Con un número en pantalla es mejor quedarse corto que pasarse.

⚠️ El quiz tiene CUATRO metodologías (ICT, Pattern Trading, Wyckoff, SMC), no
   siete: las siete son las del analizador. Confundirlas sería anunciar algo
   que el producto no da.

    python3 tools/reel_quiz.py
"""
from __future__ import print_function

import glob
import io
import json
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'out', 'reels')
QZ = os.path.join(SALIDA, '_qz')
W, H, FPS = 1080, 1920, 30

ORO = '#c9a227'
ROJO = '#e5484d'
VERDE = '#30a46c'
MARCA_VOL = 0.877

# 🔴 REESTRUCTURADO para TikTok tras la revisión del dueño: "no me llama la
#    atención ni me despierta nada… alguien ve 3 o 4 s y si no lo engancha
#    desliza". Lo que se fue: las rejillas de metodologías y de temas, que son
#    catálogo de funciones — nadie se queda por un catálogo.
#    Lo que manda ahora es SU observación: hay conceptos que crees saber y con
#    el tiempo descubres que los tenías mal. Eso es el gancho, y va en los
#    primeros 2,6 s.
#    Y la pregunta entra en el segundo 5,6 para que el espectador JUEGUE — que
#    es lo que retiene en TikTok, no que le enseñen pantallas.
T_H1 = (0.00, 2.60)      # "crees que lo sabes"
T_H2 = (2.60, 5.60)      # "…hasta que descubres que lo tenías mal"
T_PRE = (5.60, 13.60)    # la pregunta, con el reloj — que la conteste él
T_REV = (13.60, 19.00)   # la correcta y la explicación
T_NIV = (19.00, 23.20)   # de principiante a avanzado
T_HC = (23.20, 29.20)    # hardcore: además, en el gráfico
T_NUM = (29.20, 32.80)   # el número
T_CIERRE = (32.80, 36.80)
TOTAL = 36.80

TXT = {
    'k1': '',
    'h1': 'There\u2019s always a concept<br>you <em>think</em> you know.',
    'k2': '',
    'h2': 'Until you find out<br>you had it <em>wrong</em>.',
    'k_pre': 'Try this one',
    'h_pre': 'Can you answer it?',
    'k_rev': 'The answer',
    'k_niv': 'Beginner to Advanced',
    'h_niv': 'For every concept<br>you\u2019re not sure about.',
    'cap_niv': 'pick the level, not the guesswork',
    'k_hc': 'And then',
    'h_hc': 'Hardcore.',
    'cap_hc': 'not just what you know — how it looks on the chart',
    'k_num': '',
    'p_num': 'How many would you get wrong?',
    'lema': 'Process over impulse.',
    'legal': 'Educational content · Not financial advice',
}


def datos():
    with io.open(os.path.join(QZ, 'leido.json'), encoding='utf-8') as f:
        d = json.load(f)
    ops = d.get('opciones') or []
    # normaliza: la captura vieja guardaba cadenas, la nueva {txt, ok}
    ops = [o if isinstance(o, dict) else {'txt': o, 'ok': False} for o in ops]
    ok = d.get('correcta') or {}
    if not any(o['ok'] for o in ops) and ok.get('indice', -1) >= 0:
        ops[ok['indice']]['ok'] = True
    if not any(o['ok'] for o in ops):
        sys.exit('🔴 no sé cuál es la correcta — no se puede montar el reel '
                 'sin eso; vuelve a correr tools/capta_quiz.py')
    return {'q': d['pregunta'], 'ops': ops, 'exp': d['explicacion'],
            'tema': d.get('tema', ''), 'nivel': d.get('nivel', '')}


def logo_oscuro():
    """Logotipo para fondo oscuro conservando su "a" AZUL (ver reel 2)."""
    from PIL import Image
    import numpy as np
    dest = os.path.join(SALIDA, '_logo_oscuro.png')
    if os.path.exists(dest):
        return dest
    a = np.array(Image.open(os.path.join(
        RAIZ, 'scalpel', 'static', 'logo_t.png')).convert('RGBA')).astype(int)
    al = a[:, :, 3]
    azul = (al > 60) & (a[:, :, 2] > a[:, :, 0] + 40)
    out = a.copy()
    tinta = (al > 0) & (~azul)
    for c in range(3):
        out[:, :, c] = np.where(tinta, 255, out[:, :, c])
    Image.fromarray(out.astype('uint8')).save(dest)
    return dest


def recorta_hardcore():
    """Del pantallazo hardcore, solo el GRÁFICO y su leyenda.

    ⚠️ `hardcore.png` mide 1280×1684 (chart + pregunta + cuatro opciones muy
    largas): a lo ancho del lienzo no se lee ni el enunciado. Lo que vale del
    hardcore es que trae un ESCENARIO DE GRÁFICO, así que se recorta eso.
    """
    from PIL import Image
    src = os.path.join(QZ, 'hardcore.png')
    if not os.path.exists(src):
        return
    im = Image.open(src)
    im.crop((0, 0, im.size[0], min(640, im.size[1]))) \
      .save(os.path.join(QZ, 'hardcore_rec.png'))


PAGINA = u"""<!doctype html><meta charset=utf-8>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap" rel=stylesheet>
<style>
 *{margin:0;padding:0;box-sizing:border-box}
 html,body{width:@@W@@px;height:@@H@@px;overflow:hidden;background:#07080b}
 #e{position:relative;width:@@W@@px;height:@@H@@px;
   font-family:Inter,system-ui,sans-serif;color:#fff}
 #vin{position:absolute;inset:0;pointer-events:none;
   background:radial-gradient(120% 80% at 50% 44%,transparent 40%,rgba(0,0,0,.62))}
 #tit{position:absolute;left:96px;right:96px;top:190px;opacity:0}
 #tit .k{font:700 21px 'JetBrains Mono',monospace;letter-spacing:.16em;
   text-transform:uppercase;color:rgba(255,255,255,.52)}
 #tit .g{margin-top:14px;font:900 62px/1.07 Inter,sans-serif;letter-spacing:-.02em;
   text-shadow:0 8px 40px rgba(0,0,0,.95)}
 #tit .g em{font-style:normal;color:@@ORO@@}
 #shot{position:absolute;left:60px;right:60px;opacity:0}
 #shot img{width:100%;display:block;border-radius:14px;
   box-shadow:0 30px 70px rgba(0,0,0,.75), 0 0 0 1px rgba(255,255,255,.07)}
 #shot .cap{margin-top:24px;text-align:center;
   font:700 20px 'JetBrains Mono',monospace;letter-spacing:.14em;
   text-transform:uppercase;color:rgba(255,255,255,.55)}
 /* la pregunta, COMPUESTA: la captura del bloque no se lee a este tamaño */
 #q{position:absolute;left:74px;right:74px;top:560px;opacity:0;
   transition:none}
 #q .pills{display:flex;gap:10px;margin-bottom:20px}
 #q .pill{font:700 17px 'JetBrains Mono',monospace;letter-spacing:.12em;
   text-transform:uppercase;padding:7px 14px;border-radius:999px;
   background:rgba(255,255,255,.07);color:rgba(255,255,255,.66)}
 #q .pill.lv{background:rgba(201,162,39,.16);color:@@ORO@@}
 #q .txt{font:800 39px/1.28 Inter,sans-serif;color:#fff}
 #q ul{list-style:none;margin-top:26px;display:flex;flex-direction:column;gap:12px}
 #q li{font:500 27px/1.36 Inter,sans-serif;color:rgba(255,255,255,.86);
   padding:18px 20px;border-radius:12px;
   background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09)}
 #q li.ok{background:rgba(48,163,108,.16);border-color:@@VERDE@@;color:#fff}
 #q li.no{opacity:.30}
 #reloj{position:absolute;right:74px;top:400px;opacity:0;
   font:700 76px 'JetBrains Mono',monospace;color:#fff;
   font-variant-numeric:tabular-nums}
 #reloj.rojo{color:@@ROJO@@}
 #exp{position:absolute;left:74px;right:74px;opacity:0}
 #exp .k{font:700 19px 'JetBrains Mono',monospace;letter-spacing:.16em;
   text-transform:uppercase;color:@@VERDE@@}
 #exp .t{margin-top:16px;font:500 29px/1.44 Inter,sans-serif;
   color:rgba(255,255,255,.88)}
 #num{position:absolute;left:96px;right:96px;top:700px;opacity:0;text-align:center}
 #num .g{font:900 116px/1 Inter,sans-serif;color:@@ORO@@;letter-spacing:-.04em}
 #num .l{margin-top:12px;font:800 46px/1.2 Inter,sans-serif}
 #num .p{margin-top:26px;font:500 31px/1.4 Inter,sans-serif;
   color:rgba(255,255,255,.70)}
 #out{position:absolute;inset:0;opacity:0;display:flex;flex-direction:column;
   align-items:center;justify-content:center;background:#07080b}
 #out .lg{width:520px}
 #out .sl{margin-top:34px;font:800 40px Inter,sans-serif}
 #out .lgl{position:absolute;left:0;right:0;bottom:150px;text-align:center;
   font:500 22px Inter,sans-serif;color:rgba(255,255,255,.42)}
 #bar{position:absolute;left:0;bottom:0;height:5px;background:@@ORO@@;width:0}
</style>
<div id=e>
  <div id=shot><img id=shotimg><div class=cap></div></div>
  <div id=q><div class=pills></div><div class=txt></div><ul></ul></div>
  <div id=reloj></div>
  <div id=exp><div class=k></div><div class=t></div></div>
  <div id=num><div class=g></div><div class=l></div><div class=p></div></div>
  <div id=tit><div class=k></div><div class=g></div></div>
  <div id=out><img class=lg src="@@LOGO@@"><div class=sl>@@LEMA@@</div>
    <div class=lgl>@@LEGAL@@</div></div>
  <div id=vin></div><div id=bar></div>
</div>
<script>
const D=@@DATOS@@, T=@@TXT@@, P=@@PASOS@@, TOTAL=@@TOTAL@@;
const E=id=>document.getElementById(id);
const cl=(v,a,b)=>Math.max(a,Math.min(b,v));
const tr=(t,a,b)=>{const x=cl((t-a)/(b-a),0,1);return x*x*(3-2*x);};

let pintado=null;
function pinta(t){
  let p=null; for(const s of P) if(t>=s.t0 && t<s.t1) p=s;

  // rótulo
  const ti=E('tit');
  if(p && p.h){ ti.style.opacity=tr(t,p.t0+.10,p.t0+.65)*(1-tr(t,p.t1-.30,p.t1));
    ti.querySelector('.k').textContent=p.k||'';
    ti.querySelector('.g').innerHTML=p.h; } else ti.style.opacity=0;

  // captura
  const sh=E('shot');
  if(p && p.img){ sh.style.opacity=tr(t,p.t0,p.t0+.55)*(1-tr(t,p.t1-.35,p.t1));
    sh.style.top=p.top+'px';
    sh.style.transform='translateY('+(24*(1-tr(t,p.t0,p.t0+.7)))+'px)';
    if(E('shotimg').getAttribute('src')!==p.img) E('shotimg').setAttribute('src',p.img);
    sh.querySelector('.cap').textContent=p.cap||''; } else sh.style.opacity=0;

  // la pregunta: las opciones entran una a una, y en el veredicto la correcta
  // se enciende y las otras se apagan — así el ojo va donde tiene que ir
  const q=E('q'), rl=E('reloj');
  if(p && (p.pregunta || p.revela)){
    q.style.opacity=tr(t,p.t0,p.t0+.5);
    q.style.top=(p.revela?390:560)+'px';
    if(pintado!=='q'){
      q.querySelector('.pills').innerHTML =
        '<span class=pill>'+D.tema+'</span><span class="pill lv">'+D.nivel+'</span>';
      q.querySelector('.txt').textContent=D.q;
      q.querySelector('ul').innerHTML=D.ops.map((o,i)=>
        '<li data-i="'+i+'" data-ok="'+(o.ok?1:0)+'">'+o.txt+'</li>').join('');
      pintado='q';
    }
    const lis=[...q.querySelectorAll('li')];
    if(p.pregunta){
      lis.forEach((li,i)=>{ li.className='';
        li.style.opacity=tr(t,p.t0+.7+i*.35,p.t0+1.1+i*.35); });
      // el reloj baja de verdad: 3, 2, 1 en los últimos segundos
      const queda=Math.max(0,Math.ceil(p.t1-t));
      rl.style.opacity=tr(t,p.t0+.4,p.t0+.9);
      rl.textContent=queda<=3?String(queda):('0:'+String(Math.min(59,queda)).padStart(2,'0'));
      rl.className=queda<=3?'rojo':'';
    } else {
      rl.style.opacity=0;
      lis.forEach(li=>{ li.style.opacity=1;
        li.className=li.dataset.ok==='1'?'ok':'no'; });
    }
  } else { q.style.opacity=0; rl.style.opacity=0; }

  // la explicación, la que escribe la propia app
  const ex=E('exp');
  if(p && p.revela){ ex.style.opacity=tr(t,p.t0+1.0,p.t0+1.6);
    ex.style.top=(H_EXP)+'px';
    ex.querySelector('.k').textContent=T.k_rev;
    ex.querySelector('.t').textContent=D.exp; } else ex.style.opacity=0;

  // el número
  const nu=E('num');
  if(p && p.numero){ nu.style.opacity=tr(t,p.t0,p.t0+.5);
    nu.querySelector('.g').textContent='598';
    nu.querySelector('.l').textContent='questions.';
    nu.querySelector('.p').textContent=T.p_num; } else nu.style.opacity=0;

  const ou=E('out');
  if(t>=CIE){ const g=tr(t,CIE,CIE+.5); ou.style.opacity=1;
    ou.style.clipPath='inset(0 0 '+(100*(1-g))+'% 0)'; } else ou.style.opacity=0;
  E('bar').style.width=(100*cl(t/TOTAL,0,1))+'%';
}
const CIE=@@CIE@@, H_EXP=@@HEXP@@;
window.pinta=pinta;
</script>"""


def pasos():
    u = lambda n: 'file://' + os.path.join(QZ, n + '.png')
    return [
        dict(t0=T_H1[0], t1=T_H1[1], k=TXT['k1'], h=TXT['h1']),
        dict(t0=T_H2[0], t1=T_H2[1], k=TXT['k2'], h=TXT['h2']),
        dict(t0=T_PRE[0], t1=T_PRE[1], pregunta=True, k=TXT['k_pre'],
             h=TXT['h_pre']),
        dict(t0=T_REV[0], t1=T_REV[1], revela=True),
        dict(t0=T_NIV[0], t1=T_NIV[1], img=u('niveles'), top=900,
             k=TXT['k_niv'], h=TXT['h_niv'], cap=TXT['cap_niv']),
        dict(t0=T_HC[0], t1=T_HC[1], img=u('hardcore_rec'), top=820,
             k=TXT['k_hc'], h=TXT['h_hc'], cap=TXT['cap_hc']),
        dict(t0=T_NUM[0], t1=T_NUM[1], numero=True, k=TXT['k_num']),
    ]


def monta():
    from playwright.sync_api import sync_playwright
    import imageio_ffmpeg
    if not os.path.exists(os.path.join(QZ, 'leido.json')):
        sys.exit('faltan las fotos — corre antes tools/capta_quiz.py')
    recorta_hardcore()
    d = datos()
    doc = PAGINA
    for k, v in [('@@W@@', str(W)), ('@@H@@', str(H)), ('@@ORO@@', ORO),
                 ('@@ROJO@@', ROJO), ('@@VERDE@@', VERDE),
                 ('@@TOTAL@@', '%.2f' % TOTAL),
                 ('@@CIE@@', '%.2f' % T_CIERRE[0]),
                 ('@@HEXP@@', '1330'),
                 ('@@DATOS@@', json.dumps(d)), ('@@TXT@@', json.dumps(TXT)),
                 ('@@PASOS@@', json.dumps(pasos())),
                 ('@@LOGO@@', 'file://' + logo_oscuro()),
                 ('@@LEMA@@', TXT['lema']), ('@@LEGAL@@', TXT['legal'])]:
        doc = doc.replace(k, v)
    ruta = os.path.join(SALIDA, '_montaje_quiz.html')
    with io.open(ruta, 'w', encoding='utf-8') as f:
        f.write(doc)

    carpeta = os.path.join(SALIDA, '_qzf')
    shutil.rmtree(carpeta, ignore_errors=True)
    os.makedirs(carpeta)
    n = int(TOTAL * FPS)
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    print('montando %.1f s · %d fotogramas' % (TOTAL, n))
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox', '--hide-scrollbars',
                                    '--allow-file-access-from-files'],
                              **({'executable_path': exe} if exe else {}))
        pg = b.new_page(viewport={'width': W, 'height': H})
        fallos = []
        pg.on('pageerror', lambda e: fallos.append(str(e)))
        pg.goto('file://' + ruta, wait_until='load')
        pg.wait_for_timeout(1400)
        for i in range(n):
            pg.evaluate('t => window.pinta(t)', i / float(FPS))
            pg.screenshot(path=os.path.join(carpeta, '%04d.png' % i))
            if i % 120 == 0:
                print('  fotograma %d/%d' % (i, n))
        if fallos:
            print('🔴 errores JS:', fallos[:3])
        b.close()

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    mudo = os.path.join(SALIDA, '_qz_mudo.mp4')
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(FPS),
                    '-i', os.path.join(carpeta, '%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18',
                    '-movflags', '+faststart', mudo], check=True)
    shutil.rmtree(carpeta, ignore_errors=True)
    dest = os.path.join(SALIDA, 'reel-quiz.mp4')
    wav = os.path.join(RAIZ, 'out', 'marca_sonora', '03E_solo_cuerda_larga.wav')
    if os.path.exists(wav):
        ms = int(round(max(0.0, T_CIERRE[0] + 0.50 - 2.00) * 1000))
        subprocess.run(
            [ff, '-y', '-loglevel', 'error', '-i', mudo, '-i', wav,
             '-filter_complex',
             '[1:a]adelay=%d|%d,volume=%.3f,pan=stereo|c0=c0|c1=c0[a]'
             % (ms, ms, MARCA_VOL),
             '-map', '0:v:0', '-map', '[a]', '-c:v', 'copy',
             '-c:a', 'aac', '-b:a', '192k', '-shortest',
             '-movflags', '+faststart', dest], check=True)
    else:
        shutil.copy(mudo, dest)
    print('listo:', dest, '· %.1f MB' % (os.path.getsize(dest) / 1e6))
    return dest


if __name__ == '__main__':
    monta()
