# -*- coding: utf-8 -*-
"""Genera el bloque CSS del camo NILE y lo inserta en index.html.

Temática (ruleta, mes real NOVIEMBRE 2026 tras la rodada — lote '2026-10'):
**el Egipto del río**. La placa `nile` puso el lenguaje: arena + lapislázuli,
pirámides, obelisco, papiros y la franja del río. El camo es la escena
completa: las tres pirámides en el horizonte, el obelisco con sus marcas, las
palmeras, las dunas y — abajo del todo — EL NILO, con una faluca navegándolo
en la esquina inferior derecha (la vela latina es el objeto que nombra al
camo, como el tomo de Chronicles y el balón de Gridiron).

DOS LOOKS (patrón Chronicles/Pole/Mission — NO va en DARK_ALWAYS):
  ☀️ day   · desierto a pleno sol: cielo crema, sol alto, caras de pirámide
             iluminada/en sombra, río lapislázuli.
  🌙 night · la MISMA geometría de noche: luna, estrellas, pirámides en
             sombra con el filo lunar, y el río oscuro con los reflejos.
Una geometría, dos paletas (dict PALETTE) — re-correr el script re-inserta el
bloque, es idempotente.

Reglas del sitio que respeta (las de siempre):
  · Nada de `cover` con horizonte: la tierra se ancla `center bottom /
    100% auto`.
  · Todo lo importante vive en la franja BAJA (los paneles tapan el centro).
  · El adorno de esquina se RECONOCE a la primera → la faluca en el río.
  · Legal / división del arte: monumentos y barcas son OBJETOS y se dibujan
    acá; el faraón vive en la botarga del ilustrador.
  · iOS-safe: body transparente + ::before position:fixed.
  · Jinja: ningún `{#`/`{{`/`{%` dentro del CSS insertado.

Uso:  python3 tools/build_nile_camo.py        (desde la raíz del repo)
"""
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
    # ☀️ pleno sol — los tonos de la placa `nile` (arena + lapislázuli)
    'day': dict(PYR_L='#d5a55f', PYR_D='#b4803c', PYR2_L='#ddb16c',
                PYR2_D='#bd8a44', SAND='#e0bd86', SAND_D='#c9a468',
                OBE='#cfa059', OBE_CAP='#ead0a0', OBE_MARK='#8a6a34',
                PALM='#4d7c3c', PALM_T='#7a5a30',
                RIV_A='#2b66ad', RIV_B='#103a70', WAVE='#84baea',
                SAIL='#f6efe0', HULL='#6b4a26',
                ASTRO='#e5952f', ASTRO_OP='0.9'),
    # 🌙 la misma escena de noche: luna, filos lunares y el río oscuro
    'night': dict(PYR_L='#3b3050', PYR_D='#241c38', PYR2_L='#453a5c',
                  PYR2_D='#2c2244', SAND='#2e2542', SAND_D='#221b33',
                  OBE='#3d3358', OBE_CAP='#8fa0c8', OBE_MARK='#151024',
                  PALM='#1e2c22', PALM_T='#241c30',
                  RIV_A='#12305c', RIV_B='#060f24', WAVE='#7d9fd6',
                  SAIL='#c9d4e8', HULL='#1c1428',
                  ASTRO='#e8e4d4', ASTRO_OP='0.95'),
}


def pyramid(x, w, y_base, apex_h, light, dark):
    """Pirámide con cara iluminada (izq) y cara en sombra (der)."""
    ax = x + w * 0.52                       # el ápice, apenas descentrado
    return ("<path d='M%d,%d L%.0f,%d L%.0f,%d Z' fill='%s'/>"
            "<path d='M%.0f,%d L%d,%d L%.0f,%d Z' fill='%s'/>"
            % (x, y_base, ax, y_base - apex_h, ax, y_base, light,
               ax, y_base - apex_h, x + w, y_base, ax, y_base, dark))


