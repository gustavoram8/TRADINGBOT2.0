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
            'width="32" height="32"><defs>%s</defs>'
            '<g stroke-width="1.8" stroke-linejoin="round" '
            'stroke-linecap="round">%s</g></svg>' % (defs, body))


# El estado ACTIVO es el cuerpo normal + un extra encima (chispa, brillo,
# repintado de una pieza). Guardar solo el extra evita duplicar cada figura y
# obliga a que los dos estados compartan silueta, que es lo que hace que el
# hover se lea como "la misma herramienta, encendida".
CHISPAS = ('<circle cx="9.6" cy="4.6" r="1.3" fill="#fff3c4"/>'
           '<circle cx="5.2" cy="9.8" r="1" fill="#fff3c4" opacity=".85"/>')

# (slug, nombre, temporada, defs, cuerpo, extra del estado activo)
CURSORS = [
 ('chronicles', 'Chronicles · escudo', '2026-08', '',
  '<path d="M4.6 4 L27.4 4 L27.4 15.4 C27.4 22.4 22.4 27 16 29.4'
  ' C9.6 27 4.6 22.4 4.6 15.4 Z" fill="#4a5462" stroke="#171c23"'
  ' stroke-width="1.8" stroke-linejoin="round"/>'
  '<path d="M4.6 12.6 L27.4 12.6 L27.4 16 L4.6 16 Z" fill="#2f3640"/>'
  '<path d="M16 6.6 C21.4 12 20.4 17.6 16 21.6 C11.6 17.6 10.6 12 16 6.6 Z"'
  ' fill="#ff5a1e" stroke="#7a2708" stroke-width="1.3" stroke-linejoin="round"/>'
  '<path d="M16 11.6 C18.6 14.6 18.2 17 16 19 C13.8 17 13.4 14.6 16 11.6 Z"'
  ' fill="#ffb347"/>',
  '<circle cx="16" cy="13" r="7.6" fill="#ff5a1e" opacity=".3"/>'
  '<circle cx="9" cy="6.4" r="1.4" fill="#ffd08a"/>'),

 ('gridiron', 'American Football · balón', '2026-09', '',
  '<path d="M2.4 16 C5.8 9.4 10.6 6.2 16 6.2 C21.4 6.2 26.2 9.4 29.6 16'
  ' C26.2 22.6 21.4 25.8 16 25.8 C10.6 25.8 5.8 22.6 2.4 16 Z" fill="#7d3a17"'
  ' stroke="#2b1408" stroke-width="1.8" stroke-linejoin="round"/>'
  '<path d="M2.4 16 C3.4 14 4.6 12.2 6 10.8 C7 12.4 7.4 14.2 7.4 16'
  ' C7.4 17.8 7 19.6 6 21.2 C4.6 19.8 3.4 18 2.4 16 Z" fill="#f3ece0"'
  ' stroke="#2b1408" stroke-width="1.5" stroke-linejoin="round"/>'
  '<path d="M29.6 16 C28.6 14 27.4 12.2 26 10.8 C25 12.4 24.6 14.2 24.6 16'
  ' C24.6 17.8 25 19.6 26 21.2 C27.4 19.8 28.6 18 29.6 16 Z" fill="#f3ece0"'
  ' stroke="#2b1408" stroke-width="1.5" stroke-linejoin="round"/>'
  '<path d="M12.4 16 L19.6 16" fill="none" stroke="#f3ece0" stroke-width="2.4"'
  ' stroke-linecap="round"/>'
  '<path d="M13.6 13.8 L13.6 18.2 M16 13.4 L16 18.6 M18.4 13.8 L18.4 18.2"'
  ' fill="none" stroke="#f3ece0" stroke-width="1.6" stroke-linecap="round"/>', None),

 ('nile', 'Nile · pirámide', '2026-10', '',
  '<circle cx="25" cy="7.4" r="4" fill="#f2b33d" stroke="#8a5a12" stroke-width="1.4"/>'
  '<path d="M16 3 L29.4 26.6 L2.6 26.6 Z" fill="#e8c076" stroke="#5c421a"'
  ' stroke-width="1.8" stroke-linejoin="round"/>'
  '<path d="M16 3 L29.4 26.6 L16 26.6 Z" fill="#c39a48"/>'
  '<path d="M9.6 14.4 L22.4 14.4 M6.4 20.4 L25.6 20.4" fill="none"'
  ' stroke="#8a6a2a" stroke-width="1.3" opacity=".8"/>', None),

 ('colosseum', 'Colosseum · casco', '2026-11', '',
  '<path d="M6 13 C6 6.4 11.4 2.6 16 2.6 C20.6 2.6 26 6.4 26 13 L26 19'
  ' C26 24 22 27.4 16 27.4 C10 27.4 6 24 6 19 Z" fill="#c9a227"'
  ' stroke="#2a1f08" stroke-width="1.8" stroke-linejoin="round"/>'
  '<path d="M6 13 C10 15 22 15 26 13 L26 15.4 C22 17.4 10 17.4 6 15.4 Z"'
  ' fill="#8a6a14" stroke="#2a1f08" stroke-width="1.5"/>'
  '<path d="M14.6 15.6 L17.4 15.6 L17.4 27 L14.6 27 Z" fill="#2a1f08"/>'
  '<path d="M9.4 19.4 L12.6 19.4 L12.6 24.6 L9.4 24.6 Z" fill="#2a1f08"/>'
  '<path d="M19.4 19.4 L22.6 19.4 L22.6 24.6 L19.4 24.6 Z" fill="#2a1f08"/>'
  '<path d="M13 2.8 C13 0.6 19 0.6 19 2.8 L19 6 C19 7.4 13 7.4 13 6 Z"'
  ' fill="#b8332e" stroke="#2a1f08" stroke-width="1.6" stroke-linejoin="round"/>',
  None),

 ('summit', 'Summit · bota', '2026-12', '',
  '<path d="M4.6 3 L13.4 3 C14.6 3 15.4 3.8 15.4 5 L15.4 13.4'
  ' C15.4 15.4 17 16.2 19.4 17 L25.6 19.2 C27.4 19.8 28 21 28 22.6 L28 24.6'
  ' L4.6 24.6 Z" fill="#c8402f" stroke="#3a1108" stroke-width="1.8"'
  ' stroke-linejoin="round"/>'
  '<path d="M4.6 19.6 L28 19.6 L28 24.6 L4.6 24.6 Z" fill="#2f3b48"'
  ' stroke="#141c26" stroke-width="1.6" stroke-linejoin="round"/>'
  '<path d="M6.6 24.6 L6.6 28 M11.4 24.6 L11.4 28 M16.2 24.6 L16.2 28'
  ' M21 24.6 L21 28 M25.8 24.6 L25.8 28" fill="none" stroke="#8d99a8"'
  ' stroke-width="2" stroke-linecap="round"/>'
  '<path d="M6.6 6.6 L13.4 6.6 M6.6 10.4 L13.4 10.4 M6.6 14.2 L13.4 14.2"'
  ' fill="none" stroke="#f2e2d8" stroke-width="1.4" stroke-linecap="round"/>',
  None),

 ('bengal', 'Bengal · huella', '2027-01', '',
  '<path d="M16 15 C21.6 15 25.4 18.4 25.4 22 C25.4 25.8 21.6 28.4 16 28.4'
  ' C10.4 28.4 6.6 25.8 6.6 22 C6.6 18.4 10.4 15 16 15 Z" fill="#e0752f"'
  ' stroke="#3a2415" stroke-width="1.8" stroke-linejoin="round"/>'
  '<ellipse cx="8.2" cy="13.4" rx="3" ry="3.8" fill="#e0752f" stroke="#3a2415"'
  ' stroke-width="1.7"/>'
  '<ellipse cx="13.4" cy="8.4" rx="3.1" ry="4" fill="#e0752f" stroke="#3a2415"'
  ' stroke-width="1.7"/>'
  '<ellipse cx="19.4" cy="8.4" rx="3.1" ry="4" fill="#e0752f" stroke="#3a2415"'
  ' stroke-width="1.7"/>'
  '<ellipse cx="24.6" cy="13.4" rx="3" ry="3.8" fill="#e0752f" stroke="#3a2415"'
  ' stroke-width="1.7"/>', None),

 ('olympus', 'Olympus · ánfora', '2027-02', '',
  '<path d="M11.6 3.2 L20.4 3.2 L20.4 5.8 L18.6 5.8 L18.6 9.4 L13.4 9.4'
  ' L13.4 5.8 L11.6 5.8 Z" fill="#e8dcc4" stroke="#3a2f1c" stroke-width="1.6"'
  ' stroke-linejoin="round"/>'
  '<path d="M13.4 9.4 C7.6 11.6 6.4 17 8.4 21.6 C10 25.4 22 25.4 23.6 21.6'
  ' C25.6 17 24.4 11.6 18.6 9.4 Z" fill="#c96a3c" stroke="#4a1f0c"'
  ' stroke-width="1.8" stroke-linejoin="round"/>'
  '<path d="M9 13.4 C5.6 12.6 5 17 8.2 18.6 M23 13.4 C26.4 12.6 27 17 23.8 18.6"'
  ' fill="none" stroke="#4a1f0c" stroke-width="1.8" stroke-linecap="round"/>'
  '<path d="M7.4 14.6 L24.6 14.6 L24.6 18.6 L7.4 18.6 Z" fill="#2b1a12"/>'
  '<circle cx="12" cy="16.6" r="1.3" fill="#e8dcc4"/>'
  '<circle cx="16" cy="16.6" r="1.3" fill="#e8dcc4"/>'
  '<circle cx="20" cy="16.6" r="1.3" fill="#e8dcc4"/>'
  '<path d="M12.6 25.2 L19.4 25.2 L18.6 28.4 L13.4 28.4 Z" fill="#c96a3c"'
  ' stroke="#4a1f0c" stroke-width="1.6" stroke-linejoin="round"/>', None),

 ('quetzal', 'Quetzalcóatl · disco solar', '2027-03', '',
  '<path d="M16 1.4 L18.8 5.6 L23.6 4 L23.6 9 L28.4 10.4 L25.4 14.4 L28.4 18.4'
  ' L23.6 19.8 L23.6 24.8 L18.8 23.2 L16 27.4 L13.2 23.2 L8.4 24.8 L8.4 19.8'
  ' L3.6 18.4 L6.6 14.4 L3.6 10.4 L8.4 9 L8.4 4 L13.2 5.6 Z" fill="#e8b93f"'
  ' stroke="#7a4a10" stroke-width="1.5" stroke-linejoin="round"/>'
  '<circle cx="16" cy="14.4" r="8.2" fill="#1f8f7a" stroke="#0c4a3f" stroke-width="1.7"/>'
  '<path d="M12.4 10.8 L19.6 10.8 L19.6 18 L12.4 18 Z" fill="#e8b93f"'
  ' stroke="#7a4a10" stroke-width="1.3"/>'
  '<circle cx="16" cy="14.4" r="2" fill="#b8332e"/>', None),

 ('baseball', 'Baseball · pelota', '2027-04', '',
  '<circle cx="16" cy="16" r="12.4" fill="#f4efe6" stroke="#3a3028" stroke-width="1.8"/>'
  '<path d="M8.6 6.6 C12 10.6 12 21.4 8.6 25.4" fill="none" stroke="#c8402f"'
  ' stroke-width="1.8" stroke-linecap="round"/>'
  '<path d="M23.4 6.6 C20 10.6 20 21.4 23.4 25.4" fill="none" stroke="#c8402f"'
  ' stroke-width="1.8" stroke-linecap="round"/>'
  '<path d="M9.4 11 L12 12 M9.2 15 L11.8 15.4 M9.4 19.4 L12 18.6'
  ' M22.6 11 L20 12 M22.8 15 L20.2 15.4 M22.6 19.4 L20 18.6" fill="none"'
  ' stroke="#c8402f" stroke-width="1.4" stroke-linecap="round"/>', None),

 ('apiarist', 'Apiarist · tarro de miel', '2027-05', '',
  '<path d="M8.6 11.4 L23.4 11.4 L24.6 24.6 C24.8 26.6 23.4 28 21.6 28'
  ' L10.4 28 C8.6 28 7.2 26.6 7.4 24.6 Z" fill="#e8a92c" stroke="#4a2f06"'
  ' stroke-width="1.8" stroke-linejoin="round"/>'
  '<path d="M7.4 7.4 L24.6 7.4 L24.6 11.4 L7.4 11.4 Z" fill="#c98a1c"'
  ' stroke="#4a2f06" stroke-width="1.8" stroke-linejoin="round"/>'
  '<path d="M9.6 16.6 C13 19 19 19 22.4 16.6 L22.9 22 C19 24.4 13 24.4 9.1 22 Z"'
  ' fill="#fff0c2" stroke="#4a2f06" stroke-width="1.5" stroke-linejoin="round"/>'
  '<path d="M2.6 2.6 L9 9" fill="none" stroke="#8a5a1a" stroke-width="2.8"'
  ' stroke-linecap="round"/>'
  '<circle cx="10.4" cy="10.4" r="2.6" fill="#8a5a1a" stroke="#4a2f06" stroke-width="1.4"/>',
  None),

 ('welder', 'Welder · careta', '2027-06', '',
  '<path d="M6 4.6 L26 4.6 C27.2 4.6 27.8 5.4 27.8 6.6 L27.8 18.6'
  ' C27.8 24.6 23.4 28.6 16 28.6 C8.6 28.6 4.2 24.6 4.2 18.6 L4.2 6.6'
  ' C4.2 5.4 4.8 4.6 6 4.6 Z" fill="#33404e" stroke="#111820" stroke-width="1.8"'
  ' stroke-linejoin="round"/>'
  '<path d="M8.4 9.4 L23.6 9.4 L23.6 15.4 L8.4 15.4 Z" fill="#7fc7ff"'
  ' stroke="#111820" stroke-width="1.6" stroke-linejoin="round"/>'
  '<path d="M10.4 14 L14 10.8 M15.4 14 L19 10.8" fill="none" stroke="#eaf7ff"'
  ' stroke-width="1.3" stroke-linecap="round" opacity=".9"/>'
  '<path d="M4.2 19.6 L27.8 19.6" fill="none" stroke="#1d2731" stroke-width="1.6"/>'
  '<path d="M11 23 L21 23" fill="none" stroke="#e0752f" stroke-width="2"'
  ' stroke-linecap="round"/>', None),

 ('zeppelin', 'Zeppelin · dirigible', '2027-07', '',
  '<path d="M2.2 13.6 C4.2 9.6 9.6 6.8 16 6.8 C22.4 6.8 27.8 9.6 29.8 13.6'
  ' C27.8 17.6 22.4 20.4 16 20.4 C9.6 20.4 4.2 17.6 2.2 13.6 Z" fill="#b8863f"'
  ' stroke="#4a3315" stroke-width="1.8" stroke-linejoin="round"/>'
  '<path d="M6.6 9.6 C11.6 8.2 20.4 8.2 25.4 9.6" fill="none" stroke="#f2dcae"'
  ' stroke-width="1.4" stroke-linecap="round" opacity=".9"/>'
  '<path d="M2.2 13.6 L29.8 13.6" fill="none" stroke="#7d5622" stroke-width="1.3"'
  ' opacity=".8"/>'
  '<path d="M27 13.6 L27 6.6 L29.4 6.6 L29.4 13.6 Z" fill="#8a5f28"'
  ' stroke="#4a3315" stroke-width="1.4" stroke-linejoin="round"/>'
  '<path d="M27 13.6 L27 20.6 L29.4 20.6 L29.4 13.6 Z" fill="#8a5f28"'
  ' stroke="#4a3315" stroke-width="1.4" stroke-linejoin="round"/>'
  '<path d="M11.4 20 L20.6 20 L20.6 24.6 C20.6 26 11.4 26 11.4 24.6 Z"'
  ' fill="#5c4018" stroke="#33230f" stroke-width="1.7" stroke-linejoin="round"/>'
  '<path d="M13.6 22.4 L14.8 22.4 M15.4 22.4 L16.6 22.4 M17.2 22.4 L18.4 22.4"'
  ' fill="none" stroke="#ffd98f" stroke-width="1.6" stroke-linecap="round"/>', None),

 # ══ LIBRES DE RULETA (2 por mes) ══════════════════════════════════════════
 ('candle', 'Vela alcista', 'libre', '',
  '<path d="M16 2 L16 9 M16 23 L16 30" fill="none" stroke="#06341f"/>'
  '<path d="M9.6 9 L22.4 9 L22.4 23 L9.6 23 Z" fill="#39d98a" stroke="#06341f"/>', None),

 ('coin', 'Moneda', 'libre', '',
  '<circle cx="16" cy="16" r="12.6" fill="#e8b93f" stroke="#7a4a10"/>'
  '<circle cx="16" cy="16" r="8.4" fill="none" stroke="#7a4a10" stroke-width="1.4"/>'
  '<path d="M16 10.4 L16 21.6 M12.8 13 L19.2 13 M12.8 19 L19.2 19" fill="none"'
  ' stroke="#7a4a10" stroke-width="1.6"/>', None),

 ('chart', 'Barras', 'libre', '',
  '<path d="M4.4 18 L10 18 L10 27.6 L4.4 27.6 Z" fill="#5fa8e8" stroke="#123a5c"/>'
  '<path d="M13.2 11 L18.8 11 L18.8 27.6 L13.2 27.6 Z" fill="#39d98a" stroke="#06341f"/>'
  '<path d="M22 5 L27.6 5 L27.6 27.6 L22 27.6 Z" fill="#e8b93f" stroke="#7a4a10"/>', None),

 ('bell', 'Campana', 'libre', '',
  '<path d="M16 3.4 C21.6 3.4 24.4 8 24.4 13.4 L24.4 21.6 L7.6 21.6 L7.6 13.4'
  ' C7.6 8 10.4 3.4 16 3.4 Z" fill="#e8b93f" stroke="#7a4a10"/>'
  '<path d="M5.4 21.6 L26.6 21.6 L26.6 24.6 L5.4 24.6 Z" fill="#c99a1c" stroke="#7a4a10"/>'
  '<circle cx="16" cy="27" r="2.6" fill="#c99a1c" stroke="#7a4a10"/>', None),

 ('diamond', 'Diamante', 'libre', '',
  '<path d="M8 5.4 L24 5.4 L29 12.4 L16 28.6 L3 12.4 Z" fill="#7fc7ff" stroke="#12446e"/>'
  '<path d="M8 5.4 L11.4 12.4 L3 12.4 Z M24 5.4 L20.6 12.4 L29 12.4 Z"'
  ' fill="#bfe4ff" stroke="#12446e" stroke-width="1.3"/>'
  '<path d="M11.4 12.4 L20.6 12.4 L16 28.6 Z" fill="#a8d8ff" stroke="#12446e"'
  ' stroke-width="1.3"/>', None),

 ('rocket', 'Cohete', 'libre', '',
  '<path d="M16 2.4 C20.4 6.4 22.4 12 22.4 17.6 L22.4 22 L9.6 22 L9.6 17.6'
  ' C9.6 12 11.6 6.4 16 2.4 Z" fill="#e8eef6" stroke="#2a3038"/>'
  '<path d="M9.6 15 L4.6 21.6 L9.6 21.6 Z M22.4 15 L27.4 21.6 L22.4 21.6 Z"'
  ' fill="#c8402f" stroke="#5c1613"/>'
  '<circle cx="16" cy="11.4" r="3.2" fill="#5fa8e8" stroke="#2a3038" stroke-width="1.5"/>'
  '<path d="M12.6 22 C13.6 26.6 18.4 26.6 19.4 22 Z" fill="#f2a03d" stroke="#a8541a"/>',
  None),

 ('target', 'Diana', 'libre', '',
  '<circle cx="16" cy="16" r="12.6" fill="#f4efe6" stroke="#3a3028"/>'
  '<circle cx="16" cy="16" r="8.4" fill="#c8402f" stroke="#5c1613" stroke-width="1.5"/>'
  '<circle cx="16" cy="16" r="4.2" fill="#f4efe6" stroke="#5c1613" stroke-width="1.5"/>'
  '<circle cx="16" cy="16" r="1.6" fill="#c8402f"/>', None),

 ('clock', 'Reloj', 'libre', '',
  '<circle cx="16" cy="17" r="12" fill="#f2ead6" stroke="#3a2f1c"/>'
  '<path d="M11.4 3.4 L20.6 3.4 M16 3.4 L16 5.4" fill="none" stroke="#3a2f1c"/>'
  '<path d="M16 17 L16 10.4 M16 17 L21 20" fill="none" stroke="#2a2114" stroke-width="2.2"/>'
  '<circle cx="16" cy="17" r="1.5" fill="#c8402f"/>', None),

 ('key', 'Llave', 'libre', '',
  '<circle cx="10" cy="10" r="6.6" fill="#e8b93f" stroke="#7a4a10"/>'
  '<circle cx="10" cy="10" r="2.4" fill="none" stroke="#7a4a10" stroke-width="1.5"/>'
  '<path d="M13.6 14.4 L26 26.8" fill="none" stroke="#e8b93f" stroke-width="4.4"/>'
  '<path d="M13.6 14.4 L26 26.8" fill="none" stroke="#7a4a10" stroke-width="1.4"/>'
  '<path d="M20 21 L23.4 17.6 M23 24 L26.4 20.6" fill="none" stroke="#e8b93f"'
  ' stroke-width="3.6"/>', None),

 ('lock', 'Candado', 'libre', '',
  '<path d="M10.4 13.4 L10.4 9.4 C10.4 5.6 21.6 5.6 21.6 9.4 L21.6 13.4"'
  ' fill="none" stroke="#8d99a8" stroke-width="3.4"/>'
  '<path d="M6.6 13.4 L25.4 13.4 C26.6 13.4 27.4 14.2 27.4 15.4 L27.4 26'
  ' C27.4 27.2 26.6 28 25.4 28 L6.6 28 C5.4 28 4.6 27.2 4.6 26 L4.6 15.4'
  ' C4.6 14.2 5.4 13.4 6.6 13.4 Z" fill="#e8b93f" stroke="#7a4a10"/>'
  '<circle cx="16" cy="19.4" r="2.6" fill="#7a4a10"/>'
  '<path d="M16 21.4 L16 24.4" fill="none" stroke="#7a4a10" stroke-width="2.2"/>', None),

 ('crown', 'Corona', 'libre', '',
  '<path d="M4 22 L4 8.4 L10.6 14.4 L16 5.4 L21.4 14.4 L28 8.4 L28 22 Z"'
  ' fill="#e8b93f" stroke="#7a4a10"/>'
  '<path d="M4 22 L28 22 L28 26.6 L4 26.6 Z" fill="#c99a1c" stroke="#7a4a10"/>'
  '<circle cx="16" cy="17.6" r="1.8" fill="#c8402f"/>', None),

 ('anchor', 'Ancla', 'libre', '',
  '<circle cx="16" cy="5.6" r="3.4" fill="none" stroke="#2f3b48" stroke-width="2.4"/>'
  '<path d="M16 9 L16 27.4" fill="none" stroke="#2f3b48" stroke-width="3"/>'
  '<path d="M9.4 12.4 L22.6 12.4" fill="none" stroke="#2f3b48" stroke-width="2.6"/>'
  '<path d="M5 18.4 C5 25 10.6 28.6 16 28.6 C21.4 28.6 27 25 27 18.4"'
  ' fill="none" stroke="#2f3b48" stroke-width="3"/>', None),

 ('compass', 'Brújula', 'libre', '',
  '<circle cx="16" cy="16" r="12.6" fill="#e8dcc4" stroke="#3a2f1c"/>'
  '<path d="M22 10 L18 18 L10 22 L14 14 Z" fill="#c8402f" stroke="#5c1613"'
  ' stroke-width="1.4"/>'
  '<circle cx="16" cy="16" r="1.5" fill="#3a2f1c"/>', None),

 ('hourglass', 'Reloj de arena', 'libre', '',
  '<path d="M6.6 3.4 L25.4 3.4 M6.6 28.6 L25.4 28.6" fill="none" stroke="#6b4a24"'
  ' stroke-width="2.6"/>'
  '<path d="M9.4 3.4 L22.6 3.4 L16 16 L22.6 28.6 L9.4 28.6 L16 16 Z"'
  ' fill="#f2ead6" stroke="#6b4a24"/>'
  '<path d="M11.4 6 L20.6 6 L16 14.6 Z" fill="#e8b93f"/>'
  '<path d="M12.6 26 L19.4 26 L16 20 Z" fill="#e8b93f"/>', None),

 ('bulb', 'Bombilla', 'libre', '',
  '<path d="M16 2.6 C22 2.6 26 7 26 12.4 C26 16.4 23.4 18.6 22 21.4 L10 21.4'
  ' C8.6 18.6 6 16.4 6 12.4 C6 7 10 2.6 16 2.6 Z" fill="#ffe066" stroke="#8a6a14"/>'
  '<path d="M10.6 22.6 L21.4 22.6 M11.4 26 L20.6 26" fill="none" stroke="#8d99a8"'
  ' stroke-width="2.6"/>'
  '<path d="M13.4 29 L18.6 29" fill="none" stroke="#8d99a8" stroke-width="2.4"/>', None),

 ('flame', 'Llama', 'libre', '',
  '<path d="M16 2 C23.4 9.4 25.4 16 25.4 20 C25.4 25.4 21.4 29.4 16 29.4'
  ' C10.6 29.4 6.6 25.4 6.6 20 C6.6 16 8.6 9.4 16 2 Z" fill="#ff5a1e"'
  ' stroke="#7a2708"/>'
  '<path d="M16 13.4 C19.4 17.4 20.6 20.4 20.6 22.4 C20.6 25 18.6 26.6 16 26.6'
  ' C13.4 26.6 11.4 25 11.4 22.4 C11.4 20.4 12.6 17.4 16 13.4 Z" fill="#ffd76a"/>',
  None),

 ('star', 'Estrella', 'libre', '',
  '<path d="M16 2 L20.2 11.4 L30.4 12.6 L22.8 19.4 L24.8 29.4 L16 24.4'
  ' L7.2 29.4 L9.2 19.4 L1.6 12.6 L11.8 11.4 Z" fill="#ffd76a" stroke="#8a6a14"/>',
  None),

 ('dice', 'Dado', 'libre', '',
  '<path d="M6 6 L26 6 C27.2 6 28 6.8 28 8 L28 26 C28 27.2 27.2 28 26 28'
  ' L6 28 C4.8 28 4 27.2 4 26 L4 8 C4 6.8 4.8 6 6 6 Z" fill="#f4efe6"'
  ' stroke="#3a3028"/>'
  '<circle cx="10.4" cy="12.4" r="2.2" fill="#3a3028"/>'
  '<circle cx="21.6" cy="12.4" r="2.2" fill="#3a3028"/>'
  '<circle cx="16" cy="17" r="2.2" fill="#c8402f"/>'
  '<circle cx="10.4" cy="21.6" r="2.2" fill="#3a3028"/>'
  '<circle cx="21.6" cy="21.6" r="2.2" fill="#3a3028"/>', None),

 ('magnet', 'Imán', 'libre', '',
  '<path d="M6.6 24 L6.6 14 C6.6 8.6 11 4.6 16 4.6 C21 4.6 25.4 8.6 25.4 14'
  ' L25.4 24" fill="none" stroke="#8d99a8" stroke-width="6.6"/>'
  '<path d="M6.6 24 L6.6 14 C6.6 8.6 11 4.6 16 4.6 C21 4.6 25.4 8.6 25.4 14'
  ' L25.4 24" fill="none" stroke="#2f3b48" stroke-width="1.6"/>'
  '<path d="M3.4 24 L10 24 L10 28.6 L3.4 28.6 Z" fill="#c8402f" stroke="#5c1613"/>'
  '<path d="M22 24 L28.6 24 L28.6 28.6 L22 28.6 Z" fill="#5fa8e8" stroke="#123a5c"/>',
  None),

 ('umbrella', 'Paraguas', 'libre', '',
  '<path d="M2.6 16.4 C2.6 8.6 8.6 3.4 16 3.4 C23.4 3.4 29.4 8.6 29.4 16.4 Z"'
  ' fill="#c8402f" stroke="#5c1613"/>'
  '<path d="M10.4 16.4 C10.4 9.6 12.6 3.4 16 3.4 C19.4 3.4 21.6 9.6 21.6 16.4"'
  ' fill="none" stroke="#5c1613" stroke-width="1.4"/>'
  '<path d="M16 16.4 L16 25 C16 28.4 21 28.4 21 25" fill="none" stroke="#6b4a24"'
  ' stroke-width="2.6"/>', None),

 ('mug', 'Taza', 'libre', '',
  '<path d="M5.4 10.6 L21.4 10.6 L21.4 23 C21.4 26 19 28 16 28 L10.8 28'
  ' C7.8 28 5.4 26 5.4 23 Z" fill="#f4efe6" stroke="#3a3028"/>'
  '<path d="M21.4 13.4 C26.6 13.4 26.6 21.4 21.4 21.4" fill="none" stroke="#3a3028"'
  ' stroke-width="2.4"/>'
  '<path d="M5.4 14.6 L21.4 14.6" fill="none" stroke="#c8402f" stroke-width="2.4"/>'
  '<path d="M10 6.6 C10 4.6 12 4.6 12 2.6 M16 6.6 C16 4.6 18 4.6 18 2.6"'
  ' fill="none" stroke="#b8c2cc" stroke-width="1.6"/>', None),

 ('cactus', 'Cactus', 'libre', '',
  '<path d="M13 6 C13 3.4 19 3.4 19 6 L19 24 L13 24 Z" fill="#4d8a3d"'
  ' stroke="#22431a"/>'
  '<path d="M13 12.4 L9 12.4 C6.6 12.4 6.6 8.4 9 8.4 C10.4 8.4 10.4 10 10.4 11"'
  ' fill="none" stroke="#4d8a3d" stroke-width="4"/>'
  '<path d="M19 16 L23 16 C25.4 16 25.4 11.4 23 11.4 C21.6 11.4 21.6 13 21.6 14"'
  ' fill="none" stroke="#4d8a3d" stroke-width="4"/>'
  '<path d="M8.4 24 L23.6 24 L22.4 28.6 L9.6 28.6 Z" fill="#c96a3c" stroke="#5c2b12"/>',
  None),

 ('balloon', 'Globo', 'libre', '',
  '<path d="M16 2.6 C21.6 2.6 25.4 7 25.4 12.4 C25.4 17.6 20.4 21.4 16 23.4'
  ' C11.6 21.4 6.6 17.6 6.6 12.4 C6.6 7 10.4 2.6 16 2.6 Z" fill="#e8547a"'
  ' stroke="#7a1f38"/>'
  '<path d="M13.6 23.4 L18.4 23.4 L16 26 Z" fill="#e8547a" stroke="#7a1f38"'
  ' stroke-width="1.4"/>'
  '<path d="M16 26 C13.4 28 18.6 28.6 16 30.4" fill="none" stroke="#7a1f38"'
  ' stroke-width="1.4"/>', None),

 ('moon', 'Luna', 'libre', '',
  '<path d="M20 2.6 C13 4.4 8 10.6 8 18 C8 21.6 9.2 25 11.4 27.6'
  ' C5.4 24.4 1.6 18 1.6 11.4 C1.6 5.4 9.4 0.6 20 2.6 Z" fill="#0000" opacity="0"/>'
  '<path d="M24.6 20.6 C22.6 21.6 20.4 22.2 18 22.2 C10.6 22.2 4.6 16.2 4.6 8.8'
  ' C4.6 6.4 5.2 4.2 6.2 2.2 C-0.4 6 -0.4 24.6 10.4 29 C18.6 32.4 25.4 27.4'
  ' 24.6 20.6 Z" fill="#ffe9a8" stroke="#8a6a14" transform="translate(4,0)"/>',
  None),
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
