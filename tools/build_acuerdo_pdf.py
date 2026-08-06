# -*- coding: utf-8 -*-
"""Genera el PDF del acuerdo de colaboración con el socio.

    python3 tools/build_acuerdo_pdf.py [salida.pdf]

🔴 POR QUÉ ESTE ARCHIVO ESTÁ EN EL REPO. El acuerdo se redactó el 2026-08-04 y
vivía SOLO en un directorio temporal del contenedor y en el PC del dueño. Él
borró su copia dando por hecho que yo la conservaba — y un contenedor se
recicla sin avisar. Ahora la fuente (docs/acuerdo_colaboracion.md) y este
generador viven en git, así que el documento se puede reconstruir siempre.

El texto vive en el Markdown; aquí solo se le da forma. Para cambiar el
acuerdo se edita el .md y se vuelve a correr esto.
"""
import html as _html
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTE = os.path.join(RAIZ, 'docs', 'acuerdo_colaboracion.md')

# Réplica del aspecto original: Helvetica, títulos dorados, texto justificado,
# reglas finas doradas y pie con el nombre del documento.
CSS = """
@page {
  size: A4; margin: 20mm 18mm 18mm 18mm;
  @bottom-left  { content: "Acuerdo de colaboración · Tradeable Academy";
                  font-family: Helvetica, Arial, sans-serif;
                  font-size: 7.5pt; color: #8a8f9e; }
  @bottom-right { content: "Página " counter(page);
                  font-family: Helvetica, Arial, sans-serif;
                  font-size: 7.5pt; color: #8a8f9e; }
}
body { font-family: Helvetica, Arial, sans-serif; font-size: 9.5pt;
       line-height: 1.62; color: #22252e; }
h1 { font-size: 21pt; font-weight: bold; color: #16181f; margin-bottom: 9pt;
     padding-bottom: 9pt; border-bottom: 1.5pt solid #b8860b; }
h2 { font-size: 12.5pt; font-weight: bold; color: #b8860b;
     margin: 19pt 0 8pt; page-break-after: avoid; }
p  { margin-bottom: 8pt; text-align: justify; }
strong { color: #16181f; }
ul { margin: 0 0 8pt 14pt; padding: 0; }
li { margin-bottom: 5pt; text-align: justify; padding-left: 3pt; }
li::marker { color: #b8860b; }
hr { border: none; border-top: 1px solid #e0e3ea; margin: 16pt 0; }
table { width: 100%; border-collapse: collapse; margin: 4pt 0 10pt; }
th { text-align: left; font-weight: normal; color: #5a6070; font-size: 9pt;
     padding: 5pt 4pt; border-bottom: 1.2pt solid #b8860b; }
td { padding: 6pt 4pt; border-bottom: 1px solid #e8eaf0; }
em { color: #5a6070; }
/* El bloque de firmas NO se puede partir: en la primera versión los nombres
   quedaron en una página y las líneas de "Fecha: ____" solas en la siguiente,
   que en un documento que se firma se lee como una hoja suelta. */
.firmas { page-break-inside: avoid; }
.firmas td { padding: 9pt 4pt; }
"""


def inline(t):
    """**negrita**, *cursiva* y escapado. Nada más: el documento no usa más."""
    t = _html.escape(t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t, flags=re.S)
    t = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', t)
    return t


def md_a_html(md):
    """Subconjunto de Markdown que usa el acuerdo: #, ##, -, tablas, ---."""
    out, i = [], 0
    lineas = md.split('\n')
    while i < len(lineas):
        ln = lineas[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        if s == '---':
            out.append('<hr/>')
            i += 1
            continue
        if s.startswith('## '):
            out.append('<h2>%s</h2>' % inline(s[3:]))
            i += 1
            continue
        if s.startswith('# '):
            out.append('<h1>%s</h1>' % inline(s[2:]))
            i += 1
            continue
        if s.startswith('|'):
            filas = []
            while i < len(lineas) and lineas[i].strip().startswith('|'):
                filas.append([c.strip() for c in
                              lineas[i].strip().strip('|').split('|')])
                i += 1
            # La 2ª fila de una tabla Markdown es el separador (---|---)
            sep = len(filas) > 1 and set(''.join(filas[1])) <= set('-: ')
            cuerpo = filas[2:] if sep else filas
            # ⚠️ La tabla de firmas declara su cabecera VACÍA (`| | |`). Una
            # lista de celdas vacías sigue siendo verdadera en Python, así que
            # tratarla como cabecera real pintaba un <thead> con su regla
            # dorada suelta encima de las fechas Y dejaba el bloque sin la
            # clase que impide partirlo entre páginas.
            cab = (filas[0] if sep and any(c.strip() for c in filas[0])
                   else None)
            firmas = ' class="firmas"' if cab is None else ''
            t = ['<table%s>' % firmas]
            if cab:
                t.append('<thead><tr>%s</tr></thead>'
                         % ''.join('<th>%s</th>' % inline(c) for c in cab))
            t.append('<tbody>%s</tbody>' % ''.join(
                '<tr>%s</tr>' % ''.join('<td>%s</td>' % inline(c) for c in f)
                for f in cuerpo))
            t.append('</table>')
            out.append(''.join(t))
            continue
        if s.startswith('- '):
            items = []
            while i < len(lineas) and lineas[i].strip().startswith('- '):
                trozo = [lineas[i].strip()[2:]]
                i += 1
                # continuación indentada de la misma viñeta
                while (i < len(lineas) and lineas[i].startswith('  ')
                       and lineas[i].strip()
                       and not lineas[i].strip().startswith('- ')):
                    trozo.append(lineas[i].strip())
                    i += 1
                items.append(' '.join(trozo))
            out.append('<ul>%s</ul>'
                       % ''.join('<li>%s</li>' % inline(x) for x in items))
            continue
        # párrafo: hasta la próxima línea en blanco o marcador
        parr = []
        while i < len(lineas) and lineas[i].strip() and not re.match(
                r'^\s*(#{1,2} |- |\||---\s*$)', lineas[i]):
            parr.append(lineas[i].strip())
            i += 1
        if parr:
            out.append('<p>%s</p>' % inline(' '.join(parr)))
    return '\n'.join(out)


def main():
    salida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        RAIZ, 'out', 'Acuerdo_de_colaboracion_Tradeable_Academy.pdf')
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    md = open(FUENTE, encoding='utf-8').read()
    from weasyprint import HTML, CSS as WCSS
    doc = ('<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
           '<title>Acuerdo de colaboración — Tradeable Academy</title></head>'
           '<body>%s</body></html>' % md_a_html(md))
    HTML(string=doc).write_pdf(salida, stylesheets=[WCSS(string=CSS)])
    print('PDF: %s (%d KB)' % (salida, os.path.getsize(salida) // 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())
