# -*- coding: utf-8 -*-
"""Candidatos a MARCA SONORA (audio logo) de Tradeable Academy.

Qué es esto: los 4-5 segundos de sonido que suenan cuando aparece el logo al
final de un vídeo. Es lo mismo que hace Netflix con su "TU-DUM" o Intel con sus
cinco notas — una firma que se reconoce sin mirar la pantalla. Se decide UNA
vez y luego se repite en todas las piezas para siempre, así que conviene
escuchar varias antes de casarse con ninguna.

CÓMO SE HACE AQUÍ. No hay ningún modelo de música de por medio: cada sonido se
SINTETIZA con matemáticas (senos, ruido filtrado, envolventes) y se escribe
como WAV. Eso tiene dos ventajas que no da una pista descargada:
  · es 100% nuestro — no hay licencia, ni derechos, ni riesgo de que una
    plataforma silencie el vídeo;
  · es reproducible y se puede afinar al milisegundo (subir una nota, alargar
    la cola, mover el golpe) volviendo a correr el script.

Cada candidato se entrega montado sobre los últimos segundos REALES del reel,
porque una marca sonora no se juzga aislada: se juzga con el golpe cayendo
exactamente donde el barrido descubre el logo.

    python3 tools/marca_sonora.py            # genera los candidatos
    python3 tools/marca_sonora.py --solo-audio   # sin montar el vídeo

⚠️ El impacto tiene que caer en el fotograma en que se completa el barrido a
   negro, no cuando empieza: si cae antes, el oído lo separa del logo y deja de
   leerse como una firma.
"""
from __future__ import print_function

import io
import os
import struct
import subprocess
import sys

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'out', 'marca_sonora')
REEL = os.path.join(RAIZ, 'out', 'reels', 'reel-tour.mp4')
SR = 48000
DUR = 6.0           # el clip completo
REEL_DESDE = 36.30  # para que GOLPE coincida con el barrido del reel
# ⚠️ 2,00 no es un número redondo elegido a ojo: se midió fotograma a fotograma
#    dónde ASIENTA el logo. El barrido empieza en 1,70 y a 1,90 todavía se ve
#    Tessera; el logotipo está entero a 2,05. Con el golpe en 1,70 el oído lo
#    oye ANTES de ver la marca y deja de leerse como una firma.
GOLPE = 2.00


# ══ utilidades de síntesis ═══════════════════════════════════════════════
def lienzo(dur=DUR):
    return np.zeros(int(SR * dur))


def t_de(n):
    return np.arange(n) / float(SR)


def env(n, ataque=0.004, caida=0.6, curva=2.2):
    """Envolvente percusiva: sube casi instantánea y cae exponencial."""
    t = t_de(n)
    a = np.clip(t / max(ataque, 1e-6), 0, 1)
    d = np.exp(-curva * t / max(caida, 1e-6))
    return a * d


def pon(buf, x, seg, gan=1.0):
    """Mezcla `x` dentro de `buf` empezando en el segundo `seg`."""
    i = int(seg * SR)
    n = min(len(x), len(buf) - i)
    if n > 0:
        buf[i:i + n] += x[:n] * gan
    return buf


def tono(f, dur, ataque=0.004, caida=0.6, curva=2.2, armonicos=(1.0,)):
    n = int(SR * dur)
    t = t_de(n)
    x = np.zeros(n)
    for k, amp in enumerate(armonicos, start=1):
        x += amp * np.sin(2 * np.pi * f * k * t)
    return x * env(n, ataque, caida, curva) / max(1.0, sum(armonicos))


def campana(f, dur, caida=1.6):
    """Campana: parciales INARMÓNICOS (no múltiplos exactos) — es justo eso
    lo que separa una campana de un pitido de microondas."""
    n = int(SR * dur)
    t = t_de(n)
    x = np.zeros(n)
    for mult, amp, cd in ((1.0, 1.0, 1.0), (2.76, .55, .55), (5.40, .32, .34),
                          (8.93, .18, .22), (13.3, .09, .16)):
        x += amp * np.sin(2 * np.pi * f * mult * t) * np.exp(-t / (caida * cd))
    return x / 2.1


def sub(f0, f1, dur, caida=0.9):
    """Golpe de sub-graves con caída de tono: el 'boom' de tráiler."""
    n = int(SR * dur)
    t = t_de(n)
    f = f1 + (f0 - f1) * np.exp(-4.5 * t / dur)
    fase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(fase) * env(n, 0.002, caida, 2.6)


