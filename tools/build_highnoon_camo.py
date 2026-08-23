# -*- coding: utf-8 -*-
"""Genera el bloque CSS del camo HIGH NOON y lo inserta en index.html.

Temática (tienda, camo común $4.99): **CUERO DE TALABARTERÍA** — la bio de la
tienda manda: "cuero, arena y un duelo al mediodía". v2 tras el veredicto del
dueño sobre la v1 (una calle del oeste): *"prácticamente iguales al de Egipto
e iguales entre ellos… no cambian absolutamente nada en diseño"*. Tenía
razón: la v1 aplicaba la fórmula de los camos de RULETA (paisaje en franja
baja + recolor nocturno). Los camos de TIENDA buenos son un MATERIAL, no una
escena: Pole = plano/cianotipo, Standard = placa de acero, Premium =
obsidiana. Éste es la piel de una montura:

  · la superficie entera es cuero con su veta y sus manchas de tinte,
  · costura doble de talabartero recorriendo los CUATRO bordes (en CSS puro,
    así abraza cualquier pantalla sin estirarse),
  · conchos de latón remachados en las cuatro esquinas,
  · una cenefa REPUJADA de rollos del oeste a lo largo del borde inferior
    (el grabado se lee como surco con el truco de Standard: cada trazo dos
    veces, la copia clara 1.6px abajo y la tinta encima),
  · y la ESTRELLA DE SHERIFF herrada A FUEGO en la esquina inferior derecha
    — el objeto que nombra el duelo.

DOS LOOKS = DOS MATERIALES (patrón Pole, no día/noche):
  ☀️ light · cuero NUEVO color miel, recién repujado, hilo crema.
  🌙 dark  · el MISMO cuero años después: engrasado, casi espresso, con el
             hilo dorado y los brillos del latón — nada de lunas ni estrellas.
Una geometría, dos paletas (dict PALETTE) — re-correr el script re-inserta el
bloque, es idempotente.

Reglas del sitio que respeta:
  · Trazos GRUESOS (el dueño rechaza las telarañas de línea fina).
  · El adorno se RECONOCE a la primera → la estrella herrada.
  · La veta va en un TILE que se repite (no `cover`; sin costuras visibles
    porque los poros no tocan los bordes del tile).
  · iOS-safe: body transparente + ::before position:fixed.
  · Jinja: ningún `{#`/`{{`/`{%` dentro del CSS insertado.

Uso:  python3 tools/build_highnoon_camo.py        (desde la raíz del repo)
"""
import math
import os
import random
import re
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'scalpel', 'templates', 'index.html')


def datauri(svg):
    svg = re.sub(r'\s+', ' ', svg).strip()
    return "url(\"data:image/svg+xml,%s\")" % quote(svg, safe="/:=;,.-()'% ")


# ══ una geometría, dos paletas ════════════════════════════════════════════
PALETTE = {
    # ☀️ cuero nuevo color miel
    'day': dict(PORE='#7a4a22', PORE_OP='0.10',
                TOOL_INK='#6e3d18', TOOL_LIGHT='#e0b078',
                BRAND='#4a2408', BRAND_RIM='#e0b078',
                CONCHO='#caa24a', CONCHO_D='#8a6a2a', CONCHO_HI='#f0dca0',
                THREAD='#f2e2c4'),
    # 🌙 el mismo cuero engrasado: espresso con hilo y latón dorados
    'night': dict(PORE='#000000', PORE_OP='0.16',
                  TOOL_INK='#120a04', TOOL_LIGHT='#7a5a30',
                  BRAND='#0c0602', BRAND_RIM='#caa24a',
                  CONCHO='#caa24a', CONCHO_D='#6e4f1e', CONCHO_HI='#f0d08a',
                  THREAD='#caa24a'),
}


