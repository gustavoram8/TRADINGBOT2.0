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
    # ⚠️ El lienzo del SVG es MÁS ALTO que la zona de precios: los 52 de abajo
    #    son para el rótulo de la barrida, que cuelga de la mecha. Sin esa
    #    reserva el rótulo cae fuera del viewBox y se come el texto siguiente.
    AN, AL, ALTO = 1000.0, 384.0, 336.0
    # ⚠️ PAD_D es GRANDE porque el gráfico va A SANGRE: con el margen justo,
    #    las pastillas de ENTRY/STOP quedaban pegadas al borde de la pantalla.
    PAD_D = 164.0
    todos = [v for d in SERIE for v in d]
    lo, hi = min(todos), max(todos)
    m = (hi - lo) * .07
    lo, hi = lo - m, hi + m
    n = len(SERIE)
    paso = (AN - PAD_D) / n
    cw = paso * .52

    def Y(v):
        return ALTO - (v - lo) / (hi - lo) * ALTO

    def X(i):
        return paso * (i + .5)

    p = []
    # rejilla: sólo horizontales y muy tenues. Es un eje de precios, no la
    # cuadrícula decorativa que llevaba la versión anterior.
    for k in range(1, 6):
        y = ALTO * k / 6.0
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
    return ('<svg viewBox="0 0 %.0f %.0f" preserveAspectRatio="xMidYMid meet" '
            'style="width:100%%;height:auto" '
            'xmlns="http://www.w3.org/2000/svg">%s</svg>' % (AN, AL, ''.join(p)))


# ── textos ───────────────────────────────────────────────────────────────
# Escritos en inglés, no traducidos: "stopped out", "it ran without you",
# "no fine print" y "the read" son lo que un trader dice de verdad.
T = {
    'e1': 'THE ANALYZER',
    't1': 'STOPPED<br>OUT.',
    's1': 'Then it ran without you.',
    # 🔴 El caso dibujado es UNO. Sin esta linea la pieza se lee como "el
    #    analizador sirve para stops cazados", que es una fraccion de lo que
    #    hace — y una promesa mas pequena que el producto.
    'v1': 'That’s one mistake. It reads the whole trade:',
    'p1': 'ENTRY · STOP · TARGET · TIMING · RISK · THE SETUP ITSELF',
    'c1': 'GET YOUR ANALYSIS RIGHT NOW',
    'c1b': 'upload the chart · say what you were after · get the read',
    'n1': 'tradeable.academy · no card needed',

    'e2': 'NO FINE PRINT',
    't2': 'WHAT<br>WE’RE<br><em>NOT</em>',
    'p2': ['Signals', 'A “copy my trades” group', 'Profit screenshots'],
    'r2': ('At 3 a.m., when there’s<br>no mentor to ask —<br>'
           'or there is, and no answer comes.'),
    'r2b': ('An educational ecosystem, built so you find '
            'and fix your own mistakes faster.'),
    # ⚠️ El sello va DENTRO del bloque, pegado al «3 a.m.»: suelto arriba se
    #    lee como un dato más y no corrige la lectura de que el analizador
    #    solo funciona de madrugada, que es justo lo que hay que evitar.
    'sello2': 'OPEN 24/7',
    'c2': 'FOLLOW US',
    'n2': 'This week we break down every tool.',

    # ── 3 · EL RELOJ DEL MERCADO. La versión anterior de esta tercera
    #    historia iba de tamaño de posición y el dueño la descartó entera:
    #    *"no me gusta la de los lotes, brokers, pérdidas"*. Ésta cambia de
    #    tema Y de estructura — un riel vertical de 24 h en vez de bandas
    #    apiladas — y se apoya en una de las POCAS piezas gratis del sitio,
    #    así que la promesa se puede cumplir sin muro de pago.
    'e4': 'MARKET TIMING',
    't4': 'NOT ALL<br>HOURS ARE<br>THE SAME.',
    's4': 'Where the volume actually shows up.',
    'spec4': 'ALL TIMES NEW YORK (ET)',
    'nota4': 'The brighter hour inside London and NY is the Silver Bullet.',
    # 🔴 Sin promesa: un reloj no hace que un setup funcione, y decir lo
    #    contrario sería justo lo que el sitio no puede prometer.
    'v4': ('A clock won’t make a bad setup work. It will tell you why '
           'the good one went nowhere.'),
    'c4': 'THE LIVE CLOCK',
    'c4b': 'kill zones · session countdown · economic calendar',
    'n4': 'tradeable.academy · free · no card needed',
}


