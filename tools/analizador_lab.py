# -*- coding: utf-8 -*-
"""EL ANALIZADOR DEL SITIO, EN LABORATORIO — para comparar sin tocarlo.

    python3 tools/analizador_lab.py --imagen docs/capturas_prueba/mes_ote_perdedor.png \\
        --construccion docs/capturas_prueba/mes_ote_construccion.txt \\
        --columnas @out/analizador2/columnas_mes_ote_perdedor.txt

🔴 NO TOCA EL ANALIZADOR DEL SITIO, y no lo importa. Solo LEE `scalpel/app.py`.

═══ QUÉ HACE Y POR QUÉ ASÍ ═══
La pregunta que decide si el analizador 2.0 vale la pena no es "¿mide bien las
velas?" —eso ya está medido— sino **"¿cambia lo que el analizador le responde a
un trader?"**. Y eso solo se contesta poniendo las respuestas una al lado de la
otra sobre el MISMO trade. Aquí se producen tres:

  A · como corre hoy en el sitio
  B · con la cláusula de verificación ENCENDIDA (existe ya, apagada por
      defecto: `ANALYZE_VERIFY_CLAIMS`). Es la alternativa BARATA a todo
      nuestro trabajo y hay que probarla ANTES de defenderlo.
  C · con el BLOQUE DE HECHOS medido delante

🔑 B puede salir de dos formas y las dos son datos: que el modelo diga
honestamente "no puedo verificarlo" (bien, pero deja de responder), o que
**afirme que lo verificó sin poder** — que es peor que ahora. Medimos en agosto
que GPT-4o no sabe comparar dos alturas: pedirle que compruebe un nivel es
pedirle justo lo que no hace.

═══ POR QUÉ SE EXTRAE EL PROMPT EN VEZ DE COPIARLO ═══
🔴 `import app` NO se hace: importar la aplicación arranca la base de datos de
PRODUCCIÓN. Se lee el archivo, se saca por AST solo lo que hace falta
(`SYSTEM_PROMPT`, `VERIFY_CLAIMS_CLAUSE`, `build_system_prompt`,
`normalize_chart_image` y sus constantes) y se ejecuta en un espacio aislado.

⚠️ Y no se copia y pega: si el dueño cambia el prompt del sitio, este
laboratorio cambia con él. Un prompt duplicado a mano se desincroniza en una
semana y a partir de ahí la comparación miente.

⚠️ La imagen se normaliza EXACTAMENTE igual que en el sitio, así que la
captura de 1817 px baja a 1280 antes de enviarse. Es lo que el analizador ve
de verdad; medir sobre la grande y comparar contra otra cosa sería trampa.
"""
from __future__ import print_function

import argparse
import ast
import base64
import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, 'scalpel', 'app.py')
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

ASIGNACIONES = {'SYSTEM_PROMPT', 'VERIFY_CLAIMS_CLAUSE', 'MODEL',
                'ANALYZE_IMG_DETAIL', 'ANALYZE_IMG_MAX_PX',
                'ANALYZE_IMG_HARD_PX'}
FUNCIONES = {'build_system_prompt', 'normalize_chart_image'}
CLASES = {'ImageTooLarge'}


class _Log(object):
    def warning(self, *a, **k):
        pass


def del_sitio():
    """Saca del `app.py` REAL las piezas del analizador, sin ejecutarlo."""
    from PIL import Image
    fuente = io.open(APP, encoding='utf-8').read()
    arbol = ast.parse(fuente)
    ns = {'os': os, 're': re, 'io': io, 'base64': base64, 'Image': Image,
          'app': type('X', (), {'logger': _Log()})()}
    for nodo in arbol.body:
        quiero = False
        if isinstance(nodo, ast.Assign):
            quiero = any(isinstance(t, ast.Name) and t.id in ASIGNACIONES
                         for t in nodo.targets)
        elif isinstance(nodo, ast.FunctionDef):
            quiero = nodo.name in FUNCIONES
        elif isinstance(nodo, ast.ClassDef):
            quiero = nodo.name in CLASES
        if quiero:
            mod = ast.Module(body=[nodo], type_ignores=[])
            exec(compile(mod, APP, 'exec'), ns)
    faltan = (ASIGNACIONES | FUNCIONES | CLASES) - set(ns)
    if faltan:
        raise SystemExit('no se pudo extraer de app.py: %s' % sorted(faltan))
    return ns


