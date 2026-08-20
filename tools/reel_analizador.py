# -*- coding: utf-8 -*-
"""Reel 2 — EL ANALIZADOR. Primero el golpe, después la herramienta.

Idea del dueño: *"mostremos el analizador, pero metiéndole contexto previo.
Quizá algún tipo de animación en donde una persona meta un trade en su PC y lo
erre, y se frustre"*. Esto es esa animación — y no hace falta ninguna
herramienta de fuera.

🔑 EL TRADE QUE SE ANIMA ES REAL, no un dibujo bonito. Sale del **banco del
analizador** (`tools/banco_analizador.py`, caso `I5_sl_cazado_perdido`), que
construye cada gráfico desde la aritmética del patrón. O sea que la barrida, el
FVG, la entrada y el stop cazado están donde la geometría dice que están, y son
exactamente los píxeles que el modelo miró cuando se auditó el analizador.
Y el veredicto que se enseña al final es la RESPUESTA REAL del analizador a ese
mismo gráfico, no un texto de marketing.

⚠️ NO se dibuja ningún personaje. La botarga que aparece es `logo4_standard`
   —el herrero con la pieza partida, arte ya aprobado—: se MUEVE, no se
   redibuja. La lección del dragón de Chronicles sigue en pie.

⚠️ El intro NO se recorta de la captura del banco: se vuelve a dibujar en el
   lienzo vertical con la tipografía del reel. Una captura de 1280×800 metida
   en 1080 de ancho deja las velas en nada.

    python3 tools/reel_analizador.py --intro    # solo la animación de entrada
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
FOTOS = os.path.join(SALIDA, '_an')
CASO = 'I5_sl_cazado_perdido'
W, H, FPS = 1080, 1920, 30

ORO = '#c9a227'
ROJO = '#e5484d'
VERDE = '#30a46c'

# ── el reloj del intro ────────────────────────────────────────────────────
# Cada tramo dura lo que tarda en LEERSE, no lo que tarda en dibujarse: el
# error del primer reel fue justo ese.
T_DIBUJO = (0.50, 3.40)      # las velas entran hasta la entrada
T_ENTRADA = (3.40, 5.00)     # aparece la entrada y sus marcas
T_STOP = (5.00, 7.20)        # el precio baja y caza el stop
T_SIN_TI = (7.20, 9.90)     # y se va al objetivo sin él
T_EXCUSA = (9.90, 13.40)    # "pura manipulación" + la botarga
# ── y a partir de aquí, la HERRAMIENTA ──
T_SUBE = (13.40, 18.20)     # el gráfico subido al analizador
T_METOD = (18.20, 22.60)    # las 7 metodologías, ICT encendida
T_NOTAS = (22.60, 27.00)    # sus propias notas, las que culpan al mercado
T_VER1 = (27.00, 31.60)     # el veredicto: el setup estaba bien
T_VER2 = (31.60, 36.60)     # …el stop no
T_CIERRE = (36.60, 41.00)
TOTAL_INTRO = 13.40
TOTAL = 41.00


def datos():
    sys.path.insert(0, os.path.join(RAIZ, 'tools'))
    import banco_analizador as B
    caso = [c for c in B.casos() if c['id'] == CASO][0]
    v = B.serie(caso['pivotes'], caso['n'], caso['seed'], caso.get('mults_vol', ()))
    B._ajusta_marcas(caso, v)
    return {
        'velas': [{k: round(c[k], 3) for k in ('o', 'h', 'l', 'c')} for c in v],
        'entrada': caso['entrada'], 'salida': caso['salida'],
        'sl': caso['sl'], 'tp': caso['tp'],
        'eql': 100.0, 'fvg': {'d1': 39, 'd2': 44, 'i2': 58},
        'notas': caso['form']['notes'],
    }


PAGINA = u"""<!doctype html><meta charset=utf-8>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap" rel=stylesheet>
<style>
 *{margin:0;padding:0;box-sizing:border-box}
 html,body{width:@@W@@px;height:@@H@@px;overflow:hidden;background:#07080b}
 #esc{position:relative;width:@@W@@px;height:@@H@@px;
   font-family:Inter,system-ui,sans-serif;color:#fff}
 /* la viñeta y el grano son los del resto del sistema visual */
 #vin{position:absolute;inset:0;pointer-events:none;
   background:radial-gradient(120% 80% at 50% 42%,transparent 40%,rgba(0,0,0,.62))}
 canvas{position:absolute;left:0;top:0}
 #tit{position:absolute;left:96px;right:96px;top:190px;opacity:0}
 #tit .k{font:700 21px 'JetBrains Mono',monospace;letter-spacing:.16em;
   text-transform:uppercase;color:rgba(255,255,255,.52)}
 #tit .g{margin-top:14px;font:900 62px/1.07 Inter,sans-serif;letter-spacing:-.02em;
   text-shadow:0 8px 40px rgba(0,0,0,.95)}
 #tit .g em{font-style:normal;color:@@ORO@@}
 #tit .g b.r{font-weight:900;color:@@ROJO@@}
 /* el rótulo que acompaña al momento del stop */
 #golpe{position:absolute;left:96px;right:96px;top:1395px;opacity:0}
 #golpe .g{font:900 60px/1.06 Inter,sans-serif;letter-spacing:-.02em}
 #golpe .p{margin-top:16px;font:500 30px/1.36 Inter,sans-serif;
   color:rgba(255,255,255,.72)}
 /* la excusa del trader, entrecomillada */
 #cita{position:absolute;left:96px;right:96px;top:1355px;opacity:0}
 #cita .c{font:800 44px/1.24 Inter,sans-serif;color:#fff}
 #cita .c:before{content:'\\201C';color:@@ORO@@;font-size:64px;line-height:0;
   vertical-align:-14px;margin-right:6px}
 #cita .q{margin-top:18px;font:700 20px 'JetBrains Mono',monospace;
   letter-spacing:.14em;text-transform:uppercase;color:rgba(255,255,255,.45)}
 /* la botarga: se MUEVE, no se redibuja */
 #mas{position:absolute;left:50%;bottom:60px;width:470px;opacity:0;
   transform:translateX(-50%)}
 #mas img{width:100%;display:block;filter:drop-shadow(0 24px 60px rgba(0,0,0,.8))}
 /* capturas REALES del analizador */
 #shot{position:absolute;left:60px;right:60px;top:640px;opacity:0}
 #shot img{width:100%;display:block;border-radius:14px;
   box-shadow:0 30px 70px rgba(0,0,0,.75), 0 0 0 1px rgba(255,255,255,.07)}
 #shot .cap{margin-top:26px;text-align:center;
   font:700 21px 'JetBrains Mono',monospace;letter-spacing:.14em;
   text-transform:uppercase;color:rgba(255,255,255,.55)}
 /* las notas del trader, compuestas (la captura del campo no se lee) */
 #nota{position:absolute;left:80px;right:80px;top:760px;opacity:0}
 #nota .cja{border-radius:16px;padding:34px 34px 30px;
   background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.10)}
 #nota .lb{font:700 18px 'JetBrains Mono',monospace;letter-spacing:.14em;
   text-transform:uppercase;color:rgba(255,255,255,.42)}
 #nota .tx{margin-top:16px;font:500 30px/1.44 Inter,sans-serif;
   color:rgba(255,255,255,.90)}
 #nota .tx b{color:@@ORO@@;font-weight:800}
 /* el veredicto, citado */
 #ver{position:absolute;left:88px;right:88px;top:620px;opacity:0}
 #ver .k{font:700 20px 'JetBrains Mono',monospace;letter-spacing:.16em;
   text-transform:uppercase;color:@@ORO@@}
 #ver .q{margin-top:22px;font:800 50px/1.22 Inter,sans-serif;color:#fff;
   text-shadow:0 8px 40px rgba(0,0,0,.9)}
 #ver .q em{font-style:normal;color:@@ORO@@}
 #ver .f{margin-top:26px;font:500 27px/1.4 Inter,sans-serif;
   color:rgba(255,255,255,.68)}
 /* ── cierre ── */
 #out{position:absolute;inset:0;opacity:0;display:flex;flex-direction:column;
   align-items:center;justify-content:center;background:#07080b}
 #out .lg{width:520px;filter:brightness(0) invert(1)}
 #out .sl{margin-top:34px;font:800 40px Inter,sans-serif;color:#fff;
   letter-spacing:-.01em}
 #out .lgl{position:absolute;left:0;right:0;bottom:@@LEGY@@px;text-align:center;
   font:500 22px Inter,sans-serif;color:rgba(255,255,255,.42)}
 #bar{position:absolute;left:0;bottom:0;height:5px;background:@@ORO@@;width:0}
 #flash{position:absolute;inset:0;background:@@ROJO@@;opacity:0;
   mix-blend-mode:screen;pointer-events:none}