def scene_svg(mode='day'):
    """1440×540. Horizonte de pirámides + obelisco + palmeras sobre las
    dunas, y el RÍO como franja final. Sol o luna arriba a la derecha."""
    W, H = 1440, 540
    C = PALETTE[mode]
    night = mode == 'night'
    RIVER_TOP = 470
    SAND_TOP = 300
    rng = random.Random(20261101)
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
         "viewBox='0 0 %d %d'>" % (W, H, W, H)]
    p.append(
        "<defs>"
        "<linearGradient id='nRiv' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='%s'/>"
        "<stop offset='1' stop-color='%s'/></linearGradient>"
        "<linearGradient id='nSand' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='%s'/>"
        "<stop offset='1' stop-color='%s'/></linearGradient>"
        "<radialGradient id='nAstro' cx='50%%' cy='50%%' r='50%%'>"
        "<stop offset='0' stop-color='%s' stop-opacity='%s'/>"
        "<stop offset='0.6' stop-color='%s' stop-opacity='0.35'/>"
        "<stop offset='1' stop-color='%s' stop-opacity='0'/></radialGradient>"
        "</defs>" % (C['RIV_A'], C['RIV_B'], C['SAND'], C['SAND_D'],
                     C['ASTRO'], C['ASTRO_OP'], C['ASTRO'], C['ASTRO']))

    # ── sol / luna, arriba a la derecha (los paneles no llegan ahí) ──
    p.append("<circle cx='1240' cy='96' r='84' fill='url(#nAstro)'/>")
    p.append("<circle cx='1240' cy='96' r='34' fill='%s' opacity='%s'/>"
             % (C['ASTRO'], '0.95' if night else '0.8'))
    if night:
        # el mordisco de la luna + estrellas de 4 puntas (regla Mission:
        # destellos, no círculos — y pocas, con rechazo de distancia)
        p.append("<circle cx='1226' cy='84' r='30' fill='#0d1226' opacity='0.55'/>")
        pts, tries = [], 0
        while len(pts) < 14 and tries < 300:
            tries += 1
            x, y = rng.uniform(30, 1380), rng.uniform(20, 210)
            if (x - 1240) ** 2 + (y - 96) ** 2 < 150 ** 2:
                continue
            if all((x - a) ** 2 + (y - b) ** 2 > 120 ** 2 for a, b in pts):
                pts.append((x, y))
        for x, y in pts:
            s = rng.uniform(3.5, 7)
            p.append("<path d='M%.0f,%.0f l%.1f,%.1f l%.1f,%.1f l%.1f,%.1f "
                     "l%.1f,%.1f Z' fill='#cfd8ee' opacity='%.2f'/>"
                     % (x, y - s, s * .28, s * .72, s * .72, s * .28,
                        -s * .72, s * .28, -s * .28, s * .72,
                        rng.uniform(0.4, 0.85)))

    # ── las tres pirámides en el horizonte de arena ──
    p.append(pyramid(310, 330, SAND_TOP + 40, 210, C['PYR_L'], C['PYR_D']))
    p.append(pyramid(640, 240, SAND_TOP + 42, 150, C['PYR2_L'], C['PYR2_D']))
    p.append(pyramid(880, 160, SAND_TOP + 44, 96, C['PYR_L'], C['PYR_D']))

    # ── el obelisco, con sus marcas ──
    ox = 1130
    p.append("<rect x='%d' y='%d' width='26' height='150' fill='%s'/>"
             % (ox, SAND_TOP - 104, C['OBE']))
    p.append("<path d='M%d,%d L%d,%d L%d,%d Z' fill='%s'/>"
             % (ox, SAND_TOP - 104, ox + 13, SAND_TOP - 132, ox + 26,
                SAND_TOP - 104, C['OBE_CAP']))
    p.append("<g fill='%s' opacity='0.8'>" % C['OBE_MARK'])
    for i in range(6):
        p.append("<rect x='%d' y='%d' width='14' height='5'/>"
                 % (ox + 6, SAND_TOP - 88 + i * 20))
    p.append("</g>")

    # ── dunas ──
    p.append("<rect x='0' y='%d' width='%d' height='%d' fill='url(#nSand)'/>"
             % (SAND_TOP, W, RIVER_TOP - SAND_TOP))
    p.append("<path d='M0,%d Q360,%d 720,%d T1440,%d L1440,%d L0,%d Z' "
             "fill='%s' opacity='0.5'/>"
             % (SAND_TOP + 46, SAND_TOP + 6, SAND_TOP + 40, SAND_TOP + 30,
                RIVER_TOP, RIVER_TOP, C['SAND_D']))

    # ── palmeras en la orilla (troncos curvos + abanicos de hojas) ──
    for px_, s_ in ((150, 1.0), (208, 0.72), (1330, 0.9)):
        top = RIVER_TOP - 90 * s_
        p.append("<path d='M%d,%d Q%d,%d %d,%.0f' stroke='%s' fill='none' "
                 "stroke-width='%.0f' stroke-linecap='round'/>"
                 % (px_, RIVER_TOP, px_ + 10, RIVER_TOP - 50 * s_, px_ + 18,
                    top, C['PALM_T'], 7 * s_))
        p.append("<g stroke='%s' stroke-width='%.0f' fill='none' "
                 "stroke-linecap='round'>" % (C['PALM'], 5 * s_))
        for ang in (-80, -45, -10, 25, 60, 95):
            dx = 46 * s_ * (1 if ang > -40 else 0.8)
            p.append("<path d='M%d,%.0f q%.0f,%.0f %.0f,%.0f'/>"
                     % (px_ + 18, top, dx * 0.6,
                        -18 * s_ + ang * 0.12, dx, ang * 0.42))
        p.append("</g>")

    # ── papiros junto al agua (los de la placa) ──
    p.append("<g stroke='%s' stroke-width='3' stroke-linecap='round' "
             "fill='none'>" % C['PALM'])
    for i, hx in enumerate((980, 992, 1004, 1016)):
        hh = (26, 16, 30, 20)[i]
        p.append("<path d='M%d,%d V%d'/>" % (hx, RIVER_TOP, RIVER_TOP - hh))
        p.append("<circle cx='%d' cy='%d' r='4' fill='%s' stroke='none'/>"
                 % (hx, RIVER_TOP - hh - 3, C['PALM']))
    p.append("</g>")

    # ── EL NILO ──
    p.append("<rect x='0' y='%d' width='%d' height='%d' fill='url(#nRiv)'/>"
             % (RIVER_TOP, W, H - RIVER_TOP))
    p.append("<g stroke='%s' stroke-width='2' opacity='0.55' fill='none'>"
             % C['WAVE'])
    for _ in range(14):
        x0 = rng.uniform(0, W - 220)
        y0 = rng.uniform(RIVER_TOP + 10, H - 8)
        p.append("<path d='M%.0f,%.0f h%.0f'/>" % (x0, y0, rng.uniform(70, 200)))
    p.append("</g>")
    if night:
        # el reflejo de la luna, roto en trazos
        p.append("<g stroke='#cfd8ee' stroke-width='3' opacity='0.4'>")
        for i in range(5):
            p.append("<path d='M%d,%d h%d'/>"
                     % (1218 + rng.randint(-14, 14), RIVER_TOP + 12 + i * 13,
                        rng.randint(20, 46)))
        p.append("</g>")
    p.append("</svg>")
    return ''.join(p)


