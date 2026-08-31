# -*- coding: utf-8 -*-
"""PASO A — cuánto ve de fino cada modelo de visión sobre un gráfico de trading.

    python3 tools/agudeza_visual.py --generar          # dibuja las láminas (gratis)
    python3 tools/agudeza_visual.py --correr openai:gpt-4o          # gasta dinero
    python3 tools/agudeza_visual.py --correr gemini:gemini-3-pro
    python3 tools/agudeza_visual.py --tabla            # el resultado, comparado

Existe para responder UNA pregunta antes de pagar ningún modelo nuevo: **¿a qué
tamaño en píxeles deja de ver cada modelo?** No mide si sabe de trading —eso lo
mide el banco de 30 casos (`corre_banco.py`)—, mide la vista. Si un candidato no
supera aquí a GPT-4o, no tiene sentido pasarle el banco.

🔑 LAS LÁMINAS SON DE 1920×1080 A PROPÓSITO, y eso es el experimento entero.
   GPT-4o **reduce el lado corto a 768 px** antes de mirar; Gemini procesa a
   bastante más resolución. Ese reescalado ES el fallo que estamos midiendo, así
   que la lámina tiene que llegar al mismo tamaño que el screenshot de un cliente
   real. Generar imágenes pequeñas "para que se vean bien" mataría la prueba: el
   modelo aprobaría todo y no habríamos medido nada.

🔑 CADA FAMILIA VARÍA UN SOLO NÚMERO, en píxeles, y ese número es la respuesta.
   No se pregunta "¿ves bien el gráfico?" sino "¿a partir de cuántos píxeles
   aciertas?". El umbral que imprime `--tabla` es el primer nivel donde el modelo
   llega al 75% de aciertos y ya no baja.

🔴 CONTROL DE ADIVINANZA — la mitad de los casos de cada familia de SÍ/NO son
   NO. Sin eso, un modelo que conteste "sí" siempre sacaría 100% y quedaría como
   el mejor. Con el balance, contestar a ciegas da 50% y se nota. Las familias de
   número (OCR, conteo) no necesitan balance: acertar por azar es improbable.

🔴 SE CORRE EN EL VPS. Este contenedor no llega a api.openai.com ni a
   generativelanguage.googleapis.com, y las claves viven en `scalpel/.env`.
   Generar las láminas sí funciona en cualquier sitio.

Costo: 144 láminas ≈ $0.6-1,5 por modelo según tarifa. Nada que ver con el banco.
"""
from __future__ import print_function

import argparse
import base64
import glob
import io
import json
import os
import random
import sys
import time

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'out', 'agudeza')
LAMINAS = os.path.join(SALIDA, 'laminas')
AN, AL = 1920, 1080

# — paleta de un gráfico oscuro cualquiera —
FONDO = (14, 17, 23)
REJILLA = (30, 35, 46)
EJE = (140, 150, 168)
SUBE = (38, 166, 109)
BAJA = (223, 74, 74)
LINEA_A = (79, 140, 255)
LINEA_B = (240, 176, 60)
NIVEL = (200, 205, 215)

FUENTES = ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
           '/usr/share/fonts/truetype/freefont/FreeSans.ttf']


def _fuente(px):
    for f in FUENTES:
        if os.path.exists(f):
            return ImageFont.truetype(f, px)
    return ImageFont.load_default()


def _lienzo():
    im = Image.new('RGB', (AN, AL), FONDO)
    d = ImageDraw.Draw(im)
    for y in range(0, AL, 90):
        d.line([(0, y), (AN, y)], fill=REJILLA)
    for x in range(0, AN, 120):
        d.line([(x, 0), (x, AL)], fill=REJILLA)
    d.line([(AN - 150, 0), (AN - 150, AL)], fill=(48, 55, 70))
    return im, d


def _velas(d, x0, x1, y0, y1, semilla, ancho=11, hueco=6):
    """Velas de relleno. Solo son decorado: ninguna familia se juega la
    respuesta en ellas salvo la de ruptura, que dibuja la suya aparte."""
    rnd = random.Random(semilla)
    p = (y0 + y1) / 2.0
    x = x0
    while x < x1 - ancho:
        ap = p
        ci = ap + rnd.uniform(-26, 26)
        hi = min(ap, ci) - rnd.uniform(2, 16)
        lo = max(ap, ci) + rnd.uniform(2, 16)
        hi, lo = max(y0, hi), min(y1, lo)
        col = SUBE if ci < ap else BAJA
        cx = x + ancho // 2
        d.line([(cx, hi), (cx, lo)], fill=col)
        d.rectangle([x, min(ap, ci), x + ancho, max(ap, ci)], fill=col)
        p = ci
        x += ancho + hueco
    return p


