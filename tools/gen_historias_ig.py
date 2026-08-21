# -*- coding: utf-8 -*-
"""Historias de Instagram 1080×1920 — generador.

    python3 tools/gen_historias_ig.py            # PNG listos para subir
    python3 tools/gen_historias_ig.py --guias    # marca las zonas que tapa la app

Sale en `out/historias_ig/` (ignorado por git).

PARA QUÉ SON. Una historia NO es un post: dura 24 h, se ve una vez y se pasa.
Su trabajo aquí es retener a quien entra al perfil desde el reel publicitado y
ganarse el follow — no explicar el producto (para eso están los 12 posts del
feed y los carruseles que vienen después).

Son DOS, pensadas para verse seguidas:
  1. `entrada`  — el gancho. Un trade real que salió mal, dibujado.
  2. `no-somos` — el anti-pitch. Es el que gana el follow.

EN INGLÉS, y escrito en inglés — no traducido. "Stopped out", "it ran without
you", "no fine print" son cosas que un trader dice; sus equivalentes literales
del español no lo son.

DECISIONES QUE NO SON COSMÉTICAS
--------------------------------
· **El gráfico ES la historia.** La primera versión era tipografía sobre negro
  y no paraba ningún scroll. Lo más característico del mundo de Tradeable es un
  gráfico, así que el gráfico va de protagonista y el titular encima. El trade
  dibujado es el caso `I5` del banco del analizador: barrida de los mínimos
  iguales, displacement con FVG, entrada en el retroceso, **stop demasiado
  ajustado que el precio caza**, y después se va sin ti.
· **Las velas son CORRECTAS y hay un assert que lo comprueba** (mecha contiene
  cuerpo, mínimos iguales de verdad, la barrida cierra dentro del rango, y el
  FVG es el hueco real entre el máximo de la 1ª y el mínimo de la 3ª). Un
  diagrama bonito pero falso cuesta credibilidad ante gente que sabe leer — la
  misma regla que los posts del feed.
· **NO se dibuja objetivo ni R:R.** Con el stop tan ajustado como el del caso
  salía 10:1, que se lee como fantasía; y una cifra de beneficio en un anuncio
  es justo lo que el sitio no puede prometer. Se enseña lo que hizo el precio,
  y punto.
· **Se nombra SOLO el analizador.** De las seis herramientas cinco son de pago;
  prometer "todas las herramientas" y que al pinchar aparezca un muro de $50
  quema al visitante justo cuando se está pagando por traerlo. Además
  contradice el posicionamiento oficial, que dice que la herramienta principal
  ES el analizador.
· **No se dice "your first analysis is free".** La palabra *first* pone un
  contador a la vista y lo que se lee es el segundo, no el primero. La señal de
  que no hay barrera va abajo como `no card needed`, que es verdad literal: el
  registro pide usuario, correo y contraseña.
· **El dominio va ESCRITO además del sticker.** El sticker de enlace se pierde
  con facilidad y hay quien captura la pantalla en vez de pinchar;
  `tradeable.academy` es corto y se memoriza de una lectura.
· **Zonas muertas reservadas.** Instagram tapa ~250 px arriba (foto y nombre) y
  ~272 px abajo (barra de responder). Todo lo legible vive entre esas dos
  líneas; `--guias` las dibuja. Bajo el CTA se deja una banda LIBRE para que el
  sticker nativo del enlace caiga ahí sin pisar texto.
· **Un solo acento por pieza** (misma regla que los posts y los camos): azul =
  producto en la primera, dorado en el anti-pitch. Dorado y no blanco porque
  con el acento blanco el <em>NOT</em> del titular queda del mismo color que el
  resto y deja de señalar nada.
"""
from __future__ import print_function

import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_posts_ig import (AZUL, GRAFITO, ORO, asegura_fuentes,  # noqa: E402
                          caras, piezas_logo)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'out', 'historias_ig')
W, H = 1080, 1920
SEG_ARRIBA, SEG_ABAJO = 250, 272      # lo que tapa la interfaz de la app

VERDE, ROJO = '#2fa572', '#e0524d'