# ══ CAPA 2 · la FALUCA, esquina inferior derecha ══════════════════════════
def felucca_svg(mode='day'):
    """230×170. La barca del Nilo: casco, mástil inclinado y la vela latina
    triangular — inconfundible. Navega EN el río (la capa se ancla abajo a la
    derecha, sobre la franja del agua)."""
    C = PALETTE[mode]
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='230' height='170' "
         "viewBox='0 0 230 170'>"]
    # vela latina: triángulo curvo colgado de una verga inclinada
    p.append("<path d='M52,128 L176,120 L96,16 Z' fill='%s' opacity='0.97'/>"
             % C['SAIL'])
    p.append("<path d='M96,16 Q118,70 176,120' stroke='%s' stroke-width='3' "
             "fill='none' opacity='0.5'/>" % C['HULL'])
    # verga y mástil
    p.append("<path d='M40,136 L100,10' stroke='%s' stroke-width='5' "
             "stroke-linecap='round'/>" % C['HULL'])
    p.append("<path d='M108,128 L104,52' stroke='%s' stroke-width='4' "
             "stroke-linecap='round'/>" % C['HULL'])
    # casco en media luna
    p.append("<path d='M30,132 L196,132 Q178,156 120,156 Q62,156 30,132 Z' "
             "fill='%s'/>" % C['HULL'])
    # la estela en el agua
    p.append("<g stroke='%s' stroke-width='2.5' opacity='0.5' fill='none'>"
             % C['WAVE'])
    p.append("<path d='M14,160 h58 M158,162 h52 M84,166 h74'/>")
    p.append("</g>")
    p.append("</svg>")
    return ''.join(p)


