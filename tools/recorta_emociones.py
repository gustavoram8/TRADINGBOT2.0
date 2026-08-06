# -*- coding: utf-8 -*-
"""Recorta los 12 rubíes (cubo + su expresión) de `tessera_emociones.png`.

La lámina es una rejilla de 4×3 paneles con MARCO NEGRO sobre fondo crema; cada
panel trae el teseracto con sus garabatos (estrellas, corazones, nube, zzz…) y
la etiqueta DEBAJO del marco. Aquí se detecta cada marco negro y se recorta su
INTERIOR: nos quedamos con el cubo y su expresión, sin el marco ni la etiqueta.

Solo necesita Pillow (ya instalado). Se corre EN EL VPS:

    cd /var/www/TRADINGBOT2.0
    git checkout origin/claude/gallant-volta-i7cqmf -- tools/recorta_emociones.py
    venv/bin/python3 tools/recorta_emociones.py

Deja en `scalpel/static/`:
  · `emo-<nombre>.png`  (los 12 rubíes recortados, servidos al navegador)
  · `_emo_contacto.png` (hoja de contacto para REVISAR el recorte)

Revisa:  https://tradeable.academy/static/_emo_contacto.png
"""
import os
import warnings

warnings.filterwarnings('ignore')
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(AQUI, '..', 'scalpel', 'static')
FUENTE = os.path.join(STATIC, 'tessera_emociones.png')

FILAS = [
    ['emocionado', 'alegre',   'triste',   'llorando'],
    ['sudando',    'enojado',  'molesto',  'pensando'],
    ['cansado',    'nervioso', 'asustado', 'sorprendido'],
]
COLS, NFIL = 4, 3

UMBRAL_OSCURO = 90    # gris < esto = trazo negro (marco / cubo / garabato)
INSET = 0.012         # meterse hacia dentro del marco (fracción del panel)


def _perfil_columnas(mask, W):
    """Media de oscuridad por columna (0..255), sin numpy."""
    return list(mask.resize((W, 1), Image.BOX).getdata())


def _perfil_filas(mask, H):
    return list(mask.resize((1, H), Image.BOX).getdata())


def _bandas(perfil, umbral):
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


def main():
    if not os.path.exists(FUENTE):
        print('✗ Falta scalpel/static/tessera_emociones.png')
        return 1
    im = Image.open(FUENTE).convert('RGB')
    W, H = im.size
    print('Lámina: %d×%d' % (W, H))
    gris = im.convert('L')
    # máscara de oscuridad: 255 donde hay trazo negro, 0 en el crema
    mask = gris.point(lambda p: 255 if p < UMBRAL_OSCURO else 0)

    # 1) barra de título: filas de arriba casi todas negras (>45%)
    fila = _perfil_filas(mask, H)
    top = 0
    while top < H and fila[top] > 115:   # 0.45*255
        top += 1
    top = min(top + 2, H - 1)

    # 2) columnas: sobre el área de paneles
    sub = mask.crop((0, top, W, H))
    col = _perfil_columnas(sub, W)
    cols = [b for b in _bandas(col, 13) if (b[1] - b[0]) > W * 0.04]   # 0.05*255
    cols = sorted(sorted(cols, key=lambda b: b[1] - b[0], reverse=True)[:COLS])

    # 3) filas: los paneles son bandas ALTAS; las etiquetas, finas
    filb = [(a + top, b + top) for (a, b) in _bandas(fila[top:], 10)]
    filas = sorted(sorted(filb, key=lambda b: b[1] - b[0], reverse=True)[:NFIL])

    if len(cols) != COLS or len(filas) != NFIL:
        print('⚠️  Detecté %d columnas / %d filas (esperaba %d×%d) — reparto '
              'uniforme de respaldo.' % (len(cols), len(filas), COLS, NFIL))
    if len(cols) != COLS:
        m = int(W * 0.02); cw = (W - 2 * m) / COLS
        cols = [(int(m + i * cw), int(m + (i + 1) * cw)) for i in range(COLS)]
    if len(filas) != NFIL:
        t = int(H * 0.11); rh = (H - t) / NFIL
        filas = [(int(t + i * rh), int(t + (i + 1) * rh)) for i in range(NFIL)]

    caras = []
    for f, (ry0, ry1) in enumerate(filas):
        for c, (cx0, cx1) in enumerate(cols):
            nombre = FILAS[f][c]
            iw = (cx1 - cx0) * INSET
            ih = (ry1 - ry0) * INSET
            cara = im.crop((int(cx0 + iw), int(ry0 + ih),
                            int(cx1 - iw), int(ry1 - ih)))
            cara.save(os.path.join(STATIC, 'emo-%s.png' % nombre))
            caras.append((nombre, cara))
    print('✓ 12 rubíes -> scalpel/static/emo-<nombre>.png')

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