# ══════════════════════════════════════════════════════════════════════════
# LAS SEIS FAMILIAS
# Cada una devuelve (imagen, pregunta, respuesta_correcta).
# ══════════════════════════════════════════════════════════════════════════

def fam_ocr(nivel, k, rnd):
    """AGUDEZA PURA — leer una etiqueta de precio de `nivel` px de alto.

    Es el ciego T3 en su forma más simple: si no puede leer el "30" del eje del
    RSI, cualquier lectura de ese indicador es inventada."""
    im, d = _lienzo()
    _velas(d, 60, AN - 170, 200, 880, rnd.randint(0, 10 ** 6))
    valor = rnd.randint(1000, 9999)
    y = rnd.randint(260, 820)
    d.line([(60, y), (AN - 150, y)], fill=NIVEL, width=1)
    d.text((AN - 142, y - nivel / 2.0 - 1), str(valor), font=_fuente(nivel), fill=(235, 240, 248))
    # distractores: otras etiquetas del eje, del mismo tamaño
    for dy in (-170, -90, 90, 170):
        yy = y + dy
        if 40 < yy < AL - 40:
            d.text((AN - 142, yy - nivel / 2.0 - 1), str(rnd.randint(1000, 9999)),
                   font=_fuente(nivel), fill=(150, 158, 172))
    return im, ('En el eje de precios de la derecha hay una etiqueta a la altura de la '
                'línea horizontal blanca que cruza todo el gráfico. Responde SOLO con '
                'ese número de 4 cifras, sin nada más.'), str(valor)


def fam_cruce(nivel, k, rnd):
    """RELACIONAL — ¿las dos medias se cruzan, o se acercan sin tocarse?

    Es el ciego T4 exacto. `nivel` = separación mínima en px cuando NO se cruzan.
    Los casos de cruce se solapan `nivel` px del otro lado, para que la única
    diferencia entre un sí y un no sea el signo de esa distancia."""
    im, d = _lienzo()
    cruza = (k % 2 == 0)
    _velas(d, 60, AN - 170, 240, 900, rnd.randint(0, 10 ** 6))
    x0, x1 = 90, AN - 180
    xc = rnd.randint(int(AN * .35), int(AN * .70))
    base = rnd.randint(420, 660)
    a, b = [], []
    # 🔴 NO se pueden usar dos RECTAS de pendiente opuesta: se cruzan SIEMPRE, y
    #    desplazar una `nivel` px solo mueve el punto de cruce a otro sitio. Los
    #    casos "NO" salían dibujados como "SI" (cazado midiendo los píxeles).
    #    La construcción correcta es un pico contra un valle: se ACERCAN hasta
    #    `nivel` px en xc y se separan otra vez. Con el signo invertido se
    #    penetran esos mismos `nivel` px y cruzan dos veces. Así lo único que
    #    distingue un sí de un no es el signo de esa distancia.
    # ⚠️ La ondulación es COMPARTIDA por las dos líneas: se le suma la MISMA
    #    `w(x)` a ambas, así parecen medias de verdad y no dos rectas, pero la
    #    distancia vertical entre ellas —que es la verdad del caso— no cambia
    #    ni un píxel. Una ondulación independiente por línea abriría cruces
    #    fantasma y la respuesta declarada dejaría de ser cierta.
    import math
    f1, f2 = rnd.uniform(2.0, 3.5), rnd.uniform(5.0, 8.0)
    d1, d2 = rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)
    for x in range(x0, x1, 4):
        u = (x - x0) / float(x1 - x0)
        t = abs(x - xc) / float(x1 - x0)
        sep = nivel if not cruza else -nivel
        w = 34 * math.sin(f1 * u * 6.28 + d1) + 16 * math.sin(f2 * u * 6.28 + d2)
        a.append((x, base - t * 520 + w))
        b.append((x, base + sep + t * 520 + w))
    # ⚠️ Trazo de 1 px, no 2: con 2 px de grosor una separación de 2 px deja a
    #    las líneas TOCÁNDOSE, y el nivel deja de significar lo que dice. El
    #    número mide distancia entre ejes, así que el trazo tiene que ser fino.
    d.line(a, fill=LINEA_A, width=1)
    d.line(b, fill=LINEA_B, width=1)
    return im, ('En el gráfico hay dos medias móviles, una AZUL y una NARANJA. '
                '¿Se llegan a cruzar en algún punto? Responde SOLO SI o NO.'), \
        ('SI' if cruza else 'NO')


