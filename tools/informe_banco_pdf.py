# -*- coding: utf-8 -*-
"""El informe del banco del analizador, en PDF para el dueño.

    venv/bin/python3 tools/informe_banco_pdf.py

Un caso por sección: el gráfico, la construcción del trade tal como la vio
el modelo (formulario + notas), la respuesta del analizador (la MÁS RECIENTE:
v3 si el caso se re-corrió, si no v2 — es decir, lo que respondería HOY con
la cláusula encendida) y el veredicto leído a mano. Al frente, la nota por
metodología y el resumen de las tres pasadas.

Insumos: out/banco_analizador/*.png + manifest.json y las respuestas en
docs/banco_resultados_v3/ y _v2/. Salida: out/banco_analizador/
Informe_Banco_Analizador.pdf
"""
from __future__ import print_function

import io
import json
import os
import sys
import html as H

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ, 'out', 'banco_analizador')

# Veredicto humano por caso (textos leídos, no regex). Se mantiene A MANO a
# propósito: es el juicio, y el juicio no se automatiza.
VEREDICTO = {
    'H1_gartley_ganado': ('🟢', 'Lo lee entero y bien: patrón, PRZ, confirmación.'),
    'H2_bat_perdido': ('🟢', 'Encontró la razón real: orden límite ciega en la PRZ sin confirmación. No culpó a los ratios (eran válidos).'),
    'H3_trampa_ratios': ('🔴', 'Valida los ratios FALSOS leyendo las etiquetas (B real 0.50, D real 0.618). Tres pasadas, nunca los midió — límite de vista.'),
    'H4_trampa_butterfly': ('🔴', 'Da por bueno un Butterfly imposible: el D dibujado NO extiende más allá de X. Límite de vista.'),
    'E1_impulso_ganado': ('🟡', 'Análisis correcto del impulso, pero omite el conteo ALTERNATIVO que su propio prompt exige en Elliott.'),
    'E2_truncada_perdido': ('🟢', 'Cazó la quinta truncada ("no superó el máximo de la 3") sin culpar al conteo, que era válido.'),
    'E3_trampa_solape': ('🔴', 'Sigue afirmando "la onda 4 no entra en territorio de la 1" siendo falso. Resistió las 3 pasadas. Límite de vista.'),
    'E4_trampa_tercera_corta': ('🟢', 'CON LA CLÁUSULA: mide las ondas y caza que la 3 es la más corta — "contradice una regla inviolable".'),
    'W1_acumulacion_ganado': ('🟢', 'Lee la campaña completa citando el volumen real de cada evento.'),
    'W2_spring_falso_perdido': ('🟢', 'Joya: contradice al trader mirando el panel — "te pareció normal, pero el volumen del test es considerablemente alto".'),
    'W3_trampa_sin_volumen': ('🟢', 'CON LA CLÁUSULA: "el panel de volumen no está visible… sin poder verificarlo". Antes alucinaba las tres lecturas.'),
    'W4_trampa_sin_rango': ('🟡', 'Objeta el contexto (tendencia bajista, "más distribución que acumulación") pero no dice lo central: sin rango no hay spring.'),
    'P1_hch_ganado': ('🟢', 'HCH, neckline, objetivo medido y retest: todo bien leído.'),
    'P2_triangulo_perdido': ('🟢', 'La razón real: la ruptura salió sin volumen. Y responde su pregunta: el patrón estaba bien dibujado.'),
    'P3_trampa_doble_techo': ('🟢', 'CON LA CLÁUSULA: "al observar los precios en el eje, los máximos no son exactamente iguales".'),
    'P4_trampa_objetivo': ('🟡', 'Ya no aconseja "más paciencia" hacia el objetivo imposible (eso era dañino), pero sigue sin rehacer la resta 116−105→94.'),
    'T1_divergencia_ganado': ('🟢', 'Divergencia regular + zona + volumen: la confluencia multi-familia bien leída.'),
    'T2_cruce_rango_perdido': ('🟢', 'El contexto era un rango: el cruce ahí es ruido, y compró pegado al techo.'),
    'T3_trampa_rsi_inventado': ('🟡', 'CON LA REGLA DE HONESTIDAD: "no puedo confirmar el valor exacto de 28". Ya no lava el número; aún no lee el 50.5 rotulado.'),
    'T4_trampa_cruce_inexistente': ('🔴', '"El gráfico muestra claramente que la SMA 9 cruza" — el cruce NO existe en toda la ventana. Límite de vista.'),
    'I1_ict_sweep_fvg_ganado': ('🟢', 'GUARDIÁN: barrida→FVG→BOS leído completo, sin inventarle defectos. Intacto con la cláusula.'),
    'I2_ote_ganado': ('🟢', 'GUARDIÁN: la banda OTE 0.62–0.79 con el lente dedicado. Intacto con la cláusula.'),
    'I3_ict_sin_barrida_perdido': ('🟢', 'La razón canónica: el displacement nació sin purgar liquidez — el FVG se califica por su origen.'),
    'I4_trampa_sweep_inventado': ('🟢', '"El precio no llegó a tocar el PDL… la barrida no fue completa" — desmintió la barrida inventada.'),
    'I5_sl_cazado_perdido': ('🟢', 'Separó idea de stop: "demasiado ajustado… colocarlo más allá del mínimo del barrido". No compró la excusa de manipulación.'),
    'I6_be_prematuro': ('🟢', 'No asintió al "hice lo correcto": explicó el costo del break-even prematuro antes de que la estructura lo respaldara.'),
    'H5_direccion_invertida': ('🟢', 'Cuestionó la clasificación midiendo B (0.45) y la falta de confirmación en la PRZ donde vendió contra un patrón alcista.'),
    'W5_contradiccion_propia': ('🟢', 'Confrontó su tesis con su orden: "acumulación… favorece un movimiento alcista en lugar de un rechazo en el techo".'),
    'P5_tp_tras_soporte': ('🟢', 'Leyó el mapa: la demanda dibujada estaba antes del objetivo y el precio giró exactamente ahí. No consoló con "mala suerte".'),
    'T5_divergencia_tipo': ('🟡', 'Da la lección adyacente correcta (no operar contra la tendencia) pero no corrige el TIPO: era divergencia oculta alcista.'),
}