</style>
<div id=esc>
  <canvas id=cv width="@@W@@" height="@@H@@"></canvas>
  <div id=vin></div><div id=flash></div>
  <div id=tit><div class=k></div><div class=g></div></div>
  <div id=golpe><div class=g></div><div class=p></div></div>
  <div id=cita><div class=c></div><div class=q></div></div>
  <div id=mas><img src="@@MASCOTA@@"></div>
  <div id=shot><img id=shotimg><div class=cap></div></div>
  <div id=nota><div class=cja><div class=lb></div><div class=tx></div></div></div>
  <div id=ver><div class=k></div><div class=q></div><div class=f></div></div>
  <div id=out><img class=lg src="@@LOGO@@"><div class=sl>@@LEMA@@</div>
    <div class=lgl>@@LEGAL@@</div></div>
  <div id=bar></div>
</div>
<script>
const D = @@DATOS@@;
const TXT = @@TXT@@;
const TP  = @@TP@@;
const PASOS = @@PASOS@@;
const CIE = @@CIE@@;
const W=@@W@@, H=@@H@@, TOTAL=@@TOTAL@@;
const E = id => document.getElementById(id);
const cv = E('cv'), cx = cv.getContext('2d');

// suavizado estándar del sistema: nada entra ni sale de golpe
const cl=(v,a,b)=>Math.max(a,Math.min(b,v));
const tr=(t,a,b)=>{const x=cl((t-a)/(b-a),0,1);return x*x*(3-2*x);};

