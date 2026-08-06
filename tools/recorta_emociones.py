# -*- coding: utf-8 -*-
"""Recorta las 12 caras del teseracto de `tessera_emociones.png`.

La lámina es una rejilla de 4 columnas × 3 filas. Cada celda trae la cara
arriba y su etiqueta abajo; nosotros nos quedamos SOLO con la cara.

Se corre EN EL VPS, donde la lámina ya vive:

    cd /var/www/TRADINGBOT2.0
    git pull origin claude/gallant-volta-i7cqmf
    venv/bin/python3 tools/recorta_emociones.py

Deja en `scalpel/static/`:
  · `emo-<nombre>.png`  (las 12 caras, servidas al navegador)
  · `_emo_contacto.png` (hoja de contacto para REVISAR el recorte)

Abre la hoja de contacto en el navegador para ver si el corte quedó
alineado:  https://tradeable.academy/static/_emo_contacto.png?pase=<tu-pase>
Si algo está corrido, avísame qué (p. ej. "corta la etiqueta de más" o
"queda un borde arriba") y ajusto UN número aquí; no hay que adivinar.
"""
import os

from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(AQUI, '..', 'scalpel', 'static')
FUENTE = os.path.join(STATIC, 'tessera_emociones.png')

# --- Rejilla (orden EXACTO de la lámina, de izquierda a derecha, arriba a abajo)
FILAS = [
    ['emocionado', 'alegre',   'triste',   'llorando'],
    ['sudando',    'enojado',  'molesto',  'pensando'],
    ['cansado',    'nervioso', 'asustado', 'sorprendido'],
]
COLS = 4
NFIL = 3

# --- Números que se pueden tocar si el recorte sale corrido (todo en fracciones
#     0..1 de la imagen, así funciona sea cual sea el tamaño real de la lámina).
BARRA_TITULO = 0.00   # ¿hay una franja de título arriba? fracción del alto total
MARGEN_ARRIBA = 0.02  # aire por encima de la primera fila de caras
MARGEN_ABAJO = 0.02   # aire por debajo de la última fila
MARGEN_LADO = 0.02    # aire a izquierda y derecha
ETIQUETA = 0.26       # cuánto del ALTO de cada celda es la etiqueta (se descarta)
RELLENO = 0.06        # recorte fino del borde de cada cara (contra líneas/marcos)


def _fuente_tipo(px):
    for ruta in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, px)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    if not os.path.exists(FUENTE):
        print('✗ No encuentro %s' % FUENTE)
        print('  La lámina tiene que estar en scalpel/static/tessera_emociones.png')
        return 1
    lam = Image.open(FUENTE).convert('RGBA')
    W, H = lam.size
    print('Lámina: %d×%d' % (W, H))

    top = int(H * (BARRA_TITULO + MARGEN_ARRIBA))
    bot = int(H * (1 - MARGEN_ABAJO))
    izq = int(W * MARGEN_LADO)
    der = int(W * (1 - MARGEN_LADO))
    ancho_util = der - izq
    alto_util = bot - top
    cw = ancho_util / COLS
    ch = alto_util / NFIL

    caras = []  # (nombre, imagen recortada)
    for f in range(NFIL):
        for c in range(COLS):
            nombre = FILAS[f][c]
            x0 = izq + c * cw
            y0 = top + f * ch
            # cara = celda menos la etiqueta de abajo, menos relleno de borde
            cx0 = int(x0 + cw * RELLENO)
            cx1 = int(x0 + cw * (1 - RELLENO))
            cy0 = int(y0 + ch * RELLENO)
            cy1 = int(y0 + ch * (1 - ETIQUETA))
            cara = lam.crop((cx0, cy0, cx1, cy1))
            cara.save(os.path.join(STATIC, 'emo-%s.png' % nombre))
            caras.append((nombre, cara))
    print('✓ 12 caras guardadas como scalpel/static/emo-<nombre>.png')

    # --- Hoja de contacto para revisar a ojo -------------------------------
    celda = 220
    etiqueta_h = 30
    hoja_w = COLS * celda
    hoja_h = NFIL * (celda + etiqueta_h)
    hoja = Image.new('RGBA', (hoja_w, hoja_h), (18, 20, 28, 255))
    dib = ImageDraw.Draw(hoja)
    tipo = _fuente_tipo(18)
    i = 0
    for f in range(NFIL):
        for c in range(COLS):
            nombre, cara = caras[i]
            i += 1
            miniatura = cara.copy()
            miniatura.thumbnail((celda - 16, celda - 16))
            px = c * celda + (celda - miniatura.width) // 2
            py = f * (celda + etiqueta_h) + (celda - miniatura.height) // 2
            hoja.alpha_composite(miniatura, (px, py))
            tx = c * celda + 8
            ty = f * (celda + etiqueta_h) + celda + 4
            dib.text((tx, ty), nombre, font=tipo, fill=(230, 200, 90, 255))
    salida = os.path.join(STATIC, '_emo_contacto.png')
    hoja.convert('RGB').save(salida)
    print('✓ Hoja de contacto: scalpel/static/_emo_contacto.png')
    print('  Ábrela en el navegador:')
    print('  https://tradeable.academy/static/_emo_contacto.png')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