def fam_ruptura(nivel, k, rnd):
    """RELACIONAL — ¿el cierre rompió el nivel, o se quedó a `nivel` px?"""
    im, d = _lienzo()
    rompe = (k % 2 == 0)
    y_niv = rnd.randint(400, 620)
    _velas(d, 60, 1180, y_niv + 60, y_niv + 300, rnd.randint(0, 10 ** 6))
    # 1 px: con 2, un rebase de 1 px cae DENTRO del propio grosor de la línea
    # y "por encima del nivel" deja de tener una respuesta clara.
    d.line([(60, y_niv), (AN - 150, y_niv)], fill=NIVEL, width=1)
    # la vela del veredicto: su CIERRE queda `nivel` px por encima o por debajo
    cx = 1260
    cierre = y_niv - nivel if rompe else y_niv + nivel
    apert = y_niv + 70
    d.line([(cx + 6, cierre - 22), (cx + 6, apert + 14)], fill=SUBE)
    d.rectangle([cx, cierre, cx + 13, apert], fill=SUBE)
    _velas(d, 1290, AN - 170, y_niv - 40, y_niv + 220, rnd.randint(0, 10 ** 6))
    return im, ('Hay una línea horizontal blanca (un nivel). Fíjate en la vela '
                'verde grande que llega hasta esa línea. ¿Su CIERRE (el borde superior '
                'del cuerpo, no la mecha) quedó por ENCIMA de la línea? '
                'Responde SOLO SI o NO.'), ('SI' if rompe else 'NO')


def fam_rsi(nivel, k, rnd):
    """AGUDEZA EN PANEL PEQUEÑO — el ciego T3 en su forma real.

    `nivel` = ALTO EN PÍXELES del panel del indicador. Es la variable que de
    verdad mata: un RSI dibujado en 60 px de alto dentro de una lámina de 1080
    no se puede leer aunque el modelo sea excelente."""
    im, d = _lienzo()
    _velas(d, 60, AN - 170, 120, AL - nivel - 90, rnd.randint(0, 10 ** 6))
    top = AL - nivel - 40
    d.rectangle([60, top, AN - 150, top + nivel], outline=(60, 68, 85))
    y30 = top + nivel * 0.70                      # 30 en escala 0-100 invertida
    y70 = top + nivel * 0.30
    for yy in (y30, y70):
        d.line([(62, yy), (AN - 152, yy)], fill=(90, 98, 116))
    d.text((AN - 146, y30 - 6), '30', font=_fuente(11), fill=EJE)
    d.text((AN - 146, y70 - 6), '70', font=_fuente(11), fill=EJE)
    abajo = (k % 2 == 0)
    fin = rnd.uniform(0.10, 0.24) if abajo else rnd.uniform(0.40, 0.62)   # valor 0-1
    pts, v = [], rnd.uniform(0.35, 0.60)
    xs = list(range(70, AN - 155, 5))
    for i, x in enumerate(xs):
        t = i / float(len(xs) - 1)
        v = v * (1 - t) + fin * t + rnd.uniform(-.02, .02)
        v = min(0.97, max(0.03, v))
        pts.append((x, top + nivel * (1 - v)))
    d.line(pts, fill=(190, 120, 235), width=2)
    return im, ('Abajo del gráfico hay un panel con un indicador tipo RSI (línea '
                'morada) y dos guías horizontales marcadas 30 y 70. ¿El ÚLTIMO valor '
                'del indicador, en el extremo derecho, está por DEBAJO de la guía 30? '
                'Responde SOLO SI o NO.'), ('SI' if abajo else 'NO')