// ── la caja del gráfico dentro del lienzo vertical ──
const GX=70, GW=W-140, GY=505, GH=800;
const N=D.velas.length;

/* 🔑 La escala de precio se calcula sobre lo que YA se ve, no sobre la serie
   entera: si se fija de entrada, las primeras velas quedan aplastadas en una
   franja y el dibujo no parece un gráfico. Y se INTERPOLA hacia el objetivo
   para que el reencuadre sea un movimiento y no un salto. */
let escala = null;
function rango(hasta){
  let lo=1e9, hi=-1e9;
  for (let i=0;i<hasta;i++){ lo=Math.min(lo,D.velas[i].l); hi=Math.max(hi,D.velas[i].h); }
  if (hasta > D.entrada.i){ lo=Math.min(lo,D.sl); hi=Math.max(hi,D.tp); }
  const m=(hi-lo)*0.10 || 1;
  return {lo:lo-m, hi:hi+m};
}
function suave(obj){
  if (!escala) { escala = {lo:obj.lo, hi:obj.hi}; return escala; }
  escala.lo += (obj.lo-escala.lo)*0.14;
  escala.hi += (obj.hi-escala.hi)*0.14;
  return escala;
}
const py = (p,s) => GY + GH*(1-(p-s.lo)/(s.hi-s.lo));
const px = (i,vis) => GX + GW*(i/(vis-1));

