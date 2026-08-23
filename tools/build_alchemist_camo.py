# -*- coding: utf-8 -*-
"""Genera el bloque CSS del camo THE ALCHEMIST y lo inserta en index.html.

Temática (tienda, camo común $4.99): **LA PÁGINA DEL GRIMORIO** — la bio de
la tienda manda: "púrpuras arcanos y un brillo esmeralda — convierte los
gráficos en oro". v2 tras el veredicto del dueño sobre la v1 (una mesa de
laboratorio): *"el diseño de alquimista no me gusta… iguales al de Egipto"*.
La v1 era la fórmula de los camos de ruleta (escena en franja baja). Ésta es
el cuaderno del alquimista, con el patrón que hizo bueno a Pole — el MISMO
dibujo en dos materiales:

  ☀️ light · la página de VITELA: tinta ferrogálica sobre pergamino, con los
             toques de PAN DE ORO (el centro del diagrama, la gota).
  🌙 dark  · el MISMO dibujo FOSFORESCENTE: el conjuro activo — líneas
             esmeralda con halo y el oro encendido sobre púrpura casi negro.

El dibujo (idéntico en ambos looks — eso ES el patrón Pole):
  · el DIAGRAMA DE LA GRAN OBRA abajo a la izquierda: la cuadratura del
    círculo (círculo–triángulo–cuadrado–círculo) con los triángulos de los
    cuatro elementos y el símbolo del ORO en el centro. Trazos GRUESOS —
    el dueño rechazó las telarañas de línea fina (lección de Premium).
  · la RECETA a lo largo del borde inferior: la fila de símbolos alquímicos
    (mercurio, azufre, sal, oro, plata) como GEOMETRÍA pura — nada de
    <text>, un SVG de background no hereda fuentes — sobre sus renglones.
  · el ALAMBIQUE dibujado a tinta en la esquina inferior derecha, destilando
    su GOTA DE ORO: el objeto que nombra al camo.
  · los renglones de margen a los lados en CSS puro (abrazan cualquier
    pantalla sin estirarse).

Una geometría, dos tintas (dict PALETTE) — re-correr el script re-inserta el
bloque, es idempotente.

Reglas del sitio que respeta:
  · El adorno se RECONOCE a la primera → el diagrama y el alambique.
  · Todo lo importante vive en la franja BAJA y en los laterales (los
    paneles tapan el centro).
  · iOS-safe: body transparente + ::before position:fixed.
  · Jinja: ningún `{#`/`{{`/`{%` dentro del CSS insertado.

Uso:  python3 tools/build_alchemist_camo.py        (desde la raíz del repo)
"""
import math
import os
import re
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'scalpel', 'templates', 'index.html')


def datauri(svg):
    svg = re.sub(r'\s+', ' ', svg).strip()
    return "url(\"data:image/svg+xml,%s\")" % quote(svg, safe="/:=;,.-()'% ")


# ══ un dibujo, dos tintas ═════════════════════════════════════════════════
PALETTE = {
    # ☀️ tinta ferrogálica + pan de oro sobre vitela
    'day': dict(INK='#4a3520', GOLD='#c8912a', HALO=None, HALO_G=None),
    # 🌙 el conjuro activo: esmeralda con halo + oro encendido
    'night': dict(INK='#35d18e', GOLD='#e8b34a',
                  HALO='#35d18e', HALO_G='#e8b34a'),
}


def _stroke(d, C, w=4.5, gold=False, fill='none'):
    """Un trazo con su halo cuando el look es fosforescente. El halo es el
    MISMO path, gordo y translúcido, debajo — así el 'brillo' funciona en un
    SVG de background sin filtros."""
    col = C['GOLD'] if gold else C['INK']
    halo = C['HALO_G'] if gold else C['HALO']
    out = []
    if halo:
        out.append("<path d='%s' fill='%s' stroke='%s' stroke-width='%.1f' "
                   "opacity='0.28' stroke-linecap='round'/>"
                   % (d, 'none' if fill == 'none' else halo, halo, w * 3))
    out.append("<path d='%s' fill='%s' stroke='%s' stroke-width='%.1f' "
               "stroke-linecap='round' stroke-linejoin='round'/>"
               % (d, fill if fill == 'none' else col, col, w))
    return ''.join(out)


def _circle(cx, cy, r, C, w=4.5, gold=False):
    d = ("M%.0f,%.0f a%.0f,%.0f 0 1,0 %.0f,0 a%.0f,%.0f 0 1,0 -%.0f,0"
         % (cx - r, cy, r, r, 2 * r, r, r, 2 * r))
    return _stroke(d, C, w, gold)