CSS = """
/* ═══ CARTEL, NO "DARK TECH" ═══════════════════════════════════════════
   🔴 La versión anterior tenía los cuatro tics del arte generado por
   defecto: resplandor radial arriba, rejilla tenue de 60 px, esquinas
   redondeadas y todo a la izquierda con un gris apagado debajo. El dueño lo
   cazó a la primera ("se ve muy Claude") y tenía razón.
   Se va TODO eso y se adopta el lenguaje que sí funcionó en las portadas de
   destacadas: FORMA MACIZA, color plano, cero adorno fino. En cartel eso es:
   bandas sólidas a sangre, tipografía colosal con interlineado cerrado,
   filetes gruesos y ningún degradado. El único gradiente que sobrevive es un
   velo casi negro al pie, y sólo porque el gráfico sangra por ahí. */
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;background:GRAFITO}
.lienzo{position:relative;width:1080px;height:1920px;overflow:hidden;
  background:GRAFITO;font-family:Inter,sans-serif;color:#f4f6fa}
.marco{position:relative;z-index:3;height:100%;display:flex;flex-direction:column;
  padding-top:SEGARRIBApx;padding-bottom:SEGABAJOpx}
.aire{padding-left:76px;padding-right:76px}

/* — la banda de cabecera: sólida y A SANGRE, negro sobre el acento — */
.banda{background:ACENTO;color:#07080b;display:flex;align-items:center;
  justify-content:space-between;padding:16px 76px;
  font-family:Mono,monospace;font-size:25px;font-weight:700;letter-spacing:.22em}
.banda .b2{letter-spacing:.10em;opacity:.78}

/* — tipografía colosal. Inter a 900 con el tracking muy cerrado y el
     interlineado por debajo de 1 no se parece a Inter por defecto — */
h1{font-size:136px;font-weight:900;line-height:.86;letter-spacing:-.055em;
  margin-top:46px}
h1.tres{font-size:106px}
h1 em{font-style:normal;color:ACENTO}
.filete{height:9px;background:ACENTO;margin:30px 0 20px;width:210px}
.sub{font-size:50px;font-weight:800;letter-spacing:-.025em;line-height:1.1;
  color:ACENTO}

/* — el gráfico sangra de borde a borde: dentro de una caja se lee como una
     ilustración, a sangre se lee como el propio mercado — */
.grafico{margin:26px 0 0;position:relative}
.grafico svg{display:block;width:100%}

.pregunta{margin-top:26px;font-size:34px;line-height:1.3;font-weight:600;
  color:#f4f6fa;max-width:900px}
/* la lista de lo que el analizador lee. ⚠️ Calibrada para UNA sola línea: al
   partirse en dos la pieza crece y el remate se mete en la barra de responder
   de Instagram. Si se añade un término, baja el cuerpo. */
.lee{margin-top:18px;font-family:Mono,monospace;font-size:21px;font-weight:700;
  letter-spacing:.09em;color:ACENTO;white-space:nowrap}

/* — el anti-pitch: tachado literal, grueso, y que SE SALGA del lienzo — */
.no{display:flex;flex-direction:column;gap:26px;margin-top:44px}
.no div{position:relative;display:inline-block;align-self:flex-start;
  font-size:54px;font-weight:800;letter-spacing:-.02em;color:#767e8f}
.no div::after{content:'';position:absolute;left:-26px;right:-62px;top:52%;
  height:9px;background:ACENTO;transform:rotate(ROTdeg);transform-origin:left center}

/* — el bloque invertido: la única cosa que sí somos, en negativo sobre el
     acento. Es el remate del cartel — */
.bloque{margin-top:38px;background:ACENTO;color:#07080b;padding:30px 38px 34px;
  font-size:44px;font-weight:800;line-height:1.18;letter-spacing:-.025em}
/* sello invertido: negro macizo sobre el oro. Mismo recurso que el bloque
   sobre el fondo, un peldaño más adentro */
/* ⚠️ `display:table`, NO `inline-block`: al ir el sello delante del texto del
   bloque, inline-block se mete EN LA MISMA LÍNEA que la frase. table encoge al
   contenido igual pero ocupa su propio renglón. */
.bloque .sello{display:table;margin-bottom:20px;background:#07080b;
  color:ACENTO;font-family:Mono,monospace;font-size:23px;font-weight:700;
  letter-spacing:.20em;padding:9px 16px}
/* la promesa de fondo va DENTRO del bloque y en cuerpo pequeño: fuera pedía su
   propio margen y hacía crecer la pieza más de lo que cabe */
.bloque .eco{margin-top:20px;padding-top:18px;border-top:3px solid rgba(7,8,11,.30);
  font-size:27px;font-weight:700;line-height:1.34;letter-spacing:0}

.cuerpo{flex:1;display:flex;flex-direction:column;justify-content:center}
.abajo{margin-top:auto}

/* — remate: barra sólida a sangre. En la 1 lleva el CTA y el dominio; bajo
     ella queda la banda LIBRE donde cae el sticker del enlace — */
.remate{background:ACENTO;color:#07080b;padding:22px 76px 26px}
.remate .t{font-size:52px;font-weight:900;letter-spacing:-.02em;line-height:1.06}
.remate .p{margin-top:12px;font-family:Mono,monospace;font-size:23px;
  font-weight:700;letter-spacing:.05em;opacity:.90}
.remate .n{margin-top:5px;font-family:Mono,monospace;font-size:23px;
  font-weight:700;letter-spacing:.05em;opacity:.72}
.hueco{height:HUECOpx}
/* remate en claro para el anti-pitch, que ya gastó el acento en el bloque */
.remate.plano{background:transparent;color:#f4f6fa;padding-bottom:0}
.remate.plano .t{color:#f4f6fa}
.remate.plano .n{margin-top:10px;opacity:1;color:#9aa2b4;
  font-family:Inter,sans-serif;font-size:33px;font-weight:600;letter-spacing:0}

.pie{display:flex;align-items:center;justify-content:space-between;
  padding:0 76px;margin:24px 0 14px}
.pie img{height:40px;opacity:.85}
.pie .ar{font-family:Mono,monospace;font-size:23px;color:#6d7484}

/* — guías: sólo en la versión de revisión — */
.g{position:absolute;left:0;right:0;z-index:9;pointer-events:none;
  outline:3px dashed rgba(255,120,120,.8)}
.g.arr{top:0;height:SEGARRIBApx}
.g.aba{bottom:0;height:SEGABAJOpx}
"""


