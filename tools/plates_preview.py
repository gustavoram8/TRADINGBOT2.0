# -*- coding: utf-8 -*-
"""Catálogo de MARCOS (placas del bloque de autor).

Un marco es una placa rectangular que va DETRÁS del bloque del autor en el
foro: avatar + medalla del rango + nombre + chip de racha + pastilla. Se eligió
esta forma sobre el aro alrededor del avatar porque el aro no se puede
presumir: nadie paga por decorar el borde de un círculo de 40px.

DOS REGLAS ESTRUCTURALES:

1. Cada placa lleva un DIBUJO, no solo textura. La primera tanda se hizo solo
   con degradados CSS y salieron todas iguales — "fondo oscuro con difuminado"
   ×32 — porque un degradado no puede dibujar. El motivo va en SVG.
2. El arte vive a la IZQUIERDA y la placa se apaga hacia la DERECHA (ver
   .plate::after). Así la medalla y la pastilla del rango caen siempre sobre
   fondo calmado y la placa nunca se come al rango.

    python3 tools/plates_preview.py               # todas
    python3 tools/plates_preview.py chronicles    # algunas
"""
import os
import subprocess
import sys
import tempfile

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
OUT = os.environ.get('PLATES_OUT', '/tmp/plates_preview.png')

# El motivo se dibuja en un lienzo 64×64 y se repite/ancla a la izquierda.
# Siluetas gruesas a propósito: tienen que leerse a 48px de alto.
PLATES = [
 # ── ÉPICA ───────────────────────────────────────────────────────────────
 ('chronicles', 'Chronicles', 'épica',
  "background:#14060b;background-image:linear-gradient(100deg,#1e070e,#5c1120 62%,#12060a);",
  '#f0b8b0', """
   <path d="M6 44 C14 40 16 30 24 27 C30 25 34 28 40 24 C44 21 45 15 52 13
            C50 19 47 22 44 25 C48 26 52 25 56 22 C54 29 48 33 42 33
            C38 39 30 43 22 44 Z" fill="currentColor" opacity=".92"/>
   <path d="M44 20 L50 9 L47 20 Z" fill="currentColor"/>
   <circle cx="45.5" cy="20.5" r="1.6" fill="#14060b"/>
   <path d="M8 46 C18 52 34 52 46 45 C36 56 16 56 8 46 Z"
         fill="currentColor" opacity=".5"/>
  """),
 ('samurai', 'Samurai', 'épica',
  "background:#0c1330;background-image:linear-gradient(100deg,#0a1029,#1f3068 60%,#090e24);",
  '#c9d8ff', """
   <circle cx="46" cy="18" r="10" fill="#d84a4a" opacity=".85"/>
   <path d="M14 40 C14 26 22 19 32 19 C42 19 50 26 50 40 L44 40
            C44 30 39 25 32 25 C25 25 20 30 20 40 Z" fill="currentColor"/>
   <path d="M20 22 C24 12 40 12 44 22 C38 17 26 17 20 22 Z" fill="currentColor"/>
   <rect x="12" y="40" width="40" height="5" rx="2.5" fill="currentColor" opacity=".8"/>
   <rect x="14" y="47" width="36" height="4" rx="2" fill="currentColor" opacity=".55"/>
  """),
 ('cathedral', 'Cathedral', 'épica',
  "background:#080c26;background-image:linear-gradient(100deg,#070a22,#1b2668 60%,#060919);",
  '#9db6ff', """
   <circle cx="32" cy="32" r="21" fill="none" stroke="currentColor" stroke-width="2.4"/>
   <circle cx="32" cy="32" r="7" fill="currentColor" opacity=".9"/>
   <g stroke="currentColor" stroke-width="1.8">
     <path d="M32 11 V53 M11 32 H53 M17 17 L47 47 M47 17 L17 47"/>
   </g>
   <g fill="currentColor" opacity=".75">
     <circle cx="32" cy="16" r="3.4"/><circle cx="32" cy="48" r="3.4"/>
     <circle cx="16" cy="32" r="3.4"/><circle cx="48" cy="32" r="3.4"/>
   </g>
  """),
 ('runes', 'Runestone', 'épica',
  "background:#101216;background-image:linear-gradient(100deg,#0d0f13,#2b3138 60%,#0c0e12);",
  '#63dcff', """
   <g fill="#5a6470">
     <path d="M8 52 V26 C8 21 12 18 15 18 C18 18 22 21 22 26 V52 Z"/>
     <path d="M26 52 V16 C26 10 30 7 34 7 C38 7 42 10 42 16 V52 Z"/>
     <path d="M46 52 V30 C46 25 49 22 52 22 C55 22 58 25 58 30 V52 Z"/>
   </g>
   <g stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none">
     <path d="M15 26 V38 M11 30 L15 34 L19 30"/>
     <path d="M34 16 V40 M28 22 L34 28 L40 22 M28 34 L34 28"/>
     <path d="M52 30 V42 M48 36 H56"/>
   </g>
  """),

 # ── MERCADO ─────────────────────────────────────────────────────────────
 ('bullrun', 'Bull Run', 'mercado',
  "background:#04170f;background-image:linear-gradient(100deg,#04150e,#0d5636 60%,#03120c);",
  '#5cf0a8', """
   <path d="M12 20 C6 16 5 9 8 6 C13 11 18 14 22 15 L22 22 Z" fill="currentColor"/>
   <path d="M52 20 C58 16 59 9 56 6 C51 11 46 14 42 15 L42 22 Z" fill="currentColor"/>
   <path d="M22 14 C22 14 26 12 32 12 C38 12 42 14 42 14 L42 30
            C42 42 37 50 32 50 C27 50 22 42 22 30 Z" fill="currentColor"/>
   <g fill="#04170f"><circle cx="26.5" cy="26" r="2.4"/><circle cx="37.5" cy="26" r="2.4"/></g>
   <path d="M28 39 C30 41 34 41 36 39" stroke="#04170f" stroke-width="2"
         fill="none" stroke-linecap="round"/>
  """),
 ('bearcave', 'Bear Cave', 'mercado',
  "background:#180810;background-image:linear-gradient(100deg,#160710,#571426 60%,#140610);",
  '#ff8fa8', """
   <circle cx="15" cy="17" r="8" fill="currentColor"/>
   <circle cx="49" cy="17" r="8" fill="currentColor"/>
   <circle cx="15" cy="17" r="4" fill="#180810" opacity=".55"/>
   <circle cx="49" cy="17" r="4" fill="#180810" opacity=".55"/>
   <path d="M32 12 C44 12 52 22 52 33 C52 45 43 52 32 52
            C21 52 12 45 12 33 C12 22 20 12 32 12 Z" fill="currentColor"/>
   <g fill="#180810"><circle cx="25" cy="30" r="2.6"/><circle cx="39" cy="30" r="2.6"/></g>
   <ellipse cx="32" cy="40" rx="7" ry="5.5" fill="#180810" opacity=".45"/>
   <ellipse cx="32" cy="37" rx="3.4" ry="2.6" fill="#180810"/>
  """),
 ('session', 'Kill Zone', 'mercado',
  "background:#08111f;background-image:linear-gradient(100deg,#070f1c,#173257 60%,#060d18);",
  '#7fb6ff', """
   <circle cx="32" cy="32" r="23" fill="none" stroke="currentColor" stroke-width="2.4"/>
   <path d="M32 32 L32 9 A23 23 0 0 1 51.9 43.5 Z" fill="currentColor" opacity=".33"/>
   <g stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
     <path d="M32 14 V32 L45 39"/>
   </g>
   <g stroke="currentColor" stroke-width="2.4" stroke-linecap="round" opacity=".8">
     <path d="M32 6 V11 M32 53 V58 M6 32 H11 M53 32 H58"/>
   </g>
  """),
 ('terminal', 'Terminal', 'mercado',
  "background:#02100a;background-image:linear-gradient(100deg,#020e08,#0a4023 60%,#010c07);",
  '#4dff9b', """
   <rect x="6" y="12" width="52" height="36" rx="4" fill="none"
         stroke="currentColor" stroke-width="2.4"/>
   <g stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
     <path d="M13 22 L18 27 L13 32"/>
     <path d="M22 33 H34"/>
   </g>
   <rect x="38" y="20" width="4" height="9" fill="currentColor" opacity=".9"/>
   <g stroke="currentColor" stroke-width="1.8" opacity=".55">
     <path d="M13 39 H30 M35 39 H50 M44 27 H52"/>
   </g>
   <path d="M24 48 H40 L38 54 H26 Z" fill="currentColor" opacity=".7"/>
  """),
 ('liquidity', 'Liquidity Pool', 'mercado',
  "background:#031620;background-image:linear-gradient(100deg,#02121b,#0a4a63 60%,#02101a);",
  '#6fe0ff', """
   <path d="M32 8 C34 20 44 24 44 34 C44 42 39 48 32 48
            C25 48 20 42 20 34 C20 24 30 20 32 8 Z" fill="currentColor" opacity=".9"/>
   <path d="M30 26 C27 31 27 37 30 41" stroke="#031620" stroke-width="2"
         fill="none" stroke-linecap="round" opacity=".7"/>
   <g stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" opacity=".65">
     <path d="M4 52 C10 48 14 56 20 52 C26 48 30 56 36 52 C42 48 46 56 52 52 C56 49 58 52 60 53"/>
     <path d="M4 58 C10 54 14 62 20 58 C26 54 30 62 36 58" opacity=".6"/>
   </g>
  """),

 # ── NATURAL ─────────────────────────────────────────────────────────────
 ('storm', 'Storm', 'natural',
  "background:#0d1219;background-image:linear-gradient(100deg,#0b1017,#2b3543 60%,#0a0e15);",
  '#cfe6ff', """
   <path d="M16 34 C9 34 5 29 5 24 C5 19 9 15 14 15 C16 8 23 4 30 4
            C39 4 46 11 46 20 C53 20 58 25 58 31 C58 37 53 41 47 41 L16 41 Z"
         fill="currentColor" opacity=".92"/>
   <path d="M34 38 L24 54 L31 54 L26 62 L40 44 L32 44 Z" fill="#ffe066"/>
  """),
 ('abyss', 'Abyss', 'natural',
  "background:#020a14;background-image:linear-gradient(100deg,#01080f,#093050 60%,#010710);",
  '#7cc9ff', """
   <path d="M4 44 C14 38 24 38 32 42 C34 34 40 26 50 20
            C48 30 46 38 46 44 C46 50 48 56 50 62 C40 56 34 50 32 44
            C24 50 14 50 4 44 Z" fill="currentColor" opacity=".9"/>
   <g fill="currentColor" opacity=".55">
     <circle cx="12" cy="18" r="3"/><circle cx="20" cy="9" r="2"/>
     <circle cx="26" cy="20" r="1.6"/><circle cx="8" cy="30" r="1.8"/>
   </g>
  """),
 ('dunes', 'Desert Night', 'natural',
  "background:#070a1c;background-image:linear-gradient(100deg,#06081a,#1d2352 60%,#05071a);",
  '#b9a6ff', """
   <circle cx="46" cy="16" r="9" fill="#e8e2ff" opacity=".92"/>
   <circle cx="42" cy="13" r="8" fill="#070a1c"/>
   <g fill="#ffffff" opacity=".85">
     <circle cx="12" cy="10" r="1.4"/><circle cx="24" cy="18" r="1"/>
     <circle cx="8" cy="24" r="1.1"/><circle cx="56" cy="30" r="1.2"/>
   </g>
   <path d="M0 52 C10 42 20 50 30 44 C40 38 50 46 64 40 L64 64 L0 64 Z"
         fill="currentColor" opacity=".55"/>
   <path d="M0 60 C12 52 24 60 36 54 C48 48 56 56 64 52 L64 64 L0 64 Z"
         fill="currentColor" opacity=".85"/>
  """),
 ('jungle', 'Jungle', 'natural',
  "background:#04170c;background-image:linear-gradient(100deg,#03140a,#0d5424 60%,#031209);",
  '#63e07a', """
   <g stroke="currentColor" stroke-width="2.4" fill="none" stroke-linecap="round">
     <path d="M6 60 C6 40 14 24 30 14"/>
     <path d="M30 14 C22 16 16 22 13 30 M30 14 C24 20 20 28 18 38
              M30 14 C36 18 40 24 41 32 M30 14 C34 22 35 32 33 42"/>
   </g>
   <g stroke="currentColor" stroke-width="2.2" fill="none" stroke-linecap="round" opacity=".65">
     <path d="M56 60 C56 44 50 32 40 24"/>
     <path d="M40 24 C46 27 50 32 52 38 M40 24 C44 31 45 39 44 46"/>
   </g>
  """),

 # ── MATERIAL ────────────────────────────────────────────────────────────
 ('circuit', 'Circuit', 'material',
  "background:#040e0c;background-image:linear-gradient(100deg,#030c0a,#0b3a30 60%,#020a08);",
  '#54e8bd', """
   <g stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round">
     <path d="M4 20 H18 V34 H32"/>
     <path d="M4 44 H24 V52 H44"/>
     <path d="M32 34 V12 H52"/>
     <path d="M44 52 V40 H58"/>
   </g>
   <g fill="currentColor">
     <circle cx="18" cy="20" r="3"/><circle cx="32" cy="34" r="3.4"/>
     <circle cx="24" cy="44" r="3"/><circle cx="52" cy="12" r="3"/>
     <circle cx="44" cy="52" r="3"/>
   </g>
   <rect x="26" y="24" width="14" height="14" rx="2.5" fill="none"
         stroke="currentColor" stroke-width="2" opacity=".7"/>
  """),
 ('obsidian', 'Obsidian', 'material',
  "background:#06040e;background-image:linear-gradient(100deg,#05030c,#1e1240 60%,#050310);",
  '#b18cff', """
   <path d="M32 4 L52 26 L32 60 L12 26 Z" fill="currentColor" opacity=".85"/>
   <path d="M32 4 L32 60 L12 26 Z" fill="#06040e" opacity=".45"/>
   <path d="M32 4 L52 26 L32 34 Z" fill="#ffffff" opacity=".25"/>
   <g stroke="#ffffff" stroke-width="1.4" opacity=".35" fill="none">
     <path d="M12 26 H52 M32 34 L52 26"/>
   </g>
  """),
 ('cartography', 'Cartography', 'épica',
  "background:#0d1820;background-image:linear-gradient(100deg,#0b151c,#24414f 60%,#0a1319);",
  '#8fd4e8', """
   <circle cx="32" cy="32" r="22" fill="none" stroke="currentColor"
           stroke-width="2" opacity=".7"/>
   <path d="M32 4 L37 27 L60 32 L37 37 L32 60 L27 37 L4 32 L27 27 Z"
         fill="currentColor" opacity=".9"/>
   <path d="M32 12 L35 29 L52 32 L35 35 L32 52 L29 35 L12 32 L29 29 Z"
         fill="#0d1820" opacity=".55"/>
   <circle cx="32" cy="32" r="3.6" fill="currentColor"/>
  """),
]

