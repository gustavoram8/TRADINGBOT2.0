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
# EN o CERCA de la festividad (pedido 2026-08-02: espejo de los camos
# festivos). Fechas estipuladas: newyear 01-01 · valentine 02-14 · lucky
# 03-17 · easter (móvil, la fija el dueño cada año) · fourth 07-04 · hallow
# 10-31 · muertos 11-02 · frost 12-21 (solsticio) · santa 12-25.
FESTIVOS = ['frost', 'muertos', 'santa', 'hallow', 'fourth', 'lucky',
            'valentine', 'easter', 'newyear']

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

 # ══ FESTIVAS de TIENDA (2026-08-02): una por cada festividad que ya tiene
 #    camo. Ventana de compra de 24h en la fecha estipulada (ver FESTIVOS).
 #    Sin personajes ni criaturas: objetos y escenografía solamente. ═════════
 ('santa', 'Christmas Eve', 'festiva', 'light', """
  <defs><linearGradient id="sa-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0a1428"/><stop offset="1" stop-color="#152a4d"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#sa-sky)"/>
  <circle cx="300" cy="12" r="7" fill="#f4f0e2" opacity=".8"/>
  <g fill="#eef4fb" opacity=".9">
    <circle cx="340" cy="8" r="1"/><circle cx="420" cy="5" r="1.1"/><circle cx="505" cy="9" r="1"/>
    <circle cx="580" cy="4" r="1"/><circle cx="630" cy="12" r="1.1"/><circle cx="376" cy="14" r=".9"/>
  </g>
  <path d="M0 44 C90 40 180 46 280 42 C380 38 480 45 560 41 C600 39 620 42 640 40 L640 48 L0 48 Z"
        fill="#f2f6fb"/>
  <g fill="#123420">
    <path d="M356 42 L372 14 L388 42 Z"/><path d="M360 32 L372 10 L384 32 Z"/>
    <path d="M448 42 L462 18 L476 42 Z"/><path d="M452 34 L462 15 L472 34 Z"/>
    <path d="M540 42 L552 22 L564 42 Z"/>
  </g>
  <g fill="#1d4a2e">
    <path d="M352 42 L372 20 L392 42 Z" opacity=".55"/>
    <path d="M444 42 L462 24 L480 42 Z" opacity=".55"/>
  </g>
  <g>
    <circle cx="366" cy="30" r="1.4" fill="#ffd76a"/><circle cx="377" cy="24" r="1.3" fill="#ff8a7a"/>
    <circle cx="371" cy="37" r="1.3" fill="#8fd0ff"/><circle cx="458" cy="30" r="1.3" fill="#ffd76a"/>
    <circle cx="466" cy="36" r="1.3" fill="#ff8a7a"/><circle cx="553" cy="32" r="1.2" fill="#8fd0ff"/>
  </g>
  <g>
    <rect x="596" y="34" width="13" height="10" rx="1" fill="#b8412f"/>
    <rect x="601.5" y="34" width="2.4" height="10" fill="#ffd76a"/>
    <rect x="614" y="37" width="10" height="7" rx="1" fill="#2f6ea8"/>
    <rect x="618" y="37" width="2" height="7" fill="#f2f6fb"/>
  </g>
 """),
 ('hallow', 'All Hallows', 'festiva', 'light', """
  <defs><linearGradient id="hw-sky" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#0e0716"/><stop offset="1" stop-color="#2a1240"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#hw-sky)"/>
  <circle cx="560" cy="12" r="10" fill="#f2e6c9" opacity=".9"/>
  <circle cx="556" cy="10" r="8.6" fill="#1d0f30"/>
  <path d="M0 46 H640 M0 46" stroke="#000" stroke-width="0"/>
  <rect y="44" width="640" height="4" fill="#120a1e"/>
  <g stroke="#241536" stroke-width="2.4">
    <path d="M300 44 V32 M316 44 V30 M332 44 V33 M348 44 V31 M364 44 V33"/>
    <path d="M296 36 H368" stroke-width="1.6"/>
  </g>
  <g stroke="#1c1029" stroke-width="2" fill="none">
    <path d="M608 44 V20 C608 14 604 10 600 8 M608 24 C614 22 618 18 618 12 M608 30 C602 28 598 24 598 20"/>
  </g>
  <g>
    <ellipse cx="420" cy="38" rx="13" ry="10" fill="#e8760f"/>
    <path d="M420 27 C418 24 421 22 423 23" stroke="#3f5a2a" stroke-width="2" fill="none"/>
    <g fill="#ffd76a"><path d="M413 35 L417 38 L409 38 Z"/><path d="M427 35 L431 38 L423 38 Z"/>
      <path d="M413 41 L420 45 L427 41 L424 43 L420 41 L416 43 Z"/></g>
    <ellipse cx="470" cy="40" rx="10" ry="8" fill="#c9640d"/>
    <path d="M470 31 C468 29 470 27 472 28" stroke="#3f5a2a" stroke-width="1.8" fill="none"/>
    <g fill="#ffcf5c"><path d="M465 38 L468 40 L462 40 Z"/><path d="M475 38 L478 40 L472 40 Z"/>
      <path d="M464 43 L470 45 L476 43 L470 44.6 Z"/></g>
  </g>
  <g fill="#0a0512" opacity=".9">
    <path d="M380 12 C384 8 388 8 390 10 C392 8 396 8 400 12 C396 12 392 11 390 13 C388 11 384 12 380 12 Z"/>
    <path d="M500 8 C503 5 506 5 508 7 C510 5 513 5 516 8 C513 8 510 7 508 9 C506 7 503 8 500 8 Z"/>
  </g>
 """),
 ('fourth', 'Stars and Stripes', 'festiva', 'light', """
  <defs><linearGradient id="fj-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#0a1230"/><stop offset="1" stop-color="#1c2c5c"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#fj-sky)"/>
  <g stroke="#ffd76a" stroke-width="1.1" stroke-linecap="round" opacity=".95">
    <g transform="translate(380,16)">
      <path d="M0 0 L0 -11 M0 0 L8 -8 M0 0 L11 0 M0 0 L8 8 M0 0 L0 11 M0 0 L-8 8 M0 0 L-11 0 M0 0 L-8 -8"/>
    </g>
    <g transform="translate(500,10)" stroke="#ff7a6a">
      <path d="M0 0 L0 -9 M0 0 L7 -6 M0 0 L9 0 M0 0 L7 6 M0 0 L0 9 M0 0 L-7 6 M0 0 L-9 0 M0 0 L-7 -6"/>
    </g>
    <g transform="translate(590,18)" stroke="#8fd0ff">
      <path d="M0 0 L0 -10 M0 0 L7 -7 M0 0 L10 0 M0 0 L7 7 M0 0 L0 10 M0 0 L-7 7 M0 0 L-10 0 M0 0 L-7 -7"/>
    </g>
  </g>
  <g fill="#ffd76a"><circle cx="380" cy="16" r="1.6"/><circle cx="590" cy="18" r="1.4"/></g>
  <g fill="#ff7a6a"><circle cx="500" cy="10" r="1.4"/></g>
  <g fill="#eef4fb" opacity=".85">
    <circle cx="330" cy="8" r="1"/><circle cx="445" cy="6" r="1"/><circle cx="548" cy="7" r="1"/>
    <circle cx="622" cy="9" r="1"/>
  </g>
  <!-- banderines triangulares (bunting) -->
  <path d="M256 38 C320 34 384 42 448 38 C512 34 576 42 640 38" stroke="#e8ecf4"
        stroke-width="1.4" fill="none"/>
  <g>
    <path d="M276 37 L282 45 L288 36 Z" fill="#b8412f"/>
    <path d="M308 36 L314 44 L320 36 Z" fill="#eef4fb"/>
    <path d="M340 37 L346 45 L352 37 Z" fill="#2f4d9c"/>
    <path d="M372 38 L378 46 L384 37 Z" fill="#b8412f"/>
    <path d="M404 37 L410 45 L416 36 Z" fill="#eef4fb"/>
    <path d="M436 36 L442 44 L448 37 Z" fill="#2f4d9c"/>
    <path d="M468 37 L474 45 L480 37 Z" fill="#b8412f"/>
    <path d="M500 38 L506 46 L512 37 Z" fill="#eef4fb"/>
    <path d="M532 37 L538 45 L544 36 Z" fill="#2f4d9c"/>
    <path d="M564 36 L570 44 L576 37 Z" fill="#b8412f"/>
    <path d="M596 37 L602 45 L608 37 Z" fill="#eef4fb"/>
    <path d="M626 38 L632 46 L638 37 Z" fill="#2f4d9c"/>
  </g>
 """),
 ('lucky', 'Pot of Gold', 'festiva', 'light', """
  <defs>
    <linearGradient id="lk-bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0c2e1c"/><stop offset="1" stop-color="#155232"/></linearGradient>
  </defs>
  <rect width="640" height="48" fill="url(#lk-bg)"/>
  <!-- arcoiris que cae en la olla -->
  <g fill="none" stroke-linecap="round">
    <path d="M340 48 C380 2 520 2 560 40" stroke="#d94f3d" stroke-width="4"/>
    <path d="M340 48 C380 8 516 8 556 42" stroke="#e8a23d" stroke-width="4" transform="translate(0,4)"/>
    <path d="M340 48 C382 14 512 14 552 44" stroke="#e8d23d" stroke-width="4" transform="translate(0,8)"/>
  </g>
  <g>
    <path d="M544 34 C544 42 552 46 562 46 C572 46 580 42 580 34 Z" fill="#141017"/>
    <ellipse cx="562" cy="34" rx="18" ry="4" fill="#241c2b"/>
    <g fill="#ffd347">
      <circle cx="554" cy="32" r="2.6"/><circle cx="562" cy="30" r="2.8"/><circle cx="570" cy="32" r="2.6"/>
      <circle cx="558" cy="28" r="2.2"/><circle cx="566" cy="28" r="2.2"/>
    </g>
  </g>
  <g fill="#2f8a4e">
    <g transform="translate(292,20)"><path d="M0 0 C-4 -6 2 -10 3 -4 C4 -10 10 -6 6 0 C10 2 6 8 3 4 C0 8 -4 2 0 0 Z"/></g>
    <g transform="translate(400,36) scale(.8)"><path d="M0 0 C-4 -6 2 -10 3 -4 C4 -10 10 -6 6 0 C10 2 6 8 3 4 C0 8 -4 2 0 0 Z"/></g>
    <g transform="translate(470,14) scale(.7)"><path d="M0 0 C-4 -6 2 -10 3 -4 C4 -10 10 -6 6 0 C10 2 6 8 3 4 C0 8 -4 2 0 0 Z"/></g>
    <g transform="translate(614,20) scale(.75)"><path d="M0 0 C-4 -6 2 -10 3 -4 C4 -10 10 -6 6 0 C10 2 6 8 3 4 C0 8 -4 2 0 0 Z"/></g>
  </g>
  <g fill="#ffd347" opacity=".7">
    <circle cx="380" cy="10" r="1"/><circle cx="440" cy="24" r="1"/><circle cx="520" cy="12" r="1"/>
    <circle cx="600" cy="38" r="1"/>
  </g>
 """),
 ('valentine', 'Sweetheart', 'festiva', 'dark', """
  <defs><linearGradient id="vt-bg" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#fdeef2"/><stop offset="1" stop-color="#f9dbe4"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#vt-bg)"/>
  <path d="M256 40 C330 30 400 44 470 34 C540 24 590 36 640 28" stroke="#e8a8bb"
        stroke-width="1.4" fill="none" opacity=".8"/>
  <g fill="#d94f6e">
    <path d="M470 18 C466 12 456 13 456 20 C456 26 465 31 470 34 C475 31 484 26 484 20 C484 13 474 12 470 18 Z"/>
  </g>
  <g fill="#e8748f">
    <path d="M540 26 C537 22 530 23 530 28 C530 32 536 35 540 37 C544 35 550 32 550 28 C550 23 543 22 540 26 Z"/>
    <path d="M382 30 C379.6 27 374 27.6 374 31.6 C374 34.8 379 37.4 382 39 C385 37.4 390 34.8 390 31.6 C390 27.6 384.4 27 382 30 Z"/>
  </g>
  <g fill="#f0a4b8">
    <path d="M600 14 C598 11.4 593.6 11.9 593.6 15.4 C593.6 18.2 597.6 20.4 600 21.8 C602.4 20.4 606.4 18.2 606.4 15.4 C606.4 11.9 602 11.4 600 14 Z"/>
    <path d="M430 8 C428.4 6 424.9 6.4 424.9 9.2 C424.9 11.4 428 13.2 430 14.3 C432 13.2 435.1 11.4 435.1 9.2 C435.1 6.4 431.6 6 430 8 Z"/>
    <path d="M320 16 C318.4 14 314.9 14.4 314.9 17.2 C314.9 19.4 318 21.2 320 22.3 C322 21.2 325.1 19.4 325.1 17.2 C325.1 14.4 321.6 14 320 16 Z"/>
  </g>
  <g fill="#c9375c" opacity=".55">
    <circle cx="356" cy="42" r="1.2"/><circle cx="505" cy="10" r="1.2"/><circle cx="572" cy="42" r="1.2"/>
    <circle cx="626" cy="38" r="1.2"/><circle cx="300" cy="34" r="1.1"/>
  </g>
 """),
 ('easter', 'Egg Hunt', 'festiva', 'dark', """
  <defs><linearGradient id="ea-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#eef7fb"/><stop offset="1" stop-color="#dff0e6"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#ea-sky)"/>
  <path d="M0 44 C110 40 220 46 330 42 C440 38 550 45 640 41 L640 48 L0 48 Z" fill="#a8d9a0"/>
  <g stroke="#7fbf78" stroke-width="1.6" stroke-linecap="round">
    <path d="M300 44 V38 M306 44 V36 M312 44 V39 M420 43 V37 M426 43 V35 M540 44 V38 M546 44 V36"/>
  </g>
  <g>
    <ellipse cx="372" cy="36" rx="10" ry="12" fill="#8fc7e8"/>
    <path d="M364 36 C368 33 376 33 380 36 M364 41 C368 38 376 38 380 41" stroke="#f4f9fd"
          stroke-width="1.6" fill="none"/>
    <ellipse cx="470" cy="37" rx="9" ry="11" fill="#f2c85c"/>
    <g fill="#e8925c"><circle cx="466" cy="33" r="1.7"/><circle cx="474" cy="38" r="1.7"/>
      <circle cx="468" cy="42" r="1.5"/></g>
    <ellipse cx="598" cy="36" rx="10" ry="12" fill="#d9a8d4"/>
    <path d="M590 36 L594 39 L598 34 L602 39 L606 36" stroke="#f7eef6" stroke-width="1.6" fill="none"/>
  </g>
  <g>
    <g stroke="#4d9a48" stroke-width="1.6" fill="none">
      <path d="M330 44 C330 38 328 32 324 28 M330 44 C330 38 333 33 337 30"/>
    </g>
    <path d="M324 28 C320 24 322 18 327 19 C332 20 331 26 324 28 Z" fill="#e86a8a"/>
    <path d="M337 30 C334 25 337 20 342 22 C346 24 343 29 337 30 Z" fill="#f2c85c"/>
  </g>
 """),
 ('newyear', 'Midnight Toast', 'festiva', 'light', """
  <defs><linearGradient id="ny-bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#07070c"/><stop offset="1" stop-color="#1a1626"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#ny-bg)"/>
  <g stroke="#e8c66a" stroke-width="1" stroke-linecap="round" opacity=".95">
    <g transform="translate(360,14)">
      <path d="M0 0 V-10 M0 0 L7 -7 M0 0 H10 M0 0 L7 7 M0 0 V10 M0 0 L-7 7 M0 0 H-10 M0 0 L-7 -7"/>
    </g>
    <g transform="translate(462,8) scale(.8)" stroke="#e8e2f4">
      <path d="M0 0 V-10 M0 0 L7 -7 M0 0 H10 M0 0 L7 7 M0 0 V10 M0 0 L-7 7 M0 0 H-10 M0 0 L-7 -7"/>
    </g>
  </g>
  <g fill="#e8c66a">
    <circle cx="360" cy="14" r="1.4"/><circle cx="462" cy="8" r="1.1"/>
    <circle cx="320" cy="30" r="1"/><circle cx="420" cy="26" r="1"/><circle cx="500" cy="20" r="1"/>
    <circle cx="404" cy="8" r="1"/><circle cx="290" cy="12" r="1"/>
  </g>
  <!-- dos copas brindando -->
  <g transform="translate(566,26)">
    <g fill="none" stroke="#d9dbe8" stroke-width="1.6">
      <path d="M-22 -12 C-22 -2 -18 2 -13 2 C-8 2 -6 -3 -7 -12 Z" fill="rgba(233,226,244,.16)"/>
      <path d="M-13 2 L-15 16 M-21 17 L-9 15" />
      <path d="M22 -14 C22 -4 18 0 13 0 C8 0 6 -5 7 -14 Z" fill="rgba(233,226,244,.16)"/>
      <path d="M13 0 L16 15 M10 17 L22 14"/>
    </g>
    <path d="M-20 -10 C-20 -6 -17 -4 -14 -5" stroke="#e8c66a" stroke-width="1.4" fill="none"/>
    <path d="M20 -12 C20 -8 17 -6 14 -7" stroke="#e8c66a" stroke-width="1.4" fill="none"/>
    <g fill="#e8c66a" opacity=".9">
      <circle cx="-16" cy="-16" r="1"/><circle cx="-11" cy="-20" r=".9"/><circle cx="-19" cy="-22" r=".8"/>
      <circle cx="16" cy="-18" r="1"/><circle cx="11" cy="-22" r=".9"/><circle cx="20" cy="-24" r=".8"/>
      <circle cx="0" cy="-8" r=".9"/><circle cx="2" cy="-14" r=".8"/>
    </g>
  </g>
 """),

 # ══ LIBRES de TIENDA (2026-08-02): 12 temáticas nuevas, deliberadamente
 #    LEJOS de los camos existentes (nada militar, espacial, F1, pirata,
 #    Japón, acero, dorado déco ni USA) y de las 12 temporadas mensuales. ════
 ('gambit', 'Gambit', 'libre', 'light', """
  <defs><linearGradient id="gb-bg" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#1a120c"/><stop offset="1" stop-color="#33241a"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#gb-bg)"/>
  <!-- tablero en perspectiva, esquina inferior derecha -->
  <g>
    <path d="M368 48 L400 30 L640 30 L640 48 Z" fill="#8a6a44"/>
    <g fill="#2b1c10">
      <path d="M398 48 L424 30 L452 30 L432 48 Z"/><path d="M462 48 L484 30 L512 30 L494 48 Z"/>
      <path d="M524 48 L544 30 L572 30 L554 48 Z"/><path d="M584 48 L604 30 L632 30 L614 48 Z"/>
      <path d="M383 39 L640 39 L640 39.2 L383 39.2 Z" stroke="#2b1c10" stroke-width=".6"/>
    </g>
    <path d="M368 48 L400 30 L640 30" fill="none" stroke="#c9a86a" stroke-width="1.2"/>
  </g>
  <!-- piezas: torre, caballo (silueta simple), dama, peon -->
  <g fill="#0e0906">
    <path d="M432 30 V18 H436 V21 H440 V18 H444 V21 H448 V18 H452 V30 Z M430 30 H454 V33 H430 Z"/>
    <path d="M500 31 C494 31 492 26 494 21 C496 16 502 13 508 14 L506 18 L512 16 C516 20 514 27 508 31 Z M496 31 H512 V34 H496 Z"/>
    <path d="M566 30 C560 28 559 21 564 18 L562 13 L566 15 L568 11 L570 15 L574 13 L572 18 C577 21 576 28 570 30 Z M562 30 H574 V33 H562 Z"/>
    <circle cx="614" cy="18" r="3.4"/><path d="M610 30 C609 24 612 21 614 21 C616 21 619 24 618 30 Z M608 30 H620 V33 H608 Z"/>
  </g>
  <g fill="#f2e6d0" opacity=".92">
    <path d="M300 40 C295 38 294 32 298 29 L296 25 L299 26.5 L300 23 L301.6 26.5 L305 25 L303 29 C307 32 306 38 301 40 Z M296 40 H306 V43 H296 Z"/>
  </g>
 """),
 ('beacon', 'Beacon', 'libre', 'light', """
  <defs>
    <linearGradient id="bc-sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0a1224"/><stop offset="1" stop-color="#14263d"/></linearGradient>
    <linearGradient id="bc-beam" x1="1" y1="0" x2="0" y2="0">
      <stop offset="0" stop-color="#ffe9a8" stop-opacity=".55"/>
      <stop offset="1" stop-color="#ffe9a8" stop-opacity="0"/></linearGradient>
  </defs>
  <rect width="640" height="48" fill="url(#bc-sky)"/>
  <g fill="#e8eef6" opacity=".8">
    <circle cx="300" cy="8" r="1"/><circle cx="380" cy="5" r="1"/><circle cx="452" cy="10" r=".9"/>
    <circle cx="330" cy="16" r=".8"/>
  </g>
  <path d="M574 14 L300 2 L300 22 Z" fill="url(#bc-beam)"/>
  <rect y="40" width="640" height="8" fill="#0a1830"/>
  <g stroke="#3d5a7a" stroke-width="1" opacity=".7">
    <path d="M256 43 H360 M380 45 H470 M490 43 H580 M300 46 H420 M520 46 H640"/>
  </g>
  <g>
    <path d="M560 40 L566 12 H582 L588 40 Z" fill="#c9d4de"/>
    <path d="M560 40 L566 12 H574 V40 Z" fill="#a8b6c4"/>
    <g fill="#b8422f">
      <path d="M563.5 24 H584.5 L583 18 H565 Z"/><path d="M561 36 H587 L585.5 30 H562.5 Z"/>
    </g>
    <rect x="564" y="8" width="20" height="6" rx="1" fill="#2b3948"/>
    <rect x="568" y="9" width="12" height="4" fill="#ffe9a8"/>
    <path d="M562 8 H586 L574 2 Z" fill="#2b3948"/>
    <rect x="556" y="40" width="36" height="3" fill="#22303f"/>
  </g>
  <g fill="#0e2036">
    <path d="M600 40 C606 34 614 36 618 40 Z M280 40 C286 35 294 36 298 40 Z"/>
  </g>
 """),
 ('vineyard', 'Vineyard', 'libre', 'dark', """
  <defs><linearGradient id="vy-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f7e3c4"/><stop offset="1" stop-color="#eec89a"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#vy-sky)"/>
  <circle cx="320" cy="14" r="9" fill="#e8944f" opacity=".65"/>
  <path d="M0 34 C120 28 240 36 380 30 C500 25 580 32 640 28 L640 48 L0 48 Z" fill="#c9a266"/>
  <path d="M0 40 C140 34 300 42 640 34 L640 48 L0 48 Z" fill="#8a9a4e"/>
  <!-- hileras de vides en perspectiva -->
  <g stroke="#4d6428" stroke-width="2.2" stroke-linecap="round">
    <path d="M420 34 L400 48 M470 33 L458 48 M520 33 L516 48 M570 33 L574 48 M618 34 L632 48"/>
  </g>
  <g stroke="#5d7a30" stroke-width="1.1" fill="none" opacity=".9">
    <path d="M420 37 C436 35 452 35 470 36 C488 35 504 35 520 36 C536 35 552 35 570 36 C586 35 602 36 618 37"/>
    <path d="M412 42 C432 40 452 40 474 41 C496 40 516 40 538 41 C560 40 582 41 606 42 C614 42 622 43 630 43"/>
  </g>
  <g fill="#5b2547">
    <circle cx="444" cy="37" r="1.6"/><circle cx="447" cy="39.4" r="1.6"/><circle cx="441" cy="39.4" r="1.6"/>
    <circle cx="544" cy="37" r="1.6"/><circle cx="547" cy="39.4" r="1.6"/><circle cx="541" cy="39.4" r="1.6"/>
    <circle cx="600" cy="38" r="1.5"/><circle cx="603" cy="40.2" r="1.5"/><circle cx="597" cy="40.2" r="1.5"/>
  </g>
  <g fill="#6d8436">
    <path d="M448 34 C450 31 454 31 455 34 C452 35 450 35 448 34 Z"/>
    <path d="M536 34 C538 31 542 31 543 34 C540 35 538 35 536 34 Z"/>
  </g>
 """),
 ('archive', 'The Archive', 'libre', 'light', """
  <defs><linearGradient id="av-bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#241812"/><stop offset="1" stop-color="#3a2a1e"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#av-bg)"/>
  <!-- estanteria: dos baldas llenas de lomos -->
  <g>
    <rect x="288" y="4" width="352" height="2.6" fill="#8a6a44"/>
    <rect x="288" y="24" width="352" height="2.6" fill="#8a6a44"/>
    <rect x="288" y="44" width="352" height="2.6" fill="#8a6a44"/>
    <g>
      <rect x="296" y="8" width="7" height="16" fill="#7a3b2a"/><rect x="305" y="10" width="6" height="14" fill="#2f4d5c"/>
      <rect x="313" y="7" width="8" height="17" fill="#8a6a2a"/><rect x="323" y="11" width="5" height="13" fill="#4d2f5c"/>
      <rect x="330" y="9" width="7" height="15" fill="#2a5c3f"/><rect x="339" y="8" width="6" height="16" fill="#7a3b2a"/>
      <rect x="347" y="12" width="9" height="12" fill="#33506d" transform="rotate(-8 351 18)"/>
      <rect x="360" y="7" width="7" height="17" fill="#5c452a"/><rect x="369" y="10" width="6" height="14" fill="#2f4d5c"/>
      <rect x="377" y="8" width="8" height="16" fill="#6d2a3f"/><rect x="387" y="11" width="5" height="13" fill="#8a6a2a"/>
      <rect x="394" y="9" width="7" height="15" fill="#2a5c3f"/>
    </g>
    <g>
      <rect x="420" y="28" width="7" height="16" fill="#2f4d5c"/><rect x="429" y="30" width="6" height="14" fill="#7a3b2a"/>
      <rect x="437" y="27" width="8" height="17" fill="#4d2f5c"/><rect x="447" y="31" width="5" height="13" fill="#2a5c3f"/>
      <rect x="454" y="29" width="7" height="15" fill="#8a6a2a"/><rect x="463" y="28" width="6" height="16" fill="#33506d"/>
      <rect x="471" y="32" width="9" height="12" fill="#6d2a3f" transform="rotate(7 475 38)"/>
      <rect x="484" y="27" width="7" height="17" fill="#2a5c3f"/><rect x="493" y="30" width="6" height="14" fill="#5c452a"/>
      <rect x="501" y="28" width="8" height="16" fill="#2f4d5c"/><rect x="511" y="31" width="5" height="13" fill="#7a3b2a"/>
    </g>
  </g>
  <!-- lampara de lectura verde -->
  <g transform="translate(596,28)">
    <ellipse cx="0" cy="0" rx="22" ry="14" fill="#e8c66a" opacity=".18"/>
    <path d="M-12 -2 C-12 -8 12 -8 12 -2 Z" fill="#2a6d4f"/>
    <rect x="-1.2" y="-2" width="2.4" height="12" fill="#8a6a2a"/>
    <rect x="-8" y="10" width="16" height="2.4" rx="1" fill="#8a6a2a"/>
    <rect x="-9" y="-3.4" width="18" height="2" rx="1" fill="#ffe9a8"/>
  </g>
  <g stroke="#e8c66a" stroke-width=".8" opacity=".35">
    <path d="M560 14 H636 M560 18 H628 M560 22 H636"/>
  </g>
 """),
 ('clockwork', 'Clockwork', 'libre', 'light', """
  <defs><linearGradient id="cw-bg" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#141210"/><stop offset="1" stop-color="#2a241c"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#cw-bg)"/>
  <!-- engranajes de laton entrelazados -->
  <g fill="#a8813d">
    <g transform="translate(430,24)">
      <circle r="13" fill="none" stroke="#a8813d" stroke-width="5"/>
      <g><rect x="-2.2" y="-19" width="4.4" height="7"/><rect x="-2.2" y="12" width="4.4" height="7"/>
        <rect x="-19" y="-2.2" width="7" height="4.4"/><rect x="12" y="-2.2" width="7" height="4.4"/>
        <rect x="-2.2" y="-19" width="4.4" height="7" transform="rotate(45)"/>
        <rect x="-2.2" y="12" width="4.4" height="7" transform="rotate(45)"/>
        <rect x="-19" y="-2.2" width="7" height="4.4" transform="rotate(45)"/>
        <rect x="12" y="-2.2" width="7" height="4.4" transform="rotate(45)"/></g>
      <circle r="3.6" fill="#141210" stroke="#a8813d" stroke-width="2"/>
    </g>
    <g transform="translate(474,10) scale(.62)" fill="#c9a86a">
      <circle r="13" fill="none" stroke="#c9a86a" stroke-width="5"/>
      <g><rect x="-2.2" y="-19" width="4.4" height="7"/><rect x="-2.2" y="12" width="4.4" height="7"/>
        <rect x="-19" y="-2.2" width="7" height="4.4"/><rect x="12" y="-2.2" width="7" height="4.4"/>
        <rect x="-2.2" y="-19" width="4.4" height="7" transform="rotate(45)"/>
        <rect x="-2.2" y="12" width="4.4" height="7" transform="rotate(45)"/>
        <rect x="-19" y="-2.2" width="7" height="4.4" transform="rotate(45)"/>
        <rect x="12" y="-2.2" width="7" height="4.4" transform="rotate(45)"/></g>
      <circle r="3.6" fill="#141210" stroke="#c9a86a" stroke-width="2"/>
    </g>
    <g transform="translate(478,40) scale(.5)" fill="#8a6a34">
      <circle r="13" fill="none" stroke="#8a6a34" stroke-width="5"/>
      <g><rect x="-2.2" y="-19" width="4.4" height="7"/><rect x="-2.2" y="12" width="4.4" height="7"/>
        <rect x="-19" y="-2.2" width="7" height="4.4"/><rect x="12" y="-2.2" width="7" height="4.4"/></g>
      <circle r="3.6" fill="#141210" stroke="#8a6a34" stroke-width="2"/>
    </g>
  </g>
  <!-- esfera con agujas -->
  <g transform="translate(576,24)">
    <circle r="17" fill="#f2ead6" stroke="#a8813d" stroke-width="2.4"/>
    <g stroke="#3a2f1c" stroke-width="1.2">
      <path d="M0 -14 V-11 M14 0 H11 M0 14 V11 M-14 0 H-11 M9.9 -9.9 L7.8 -7.8 M9.9 9.9 L7.8 7.8 M-9.9 9.9 L-7.8 7.8 M-9.9 -9.9 L-7.8 -7.8"/>
    </g>
    <path d="M0 0 L0 -9" stroke="#1c150c" stroke-width="2" stroke-linecap="round"/>
    <path d="M0 0 L6.5 3.5" stroke="#1c150c" stroke-width="2.6" stroke-linecap="round"/>
    <circle r="1.6" fill="#a8412f"/>
  </g>
  <g stroke="#3a3226" stroke-width="1" opacity=".8">
    <path d="M256 8 H400 M256 40 H396"/>
  </g>
 """),
 ('windmill', 'Windmill', 'libre', 'dark', """
  <defs><linearGradient id="wm-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#dff0f7"/><stop offset="1" stop-color="#f2f8fb"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#wm-sky)"/>
  <g fill="#fff" opacity=".9">
    <ellipse cx="330" cy="10" rx="26" ry="5"/><ellipse cx="470" cy="7" rx="20" ry="4"/>
  </g>
  <!-- campos de tulipanes en franjas -->
  <path d="M0 34 L640 30 L640 48 L0 48 Z" fill="#4d8a3d"/>
  <path d="M0 38 L640 34 L640 40 L0 44 Z" fill="#d94f6e"/>
  <path d="M0 44 L640 40 L640 45 L0 48 Z" fill="#e8b23d"/>
  <g fill="#7a3b8a" opacity=".9"><path d="M0 47 L640 44 L640 48 L0 48 Z"/></g>
  <!-- molino -->
  <g transform="translate(560,26)">
    <path d="M-9 16 L-5 -6 H5 L9 16 Z" fill="#8a5c3d"/>
    <path d="M-9 16 L-5 -6 H0 V16 Z" fill="#6d4530"/>
    <path d="M-7 -6 H7 L0 -13 Z" fill="#4d3322"/>
    <rect x="-2" y="8" width="4" height="8" fill="#2b1c10"/>
    <g stroke="#3a2a1c" stroke-width="1.8">
      <path d="M0 -10 L11 -21 M0 -10 L11 1 M0 -10 L-11 -21 M0 -10 L-11 1"/>
    </g>
    <g fill="none" stroke="#3a2a1c" stroke-width="1">
      <path d="M1.5 -11.5 L9 -19 L11.5 -16.5 L4 -9 Z M-1.5 -8.5 L-9 -1 L-11.5 -3.5 L-4 -11 Z"/>
    </g>
    <circle cx="0" cy="-10" r="1.6" fill="#2b1c10"/>
  </g>
 """),
 ('fireflies', 'Fireflies', 'libre', 'light', """
  <defs>
    <linearGradient id="ff-bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#071410"/><stop offset="1" stop-color="#10281e"/></linearGradient>
    <radialGradient id="ff-glow">
      <stop offset="0" stop-color="#d9f26a" stop-opacity=".9"/>
      <stop offset="1" stop-color="#d9f26a" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="640" height="48" fill="url(#ff-bg)"/>
  <g stroke="#1c3d2c" stroke-width="1.8" stroke-linecap="round" fill="none">
    <path d="M280 48 C282 40 278 34 274 30 M310 48 C312 42 316 38 314 32 M350 48 C348 40 352 36 350 30
             M420 48 C422 41 418 36 416 31 M470 48 C472 42 468 37 470 32 M540 48 C538 41 542 36 540 31
             M590 48 C592 42 588 37 590 33 M620 48 C622 43 618 38 620 34"/>
  </g>
  <g>
    <circle cx="380" cy="22" r="9" fill="url(#ff-glow)"/><circle cx="380" cy="22" r="1.5" fill="#eef79a"/>
    <circle cx="452" cy="12" r="7" fill="url(#ff-glow)"/><circle cx="452" cy="12" r="1.3" fill="#eef79a"/>
    <circle cx="520" cy="26" r="10" fill="url(#ff-glow)"/><circle cx="520" cy="26" r="1.6" fill="#eef79a"/>
    <circle cx="584" cy="14" r="7" fill="url(#ff-glow)"/><circle cx="584" cy="14" r="1.2" fill="#eef79a"/>
    <circle cx="620" cy="30" r="6" fill="url(#ff-glow)"/><circle cx="620" cy="30" r="1.1" fill="#eef79a"/>
    <circle cx="330" cy="12" r="6" fill="url(#ff-glow)"/><circle cx="330" cy="12" r="1.1" fill="#eef79a"/>
    <circle cx="490" cy="40" r="6" fill="url(#ff-glow)"/><circle cx="490" cy="40" r="1.1" fill="#eef79a"/>
  </g>
  <g fill="#9ab24d" opacity=".5">
    <circle cx="300" cy="28" r=".8"/><circle cx="410" cy="36" r=".8"/><circle cx="556" cy="38" r=".8"/>
    <circle cx="636" cy="10" r=".8"/>
  </g>
 """),
 ('harvest', 'Golden Harvest', 'libre', 'dark', """
  <defs><linearGradient id="hv-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f7ecd0"/><stop offset="1" stop-color="#f2d9a0"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#hv-sky)"/>
  <circle cx="300" cy="12" r="10" fill="#e8a23d" opacity=".55"/>
  <path d="M0 36 C160 32 320 38 640 32 L640 48 L0 48 Z" fill="#d9a648"/>
  <path d="M0 42 C200 38 400 44 640 39 L640 48 L0 48 Z" fill="#c08a2c"/>
  <!-- espigas -->
  <g stroke="#8a6018" stroke-width="2" fill="none" stroke-linecap="round">
    <path d="M420 44 C420 36 418 30 414 24 M470 44 C470 35 472 29 476 23 M530 44 C530 35 528 29 524 24
             M580 44 C580 36 582 30 586 24 M620 44 C620 37 618 31 616 26"/>
  </g>
  <g fill="#e8c66a">
    <g transform="translate(414,24) rotate(-14) scale(1.35)"><ellipse cx="0" cy="-2" rx="2" ry="3.4"/>
      <ellipse cx="-3" cy="2" rx="2" ry="3.4"/><ellipse cx="3" cy="2" rx="2" ry="3.4"/>
      <ellipse cx="-3" cy="7" rx="2" ry="3.4"/><ellipse cx="3" cy="7" rx="2" ry="3.4"/></g>
    <g transform="translate(476,23) rotate(12) scale(1.35)"><ellipse cx="0" cy="-2" rx="2" ry="3.4"/>
      <ellipse cx="-3" cy="2" rx="2" ry="3.4"/><ellipse cx="3" cy="2" rx="2" ry="3.4"/>
      <ellipse cx="-3" cy="7" rx="2" ry="3.4"/><ellipse cx="3" cy="7" rx="2" ry="3.4"/></g>
    <g transform="translate(524,24) rotate(-10) scale(1.35)"><ellipse cx="0" cy="-2" rx="2" ry="3.4"/>
      <ellipse cx="-3" cy="2" rx="2" ry="3.4"/><ellipse cx="3" cy="2" rx="2" ry="3.4"/>
      <ellipse cx="-3" cy="7" rx="2" ry="3.4"/><ellipse cx="3" cy="7" rx="2" ry="3.4"/></g>
    <g transform="translate(586,24) rotate(14) scale(1.35)"><ellipse cx="0" cy="-2" rx="2" ry="3.4"/>
      <ellipse cx="-3" cy="2" rx="2" ry="3.4"/><ellipse cx="3" cy="2" rx="2" ry="3.4"/>
      <ellipse cx="-3" cy="7" rx="2" ry="3.4"/><ellipse cx="3" cy="7" rx="2" ry="3.4"/></g>
  </g>
  <!-- fardo -->
  <g transform="translate(348,38)">
    <rect x="-14" y="-8" width="28" height="16" rx="2" fill="#d9a648"/>
    <path d="M-14 -2 H14 M-14 4 H14" stroke="#a87c24" stroke-width="1.2"/>
    <path d="M-6 -8 V8 M6 -8 V8" stroke="#8a6018" stroke-width="1"/>
  </g>
 """),
 ('cascade', 'Cascade', 'libre', 'light', """
  <defs>
    <linearGradient id="cd-bg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#12281e"/><stop offset="1" stop-color="#1d3d2c"/></linearGradient>
    <linearGradient id="cd-fall" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#cfe8f2"/><stop offset="1" stop-color="#8fc7dd"/></linearGradient>
  </defs>
  <rect width="640" height="48" fill="url(#cd-bg)"/>
  <!-- pared de roca y cascada -->
  <g fill="#2b4434">
    <path d="M470 0 H640 V48 H540 C534 30 528 14 470 0 Z"/>
  </g>
  <g fill="#1c3325">
    <path d="M540 0 H640 V48 H600 C596 28 586 10 540 0 Z"/>
  </g>
  <path d="M560 0 C560 16 556 34 548 48 H584 C590 32 592 14 590 0 Z" fill="url(#cd-fall)"/>
  <g stroke="#eef7fb" stroke-width="1.2" fill="none" opacity=".8">
    <path d="M566 2 C566 16 562 32 556 46 M578 2 C580 16 578 32 572 46"/>
  </g>
  <ellipse cx="566" cy="47" rx="30" ry="4" fill="#cfe8f2" opacity=".9"/>
  <ellipse cx="566" cy="45" rx="16" ry="2.4" fill="#ffffff" opacity=".8"/>
  <g fill="#ffffff" opacity=".7">
    <circle cx="542" cy="42" r="1"/><circle cx="592" cy="41" r="1"/><circle cx="600" cy="45" r=".9"/>
    <circle cx="534" cy="46" r=".9"/>
  </g>
  <!-- vegetacion colgante -->
  <g stroke="#3f6a42" stroke-width="1.6" stroke-linecap="round" fill="none">
    <path d="M478 4 C482 10 480 16 476 20 M496 2 C500 10 498 18 492 24 M622 6 C618 12 620 18 624 22"/>
  </g>
  <g fill="#4d8a52" opacity=".8">
    <circle cx="476" cy="20" r="2"/><circle cx="492" cy="24" r="2.2"/><circle cx="624" cy="22" r="2"/>
  </g>
 """),
 ('bazaar', 'Night Bazaar', 'libre', 'light', """
  <defs><linearGradient id="bz-bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#160e1e"/><stop offset="1" stop-color="#2b1a30"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#bz-bg)"/>
  <!-- guirnaldas de lamparas colgantes -->
  <path d="M256 4 C340 12 420 2 500 10 C560 15 600 8 640 12" stroke="#4d3a52" stroke-width="1.2" fill="none"/>
  <g>
    <g transform="translate(310,10)"><rect x="-1" y="-3" width="2" height="3" fill="#8a6a34"/>
      <path d="M-5 0 C-5 -3 5 -3 5 0 L4 9 C4 12 -4 12 -4 9 Z" fill="#e8944f"/>
      <ellipse cx="0" cy="5" rx="6" ry="7" fill="#e8944f" opacity=".35"/>
      <path d="M-2 12 L0 15 L2 12" stroke="#8a6a34" stroke-width="1" fill="none"/></g>
    <g transform="translate(388,8)"><rect x="-1" y="-3" width="2" height="3" fill="#8a6a34"/>
      <circle cy="6" r="6" fill="#5fb2d9"/><circle cy="6" r="8.5" fill="#5fb2d9" opacity=".3"/>
      <path d="M-4 2 H4 M-5 6 H5 M-4 10 H4" stroke="#2b5c74" stroke-width="1"/></g>
    <g transform="translate(462,12)"><rect x="-1" y="-3" width="2" height="3" fill="#8a6a34"/>
      <path d="M-5 0 H5 L3 10 H-3 Z" fill="#d94f6e"/>
      <ellipse cx="0" cy="5" rx="7" ry="8" fill="#d94f6e" opacity=".3"/>
      <circle cy="12" r="1.2" fill="#e8c66a"/></g>
    <g transform="translate(540,10)"><rect x="-1" y="-3" width="2" height="3" fill="#8a6a34"/>
      <path d="M0 0 L5 5 L0 13 L-5 5 Z" fill="#8ad95f"/>
      <path d="M0 0 L5 5 L0 13 L-5 5 Z" fill="#8ad95f" opacity=".35" transform="scale(1.5)"/></g>
    <g transform="translate(608,13)"><rect x="-1" y="-3" width="2" height="3" fill="#8a6a34"/>
      <path d="M-4 0 C-6 4 -6 8 0 11 C6 8 6 4 4 0 Z" fill="#e8c66a"/>
      <ellipse cx="0" cy="5" rx="7" ry="8" fill="#e8c66a" opacity=".3"/></g>
  </g>
  <!-- puestos abajo: toldos a rayas -->
  <g>
    <path d="M300 48 V42 H360 V48 Z" fill="#33202b"/>
    <path d="M296 42 L302 36 H358 L364 42 Z" fill="#a8442e"/>
    <path d="M310 42 L314 36 H322 L319 42 Z M330 42 L334 36 H342 L339 42 Z" fill="#e8dcc9"/>
    <path d="M480 48 V43 H540 V48 Z" fill="#33202b"/>
    <path d="M476 43 L482 37 H538 L544 43 Z" fill="#2f5c74"/>
    <path d="M490 43 L494 37 H502 L499 43 Z M510 43 L514 37 H522 L519 43 Z" fill="#e8dcc9"/>
  </g>
 """),
 ('salar', 'Salt Mirror', 'libre', 'dark', """
  <defs>
    <linearGradient id="sl-sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f7e6ee"/><stop offset=".6" stop-color="#e8ddf2"/>
      <stop offset="1" stop-color="#d4e4f2"/></linearGradient>
  </defs>
  <rect width="640" height="48" fill="url(#sl-sky)"/>
  <!-- nubes y su reflejo espejo -->
  <g fill="#fff">
    <ellipse cx="360" cy="12" rx="30" ry="4.4"/><ellipse cx="500" cy="8" rx="24" ry="3.8"/>
    <ellipse cx="600" cy="14" rx="20" ry="3.4"/>
  </g>
  <rect y="28" width="640" height="20" fill="#e4ecf4"/>
  <g fill="#fff" opacity=".65">
    <ellipse cx="360" cy="36" rx="30" ry="3.6"/><ellipse cx="500" cy="39" rx="24" ry="3.2"/>
    <ellipse cx="600" cy="34" rx="20" ry="2.8"/>
  </g>
  <path d="M0 28 H640" stroke="#c9d4e4" stroke-width="1"/>
  <circle cx="430" cy="20" r="7" fill="#f2b56a" opacity=".8"/>
  <ellipse cx="430" cy="33" rx="7" ry="4" fill="#f2b56a" opacity=".4"/>
  <!-- grietas hexagonales de sal en primer plano -->
  <g stroke="#b8c4d4" stroke-width="1" fill="none" opacity=".9">
    <path d="M280 48 L292 40 L312 41 L322 48 M312 41 L318 34 M292 40 L286 33
             M370 48 L382 41 L402 42 L410 48 M402 42 L408 35 M382 41 L376 34
             M470 48 L484 42 L502 42 L510 48 M502 42 L508 36 M484 42 L478 35
             M560 48 L572 41 L590 42 L598 48 M590 42 L596 35 M572 41 L566 34"/>
  </g>
 """),
 ('express', 'Night Express', 'libre', 'light', """
  <defs><linearGradient id="ex-sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#1c1428"/><stop offset="1" stop-color="#3d2440"/></linearGradient></defs>
  <rect width="640" height="48" fill="url(#ex-sky)"/>
  <circle cx="330" cy="10" r="8" fill="#f2e6c9" opacity=".75"/>
  <g fill="#f2e6c9" opacity=".7">
    <circle cx="380" cy="6" r=".9"/><circle cx="470" cy="4" r=".9"/><circle cx="560" cy="7" r=".9"/>
  </g>
  <!-- viaducto de arcos -->
  <g fill="#171020">
    <rect x="256" y="30" width="384" height="5"/>
    <path d="M280 48 V38 C280 33 288 33 288 38 V48 Z M328 48 V38 C328 33 336 33 336 38 V48 Z
             M376 48 V38 C376 33 384 33 384 38 V48 Z M424 48 V38 C424 33 432 33 432 38 V48 Z
             M472 48 V38 C472 33 480 33 480 38 V48 Z M520 48 V38 C520 33 528 33 528 38 V48 Z
             M568 48 V38 C568 33 576 33 576 38 V48 Z M616 48 V38 C616 33 624 33 624 38 V48 Z"/>
    <rect x="256" y="35" width="384" height="13" fill="#171020" opacity="0"/>
    <path d="M256 35 H640 V48 H632 V38 C632 31 610 31 610 38 V48 H584 V38 C584 31 562 31 562 38 V48
             H536 V38 C536 31 514 31 514 38 V48 H488 V38 C488 31 466 31 466 38 V48 H440 V38
             C440 31 418 31 418 38 V48 H392 V38 C392 31 370 31 370 38 V48 H344 V38 C344 31 322 31
             322 38 V48 H296 V38 C296 31 274 31 274 38 V48 H256 Z"/>
  </g>
  <!-- tren silueta con ventanas encendidas -->
  <g>
    <path d="M420 30 V22 C420 19 423 17 426 17 H438 V13 C438 11 440 10 442 10 H452 C455 10 457 12 457 15 V30 Z"
          fill="#0c0812"/>
    <rect x="461" y="18" width="52" height="12" rx="2" fill="#0c0812"/>
    <rect x="517" y="18" width="52" height="12" rx="2" fill="#0c0812"/>
    <g fill="#ffd98f">
      <rect x="465" y="21" width="7" height="5" rx="1"/><rect x="476" y="21" width="7" height="5" rx="1"/>
      <rect x="487" y="21" width="7" height="5" rx="1"/><rect x="498" y="21" width="7" height="5" rx="1"/>
      <rect x="521" y="21" width="7" height="5" rx="1"/><rect x="532" y="21" width="7" height="5" rx="1"/>
      <rect x="543" y="21" width="7" height="5" rx="1"/><rect x="554" y="21" width="7" height="5" rx="1"/>
      <circle cx="422" cy="26" r="2"/>
    </g>
    <g fill="#d9dbe8" opacity=".7">
      <circle cx="436" cy="6" r="2.6"/><circle cx="428" cy="4" r="2"/><circle cx="420" cy="3" r="1.5"/>
      <circle cx="412" cy="4" r="1.2"/>
    </g>
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
