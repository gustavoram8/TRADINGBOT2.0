# -*- coding: utf-8 -*-
"""Artes de Instagram/TikTok de Tradeable Academy — generador.

Se corre desde la raíz del repo:

    python3 tools/gen_posts_ig.py            # todo
    python3 tools/gen_posts_ig.py --guias     # además, con la zona segura marcada

Sale en `out/posts_ig/` (ignorado por git): 9 posts 1080×1350, 5 portadas de
historias destacadas 1080×1080 y el avatar 1000×1000.

Por qué un generador y no 14 diseños sueltos: es el mismo criterio de las placas
del foro y los cursores. Se cambia el texto de la lista POSTS y el arte se
rehace con la misma rejilla, el mismo resplandor y las mismas tipografías.
Diseñar cada pieza a mano es exactamente como se desincroniza una marca.

DECISIONES QUE NO SON COSMÉTICAS
--------------------------------
· **1080×1350 (4:5)** ocupa más pantalla en el feed que un cuadrado. ⚠️ PERO la
  cuadrícula del perfil RECORTA al cuadrado central: todo lo que deba entenderse
  ahí vive dentro de esos 1080×1080 del medio. `--guias` lo dibuja para
  verificarlo. Es el error que deja títulos cortados en media red.
· **Un solo acento por pieza.** Azul = producto, dorado = conocimiento, blanco =
  disciplina. Nunca dos compitiendo — la misma lección de los camos.
· **Números en JetBrains Mono.** En la tipografía de texto un número se lee como
  adorno; en monoespaciada se lee como dato.
· **Las velas se dibujan de verdad**, a partir de OHLC. El Order Block señala la
  última vela BAJISTA antes del desplazamiento (no cualquier vela roja) y el
  Fair Value Gap marca el hueco entre el máximo de la 1ª y el mínimo de la 3ª.
  Es contenido para gente que sabe leer un gráfico: un diagrama decorativo pero
  falso cuesta credibilidad.
· **Las portadas de destacadas van SIN TEXTO.** Instagram escribe el título
  debajo del círculo; la palabra dentro sobra y a ~64px no se lee.
· **El avatar es la "a", no el logotipo.** El logotipo es 6:1 y la foto de perfil
  es un círculo: a 32px (comentarios) la palabra entera es una mancha.
· Tipografías **embebidas en base64**: el navegador no debe depender de que un
  CDN responda para que un arte salga bien.
"""
import argparse
import base64
import io
import json
import os
import subprocess
import sys
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_SRC = os.path.join(RAIZ, 'scalpel', 'static', 'logo_t.png')
FUENTES_DIR = os.path.join(RAIZ, 'tools', '.fuentes')   # ignorado por git
SALIDA = os.path.join(RAIZ, 'out', 'posts_ig')

AZUL = '#004feb'          # medido del propio logotipo, no elegido a ojo
ORO = '#c9a227'
BLANCO = '#ffffff'
GRAFITO = '#0d0f14'

# Ambas familias son SIL Open Font License. Se bajan a una carpeta ignorada en
# vez de commitear 2 MB de binarios que no son del producto.
FUENTES = [
    ('Inter', 'Inter:wght@400;600;700;800;900'),
    ('JetBrainsMono', 'JetBrains+Mono:wght@400;700'),
]


# ── tipografías ──────────────────────────────────────────────────────────
def asegura_fuentes():
    os.makedirs(FUENTES_DIR, exist_ok=True)
    faltan = [f for f in FUENTES
              if not any(x.startswith(f[0] + '-') for x in os.listdir(FUENTES_DIR))]
    if not faltan:
        return
    import re
    for nombre, spec in faltan:
        css = subprocess.run(
            ['curl', '-s', '-A', 'Mozilla/5.0',
             'https://fonts.googleapis.com/css2?family=%s&display=swap' % spec],
            capture_output=True, text=True, timeout=90).stdout
        pares = re.findall(r'font-weight:\s*(\d+);.*?url\((https://[^)]+\.ttf)\)',
                           css, re.S)
        if not pares:
            sys.exit('No se pudieron bajar las tipografías (%s). Sin red, copia '
                     'los .ttf de Inter y JetBrains Mono en %s' % (nombre, FUENTES_DIR))
        for peso, url in pares:
            destino = os.path.join(FUENTES_DIR, '%s-%s.ttf' % (nombre, peso))
            subprocess.run(['curl', '-s', '-o', destino, url], timeout=90)
    print('tipografías en %s' % FUENTES_DIR)


