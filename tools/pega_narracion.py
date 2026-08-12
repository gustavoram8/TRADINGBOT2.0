# -*- coding: utf-8 -*-
"""Encaja la narración grabada dentro del reel, frase por frase.

🔑 EL HALLAZGO QUE CAMBIA EL ARREGLO. El dueño pidió "adecuar la voz porque la
IA narró muy lento". Medido: la locución dura 39 s pero **solo 20,7 s son voz**
— el 47 % son silencios. O sea que no habla lento (3,0 palabras/segundo es un
ritmo normal): lo que sobra son las PAUSAS entre frases. Por eso aquí no se
acelera la voz —que sonaría a ardilla y se notaría— sino que se **recorta cada
frase y se coloca en el segundo donde su escena está en pantalla**.

CÓMO SE SABE QUÉ FRASE ES CUÁL, sin transcribir:
  1. se detectan los tramos de voz por energía (18 tramos);
  2. se reparten entre las 10 líneas del guion EN ORDEN, con programación
     dinámica, minimizando la diferencia entre lo que dura cada línea y lo que
     DEBERÍA durar según sus palabras al ritmo medido.
  Confirmación de que el reparto es bueno: a la línea 7 —que en el guion tiene
  cuatro frases— le tocan exactamente cuatro tramos, y a la 4 —que tiene dos—
  le tocan dos.

⚠️ NO se recorta ni un fotograma del reel: la restricción es del dueño y es la
correcta, porque el vídeo ya está aprobado. La voz se adapta al vídeo, nunca al
revés. Si una frase no cupiera en su escena, se estrecharían sus pausas
internas antes que tocar la imagen.

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
MARCA_EN = 36.30          # la marca sonora entra retrasada estos segundos

# Las 10 líneas del guion, con sus palabras y DÓNDE tiene que sonar cada una.
# `cue` = segundo del reel en que arranca; `tope` = segundo en que su escena
# desaparece de pantalla. Salen de docs/reel_narracion.md.
LINEAS = [
    ('This is not a course.',                    5,  0.35,  4.70),
    ("It's an ecosystem.",                       3,  2.55,  4.75),
    ('Break your trade down, step by step.',     7,  5.05,  7.95),
    ('Stop trading on impulse. Build the checklist you actually follow.',
                                                10,  8.30, 13.35),
    ('Over four hundred quizzes. Beginner to ultra-hardcore.',
                                                 7, 13.75, 17.75),
    ('Study on your own chalkboard.',            5, 18.10, 20.55),
    ('Forty-one topics. Five methodologies. One map. Open any concept and study it.',
                                                12, 21.00, 28.35),
    ('A real community.',                        3, 28.75, 30.55),
    ('Make the ecosystem yours.',                4, 30.95, 33.15),
    ('And help right inside the site.',          6, 33.70, 37.95),
]
HUECO = 0.34              # pausa que se deja DENTRO de una línea, entre tramos


def pcm(ruta, canales=1):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    p = subprocess.run([ff, '-i', ruta, '-map', '0:a:0', '-ac', str(canales),
                        '-ar', str(SR), '-f', 's16le', '-'], capture_output=True)
    return np.frombuffer(p.stdout, dtype='<i2').astype(float) / 32768


def tramos(x):
    """Trozos con voz, uniendo los separados por menos de 0,32 s."""
    w = int(SR * 0.02)
    e = np.array([np.sqrt((x[i:i + w] ** 2).mean())
                  for i in range(0, len(x) - w, w)])
    hab = e > max(e.max() * 0.035, 0.004)
    out, dentro, ini = [], False, 0
    for i, v in enumerate(hab):
        if v and not dentro:
            dentro, ini = True, i
        elif not v and dentro:
            if (i - ini) * .02 > 0.18:
                out.append((ini * .02, i * .02))
            dentro = False
    if dentro:
        out.append((ini * .02, len(hab) * .02))
    u = []
    for s in out:
        if u and s[0] - u[-1][1] < 0.32:
            u[-1] = (u[-1][0], s[1])
        else:
            u.append(s)
    return u


def reparte(dur, esperado):
    """Cada línea se queda con 1..n tramos CONSECUTIVOS. Programación dinámica
    sobre el error total; el orden del guion es la restricción que lo hace
    resoluble sin transcribir."""
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
                c = best[i][j] + abs(acum - esperado[j])
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
    pal = sum(p for _, p, _, _ in LINEAS)
    sxp = sum(dur) / pal
    print('locución: %.1f s totales · %.1f s de voz (%.0f%% silencio) · %.1f pal/s'
          % (len(x) / SR, sum(dur), 100 * (1 - sum(dur) / (len(x) / SR)), 1 / sxp))
    plan = reparte(dur, [p * sxp for _, p, _, _ in LINEAS])

    pista = np.zeros(int(TOTAL * SR))
    borde = int(SR * 0.006)                 # 6 ms de entrada/salida: sin clics
    print('\n%-3s %-44s %7s %7s %s' % ('#', 'línea', 'entra', 'dura', 'cabe'))
    for (j, a, b) in plan:
        txt, _, cue, tope = LINEAS[j]
        piezas = []
        for k in range(a, b):
            i0, i1 = int(t[k][0] * SR), int(t[k][1] * SR)
            tr = x[i0:i1].copy()
            tr[:borde] *= np.linspace(0, 1, borde)
            tr[-borde:] *= np.linspace(1, 0, borde)
            piezas.append(tr)
            if k < b - 1:
                piezas.append(np.zeros(int(HUECO * SR)))
        linea = np.concatenate(piezas)
        # ⚠️ si no cupiera, se estrecha la pausa interna — nunca el vídeo
        if cue + len(linea) / SR > tope and b - a > 1:
            sob = cue + len(linea) / SR - tope
            h = max(0.12, HUECO - sob / (b - a - 1))
            piezas = []
            for k in range(a, b):
                i0, i1 = int(t[k][0] * SR), int(t[k][1] * SR)
                tr = x[i0:i1].copy()
                tr[:borde] *= np.linspace(0, 1, borde)
                tr[-borde:] *= np.linspace(1, 0, borde)
                piezas.append(tr)
                if k < b - 1:
                    piezas.append(np.zeros(int(h * SR)))
            linea = np.concatenate(piezas)
        fin = cue + len(linea) / SR
        print('%-3d %-44s %6.2fs %6.2fs %s'
              % (j + 1, txt[:42], cue, len(linea) / SR,
                 'sí' if fin <= tope else '⚠️ se pasa %.2f s' % (fin - tope)))
        i = int(cue * SR)
        n = min(len(linea), len(pista) - i)
        pista[i:i + n] += linea[:n]

    # la marca sonora, en su sitio de siempre
    g = pcm(MARCA)
    i = int(MARCA_EN * SR)
    n = min(len(g), len(pista) - i)
    pista[i:i + n] += g[:n] * 0.85

    pista = np.tanh(pista * 1.02)
    pista = pista / (np.abs(pista).max() + 1e-9) * 0.92
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
    print('\nlisto: %s · %.1f MB' % (DEST, os.path.getsize(DEST) / 1e6))


if __name__ == '__main__':
    main()
