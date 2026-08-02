# -*- coding: utf-8 -*-
"""Publica el catálogo de marcos como archivos estáticos.

Los marcos se DIBUJAN en tools/plates_preview.py (ahí vive el catálogo y su
banco de pruebas), pero el navegador no puede leer un .py: este script escribe
cada placa como scalpel/static/plates/<slug>.svg + un manifiesto plates.json
con {slug: {name, ink}} que app.py consume para (a) saber qué slugs existen y
(b) decirle al cliente de qué color va el texto sobre cada placa.

    python3 tools/build_plates.py     # regenera TODO (idempotente)

Correr después de CUALQUIER cambio en plates_preview.py y commitear los
archivos generados — el server no regenera nada en runtime.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plates_preview import CANVAS_VIEWBOX, PLATES  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'scalpel', 'static', 'plates')

# preserveAspectRatio="none": la placa rellena el bloque del autor, que es un
# poco más ancho o angosto según la pantalla. El arte está autorado en el
# aspecto real (640x48), así que el estirón residual es de ~1.1x — invisible.
# (El bug histórico era autorar a 420x56 y estirar 2x; ver plates_preview.)
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s" '
       'preserveAspectRatio="none">%s</svg>')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    manifest = {}
    for slug, name, family, ink, art in PLATES:
        path = os.path.join(OUT_DIR, '%s.svg' % slug)
        with open(path, 'w') as fh:
            fh.write(SVG % (CANVAS_VIEWBOX, ' '.join(art.split())))
        manifest[slug] = {'name': name, 'ink': ink}
    with open(os.path.join(OUT_DIR, 'plates.json'), 'w') as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    print('escritas %d placas + plates.json en %s'
          % (len(manifest), os.path.relpath(OUT_DIR)))


if __name__ == '__main__':
    main()
