# -*- coding: utf-8 -*-
"""Encaja la narración dentro del reel SIN cortar una sola sílaba.

🔴 QUÉ SALIÓ MAL EN LA PRIMERA VERSIÓN, porque la lección es la importante.
Aquella recortaba cada frase detectada y la pegaba en su escena. Dos fallos
encadenados: (1) el detector de voz usaba un umbral alto, y las sílabas
flojas del final de una frase caen por debajo de él — o sea que el propio
detector se comía palabras; (2) al pegar trozo con trozo, lo que se comía
desaparecía sin dejar rastro. El dueño lo oyó al instante: "break your trade
down, Ssimpulse", que es *step by step. Stop trading on* evaporado.

🔑 EL REDISEÑO: **de la voz no se corta nada, jamás.** Lo único que se toca son
los SILENCIOS entre frases — se estiran o se encogen para que cada línea entre
justo cuando su escena está en pantalla. Si el reparto de frases se equivocara,
lo peor que pasa es que una frase entre medio segundo antes o después; nunca
que falte una palabra. Un fallo de colocación se ve; uno que borra audio, no.

Y encaja casi solo: la locución trae 20,7 s de voz y 18,3 s de silencio, y el
hueco del reel para narrar son 37,6 s. O sea que basta con ajustar los
silencios un 7 % — no hay que acelerar a nadie.

⚠️ Cada tramo de voz se ENSANCHA 120 ms por cada lado antes de considerar que
empieza el silencio. Es el margen que protege consonantes sordas y finales
apagados, que son justo lo que el detector no ve.
⚠️ No se toca ni un fotograma del vídeo. La imagen ya está aprobada.

    python3 tools/pega_narracion.py
"""
from __future__ import print_function

import io
import os
import struct
import subprocess
import sys

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REELS = os.path.join(RAIZ, 'out', 'reels')
VOZ = os.path.join(REELS, '_narracion.mp3')
MUDO = os.path.join(REELS, 'reel-tour.mp4')
MARCA = os.path.join(RAIZ, 'out', 'marca_sonora', '03E_solo_cuerda_larga.wav')
DEST = os.path.join(REELS, 'reel-tour-narrado.mp4')
SR = 48000
TOTAL = 42.30
MARCA_EN = 36.30
GUARDA = 0.12          # margen de seguridad a cada lado de un tramo de voz

# (texto, palabras, cuándo entra, hasta cuándo dura su escena)
LINEAS = [
    ('This is not a course.',                    5,  0.35,  4.75),
    ("It's an ecosystem.",                       3,  2.45,  4.78),
    ('Break your trade down, step by step.',     7,  4.95,  7.95),
    ('Stop trading on impulse. Build the checklist you actually follow.',
                                                10,  8.25, 13.35),
    ('Over four hundred quizzes. Beginner to ultra-hardcore.',
                                                 7, 13.70, 17.75),
    ('Study on your own chalkboard.',            5, 18.05, 20.55),
    ('Forty-one topics. Five methodologies. One map. Open any concept and study it.',
                                                12, 20.95, 28.35),
    ('A real community.',                        3, 28.70, 30.55),
    ('Make the ecosystem yours.',                4, 30.90, 33.15),
    ('And help right inside the site.',          6, 33.65, 37.95),
]


def pcm(ruta):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    p = subprocess.run([ff, '-i', ruta, '-map', '0:a:0', '-ac', '1',
                        '-ar', str(SR), '-f', 's16le', '-'], capture_output=True)
    return np.frombuffer(p.stdout, dtype='<i2').astype(float) / 32768


def tramos(x, guarda=None):
    """Tramos de voz, con umbral BAJO y ensanchados por los dos lados.

    El umbral de la versión anterior (3,5 % del pico) dejaba fuera los finales
    apagados. Aquí se baja al 1,2 % y además se añade GUARDA a cada lado: es
    preferible tomar de más —un poco de silencio— que de menos —media palabra.
    """
    w = int(SR * 0.01)
    e = np.array([np.sqrt((x[i:i + w] ** 2).mean())
                  for i in range(0, len(x) - w, w)])
    hab = e > max(e.max() * 0.012, 0.0015)
    out, dentro, ini = [], False, 0
    for i, v in enumerate(hab):
        if v and not dentro:
            dentro, ini = True, i
        elif not v and dentro:
            out.append((ini * .01, i * .01))
            dentro = False
    if dentro:
        out.append((ini * .01, len(hab) * .01))
    g = []
    for a, b in out:
        gd = GUARDA if guarda is None else guarda
        a, b = max(0.0, a - gd), min(len(x) / SR, b + gd)
        if g and a <= g[-1][1] + 0.10:            # se solapan → una sola frase
            g[-1] = (g[-1][0], max(g[-1][1], b))
        else:
            g.append((a, b))
    return [t for t in g if t[1] - t[0] > 0.20]


