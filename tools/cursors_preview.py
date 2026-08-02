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

# ── CADA CURSOR ES UNA FIGURA ─────────────────────────────────────────────
# Decisión del dueño (2026-08-02): NO es la flecha del sistema recoloreada —
# cada cursor es un objeto con su propia silueta. Lo único que se hereda es la
# REGLA DE LA PUNTA: el punto activo va arriba-izquierda, en la punta afilada
# de la figura, para que el usuario nunca pierda dónde está clickeando.
#
# Dos estados por cursor, y el segundo no es un dibujo aparte: es la MISMA
# figura "encendida" (hoja al rojo, tinta que brota, chispa). Así el hover se
# entiende solo —"esto se puede clickear"— y cada cursor cuesta una figura y
# no dos.
HOTSPOT = (2, 2)          # la punta, en píxeles del lienzo de 32x32


def cursor_svg(body, defs=''):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" '
            'width="32" height="32"><defs>%s</defs>%s</svg>' % (defs, body))


# (slug, nombre, familia, defs, cuerpo normal, cuerpo activo)
CURSORS = [
 ('chronicles', 'Chronicles — espada', 'temporada',
  '<linearGradient id="sw-b" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#e8eef6"/><stop offset=".55" stop-color="#8d99a8"/>'
  '<stop offset="1" stop-color="#4a5462"/></linearGradient>'
  '<linearGradient id="sw-h" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#ffd76a"/><stop offset="1" stop-color="#a8752a"/></linearGradient>',
  # hoja + guarda + empuñadura + pomo
  '<path d="M2.2 2.2 L17.1 14.9 L14.9 17.1 Z" fill="url(#sw-b)" stroke="#2a3038"'
  ' stroke-width="1.1" stroke-linejoin="round"/>'
  '<path d="M19.7 12.6 L21.4 14.3 L14.3 21.4 L12.6 19.7 Z" fill="url(#sw-h)"'
  ' stroke="#5a3f14" stroke-width="1"/>'
  '<path d="M17.8 16.2 L25.3 23.7 L23.7 25.3 L16.2 17.8 Z" fill="#6b4a24"'
  ' stroke="#33230f" stroke-width="1"/>'
  '<circle cx="26.2" cy="26.2" r="2.3" fill="url(#sw-h)" stroke="#5a3f14" stroke-width="1"/>',
  # activa: la hoja se pone al rojo y suelta brasas
  '<path d="M2.2 2.2 L17.1 14.9 L14.9 17.1 Z" fill="#ff5a1e" stroke="#ffd08a"'
  ' stroke-width="1.1" stroke-linejoin="round"/>'
  '<path d="M4.6 4.6 L14.4 13.2" fill="none" stroke="#fff3c4" stroke-width="1.2"'
  ' stroke-linecap="round"/>'
  '<path d="M19.7 12.6 L21.4 14.3 L14.3 21.4 L12.6 19.7 Z" fill="url(#sw-h)"'
  ' stroke="#5a3f14" stroke-width="1"/>'
  '<path d="M17.8 16.2 L25.3 23.7 L23.7 25.3 L16.2 17.8 Z" fill="#6b4a24"'
  ' stroke="#33230f" stroke-width="1"/>'
  '<circle cx="26.2" cy="26.2" r="2.3" fill="url(#sw-h)" stroke="#5a3f14" stroke-width="1"/>'
  '<circle cx="9.4" cy="4.4" r="1.3" fill="#ffb347"/>'
  '<circle cx="13.6" cy="7.2" r="1" fill="#ffd08a"/>'),

 ('quill', 'Pluma', 'libre',
  '<linearGradient id="qf-b" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#7fc7ff"/><stop offset="1" stop-color="#2a5c9c"/></linearGradient>',
  # punta metálica + caña + barbas de la pluma
  '<path d="M2.2 2.2 L8.6 7.4 L6.8 9.4 Z" fill="#dfe7f2" stroke="#2a3038"'
  ' stroke-width="1" stroke-linejoin="round"/>'
  '<path d="M7.6 8.4 C14.4 9.6 23 17 26.4 25.8 L23.2 24.8 L22.4 22 L19.6 21.4'
  ' L18.8 18.6 L16 18 L15.2 15.2 L12.4 14.6 L11.6 11.8 L8.8 11.2 Z"'
  ' fill="url(#qf-b)" stroke="#12335c" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M8.2 8.8 L25.6 25.4" fill="none" stroke="#eaf4ff" stroke-width="1.15"'
  ' stroke-linecap="round" opacity=".95"/>',
  # activa: la punta suelta una gota de tinta
  '<path d="M2.2 2.2 L8.6 7.4 L6.8 9.4 Z" fill="#f2f7ff" stroke="#2a3038"'
  ' stroke-width="1" stroke-linejoin="round"/>'
  '<path d="M7.6 8.4 C14.4 9.6 23 17 26.4 25.8 L23.2 24.8 L22.4 22 L19.6 21.4'
  ' L18.8 18.6 L16 18 L15.2 15.2 L12.4 14.6 L11.6 11.8 L8.8 11.2 Z"'
  ' fill="url(#qf-b)" stroke="#12335c" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M8.2 8.8 L25.6 25.4" fill="none" stroke="#eaf4ff" stroke-width="1.15"'
  ' stroke-linecap="round" opacity=".95"/>'
  '<path d="M4.4 9.4 C4.4 12.4 7.6 12.4 7.6 9.4 C7.6 7.6 6 6.2 6 6.2'
  ' C6 6.2 4.4 7.6 4.4 9.4 Z" fill="#2f6ed9" stroke="#12335c" stroke-width=".9"/>',
  ),

 ('bolt', 'Rayo', 'libre',
  '<linearGradient id="bl-b" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#fff3a8"/><stop offset=".5" stop-color="#ffc23d"/>'
  '<stop offset="1" stop-color="#e07a12"/></linearGradient>',
  '<path d="M2.2 2.2 L17.4 9.6 L11.2 12.4 L22.6 17.6 L14.8 19.4 L21.4 28.4'
  ' L8.4 18.6 L14.8 16.4 L4.4 11.2 L10.2 9.4 Z" fill="url(#bl-b)" stroke="#8a4a06"'
  ' stroke-width="1.1" stroke-linejoin="round"/>',
  '<path d="M2.2 2.2 L17.4 9.6 L11.2 12.4 L22.6 17.6 L14.8 19.4 L21.4 28.4'
  ' L8.4 18.6 L14.8 16.4 L4.4 11.2 L10.2 9.4 Z" fill="#fff8d2" stroke="#e07a12"'
  ' stroke-width="1.4" stroke-linejoin="round"/>'
  '<circle cx="24.6" cy="10.4" r="1.4" fill="#ffe066"/>'
  '<circle cx="6.6" cy="20.6" r="1.1" fill="#ffe066"/>'),
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
    import base64
    rows = []
    for slug, name, fam, defs, normal, activo in items:
        cells = []
        for cap, body in (('normal', normal), ('sobre un enlace', activo)):
            svg = cursor_svg(body, defs)
            uri = 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()
            cells.append(
                '<div class="cell"><div class="cap">%s</div>'
                '<img class="zoom" src="%s"></div>'
                '<div class="cell"><div class="cap">real</div>'
                '<div class="real"><span class="chip lt"><img src="%s"></span>'
                '<span class="chip dk"><img src="%s"></span></div></div>'
                % (cap, uri, uri, uri))
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