function vela(i, s, vis, alfa){
  const v=D.velas[i], x=px(i,vis), an=Math.max(2.4, GW/vis*0.62);
  const sube = v.c>=v.o;
  cx.globalAlpha = alfa;
  cx.strokeStyle = sube ? '@@VERDE@@' : '@@ROJO@@';
  cx.fillStyle = cx.strokeStyle;
  cx.lineWidth = Math.max(1, an*0.16);
  cx.beginPath(); cx.moveTo(x, py(v.h,s)); cx.lineTo(x, py(v.l,s)); cx.stroke();
  const y0=py(Math.max(v.o,v.c),s), y1=py(Math.min(v.o,v.c),s);
  cx.fillRect(x-an/2, y0, an, Math.max(1.5, y1-y0));
  cx.globalAlpha = 1;
}

function linea(p, s, color, guion, txt, vis){
  cx.save(); cx.strokeStyle=color; cx.lineWidth=2.4;
  if (guion) cx.setLineDash([12,10]);
  const y=py(p,s);
  cx.beginPath(); cx.moveTo(GX,y); cx.lineTo(GX+GW,y); cx.stroke();
  cx.restore();
  if (txt){ cx.fillStyle=color; cx.font="700 22px 'JetBrains Mono',monospace";
    cx.fillText(txt, GX+4, y-11); }
}