def reparte(dur, esperado, huecos):
    """Agrupa los tramos en las 10 líneas del guion, en orden.

    Al error de duración se le resta un premio por cortar donde el silencio es
    LARGO: un cambio de línea casi siempre cae en la pausa más ancha, y esa
    señal es independiente de la duración, así que las dos juntas se equivocan
    mucho menos que cualquiera por separado.
    """
    N, M = len(dur), len(esperado)
    INF = float('inf')
    best = [[INF] * (M + 1) for _ in range(N + 1)]
    prev = [[None] * (M + 1) for _ in range(N + 1)]
    best[0][0] = 0
    for i in range(N + 1):
        for j in range(M):
            if best[i][j] == INF:
                continue
            acum = 0
            for k in range(i, N):
                acum += dur[k]
                premio = huecos[k] * 1.6 if k < N - 1 else 0
                c = best[i][j] + abs(acum - esperado[j]) - premio
                if c < best[k + 1][j + 1]:
                    best[k + 1][j + 1] = c
                    prev[k + 1][j + 1] = (i, j)
    i, j, camino = N, M, []
    while j > 0:
        pi, pj = prev[i][j]
        camino.append((pj, pi, i))
        i, j = pi, pj
    return list(reversed(camino))


def main():
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    if not os.path.exists(VOZ):
        sys.exit('falta la locución en %s' % VOZ)
    x = pcm(VOZ)
    t = tramos(x)
    dur = [b - a for a, b in t]
    huecos = [(t[i + 1][0] - t[i][1]) for i in range(len(t) - 1)] + [0]
    pal = sum(p for _, p, _, _ in LINEAS)
    sxp = sum(dur) / pal
    print('locución %.1f s · voz %.1f s (%.0f%% silencio) · %.1f pal/s · %d tramos'
          % (len(x) / SR, sum(dur), 100 * (1 - sum(dur) / (len(x) / SR)),
             1 / sxp, len(t)))
    plan = reparte(dur, [p * sxp for _, p, _, _ in LINEAS], huecos)

    pista = np.zeros(int(TOTAL * SR))
    print('\n%-3s %-42s %7s %7s %s' % ('#', 'línea', 'entra', 'dura', 'estado'))
    for (j, a, b) in plan:
        txt, _, cue, tope = LINEAS[j]
        # 🔑 se toma el bloque CONTIGUO del original (voz + sus pausas internas
        #    intactas): dentro de una línea no se corta absolutamente nada
        i0, i1 = int(t[a][0] * SR), int(t[b - 1][1] * SR)
        linea = x[i0:i1].copy()
        largo = len(linea) / SR
        nota = 'intacta'
        if cue + largo > tope:
            # no cabe → se encogen SOLO sus silencios internos, nunca la voz
            piezas, fin_ant = [], a
            sobra = cue + largo - tope
            n_huecos = b - 1 - a
            for k in range(a, b):
                s0, s1 = int(t[k][0] * SR), int(t[k][1] * SR)
                piezas.append(x[s0:s1])
                if k < b - 1:
                    h = (t[k + 1][0] - t[k][1]) - (sobra / max(1, n_huecos))
                    piezas.append(np.zeros(int(max(0.10, h) * SR)))
            linea = np.concatenate(piezas)
            largo = len(linea) / SR
            nota = 'pausas internas encogidas'
        print('%-3d %-42s %6.2fs %6.2fs %s' % (j + 1, txt[:40], cue, largo, nota))
        i = int(cue * SR)
        n = min(len(linea), len(pista) - i)
        pista[i:i + n] += linea[:n]

    g = pcm(MARCA)
    i = int(MARCA_EN * SR)
    n = min(len(g), len(pista) - i)
    pista[i:i + n] += g[:n] * 0.85

    pista = np.tanh(pista * 1.02)
    pista = pista / (np.abs(pista).max() + 1e-9) * 0.92
    # 🔑 LA COMPROBACIÓN QUE IMPORTA: se vuelve a medir cuánta VOZ hay en la
    # pista montada y se compara con la del original. Si falta algo, aquí sale
    # — es la prueba que la versión anterior no tenía y por eso se publicó con
    # media frase evaporada.
    # ⚠️ se mide SIN margen en los dos lados: con margen, al encoger una pausa
    #    dos márgenes se solapan y el medidor acusa una pérdida que no existe.
    voz_out = sum(b - a for a, b in tramos(pista[:int(38.0 * SR)], 0.0))
    voz_in = sum(b - a for a, b in tramos(x, 0.0))
    print('\nvoz en el original %.2f s → en la pista %.2f s   (%+.2f s)'
          % (voz_in, voz_out, voz_out - voz_in))
    if voz_out < voz_in - 0.15:
        print('🔴 SE PERDIÓ VOZ — no publicar')

    wav = os.path.join(REELS, '_pista_narrada.wav')
    d = (np.clip(pista, -1, 1) * 32767).astype('<i2').tobytes()
    with io.open(wav, 'wb') as f:
        f.write(b'RIFF' + struct.pack('<I', 36 + len(d)) + b'WAVEfmt ')
        f.write(struct.pack('<IHHIIHH', 16, 1, 1, SR, SR * 2, 2, 16))
        f.write(b'data' + struct.pack('<I', len(d)) + d)
    subprocess.run([ff, '-y', '-loglevel', 'error', '-i', MUDO, '-i', wav,
                    '-filter_complex', '[1:a]pan=stereo|c0=c0|c1=c0[a]',
                    '-map', '0:v:0', '-map', '[a]', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '192k', '-shortest',
                    '-movflags', '+faststart', DEST], check=True)
    print('listo: %s · %.1f MB' % (DEST, os.path.getsize(DEST) / 1e6))


if __name__ == '__main__':
    main()
