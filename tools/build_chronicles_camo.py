# -*- coding: utf-8 -*-
"""Genera el bloque CSS del camo CHRONICLES y lo inserta en index.html.

Temática (temporada 1, agosto 2026): **MEDIEVAL**. El dueño corrigió el primer
intento —«Chronicles no se trata de volcanes, se trata de Medieval; lo que tiene
que predominar de fondo es una especie de Reino»—, así que la lava y la paleta
oscura de la placa `chronicles` (#120409 / #2a0810 / #5c1210, lava #ff5a1e,
brasa #ff8a3c, oro pálido #ffd08a) se quedan como CIELO y horizonte, y quien
manda es el reino amurallado.

Escena: una ciudad medieval de noche recortada contra el resplandor del
horizonte — muralla almenada de borde a borde, puerta iluminada entre dos
torres, torres con techo cónico y estandartes, la torre del homenaje, la aguja
de la catedral, los tejados del caserío y las ventanas encendidas; a lo lejos,
un volcán chico que mantiene el vínculo con la placa. En la esquina inferior
derecha, el TOMO abierto — el objeto que le da el nombre al camo.

Reglas aprendidas que este archivo respeta:
  · Nada de `cover` en una escena con horizonte: la tierra se ancla con
    `center bottom / 100% auto`, así la altura depende SOLO del ancho y el
    horizonte queda pegado abajo en cualquier relación de aspecto.
  · Todo lo que importa vive en la franja BAJA del lienzo: es la única que los
    paneles del /app no tapan.
  · Lo que DEBE tocarse va en el MISMO SVG.
  · iOS-safe: body transparente + ::before position:fixed (nunca
    background-attachment:fixed).
  · El adorno de esquina tiene que RECONOCERSE a la primera.

Uso:  python3 tools/build_chronicles_camo.py        (desde la raíz del repo)
"""
import math
import os
import random
import re
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'scalpel', 'templates', 'index.html')

# ── paleta ────────────────────────────────────────────────────────────────
BASALT_FAR = '#3a1720'
BASALT_MID = '#260d14'
BASALT_NEAR = '#180709'
COLUMN = '#100407'
COLUMN_EDGE = '#4a1f1e'
LAVA = '#ff5a1e'
EMBER = '#ff8a3c'
GOLD = '#ffd08a'


def datauri(svg):
    """SVG compacto como data-URI de CSS (comillas simples adentro)."""
    svg = re.sub(r'\s+', ' ', svg).strip()
    return "url(\"data:image/svg+xml,%s\")" % quote(svg, safe="/:=;,.-()'% ")


def ridge(pts, y_bottom, fill, opacity=1.0):
    d = ' '.join('L%d,%d' % (x, y) for x, y in pts)
    return ("<path d='M%d,%d %s L%d,%d L%d,%d Z' fill='%s' opacity='%s'/>"
            % (pts[0][0], y_bottom, d, pts[-1][0], y_bottom,
               pts[0][0], y_bottom, fill, opacity))


def jagged(rng, x0, x1, n, base, amp, sharp=0.55):
    """Cresta dentada: picos de basalto, no colinas suaves."""
    out = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        y = base + rng.uniform(-amp, amp)
        if rng.random() < sharp:                 # cada tanto, una aguja
            y -= rng.uniform(amp * 0.5, amp * 1.4)
        out.append((int(x), int(y)))
    return out


# ══ CAPA 1 · la escena (el REINO de noche) ════════════════════════════════
PALETTE = {
    # NOCHE — el reino recortado contra el resplandor del horizonte.
    'dark': dict(STONE='#1d0d13', STONE_D='#140810', STONE_L='#2a141c',
                 ROOF='#3a1520', WIN='#ffb45c', BANNER='#a5301f',
                 GROUND='#0d0509'),
    # DÍA — pedido del dueño (2026-08-02): «para light mode… un reino rodeado
    # de colinas de montañas, un sol, cielo azul y despejado». Misma
    # arquitectura, piedra clara, tejas de terracota y ventanas APAGADAS (de
    # día una ventana encendida se lee como error, no como vida).
    'light': dict(STONE='#e3d9c4', STONE_D='#c9bda3', STONE_L='#f4ecdc',
                  ROOF='#b0533a', WIN='#5e5546', BANNER='#b23a2a',
                  GROUND='#6f9f4f'),
}