PAGE = """<!doctype html><meta charset="utf-8">
<style>
 body{margin:0;font-family:'Inter',system-ui,sans-serif;background:#eef1f6;padding:22px 26px;}
 h2{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#5a6172;
    margin:20px 0 10px;grid-column:1/-1;}
 h2:first-child{margin-top:0;}
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px 26px;}
 .cap{font-size:11px;font-weight:800;color:#5a6172;margin-bottom:5px;letter-spacing:.03em;}
 .post{background:#fff;border:1px solid #e4e6ec;border-radius:12px;padding:11px 13px;}
 .top{display:flex;align-items:center;gap:8px;position:relative;}
 .plate{position:absolute;left:-8px;top:-6px;bottom:-6px;right:-8px;border-radius:9px;
        z-index:1;overflow:hidden;}
 /* El dibujo va a la DERECHA, en el espacio que queda libre después de la
    pastilla del rango. Primero lo puse a la izquierda y el avatar lo tapaba
    entero: ahí es donde está el contenido, no donde hay lugar. */
 .plate svg{position:absolute;right:4px;top:50%;transform:translateY(-50%);
            height:190%;width:auto;opacity:.92;}
 /* Y la calma va a la IZQUIERDA, encima del arte, que es donde vive el texto:
    avatar, nombre, chip y pastilla del rango siempre sobre fondo tranquilo. */
 .plate::after{content:'';position:absolute;inset:0;z-index:2;
   background:linear-gradient(90deg,rgba(6,8,13,.90) 0 46%,rgba(6,8,13,.45) 66%,transparent 92%);}
 .av{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;color:#fff;
     font-weight:800;font-size:15px;background:linear-gradient(135deg,#2563eb,#1e40af);
     flex:0 0 auto;position:relative;z-index:3;box-shadow:0 0 0 2px rgba(255,255,255,.25);}
 .medal{width:17px;height:17px;border-radius:4px;flex:0 0 auto;position:relative;z-index:3;
        background:linear-gradient(135deg,#f3c768,#a87f1f);}
 .nm{font-weight:800;font-size:13px;position:relative;z-index:3;color:#fff;
     text-shadow:0 1px 3px rgba(0,0,0,.7);}
 .chip{font-size:9.5px;font-weight:800;color:#ffb27a;background:rgba(224,117,47,.22);
       border:1px solid rgba(255,160,100,.5);border-radius:9px;padding:1px 5px;
       position:relative;z-index:3;}
 .pill{font-size:8.5px;font-weight:700;padding:2px 5px;border-radius:3px;white-space:nowrap;
       border:1px solid rgba(243,199,104,.55);color:#f3c768;position:relative;z-index:3;}
 .ttl{font-weight:800;font-size:13px;margin-top:9px;}
__PLATECSS__
</style>
<div class="grid">__BODY__</div>
"""


