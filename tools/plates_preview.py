# -*- coding: utf-8 -*-
"""Catálogo de MARCOS (placas del bloque de autor).

Un marco es una placa rectangular que va DETRÁS del bloque del autor en el
foro: avatar + medalla del rango + nombre + chip de racha + pastilla.

TRES REGLAS, todas aprendidas a los golpes:

1. La placa es una ESCENA QUE OCUPA TODO EL ANCHO, no un ícono pegado a un
   lado. La segunda tanda dibujaba un motivo de 64×64 en una esquina y se
   veía como un sticker; el lienzo real es 420×56 y hay que usarlo entero.
2. Los fondos NO son todos oscuros. Cada temática trae su propia paleta, y
   varias son claras. Cada placa declara el color de su TEXTO (`ink`) porque
   sobre una placa clara el nombre tiene que ser oscuro.
3. La composición deja el TERCIO IZQUIERDO tranquilo — cielo, arena, vacío —
   en vez de taparlo con un degradado. Ahí caen el avatar y el nombre. Así el
   arte se ve entero y el rango nunca pelea contra el fondo.

    python3 tools/plates_preview.py               # todas
    python3 tools/plates_preview.py chronicles    # algunas
"""
import os
import subprocess
import sys
import tempfile

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
OUT = os.environ.get('PLATES_OUT', '/tmp/plates_preview.png')