def grain_svg(mode='day'):
    """480×480, para REPETIR: los poros y arrugas del cuero. Los trazos no
    tocan los bordes del tile, así la repetición no deja costuras."""
    C = PALETTE[mode]
    rng = random.Random(20260710)
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='480' height='480' "
         "viewBox='0 0 480 480'>"]
    p.append("<g stroke='%s' fill='none' stroke-linecap='round' "
             "opacity='%s'>" % (C['PORE'], C['PORE_OP']))
    for _ in range(150):
        x = rng.uniform(18, 462)
        y = rng.uniform(18, 462)
        l = rng.uniform(4, 16)
        a = rng.uniform(0, math.pi)
        b = rng.uniform(-14, 14)
        p.append("<path d='M%.0f,%.0f q%.0f,%.0f %.0f,%.0f' "
                 "stroke-width='%.1f'/>"
                 % (x, y, l * .5 * math.cos(a) + b * .2, l * .5 * math.sin(a),
                    l * math.cos(a), l * math.sin(a), rng.uniform(1.0, 2.2)))
    p.append("</g>")
    # unas pocas arrugas largas, más tenues
    p.append("<g stroke='%s' fill='none' stroke-width='1.6' opacity='%.2f'>"
             % (C['PORE'], float(C['PORE_OP']) * 0.6))
    for _ in range(9):
        x = rng.uniform(30, 380)
        y = rng.uniform(30, 430)
        p.append("<path d='M%.0f,%.0f q%.0f,%.0f %.0f,%.0f'/>"
                 % (x, y, rng.uniform(20, 60), rng.uniform(-18, 18),
                    rng.uniform(50, 90), rng.uniform(-10, 10)))
    p.append("</g>")
    p.append("</svg>")
    return ''.join(p)


def _voluta(cx, cy, r0, sign=1):
    """Una VOLUTA de repujado: espiral de vuelta y media que se cierra hacia
    su ojo. Se traza con segmentos cortos (15 grados) — con punta redonda y
    5px de grosor se lee continua. ⚠️ La v2.0 usaba tres cuartos de 'q' y se
    leia como garabato de caligrafia, no como talabarteria."""
    import math as _m
    pts = []
    vueltas = 1.5 * 2 * _m.pi
    n = 40
    for i in range(n + 1):
        t = i / float(n)
        a = sign * (t * vueltas) - _m.pi / 2
        r = r0 * (1.0 - 0.82 * t)
        pts.append((cx + r * _m.cos(a), cy + r * _m.sin(a)))
    return "<path d='M" + ' L'.join('%.1f,%.1f' % q for q in pts) + "'/>"


def _abanico(cx, cy, s, sign=1):
    """El abanico de hojas que brota entre voluta y voluta."""
    import math as _m
    out = []
    for k in (-2, -1, 0, 1, 2):
        a = -_m.pi / 2 + k * 0.42
        out.append("<path d='M%.0f,%.0f q%.0f,%.0f %.0f,%.0f'/>"
                   % (cx, cy, s * .55 * _m.sin(a) - 6 * k,
                      -s * .75, s * _m.sin(a), s * _m.cos(a) * -1.15))
    return ''.join(out)


