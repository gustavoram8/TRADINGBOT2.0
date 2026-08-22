# -*- coding: utf-8 -*-
"""Genera el bloque CSS del camo AMERICAN FOOTBALL (`gridiron`) y lo inserta
en index.html.

Temática (ruleta, mes real OCTUBRE 2026 tras la rodada — lote '2026-09'):
**noche de partido**. La placa `gridiron` ya puso el lenguaje: campo de noche,
torres de luz, postes amarillos. El camo es la vista desde ADENTRO: el cielo
azul-noche del estadio arriba y, abajo del todo, el CÉSPED — bandas de corte
alternadas, líneas de yarda blancas con sus números y las marcas de hash. En
la esquina inferior derecha, el BALÓN de cuero con su cordón blanco (el objeto
que nombra al camo, como el tomo de Chronicles).

UN SOLO LOOK — **DARK_ALWAYS**, como Premium: un partido de la NFL se ve de
noche, y una versión diurna diluiría la identidad. La preferencia clara del
usuario solo marca `.camo-day` (mascota / iconos), el suelo no cambia.
⚠️ Eso significa que el slug va en LAS DOS copias de la lista de index.html
   (pre-paint `DARK_ALWAYS` y apply-theme `DARK_ALWAYS_T`) — ese cableado NO
   lo hace este script, es una edición aparte y está hecha a mano.

Reglas del sitio que este archivo respeta (las de siempre):
  · Nada de `cover` en una escena con horizonte: el campo se ancla con
    `center bottom / 100% auto` — la altura depende SOLO del ancho y el
    césped queda pegado abajo en cualquier relación de aspecto.
  · Todo lo importante vive en la franja BAJA del lienzo (los paneles del
    /app tapan el centro).
  · El adorno de esquina tiene que RECONOCERSE a la primera → un balón.
  · Legal: cero logos, cero nombres de equipo, cero jugadores. Aquí solo hay
    césped, luces y un balón — el jugador vive en la botarga del ilustrador.
  · iOS-safe: body transparente + ::before position:fixed.
  · Jinja: ningún `{#`/`{{`/`{%` puede quedar dentro del CSS insertado.

Uso:  python3 tools/build_gridiron_camo.py        (desde la raíz del repo)
"""
import os
import random
import re
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'scalpel', 'templates', 'index.html')

# ── paleta ────────────────────────────────────────────────────────────────
TURF_A = '#155e33'          # banda de corte iluminada
TURF_B = '#0e4726'          # banda de corte en sombra
TURF_EDGE = '#0a3018'       # borde del campo, fuera de las luces
LINE = '#eef6ee'            # pintura blanca de las líneas
GOLD = '#f2b332'            # el amarillo de los postes → acento del camo
STAND = '#0a1322'           # gradería en sombra
STAND_D = '#060c18'
SKYGLOW = '#16283f'         # resplandor de las torres contra el cielo


def datauri(svg):
    svg = re.sub(r'\s+', ' ', svg).strip()
    return "url(\"data:image/svg+xml,%s\")" % quote(svg, safe="/:=;,.-()'% ")