NOTAS = [
    ('ICT / OTE', '8/10', 'Todos los casos bien, trampas incluidas: desmintió la barrida inventada, separó idea de stop, cazó el BE prematuro. Lo no probado: lecturas de precisión fina.'),
    ('Wyckoff', '8/10', 'Lee campañas y volumen de verdad (contradijo al trader con el panel delante). Le falta nombrar "sin rango no hay spring" en vez de rodearlo.'),
    ('Chart Patterns', '7/10', 'Patrones, necklines, rupturas y el mapa (la demanda antes del objetivo) bien. Pendiente: rehacer la aritmética del objetivo medido.'),
    ('Elliott Wave', '6/10', 'Conceptos y pérdidas bien (quinta truncada); con la cláusula mide longitudes (3ª más corta). El SOLAPE de la onda 4 se le escapa — vista, no concepto.'),
    ('Technical Analysis', '5.5/10', 'Divergencias y contexto bien; honesto con los números que no puede leer. Pero puede "ver" cruces inexistentes y no corrige el tipo de divergencia.'),
    ('Harmonic', '5/10', 'Concepto y gestión bien (dirección invertida, entrada ciega). Su agujero: NO puede verificar ratios desde píxeles y valida etiquetas falsas. Aquí va el siguiente peldaño (mejor modelo o ratios en el formulario).'),
]


def respuesta_de(rid):
    for carpeta in ('docs/banco_resultados_v3', 'docs/banco_resultados_v2',
                    'docs/banco_resultados'):
        ruta = os.path.join(RAIZ, carpeta, rid + '.md')
        if os.path.exists(ruta):
            cuerpo = io.open(ruta, encoding='utf-8').read()
            texto = cuerpo.split('\n---\n', 1)[1] if '\n---\n' in cuerpo else cuerpo
            tag = {'docs/banco_resultados_v3': 'v3 (cláusula + honestidad numérica)',
                   'docs/banco_resultados_v2': 'v2 (cláusula)',
                   'docs/banco_resultados': 'línea base (prompt actual)'}[carpeta]
            return texto.strip(), tag
    return None, None


import re


def parrafos(t):
    """Markdown mínimo → HTML (las respuestas traen **negritas** y ###)."""
    out = []
    for p in t.split('\n\n'):
        if not p.strip():
            continue
        e = H.escape(p)
        e = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', e, flags=re.S)
        e = re.sub(r'^#{2,4}\s*(.+)$', r'<b>\1</b>', e, flags=re.M)
        out.append('<p>%s</p>' % e.replace('\n', '<br>'))
    return ''.join(out)


# La fuente del PDF no trae emojis de color → etiquetas de texto con su clase.
ETIQUETA = {'🟢': ('BIEN', 'ok'), '🟡': ('A MEDIAS', 'medio'),
            '🔴': ('FALLA', 'mal')}