def mensaje_usuario(datos, notas, hechos=None, tabla=None):
    """La MISMA plantilla que arma el sitio, más el bloque de hechos si lo hay.

    🔑 El bloque va al PRINCIPIO y dicho como lo que es: medido, no
    interpretado. Puesto al final se lee como un apéndice y el modelo lo
    ignora; puesto delante y con esa etiqueta, es el suelo sobre el que
    razona."""
    bloque = ''
    if notas:
        bloque = ('\nTRADER\'S TRADE CONSTRUCTION (what the trader saw and why '
                  'they took this trade):\n"""\n%s\n"""\n'
                  'This is the trader\'s own account of how they built the '
                  'trade — their reasoning, the levels they identified, what '
                  'they were waiting for, and how they decided to enter. Treat '
                  'this as their declared thesis. Your job is to:\n'
                  '1. Evaluate whether what they described is visible and '
                  'consistent with what you see on the chart.\n'
                  '2. Contrast their declared construction against the actual '
                  'price action — where does the chart confirm their thesis? '
                  'Where does it diverge or show something they may not have '
                  'accounted for?\n'
                  '3. Be specific: if they say they identified a FVG or OB at a '
                  'certain point, look for it on the chart and comment on its '
                  'quality. If they mention a liquidity sweep, verify whether '
                  'it looks like a clean sweep with displacement on the chart.\n'
                  'Do NOT simply repeat their construction back — analyze and '
                  'contrast it.' % notas)
    cabeza = ''
    if hechos:
        cabeza = (
            'MEASURED FACTS ABOUT THIS EXACT SCREENSHOT (computed from the '
            'pixels by a separate tool, NOT read off the image by you). These '
            'are arithmetic, not interpretation: candle highs, lows and closes '
            'were measured and the events below follow from comparing those '
            'numbers. Treat them as ground truth about what price did, and '
            'never contradict them. They do not tell you what the trade means '
            '— that is your job.\n\n%s\n\n'
            'Anything NOT listed here was not measured: do not assume its '
            'absence proves anything.\n'
            'HARD RULE: you may cite ONLY the candles and levels that appear '
            'in that list, exactly as written. NEVER introduce a candle number '
            'or a price level of your own — not from the image, not from the '
            'trader\'s notes, not inferred. If you want to talk about '
            'something you see but cannot cite from the list, describe it in '
            'words without numbering it. Inventing a reference is the single '
            'worst thing you can do here, because the trader will trust it as '
            'measured.\n\n' % hechos)
    if tabla:
        cabeza += tabla + '\n\n'
    return (cabeza + 'Trade submitted for retrospective, educational analysis '
            '(approach: %(approach)s):\n\n'
            'Instrument: %(instrument)s\n'
            'DIRECTION (ground truth — the trader took a %(direction)s '
            'position): %(direction)s\n'
            'Session: %(session)s\n'
            'Result: %(result)s\n'
            'HTF Bias held: %(htf)s\n'
            'Traded aligned with HTF bias: %(aligned)s\n'
            'Approach / model used: %(approach)s\n'
            'Confluences identified by trader: %(confluences)s\n'
            % datos + bloque +
            '\nThis was a %(direction)s trade — anchor your entire analysis to '
            'that fact. Locate where the trader entered and exited on the chart '
            'using the %(direction)s direction as your reference. Analyze it '
            'through the trader\'s stated approach (%(approach)s) via the '
            'METHODOLOGY ROUTER — if the approach is OTE / Std Dev, lead with '
            'the dedicated OTE / Standard Deviation lens (its distinct '
            'fib-driven trigger), not a generic ICT read. Identify possible '
            'setup considerations — or confirm if the setup was technically '
            'sound and this may have been within normal statistical variance.'
            '\n\nLANGUAGE: Write your entire response in %(idioma)s. Keep '
            'ICT-specific terms and acronyms (FVG, IFVG, OTE, CHoCH, MSS, BOS, '
            'OB, SMT, BSL, SSL, EQH, EQL, Kill Zone, Silver Bullet, etc.) in '
            'their standard English form, but write all explanatory prose in '
            '%(idioma)s.' % datos)


