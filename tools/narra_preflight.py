# -*- coding: utf-8 -*-
"""Calza la locución del reel de Pre-Flight y deja el vídeo a su ritmo.

🔴 EL PROBLEMA, medido antes de tocar nada: la locución trae **40,6 s de voz**
y el hueco para narrar del montaje aprobado eran 39,6 s. O sea que la voz SOLA
ya no cabía — ninguna colocación lo arreglaba. Aquí se resuelve al revés que en
el reel del tour: en vez de meter la voz en el vídeo, **el vídeo se estira para
seguir a la voz**. Cada escena dura lo que dura su frase.

🔑 De la voz no se corta nada, jamás. Lo único que se ajusta son los SILENCIOS
ENTRE frases (los de DENTRO de una frase se respetan tal cual, que son los que
le dan el ritmo a "go… caution… or no"). Un fallo de colocación se ve y se
arregla; uno que borra media palabra pasa desapercibido hasta que lo oye el
dueño.

⚠️ Las frases NO se reparten con el agrupador automático del otro reel. Aquí se
   escribieron a mano contra la estructura FINA del audio (26 tramos sin
   fusionar), porque el automático estaba forzando 11 grupos donde solo hay 10
   frases y descuadraba cinco de ellas.

⚠️ HALLAZGO: la locución **no dice la última línea** ("Tradeable Academy.
   Process over impulse."). Termina en "…is the one that pays most." No se
   inventa nada: el cierre queda solo con el logotipo y la marca sonora, que
   además es lo correcto — una firma no se pisa con voz.

    python3 tools/narra_preflight.py            # audio + tiempos
    python3 tools/narra_preflight.py --montar   # …y además rehace el vídeo
"""
from __future__ import print_function

import io
import json
import os
import struct
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pega_narracion as P                                  # noqa: E402

RAIZ = P.RAIZ
REELS = P.REELS
VOZ = os.path.join(REELS, '_narracion_pf.mp3')
TIEMPOS = os.path.join(REELS, '_tiempos_narracion.json')
MUDO = os.path.join(REELS, 'reel-preflight.mp4')
DEST = os.path.join(REELS, 'reel-preflight-narrado.mp4')
MARCA = os.path.join(RAIZ, 'out', 'marca_sonora', '03E_solo_cuerda_larga.wav')
SR = P.SR
MARCA_VOL = 0.77       # el mismo nivel que aprobó el dueño en el reel del tour
GOLPE_EN_WAV = 2.00

ENTRADA = 0.30         # silencio antes de la primera palabra
GAP_MIN, GAP_MAX = 0.42, 0.62   # a cuánto se acotan las pausas ENTRE frases
LEAD = 0.35            # la imagen entra este pelín antes que su frase
COLA_LOGO = 4.40       # lo que dura el cierre después del último corte

# (frase, primer tramo, último tramo, escena que abre)  ── tramos 1..23 del
# detector con guarda, verificados uno a uno contra la estructura fina.
LINEAS = [
    ('How many of your trades actually followed your plan?',  1,  1, 'problema1'),
    ("Not the one you'd describe. The one you wrote down.",    2,  3, None),
    ('How many were revenge? How many were fear?',             4,  5, 'problema2'),
    ('Those days are over.',                                   6,  6, 'giro'),
    ('With Pre-Flight, you write down every confluence you '
     'actually use. Your setup, your words.',                  7,  9, 'lista'),
    ('Then you decide how many are enough to enter.',         10, 10, 'umbral'),
    ('And before you click, a traffic light answers: '
     'go, caution, or no.',                                   11, 15, 'semaforo'),
    ('Every check you log becomes your own numbers. Win rate. '
     'Expectancy. Profit factor. Drawdown.',                  16, 20, 'stats'),
    ('Trading more than one strategy? Put them side by side.', 21, 22, 'cmp'),
    ('The one that wins least is the one that pays most.',    23, 23, 'vuelta'),
]


