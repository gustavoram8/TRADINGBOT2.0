# -*- coding: utf-8 -*-
"""El acuerdo, en PDF legible.

Conversion a mano y no con una libreria generica de markdown porque el documento
tiene tres construcciones que esas librerias maquetan mal: la tabla de tramos, el
bloque de firmas y las viñetas dentro de apartados numerados.

⚠️ La primera version se colgo en un bucle infinito: una linea sangrada que NO
venia detras de una viñeta entraba en la rama de listas, no consumia nada y
dejaba el indice donde estaba. El arreglo no es parchear esa condicion sino
quitarle el problema de encima al parser: en una PRIMERA pasada se juntan las
continuaciones con su linea madre, y despues cada rama consume exactamente una
linea (salvo la tabla). Ademas hay un guardia que revienta si el indice no
avanza, para que un fallo asi se vea en vez de colgarse.
"""
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, Image, ListFlowable, ListItem,
                                Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

import os

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN = os.path.join(_RAIZ, 'docs', 'acuerdo_colaboracion.md')
DESTINO = os.path.join(_RAIZ, 'out', 'Acuerdo_de_colaboracion_Tradeable_Academy.pdf')
os.makedirs(os.path.dirname(DESTINO), exist_ok=True)

TINTA = colors.HexColor('#1b1c20')
SUAVE = colors.HexColor('#5c6274')
ORO = colors.HexColor('#a97e14')
LINEA = colors.HexColor('#d9dce3')

ss = getSampleStyleSheet()
E = {
    'h1': ParagraphStyle('h1', parent=ss['Title'], fontName='Helvetica-Bold',
                         fontSize=19, leading=24, textColor=TINTA,
                         spaceAfter=2, alignment=0),
    'h2': ParagraphStyle('h2', parent=ss['Heading2'], fontName='Helvetica-Bold',
                         fontSize=12.5, leading=16, textColor=ORO,
                         spaceBefore=15, spaceAfter=5),
    'p': ParagraphStyle('p', parent=ss['BodyText'], fontName='Helvetica',
                        fontSize=9.6, leading=14.2, textColor=TINTA,
                        alignment=TA_JUSTIFY, spaceAfter=7),
    'li': ParagraphStyle('li', parent=ss['BodyText'], fontName='Helvetica',
                         fontSize=9.6, leading=13.8, textColor=TINTA,
                         alignment=TA_JUSTIFY, spaceAfter=4),
    'celda': ParagraphStyle('celda', parent=ss['BodyText'], fontName='Helvetica',
                            fontSize=9.4, leading=13, textColor=TINTA,
                            spaceAfter=0),
    'nota': ParagraphStyle('nota', parent=ss['BodyText'], fontName='Helvetica-Oblique',
                           fontSize=8.6, leading=12.4, textColor=SUAVE,
                           alignment=TA_JUSTIFY, spaceBefore=4, spaceAfter=6),
}


def enriquece(t):
    """Markdown en linea -> etiquetas de reportlab. El orden importa: primero lo
    doble, o **negrita** se leeria como dos cursivas."""
    t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<i>\1</i>', t)
    t = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', t)
    return t


def junta_continuaciones(bruto):
    """Markdown se lee por BLOQUES, no por lineas.

    ⚠️ Dos fallos reales que motivan esto:
      · la primera version se colgaba (una linea sangrada que no seguia a una
        viñeta no consumia nada y dejaba el indice quieto);
      · la segunda no se colgaba pero maquetaba fatal: cada linea del origen
        salia como parrafo propio, con el texto en escalera, y una **negrita**
        partida entre dos lineas se imprimia con los asteriscos a la vista.

    Ambos desaparecen si el texto se agrupa ANTES: un bloque = un elemento, con
    sus lineas ya unidas. Lo unico que conserva sus lineas es la tabla, y las
    viñetas, que se separan por elemento.
    """
    bloques, actual = [], []
    for l in bruto.split('\n'):
        if l.strip():
            actual.append(l.rstrip())
        elif actual:
            bloques.append(actual); actual = []
    if actual:
        bloques.append(actual)

    fuera = []
    for b in bloques:
        if b[0].startswith('|'):
            fuera.append(('tabla', b))
        elif b[0].startswith('#'):
            fuera.append(('titulo', [b[0]]))
            resto = b[1:]
            if resto:
                fuera.append(('parrafo', [' '.join(x.strip() for x in resto)]))
        elif b[0].startswith('---'):
            fuera.append(('regla', []))
            resto = b[1:]
            if resto:
                fuera.append(('parrafo', [' '.join(x.strip() for x in resto)]))
        elif any(x.startswith('- ') for x in b):
            items = []
            for l in b:
                if l.startswith('- '):
                    items.append(l[2:].strip())
                elif items:
                    items[-1] += ' ' + l.strip()
                else:
                    fuera.append(('parrafo', [l.strip()]))
            fuera.append(('lista', items))
        else:
            fuera.append(('parrafo', [' '.join(x.strip() for x in b)]))
    return fuera