def scene_svg(mode='dark'):
    """La imagen del camo: un REINO MEDIEVAL, de noche o a pleno día.

    Corrección del dueño (2026-08-02): «Chronicles no se trata de volcanes, se
    trata de MEDIEVAL; lo que tiene que predominar de fondo es una especie de
    Reino». La lava y los tonos oscuros se quedan, pero como CIELO y horizonte
    lejano — quien manda es la muralla: almenas, torres con techo cónico,
    estandartes, la torre del homenaje, la catedral y las ventanas encendidas.
    Todo lo importante vive en la franja BAJA del lienzo, que es la única que
    los paneles del /app no tapan.

    Reglas del sitio que respeta: la tierra se ancla con `100% auto center
    bottom` (nunca `cover`, o el horizonte flota); lo que debe tocarse va en el
    MISMO SVG; el adorno de esquina tiene que reconocerse a la primera."""
    W, H = 1440, 560
    rng = random.Random(20260802)
    day = mode == 'light'
    C = PALETTE[mode]
    STONE, STONE_D, STONE_L = C['STONE'], C['STONE_D'], C['STONE_L']
    ROOF, WIN, BANNER = C['ROOF'], C['WIN'], C['BANNER']
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d' "
         "viewBox='0 0 %d %d'>" % (W, H, W, H)]
    p.append(
        "<defs>"
        "<linearGradient id='kSky' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='%s' stop-opacity='0'/>"
        "<stop offset='1' stop-color='%s' stop-opacity='0.40'/></linearGradient>"
        "<radialGradient id='kCrater' cx='50%%' cy='60%%' r='55%%'>"
        "<stop offset='0' stop-color='#ffc98a' stop-opacity='0.5'/>"
        "<stop offset='0.5' stop-color='%s' stop-opacity='0.18'/>"
        "<stop offset='1' stop-color='%s' stop-opacity='0'/></radialGradient>"
        "<radialGradient id='kGate' cx='50%%' cy='85%%' r='70%%'>"
        "<stop offset='0' stop-color='#ffcf8a' stop-opacity='0.9'/>"
        "<stop offset='1' stop-color='%s' stop-opacity='0'/></radialGradient>"
        "<radialGradient id='kSun' cx='50%%' cy='50%%' r='50%%'>"
        "<stop offset='0' stop-color='#fffbe8'/>"
        "<stop offset='0.55' stop-color='#ffe9a8'/>"
        "<stop offset='1' stop-color='#ffe9a8' stop-opacity='0'/></radialGradient>"
        "<linearGradient id='kHillA' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='#8fbe6c'/><stop offset='1' stop-color='#6fa052'/>"
        "</linearGradient>"
        "<linearGradient id='kHillB' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='#79ad5c'/><stop offset='1' stop-color='#578a42'/>"
        "</linearGradient>"
        "<linearGradient id='kHillC' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='#63954a'/><stop offset='1' stop-color='#3f6f33'/>"
        "</linearGradient>"
        "</defs>" % (LAVA, LAVA, LAVA, LAVA, LAVA))

    def hill(y0, amp, seed, fill, seg=240):
        """Colina de lomo REDONDO. Las crestas dentadas de la versión nocturna
        leen como roca volcánica; de día tienen que leer como pasto."""
        r = random.Random(seed)
        d = ['M-40,%d' % H, 'L-40,%d' % y0]
        x = -40
        while x < W + 40:
            nx = x + seg * r.uniform(0.7, 1.3)
            ny = y0 + r.uniform(-amp, amp)
            d.append('Q%.0f,%.0f %.0f,%.0f'
                     % ((x + nx) / 2, ny - amp * 1.5, nx, ny))
            x = nx
        d.append('L%d,%d Z' % (W + 40, H))
        return "<path d='%s' fill='%s'/>" % (' '.join(d), fill)

    if day:
        # ── DÍA: sol, cielo despejado, sierra azulada y colinas verdes ──
        p.append("<circle cx='1214' cy='96' r='150' fill='url(#kSun)' opacity='0.75'/>")
        p.append("<circle cx='1214' cy='96' r='42' fill='#fff6cf'/>")
        p.append("<g fill='#ffffff' opacity='0.85'>")          # nubes
        for cxc, cyc, sc in ((250, 120, 1.0), (620, 76, 0.72), (930, 148, 0.55)):
            p.append("<g transform='translate(%d,%d) scale(%.2f)'>"
                     "<ellipse cx='0' cy='0' rx='74' ry='24'/>"
                     "<ellipse cx='-34' cy='8' rx='46' ry='18'/>"
                     "<ellipse cx='30' cy='6' rx='52' ry='20'/>"
                     "<ellipse cx='-4' cy='-16' rx='38' ry='22'/></g>"
                     % (cxc, cyc, sc))
        p.append("</g>")
        p.append("<g fill='#9fb6c9' opacity='0.55'>")          # sierra lejana
        p.append("<path d='M-20,392 L120,300 L232,368 L340,286 L470,378 L600,312 "
                 "L742,372 L880,296 L1010,376 L1150,318 L1290,380 L1460,320 "
                 "L1460,%d L-20,%d Z' fill='#9fb6c9'/>" % (H, H))
        p.append("</g>")
        p.append("<g fill='#ffffff' opacity='0.5'>")           # nieve en las cimas
        for px, py in ((120, 300), (340, 286), (880, 296), (1150, 318)):
            p.append("<path d='M%d,%d l-20,17 l10,-3 l8,6 l12,-8 l10,3 Z'/>"
                     % (px, py))
        p.append("</g>")
        p.append(hill(392, 16, 3, 'url(#kHillA)'))
        p.append(hill(428, 12, 5, 'url(#kHillB)'))
    else:
        # ── NOCHE: resplandor del horizonte, sierra y el VOLCÁN ──
        p.append("<rect x='0' y='236' width='%d' height='264' fill='url(#kSky)'/>" % W)

        # El volcán se dibuja ANTES de la sierra y con su propia falda: la
        # primera versión era un cono chico suelto en el aire y el dueño lo
        # cazó — «se entiende que es un volcán si lo rebuscas… está como
        # flotando». Lo que lo arregla no es agrandarlo, es DARLE ENTORNO:
        # la falda que se funde con el terreno y la sierra por delante, que le
        # come la base y lo deja plantado en el paisaje en vez de pegado encima.
        # ⚠️ Se PROBÓ un penacho de ceniza (bocanadas desenfocadas subiendo del
        # cráter) y el dueño lo rechazó — "sácale ese humo, no queda bien". NO
        # re-agregarlo: lo que hace legible al volcán es la falda + el corte de
        # la sierra, no el humo.
        vx, vtop, vbase, vhalf = 1244, 330, 452, 122
        p.append("<path d='M%d,%d C%d,%d %d,%d %d,%d C%d,%d %d,%d %d,%d "
                 "L%d,%d C%d,%d %d,%d %d,%d Z' fill='%s' opacity='0.5'/>"
                 % (vx - vhalf - 120, vbase, vx - vhalf - 40, vbase - 14,
                    vx - vhalf, vbase - 26, vx - vhalf + 30, vbase - 30,
                    vx - 60, vtop + 96, vx - 40, vtop + 40, vx - 22, vtop + 8,
                    vx + 22, vtop + 8, vx + 44, vtop + 44, vx + 78, vtop + 110,
                    vx + vhalf + 130, vbase, '#2a1018'))
        # el cono
        p.append("<path d='M%d,%d Q%d,%d %d,%d L%d,%d Q%d,%d %d,%d Z' fill='%s'/>"
                 % (vx - vhalf, vbase, vx - 96, vbase - 62, vx - 20, vtop,
                    vx + 15, vtop, vx + 74, vbase - 40, vx + vhalf, vbase,
                    '#170609'))
        # la ladera que mira al cráter, apenas encendida
        p.append("<path d='M%d,%d Q%d,%d %d,%d L%d,%d Z' fill='%s' opacity='0.13'/>"
                 % (vx + 15, vtop, vx + 74, vbase - 40, vx + vhalf, vbase,
                    vx + 20, vbase, LAVA))
        # boca + resplandor
        p.append("<ellipse cx='%d' cy='%d' rx='40' ry='30' fill='url(#kCrater)'/>"
                 % (vx, vtop - 10))
        p.append("<path d='M%d,%d Q%d,%d %d,%d Q%d,%d %d,%d Z' fill='%s'/>"
                 % (vx - 15, vtop, vx, vtop - 4, vx + 15, vtop,
                    vx, vtop + 5, vx - 15, vtop, LAVA))
        # PENACHO de ceniza: sube y se tuerce con el viento. Es la pieza que
        # más hace por la lectura, más que el tamaño del cono.
        # una colada corta por el flanco
        d = ("M%d,%d Q%d,%d %d,%d" % (vx + 9, vtop + 8, vx + 30, vtop + 42,
                                      vx + 26, vtop + 74))
        p.append("<path d='%s' fill='none' stroke='#c9330a' stroke-width='6' "
                 "stroke-linecap='round' opacity='0.30'/>" % d)
        p.append("<path d='%s' fill='none' stroke='%s' stroke-width='2' "
                 "stroke-linecap='round' opacity='0.9'/>" % (d, LAVA))
        # la sierra pasa POR DELANTE y le come el pie: sin esto el cono
        # termina en una línea recta suspendida sobre la nada
        far = jagged(rng, -20, 1460, 46, 428, 16, sharp=0.20)
        p.append(ridge(far, H, BASALT_FAR, '0.55'))

    # ── piezas del reino ──────────────────────────────────────────────────
    def merlons(x0, x1, y, mw=13, gap=11, h=11, fill=STONE):
        """Almenas: el rasgo que hace que un rectángulo se lea como MURALLA."""
        out, x = [], x0
        while x + mw <= x1:
            out.append("<rect x='%d' y='%d' width='%d' height='%d' fill='%s'/>"
                       % (x, y - h, mw, h + 3, fill))
            x += mw + gap
        return ''.join(out)

    def windows(x0, x1, y0, y1, cols, rows, w=5, h=8, seed=0):
        """Ventanas: de noche ENCENDIDAS (sin ellas la silueta es una roca
        cualquiera); de día, huecos oscuros — una ventana iluminada a mediodía
        se lee como un error de dibujo."""
        r = random.Random(seed)
        out = []
        for i in range(cols):
            for j in range(rows):
                if r.random() < (0.25 if day else 0.42):
                    continue
                x = x0 + (x1 - x0 - w) * (i / max(1, cols - 1.0))
                y = y0 + (y1 - y0 - h) * (j / max(1, rows - 1.0))
                out.append("<rect x='%.0f' y='%.0f' width='%d' height='%d' rx='2' "
                           "fill='%s' opacity='%.2f'/>"
                           % (x, y, w, h, WIN,
                              r.uniform(0.5, 0.8) if day else r.uniform(0.55, 0.95)))
        return ''.join(out)

    def tower(x, w, top, roof=44, flag=True, seed=0, body=STONE):
        """Torre cilíndrica con techo CÓNICO y gallardete — la silueta que
        dice 'castillo' de un vistazo."""
        out = ["<rect x='%d' y='%d' width='%d' height='%d' fill='%s'/>"
               % (x, top, w, H - top, body)]
        out.append(merlons(x - 3, x + w + 3, top + 4, 11, 9, 10, body))
        out.append("<rect x='%d' y='%d' width='%d' height='4' fill='%s'/>"
                   % (x - 4, top + 4, w + 8, STONE_L))
        out.append("<path d='M%d,%d L%d,%d L%d,%d Z' fill='%s'/>"
                   % (x - 6, top - 6, x + w / 2.0, top - 6 - roof, x + w + 6,
                      top - 6, ROOF))
        if flag:
            px = x + w / 2.0
            out.append("<path d='M%.0f,%d L%.0f,%d' stroke='%s' stroke-width='2'/>"
                       % (px, top - 6 - roof, px, top - 6 - roof - 26, STONE_L))
            out.append("<path d='M%.0f,%d L%.0f,%d L%.0f,%d Z' fill='%s'/>"
                       % (px, top - 6 - roof - 26, px + 26, top - 6 - roof - 19,
                          px, top - 6 - roof - 12, BANNER))
        out.append(windows(x + 7, x + w - 7, top + 30, H - 52, 2, 3,
                           6, 10, seed=seed))
        return ''.join(out)

    # ── el pueblo detrás de la muralla: tejados a dos aguas ──
    roofs = []
    x = -10
    while x < W:
        rw, rh = rng.randint(38, 76), rng.randint(30, 54)
        base = 470
        roofs.append("<path d='M%d,%d L%d,%d L%d,%d Z' fill='%s'/>"
                     % (x, base, x + rw / 2.0, base - rh, x + rw, base, STONE_D))
        roofs.append("<rect x='%d' y='%d' width='%d' height='%d' fill='%s'/>"
                     % (x, base - 2, rw, 30, STONE_D))
        if rng.random() < 0.55:
            roofs.append(windows(x + 9, x + rw - 9, base - rh * 0.45,
                                 base - 6, 2, 1, 5, 7, seed=int(x)))
        x += rw + rng.randint(4, 18)
    p.append(''.join(roofs))

    # ── la CATEDRAL y la TORRE DEL HOMENAJE, lo más alto del reino ──
    #    (asoman por encima del caserío; en pantallas anchas se ven enteras)
    kx, ktop = 372, 300
    p.append("<rect x='%d' y='%d' width='118' height='%d' fill='%s'/>"
             % (kx, ktop, H - ktop, STONE))
    p.append(merlons(kx - 5, kx + 123, ktop + 5, 15, 12, 13, STONE))
    p.append("<rect x='%d' y='%d' width='128' height='5' fill='%s'/>"
             % (kx - 5, ktop + 5, STONE_L))
    for tx in (kx - 12, kx + 106):                    # torretas de esquina
        p.append("<rect x='%d' y='%d' width='24' height='%d' fill='%s'/>"
                 % (tx, ktop - 24, H - ktop + 24, STONE))
        p.append("<path d='M%d,%d L%d,%d L%d,%d Z' fill='%s'/>"
                 % (tx - 5, ktop - 24, tx + 12, ktop - 70, tx + 29, ktop - 24, ROOF))
    p.append(windows(kx + 16, kx + 102, ktop + 34, 470, 3, 4, 7, 12, seed=11))

    cx2 = 806
    p.append("<rect x='%d' y='368' width='96' height='%d' fill='%s'/>"
             % (cx2, H - 368, STONE))
    p.append("<path d='M%d,368 L%d,332 L%d,368 Z' fill='%s'/>"
             % (cx2, cx2 + 48, cx2 + 96, ROOF))
    p.append("<rect x='%d' y='286' width='30' height='%d' fill='%s'/>"
             % (cx2 + 100, H - 286, STONE))
    p.append("<path d='M%d,286 L%d,214 L%d,286 Z' fill='%s'/>"   # aguja
             % (cx2 + 100, cx2 + 115, cx2 + 130, ROOF))
    p.append("<circle cx='%d' cy='%d' r='9' fill='%s' opacity='0.9'/>"
             % (cx2 + 48, 402, WIN))                  # rosetón
    p.append(windows(cx2 + 12, cx2 + 84, 424, 486, 3, 2, 6, 14, seed=12))

    # ── LA MURALLA: corre de borde a borde, con su cordón y sus almenas ──
    WALL = 470
    p.append("<rect x='0' y='%d' width='%d' height='%d' fill='%s'/>"
             % (WALL, W, H - WALL, STONE))
    p.append(merlons(0, W, WALL + 2, 15, 13, 14, STONE))
    p.append("<rect x='0' y='%d' width='%d' height='5' fill='%s'/>"
             % (WALL + 2, W, STONE_L))
    p.append("<g stroke='%s' stroke-width='1' opacity='0.5'>" % STONE_L)
    for j in range(3):                                  # hiladas de sillares
        y = WALL + 22 + j * 24
        p.append("<path d='M0,%d H%d'/>" % (y, W))
    x = 0
    while x < W:                                        # juntas verticales
        y0 = WALL + 22 + rng.randint(0, 2) * 24
        p.append("<path d='M%d,%d v24'/>" % (x, y0))
        x += rng.randint(26, 46)
    p.append("</g>")

    if not day:                       # faroles del adarve: cosa de la noche
        p.append("<g>")
        for tx in range(70, W, 168):
            p.append("<ellipse cx='%d' cy='%d' rx='16' ry='13' fill='%s' "
                     "opacity='0.16'/>" % (tx, WALL + 12, LAVA))
            p.append("<circle cx='%d' cy='%d' r='2.6' fill='%s' opacity='0.95'/>"
                     % (tx, WALL + 11, WIN))
        p.append("</g>")

    # ── la PUERTA: arco iluminado entre dos torres. Es lo que convierte la
    #    muralla en la entrada de un reino habitado. ──
    gx = 1006
    if not day:
        p.append("<ellipse cx='%d' cy='%d' rx='62' ry='46' fill='url(#kGate)'/>"
                 % (gx + 34, H - 6))
    p.append("<path d='M%d,%d L%d,%d A%d,%d 0 0 1 %d,%d L%d,%d Z' fill='%s'/>"
             % (gx + 8, H, gx + 8, 508, 26, 30, gx + 60, 508, gx + 60, H,
                '#4a3b28' if day else '#0b0407'))
    if not day:
        p.append("<path d='M%d,%d L%d,%d A%d,%d 0 0 1 %d,%d L%d,%d Z' fill='%s' "
                 "opacity='0.35'/>"
                 % (gx + 16, H, gx + 16, 512, 18, 22, gx + 52, 512, gx + 52, H, WIN))
    for tx, w, top, sd in ((-14, 62, 402, 1), (196, 54, 424, 2), (612, 58, 414, 3),
                           (gx - 62, 66, 396, 4), (gx + 62, 66, 396, 5),
                           (1330, 62, 408, 6)):
        p.append(tower(tx, w, top, seed=sd))

    if day:
        # ── DÍA: la colina en primer plano, el camino a la puerta y arboleda ──
        p.append(hill(524, 9, 9, 'url(#kHillC)'))
        p.append("<path d='M%d,%d C%d,%d %d,%d %d,%d L%d,%d C%d,%d %d,%d %d,%d Z' "
                 "fill='#c7ab7d' opacity='0.85'/>"
                 % (gx + 14, H, gx + 4, 548, 900, 552, 806, H,
                    980, H, 1030, 552, gx + 52, 548, gx + 52, H))
        p.append("<g>")
        for tx, ty, sc in ((96, 540, 1.15), (232, 548, 0.9), (416, 545, 1.0),
                           (640, 552, 0.8), (1188, 542, 1.1), (1348, 550, 0.95),
                           (760, 543, 1.05)):
            p.append("<g transform='translate(%d,%d) scale(%.2f)'>"
                     "<rect x='-3' y='-14' width='6' height='18' fill='#6b4a2a'/>"
                     "<circle cx='0' cy='-24' r='17' fill='#3f7038'/>"
                     "<circle cx='-11' cy='-16' r='12' fill='#4a8040'/>"
                     "<circle cx='11' cy='-17' r='12' fill='#356030'/></g>"
                     % (tx, ty, sc))
        p.append("</g>")
        p.append("<g fill='none' stroke='#5a6f80' stroke-width='2' "
                 "stroke-linecap='round' opacity='0.6'>")      # pájaros
        for bx, by, bs in ((470, 148, 1.0), (512, 128, 0.8), (556, 160, 0.7)):
            p.append("<path d='M%d,%d q%d,-%d %d,0 q%d,-%d %d,0'/>"
                     % (bx, by, int(7 * bs), int(6 * bs), int(14 * bs),
                        int(7 * bs), int(6 * bs), int(14 * bs)))
        p.append("</g>")
    else:
        # ── NOCHE: el suelo delante de la muralla, roca oscura y brasas ──
        p.append("<path d='M0,%d L0,548 %s L%d,548 L%d,%d Z' fill='%s'/>"
                 % (H, ' '.join('L%d,%d' % (x, 548 + rng.randint(-6, 5))
                                for x in range(0, W + 1, 90)), W, W, H, C['GROUND']))
        p.append("<g fill='%s'>" % EMBER)
        for _ in range(26):
            p.append("<circle cx='%d' cy='%d' r='%s' opacity='%s'/>"
                     % (rng.randint(0, W), rng.randint(180, 420),
                        round(rng.uniform(0.7, 1.6), 1),
                        round(rng.uniform(.2, .55), 2)))
        p.append("</g>")
    p.append("</svg>")
    return ''.join(p)