def main():
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    if not os.path.exists(VOZ):
        sys.exit('falta la locución en %s' % VOZ)

    x = P.pcm(VOZ)
    t = P.tramos(x)
    if len(t) != 23:
        sys.exit('🔴 el detector ve %d tramos y el reparto está escrito para 23.\n'
                 '   La locución cambió: hay que rehacer LINEAS mirando la '
                 'estructura fina.' % len(t))

    # ── se rearma la pista moviendo SOLO las pausas entre frases ──
    piezas, cues, reloj = [], [], ENTRADA
    piezas.append(np.zeros(int(ENTRADA * SR)))
    for i, (txt, a, b, _) in enumerate(LINEAS):
        i0, i1 = int(t[a - 1][0] * SR), int(t[b - 1][1] * SR)
        bloque = x[i0:i1]              # contiguo: dentro de la frase, intacto
        cues.append((reloj, reloj + len(bloque) / float(SR)))
        piezas.append(bloque)
        reloj += len(bloque) / float(SR)
        if i < len(LINEAS) - 1:
            hueco_real = t[LINEAS[i + 1][1] - 1][0] - t[b - 1][1]
            g = min(GAP_MAX, max(GAP_MIN, hueco_real))
            piezas.append(np.zeros(int(g * SR)))
            reloj += g
    voz_pista = np.concatenate(piezas)
    fin_voz = reloj

    # ── el vídeo se corta donde manda la voz ──
    cortes, ultimo = {}, None
    for (txt, a, b, escena), (c0, c1) in zip(LINEAS, cues):
        if escena:
            cortes[escena] = round(max(0.0, c0 - LEAD), 2)
        ultimo = c1
    cortes['fin'] = round(ultimo + 0.55, 2)          # cuando arranca el cierre
    cortes['total'] = round(cortes['fin'] + COLA_LOGO, 2)

    print('locución original %.2f s · voz %.2f s' % (len(x) / SR, sum(b - a for a, b in t)))
    print('pista montada     %.2f s · cierre hasta %.2f s\n' % (fin_voz, cortes['total']))
    print('%-3s %-56s %7s %7s' % ('#', 'frase', 'entra', 'sale'))
    for (txt, a, b, escena), (c0, c1) in zip(LINEAS, cues):
        print('%-3d %-56s %6.2fs %6.2fs' % (LINEAS.index((txt, a, b, escena)) + 1,
                                            txt[:54], c0, c1))
    print('\ncortes del vídeo:', json.dumps(cortes, sort_keys=True))
    with io.open(TIEMPOS, 'w', encoding='utf-8') as f:
        f.write(json.dumps(cortes, indent=1, sort_keys=True).decode('utf-8')
                if sys.version_info[0] == 2 else json.dumps(cortes, indent=1, sort_keys=True))

    if '--montar' in sys.argv:
        # el generador lee _tiempos_narracion.json y se re-temporiza solo
        subprocess.run([sys.executable, os.path.join(RAIZ, 'tools', 'reel_preflight.py'),
                        '--solo-montar', '--mudo'], check=True)

    if not os.path.exists(MUDO):
        print('\n(falta %s — corre con --montar)' % MUDO)
        return

    # ── pista final: voz + marca sonora clavada en el logo ──
    pista = np.zeros(int(cortes['total'] * SR))
    n = min(len(voz_pista), len(pista))
    pista[:n] += voz_pista[:n]
    g = P.pcm(MARCA)
    # el logo asienta 0,5 s después del corte; el golpe del wav va en el 2,00
    i = int(max(0.0, cortes['fin'] + 0.50 - GOLPE_EN_WAV) * SR)
    n = min(len(g), len(pista) - i)
    pista[i:i + n] += g[:n] * MARCA_VOL

    pista = np.tanh(pista * 1.02)
    pista = pista / (np.abs(pista).max() + 1e-9) * 0.92

    # 🔑 LA COMPROBACIÓN QUE IMPORTA: se vuelve a medir la voz de la pista y se
    # compara con la del original. Es la prueba que faltaba la vez que se
    # publicó un reel con media frase evaporada.
    dentro = sum(b - a for a, b in P.tramos(pista[:int((fin_voz + .2) * SR)], 0.0))
    fuera = sum(b - a for a, b in P.tramos(x, 0.0))
    print('\nvoz original %.2f s → en la pista %.2f s   (%+.2f s)'
          % (fuera, dentro, dentro - fuera))
    if dentro < fuera - 0.15:
        sys.exit('🔴 SE PERDIÓ VOZ — no publicar')

    wav = os.path.join(REELS, '_pista_pf.wav')
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