def construye():
    hist = []
    for clase, cuerpo in junta_continuaciones(open(ORIGEN, encoding='utf-8').read()):
        if clase == 'titulo':
            l = cuerpo[0]
            if l.startswith('## '):
                hist.append(Paragraph(enriquece(l[3:]), E['h2']))
            else:
                hist.append(Paragraph(enriquece(l.lstrip('# ')), E['h1']))
                hist.append(HRFlowable(width='100%', color=ORO, thickness=1.4,
                                       spaceBefore=7, spaceAfter=11))
        elif clase == 'regla':
            hist.append(HRFlowable(width='100%', color=LINEA, thickness=.7,
                                   spaceBefore=9, spaceAfter=9))
        elif clase == 'tabla':
            filas = []
            for l in cuerpo:
                celdas = [c.strip() for c in l.strip().strip('|').split('|')]
                if not set(''.join(celdas)) <= set('-: '):     # la fila de guiones
                    filas.append(celdas)
            if not filas:
                continue
            n = max(len(f) for f in filas)
            filas = [f + [''] * (n - len(f)) for f in filas]
            datos = [[Paragraph(enriquece(c), E['celda']) for c in f] for f in filas]
            t = Table(datos, colWidths=[166 * mm / n] * n, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('LINEBELOW', (0, 0), (-1, 0), .9, ORO),
                ('LINEBELOW', (0, 1), (-1, -2), .4, LINEA),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ]))
            hist.extend([Spacer(1, 4), t, Spacer(1, 10)])
        elif clase == 'lista':
            hist.append(ListFlowable(
                [ListItem(Paragraph(enriquece(x), E['li']), leftIndent=13)
                 for x in cuerpo],
                bulletType='bullet', start='\u2022', bulletColor=ORO,
                leftIndent=13, bulletFontSize=8, spaceAfter=7))
        else:
            t = cuerpo[0]
            estilo = E['nota'] if (t.startswith('*') and t.endswith('*')
                                   and '**' not in t) else E['p']
            hist.append(Paragraph(enriquece(t.strip('*') if estilo is E['nota'] else t),
                                  estilo))
    # una negrita partida entre lineas ya no puede llegar entera al PDF, pero se
    # comprueba igual: es el sintoma exacto del fallo anterior
    crudos = [f for f in hist if isinstance(f, Paragraph) and '**' in f.text]
    assert not crudos, 'quedaron asteriscos sin convertir'
    # La marca cierra el documento (pedido del dueno): el logo con la "a" azul,
    # centrado bajo las firmas. Recortado del aire transparente del PNG
    # original (1536x1024 con el arte en una franja de 1398x232).
    LOGO = os.path.join(_RAIZ, 'docs', 'assets', 'logo_acuerdo.png')
    ancho = 52 * mm
    alto = ancho * 232.0 / 1398.0
    img = Image(LOGO, width=ancho, height=alto)
    img.hAlign = 'CENTER'
    hist.extend([Spacer(1, 26), img])
    return hist


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(SUAVE)
    canvas.drawString(22 * mm, 12 * mm, 'Acuerdo de colaboración · Tradeable Academy')
    canvas.drawRightString(A4[0] - 22 * mm, 12 * mm, 'Página %d' % doc.page)
    canvas.setStrokeColor(LINEA)
    canvas.line(22 * mm, 16 * mm, A4[0] - 22 * mm, 16 * mm)
    canvas.restoreState()


doc = SimpleDocTemplate(DESTINO, pagesize=A4,
                        leftMargin=22 * mm, rightMargin=22 * mm,
                        topMargin=20 * mm, bottomMargin=22 * mm,
                        title='Acuerdo de colaboración — Tradeable Academy',
                        author='Tradeable Academy')
doc.build(construye(), onFirstPage=pie, onLaterPages=pie)
print('PDF escrito en', DESTINO)
