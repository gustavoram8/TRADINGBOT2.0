# -*- coding: utf-8 -*-
"""Catálogo de MARCOS (placas del bloque de autor) para elegir temáticas.

Un marco es una placa rectangular que va DETRÁS del bloque del autor en el
foro: avatar + medalla del rango + nombre + chip de racha + pastilla. Se eligió
esta forma sobre el aro alrededor del avatar porque el aro no se puede
presumir: nadie paga por decorar el borde de un círculo de 40px.

REGLA ESTRUCTURAL (aplicada a todas por igual, ver .plate::after):
el arte vive a la IZQUIERDA y la placa se apaga hacia la DERECHA. La medalla y
la pastilla del rango caen siempre sobre fondo calmado, así que la placa nunca
se come al rango — que es la condición innegociable del dueño.

    python3 tools/plates_preview.py            # todas
    python3 tools/plates_preview.py tape runes # algunas
"""
import os
import subprocess
import sys
import tempfile

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
OUT = os.environ.get('PLATES_OUT', '/tmp/plates_preview.png')

# (slug, nombre visible, familia, CSS de fondo)
PLATES = [
 # ── El lenguaje propio de la marca ──────────────────────────────────────
 ('tape', 'Tape Reader', 'mercado',
  "background:#0b1a2e;background-image:repeating-linear-gradient(90deg,rgba(120,200,255,.30) 0 2px,transparent 2px 11px),linear-gradient(100deg,#081525,#14395e 55%,#081525);"),
 ('orderflow', 'Order Flow', 'mercado',
  "background:#08201f;background-image:repeating-linear-gradient(0deg,rgba(60,220,190,.30) 0 2px,transparent 2px 7px),linear-gradient(100deg,#06201d,#0d443c 55%,#06201d);"),
 ('liquidity', 'Liquidity Pool', 'mercado',
  "background:#04202c;background-image:radial-gradient(ellipse 70px 16px at 22% 60%,rgba(90,215,255,.35),transparent 70%),radial-gradient(ellipse 50px 12px at 38% 35%,rgba(90,215,255,.22),transparent 70%),linear-gradient(100deg,#03151d,#0a4058 60%,#03151d);"),
 ('candlegrid', 'Candle Grid', 'mercado',
  "background:#0d1420;background-image:repeating-linear-gradient(0deg,rgba(255,255,255,.06) 0 1px,transparent 1px 11px),repeating-linear-gradient(90deg,rgba(255,255,255,.06) 0 1px,transparent 1px 15px),linear-gradient(100deg,#0b1119,#1b2b42 55%,#0b1119);"),
 ('volume', 'Volume Profile', 'mercado',
  "background:#111722;background-image:repeating-linear-gradient(0deg,rgba(120,170,255,.34) 0 4px,transparent 4px 9px),linear-gradient(90deg,rgba(120,170,255,.16),transparent 46%),linear-gradient(100deg,#0d131c,#243349 60%,#0d131c);"),
 ('session', 'Kill Zone', 'mercado',
  "background:#0a1526;background-image:linear-gradient(90deg,transparent 6%,rgba(90,160,255,.30) 6% 14%,transparent 14% 26%,rgba(90,160,255,.22) 26% 32%,transparent 32%),linear-gradient(100deg,#08111f,#16294a 55%,#08111f);"),
 ('bullrun', 'Bull Run', 'mercado',
  "background:#062016;background-image:repeating-linear-gradient(58deg,rgba(70,225,150,.26) 0 3px,transparent 3px 14px),linear-gradient(100deg,#04170f,#0c4a30 58%,#04170f);"),
 ('bearcave', 'Bear Cave', 'mercado',
  "background:#1c0a10;background-image:repeating-linear-gradient(-58deg,rgba(230,80,110,.22) 0 3px,transparent 3px 15px),linear-gradient(100deg,#150710,#4a1020 58%,#150710);"),
 ('blueprint', 'Blueprint', 'mercado',
  "background:#0a2f5e;background-image:repeating-linear-gradient(0deg,rgba(255,255,255,.20) 0 1px,transparent 1px 9px),repeating-linear-gradient(90deg,rgba(255,255,255,.20) 0 1px,transparent 1px 9px),linear-gradient(100deg,#07234a,#0f4a8f 60%,#07234a);"),
 ('terminal', 'Terminal', 'mercado',
  "background:#03120a;background-image:repeating-linear-gradient(0deg,rgba(60,255,140,.18) 0 1px,transparent 1px 4px),linear-gradient(100deg,#020d07,#07351c 58%,#020d07);"),

 # ── Materiales ──────────────────────────────────────────────────────────
 ('carbon', 'Carbon Fiber', 'material',
  "background:#14161c;background-image:repeating-linear-gradient(45deg,#1e222b 0 5px,#0f1116 5px 10px),repeating-linear-gradient(-45deg,rgba(255,255,255,.05) 0 5px,transparent 5px 10px);"),
 ('steel', 'Brushed Steel', 'material',
  "background:#4b5361;background-image:repeating-linear-gradient(102deg,rgba(255,255,255,.11) 0 2px,transparent 2px 5px),linear-gradient(100deg,#39404c,#8993a3 55%,#39404c);"),
 ('obsidian', 'Obsidian', 'material',
  "background:#0a0810;background-image:linear-gradient(112deg,transparent 30%,rgba(150,110,255,.30) 48%,transparent 62%),linear-gradient(100deg,#070510,#1a1030 58%,#070510);"),
 ('concrete', 'Brutalist', 'material',
  "background:#3a3d42;background-image:linear-gradient(90deg,transparent 33%,rgba(0,0,0,.35) 33% 34%,transparent 34%),radial-gradient(circle at 20% 40%,rgba(255,255,255,.10),transparent 40%),linear-gradient(100deg,#2f3237,#575c64 58%,#2f3237);"),
 ('copper', 'Copper Patina', 'material',
  "background:#0d3630;background-image:radial-gradient(ellipse 40px 20px at 18% 30%,rgba(90,215,180,.40),transparent 65%),radial-gradient(ellipse 34px 16px at 34% 70%,rgba(190,120,80,.35),transparent 65%),linear-gradient(100deg,#0a2a26,#155048 58%,#0a2a26);"),
 ('damascus', 'Damascus', 'material',
  "background:#2a2f38;background-image:repeating-radial-gradient(ellipse 60px 14px at 20% 50%,rgba(255,255,255,.16) 0 3px,transparent 3px 8px),linear-gradient(100deg,#20242c,#4a525f 58%,#20242c);"),
 ('circuit', 'Circuit', 'material',
  "background:#06120f;background-image:linear-gradient(90deg,transparent 10%,rgba(70,230,180,.5) 10% 10.5%,transparent 10.5% 22%,rgba(70,230,180,.5) 22% 22.5%,transparent 22.5%),repeating-linear-gradient(0deg,rgba(70,230,180,.16) 0 1px,transparent 1px 12px),linear-gradient(100deg,#040d0b,#0a2f26 58%,#040d0b);"),

 # ── Naturaleza / elemental (sin fuego: el fuego es del salón de la fama) ─
 ('abyss', 'Abyss', 'natural',
  "background:#03101f;background-image:linear-gradient(76deg,rgba(120,200,255,.22) 0 4px,transparent 4px 26px),linear-gradient(100deg,#020a14,#0a2b4d 58%,#020a14);"),
 ('glacier', 'Glacier', 'natural',
  "background:#12384d;background-image:linear-gradient(62deg,transparent 40%,rgba(220,250,255,.45) 41% 42%,transparent 43%),linear-gradient(-48deg,transparent 55%,rgba(220,250,255,.30) 56% 57%,transparent 58%),linear-gradient(100deg,#0d2b3c,#2a6f8f 58%,#0d2b3c);"),
 ('aurora', 'Aurora', 'natural',
  "background:#050b1a;background-image:radial-gradient(ellipse 60px 34px at 20% 90%,rgba(70,230,170,.45),transparent 70%),radial-gradient(ellipse 50px 30px at 34% 100%,rgba(150,110,255,.40),transparent 70%),linear-gradient(100deg,#04091a,#0a1738 60%,#04091a);"),
 ('storm', 'Storm', 'natural',
  "background:#141a24;background-image:linear-gradient(72deg,transparent 44%,rgba(210,235,255,.75) 45% 46%,transparent 47%),radial-gradient(ellipse 60px 26px at 24% 20%,rgba(255,255,255,.13),transparent 70%),linear-gradient(100deg,#0e131b,#2b3543 58%,#0e131b);"),
 ('jungle', 'Jungle', 'natural',
  "background:#07230f;background-image:radial-gradient(ellipse 30px 14px at 14% 30%,rgba(90,200,110,.40),transparent 68%),radial-gradient(ellipse 26px 12px at 28% 72%,rgba(50,150,80,.45),transparent 68%),linear-gradient(100deg,#051a0c,#0d4a20 58%,#051a0c);"),
 ('dunes', 'Desert Night', 'natural',
  "background:#0a0f26;background-image:radial-gradient(circle at 16% 26%,rgba(255,255,255,.85) 0 1px,transparent 2px),radial-gradient(circle at 30% 16%,rgba(255,255,255,.7) 0 1px,transparent 2px),radial-gradient(ellipse 90px 26px at 26% 130%,rgba(120,100,180,.55),transparent 70%),linear-gradient(100deg,#070a1c,#181f45 60%,#070a1c);"),
 ('ash', 'Ashfall', 'natural',
  "background:#1a1a1d;background-image:radial-gradient(circle at 14% 30%,rgba(220,220,225,.6) 0 1px,transparent 2px),radial-gradient(circle at 26% 66%,rgba(200,200,210,.5) 0 1px,transparent 2px),radial-gradient(circle at 36% 24%,rgba(230,230,235,.45) 0 1px,transparent 2px),linear-gradient(100deg,#131316,#333338 58%,#131316);"),
 ('nebula', 'Nebula', 'natural',
  "background:#0a0618;background-image:radial-gradient(ellipse 56px 26px at 20% 45%,rgba(190,90,220,.45),transparent 70%),radial-gradient(ellipse 44px 22px at 34% 70%,rgba(90,130,255,.40),transparent 70%),linear-gradient(100deg,#070412,#1c0f3a 60%,#070412);"),

 # ── Épicas / culturales ─────────────────────────────────────────────────
 ('chronicles', 'Chronicles', 'épica',
  "background:#1a0a10;background-image:repeating-radial-gradient(circle at 18% 50%,rgba(200,60,70,.30) 0 4px,transparent 4px 9px),linear-gradient(90deg,transparent 28%,rgba(230,190,140,.22) 28% 29%,transparent 29%),linear-gradient(100deg,#12070c,#4a1320 58%,#12070c);"),
 ('samurai', 'Samurai', 'épica',
  "background:#101a34;background-image:radial-gradient(circle 20px at 22% 50%,rgba(220,60,60,.75),transparent 72%),repeating-linear-gradient(0deg,rgba(255,255,255,.05) 0 1px,transparent 1px 6px),linear-gradient(100deg,#0b1226,#1e2f57 58%,#0b1226);"),
 ('cartography', 'Cartography', 'épica',
  "background:#16232c;background-image:radial-gradient(ellipse 44px 20px at 22% 50%,transparent 60%,rgba(150,200,220,.35) 61% 63%,transparent 64%),linear-gradient(38deg,transparent 46%,rgba(150,200,220,.30) 47% 48%,transparent 49%),linear-gradient(100deg,#101a22,#26404f 58%,#101a22);"),
 ('runes', 'Runestone', 'épica',
  "background:#1c1e22;background-image:linear-gradient(90deg,transparent 12%,rgba(90,220,255,.55) 12% 12.6%,transparent 12.6% 20%,rgba(90,220,255,.4) 20% 20.6%,transparent 20.6% 30%,rgba(90,220,255,.5) 30% 30.6%,transparent 30.6%),linear-gradient(100deg,#141518,#34383f 58%,#141518);"),
 ('cathedral', 'Cathedral', 'épica',
  "background:#0b1030;background-image:linear-gradient(90deg,rgba(90,60,200,.55) 0 8%,rgba(20,20,20,.6) 8% 9%,rgba(50,120,200,.5) 9% 18%,rgba(20,20,20,.6) 18% 19%,rgba(140,60,160,.5) 19% 28%,rgba(20,20,20,.6) 28% 29%,transparent 29%),linear-gradient(100deg,#080c26,#161d4d 60%,#080c26);"),

 # ── Festivas (pocas, a pedido) ──────────────────────────────────────────
 ('frost', 'Winter Frost', 'festiva',
  "background:#0e2a3d;background-image:radial-gradient(circle at 15% 34%,rgba(255,255,255,.85) 0 1.5px,transparent 3px),radial-gradient(circle at 27% 66%,rgba(230,250,255,.7) 0 1.5px,transparent 3px),linear-gradient(56deg,transparent 44%,rgba(220,250,255,.35) 45% 46%,transparent 47%),linear-gradient(100deg,#0a1f2e,#1d5878 58%,#0a1f2e);"),
 ('muertos', 'Marigold Night', 'festiva',
  "background:#1d0d2e;background-image:radial-gradient(circle 9px at 17% 40%,rgba(255,160,50,.75),transparent 72%),radial-gradient(circle 7px at 29% 68%,rgba(255,190,80,.6),transparent 72%),linear-gradient(100deg,#150922,#3d1a5c 58%,#150922);"),
]

