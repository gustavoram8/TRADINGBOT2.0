# -*- coding: utf-8 -*-
"""Convierte docs/acuerdo_colaboracion.md en un PDF listo para firmar.

    python3 tools/build_acuerdo_pdf.py

Se regenera tras CADA ronda de correcciones del acuerdo: el .md es la fuente
de verdad, el PDF es solo su presentacion. Nunca editar el PDF a mano.

Tipografia: Inter (la de la marca) en los titulos y Bitstream Charter en el
cuerpo. Charter porque es la unica serif del sistema con familia COMPLETA
—regular, cursiva, negrita y negrita cursiva—: DejaVu Serif no trae cursiva y
WeasyPrint acabaria inclinando las letras por calculo, que en un documento
que se imprime y se firma se nota.
"""
import base64
import io
import os
import re
import sys

import markdown
from PIL import Image
from weasyprint import HTML

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(RAIZ, 'docs', 'acuerdo_colaboracion.md')
PDF = os.path.join(RAIZ, 'docs', 'acuerdo_colaboracion.pdf')
FUENTES = os.path.join(RAIZ, 'tools', '.fuentes')

AZUL = '#004feb'
TINTA = '#15181f'


def caras():
    """@font-face de Inter y JetBrains Mono desde tools/.fuentes (gitignored).

    Si la carpeta no esta, se cae a las del sistema sin romper el documento.
    """
    reglas = []
    for fam, archivo, peso in (('InterDoc', 'Inter-400.ttf', 400),
                               ('InterDoc', 'Inter-700.ttf', 700),
                               ('InterDoc', 'Inter-800.ttf', 800),
                               ('MonoDoc', 'JetBrainsMono-400.ttf', 400)):
        ruta = os.path.join(FUENTES, archivo)
        if os.path.exists(ruta):
            reglas.append("@font-face{font-family:'%s';font-weight:%d;"
                          "src:url('file://%s')}" % (fam, peso, ruta))
    return '\n'.join(reglas)


def logo_uri():
    """El logotipo, recortado a su tinta y en data URI.

    Va recortado porque el PNG original mide 1536x1024 con el logotipo
    flotando en medio: sin recortar, el hueco transparente ocupa sitio y el
    logotipo queda descentrado al pie. Va en data URI y no como archivo
    para que el PDF no dependa de rutas al generarse desde otra carpeta.
    Devuelve (uri, proporcion ancho/alto) o (None, 0) si falta el archivo.
    """
    ruta = os.path.join(RAIZ, 'scalpel', 'static', 'logo_t.png')
    if not os.path.exists(ruta):
        return None, 0
    im = Image.open(ruta).convert('RGBA')
    im = im.crop(im.getbbox())
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    uri = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    return uri, im.width / float(im.height)