# Lienzo de la escena: 420 × 56. Se dibuja completa y se escala a la placa.
# (slug, nombre, familia, ink 'light'|'dark', escena SVG)
PLATES = [
 ('chronicles', 'Chronicles', 'épica', 'light', """
  <defs><linearGradient id="ch-sky" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#140508"/><stop offset=".5" stop-color="#2c0910"/>
    <stop offset="1" stop-color="#611510"/></linearGradient></defs>
  <rect width="420" height="56" fill="url(#ch-sky)"/>

  <!-- CASTILLO: muralla almenada + dos torres con techo cónico + portón.
       Antes eran tres rectángulos y se leían como edificios de oficina. -->
  <g fill="#0b0305">
    <path d="M318 56 V40 h5 v-4 h5 v4 h5 v-4 h5 v4 h5 v-4 h5 v4 h5 v-4 h5 v4 h5 v-4 h5 v4 h5 V56 Z"/>
    <rect x="312" y="30" width="18" height="26"/>
    <path d="M311 30 L321 16 L331 30 Z"/>
    <rect x="378" y="26" width="20" height="30"/>
    <path d="M377 26 L388 10 L399 26 Z"/>
    <path d="M348 56 V46 a7 7 0 0 1 14 0 V56 Z"/>
  </g>
  <g fill="#ff8a3c" opacity=".9">
    <rect x="318" y="36" width="4" height="5"/><rect x="384" y="32" width="5" height="6"/>
    <rect x="352" y="49" width="6" height="7"/>
  </g>

  <!-- CABEZA DE DRAGÓN saliendo de la penumbra. Un dragón entero a 56px de
       alto no se lee (se leía como un pájaro): la cabeza sí, porque el hocico,
       el cuerno y las fauces son siluetas inconfundibles a cualquier tamaño. -->
  <g fill="#1e0709" stroke="#ff7a2e" stroke-width="1.2" stroke-linejoin="round">
    <path d="M214 30 C224 22 244 16 266 16 C288 16 306 20 318 26
             C324 29 330 30 336 29 L340 36 C330 40 316 42 300 42
             C280 42 246 40 214 30 Z"/>
    <path d="M226 36 C240 42 262 47 286 48 C300 48.5 312 47 320 45
             L318 39 C306 41 292 42 278 41 C258 40 240 38 226 36 Z"/>
    <path d="M300 20 C312 8 330 2 350 2 C338 8 330 14 326 22 Z"/>
    <path d="M282 15 C292 6 306 2 318 2 C308 7 300 12 296 18 Z" opacity=".85"/>
    <path d="M240 30 L236 24 L246 27 Z M256 33 L252 27 L262 30 Z
             M272 35 L268 29 L278 32 Z"/>
    <path d="M244 38 L248 44 L238 41 Z M262 41 L266 47 L256 44 Z"/>
  </g>
  <circle cx="300" cy="27" r="3.4" fill="#ffb347"/>
  <ellipse cx="300" cy="27" rx="1.1" ry="3" fill="#1e0709"/>
  <ellipse cx="234" cy="28" rx="2.6" ry="1.8" fill="#ff7a2e" opacity=".8"/>
  <!-- aliento de fuego saliendo del hocico hacia la izquierda -->
  <g fill="#ff5a1e" opacity=".8">
    <path d="M212 32 C198 28 182 30 168 36 C182 34 196 34 210 37 Z"/>
    <path d="M204 27 C190 22 172 22 158 26 C174 26 190 28 202 32 Z" opacity=".6"/>
  </g>

  <!-- grietas de lava a lo ancho -->
  <g stroke="#ff5a1e" stroke-linecap="round" fill="none">
    <path d="M0 48 L34 43 L60 50 L100 41 L146 48 L190 39 L238 47 L286 38 L332 46 L380 37 L420 44"
          stroke-width="2.6" opacity=".95"/>
    <path d="M60 50 L68 56 M146 48 L138 56 M238 47 L246 56"
          stroke-width="1.8" opacity=".8"/>
  </g>
  <g stroke="#ffd08a" stroke-width="1" fill="none" opacity=".5">
    <path d="M0 48 L34 43 L60 50 L100 41 L146 48 L190 39 L238 47 L286 38 L332 46 L380 37 L420 44"/>
  </g>
  <g fill="#ff8a3c" opacity=".65">
    <circle cx="112" cy="26" r="1.3"/><circle cx="160" cy="18" r="1"/>
    <circle cx="200" cy="28" r="1.2"/><circle cx="86" cy="34" r="1"/>
  </g>
 """),
 ('arcade', 'Insert Coin', 'retro', 'light', """
  <defs><linearGradient id="ar-bg" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#100425"/><stop offset=".5" stop-color="#2a0846"/>
    <stop offset="1" stop-color="#4a0d5e"/></linearGradient></defs>
  <rect width="420" height="56" fill="url(#ar-bg)"/>
  <!-- rejilla en perspectiva -->
  <g stroke="#ff2e97" stroke-width="1" opacity=".45">
    <path d="M0 44 H420 M0 50 H420"/>
    <path d="M20 44 L0 56 M80 44 L64 56 M140 44 L130 56 M200 44 L196 56
             M260 44 L262 56 M320 44 L328 56 M380 44 L394 56"/>
  </g>
  <!-- maquinita de arcade, al centro -->
  <g transform="translate(196,4)">
    <rect x="0" y="4" width="34" height="48" rx="4" fill="#1a0730"
          stroke="#00e5ff" stroke-width="1.6"/>
    <rect x="4" y="9" width="26" height="15" rx="2" fill="#03121c"
          stroke="#00e5ff" stroke-width="1"/>
    <g fill="#ffe066"><rect x="8" y="19" width="3" height="3"/>
      <rect x="14" y="16" width="3" height="3"/><rect x="22" y="13" width="3" height="3"/></g>
    <rect x="6" y="28" width="22" height="7" rx="2" fill="#2b0d4a"/>
    <circle cx="12" cy="31.5" r="2.2" fill="#ff2e97"/>
    <circle cx="20" cy="31.5" r="1.8" fill="#00e5ff"/>
    <rect x="8" y="39" width="18" height="9" rx="1.5" fill="#12052a"/>
  </g>
  <!-- píxeles / naves invasoras a los lados -->
  <g fill="#00e5ff" opacity=".85">
    <path d="M96 14 h4 v4 h-4 Z M104 10 h4 v4 h-4 Z M112 14 h4 v4 h-4 Z M104 18 h4 v4 h-4 Z"/>
    <path d="M300 20 h4 v4 h-4 Z M308 16 h4 v4 h-4 Z M316 20 h4 v4 h-4 Z M308 24 h4 v4 h-4 Z"/>
  </g>
  <g fill="#ffe066" opacity=".8">
    <rect x="352" y="12" width="5" height="5"/><rect x="364" y="20" width="4" height="4"/>
    <rect x="380" y="10" width="4" height="4"/><rect x="392" y="24" width="5" height="5"/>
  </g>
 """),

 ('mars', 'Red Planet', 'natural', 'dark', """
  <defs>
    <linearGradient id="ma-sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#f0cdb2"/>
    </linearGradient>
  </defs>
  <rect width="420" height="56" fill="url(#ma-sky)"/>
  <!-- destellos de 4 puntas, como en el camo Mission -->
  <g fill="#ffffff" opacity=".9">
    <path d="M64 12 l1.4 4 4 1.4 -4 1.4 -1.4 4 -1.4-4 -4-1.4 4-1.4 Z"/>
    <path d="M188 8 l1 3 3 1 -3 1 -1 3 -1-3 -3-1 3-1 Z"/>
    <path d="M330 14 l1.2 3.5 3.5 1.2 -3.5 1.2 -1.2 3.5 -1.2-3.5 -3.5-1.2 3.5-1.2 Z"/>
  </g>
  <circle cx="286" cy="16" r="9" fill="#f6a97a" opacity=".55"/>
  <!-- cordilleras superpuestas, como el camo de Marte -->
  <path d="M0 40 L46 26 L84 38 L128 22 L176 36 L226 24 L272 37 L320 25 L366 38 L420 28 L420 56 L0 56 Z"
        fill="#c96a4a" opacity=".55"/>
  <path d="M0 46 L40 34 L88 45 L138 32 L186 44 L236 33 L288 45 L338 34 L390 45 L420 38 L420 56 L0 56 Z"
        fill="#a64f30" opacity=".8"/>
  <path d="M0 52 L54 43 L110 52 L166 42 L222 52 L280 43 L338 52 L396 44 L420 48 L420 56 L0 56 Z"
        fill="#7d3520"/>
  <!-- cañón en primer plano -->
  <path d="M0 56 L0 50 L34 56 Z M420 56 L420 48 L382 56 Z" fill="#5e2415"/>
 """),

 ('washi', 'Rising Sun', 'épica', 'dark', """
  <rect width="420" height="56" fill="#f7f2e7"/>
  <rect width="420" height="56" fill="none"/>
  <g opacity=".5" stroke="#d8cdb6" stroke-width="1">
    <path d="M0 14 H420 M0 30 H420 M0 46 H420"/>
  </g>
  <circle cx="268" cy="26" r="19" fill="#c2352b" opacity=".9"/>
  <!-- montañas de tinta -->
  <path d="M300 56 L340 24 L368 44 L392 30 L420 56 Z" fill="#2f3640" opacity=".8"/>
  <path d="M180 56 L214 30 L242 48 L262 38 L286 56 Z" fill="#4a5462" opacity=".6"/>
  <!-- bambú -->
  <g stroke="#3f5a44" stroke-width="3" stroke-linecap="round" opacity=".75">
    <path d="M126 56 V18 M138 56 V28"/>
  </g>
  <g stroke="#3f5a44" stroke-width="2" fill="none" opacity=".7">
    <path d="M126 24 C118 20 112 22 108 26 M126 34 C134 30 140 32 144 36
             M138 34 C146 31 150 33 153 37"/>
  </g>
  <g stroke="#a8a08c" stroke-width="1" opacity=".55">
    <path d="M126 22 H127 M126 32 H127 M126 42 H127"/>
  </g>
 """),

 ('glacier', 'Glacier', 'natural', 'dark', """
  <defs><linearGradient id="gl-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#eaf7ff"/><stop offset="1" stop-color="#b9e2f4"/>
  </linearGradient></defs>
  <rect width="420" height="56" fill="url(#gl-sky)"/>
  <!-- picos de hielo cruzando -->
  <path d="M0 56 L38 30 L64 44 L104 18 L146 42 L190 26 L232 46 L276 22 L318 44 L362 28 L400 46 L420 36 L420 56 Z"
        fill="#7fc4e0" opacity=".75"/>
  <path d="M0 56 L44 40 L92 52 L140 34 L188 50 L238 36 L288 52 L336 38 L386 52 L420 46 L420 56 Z"
        fill="#4d9cc0"/>
  <!-- grietas -->
  <g stroke="#ffffff" stroke-width="1.4" opacity=".8" fill="none">
    <path d="M104 18 L112 34 L106 44 M276 22 L284 36 L278 48 M190 26 L196 40"/>
  </g>
  <g fill="#ffffff" opacity=".75">
    <circle cx="150" cy="12" r="1.6"/><circle cx="248" cy="9" r="1.2"/>
    <circle cx="344" cy="14" r="1.4"/>
  </g>
 """),

 ('abyss', 'Abyss', 'natural', 'light', """
  <defs><linearGradient id="ab-w" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0a3355"/><stop offset="1" stop-color="#010810"/>
  </linearGradient></defs>
  <rect width="420" height="56" fill="url(#ab-w)"/>
  <!-- haces de luz desde arriba -->
  <g fill="#9fd8ff" opacity=".16">
    <path d="M60 0 L86 0 L58 56 L38 56 Z"/><path d="M150 0 L168 0 L146 56 L132 56 Z"/>
    <path d="M300 0 L322 0 L298 56 L280 56 Z"/>
  </g>
  <!-- ballena cruzando la escena -->
  <g fill="#6fb6e8" opacity=".92">
    <path d="M150 34 C176 20 224 18 268 26 C286 29 300 34 312 40
             C296 44 268 46 236 44 C202 42 170 40 150 34 Z"/>
    <path d="M312 40 C322 34 332 26 340 16 C342 28 340 38 336 46
             C332 44 320 43 312 40 Z"/>
    <path d="M212 42 C216 50 224 54 232 55 C222 55 210 50 204 44 Z"/>
    <path d="M168 28 C166 20 170 14 176 10 C176 18 174 24 172 29 Z" opacity=".8"/>
  </g>
  <circle cx="166" cy="31" r="1.8" fill="#021018"/>
  <g fill="#bfe6ff" opacity=".7">
    <circle cx="120" cy="18" r="2.4"/><circle cx="106" cy="10" r="1.6"/>
    <circle cx="132" cy="8" r="1.2"/><circle cx="372" cy="22" r="2"/>
    <circle cx="388" cy="14" r="1.4"/>
  </g>
 """),

 ('bullrun', 'Bull Run', 'mercado', 'dark', """
  <rect width="420" height="56" fill="#eef8f1"/>
  <g stroke="#c9e4d2" stroke-width="1">
    <path d="M0 14 H420 M0 28 H420 M0 42 H420"/>
  </g>
  <!-- velas verdes subiendo a lo ancho -->
  <g fill="#1f9d55">
    <g><rect x="112" y="34" width="7" height="12" rx="1"/><rect x="114.6" y="28" width="1.8" height="24"/></g>
    <g><rect x="132" y="28" width="7" height="14" rx="1"/><rect x="134.6" y="22" width="1.8" height="26"/></g>
    <g><rect x="152" y="24" width="7" height="12" rx="1"/><rect x="154.6" y="18" width="1.8" height="24"/></g>
    <g><rect x="172" y="18" width="7" height="14" rx="1"/><rect x="174.6" y="12" width="1.8" height="26"/></g>
    <g><rect x="192" y="14" width="7" height="11" rx="1"/><rect x="194.6" y="8" width="1.8" height="23"/></g>
  </g>
  <!-- línea de tendencia -->
  <path d="M100 48 L140 38 L180 28 L220 16 L250 10" stroke="#1f9d55"
        stroke-width="2" fill="none" stroke-linecap="round" opacity=".55"/>
  <!-- toro embistiendo, a la derecha -->
  <g fill="#134e33">
    <path d="M300 22 C290 17 288 8 292 4 C300 11 310 15 316 16 L316 24 Z"/>
    <path d="M368 22 C378 17 380 8 376 4 C368 11 358 15 352 16 L352 24 Z"/>
    <path d="M316 15 C316 15 324 12 334 12 C344 12 352 15 352 15 L352 32
             C352 46 344 54 334 54 C324 54 316 46 316 32 Z"/>
    <path d="M400 46 C392 42 386 44 382 48" stroke="#134e33" stroke-width="3"
          fill="none" stroke-linecap="round"/>
  </g>
  <g fill="#eef8f1"><circle cx="326" cy="28" r="2.6"/><circle cx="342" cy="28" r="2.6"/></g>
 """),

 ('terminal', 'Terminal', 'mercado', 'light', """
  <rect width="420" height="56" fill="#04120b"/>
  <g stroke="#0d3a22" stroke-width="1" opacity=".9">
    <path d="M0 8 H420 M0 16 H420 M0 24 H420 M0 32 H420 M0 40 H420 M0 48 H420"/>
  </g>
  <g font-family="monospace" font-size="9" fill="#3ef58e" opacity=".85">
    <text x="150" y="14">&gt; scan --session=london</text>
    <text x="150" y="26">  sweep detected @ PDL</text>
    <text x="150" y="38">  displacement: TRUE</text>
    <text x="150" y="50">&gt; _</text>
  </g>
  <rect x="196" y="43" width="6" height="9" fill="#3ef58e" opacity=".9"/>
  <g stroke="#3ef58e" stroke-width="1.6" fill="none" opacity=".55">
    <path d="M330 44 L346 30 L358 36 L374 18 L390 26 L406 12"/>
  </g>
  <g fill="#3ef58e" opacity=".5">
    <circle cx="346" cy="30" r="2"/><circle cx="374" cy="18" r="2"/><circle cx="406" cy="12" r="2"/>
  </g>
 """),

 ('dunes', 'Desert Night', 'natural', 'light', """
  <defs><linearGradient id="du-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0a0c22"/><stop offset="1" stop-color="#2a2050"/>
  </linearGradient></defs>
  <rect width="420" height="56" fill="url(#du-sky)"/>
  <circle cx="300" cy="16" r="10" fill="#f0ead8"/>
  <circle cx="295" cy="13" r="9" fill="#0d0f26"/>
  <g fill="#ffffff" opacity=".85">
    <circle cx="120" cy="10" r="1.3"/><circle cx="168" cy="18" r="1"/>
    <circle cx="212" cy="8" r="1.2"/><circle cx="352" cy="12" r="1.1"/>
    <circle cx="386" cy="22" r="1.3"/><circle cx="252" cy="20" r="0.9"/>
  </g>
  <path d="M0 56 C60 38 120 50 180 40 C240 30 300 46 360 36 C390 31 406 34 420 32 L420 56 Z"
        fill="#5b4a86" opacity=".65"/>
  <path d="M0 56 C70 46 140 56 210 46 C280 36 340 52 420 42 L420 56 Z"
        fill="#3b2f60"/>
  <!-- caravana -->
  <g fill="#181233">
    <path d="M236 44 C238 40 242 39 244 41 C246 38 250 38 251 42 L253 48 L249 48 L248 45 L242 45 L241 48 L237 48 Z"/>
    <path d="M262 45 C263 42 266 41 268 43 C270 41 273 41 274 44 L275 48 L272 48 L271 46 L266 46 L265 48 L262 48 Z"/>
  </g>
 """),

 ('cathedral', 'Cathedral', 'épica', 'light', """
  <rect width="420" height="56" fill="#0a0e2a"/>
  <!-- vitrales a lo ancho -->
  <g opacity=".92">
    <path d="M96 56 V24 C96 14 104 8 112 8 C120 8 128 14 128 24 V56 Z" fill="#3b5bd6"/>
    <path d="M136 56 V18 C136 6 146 0 156 0 C166 0 176 6 176 18 V56 Z" fill="#8f3bc9"/>
    <path d="M184 56 V24 C184 14 192 8 200 8 C208 8 216 14 216 24 V56 Z" fill="#2c8fb8"/>
    <path d="M224 56 V18 C224 6 234 0 244 0 C254 0 264 6 264 18 V56 Z" fill="#c93b6e"/>
    <path d="M272 56 V24 C272 14 280 8 288 8 C296 8 304 14 304 24 V56 Z" fill="#3b8f5e"/>
    <path d="M312 56 V18 C312 6 322 0 332 0 C342 0 352 6 352 18 V56 Z" fill="#5b3bc9"/>
  </g>
  <!-- plomos -->
  <g stroke="#05061a" stroke-width="3" fill="none" opacity=".85">
    <path d="M112 8 V56 M156 0 V56 M200 8 V56 M244 0 V56 M288 8 V56 M332 0 V56"/>
    <path d="M96 30 H128 M136 24 H176 M184 30 H216 M224 24 H264 M272 30 H304 M312 24 H352"/>
  </g>
  <g stroke="#05061a" stroke-width="4" fill="none">
    <path d="M96 56 V24 C96 14 104 8 112 8 C120 8 128 14 128 24 V56"/>
    <path d="M136 56 V18 C136 6 146 0 156 0 C166 0 176 6 176 18 V56"/>
    <path d="M184 56 V24 C184 14 192 8 200 8 C208 8 216 14 216 24 V56"/>
    <path d="M224 56 V18 C224 6 234 0 244 0 C254 0 264 6 264 18 V56"/>
    <path d="M272 56 V24 C272 14 280 8 288 8 C296 8 304 14 304 24 V56"/>
    <path d="M312 56 V18 C312 6 322 0 332 0 C342 0 352 6 352 18 V56"/>
  </g>
 """),
]

