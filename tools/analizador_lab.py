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


def mensaje_usuario(datos, notas, hechos=None):
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
            'absence proves anything.\n\n' % hechos)
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


def bloque_de_hechos(imagen, columnas, prov=None, modelo=None):
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
    lineas = ['VERIFIED (measured, high confidence):']
    lineas += ['  - ' + t for _f, t in firmes] or ['  - (none)']
    if marcados:
        lineas.append('')
        lineas.append('DETECTED BUT NOT VERIFIED (lower measured precision — '
                      'mention only as possibilities, never as fact):')
        lineas += ['  - ' + t for _f, t in marcados]
    return '\n'.join(lineas), r


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
        hechos_txt, _r = bloque_de_hechos(a.imagen, a.columnas, prov, modelo)
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
    if hechos_txt:
        variantes.append(('C', 'con el BLOQUE DE HECHOS medido', False,
                          hechos_txt))
    if a.solo:
        quiero = set(a.solo.upper().replace(',', ' ').split())
        variantes = [v for v in variantes if v[0] in quiero]

    salida = ['# Comparativa del analizador — %s\n' % os.path.basename(a.imagen)]
    if hechos_txt:
        salida += ['## Bloque de hechos que se le entrega en C\n',
                   '```\n%s\n```\n' % hechos_txt]
    for letra, titulo, verificar, hechos in variantes:
        sitio['ANALYZE_VERIFY_CLAIMS'] = verificar
        sistema = sitio['build_system_prompt'](a.approach)
        usuario = mensaje_usuario(datos, notas, hechos)
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

    carpeta = os.path.dirname(a.salida)
    if carpeta and not os.path.isdir(carpeta):
        os.makedirs(carpeta)
    io.open(a.salida, 'w', encoding='utf-8').write('\n'.join(salida))
    print('\nguardado en %s' % a.salida)


if __name__ == '__main__':
    main()