# ══ el bloque CSS ═════════════════════════════════════════════════════════
def css_block():
    return ("""
    /* ═══ Nile (ruleta · mes real noviembre 2026) — el EGIPTO DEL RÍO, con
       DOS looks (patrón Chronicles / Pole / Mission — NO es DARK_ALWAYS):

       ☀️ light · desierto a pleno sol: cielo crema, las tres pirámides con su
                  cara iluminada y su cara en sombra, el obelisco, palmeras y
                  papiros en la orilla, y el NILO en lapislázuli abajo del
                  todo, con la faluca navegando en la esquina.
       🌙 dark  · la MISMA escena de noche: luna con su mordisco, estrellas de
                  cuatro puntas, filos lunares en la piedra y el reflejo de la
                  luna roto en trazos sobre el agua.

       La tierra se ancla `100% auto center bottom` (nunca `cover`); iOS-safe
       (body transparente + ::before fixed); el logo va por defecto sobre el
       día y blanco sobre la noche, igual que Chronicles. */
    body.camo-nile { background: transparent !important; }
    body.camo-nile.light {
      --bg:#f2e4c8;--surface:rgba(255,251,240,0.60);--card:rgba(255,251,240,0.72);
      --border:rgba(90,64,26,0.20);--border2:rgba(90,64,26,0.32);
      --text:#3c2b14;--muted:rgba(60,43,20,0.62);
      --accent:#2b66ad;--accent-h:#1d4f8e;--win:#2f8f5a;--loss:#c0392b;--be:#b4803c;
      color: var(--text);
    }
    body.camo-nile.light::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __FEL_DAY__ right 4% bottom 2% / 210px auto no-repeat,
        __DAY__ center bottom / 100% auto no-repeat,
        linear-gradient(#fcefd3,#f3d9a4 58%,#efce97);
    }
    body.camo-nile.light::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 88% at 50% 44%, transparent 60%, rgba(96,64,20,0.16) 100%);
    }
    body.camo-nile:not(.light) {
      --bg:#0d1226;--surface:rgba(255,255,255,0.06);--card:rgba(255,255,255,0.075);
      --border:rgba(143,160,200,0.18);--border2:rgba(143,160,200,0.30);
      --text:#e9e4d6;--muted:rgba(233,228,214,0.62);
      --accent:#e8b34a;--accent-h:#cf9930;--win:#43d18d;--loss:#e05563;--be:#e8b34a;
      color: var(--text);
    }
    body.camo-nile:not(.light)::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __FEL_NIGHT__ right 4% bottom 2% / 210px auto no-repeat,
        __NIGHT__ center bottom / 100% auto no-repeat,
        linear-gradient(#070b1a,#0d1226 52%,#1a2545);
    }
    body.camo-nile:not(.light)::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 90% at 50% 42%, transparent 56%, rgba(3,5,12,0.55) 100%);
    }
    body.camo-nile:not(.light) .logo-img {
      content: url('/static/logo_t.png'); filter: invert(1); mix-blend-mode: normal;
    }
"""
            .replace('__FEL_DAY__', datauri(felucca_svg('day')))
            .replace('__FEL_NIGHT__', datauri(felucca_svg('night')))
            .replace('__DAY__', datauri(scene_svg('day')))
            .replace('__NIGHT__', datauri(scene_svg('night'))))


ANCHOR = '    /* ═══ Blackflag (pirate)'


def main():
    html = open(INDEX, encoding='utf-8').read()
    if 'body.camo-nile' in html:
        start = html.index('    /* ═══ Nile (ruleta')
        end = html.index(ANCHOR, start)
        html = html[:start] + html[end:]
    if ANCHOR not in html:
        raise SystemExit('No encontré el ancla del bloque Blackflag.')
    block = css_block()
    for bad in ('{#', '{%', '{{'):
        if bad in block:
            raise SystemExit('El bloque contiene %r — Jinja lo interpretaría.' % bad)
    html = html.replace(ANCHOR, block + '\n\n' + ANCHOR, 1)
    open(INDEX, 'w', encoding='utf-8').write(html)
    print('bloque nile insertado (%d chars)' % len(block))


if __name__ == '__main__':
    main()
