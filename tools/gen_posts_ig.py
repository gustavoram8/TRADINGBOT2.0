# -*- coding: utf-8 -*-
"""Artes de Instagram/TikTok de Tradeable Academy — generador.

    python3 tools/gen_posts_ig.py             # todo
    python3 tools/gen_posts_ig.py --guias     # además, con la zona segura marcada
    python3 tools/rasteriza_posts.py          # pasarlo a PNG

Sale en `out/posts_ig/` (ignorado por git): 9 posts 1080×1350, 5 portadas de
destacadas 1080×1080 y el avatar 1000×1000.

PARA QUÉ SON: son posts del FEED — la cuadrícula del perfil. No son historias ni
destacadas. Son el escaparate que decide si alguien te sigue, así que van ANTES
de empezar con reels: el reel trae gente y esa gente aterriza aquí.

Por qué un generador y no 14 diseños sueltos: mismo criterio que las placas del
foro y los cursores. Se cambia el texto y el arte se rehace con el mismo suelo,
las mismas tipografías y las mismas reglas.

DECISIONES QUE NO SON COSMÉTICAS
--------------------------------
· **1080×1350 (4:5)** ocupa más pantalla en el feed. ⚠️ PERO la cuadrícula del
  perfil RECORTA al cuadrado central: lo que deba entenderse ahí vive en esos
  1080×1080 del medio. `--guias` lo dibuja.
· **Un solo acento por pieza.** Azul = producto, dorado = conocimiento, blanco =
  disciplina. Nunca dos compitiendo — la misma lección de los camos.
· **Composición VARIADA, suelo constante.** Nueve piezas con la misma retícula
  se leen como una plantilla, no como una marca. Cada post usa un `tipo` de
  maquetación distinto; lo que se repite es el grafito, la rejilla, el
  resplandor y la tipografía. Eso es lo que hace sistema; lo otro hacía monotonía.
· **La mascota ancla la cuadrícula.** Va enorme y translúcida en el post CENTRAL
  (el 5º), que es el que cae en el medio del 3×3, y sólida y pequeña en el post
  de "cómo funciona", donde hace de profesor entregando la corrección.
· **Números en JetBrains Mono.** En la tipografía de texto un número se lee como
  adorno; en monoespaciada se lee como dato.
· **Las velas se dibujan desde OHLC y son correctas.** El Order Block señala la
  última vela BAJISTA antes del desplazamiento; el Fair Value Gap, el hueco
  entre el MÁXIMO de la 1ª y el MÍNIMO de la 3ª — con líneas punteadas y sus
  rótulos, porque una banda sin borde se lee como decoración y no como hueco.
  Un diagrama bonito pero falso cuesta credibilidad ante gente que sabe leer.
· **Las portadas de destacadas van SIN TEXTO** (Instagram escribe el título
  debajo del círculo) y con glifos SIMPLES: a ~64px un icono con detalle se
  vuelve una mancha.
· **El avatar es la "a", no el logotipo**: el logotipo es 6:1 y la foto de perfil
  es un círculo; a 32px la palabra entera es ilegible.
"""
import argparse
import base64
import io
import json
import os
import random
import subprocess
import sys
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EST = os.path.join(RAIZ, 'scalpel', 'static')
LOGO_SRC = os.path.join(EST, 'logo_t.png')
MASCOTA_SRC = os.path.join(EST, 'logo2_dark.png')   # el muñeco-flecha, saludando
FUENTES_DIR = os.path.join(RAIZ, 'tools', '.fuentes')
SALIDA = os.path.join(RAIZ, 'out', 'posts_ig')

AZUL = '#004feb'          # medido del propio logotipo, no elegido a ojo
ORO = '#c9a227'
BLANCO = '#ffffff'
GRAFITO = '#0d0f14'

FUENTES = [('Inter', 'Inter:wght@400;600;700;800;900'),
           ('JetBrainsMono', 'JetBrains+Mono:wght@400;700')]