# ── el trade: caso I5 del banco del analizador ───────────────────────────
# (apertura, cierre, máximo, mínimo)
SERIE = [(100.2, 100.6, 100.9, 100.00), (100.6, 100.1, 100.8, 99.95),
         (100.1, 100.5, 100.7, 100.02), (100.5, 100.0, 100.6, 99.98),
         (100.0, 99.40, 100.1, 98.60), (99.40, 101.3, 101.5, 99.30),
         (101.3, 103.6, 103.8, 101.20), (103.6, 104.4, 104.6, 103.40),
         (104.4, 103.2, 104.5, 103.00), (103.2, 102.0, 103.3, 101.70),
         (102.0, 101.0, 102.1, 100.60), (101.0, 103.0, 103.2, 100.90),
         (103.0, 105.2, 105.4, 102.90), (105.2, 107.0, 107.3, 105.00),
         (107.0, 108.4, 108.8, 106.90)]
I_BARRIDA, I_ENTRADA, I_STOP = 4, 9, 10
ENTRADA, STOP = 102.0, 101.4


def comprueba_serie():
    """Lo que un trader vería mal de un vistazo, comprobado a mano."""
    for i, (o, c, h, l) in enumerate(SERIE):
        assert h >= max(o, c) and l <= min(o, c), 'vela %d: la mecha no contiene el cuerpo' % i
    lows = [SERIE[i][3] for i in range(4)]
    assert max(lows) - min(lows) < .12, 'los "mínimos iguales" no son iguales'
    assert SERIE[I_BARRIDA][3] < min(lows), 'la barrida no barre nada'
    assert SERIE[I_BARRIDA][1] > SERIE[I_BARRIDA][3] + .5, 'la barrida debe cerrar dentro'
    # FVG alcista: hueco entre el MÁXIMO de la 1ª y el MÍNIMO de la 3ª
    fvg = (SERIE[5][2], SERIE[7][3])
    assert fvg[1] > fvg[0], 'no hay hueco: eso no es un FVG'
    assert fvg[0] <= ENTRADA <= fvg[1], 'la entrada cae fuera del FVG'
    assert SERIE[I_STOP][3] < STOP < SERIE[I_ENTRADA][1] + .5, 'el stop no lo caza nadie'
    return fvg


