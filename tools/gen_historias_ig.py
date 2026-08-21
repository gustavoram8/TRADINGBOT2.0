# -*- coding: utf-8 -*-
"""Historias de Instagram 1080×1920 — generador.

    python3 tools/gen_historias_ig.py            # los dos idiomas, PNG incluido
    python3 tools/gen_historias_ig.py --guias    # marca las zonas que tapa la app

Sale en `out/historias_ig/` (ignorado por git).

PARA QUÉ SON. Una historia NO es un post: dura 24 h, se ve una vez y se pasa.
Su trabajo aquí es retener a quien entra al perfil desde el reel publicitado y
ganarse el follow — no explicar el producto (para eso están los 12 posts del
feed y los carruseles que vienen después).

Son DOS, pensadas para verse seguidas:
  1. `analizador` — la puerta. Nombra UNA herramienta, no seis.
  2. `no-somos`   — el anti-pitch. Es el que gana el follow.

DECISIONES QUE NO SON COSMÉTICAS
--------------------------------
· **Se nombra SOLO el analizador.** De las seis herramientas, cinco son de pago;
  prometer "las herramientas perfectas" y que al pinchar aparezca un muro de $50
  quema al visitante en el segundo exacto en que se está pagando por traerlo. Y
  además contradice el posicionamiento oficial, que dice que Tradeable es un
  ecosistema cuya **herramienta principal es el analizador**. La historia honesta
  y la comercial son la misma.
· **No se dice "tu primer análisis es gratis".** La palabra *primer* pone un
  contador a la vista y lo que se lee es el segundo, no el primero. El CTA es
  "obtén tu análisis ahora mismo" y la señal de que no hay barrera va abajo, en
  gris, como `sin tarjeta` — que es verdad literal: el registro pide usuario,
  correo y contraseña, nada más.
· **El dominio va ESCRITO además del sticker.** El sticker de enlace se pierde
  con facilidad y hay quien captura la pantalla en vez de pinchar;
  `tradeable.academy` es corto y se memoriza de una lectura.
· **Zonas muertas reservadas.** Instagram tapa ~250 px arriba (foto y nombre) y
  ~250 px abajo (barra de responder). Todo lo legible vive entre esas dos
  líneas; `--guias` las dibuja. Debajo del CTA se deja una banda LIBRE de 210 px
  para que el sticker nativo del enlace caiga ahí sin pisar texto.
· **Un solo acento por pieza** (misma regla que los posts y los camos): azul =
  producto en la primera, blanco = disciplina en el anti-pitch.
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

TEXTOS = {
    'es': {
        'e1': 'EL ANALIZADOR',
        't1': '¿Tienes dudas<br>sobre un trade<br>que <em>no te salió</em>?',
        'p1': ['Sube la captura',
               'Escribe qué buscabas',
               'Te lo desglosa'],
        'v1': ('Para que <b>comprendas</b>, <b>corrijas</b> y '
               '<b>optimices</b> tu trading.'),
        'c1': 'Obtén tu análisis ahora mismo',
        'n1': 'sin tarjeta',

        'e2': 'SIN LETRA PEQUEÑA',
        't2': 'Lo que <em>NO</em><br>somos',
        'p2': ['Señales',
               '«Copia mis trades»',
               'Capturas de ganancias'],
        'v2': 'Somos la segunda opinión que<br>no tenías a las 3 AM.',
        'c2': 'Síguenos',
        'n2': 'Esta semana desglosamos<br>cada herramienta.',
    },
    'en': {
        'e1': 'THE ANALYZER',
        't1': 'Not sure why<br>that trade<br><em>didn’t work</em>?',
        'p1': ['Upload the screenshot',
               'Tell it what you were looking for',
               'It breaks the trade down'],
        'v1': ('So you <b>understand</b>, <b>fix</b> and <b>refine</b> '
               'your trading.'),
        'c1': 'Get your analysis right now',
        'n1': 'no card needed',

        'e2': 'NO FINE PRINT',
        't2': 'What we’re<br><em>NOT</em>',
        'p2': ['Signals',
               '“Copy my trades”',
               'Profit screenshots'],
        'v2': 'We’re the second opinion<br>you didn’t have at 3 AM.',
        'c2': 'Follow us',
        'n2': 'This week we break down<br>every tool.',
    },
}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;background:GRAFITO}
.lienzo{position:relative;width:1080px;height:1920px;overflow:hidden;
  background:GRAFITO;font-family:Inter,sans-serif;color:#eef0f5}
/* el mismo suelo que los posts del feed: si la historia no se reconoce como la
   misma casa, no suma marca */
.lienzo::before{content:'';position:absolute;inset:0;z-index:0;
  background:radial-gradient(58% 34% at 50% -2%, ACENTO26, transparent 70%)}
.lienzo::after{content:'';position:absolute;inset:0;z-index:0;opacity:.5;
  background-image:linear-gradient(rgba(255,255,255,.055) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.055) 1px,transparent 1px);
  background-size:60px 60px;
  -webkit-mask-image:radial-gradient(70% 44% at 50% 6%,#000,transparent 78%)}
.brillo{position:absolute;z-index:0;left:50%;bottom:-320px;width:1500px;height:760px;
  margin-left:-750px;pointer-events:none;
  background:radial-gradient(closest-side, ACENTO1c, transparent 72%)}

.marco{position:relative;z-index:3;height:100%;
  padding:SEGARRIBApx 84px SEGABAJOpx;display:flex;flex-direction:column}
.etq{font-family:Mono,monospace;font-size:25px;font-weight:700;letter-spacing:.24em;
  color:ACENTO;text-transform:uppercase}
h1{margin-top:40px;font-size:92px;font-weight:900;line-height:1.03;
  letter-spacing:-.035em}
h1 em{font-style:normal;color:ACENTO}
.cuerpo{flex:1;display:flex;flex-direction:column;justify-content:center}

/* — los pasos numerados — */
.pasos{display:flex;flex-direction:column;gap:26px;margin-top:56px}
.pasos div{display:flex;align-items:center;gap:26px;font-size:44px;font-weight:700}
.pasos i{font-style:normal;font-family:Mono,monospace;font-size:28px;color:ACENTO;
  min-width:62px}

/* — la lista del anti-pitch: la cruz es del color del acento y el texto queda
     en gris, porque lo que se afirma no es la cruz, es la ausencia — */
.no{display:flex;flex-direction:column;gap:30px;margin-top:60px}
.no div{display:flex;align-items:center;gap:28px;font-size:48px;font-weight:800;
  color:#c8cedb}
.no span{display:grid;place-items:center;width:60px;height:60px;flex:0 0 60px;
  border-radius:50%;border:3px solid ACENTO66;color:ACENTO;font-size:34px;
  font-weight:900;line-height:1}

.verbos{margin-top:58px;font-size:40px;line-height:1.42;color:#aab2c4}
.verbos b{color:#eef0f5;font-weight:800}

/* — el pie de llamada — */
.cta{position:relative;z-index:3;margin-top:40px}
.cta .t{font-size:56px;font-weight:900;letter-spacing:-.02em;line-height:1.12}
.cta .t em{font-style:normal;color:ACENTO}
/* banda LIBRE: aquí cae el sticker nativo del enlace, no se pinta nada */
.hueco{height:210px}
.cta .dom{font-family:Mono,monospace;font-size:38px;font-weight:700;color:ACENTO;
  letter-spacing:.02em}
.cta .nota{margin-top:14px;font-family:Mono,monospace;font-size:26px;color:#7c8496;
  letter-spacing:.06em}
/* el anti-pitch no lleva enlace: su razón para seguir va PEGADA al CTA, no
   detrás del hueco del sticker */
.cta .razon{margin-top:18px;font-size:38px;line-height:1.36;color:#aab2c4}
.pie{position:relative;z-index:3;margin-top:44px;display:flex;align-items:center;
  justify-content:space-between}
.pie img{height:42px;opacity:.9}
.pie .ar{font-family:Mono,monospace;font-size:24px;color:#6d7484}

/* — guías: sólo en la versión de revisión — */
.g{position:absolute;left:0;right:0;z-index:9;pointer-events:none;
  outline:3px dashed rgba(255,120,120,.8)}
.g.arr{top:0;height:SEGARRIBApx}
.g.aba{bottom:0;height:SEGABAJOpx}
"""