# ── tipografías (SIL OFL; se bajan a una carpeta ignorada) ───────────────
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
                     'los .ttf en %s' % (nombre, FUENTES_DIR))
        for peso, url in pares:
            subprocess.run(['curl', '-s', '-o',
                            os.path.join(FUENTES_DIR, '%s-%s.ttf' % (nombre, peso)),
                            url], timeout=90)


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
    """(logotipo blanco b64, "a" blanca b64, azul de marca, "a" como imagen).

    ⚠️ El azul se toma del color MÁS REPETIDO entre píxeles opacos, no del
    primero: el primero cae en el borde suavizado y da #84a9e8, no #004feb.
    """
    from PIL import Image
    im = Image.open(LOGO_SRC).convert('RGBA')
    im = im.crop(im.getchannel('A').getbbox())
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
    p1, p2 = (os.path.join(SALIDA, '_logo_blanco.png'),
              os.path.join(SALIDA, '_a_blanca.png'))
    blanco.save(p1)
    letra.save(p2)
    return b64(p1), b64(p2), azul, letra


# ── velas ────────────────────────────────────────────────────────────────
def velas(datos, alto=100, destacar=None, zona=None, acento=ORO, etiquetas=None):
    """datos: [(apertura, cierre, máximo, mínimo)]. destacar: índice a enmarcar.
    zona: (precio_bajo, precio_alto), sombreada CON borde punteado — el borde es
    lo que la hace leerse como un hueco delimitado y no como una banda de color.
    etiquetas: [(precio, texto)] rotuladas a la derecha."""
    n = len(datos)
    ancho = n * 40
    todos = [v for d in datos for v in d]
    lo, hi = min(todos), max(todos)
    pad = (hi - lo) * .12
    lo, hi = lo - pad, hi + pad

    def Y(v):
        return alto - (v - lo) / (hi - lo) * alto

    paso, piezas = ancho / n, []
    cw = paso * .5
    if zona:
        y0, y1 = Y(zona[1]), Y(zona[0])
        piezas.append('<rect x="0" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                      'opacity=".16"/>' % (y0, ancho, y1 - y0, acento))
        for yy in (y0, y1):
            piezas.append('<line x1="0" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                          'stroke-width="1.6" stroke-dasharray="6 5"/>'
                          % (yy, ancho, yy, acento))
    for i, (ap, ci, mx, mn) in enumerate(datos):
        cx = paso * (i + .5)
        col = '#3fb27f' if ci >= ap else '#d8544f'
        piezas.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                      'stroke-width="2.6"/>' % (cx, Y(mx), cx, Y(mn), col))
        y0, y1 = Y(max(ap, ci)), Y(min(ap, ci))
        h = max(2.5, y1 - y0)
        piezas.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                      'rx="1.5"/>' % (cx - cw / 2, y0, cw, h, col))
        if destacar == i:
            piezas.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                          'fill="none" stroke="%s" stroke-width="3" rx="4"/>'
                          % (cx - cw / 2 - 8, y0 - 8, cw + 16, h + 16, acento))
    for precio, texto in (etiquetas or []):
        piezas.append('<text x="%.1f" y="%.1f" fill="%s" font-size="7" '
                      'font-family="monospace" text-anchor="end">%s</text>'
                      % (ancho - 3, Y(precio) - 3.2, acento, texto))
    return ('<svg viewBox="0 0 %.0f %.0f" style="width:100%%;height:auto" '
            'xmlns="http://www.w3.org/2000/svg">%s</svg>'
            % (ancho, alto, ''.join(piezas)))


