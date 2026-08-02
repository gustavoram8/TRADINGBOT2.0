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


# El estado ACTIVO es el cuerpo normal + un extra encima (chispa, brillo,
# repintado de una pieza). Guardar solo el extra evita duplicar cada figura y
# obliga a que los dos estados compartan silueta, que es lo que hace que el
# hover se lea como "la misma herramienta, encendida".
CHISPAS = ('<circle cx="9.6" cy="4.6" r="1.3" fill="#fff3c4"/>'
           '<circle cx="5.2" cy="9.8" r="1" fill="#fff3c4" opacity=".85"/>')

# (slug, nombre, temporada, defs, cuerpo, extra del estado activo)
CURSORS = [
 ('chronicles', 'Chronicles · espada', '2026-08',
  '<linearGradient id="a1" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#eef3fa"/><stop offset=".55" stop-color="#8d99a8"/>'
  '<stop offset="1" stop-color="#49525f"/></linearGradient>'
  '<linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#ffd76a"/><stop offset="1" stop-color="#a8752a"/></linearGradient>',
  '<path d="M2.2 2.2 L17.1 14.9 L14.9 17.1 Z" fill="url(#a1)" stroke="#2a3038"'
  ' stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M19.7 12.6 L21.4 14.3 L14.3 21.4 L12.6 19.7 Z" fill="url(#g1)"'
  ' stroke="#5a3f14" stroke-width=".95"/>'
  '<path d="M17.8 16.2 L25.3 23.7 L23.7 25.3 L16.2 17.8 Z" fill="#6b4a24"'
  ' stroke="#33230f" stroke-width=".95"/>'
  '<circle cx="26.2" cy="26.2" r="2.2" fill="url(#g1)" stroke="#5a3f14" stroke-width=".95"/>',
  '<path d="M2.2 2.2 L17.1 14.9 L14.9 17.1 Z" fill="#ff5a1e" stroke="#ffd08a"'
  ' stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M4.8 4.8 L14.2 12.9" fill="none" stroke="#fff3c4" stroke-width="1.1"'
  ' stroke-linecap="round"/>' + CHISPAS),

 ('gridiron', 'American Football · balón', '2026-09',
  '<linearGradient id="a2" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#a9552a"/><stop offset=".5" stop-color="#7d3a17"/>'
  '<stop offset="1" stop-color="#4e220c"/></linearGradient>',
  '<path d="M2.4 2.4 C11.4 4.2 23.2 16 25 25 C16 23.2 4.2 11.4 2.4 2.4 Z"'
  ' fill="url(#a2)" stroke="#2b1408" stroke-width="1.1" stroke-linejoin="round"/>'
  '<path d="M8.6 5.8 L5.8 8.6 M23 20.4 L20.4 23" fill="none" stroke="#f3ece0"'
  ' stroke-width="1.5" stroke-linecap="round"/>'
  '<path d="M10.6 16.8 L16.8 10.6" fill="none" stroke="#f3ece0" stroke-width="1.5"'
  ' stroke-linecap="round"/>'
  '<path d="M11.6 14 L14 11.6 M13.4 15.8 L15.8 13.4" fill="none" stroke="#f3ece0"'
  ' stroke-width="1.3" stroke-linecap="round"/>', None),

 ('nile', 'Nile · obelisco', '2026-10',
  '<linearGradient id="a3" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#f0d49a"/><stop offset=".55" stop-color="#cfa055"/>'
  '<stop offset="1" stop-color="#8f6a28"/></linearGradient>',
  '<path d="M7.94 5.26 L25.84 22.16 L22.16 25.84 L5.26 7.94 Z" fill="url(#a3)"'
  ' stroke="#5c421a" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M2.2 2.2 L8.16 5.04 L5.04 8.16 Z" fill="#e8c066" stroke="#5c421a"'
  ' stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M11.4 8.4 L8.4 11.4 M15.4 12.4 L12.4 15.4 M19.4 16.4 L16.4 19.4"'
  ' fill="none" stroke="#2f5fa8" stroke-width="1.2" stroke-linecap="round"/>'
  '<path d="M22.6 21.4 L26.6 25.4 L25 27 L21 23 Z" fill="#2f5fa8"'
  ' stroke="#173a6c" stroke-width=".9" stroke-linejoin="round"/>', None),

 ('colosseum', 'Colosseum · tridente', '2026-11',
  '<linearGradient id="a4" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#d7dde6"/><stop offset="1" stop-color="#6b7480"/></linearGradient>',
  '<path d="M12.6 12.6 L26.4 26.4" fill="none" stroke="#7a5326" stroke-width="3.2"'
  ' stroke-linecap="round"/>'
  '<path d="M8.9 15.1 L15.1 8.9 L16.5 10.3 L10.3 16.5 Z" fill="url(#a4)"'
  ' stroke="#3d4650" stroke-width=".95" stroke-linejoin="round"/>'
  '<path d="M2.2 2.2 L13.2 11 L11 13.2 Z" fill="url(#a4)" stroke="#3d4650"'
  ' stroke-width=".95" stroke-linejoin="round"/>'
  '<path d="M8.6 3.2 L14.6 11.4 L12.4 12.6 Z" fill="url(#a4)" stroke="#3d4650"'
  ' stroke-width=".95" stroke-linejoin="round"/>'
  '<path d="M3.2 8.6 L11.4 14.6 L12.6 12.4 Z" fill="url(#a4)" stroke="#3d4650"'
  ' stroke-width=".95" stroke-linejoin="round"/>', None),

 ('summit', 'Summit · piolet', '2026-12',
  '<linearGradient id="a5" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#dfe9f4"/><stop offset="1" stop-color="#7e8b9b"/></linearGradient>',
  '<path d="M13.4 13.4 L26 26" fill="none" stroke="#2f3b48" stroke-width="3"'
  ' stroke-linecap="round"/>'
  '<path d="M2.2 2.2 C7.4 5.4 11 8.4 14.6 12.6 L11.4 15.4 C8.6 10.6 5.6 6.4 2.2 2.2 Z"'
  ' fill="url(#a5)" stroke="#2f3b48" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M13.2 11 L20.8 7.4 L22.6 11.6 L15.6 14.6 Z" fill="url(#a5)"'
  ' stroke="#2f3b48" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M25.4 24.2 L28 26.8" fill="none" stroke="#c8402f" stroke-width="2.4"'
  ' stroke-linecap="round"/>', None),

 ('bengal', 'Bengal · garra', '2027-01',
  '<linearGradient id="a6" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#fff6e6"/><stop offset="1" stop-color="#c2a06a"/></linearGradient>',
  '<path d="M2.2 2.2 C7.8 6.4 12.4 12.6 15 19.6 L10.6 20.6 C9 13.8 6.2 7.4 2.2 2.2 Z"'
  ' fill="#fff4e2" stroke="#3a2415" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M9.6 3.6 C13.6 8.4 16.6 14.4 18 21.2 L13.8 21.8 C13 15.2 11.4 9.2 9.6 3.6 Z"'
  ' fill="#f2e0c8" stroke="#3a2415" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M17.4 6.6 C20.2 11.4 21.8 16.6 22.2 22 L18 22.2 C18 16.8 17.8 11.6 17.4 6.6 Z"'
  ' fill="#e6d0b2" stroke="#3a2415" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M9.4 20.8 C9.4 25.6 21.6 25.6 21.6 20.8 C18 22 13 22 9.4 20.8 Z"'
  ' fill="#e0752f" stroke="#3a2415" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M12.6 24 L13.4 21.8 M16 24.6 L16 22.2 M19.2 23.8 L18.4 21.6"'
  ' fill="none" stroke="#8a4a1e" stroke-width=".9" stroke-linecap="round"/>', None),

 ('olympus', 'Olympus · lanza', '2027-02',
  '<linearGradient id="a7" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#ffe6a0"/><stop offset="1" stop-color="#b08a2e"/></linearGradient>',
  '<path d="M11.6 11.6 L26.6 26.6" fill="none" stroke="#8a6a3d" stroke-width="2.8"'
  ' stroke-linecap="round"/>'
  '<path d="M2.2 2.2 C6.6 4.4 10.4 8.2 12.6 12.6 L9.4 15.8 C6.4 12 3.6 7.4 2.2 2.2 Z"'
  ' fill="url(#a7)" stroke="#5c451c" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M4.6 4.6 L11.2 11.2" fill="none" stroke="#fff6d8" stroke-width="1"'
  ' stroke-linecap="round" opacity=".9"/>'
  '<path d="M14.6 18.4 C17 16 20 16.6 21 18.6 C18.6 19.6 16 19.6 14.6 18.4 Z"'
  ' fill="#4d8a52" stroke="#2c5730" stroke-width=".9"/>'
  '<path d="M18.4 22.2 C20.8 19.8 23.8 20.4 24.8 22.4 C22.4 23.4 19.8 23.4 18.4 22.2 Z"'
  ' fill="#4d8a52" stroke="#2c5730" stroke-width=".9"/>', None),

 ('quetzal', 'Quetzalcóatl · cuchillo', '2027-03',
  '<linearGradient id="a8" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#4a4560"/><stop offset=".5" stop-color="#1b1826"/>'
  '<stop offset="1" stop-color="#0b0a12"/></linearGradient>',
  '<path d="M2.2 2.2 L8.4 8 L6.6 10.2 L11 12.6 L9 15 L13.4 17 L16.4 14 L2.2 2.2 Z"'
  ' fill="url(#a8)" stroke="#5b5470" stroke-width="1" stroke-linejoin="round"/>'
  '<path d="M15 15.4 L21.8 22.2 L18 26 L11.2 19.2 Z" fill="#1f8f7a" stroke="#0c4a3f"'
  ' stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M17.4 17.8 L19.6 20 M15.4 19.8 L17.6 22" fill="none" stroke="#e8b93f"'
  ' stroke-width="1.2" stroke-linecap="round"/>'
  '<circle cx="24.4" cy="24.4" r="2.4" fill="#e8b93f" stroke="#8a6a1e" stroke-width=".9"/>',
  None),

 ('baseball', 'Baseball · bate', '2027-04',
  '<linearGradient id="a9" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#e8c78e"/><stop offset=".6" stop-color="#c79a52"/>'
  '<stop offset="1" stop-color="#8a6530"/></linearGradient>',
  '<path d="M2.6 2.6 C6.4 1.4 9.6 3 11 5.4 L21.6 16 L17.4 20.2 L6.8 9.6'
  ' C4.4 8.2 1.4 6.4 2.6 2.6 Z" fill="url(#a9)" stroke="#4e3717" stroke-width="1.05"'
  ' stroke-linejoin="round"/>'
  '<path d="M18.6 17.4 L25.2 24 L22.4 26.8 L15.8 20.2 Z" fill="#b8332e"'
  ' stroke="#5c1613" stroke-width="1"/>'
  '<path d="M20.6 18 L18.4 20.2 M22.6 20 L20.4 22.2" fill="none" stroke="#e8dcd2"'
  ' stroke-width=".9" opacity=".8"/>'
  '<circle cx="26.4" cy="26.4" r="2.3" fill="url(#a9)" stroke="#4e3717" stroke-width="1"/>',
  None),

 ('apiarist', 'Apiarist · ahumador', '2027-05',
  '<linearGradient id="a10" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#e8c76a"/><stop offset="1" stop-color="#9a6f22"/></linearGradient>',
  # pico + tapa cónica + cuerpo cilíndrico + fuelle: las cuatro piezas que
  # hacen que se lea AHUMADOR y no un adorno redondo
  '<path d="M2.2 2.2 L9 6 L6 9 Z" fill="#c9a24a" stroke="#4e3712"'
  ' stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M6.2 9.2 L9.2 6.2 L14.8 10.4 L10.4 14.8 Z" fill="url(#a10)"'
  ' stroke="#4e3712" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M10.8 15.2 L15.2 10.8 L22.4 18 C24.6 20.2 20.2 24.6 18 22.4 Z"'
  ' fill="url(#a10)" stroke="#4e3712" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M13.4 17.8 L17.8 13.4 M16 20.4 L20.4 16" fill="none" stroke="#5c4318"'
  ' stroke-width=".95" opacity=".75"/>'
  '<path d="M20.4 13.4 C24.8 11.6 28.2 15 26.4 19.4 C24 17.4 22.4 15.8 20.4 13.4 Z"'
  ' fill="#8a5a2a" stroke="#4e3712" stroke-width="1" stroke-linejoin="round"/>',
  # activo: sale el humo por el pico
  '<circle cx="6.4" cy="3.4" r="1.6" fill="#e8e2d4" opacity=".9"/>'
  '<circle cx="9.6" cy="1.8" r="1.2" fill="#e8e2d4" opacity=".75"/>'
  '<circle cx="3.4" cy="6.6" r="1.3" fill="#e8e2d4" opacity=".8"/>'),

 ('welder', 'Welder · soplete', '2027-06',
  '<linearGradient id="a11" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#c9d4de"/><stop offset="1" stop-color="#5e6975"/></linearGradient>',
  '<path d="M2.2 2.2 C6.6 4.2 9.4 7 11.4 11.4 L8.2 14.6 C6 10.2 3.8 6.4 2.2 2.2 Z"'
  ' fill="#7fc7ff" stroke="#2a6ea8" stroke-width="1" stroke-linejoin="round"/>'
  '<path d="M3.6 3.6 C6.4 5.4 8.2 7.4 9.6 10.2 L8 11.8 C6.4 8.6 5 6 3.6 3.6 Z"'
  ' fill="#f2fbff"/>'
  '<path d="M10.6 10.6 L16.6 16.6 L13.4 19.8 L7.4 13.8 Z" fill="url(#a11)"'
  ' stroke="#2f3b48" stroke-width="1.05" stroke-linejoin="round"/>'
  '<path d="M16 16 L26.4 26.4" fill="none" stroke="#33404e" stroke-width="3.4"'
  ' stroke-linecap="round"/>'
  '<path d="M19.4 19.4 L23.4 23.4" fill="none" stroke="#e0752f" stroke-width="2"'
  ' stroke-linecap="round"/>', None),

 ('zeppelin', 'Zeppelin · dirigible', '2027-07',
  '<linearGradient id="a12" x1="0" y1="0" x2="1" y2="1">'
  '<stop offset="0" stop-color="#e6c184"/><stop offset=".5" stop-color="#b8863f"/>'
  '<stop offset="1" stop-color="#7d5622"/></linearGradient>',
  '<path d="M2.4 2.4 C12.4 3.6 22.6 13.8 23.8 23.8 C13.8 22.6 3.6 12.4 2.4 2.4 Z"'
  ' fill="url(#a12)" stroke="#4a3315" stroke-width="1.1" stroke-linejoin="round"/>'
  '<path d="M6.4 4.6 C12.4 8.4 17.4 13.4 21.2 19.4" fill="none" stroke="#f2dcae"'
  ' stroke-width="1" stroke-linecap="round" opacity=".9"/>'
  '<path d="M22.4 22.4 L28.4 24.6 L26.6 26.4 L24.4 28.4 L22.2 22.2 Z" fill="#8a5f28"'
  ' stroke="#4a3315" stroke-width="1" stroke-linejoin="round"/>'
  '<path d="M13 18.6 L18.6 13 L20.6 15 L15 20.6 Z" fill="#5c4018" stroke="#33230f"'
  ' stroke-width=".9"/>', None),
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
        encendido = normal + (activo or CHISPAS)
        for cap, body in (('normal', normal), ('sobre un enlace', encendido)):
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