def fam_solape(nivel, k, rnd):
    """RELACIONAL — el ciego E3: ¿las dos zonas se solapan o no?

    `nivel` = píxeles de solape (o de separación, en los casos NO)."""
    im, d = _lienzo()
    _velas(d, 60, AN - 170, 240, 880, rnd.randint(0, 10 ** 6))
    solapan = (k % 2 == 0)
    y = rnd.randint(360, 700)
    alto = 90
    # 🔴 Las zonas NO pueden compartir columnas: la que se dibuja después TAPA a
    #    la otra justo en la franja del solape, y con 1-2 px la respuesta deja de
    #    ser discernible incluso a resolución completa — la verdad se vuelve
    #    ambigua y el test mediría ruido. Van lado a lado, sin ocluirse, que
    #    además es el caso real: dos zonas de sesiones distintas.
    #    Sin `outline` a propósito: el borde metería sus propios píxeles en el
    #    cálculo y un solape de 1 px sería en realidad de 3.
    z1 = (140, y, 900, y + alto)
    y2 = (y + alto - nivel) if solapan else (y + alto + nivel)
    z2 = (1020, y2, AN - 140, y2 + alto)
    d.rectangle(z1, fill=(40, 92, 178))
    d.rectangle(z2, fill=(190, 112, 42))
    return im, ('Hay dos zonas rectangulares, una AZUL y una NARANJA. ¿Se solapan '
                'verticalmente, es decir, comparten algún rango de precio? '
                'Responde SOLO SI o NO.'), ('SI' if solapan else 'NO')


def fam_conteo(nivel, k, rnd):
    """DETECCIÓN — contar líneas de `nivel` px de grosor.

    Si no puede contarlas, tampoco puede saber cuántos niveles marcó el trader,
    ni cuántas medias hay en el gráfico."""
    im, d = _lienzo()
    _velas(d, 60, AN - 170, 200, 900, rnd.randint(0, 10 ** 6))
    n = rnd.randint(2, 6)
    ys = rnd.sample(range(260, 860, 45), n)
    for yy in ys:
        d.line([(60, yy), (AN - 150, yy)], fill=(255, 235, 120), width=nivel)
    return im, ('¿Cuántas líneas horizontales AMARILLAS hay dibujadas sobre el '
                'gráfico? Responde SOLO con el número.'), str(n)


FAMILIAS = {
    'ocr':      (fam_ocr,      'tamaño de la letra (px)',    [5, 7, 9, 12, 16, 22]),
    'cruce':    (fam_cruce,    'separación mínima (px)',     [2, 3, 4, 6, 10, 18]),
    'ruptura':  (fam_ruptura,  'margen del cierre (px)',     [1, 2, 3, 5, 9, 16]),
    'rsi':      (fam_rsi,      'alto del panel (px)',        [40, 60, 90, 130, 190, 260]),
    'solape':   (fam_solape,   'solape / separación (px)',   [1, 2, 4, 7, 12, 20]),
    'conteo':   (fam_conteo,   'grosor de línea (px)',       [1, 2, 3, 4, 6, 9]),
}
REPES = 4          # por familia y nivel. Par, para que el balance SI/NO cuadre.