def grafico():
    """El trade, en SVG. Coordenadas propias 0-1000 × 0-560."""
    fvg = comprueba_serie()
    AN, AL = 1000.0, 500.0
    PAD_D = 96.0                       # sitio para los rótulos de precio
    todos = [v for d in SERIE for v in d]
    lo, hi = min(todos), max(todos)
    m = (hi - lo) * .07
    lo, hi = lo - m, hi + m
    n = len(SERIE)
    paso = (AN - PAD_D) / n
    cw = paso * .52

    def Y(v):
        return AL - (v - lo) / (hi - lo) * AL

    def X(i):
        return paso * (i + .5)

    p = []
    # rejilla: tenue, sólo para que el espacio se lea como un gráfico
    for k in range(1, 6):
        y = AL * k / 6.0
        p.append('<line x1="0" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#ffffff" '
                 'stroke-opacity=".055" stroke-width="1"/>' % (y, AN, y))

    # el FVG, con borde punteado: una banda sin borde se lee como adorno y no
    # como hueco delimitado
    p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
             'fill-opacity=".13"/>'
             % (X(5) - cw, Y(fvg[1]), X(8) - X(5) + cw * 2, Y(fvg[0]) - Y(fvg[1]), AZUL))
    for v in fvg:
        p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="1.5" stroke-dasharray="7 6" stroke-opacity=".7"/>'
                 % (X(5) - cw, Y(v), X(8) + cw, Y(v), AZUL))
    p.append('<text x="%.1f" y="%.1f" fill="%s" font-size="15" font-weight="700" '
             'font-family="Mono,monospace" letter-spacing="1.6">FVG</text>'
             % (X(5) - cw + 8, Y(fvg[1]) + 24, AZUL))

    # la línea de los mínimos iguales: es lo que el precio va a ir a buscar
    yl = Y(sum(SERIE[i][3] for i in range(4)) / 4.0)
    p.append('<line x1="0" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8e96a8" '
             'stroke-width="1.4" stroke-dasharray="4 7"/>' % (yl, X(6), yl))

    # velas. Las posteriores al stop van atenuadas: son las que ya no son tuyas
    for i, (o, c, h, l) in enumerate(SERIE):
        cx = X(i)
        col = VERDE if c >= o else ROJO
        op = '.30' if i > I_STOP else '1'
        p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="3" opacity="%s"/>' % (cx, Y(h), cx, Y(l), col, op))
        y0, y1 = Y(max(o, c)), Y(min(o, c))
        p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                 'rx="2" opacity="%s"/>'
                 % (cx - cw / 2, y0, cw, max(3.0, y1 - y0), col, op))

    # el rótulo de la barrida, colgado de la mecha que baja
    p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#8e96a8" '
             'stroke-width="1.3"/>'
             % (X(I_BARRIDA), Y(SERIE[I_BARRIDA][3]) + 6,
                X(I_BARRIDA), Y(SERIE[I_BARRIDA][3]) + 30))
    p.append('<text x="%.1f" y="%.1f" fill="#aab2c4" font-size="15" '
             'font-weight="700" font-family="Mono,monospace" letter-spacing="1.4" '
             'text-anchor="middle">SWEEP</text>'
             % (X(I_BARRIDA), Y(SERIE[I_BARRIDA][3]) + 48))

    def nivel(v, color, etiqueta, x0, dy):
        """⚠️ `dy` no es un ajuste fino: entrada y stop distan 0,6 en precio, o
        sea menos que el alto de sus propias pastillas — sin separarlas se
        pisan. Cada una se aparta de su línea y un tirante la reconecta."""
        yv = Y(v)
        p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="2" stroke-dasharray="9 6"/>'
                 % (x0, yv, AN - PAD_D + 6, yv, color))
        p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="2"/>'
                 % (AN - PAD_D + 6, yv, AN - PAD_D + 6, yv + dy, color))
        p.append('<rect x="%.1f" y="%.1f" width="88" height="30" rx="7" fill="%s"/>'
                 % (AN - PAD_D + 6, yv + dy - 15, color))
        p.append('<text x="%.1f" y="%.1f" fill="#0b0d12" font-size="16" '
                 'font-weight="700" font-family="Mono,monospace" letter-spacing="1.2" '
                 'text-anchor="middle">%s</text>'
                 % (AN - PAD_D + 50, yv + dy + 6, etiqueta))

    nivel(ENTRADA, AZUL, 'ENTRY', X(I_ENTRADA) - cw, -22)
    nivel(STOP, ROJO, 'STOP', X(I_ENTRADA) - cw, 22)

    # la ✕ donde el stop se ejecuta: es el único punto que la historia cuenta
    xs, ys = X(I_STOP), Y(STOP)
    p.append('<circle cx="%.1f" cy="%.1f" r="30" fill="%s" fill-opacity=".14"/>'
             % (xs, ys, ROJO))
    p.append('<circle cx="%.1f" cy="%.1f" r="30" fill="none" stroke="%s" '
             'stroke-width="3"/>' % (xs, ys, ROJO))
    for dx, dy in ((-11, -11), (-11, 11)):
        p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="4.4" stroke-linecap="round"/>'
                 % (xs + dx, ys + dy, xs - dx, ys - dy, ROJO))

    # ⚠️ El tramo posterior NO lleva rótulo: el titular ya dice "without you" y
    #    repetirlo sobre las velas se lee como un pie de foto de más. Lo cuentan
    #    la atenuación y la ✕.
    return ('<svg viewBox="0 0 %.0f %.0f" style="width:100%%;height:auto;'
            'overflow:visible" xmlns="http://www.w3.org/2000/svg">%s</svg>'
            % (AN, AL, ''.join(p)))


