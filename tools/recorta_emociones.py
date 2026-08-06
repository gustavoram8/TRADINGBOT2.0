# -*- coding: utf-8 -*-
"""Recorta los 12 rubíes de `tessera_emociones.png` y les BORRA EL FONDO.

La lámina es una rejilla de 4×3 paneles con MARCO NEGRO sobre fondo crema; cada
panel trae el teseracto con sus garabatos (estrellas, corazones, nube, zzz…) y
la etiqueta DEBAJO del marco.

Dos pasos:
  1) detecta los 12 marcos negros y recorta el interior de cada uno.
  2) BORRA EL FONDO inundando el crema desde los bordes (como las botargas):
     el crema, el piso y el marco se van a transparente; lo que queda encerrado
     por un contorno (globos de texto, brillos internos) se conserva. Luego
     recorta pegado al cubo.

Solo necesita Pillow. Se corre EN EL VPS:

    cd /var/www/TRADINGBOT2.0
    git checkout origin/claude/gallant-volta-i7cqmf -- tools/recorta_emociones.py
    venv/bin/python3 tools/recorta_emociones.py

Deja en `scalpel/static/`:
  · `emo-<nombre>.png`  (los 12 rubíes con fondo transparente)
  · `_emo_contacto.png` (hoja de contacto sobre tablero de ajedrez para revisar)
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
INSET = 0.02          # meterse hacia dentro del marco antes de inundar
FLOOD_THRESH = 86     # tolerancia del relleno de fondo (crema + piso + sombra)
MARCA = (0, 255, 1)   # color centinela imposible en el arte


def _perfil_columnas(mask, W):
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


def _anillo(w, h, fx):
    """Puntos a lo largo de un rectángulo metido 'fx' hacia dentro."""
    x0, y0 = int(w * fx), int(h * fx)
    x1, y1 = w - 1 - x0, h - 1 - y0
    pts = []
    for x in range(x0, x1 + 1, max(1, w // 26)):
        pts += [(x, y0), (x, y1)]
    for y in range(y0, y1 + 1, max(1, h // 26)):
        pts += [(x0, y), (x1, y)]
    return pts


def dentro_del_marco(panel):
    """Recorta el panel a JUSTO POR DENTRO de su marco negro.

    Los garabatos de la expresión viven dentro del marco, así que recortar por
    su borde interior los conserva enteros y deja fuera el marco. No toca nada
    oscuro: solo mide dónde está el marco (línea negra de ancho casi completo).
    """
    g = panel.convert('L')
    w, h = panel.size
    m = g.point(lambda p: 255 if p < UMBRAL_OSCURO else 0)
    rows = _perfil_filas(m, h)      # 0..255 = % de negro por fila
    cols = _perfil_columnas(m, w)

    def borde(prof, n):
        # desde el principio: salta crema, cruza el marco, para en lo de dentro
        i = 0
        while i < n and prof[i] < 90:  i += 1   # crema exterior
        while i < n and prof[i] >= 40: i += 1   # el trazo del marco
        a = i
        j = n - 1
        while j >= 0 and prof[j] < 90:  j -= 1
        while j >= 0 and prof[j] >= 40: j -= 1
        b = j
        return a, b

    top, bot = borde(rows, h)
    left, right = borde(cols, w)
    if bot - top < h * 0.45 or right - left < w * 0.45:
        return panel               # detección dudosa -> deja el panel completo
    return panel.crop((max(0, left), max(0, top),
                       min(w, right + 1), min(h, bot + 1)))


def quita_fondo(panel):
    """Borra el fondo del PANEL COMPLETO (crema + piso + marco) sin recortar la
    expresión.

    Recibe el panel entero, con su marco. Siembra el relleno en tres sitios:
      · el borde y un anillo justo por DENTRO del marco -> se lleva el crema y el
        piso, tanto el de fuera del marco como el de dentro (que el marco aísla);
      · sobre el propio marco negro -> lo quita.
    Los blancos ENCERRADOS por un contorno (globos de texto, brillo interno del
    cubo) no se tocan: el relleno no llega a ellos. Devuelve un RGBA recortado
    pegado a lo que queda, con lo que quede de la expresión INTACTO.
    """
    rgb = panel.convert('RGB')
    w, h = rgb.size

    # ── 1) BORRAR SOLO LA LÍNEA DEL MARCO ──────────────────────────────────
    # Se localiza cada lado del marco (la fila/columna más negra cerca de cada
    # borde) y se limpia ESA banda fina, solo sus píxeles oscuros. Así el marco
    # se va pero los garabatos que lo cruzan (nubes, WOW, lámpara) y la punta
    # del cubo se quedan enteros: solo pierden el pelo de píxel donde pisan la
    # raya del marco.
    gray = panel.convert('L')
    # Máscara SOLO de negro-marco (~15), NO del rojo oscuro del cubo (~47): así
    # una fila/columna que cruza el cubo casi no cuenta, y solo las líneas
    # realmente negras del marco superan el listón.
    mk = gray.point(lambda p: 255 if p < 42 else 0)
    rows = _perfil_filas(mk, h)
    cols = _perfil_columnas(mk, w)
    gpx = gray.load()

    # Una FILA del marco está casi toda negra (línea de borde a borde); un
    # garabato solo ennegrece un trozo. Se limpia toda fila/columna del borde
    # que supere el umbral -> se va el marco entero, caiga donde caiga, sin
    # tocar el cubo (que está en el centro, fuera de estas bandas).
    # Una línea del marco es negra casi de punta a punta (fila/columna ~90%+
    # oscura). Una fila/columna que cruza el CUBO llega como mucho a ~60%
    # (el cubo no ocupa todo el alto y tiene brillos claros). Con el listón
    # alto se borra el marco entero y jamás se toca el cubo, aunque se
    # ensanche la banda.
    LINEA = 120   # con la máscara de negro-marco, una línea llena supera esto;
                  # una fila/columna que cruza el cubo (solo su contorno) no.

    def _limpia_filas(lo, hi):
        for yy in range(max(0, lo), min(h, hi)):
            if rows[yy] > LINEA:
                for xx in range(w):
                    if gpx[xx, yy] < 130:
                        rgb.putpixel((xx, yy), MARCA)

    def _limpia_cols(lo, hi):
        for xx in range(max(0, lo), min(w, hi)):
            if cols[xx] > LINEA:
                for yy in range(h):
                    if gpx[xx, yy] < 130:
                        rgb.putpixel((xx, yy), MARCA)

    _limpia_filas(0, int(0.20 * h))
    _limpia_filas(int(0.80 * h), h)
    _limpia_cols(0, int(0.20 * w))
    _limpia_cols(int(0.80 * w), w)

    # ── 2) INUNDAR SOLO EL CREMA CLARO ─────────────────────────────────────
    # Desde el borde (crema exterior) y desde anillos por dentro del marco
    # (crema interior). Nunca se toca nada oscuro -> el cubo queda INTACTO.
    for fx in (0.0, 0.04, 0.09, 0.14):
        for sx, sy in _anillo(w, h, fx):
            r, g, b = rgb.getpixel((sx, sy))
            if (r + g + b) / 3 > 150 and rgb.getpixel((sx, sy)) != MARCA:
                ImageDraw.floodfill(rgb, (sx, sy), MARCA, thresh=FLOOD_THRESH)
    # alpha: transparente donde quedó la marca; opaco en el resto
    px = rgb.load()
    out = panel.convert('RGBA')
    op = out.load()
    minx, miny, maxx, maxy = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = op[x, y]
            # 2ª pasada: bolsas de fondo ENCERRADAS que el relleno no alcanzó.
            # Beige/tan claro y neutro (R≈G≈B) -> fondo. Se protege el brillo
            # ROSADO del cubo (R alto, saturado), las gotas AZULES, las estrellas
            # DORADAS (todas con mucha diferencia entre canales) y el blanco puro
            # de los globos de texto (min>238).
            spread = max(r, g, b) - min(r, g, b)
            if px[x, y] != MARCA and (r + g + b) / 3 > 168 and spread < 40 \
                    and min(r, g, b) <= 238 and r >= b:
                px[x, y] = MARCA
            if px[x, y] == MARCA:
                op[x, y] = (0, 0, 0, 0)
            else:
                if x < minx: minx = x
                if y < miny: miny = y
                if x > maxx: maxx = x
                if y > maxy: maxy = y
    if maxx <= minx or maxy <= miny:
        return out                     # nada que recortar (raro)
    pad = 6
    box = (max(0, minx - pad), max(0, miny - pad),
           min(w, maxx + 1 + pad), min(h, maxy + 1 + pad))
    return out.crop(box)


def main():
    if not os.path.exists(FUENTE):
        print('✗ Falta scalpel/static/tessera_emociones.png')
        return 1
    im = Image.open(FUENTE).convert('RGB')
    W, H = im.size
    print('Lámina: %d×%d' % (W, H))
    gris = im.convert('L')
    mask = gris.point(lambda p: 255 if p < UMBRAL_OSCURO else 0)

    fila = _perfil_filas(mask, H)
    top = 0
    while top < H and fila[top] > 115:
        top += 1
    top = min(top + 2, H - 1)

    sub = mask.crop((0, top, W, H))
    col = _perfil_columnas(sub, W)
    cols = [b for b in _bandas(col, 13) if (b[1] - b[0]) > W * 0.04]
    cols = sorted(sorted(cols, key=lambda b: b[1] - b[0], reverse=True)[:COLS])

    filb = [(a + top, b + top) for (a, b) in _bandas(fila[top:], 10)]
    filas = sorted(sorted(filb, key=lambda b: b[1] - b[0], reverse=True)[:NFIL])

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
            # panel COMPLETO con margen generoso: entran TODOS los garabatos,
            # incluso los que cruzan el marco (nubes, WOW, lámpara). El marco lo
            # borra quita_fondo() por su línea, no recortándolo.
            ex = int((cx1 - cx0) * 0.06)
            ey = int((ry1 - ry0) * 0.06)
            panel = im.crop((max(0, cx0 - ex), max(0, ry0 - ey),
                             min(W, cx1 + ex), min(H, ry1 + ey)))
            cara = quita_fondo(panel)
            cara.save(os.path.join(STATIC, 'emo-%s.png' % nombre))
            caras.append((nombre, cara))
    print('✓ 12 rubíes (fondo transparente) -> scalpel/static/emo-<nombre>.png')

    # hoja de contacto sobre tablero de ajedrez (para VER la transparencia)
    celda, eti, q = 300, 34, 15
    tabl = Image.new('RGB', (celda, celda), (210, 210, 210))
    dt = ImageDraw.Draw(tabl)
    for yy in range(0, celda, q):
        for xx in range(0, celda, q):
            if (xx // q + yy // q) % 2:
                dt.rectangle([xx, yy, xx + q, yy + q], fill=(170, 170, 170))
    hoja = Image.new('RGB', (COLS * celda, NFIL * (celda + eti)), (60, 62, 70))
    dib = ImageDraw.Draw(hoja)
    tipo = _fuente(20)
    for i, (nombre, cara) in enumerate(caras):
        f, c = divmod(i, COLS)
        fondo = tabl.copy()
        mini = cara.copy(); mini.thumbnail((celda - 20, celda - 20))
        fondo.paste(mini, ((celda - mini.width) // 2, (celda - mini.height) // 2), mini)
        hoja.paste(fondo, (c * celda, f * (celda + eti)))
        dib.text((c * celda + 8, f * (celda + eti) + celda + 6), nombre,
                 font=tipo, fill=(240, 215, 110))
    hoja.save(os.path.join(STATIC, '_emo_contacto.png'))
    print('✓ Hoja de contacto -> scalpel/static/_emo_contacto.png')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