PAGE = """<!doctype html><meta charset="utf-8">
<style>
 body{margin:0;font-family:'Inter',system-ui,sans-serif;background:#eef1f6;padding:22px 26px;}
 .cap{font-size:11.5px;font-weight:800;color:#5a6172;margin-bottom:5px;letter-spacing:.03em;}
 .cap span{font-weight:600;opacity:.7;}
 .post{background:#fff;border:1px solid #e4e6ec;border-radius:12px;padding:11px 13px;
       margin-bottom:14px;}
 .top{display:flex;align-items:center;gap:8px;position:relative;}
 .plate{position:absolute;left:-8px;top:-6px;bottom:-6px;right:-8px;border-radius:9px;
        z-index:1;overflow:hidden;}
 .plate svg{width:100%;height:100%;display:block;}
 .av{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;color:#fff;
     font-weight:800;font-size:15px;background:linear-gradient(135deg,#2563eb,#1e40af);
     flex:0 0 auto;position:relative;z-index:3;box-shadow:0 0 0 2px rgba(255,255,255,.3);}
 .medal{width:17px;height:17px;border-radius:4px;flex:0 0 auto;position:relative;z-index:3;
        background:linear-gradient(135deg,#f3c768,#a87f1f);
        box-shadow:0 0 0 1.5px rgba(0,0,0,.25);}
 .nm{font-weight:800;font-size:13px;position:relative;z-index:3;}
 .chip{font-size:9.5px;font-weight:800;border-radius:9px;padding:1px 5px;
       position:relative;z-index:3;}
 .pill{font-size:8.5px;font-weight:700;padding:2px 5px;border-radius:3px;white-space:nowrap;
       position:relative;z-index:3;}
 /* Texto claro sobre placa oscura */
 .ink-light .nm{color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.8);}
 .ink-light .chip{color:#ffc79a;background:rgba(0,0,0,.42);border:1px solid rgba(255,170,110,.6);}
 .ink-light .pill{color:#f6d489;border:1px solid rgba(246,212,137,.6);background:rgba(0,0,0,.42);}
 /* Texto oscuro sobre placa clara */
 .ink-dark .nm{color:#14161c;text-shadow:0 1px 2px rgba(255,255,255,.75);}
 .ink-dark .chip{color:#a8410f;background:rgba(255,255,255,.72);border:1px solid rgba(168,65,15,.45);}
 .ink-dark .pill{color:#6b5310;border:1px solid rgba(107,83,16,.5);background:rgba(255,255,255,.72);}
 .ttl{font-weight:800;font-size:13px;margin-top:9px;}
</style>
__BODY__
"""


def build(slugs):
    body = []
    for slug, name, family, ink, art in PLATES:
        if slug not in slugs:
            continue
        body.append(
            '<div><div class="cap">%s <span>· %s · fondo %s</span></div>'
            '<div class="post"><div class="top ink-%s">'
            '<div class="plate"><svg viewBox="0 0 420 56" preserveAspectRatio="none">%s</svg></div>'
            '<div class="av">M</div><span class="medal"></span>'
            '<span class="nm">marcus_dw</span><span class="chip">🔥12</span>'
            '<span class="pill">Trading Legend</span></div>'
            '<div class="ttl">Sweep del PDL y reclaim</div></div></div>'
            % (name, family, 'oscuro' if ink == 'light' else 'claro', ink, art))
    return PAGE.replace('__BODY__', '\n'.join(body))


def shoot(slugs):
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False) as fh:
        fh.write(build(slugs))
        path = fh.name
    script = f'''
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path={CHROME!r})
    pg = b.new_page(viewport={{'width': 760, 'height': 500}}, device_scale_factor=2)
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