def historia_entrada():
    cuerpo = ("<div class='banda'><span>%s</span>"
              "<span class='b2'>TRADEABLE.ACADEMY</span></div>"
              "<div class='aire'><h1>%s</h1><div class='filete'></div>"
              "<div class='sub'>%s</div></div>"
              "<div class='grafico'>%s</div>"
              "<div class='aire'><p class='pregunta'>%s</p>"
              "<div class='lee'>%s</div></div>"
              "<div class='abajo'><div class='remate'><div class='t'>%s</div>"
              "<div class='p'>%s</div><div class='n'>%s</div></div>"
              "<div class='hueco'></div></div>"
              % (T['e1'], T['t1'], T['s1'], grafico(), T['v1'], T['p1'],
                 T['c1'], T['c1b'], T['n1']))
    return 'historia-1-entrada', AZUL, cuerpo, 118, False


def historia_no_somos():
    """Tachado LITERAL en vez de una cruz al lado: se entiende sin leer, que es
    todo lo que se le pide a una historia. Cada línea con su propio ángulo —
    tres tachones idénticos se leen como una tabla, no como una mano."""
    angulos = (-1.0, -.5, -1.2)
    lista = ''.join("<div style='--r:%.1fdeg'>%s</div>" % (a, x)
                    for a, x in zip(angulos, T['p2']))
    cuerpo = ("<div class='banda'><span>%s</span>"
              "<span class='b2'>TRADEABLE.ACADEMY</span></div>"
              "<div class='aire cuerpo'><h1 class='tres'>%s</h1>"
              "<div class='no'>%s</div>"
              "<div class='bloque'><div class='sello'>%s</div>%s"
              "<div class='eco'>%s</div></div></div>"
              "<div class='abajo'><div class='remate plano'><div class='t'>%s</div>"
              "<div class='n'>%s</div></div></div>"
              % (T['e2'], T['t2'], lista, T['sello2'], T['r2'], T['r2b'],
                 T['c2'], T['n2']))
    return 'historia-2-no-somos', ORO, cuerpo, 0, True


