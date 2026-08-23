# -*- coding: utf-8 -*-
"""Genera el bloque CSS del camo HIGH NOON y lo inserta en index.html.

Temática (tienda, camo común $4.99): **el lejano oeste al mediodía** — la bio
de la tienda lo fija desde siempre: "cuero, arena y un duelo al mediodía".
La escena es la calle principal de un pueblo fronterizo: mesetas de fondo,
el saloon con su falsa fachada y su toldo, el almacén, el banco de dos
plantas, la torre de agua, los saguaros y la bola de matojo rodando por la
calle. El adorno de esquina que NOMBRA al camo (como la faluca de Nile o el
balón de Gridiron): **la estrella de sheriff**.

DOS LOOKS pedidos por el dueño (patrón Chronicles/Nile — NO va en
DARK_ALWAYS):
  ☀️ day   · el duelo a pleno sol: cielo recalentado, sol alto y blanco, la
             madera y el adobe en tonos de cuero, sombras cortas de mediodía.
  🌙 night · la MISMA calle de noche: luna, estrellas de cuatro puntas, las
             siluetas del pueblo con las ventanas del saloon encendidas.
Una geometría, dos paletas (dict PALETTE) — re-correr el script re-inserta el
bloque, es idempotente.

Reglas del sitio que respeta (las de siempre):
  · Nada de `cover` con horizonte: la tierra se ancla `center bottom /
    100% auto`.
  · Todo lo importante vive en la franja BAJA (los paneles tapan el centro).
  · El adorno de esquina se RECONOCE a la primera → la estrella de sheriff.
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
    # ☀️ mediodía — cuero, arena y adobe recalentado (los tonos de la bio)
    'day': dict(MESA='#c98a52', MESA_D='#b06f3a',
                WOOD='#8a5a32', WOOD_D='#6e4322', TRIM='#5a3618',
                ADOBE='#dcb277', ROOF='#7a4a26',
                WIN='#4c3016', DOOR='#3c2510',
                TANK='#9a6a3c', LEG='#6e4a28',
                GROUND='#dcb277', GROUND_D='#c99a5e', RUT='#a87c46',
                CACTUS='#4e7a3a', CACTUS_D='#3c6130', TUMBLE='#8a6a34',
                ASTRO='#fff6dc', ASTRO_OP='0.95',
                BADGE_BG='#8a5230', BADGE_RING='#caa24a',
                BADGE_STAR='#e0b45c', BADGE_EDGE='#7a5a1e'),
    # 🌙 la misma calle de noche: siluetas frías y ventanas encendidas
    'night': dict(MESA='#262046', MESA_D='#1a1634',
                  WOOD='#241a34', WOOD_D='#1a1228', TRIM='#100b1e',
                  ADOBE='#2e2548', ROOF='#1c1530',
                  WIN='#ffb85c', DOOR='#e8933c',
                  TANK='#2a2144', LEG='#1c1530',
                  GROUND='#282045', GROUND_D='#1e1836', RUT='#151028',
                  CACTUS='#1c2c20', CACTUS_D='#141f17', TUMBLE='#3a2f52',
                  ASTRO='#e8e4d4', ASTRO_OP='0.95',
                  BADGE_BG='#241c3a', BADGE_RING='#8fa0c8',
                  BADGE_STAR='#c9d4e8', BADGE_EDGE='#5a6890'),
}

GROUND_TOP = 470          # donde arranca la calle
BASE = 470                # los edificios apoyan aquí


def _win(x, y, w, h, fill, lit):
    """Ventana: de día un hueco oscuro, de noche un rectángulo encendido."""
    extra = " opacity='0.92'" if lit else ''
    return "<rect x='%d' y='%d' width='%d' height='%d' fill='%s'%s/>" % (
        x, y, w, h, fill, extra)


def scene_svg(mode='day'):
    """1440×540. Mesetas al fondo, la calle del pueblo con sus edificios en
    los dos tercios laterales (el centro queda tranquilo: ahí caen los
    paneles), saguaros, y el suelo con las rodadas y el matojo."""
    W, H = 1440, 540
    C = PALETTE[mode]
    night = mode == 'night'
    rng = random.Random(20261031)
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
         "viewBox='0 0 %d %d'>" % (W, H, W, H)]
    p.append(
        "<defs>"
        "<linearGradient id='hGro' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='%s'/>"
        "<stop offset='1' stop-color='%s'/></linearGradient>"
        "<radialGradient id='hAstro' cx='50%%' cy='50%%' r='50%%'>"
        "<stop offset='0' stop-color='%s' stop-opacity='%s'/>"
        "<stop offset='0.55' stop-color='%s' stop-opacity='0.4'/>"
        "<stop offset='1' stop-color='%s' stop-opacity='0'/></radialGradient>"
        "</defs>" % (C['GROUND'], C['GROUND_D'],
                     C['ASTRO'], C['ASTRO_OP'], C['ASTRO'], C['ASTRO']))

    # ── el sol del duelo / la luna — alto y a la derecha, fuera de los
    #    paneles. De día el halo es ancho: es el sol que aplasta la calle. ──
    p.append("<circle cx='1240' cy='92' r='%d' fill='url(#hAstro)'/>"
             % (110 if not night else 84))
    p.append("<circle cx='1240' cy='92' r='34' fill='%s' opacity='0.95'/>"
             % C['ASTRO'])
    if night:
        p.append("<circle cx='1227' cy='81' r='29' fill='#0d0f24' opacity='0.5'/>")
        pts, tries = [], 0
        while len(pts) < 14 and tries < 300:
            tries += 1
            x, y = rng.uniform(30, 1380), rng.uniform(20, 220)
            if (x - 1240) ** 2 + (y - 92) ** 2 < 150 ** 2:
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

    # ── mesetas de fondo (buttes de tapa plana — el desierto del oeste) ──
    for x0, w, h_, top_w, col in ((-60, 340, 120, 150, C['MESA_D']),
                                  (250, 260, 96, 120, C['MESA']),
                                  (930, 300, 110, 140, C['MESA']),
                                  (1210, 300, 130, 160, C['MESA_D'])):
        xm = x0 + (w - top_w) / 2.0
        p.append("<path d='M%d,%d L%.0f,%d L%.0f,%d L%d,%d Z' fill='%s' "
                 "opacity='0.85'/>"
                 % (x0, GROUND_TOP, xm, GROUND_TOP - h_, xm + top_w,
                    GROUND_TOP - h_, x0 + w, GROUND_TOP, col))

    # ── LA CALLE ──
    p.append("<rect x='0' y='%d' width='%d' height='%d' fill='url(#hGro)'/>"
             % (GROUND_TOP, W, H - GROUND_TOP))

    # ── manzana IZQUIERDA: el SALOON con su falsa fachada y su toldo ──
    sx = 70
    p.append("<rect x='%d' y='%d' width='190' height='140' fill='%s'/>"
             % (sx, BASE - 140, C['WOOD']))
    # falsa fachada escalonada + cornisa
    p.append("<path d='M%d,%d h190 v-34 h-40 v-14 h-110 v14 h-40 Z' fill='%s'/>"
             % (sx, BASE - 140, C['WOOD_D']))
    p.append("<rect x='%d' y='%d' width='190' height='6' fill='%s'/>"
             % (sx, BASE - 144, C['TRIM']))
    # toldo del porche con sus postes
    p.append("<rect x='%d' y='%d' width='190' height='12' fill='%s'/>"
             % (sx, BASE - 74, C['ROOF']))
    for px_ in (sx + 12, sx + 95, sx + 178):
        p.append("<rect x='%d' y='%d' width='5' height='62' fill='%s'/>"
                 % (px_, BASE - 62, C['TRIM']))
    # puerta de vaivén (dos hojas cortas) + ventanas
    p.append("<rect x='%d' y='%d' width='34' height='44' fill='%s'/>"
             % (sx + 78, BASE - 44, C['DOOR']))
    p.append("<rect x='%d' y='%d' width='14' height='26' fill='%s' opacity='0.85'/>"
             % (sx + 80, BASE - 40, C['WIN']))
    p.append("<rect x='%d' y='%d' width='14' height='26' fill='%s' opacity='0.85'/>"
             % (sx + 96, BASE - 40, C['WIN']))
    p.append(_win(sx + 22, BASE - 52, 26, 30, C['WIN'], night))
    p.append(_win(sx + 142, BASE - 52, 26, 30, C['WIN'], night))
    p.append(_win(sx + 55, BASE - 122, 30, 24, C['WIN'], night))
    p.append(_win(sx + 105, BASE - 122, 30, 24, C['WIN'], night))

    # ── el ALMACÉN, pegado al saloon (parapeto triangular de adobe) ──
    gx = 290
    p.append("<rect x='%d' y='%d' width='130' height='104' fill='%s'/>"
             % (gx, BASE - 104, C['ADOBE']))
    p.append("<path d='M%d,%d h130 l-18,-26 h-94 Z' fill='%s'/>"
             % (gx, BASE - 104, C['ROOF']))
    p.append(_win(gx + 18, BASE - 78, 26, 30, C['WIN'], night))
    p.append("<rect x='%d' y='%d' width='30' height='52' fill='%s'/>"
             % (gx + 78, BASE - 52, C['DOOR']))

    # ── manzana DERECHA: el banco de dos plantas + la TORRE DE AGUA ──
    bx = 960
    p.append("<rect x='%d' y='%d' width='150' height='168' fill='%s'/>"
             % (bx, BASE - 168, C['WOOD_D']))
    p.append("<rect x='%d' y='%d' width='150' height='7' fill='%s'/>"
             % (bx, BASE - 172, C['TRIM']))
    p.append("<rect x='%d' y='%d' width='150' height='5' fill='%s'/>"
             % (bx, BASE - 92, C['TRIM']))
    for row, wy in ((0, BASE - 150), (1, BASE - 72)):
        for i in range(3):
            p.append(_win(bx + 18 + i * 46, wy, 26, 32, C['WIN'],
                          night and (row + i) % 2 == 0))
    # la torre: cuatro patas cruzadas, el tanque y su techo cónico
    tx, ty = 1250, BASE - 190          # esquina sup-izq del tanque
    p.append("<g stroke='%s' stroke-width='7' stroke-linecap='round'>"
             % C['LEG'])
    p.append("<path d='M%d,%d L%d,%d M%d,%d L%d,%d'/>"
             % (tx + 8, ty + 74, tx - 16, BASE, tx + 80, ty + 74, tx + 104, BASE))
    p.append("<path d='M%d,%d L%d,%d M%d,%d L%d,%d' stroke-width='4'/>"
             % (tx - 8, BASE - 56, tx + 98, BASE - 12,
                tx + 96, BASE - 56, tx - 10, BASE - 12))
    p.append("</g>")
    p.append("<rect x='%d' y='%d' width='88' height='74' rx='6' fill='%s'/>"
             % (tx, ty, C['TANK']))
    p.append("<g stroke='%s' stroke-width='3' opacity='0.6'>" % C['TRIM'])
    p.append("<path d='M%d,%d h88 M%d,%d h88'/>"
             % (tx, ty + 22, tx, ty + 52))
    p.append("</g>")
    p.append("<path d='M%d,%d L%d,%d L%d,%d Z' fill='%s'/>"
             % (tx - 8, ty, tx + 44, ty - 34, tx + 96, ty, C['ROOF']))

    # ── saguaros (el de dos brazos es la silueta que TODOS reconocen) ──
    for cx_, s_ in ((510, 1.0), (760, 0.62), (1395, 0.8)):
        h_ = 110 * s_
        wda = 11 * s_
        p.append("<g fill='%s'>" % (C['CACTUS'] if not night else C['CACTUS']))
        p.append("<rect x='%.0f' y='%.0f' width='%.0f' height='%.0f' rx='%.0f'/>"
                 % (cx_ - wda / 2, BASE - h_, wda, h_, wda / 2))
        # brazo izquierdo (sube en L) y derecho, a alturas distintas
        p.append("<path d='M%.0f,%.0f h-%.0f v-%.0f h%.0f v%.0f h-%.0f Z' "
                 "fill='%s'/>"
                 % (cx_ - wda / 2, BASE - h_ * 0.55, 20 * s_, 34 * s_,
                    9 * s_, 25 * s_ + 9 * s_, 0, C['CACTUS_D']))
        p.append("<path d='M%.0f,%.0f h%.0f v-%.0f h%.0f v%.0f h-%.0f Z' "
                 "fill='%s'/>"
                 % (cx_ + wda / 2, BASE - h_ * 0.38, 11 * s_, 26 * s_,
                    9 * s_, 17 * s_ + 9 * s_, 0, C['CACTUS_D']))
        p.append("</g>")

    # ── el suelo del duelo: rodadas de carreta + la bola de matojo ──
    p.append("<g stroke='%s' stroke-width='3' opacity='0.5' fill='none'>"
             % C['RUT'])
    for _ in range(12):
        x0 = rng.uniform(0, W - 200)
        y0 = rng.uniform(GROUND_TOP + 14, H - 10)
        p.append("<path d='M%.0f,%.0f h%.0f'/>" % (x0, y0, rng.uniform(60, 180)))
    p.append("</g>")
    # matojo: una madeja de arcos dentro de un círculo, rodando abajo-izq
    mx, my, mr = 150, 506, 26
    p.append("<g stroke='%s' stroke-width='2' fill='none' opacity='0.8'>"
             % C['TUMBLE'])
    p.append("<circle cx='%d' cy='%d' r='%d'/>" % (mx, my, mr))
    for a0 in range(0, 360, 45):
        r = math.radians(a0)
        p.append("<path d='M%.0f,%.0f Q%d,%d %.0f,%.0f'/>"
                 % (mx + mr * math.cos(r), my + mr * math.sin(r), mx, my,
                    mx + mr * math.cos(r + 2.2), my + mr * math.sin(r + 2.2)))
    p.append("</g>")
    p.append("</svg>")
    return ''.join(p)


# ══ CAPA 2 · la ESTRELLA DE SHERIFF, esquina inferior derecha ═════════════
def badge_svg(mode='day'):
    """210×200. La placa: anillo con remaches y la estrella de cinco puntas
    con bolitas en las puntas — el objeto que nombra el duelo del mediodía."""
    C = PALETTE[mode]
    cx, cy = 105, 100
    ro, ri = 62, 26
    pts = []
    for i in range(10):
        r = ro if i % 2 == 0 else ri
        a = -math.pi / 2 + i * math.pi / 5
        pts.append('%.1f,%.1f' % (cx + r * math.cos(a), cy + r * math.sin(a)))
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='210' height='200' "
         "viewBox='0 0 210 200'>"]
    p.append("<circle cx='%d' cy='%d' r='86' fill='%s' opacity='0.95'/>"
             % (cx, cy, C['BADGE_BG']))
    p.append("<circle cx='%d' cy='%d' r='86' fill='none' stroke='%s' "
             "stroke-width='7'/>" % (cx, cy, C['BADGE_RING']))
    # remaches del anillo
    for i in range(8):
        a = i * math.pi / 4
        p.append("<circle cx='%.1f' cy='%.1f' r='4' fill='%s'/>"
                 % (cx + 86 * math.cos(a), cy + 86 * math.sin(a),
                    C['BADGE_RING']))
    p.append("<polygon points='%s' fill='%s' stroke='%s' stroke-width='4' "
             "stroke-linejoin='round'/>"
             % (' '.join(pts), C['BADGE_STAR'], C['BADGE_EDGE']))
    # bolitas en las cinco puntas (la placa clásica de sheriff las lleva)
    for i in range(0, 10, 2):
        a = -math.pi / 2 + i * math.pi / 5
        p.append("<circle cx='%.1f' cy='%.1f' r='7' fill='%s' stroke='%s' "
                 "stroke-width='3'/>"
                 % (cx + ro * math.cos(a), cy + ro * math.sin(a),
                    C['BADGE_STAR'], C['BADGE_EDGE']))
    p.append("<circle cx='%d' cy='%d' r='9' fill='%s'/>"
             % (cx, cy, C['BADGE_EDGE']))
    p.append("</svg>")
    return ''.join(p)


# ══ el bloque CSS ═════════════════════════════════════════════════════════
def css_block():
    return ("""
    /* ═══ High Noon (tienda · camo común) — el LEJANO OESTE del duelo al
       mediodía, con DOS looks (patrón Chronicles / Nile — NO es DARK_ALWAYS):

       ☀️ light · la calle principal a pleno sol: cielo recalentado, sol alto
                  con su halo blanco, mesetas al fondo, el saloon con su falsa
                  fachada y su toldo, el almacén de adobe, el banco de dos
                  plantas, la torre de agua, los saguaros y el matojo rodando
                  entre las rodadas de carreta.
       🌙 dark  · la MISMA calle de noche: luna con su mordisco, estrellas de
                  cuatro puntas y el pueblo en silueta con las ventanas del
                  saloon encendidas en ámbar.

       El adorno de esquina es la ESTRELLA DE SHERIFF (de latón al sol, de
       plata a la luna). La tierra se ancla `100% auto center bottom` (nunca
       `cover`); iOS-safe (body transparente + ::before fixed); el logo va por
       defecto sobre el día y blanco sobre la noche, igual que Nile. */
    body.camo-highnoon { background: transparent !important; }
    body.camo-highnoon.light {
      --bg:#f3e3c2;--surface:rgba(255,250,238,0.60);--card:rgba(255,250,238,0.72);
      --border:rgba(96,64,22,0.20);--border2:rgba(96,64,22,0.32);
      --text:#3a2a12;--muted:rgba(58,42,18,0.62);
      --accent:#b3402a;--accent-h:#93301e;--win:#2f8f5a;--loss:#c0392b;--be:#b4803c;
      color: var(--text);
    }
    body.camo-highnoon.light::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __BADGE_DAY__ right 4% bottom 2% / 190px auto no-repeat,
        __DAY__ center bottom / 100% auto no-repeat,
        linear-gradient(#f8ecd0,#f2d9a0 55%,#eccc92);
    }
    body.camo-highnoon.light::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 88% at 50% 44%, transparent 60%, rgba(96,58,18,0.16) 100%);
    }
    body.camo-highnoon:not(.light) {
      --bg:#131836;--surface:rgba(255,255,255,0.06);--card:rgba(255,255,255,0.075);
      --border:rgba(160,170,210,0.18);--border2:rgba(160,170,210,0.30);
      --text:#ece4d2;--muted:rgba(236,228,210,0.62);
      --accent:#e8a94a;--accent-h:#d18f2e;--win:#43d18d;--loss:#e05563;--be:#e8a94a;
      color: var(--text);
    }
    body.camo-highnoon:not(.light)::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __BADGE_NIGHT__ right 4% bottom 2% / 190px auto no-repeat,
        __NIGHT__ center bottom / 100% auto no-repeat,
        linear-gradient(#0d1128,#131836 52%,#232c52);
    }
    body.camo-highnoon:not(.light)::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 90% at 50% 42%, transparent 56%, rgba(4,6,16,0.55) 100%);
    }
    body.camo-highnoon:not(.light) .logo-img {
      content: url('/static/logo_t.png'); filter: invert(1); mix-blend-mode: normal;
    }
"""
            .replace('__BADGE_DAY__', datauri(badge_svg('day')))
            .replace('__BADGE_NIGHT__', datauri(badge_svg('night')))
            .replace('__DAY__', datauri(scene_svg('day')))
            .replace('__NIGHT__', datauri(scene_svg('night'))))


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
