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

# ── SELECCIÓN CONFIRMADA (2026-08-02) ────────────────────────────────────────
# Los 24 marcos de ruleta se reparten 2 por mes durante un año, y UNO de cada
# mes comparte temática con el camo mensual. Como de esas 12 temáticas solo
# existe Chronicles, se congelaron los 12 marcos LIBRES —los que no dependen
# de ninguna temática mensual— y los 11 restantes se diseñan junto a sus camos.
# Del catálogo de 36: 13 van a la ruleta (12 libres + Chronicles) y los otros
# 23 quedan para la tienda.
RULETA_LIBRES = ['candlegrid', 'volume', 'terminal', 'orderflow', 'mars',
                 'dunes', 'sakura', 'volcano', 'circuit', 'obsidian',
                 'cartography', 'arcade']                       # 12
# Atados a la temática del camo mensual: 12 en total. Solo existe el primero
# (Chronicles, cuyo camo ya encargó el dueño); los otros 11 se diseñan junto
# con sus camos.
#
# Criterio fijado 2026-08-02 por el dueño: épocas y actividades POCO
# TRANSITADAS — nada de piratas, ninjas, vaqueros, astronautas ni safaris —
# y, tras aprobar béisbol y fútbol americano, nada MÁS de deportes ni de
# oficios, que ya quedaron cubiertos.
#
# Legalidad del deporte (consultado 2026-08-02): un deporte no se registra.
# Lo protegido son las MARCAS —nombres/escudos de equipos, el logo de la NFL
# o la MLB, el término "Super Bowl"— y la imagen de jugadores reales. Una
# botarga genérica con casco y hombreras, o con bate y guante, no toca nada
# de eso. Regla para el ilustrador: cero logos, cero nombres de equipo, cero
# parecidos a un jugador identificable.
#
# CALENDARIO (fijado 2026-08-02, reordenado el mismo día). La TEMPORADA 1 es
# **agosto de 2026**: el dueño abre la plataforma esta semana o la siguiente y
# Chronicles es el único camo que ya existe, así que ocupa el mes en curso y
# los 11 restantes se reparten de septiembre en adelante.
#
# Tres criterios ordenan la rueda:
#   · COSTO: septiembre y octubre son a propósito las dos botargas más
#     baratas, porque ahí se arma el colchón de 3 meses antes de encender la
#     rotación. De noviembre en adelante alterna caro/barato sin excepción:
#     las 5 caras (armadura y gradas del coliseo, tigre, serpiente emplumada,
#     velo translúcido del apicultor, góndola del dirigible) nunca caen
#     seguidas.
#   · PALETA: ningún mes repite la familia de color del anterior.
#   · ESTACIÓN, donde existe: la NFL arranca en septiembre, el alpinismo cae
#     en diciembre, la serpiente emplumada en marzo —el equinoccio de Chichén
#     Itzá, cuando la sombra de la serpiente baja la pirámide—, el béisbol en
#     el opening day de abril y la floración del apicultor en mayo.
TEMPORADAS = [
    ('2026-08', 'chronicles', 'Chronicles',        'basalto + lava'),
    ('2026-09', 'gridiron',   'American Football', 'noche de estadio + focos'),
    ('2026-10', 'nile',       'Nile',              'arena + lapislázuli'),
    ('2026-11', 'colosseum',  'Colosseum',         'ocre oscuro + antorcha'),
    ('2026-12', 'summit',     'Summit',            'hielo + granito'),
    ('2027-01', 'bengal',     'Bengal',            'bambú de noche + brasa'),
    ('2027-02', 'olympus',    'Olympus',           'mármol + oro pálido'),
    ('2027-03', 'quetzal',    'Quetzalcóatl',      'jade + oro + terracota'),
    ('2027-04', 'baseball',   'Baseball',          'césped + cal, a pleno día'),
    ('2027-05', 'apiarist',   'Apiarist',          'ámbar + velo blanco'),
    ('2027-06', 'welder',     'Welder',            'acero + arco azul'),
    ('2027-07', 'zeppelin',   'Zeppelin',          'latón + sepia cálido'),
]
# ⚠️ Único empalme flojo: abril (arcilla del béisbol) contra mayo (ámbar del
# apicultor). Se resuelve en el DISEÑO, no reordenando: la placa de béisbol
# manda con el VERDE del césped y la cal, dejando la arcilla de acento, y la
# del apicultor se queda en ámbar sobre crema sin verde. Por eso las paletas
# de arriba dicen "césped + cal" y "ámbar + velo".
#
# ⚠️ Bengal = tigre de Bengala sobre bosque de bambú de la INDIA (confirmado
# por el dueño). El tigre es una CRIATURA, así que vive en la botarga (la
# dibuja el ilustrador), nunca en el marco. El marco es el bambú de noche con
# el resplandor de las brasas — eso sí es procedimental y entra en lo que se
# puede dibujar acá. Misma división que con el dragón de Chronicles.
RULETA_TEMATICOS = [s for _, s, _, _ in TEMPORADAS]             # 12 de 12
# Festivos: NO entran a la ruleta. Se venden en la tienda con ventana de 24h
# el día de la festividad, misma regla que los camos festivos.
FESTIVOS = ['frost', 'muertos']