# ══ CAPA 2 · el TOMO (adorno de esquina) ══════════════════════════════════
def tome_svg():
    """Un tomo abierto: lomo de cuero, dos bloques de páginas y un sello de
    lava en la página derecha. Objeto ÚNICO y macizo — se reconoce de un
    vistazo, que es la regla del sitio para los adornos."""
    p = ["<svg xmlns='http://www.w3.org/2000/svg' width='260' height='168' "
         "viewBox='0 0 260 168'>"]
    p.append(
        "<defs>"
        "<linearGradient id='tPg' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='#e4cba0'/><stop offset='1' stop-color='#b99a6c'/>"
        "</linearGradient>"
        "<linearGradient id='tPgR' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='#efd9b2'/><stop offset='1' stop-color='#c6a878'/>"
        "</linearGradient>"
        "<radialGradient id='tSeal' cx='50%%' cy='45%%' r='60%%'>"
        "<stop offset='0' stop-color='#fff0cf'/>"
        "<stop offset='0.45' stop-color='%s'/>"
        "<stop offset='1' stop-color='#7a1c06'/></radialGradient>"
        "</defs>" % LAVA)
    # tapa de cuero (asoma por fuera de las páginas)
    p.append("<path d='M8,116 L128,92 L252,116 L252,132 L128,110 L8,132 Z' "
             "fill='#3d1410'/>")
    p.append("<path d='M8,116 L128,92 L252,116 L128,104 Z' fill='#5a2018'/>")
    # bloques de páginas
    p.append("<path d='M18,110 C56,84 96,80 126,92 L126,104 C96,92 56,96 18,120 Z' "
             "fill='url(#tPg)'/>")
    p.append("<path d='M242,110 C204,84 164,80 134,92 L134,104 C164,92 204,96 242,120 Z' "
             "fill='url(#tPgR)'/>")
    # hojas abiertas
    p.append("<path d='M18,110 C56,84 96,80 126,92 L126,40 C96,28 56,32 18,58 Z' "
             "fill='url(#tPg)'/>")
    p.append("<path d='M242,110 C204,84 164,80 134,92 L134,40 C164,28 204,32 242,58 Z' "
             "fill='url(#tPgR)'/>")
    # lomo
    p.append("<path d='M126,92 L130,96 L134,92 L134,40 L130,36 L126,40 Z' "
             "fill='#48180f'/>")
    # renglones (crónica escrita)
    rng = random.Random(7)
    p.append("<g stroke='#7a5a38' stroke-width='2' stroke-linecap='round' "
             "opacity='0.55'>")
    for i in range(7):
        y = 50 + i * 7
        p.append("<path d='M%d,%d L%d,%d'/>" % (34, y + 6, 34 + rng.randint(48, 76),
                                                y + 6 - 4))
    for i in range(4):
        y = 50 + i * 7
        p.append("<path d='M%d,%d L%d,%d'/>" % (150, y + 6 - 4,
                                                150 + rng.randint(44, 72), y + 6))
    p.append("</g>")
    # sello de lava en la página derecha
    wax = random.Random(3)
    seal = []
    for k in range(14):
        a_ = 2 * math.pi * k / 14.0
        rr = 15 * wax.uniform(0.88, 1.12)
        seal.append((196 + math.cos(a_) * rr, 84 + math.sin(a_) * rr))
    p.append("<path d='M%.1f,%.1f %s Z' fill='url(#tSeal)'/>"
             % (seal[0][0], seal[0][1],
                ' '.join('L%.1f,%.1f' % q for q in seal[1:])))
    p.append("<circle cx='196' cy='84' r='9.5' fill='none' stroke='#7a1c06' "
             "stroke-width='2' opacity='0.55'/>")
    p.append("<path d='M191,84 L201,84 M193,79.5 L199,79.5 M193,88.5 L199,88.5' "
             "stroke='#7a1c06' stroke-width='1.8' stroke-linecap='round' "
             "opacity='0.6'/>")
    # brasas saliendo del tomo
    p.append("<g fill='%s'>" % EMBER)
    for cx_, cy_, r_, op_ in ((208, 52, 2.0, .75), (220, 34, 1.5, .6),
                              (198, 30, 1.2, .5), (232, 16, 1.8, .45),
                              (212, 12, 1.1, .35)):
        p.append("<circle cx='%s' cy='%s' r='%s' opacity='%s'/>" % (cx_, cy_, r_, op_))
    p.append("</g>")
    p.append("</svg>")
    return ''.join(p)