# ── textos ───────────────────────────────────────────────────────────────
# Escritos en inglés, no traducidos: "stopped out", "it ran without you",
# "no fine print" y "the read" son lo que un trader dice de verdad.
T = {
    'e1': 'THE ANALYZER',
    't1': 'Stopped out.<br>Then it ran<br><em>without you.</em>',
    'v1': 'Was it manipulation — or was your stop in the wrong place?',
    'p1': ['Upload the chart', 'Say what you were after', 'Get the read'],
    'c1': 'Get your analysis right now',
    'n1': 'no card needed',

    'e2': 'NO FINE PRINT',
    't2': 'What we’re<br><em>not</em>',
    'p2': ['Signals', 'A “copy my trades” group', 'Profit screenshots'],
    'r2': 'A second opinion at 3 a.m.<br>that reads your chart<br>back to you.',
    'c2': 'Follow us',
    'n2': 'This week we break down every tool.',
}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;background:GRAFITO}
.lienzo{position:relative;width:1080px;height:1920px;overflow:hidden;
  background:GRAFITO;font-family:Inter,sans-serif;color:#eef0f5}
/* el mismo suelo que los posts del feed: si la historia no se reconoce como la
   misma casa, no suma marca */
.lienzo::before{content:'';position:absolute;inset:0;z-index:0;
  background:radial-gradient(58% 32% at 50% -2%, ACENTO26, transparent 70%)}
.lienzo::after{content:'';position:absolute;inset:0;z-index:0;opacity:.5;
  background-image:linear-gradient(rgba(255,255,255,.055) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.055) 1px,transparent 1px);
  background-size:60px 60px;
  -webkit-mask-image:radial-gradient(72% 46% at 50% 8%,#000,transparent 78%)}
.brillo{position:absolute;z-index:0;left:50%;bottom:-340px;width:1560px;height:800px;
  margin-left:-780px;pointer-events:none;
  background:radial-gradient(closest-side, ACENTO1c, transparent 72%)}

.marco{position:relative;z-index:3;height:100%;
  padding:SEGARRIBApx 84px SEGABAJOpx;display:flex;flex-direction:column}
.etq{display:flex;align-items:center;gap:16px;
  font-family:Mono,monospace;font-size:25px;font-weight:700;letter-spacing:.24em;
  color:ACENTO;text-transform:uppercase}
.etq::after{content:'';flex:1;height:1px;background:ACENTO;opacity:.30}
h1{margin-top:34px;font-size:88px;font-weight:900;line-height:1.02;
  letter-spacing:-.038em}
h1 em{font-style:normal;color:ACENTO}
.cuerpo{flex:1;display:flex;flex-direction:column;justify-content:center}

/* — el gráfico, protagonista — */
/* el gráfico sube y se mete BAJO el titular: la tendencia deja libre
   justo la esquina superior izquierda, que es donde cae el texto */
.grafico{margin:-116px 0 4px;position:relative;z-index:-1}
.pregunta{font-size:38px;line-height:1.36;color:#aab2c4;max-width:850px}
/* los pasos en UNA línea con separadores: en una historia que ya lleva un
   gráfico, tres filas numeradas roban el sitio que necesita el titular */
.pasos{display:flex;flex-wrap:wrap;align-items:center;gap:14px 18px;margin-top:26px}
.pasos span{font-size:28px;font-weight:700;color:#eef0f5}
.pasos b{width:7px;height:7px;border-radius:50%;background:ACENTO;display:block}

/* — el anti-pitch: tachado de verdad, no una cruz al lado — */
.no{display:flex;flex-direction:column;gap:34px;margin-top:56px}
.no div{position:relative;display:inline-block;align-self:flex-start;
  font-size:56px;font-weight:800;color:#6f7787}
.no div::after{content:'';position:absolute;left:-22px;right:-22px;top:52%;
  height:5px;border-radius:3px;background:ACENTO;transform:rotate(ROTdeg);
  transform-origin:left center}
.si{margin-top:64px;padding-left:30px;border-left:5px solid ACENTO;
  font-size:52px;font-weight:800;line-height:1.24;letter-spacing:-.02em}

/* — el pie de llamada — */
.cta{position:relative;z-index:3;margin-top:38px}
.cta .t{font-size:56px;font-weight:900;letter-spacing:-.02em;line-height:1.12}
/* banda LIBRE: aquí cae el sticker nativo del enlace, no se pinta nada */
.hueco{height:HUECOpx}
.cta .dom{font-family:Mono,monospace;font-size:38px;font-weight:700;color:ACENTO;
  letter-spacing:.02em}
.cta .nota{margin-top:14px;font-family:Mono,monospace;font-size:26px;color:#7c8496;
  letter-spacing:.06em}
/* el anti-pitch no lleva enlace: su razón para seguir va PEGADA al CTA */
.cta .razon{margin-top:16px;font-size:36px;line-height:1.36;color:#aab2c4}
.pie{position:relative;z-index:3;margin-top:40px;display:flex;align-items:center;
  justify-content:space-between}
.pie img{height:42px;opacity:.9}
.pie .ar{font-family:Mono,monospace;font-size:24px;color:#6d7484}

/* — guías: sólo en la versión de revisión — */
.g{position:absolute;left:0;right:0;z-index:9;pointer-events:none;
  outline:3px dashed rgba(255,120,120,.8)}
.g.arr{top:0;height:SEGARRIBApx}
.g.aba{bottom:0;height:SEGABAJOpx}
"""


def historia_entrada():
    pasos = '<b></b>'.join('<span>%s</span>' % s for s in T['p1'])
    cuerpo = ("<div class='etq'>%s</div>"
              "<div class='cuerpo'><h1>%s</h1>"
              "<div class='grafico'>%s</div>"
              "<p class='pregunta'>%s</p>"
              "<div class='pasos'>%s</div></div>"
              "<div class='cta'><div class='t'>%s</div>"
              "<div class='hueco'></div>"
              "<div class='dom'>tradeable.academy</div>"
              "<div class='nota'>%s</div></div>"
              % (T['e1'], T['t1'], grafico(), T['v1'], pasos, T['c1'], T['n1']))
    return 'historia-1-entrada', AZUL, cuerpo, 150


def historia_no_somos():
    """Tachado LITERAL en vez de una cruz al lado: se entiende sin leer, que es
    todo lo que se pide de una historia. Cada línea con su propio ángulo — tres
    tachones idénticos se leen como una tabla, no como una mano."""
    angulos = (-1.0, -.5, -1.2)
    lista = ''.join("<div style='--r:%.1fdeg'>%s</div>" % (a, p)
                    for a, p in zip(angulos, T['p2']))
    cuerpo = ("<div class='etq'>%s</div>"
              "<div class='cuerpo'><h1>%s</h1>"
              "<div class='no'>%s</div>"
              "<div class='si'>%s</div></div>"
              "<div class='cta'><div class='t'>%s</div>"
              "<div class='razon'>%s</div></div>"
              % (T['e2'], T['t2'], lista, T['r2'], T['c2'], T['n2']))
    return 'historia-2-no-somos', ORO, cuerpo, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--guias', action='store_true',
                    help='dibuja las bandas que tapa la interfaz de Instagram')
    args = ap.parse_args()

    asegura_fuentes()
    os.makedirs(SALIDA, exist_ok=True)
    fuentes = caras()
    logo_b64, _letra, azul, _im = piezas_logo()
    assert '#%02x%02x%02x' % azul == AZUL, \
        'el azul del logo cambió (%s)' % ('#%02x%02x%02x' % azul)

    def pagina(acento, cuerpo, hueco, guia):
        css = (CSS.replace('ACENTO', acento).replace('GRAFITO', GRAFITO)
                  .replace('SEGARRIBA', str(SEG_ARRIBA))
                  .replace('SEGABAJO', str(SEG_ABAJO))
                  .replace('HUECO', str(hueco))
                  .replace('rotate(ROTdeg)', 'rotate(var(--r,-1.2deg))'))
        g = "<div class='g arr'></div><div class='g aba'></div>" if guia else ''
        return ("<!doctype html><meta charset='utf-8'><style>%s%s</style>"
                "<div class='lienzo'><div class='brillo'></div>%s"
                "<div class='marco'>%s<div class='pie'>"
                "<img src='data:image/png;base64,%s'>"
                "<span class='ar'>@tradeableacademy</span></div></div></div>"
                % (fuentes, css, g, cuerpo, logo_b64))

    plan = []
    for hacer in (historia_entrada, historia_no_somos):
        nombre, acento, cuerpo, hueco = hacer()
        io.open(os.path.join(SALIDA, nombre + '.html'), 'w',
                encoding='utf-8').write(pagina(acento, cuerpo, hueco, False))
        plan.append(nombre)
        if args.guias:
            io.open(os.path.join(SALIDA, nombre + '.guia.html'), 'w',
                    encoding='utf-8').write(pagina(acento, cuerpo, hueco, True))
            plan.append(nombre + '.guia')
    io.open(os.path.join(SALIDA, 'plan.json'), 'w').write(json.dumps(plan))
    rasteriza(plan)
    print('%d historias en %s' % (len(plan), os.path.relpath(SALIDA, RAIZ)))


def rasteriza(plan):
    """A PNG. ⚠️ `device_scale_factor=1`: el lienzo YA mide 1080 px, que es lo
    que Instagram quiere; a densidad 2 saldrían 2160 y la red los recomprime."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('⚠️ sin playwright: quedan los HTML, ábrelos en el navegador')
        return
    import glob
    exe = ((glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')
            or glob.glob('/opt/pw-browsers/chromium')) or [None])[0]
    with sync_playwright() as p:
        nav = p.chromium.launch(args=['--no-sandbox'],
                                **({'executable_path': exe} if exe else {}))
        for nombre in plan:
            pg = nav.new_page(viewport={'width': W, 'height': H},
                              device_scale_factor=1)
            # todo va embebido: se corta la red para no depender de ningún CDN
            pg.route('**/*', lambda r: (r.abort()
                                        if r.request.url.startswith('http')
                                        else r.continue_()))
            pg.goto('file://' + os.path.join(SALIDA, nombre + '.html'),
                    wait_until='domcontentloaded')
            pg.wait_for_timeout(450)
            pg.screenshot(path=os.path.join(SALIDA, nombre + '.png'))
            pg.close()
        nav.close()


if __name__ == '__main__':
    main()