def historia_analizador(T):
    pasos = ''.join('<div><i>%02d</i>%s</div>' % (i + 1, p)
                    for i, p in enumerate(T['p1']))
    cuerpo = ("<div class='etq'>%s</div>"
              "<div class='cuerpo'><h1>%s</h1>"
              "<div class='pasos'>%s</div>"
              "<p class='verbos'>%s</p></div>"
              "<div class='cta'><div class='t'>%s</div>"
              "<div class='hueco'></div>"
              "<div class='dom'>tradeable.academy</div>"
              "<div class='nota'>%s</div></div>"
              % (T['e1'], T['t1'], pasos, T['v1'], T['c1'], T['n1']))
    return 'historia-1-analizador', AZUL, cuerpo


def historia_no_somos(T):
    """⚠️ Acento DORADO, no blanco. Con blanco el <em>NO</em> del titular queda
    del mismo color que el resto y deja de destacar — el acento tiene que poder
    señalar algo. El dorado además hace que las cruces se lean como exclusiones
    deliberadas y no como errores (el rojo del sitio significa pérdida)."""
    lista = ''.join("<div><span>✕</span>%s</div>" % p for p in T['p2'])
    cuerpo = ("<div class='etq'>%s</div>"
              "<div class='cuerpo'><h1>%s</h1>"
              "<div class='no'>%s</div>"
              "<p class='verbos'>%s</p></div>"
              "<div class='cta'><div class='t'>%s</div>"
              "<div class='razon'>%s</div></div>"
              % (T['e2'], T['t2'], lista, T['v2'], T['c2'], T['n2']))
    return 'historia-2-no-somos', ORO, cuerpo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--guias', action='store_true',
                    help='dibuja las bandas que tapa la interfaz de Instagram')
    ap.add_argument('--idioma', default='ambos',
                    choices=['ambos'] + sorted(TEXTOS))
    args = ap.parse_args()

    asegura_fuentes()
    os.makedirs(SALIDA, exist_ok=True)
    fuentes = caras()
    logo_b64, _letra, azul, _im = piezas_logo()
    assert '#%02x%02x%02x' % azul == AZUL, \
        'el azul del logo cambió (%s)' % ('#%02x%02x%02x' % azul)

    def pagina(acento, cuerpo, guia):
        css = (CSS.replace('ACENTO', acento).replace('GRAFITO', GRAFITO)
                  .replace('SEGARRIBA', str(SEG_ARRIBA))
                  .replace('SEGABAJO', str(SEG_ABAJO)))
        g = "<div class='g arr'></div><div class='g aba'></div>" if guia else ''
        return ("<!doctype html><meta charset='utf-8'><style>%s%s</style>"
                "<div class='lienzo'><div class='brillo'></div>%s"
                "<div class='marco'>%s<div class='pie'>"
                "<img src='data:image/png;base64,%s'>"
                "<span class='ar'>@tradeableacademy</span></div></div></div>"
                % (fuentes, css, g, cuerpo, logo_b64))

    idiomas = sorted(TEXTOS) if args.idioma == 'ambos' else [args.idioma]
    plan = []
    for idi in idiomas:
        T = TEXTOS[idi]
        for hacer in (historia_analizador, historia_no_somos):
            nombre, acento, cuerpo = hacer(T)
            nombre = '%s-%s' % (nombre, idi)
            io.open(os.path.join(SALIDA, nombre + '.html'), 'w',
                    encoding='utf-8').write(pagina(acento, cuerpo, False))
            plan.append(nombre)
            if args.guias:
                io.open(os.path.join(SALIDA, nombre + '.guia.html'), 'w',
                        encoding='utf-8').write(pagina(acento, cuerpo, True))
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