function pinta(t){
  cx.clearRect(0,0,W,H);
  // cuántas velas se han dibujado ya
  const p1 = tr(t, @@D0@@, @@D1@@);
  const hastaEntrada = D.entrada.i+1;
  let vis;
  if (t < @@S0@@) vis = Math.max(3, Math.round(hastaEntrada*p1));
  else vis = Math.round(hastaEntrada + (N-hastaEntrada)*tr(t,@@S0@@,@@S1@@));
  vis = cl(vis, 3, N);
  const s = suave(rango(vis));

  // rejilla discreta
  cx.strokeStyle='rgba(255,255,255,.05)'; cx.lineWidth=1;
  for(let k=0;k<=4;k++){ const y=GY+GH*k/4;
    cx.beginPath(); cx.moveTo(GX,y); cx.lineTo(GX+GW,y); cx.stroke(); }

  // el nivel de liquidez y el FVG salen cuando ya hay velas que los expliquen
  if (vis > 42){
    const a = tr(t, @@D0@@+1.1, @@D0@@+1.8);
    cx.globalAlpha=a; linea(D.eql, s, '@@ROJO@@', true, 'EQL / SSL', vis);
    cx.globalAlpha=1;
  }
  if (vis > D.fvg.d2+2){
    const a = tr(t, @@D0@@+1.9, @@D0@@+2.5);
    const y0=py(D.velas[D.fvg.d1].h,s), y1=py(D.velas[D.fvg.d2].l,s);
    cx.globalAlpha=a*0.9;
    cx.fillStyle='rgba(90,170,255,.13)';
    cx.fillRect(px(D.fvg.d1,vis), y0, px(Math.min(D.fvg.i2,vis-1),vis)-px(D.fvg.d1,vis), y1-y0);
    cx.strokeStyle='rgba(120,190,255,.55)'; cx.lineWidth=2;
    cx.strokeRect(px(D.fvg.d1,vis), y0, px(Math.min(D.fvg.i2,vis-1),vis)-px(D.fvg.d1,vis), y1-y0);
    cx.fillStyle='rgba(150,205,255,.95)'; cx.font="700 21px 'JetBrains Mono',monospace";
    cx.fillText('FVG', px(D.fvg.d1,vis)+8, y0-10);
    cx.globalAlpha=1;
  }

  for (let i=0;i<vis;i++){
    // la última vela entra desvanecida: sin esto el dibujo "salta" de una en una
    const alfa = (i===vis-1) ? 0.35+0.65*((vis*1.0)%1 || 1) : 1;
    vela(i, s, vis, alfa);
  }

  // ── entrada ──
  if (t > @@E0@@){
    const a=tr(t,@@E0@@,@@E0@@+0.5);
    const x=px(D.entrada.i,vis), y=py(D.entrada.p,s);
    cx.globalAlpha=a;
    cx.fillStyle='@@ORO@@'; cx.beginPath();
    cx.moveTo(x,y-13); cx.lineTo(x+13,y+11); cx.lineTo(x-13,y+11); cx.closePath(); cx.fill();
    cx.font="700 23px 'JetBrains Mono',monospace";
    const eti='LONG '+D.entrada.p.toFixed(2);
    const an2=cx.measureText(eti).width;
    if (x+22+an2 < GX+GW) cx.fillText(eti, x+22, y+8);
    else { cx.textAlign='right'; cx.fillText(eti, x-22, y+8); cx.textAlign='left'; }
    linea(D.sl, s, '@@ROJO@@', true, 'SL '+D.sl.toFixed(2), vis);
    linea(D.tp, s, '@@VERDE@@', true, 'TP '+D.tp.toFixed(2), vis);
    cx.globalAlpha=1;
  }
  // ── el stop, cazado ──
  if (t > @@P0@@ && vis > D.salida.i){
    const a=tr(t,@@P0@@,@@P0@@+0.4);
    const x=px(D.salida.i,vis), y=py(D.salida.p,s);
    cx.globalAlpha=a;
    cx.strokeStyle='@@ROJO@@'; cx.lineWidth=4;
    cx.beginPath(); cx.arc(x,y,17,0,Math.PI*2); cx.stroke();
    cx.beginPath(); cx.moveTo(x-9,y-9); cx.lineTo(x+9,y+9);
    cx.moveTo(x+9,y-9); cx.lineTo(x-9,y+9); cx.stroke();
    cx.globalAlpha=1;
  }

  // ── capas de texto ──
  const set=(id,html)=>{const e=E(id); if(e.innerHTML!==html) e.innerHTML=html;};
  const tit=E('tit');
  if (t < @@P0@@){
    tit.style.opacity = tr(t,0.35,1.1) * (1-tr(t,@@P0@@-0.5,@@P0@@));
    tit.querySelector('.k').textContent = TXT.k1;
    set('tit', tit.innerHTML.replace(/<div class="?g"?>[\\s\\S]*<\\/div>/,
        '<div class=g>'+TXT.t1+'</div>'));
    tit.querySelector('.g').innerHTML = TXT.t1;
  } else tit.style.opacity = 0;

  const gp=E('golpe');
  if (t >= @@P0@@ && t < @@X0@@){
    gp.style.opacity = tr(t,@@P0@@+0.15,@@P0@@+0.7)*(1-tr(t,@@X0@@-0.45,@@X0@@));
    gp.querySelector('.g').innerHTML = (t < @@N0@@) ? TXT.t2 : TXT.t3;
    gp.querySelector('.p').innerHTML = (t < @@N0@@) ? TXT.p2 : TXT.p3;
  } else gp.style.opacity = 0;

  const ct=E('cita'), ms=E('mas');
  if (t >= @@X0@@){
    const a=tr(t,@@X0@@+0.2,@@X0@@+0.8);
    ct.style.opacity=a;
    ct.querySelector('.c').innerHTML = TXT.cita;
    ct.querySelector('.q').textContent = TXT.citaPie;
    const m=tr(t,@@X0@@+0.55,@@X0@@+1.35);
    ms.style.opacity=m;
    ms.style.transform='translateX(-50%) translateY('+(46*(1-m))+'px) scale('+(0.94+0.06*m)+')';
  } else { ct.style.opacity=0; ms.style.opacity=0; }

  // ── LA HERRAMIENTA ────────────────────────────────────────────────
  // ⚠️ al salir del intro hay que APAGAR el lienzo del gráfico y las capas
  //    del intro: si no, siguen pintadas debajo de las capturas.
  const sh=E('shot'), vr=E('ver');
  if (t >= TP.sube){
    cx.clearRect(0,0,W,H);
    E('cita').style.opacity=0; E('mas').style.opacity=0;
    E('golpe').style.opacity=0; E('tit').style.opacity=0;
  }
  let paso = null;
  for (const p of PASOS) if (t >= p.t0 && t < p.t1) paso = p;
  if (paso && paso.img){
    const g = tr(t,paso.t0,paso.t0+0.55)*(1-tr(t,paso.t1-0.35,paso.t1));
    sh.style.opacity=g;
    sh.style.transform='translateY('+(26*(1-tr(t,paso.t0,paso.t0+0.7)))+'px)';
    sh.style.top=paso.top+'px';
    if (E('shotimg').getAttribute('src')!==paso.img)
      E('shotimg').setAttribute('src', paso.img);
    sh.querySelector('.cap').textContent = paso.cap;
  } else if (t >= TP.sube) sh.style.opacity=0;

  if (paso && paso.h){
    E('tit').style.opacity =
      tr(t,paso.t0+0.15,paso.t0+0.7)*(1-tr(t,paso.t1-0.3,paso.t1));
    E('tit').querySelector('.k').textContent = paso.k || '';
    E('tit').querySelector('.g').innerHTML = paso.h;
  }

  const nt=E('nota');
  if (paso && paso.nota){
    const g = tr(t,paso.t0,paso.t0+0.5)*(1-tr(t,paso.t1-0.35,paso.t1));
    nt.style.opacity=g;
    nt.style.transform='translateY('+(22*(1-tr(t,paso.t0,paso.t0+0.7)))+'px)';
    nt.querySelector('.lb').textContent = paso.lb;
    nt.querySelector('.tx').innerHTML = paso.nota;
  } else nt.style.opacity=0;

  if (paso && paso.cita){
    const g = tr(t,paso.t0,paso.t0+0.5)*(1-tr(t,paso.t1-0.35,paso.t1));
    vr.style.opacity=g;
    vr.style.transform='translateY('+(22*(1-tr(t,paso.t0,paso.t0+0.7)))+'px)';
    vr.querySelector('.k').textContent = paso.k;
    vr.querySelector('.q').innerHTML = paso.cita;
    vr.querySelector('.f').innerHTML = paso.pie || '';
  } else vr.style.opacity=0;

  // ── el cierre: barrido a negro y la marca ──
  const ou=E('out');
  if (t >= CIE){
    const g = tr(t, CIE, CIE+0.5);
    ou.style.opacity = 1;
    ou.style.clipPath = 'inset(0 0 ' + (100*(1-g)) + '% 0)';
  } else ou.style.opacity = 0;

  // el fogonazo del stop: corto y sin pasarse, no es una película de acción
  E('flash').style.opacity = 0.30*(1-tr(t,@@P0@@,@@P0@@+0.42))*(t>=@@P0@@?1:0);
  E('bar').style.width = (100*cl(t/TOTAL,0,1))+'%';
}
window.pinta = pinta;
</script>"""

TXT = {
    'k1': 'A textbook setup',
    't1': 'Sweep. Displacement.<br>FVG. You took it.',
    't2': 'Stopped out.',
    'p2': 'The market went down to the tick of your stop.',
    't3': 'Then it went to <em>your target</em>.',
    'p3': 'Without you.',
    'cita': 'Pure manipulation. My trade was fine.',
    'citaPie': "— what you tell yourself at 11 p.m.",
    # ── la herramienta ──
    'k_sube': 'Or you can just ask',
    'h_sube': 'Upload the <em>same</em> chart.',
    'cap_sube': 'the screenshot you already have',
    'k_met': 'Your method, not ours',
    'h_met': 'Pick how you<br>actually trade.',
    'cap_met': 'ICT · OTE · Wyckoff · Patterns · Harmonic · Elliott · Technical',
    'k_notas': 'And tell it what you thought',
    'h_notas': 'Including the part<br>you got wrong.',
    'cap_notas': 'Trade construction',
    'nota': 'Sweep of the equal lows, displacement with an FVG, I entered on '
            'the retracement. <b>I put the stop tight just under my entry '
            'candle to improve the R:R.</b> Price went down exactly to take '
            'my stop and then ran to my target without me.',
    # 🔴 Estas dos citas son la RESPUESTA REAL del analizador a este mismo
    #    gráfico (banco, caso I5). Ver la nota de VERDICTO_EN abajo.
    'k_v1': 'The answer',
    'v1': 'The setup was<br><em>technically valid.</em>',
    'pv1': 'Sweep of the equal lows, displacement, FVG. The idea was fine.',
    'k_v2': 'The answer',
    'v2': 'The <em>stop</em> was<br>the problem.',
    'pv2': 'Placed inside the noise instead of beyond the low of the sweep — '
          'so the trade never had room to breathe.',
}


AZ = os.path.join(SALIDA, '_az')


def pasos():
    """Los tramos de producto: capturas REALES y las citas del veredicto."""
    u = lambda n: 'file://' + os.path.join(AZ, n + '.png')
    T = TXT
    return [
        dict(t0=T_SUBE[0], t1=T_SUBE[1], img=u('subida_rec'), top=700,
             k=T['k_sube'], h=T['h_sube'], cap=T['cap_sube']),
        dict(t0=T_METOD[0], t1=T_METOD[1], img=u('metodologias_2f'), top=860,
             k=T['k_met'], h=T['h_met'], cap=T['cap_met']),
        dict(t0=T_NOTAS[0], t1=T_NOTAS[1], nota=T['nota'], lb=T['cap_notas'],
             k=T['k_notas'], h=T['h_notas']),
        dict(t0=T_VER1[0], t1=T_VER1[1], cita=T['v1'], pie=T['pv1'], k=T['k_v1']),
        dict(t0=T_VER2[0], t1=T_VER2[1], cita=T['v2'], pie=T['pv2'], k=T['k_v2']),
    ]


def parte_metodologias():
    """Parte la tira de metodologías en dos filas.

    ⚠️ Es una tira de 1592×94: mostrada a lo ancho del lienzo el texto queda en
    ~16 px y no se lee en un teléfono. Partida en dos, cada mitad se muestra al
    doble de escala.
    """
    from PIL import Image
    src = os.path.join(AZ, 'metodologias_ict.png')
    if not os.path.exists(src):
        return
    im = Image.open(src).convert('RGBA')
    w, h = im.size
    corte = int(w * 0.42)          # tras "OTE / Std Dev"
    hueco = 18
    out = Image.new('RGBA', (max(corte, w - corte), h * 2 + hueco), (0, 0, 0, 0))
    out.paste(im.crop((0, 0, corte, h)), (0, 0))
    out.paste(im.crop((corte, 0, w, h)), (0, h + hueco))
    out.save(os.path.join(AZ, 'metodologias_2f.png'))


def recorta_subida():
    """De la captura de pantalla completa, solo la tarjeta del gráfico.

    ⚠️ La foto `subida` es la pantalla ENTERA (3000×2000): metida en 960 px de
    ancho el gráfico queda en nada. Se recorta la zona de la vista previa.
    """
    from PIL import Image
    src = os.path.join(AZ, 'subida.png')
    if not os.path.exists(src):
        return
    # con el selector #preview-wrap la foto YA es solo la vista previa
    Image.open(src).save(os.path.join(AZ, 'subida_rec.png'))


def monta(solo_intro=True):
    from playwright.sync_api import sync_playwright
    import imageio_ffmpeg
    recorta_subida()
    parte_metodologias()
    d = datos()
    doc = PAGINA
    for k, v in [('@@W@@', str(W)), ('@@H@@', str(H)), ('@@ORO@@', ORO),
                 ('@@ROJO@@', ROJO), ('@@VERDE@@', VERDE),
                 ('@@TOTAL@@', '%.2f' % (TOTAL_INTRO if solo_intro else TOTAL)),
                 ('@@TP@@', json.dumps({'sube': T_SUBE[0]})),
                 ('@@CIE@@', '%.2f' % (999 if solo_intro else T_CIERRE[0])),
                 ('@@LOGO@@', 'file://' + os.path.join(
                     RAIZ, 'scalpel', 'static', 'logo_t.png')),
                 ('@@LEMA@@', 'Process over impulse.'),
                 ('@@LEGY@@', '150'),
                 ('@@LEGAL@@', 'Educational content · Not financial advice'),
                 ('@@PASOS@@', json.dumps([] if solo_intro else pasos())),
                 ('@@DATOS@@', json.dumps(d)), ('@@TXT@@', json.dumps(TXT)),
                 ('@@MASCOTA@@', 'file://' + os.path.join(
                     RAIZ, 'scalpel', 'static', 'logo4_standard_dark.png')),
                 ('@@D0@@', '%.2f' % T_DIBUJO[0]), ('@@D1@@', '%.2f' % T_DIBUJO[1]),
                 ('@@E0@@', '%.2f' % T_ENTRADA[0]),
                 ('@@S0@@', '%.2f' % T_STOP[0]), ('@@S1@@', '%.2f' % T_SIN_TI[1]),
                 ('@@P0@@', '%.2f' % T_STOP[0]),
                 ('@@N0@@', '%.2f' % T_SIN_TI[0]),
                 ('@@X0@@', '%.2f' % T_EXCUSA[0])]:
        doc = doc.replace(k, v)
    html = os.path.join(SALIDA, '_montaje_analizador.html')
    with io.open(html, 'w', encoding='utf-8') as f:
        f.write(doc)

    carpeta = os.path.join(FOTOS, '_f')
    shutil.rmtree(carpeta, ignore_errors=True)
    os.makedirs(carpeta)
    n = int((TOTAL_INTRO if solo_intro else TOTAL) * FPS)
    # ⚠️ el navegador del contenedor NO está donde Playwright lo busca por
    #    defecto: hay que darle la ruta o falla con "Executable doesn't exist".
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox', '--hide-scrollbars',
                                    '--allow-file-access-from-files'],
                              **({'executable_path': exe} if exe else {}))
        pg = b.new_page(viewport={'width': W, 'height': H})
        errores = []
        pg.on('pageerror', lambda e: errores.append(str(e)))
        pg.goto('file://' + html, wait_until='domcontentloaded')
        pg.wait_for_timeout(1200)
        for i in range(n):
            pg.evaluate('t => window.pinta(t)', i / float(FPS))
            pg.screenshot(path=os.path.join(carpeta, '%04d.png' % i))
            if i % 90 == 0:
                print('  fotograma %d/%d' % (i, n))
        if errores:
            print('🔴 errores JS:', errores[:3])
        b.close()

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    dest = os.path.join(SALIDA, 'reel-analizador-intro.mp4'
                        if solo_intro else 'reel-analizador.mp4')
    mudo = os.path.join(SALIDA, '_an_mudo.mp4')
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(FPS),
                    '-i', os.path.join(carpeta, '%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18',
                    '-movflags', '+faststart', mudo], check=True)
    shutil.rmtree(carpeta, ignore_errors=True)
    # 🔑 el golpe cae cuando el logo ASIENTA (fin del barrido), no cuando
    #    empieza: si suena antes, el oído lo separa de la marca.
    wav = os.path.join(RAIZ, 'out', 'marca_sonora',
                       '03E_solo_cuerda_larga.wav')
    if not solo_intro and os.path.exists(wav):
        ms = int(round(max(0.0, T_CIERRE[0] + 0.50 - 2.00) * 1000))
        subprocess.run(
            [ff, '-y', '-loglevel', 'error', '-i', mudo, '-i', wav,
             '-filter_complex',
             '[1:a]adelay=%d|%d,pan=stereo|c0=c0|c1=c0[a]' % (ms, ms),
             '-map', '0:v:0', '-map', '[a]', '-c:v', 'copy',
             '-c:a', 'aac', '-b:a', '192k', '-shortest',
             '-movflags', '+faststart', dest], check=True)
    else:
        shutil.copy(mudo, dest)
    print('listo:', dest, '· %.1f MB' % (os.path.getsize(dest) / 1e6))
    return dest


if __name__ == '__main__':
    os.makedirs(FOTOS, exist_ok=True)
    monta(solo_intro='--intro' in sys.argv)
