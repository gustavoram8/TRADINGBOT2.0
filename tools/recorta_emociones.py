# -*- coding: utf-8 -*-
"""Recorta los 12 rubíes (cubo + su expresión) de `tessera_emociones.png`.

La lámina es una rejilla de 4×3 paneles con MARCO NEGRO sobre fondo crema; cada
panel trae el teseracto con sus garabatos (estrellas, corazones, nube, zzz…) y
la etiqueta DEBAJO del marco. Aquí se detecta cada marco negro y se recorta su
INTERIOR: nos quedamos con el cubo y su expresión, sin el marco ni la etiqueta.

Se corre EN EL VPS, donde la lámina ya vive:

    cd /var/www/TRADINGBOT2.0
    git checkout origin/claude/gallant-volta-i7cqmf -- tools/recorta_emociones.py
    venv/bin/python3 tools/recorta_emociones.py

Deja en `scalpel/static/`:
  · `emo-<nombre>.png`  (los 12 rubíes recortados, servidos al navegador)
  · `_emo_contacto.png` (hoja de contacto para REVISAR el recorte)

Revisa:  https://tradeable.academy/static/_emo_contacto.png
"""
import os

try:
    import numpy as np
except ImportError:
    raise SystemExit('Falta numpy:  venv/bin/pip install numpy')
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(AQUI, '..', 'scalpel', 'static')
FUENTE = os.path.join(STATIC, 'tessera_emociones.png')

# Orden EXACTO de la lámina (izq→der, arriba→abajo)
FILAS = [
    ['emocionado', 'alegre',   'triste',   'llorando'],
    ['sudando',    'enojado',  'molesto',  'pensando'],
    ['cansado',    'nervioso', 'asustado', 'sorprendido'],
]
COLS, NFIL = 4, 3

UMBRAL_OSCURO = 90    # gris < esto = trazo negro del marco / cubo / garabato
INSET = 0.012         # cuánto meterse hacia dentro del marco (fracción del panel)


def _bandas(perfil, umbral):
    """Runs contiguos de índices donde perfil>umbral -> [(ini,fin),...]."""
    bandas, i, n = [], 0, len(perfil)
    while i < n:
        if perfil[i] > umbral:
            j = i
            while j < n and perfil[j] > umbral:
                j += 1
            bandas.append((i, j))
            i = j
        else:
            i += 1
    return bandas


def _fuente(px):
    for r in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(r):
            try:
                return ImageFont.truetype(r, px)
            except Exception:
                pass
    return ImageFont.load_default()


def detectar_paneles(dark, H, W):
    """Devuelve (columnas, filas) como listas de (ini,fin) de los marcos."""
    # 1) barra de título: filas iniciales casi todas negras (ancho completo)
    frac_fila = dark.mean(axis=1)
    top = 0
    while top < H and frac_fila[top] > 0.45:
        top += 1
    top = min(top + 2, H - 1)

    # 2) columnas: sobre el área de paneles, columnas con trazo (marco/cubo)
    col = dark[top:, :].mean(axis=0)
    cols = _bandas(col, 0.05)
    cols = [b for b in cols if (b[1] - b[0]) > W * 0.04]
    cols = sorted(sorted(cols, key=lambda b: b[1] - b[0], reverse=True)[:COLS])

    # 3) filas: los paneles son bandas ALTAS; las etiquetas, bandas finas
    fila = dark[top:, :].mean(axis=1)
    filas = _bandas(fila, 0.04)
    filas = [(a + top, b + top) for (a, b) in filas]
    filas = sorted(sorted(filas, key=lambda b: b[1] - b[0], reverse=True)[:NFIL])
    return cols, filas


def main():
    if not os.path.exists(FUENTE):
        print('✗ Falta scalpel/static/tessera_emociones.png')
        return 1
    im = Image.open(FUENTE).convert('RGB')
    W, H = im.size
    arr = np.asarray(im).astype(int)
    gray = arr.mean(axis=2)
    dark = gray < UMBRAL_OSCURO
    print('Lámina: %d×%d' % (W, H))

    cols, filas = detectar_paneles(dark, H, W)
    if len(cols) != COLS or len(filas) != NFIL:
        print('⚠️  Detecté %d columnas y %d filas (esperaba %d×%d).'
              % (len(cols), len(filas), COLS, NFIL))
        print('   Mándame la hoja de contacto y ajusto los umbrales.')
    # completa por si faltara alguna banda (reparto uniforme como red de seguridad)
    if len(cols) != COLS:
        m = int(W * 0.02)
        cw = (W - 2 * m) / COLS
        cols = [(int(m + i * cw), int(m + (i + 1) * cw)) for i in range(COLS)]
    if len(filas) != NFIL:
        t = int(H * 0.11)
        rh = (H - t) / NFIL
        filas = [(int(t + i * rh), int(t + (i + 1) * rh)) for i in range(NFIL)]

    caras = []
    for f, (ry0, ry1) in enumerate(filas):
        for c, (cx0, cx1) in enumerate(cols):
            nombre = FILAS[f][c]
            iw = (cx1 - cx0) * INSET
            ih = (ry1 - ry0) * INSET
            x0, x1 = int(cx0 + iw), int(cx1 - iw)
            y0, y1 = int(ry0 + ih), int(ry1 - ih)
            cara = im.crop((x0, y0, x1, y1))
            cara.save(os.path.join(STATIC, 'emo-%s.png' % nombre))
            caras.append((nombre, cara))
    print('✓ 12 rubíes -> scalpel/static/emo-<nombre>.png')

    # hoja de contacto
    celda, eti = 300, 34
    hoja = Image.new('RGB', (COLS * celda, NFIL * (celda + eti)), (70, 72, 80))
    dib = ImageDraw.Draw(hoja)
    tipo = _fuente(20)
    for i, (nombre, cara) in enumerate(caras):
        f, c = divmod(i, COLS)
        mini = cara.copy()
        mini.thumbnail((celda - 12, celda - 12))
        px = c * celda + (celda - mini.width) // 2
        py = f * (celda + eti) + (celda - mini.height) // 2
        hoja.paste(mini, (px, py))
        dib.text((c * celda + 8, f * (celda + eti) + celda + 6), nombre,
                 font=tipo, fill=(240, 215, 110))
    hoja.save(os.path.join(STATIC, '_emo_contacto.png'))
    print('✓ Hoja de contacto -> scalpel/static/_emo_contacto.png')
    print('  https://tradeable.academy/static/_emo_contacto.png')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