def riel():
    """El día completo en vertical: 24 h de riel y, encima, las ventanas.

    La estructura ES el argumento — casi todo el riel está APAGADO, y eso se
    ve antes de leer nada. Los horarios salen de la tabla real de la app
    (`index.html`, sección MARKET TIMING), no de memoria.

    ⚠️ LUNCH va en gris y no en el acento a propósito: no es una kill zone,
    es la hora muerta. Pintarla igual que las demás diría lo contrario de lo
    que enseña la pieza.
    """
    # ⚠️ PAD no es margen decorativo: sin él la etiqueta de las 00:00 se sale
    #    por arriba del viewBox y la de la izquierda se corta (se veía "0:00"
    #    en vez de "00:00", porque `text-anchor=end` la empuja fuera del 0).
    AN, AL, PAD = 928.0, 592.0, 16.0
    ALTO = AL - PAD * 2
    X0, ANCHO = 104.0, 56.0         # el riel
    XT = 182.0                      # donde empiezan las etiquetas
    # el riel apagado tiene que DISTINGUIRSE del fondo: si no, no se ve que
    # casi todo el día está vacío, que es el argumento entero de la pieza
    APAGADO = '#242938'
    GRIS = '#6d7484'

    def Y(h):
        return PAD + h / 24.0 * ALTO

    p = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
         % (X0, PAD, ANCHO, ALTO, APAGADO)]

    # las horas de referencia, a la izquierda
    for h in (0, 6, 12, 18, 24):
        y = Y(h)
        p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#394054" '
                 'stroke-width="2"/>' % (X0 - 14, y, X0, y))
        p.append('<text x="%.1f" y="%.1f" fill="%s" font-size="21" '
                 'font-weight="700" font-family="Mono,monospace" '
                 'text-anchor="end">%02d:00</text>' % (X0 - 26, y + 7, GRIS, h))

    # (inicio, fin, nombre, horario, color, silver bullet)
    ZONAS = [(2.0, 5.0, 'LONDON', '2:00 – 5:00', AZUL, (3.0, 4.0)),
             (9.5, 11.0, 'NY AM', '9:30 – 11:00', AZUL, (10.0, 11.0)),
             (12.0, 13.0, 'LUNCH', '12:00 – 13:00', GRIS, None),
             (13.5, 16.0, 'NY PM', '13:30 – 16:00', AZUL, (14.0, 15.0)),
             (20.0, 24.0, 'ASIA', '20:00 – 00:00', AZUL, None)]

    for h0, h1, nombre, horario, color, sb in ZONAS:
        y0, y1 = Y(h0), Y(h1)
        p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                 % (X0, y0, ANCHO, y1 - y0, color))
        if sb:
            s0, s1 = Y(sb[0]), Y(sb[1])
            p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                     'fill="#ffffff" fill-opacity=".72"/>'
                     % (X0 + 12, s0, ANCHO - 24, s1 - s0))
        cy = (y0 + y1) / 2.0
        p.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                 'stroke-width="2" stroke-opacity=".5"/>'
                 % (X0 + ANCHO, cy, XT - 16, cy, color))
        tinta = '#f4f6fa' if color != GRIS else GRIS
        p.append('<text x="%.1f" y="%.1f" fill="%s" font-size="31" '
                 'font-weight="800" font-family="Inter,sans-serif" '
                 'letter-spacing="-.01em">%s</text>' % (XT, cy + 1, tinta, nombre))
        p.append('<text x="%.1f" y="%.1f" fill="%s" font-size="22" '
                 'font-weight="700" font-family="Mono,monospace" '
                 'letter-spacing=".06em">%s</text>'
                 % (XT + 185, cy + 1, GRIS, horario))

    return ('<svg viewBox="0 0 %.0f %.0f" preserveAspectRatio="xMidYMid meet" '
            'style="width:100%%;height:auto" '
            'xmlns="http://www.w3.org/2000/svg">%s</svg>' % (AN, AL, ''.join(p)))