def ruido(dur):
    return np.random.default_rng(7).standard_normal(int(SR * dur))


def paso_bajo(x, fc):
    """Un polo. Suficiente para quitar filo sin sonar a nada raro."""
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def paso_alto(x, fc):
    return x - paso_bajo(x, fc)


def whoosh(dur, fc0=400, fc1=6000, invertido=False):
    """Barrido de ruido. Se sintetiza como suma de dos bandas cruzándose, que
    es más barato que filtrar con frecuencia variable y suena igual."""
    n = int(SR * dur)
    r = ruido(dur)
    grave = paso_bajo(r, 700)
    agudo = paso_alto(paso_bajo(r, 9000), 2500)
    k = np.linspace(0, 1, n) ** 1.6
    if invertido:
        k = k[::-1]
    x = grave * (1 - k) + agudo * k
    forma = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.4
    return x * forma * 0.6


def eco(x, retardo=0.16, realim=0.42, veces=6):
    y = x.copy()
    d = int(retardo * SR)
    for k in range(1, veces + 1):
        i = d * k
        if i >= len(x):
            break
        y[i:] += x[:len(x) - i] * (realim ** k)
    return y


def cola(x, largo=1.1, mezcla=0.28):
    """Reverberación pobre pero honesta: convolución con ruido decreciente."""
    n = int(SR * largo)
    ir = np.random.default_rng(3).standard_normal(n) * np.exp(-4.0 * t_de(n) / largo)
    ir = paso_bajo(ir, 4200)
    hum = np.convolve(x, ir)[:len(x)]
    hum /= (np.max(np.abs(hum)) + 1e-9)
    return x * (1 - mezcla) + hum * mezcla


def normaliza(x, pico=0.89):
    x = np.tanh(x * 1.05)                      # limitador suave, sin recorte duro
    return x / (np.max(np.abs(x)) + 1e-9) * pico


def guarda_wav(x, ruta):
    d = (np.clip(x, -1, 1) * 32767).astype('<i2').tobytes()
    with io.open(ruta, 'wb') as f:
        f.write(b'RIFF' + struct.pack('<I', 36 + len(d)) + b'WAVEfmt ')
        f.write(struct.pack('<IHHIIHH', 16, 1, 1, SR, SR * 2, 2, 16))
        f.write(b'data' + struct.pack('<I', len(d)) + d)


# ══ los candidatos ═══════════════════════════════════════════════════════
# Nota base: RE (D) — grave, sobrio, ni triunfal ni triste.
D2, D3, A3, D4, Fs4, A4 = 73.42, 146.83, 220.00, 293.66, 369.99, 440.00


def c1_campana():
    """01 · CAMPANA — la campana de apertura del mercado, en versión sobria."""
    b = lienzo()
    pon(b, whoosh(GOLPE, invertido=False), 0.05, 0.30)
    pon(b, sub(90, 42, 1.5, 0.75), GOLPE, 0.85)
    pon(b, cola(campana(D4, 2.8, 1.7), 1.4, .32), GOLPE, 0.75)
    pon(b, cola(campana(A4, 2.4, 1.4), GOLPE + 0.14, .30), 0.0, 0.0)  # (no)
    pon(b, cola(campana(A4, 2.3, 1.3), 1.3, .30), GOLPE + 0.15, 0.42)
    return normaliza(b)


def c2_dos_notas():
    """02 · DOS NOTAS — intervalo ascendente limpio. Lo más 'marca' de todas:
    es lo que se puede tararear, que es la prueba de fuego de un audio logo."""
    b = lienzo()
    pon(b, whoosh(GOLPE * .9, invertido=True), 0.10, 0.22)
    pon(b, sub(96, 45, 1.4, 0.8), GOLPE, 0.90)
    n1 = tono(D3, 1.5, .006, .9, 2.0, (1.0, .38, .16, .07))
    n2 = tono(A3, 2.4, .006, 1.5, 1.6, (1.0, .42, .20, .09))
    pon(b, cola(n1, 1.0, .24), GOLPE, 0.60)
    pon(b, cola(n2, 1.6, .30), GOLPE + 0.26, 0.62)
    pon(b, cola(tono(D4, 2.2, .01, 1.4, 1.6, (1.0, .25)), 1.5, .34),
        GOLPE + 0.26, 0.26)
    return normaliza(b)