# ══ el bloque CSS ═════════════════════════════════════════════════════════
def css_block():
    tome = datauri(tome_svg())
    return ("""
    /* ═══ Chronicles (temporada 1 · agosto 2026, premio de ruleta) — un REINO
       MEDIEVAL, con DOS looks (patrón Pole / Mission / Standard):

       🌙 dark  · el reino de noche recortado contra el resplandor del
                  horizonte: muralla almenada de borde a borde, puerta
                  iluminada, torres con techo cónico y estandartes, torre del
                  homenaje, aguja de catedral, ventanas y faroles encendidos;
                  a lo lejos, un volcán chico que conserva la lava de la placa
                  `chronicles`.
       ☀️ light · el MISMO reino a pleno día, pedido del dueño: sol, cielo azul
                  despejado con nubes, sierra nevada al fondo y colinas verdes
                  alrededor; piedra clara, tejas de terracota, arboleda y el
                  camino de tierra que sube a la puerta.

       Reglas que respeta: la tierra se ancla con `100% auto center bottom`
       (nunca `cover`, o el horizonte flota); iOS-safe (body transparente +
       ::before fixed); el logo va blanco sobre la noche y por defecto sobre el
       día, igual que Mission. NO es DARK_ALWAYS: al tener look propio para
       cada modo, el toggle claro/oscuro elige escena. */
    body.camo-chronicles { background: transparent !important; }
    body.camo-chronicles:not(.light) {
      --bg:#140609;--surface:rgba(255,255,255,0.06);--card:rgba(255,255,255,0.075);
      --border:rgba(255,186,146,0.16);--border2:rgba(255,186,146,0.28);
      --text:#f7e7dc;--muted:rgba(247,231,220,0.62);
      --accent:#ff5a1e;--accent-h:#e04510;--win:#43d18d;--loss:#e0495a;--be:#ff5a1e;
      color: var(--text);
    }
    body.camo-chronicles:not(.light)::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __TOME__ right 3% bottom 5% / 230px auto no-repeat,
        __NIGHT__ center bottom / 100% auto no-repeat,
        radial-gradient(ellipse 90% 26% at 50% 96%, rgba(255,90,30,0.16), transparent 72%),
        linear-gradient(#0d0308,#1c060c 54%,#3a0f10);
    }
    body.camo-chronicles:not(.light)::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background: radial-gradient(ellipse 96% 90% at 50% 42%, transparent 56%, rgba(8,2,4,0.52) 100%);
    }
    body.camo-chronicles:not(.light) .logo-img {
      content: url('/static/logo_t.png'); filter: invert(1); mix-blend-mode: normal;
    }
    /* ☀️ Día: paneles translúcidos para que la escena se vea a través, tinta
       marrón de tinta ferrogálica y acento rojo de estandarte. */
    body.camo-chronicles.light {
      --bg:#dfeaf6;--surface:rgba(255,253,247,0.60);--card:rgba(255,253,247,0.72);
      --border:rgba(80,60,30,0.20);--border2:rgba(80,60,30,0.30);
      --text:#3a2c17;--muted:rgba(58,44,23,0.62);
      --accent:#b23a2a;--accent-h:#94301f;--win:#2f8f5a;--loss:#c0392b;--be:#b23a2a;
      color: var(--text);
    }
    body.camo-chronicles.light::before {
      content:""; position:fixed; inset:0; z-index:-2; pointer-events:none;
      background:
        __TOME__ right 3% bottom 5% / 230px auto no-repeat,
        __DAY__ center bottom / 100% auto no-repeat,
        linear-gradient(#8fc4ee,#bfe0f6 46%,#e7f3fb);
    }
    body.camo-chronicles.light::after {
      content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
      background:
        radial-gradient(ellipse 70% 46% at 84% 6%, rgba(255,245,205,0.55), transparent 60%),
        radial-gradient(ellipse 96% 88% at 50% 44%, transparent 60%, rgba(40,60,30,0.16) 100%);
    }
"""
            .replace('__TOME__', tome)
            .replace('__NIGHT__', datauri(scene_svg('dark')))
            .replace('__DAY__', datauri(scene_svg('light'))))


ANCHOR = '    /* ═══ Blackflag (pirate)'


def main():
    html = open(INDEX, encoding='utf-8').read()
    if 'body.camo-chronicles' in html:
        # reemplazo idempotente: borra el bloque anterior y vuelve a insertarlo
        start = html.index('    /* ═══ Chronicles (temporada 1')
        end = html.index(ANCHOR, start)
        html = html[:start] + html[end:]
    if ANCHOR not in html:
        raise SystemExit('No encontré el ancla del bloque Blackflag.')
    block = css_block()
    # Jinja: `{#` abre un comentario. Ningún CSS insertado puede contenerlo.
    for bad in ('{#', '{%', '{{'):
        if bad in block:
            raise SystemExit('El bloque contiene %r — Jinja lo interpretaría.' % bad)
    html = html.replace(ANCHOR, block + '\n\n' + ANCHOR, 1)
    open(INDEX, 'w', encoding='utf-8').write(html)
    print('bloque insertado (%d chars)' % len(block))


if __name__ == '__main__':
    main()