def b64(ruta):
    return base64.b64encode(io.open(ruta, 'rb').read()).decode()


def caras():
    out = []
    for archivo in sorted(os.listdir(FUENTES_DIR)):
        if not archivo.endswith('.ttf'):
            continue
        familia, peso = archivo[:-4].rsplit('-', 1)
        familia = 'Mono' if familia == 'JetBrainsMono' else familia
        out.append("@font-face{font-family:'%s';font-weight:%s;font-style:normal;"
                   "src:url(data:font/ttf;base64,%s) format('truetype')}"
                   % (familia, peso, b64(os.path.join(FUENTES_DIR, archivo))))
    return ''.join(out)


# ── piezas del logotipo ──────────────────────────────────────────────────
def piezas_logo():
    """Devuelve (logotipo blanco b64, "a" blanca b64, azul de marca).

    ⚠️ El azul se toma del color MÁS REPETIDO entre los píxeles opacos, no del
    primero que aparece: el primero cae en el borde suavizado de la letra y es
    una mezcla con el fondo (daba #84a9e8 en vez de #004feb).
    """
    from PIL import Image
    im = Image.open(LOGO_SRC).convert('RGBA')
    im = im.crop(im.getchannel('A').getbbox())      # fuera el aire transparente
    W, H = im.size
    px = im.load()

    def azulp(p):
        r, g, b, a = p
        return a > 120 and b > 90 and b - r > 45 and b - g > 35

    pts = [(x, y) for y in range(H) for x in range(W) if azulp(px[x, y])]
    azul = Counter(px[x, y][:3] for x, y in pts
                   if px[x, y][3] == 255).most_common(1)[0][0]
    assert azul[2] - azul[0] > 100, 'ese no es el azul de relleno'

    blanco = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    q = blanco.load()
    for y in range(H):
        for x in range(W):
            a = px[x, y][3]
            if a:
                q[x, y] = (255, 255, 255, a)

    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    letra = Image.new('RGBA', (x1 - x0 + 1, y1 - y0 + 1), (0, 0, 0, 0))
    lp = letra.load()
    for x, y in pts:
        lp[x - x0, y - y0] = (255, 255, 255, px[x, y][3])

    os.makedirs(SALIDA, exist_ok=True)
    p1 = os.path.join(SALIDA, '_logo_blanco.png')
    p2 = os.path.join(SALIDA, '_a_blanca.png')
    blanco.save(p1)
    letra.save(p2)
    return b64(p1), b64(p2), azul, letra