def c3_precision():
    """03 · PRECISIÓN — tres clics que aceleran y encajan en un golpe: suena a
    mecanismo que cierra. Es la idea de 'plan, no impulso' hecha sonido."""
    b = lienzo()
    for k, seg in enumerate((GOLPE - 0.62, GOLPE - 0.34, GOLPE - 0.15)):
        clic = paso_alto(ruido(0.05), 1800) * env(int(SR * .05), .0008, .02, 3.0)
        pon(b, clic, seg, 0.30 + 0.12 * k)
    pon(b, sub(104, 44, 1.3, 0.7), GOLPE, 0.92)
    pon(b, cola(tono(D3, 2.6, .004, 1.7, 1.5, (1.0, .30, .12)), 1.3, .26),
        GOLPE, 0.66)
    pon(b, cola(tono(Fs4, 1.8, .004, 1.0, 1.9, (1.0, .18)), 1.2, .34),
        GOLPE + 0.02, 0.20)
    return normaliza(b)


def c4_grafito():
    """04 · GRAFITO — barrido de aire y un boom profundo. Cinematográfico:
    el que mejor funcionaría en un anuncio pagado."""
    b = lienzo()
    pon(b, whoosh(GOLPE + .1, invertido=False), 0.02, 0.42)
    pon(b, sub(120, 38, 2.2, 1.15), GOLPE, 1.00)
    brillo = paso_alto(ruido(0.9), 5200) * env(int(SR * .9), .001, .28, 3.2)
    pon(b, cola(brillo, 1.3, .34), GOLPE, 0.22)
    pon(b, cola(tono(D2, 2.8, .01, 2.0, 1.4, (1.0, .5, .2)), 1.4, .22),
        GOLPE, 0.34)
    return normaliza(b)


def c5_teseracto():
    """05 · TESERACTO — ping metálico con eco sobre un zumbido bajo. Es el que
    hereda la identidad de Synapse y de la Cámara de Tessera."""
    b = lienzo()
    n = int(SR * (GOLPE + 0.3))
    drone = (np.sin(2 * np.pi * D2 * t_de(n)) * 0.5
             + np.sin(2 * np.pi * D2 * 1.5 * t_de(n)) * 0.2)
    drone *= np.linspace(0, 1, n) ** 2
    pon(b, drone, 0.0, 0.40)
    pon(b, sub(84, 41, 1.6, 0.9), GOLPE, 0.70)
    ping = campana(A4 * 1.5, 2.2, 1.1)
    pon(b, cola(eco(ping, 0.185, 0.40, 6), 1.5, .34), GOLPE, 0.52)
    pon(b, cola(tono(D3, 2.6, .02, 1.9, 1.3, (1.0, .35, .14)), 1.4, .26),
        GOLPE, 0.44)
    return normaliza(b)


def c6_ascenso():
    """06 · ASCENSO — un riser que sube y remata en acorde. El más 'lanzamiento
    de producto'; también el más común, y por eso el menos distintivo."""
    b = lienzo()
    n = int(SR * GOLPE)
    t = t_de(n)
    f = 110 * (2 ** (2.6 * (t / GOLPE) ** 1.7))
    riser = np.sin(2 * np.pi * np.cumsum(f) / SR) * (np.linspace(0, 1, n) ** 2.4)
    pon(b, riser, 0.0, 0.30)
    pon(b, whoosh(GOLPE, invertido=True), 0.0, 0.26)
    pon(b, sub(112, 40, 1.8, 1.0), GOLPE, 0.95)
    for f0, g in ((D3, .55), (Fs4, .26), (A4, .20)):
        pon(b, cola(tono(f0, 2.4, .005, 1.5, 1.5, (1.0, .30, .12)), 1.5, .32),
            GOLPE, g)
    return normaliza(b)