# Lienzo REAL de la placa: 640 x 48 — ancha y baja, como la fila del foro.
# (slug, nombre, familia, ink 'light'=texto claro | 'dark'=texto oscuro, escena)
PLATES = [
 # ══ MERCADO ═══════════════════════════════════════════════════════════════
 ('tape', 'Tape Reader', 'mercado', 'light', """
  <rect width="640" height="48" fill="#081525"/>
  <rect y="14" width="640" height="20" fill="#0f2b47"/>
  <g stroke="#1d4a78" stroke-width="1"><path d="M0 14 H640 M0 34 H640"/></g>
  <g font-family="monospace" font-size="8" fill="#5fd3a0">
    <text x="264" y="27">NQ +1.24%  ES +0.83%  GC -0.41%  EU +0.19%  YM +1.02%</text>
  </g>
  <g fill="#1d4a78"><rect x="264" y="6" width="3" height="4"/><rect x="300" y="6" width="3" height="4"/>
    <rect x="336" y="6" width="3" height="4"/><rect x="372" y="6" width="3" height="4"/>
    <rect x="408" y="6" width="3" height="4"/><rect x="444" y="6" width="3" height="4"/>
    <rect x="480" y="6" width="3" height="4"/><rect x="516" y="6" width="3" height="4"/>
    <rect x="552" y="6" width="3" height="4"/><rect x="588" y="6" width="3" height="4"/>
    <rect x="264" y="38" width="3" height="4"/><rect x="300" y="38" width="3" height="4"/>
    <rect x="336" y="38" width="3" height="4"/><rect x="372" y="38" width="3" height="4"/>
    <rect x="408" y="38" width="3" height="4"/><rect x="444" y="38" width="3" height="4"/>
    <rect x="480" y="38" width="3" height="4"/><rect x="516" y="38" width="3" height="4"/>
    <rect x="552" y="38" width="3" height="4"/><rect x="588" y="38" width="3" height="4"/></g>
 """),
 ('candlegrid', 'Candle Grid', 'mercado', 'light', """
  <rect width="640" height="48" fill="#0b111c"/>
  <g stroke="#1a2436" stroke-width="1">
    <path d="M0 12 H640 M0 24 H640 M0 36 H640"/>
    <path d="M300 0 V48 M340 0 V48 M380 0 V48 M420 0 V48 M460 0 V48 M500 0 V48 M540 0 V48 M580 0 V48"/>
  </g>
  <g>
    <g fill="#2fbf71"><rect x="290" y="26" width="8" height="12" rx="1"/><rect x="293" y="20" width="2" height="24"/></g>
    <g fill="#e0455e"><rect x="312" y="20" width="8" height="10" rx="1"/><rect x="315" y="15" width="2" height="21"/></g>
    <g fill="#2fbf71"><rect x="334" y="22" width="8" height="13" rx="1"/><rect x="337" y="16" width="2" height="25"/></g>
    <g fill="#2fbf71"><rect x="356" y="17" width="8" height="11" rx="1"/><rect x="359" y="11" width="2" height="23"/></g>
    <g fill="#e0455e"><rect x="378" y="14" width="8" height="9" rx="1"/><rect x="381" y="9" width="2" height="19"/></g>
    <g fill="#2fbf71"><rect x="400" y="18" width="8" height="14" rx="1"/><rect x="403" y="12" width="2" height="26"/></g>
    <g fill="#2fbf71"><rect x="422" y="12" width="8" height="12" rx="1"/><rect x="425" y="7" width="2" height="22"/></g>
    <g fill="#e0455e"><rect x="444" y="16" width="8" height="10" rx="1"/><rect x="447" y="11" width="2" height="20"/></g>
    <g fill="#2fbf71"><rect x="466" y="20" width="8" height="12" rx="1"/><rect x="469" y="14" width="2" height="24"/></g>
    <g fill="#2fbf71"><rect x="488" y="14" width="8" height="13" rx="1"/><rect x="491" y="8" width="2" height="25"/></g>
    <g fill="#e0455e"><rect x="510" y="10" width="8" height="9" rx="1"/><rect x="513" y="6" width="2" height="18"/></g>
    <g fill="#2fbf71"><rect x="532" y="13" width="8" height="14" rx="1"/><rect x="535" y="7" width="2" height="26"/></g>
    <g fill="#2fbf71"><rect x="554" y="8" width="8" height="12" rx="1"/><rect x="557" y="3" width="2" height="22"/></g>
    <g fill="#e0455e"><rect x="576" y="12" width="8" height="10" rx="1"/><rect x="579" y="7" width="2" height="20"/></g>
    <g fill="#2fbf71"><rect x="598" y="9" width="8" height="13" rx="1"/><rect x="601" y="4" width="2" height="24"/></g>
  </g>
 """),
 ('volume', 'Volume Profile', 'mercado', 'light', """
  <rect width="640" height="48" fill="#0d131f"/>
  <g fill="#3d6ea8" opacity=".85">
    <rect x="256" y="40" width="20" height="8"/><rect x="280" y="34" width="20" height="14"/>
    <rect x="304" y="26" width="20" height="22"/><rect x="328" y="30" width="20" height="18"/>
    <rect x="352" y="18" width="20" height="30"/><rect x="376" y="10" width="20" height="38"/>
    <rect x="400" y="16" width="20" height="32"/><rect x="424" y="24" width="20" height="24"/>
    <rect x="448" y="20" width="20" height="28"/><rect x="472" y="32" width="20" height="16"/>
    <rect x="496" y="28" width="20" height="20"/><rect x="520" y="36" width="20" height="12"/>
    <rect x="544" y="30" width="20" height="18"/><rect x="568" y="38" width="20" height="10"/>
    <rect x="592" y="42" width="20" height="6"/><rect x="616" y="36" width="20" height="12"/>
  </g>
  <path d="M376 10 H640" stroke="#7fb6ff" stroke-width="1.4" stroke-dasharray="4 4" opacity=".8"/>
  <g stroke="#1c2b42" stroke-width="1"><path d="M0 47 H640"/></g>
 """),
 ('killzone', 'Kill Zone', 'mercado', 'light', """
  <rect width="640" height="48" fill="#070f1c"/>
  <rect x="270" width="70" height="48" fill="#1c4a86" opacity=".55"/>
  <rect x="392" width="54" height="48" fill="#1c4a86" opacity=".4"/>
  <rect x="504" width="62" height="48" fill="#1c4a86" opacity=".5"/>
  <g stroke="#7fb6ff" stroke-width="1" opacity=".55">
    <path d="M270 0 V48 M340 0 V48 M392 0 V48 M446 0 V48 M504 0 V48 M566 0 V48"/>
  </g>
  <g font-family="monospace" font-size="7" fill="#a8ccff" opacity=".9">
    <text x="278" y="10">LONDON</text><text x="398" y="10">NY AM</text><text x="510" y="10">NY PM</text>
  </g>
  <g stroke="#7fb6ff" stroke-width="1.6" fill="none" opacity=".8">
    <path d="M256 36 L292 30 L318 34 L352 22 L392 28 L424 18 L460 26 L504 16 L540 24 L580 12 L640 20"/>
  </g>
 """),
 ('bullrun', 'Bull Run', 'mercado', 'dark', """
  <rect width="640" height="48" fill="#f0f9f3"/>
  <g stroke="#cbe7d6" stroke-width="1"><path d="M0 12 H640 M0 24 H640 M0 36 H640"/></g>
  <g fill="#1f9d55">
    <g><rect x="264" y="32" width="9" height="10" rx="1"/><rect x="267.5" y="27" width="2" height="20"/></g>
    <g><rect x="292" y="27" width="9" height="12" rx="1"/><rect x="295.5" y="22" width="2" height="22"/></g>
    <g><rect x="320" y="23" width="9" height="11" rx="1"/><rect x="323.5" y="18" width="2" height="21"/></g>
    <g><rect x="348" y="19" width="9" height="12" rx="1"/><rect x="351.5" y="14" width="2" height="22"/></g>
    <g><rect x="376" y="15" width="9" height="11" rx="1"/><rect x="379.5" y="10" width="2" height="21"/></g>
    <g><rect x="404" y="12" width="9" height="12" rx="1"/><rect x="407.5" y="7" width="2" height="22"/></g>
    <g><rect x="432" y="8" width="9" height="11" rx="1"/><rect x="435.5" y="4" width="2" height="20"/></g>
  </g>
  <path d="M252 42 L296 34 L340 27 L384 19 L428 12 L472 6 L520 3"
        stroke="#127a41" stroke-width="2.2" fill="none" stroke-linecap="round"/>
  <path d="M520 3 L508 8 M520 3 L516 15" stroke="#127a41" stroke-width="2.2"
        fill="none" stroke-linecap="round"/>
  <g fill="#1f9d55" opacity=".18">
    <path d="M252 48 L296 34 L340 27 L384 19 L428 12 L472 6 L520 3 L640 3 L640 48 Z"/>
  </g>
 """),
 ('bearcave', 'Bear Cave', 'mercado', 'light', """
  <rect width="640" height="48" fill="#160710"/>
  <g stroke="#38121f" stroke-width="1"><path d="M0 12 H640 M0 24 H640 M0 36 H640"/></g>
  <g fill="#d8304f">
    <g><rect x="264" y="6" width="9" height="11" rx="1"/><rect x="267.5" y="2" width="2" height="20"/></g>
    <g><rect x="292" y="10" width="9" height="12" rx="1"/><rect x="295.5" y="5" width="2" height="22"/></g>
    <g><rect x="320" y="15" width="9" height="11" rx="1"/><rect x="323.5" y="10" width="2" height="21"/></g>
    <g><rect x="348" y="19" width="9" height="12" rx="1"/><rect x="351.5" y="14" width="2" height="22"/></g>
    <g><rect x="376" y="24" width="9" height="11" rx="1"/><rect x="379.5" y="19" width="2" height="21"/></g>
    <g><rect x="404" y="28" width="9" height="12" rx="1"/><rect x="407.5" y="23" width="2" height="22"/></g>
    <g><rect x="432" y="33" width="9" height="11" rx="1"/><rect x="435.5" y="28" width="2" height="20"/></g>
  </g>
  <path d="M252 5 L296 13 L340 20 L384 28 L428 35 L472 41 L520 45"
        stroke="#ff5c78" stroke-width="2.2" fill="none" stroke-linecap="round"/>
  <path d="M520 45 L508 41 M520 45 L516 34" stroke="#ff5c78" stroke-width="2.2"
        fill="none" stroke-linecap="round"/>
 """),
 ('blueprint', 'Blueprint', 'mercado', 'light', """
  <rect width="640" height="48" fill="#0a3468"/>
  <g stroke="#2a6db8" stroke-width="1" opacity=".8">
    <path d="M0 8 H640 M0 16 H640 M0 24 H640 M0 32 H640 M0 40 H640"/>
    <path d="M264 0 V48 M296 0 V48 M328 0 V48 M360 0 V48 M392 0 V48 M424 0 V48
             M456 0 V48 M488 0 V48 M520 0 V48 M552 0 V48 M584 0 V48 M616 0 V48"/>
  </g>
  <g stroke="#dbe9ff" stroke-width="1.5" fill="none">
    <rect x="300" y="12" width="90" height="26" rx="2"/>
    <path d="M300 20 H390 M330 12 V38 M360 12 V38"/>
    <circle cx="470" cy="24" r="13"/><circle cx="470" cy="24" r="5"/>
    <path d="M470 6 V11 M470 37 V42 M452 24 H457 M483 24 H488"/>
    <path d="M520 38 L546 16 L566 28 L596 8"/>
  </g>
  <g stroke="#dbe9ff" stroke-width="1" opacity=".7" fill="none">
    <path d="M300 44 H390 M300 42 V46 M390 42 V46"/>
  </g>
 """),
 ('terminal', 'Terminal', 'mercado', 'light', """
  <rect width="640" height="48" fill="#03110a"/>
  <g stroke="#0c3a20" stroke-width="1" opacity=".8">
    <path d="M0 6 H640 M0 12 H640 M0 18 H640 M0 24 H640 M0 30 H640 M0 36 H640 M0 42 H640"/>
  </g>
  <g font-family="monospace" font-size="8.5" fill="#3ef58e">
    <text x="262" y="14">&gt; scan --session=london</text>
    <text x="262" y="26">  sweep @ PDL · displacement TRUE</text>
    <text x="262" y="38">&gt; _</text>
  </g>
  <rect x="277" y="32" width="6" height="8" fill="#3ef58e"/>
  <g stroke="#3ef58e" stroke-width="1.6" fill="none" opacity=".5">
    <path d="M500 40 L524 26 L544 32 L568 14 L592 22 L624 6"/>
  </g>
 """),
 ('liquidity', 'Liquidity Pool', 'mercado', 'light', """
  <rect width="640" height="48" fill="#02121b"/>
  <path d="M0 48 L640 48 L640 20 C600 26 560 14 520 20 C480 26 440 14 400 20
           C360 26 320 14 280 20 C240 26 200 16 160 22 C120 28 60 18 0 24 Z"
        fill="#0a4a63" opacity=".85"/>
  <path d="M0 48 L640 48 L640 30 C596 36 552 24 508 30 C464 36 420 26 376 32
           C332 38 288 28 244 34 C200 40 100 30 0 36 Z" fill="#0e6b8c"/>
  <g stroke="#7fe4ff" stroke-width="1.4" fill="none" opacity=".7">
    <path d="M280 14 C296 8 312 18 328 12 C344 6 360 16 376 10"/>
    <path d="M420 18 C436 12 452 22 468 16 C484 10 500 20 516 14"/>
  </g>
  <g fill="#bff0ff" opacity=".6">
    <circle cx="352" cy="26" r="2.4"/><circle cx="366" cy="20" r="1.6"/>
    <circle cx="474" cy="30" r="2"/><circle cx="488" cy="24" r="1.4"/>
    <circle cx="560" cy="26" r="2.2"/>
  </g>
 """),
 ('orderflow', 'Order Flow', 'mercado', 'light', """
  <rect width="640" height="48" fill="#04150f"/>
  <g fill="#2fbf71" opacity=".8">
    <rect x="330" y="26" width="30" height="4"/><rect x="330" y="32" width="52" height="4"/>
    <rect x="330" y="38" width="38" height="4"/><rect x="330" y="44" width="66" height="4"/>
  </g>
  <g fill="#e0455e" opacity=".8">
    <rect x="330" y="2" width="44" height="4"/><rect x="330" y="8" width="26" height="4"/>
    <rect x="330" y="14" width="58" height="4"/><rect x="330" y="20" width="34" height="4"/>
  </g>
  <path d="M326 0 V48" stroke="#5fd3a0" stroke-width="1.5"/>
  <g font-family="monospace" font-size="7" fill="#5fd3a0" opacity=".85">
    <text x="424" y="14">ASK 21 452</text><text x="424" y="26">──────────</text>
    <text x="424" y="38">BID 21 448</text>
  </g>
  <g fill="#2fbf71" opacity=".5">
    <rect x="536" y="30" width="6" height="14"/><rect x="548" y="24" width="6" height="20"/>
    <rect x="560" y="34" width="6" height="10"/><rect x="572" y="18" width="6" height="26"/>
    <rect x="584" y="28" width="6" height="16"/><rect x="596" y="12" width="6" height="32"/>
    <rect x="608" y="22" width="6" height="22"/><rect x="620" y="8" width="6" height="36"/>
  </g>
 """),

 # ══ NATURAL ═══════════════════════════════════════════════════════════════
 ('mars', 'Red Planet', 'natural', 'dark', """
  <defs><linearGradient id="ma-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#f2d2b8"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#ma-sky)"/>
  <g fill="#ffffff">
    <path d="M300 8 l1.4 4 4 1.4 -4 1.4 -1.4 4 -1.4-4 -4-1.4 4-1.4 Z"/>
    <path d="M418 5 l1 3 3 1 -3 1 -1 3 -1-3 -3-1 3-1 Z"/>
    <path d="M540 10 l1.2 3.5 3.5 1.2 -3.5 1.2 -1.2 3.5 -1.2-3.5 -3.5-1.2 3.5-1.2 Z"/>
  </g>
  <circle cx="478" cy="13" r="8" fill="#f6a97a" opacity=".5"/>
  <path d="M0 32 L70 20 L128 30 L196 16 L268 28 L344 18 L416 29 L488 19 L560 30 L640 21 L640 48 L0 48 Z"
        fill="#c96a4a" opacity=".55"/>
  <path d="M0 38 L64 27 L134 37 L210 25 L284 36 L360 26 L436 37 L512 27 L588 37 L640 31 L640 48 L0 48 Z"
        fill="#a64f30" opacity=".85"/>
  <path d="M0 44 L82 36 L168 44 L254 35 L338 44 L426 36 L512 44 L598 37 L640 41 L640 48 L0 48 Z"
        fill="#7d3520"/>
  <path d="M0 48 L0 43 L52 48 Z M640 48 L640 41 L582 48 Z" fill="#5e2415"/>
 """),
 ('glacier', 'Glacier', 'natural', 'dark', """
  <defs><linearGradient id="gl-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f0fbff"/><stop offset="1" stop-color="#bfe6f7"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#gl-sky)"/>
  <g fill="#ffffff" opacity=".85">
    <circle cx="300" cy="8" r="1.4"/><circle cx="392" cy="6" r="1"/><circle cx="524" cy="9" r="1.2"/>
  </g>
  <path d="M0 48 L58 24 L98 36 L158 14 L222 34 L288 20 L352 38 L418 18 L484 36 L548 22 L606 38 L640 30 L640 48 Z"
        fill="#8fd0e8" opacity=".8"/>
  <path d="M0 48 L68 34 L140 44 L212 28 L284 42 L358 30 L430 44 L502 32 L574 44 L640 38 L640 48 Z"
        fill="#4d9cc0"/>
  <g stroke="#ffffff" stroke-width="1.4" opacity=".85" fill="none">
    <path d="M158 14 L168 28 L160 38 M288 20 L296 32 L288 42 M418 18 L428 30 L420 40 M548 22 L556 34"/>
  </g>
 """),
 ('abyss', 'Abyss', 'natural', 'light', """
  <defs><linearGradient id="ab-w" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0c3b60"/><stop offset="1" stop-color="#010710"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#ab-w)"/>
  <g fill="#9fd8ff" opacity=".14">
    <path d="M280 0 L308 0 L272 48 L250 48 Z"/><path d="M380 0 L400 0 L370 48 L354 48 Z"/>
    <path d="M496 0 L524 0 L490 48 L468 48 Z"/><path d="M594 0 L612 0 L586 48 L570 48 Z"/>
  </g>
  <g fill="#bfe6ff" opacity=".55">
    <circle cx="330" cy="30" r="2.4"/><circle cx="342" cy="22" r="1.6"/><circle cx="352" cy="34" r="1.2"/>
    <circle cx="452" cy="18" r="2"/><circle cx="464" cy="28" r="1.4"/>
    <circle cx="560" cy="24" r="2.2"/><circle cx="572" cy="14" r="1.4"/>
  </g>
  <path d="M0 48 L640 48 L640 42 C580 38 520 44 460 41 C400 38 340 44 280 41
           C220 38 160 44 100 41 C60 39 30 42 0 44 Z" fill="#02141f"/>
  <g stroke="#4a9ac8" stroke-width="1.2" fill="none" opacity=".5">
    <path d="M300 44 C304 38 308 36 312 34 M420 43 C424 37 428 34 434 32
             M540 44 C544 38 548 35 554 33"/>
  </g>
 """),
 ('aurora', 'Aurora', 'natural', 'light', """
  <rect width="640" height="48" fill="#040914"/>
  <g fill="#ffffff" opacity=".8">
    <circle cx="300" cy="6" r="1.1"/><circle cx="368" cy="12" r=".9"/><circle cx="440" cy="5" r="1.2"/>
    <circle cx="520" cy="10" r="1"/><circle cx="600" cy="7" r="1.1"/>
  </g>
  <g opacity=".75">
    <path d="M256 48 C268 26 280 12 296 4 C304 16 300 32 292 48 Z" fill="#3fe0a8"/>
    <path d="M304 48 C318 22 332 10 350 2 C356 18 350 34 342 48 Z" fill="#5fe8c0" opacity=".8"/>
    <path d="M356 48 C370 24 384 12 402 6 C408 20 402 36 394 48 Z" fill="#7f8cff" opacity=".7"/>
    <path d="M410 48 C424 20 438 10 456 4 C462 20 456 36 448 48 Z" fill="#3fe0a8" opacity=".65"/>
    <path d="M464 48 C478 26 492 14 510 8 C516 22 510 36 502 48 Z" fill="#a06ff0" opacity=".6"/>
    <path d="M518 48 C532 22 546 12 564 6 C570 20 564 36 556 48 Z" fill="#5fe8c0" opacity=".55"/>
  </g>
  <path d="M0 48 L120 40 L240 44 L360 38 L480 43 L600 37 L640 40 L640 48 Z" fill="#060d1c"/>
 """),
 ('dunes', 'Desert Night', 'natural', 'light', """
  <defs><linearGradient id="du-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#080b20"/><stop offset="1" stop-color="#2c2358"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#du-sky)"/>
  <circle cx="470" cy="12" r="9" fill="#f2ecda"/>
  <circle cx="465" cy="9" r="8" fill="#0b0e24"/>
  <g fill="#ffffff" opacity=".85">
    <circle cx="300" cy="8" r="1.2"/><circle cx="352" cy="14" r=".9"/><circle cx="398" cy="6" r="1.1"/>
    <circle cx="540" cy="10" r="1"/><circle cx="586" cy="18" r="1.2"/><circle cx="616" cy="6" r=".9"/>
  </g>
  <path d="M0 48 C90 32 180 42 270 34 C360 26 450 40 540 32 C580 28 610 31 640 29 L640 48 Z"
        fill="#5b4a86" opacity=".6"/>
  <path d="M0 48 C110 40 220 48 330 40 C440 32 530 44 640 36 L640 48 Z" fill="#3b2f60"/>
 """),
 ('storm', 'Storm', 'natural', 'light', """
  <rect width="640" height="48" fill="#0c1119"/>
  <g fill="#39434f" opacity=".95">
    <path d="M280 22 C270 22 264 17 264 11 C264 5 270 0 277 0 L560 0 C572 0 580 6 580 13
             C580 19 573 24 564 24 Z"/>
  </g>
  <g fill="#59667a" opacity=".8">
    <path d="M300 26 C292 26 288 22 288 18 L520 18 C528 18 532 22 532 26 Z"/>
  </g>
  <path d="M392 26 L376 42 L388 42 L378 56 L406 34 L392 34 Z" fill="#ffe066"/>
  <path d="M492 24 L480 38 L490 38 L482 50 L504 30 L492 30 Z" fill="#ffe066" opacity=".7"/>
  <g stroke="#7fa8d0" stroke-width="1" opacity=".45">
    <path d="M310 30 L306 44 M330 28 L326 44 M350 32 L346 46 M430 30 L426 44
             M450 28 L446 44 M530 30 L526 44 M550 28 L546 42 M570 32 L566 46"/>
  </g>
  <path d="M0 48 L640 48 L640 44 C540 40 440 46 340 43 C240 40 120 46 0 43 Z" fill="#161d28"/>
 """),
 ('jungle', 'Jungle', 'natural', 'light', """
  <defs><linearGradient id="ju-bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0a2f16"/><stop offset="1" stop-color="#04170b"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#ju-bg)"/>
  <g fill="#1d6b33" opacity=".85">
    <path d="M256 0 C276 6 288 18 292 34 C280 22 268 12 254 8 Z"/>
    <path d="M330 0 C346 8 354 22 354 38 C346 24 334 14 320 8 Z"/>
    <path d="M404 0 C424 6 436 20 438 36 C428 22 414 12 400 8 Z"/>
    <path d="M478 0 C494 8 502 22 502 38 C494 24 482 14 468 8 Z"/>
    <path d="M552 0 C572 6 584 18 588 34 C576 22 564 12 550 8 Z"/>
  </g>
  <g fill="#2f9e4a" opacity=".6">
    <path d="M292 48 C288 34 294 22 306 14 C306 28 302 40 300 48 Z"/>
    <path d="M366 48 C362 32 370 20 382 12 C382 26 376 40 374 48 Z"/>
    <path d="M440 48 C436 34 442 22 454 14 C454 28 450 40 448 48 Z"/>
    <path d="M514 48 C510 32 518 20 530 12 C530 26 524 40 522 48 Z"/>
    <path d="M588 48 C584 34 590 22 602 14 C602 28 598 40 596 48 Z"/>
  </g>
  <g fill="#7fe08f" opacity=".35">
    <circle cx="330" cy="24" r="1.4"/><circle cx="470" cy="18" r="1.2"/><circle cx="560" cy="28" r="1.3"/>
  </g>
 """),
 ('sakura', 'Sakura', 'natural', 'dark', """
  <defs><linearGradient id="sk-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff6f8"/><stop offset="1" stop-color="#fbdde6"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#sk-sky)"/>
  <g stroke="#6b4a3c" stroke-width="2.4" fill="none" stroke-linecap="round">
    <path d="M640 6 C600 10 570 8 540 16 C512 23 486 20 458 28"/>
    <path d="M570 10 C566 20 560 26 550 32 M512 22 C510 30 504 36 496 40
             M600 8 C598 16 594 22 588 27"/>
  </g>
  <g fill="#f58fb0">
    <circle cx="548" cy="18" r="4"/><circle cx="588" cy="12" r="3.4"/>
    <circle cx="512" cy="24" r="3.6"/><circle cx="612" cy="8" r="3"/>
    <circle cx="478" cy="28" r="3.2"/><circle cx="566" cy="30" r="2.8"/>
    <circle cx="496" cy="38" r="2.6"/>
  </g>
  <g fill="#f7b5cc">
    <circle cx="560" cy="24" r="2.4"/><circle cx="600" cy="20" r="2"/><circle cx="530" cy="34" r="2.2"/>
  </g>
  <g fill="#f58fb0" opacity=".75">
    <ellipse cx="300" cy="20" rx="3" ry="2" transform="rotate(-25 300 20)"/>
    <ellipse cx="348" cy="34" rx="2.6" ry="1.8" transform="rotate(15 348 34)"/>
    <ellipse cx="396" cy="14" rx="2.8" ry="1.9" transform="rotate(-40 396 14)"/>
    <ellipse cx="428" cy="40" rx="2.4" ry="1.7" transform="rotate(20 428 40)"/>
    <ellipse cx="268" cy="38" rx="2.6" ry="1.8" transform="rotate(-10 268 38)"/>
  </g>
 """),
 ('nebula', 'Nebula', 'natural', 'light', """
  <defs>
    <radialGradient id="ne-a" cx=".5" cy=".5" r=".5">
      <stop offset="0" stop-color="#c05ae0" stop-opacity=".85"/>
      <stop offset="1" stop-color="#c05ae0" stop-opacity="0"/></radialGradient>
    <radialGradient id="ne-b" cx=".5" cy=".5" r=".5">
      <stop offset="0" stop-color="#4a7cf5" stop-opacity=".8"/>
      <stop offset="1" stop-color="#4a7cf5" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="640" height="48" fill="#060412"/>
  <ellipse cx="360" cy="24" rx="90" ry="26" fill="url(#ne-a)"/>
  <ellipse cx="480" cy="28" rx="80" ry="24" fill="url(#ne-b)"/>
  <ellipse cx="580" cy="18" rx="60" ry="20" fill="url(#ne-a)" opacity=".7"/>
  <g fill="#ffffff">
    <circle cx="296" cy="10" r="1.2"/><circle cx="330" cy="30" r=".9"/><circle cx="372" cy="8" r="1.4"/>
    <circle cx="410" cy="36" r="1"/><circle cx="452" cy="14" r="1.2"/><circle cx="498" cy="34" r=".9"/>
    <circle cx="540" cy="10" r="1.3"/><circle cx="586" cy="32" r="1"/><circle cx="620" cy="16" r="1.2"/>
  </g>
 """),
 ('volcano', 'Ashfall', 'natural', 'light', """
  <rect width="640" height="48" fill="#141318"/>
  <path d="M0 48 L640 48 L640 34 L560 34 L500 12 L440 34 L360 34 L300 18 L240 34 L0 34 Z"
        fill="#241f26"/>
  <path d="M500 12 L470 34 L530 34 Z" fill="#3a2f38"/>
  <g fill="#ff6a2e" opacity=".9">
    <path d="M500 12 C496 18 494 24 494 30 C500 24 504 20 506 14 Z"/>
  </g>
  <g fill="#ff9a4a" opacity=".55">
    <ellipse cx="500" cy="8" rx="16" ry="6"/><ellipse cx="490" cy="2" rx="10" ry="4"/>
  </g>
  <g fill="#c9c4cc" opacity=".65">
    <circle cx="290" cy="14" r="1.2"/><circle cx="330" cy="24" r="1"/><circle cx="366" cy="10" r="1.3"/>
    <circle cx="404" cy="26" r="1"/><circle cx="560" cy="18" r="1.2"/><circle cx="600" cy="8" r="1"/>
    <circle cx="618" cy="26" r="1.3"/><circle cx="452" cy="16" r="1.1"/>
  </g>
 """),

 # ══ MATERIAL ══════════════════════════════════════════════════════════════
 ('carbon', 'Carbon Fiber', 'material', 'light', """
  <defs><pattern id="cf" width="16" height="16" patternUnits="userSpaceOnUse">
    <rect width="16" height="16" fill="#101218"/>
    <rect width="8" height="8" fill="#1d212b"/><rect x="8" y="8" width="8" height="8" fill="#1d212b"/>
    <path d="M0 0 L8 8 M8 8 L16 16" stroke="#272c38" stroke-width="1.4"/>
    <path d="M8 0 L0 8 M16 8 L8 16" stroke="#272c38" stroke-width="1.4"/>
  </pattern></defs>
  <rect width="640" height="48" fill="url(#cf)"/>
  <rect width="640" height="48" fill="none" stroke="#4a90d9" stroke-width="2" opacity=".4"/>
  <path d="M256 0 L292 48" stroke="#6fb6ff" stroke-width="2" opacity=".35"/>
  <path d="M600 0 L636 48" stroke="#6fb6ff" stroke-width="2" opacity=".35"/>
 """),
 ('circuit', 'Circuit', 'material', 'light', """
  <rect width="640" height="48" fill="#04120e"/>
  <g stroke="#2fbf8f" stroke-width="1.6" fill="none" stroke-linecap="round">
    <path d="M256 12 H320 V30 H384"/>
    <path d="M256 38 H296 V20 H352 V6 H428"/>
    <path d="M384 30 V44 H470"/>
    <path d="M428 6 H500 V24 H568"/>
    <path d="M470 44 H540 V32 H600"/>
    <path d="M568 24 V10 H628"/>
  </g>
  <g fill="#2fbf8f">
    <circle cx="320" cy="12" r="3"/><circle cx="384" cy="30" r="3.4"/><circle cx="296" cy="38" r="3"/>
    <circle cx="352" cy="20" r="3"/><circle cx="428" cy="6" r="3.4"/><circle cx="500" cy="24" r="3"/>
    <circle cx="470" cy="44" r="3"/><circle cx="568" cy="24" r="3.4"/><circle cx="540" cy="32" r="3"/>
    <circle cx="628" cy="10" r="3"/>
  </g>
  <rect x="396" y="14" width="34" height="22" rx="3" fill="none" stroke="#2fbf8f"
        stroke-width="1.6" opacity=".8"/>
  <g stroke="#2fbf8f" stroke-width="1.4" opacity=".8">
    <path d="M396 20 H390 M396 28 H390 M430 20 H436 M430 28 H436"/>
  </g>
 """),
 ('obsidian', 'Obsidian', 'material', 'light', """
  <rect width="640" height="48" fill="#06040e"/>
  <g fill="#241348">
    <path d="M256 48 L300 6 L344 48 Z"/><path d="M330 48 L378 0 L426 48 Z"/>
    <path d="M410 48 L452 10 L494 48 Z"/><path d="M478 48 L528 2 L578 48 Z"/>
    <path d="M562 48 L604 12 L646 48 Z"/>
  </g>
  <g fill="#4a2a8f" opacity=".7">
    <path d="M300 6 L344 48 L322 48 Z"/><path d="M378 0 L426 48 L402 48 Z"/>
    <path d="M452 10 L494 48 L473 48 Z"/><path d="M528 2 L578 48 L553 48 Z"/>
    <path d="M604 12 L646 48 L625 48 Z"/>
  </g>
  <g stroke="#b48cff" stroke-width="1" opacity=".55" fill="none">
    <path d="M300 6 L300 48 M378 0 L378 48 M452 10 L452 48 M528 2 L528 48 M604 12 L604 48"/>
  </g>
 """),
 ('copper', 'Copper Patina', 'material', 'light', """
  <rect width="640" height="48" fill="#0c332c"/>
  <g fill="#1a6b58" opacity=".85">
    <ellipse cx="300" cy="18" rx="44" ry="14"/><ellipse cx="390" cy="34" rx="52" ry="16"/>
    <ellipse cx="486" cy="14" rx="46" ry="13"/><ellipse cx="570" cy="32" rx="50" ry="15"/>
  </g>
  <g fill="#3fbf9a" opacity=".55">
    <ellipse cx="330" cy="26" rx="26" ry="9"/><ellipse cx="440" cy="16" rx="24" ry="8"/>
    <ellipse cx="530" cy="30" rx="28" ry="9"/><ellipse cx="612" cy="18" rx="22" ry="8"/>
  </g>
  <g fill="#c97a3f" opacity=".5">
    <ellipse cx="356" cy="38" rx="18" ry="6"/><ellipse cx="468" cy="40" rx="16" ry="5"/>
    <ellipse cx="592" cy="8" rx="14" ry="5"/>
  </g>
  <g stroke="#0a2a24" stroke-width="1" opacity=".5">
    <path d="M256 0 V48 M320 0 V48 M384 0 V48 M448 0 V48 M512 0 V48 M576 0 V48"/>
  </g>
 """),
 ('marble', 'Marble', 'material', 'dark', """
  <rect width="640" height="48" fill="#f4f2ee"/>
  <g stroke="#c9c3b8" stroke-width="1.6" fill="none" opacity=".9">
    <path d="M240 44 C280 34 300 40 340 28 C380 16 410 22 450 12 C490 2 530 8 570 2"/>
    <path d="M256 12 C296 20 320 14 356 24 C392 34 420 28 460 38 C500 48 540 42 580 46"/>
  </g>
  <g stroke="#a8a196" stroke-width=".9" fill="none" opacity=".8">
    <path d="M300 46 C330 38 348 42 378 32 M420 6 C450 14 470 10 500 18
             M520 40 C550 32 570 36 600 28"/>
  </g>
  <g stroke="#8f887c" stroke-width=".6" fill="none" opacity=".55">
    <path d="M268 30 C298 24 316 28 344 20 M462 26 C492 20 510 24 540 16"/>
  </g>
 """),
 ('brutalist', 'Brutalist', 'material', 'dark', """
  <rect width="640" height="48" fill="#d6d4cf"/>
  <g fill="#bfbcb5">
    <rect x="256" y="0" width="60" height="48"/><rect x="332" y="0" width="60" height="48"/>
    <rect x="408" y="0" width="60" height="48"/><rect x="484" y="0" width="60" height="48"/>
    <rect x="560" y="0" width="60" height="48"/>
  </g>
  <g fill="#a5a29a">
    <rect x="256" y="18" width="60" height="6"/><rect x="332" y="26" width="60" height="6"/>
    <rect x="408" y="14" width="60" height="6"/><rect x="484" y="30" width="60" height="6"/>
    <rect x="560" y="20" width="60" height="6"/>
  </g>
  <g stroke="#8f8c84" stroke-width="1.4">
    <path d="M316 0 V48 M392 0 V48 M468 0 V48 M544 0 V48 M620 0 V48"/>
  </g>
  <g fill="#8f8c84" opacity=".6">
    <circle cx="286" cy="8" r="1.6"/><circle cx="362" cy="8" r="1.6"/><circle cx="438" cy="8" r="1.6"/>
    <circle cx="514" cy="8" r="1.6"/><circle cx="590" cy="8" r="1.6"/>
  </g>
 """),
 ('damascus', 'Damascus', 'material', 'light', """
  <rect width="640" height="48" fill="#22262e"/>
  <g stroke="#5c6472" stroke-width="2" fill="none" opacity=".9">
    <path d="M240 6 C300 2 340 14 400 10 C460 6 500 18 560 14 C600 11 620 14 640 12"/>
    <path d="M240 16 C300 12 340 24 400 20 C460 16 500 28 560 24 C600 21 620 24 640 22"/>
    <path d="M240 26 C300 22 340 34 400 30 C460 26 500 38 560 34 C600 31 620 34 640 32"/>
    <path d="M240 36 C300 32 340 44 400 40 C460 36 500 48 560 44 C600 41 620 44 640 42"/>
  </g>
  <g stroke="#98a2b3" stroke-width="1" fill="none" opacity=".75">
    <path d="M240 11 C300 7 340 19 400 15 C460 11 500 23 560 19 C600 16 620 19 640 17"/>
    <path d="M240 31 C300 27 340 39 400 35 C460 31 500 43 560 39 C600 36 620 39 640 37"/>
  </g>
 """),

 # ══ ÉPICA / CULTURAL ══════════════════════════════════════════════════════
 ('chronicles', 'Chronicles', 'épica', 'light', """
  <defs><linearGradient id="ch-sky" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#120409"/><stop offset=".5" stop-color="#2a0810"/>
    <stop offset="1" stop-color="#5c1210"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#ch-sky)"/>
  <path d="M0 41 L52 37 L92 43 L152 35 L222 41 L290 33 L362 40 L436 32 L506 39 L580 31 L640 38
           L640 48 L0 48 Z" fill="#ff5a1e" opacity=".12"/>
  <g stroke="#ff5a1e" stroke-linecap="round" fill="none">
    <path d="M0 41 L52 37 L92 43 L152 35 L222 41 L290 33 L362 40 L436 32 L506 39 L580 31 L640 38"
          stroke-width="2.4" opacity=".95"/>
    <path d="M92 43 L100 48 M222 41 L214 48 M362 40 L370 48 M506 39 L500 48"
          stroke-width="1.6" opacity=".8"/>
    <path d="M290 33 L298 24 M436 32 L444 22 M580 31 L588 21" stroke-width="1.2" opacity=".5"/>
  </g>
  <g stroke="#ffd08a" stroke-width=".9" fill="none" opacity=".5">
    <path d="M0 41 L52 37 L92 43 L152 35 L222 41 L290 33 L362 40 L436 32 L506 39 L580 31 L640 38"/>
  </g>
  <g fill="#ff8a3c" opacity=".6">
    <circle cx="300" cy="26" r="1.2"/><circle cx="380" cy="18" r="1"/><circle cx="452" cy="27" r="1.1"/>
    <circle cx="530" cy="16" r="1"/><circle cx="600" cy="24" r="1.2"/>
  </g>
 """),
 ('washi', 'Rising Sun', 'épica', 'dark', """
  <rect width="640" height="48" fill="#f7f2e7"/>
  <g stroke="#ddd2ba" stroke-width="1" opacity=".8">
    <path d="M0 10 H640 M0 22 H640 M0 34 H640 M0 46 H640"/>
  </g>
  <circle cx="430" cy="20" r="16" fill="#c2352b" opacity=".92"/>
  <path d="M470 48 L516 18 L548 38 L578 22 L640 48 Z" fill="#2f3640" opacity=".85"/>
  <path d="M300 48 L342 22 L372 40 L396 28 L426 48 Z" fill="#586374" opacity=".6"/>
  <g stroke="#3f5a44" stroke-width="3" stroke-linecap="round" opacity=".8">
    <path d="M256 48 V14 M270 48 V24"/>
  </g>
  <g stroke="#3f5a44" stroke-width="2" fill="none" opacity=".75">
    <path d="M256 20 C246 15 238 17 232 22 M256 30 C266 25 274 27 280 32
             M270 30 C280 26 286 28 291 33"/>
  </g>
 """),
 ('cathedral', 'Cathedral', 'épica', 'light', """
  <rect width="640" height="48" fill="#0a0e2a"/>
  <g>
    <path d="M262 48 V20 C262 10 270 4 279 4 C288 4 296 10 296 20 V48 Z" fill="#2f5bd6"/>
    <path d="M310 48 V14 C310 3 320 -4 331 -4 C342 -4 352 3 352 14 V48 Z" fill="#7a3bc9"/>
    <path d="M366 48 V20 C366 10 374 4 383 4 C392 4 400 10 400 20 V48 Z" fill="#2f5bd6"/>
    <path d="M414 48 V14 C414 3 424 -4 435 -4 C446 -4 456 3 456 14 V48 Z" fill="#7a3bc9"/>
    <path d="M470 48 V20 C470 10 478 4 487 4 C496 4 504 10 504 20 V48 Z" fill="#2f5bd6"/>
    <path d="M518 48 V14 C518 3 528 -4 539 -4 C550 -4 560 3 560 14 V48 Z" fill="#7a3bc9"/>
    <path d="M574 48 V20 C574 10 582 4 591 4 C600 4 608 10 608 20 V48 Z" fill="#2f5bd6"/>
  </g>
  <g stroke="#05061a" stroke-width="3.5" fill="none">
    <path d="M262 48 V20 C262 10 270 4 279 4 C288 4 296 10 296 20 V48"/>
    <path d="M310 48 V14 C310 3 320 -4 331 -4 C342 -4 352 3 352 14 V48"/>
    <path d="M366 48 V20 C366 10 374 4 383 4 C392 4 400 10 400 20 V48"/>
    <path d="M414 48 V14 C414 3 424 -4 435 -4 C446 -4 456 3 456 14 V48"/>
    <path d="M470 48 V20 C470 10 478 4 487 4 C496 4 504 10 504 20 V48"/>
    <path d="M518 48 V14 C518 3 528 -4 539 -4 C550 -4 560 3 560 14 V48"/>
    <path d="M574 48 V20 C574 10 582 4 591 4 C600 4 608 10 608 20 V48"/>
    <path d="M279 4 V48 M331 -4 V48 M383 4 V48 M435 -4 V48 M487 4 V48 M539 -4 V48 M591 4 V48"/>
    <path d="M262 28 H296 M310 22 H352 M366 28 H400 M414 22 H456 M470 28 H504 M518 22 H560 M574 28 H608"/>
  </g>
 """),
 ('cartography', 'Cartography', 'épica', 'dark', """
  <rect width="640" height="48" fill="#e8dfc6"/>
  <g stroke="#b8a878" stroke-width="1.2" fill="none" opacity=".9">
    <path d="M256 40 C286 32 300 24 330 22 C360 20 372 28 400 26"/>
    <path d="M262 44 C294 36 310 28 342 26 C374 24 388 32 418 30"/>
    <path d="M270 48 C304 40 322 32 356 30 C390 28 406 36 438 34"/>
    <path d="M446 14 C470 8 486 12 508 8 M452 20 C476 14 492 18 514 14"/>
  </g>
  <g stroke="#8f7a4a" stroke-width="1.4" fill="none" stroke-dasharray="3 4">
    <path d="M300 36 C340 26 380 34 420 22 C460 10 500 20 546 12"/>
  </g>
  <g fill="#a8442e">
    <path d="M540 6 L552 18 M552 6 L540 18" stroke="#a8442e" stroke-width="2.6"/>
  </g>
  <g transform="translate(596,24)">
    <circle r="15" fill="none" stroke="#8f7a4a" stroke-width="1.2"/>
    <path d="M0 -16 L3.6 -3.6 L16 0 L3.6 3.6 L0 16 L-3.6 3.6 L-16 0 L-3.6 -3.6 Z" fill="#6b5a34"/>
    <circle r="2.4" fill="#e8dfc6"/>
  </g>
 """),
 ('runes', 'Runestone', 'épica', 'light', """
  <rect width="640" height="48" fill="#14161a"/>
  <g fill="#3a4048">
    <path d="M270 48 V18 C270 10 276 5 282 5 C288 5 294 10 294 18 V48 Z"/>
    <path d="M330 48 V10 C330 2 337 -3 344 -3 C351 -3 358 2 358 10 V48 Z"/>
    <path d="M394 48 V22 C394 14 400 9 406 9 C412 9 418 14 418 22 V48 Z"/>
    <path d="M454 48 V12 C454 4 461 -1 468 -1 C475 -1 482 4 482 12 V48 Z"/>
    <path d="M518 48 V20 C518 12 524 7 530 7 C536 7 542 12 542 20 V48 Z"/>
    <path d="M580 48 V14 C580 6 587 1 594 1 C601 1 608 6 608 14 V48 Z"/>
  </g>
  <g stroke="#5fd8ff" stroke-width="2" stroke-linecap="round" fill="none">
    <path d="M282 16 V34 M275 22 L282 29 L289 22"/>
    <path d="M344 8 V38 M336 16 L344 24 L352 16 M336 30 L344 24"/>
    <path d="M406 20 V38 M399 28 H413"/>
    <path d="M468 10 V38 M460 18 L468 26 M476 18 L468 26 M460 34 H476"/>
    <path d="M530 18 V38 M523 24 L530 30 L537 24"/>
    <path d="M594 12 V38 M586 20 L594 12 L602 20 M586 32 H602"/>
  </g>
 """),
 ('arcade', 'Insert Coin', 'retro', 'light', """
  <defs><linearGradient id="ar-bg" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#0e0322"/><stop offset=".5" stop-color="#2a0846"/>
    <stop offset="1" stop-color="#4a0d5e"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#ar-bg)"/>
  <g stroke="#ff2e97" stroke-width="1" opacity=".5">
    <path d="M0 38 H640 M0 43 H640 M0 48 H640"/>
    <path d="M270 38 L258 48 M330 38 L324 48 M390 38 L390 48 M450 38 L456 48
             M510 38 L522 48 M570 38 L588 48"/>
  </g>
  <g transform="translate(400,2)">
    <rect x="0" y="2" width="30" height="44" rx="3" fill="#190630" stroke="#00e5ff" stroke-width="1.6"/>
    <rect x="4" y="6" width="22" height="13" rx="2" fill="#03121c" stroke="#00e5ff" stroke-width="1"/>
    <g fill="#ffe066"><rect x="7" y="14" width="3" height="3"/><rect x="13" y="11" width="3" height="3"/>
      <rect x="20" y="8" width="3" height="3"/></g>
    <rect x="5" y="23" width="20" height="6" rx="2" fill="#2b0d4a"/>
    <circle cx="11" cy="26" r="2" fill="#ff2e97"/><circle cx="19" cy="26" r="1.6" fill="#00e5ff"/>
    <rect x="7" y="33" width="16" height="8" rx="1.5" fill="#12052a"/>
  </g>
  <g fill="#00e5ff" opacity=".9">
    <path d="M270 14 h5 v5 h-5 Z M280 8 h5 v5 h-5 Z M290 14 h5 v5 h-5 Z M280 20 h5 v5 h-5 Z"/>
    <path d="M520 18 h5 v5 h-5 Z M530 12 h5 v5 h-5 Z M540 18 h5 v5 h-5 Z M530 24 h5 v5 h-5 Z"/>
  </g>
  <g fill="#ffe066" opacity=".85">
    <rect x="330" y="10" width="5" height="5"/><rect x="348" y="22" width="4" height="4"/>
    <rect x="366" y="8" width="4" height="4"/><rect x="580" y="14" width="5" height="5"/>
    <rect x="600" y="26" width="4" height="4"/><rect x="616" y="10" width="5" height="5"/>
  </g>
 """),
 ('pagoda', 'Pagoda Night', 'épica', 'light', """
  <defs><linearGradient id="pg-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0b1030"/><stop offset="1" stop-color="#1d2a5c"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#pg-sky)"/>
  <circle cx="330" cy="12" r="8" fill="#f2ecda" opacity=".9"/>
  <g fill="#ffffff" opacity=".7">
    <circle cx="280" cy="8" r="1"/><circle cx="392" cy="6" r="1.1"/><circle cx="600" cy="10" r="1"/>
  </g>
  <g fill="#070a1e">
    <path d="M470 48 V26 h-14 l22 -8 l22 8 h-14 v22 Z"/>
    <path d="M446 30 h64 l-8 -5 h-48 Z M452 20 h52 l-6 -5 h-40 Z"/>
    <path d="M556 48 V30 h-10 l16 -6 l16 6 h-10 v18 Z"/>
    <path d="M538 33 h48 l-6 -4 h-36 Z"/>
  </g>
  <path d="M0 48 L640 48 L640 44 C560 41 480 46 400 43 C320 40 240 46 160 43 C100 41 50 44 0 42 Z"
        fill="#070a1e"/>
  <g fill="#ff9a4a" opacity=".85">
    <rect x="474" y="34" width="4" height="5"/><rect x="560" y="37" width="4" height="4"/>
  </g>
 """),

 # ══ FESTIVAS (pocas, a pedido) ════════════════════════════════════════════
 ('frost', 'Winter Frost', 'festiva', 'dark', """
  <defs><linearGradient id="fr-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f2fbff"/><stop offset="1" stop-color="#c4e6f5"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#fr-sky)"/>
  <g stroke="#7fbdd8" stroke-width="1.4" opacity=".85">
    <g transform="translate(320,14)"><path d="M0 -8 V8 M-7 -4 L7 4 M-7 4 L7 -4"/></g>
    <g transform="translate(430,26)"><path d="M0 -6 V6 M-5 -3 L5 3 M-5 3 L5 -3"/></g>
    <g transform="translate(540,12)"><path d="M0 -7 V7 M-6 -3.5 L6 3.5 M-6 3.5 L6 -3.5"/></g>
    <g transform="translate(600,32)"><path d="M0 -5 V5 M-4 -2.5 L4 2.5 M-4 2.5 L4 -2.5"/></g>
    <g transform="translate(370,38)"><path d="M0 -4 V4 M-3.5 -2 L3.5 2 M-3.5 2 L3.5 -2"/></g>
  </g>
  <path d="M0 48 C80 40 160 46 240 40 C320 34 400 44 480 38 C560 32 600 38 640 34 L640 48 Z"
        fill="#ffffff" opacity=".9"/>
  <g fill="#2f6f8f">
    <path d="M488 40 L494 26 L500 40 Z M482 40 L494 18 L506 40 Z"/>
    <path d="M556 40 L561 30 L566 40 Z M551 40 L561 24 L571 40 Z"/>
  </g>
 """),
 ('muertos', 'Marigold Night', 'festiva', 'light', """
  <defs><linearGradient id="mu-bg" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#150922"/><stop offset="1" stop-color="#3d1a5c"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#mu-bg)"/>
  <g stroke="#7a4bb8" stroke-width="1.4" fill="none" opacity=".7">
    <path d="M256 6 C300 14 340 6 384 14 C428 22 470 12 514 20 C558 28 600 18 640 24"/>
  </g>
  <g fill="#ff9a2e">
    <circle cx="288" cy="12" r="5"/><circle cx="356" cy="10" r="4.4"/>
    <circle cx="426" cy="18" r="5"/><circle cx="496" cy="17" r="4.2"/>
    <circle cx="566" cy="22" r="4.8"/><circle cx="622" cy="22" r="4"/>
  </g>
  <g fill="#ffc46b" opacity=".85">
    <circle cx="288" cy="12" r="2.2"/><circle cx="356" cy="10" r="2"/><circle cx="426" cy="18" r="2.2"/>
    <circle cx="496" cy="17" r="1.9"/><circle cx="566" cy="22" r="2.1"/><circle cx="622" cy="22" r="1.8"/>
  </g>
  <g fill="#ffd88f" opacity=".9">
    <path d="M320 40 h6 v-8 h-6 Z"/><path d="M318 32 h10 l-5 -6 Z"/>
    <path d="M462 42 h5 v-7 h-5 Z"/><path d="M460 35 h9 l-4.5 -5 Z"/>
    <path d="M598 41 h5 v-7 h-5 Z"/><path d="M596 34 h9 l-4.5 -5 Z"/>
  </g>
  <g fill="#ffb347" opacity=".5">
    <circle cx="323" cy="24" r="3"/><circle cx="464" cy="28" r="2.6"/><circle cx="600" cy="27" r="2.8"/>
  </g>
 """),

 # ══ TEMPORADAS ════════════════════════════════════════════════════════════
 # Una por mes, hermana del camo de ese mes (ver TEMPORADAS arriba). Chronicles
 # —la de agosto— vive con las épicas porque nació antes que el calendario.
 # Ninguna dibuja criaturas ni personajes: eso vive en la botarga del camo.
 ('gridiron', 'American Football', 'temporada', 'light', """
  <defs>
    <linearGradient id="gi-sky" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#050a12"/><stop offset="1" stop-color="#0e2136"/></linearGradient>
    <radialGradient id="gi-lamp">
      <stop offset="0" stop-color="#dcecff" stop-opacity=".8"/>
      <stop offset="1" stop-color="#dcecff" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="640" height="48" fill="url(#gi-sky)"/>
  <ellipse cx="339" cy="14" rx="40" ry="17" fill="url(#gi-lamp)"/>
  <ellipse cx="479" cy="12" rx="40" ry="17" fill="url(#gi-lamp)"/>
  <ellipse cx="614" cy="14" rx="34" ry="15" fill="url(#gi-lamp)"/>
  <g fill="#1b2c3d">
    <rect x="326" y="6" width="26" height="6" rx="1.5"/><rect x="337" y="12" width="4" height="16"/>
    <rect x="466" y="4" width="26" height="6" rx="1.5"/><rect x="477" y="10" width="4" height="18"/>
    <rect x="602" y="6" width="24" height="6" rx="1.5"/><rect x="612" y="12" width="4" height="16"/>
  </g>
  <g fill="#eaf4ff" opacity=".9">
    <rect x="329" y="7" width="5" height="4"/><rect x="337" y="7" width="5" height="4"/>
    <rect x="345" y="7" width="5" height="4"/>
    <rect x="469" y="5" width="5" height="4"/><rect x="477" y="5" width="5" height="4"/>
    <rect x="485" y="5" width="5" height="4"/>
    <rect x="605" y="7" width="5" height="4"/><rect x="614" y="7" width="5" height="4"/>
  </g>
  <rect y="26" width="640" height="22" fill="#11331f"/>
  <g fill="#164a29">
    <rect x="256" y="26" width="34" height="22"/><rect x="324" y="26" width="34" height="22"/>
    <rect x="392" y="26" width="34" height="22"/><rect x="460" y="26" width="34" height="22"/>
    <rect x="528" y="26" width="34" height="22"/><rect x="596" y="26" width="34" height="22"/>
  </g>
  <g stroke="#e8f1ea" stroke-width="1.3" opacity=".8">
    <path d="M300 26 L292 48 M360 26 L354 48 M420 26 L418 48 M480 26 L482 48
             M540 26 L546 48 M600 26 L610 48"/>
  </g>
  <g stroke="#e8f1ea" stroke-width=".9" opacity=".4">
    <path d="M268 34 H640 M262 42 H640"/>
  </g>
  <g stroke="#f2c53d" stroke-width="2.6" stroke-linecap="round" fill="none">
    <path d="M566 46 V32 M552 32 H580 M552 32 V12 M580 32 V12"/>
  </g>
 """),
 ('nile', 'Nile', 'temporada', 'dark', """
  <defs>
    <linearGradient id="nl-sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fcefd3"/><stop offset="1" stop-color="#efce97"/></linearGradient>
    <linearGradient id="nl-riv" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2b66ad"/><stop offset="1" stop-color="#103a70"/></linearGradient>
  </defs>
  <rect width="640" height="48" fill="url(#nl-sky)"/>
  <circle cx="600" cy="14" r="10" fill="#e5952f" opacity=".45"/>
  <path d="M292 36 L336 8 L380 36 Z" fill="#d5a55f"/>
  <path d="M336 8 L380 36 L336 36 Z" fill="#b4803c"/>
  <path d="M386 36 L416 17 L446 36 Z" fill="#ddb16c"/>
  <path d="M416 17 L446 36 L416 36 Z" fill="#bd8a44"/>
  <path d="M452 36 L472 24 L492 36 Z" fill="#e4bd80"/>
  <path d="M472 24 L492 36 L472 36 Z" fill="#c79750"/>
  <g><rect x="536" y="14" width="9" height="22" fill="#cfa059"/>
     <path d="M536 14 L540.5 5 L545 14 Z" fill="#ead0a0"/>
     <g fill="#8a6a34" opacity=".8"><rect x="538" y="19" width="5" height="1.6"/>
       <rect x="538" y="24" width="5" height="1.6"/><rect x="538" y="29" width="5" height="1.6"/></g>
  </g>
  <g stroke="#4d7c3c" stroke-width="1.6" stroke-linecap="round">
    <path d="M508 36 V26 M514 36 V30 M520 36 V24 M526 36 V29"/>
  </g>
  <rect y="36" width="640" height="12" fill="url(#nl-riv)"/>
  <g stroke="#84baea" stroke-width="1" opacity=".6" fill="none">
    <path d="M262 40 H358 M378 40 H468 M492 40 H602 M298 44 H418 M446 44 H556 M580 44 H636"/>
  </g>
 """),
 ('colosseum', 'Colosseum', 'temporada', 'light', """
  <defs>
    <linearGradient id="co-bg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#140d05"/><stop offset="1" stop-color="#35210c"/></linearGradient>
    <radialGradient id="co-fire">
      <stop offset="0" stop-color="#ffb347" stop-opacity=".75"/>
      <stop offset="1" stop-color="#ffb347" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="640" height="48" fill="url(#co-bg)"/>
  <rect x="256" y="0" width="384" height="44" fill="#6b4a22"/>
  <rect x="256" y="0" width="384" height="6" fill="#3d2810"/>
  <g fill="#59401b">
    <rect x="264" y="1" width="8" height="4"/><rect x="292" y="1" width="8" height="4"/>
    <rect x="320" y="1" width="8" height="4"/><rect x="348" y="1" width="8" height="4"/>
    <rect x="376" y="1" width="8" height="4"/><rect x="404" y="1" width="8" height="4"/>
    <rect x="432" y="1" width="8" height="4"/><rect x="460" y="1" width="8" height="4"/>
    <rect x="488" y="1" width="8" height="4"/><rect x="516" y="1" width="8" height="4"/>
    <rect x="544" y="1" width="8" height="4"/><rect x="572" y="1" width="8" height="4"/>
    <rect x="600" y="1" width="8" height="4"/><rect x="628" y="1" width="8" height="4"/>
  </g>
  <rect x="256" y="6" width="384" height="3" fill="#8a6229"/>
  <g fill="#120b04">
    <path d="M280 40 V26 A20 14 0 0 1 320 26 V40 Z"/>
    <path d="M338 40 V26 A20 14 0 0 1 378 26 V40 Z"/>
    <path d="M396 40 V26 A20 14 0 0 1 436 26 V40 Z"/>
    <path d="M454 40 V26 A20 14 0 0 1 494 26 V40 Z"/>
    <path d="M512 40 V26 A20 14 0 0 1 552 26 V40 Z"/>
    <path d="M570 40 V26 A20 14 0 0 1 610 26 V40 Z"/>
  </g>
  <g fill="none" stroke="#8a6229" stroke-width="1.6">
    <path d="M280 40 V26 A20 14 0 0 1 320 26 V40"/>
    <path d="M338 40 V26 A20 14 0 0 1 378 26 V40"/>
    <path d="M396 40 V26 A20 14 0 0 1 436 26 V40"/>
    <path d="M454 40 V26 A20 14 0 0 1 494 26 V40"/>
    <path d="M512 40 V26 A20 14 0 0 1 552 26 V40"/>
    <path d="M570 40 V26 A20 14 0 0 1 610 26 V40"/>
  </g>
  <g fill="#a37a35">
    <rect x="296" y="10" width="8" height="4"/><rect x="354" y="10" width="8" height="4"/>
    <rect x="412" y="10" width="8" height="4"/><rect x="470" y="10" width="8" height="4"/>
    <rect x="528" y="10" width="8" height="4"/><rect x="586" y="10" width="8" height="4"/>
  </g>
  <rect x="256" y="40" width="384" height="3" fill="#8a6229"/>
  <rect y="43" width="640" height="5" fill="#7a5c2a"/>
  <g><ellipse cx="329" cy="30" rx="20" ry="15" fill="url(#co-fire)"/>
     <ellipse cx="445" cy="30" rx="20" ry="15" fill="url(#co-fire)"/>
     <ellipse cx="561" cy="30" rx="20" ry="15" fill="url(#co-fire)"/></g>
  <g fill="#4d3512"><rect x="327" y="28" width="4" height="12"/>
    <rect x="443" y="28" width="4" height="12"/><rect x="559" y="28" width="4" height="12"/></g>
  <g fill="#ff9e2c"><path d="M329 17 C335 24 333 28 329 30 C325 28 323 24 329 17 Z"/>
    <path d="M445 17 C451 24 449 28 445 30 C441 28 439 24 445 17 Z"/>
    <path d="M561 17 C567 24 565 28 561 30 C557 28 555 24 561 17 Z"/></g>
  <g fill="#ffe9b5"><path d="M329 23 C332 27 331 29 329 30 C327 29 326 27 329 23 Z"/>
    <path d="M445 23 C448 27 447 29 445 30 C443 29 442 27 445 23 Z"/>
    <path d="M561 23 C564 27 563 29 561 30 C559 29 558 27 561 23 Z"/></g>
 """),
 ('summit', 'Summit', 'temporada', 'dark', """
  <defs><linearGradient id="su-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#d8e9f8"/><stop offset="1" stop-color="#f6fafd"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#su-sky)"/>
  <circle cx="300" cy="12" r="8" fill="#ffffff" opacity=".75"/>
  <path d="M256 48 L318 20 L358 33 L410 12 L470 31 L522 17 L580 33 L640 21 L640 48 Z"
        fill="#b6cbdf"/>
  <g fill="#ffffff" opacity=".9">
    <path d="M318 20 L328 27 L322 27 L312 28 Z"/>
    <path d="M410 12 L422 21 L414 21 L402 23 Z"/>
    <path d="M522 17 L533 25 L526 25 L514 26 Z"/>
  </g>
  <path d="M256 48 L302 32 L342 41 L396 22 L444 38 L502 27 L558 40 L612 29 L640 36 L640 48 Z"
        fill="#8ba7c2"/>
  <g fill="#ffffff">
    <path d="M396 22 L408 30 L400 30 L388 32 Z"/>
    <path d="M502 27 L512 34 L505 34 L494 35 Z"/>
    <path d="M302 32 L310 38 L304 38 L295 39 Z"/>
  </g>
  <g stroke="#6d8aa8" stroke-width="1" opacity=".7" fill="none">
    <path d="M396 22 L392 34 L398 44 M502 27 L498 36 L504 46 M302 32 L300 40 L305 48"/>
  </g>
  <g><rect x="395" y="8" width="1.6" height="14" fill="#5c728a"/>
     <path d="M397 8 L412 12 L397 16 Z" fill="#c8402f"/></g>
 """),
 ('bengal', 'Bengal', 'temporada', 'light', """
  <defs>
    <linearGradient id="be-bg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#04100a"/><stop offset=".55" stop-color="#0a1d13"/>
      <stop offset="1" stop-color="#12301c"/></linearGradient>
    <radialGradient id="be-ember">
      <stop offset="0" stop-color="#ff8f33" stop-opacity=".6"/>
      <stop offset="1" stop-color="#ff8f33" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="640" height="48" fill="url(#be-bg)"/>
  <ellipse cx="512" cy="46" rx="128" ry="22" fill="url(#be-ember)"/>
  <g fill="#1d4127">
    <rect x="272" y="0" width="7" height="48"/><rect x="300" y="0" width="5" height="48"/>
    <rect x="344" y="0" width="8" height="48"/><rect x="376" y="0" width="5" height="48"/>
    <rect x="416" y="0" width="7" height="48"/><rect x="452" y="0" width="6" height="48"/>
    <rect x="492" y="0" width="8" height="48"/><rect x="528" y="0" width="5" height="48"/>
    <rect x="566" y="0" width="7" height="48"/><rect x="606" y="0" width="6" height="48"/>
  </g>
  <g fill="#2f6b3c" opacity=".9">
    <rect x="272" y="0" width="2" height="48"/><rect x="344" y="0" width="2" height="48"/>
    <rect x="416" y="0" width="2" height="48"/><rect x="492" y="0" width="2" height="48"/>
    <rect x="566" y="0" width="2" height="48"/>
  </g>
  <g fill="#c96a26" opacity=".75">
    <rect x="497" y="0" width="3" height="48"/><rect x="571" y="0" width="2" height="48"/>
    <rect x="421" y="0" width="2" height="48"/><rect x="610" y="0" width="2" height="48"/>
  </g>
  <g fill="#0a1a10" opacity=".85">
    <rect x="271" y="14" width="9" height="2"/><rect x="271" y="33" width="9" height="2"/>
    <rect x="343" y="9" width="10" height="2"/><rect x="343" y="29" width="10" height="2"/>
    <rect x="415" y="18" width="9" height="2"/><rect x="415" y="37" width="9" height="2"/>
    <rect x="491" y="12" width="10" height="2"/><rect x="491" y="31" width="10" height="2"/>
    <rect x="565" y="21" width="9" height="2"/><rect x="565" y="40" width="9" height="2"/>
  </g>
  <g stroke="#2a6238" stroke-width="1.8" fill="none" stroke-linecap="round" opacity=".9">
    <path d="M280 12 C296 8 306 12 314 18 M352 26 C368 22 378 26 386 32
             M424 8 C440 4 450 8 458 14 M500 30 C516 26 526 30 534 36
             M574 16 C590 12 600 16 608 22"/>
  </g>
  <g fill="#ffab4d">
    <circle cx="470" cy="34" r="1.3"/><circle cx="540" cy="26" r="1"/>
    <circle cx="596" cy="36" r="1.2"/><circle cx="440" cy="42" r="1"/>
    <circle cx="512" cy="18" r=".9"/>
  </g>
 """),
 ('olympus', 'Olympus', 'temporada', 'dark', """
  <defs><linearGradient id="ol-bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f8f5ec"/><stop offset="1" stop-color="#e3dccb"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#ol-bg)"/>
  <g stroke="#d9d1bd" stroke-width="1" fill="none" opacity=".8">
    <path d="M0 30 C40 26 70 34 110 30 C150 26 180 34 220 30"/>
    <path d="M0 40 C50 36 90 42 140 38 C190 34 220 40 250 37"/>
  </g>
  <rect x="256" y="13" width="384" height="29" fill="#8b7b5b"/>
  <rect x="256" y="4" width="384" height="9" fill="#f4efe1"/>
  <rect x="256" y="13" width="384" height="2.6" fill="#9c927a"/>
  <g fill="#cdc3a9">
    <rect x="262" y="5" width="3" height="7"/><rect x="286" y="5" width="3" height="7"/>
    <rect x="310" y="5" width="3" height="7"/><rect x="334" y="5" width="3" height="7"/>
    <rect x="358" y="5" width="3" height="7"/><rect x="382" y="5" width="3" height="7"/>
    <rect x="406" y="5" width="3" height="7"/><rect x="430" y="5" width="3" height="7"/>
    <rect x="454" y="5" width="3" height="7"/><rect x="478" y="5" width="3" height="7"/>
    <rect x="502" y="5" width="3" height="7"/><rect x="526" y="5" width="3" height="7"/>
    <rect x="550" y="5" width="3" height="7"/><rect x="574" y="5" width="3" height="7"/>
    <rect x="598" y="5" width="3" height="7"/><rect x="622" y="5" width="3" height="7"/>
  </g>
  <rect x="256" y="2" width="384" height="2.4" fill="#c9a227"/>
  <g>
    <g fill="#fdfaf2"><rect x="284" y="16" width="17" height="26"/><rect x="336" y="16" width="17" height="26"/>
      <rect x="388" y="16" width="17" height="26"/><rect x="440" y="16" width="17" height="26"/>
      <rect x="492" y="16" width="17" height="26"/><rect x="544" y="16" width="17" height="26"/>
      <rect x="596" y="16" width="17" height="26"/></g>
    <g fill="#efe8d6"><rect x="280" y="15" width="25" height="4"/><rect x="332" y="15" width="25" height="4"/>
      <rect x="384" y="15" width="25" height="4"/><rect x="436" y="15" width="25" height="4"/>
      <rect x="488" y="15" width="25" height="4"/><rect x="540" y="15" width="25" height="4"/>
      <rect x="592" y="15" width="25" height="4"/></g>
    <g stroke="#b7ad92" stroke-width="1.1">
      <path d="M288 20 V42 M293 20 V42 M298 20 V42 M340 20 V42 M345 20 V42 M350 20 V42
               M392 20 V42 M397 20 V42 M402 20 V42 M444 20 V42 M449 20 V42 M454 20 V42
               M496 20 V42 M501 20 V42 M506 20 V42 M548 20 V42 M553 20 V42 M558 20 V42
               M600 20 V42 M605 20 V42 M610 20 V42"/></g>
    <g fill="#a1977e"><rect x="299" y="16" width="4" height="26"/>
      <rect x="351" y="16" width="4" height="26"/><rect x="403" y="16" width="4" height="26"/>
      <rect x="455" y="16" width="4" height="26"/><rect x="507" y="16" width="4" height="26"/>
      <rect x="559" y="16" width="4" height="26"/><rect x="611" y="16" width="4" height="26"/></g>
  </g>
  <rect y="42" width="640" height="3" fill="#efe8d6"/>
  <rect y="45" width="640" height="3" fill="#d3c9b0"/>
 """),
 ('quetzal', 'Quetzalcóatl', 'temporada', 'light', """
  <defs>
    <linearGradient id="qz-bg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#042f2d"/><stop offset="1" stop-color="#0a6053"/></linearGradient>
    <radialGradient id="qz-sun">
      <stop offset="0" stop-color="#ffe6a0" stop-opacity=".95"/>
      <stop offset=".45" stop-color="#f2c04a" stop-opacity=".5"/>
      <stop offset="1" stop-color="#f2c04a" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="640" height="48" fill="url(#qz-bg)"/>
  <circle cx="336" cy="22" r="26" fill="url(#qz-sun)"/>
  <circle cx="336" cy="22" r="7.5" fill="#f7d271"/>
  <g fill="#0b4a42"><rect x="256" y="0" width="384" height="7"/></g>
  <g stroke="#e0b64a" stroke-width="1.6" fill="none" opacity=".85">
    <path d="M262 6 V2 H272 V6 H282 V2 H292 V6 H302 V2 H312 V6 H322 V2 H332 V6 H342 V2 H352 V6
             H362 V2 H372 V6 H382 V2 H392 V6 H402 V2 H412 V6 H422 V2 H432 V6 H442 V2 H452 V6
             H462 V2 H472 V6 H482 V2 H492 V6 H502 V2 H512 V6 H522 V2 H532 V6 H542 V2 H552 V6
             H562 V2 H572 V6 H582 V2 H592 V6 H602 V2 H612 V6 H622 V2 H632 V6"/>
  </g>
  <g>
    <path d="M398 44 H606 L594 37 H410 Z" fill="#a44e2b"/>
    <path d="M410 37 H594 L584 30 H420 Z" fill="#b45932"/>
    <path d="M420 30 H584 L574 23 H430 Z" fill="#c26439"/>
    <path d="M430 23 H574 L564 16 H440 Z" fill="#cf7043"/>
    <rect x="470" y="7" width="64" height="9" fill="#c26439"/>
    <rect x="468" y="4" width="68" height="3" fill="#cf7043"/>
    <rect x="494" y="10" width="16" height="6" fill="#3d1a0e"/>
  </g>
  <g fill="#d98c52"><rect x="486" y="16" width="32" height="28"/></g>
  <g stroke="#a04829" stroke-width="1" opacity=".85">
    <path d="M486 21 H518 M486 26 H518 M486 31 H518 M486 36 H518 M486 41 H518"/>
  </g>
  <g fill="#a04829">
    <path d="M486 44 V16 L478 22 V28 L470 34 V40 L462 44 Z"/>
    <path d="M518 44 V16 L526 22 V28 L534 34 V40 L542 44 Z"/>
  </g>
  <g fill="none" stroke="#e0955c" stroke-width="1" opacity=".8">
    <path d="M486 16 L478 22 V28 L470 34 V40 L462 44"/>
    <path d="M518 16 L526 22 V28 L534 34 V40 L542 44"/>
  </g>
  <g fill="#e8b93f" opacity=".9">
    <rect x="468" y="15" width="68" height="2"/>
  </g>
 """),
 ('baseball', 'Baseball', 'temporada', 'dark', """
  <defs>
    <linearGradient id="bb-turf" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#8fc97c"/><stop offset=".55" stop-color="#67ae59"/>
      <stop offset="1" stop-color="#4f9a48"/></linearGradient>
  </defs>
  <rect width="640" height="48" fill="#cfe7f6"/>
  <rect y="13" width="640" height="35" fill="url(#bb-turf)"/>
  <g fill="#ffffff" opacity=".14">
    <rect x="256" y="13" width="30" height="35"/><rect x="316" y="13" width="30" height="35"/>
    <rect x="376" y="13" width="30" height="35"/><rect x="436" y="13" width="30" height="35"/>
    <rect x="496" y="13" width="30" height="35"/><rect x="556" y="13" width="30" height="35"/>
    <rect x="616" y="13" width="24" height="35"/>
  </g>
  <rect y="9" width="640" height="5" fill="#2f6b39"/>
  <rect y="8" width="640" height="1.6" fill="#f0d84e"/>
  <g fill="#c9884b"><path d="M516 16 L608 29 L516 42 L424 29 Z"/></g>
  <g fill="#63ab55"><path d="M516 21 L596 29 L516 37 L436 29 Z"/></g>
  <g fill="#ffffff">
    <path d="M516 15 L521 18 L516 21 L511 18 Z"/>
    <path d="M602 26 L608 29 L602 32 L596 29 Z"/>
    <path d="M516 37 L521 40 L516 43 L511 40 Z"/>
    <path d="M430 26 L436 29 L430 32 L424 29 Z"/>
  </g>
  <ellipse cx="516" cy="29" rx="8" ry="4" fill="#c9884b"/>
  <ellipse cx="516" cy="29" rx="3.4" ry="1.8" fill="#d99a5d"/>
  <g stroke="#ffffff" stroke-width="1.8" opacity=".9">
    <path d="M522 41 L572 47 M510 41 L460 47"/>
  </g>
  <g fill="#e6503f" opacity=".85">
    <path d="M300 9 L308 6 L300 3 Z"/><path d="M340 9 L348 6 L340 3 Z"/>
    <path d="M380 9 L388 6 L380 3 Z"/><path d="M420 9 L428 6 L420 3 Z"/>
    <path d="M460 9 L468 6 L460 3 Z"/><path d="M500 9 L508 6 L500 3 Z"/>
    <path d="M540 9 L548 6 L540 3 Z"/><path d="M580 9 L588 6 L580 3 Z"/>
  </g>
 """),
 ('apiarist', 'Apiarist', 'temporada', 'dark', """
  <defs>
    <linearGradient id="ap-bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fdf6e4"/><stop offset="1" stop-color="#f3e2bc"/></linearGradient>
    <path id="ap-h" d="M0 -9 L7.8 -4.5 L7.8 4.5 L0 9 L-7.8 4.5 L-7.8 -4.5 Z"/>
  </defs>
  <rect width="640" height="48" fill="url(#ap-bg)"/>
  <g fill="#f2c85c" fill-opacity=".55" stroke="#d9a03a" stroke-width="1.2">
    <use href="#ap-h" x="290" y="8"/><use href="#ap-h" x="306" y="8"/><use href="#ap-h" x="322" y="8"/>
    <use href="#ap-h" x="338" y="8"/><use href="#ap-h" x="354" y="8"/><use href="#ap-h" x="370" y="8"/>
    <use href="#ap-h" x="386" y="8"/><use href="#ap-h" x="402" y="8"/><use href="#ap-h" x="418" y="8"/>
    <use href="#ap-h" x="434" y="8"/><use href="#ap-h" x="450" y="8"/><use href="#ap-h" x="466" y="8"/>
    <use href="#ap-h" x="482" y="8"/><use href="#ap-h" x="498" y="8"/>
    <use href="#ap-h" x="298" y="22"/><use href="#ap-h" x="314" y="22"/><use href="#ap-h" x="330" y="22"/>
    <use href="#ap-h" x="346" y="22"/><use href="#ap-h" x="362" y="22"/><use href="#ap-h" x="378" y="22"/>
    <use href="#ap-h" x="394" y="22"/><use href="#ap-h" x="410" y="22"/><use href="#ap-h" x="426" y="22"/>
    <use href="#ap-h" x="442" y="22"/><use href="#ap-h" x="458" y="22"/><use href="#ap-h" x="474" y="22"/>
    <use href="#ap-h" x="490" y="22"/>
    <use href="#ap-h" x="290" y="36"/><use href="#ap-h" x="306" y="36"/><use href="#ap-h" x="322" y="36"/>
    <use href="#ap-h" x="338" y="36"/><use href="#ap-h" x="354" y="36"/><use href="#ap-h" x="370" y="36"/>
    <use href="#ap-h" x="386" y="36"/><use href="#ap-h" x="402" y="36"/><use href="#ap-h" x="418" y="36"/>
    <use href="#ap-h" x="434" y="36"/><use href="#ap-h" x="450" y="36"/><use href="#ap-h" x="466" y="36"/>
    <use href="#ap-h" x="482" y="36"/><use href="#ap-h" x="498" y="36"/>
  </g>
  <g>
    <rect x="556" y="18" width="52" height="9" fill="#e8dcc0" stroke="#b9a473" stroke-width="1"/>
    <rect x="556" y="27" width="52" height="9" fill="#f2e8d0" stroke="#b9a473" stroke-width="1"/>
    <rect x="556" y="36" width="52" height="9" fill="#e8dcc0" stroke="#b9a473" stroke-width="1"/>
    <path d="M550 18 H614 L606 12 H558 Z" fill="#c9a55f"/>
    <rect x="570" y="41" width="24" height="2.4" fill="#8a7038"/>
  </g>
  <g stroke="#c08b2c" stroke-width="1" fill="none" stroke-dasharray="2 4" opacity=".85">
    <path d="M508 20 C528 12 540 26 552 20 M512 34 C532 40 542 28 554 32"/>
  </g>
 """),
 ('welder', 'Welder', 'temporada', 'light', """
  <defs>
    <linearGradient id="we-bg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#12161c"/><stop offset="1" stop-color="#242c36"/></linearGradient>
    <radialGradient id="we-arc">
      <stop offset="0" stop-color="#f2fbff" stop-opacity=".95"/>
      <stop offset=".38" stop-color="#7fc7ff" stop-opacity=".5"/>
      <stop offset="1" stop-color="#3a7fd5" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="640" height="48" fill="url(#we-bg)"/>
  <g stroke="#2b333e" stroke-width="2.4" opacity=".8">
    <path d="M256 48 L292 0 M286 48 L322 0 M316 48 L352 0 M346 48 L382 0 M376 48 L412 0
             M406 48 L442 0 M436 48 L472 0 M466 48 L502 0 M496 48 L532 0 M526 48 L562 0
             M556 48 L592 0 M586 48 L622 0 M616 48 L652 0"/>
  </g>
  <rect x="256" y="22" width="384" height="1.6" fill="#0b0e13"/>
  <rect x="256" y="34" width="384" height="1.6" fill="#0b0e13"/>
  <path fill="none" stroke="#8d97a2" stroke-width="7" stroke-linecap="round"
        d="M262 29 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0
           q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0
           q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0
           q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0"/>
  <path fill="none" stroke="#c8d2dc" stroke-width="2" stroke-linecap="round" opacity=".75"
        d="M262 27.5 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0
           q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0
           q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0
           q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0 q7 -5 14 0"/>
  <ellipse cx="546" cy="29" rx="46" ry="22" fill="url(#we-arc)"/>
  <circle cx="546" cy="29" r="4" fill="#ffffff"/>
  <g stroke="#ffc46b" stroke-width="1.3" stroke-linecap="round" opacity=".9">
    <path d="M546 29 L522 14 M546 29 L560 10 M546 29 L578 18 M546 29 L590 30
             M546 29 L570 44 M546 29 L520 42 M546 29 L504 22"/>
  </g>
  <g fill="#ffe3a8">
    <circle cx="520" cy="13" r="1.2"/><circle cx="562" cy="8" r="1"/><circle cx="582" cy="16" r="1.1"/>
    <circle cx="594" cy="31" r="1"/><circle cx="572" cy="46" r="1.1"/><circle cx="502" cy="20" r="1"/>
  </g>
 """),
 ('zeppelin', 'Zeppelin', 'temporada', 'dark', """
  <defs>
    <linearGradient id="ze-sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f8ead0"/><stop offset="1" stop-color="#e2c79c"/></linearGradient>
    <linearGradient id="ze-hull" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e6c184"/><stop offset=".45" stop-color="#b8863f"/>
      <stop offset="1" stop-color="#8a5f28"/></linearGradient>
  </defs>
  <rect width="640" height="48" fill="url(#ze-sky)"/>
  <circle cx="296" cy="12" r="11" fill="#f6d99b" opacity=".8"/>
  <g fill="#fbf2df" opacity=".75">
    <ellipse cx="300" cy="40" rx="64" ry="7"/><ellipse cx="430" cy="44" rx="70" ry="7"/>
    <ellipse cx="576" cy="38" rx="56" ry="6"/>
  </g>
  <g transform="translate(468,21)">
    <ellipse rx="84" ry="13" fill="url(#ze-hull)"/>
    <ellipse rx="84" ry="13" fill="none" stroke="#79521f" stroke-width="1"/>
    <g stroke="#8a6229" stroke-width="1" fill="none" opacity=".85">
      <path d="M-56 -11.5 C-50 0 -50 0 -56 11.5 M-28 -12.8 C-22 0 -22 0 -28 12.8
               M0 -13 C6 0 6 0 0 13 M28 -12.8 C34 0 34 0 28 12.8 M56 -11.5 C62 0 62 0 56 11.5"/>
      <path d="M-84 0 H84"/>
    </g>
    <path d="M-84 0 L-98 -7 L-94 0 L-98 7 Z" fill="#9a6c2c"/>
    <path d="M-80 -4 L-96 -12 L-78 -9 Z" fill="#8a5f28"/>
    <path d="M-80 4 L-96 12 L-78 9 Z" fill="#8a5f28"/>
    <rect x="-12" y="13" width="24" height="7" rx="2.4" fill="#6d4a1e"/>
    <g stroke="#6d4a1e" stroke-width="1"><path d="M-8 13 V10 M8 13 V10"/></g>
    <g fill="#f6e3bb"><rect x="-8" y="15" width="4" height="3"/><rect x="-1" y="15" width="4" height="3"/>
      <rect x="6" y="15" width="4" height="3"/></g>
  </g>
  <rect y="44" width="640" height="4" fill="#c39a53"/>
  <g fill="#8a6229" opacity=".8">
    <circle cx="270" cy="46" r="1.2"/><circle cx="310" cy="46" r="1.2"/><circle cx="350" cy="46" r="1.2"/>
    <circle cx="390" cy="46" r="1.2"/><circle cx="430" cy="46" r="1.2"/><circle cx="470" cy="46" r="1.2"/>
    <circle cx="510" cy="46" r="1.2"/><circle cx="550" cy="46" r="1.2"/><circle cx="590" cy="46" r="1.2"/>
    <circle cx="630" cy="46" r="1.2"/>
  </g>
 """),
]