def tooling_svg(mode='day'):
    """1440×230: la cenefa repujada del borde inferior — volutas grandes
    alternando el giro, unidas por su tallo, con el abanico de hojas entre
    ellas y el FONDO PICADO (el punteado que el talabartero mete detras del
    dibujo para que el motivo salte). El grabado se lee como SURCO con el
    truco de Standard: el dibujo en <defs> y dos <use> — la copia clara
    1.6px abajo y la tinta encima."""
    import random as _rnd
    C = PALETTE[mode]
    rng = _rnd.Random(20261200)
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='1440' height='230' "
         "viewBox='0 0 1440 230'>"]
    dib = ["<g id='t' fill='none' stroke-width='5' stroke-linecap='round'>"]
    dib.append("<path d='M0,30 h1440 M0,202 h1440' stroke-width='4'/>")
    n = 8
    paso = 1440 / n
    for i in range(n):
        cx = paso * (i + 0.5)
        sign = 1 if i % 2 == 0 else -1
        cy = 112 + sign * 8
        dib.append(_voluta(cx, cy, 52, sign))
        # el tallo que la une con la siguiente
        if i < n - 1:
            dib.append("<path d='M%.0f,%.0f q%.0f,%.0f %.0f,%.0f'/>"
                       % (cx + 40, cy + sign * 26, paso * .32,
                          -sign * 44, paso - 80, -sign * 16))
            dib.append(_abanico(paso * (i + 1), 148 if sign > 0 else 84,
                                34, sign))
    dib.append("</g>")
    p.append("<defs>%s</defs>" % ''.join(dib))
    # el fondo picado, SOLO tinta (un punteado no lleva surco)
    p.append("<g fill='%s' opacity='0.30'>" % C['TOOL_INK'])
    for _ in range(430):
        x = rng.uniform(8, 1432)
        y = rng.uniform(40, 194)
        p.append("<circle cx='%.0f' cy='%.0f' r='1.5'/>" % (x, y))
    p.append("</g>")
    p.append("<use href='#t' stroke='%s' transform='translate(0,1.6)'/>"
             % C['TOOL_LIGHT'])
    p.append("<use href='#t' stroke='%s'/>" % C['TOOL_INK'])
    p.append("</svg>")
    return ''.join(p)


def brand_svg(mode='day'):
    """210×200: la estrella de sheriff HERRADA a fuego. v2.1: la estrella va
    MACIZA (rellena del color de la quemadura) — de puro contorno se perdia
    sobre el cuero oscuro — y el anillo mas grueso, con el filo claro de la
    piel levantada por debajo."""
    C = PALETTE[mode]
    cx, cy, ro, ri = 105, 100, 64, 27
    pts = []
    for i in range(10):
        r = ro if i % 2 == 0 else ri
        a = -math.pi / 2 + i * math.pi / 5
        pts.append('%.1f,%.1f' % (cx + r * math.cos(a), cy + r * math.sin(a)))
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='210' height='200' "
         "viewBox='0 0 210 200'>"]
    p.append("<g transform='translate(0,2.6)'>")
    p.append("<circle cx='%d' cy='%d' r='84' fill='none' stroke='%s' "
             "stroke-width='10' opacity='0.85'/>" % (cx, cy, C['BRAND_RIM']))
    p.append("<polygon points='%s' fill='none' stroke='%s' stroke-width='6' "
             "stroke-linejoin='round' opacity='0.85'/>"
             % (' '.join(pts), C['BRAND_RIM']))
    p.append("</g>")
    p.append("<circle cx='%d' cy='%d' r='84' fill='none' stroke='%s' "
             "stroke-width='10'/>" % (cx, cy, C['BRAND']))
    p.append("<polygon points='%s' fill='%s' stroke='%s' stroke-width='6' "
             "stroke-linejoin='round' opacity='0.92'/>"
             % (' '.join(pts), C['BRAND'], C['BRAND']))
    return ''.join(p) + "</svg>"


def concho_svg(mode='day'):
    """44×44: el concho de latón — el botón remachado de las esquinas."""
    C = PALETTE[mode]
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='44' height='44' "
         "viewBox='0 0 44 44'>"]
    p.append("<circle cx='22' cy='22' r='18' fill='%s'/>" % C['CONCHO_D'])
    p.append("<circle cx='22' cy='22' r='15' fill='%s'/>" % C['CONCHO'])
    # el borde festoneado (media luna de sombras alrededor)
    for i in range(8):
        a = i * math.pi / 4
        p.append("<circle cx='%.1f' cy='%.1f' r='2.6' fill='%s'/>"
                 % (22 + 15 * math.cos(a), 22 + 15 * math.sin(a),
                    C['CONCHO_D']))
    p.append("<circle cx='22' cy='22' r='5' fill='%s'/>" % C['CONCHO_D'])
    p.append("<circle cx='18' cy='17' r='4' fill='%s' opacity='0.7'/>"
             % C['CONCHO_HI'])
    return ''.join(p) + "</svg>"