# ── velas ────────────────────────────────────────────────────────────────
def velas(datos, alto=100, destacar=None, zona=None, acento=ORO):
    """datos: [(apertura, cierre, máximo, mínimo)]. destacar: índice a enmarcar.
    zona: (precio_bajo, precio_alto) de la franja sombreada."""
    n = len(datos)
    ancho = n * 34
    todos = [v for d in datos for v in d]
    lo, hi = min(todos), max(todos)
    pad = (hi - lo) * .14
    lo, hi = lo - pad, hi + pad

    def Y(v):
        return alto - (v - lo) / (hi - lo) * alto

    paso, piezas = ancho / n, []
    cw = paso * .52
    if zona:
        y0, y1 = Y(zona[1]), Y(zona[0])
        piezas.append('<rect x="0" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                      'opacity=".18"/>' % (y0, ancho, y1 - y0, acento))
    for i, (ap, ci, mx, mn) in enumerate(datos):
        cx = paso * (i + .5)
        col = '#3fb27f' if ci >= ap else '#d8544f'
        piezas.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                      'stroke-width="2.4"/>' % (cx, Y(mx), cx, Y(mn), col))
        y0, y1 = Y(max(ap, ci)), Y(min(ap, ci))
        h = max(2.5, y1 - y0)
        piezas.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                      'rx="1.5"/>' % (cx - cw / 2, y0, cw, h, col))
        if destacar == i:
            piezas.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                          'fill="none" stroke="%s" stroke-width="3" rx="4"/>'
                          % (cx - cw / 2 - 7, y0 - 7, cw + 14, h + 14, acento))
    return ('<svg viewBox="0 0 %.0f %.0f" style="width:100%%;height:auto" '
            'xmlns="http://www.w3.org/2000/svg">%s</svg>'
            % (ancho, alto, ''.join(piezas)))


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:HEIGHTpx;background:GRAFITO}
.lienzo{position:relative;width:1080px;height:HEIGHTpx;overflow:hidden;
  background:GRAFITO;font-family:Inter,sans-serif;color:#eef0f5}
.lienzo::before{content:'';position:absolute;inset:0;
  background:radial-gradient(62% 46% at 50% -6%, ACENTO22, transparent 70%)}
.lienzo::after{content:'';position:absolute;inset:0;opacity:.5;
  background-image:linear-gradient(rgba(255,255,255,.055) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.055) 1px,transparent 1px);
  background-size:60px 60px;
  -webkit-mask-image:radial-gradient(72% 56% at 50% 4%,#000,transparent 76%)}
.marco{position:relative;z-index:2;height:100%;padding:96px 88px 84px;
  display:flex;flex-direction:column}
.etq{font-family:Mono,monospace;font-size:23px;font-weight:700;letter-spacing:.22em;
  color:ACENTO;text-transform:uppercase;margin-bottom:34px}
h1{font-size:96px;font-weight:900;line-height:1.02;letter-spacing:-.035em}
h1 em{font-style:normal;color:ACENTO}
.sub{margin-top:32px;font-size:37px;line-height:1.42;color:#aab2c4;max-width:820px}
.cuerpo{flex:1;display:flex;flex-direction:column;justify-content:center}
.pie{position:relative;z-index:2;display:flex;align-items:center;justify-content:space-between}
.pie img{height:44px;opacity:.92}
.pie .ar{font-family:Mono,monospace;font-size:24px;color:#6d7484;letter-spacing:.04em}
.segura{position:absolute;left:0;right:0;top:SEGTOPpx;height:1080px;z-index:5;
  outline:3px dashed rgba(255,120,120,.85);pointer-events:none}
.lista{display:flex;flex-direction:column;gap:22px;margin-top:16px}
.lista div{display:flex;align-items:center;gap:22px;font-size:40px;font-weight:700}
.lista i{font-style:normal;font-family:Mono,monospace;font-size:26px;color:ACENTO;min-width:56px}
.graf{margin:44px 0 10px;padding:36px 40px;border:1px solid rgba(255,255,255,.12);
  border-radius:22px;background:rgba(255,255,255,.03)}
.nota{margin-top:26px;font-size:31px;color:#9aa2b4;line-height:1.4}
"""

DEST_CSS = """
.dest{position:relative;width:1080px;height:1080px;background:GRAFITO;overflow:hidden;
  display:grid;place-items:center}
.dest::before{content:'';position:absolute;inset:0;
  background:radial-gradient(72% 62% at 50% 50%, ACENTO1f, transparent 72%)}
.dest .g{position:relative;z-index:2;width:420px;height:420px}
.dest .g svg{width:100%;height:100%}
.dest .m{position:relative;z-index:2;width:300px}
"""


def glifos(A):
    return {
        'velas': ("<svg viewBox='0 0 100 100' fill='none'>"
                  "<g stroke='%s' stroke-width='7' stroke-linecap='round'>"
                  "<line x1='22' y1='30' x2='22' y2='72'/><line x1='50' y1='18' x2='50' y2='80'/>"
                  "<line x1='78' y1='34' x2='78' y2='66'/></g><g fill='%s'>"
                  "<rect x='14' y='40' width='16' height='22' rx='3'/>"
                  "<rect x='42' y='30' width='16' height='38' rx='3'/>"
                  "<rect x='70' y='44' width='16' height='14' rx='3'/></g></svg>") % (A, A),
        'nodos': ("<svg viewBox='0 0 100 100' fill='none'>"
                  "<g stroke='%s' stroke-width='5' opacity='.75'>"
                  "<line x1='50' y1='50' x2='22' y2='24'/><line x1='50' y1='50' x2='80' y2='28'/>"
                  "<line x1='50' y1='50' x2='26' y2='78'/><line x1='50' y1='50' x2='76' y2='76'/></g>"
                  "<g fill='%s'><circle cx='50' cy='50' r='13'/><circle cx='22' cy='24' r='8'/>"
                  "<circle cx='80' cy='28' r='8'/><circle cx='26' cy='78' r='8'/>"
                  "<circle cx='76' cy='76' r='8'/></g></svg>") % (A, A),
        'medalla': ("<svg viewBox='0 0 100 100' fill='none'>"
                    "<circle cx='50' cy='58' r='26' fill='%s'/>"
                    "<path d='M32 12h14l6 20H38z' fill='%s' opacity='.75'/>"
                    "<path d='M68 12H54l-6 20h14z' fill='%s' opacity='.75'/>"
                    "<path d='M50 46l4.6 9.4 10.4 1.5-7.5 7.3 1.8 10.3L50 69.6 40.7 74.5"
                    "l1.8-10.3-7.5-7.3 10.4-1.5z' fill='#0d0f14'/></svg>") % (A, A, A),
        'flecha': ("<svg viewBox='0 0 100 100' fill='none'>"
                   "<g stroke='%s' stroke-width='9' stroke-linecap='round' "
                   "stroke-linejoin='round'><line x1='20' y1='68' x2='74' y2='28'/>"
                   "<polyline points='48,26 78,25 77,55'/></g></svg>") % A,
    }


def bloque(etq, titulo, sub='', extra=''):
    return ("<div class='etq'>%s</div><div class='cuerpo'><h1>%s</h1>%s%s</div>"
            % (etq, titulo, ("<p class='sub'>%s</p>" % sub) if sub else '', extra))


def construye_posts():
    P = []
    P.append(('01-manifiesto', AZUL, bloque(
        'Tradeable Academy', 'Tu gráfico ya te dijo<br>qué hiciste mal.',
        'Nadie te lo tradujo.')))
    P.append(('02-problema', BLANCO, bloque(
        'El problema', 'Cientos de capturas.<br><em>Ningún método.</em>',
        'Guardar tus trades no es revisarlos. Una carpeta llena de gráficos no '
        'te dice qué repetiste mal.')))
    P.append(('03-que-hace', AZUL, bloque(
        'Cómo funciona', 'No detecta patrones.<br>Aplica <em>tu</em> metodología.',
        'Subes tu gráfico, eliges tu enfoque, y recibes una corrección escrita '
        'como te la daría un profesor.')))
    P.append(('04-order-block', ORO, bloque(
        'Concepto', 'Order Block', '',
        "<div class='graf'>%s</div><p class='nota'>La última vela bajista antes "
        "de un movimiento alcista con desplazamiento. No es cualquier vela roja: "
        "es la que quedó <b>antes</b> de que el precio saliera disparado.</p>"
        % velas([(50, 52, 53, 49), (52, 51, 53, 50), (51, 48, 52, 47),
                 (48, 58, 60, 47), (58, 66, 68, 57), (66, 64, 69, 62),
                 (64, 71, 73, 63)], destacar=2))))
    P.append(('05-fvg', ORO, bloque(
        'Concepto', 'Fair Value Gap', '',
        "<div class='graf'>%s</div><p class='nota'>Tres velas. El máximo de la "
        "primera queda <b>por debajo</b> del mínimo de la tercera: ese hueco es "
        "precio entregado demasiado rápido, y el mercado suele volver a "
        "visitarlo.</p>"
        % velas([(50, 51, 52, 49), (51, 53, 54, 50), (53, 62, 63, 56),
                 (62, 70, 71, 61), (70, 68, 72, 66)], zona=(54, 61)))))
    P.append(('06-disciplina', BLANCO, bloque(
        'Disciplina', 'La mayoría de tus<br>errores no son<br>de análisis.',
        'Son de ejecución. Entraste antes, moviste el stop, doblaste la '
        'posición. Y eso sí se puede medir.')))
    P.append(('07-metodologias', AZUL, bloque(
        'Enfoques', 'Siete formas de leer<br>el mismo gráfico.', '',
        "<div class='lista'><div><i>01</i>ICT</div>"
        "<div><i>02</i>Smart Money Concepts</div><div><i>03</i>Wyckoff</div>"
        "<div><i>04</i>Price Action</div><div><i>05</i>Patrones y armónicos</div>"
        "<div><i>06</i>Elliott</div><div><i>07</i>Análisis técnico</div></div>"
        "<p class='nota'>Eliges la tuya. La corrección llega en ese idioma.</p>")))
    P.append(('08-rangos', ORO, bloque(
        'La academia', 'De Paper Trader<br>a Market Maker.',
        'Ocho rangos. Se suben estudiando, resolviendo y revisando — no '
        'acertando operaciones.',
        "<div class='lista' style='margin-top:34px'><div><i>R1</i>Paper Trader</div>"
        "<div><i>R4</i>Liquidity Hunter</div><div><i>R8</i>Market Maker</div></div>")))
    P.append(('09-detras', AZUL, bloque(
        'Detrás', 'Estamos<br>construyendo<br>algo.',
        'Un sitio donde revisar tus gráficos deje de ser una carpeta de '
        'capturas. Te vamos a ir enseñando cada pieza.')))
    return P


DESTACADAS = [('h1-que-es', AZUL, 'marca'), ('h2-metodos', AZUL, 'velas'),
              ('h3-conceptos', ORO, 'nodos'), ('h4-academia', ORO, 'medalla'),
              ('h5-empezar', BLANCO, 'flecha')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--guias', action='store_true',
                    help='dibuja la zona segura de la cuadrícula del perfil')
    args = ap.parse_args()

    asegura_fuentes()
    os.makedirs(SALIDA, exist_ok=True)
    fuentes = caras()
    logo_b64, letra_b64, azul, letra_img = piezas_logo()
    assert '#%02x%02x%02x' % azul == AZUL, \
        'el azul del logo cambió (%s): actualiza la constante' % ('#%02x%02x%02x' % azul)

    def pagina(acento, cuerpo, alto=1350, guia=False):
        css = (CSS.replace('ACENTO', acento).replace('GRAFITO', GRAFITO)
                  .replace('HEIGHT', str(alto))
                  .replace('SEGTOP', str((alto - 1080) // 2)))
        seg = '<div class="segura"></div>' if guia else ''
        return ("<!doctype html><meta charset='utf-8'><style>%s%s</style>"
                "<div class='lienzo'>%s<div class='marco'>%s<div class='pie'>"
                "<img src='data:image/png;base64,%s'>"
                "<span class='ar'>@tradeableacademy</span></div></div></div>"
                % (fuentes, css, seg, cuerpo, logo_b64))

    def pagina_dest(acento, clave):
        css = (fuentes + DEST_CSS.replace('ACENTO', acento).replace('GRAFITO', GRAFITO)
               + 'html,body{margin:0;width:1080px;height:1080px;background:%s}' % GRAFITO)
        cuerpo = ("<img class='m' src='data:image/png;base64,%s'>" % letra_b64
                  if clave == 'marca' else
                  "<div class='g'>%s</div>" % glifos(acento)[clave])
        return ("<!doctype html><meta charset='utf-8'><style>%s</style>"
                "<div class='dest'>%s</div>" % (css, cuerpo))

    plan = []
    for nombre, acento, cuerpo in construye_posts():
        io.open(os.path.join(SALIDA, nombre + '.html'), 'w', encoding='utf-8').write(
            pagina(acento, cuerpo))
        plan.append({'archivo': nombre, 'alto': 1350})
        if args.guias:
            io.open(os.path.join(SALIDA, nombre + '.guia.html'), 'w',
                    encoding='utf-8').write(pagina(acento, cuerpo, guia=True))
            plan.append({'archivo': nombre + '.guia', 'alto': 1350})
    for nombre, acento, clave in DESTACADAS:
        io.open(os.path.join(SALIDA, nombre + '.html'), 'w', encoding='utf-8').write(
            pagina_dest(acento, clave))
        plan.append({'archivo': nombre, 'alto': 1080})
    io.open(os.path.join(SALIDA, 'plan.json'), 'w').write(json.dumps(plan))

    # ── avatar: la "a" blanca sobre el azul, CUADRADO A SANGRE ──
    # Instagram recorta el círculo solo; subir el círculo ya recortado deja
    # esquinas transparentes que el visor rellena de blanco o negro.
    from PIL import Image
    D = 1000
    av = Image.new('RGBA', (D, D), azul + (255,))
    w = int(D * .50)
    h = max(1, int(letra_img.size[1] * w / letra_img.size[0]))
    av.alpha_composite(letra_img.resize((w, h), Image.LANCZOS),
                       ((D - w) // 2, (D - h) // 2 - 8))
    av.convert('RGB').save(os.path.join(SALIDA, 'avatar.png'))

    print('%d páginas + avatar en %s' % (len(plan), SALIDA))
    print('Para rasterizar:  python3 tools/rasteriza_posts.py')


if __name__ == '__main__':
    main()