PAGE = """<!doctype html><meta charset="utf-8">
<style>
 body{margin:0;font-family:'Inter',system-ui,sans-serif;background:#eef1f6;padding:22px 26px;}
 .cap{font-size:11.5px;font-weight:800;color:#5a6172;margin-bottom:5px;letter-spacing:.03em;}
 .cap span{font-weight:600;opacity:.7;}
 .post{background:#fff;border:1px solid #e4e6ec;border-radius:12px;padding:11px 13px;
       margin-bottom:14px;max-width:660px;}
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


# Lienzo real de la placa: MUY ancho y bajo. Autorar en 420x56 y estirar a
# 624x48 deformaba el doble en horizontal — por eso el dragón salía aplastado.
CANVAS_VIEWBOX = '0 0 640 48'


def build(slugs):
    body = []
    n = 0
    for slug, name, family, ink, art in PLATES:
        if slug not in slugs:
            continue
        n += 1
        name = '%02d. %s' % (n, name)
        body.append(
            '<div><div class="cap">%s <span>· %s · fondo %s</span></div>'
            '<div class="post"><div class="top ink-%s">'
            '<div class="plate"><svg viewBox="%s" preserveAspectRatio="none">%s</svg></div>'
            '<div class="av">M</div><span class="medal"></span>'
            '<span class="nm">marcus_dw</span><span class="chip">🔥12</span>'
            '<span class="pill">Trading Legend</span></div>'
            '<div class="ttl">Sweep del PDL y reclaim</div></div></div>'
            % (name, family, 'oscuro' if ink == 'light' else 'claro', ink,
               CANVAS_VIEWBOX, art))
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