PAGE = """<!doctype html><meta charset="utf-8">
<style>
 body{margin:0;font-family:'Inter',system-ui,sans-serif;background:#eef1f6;padding:22px 26px;}
 h2{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#5a6172;
    margin:20px 0 10px;grid-column:1/-1;}
 h2:first-child{margin-top:0;}
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px 26px;}
 .item{}
 .cap{font-size:11px;font-weight:800;color:#5a6172;margin-bottom:5px;letter-spacing:.03em;}
 .post{background:#fff;border:1px solid #e4e6ec;border-radius:12px;padding:11px 13px;}
 .top{display:flex;align-items:center;gap:8px;position:relative;}
 .plate{position:absolute;left:-8px;top:-6px;bottom:-6px;right:-8px;border-radius:9px;z-index:1;
        overflow:hidden;}
 /* La regla estructural: el arte a la izquierda, calma a la derecha, para que
    la medalla y la pastilla del rango nunca peleen contra el fondo. */
 .plate::after{content:'';position:absolute;inset:0;
   background:linear-gradient(90deg,transparent 0 42%,rgba(8,10,16,.55) 66%,rgba(8,10,16,.86) 84%);}
 .av{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;color:#fff;
     font-weight:800;font-size:15px;background:linear-gradient(135deg,#2563eb,#1e40af);
     flex:0 0 auto;position:relative;z-index:3;box-shadow:0 0 0 2px rgba(255,255,255,.22);}
 .medal{width:17px;height:17px;border-radius:4px;flex:0 0 auto;position:relative;z-index:3;
        background:linear-gradient(135deg,#f3c768,#a87f1f);}
 .nm{font-weight:800;font-size:13px;position:relative;z-index:3;color:#fff;
     text-shadow:0 1px 2px rgba(0,0,0,.5);}
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
    css = '\n'.join('.pl-%s{%s}' % (s, c) for s, _n, _f, c in sel)
    body, fam = [], None
    for slug, name, family, _c in sel:
        if family != fam:
            fam = family
            body.append('<h2>%s</h2>' % family)
        body.append(
            '<div class="item"><div class="cap">%s</div>'
            '<div class="post"><div class="top">'
            '<div class="plate pl-%s"></div>'
            '<div class="av">M</div><span class="medal"></span>'
            '<span class="nm">marcus_dw</span><span class="chip">🔥12</span>'
            '<span class="pill">Trading Legend</span></div>'
            '<div class="ttl">Sweep del PDL y reclaim</div></div></div>'
            % (name, slug))
    return PAGE.replace('__PLATECSS__', css).replace('__BODY__', '\n'.join(body))


def shoot(slugs):
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False) as fh:
        fh.write(build(slugs))
        path = fh.name
    script = f'''
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path={CHROME!r})
    pg = b.new_page(viewport={{'width': 1180, 'height': 500}}, device_scale_factor=1.5)
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