CSS = """
%(caras)s

@page {
  size: A4;
  margin: 22mm 20mm 20mm 20mm;
  @bottom-center {
    content: "P\\00E1gina " counter(page) " de " counter(pages);
    font-family: 'InterDoc', 'Liberation Sans', sans-serif;
    font-size: 8.4pt; color: #8b93a6; padding-top: 5mm;
  }
}
/* La primera pagina lleva el titulo, no necesita ademas la cabecera */
@page :first { @top-right { content: ""; } }
@page { @top-right {
    content: "Carta de acuerdo de colaboraci\\00F3n \\2014  Tradeable Academy";
    font-family: 'InterDoc', 'Liberation Sans', sans-serif;
    font-size: 8.4pt; color: #a7aebd; padding-bottom: 6mm;
} }

body {
  font-family: 'Bitstream Charter', 'Charter', 'Liberation Serif', serif;
  font-size: 11.5pt; line-height: 1.55; color: %(tinta)s;
  text-align: justify; hyphens: none;
  widows: 3; orphans: 3;
}

h1 {
  font-family: 'InterDoc', 'Liberation Sans', sans-serif;
  font-size: 21pt; font-weight: 800; letter-spacing: -0.015em;
  line-height: 1.15; margin: 0 0 2mm; color: #0d0f14; text-align: left;
}
h1 + p { margin-top: 0; }
h2 {
  font-family: 'InterDoc', 'Liberation Sans', sans-serif;
  font-size: 13.6pt; font-weight: 700; color: #0d0f14;
  margin: 9mm 0 3mm; padding-bottom: 1.6mm;
  border-bottom: 1.6pt solid %(azul)s;
  text-align: left; page-break-after: avoid; break-after: avoid;
}
h2 + p, h2 + ul, h2 + table { page-break-before: avoid; }

p { margin: 0 0 3.2mm; }
strong { font-weight: 700; }
em { font-style: italic; }

ul { margin: 0 0 3.4mm; padding-left: 6.5mm; }
li { margin-bottom: 1.4mm; padding-left: 1mm; }
li::marker { color: %(azul)s; }

hr {
  border: 0; border-top: 0.6pt solid #d3d8e2; margin: 7mm 0;
}

table {
  width: 100%%; border-collapse: collapse; margin: 3mm 0 5mm;
  font-size: 10.8pt; page-break-inside: avoid;
}
th {
  font-family: 'InterDoc', 'Liberation Sans', sans-serif;
  font-size: 9.4pt; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; text-align: left; color: #fff;
  background: %(azul)s; padding: 2.4mm 3mm;
}
td {
  padding: 2.2mm 3mm; border-bottom: 0.5pt solid #dfe3ec; text-align: left;
}
tr:last-child td { border-bottom: 0; }

/* El dibujo de la escalera: monoespaciada y en su caja */
pre {
  font-family: 'MonoDoc', 'DejaVu Sans Mono', monospace;
  font-size: 9.2pt; line-height: 1.5; text-align: left;
  background: #f4f6fa; border-left: 2.4pt solid %(azul)s;
  padding: 3.5mm 4mm; margin: 3mm 0 4mm; white-space: pre;
  page-break-inside: avoid;
}

/* Bloque de firmas: jamas partido entre dos paginas */
.firmas { page-break-inside: avoid; margin-top: 4mm; }
.firmas table { margin-top: 6mm; }
.firmas table td { padding: 2mm 6mm 2mm 0; vertical-align: bottom;
  border-bottom: 0; width: 50%%; }
/* El hueco donde se firma. La raya va en un <span> DENTRO de la celda, no
   en el borde de la celda: con border-collapse las dos celdas quedan
   pegadas y las rayas se sueldan en una sola linea de lado a lado, como si
   ambos firmaran encima del mismo renglon. */
.firmas tr.rubrica td { padding: 0; }
.firmas .raya {
  display: block; height: 22mm; margin-right: 14mm;
  border-bottom: 0.8pt solid #6f7789;
}
.firmas tr.rubrica + tr td { padding-top: 2.4mm; }

/* El logotipo cierra el documento, centrado al pie de la ultima pagina */
.sello { text-align: center; margin: 14mm 0 0; }
.sello img { height: 9mm; }

.cierre {
  font-size: 9.6pt; color: #5d6474; font-style: italic;
  text-align: left; margin-top: 6mm;
}
"""


def md_a_html(texto):
    html = markdown.markdown(texto, extensions=['tables', 'fenced_code',
                                                'sane_lists'])
    # La tabla de firmas nace con una cabecera vacia (| | |): se quita, o
    # el PDF muestra una franja azul sin texto encima de los nombres.
    html = re.sub(r'<thead>\s*<tr>\s*(<th[^>]*>\s*</th>\s*)+</tr>\s*</thead>',
                  '', html)
    # ...y se le abre arriba el hueco donde cada uno estampa su firma.
    html = html.replace('<tbody>\n<tr>\n<td><strong>[TU NOMBRE]',
                        '<tbody>\n<tr class="rubrica">'
                        '<td><span class="raya"></span></td>'
                        '<td><span class="raya"></span></td></tr>'
                        '\n<tr>\n<td><strong>[TU NOMBRE]')
    return html


def main():
    if not os.path.exists(MD):
        sys.exit('No encuentro %s' % MD)
    with open(MD, encoding='utf-8') as fh:
        texto = fh.read()

    cuerpo = md_a_html(texto)
    uri, _ = logo_uri()

    # El bloque final (firmas + nota del abogado) se envuelve para poder
    # pedirle a WeasyPrint que no lo parta en dos paginas. El logotipo cierra
    # el documento y va DENTRO de ese bloque: asi no puede quedar solo en una
    # pagina de mas, sin nada mas alrededor.
    if '<h2>Firmas</h2>' in cuerpo:
        cabeza, cola = cuerpo.split('<h2>Firmas</h2>', 1)
        sello = ('<div class="sello"><img src="%s" alt="Tradeable Academy">'
                 '</div>' % uri if uri else '')
        cuerpo = (cabeza + '<div class="firmas"><h2>Firmas</h2>' + cola
                  + sello + '</div>')
    cuerpo = cuerpo.replace('<p><em>Documento redactado',
                            '<p class="cierre"><em>Documento redactado')

    doc = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
           '<title>Carta de acuerdo de colaboracion</title>'
           '<style>%s</style></head><body>%s</body></html>'
           % (CSS % {'caras': caras(), 'azul': AZUL, 'tinta': TINTA}, cuerpo))

    HTML(string=doc, base_url=RAIZ).write_pdf(PDF)
    print('ok -> %s (%.0f KB)' % (PDF, os.path.getsize(PDF) / 1024.0))


if __name__ == '__main__':
    main()
