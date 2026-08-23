# -*- coding: utf-8 -*-
"""Genera el bloque CSS del camo THE ALCHEMIST y lo inserta en index.html.

Temática (tienda, camo común $4.99): **el laboratorio del alquimista** — la
bio de la tienda lo fija desde siempre: "púrpuras arcanos y un brillo
esmeralda — convierte los gráficos en oro". La escena es la mesa de trabajo:
la pila de tomos con la vela encima, el mortero, los matraces (el cónico
púrpura y el de bola esmeralda burbujeando sobre su trípode), el pergamino,
el estante de frascos y los símbolos alquímicos desvaídos en la pared. El
adorno de esquina que NOMBRA al camo (como la faluca de Nile o la estrella
de High Noon): **el ALAMBIQUE destilando una gota de ORO** en su vial.

DOS LOOKS pedidos por el dueño (patrón Chronicles/Nile — NO va en
DARK_ALWAYS):
  🌙 night · el laboratorio a la luz de la vela: piedra púrpura, la llama y
             los brillos — el esmeralda del matraz y el oro del alambique.
  ☀️ day   · el MISMO estudio de día: pared de pergamino cálido, los
             líquidos en tonos joya y los símbolos como tinta desvaída.
Una geometría, dos paletas (dict PALETTE) — re-correr el script re-inserta el
bloque, es idempotente.

Reglas del sitio que respeta (las de siempre):
  · Nada de `cover` con horizonte: la mesa se ancla `center bottom /
    100% auto`.
  · Todo lo importante vive en la franja BAJA (los paneles tapan el centro).
  · El adorno de esquina se RECONOCE a la primera → el alambique y su gota.
  · Los símbolos de la pared son GEOMETRÍA (círculos, triángulos, lunas):
    nada de <text> — un SVG de background no hereda fuentes.
  · iOS-safe: body transparente + ::before position:fixed.
  · Jinja: ningún `{#`/`{{`/`{%` dentro del CSS insertado.

Uso:  python3 tools/build_alchemist_camo.py        (desde la raíz del repo)
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
    # 🌙 el laboratorio de noche — piedra púrpura + esmeralda + oro (la bio)
    'night': dict(SYM='#8f7fc0', SYM_OP='0.30',
                  BENCH='#3a2a20', BENCH_D='#2a1d15', SHELF='#32241a',
                  GLASS='#b9c4e8', BOOK1='#5a3a6e', BOOK2='#2f5a4a',
                  BOOK3='#7a5a2a', PAGE='#d8cba8',
                  LIQ_P='#7a4fc0', LIQ_E='#35d18e', LIQ_G='#e8b34a',
                  FLAME='#ffb85c', CANDLE='#d8cba8',
                  GLOW_OP='0.5', IRON='#242032',
                  JAR='#4a3a68', CORK='#8a6a3c'),
    # ☀️ el mismo estudio de día — pergamino, madera cálida y tinta
    'day': dict(SYM='#8a6a34', SYM_OP='0.28',
                BENCH='#8a5f38', BENCH_D='#6e4826', SHELF='#7a5230',
                GLASS='#6e5a3a', BOOK1='#6a3fa0', BOOK2='#2f8f5a',
                BOOK3='#a8742e', PAGE='#fdf6e0',
                LIQ_P='#6a3fa0', LIQ_E='#2f8f5a', LIQ_G='#c8912a',
                FLAME='#e8933c', CANDLE='#f2e8cc',
                GLOW_OP='0.0', IRON='#4a3a28',
                JAR='#c9a468', CORK='#8a6a3c'),
}

BENCH_TOP = 430           # la tabla de la mesa


def _symbol(kind, cx, cy, s, col, op):
    """Símbolos alquímicos como geometría pura (sin <text>): el círculo con
    su triángulo inscrito, la luna creciente, el 'mercurio' (círculo + cruz +
    cuernos) y el sol con sus rayos."""
    p = []
    if kind == 'tri':
        p.append("<circle cx='%d' cy='%d' r='%.0f' fill='none' stroke='%s' "
                 "stroke-width='2.5' opacity='%s'/>" % (cx, cy, s, col, op))
        pts = []
        for i in range(3):
            a = -math.pi / 2 + i * 2 * math.pi / 3
            pts.append('%.0f,%.0f' % (cx + s * .8 * math.cos(a),
                                      cy + s * .8 * math.sin(a)))
        p.append("<polygon points='%s' fill='none' stroke='%s' "
                 "stroke-width='2.5' opacity='%s'/>" % (' '.join(pts), col, op))
    elif kind == 'moon':
        p.append("<path d='M%d,%d a%.0f,%.0f 0 1,0 0,%.0f a%.0f,%.0f 0 1,1 "
                 "0,-%.0f Z' fill='%s' opacity='%s'/>"
                 % (cx, cy - s, s, s, 2 * s, s * .72, s * .72, 2 * s, col, op))
    elif kind == 'merc':
        p.append("<g stroke='%s' stroke-width='2.5' fill='none' opacity='%s'>"
                 % (col, op))
        p.append("<circle cx='%d' cy='%d' r='%.0f'/>" % (cx, cy, s * .55))
        p.append("<path d='M%d,%.0f v%.0f M%.0f,%.0f h%.0f'/>"
                 % (cx, cy + s * .55, s * .8,
                    cx - s * .5, cy + s * 1.0, s))
        p.append("<path d='M%.0f,%.0f a%.0f,%.0f 0 0,0 %.0f,0'/>"
                 % (cx - s * .55, cy - s * .8, s * .55, s * .55, s * 1.1))
        p.append("</g>")
    else:                                   # 'sun'
        p.append("<circle cx='%d' cy='%d' r='%.0f' fill='none' stroke='%s' "
                 "stroke-width='2.5' opacity='%s'/>" % (cx, cy, s * .6, col, op))
        p.append("<g stroke='%s' stroke-width='2' opacity='%s'>" % (col, op))
        for i in range(8):
            a = i * math.pi / 4
            p.append("<path d='M%.0f,%.0f L%.0f,%.0f'/>"
                     % (cx + s * .75 * math.cos(a), cy + s * .75 * math.sin(a),
                        cx + s * 1.05 * math.cos(a), cy + s * 1.05 * math.sin(a)))
        p.append("</g>")
    return ''.join(p)


def scene_svg(mode='night'):
    """1440×540. Los símbolos desvaídos en la pared, el estante de frascos a
    la derecha, y la MESA a lo ancho con todo el instrumental encima. El
    centro-alto queda tranquilo: ahí caen los paneles."""
    W, H = 1440, 540
    C = PALETTE[mode]
    night = mode == 'night'
    rng = random.Random(20260499)
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
         "viewBox='0 0 %d %d'>" % (W, H, W, H)]
    p.append(
        "<defs>"
        "<linearGradient id='aBen' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='%s'/>"
        "<stop offset='1' stop-color='%s'/></linearGradient>"
        "<radialGradient id='aGlowE' cx='50%%' cy='50%%' r='50%%'>"
        "<stop offset='0' stop-color='%s' stop-opacity='%s'/>"
        "<stop offset='1' stop-color='%s' stop-opacity='0'/></radialGradient>"
        "<radialGradient id='aGlowF' cx='50%%' cy='50%%' r='50%%'>"
        "<stop offset='0' stop-color='%s' stop-opacity='%s'/>"
        "<stop offset='1' stop-color='%s' stop-opacity='0'/></radialGradient>"
        "</defs>" % (C['BENCH'], C['BENCH_D'],
                     C['LIQ_E'], C['GLOW_OP'], C['LIQ_E'],
                     C['FLAME'], C['GLOW_OP'], C['FLAME']))

    # ── los símbolos en la pared, desvaídos y SOLO en los laterales ──
    for kind, cx, cy, s in (('tri', 130, 240, 34), ('moon', 300, 320, 16),
                            ('merc', 90, 380, 22), ('sun', 260, 170, 26),
                            ('tri', 1330, 300, 26), ('sun', 1160, 210, 22),
                            ('moon', 1240, 370, 14), ('merc', 1380, 170, 20)):
        p.append(_symbol(kind, cx, cy, s, C['SYM'], C['SYM_OP']))

    # ── el estante de la derecha con sus frascos ──
    shx = 1080
    p.append("<rect x='%d' y='330' width='260' height='10' fill='%s'/>"
             % (shx, C['SHELF']))
    p.append("<path d='M%d,340 l14,18 M%d,340 l-14,18' stroke='%s' "
             "stroke-width='5'/>" % (shx + 8, shx + 252, C['SHELF']))
    for i, (jw, jh) in enumerate(((30, 40), (24, 30), (34, 46), (26, 36))):
        jx = shx + 22 + i * 60
        p.append("<rect x='%d' y='%d' width='%d' height='%d' rx='5' "
                 "fill='%s' opacity='0.9'/>" % (jx, 330 - jh, jw, jh, C['JAR']))
        p.append("<rect x='%d' y='%d' width='%d' height='7' rx='2' fill='%s'/>"
                 % (jx + jw // 4, 330 - jh - 6, jw // 2, C['CORK']))

    # ── LA MESA, de borde a borde ──
    p.append("<rect x='0' y='%d' width='%d' height='14' fill='%s'/>"
             % (BENCH_TOP, W, C['SHELF']))
    p.append("<rect x='0' y='%d' width='%d' height='%d' fill='url(#aBen)'/>"
             % (BENCH_TOP + 14, W, H - BENCH_TOP - 14))
    p.append("<g stroke='%s' stroke-width='2' opacity='0.35' fill='none'>"
             % C['BENCH_D'])
    for _ in range(8):
        x0 = rng.uniform(0, W - 260)
        y0 = rng.uniform(BENCH_TOP + 30, H - 12)
        p.append("<path d='M%.0f,%.0f h%.0f'/>" % (x0, y0, rng.uniform(90, 240)))
    p.append("</g>")

    # ── la pila de tomos con la VELA encima (izquierda) ──
    bx = 110
    for i, (bw, bh, col) in enumerate(((150, 26, C['BOOK1']),
                                       (136, 22, C['BOOK2']),
                                       (144, 24, C['BOOK3']))):
        by = BENCH_TOP - sum(h for _, h, _ in
                             (((150, 26, 0), (136, 22, 0), (144, 24, 0))[:i + 1]))
        p.append("<rect x='%d' y='%d' width='%d' height='%d' rx='4' fill='%s'/>"
                 % (bx + i * 5, by, bw, bh, col))
        p.append("<rect x='%d' y='%d' width='%d' height='4' fill='%s' "
                 "opacity='0.8'/>" % (bx + i * 5 + 6, by + bh - 7, bw - 12,
                                      C['PAGE']))
    cy_top = BENCH_TOP - 72
    p.append("<rect x='%d' y='%d' width='16' height='44' rx='3' fill='%s'/>"
             % (bx + 62, cy_top - 44, C['CANDLE']))
    if night:
        p.append("<circle cx='%d' cy='%d' r='46' fill='url(#aGlowF)'/>"
                 % (bx + 70, cy_top - 56))
        p.append("<path d='M%d,%d q7,-12 0,-22 q-7,10 0,22 Z' fill='%s'/>"
                 % (bx + 70, cy_top - 46, C['FLAME']))
    else:
        p.append("<path d='M%d,%d v-9' stroke='%s' stroke-width='2'/>"
                 % (bx + 70, cy_top - 44, C['GLASS']))

    # ── el mortero con su mano ──
    mx = 380
    p.append("<path d='M%d,%d h84 q-6,36 -42,36 q-36,0 -42,-36 Z' fill='%s'/>"
             % (mx, BENCH_TOP - 36, C['IRON']))
    p.append("<path d='M%d,%d l26,-34' stroke='%s' stroke-width='9' "
             "stroke-linecap='round'/>" % (mx + 52, BENCH_TOP - 40, C['IRON']))

    # ── el matraz cónico (líquido púrpura) ──
    ex = 640
    p.append("<path d='M%d,%d h24 v-52 h-24 Z M%d,%d l-30,84 h108 l-30,-84 Z' "
             "fill='none' stroke='%s' stroke-width='4' "
             "stroke-linejoin='round'/>"
             % (ex + 12, BENCH_TOP - 84, ex, BENCH_TOP - 84, C['GLASS']))
    p.append("<path d='M%d,%d l-13,38 h74 l-13,-38 Z' fill='%s' opacity='0.9'/>"
             % (ex - 12, BENCH_TOP - 38, C['LIQ_P']))

    # ── el matraz de bola sobre su trípode, burbujeando esmeralda ──
    fx, fy = 880, BENCH_TOP - 66
    if night:
        p.append("<circle cx='%d' cy='%d' r='84' fill='url(#aGlowE)'/>"
                 % (fx, fy))
    p.append("<path d='M%.0f,%d l%.0f,%.0f h%.0f Z' fill='none' stroke='%s' "
             "stroke-width='4'/>" % (fx - 34, BENCH_TOP, 34, -26.0, 68,
                                     C['IRON']))
    p.append("<path d='M%d,%d q-8,10 -8,18 M%d,%d q8,10 8,18' stroke='%s' "
             "stroke-width='4' fill='none'/>"
             % (fx - 30, BENCH_TOP - 26, fx + 30, BENCH_TOP - 26, C['IRON']))
    p.append("<circle cx='%d' cy='%d' r='36' fill='none' stroke='%s' "
             "stroke-width='4'/>" % (fx, fy, C['GLASS']))
    p.append("<rect x='%d' y='%d' width='18' height='26' fill='none' "
             "stroke='%s' stroke-width='4'/>"
             % (fx - 9, fy - 36 - 24, C['GLASS']))
    p.append("<path d='M%d,%d a36,36 0 0,0 72,0 Z' fill='%s' opacity='0.92'/>"
             % (fx - 36, fy, C['LIQ_E']))
    for bx_, by_, br_ in ((fx - 10, fy - 8, 4), (fx + 12, fy - 20, 3),
                          (fx + 2, fy - 34, 2.5)):
        p.append("<circle cx='%d' cy='%d' r='%.1f' fill='none' stroke='%s' "
                 "stroke-width='2' opacity='0.8'/>"
                 % (bx_, by_, br_, C['LIQ_E'] if night else C['GLASS']))
    p.append("<path d='M%d,%d q6,-12 0,-20 q-6,8 0,20 Z' fill='%s'/>"
             % (fx, BENCH_TOP - 6, C['FLAME']))

    # ── el pergamino desenrollado ──
    px_ = 1020
    p.append("<rect x='%d' y='%d' width='104' height='34' rx='4' fill='%s' "
             "opacity='0.95'/>" % (px_, BENCH_TOP - 34, C['PAGE']))
    p.append("<rect x='%d' y='%d' width='10' height='34' rx='5' fill='%s'/>"
             % (px_ - 8, BENCH_TOP - 34, C['CORK']))
    p.append("<rect x='%d' y='%d' width='10' height='34' rx='5' fill='%s'/>"
             % (px_ + 102, BENCH_TOP - 34, C['CORK']))
    p.append("<g stroke='%s' stroke-width='2' opacity='0.5'>" % C['SYM'])
    for i in range(3):
        p.append("<path d='M%d,%d h%d'/>"
                 % (px_ + 12, BENCH_TOP - 26 + i * 8, 80 - i * 14))
    p.append("</g>")
    p.append("</svg>")
    return ''.join(p)


# ══ CAPA 2 · el ALAMBIQUE, esquina inferior derecha ═══════════════════════
def alembic_svg(mode='night'):
    """210×190. El alambique clásico: la cucúrbita con su líquido, el capitel
    con el pico de cisne, y la GOTA DE ORO cayendo en el vial — convierte los
    gráficos en oro, dice la bio."""
    C = PALETTE[mode]
    night = mode == 'night'
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='210' height='190' "
         "viewBox='0 0 210 190'>"]
    if night:
        p.append("<circle cx='160' cy='150' r='38' fill='%s' opacity='0.30'/>"
                 % C['LIQ_G'])
    # la cucúrbita (cuerpo de cebolla) con su base
    p.append("<path d='M30,168 h76 M40,168 q-18,-30 4,-58 q-26,-22 -6,-52 "
             "h60 q20,30 -6,52 q22,28 4,58' fill='none' stroke='%s' "
             "stroke-width='4' stroke-linejoin='round'/>" % C['GLASS'])
    p.append("<path d='M42,166 q-14,-26 6,-52 h40 q20,26 6,52 Z' fill='%s' "
             "opacity='0.9'/>" % C['LIQ_G'])
    # el capitel y el pico de cisne que baja a la derecha
    p.append("<path d='M38,58 q30,-34 60,0' fill='none' stroke='%s' "
             "stroke-width='4'/>" % C['GLASS'])
    p.append("<path d='M96,44 q44,6 54,58 l6,34' fill='none' stroke='%s' "
             "stroke-width='4' stroke-linecap='round'/>" % C['GLASS'])
    # la GOTA de oro, cayendo del pico al vial
    p.append("<path d='M158,146 q5,-9 0,-16 q-5,7 0,16 Z' fill='%s'/>"
             % C['LIQ_G'])
    # el vial que la recoge
    p.append("<path d='M146,152 h24 v22 q0,8 -12,8 q-12,0 -12,-8 Z' "
             "fill='none' stroke='%s' stroke-width='3.5'/>" % C['GLASS'])
    p.append("<path d='M149,166 h18 v8 q0,5 -9,5 q-9,0 -9,-5 Z' fill='%s'/>"
             % C['LIQ_G'])
    # las burbujas dentro de la cucúrbita
    for bx_, by_, br_ in ((60, 140, 4), (78, 128, 3), (70, 150, 2.5)):
        p.append("<circle cx='%d' cy='%d' r='%.1f' fill='none' stroke='%s' "
                 "stroke-width='2' opacity='0.75'/>"
                 % (bx_, by_, br_, C['PAGE'] if night else C['GLASS']))
    p.append("</svg>")
    return ''.join(p)


# ══ el bloque CSS ═════════════════════════════════════════════════════════
def css_block():
    return ("""
    /* ═══ The Alchemist (tienda · camo común) — el LABORATORIO del
       alquimista, con DOS looks (patrón Chronicles / Nile — NO es
       DARK_ALWAYS):

       🌙 dark  · el taller a la luz de la vela: piedra púrpura, los símbolos
                  desvaídos en la pared, la pila de tomos con la vela, el
                  mortero, el matraz cónico púrpura, el de bola burbujeando
                  ESMERALDA sobre su llama, el pergamino y el estante de
                  frascos — y el alambique destilando su gota de ORO en la
                  esquina.
       ☀️ light · el MISMO estudio de día: pergamino cálido, madera, los
                  líquidos en tonos joya y los símbolos como tinta desvaída.

       La mesa se ancla `100% auto center bottom` (nunca `cover`); iOS-safe
       (body transparente + ::before fixed); el logo va por defecto sobre el
       día y blanco sobre la noche, igual que Nile. */
    body.camo-alchemist { background: transparent !important; }
    body.camo-alchemist.light {
      --bg:#f0e2c4;--surface:rgba(255,250,238,0.60);--card:rgba(255,250,238,0.72);
      --border:rgba(90,60,120,0.20);--border2:rgba(90,60,120,0.32);
      --text:#38254a;--muted:rgba(56,37,74,0.62);
      --accent:#6a3fa0;--accent-h:#55328a;--win:#2f8f5a;--loss:#c0392b;--be:#b4803c;
      color: var(--text);
    }
    body.camo-alchemist.light::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __ALE_DAY__ right 4% bottom 2% / 195px auto no-repeat,
        __DAY__ center bottom / 100% auto no-repeat,
        linear-gradient(#f6ecd6,#efe0bc 60%,#e7d4a8);
    }
    body.camo-alchemist.light::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 88% at 50% 44%, transparent 60%, rgba(70,44,100,0.14) 100%);
    }
    body.camo-alchemist:not(.light) {
      --bg:#170f2e;--surface:rgba(255,255,255,0.06);--card:rgba(255,255,255,0.075);
      --border:rgba(150,140,200,0.18);--border2:rgba(150,140,200,0.30);
      --text:#e9e2f2;--muted:rgba(233,226,242,0.62);
      --accent:#35d18e;--accent-h:#27b478;--win:#43d18d;--loss:#e05563;--be:#e8b34a;
      color: var(--text);
    }
    body.camo-alchemist:not(.light)::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __ALE_NIGHT__ right 4% bottom 2% / 195px auto no-repeat,
        __NIGHT__ center bottom / 100% auto no-repeat,
        linear-gradient(#120b26,#170f2e 55%,#241a44);
    }
    body.camo-alchemist:not(.light)::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 90% at 50% 42%, transparent 56%, rgba(5,3,14,0.55) 100%);
    }
    body.camo-alchemist:not(.light) .logo-img {
      content: url('/static/logo_t.png'); filter: invert(1); mix-blend-mode: normal;
    }
"""
            .replace('__ALE_DAY__', datauri(alembic_svg('day')))
            .replace('__ALE_NIGHT__', datauri(alembic_svg('night')))
            .replace('__DAY__', datauri(scene_svg('day')))
            .replace('__NIGHT__', datauri(scene_svg('night'))))


ANCHOR = '    /* ═══ Blackflag (pirate)'


def main():
    html = open(INDEX, encoding='utf-8').read()
    if 'body.camo-alchemist' in html:
        start = html.index('    /* ═══ The Alchemist (tienda')
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
    print('bloque alchemist insertado (%d chars)' % len(block))


if __name__ == '__main__':
    main()