def _poly(pts, C, w=4.5, gold=False, close=True):
    d = 'M' + ' L'.join('%.0f,%.0f' % p for p in pts) + (' Z' if close else '')
    return _stroke(d, C, w, gold)


def _elemento(cx, cy, s, C, quien):
    """Los triángulos de los cuatro elementos: fuego △, agua ▽, aire △ con
    barra, tierra ▽ con barra. Macizos y chicos."""
    up = quien in ('fuego', 'aire')
    dy = -s if up else s
    pts = [(cx - s, cy - dy * .55), (cx + s, cy - dy * .55), (cx, cy + dy * .75)]
    out = [_poly(pts, C, 3.5)]
    if quien in ('aire', 'tierra'):
        out.append(_stroke('M%.0f,%.0f L%.0f,%.0f'
                           % (cx - s * .6, cy + dy * .1, cx + s * .6,
                              cy + dy * .1), C, 3.5))
    return ''.join(out)


def diagram_svg(mode='day'):
    """420×420: el diagrama de la GRAN OBRA — la cuadratura del círculo con
    los cuatro elementos y el oro en el centro."""
    C = PALETTE[mode]
    cx = cy = 210
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='420' height='420' "
         "viewBox='0 0 420 420'>"]
    p.append(_circle(cx, cy, 185, C, 5.5))          # el círculo exterior
    # el cuadrado, girado 45° no: recto, inscrito
    s = 185 * 0.7071
    p.append(_poly([(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s),
                    (cx - s, cy + s)], C, 4.5))
    # el triángulo inscrito en el cuadrado
    p.append(_poly([(cx, cy - s), (cx + s, cy + s), (cx - s, cy + s)], C, 4.5))
    p.append(_circle(cx, cy, 92, C, 4.5))           # el círculo interior
    # el símbolo del ORO en el centro: círculo con su punto, en pan de oro
    p.append(_circle(cx, cy, 40, C, 5, gold=True))
    if C['HALO_G']:
        p.append("<circle cx='%d' cy='%d' r='22' fill='%s' opacity='0.25'/>"
                 % (cx, cy, C['HALO_G']))
    p.append("<circle cx='%d' cy='%d' r='11' fill='%s'/>" % (cx, cy, C['GOLD']))
    # los cuatro elementos en las esquinas del cuadrado
    p.append(_elemento(cx, cy - 185 * .82, 17, C, 'fuego'))
    p.append(_elemento(cx + 185 * .82, cy, 17, C, 'agua'))
    p.append(_elemento(cx, cy + 185 * .82, 17, C, 'tierra'))
    p.append(_elemento(cx - 185 * .82, cy, 17, C, 'aire'))
    # los puntitos cardinales sobre el círculo exterior (macizos)
    for i in range(8):
        a = i * math.pi / 4 + math.pi / 8
        p.append("<circle cx='%.0f' cy='%.0f' r='5.5' fill='%s'/>"
                 % (cx + 185 * math.cos(a), cy + 185 * math.sin(a), C['INK']))
    p.append("</svg>")
    return ''.join(p)


def _sym(kind, cx, cy, s, C):
    """Los símbolos de la receta, como geometría: mercurio ☿, azufre 🜍,
    sal 🜔, oro ☉ y plata ☽ — trazos gruesos, nada de <text>."""
    out = []
    if kind == 'mercurio':
        out.append(_circle(cx, cy, s * .55, C, 3.8))
        out.append(_stroke('M%.0f,%.0f v%.0f M%.0f,%.0f h%.0f'
                           % (cx, cy + s * .55, s * .8, cx - s * .5,
                              cy + s * 1.0, s), C, 3.8))
        out.append(_stroke('M%.0f,%.0f a%.0f,%.0f 0 0,0 %.0f,0'
                           % (cx - s * .55, cy - s * .85, s * .55, s * .55,
                              s * 1.1), C, 3.8))
    elif kind == 'azufre':
        out.append(_poly([(cx - s * .6, cy), (cx + s * .6, cy),
                          (cx, cy - s * .95)], C, 3.8))
        out.append(_stroke('M%.0f,%.0f v%.0f M%.0f,%.0f h%.0f'
                           % (cx, cy, s * .9, cx - s * .45, cy + s * .55,
                              s * .9), C, 3.8))
    elif kind == 'sal':
        out.append(_circle(cx, cy, s * .75, C, 3.8))
        out.append(_stroke('M%.0f,%.0f h%.0f'
                           % (cx - s * .75, cy, s * 1.5), C, 3.8))
    elif kind == 'oro':
        out.append(_circle(cx, cy, s * .75, C, 3.8, gold=True))
        out.append("<circle cx='%.0f' cy='%.0f' r='%.1f' fill='%s'/>"
                   % (cx, cy, s * .22, C['GOLD']))
    else:                                            # plata
        d = ("M%.0f,%.0f a%.0f,%.0f 0 1,1 0,%.0f a%.0f,%.0f 0 1,0 0,-%.0f Z"
             % (cx, cy - s * .8, s * .8, s * .8, s * 1.6, s * .58, s * .58,
                s * 1.6))
        out.append(_stroke(d, C, 3.5))
    return ''.join(out)