# ══ CAPA 1 · la escena: gradería, torres de luz y el CÉSPED ═══════════════
def scene_svg():
    """1440×540. El campo ocupa la franja baja; encima, la silueta de la
    gradería con sus puntitos de público y dos torres de luz encendidas.

    ⚠️ Los números de yarda se dibujan con TRAZOS (paths), no con <text>: un
    SVG de background no hereda fuentes y cada visor lo tipografiaría
    distinto — trazado a mano sale idéntico en todos lados."""
    W, H = 1440, 540
    FIELD_TOP = 330             # donde arranca el césped
    rng = random.Random(20261001)
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
         "viewBox='0 0 %d %d'>" % (W, H, W, H)]
    p.append(
        "<defs>"
        "<radialGradient id='gwash' cx='50%' cy='0%' r='90%'>"
        "<stop offset='0' stop-color='#f5f9ff' stop-opacity='0.30'/>"
        "<stop offset='1' stop-color='#f5f9ff' stop-opacity='0'/></radialGradient>"
        "<linearGradient id='gturf' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='#1a6b3b'/>"
        "<stop offset='1' stop-color='#0c3c20'/></linearGradient>"
        "</defs>")

    # ── gradería: dos niveles en sombra con el público como puntitos ──
    p.append("<rect x='0' y='%d' width='%d' height='%d' fill='%s'/>"
             % (170, W, FIELD_TOP - 170, STAND_D))
    p.append("<path d='M0,258 L%d,238 L%d,%d L0,%d Z' fill='%s'/>"
             % (W, W, FIELD_TOP, FIELD_TOP, STAND))
    # público: puntos tenues repartidos en la gradería (nadie identificable)
    p.append("<g fill='#8fa4c4'>")
    for _ in range(210):
        x = rng.uniform(6, W - 6)
        y = rng.uniform(184, 316)
        p.append("<circle cx='%.0f' cy='%.0f' r='%.1f' opacity='%.2f'/>"
                 % (x, y, rng.uniform(0.9, 1.7), rng.uniform(0.10, 0.34)))
    p.append("</g>")

    # ── torres de luz: mástil + panel de focos + halo ──
    for bx in (250, 1190):
        p.append("<radialGradient id='glow%d' cx='50%%' cy='50%%' r='50%%'>"
                 "<stop offset='0' stop-color='#dce9ff' stop-opacity='0.50'/>"
                 "<stop offset='1' stop-color='#dce9ff' stop-opacity='0'/>"
                 "</radialGradient>" % bx)
        p.append("<ellipse cx='%d' cy='96' rx='190' ry='96' fill='url(#glow%d)'/>"
                 % (bx, bx))
        p.append("<rect x='%d' y='108' width='7' height='150' fill='#0b1526'/>"
                 % (bx - 3))
        p.append("<rect x='%d' y='64' width='104' height='44' rx='6' "
                 "fill='#0e1a2e'/>" % (bx - 52))
        for r_ in range(2):
            for c_ in range(4):
                p.append("<rect x='%d' y='%d' width='18' height='14' rx='2.5' "
                         "fill='#f2f7ff' opacity='0.95'/>"
                         % (bx - 46 + c_ * 24, 69 + r_ * 20))

    # ── los POSTES amarillos (a la izquierda, la placa los lleva a la
    #    derecha — así el par placa+camo no se repite en espejo) ──
    gx = 150
    p.append("<g stroke='%s' stroke-width='9' stroke-linecap='round' "
             "fill='none'>" % GOLD)
    p.append("<path d='M%d,%d L%d,196'/>" % (gx, FIELD_TOP + 26, gx))
    p.append("<path d='M%d,196 L%d,196'/>" % (gx - 58, gx + 58))
    p.append("<path d='M%d,196 L%d,88 M%d,196 L%d,88'/>"
             % (gx - 58, gx - 58, gx + 58, gx + 58))
    p.append("</g>")

    # ── el CAMPO ──
    p.append("<rect x='0' y='%d' width='%d' height='%d' fill='url(#gturf)'/>"
             % (FIELD_TOP, W, H - FIELD_TOP))
    # bandas de corte verticales, una yarda-línea cada dos bandas
    band = 96
    for i in range(0, W // band + 1):
        if i % 2 == 0:
            p.append("<rect x='%d' y='%d' width='%d' height='%d' fill='%s' "
                     "opacity='0.5'/>" % (i * band, FIELD_TOP, band,
                                          H - FIELD_TOP, TURF_A))
    # lavado de luz de las torres sobre el césped
    p.append("<rect x='0' y='%d' width='%d' height='%d' fill='url(#gwash)'/>"
             % (FIELD_TOP, W, H - FIELD_TOP))
    # líneas de yarda + hash marks
    p.append("<g stroke='%s' stroke-width='4' opacity='0.85'>" % LINE)
    for i in range(0, W // band + 1):
        x = i * band
        p.append("<path d='M%d,%d L%d,%d'/>" % (x, FIELD_TOP + 6, x, H))
    p.append("</g>")
    p.append("<g stroke='%s' stroke-width='3' opacity='0.55'>" % LINE)
    for i in range(W // 24):
        x = 12 + i * 24
        p.append("<path d='M%d,%d L%d,%d'/>" % (x, 420, x, 432))
        p.append("<path d='M%d,%d L%d,%d'/>" % (x, 494, x, 506))
    p.append("</g>")

    # ── números de yarda, TRAZADOS (10 · 50 · 10) ──
    def digit(d, x, y, s=1.0):
        """Dígitos de palo seco trazados a mano (solo 0/1/5 hacen falta)."""
        st = ("<g transform='translate(%.0f,%.0f) scale(%.2f)' stroke='%s' "
              "stroke-width='7' stroke-linecap='square' fill='none' "
              "opacity='0.9'>" % (x, y, s, LINE))
        if d == '1':
            st += "<path d='M10,4 L10,44'/>"
        elif d == '0':
            st += "<path d='M4,8 L20,8 L20,40 L4,40 Z'/>"
        elif d == '5':
            st += "<path d='M22,4 L4,4 L4,22 L20,22 L20,40 L2,40'/>"
        return st + "</g>"

    for cx_, num in ((288, '10'), (672, '50'), (1056, '10')):
        p.append(digit(num[0], cx_ - 30, 442))
        p.append(digit(num[1], cx_ + 4, 442))

    p.append("</svg>")
    return ''.join(p)


# ══ CAPA 2 · el BALÓN, esquina inferior derecha ═══════════════════════════
def ball_svg():
    """260×150. Cuero con brillo de luz de estadio, costura y cordón blanco.
    Un balón es un OBJETO: pasa la regla legal (ni logos ni jugadores)."""
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='260' height='150' "
         "viewBox='0 0 260 150'>"]
    p.append(
        "<defs>"
        "<linearGradient id='bl' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='#a35a2a'/>"
        "<stop offset='0.55' stop-color='#7c3f1c'/>"
        "<stop offset='1' stop-color='#592c12'/></linearGradient>"
        "<radialGradient id='bsh' cx='35%' cy='28%' r='70%'>"
        "<stop offset='0' stop-color='#ffdba8' stop-opacity='0.35'/>"
        "<stop offset='1' stop-color='#ffdba8' stop-opacity='0'/></radialGradient>"
        "</defs>")
    # sombra sobre el césped
    p.append("<ellipse cx='132' cy='128' rx='96' ry='14' fill='#03130a' "
             "opacity='0.55'/>")
    # cuerpo (dos puntas, apoyado en diagonal suave)
    p.append("<g transform='rotate(-8 130 78)'>")
    p.append("<path d='M22,78 C42,34 92,16 130,16 C168,16 218,34 238,78 "
             "C218,122 168,140 130,140 C92,140 42,122 22,78 Z' fill='url(#bl)'/>")
    p.append("<path d='M22,78 C42,34 92,16 130,16 C168,16 218,34 238,78 "
             "C218,122 168,140 130,140 C92,140 42,122 22,78 Z' fill='url(#bsh)'/>")
    # costuras de las puntas
    p.append("<path d='M40,52 C56,40 72,32 88,28 M40,104 C56,116 72,124 88,128' "
             "stroke='#3d1d0a' stroke-width='3' fill='none' opacity='0.7'/>")
    p.append("<path d='M220,52 C204,40 188,32 172,28 M220,104 C204,116 188,124 "
             "172,128' stroke='#3d1d0a' stroke-width='3' fill='none' "
             "opacity='0.7'/>")
    # el CORDÓN: línea larga + 7 puntadas cruzadas
    p.append("<path d='M85,78 L175,78' stroke='#f4f0e6' stroke-width='6' "
             "stroke-linecap='round'/>")
    for i in range(7):
        x = 94 + i * 12
        p.append("<path d='M%d,68 L%d,88' stroke='#f4f0e6' stroke-width='5' "
                 "stroke-linecap='round'/>" % (x, x))
    p.append("</g></svg>")
    return ''.join(p)


# ══ el bloque CSS ═════════════════════════════════════════════════════════
def css_block():
    return ("""
    /* ═══ American Football (`gridiron`, ruleta · mes real octubre 2026) —
       NOCHE DE PARTIDO, un solo look (DARK_ALWAYS como Premium: un partido
       de la NFL se ve de noche; la preferencia clara solo marca .camo-day).

       Escena: cielo azul-noche del estadio, gradería en sombra con el
       público como puntitos, dos torres de luz encendidas, los postes
       amarillos a la izquierda y, abajo del todo, el CÉSPED — bandas de
       corte alternadas, líneas de yarda con sus números trazados y las
       marcas de hash. En la esquina inferior derecha, el balón de cuero con
       su cordón blanco. Cero logos, cero equipos, cero jugadores (la regla
       legal): el jugador vive en la botarga.

       El campo se ancla con `100% auto center bottom` (nunca `cover`);
       iOS-safe: body transparente + ::before fixed. El acento es el amarillo
       de los postes. */
    body.camo-gridiron { background: transparent !important; }
    body.camo-gridiron {
      --bg:#081120;--surface:rgba(255,255,255,0.055);--card:rgba(255,255,255,0.07);
      --border:rgba(242,179,50,0.16);--border2:rgba(242,179,50,0.30);
      --text:#edf3f0;--muted:rgba(237,243,240,0.62);
      --accent:#f2b332;--accent-h:#d99a1b;--win:#43d18d;--loss:#e05563;--be:#f2b332;
      color: var(--text);
    }
    body.camo-gridiron::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __BALL__ right 3% bottom 4% / 230px auto no-repeat,
        __SCENE__ center bottom / 100% auto no-repeat,
        radial-gradient(ellipse 60% 30% at 18% 10%, rgba(220,233,255,0.10), transparent 70%),
        radial-gradient(ellipse 60% 30% at 84% 10%, rgba(220,233,255,0.10), transparent 70%),
        linear-gradient(#050a14,#0a1526 55%,#12233c);
    }
    body.camo-gridiron::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 90% at 50% 40%, transparent 58%, rgba(3,7,14,0.55) 100%);
    }
    body.camo-gridiron .logo-img {
      content: url('/static/logo_t.png'); filter: invert(1); mix-blend-mode: normal;
    }
"""
            .replace('__BALL__', datauri(ball_svg()))
            .replace('__SCENE__', datauri(scene_svg())))


ANCHOR = '    /* ═══ Blackflag (pirate)'


def main():
    html = open(INDEX, encoding='utf-8').read()
    if 'body.camo-gridiron' in html:
        start = html.index('    /* ═══ American Football (`gridiron`')
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
    print('bloque gridiron insertado (%d chars)' % len(block))


if __name__ == '__main__':
    main()
