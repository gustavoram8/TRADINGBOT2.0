# -*- coding: utf-8 -*-
"""Catálogo de CURSORES + su banco de pruebas.

UN CURSOR NO ES UNA PLACA, y esto manda sobre todo el diseño:

1. El navegador solo acepta **PNG** en `cursor: url(...)`. Chrome NO renderiza
   SVG como cursor (Firefox sí; Safari tampoco), así que el arte se dibuja en
   SVG —cómodo de editar— pero se PUBLICA rasterizado a PNG.
2. El PNG se muestra a su tamaño real en píxeles CSS, así que tiene que medir
   **32x32**. Se rasteriza a 4x (128px) y se reduce con LANCZOS: a 32px directo
   los bordes salen dentados.
3. **La silueta no se negocia.** Un cursor es una herramienta antes que un
   adorno: si el usuario pierde de vista dónde está apuntando, el cosmético
   arruina el sitio. Por eso TODOS comparten la misma flecha y la misma manito,
   y la temática entra por el material, el color y una marca pequeña.
4. Dos archivos por cursor: `arrow` (por defecto) y `hand` (sobre lo clickeable).
   El punto activo va en la punta de la flecha (0,0) y en la yema del índice.

    python3 tools/cursors_preview.py            # hoja de prueba de todos
    python3 tools/cursors_preview.py chronicles # de algunos
"""
import os
import subprocess
import sys
import tempfile

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
OUT = os.environ.get('CURSORS_OUT', '/tmp/cursors_preview.png')

# ── Las dos siluetas, en un lienzo de 32x32 ────────────────────────────────
# La flecha clásica: punta arriba-izquierda, cola con el "pie" a la derecha.
ARROW = ('M1.6 1.6 L1.6 22.6 L7.2 17.4 L10.8 25.4 L14.2 23.8 L10.7 16.2 '
         'L17.6 15.9 Z')
# La manito: índice levantado + puño. Va como UNA silueta (un solo path), no
# como piezas apiladas: la primera versión dibujaba rectángulos sueltos y a
# 32px el contorno de cada pieza se fundía en un bulto sin dedos. Con un
# contorno único, el hueco entre el índice y los nudillos sobrevive al tamaño.
HAND = ('M11.2 15.4 L11.2 5.2 '
        'C11.2 3.3 14.6 3.3 14.6 5.2 L14.6 12.6 '
        'L14.6 11.4 C14.6 9.8 17.8 9.8 17.8 11.4 L17.8 13.2 '
        'L17.8 12.4 C17.8 10.9 21.0 10.9 21.0 12.4 L21.0 14.2 '
        'L21.0 13.6 C21.0 12.2 24.0 12.2 24.0 13.6 L24.0 20.4 '
        'C24.0 25.4 20.6 28.4 16.6 28.4 '
        'C12.8 28.4 10.0 26.2 10.0 22.2 L10.0 19.0 '
        'L8.0 21.4 C6.9 22.7 4.8 21.2 5.8 19.7 L11.2 15.4 Z')


def cursor_svg(shape, style, mark=''):
    """El SVG completo de una silueta con el material de un cursor."""
    defs = style.get('defs', '')
    fill = style['fill']
    edge = style.get('edge', '#0b0d12')
    ew = style.get('edge_w', 1.5)
    d = ARROW if shape == 'arrow' else HAND
    body = ('<path d="%s" fill="%s" stroke="%s" stroke-width="%s" '
            'stroke-linejoin="round" stroke-linecap="round"/>' % (d, fill, edge, ew))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" '
            'width="32" height="32"><defs>%s</defs>%s%s</svg>'
            % (defs, body, mark))