def recipe_svg(mode='day'):
    """1440×150: la línea de la receta — símbolos sobre sus renglones, con
    la flecha de la transmutación apuntando al ORO (el último)."""
    C = PALETTE[mode]
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='1440' height='150' "
         "viewBox='0 0 1440 150'>"]
    # los renglones (dos, como cuaderno)
    p.append(_stroke('M40,112 h560', C, 2.5))
    p.append(_stroke('M40,138 h430', C, 2.5))
    # la receta: mercurio + azufre + sal → oro (con la plata como resto)
    xs = (95, 205, 315, 545, 425)
    kinds = ('mercurio', 'azufre', 'sal', 'oro', 'plata')
    for x, k in zip(xs, kinds):
        p.append(_sym(k, x, 62, 26, C))
    # los signos entre símbolos: + + = (geometría, no texto)
    for x in (150, 260):
        p.append(_stroke('M%.0f,62 h24 M%.0f,50 v24' % (x - 12, x), C, 3.5))
    p.append(_stroke('M470,54 h30 M470,68 h30', C, 3.5))
    # la flechita de la transmutación bajo el oro
    p.append(_stroke('M515,112 h60 l-12,-9 m12,9 l-12,9', C, 3, gold=True))
    p.append("</svg>")
    return ''.join(p)


def alembic_svg(mode='day'):
    """230×210: el alambique A TINTA — cucúrbita con su rayado de grabado,
    capitel, pico de cisne y la gota de ORO cayendo al vial."""
    C = PALETTE[mode]
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='230' height='210' "
         "viewBox='0 0 230 210'>"]
    # cuerpo de cebolla
    p.append(_stroke('M42,188 h84 M52,188 q-20,-34 4,-64 q-28,-24 -6,-58 h64 '
                     'q22,34 -6,58 q24,30 4,64', C, 4.5))
    # el rayado del grabado dentro del cuerpo (media tinta)
    p.append("<g opacity='0.55'>")
    for i in range(5):
        y = 132 + i * 11
        p.append(_stroke('M%d,%d h%d' % (58 + i * 2, y, 58 - i * 6), C, 2.2))
    p.append("</g>")
    # capitel + pico de cisne
    p.append(_stroke('M46,66 q34,-38 66,0', C, 4.5))
    p.append(_stroke('M110,50 q48,8 58,62 l6,38', C, 4.5))
    # la GOTA de oro
    p.append(_stroke('M174,162 q6,-11 0,-19 q-6,8 0,19 Z', C, 3,
                     gold=True))
    if PALETTE[mode]['HALO_G']:
        p.append("<circle cx='174' cy='154' r='16' fill='%s' opacity='0.22'/>"
                 % C['HALO_G'])
    # el vial
    p.append(_stroke('M160,170 h28 v24 q0,9 -14,9 q-14,0 -14,-9 Z', C, 3.5))
    p.append("<path d='M164,186 h20 v8 q0,5 -10,5 q-10,0 -10,-5 Z' "
             "fill='%s'/>" % C['GOLD'])
    p.append("</svg>")
    return ''.join(p)


# ══ el bloque CSS ═════════════════════════════════════════════════════════
def _margins_css(ink, alpha):
    """Los renglones de margen del cuaderno, en CSS puro (dos líneas por
    lado, pegadas al viewport — sin SVG que estirar)."""
    c = 'rgba(%d,%d,%d,%s)' % (int(ink[1:3], 16), int(ink[3:5], 16),
                               int(ink[5:7], 16), alpha)
    return (
        "linear-gradient(90deg,transparent 54px,%(c)s 54px 56px,transparent 56px) left top / 100%% 100%% no-repeat,\n"
        "        linear-gradient(90deg,transparent 64px,%(c)s 64px 66px,transparent 66px) left top / 100%% 100%% no-repeat,\n"
        "        linear-gradient(270deg,transparent 54px,%(c)s 54px 56px,transparent 56px) left top / 100%% 100%% no-repeat,\n"
        "        linear-gradient(270deg,transparent 64px,%(c)s 64px 66px,transparent 66px) left top / 100%% 100%% no-repeat"
        % {'c': c})