def miniaturas():
    """El fondo de 'cientos de capturas': gráficos diminutos desordenados.
    Semilla fija para que la pieza salga igual cada vez que se regenere."""
    r = random.Random(7)
    out = []
    for i in range(18):
        x, y = r.randint(-6, 80), r.randint(-4, 88)
        rot = r.uniform(-11, 11)
        w, h = r.randint(17, 25), r.randint(11, 16)
        barras = ''.join(
            '<rect x="%.1f" y="%.1f" width="1.5" height="%.1f" fill="#fff" '
            'opacity=".55"/>' % (2 + j * 2.2, h - 2 - r.uniform(1.5, h - 4),
                                 r.uniform(1.5, h - 4))
            for j in range(int(w / 2.4)))
        out.append('<g transform="translate(%d,%d) rotate(%.1f)" opacity=".22">'
                   '<rect width="%d" height="%d" rx="1.6" fill="#fff" opacity=".08" '
                   'stroke="#fff" stroke-width=".5"/>%s</g>' % (x, y, rot, w, h, barras))
    return ('<svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" '
            'style="position:absolute;inset:0;width:100%;height:100%" '
            'xmlns="http://www.w3.org/2000/svg">' + ''.join(out) + '</svg>')


def pips(activos=3, total=8, color=ORO):
    """La tira de rangos: los ganados rellenos, los que faltan en contorno."""
    p = []
    for i in range(total):
        lleno = i < activos
        p.append('<rect x="%d" y="0" width="26" height="10" rx="5" fill="%s" '
                 'stroke="%s" stroke-width="1.6" opacity="%s"/>'
                 % (i * 34, color if lleno else 'none', color,
                    '1' if lleno else '.45'))
    return ('<svg viewBox="0 0 %d 10" style="width:100%%;height:auto" '
            'xmlns="http://www.w3.org/2000/svg">%s</svg>'
            % (total * 34 - 8, ''.join(p)))


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:HEIGHTpx;background:GRAFITO}
.lienzo{position:relative;width:1080px;height:HEIGHTpx;overflow:hidden;
  background:GRAFITO;font-family:Inter,sans-serif;color:#eef0f5}
/* el suelo de la casa: rejilla + resplandor, los mismos del landing */
.lienzo::before{content:'';position:absolute;inset:0;z-index:0;
  background:radial-gradient(62% 46% at 50% -6%, ACENTO24, transparent 70%)}
.lienzo::after{content:'';position:absolute;inset:0;z-index:0;opacity:.5;
  background-image:linear-gradient(rgba(255,255,255,.055) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.055) 1px,transparent 1px);
  background-size:60px 60px;
  -webkit-mask-image:radial-gradient(72% 56% at 50% 4%,#000,transparent 76%)}
.marco{position:relative;z-index:3;height:100%;padding:96px 88px 84px;
  display:flex;flex-direction:column}
.etq{font-family:Mono,monospace;font-size:23px;font-weight:700;letter-spacing:.22em;
  color:ACENTO;text-transform:uppercase;margin-bottom:32px}
h1{font-size:94px;font-weight:900;line-height:1.02;letter-spacing:-.035em}
h1.chico{font-size:74px}
h1 em{font-style:normal;color:ACENTO}
.sub{margin-top:30px;font-size:36px;line-height:1.42;color:#aab2c4;max-width:820px}
.cuerpo{flex:1;display:flex;flex-direction:column;justify-content:center}
.pie{position:relative;z-index:3;display:flex;align-items:center;justify-content:space-between}
.pie img{height:44px;opacity:.92}
.pie .ar{font-family:Mono,monospace;font-size:24px;color:#6d7484;letter-spacing:.04em}
.segura{position:absolute;left:0;right:0;top:SEGTOPpx;height:1080px;z-index:9;
  outline:3px dashed rgba(255,120,120,.85);pointer-events:none}
.nota{margin-top:26px;font-size:30px;color:#9aa2b4;line-height:1.42}
.nota b{color:#dfe3ec}

/* — capas de fondo que dan vida sin robar protagonismo — */
.agua{position:absolute;z-index:1;pointer-events:none}
.agua.a-der{right:-190px;top:120px;width:820px;opacity:.05}
.haz{position:absolute;inset:0;z-index:1;pointer-events:none;
  background:linear-gradient(112deg,transparent 34%,ACENTO14 50%,transparent 66%)}
.mascota{position:absolute;z-index:1;right:-210px;bottom:-190px;width:1010px;
  opacity:.26;pointer-events:none}
.mascota.chica{position:relative;right:auto;bottom:auto;width:250px;opacity:1;
  z-index:3;margin-top:8px}
.velo{position:absolute;inset:0;z-index:2;pointer-events:none;
  background:linear-gradient(180deg,GRAFITOe8 0%,GRAFITOb0 46%,GRAFITOee 100%)}

/* — bloques — */
.graf{margin:40px 0 6px;padding:34px 38px;border:1px solid rgba(255,255,255,.12);
  border-radius:22px;background:rgba(255,255,255,.035)}
.lista{display:flex;flex-direction:column;gap:21px;margin-top:14px}
.lista div{display:flex;align-items:center;gap:22px;font-size:39px;font-weight:700}
.lista i{font-style:normal;font-family:Mono,monospace;font-size:26px;color:ACENTO;min-width:56px}
.dos{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-top:38px}
.dos section{border:1px solid rgba(255,255,255,.13);border-radius:20px;padding:30px 28px;
  background:rgba(255,255,255,.035)}
.dos h2{font-family:Mono,monospace;font-size:24px;letter-spacing:.14em;color:ACENTO;
  text-transform:uppercase;margin-bottom:20px}
.dos li{list-style:none;font-size:29px;line-height:1.5;color:#c3cad8;
  padding-left:26px;position:relative;margin-bottom:12px}
.dos li::before{content:'';position:absolute;left:0;top:15px;width:11px;height:2px;
  border-radius:2px;background:ACENTO}
.tarj{margin-top:36px;border:1px solid ACENTO55;border-radius:22px;overflow:hidden;
  background:rgba(255,255,255,.04)}
.tarj .cab{display:flex;align-items:center;gap:14px;padding:20px 28px;
  background:ACENTO1c;font-family:Mono,monospace;font-size:22px;letter-spacing:.14em;
  color:ACENTO;text-transform:uppercase}
.tarj .cab b{width:11px;height:11px;border-radius:50%;background:ACENTO}
.tarj p{padding:26px 28px 30px;font-size:31px;line-height:1.45;color:#d5dbe6}
.tarj p u{text-decoration:none;color:ACENTO;font-weight:700}
.fila{display:flex;align-items:flex-end;gap:34px}
.pipbar{margin-top:34px;width:78%}
"""

DEST_CSS = """
.dest{position:relative;width:1080px;height:1080px;background:GRAFITO;overflow:hidden;
  display:grid;place-items:center}
.dest::before{content:'';position:absolute;inset:0;
  background:radial-gradient(72% 62% at 50% 50%, ACENTO22, transparent 72%)}
.dest .g{position:relative;z-index:2;width:430px;height:430px}
.dest .g svg{width:100%;height:100%}
.dest .m{position:relative;z-index:2;width:300px}
"""


def glifos(A):
    """Glifos de destacadas: silueta simple y maciza. A ~64px cualquier detalle
    fino desaparece — la primera versión llevaba una medalla con cintas y un
    nodo tipo molécula, y ninguno se entendía."""
    return {
        # tres velas: el símbolo más directo de "método de lectura"
        'velas': ("<svg viewBox='0 0 100 100'><g fill='%s'>"
                  "<rect x='14' y='38' width='18' height='30' rx='4'/>"
                  "<rect x='19' y='26' width='8' height='54' rx='4'/>"
                  "<rect x='41' y='22' width='18' height='50' rx='4'/>"
                  "<rect x='46' y='12' width='8' height='72' rx='4'/>"
                  "<rect x='68' y='46' width='18' height='22' rx='4'/>"
                  "<rect x='73' y='34' width='8' height='48' rx='4'/></g></svg>") % A,
        # libro abierto = conceptos, definiciones
        'libro': ("<svg viewBox='0 0 100 100' fill='none' stroke='%s' "
                  "stroke-width='7' stroke-linejoin='round' stroke-linecap='round'>"
                  "<path d='M50 30c-9-8-20-10-32-9v46c12-1 23 1 32 9'/>"
                  "<path d='M50 30c9-8 20-10 32-9v46c-12-1-23 1-32 9'/>"
                  "<line x1='50' y1='30' x2='50' y2='76'/></svg>") % A,
        # birrete = academia. Universal, y se lee entero a 64px
        'birrete': ("<svg viewBox='0 0 100 100'><g fill='%s'>"
                    "<path d='M50 22 92 40 50 58 8 40z'/>"
                    "<path d='M26 48v18c0 7 11 12 24 12s24-5 24-12V48L50 62z'/>"
                    "<rect x='86' y='40' width='6' height='26' rx='3'/></g></svg>") % A,
        'flecha': ("<svg viewBox='0 0 100 100' fill='none'><g stroke='%s' "
                   "stroke-width='11' stroke-linecap='round' stroke-linejoin='round'>"
                   "<line x1='22' y1='70' x2='72' y2='30'/>"
                   "<polyline points='44,26 76,25 75,57'/></g></svg>") % A,
    }


DESTACADAS = [('h1-que-es', AZUL, 'marca'), ('h2-metodos', AZUL, 'velas'),
              ('h3-conceptos', ORO, 'libro'), ('h4-academia', ORO, 'birrete'),
              ('h5-empezar', BLANCO, 'flecha')]


# ══ TEXTOS POR IDIOMA ════════════════════════════════════════════════════
# 🔑 El texto va HORNEADO en la imagen (no es un caption), así que cambiar de
#    idioma obliga a rehacer el arte. Por eso vive aquí y no dentro de la
#    maquetación: `--idioma en` regenera los nueve y el español no se pierde.
# ⚠️ Al traducir, vigilar el LARGO: los titulares llevan saltos de línea a mano
#    (<br>) porque están calibrados para que ninguna línea desborde el ancho
#    seguro. Una traducción más larga sin recolocar el <br> parte la maqueta.
TEXTOS = {
 'es': {
  'e1': 'Tradeable Academy',
  't1': 'Tu gráfico ya te dijo<br>qué hiciste mal.', 's1': 'Nadie te lo tradujo.',
  'e2': 'El problema',
  't2': 'Cientos<br>de capturas.<br><em>Ningún método.</em>',
  's2': ('Guardar tus trades no es revisarlos. Una carpeta llena de gráficos '
         'no te dice qué repetiste mal.'),
  'e3': 'Cómo funciona',
  't3': 'No detecta patrones.<br>Aplica <em>tu</em> metodología.',
  'c3cab': 'Corrección · ICT',
  'c3': ('Marcaste el order block sobre una vela bajista cualquiera. El válido '
         'es <u>la última antes del desplazamiento</u> — el que usaste no tenía '
         'intención detrás.'),
  'e4': 'Concepto', 't4': 'Order Block',
  'n4': ('La última vela bajista <b>antes</b> de un movimiento alcista con '
         'desplazamiento. No cualquier vela roja: la que quedó justo antes de '
         'que el precio saliera disparado.'),
  'e5': 'Detrás', 't5': 'Estamos<br>construyendo<br>algo.',
  's5': ('Un sitio donde revisar tus gráficos deje de ser una carpeta de '
         'capturas. Te vamos a ir enseñando cada pieza.'),
  'e6': 'Concepto', 't6': 'Fair Value Gap',
  'g6a': 'mínimo 3ª', 'g6b': 'máximo 1ª',
  'n6': ('Tres velas. El <b>máximo de la primera</b> queda por debajo del '
         '<b>mínimo de la tercera</b>: entre esas dos líneas no se negoció '
         'nada. El precio pasó demasiado rápido.'),
  'e7': 'Los dos frentes', 't7': 'Un trade se pierde<br>en dos sitios.',
  'h7a': 'Análisis', 'h7b': 'Ejecución',
  'l7a': ['Zona mal marcada', 'Estructura leída al revés',
          'Contexto del marco mayor ignorado'],
  'l7b': ['Entrada adelantada', 'Stop movido', 'Posición doblada'],
  'n7': ('La IA te corrige en los dos. De poco sirve leer bien el gráfico si '
         'lo operas de otra forma — y al revés tampoco.'),
  'e8': 'Enfoques', 't8': 'Siete formas de leer<br>el mismo gráfico.',
  'l8': ['ICT', 'Smart Money Concepts', 'Wyckoff', 'Price Action',
         'Patrones y armónicos', 'Elliott', 'Análisis técnico'],
  'n8': 'Eliges la tuya. La corrección llega en ese idioma.',
  'e9': 'La academia', 't9': 'De Paper Trader<br>a Market Maker.',
  's9': ('Ocho rangos. Se suben estudiando, resolviendo y revisando — no '
         'acertando operaciones.'),
  'n9': ('Premiar aciertos sería premiar suerte, y la suerte no se enseña.'),
 },
 'en': {
  'e1': 'Tradeable Academy',
  # ⚠️ el <br> tras "already" no es capricho: "Your chart already told you" no
  #    cabe en una línea a este cuerpo y el navegador partía dejando un renglón
  #    huérfano de dos palabras
  't1': 'Your chart<br>already told you<br>what went wrong.',
  's1': 'Nobody translated it for you.',
  'e2': 'The problem',
  't2': 'Hundreds<br>of screenshots.<br><em>No method.</em>',
  's2': ('Saving your trades is not reviewing them. A folder full of charts '
         "won't tell you what you keep getting wrong."),
  'e3': 'How it works',
  't3': "It doesn't spot patterns.<br>It applies <em>your</em> method.",
  'c3cab': 'Correction · ICT',
  'c3': ('You marked the order block on just any bearish candle. The valid one '
         'is <u>the last one before the displacement</u> — the one you used had '
         'no intent behind it.'),
  'e4': 'Concept', 't4': 'Order Block',
  'n4': ('The last bearish candle <b>before</b> a bullish move with '
         'displacement. Not any red candle: the one sitting right before price '
         'took off.'),
  'e5': 'Behind it', 't5': "We're<br>building<br>something.",
  's5': ('A place where reviewing your charts stops being a folder of '
         "screenshots. We'll show you every piece of it."),
  'e6': 'Concept', 't6': 'Fair Value Gap',
  'g6a': '3rd low', 'g6b': '1st high',
  'n6': ('Three candles. The <b>high of the first</b> sits below the <b>low of '
         'the third</b>: between those two lines nothing traded at all. Price '
         'moved through too fast.'),
  'e7': 'Two fronts', 't7': 'A trade is lost<br>in two places.',
  'h7a': 'Analysis', 'h7b': 'Execution',
  'l7a': ['Zone marked wrong', 'Structure read backwards',
          'Higher timeframe ignored'],
  'l7b': ['Entry taken early', 'Stop moved', 'Position doubled'],
  'n7': ('The AI corrects both. Reading the chart well is worth little if you '
         'trade it another way — and the other way round too.'),
  'e8': 'Approaches', 't8': 'Seven ways to read<br>the same chart.',
  'l8': ['ICT', 'Smart Money Concepts', 'Wyckoff', 'Price Action',
         'Patterns & harmonics', 'Elliott', 'Technical analysis'],
  'n8': 'You pick yours. The correction comes back in that language.',
  'e9': 'The academy', 't9': 'From Paper Trader<br>to Market Maker.',
  's9': ('Eight ranks. You climb them by studying, answering and reviewing — '
         'not by winning trades.'),
  'n9': 'Rewarding wins would reward luck, and luck cannot be taught.',
 },
}


def construye_posts(letra_b64, mascota_b64, T):
    """Nueve piezas, nueve maquetaciones. El suelo es lo único que se repite."""
    P = []
    li = lambda xs: ''.join('<li>%s</li>' % x for x in xs)          # noqa: E731

    # 1 · titular con la "a" gigante saliendo por el borde
    P.append(('01-manifiesto', AZUL,
              "<img class='agua a-der' src='data:image/png;base64,%s'>" % letra_b64,
              "<div class='etq'>%s</div><div class='cuerpo'>"
              "<h1>%s</h1><p class='sub'>%s</p></div>"
              % (T['e1'], T['t1'], T['s1'])))

    # 2 · el problema, con el fondo lleno de capturas
    P.append(('02-problema', BLANCO,
              miniaturas() + "<div class='velo'></div>",
              "<div class='etq'>%s</div><div class='cuerpo'>"
              "<h1>%s</h1><p class='sub'>%s</p></div>"
              % (T['e2'], T['t2'], T['s2'])))

    # 3 · cómo funciona: la corrección simulada + la mascota de profesor
    P.append(('03-que-hace', AZUL, '',
              "<div class='etq'>%s</div><div class='cuerpo'>"
              "<h1 class='chico'>%s</h1>"
              "<div class='fila'><div style='flex:1'><div class='tarj'>"
              "<div class='cab'><b></b>%s</div><p>%s</p></div></div>"
              "<img class='mascota chica' src='data:image/png;base64,%s'></div>"
              "</div>" % (T['e3'], T['t3'], T['c3cab'], T['c3'], mascota_b64)))

    # 4 · order block
    P.append(('04-order-block', ORO, '',
              "<div class='etq'>%s</div><div class='cuerpo'>"
              "<h1>%s</h1><div class='graf'>%s</div>"
              "<p class='nota'>%s</p></div>"
              % (T['e4'], T['t4'],
                 velas([(50, 52, 53, 49), (52, 51, 53, 50), (51, 48, 52, 47),
                        (48, 58, 60, 47), (58, 66, 68, 57), (66, 64, 69, 62),
                        (64, 71, 73, 63)], destacar=2), T['n4'])))

    # 5 · CENTRO de la cuadrícula: la mascota, enorme y translúcida
    P.append(('05-mascota', AZUL,
              "<img class='mascota' src='data:image/png;base64,%s'>" % mascota_b64,
              "<div class='etq'>%s</div><div class='cuerpo'>"
              "<h1>%s</h1><p class='sub'>%s</p></div>"
              % (T['e5'], T['t5'], T['s5'])))

    # 6 · fair value gap — hueco delimitado y rotulado
    P.append(('06-fvg', ORO, '',
              "<div class='etq'>%s</div><div class='cuerpo'>"
              "<h1>%s</h1><div class='graf'>%s</div>"
              "<p class='nota'>%s</p></div>"
              % (T['e6'], T['t6'],
                 velas([(50, 52, 53, 49), (52, 69, 71, 51), (69, 73, 75, 64)],
                       alto=74, zona=(53, 64),
                       etiquetas=[(64, T['g6a']), (53, T['g6b'])]), T['n6'])))

    # 7 · dónde se pierde un trade: las DOS familias de error
    P.append(('07-analisis-ejecucion', BLANCO, '',
              "<div class='etq'>%s</div><div class='cuerpo'>"
              "<h1 class='chico'>%s</h1><div class='dos'>"
              "<section><h2>%s</h2><ul>%s</ul></section>"
              "<section><h2>%s</h2><ul>%s</ul></section></div>"
              "<p class='nota'>%s</p></div>"
              % (T['e7'], T['t7'], T['h7a'], li(T['l7a']), T['h7b'],
                 li(T['l7b']), T['n7'])))

    # 8 · metodologías, con haz diagonal
    P.append(('08-metodologias', AZUL, "<div class='haz'></div>",
              "<div class='etq'>%s</div><div class='cuerpo'>"
              "<h1 class='chico'>%s</h1><div class='lista'>%s</div>"
              "<p class='nota'>%s</p></div>"
              % (T['e8'], T['t8'],
                 ''.join('<div><i>%02d</i>%s</div>' % (i + 1, m)
                         for i, m in enumerate(T['l8'])), T['n8'])))

    # 9 · rangos, con la tira de pips
    P.append(('09-rangos', ORO, '',
              "<div class='etq'>%s</div><div class='cuerpo'>"
              "<h1 class='chico'>%s</h1><div class='pipbar'>%s</div>"
              "<p class='sub' style='margin-top:34px'>%s</p>"
              "<p class='nota'>%s</p></div>"
              % (T['e9'], T['t9'], pips(3), T['s9'], T['n9'])))
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--guias', action='store_true',
                    help='dibuja la zona segura de la cuadrícula del perfil')
    ap.add_argument('--idioma', default='en', choices=sorted(TEXTOS),
                    help='idioma del texto HORNEADO en el arte (default: en)')
    args = ap.parse_args()
    T = TEXTOS[args.idioma]

    asegura_fuentes()
    os.makedirs(SALIDA, exist_ok=True)
    fuentes = caras()
    logo_b64, letra_b64, azul, letra_img = piezas_logo()
    assert '#%02x%02x%02x' % azul == AZUL, \
        'el azul del logo cambió (%s): actualiza la constante' % ('#%02x%02x%02x' % azul)
    mascota_b64 = b64(MASCOTA_SRC)

    def pagina(acento, fondo, cuerpo, alto=1350, guia=False):
        css = (CSS.replace('ACENTO', acento).replace('GRAFITO', GRAFITO)
                  .replace('HEIGHT', str(alto))
                  .replace('SEGTOP', str((alto - 1080) // 2)))
        seg = '<div class="segura"></div>' if guia else ''
        return ("<!doctype html><meta charset='utf-8'><style>%s%s</style>"
                "<div class='lienzo'>%s%s<div class='marco'>%s<div class='pie'>"
                "<img src='data:image/png;base64,%s'>"
                "<span class='ar'>@tradeableacademy</span></div></div></div>"
                % (fuentes, css, fondo, seg, cuerpo, logo_b64))

    def pagina_dest(acento, clave):
        css = (fuentes + DEST_CSS.replace('ACENTO', acento).replace('GRAFITO', GRAFITO)
               + 'html,body{margin:0;width:1080px;height:1080px;background:%s}' % GRAFITO)
        cuerpo = ("<img class='m' src='data:image/png;base64,%s'>" % letra_b64
                  if clave == 'marca' else
                  "<div class='g'>%s</div>" % glifos(acento)[clave])
        return ("<!doctype html><meta charset='utf-8'><style>%s</style>"
                "<div class='dest'>%s</div>" % (css, cuerpo))

    plan = []
    for nombre, acento, fondo, cuerpo in construye_posts(letra_b64, mascota_b64, T):
        io.open(os.path.join(SALIDA, nombre + '.html'), 'w', encoding='utf-8').write(
            pagina(acento, fondo, cuerpo))
        plan.append({'archivo': nombre, 'alto': 1350})
        if args.guias:
            io.open(os.path.join(SALIDA, nombre + '.guia.html'), 'w',
                    encoding='utf-8').write(pagina(acento, fondo, cuerpo, guia=True))
            plan.append({'archivo': nombre + '.guia', 'alto': 1350})
    for nombre, acento, clave in DESTACADAS:
        io.open(os.path.join(SALIDA, nombre + '.html'), 'w', encoding='utf-8').write(
            pagina_dest(acento, clave))
        plan.append({'archivo': nombre, 'alto': 1080})
    io.open(os.path.join(SALIDA, 'plan.json'), 'w').write(json.dumps(plan))

    # avatar: la "a" blanca sobre el azul, CUADRADO A SANGRE — Instagram recorta
    # el círculo solo, y subir el círculo ya recortado deja esquinas que el
    # visor rellena de blanco o negro.
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
