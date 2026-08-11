# -*- coding: utf-8 -*-
"""Convierte un .md del repo en un PDF presentable, con la hoja de estilo de la
marca (azul de titulares, dorado en las citas, mono en el código).

Existe porque los documentos que se le pasan a OTRA persona —el guion a un
narrador, el plan de publicación a quien lleve las redes— se leen en el teléfono
y un .md ahí se ve como código.

    python3 tools/md_a_pdf.py docs/reel_narracion.md out/Guion.pdf
"""
from __future__ import print_function

import io
import os
import re
import sys

import markdown
from weasyprint import CSS, HTML

HOJA = """
@page { size: A4; margin: 18mm 16mm; @bottom-center {
  content: counter(page); font: 9pt Helvetica; color:#8a8f9a; } }
body { font: 10.5pt/1.55 Helvetica, Arial, sans-serif; color:#1d2129; }
h1 { font-size: 19pt; color:#004feb; border-bottom:2px solid #004feb;
     padding-bottom:5px; margin:22pt 0 10pt; page-break-after:avoid; }
h1:first-child { margin-top:0; }
h2 { font-size: 13pt; margin:16pt 0 6pt; color:#0b0d12; page-break-after:avoid; }
h3 { font-size: 11pt; margin:12pt 0 4pt; color:#3a3f4a; page-break-after:avoid; }
blockquote { margin:6pt 0 8pt; padding:8pt 12pt; background:#f4f6fa;
  border-left:3px solid #c9a227; font-size:10pt; }
blockquote p { margin:0 0 5pt; } blockquote p:last-child { margin:0; }
table { border-collapse:collapse; width:100%; margin:8pt 0; font-size:9.5pt; }
th,td { border:1px solid #d5dae3; padding:5pt 7pt; text-align:left;
        vertical-align:top; }
th { background:#eef1f7; }
/* 🔑 las filas del guion NO se parten entre paginas: una linea de narracion
   cortada a la mitad obliga a pasar la hoja mientras se locuta */
tr { page-break-inside:avoid; }
code { background:#eef1f7; padding:1px 4px; border-radius:3px; font-size:9pt; }
hr { border:none; border-top:1px solid #d5dae3; margin:14pt 0; }
strong { color:#0b0d12; }
ul { margin:5pt 0 5pt 14pt; } li { margin:2pt 0; }
"""


# 🔴 En Markdown, una almohadilla al principio de línea es un TÍTULO. Una línea
# de hashtags —`#trading #ict …`— se convertía en un <h1> gigante, y encima
# perdía la primera almohadilla: en el PDF parecía que los captions no llevaban
# hashtags. Lo cazó el dueño leyéndolo.
# Un título SIEMPRE lleva espacio tras las almohadillas (`# Título`, `### A`),
# así que se escapa solo la que va pegada a una palabra. Con esto el .md sigue
# limpio y copiable — que es lo que importa, porque de ahí se pega el caption.
HASHTAG = re.compile(r'(?m)^((?:> ?)*)#(?=[^\s#])')


def convierte(origen, destino):
    md = HASHTAG.sub(r'\1\\#', io.open(origen, encoding='utf-8').read())
    cuerpo = markdown.markdown(md, extensions=['tables', 'sane_lists'])
    os.makedirs(os.path.dirname(destino) or '.', exist_ok=True)
    HTML(string='<html><meta charset="utf-8"><body>%s</body></html>'
         % cuerpo).write_pdf(destino, stylesheets=[CSS(string=HOJA)])
    return destino


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    d = convierte(sys.argv[1], sys.argv[2])
    print('%s · %.0f KB' % (d, os.path.getsize(d) / 1024))