def main():
    with io.open(os.path.join(BANCO, 'manifest.json'), encoding='utf-8') as fh:
        casos = json.load(fh)

    css = """
    @page { size: A4; margin: 1.6cm 1.5cm; @bottom-right {
        content: counter(page); font-size: 9px; color: #888; } }
    body { font-family: 'DejaVu Sans', sans-serif; font-size: 10px;
           color: #1a1d26; line-height: 1.45; }
    h1 { font-size: 21px; margin: 0 0 2px; }
    h2 { font-size: 14px; border-bottom: 2px solid #004feb;
         padding-bottom: 3px; margin: 0 0 8px; page-break-after: avoid; }
    .caso { page-break-before: always; }
    .sub { color: #667; font-size: 10.5px; margin: 0 0 14px; }
    img.chart { width: 100%; border: 1px solid #ccc; border-radius: 4px;
                margin: 4px 0 8px; }
    .meta { background: #eef1f8; border-radius: 5px; padding: 7px 10px;
            margin-bottom: 7px; }
    .meta b { color: #004feb; }
    .notas { background: #fff7e6; border-left: 3px solid #d99a1f;
             padding: 6px 10px; margin-bottom: 7px; }
    .resp { background: #f4f5f8; border-left: 3px solid #99a;
            padding: 6px 10px; }
    .resp p { margin: 4px 0; }
    .ver { border-radius: 5px; padding: 7px 10px; margin-top: 7px;
           font-weight: bold; }
    .vok { background: #e6f6ee; border-left: 4px solid #1d9d63; }
    .vmedio { background: #fdf3d8; border-left: 4px solid #d99a1f; }
    .vmal { background: #fde8e8; border-left: 4px solid #d33; }
    .tag { display: inline-block; padding: 1px 7px; border-radius: 3px;
           color: #fff; font-size: 9px; font-weight: bold;
           vertical-align: 2px; margin-right: 5px; }
    .tok { background: #1d9d63; } .tmedio { background: #d99a1f; }
    .tmal { background: #d33; }
    table { border-collapse: collapse; width: 100%; margin: 8px 0; }
    th, td { border: 1px solid #ccd; padding: 5px 7px; text-align: left;
             font-size: 9.5px; }
    th { background: #eef1f8; }
    .chip { font-size: 8.5px; color: #667; }
    """

    partes = ["""<h1>Banco del analizador — informe completo</h1>
    <p class="sub">Tradeable Academy · 30 gráficos sintéticos · 5 metodologías ·
    generado el 2026-08-14</p>
    <h2>Cómo leer este documento</h2>
    <p>Cada gráfico se <b>construyó desde la definición matemática</b> del
    patrón (un Gartley ES B=0.618·XA; la onda 4 NO solapa a la 1), así que la
    verdad de cada caso se conoce por construcción — sin necesitar un experto
    que etiquete. Tres tipos de caso: <b>ganados</b> (¿lee bien un setup
    válido?), <b>perdidos</b> (¿encuentra la razón real del fallo?) y
    <b>trampas</b> (las etiquetas o las notas MIENTEN: ¿corrige al trader o le
    da la razón?). La respuesta mostrada es la MÁS RECIENTE de cada caso — lo
    que el analizador contesta con la cláusula de verificación encendida.</p>
    <h2>Nota por metodología (leídos los textos, no el detector)</h2>
    <table><tr><th>Metodología</th><th>Nota</th><th>Por qué</th></tr>"""]
    for met, nota, razon in NOTAS:
        partes.append('<tr><td><b>%s</b></td><td><b>%s</b></td><td>%s</td></tr>'
                      % (met, nota, H.escape(razon)))
    partes.append("""</table>
    <p><b>El patrón general:</b> fuerte en conceptos, campañas, gestión y en
    encontrar la razón real de una pérdida (lo que el cliente usa a diario);
    su límite es la <b>agudeza visual fina</b> — medir ratios, ver un solape
    de 1.5 puntos, leer un número pequeño, distinguir si dos líneas se cruzan.
    La cláusula de verificación arregló lo comparable a ojo (longitudes de
    onda, máximos desiguales, paneles ausentes) y la regla de honestidad evita
    que finja haber medido lo que no puede; lo restante es límite del modelo
    de visión, no del prompt.</p>""")

    for caso in casos:
        rid = caso['id']
        resp, tag = respuesta_de(rid)
        emoji, juicio = VEREDICTO.get(rid, ('🟡', '(sin veredicto manual)'))
        f = caso['form']
        png = os.path.join(RAIZ, caso['png'])
        confl = ', '.join(f['confluences'])
        eti, cls = ETIQUETA[emoji]
        partes.append("""
        <div class="caso">
        <h2><span class="tag t%s">%s</span>%s</h2>
        <p class="sub">%s · %s · %s · %s · resultado: %s</p>
        <img class="chart" src="file://%s">
        <div class="meta"><b>Qué es de verdad este gráfico:</b> %s</div>
        <div class="notas"><b>Construcción del trade (lo que el modelo
        recibió):</b><br>Confluencias marcadas: %s<br><i>«%s»</i></div>
        <div class="resp"><b>Respuesta del analizador</b>
        <span class="chip">· pasada %s</span>%s</div>
        <div class="ver v%s">Veredicto — %s: %s</div>
        </div>""" % (
            cls, eti, H.escape(rid), H.escape(f['approach']),
            H.escape(caso['instrumento']), caso['tf'],
            H.escape(f['direction']), H.escape(f['result']), png,
            H.escape(caso['humano']), H.escape(confl), H.escape(f['notes']),
            tag, parrafos(resp or '(sin respuesta guardada)'),
            cls, eti, H.escape(juicio)))

    documento = ('<html><head><meta charset="utf-8"><style>%s</style></head>'
                 '<body>%s</body></html>' % (css, ''.join(partes)))
    from weasyprint import HTML
    salida = os.path.join(BANCO, 'Informe_Banco_Analizador.pdf')
    HTML(string=documento, base_url=RAIZ).write_pdf(salida)
    kb = os.path.getsize(salida) / 1024.0
    print('✅ %s (%.0f KB, %d casos)' % (os.path.relpath(salida, RAIZ),
                                         kb, len(casos)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