def css_block():
    return ("""
    /* ═══ The Alchemist (tienda · camo común) — LA PÁGINA DEL GRIMORIO, v2.
       La v1 era una mesa de laboratorio y al dueño no le gustó (con razón:
       la fórmula de los camos de ruleta otra vez). Ahora es el patrón que
       hizo bueno a Pole — el MISMO dibujo en dos materiales:
       ☀️ light · tinta ferrogálica sobre VITELA, con pan de oro.
       🌙 dark  · el conjuro ACTIVO: el mismo dibujo fosforescente —
                  esmeralda con halo y oro encendido sobre púrpura casi negro.
       El dibujo: el diagrama de la GRAN OBRA (cuadratura del círculo + los
       cuatro elementos + el oro en el centro) abajo-izquierda, la RECETA de
       símbolos alquímicos sobre sus renglones a lo largo del borde inferior,
       el ALAMBIQUE a tinta con su gota de oro en la esquina, y los renglones
       de margen a los lados (CSS puro: abrazan cualquier pantalla). Trazos
       GRUESOS a propósito — nada de telarañas de línea fina. */
    body.camo-alchemist { background: transparent !important; }
    body.camo-alchemist.light {
      --bg:#f2e6c8;--surface:rgba(255,251,240,0.62);--card:rgba(255,251,240,0.74);
      --border:rgba(74,53,32,0.22);--border2:rgba(74,53,32,0.34);
      --text:#38254a;--muted:rgba(56,37,74,0.62);
      --accent:#6a3fa0;--accent-h:#55328a;--win:#2f8f5a;--loss:#c0392b;--be:#c8912a;
      color: var(--text);
    }
    body.camo-alchemist.light::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __ALE_DAY__ right 3% bottom 4% / 200px auto no-repeat,
        __DIA_DAY__ left 2% bottom -60px / 360px auto no-repeat,
        __REC_DAY__ center bottom / 100% auto no-repeat,
        __MARG_DAY__,
        radial-gradient(ellipse 60% 44% at 18% 12%, rgba(138,106,52,0.14), transparent 60%),
        radial-gradient(ellipse 50% 40% at 86% 30%, rgba(138,106,52,0.10), transparent 62%),
        linear-gradient(170deg,#f6ecd4,#efe2c0 52%,#e6d3a6);
    }
    body.camo-alchemist.light::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 88% at 50% 44%, transparent 58%, rgba(90,62,24,0.20) 100%);
    }
    body.camo-alchemist:not(.light) {
      --bg:#150d28;--surface:rgba(255,255,255,0.06);--card:rgba(255,255,255,0.075);
      --border:rgba(53,209,142,0.20);--border2:rgba(53,209,142,0.32);
      --text:#e9e2f2;--muted:rgba(233,226,242,0.62);
      --accent:#35d18e;--accent-h:#27b478;--win:#43d18d;--loss:#e05563;--be:#e8b34a;
      color: var(--text);
    }
    body.camo-alchemist:not(.light)::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __ALE_NIGHT__ right 3% bottom 4% / 200px auto no-repeat,
        __DIA_NIGHT__ left 2% bottom -60px / 360px auto no-repeat,
        __REC_NIGHT__ center bottom / 100% auto no-repeat,
        __MARG_NIGHT__,
        radial-gradient(ellipse 70% 55% at 22% 78%, rgba(53,209,142,0.10), transparent 60%),
        radial-gradient(ellipse 46% 40% at 88% 82%, rgba(232,179,74,0.08), transparent 62%),
        linear-gradient(170deg,#100922,#150d28 52%,#1e1438);
    }
    body.camo-alchemist:not(.light)::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 90% at 50% 42%, transparent 56%, rgba(4,2,12,0.55) 100%);
    }
    body.camo-alchemist:not(.light) .logo-img {
      content: url('/static/logo_t.png'); filter: invert(1); mix-blend-mode: normal;
    }
"""
            .replace('__ALE_DAY__', datauri(alembic_svg('day')))
            .replace('__ALE_NIGHT__', datauri(alembic_svg('night')))
            .replace('__DIA_DAY__', datauri(diagram_svg('day')))
            .replace('__DIA_NIGHT__', datauri(diagram_svg('night')))
            .replace('__REC_DAY__', datauri(recipe_svg('day')))
            .replace('__REC_NIGHT__', datauri(recipe_svg('night')))
            .replace('__MARG_DAY__', _margins_css('#4a3520', '0.28'))
            .replace('__MARG_NIGHT__', _margins_css('#35d18e', '0.16')))


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