def build(slugs):
    sel = [p for p in PLATES if p[0] in slugs]
    css = '\n'.join('.pl-%s{%s}\n.pl-%s svg{color:%s}' % (s, bg, s, ink)
                    for s, _n, _f, bg, ink, _a in sel)
    body, fam = [], None
    for slug, name, family, _bg, _ink, art in sel:
        if family != fam:
            fam = family
            body.append('<h2>%s</h2>' % family)
        body.append(
            '<div><div class="cap">%s</div>'
            '<div class="post"><div class="top">'
            '<div class="plate pl-%s"><svg viewBox="0 0 64 64">%s</svg></div>'
            '<div class="av">M</div><span class="medal"></span>'
            '<span class="nm">marcus_dw</span><span class="chip">🔥12</span>'
            '<span class="pill">Trading Legend</span></div>'
            '<div class="ttl">Sweep del PDL y reclaim</div></div></div>'
            % (name, slug, art))
    return PAGE.replace('__PLATECSS__', css).replace('__BODY__', '\n'.join(body))


def shoot(slugs):
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False) as fh:
        fh.write(build(slugs))
        path = fh.name
    script = f'''
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path={CHROME!r})
    pg = b.new_page(viewport={{'width': 1180, 'height': 500}}, device_scale_factor=1.6)
    pg.goto('file://{path}')
    pg.wait_for_timeout(500)
    pg.screenshot(path={OUT!r}, full_page=True)
    b.close()
'''
    subprocess.run([sys.executable, '-c', script], check=True)
    os.unlink(path)
    print('captura →', OUT, '(%d placas)' % len(slugs))


if __name__ == '__main__':
    todos = [p[0] for p in PLATES]
    pedidos = sys.argv[1:] or todos
    malos = [s for s in pedidos if s not in todos]
    if malos:
        print('no existen:', malos)
        sys.exit(1)
    shoot(set(pedidos))
