# -*- coding: utf-8 -*-
"""El mismo reel del tour, re-encuadrado para TIKTOK.

No re-graba nada: reutiliza `_crudo-tour.webm` y sus marcas, y solo vuelve a
montar la capa de texto dentro de la caja segura de TikTok.

🔑 Por qué hace falta una versión aparte, medido sobre los fotogramas reales:

  1. RECORTE LATERAL. TikTok llena la pantalla. En un teléfono 19.5:9 un vídeo
     9:16 se amplía hasta cubrir el alto y se pierden ~118 px de CADA lado.
     El titular arrancaba en x=71 — o sea, DENTRO de lo que se corta. Eso es
     lo que el dueño veía como "la parte izquierda se corta".
  2. INTERFAZ ENCIMA. Abajo van usuario, texto y música (~440 px); a la
     derecha la columna de botones (~200 px); arriba las pestañas (~190 px).
     El bloque de texto bajaba hasta y=1664, casi 250 px dentro de esa zona.

  Caja segura resultante:  x 158-762   ·   y 190-1480
  Donde vivía el texto:    x  71-986   ·   y 1476-1664

⚠️ Instagram NO necesita esto: su interfaz inferior es más baja y no recorta
   los lados. Por eso el reel original se queda como está y esto es un archivo
   NUEVO — no se pisa `reel-tour.mp4`.

Uso:  python3 tools/reel_tiktok.py
"""
from __future__ import print_function
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reel_tour as R                                    # noqa: E402

# ── la caja segura, en píxeles del lienzo de 1080×1920 ──
CROP = 118          # se pierde por lado en un teléfono alto
UI_ABAJO = 440      # usuario + texto + música + barra de progreso
UI_DER = 200        # columna de botones
UI_ARRIBA = 190     # pestañas "Siguiendo / Para ti"

IZQ = CROP + 42                       # 160
DER = CROP + UI_DER + 2               # 320  → el texto termina en x=760
ABAJO = UI_ABAJO + 40                 # 480  → el texto no baja de y=1440

CAMBIOS = [
    # el bloque de titular + subtítulo entra entero en la caja segura
    ('#rot{position:absolute;left:70px;right:70px;bottom:250px}',
     '#rot{position:absolute;left:%dpx;right:%dpx;bottom:%dpx}' % (IZQ, DER, ABAJO)),
    # ⚠️ la columna pasa de 940 a 600 px de ancho: con 72px el titular se iba a
    # cuatro líneas. Se baja a 64 y el subtítulo a 29 para conservar el ritmo.
    ('#rot .g{font:900 72px/1.02 Inter,sans-serif;',
     '#rot .g{font:900 64px/1.04 Inter,sans-serif;'),
    ('#rot .p{margin-top:16px;font:500 31px/1.35 Inter,sans-serif;',
     '#rot .p{margin-top:14px;font:500 29px/1.35 Inter,sans-serif;'),
    # el número de paso caía justo debajo de los botones de TikTok
    ("#num{position:absolute;right:70px;top:120px;",
     "#num{position:absolute;right:%dpx;top:%dpx;" % (DER, UI_ARRIBA + 20)),
    # la intro es texto a sangre: sin este margen se le comen las primeras letras
    ('justify-content:center;padding:0 88px}',
     'justify-content:center;padding:0 %dpx}' % IZQ),
    ('#intro h1{font:900 116px/0.96 Inter,sans-serif;',
     '#intro h1{font:900 104px/0.98 Inter,sans-serif;'),
    # el aviso legal del cierre estaba dentro de la zona del texto de TikTok
    ('#out .l{position:absolute;bottom:140px;',
     '#out .l{position:absolute;bottom:%dpx;' % (UI_ABAJO + 60)),
    # una barra de progreso pegada al borde inferior la tapa la de TikTok
    ('#bar{position:absolute;left:0;bottom:0;',
     '#bar{position:absolute;left:0;bottom:%dpx;' % (UI_ABAJO + 10)),
]

ORIGINAL = os.path.join(R.SALIDA, 'reel-tour.mp4')
DESTINO = os.path.join(R.SALIDA, 'reel-tour-tiktok.mp4')
CON_AUDIO = os.path.join(R.SALIDA, 'reel-tour-narrado.mp4')
FINAL = os.path.join(R.SALIDA, 'reel-tour-tiktok-narrado.mp4')


def parchea():
    doc = R.PAGINA
    for viejo, nuevo in CAMBIOS:
        if viejo not in doc:
            sys.exit('🔴 no encontré en el montaje:\n   %s\n'
                     'El generador cambió; hay que revisar este parche.' % viejo)
        doc = doc.replace(viejo, nuevo)
    R.PAGINA = doc
    print('montaje parcheado: caja segura x %d-%d · y %d-%d'
          % (IZQ, R.W - DER, UI_ARRIBA, R.H - ABAJO))


def main():
    if not os.path.exists(R.CRUDO):
        sys.exit('falta %s — hay que volver a grabar con reel_tour.py' % R.CRUDO)

    # 🔴 monta() escribe SIEMPRE en reel-tour.mp4. Se aparta el original antes
    # de tocar nada: el reel de Instagram ya está publicado y no se pisa.
    guardado = ORIGINAL + '.guardado'
    if os.path.exists(ORIGINAL):
        shutil.move(ORIGINAL, guardado)

    try:
        parchea()
        R.monta()
        shutil.move(ORIGINAL, DESTINO)
    finally:
        if os.path.exists(guardado):
            shutil.move(guardado, ORIGINAL)

    # el audio ya existe: se copia tal cual, sin recodificar
    if os.path.exists(CON_AUDIO):
        ff = __import__('imageio_ffmpeg').get_ffmpeg_exe()
        subprocess.run([ff, '-y', '-loglevel', 'error', '-i', DESTINO,
                        '-i', CON_AUDIO, '-map', '0:v:0', '-map', '1:a:0',
                        '-c:v', 'copy', '-c:a', 'copy', '-shortest',
                        FINAL], check=True)
        print('listo con audio:', FINAL,
              '· %.1f MB' % (os.path.getsize(FINAL) / 1e6))
    else:
        print('listo (sin audio):', DESTINO)


if __name__ == '__main__':
    main()