# ══ LA MARCA SONORA ELEGIDA: EL 03, PELADO ═══════════════════════════════
# De los seis, el dueño eligió el 03 y fue quitándole capas en dos pasadas:
#   · "el principio es como un WOOOOP, eso no va" → era el `sub(104, 44, ...)`,
#     un golpe de graves cuyo TONO CAE de 104 a 44 Hz. Una caída de tono es
#     exactamente lo que el oído lee como "wup".
#   · "se escucha algo como unas metras cayendo, como si se te cayera una
#     moneda al suelo 2 o 3 veces" → eran los tres clics que aceleraban.
# Queda SOLO la cuerda. Y eso es lo correcto para un audio logo: cuanto menos
# elementos, más fácil de reconocer y más difícil de confundir con otro.
#
# ⚠️ DOS LECCIONES, y la segunda me costó dos rondas:
#   1. Cuando alguien aprueba un sonido y pide quitarle UN elemento, se quita
#      ese elemento — no se reconstruye el sonido "mejor". Se intentó rehacer
#      la cuerda con Karplus-Strong para poder alargarla y el dueño lo rechazó
#      de plano: sonaba a otra cosa. Por eso `largo` toca SOLO los tiempos de
#      caída, nunca cómo se genera el timbre.
#   2. Yo defendí los clics ("eso no era el wooop") en vez de preguntarme si
#      además sobraban. Tenía razón en el diagnóstico y me equivoqué en la
#      conclusión: que un elemento no sea el que molestaba no significa que
#      haga falta.


# Los tres elementos del 03, para poder quitarlos de uno en uno sin reescribir
# nada: (1) los CLICS que aceleran, que el dueño describió como "unas metras
# cayendo, como si se te cayera una moneda al suelo 2 o 3 veces" → fuera; (2)
# el GOLPE DE GRAVES con caída de tono, el "wooop" → fuera; (3) la CUERDA, que
# es lo único que se queda. `largo` solo estira los tiempos de caída.
def c3_variante(clics=False, woop=False, largo=False):
    b = lienzo()
    if clics:
        for k, seg in enumerate((GOLPE - 0.62, GOLPE - 0.34, GOLPE - 0.15)):
            clic = (paso_alto(ruido(0.05), 1800)
                    * env(int(SR * .05), .0008, .02, 3.0))
            pon(b, clic, seg, 0.30 + 0.12 * k)
    if woop:
        pon(b, sub(104, 44, 1.3, 0.7), GOLPE, 0.92)
    d1, c1, r1 = (4.0, 2.9, 1.9) if largo else (2.6, 1.7, 1.3)
    d2, c2, r2 = (3.0, 1.9, 1.7) if largo else (1.8, 1.0, 1.2)
    pon(b, cola(tono(D3, d1, .004, c1, 1.5, (1.0, .30, .12)), r1, .26),
        GOLPE, 0.66)
    pon(b, cola(tono(Fs4, d2, .004, c2, 1.9, (1.0, .18)), r2, .34),
        GOLPE + 0.02, 0.20)
    return normaliza(b)


CANDIDATOS = [
    ('01_campana', c1_campana), ('02_dos_notas', c2_dos_notas),
    ('03_precision', c3_precision), ('04_grafito', c4_grafito),
    ('05_teseracto', c5_teseracto), ('06_ascenso', c6_ascenso),
    # los dos que quedan vivos: solo la cuerda, corta y larga
    ('03D_solo_cuerda', lambda: c3_variante()),
    ('03E_solo_cuerda_larga', lambda: c3_variante(largo=True)),
]


def main():
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(SALIDA, exist_ok=True)
    solo_audio = '--solo-audio' in sys.argv
    for nombre, fn in CANDIDATOS:
        wav = os.path.join(SALIDA, nombre + '.wav')
        guarda_wav(fn(), wav)
        mp3 = os.path.join(SALIDA, nombre + '.mp3')
        subprocess.run([ff, '-y', '-loglevel', 'error', '-i', wav,
                        '-codec:a', 'libmp3lame', '-b:a', '192k', mp3],
                       check=True)
        if not solo_audio and os.path.exists(REEL):
            dest = os.path.join(SALIDA, nombre + '.mp4')
            subprocess.run([ff, '-y', '-loglevel', 'error',
                            '-ss', '%.2f' % REEL_DESDE, '-t', '%.2f' % DUR,
                            '-i', REEL, '-i', wav,
                            '-map', '0:v:0', '-map', '1:a:0',
                            '-c:v', 'libx264', '-crf', '20',
                            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                            '-shortest', '-movflags', '+faststart', dest],
                           check=True)
        print('  %-14s %s' % (nombre, SALIDA))
    print('listo:', SALIDA)


if __name__ == '__main__':
    main()
