# -*- coding: utf-8 -*-
"""Genera el PDF de la cláusula del acuerdo comercial.

    python3 tools/build_clausula_pdf.py [salida.pdf]

El acuerdo comercial completo NO vive en este repo (lo tiene el dueño). Esto
maqueta la cláusula que excluye el PDF de Synapse —y todo producto de compra
única— de la base comisionable del aliado, para anexarla o pegarla en el
documento final.

El texto es el de docs/clausula_synapse_pdf.md; aquí solo se le da forma de
documento legal. Si cambia el .md, volver a correr esto.
"""
import os
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOY = datetime.now(timezone.utc).strftime('%d/%m/%Y')

CSS = """
@page {
  size: A4; margin: 22mm 20mm 20mm 20mm;
  @bottom-center {
    content: "Página " counter(page) " de " counter(pages);
    font-family: Georgia, serif; font-size: 8.5pt; color: #767b8a;
  }
  @bottom-right {
    content: "Tradeable Academy"; font-family: Georgia, serif;
    font-size: 8.5pt; color: #767b8a;
  }
}
body { font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt;
       line-height: 1.62; color: #1b1e28; }
.doc-head { border-bottom: 2px solid #1b1e28; padding-bottom: 12pt;
            margin-bottom: 20pt; }
.eyebrow { font-family: Helvetica, Arial, sans-serif; font-size: 8pt;
           letter-spacing: .18em; text-transform: uppercase; color: #5a6070;
           margin-bottom: 6pt; }
h1 { font-size: 17pt; line-height: 1.28; margin-bottom: 8pt; font-weight: bold; }
.meta { font-family: Helvetica, Arial, sans-serif; font-size: 8.5pt;
        color: #5a6070; }
.nota { background: #f4f6fa; border-left: 3px solid #8a91a5;
        padding: 10pt 13pt; margin-bottom: 20pt;
        font-family: Helvetica, Arial, sans-serif; font-size: 9pt;
        line-height: 1.55; color: #333a49; }
.nota b { color: #1b1e28; }
h2 { font-size: 11.5pt; margin: 20pt 0 9pt; font-weight: bold;
     page-break-after: avoid; }
p { margin-bottom: 9pt; text-align: justify; }
.sub { margin-bottom: 9pt; text-align: justify; }
.sub b.n { font-weight: bold; }
/* ⚠️ WeasyPrint ignora el atributo type="a" del HTML: sin esto los literales
   salen «1. 2. 3.» y el texto que remite a «el literal b)» deja de cuadrar.
   La letra se fija por CSS. */
ol.lit { margin: 0 0 9pt 20pt; padding: 0; list-style-type: lower-alpha; }
ol.lit li { margin-bottom: 7pt; text-align: justify; padding-left: 3pt; }
ol.lit li::marker { font-weight: bold; }
.firma { margin-top: 34pt; padding-top: 14pt; border-top: 1px solid #ccd1dc;
         font-family: Helvetica, Arial, sans-serif; font-size: 8.5pt;
         color: #5a6070; }
"""

CUERPO = """
<div class="doc-head">
  <div class="eyebrow">Anexo al Acuerdo Comercial</div>
  <h1>Productos excluidos del régimen de comisiones</h1>
  <div class="meta">Tradeable Academy &nbsp;·&nbsp; Documento preparado el %(hoy)s</div>
</div>

<div class="nota">
  <b>Cómo usar este documento.</b> El texto siguiente está redactado para
  incorporarse al Acuerdo Comercial como una cláusula más. Sustituya los
  guiones bajos <b>(___)</b> por el número correlativo que le corresponda en
  el documento final y verifique que las remisiones internas
  («cláusula ___.1») queden con ese mismo número. Puede incorporarse en el
  cuerpo del acuerdo o firmarse como anexo; en este último caso, añada al
  final la fórmula de incorporación por referencia que utilice su acuerdo.
</div>

<h2>CLÁUSULA ___. PRODUCTOS EXCLUIDOS DEL RÉGIMEN DE COMISIONES</h2>

<p class="sub"><b class="n">___.1. Alcance de la base comisionable.</b> Las
comisiones pactadas en el presente Acuerdo se calculan única y exclusivamente
sobre los pagos efectivamente percibidos por concepto de <b>planes de
suscripción</b> de la plataforma (denominados a la fecha «Standard» y
«Premium»), conforme a los tramos, porcentajes y condiciones establecidos en
las cláusulas precedentes. Ningún otro producto, presente o futuro, integra la
base comisionable, salvo pacto expreso, escrito y firmado por ambas partes que
así lo establezca.</p>

<p class="sub"><b class="n">___.2. Exclusión expresa de productos de compra
única.</b> Quedan expresamente excluidos del régimen de comisiones, sin que
generen derecho a retribución, participación ni contraprestación alguna a
favor del Aliado Comercial:</p>

<ol class="lit" type="a">
  <li>el producto digital denominado <b>«Biblioteca Synapse»</b> o
      <b>«Synapse Library»</b> (documento PDF descargable), en cualquiera de
      sus idiomas, ediciones, precios o versiones presentes o futuras;</li>
  <li>los artículos cosméticos de la plataforma (temas visuales o «camos»,
      marcos de perfil y cursores), adquiridos individualmente o en carrito;
      y</li>
  <li>cualquier otro producto de pago único que la plataforma ofrezca o llegue
      a ofrecer, entendiéndose por tal todo aquel cuyo precio se abona una sola
      vez y no constituye una suscripción periódica.</li>
</ol>

<p class="sub"><b class="n">___.3. Irrelevancia del origen del cliente y del
uso del código.</b> La exclusión anterior opera con independencia de que el
comprador del producto excluido: (i) haya llegado a la plataforma por gestión,
promoción o enlace del Aliado Comercial; (ii) sea un cliente atribuido al
Aliado Comercial conforme a la cláusula de atribución de este Acuerdo; o (iii)
hubiese empleado o intentado emplear el código promocional del Aliado
Comercial en la compra. El uso del código en productos excluidos no genera
comisión, no consume posición en la escala de comisiones ni altera la
atribución del cliente.</p>

<p class="sub"><b class="n">___.4. Preservación de la atribución.</b> La
adquisición de productos excluidos por parte de un cliente atribuido al Aliado
Comercial no modifica, suspende ni extingue dicha atribución respecto de los
planes de suscripción, que continuará rigiéndose por las cláusulas
correspondientes de este Acuerdo.</p>

<p class="sub"><b class="n">___.5. Interpretación.</b> En caso de duda sobre si
un producto integra o no la base comisionable, se estará a la regla de la
cláusula ___.1: solo comisionan los planes de suscripción expresamente
pactados, y toda ampliación de la base comisionable requiere acuerdo escrito
de ambas partes.</p>

<div class="firma">
  Documento preparado para su incorporación al Acuerdo Comercial de Tradeable
  Academy. No constituye por sí mismo un contrato ni sustituye al asesoramiento
  de un profesional del Derecho en la jurisdicción aplicable.
</div>
""" % {'hoy': HOY}


def main():
    salida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        RAIZ, 'out', 'Acuerdo_Comercial_Clausula_Productos_Excluidos.pdf')
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    from weasyprint import HTML, CSS as WCSS
    html = ('<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
            '<title>Anexo — Productos excluidos del régimen de comisiones</title>'
            '</head><body>%s</body></html>' % CUERPO)
    HTML(string=html).write_pdf(salida, stylesheets=[WCSS(string=CSS)])
    print('PDF: %s (%d KB)' % (salida, os.path.getsize(salida) // 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())