# ══ el bloque CSS ═════════════════════════════════════════════════════════
def _stitch_css(thread):
    """La costura doble en CSS puro: bandas de guiones repetidos pegadas a
    los cuatro bordes — abrazan cualquier pantalla sin estirar los puntos.
    Dos pasadas por borde = puntada de talabartero."""
    h = ("repeating-linear-gradient(90deg,%s 0 14px,transparent 14px 26px)"
         % thread)
    v = ("repeating-linear-gradient(0deg,%s 0 14px,transparent 14px 26px)"
         % thread)
    capas = []
    for off in ('14px', '24px'):
        capas.append("%s left 0 top %s / 100%% 3px no-repeat" % (h, off))
        capas.append("%s left 0 bottom %s / 100%% 3px no-repeat" % (h, off))
        capas.append("%s left %s top 0 / 3px 100%% no-repeat" % (v, off))
        capas.append("%s right %s top 0 / 3px 100%% no-repeat" % (v, off))
    return ',\n        '.join(capas)


def css_block():
    return ("""
    /* ═══ High Noon (tienda · camo común) — CUERO DE TALABARTERÍA, v2.
       La v1 era una calle del oeste y el dueño la tachó con razón: era la
       fórmula de los camos de ruleta otra vez. Ahora es un MATERIAL, como
       Pole (plano) o Standard (acero): la piel de una montura con su veta,
       la costura doble en los cuatro bordes, los conchos de latón en las
       esquinas, la cenefa repujada abajo y la ESTRELLA DE SHERIFF herrada a
       fuego en la esquina. DOS looks = DOS materiales (patrón Pole):
       ☀️ light · cuero NUEVO color miel, hilo crema.
       🌙 dark  · el MISMO cuero engrasado (espresso), hilo y latón dorados —
                  sin lunas ni estrellas: sigue siendo mediodía, en otra piel.
       La costura va en CSS puro (bandas de guiones por borde) para que
       abrace cualquier viewport sin estirarse; la veta es un TILE repetido
       cuyos poros no tocan los bordes (sin costuras visibles). */
    body.camo-highnoon { background: transparent !important; }
    body.camo-highnoon.light {
      --bg:#d0a266;--surface:rgba(255,248,234,0.62);--card:rgba(255,248,234,0.74);
      --border:rgba(74,42,12,0.22);--border2:rgba(74,42,12,0.34);
      --text:#2e1c0c;--muted:rgba(46,28,12,0.62);
      --accent:#b3402a;--accent-h:#93301e;--win:#2f8f5a;--loss:#c0392b;--be:#8a6a2a;
      color: var(--text);
    }
    body.camo-highnoon.light::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __CONCHO_DAY__ left 10px top 10px / 44px 44px no-repeat,
        __CONCHO_DAY__ right 10px top 10px / 44px 44px no-repeat,
        __CONCHO_DAY__ left 10px bottom 10px / 44px 44px no-repeat,
        __CONCHO_DAY__ right 10px bottom 10px / 44px 44px no-repeat,
        __STITCH_DAY__,
        __BRAND_DAY__ right 5% bottom 6% / 175px auto no-repeat,
        __TOOL_DAY__ center bottom / 100% auto no-repeat,
        __GRAIN_DAY__ left top / 480px 480px repeat,
        radial-gradient(ellipse 90% 70% at 24% 20%, rgba(122,74,34,0.20), transparent 60%),
        radial-gradient(ellipse 80% 60% at 78% 74%, rgba(74,36,8,0.16), transparent 62%),
        linear-gradient(160deg,#dcb27a,#c9985c 46%,#b3824a);
    }
    body.camo-highnoon.light::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 90% at 50% 42%, transparent 58%, rgba(46,22,4,0.24) 100%);
    }
    body.camo-highnoon:not(.light) {
      --bg:#241509;--surface:rgba(255,255,255,0.055);--card:rgba(255,255,255,0.07);
      --border:rgba(202,162,74,0.20);--border2:rgba(202,162,74,0.32);
      --text:#f0e2cc;--muted:rgba(240,226,204,0.6);
      --accent:#e8a94a;--accent-h:#d18f2e;--win:#43d18d;--loss:#e05563;--be:#caa24a;
      color: var(--text);
    }
    body.camo-highnoon:not(.light)::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __CONCHO_NIGHT__ left 10px top 10px / 44px 44px no-repeat,
        __CONCHO_NIGHT__ right 10px top 10px / 44px 44px no-repeat,
        __CONCHO_NIGHT__ left 10px bottom 10px / 44px 44px no-repeat,
        __CONCHO_NIGHT__ right 10px bottom 10px / 44px 44px no-repeat,
        __STITCH_NIGHT__,
        __BRAND_NIGHT__ right 5% bottom 6% / 175px auto no-repeat,
        __TOOL_NIGHT__ center bottom / 100% auto no-repeat,
        __GRAIN_NIGHT__ left top / 480px 480px repeat,
        radial-gradient(ellipse 90% 70% at 24% 20%, rgba(122,90,48,0.14), transparent 60%),
        radial-gradient(ellipse 80% 60% at 78% 74%, rgba(0,0,0,0.28), transparent 62%),
        linear-gradient(160deg,#3a2412,#2b1a0b 46%,#1c0f06);
    }
    body.camo-highnoon:not(.light)::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 90% at 50% 42%, transparent 54%, rgba(0,0,0,0.5) 100%);
    }
    body.camo-highnoon:not(.light) .logo-img {
      content: url('/static/logo_t.png'); filter: invert(1); mix-blend-mode: normal;
    }
"""
            .replace('__CONCHO_DAY__', datauri(concho_svg('day')))
            .replace('__CONCHO_NIGHT__', datauri(concho_svg('night')))
            .replace('__STITCH_DAY__', _stitch_css(PALETTE['day']['THREAD']))
            .replace('__STITCH_NIGHT__', _stitch_css(PALETTE['night']['THREAD']))
            .replace('__BRAND_DAY__', datauri(brand_svg('day')))
            .replace('__BRAND_NIGHT__', datauri(brand_svg('night')))
            .replace('__TOOL_DAY__', datauri(tooling_svg('day')))
            .replace('__TOOL_NIGHT__', datauri(tooling_svg('night')))
            .replace('__GRAIN_DAY__', datauri(grain_svg('day')))
            .replace('__GRAIN_NIGHT__', datauri(grain_svg('night'))))


ANCHOR = '    /* ═══ Blackflag (pirate)'


def main():
    html = open(INDEX, encoding='utf-8').read()
    if 'body.camo-highnoon' in html:
        start = html.index('    /* ═══ High Noon (tienda')
        # ⚠️ Cortar hasta el SIGUIENTE bloque de camo (sea cual sea), no hasta
        #    Blackflag: entre este bloque y aquel ancla pueden vivir OTROS camos
        #    insertados después, y un corte largo se los llevaría por delante
        #    (pasó: re-correr highnoon borró el bloque de alchemist).
        end = html.index('    /* ═══ ', start + 20)
        html = html[:start] + html[end:]
    if ANCHOR not in html:
        raise SystemExit('No encontré el ancla del bloque Blackflag.')
    block = css_block()
    for bad in ('{#', '{%', '{{'):
        if bad in block:
            raise SystemExit('El bloque contiene %r — Jinja lo interpretaría.' % bad)
    html = html.replace(ANCHOR, block + '\n\n' + ANCHOR, 1)
    open(INDEX, 'w', encoding='utf-8').write(html)
    print('bloque highnoon insertado (%d chars)' % len(block))


if __name__ == '__main__':
    main()