def tabla_ohlc(r):
    """LA TABLA DE VELAS MEDIDAS, tal cual, para que el modelo la tenga.

    🔴 POR QUÉ EXISTE (2026-09-07, a raíz de una pregunta del dueño que da en
    el clavo): medimos 102 velas con su máximo, mínimo, apertura y cierre… y le
    entregábamos once frases. Textualmente: «es como tener una ametralladora y
    decidir usar una pistola».

    El catálogo de hechos solo cubre lo que YO decidí calcular. Todo lo demás
    —una media móvil, una compresión que no llega a mi umbral, cualquier lectura
    que a él se le ocurra y a mí no— queda fuera para siempre. Con la tabla
    delante, el modelo puede contestar preguntas que nuestro catálogo no cubre.

    🔑 Y no contradice lo medido en agosto. Lo que GPT-4o hace por azar es
    comparar DOS ALTURAS EN UNA IMAGEN. Comparar dos números en una tabla de
    texto es otra tarea completamente distinta, y en esa sí es competente.

    ⚠️ Sin escala del eje la tabla va en unidades relativas y se dice: siguen
    sirviendo para ordenar y comparar, que es lo único que se le pide."""
    esc = r['escala']
    filas = []
    # ⚠️ La serie va en unidades de -y, o sea NEGATIVAS. Comparar sigue
    #    funcionando, pero una tabla de números negativos invita a que el
    #    modelo se líe con los signos justo en la operación que le pedimos.
    #    Se desplaza para que el mínimo del gráfico sea 0.
    base = min(min(v[1], v[2]) for v in r['ohlc']) if r['ohlc'] else 0
    for i, v in enumerate(r['ohlc']):
        o, h, l, c = v
        if esc:
            o, h, l, c = [esc['precio'](-x) for x in (o, h, l, c)]
            filas.append('%3d | %9.2f %9.2f %9.2f %9.2f' % (i, o, h, l, c))
        else:
            o, h, l, c = [x - base for x in (o, h, l, c)]
            filas.append('%3d | %7.0f %7.0f %7.0f %7.0f' % (i, o, h, l, c))
    cab = ('MEASURED CANDLE TABLE — every candle in this screenshot, measured '
           'from the pixels (open, high, low, close). Candle 0 is the leftmost.'
           '\n%s\n'
           'Use this table for ANY comparison of levels. Do NOT judge whether '
           'one thing is above or below another by looking at the image — read '
           'it off these numbers. If a question can be answered from this '
           'table, answering it from the picture instead is an error.\n\n'
           'idx |      open      high       low     close\n'
           % ('Values are in PRICE.' if esc else
              'NOTE: the price axis could not be read reliably, so these are '
              'RELATIVE units — higher number = higher on the chart. They are '
              'still exact for comparing and ordering; just never present them '
              'to the trader as prices.'))
    return cab + '\n'.join(filas)


