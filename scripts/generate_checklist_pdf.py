"""Genera el PDF del checklist de pre-lanzamiento de Scalpel.
Usa Paragraph en cada celda para que el texto se ajuste al ancho de columna
(evita el solapamiento de textos) y etiquetas de color en lugar de emojis."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
    KeepTogether, PageBreak,
)

# ── Paleta ──
DARK_BG = colors.HexColor('#1a1d28')
ACCENT  = colors.HexColor('#5b8ef0')
PREMIUM = colors.HexColor('#e0a83d')
SURFACE = colors.HexColor('#22263a')
BORDER  = colors.HexColor('#2e3250')
GREEN   = colors.HexColor('#4ecd78')
RED     = colors.HexColor('#ef4444')
ORANGE  = colors.HexColor('#f97316')
MUTED   = colors.HexColor('#8b90b0')
WHITE   = colors.white

OUTPUT = '/home/user/TRADINGBOT2.0/Scalpel_Checklist_PreLanzamiento.pdf'

doc = SimpleDocTemplate(
    OUTPUT, pagesize=A4,
    leftMargin=1.6 * cm, rightMargin=1.6 * cm,
    topMargin=1.8 * cm, bottomMargin=1.6 * cm,
)

# ── Estilos ──
def S(name, **kw):
    return ParagraphStyle(name, **kw)

title_s = S('T',  fontSize=22, textColor=WHITE,  fontName='Helvetica-Bold', spaceAfter=3)
sub_s   = S('Su', fontSize=9.5, textColor=MUTED, fontName='Helvetica',      spaceAfter=2, leading=13)
sec_s   = S('Se', fontSize=12.5, textColor=ACCENT, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=7)
note_s  = S('N',  fontSize=8,  textColor=MUTED,  fontName='Helvetica-Oblique', spaceAfter=5, leading=11)
concl_s = S('C',  fontSize=9.5, textColor=WHITE, fontName='Helvetica',       leading=15)

# Celdas (se ajustan al ancho de columna)
cell_l  = S('cl', fontSize=8,   textColor=WHITE, fontName='Helvetica',      leading=10.5)
cell_c  = S('cc', fontSize=8,   textColor=WHITE, fontName='Helvetica',      leading=10.5, alignment=1)
cell_b  = S('cb', fontSize=8,   textColor=WHITE, fontName='Helvetica-Bold', leading=10.5, alignment=1)
hdr_s   = S('h',  fontSize=8.5, textColor=ACCENT, fontName='Helvetica-Bold', leading=11, alignment=1)
hdr_l   = S('hl', fontSize=8.5, textColor=ACCENT, fontName='Helvetica-Bold', leading=11)
sechdr  = S('sh', fontSize=8.5, textColor=PREMIUM, fontName='Helvetica-Bold', leading=11)

elems = []


def section(txt):
    elems.append(Paragraph(txt, sec_s))


def note(txt):
    elems.append(Paragraph(txt, note_s))


def sp(h=0.3):
    elems.append(Spacer(1, h * cm))


def hr(c=ACCENT):
    elems.append(HRFlowable(width="100%", thickness=1, color=c))


def P(txt, style=cell_l):
    return Paragraph(txt, style)


# Mapas de color para Estado y Prioridad (texto coloreado, sin emojis)
def _hex(c):
    return '#' + c.hexval()[2:]


def estado(label):
    color = {
        'LISTO': GREEN, 'PENDIENTE': PREMIUM, 'PAGAR + INSTALAR': RED,
    }.get(label, WHITE)
    return Paragraph(f'<font color="{_hex(color)}"><b>{label}</b></font>', cell_c)


def prio(label):
    color = {
        'CRÍTICO': RED, 'ALTO': ORANGE, 'MEDIO': PREMIUM, 'BAJO': MUTED, '—': MUTED,
    }.get(label, WHITE)
    return Paragraph(f'<font color="{_hex(color)}"><b>{label}</b></font>', cell_c)


# ── Encabezado ──
sp(0.2)
elems.append(Paragraph("SCALPEL", title_s))
elems.append(Paragraph(
    "Checklist de Pre-Lanzamiento — Todo lo que debes tener listo antes de abrir al público", sub_s))
elems.append(Paragraph(
    "Documento recordatorio operativo. Ningún ítem CRÍTICO puede quedar pendiente el día del lanzamiento.", sub_s))
sp(0.15)
hr()
sp(0.15)

# ── Leyenda ──
section("Leyenda de estado")
leg = [
    [Paragraph('<b>Etiqueta</b>', hdr_l), Paragraph('<b>Significado</b>', hdr_l)],
    [estado('LISTO'),            P('Ya está hecho o no requiere acción adicional')],
    [estado('PENDIENTE'),        P('Hay que hacerlo antes de lanzar, pero no cuesta dinero')],
    [estado('PAGAR + INSTALAR'), P('Requiere contratar / pagar un servicio externo antes del lanzamiento')],
]
t = Table(leg, colWidths=[4.2 * cm, 13.6 * cm], repeatRows=1)
t.setStyle(TableStyle([
    ('BACKGROUND',    (0, 0), (-1, 0),  SURFACE),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [DARK_BG, SURFACE]),
    ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING',    (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING',   (0, 0), (-1, -1), 8),
    ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
    ('GRID',          (0, 0), (-1, -1), 0.4, BORDER),
]))
elems.append(t)

# ── Checklist principal ──
section("Checklist Completo de Pre-Lanzamiento")
note("Ordenado por área. La columna PRIORIDAD indica qué tan crítico es para el día del lanzamiento.")

H = lambda txt: Paragraph(f'<b>{txt}</b>', hdr_s)
HL = lambda txt: Paragraph(f'<b>{txt}</b>', hdr_l)

def srow(txt):
    """Fila de subtítulo de sección que ocupa todo el ancho."""
    return [Paragraph(f'<b>{txt}</b>', sechdr), '', '', '', '', '']

rows = [
    [HL('#'), HL('Ítem / Tarea'), H('Estado'), H('Prioridad'), H('Costo estimado'), HL('Notas')],

    srow('INTELIGENCIA ARTIFICIAL'),
    [P('1', cell_c), P('Cuenta OpenAI + API Key activa'), estado('PAGAR + INSTALAR'), prio('CRÍTICO'),
     P('$0 crear cuenta (pago por uso)'), P('Ir a platform.openai.com y cargar créditos (~$20 para empezar)')],
    [P('2', cell_c), P('GPT-4o Vision — análisis de screenshots'), estado('PAGAR + INSTALAR'), prio('CRÍTICO'),
     P('~$0.018 por análisis'), P('Se activa sola al tener la API Key. Ya está integrada en el código.')],
    [P('3', cell_c), P('Responses API + Web Search — agente Scout'), estado('PAGAR + INSTALAR'), prio('CRÍTICO'),
     P('$20.50 / mes fijo'), P('Requiere la API Key de OpenAI. El agente semanal aún hay que programarlo.')],

    srow('HOSTING Y SERVIDOR'),
    [P('4', cell_c), P('Contratar VPS (servidor en la nube)'), estado('PAGAR + INSTALAR'), prio('CRÍTICO'),
     P('$6 – 12 / mes'), P('Recomendado: Hetzner CX22 (~€3.79/mes) o DigitalOcean Droplet $6/mes.')],
    [P('5', cell_c), P('Configurar Nginx + Gunicorn en el VPS'), estado('PENDIENTE'), prio('CRÍTICO'),
     P('$0'), P('El archivo nginx.conf ya existe en el repo. Hay que instalarlo en el VPS.')],
    [P('6', cell_c), P('Subir el código al VPS (git clone + .env)'), estado('PENDIENTE'), prio('CRÍTICO'),
     P('$0'), P('Clonar desde git en el servidor y crear el .env con todas las keys.')],

    srow('DOMINIO Y SEGURIDAD'),
    [P('7', cell_c), P('Comprar nombre de dominio (.com)'), estado('PAGAR + INSTALAR'), prio('CRÍTICO'),
     P('~$12 / año (~$1/mes)'), P('Recomendado: Namecheap o Porkbun (más baratos que GoDaddy).')],
    [P('8', cell_c), P('Configurar DNS en Cloudflare'), estado('PENDIENTE'), prio('CRÍTICO'),
     P('$0 — Gratuito'), P('Apuntar el dominio al IP del VPS. Cloudflare es gratis y da protección DDoS.')],
    [P('9', cell_c), P('Certificado SSL (HTTPS)'), estado('PENDIENTE'), prio('CRÍTICO'),
     P('$0 — Let\'s Encrypt'), P('Comando: certbot --nginx. Renovación automática cada 90 días.')],

    srow('SISTEMA DE PAGOS'),
    [P('10', cell_c), P('Cuenta Stripe + integración de pagos'), estado('PAGAR + INSTALAR'), prio('CRÍTICO'),
     P('2.9% + $0.30 por transacción'), P('Crear cuenta en stripe.com. El cobro de suscripciones aún NO está integrado en el código.')],
    [P('11', cell_c), P('Configurar planes en Stripe (Standard $10 + Premium $30)'), estado('PENDIENTE'), prio('CRÍTICO'),
     P('$0'), P('Crear los productos / precios en el dashboard de Stripe antes de lanzar.')],

    srow('EMAIL Y NOTIFICACIONES'),
    [P('12', cell_c), P('Cuenta SendGrid para emails transaccionales'), estado('PENDIENTE'), prio('ALTO'),
     P('$0 (free tier 100/día)'), P('Registro gratis en sendgrid.com. Hoy usa Gmail SMTP, que no es apto para producción.')],

    srow('PROP FIRM SCOUT'),
    [P('13', cell_c), P('Corregir bugs del Scout (filtros, layout)'), estado('PENDIENTE'), prio('ALTO'),
     P('$0'), P('Filtro de país roto, layout pequeño y filtros que rompen entre sí. Pendiente de implementar.')],
    [P('14', cell_c), P('Diseño marketplace con logos reales'), estado('PENDIENTE'), prio('ALTO'),
     P('$0'), P('Cards estilo Amazon con el logo de cada firm. Los logos se cargan gratis vía favicon.')],
    [P('15', cell_c), P('Datos reales verificados por IA (no simulados)'), estado('PAGAR + INSTALAR'), prio('ALTO'),
     P('Requiere ítem #3 (OpenAI)'), P('Sin la API de Web Search, los datos son los aproximados que insertamos.')],
    [P('16', cell_c), P('Agente de actualización semanal (APScheduler)'), estado('PENDIENTE'), prio('ALTO'),
     P('$0 (librería gratis)'), P('APScheduler es gratis. Solo requiere la API Key de OpenAI para las búsquedas web.')],

    srow('LEGAL Y COMPLIANCE'),
    [P('17', cell_c), P('Términos y Condiciones + Política de Privacidad'), estado('PENDIENTE'), prio('MEDIO'),
     P('$0 – 150'), P('Obligatorio antes de cobrar. Plantillas o abogado.')],
    [P('18', cell_c), P('Aviso legal: "Solo con fines educativos"'), estado('LISTO'), prio('—'),
     P('$0'), P('Ya aparece en el footer de la app.')],
    [P('19', cell_c), P('Política de cookies (GDPR si hay usuarios EU)'), estado('PENDIENTE'), prio('MEDIO'),
     P('$0'), P('Necesario si hay usuarios europeos. Cookiebot tiene plan gratuito.')],

    srow('EXTRAS RECOMENDADOS'),
    [P('20', cell_c), P('Backups automáticos de la base de datos'), estado('PENDIENTE'), prio('MEDIO'),
     P('$0'), P('Script cron que respalda scalpel.db cada 24h. No requiere pago.')],
    [P('21', cell_c), P('Migrar de SQLite a PostgreSQL'), estado('PENDIENTE'), prio('MEDIO'),
     P('$0 – 7 / mes'), P('SQLite aguanta hasta ~5k usuarios. Por encima de eso, migrar a PostgreSQL.')],
    [P('22', cell_c), P('Google Analytics o Plausible (estadísticas)'), estado('PENDIENTE'), prio('BAJO'),
     P('$0 – 9 / mes'), P('Para ver de dónde vienen los usuarios, qué features usan y la tasa de conversión.')],
]

col_widths = [0.8 * cm, 4.7 * cm, 2.5 * cm, 1.9 * cm, 3.0 * cm, 4.9 * cm]
t = Table(rows, colWidths=col_widths, repeatRows=1)

style = [
    ('BACKGROUND',    (0, 0), (-1, 0),  SURFACE),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [DARK_BG, SURFACE]),
    ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING',    (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ('LEFTPADDING',   (0, 0), (-1, -1), 6),
    ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
    ('GRID',          (0, 0), (-1, -1), 0.4, BORDER),
]
# Filas de subtítulo de sección: fusionar columnas y resaltar
sec_row_idx = [i for i, r in enumerate(rows) if isinstance(r[0], Paragraph) and r[1] == '' and r[2] == '']
for i in sec_row_idx:
    style.append(('SPAN', (0, i), (-1, i)))
    style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#1c2030')))
    style.append(('TOPPADDING', (0, i), (-1, i), 7))
    style.append(('BOTTOMPADDING', (0, i), (-1, i), 7))

t.setStyle(TableStyle(style))
elems.append(t)

# ── Resumen de costos (se mantiene junto en una sola página) ──
resumen_block = []
resumen_block.append(Spacer(1, 0.3 * cm))
resumen_block.append(HRFlowable(width="100%", thickness=1, color=BORDER))
resumen_block.append(Spacer(1, 0.3 * cm))
resumen_block.append(Paragraph("Resumen de costos para el día de lanzamiento", sec_s))
res = [
    [HL('Concepto'), H('Costo inicial'), H('Costo mensual recurrente')],
    [P('OpenAI API (créditos iniciales)'), P('~$20 recarga', cell_c), P('Variable según uso', cell_c)],
    [P('VPS Hosting (Hetzner CX22)'), P('$0 setup', cell_c), P('~$4 – 12 / mes', cell_c)],
    [P('Dominio .com (1 año)'), P('~$12 / año', cell_c), P('~$1 / mes', cell_c)],
    [P('Stripe (pasarela de pagos)'), P('$0 setup', cell_c), P('2.9% + $0.30 por transacción', cell_c)],
    [P('SendGrid (email)'), P('$0', cell_c), P('$0 (free tier al inicio)', cell_c)],
    [P('Cloudflare + SSL'), P('$0', cell_c), P('$0 (gratuito)', cell_c)],
    [Paragraph('<b>TOTAL ESTIMADO DÍA DE LANZAMIENTO</b>', cell_l),
     Paragraph('<b>~$32 inversión inicial</b>', cell_c),
     Paragraph('<b>~$25 – 35 / mes fijos</b>', cell_c)],
]
t2 = Table(res, colWidths=[8.0 * cm, 4.4 * cm, 5.4 * cm], repeatRows=1)
t2.setStyle(TableStyle([
    ('BACKGROUND',    (0, 0), (-1, 0),  SURFACE),
    ('ROWBACKGROUNDS', (0, 1), (-1, -2), [DARK_BG, SURFACE]),
    ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ('TOPPADDING',    (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING',   (0, 0), (-1, -1), 8),
    ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
    ('GRID',          (0, 0), (-1, -1), 0.4, BORDER),
    ('BACKGROUND',    (0, -1), (-1, -1), colors.HexColor('#1e2f1e')),
    ('TEXTCOLOR',     (0, -1), (-1, -1), GREEN),
]))
resumen_block.append(t2)
resumen_block.append(Spacer(1, 0.3 * cm))
resumen_block.append(Paragraph(
    "RECUERDA  ·  Ningún ítem marcado como CRÍTICO puede quedar pendiente el día del lanzamiento. "
    "Los ítems ALTO afectan directamente la calidad del producto (Scout sin datos reales, bugs de filtros). "
    "Los ítems MEDIO y BAJO pueden activarse en las primeras semanas post-lanzamiento sin afectar la operación.",
    concl_s))
elems.append(KeepTogether(resumen_block))


def dark_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()


doc.build(elems, onFirstPage=dark_bg, onLaterPages=dark_bg)
print("PDF generado:", OUTPUT)