# ── El catálogo. (slug, nombre, familia, estilo, marca arrow, marca hand) ──
# `familia`: 'temporada' (atado al camo del mes), 'libre' o 'festivo'.
CURSORS = [
 ('chronicles', 'Chronicles', 'temporada', {
    'defs': '<linearGradient id="cr-b" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#3a2018"/>'
            '<stop offset="1" stop-color="#12080a"/></linearGradient>',
    'fill': 'url(#cr-b)', 'edge': '#ff5a1e', 'edge_w': 1.4},
  # la grieta de lava recorre la hoja y termina en una brasa
  '<path d="M3.6 4.2 L6.2 9.4 L4.8 12.2 L7.6 17.2" fill="none" stroke="#ff5a1e"'
  ' stroke-width="1.5" stroke-linecap="round"/>'
  '<circle cx="8.2" cy="19.4" r="1.5" fill="#ffb347"/>',
  '<path d="M12.9 6.4 L12.9 14.6" fill="none" stroke="#ff5a1e" stroke-width="1.3"'
  ' stroke-linecap="round" opacity=".95"/>'
  '<path d="M12.4 19.6 L14.6 22.4 L13.2 24.6" fill="none" stroke="#ff5a1e"'
  ' stroke-width="1.2" stroke-linecap="round"/>'
  '<circle cx="19.4" cy="24.4" r="1.5" fill="#ffb347"/>'),

 ('candle', 'Green Candle', 'libre', {
    'defs': '<linearGradient id="cd-b" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#39d98a"/>'
            '<stop offset="1" stop-color="#12805a"/></linearGradient>',
    'fill': 'url(#cd-b)', 'edge': '#06341f', 'edge_w': 1.5},
  '<path d="M4.6 6.4 L4.6 15.6" fill="none" stroke="#eafff4" stroke-width="1.4"'
  ' stroke-linecap="round" opacity=".85"/>',
  '<path d="M12.9 6.2 L12.9 14" fill="none" stroke="#eafff4"'
  ' stroke-width="1.3" stroke-linecap="round" opacity=".85"/>'),

 ('terminal', 'Phosphor', 'libre', {
    'defs': '', 'fill': '#0a1410', 'edge': '#4dff9e', 'edge_w': 1.6},
  '<rect x="4" y="5" width="2" height="2" fill="#4dff9e"/>'
  '<rect x="4" y="9" width="2" height="2" fill="#4dff9e" opacity=".7"/>'
  '<rect x="4" y="13" width="2" height="2" fill="#4dff9e" opacity=".45"/>',
  '<rect x="11.9" y="6.6" width="2" height="2" fill="#4dff9e"/>'
  '<rect x="11.9" y="10.4" width="2" height="2" fill="#4dff9e" opacity=".6"/>'
  '<rect x="14.4" y="21" width="2" height="2" fill="#4dff9e" opacity=".45"/>'),
]


# ══ Banco de pruebas ═══════════════════════════════════════════════════════
PAGE = """<!doctype html><meta charset="utf-8">
<style>
 body{margin:0;font-family:'Inter',system-ui,sans-serif;background:#eef1f6;padding:22px 26px;}
 .row{display:flex;align-items:center;gap:26px;background:#fff;border:1px solid #e4e6ec;
      border-radius:14px;padding:14px 18px;margin-bottom:12px;}
 .nm{width:150px;}
 .nm b{font-size:14px;font-weight:800;display:block;}
 .nm i{font-size:11px;color:#8a8f9e;font-style:normal;}
 .pair{display:flex;gap:18px;align-items:center;}
 .cell{text-align:center;}
 .cell .cap{font-size:9.5px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;
            color:#8a8f9e;margin-bottom:5px;}
 .zoom{width:128px;height:128px;image-rendering:pixelated;border:1px solid #e4e6ec;
       border-radius:9px;background:
       linear-gradient(45deg,#f3f4f7 25%,transparent 25%,transparent 75%,#f3f4f7 75%),
       linear-gradient(45deg,#f3f4f7 25%,transparent 25%,transparent 75%,#f3f4f7 75%);
       background-size:14px 14px;background-position:0 0,7px 7px;}
 .real{display:flex;gap:10px;align-items:center;}
 .chip{width:34px;height:34px;display:grid;place-items:center;border-radius:8px;}
 .chip.lt{background:#f4f6fa;border:1px solid #e4e6ec;}
 .chip.dk{background:#12151c;}
 .chip img{width:32px;height:32px;}
</style>
__BODY__
"""


def build_sheet(items):
    rows = []
    for slug, name, fam, style, m_arrow, m_hand in items:
        cells = []
        for shape, mark in (('arrow', m_arrow), ('hand', m_hand)):
            svg = cursor_svg(shape, style, mark)
            import base64
            b64 = base64.b64encode(svg.encode()).decode()
            uri = 'data:image/svg+xml;base64,' + b64
            cells.append(
                '<div class="cell"><div class="cap">%s</div>'
                '<img class="zoom" src="%s"></div>'
                '<div class="cell"><div class="cap">real</div>'
                '<div class="real"><span class="chip lt"><img src="%s"></span>'
                '<span class="chip dk"><img src="%s"></span></div></div>'
                % (shape, uri, uri, uri))
        rows.append('<div class="row"><div class="nm"><b>%s</b><i>%s</i></div>'
                    '<div class="pair">%s</div></div>' % (name, fam, ''.join(cells)))
    return PAGE.replace('__BODY__', '\n'.join(rows))


def shoot(items):
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False) as fh:
        fh.write(build_sheet(items))
        path = fh.name
    script = f'''
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path={CHROME!r})
    pg = b.new_page(viewport={{'width': 900, 'height': 400}}, device_scale_factor=2)
    pg.goto('file://{path}'); pg.wait_for_timeout(500)
    pg.screenshot(path={OUT!r}, full_page=True)
    b.close()
'''
    subprocess.run([sys.executable, '-c', script], check=True)
    os.unlink(path)
    print('captura →', OUT, '(%d cursores)' % len(items))


if __name__ == '__main__':
    todos = [c[0] for c in CURSORS]
    pedidos = sys.argv[1:] or todos
    malos = [s for s in pedidos if s not in todos]
    if malos:
        print('no existen:', malos)
        sys.exit(1)
    shoot([c for c in CURSORS if c[0] in pedidos])