def generar():
    if not os.path.isdir(LAMINAS):
        os.makedirs(LAMINAS)
    for viejo in glob.glob(os.path.join(LAMINAS, '*.png')):
        os.remove(viejo)
    manif = []
    for fam, (fn, _etiq, niveles) in sorted(FAMILIAS.items()):
        for niv in niveles:
            for k in range(REPES):
                # Semilla fija por caso: la lámina de hoy y la de dentro de un
                # mes son el MISMO píxel, así que dos modelos corridos en días
                # distintos siguen siendo comparables.
                rnd = random.Random('%s|%d|%d' % (fam, niv, k))
                im, preg, resp = fn(niv, k, rnd)
                cid = '%s_%03d_%d' % (fam, niv, k)
                im.save(os.path.join(LAMINAS, cid + '.png'))
                manif.append({'id': cid, 'familia': fam, 'nivel': niv,
                              'pregunta': preg, 'respuesta': resp})
    with io.open(os.path.join(SALIDA, 'manifiesto.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps(manif, indent=1, ensure_ascii=False))
    print('%d láminas de %dx%d en %s' % (len(manif), AN, AL, LAMINAS))
    for fam, (_fn, etiq, niveles) in sorted(FAMILIAS.items()):
        print('  %-8s %-26s niveles %s' % (fam, etiq, niveles))
    return manif


# ══════════════════════════════════════════════════════════════════════════
# CORRER — un proveedor por vez. Se llama por HTTP crudo a propósito: son tres
# APIs distintas y no queremos que la versión de ningún SDK decida el resultado.
# ══════════════════════════════════════════════════════════════════════════
INSTR = ('Eres un lector de gráficos. Mira la imagen y responde la pregunta con '
         'la MENOR cantidad de caracteres posible: solo el número o solo SI/NO. '
         'Sin explicaciones, sin puntuación, sin unidades. Si no estás seguro, '
         'responde igualmente con tu mejor lectura.')


def _b64(ruta):
    with open(ruta, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')


def _post(url, cab, cuerpo):
    """POST con reintento que QUITA el parámetro que el proveedor rechace.

    🔴 Esto no es paranoia, son tres incompatibilidades reales entre las APIs:
       · OpenAI renombró `max_tokens` a `max_completion_tokens`; el endpoint
         compatible de Gemini todavía espera el nombre viejo.
       · Los modelos de razonamiento de OpenAI RECHAZAN `temperature` distinto
         de 1 con un 400.
       Sin este reintento, la primera corrida en el VPS muere en la lámina 1 con
       un 400 y hay que adivinar cuál de los dos era."""
    import requests
    for _ in range(4):
        r = requests.post(url, timeout=180, headers=cab, json=cuerpo)
        if r.status_code != 400:
            r.raise_for_status()
            return r.json()
        msg = r.text[:400]
        if 'max_completion_tokens' in msg and 'max_completion_tokens' in cuerpo:
            cuerpo['max_tokens'] = cuerpo.pop('max_completion_tokens')
            continue
        if 'max_tokens' in msg and 'max_tokens' in cuerpo:
            cuerpo['max_completion_tokens'] = cuerpo.pop('max_tokens')
            continue
        if 'temperature' in msg and 'temperature' in cuerpo:
            cuerpo.pop('temperature')
            continue
        r.raise_for_status()
    raise SystemExit('el proveedor sigue devolviendo 400: %s' % msg)


def _pide(prov, modelo, clave, img_b64, pregunta, tope):
    if prov in ('openai', 'gemini'):
        url = ('https://api.openai.com/v1/chat/completions' if prov == 'openai' else
               'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions')
        j = _post(url, {'Authorization': 'Bearer ' + clave}, {
            'model': modelo, 'max_completion_tokens': tope, 'temperature': 0,
            'messages': [
                {'role': 'system', 'content': INSTR},
                {'role': 'user', 'content': [
                    {'type': 'text', 'text': pregunta},
                    # 🔴 detail='high' es obligatorio: en 'auto'/'low' OpenAI manda
                    #    UN solo tile de 512px y la prueba mediría otra cosa.
                    {'type': 'image_url',
                     'image_url': {'url': 'data:image/png;base64,' + img_b64,
                                   'detail': 'high'}}]}]})
        return j['choices'][0]['message'].get('content') or ''
    if prov == 'anthropic':
        j = _post('https://api.anthropic.com/v1/messages',
                  {'x-api-key': clave, 'anthropic-version': '2023-06-01'},
                  {'model': modelo, 'max_tokens': tope, 'temperature': 0,
                   'system': INSTR,
                   'messages': [{'role': 'user', 'content': [
                       {'type': 'image', 'source': {
                           'type': 'base64', 'media_type': 'image/png',
                           'data': img_b64}},
                       {'type': 'text', 'text': pregunta}]}]})
        txt = ''.join(b.get('text', '') for b in j.get('content', []))
        return txt
    raise SystemExit('proveedor desconocido: %s' % prov)


CLAVES = {'openai': 'OPENAI_API_KEY', 'gemini': 'GEMINI_API_KEY',
          'anthropic': 'ANTHROPIC_API_KEY'}


def _normaliza(txt, esperada):
    t = (txt or '').strip().upper()
    t = t.replace('Í', 'I').replace('.', '').replace(',', '').strip()
    if esperada in ('SI', 'NO'):
        if t.startswith('SI') or t.startswith('YES'):
            return 'SI'
        if t.startswith('NO'):
            return 'NO'
        return t[:4]
    dig = ''.join(c for c in t if c.isdigit())
    return dig or t[:8]


def correr(destino, solo_familia, tope):
    prov, _, modelo = destino.partition(':')
    if not modelo:
        raise SystemExit('formato: proveedor:modelo  (ej. gemini:gemini-3-pro)')
    clave = os.environ.get(CLAVES.get(prov, ''), '')
    if not clave:
        raise SystemExit('falta %s en el entorno.\n'
                         '👉 En el VPS: export $(grep -v "^#" scalpel/.env | xargs -d "\\n")'
                         % CLAVES.get(prov, '?'))
    manif = json.load(io.open(os.path.join(SALIDA, 'manifiesto.json'), encoding='utf-8'))
    if solo_familia:
        manif = [c for c in manif if c['familia'] in solo_familia]
    print('%s · %d láminas' % (destino, len(manif)))
    filas, aciertos = [], 0
    for i, c in enumerate(manif, 1):
        ruta = os.path.join(LAMINAS, c['id'] + '.png')
        try:
            bruto = _pide(prov, modelo, clave, _b64(ruta), c['pregunta'], tope)
        except Exception as e:
            bruto = 'ERROR: %s' % e
        dada = _normaliza(bruto, c['respuesta'])
        ok = (dada == c['respuesta'])
        aciertos += ok
        filas.append(dict(c, dada=dada, bruto=(bruto or '')[:120], ok=ok))
        print('  %3d/%d %-16s %-14s dijo %-6s %s'
              % (i, len(manif), c['id'], 'espera ' + c['respuesta'], dada,
                 '✅' if ok else '🔴'))
        time.sleep(0.15)
    nombre = destino.replace('/', '_').replace(':', '__')
    with io.open(os.path.join(SALIDA, 'res_%s.json' % nombre), 'w', encoding='utf-8') as f:
        f.write(json.dumps({'destino': destino, 'filas': filas}, indent=1,
                           ensure_ascii=False))
    vacias = sum(1 for f in filas if not f['bruto'].strip())
    print('\n%s: %d/%d (%.0f%%)' % (destino, aciertos, len(filas),
                                    100.0 * aciertos / max(1, len(filas))))
    if vacias > len(filas) * 0.1:
        # 🔴 En un modelo de RAZONAMIENTO el tope incluye los tokens de
        #    pensamiento: con el tope bajo se los gasta pensando y devuelve
        #    texto vacío. Parecería que "no ve nada" cuando el problema es el
        #    presupuesto. Sin este aviso, el resultado se lee al revés.
        print('⚠️  %d respuestas VACÍAS. Si es un modelo de razonamiento, el tope'
              ' de tokens se gasta pensando: repite con --tope 2000.' % vacias)


# ══════════════════════════════════════════════════════════════════════════
def tabla():
    res = sorted(glob.glob(os.path.join(SALIDA, 'res_*.json')))
    if not res:
        raise SystemExit('no hay resultados todavía: corre --correr primero.')
    datos = [json.load(io.open(r, encoding='utf-8')) for r in res]
    print('\nACIERTOS POR FAMILIA Y NIVEL  (⚠️ en SI/NO, 50%% = adivinar)\n')
    for fam, (_fn, etiq, niveles) in sorted(FAMILIAS.items()):
        print('── %s — %s' % (fam, etiq))
        cab = '   %-34s' % 'modelo' + ''.join('%7d' % n for n in niveles) + '   umbral'
        print(cab)
        for d in datos:
            fil = [f for f in d['filas'] if f['familia'] == fam]
            if not fil:
                continue
            linea, umbral = '', None
            for n in niveles:
                sub = [f for f in fil if f['nivel'] == n]
                if not sub:
                    linea += '%7s' % '·'
                    continue
                pct = 100.0 * sum(1 for f in sub if f['ok']) / len(sub)
                linea += '%6d%%' % round(pct)
                if pct >= 75 and umbral is None:
                    umbral = n
                elif pct < 75:
                    umbral = None          # tiene que aguantar de ahí en adelante
            print('   %-34s%s   %s' % (d['destino'], linea,
                                       ('%dpx' % umbral) if umbral else 'nunca'))
        print()
    print('El UMBRAL es el primer nivel a partir del cual el modelo acierta ≥75% y ya')
    print('no vuelve a bajar. Más chico = ve más fino. "nunca" = no lo resuelve.')
    print('\nTOTALES')
    for d in datos:
        ok = sum(1 for f in d['filas'] if f['ok'])
        print('   %-34s %d/%d  (%.0f%%)' % (d['destino'], ok, len(d['filas']),
                                            100.0 * ok / max(1, len(d['filas']))))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--generar', action='store_true')
    ap.add_argument('--correr', metavar='PROVEEDOR:MODELO')
    ap.add_argument('--familia', nargs='*', help='limita a estas familias')
    ap.add_argument('--tabla', action='store_true')
    ap.add_argument('--tope', type=int, default=512,
                    help='tope de tokens de salida (subir a 2000 si el modelo '
                         'razona y devuelve vacío)')
    a = ap.parse_args()
    if not os.path.isdir(SALIDA):
        os.makedirs(SALIDA)
    if a.generar:
        generar()
    if a.correr:
        correr(a.correr, a.familia, a.tope)
    if a.tabla:
        tabla()
    if not (a.generar or a.correr or a.tabla):
        ap.print_help()