def bloque_de_hechos(imagen, columnas, prov=None, modelo=None, completo=False):
    """El bloque de hechos de `analizador2`, en texto plano y SIN PÍXELES.

    🔴 LAS COORDENADAS EN PÍXELES HAY QUE QUITARLAS, y por poco se cuelan. El
    bloque las trae —"vela 25 (x=188)"— referidas a la captura ORIGINAL de
    1817 px, pero el analizador recibe la imagen reducida a 1280 (lo hace el
    propio sitio, para acotar el coste de visión). Un x=188 de una imagen que
    él no está viendo no es solo inútil: es una invitación a que lo use y se
    equivoque, y encima con nuestra autoridad detrás.
    Se sustituyen por la POSICIÓN de la vela contando desde la izquierda, que
    sí es localizable mirando el gráfico y no depende de la resolución."""
    import analizador2 as A2
    cajas = A2.lee_columnas(columnas)
    # 🔴 CON EL MODELO, PARA QUE HAYA PRECIOS. Sin él no hay escala del eje y el
    #    bloque sale diciendo "la vela 44 hizo un BOS" — un número que el modelo
    #    NO puede situar, porque está mirando una imagen y no puede contar 44
    #    velas. Con precio sí: "BOS bajista atravesando 7.720,67" es localizable.
    #    La lectura del eje está cacheada, así que no cuesta cuota.
    r = A2.analiza(imagen, prov=prov, modelo=modelo, cajas=cajas, verboso=False)
    firmes, marcados = A2.bloque(r['velas'], r['hechos'], r['escala'])
    total = len(r['velas'])

    def limpia(par):
        t = re.sub(r'vela (\d+) \(x=\d+\)',
                   lambda m: 'candle %s of %d (counting from the left)'
                             % (m.group(1), total), par[1])
        t = re.sub(r'la vela (\d+)', lambda m: 'candle %s' % m.group(1), t)
        return (par[0], t)

    firmes = [limpia(p) for p in firmes]
    marcados = [limpia(p) for p in marcados]
    # 🔴 LA LISTA DE "NO VERIFICADOS" NO ENTRA EN EL PROMPT. Medido en la
    # primera comparación real: se la dimos etiquetada como "menciónalos solo
    # como posibilidades, nunca como hecho", y el modelo cogió de ahí la vela
    # 79 —un FVG bajista— y la presentó como **BOS alcista confirmado**. Decirle
    # a un modelo de lenguaje "esto no te lo creas" y dárselo igual no funciona:
    # una vez dentro del contexto, lo usa. O es un hecho y entra, o no entra.
    # Los no verificados se siguen calculando y se devuelven aparte, para
    # seguir midiéndolos y para enseñárselos al DUEÑO — nunca al modelo.
    lineas = ['MEASURED FACTS (verified, >=90%% accuracy):']
    lineas += ['  - ' + t for _f, t in firmes] or ['  - (none)']
    if completo:
        # 🔑 Este segundo bloque NO es la lista "sin verificar" que fracasó en
        #    la prueba C. Aquella no estaba medida y se pedía desconfianza.
        #    Estas líneas están medidas una por una y CADA UNA LLEVA SU TASA DE
        #    ACIERTO al lado: 83% no es "quizá", es un número del banco.
        lineas += ['', 'ALSO MEASURED, each with its measured hit rate. State '
                       'these as measurements, not certainties — if a line says '
                       '83%, say it looks like X rather than asserting X. The '
                       'same citation rule applies: quote them exactly, invent '
                       'nothing:']
        lineas += ['  - ' + t for _f, t in marcados] or ['  - (none)']
    return '\n'.join(lineas), r, marcados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--imagen', required=True)
    ap.add_argument('--construccion', required=True,
                    help='archivo de texto con la construcción del trade')
    ap.add_argument('--columnas', help='@ruta de las columnas ya obtenidas; '
                                       'sin esto no se puede hacer la variante C')
    ap.add_argument('--instrumento', default='MES (Micro E-mini S&P 500)')
    ap.add_argument('--direccion', default='short')
    ap.add_argument('--sesion', default='NY AM')
    ap.add_argument('--resultado', default='loss')
    ap.add_argument('--htf', default='bearish')
    ap.add_argument('--alineado', default='yes')
    ap.add_argument('--approach', default='OTE / Standard Deviation')
    ap.add_argument('--confluencias',
                    default='MSS, OTE 0.5 retracement, stacked bearish FVGs '
                            '(1H, 15m, 5m), HTF bearish bias')
    ap.add_argument('--idioma', default='Spanish')
    ap.add_argument('--modelo', metavar='PROVEEDOR:MODELO',
                    help='para leer el eje y que el bloque lleve PRECIOS')
    ap.add_argument('--solo', help='corre solo estas variantes, p.ej. C')
    ap.add_argument('--salida', default=os.path.join(RAIZ, 'out',
                                                     'comparativa.md'))
    a = ap.parse_args()

    sitio = del_sitio()
    notas = io.open(a.construccion, encoding='utf-8').read().strip()
    datos = {'instrument': a.instrumento, 'direction': a.direccion,
             'session': a.sesion, 'result': a.resultado, 'htf': a.htf,
             'aligned': a.alineado, 'approach': a.approach,
             'confluences': a.confluencias, 'idioma': a.idioma}

    hechos_txt = None
    if a.columnas:
        prov = modelo = None
        if a.modelo:
            prov, _, modelo = a.modelo.partition(':')
        hechos_txt, _r, _marcados = bloque_de_hechos(
            a.imagen, a.columnas, prov, modelo)
        completo_txt, _r2, _m2 = bloque_de_hechos(
            a.imagen, a.columnas, prov, modelo, completo=True)
        tabla_txt = tabla_ohlc(_r)
        print('[hechos] %d verificados · escala del eje: %s'
              % (hechos_txt.count('\n  - '),
                 'SÍ (con precios)' if _r['escala'] else
                 '🔴 NO — el bloque sale sin precios y la prueba pierde valor'))
        if 'en 7' not in hechos_txt and '.' not in hechos_txt.split('\n')[1]:
            print('⚠️  El bloque sale SIN PRECIOS. Pásale --modelo o la prueba '
                  'no vale: un número de vela el modelo no lo puede situar.')

    crudo = open(a.imagen, 'rb').read()
    tipo = 'image/png' if a.imagen.lower().endswith('.png') else 'image/jpeg'
    crudo, tipo = sitio['normalize_chart_image'](crudo, tipo)
    b64 = base64.b64encode(crudo).decode('ascii')

    # 🔴 UNA SESIÓN SSH NO HEREDA LAS VARIABLES DE SUPERVISOR, y en producción
    #    la clave de OpenAI vive justo ahí, no en el entorno ni en el `.env`.
    #    Mirar solo `os.environ` hacía caer al respaldo de GitHub Models —cuyo
    #    host ni siquiera resuelve DNS en el VPS— y la corrida moría con un
    #    'Name or service not known' que parece un problema de red y no lo es.
    #    ⚠️ Está DOCUMENTADO en `agudeza_visual._clave`, con la advertencia de
    #    que este mismo error casi hace cambiar de modelo por nada. Se reutiliza
    #    ese buscador en vez de repetir la trampa: entorno → scalpel/.env →
    #    línea `environment=` del conf de supervisor.
    import importlib.util
    _sp = importlib.util.spec_from_file_location(
        'ag', os.path.join(RAIZ, 'tools', 'agudeza_visual.py'))
    _ag = importlib.util.module_from_spec(_sp)
    _sp.loader.exec_module(_ag)
    from openai import OpenAI
    try:
        clave = _ag._clave('openai')
    except SystemExit:
        clave = ''
    if clave:
        cliente, backend = OpenAI(api_key=clave), 'openai'
    else:
        cliente = OpenAI(base_url='https://models.inference.ai.azure.com',
                         api_key=_ag._clave('github'))
        backend = 'github'
    # nunca la clave: solo qué backend salió
    print('[IA] backend=%s modelo=%s' % (backend, sitio['MODEL']))
    if backend != 'openai':
        print('⚠️  Sin OPENAI_API_KEY se usa GitHub Models, que en este VPS no '
              'resuelve. Si esto falla, no es la prueba: es la clave.')

    variantes = [('A', 'como corre hoy', False, None),
                 ('B', 'con la cláusula de verificación ENCENDIDA', True, None)]
    # D = C corregido: solo hechos verificados y prohibido inventar referencias
    if hechos_txt:
        variantes.append(('C', 'con el BLOQUE DE HECHOS medido', False,
                          hechos_txt))
        variantes.append(('D', 'hechos verificados + cláusula + prohibido '
                               'inventar referencias', True, hechos_txt))
    if hechos_txt:
        variantes.append(('E', 'TODO: bloque completo con sus tasas + la tabla '
                               'de velas medidas + cláusula', True,
                          completo_txt, tabla_txt))
        # 🔴 F ES LA PRUEBA LIMPIA, y existe por una objeción del dueño que era
        #    correcta: en E le damos la tabla PERO TAMBIÉN nuestras líneas de
        #    acumulación, liquidez y manipulación ya calculadas. Si entonces
        #    nombra la acumulación, no prueba que sepa deducirla: prueba que
        #    sabe copiar. Textualmente: «a mí me interesa que la IA sepa deducir
        #    cuándo hay acumulación, en dónde y cuándo no».
        #    F le da SOLO la tabla de velas medidas. Cero hechos, cero pistas,
        #    ni una palabra sobre acumulación. Lo que diga, lo dedujo él.
        #    ⚠️ Y sirve en las dos direcciones: si en F inventa una acumulación
        #    donde no la hay, eso también se ve — que es la otra mitad de lo
        #    que pidió, "y cuándo no".
        variantes.append(('F', 'SOLO la tabla de velas medidas: ¿lo deduce '
                               'sin que se lo digamos?', True, None, tabla_txt))
    variantes = [(v + (None,))[:5] for v in variantes]
    if a.solo:
        quiero = set(a.solo.upper().replace(',', ' ').split())
        variantes = [v for v in variantes if v[0] in quiero]

    salida = ['# Comparativa del analizador — %s\n' % os.path.basename(a.imagen)]
    if hechos_txt:
        salida += ['## Bloque de hechos que se le entrega en C\n',
                   '```\n%s\n```\n' % hechos_txt]
    for letra, titulo, verificar, hechos, tabla in variantes:
        sitio['ANALYZE_VERIFY_CLAIMS'] = verificar
        sistema = sitio['build_system_prompt'](a.approach)
        usuario = mensaje_usuario(datos, notas, hechos, tabla)
        print('\n─── %s · %s ───' % (letra, titulo))
        r = cliente.chat.completions.create(
            model=sitio['MODEL'],
            messages=[{'role': 'system', 'content': sistema},
                      {'role': 'user', 'content': [
                          {'type': 'text', 'text': usuario},
                          {'type': 'image_url', 'image_url': {
                              'url': 'data:%s;base64,%s' % (tipo, b64),
                              'detail': sitio['ANALYZE_IMG_DETAIL']}}]}],
            max_tokens=900, temperature=0.3)
        txt = r.choices[0].message.content
        print(txt)
        salida.append('\n## %s · %s\n\n%s\n' % (letra, titulo, txt))
        # 🔑 AUDITORÍA AUTOMÁTICA: ¿citó alguna vela que no estaba en la lista?
        # Es la comprobación que a mano se me pasó la primera vez.
        if hechos and letra in ('C', 'D', 'E'):
            dados = set(re.findall(r'candle (\d+)', hechos))
            citados = set(re.findall(r'vela[s]? (\d+)', txt))
            inventados = sorted(citados - dados, key=int)
            print('   [auditoría] velas citadas que NO estaban en el bloque: %s'
                  % (', '.join(inventados) if inventados else 'ninguna ✅'))
            salida.append('\n> auditoría — velas inventadas: %s\n'
                          % (', '.join(inventados) if inventados else 'ninguna'))

    carpeta = os.path.dirname(a.salida)
    if carpeta and not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    io.open(a.salida, 'w', encoding='utf-8').write('\n'.join(salida))
    print('\nguardado en %s' % a.salida)


if __name__ == '__main__':
    main()