def historia_reloj():
    """La tercera: el reloj del mercado. Estructura NUEVA — el riel vertical
    manda y el texto lo acompaña, al revés que las otras dos."""
    # 🔴 Overrides LOCALES: esta pieza lleva el riel, que es alto. Medida en
    #    el navegador con los cuerpos compartidos, el remate caía dentro de
    #    los 272 px de la barra de responder. Van aquí para no mover ni un
    #    píxel de las historias 1 y 2, que ya están aprobadas.
    ajuste = ("<style>h1.tres{font-size:80px;margin-top:22px}"
              ".filete{margin:18px 0 12px}.sub{font-size:42px}"
              ".spec{margin-top:10px;font-family:Mono,monospace;font-size:20px;"
              "font-weight:700;letter-spacing:.06em;color:#6d7484}"
              ".grafico{margin-top:22px}"
              ".nota{margin-top:16px;font-family:Mono,monospace;font-size:19px;"
              "font-weight:700;letter-spacing:.04em;color:#6d7484}"
              ".pregunta{margin-top:22px;margin-bottom:24px;font-size:32px;"
              "line-height:1.28}</style>")
    cuerpo = (ajuste
              + "<div class='banda'><span>%s</span>"
              "<span class='b2'>TRADEABLE.ACADEMY</span></div>"
              "<div class='aire'><h1 class='tres'>%s</h1>"
              "<div class='filete'></div><div class='sub'>%s</div>"
              "<div class='spec'>%s</div></div>"
              "<div class='aire grafico'>%s</div>"
              "<div class='aire'><div class='nota'>%s</div>"
              "<p class='pregunta'>%s</p></div>"
              "<div class='abajo'><div class='remate'><div class='t'>%s</div>"
              "<div class='p'>%s</div><div class='n'>%s</div></div>"
              "<div class='hueco'></div></div>"
              % (T['e4'], T['t4'], T['s4'], T['spec4'], riel(), T['nota4'],
                 T['v4'], T['c4'], T['c4b'], T['n4']))
    return 'historia-3-reloj', AZUL, cuerpo, 96, False


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

    def pagina(acento, cuerpo, hueco, pie, guia):
        css = (CSS.replace('ACENTO', acento).replace('GRAFITO', GRAFITO)
                  .replace('SEGARRIBA', str(SEG_ARRIBA))
                  .replace('SEGABAJO', str(SEG_ABAJO))
                  .replace('HUECO', str(hueco))
                  .replace('rotate(ROTdeg)', 'rotate(var(--r,-1.2deg))'))
        g = "<div class='g arr'></div><div class='g aba'></div>" if guia else ''
        # el logotipo sólo va al pie donde queda sitio; en la 1 ya vive en la
        # banda de cabecera y repetirlo sería ruido
        marca = ("<div class='pie'><img src='data:image/png;base64,%s'>"
                 "<span class='ar'>@tradeableacademy</span></div>" % logo_b64) if pie else ''
        return ("<!doctype html><meta charset='utf-8'><style>%s%s</style>"
                "<div class='lienzo'>%s<div class='marco'>%s%s</div></div>"
                % (fuentes, css, g, cuerpo, marca))

    plan = []
    for hacer in (historia_entrada, historia_no_somos, historia_reloj):
        nombre, acento, cuerpo, hueco, pie = hacer()
        io.open(os.path.join(SALIDA, nombre + '.html'), 'w',
                encoding='utf-8').write(pagina(acento, cuerpo, hueco, pie, False))
        plan.append(nombre)
        if args.guias:
            io.open(os.path.join(SALIDA, nombre + '.guia.html'), 'w',
                    encoding='utf-8').write(pagina(acento, cuerpo, hueco, pie, True))
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
