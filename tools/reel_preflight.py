# -*- coding: utf-8 -*-
"""Reel #2 — PRE-FLIGHT: lo que tu propio historial dice de ti.

Encargo del dueño: un reel corto, gancho primero, sobre Pre-Flight, y —añadido
suyo— que al final se vean las estadísticas COMPARADAS entre proyectos,
*"como para que vean que no solo tiene el GO / NO-GO, sino que es una
herramienta bien fundamentada"*.

═══ POR QUÉ ESTO NO GRABA VÍDEO (a diferencia de `reel_tour.py`) ═══
Una tarjeta de estadística es CONTENIDO QUIETO. Grabarla en vídeo a 900 px de
ancho y luego ampliarla para que el número se lea en un teléfono deja el texto
hecho papilla. Aquí se capturan FOTOS a doble densidad (1800 px reales) y el
movimiento —los barridos y los acercamientos— se hace en el montaje sobre esa
foto: el número sigue nítido con el doble de zoom. El único momento con
"movimiento" real, marcar las casillas, es un cambio de estado discreto: se
capturan las 4 fotos de esos 4 estados y se pasan como fotogramas.
Efecto secundario: sin vídeo no hace falta la tubería de marcas de croma ni el
WebM intermedio, así que esto es una fracción del tamaño de `reel_tour.py`.

═══ CAJA SEGURA: SIRVE PARA TIKTOK **Y** REELS DESDE EL PRIMER MONTAJE ═══
El reel del tour hubo que re-encuadrarlo después (`reel_tiktok.py`) porque
TikTok llena la pantalla y se come ~118 px de cada lado, más ~440 px de
interfaz abajo. Aquí ese margen va metido de fábrica (`CAJA`), así que un solo
archivo se publica en los dos sitios sin tocar nada.

═══ LOS NÚMEROS ═══
Salen de `tools/reel_pf_datos.py`, que declara su generador ANTES de mirar
resultados, y entran por la MISMA API que usa la pantalla. En el reel no se
escribe ni un número a mano: lo que se ve es lo que el panel calcula.
🔴 Lo medido allí es lo que decidió el guion — ver su cabecera.

    python3 tools/reel_preflight.py                  # captura y monta
    python3 tools/reel_preflight.py --solo-capturar  # solo las fotos
    python3 tools/reel_preflight.py --solo-montar    # reusa las fotos
"""
from __future__ import print_function

import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'out', 'reels')
FOTOS = os.path.join(SALIDA, '_pf')
PUERTO = 5131
CL = 'Zx9!wQ4mNp2r'
USUARIO = 'ryan.cole'
VW, VH = 900, 1600          # ventana de captura
DPR = 2                     # doble densidad: las fotos salen a 1800×3200
W, H = 1080, 1920
FPS = 30
ORO = '#c9a227'
GRAFITO = '#0b0d12'
IDIOMA = os.environ.get('REEL_LANG', 'en')
# Los dos proyectos que narra el reel, por NOMBRE (nunca por posición):
#  · PROYECTO  = el de la lista que se marca en pantalla.
#  · RENTABLE  = el del remate: el que MENOS acierta y más deja por trade.
PROYECTO = 'ICT'
RENTABLE = 'Chartismo' if IDIOMA == 'es' else 'Chart patterns'
# Las filas del panel se buscan POR SU ETIQUETA, y la etiqueta está
# traducida: con las claves en español el reel en inglés no encontraba
# ninguna y moría. Una tabla por idioma, no un `if` suelto.
FILAS = {
 'es': {'fg': 'GOs falsos', 'wr': 'Win rate', 'exp': 'Expectativa en R',
        'pf': 'Profit factor', 'dd': 'Drawdown máximo',
        'n': 'Trades registrados'},
 'en': {'fg': 'False GOs', 'wr': 'Win rate', 'exp': 'Expectancy in R',
        'pf': 'Profit factor', 'dd': 'Max drawdown',
        'n': 'Trades logged'},
}[IDIOMA]
ALTO_HIST = 2600          # px de historial que recorre el barrido del reel
# La firma sonora que eligió el dueño: el candidato 03 pelado, solo la cuerda
# (se le quitaron el "wooop" de graves y los clics). Vive en out/marca_sonora/
# y se regenera con `python3 tools/marca_sonora.py`.
MARCA_SONORA = '03E_solo_cuerda_larga'
GOLPE_EN_WAV = 2.00       # segundo del wav en que cae el impacto

sys.path.insert(0, os.path.join(RAIZ, 'tools'))


# ══ 1 · CAPTURA ══════════════════════════════════════════════════════════
def arranca_servidor(tmp):
    os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tmp, 'pf.db')
    os.environ.setdefault('SECRET_KEY', 'reel-preflight')
    sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
    import app as A
    import reel_pf_datos as D

    with A.app.app_context():
        A.db.create_all()
        u = A.User.query.filter_by(username=USUARIO).first()
        if u is None:
            u = A.User(username=USUARIO, email='pf@demo.invalid',
                       email_verified=True)
            A.db.session.add(u)
        u.set_password(CL)
        u.email_canonical = u.email
        u.plan = 'premium'
        A.db.session.commit()

    threading.Thread(target=lambda: A.app.run(port=PUERTO, threaded=True,
                                              use_reloader=False),
                     daemon=True).start()
    for _ in range(80):
        time.sleep(.25)
        try:
            urllib.request.urlopen('http://127.0.0.1:%d/health' % PUERTO,
                                   timeout=1)
            break
        except Exception:
            pass
    else:
        sys.exit('el servidor no arrancó')

    # ── los trades entran POR LA API, como los metería una persona ──
    c = A.app.test_client()
    c.post('/login', data={'identifier': USUARIO, 'password': CL},
           follow_redirects=True)
    resumen = []
    for p, cfg, trades, res in D.genera(IDIOMA):
        r = c.post('/api/preflight/checklists',
                   json={'name': p['nombre'], 'config': cfg})
        assert r.status_code == 200, (p['nombre'], r.status_code, r.get_json())
        cl = r.get_json()['checklist']
        for t in trades:
            payload = dict(t)
            payload['checklist_id'] = cl['id']
            payload['trade_date'] = t['trade_date'].isoformat()
            resultado = payload.pop('outcome')
            r = c.post('/api/preflight/checks', json=payload)
            assert r.status_code == 200, (r.status_code, r.get_json())
            chk = r.get_json()['check']
            r = c.put('/api/preflight/checks/%d' % chk['id'],
                      json={'outcome': resultado})
            assert r.status_code == 200, (r.status_code, r.get_json())
        resumen.append(res)
    print('sembrados: %d trades en %d proyectos'
          % (sum(r['registrados'] for r in resumen), len(resumen)))
    return resumen


def captura():
    from playwright.sync_api import sync_playwright
    if os.path.isdir(FOTOS):
        shutil.rmtree(FOTOS)
    os.makedirs(FOTOS)
    tmp = tempfile.mkdtemp()
    resumen = arranca_servidor(tmp)
    URL = 'http://127.0.0.1:%d' % PUERTO
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')
           or [None])[0]
    leidos = {}

    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'],
                              **({'executable_path': exe} if exe else {}))
        ctx = b.new_context(viewport={'width': VW, 'height': VH},
                            device_scale_factor=DPR)
        pg = ctx.new_page()
        errores = []
        pg.on('pageerror', lambda e: errores.append(str(e)))
        pg.route('**/*', lambda r: r.continue_()
                 if '127.0.0.1' in r.request.url else r.abort())
        pg.goto(URL + '/login', wait_until='domcontentloaded')
        pg.fill('input[name=identifier]', USUARIO)
        pg.fill('input[name=password]', CL)
        pg.click('button[type=submit]')
        pg.wait_for_timeout(900)
        pg.evaluate("localStorage.setItem('scalpel_lang','%s')" % IDIOMA)
        pg.evaluate("localStorage.setItem('scalpel_theme','dark')")
        # ⚠️ /app BORRA el cookie del splash al servirse (es de un solo uso):
        #    hay que reponerlo antes de CADA visita o rebota a /welcome.
        pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                                 'url': URL + '/'}])
        pg.goto(URL + '/app', wait_until='domcontentloaded')
        pg.wait_for_timeout(2600)
        # ⚠️ Tessera vive anclada abajo a la derecha y su nube ("¿Te echo una
        #    mano?") cae ENCIMA de la tabla en todas las fotos. En el reel del
        #    tour eso era una escena; aquí es basura sobre los datos. Se oculta
        #    SOLO en el navegador de la captura — no se toca nada del sitio.
        pg.add_style_tag(content='#nx-cube{display:none!important}')
        pg.evaluate("""() => { const e =
            document.querySelector('.tab[data-tab="preflight"]'); if (e) e.click(); }""")
        pg.wait_for_timeout(2600)

        def foto(nombre, sel=None, margen=0):
            ruta = os.path.join(FOTOS, nombre + '.png')
            if sel:
                el = pg.query_selector(sel)
                if el is None:
                    print('  ⚠️ sin selector: %s' % sel)
                    return None
                if margen:
                    caja = el.bounding_box()
                    pg.screenshot(path=ruta, clip={
                        'x': max(0, caja['x'] - margen),
                        'y': max(0, caja['y'] - margen),
                        'width': min(VW, caja['width'] + 2 * margen),
                        'height': caja['height'] + 2 * margen})
                else:
                    el.screenshot(path=ruta)
            else:
                pg.screenshot(path=ruta)
            print('  · %s' % nombre)
            return ruta

        # ── A · el tablero: la lista marcándose ──
        # ⚠️ Las confluencias NO son <input type=checkbox>: son <div class=pf-row>
        #    que llevan la clase `on` cuando están marcadas. Con el selector de
        #    checkbox no se encontraba ninguna y el tablero salía siempre vacío.
        # ⚠️ Y el proyecto se elige POR NOMBRE: el primer azulejo del mazo no es
        #    el que se cree (salió Chartismo), y el reel narra el de ICT.
        abierto = pg.evaluate("""nom => {
            const t = [...document.querySelectorAll('#pf-deck .proj-tile')]
              .find(x => x.textContent.indexOf(nom) >= 0);
            if (!t) return null; t.click(); return t.textContent.trim(); }""", PROYECTO)
        leidos['tablero_abierto'] = abierto
        pg.wait_for_timeout(1400)
        pg.evaluate("""() => document.querySelectorAll('#pf-rows .pf-row.on')
            .forEach(r => r.click())""")
        pg.wait_for_timeout(500)
        n = pg.evaluate("() => document.querySelectorAll('#pf-rows .pf-row').length")
        leidos['confluencias'] = n
        for i in range(n + 1):
            if i:
                pg.evaluate("""i => { const r =
                    document.querySelectorAll('#pf-rows .pf-row')[i-1];
                    if (r && !r.classList.contains('on')) r.click(); }""", i)
                pg.wait_for_timeout(260)
            foto('tablero_%d' % i, '#pf-board')
            leidos['veredicto_%d' % i] = pg.evaluate(
                "() => (document.getElementById('pf-verdict-label')||{}).textContent")
        foto('veredicto', '#pf-verdict', margen=10)
        # ── el CONSTRUCTOR: escribir las confluencias y fijar el umbral ──
        pg.evaluate("() => { const b = document.getElementById('pf-edit'); if (b) b.click(); }")
        pg.wait_for_timeout(1200)
        if pg.query_selector('#pf-builder'):
            foto('constructor', '#pf-builder')
            leidos['zonas_constructor'] = pg.evaluate("""dpr => {
                const c = document.getElementById('pf-builder').getBoundingClientRect();
                const uno = s => { const e = document.querySelector(s);
                  if (!e) return null; const r = e.getBoundingClientRect();
                  return {x: Math.round((r.left-c.left)*dpr), y: Math.round((r.top-c.top)*dpr),
                          w: Math.round(r.width*dpr), h: Math.round(r.height*dpr)}; };
                const a = uno('#pf-min-go'), b2 = uno('#pf-builder-rows');
                const um = document.querySelector('#pf-min-go');
                const caja = um ? um.closest('.pf-thresholds') || um.parentElement.parentElement : null;
                let u = null;
                if (caja) { const r = caja.getBoundingClientRect();
                  u = {x: Math.round((r.left-c.left)*dpr), y: Math.round((r.top-c.top)*dpr),
                       w: Math.round(r.width*dpr), h: Math.round(r.height*dpr)}; }
                return {filas: b2, mingo: a, umbral: u}; }""", DPR)
            pg.evaluate("() => { const b = document.getElementById('pf-builder-cancel'); if (b) b.click(); }")
            pg.wait_for_timeout(900)
        else:
            print('  ⚠️ no se abrió el constructor')
        # rects DENTRO de la foto del tablero, para poder encuadrar solo la
        # lista + el veredicto y dejar fuera el formulario de detalles
        leidos['zonas_tablero'] = pg.evaluate("""dpr => {
            const b = document.getElementById('pf-board').getBoundingClientRect();
            const uno = s => { const e = document.querySelector(s);
              if (!e) return null; const r = e.getBoundingClientRect();
              return {x: Math.round((r.left-b.left)*dpr), y: Math.round((r.top-b.top)*dpr),
                      w: Math.round(r.width*dpr), h: Math.round(r.height*dpr)}; };
            return {filas: uno('#pf-rows'), veredicto: uno('#pf-verdict')}; }""", DPR)

        # ── B · el historial y la tira global ──
        # ⚠️ 220 filas son ~35.000 px de alto: se recorta a lo que el barrido
        #    del reel llega a recorrer, o el montaje carga un PNG enorme para
        #    enseñar el 7%.
        # ⚠️ NO se recorta con `clip=` de la página: esas coordenadas son de
        #    PÁGINA y la tarjeta arranca muy por debajo del pliegue, así que
        #    Playwright responde "clipped area outside the image". Se le pone
        #    un tope de alto por CSS y se fotografía el elemento, que sí se
        #    desplaza solo.
        pg.add_style_tag(content='#pf-history{max-height:%dpx;overflow:hidden}'
                         % (ALTO_HIST // DPR))
        pg.wait_for_timeout(300)
        foto('historial', '#pf-history-card')
        foto('tira', '#pf-stats')
        # 🔑 Cada tarjeta con su RECT: el reel amplía la celda concreta
        #    ("Adherencia 47.4%") en vez de encoger la tira entera, que a
        #    604 px de ancho se lee como una mancha (medido).
        leidos['tira'] = pg.evaluate("""dpr => {
            const c = document.getElementById('pf-stats');
            const rc = c.getBoundingClientRect();
            return [...c.querySelectorAll('.pf-stat')].map(e => {
              const r = e.getBoundingClientRect();
              return {v: (e.querySelector('.pf-stat-val')||{}).textContent,
                      k: (e.querySelector('.pf-stat-key')||{}).textContent,
                      x: Math.round((r.left-rc.left)*dpr), y: Math.round((r.top-rc.top)*dpr),
                      w: Math.round(r.width*dpr), h: Math.round(r.height*dpr)}; }); }""", DPR)

        # ── C · las tarjetas concretas del proyecto ──
        pg.evaluate("""() => { const b =
            document.querySelector('.pf-tab[data-pftab="projects"]'); if (b) b.click(); }""")
        pg.wait_for_timeout(1400)
        # 🔴 el chip activo por defecto NO es el primero de la lista de datos:
        #    se elige por nombre o el reel narra los números de otro proyecto
        leidos['chips'] = pg.evaluate(
            "() => [...document.querySelectorAll('#pf-proj-chips .pf-proj-chip')].map(b => b.textContent.trim())")
        for nombre_p in (PROYECTO, RENTABLE):
            pg.evaluate("""nom => { const b =
                [...document.querySelectorAll('#pf-proj-chips .pf-proj-chip')]
                  .find(x => x.textContent.indexOf(nom) >= 0); if (b) b.click(); }""", nombre_p)
            pg.wait_for_timeout(1100)
            clave = 'proyecto_' + ('ict' if nombre_p == PROYECTO else 'chart')
            leidos[clave] = pg.evaluate("""() =>
                [...document.querySelectorAll('#pf-proj-stats tr')].map(tr =>
                  [...tr.children].map(td => td.textContent.trim()))""")
            foto(clave, '#pf-proj-stats')
        # se vuelve al de ICT para los recortes de estadística sueltos
        pg.evaluate("""nom => { const b =
            [...document.querySelectorAll('#pf-proj-chips .pf-proj-chip')]
              .find(x => x.textContent.indexOf(nom) >= 0); if (b) b.click(); }""", PROYECTO)
        pg.wait_for_timeout(1100)
        # 🔑 La posición de cada FILA dentro de la foto del panel, medida en el
        #    navegador y pasada a píxeles de imagen (×DPR). Con esto el montaje
        #    puede hacer el acercamiento a una fila concreta sin adivinar
        #    coordenadas: una fila mal recortada enseña el número de al lado.
        leidos['filas_ict'] = pg.evaluate("""dpr => {
            const c = document.getElementById('pf-proj-stats');
            const rc = c.getBoundingClientRect();
            return [...c.querySelectorAll('tr')].map(tr => {
              const r = tr.getBoundingClientRect();
              return {t: (tr.children[0]||{}).textContent.trim(),
                      x: Math.round((r.left - rc.left) * dpr),
                      y: Math.round((r.top - rc.top) * dpr),
                      w: Math.round(r.width * dpr),
                      h: Math.round(r.height * dpr)}; }); }""", DPR)
        # ── D · la comparación entre proyectos (el añadido del dueño) ──
        pg.evaluate("""() => { const b =
            document.querySelector('.pf-tab[data-pftab="compare"]'); if (b) b.click(); }""")
        pg.wait_for_timeout(1000)
        pg.evaluate("""() => document.querySelectorAll('#pf-cmp-chips .pf-proj-chip')
            .forEach(b => b.click())""")
        pg.wait_for_timeout(1600)
        leidos['comparacion'] = pg.evaluate("""() =>
            [...document.querySelectorAll('#pf-cmp-table tr')].map(tr =>
              [...tr.children].map(td => td.textContent.trim()))""")
        foto('comparar', '#pf-cmp-table')
        foto('comparar_pantalla')
        leidos['filas_cmp'] = pg.evaluate("""dpr => {
            const c = document.getElementById('pf-cmp-table');
            const rc = c.getBoundingClientRect();
            return [...c.querySelectorAll('tr')].map(tr => {
              const r = tr.getBoundingClientRect();
              return {t: (tr.children[0]||{}).textContent.trim(),
                      x: Math.round((r.left - rc.left) * dpr),
                      y: Math.round((r.top - rc.top) * dpr),
                      w: Math.round(r.width * dpr),
                      h: Math.round(r.height * dpr)}; }); }""", DPR)

        leidos['errores_js'] = errores
        b.close()

    io.open(os.path.join(FOTOS, 'leido.json'), 'w', encoding='utf-8').write(
        json.dumps({'resumen': resumen, 'pantalla': leidos},
                   indent=1, ensure_ascii=False))
    if errores:
        print('🔴 errores de JS: %s' % errores[:3])
    print('fotos en', FOTOS)
    return leidos




# ══ 2 · EL MONTAJE ═══════════════════════════════════════════════════════
# 🔑 CAJA SEGURA. TikTok llena la pantalla: en un teléfono 19.5:9 se pierden
#    ~118 px de cada lado, ~440 px abajo (usuario, texto, música) y ~190 px
#    arriba. Todo lo que TIENE que leerse vive dentro de esta caja; fuera solo
#    va relleno desenfocado, que se puede recortar sin perder nada.
CAJA = {'izq': 158, 'der': 762, 'arriba': 210, 'abajo': 1450}
ANCHO_CAJA = CAJA['der'] - CAJA['izq']          # 604

TEXTOS = {
 'en': {
  'eq': 'Tradeable Academy',
  'lema': 'Process over impulse.',
  # 🔴 El reel NO le habla a alguien que ya usa el sitio. Le habla a un trader
  #    que no lo conoce: primero el problema que ya tiene, después la
  #    herramienta como salida. Estructura dictada por el dueño.
  'h1': ['How many of your', 'trades actually', 'followed <em>your plan</em>?'],
  'h2': ['How many were', '<em>revenge</em>?', 'How many were <em>fear</em>?'],
  'giro': ['Those days', 'are over.'],
  'giroSub': 'PRE-FLIGHT',
  'lista': ['Write down every', 'confluence you use.'],
  'listaSub': 'Your setup. Your words. Not a template.',
  'umbral': ['You pick how many', 'are enough', 'to enter.'],
  'umbralSub': 'Set your own bar for GO and for CAUTION.',
  'semaforo': ['A traffic light', 'answers before', 'you click.'],
  'semaforoSub': 'It reads the boxes you ticked on your chart — nothing else.',
  'stats': ['Every check you log', 'becomes <em>your</em>', 'own numbers.'],
  'statsSub': 'Not a demo account. Not a guru. The trades you actually took.',
  'cmp': ['Trading more than', 'one strategy?'],
  'cmpSub': 'Put them side by side.',
  'wr': 'The one that wins least…',
  'expr': '…is the one that pays most.',
  'exprSub': 'Win rate is not profit. Expectancy in R is.',
  'duT': ['Win rate', 'is not <em>profit</em>.'],
  'legal': 'Educational content · Not financial advice · Demo data',
  'fWr': 'Win rate', 'fExp': 'Expectancy',
  'mWr': 'Win rate', 'mExp': 'Expectancy', 'mPf': 'Profit factor',
  'mDd': 'Max drawdown', 'mN': 'Trades logged',
 },
 'es': {
  'eq': 'Tradeable Academy',
  'lema': 'Proceso antes que impulso.',
  'h1': ['¿Cuántos de tus', 'trades siguieron', '<em>tu plan</em> de verdad?'],
  'h2': ['¿Cuántos fueron', '<em>venganza</em>?', '¿Cuántos fueron <em>miedo</em>?'],
  'giro': ['Esos tiempos', 'se acabaron.'],
  'giroSub': 'PRE-FLIGHT',
  'lista': ['Anota cada confluencia', 'que de verdad usas.'],
  'listaSub': 'Tu setup. Tus palabras. No una plantilla.',
  'umbral': ['Tú decides cuántas', 'bastan', 'para entrar.'],
  'umbralSub': 'Pones tu propio listón para el GO y para la PRECAUCIÓN.',
  'semaforo': ['Un semáforo', 'responde antes', 'de que hagas clic.'],
  'semaforoSub': 'Lee las casillas que marcaste en tu gráfico. Nada más.',
  'stats': ['Cada chequeo', 'se vuelve', '<em>tus</em> números.'],
  'statsSub': 'No una cuenta demo. No un gurú. Los trades que tomaste.',
  'cmp': ['¿Operas más de', 'una estrategia?'],
  'cmpSub': 'Ponlas lado a lado.',
  'wr': 'La que menos acierta…',
  'expr': '…es la que más deja.',
  'exprSub': 'El win rate no es rentabilidad. La expectativa en R sí.',
  'duT': ['Aciertos no es', '<em>rentabilidad</em>.'],
  'legal': 'Contenido educativo · No es asesoría financiera · Datos de demostración',
  'fWr': 'Aciertos', 'fExp': 'Expectativa',
  'mWr': 'Win rate', 'mExp': 'Expectativa en R', 'mPf': 'Profit factor',
  'mDd': 'Drawdown máximo', 'mN': 'Trades registrados',
 },
}


def _lee():
    """Los números del reel salen del panel, nunca de un dedo."""
    d = json.loads(io.open(os.path.join(FOTOS, 'leido.json'),
                           encoding='utf-8').read())['pantalla']
    def busca(filas, clave):
        k = clave.lower()
        for f in filas:
            if f and f[0].strip().lower() == k:
                return f
        for f in filas:
            if f and f[0].strip().lower().startswith(k):
                return f
        sys.exit('🔴 no encontré la fila "%s" en el panel' % clave)

    def de(filas, clave):
        return busca(filas, clave)[1]
    tira = {x['k']: x['v'] for x in d['tira']}
    celdas = {x['k']: x for x in d['tira']}
    ict = d['proyecto_ict']
    cmp_ = d['comparacion']
    cols = cmp_[0][1:]
    def fila(clave):
        return dict(zip(cols, busca(cmp_, clave)[1:]))
    wr = fila(FILAS['wr'])
    ex = fila(FILAS['exp'])
    # el proyecto con PEOR win rate, leído del panel (no elegido a mano)
    num = lambda s: float(s.split('%')[0].replace(',', '.'))
    rentable = min(cols, key=lambda c: num(wr[c]))
    return {
        'celdas': celdas, 'filasIct': d.get('filas_ict', []),
        'zonas': d.get('zonas_tablero', {}),
        'adherencia': tira.get('Adherencia', '—'),
        'registrados': tira.get('Chequeos registrados', '—'),
        'falsosGo': de(ict, FILAS['fg']),
        'wrIct': de(ict, FILAS['wr']), 'expIct': de(ict, FILAS['exp']),
        'pfIct': de(ict, FILAS['pf']), 'ddIct': de(ict, FILAS['dd']),
        'nIct': de(ict, FILAS['n']),
        'pf': fila(FILAS['pf']), 'dd': fila(FILAS['dd']),
        'proyIct': [f[0] for f in ict][:1] and 'ICT — NY AM',
        'cols': cols, 'wr': wr, 'expR': ex, 'rentable': rentable,
        'wrPeor': wr[rentable], 'exPeor': ex[rentable],
    }


PAGINA = u"""<!doctype html><meta charset=utf-8><style>@@FUENTES@@
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:@@W@@px;height:@@H@@px;background:@@GRAF@@;overflow:hidden;
  font-family:Inter,sans-serif;color:#fff}
/* ── ambiente: la propia captura, desenfocada, llenando el lienzo ── */
#amb{position:absolute;inset:-60px;background-size:cover;background-position:center;
  filter:blur(24px) saturate(.85) brightness(.58);opacity:0}
#vig{position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 84% 66% at 50% 44%,transparent 46%,rgba(0,0,0,.72))}
#rej{position:absolute;inset:0;opacity:.14;pointer-events:none;
  background-image:linear-gradient(rgba(255,255,255,.10) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.10) 1px,transparent 1px);
  background-size:54px 54px}
/* ── la tarjeta con la captura real ── */
#marco{position:absolute;overflow:hidden;border-radius:18px;
  border:1px solid rgba(201,162,39,.34);
  box-shadow:0 26px 90px rgba(0,0,0,.75),0 0 0 1px rgba(0,0,0,.5);opacity:0}
#marco img{position:absolute;left:0;top:0;display:block;image-rendering:auto}
/* ── tipografía del reel ── */
#h{position:absolute;left:@@IZQ@@px;width:@@ANCHO@@px;opacity:0}
#h .l{font:900 62px/1.07 Inter,sans-serif;letter-spacing:-.035em;
  text-shadow:0 8px 42px rgba(0,0,0,.92)}
#h .l em{font-style:normal;color:@@ORO@@}
#sub{position:absolute;left:@@IZQ@@px;width:@@ANCHO@@px;opacity:0;
  font:500 27px/1.34 Inter,sans-serif;color:rgba(255,255,255,.80);
  text-shadow:0 4px 24px rgba(0,0,0,.9)}
/* ── el número gigante ── */
#big{position:absolute;left:@@IZQ@@px;width:@@ANCHO@@px;text-align:center;opacity:0}
#big .n{font:900 168px/0.92 Inter,sans-serif;letter-spacing:-.055em;color:@@ORO@@;
  text-shadow:0 14px 60px rgba(0,0,0,.9)}
#big .k{margin-top:12px;font:700 25px 'JetBrains Mono',monospace;
  letter-spacing:.20em;text-transform:uppercase;color:rgba(255,255,255,.72)}
/* ── el duelo entre proyectos, tipografiado (la tabla real no se puede leer
      en vertical: 1640 px de ancho en una caja de 604) ── */
#duelo{position:absolute;left:@@IZQ@@px;width:@@ANCHO@@px;opacity:0}
#duelo table{width:100%;border-collapse:collapse}
#duelo th,#duelo td{padding:16px 5px;text-align:center}
#duelo th{font:700 24px 'JetBrains Mono',monospace;letter-spacing:.06em;
  color:rgba(255,255,255,.60);border-bottom:1px solid rgba(255,255,255,.16)}
#duelo td.k{text-align:left;font:600 24px Inter,sans-serif;
  color:rgba(255,255,255,.62);white-space:nowrap}
#duelo td.v{font:800 46px 'JetBrains Mono',monospace;letter-spacing:-.02em}
#duelo .col.on th{color:@@ORO@@}
#duelo .on-cell{color:@@ORO@@}
#duelo td.mal{color:#f0785a}
#duelo tr+tr td{border-top:1px solid rgba(255,255,255,.10)}
#duelo .cap{margin-top:30px;font:700 34px/1.30 Inter,sans-serif;
  color:rgba(255,255,255,.78)}
/* ── el nombre del producto, en el giro ── */
#marca{position:absolute;left:@@IZQ@@px;width:@@ANCHO@@px;opacity:0;
  font:900 58px 'JetBrains Mono',monospace;letter-spacing:.16em;color:@@ORO@@;
  text-shadow:0 6px 34px rgba(0,0,0,.9)}
/* ── rejilla de métricas ── */
#rej2{position:absolute;left:@@IZQ@@px;width:@@ANCHO@@px;opacity:0;
  display:grid;grid-template-columns:1fr 1fr;gap:26px 22px}
#rej2 .m{border-left:3px solid rgba(201,162,39,.55);padding:6px 0 6px 18px}
#rej2 .mk{font:700 19px 'JetBrains Mono',monospace;letter-spacing:.10em;
  text-transform:uppercase;color:rgba(255,255,255,.58)}
#rej2 .mv{margin-top:8px;font:900 54px/1 Inter,sans-serif;letter-spacing:-.03em;
  color:#fff;text-shadow:0 6px 30px rgba(0,0,0,.9)}
/* ── cierre ── */
#out{position:absolute;inset:0;background:#05060a;display:flex;
  flex-direction:column;align-items:center;justify-content:center;gap:26px;opacity:0}
#out img{width:470px}
#out .s{font:700 24px 'JetBrains Mono',monospace;letter-spacing:.32em;
  color:@@ORO@@;text-transform:uppercase}
#out .a{font:800 40px/1.2 Inter,sans-serif;text-align:center}
#out .a span{display:block;color:rgba(255,255,255,.62);font-weight:600;font-size:32px}
#out .l{position:absolute;bottom:@@LEGAL@@px;font:400 21px Inter,sans-serif;
  color:rgba(255,255,255,.34);text-align:center;width:100%}
#flash{position:absolute;inset:0;background:#fff;opacity:0;pointer-events:none}
#bar{position:absolute;left:0;bottom:@@BARRA@@px;height:6px;background:@@ORO@@}
</style><body>
<div id=amb></div><div id=rej></div>
<div id=marco><img id=shot src=""></div>
<div id=vig></div>
<div id=h></div><div id=sub></div><div id=big></div>
<div id=marca></div><div id=rej2></div><div id=duelo></div>
<div id=flash></div>
<div id=out><img src="@@LOGO@@" alt=""><div class=s>@@EQ@@</div>
  <div class=a>@@LEMA@@</div>
  <div class=l>@@LEGAL_TXT@@</div></div>
<div id=bar></div>
<script>
const PLAN=@@PLAN@@, DUR=@@DUR@@, CAJA=@@CAJA@@;
const E=id=>document.getElementById(id);
const suav=t=>t<0?0:t>1?1:t*t*(3-2*t);
const tr=(t,a,b)=>suav((t-a)/(b-a));
const lerp=(a,b,k)=>a+(b-a)*k;

function escena(t){ for(const s of PLAN) if(t>=s.t0 && t<s.t1) return s; return null; }

/* Coloca la captura: se le da un RECORTE en píxeles de la imagen y se estira
   para que ese recorte llene el ancho de la caja segura. Interpolando entre
   dos recortes sale el barrido / acercamiento. */
function encuadra(s,k){
  const img=E('shot'), marco=E('marco');
  const c=[0,1,2,3].map(i=>lerp(s.c0[i], (s.c1||s.c0)[i], k));
  const anchoCaja = s.ancho || CAJA.ancho;
  const esc = anchoCaja / c[2];
  const alto = Math.min(s.alto || 1e9, Math.round(c[3]*esc));
  marco.style.width = anchoCaja+'px';
  marco.style.height = alto+'px';
  marco.style.left = Math.round((@@W@@-anchoCaja)/2)+'px';
  marco.style.top = s.y+'px';
  img.style.width = Math.round(s.iw*esc)+'px';
  img.style.left = Math.round(-c[0]*esc)+'px';
  img.style.top = Math.round(-c[1]*esc)+'px';
}

window.enCuadre = function(t){
  const s = escena(t);
  const k = s ? (t-s.t0)/(s.t1-s.t0) : 0;
  const ap = s ? tr(t,s.t0+.06,s.t0+.34)*(1-tr(t,s.t1-.30,s.t1-.02)) : 0;

  // ── captura ──
  const marco=E('marco'), img=E('shot'), amb=E('amb');
  if (s && s.img){
    const src = (s.seq ? s.seq[Math.min(s.seq.length-1,
                  Math.floor(k*s.seq.length))] : s.img);
    if (!img.src.endsWith(src)) img.src = src;
    encuadra(s,k);
    marco.style.opacity = s.desnudo ? 0 : ap;
    amb.style.backgroundImage = 'url("'+src+'")';
    amb.style.opacity = (s.amb===0?0:1)*Math.min(1,ap*1.2);
  } else { marco.style.opacity=0; amb.style.opacity=0; }

  // ── titular y subtítulo ──
  const h=E('h'), sub=E('sub');
  if (s && s.h){
    h.innerHTML = s.h.map(l=>'<div class=l>'+l+'</div>').join('');
    h.style.top = s.hy+'px';
    const a2 = s.h2 ? tr(t,s.h2-.28,s.h2+.02) : 0;
    if (s.h2 && t>=s.h2){ h.innerHTML = s.hB.map(l=>'<div class=l>'+l+'</div>').join(''); }
    h.style.opacity = ap;
    h.style.transform = 'translateY('+(22*(1-ap))+'px)';
  } else h.style.opacity=0;
  if (s && s.sub){
    sub.textContent = s.sub; sub.style.top = s.suby+'px';
    sub.style.opacity = ap*.96;
  } else sub.style.opacity=0;

  // ── número gigante ──
  const big=E('big');
  if (s && s.big){
    big.innerHTML = '<div class=n>'+s.big+'</div><div class=k>'+s.bigK+'</div>';
    big.style.top = s.bigy+'px';
    /* el número entra con un golpe de escala: es el momento del reel */
    const g = tr(t,s.t0+.02,s.t0+.30);
    big.style.opacity = ap;
    big.style.transform = 'scale('+lerp(1.14,1,g)+')';
  } else big.style.opacity=0;

  // ── el nombre del producto ──
  const mk=E('marca');
  if (s && s.marca){ mk.textContent=s.marca; mk.style.top=s.marcay+'px';
    const g=tr(t,s.t0+.55,s.t0+1.05);
    mk.style.opacity=ap*g; mk.style.letterSpacing=(0.16+0.10*(1-g))+'em';
  } else mk.style.opacity=0;

  // ── rejilla de métricas ──
  const rj=E('rej2');
  if (s && s.rejilla){ rj.innerHTML=s.rejilla; rj.style.top=s.rejy+'px';
    rj.style.opacity=ap;
    /* entran de una en una: cuatro números de golpe no se leen */
    [...rj.children].forEach((e,i)=>{ const g=tr(t,s.t0+.30+i*.42,s.t0+.72+i*.42);
      e.style.opacity=g; e.style.transform='translateY('+(18*(1-g))+'px)'; });
  } else rj.style.opacity=0;

  // ── duelo tipografiado ──
  const du=E('duelo');
  if (s && s.duelo){
    du.innerHTML = s.duelo; du.style.top = s.duy+'px';
    du.style.opacity = ap;
    const fase2 = s.on2 && t>=s.on2;
    du.querySelectorAll('.on-cell,.mal').forEach(e=>e.classList.remove('on-cell','mal'));
    du.querySelectorAll((fase2?'.e':'.w')+s.onCol)
      .forEach(e=>e.classList.add(fase2?'on-cell':'mal'));
    if (s.cap2){ const c=du.querySelector('.cap');
      if (c) c.textContent = (t>=s.cap2 ? s.capB : s.capA); }
  } else du.style.opacity=0;

  // ── corte seco entre escenas ──
  let fl=0; for(const x of PLAN) if(x.corte) fl=Math.max(fl,1-Math.min(1,Math.abs(t-x.t0)/.08));
  E('flash').style.opacity = fl*.8;

  // ── cierre ──
  const o = tr(t,@@O0@@,@@O0@@+.5);
  E('out').style.opacity = o;
  E('out').style.clipPath = 'inset('+((1-o)*100)+'% 0 0 0)';
  E('bar').style.width = (100*t/DUR)+'%';
};
</script></body>"""


def _corto(nombre):
    """'Chartismo — Rupturas' → 'Chartismo'. Los nombres largos no caben."""
    return nombre.split('—')[0].split('(')[0].strip()


def _rejilla_html(d, T):
    """Cuatro métricas del proyecto, GRANDES.

    🔴 Antes esto era una foto del panel encogida a 700 px de ancho, y el
    dueño la vio "muy pequeña". Tenía razón: la tabla mide 1640 px nativos, o
    sea que el texto quedaba en ~12 px sobre un lienzo de 1080. Los valores
    siguen saliendo del panel (`leido.json`); lo único que cambia es que se
    componen aquí, a un tamaño que se lee en un teléfono.
    """
    filas = [(T['mWr'], d['wrIct']), (T['mExp'], d['expIct']),
             (T['mPf'], d['pfIct']), (T['mDd'], d['ddIct'])]
    return ''.join(
        '<div class="m"><div class="mk">%s</div><div class="mv">%s</div></div>'
        % (k, v.split('(')[0].strip()) for k, v in filas)


def _duelo_html(d, T):
    """La comparación, tipografiada. Los valores salen de `leido.json`."""
    cols = d['cols']
    idx = cols.index(d['rentable'])
    th = ''.join('<th class="c%d">%s</th>' % (i, _corto(c))
                 for i, c in enumerate(cols))
    def fila(clave, vals, marca):
        tds = ''.join('<td class="v c%d %s%d">%s</td>'
                      % (i, marca, i, vals[c].split('(')[0].strip())
                      for i, c in enumerate(cols))
        return '<tr><td class="k">%s</td>%s</tr>' % (clave, tds)
    wr = T['fWr'] if 'fWr' in T else 'Win rate'
    return ('<table><tr><td class="k"></td>%s</tr>%s%s</table>'
            '<div class="cap"></div>'
            % (th, fila(T['fWr'], d['wr'], 'w'),
               fila(T['fExp'], d['expR'], 'e')))


def monta():
    import imageio_ffmpeg
    from playwright.sync_api import sync_playwright
    import reel_tour as R

    T = TEXTOS[IDIOMA]
    T.setdefault('fWr', 'Win rate' if IDIOMA == 'en' else 'Aciertos')
    T.setdefault('fExp', 'Expectancy' if IDIOMA == 'en' else 'Expectativa')
    d = _lee()
    rects = json.loads(io.open(os.path.join(FOTOS, 'leido.json'),
                               encoding='utf-8').read())['pantalla']

    from PIL import Image
    tam = {}
    for f in os.listdir(FOTOS):
        if f.endswith('.png'):
            tam[f[:-4]] = Image.open(os.path.join(FOTOS, f)).size

    A = ANCHO_CAJA
    ANCHO_IMG = 760          # ancho de las capturas anchas (ver CAJA)
    todo = lambda n: [0, 0, tam[n][0], tam[n][1]]
    zon = rects['zonas_tablero']
    con = rects.get('zonas_constructor') or {}
    hw, hh = tam['historial']
    bw, bh = tam['tablero_0']

    # ── EL GUION ──────────────────────────────────────────────────────────
    # 🔴 REESCRITO tras la revisión del dueño. El primero le hablaba a alguien
    #    que YA usa el sitio ("tu adherencia", "tu lista") — o sea, no vendía
    #    nada. Este va: problema que el espectador ya tiene → la herramienta
    #    como salida → lo que le devuelve. Y cada rótulo dura 3,4 s o más:
    #    con 2,4 s la primera frase no daba tiempo ni a leerse.
    plan = []

    # 1-2 · EL PROBLEMA. Dos preguntas, sin producto todavía.
    plan.append(dict(
        t0=0.0, t1=4.00, img='historial.png', iw=hw, corte=False, desnudo=1,
        c0=[0, 0, hw, 1500], c1=[0, 700, hw, 1500], y=300, alto=900, amb=1,
        h=T['h1'], hy=560, sub=None))
    plan.append(dict(
        t0=4.00, t1=7.80, img='historial.png', iw=hw, corte=True, desnudo=1,
        c0=[0, 700, hw, 1500], c1=[0, hh - 1500, hw, 1500], y=300, alto=900, amb=1,
        h=T['h2'], hy=560, sub=None))

    # 3 · EL GIRO. Nombre del producto, a secas, sobre negro.
    plan.append(dict(
        t0=7.80, t1=11.20, img=None, corte=True,
        h=T['giro'], hy=640, big=None, marca=T['giroSub'], marcay=980))

    # 4 · LA LISTA — el constructor, que es donde se ESCRIBEN.
    if con.get('filas'):
        cf = con['filas']
        plan.append(dict(
            t0=11.20, t1=16.40, img='constructor.png', iw=tam['constructor'][0],
            corte=True, c0=[40, 800, 900, 600], c1=[40, 800, 900, 600],
            y=560, alto=640, ancho=ANCHO_IMG, amb=1,
            h=T['lista'], hy=250, sub=T['listaSub'], suby=1250))

    # 5 · EL UMBRAL — cuántas bastan para entrar.
    if con.get('umbral'):
        cu = con['umbral']
        plan.append(dict(
            t0=16.40, t1=21.00, img='constructor.png', iw=tam['constructor'][0],
            corte=True, c0=[40, 1470, 800, 200], c1=[40, 1470, 800, 200],
            y=660, alto=260, ancho=ANCHO_IMG, amb=1,
            h=T['umbral'], hy=250, sub=T['umbralSub'], suby=1230))

    # 6 · EL SEMÁFORO — la lista marcándose y el veredicto cambiando solo.
    zy, zh = zon['filas']['y'], (zon['veredicto']['y'] + zon['veredicto']['h']
                                 - zon['filas']['y'])
    plan.append(dict(
        t0=21.00, t1=26.60, img='tablero_6.png', iw=bw, corte=True,
        seq=['tablero_%d.png' % i for i in range(7)],
        c0=[zon['filas']['x'], zy, 1040, zh], c1=[zon['filas']['x'], zy, 1040, zh],
        y=540, alto=700, ancho=ANCHO_IMG, amb=1,
        h=T['semaforo'], hy=250, sub=T['semaforoSub'], suby=1290))

    # 7 · LOS NÚMEROS — tipografiados y GRANDES. La captura del panel real se
    #     quitó: el dueño la vio "muy pequeña", y con razón (1640 px de tabla
    #     metidos en 700 dejan el texto en 12 px).
    plan.append(dict(
        t0=26.60, t1=32.60, img=None, corte=True,
        rejilla=_rejilla_html(d, T), rejy=560,
        h=T['stats'], hy=250, sub=T['statsSub'], suby=1210))

    # 8 · LA COMPARACIÓN — el remate que pidió el dueño.
    plan.append(dict(
        t0=32.60, t1=39.60, img=None, corte=True,
        duelo=_duelo_html(d, T), duy=600, onCol=d['cols'].index(d['rentable']),
        on1=False, on2=36.10,
        capA=T['wr'], capB=T['expr'], cap2=36.10,
        h=T['cmp'], hy=250, sub=T['exprSub'], suby=1210))

    total = 44.20

    plan = [dict(s) for s in plan]

    doc = PAGINA
    caja = dict(CAJA); caja['ancho'] = A
    for marca, valor in (
            ('@@FUENTES@@', R.fuentes_css()), ('@@W@@', str(W)), ('@@H@@', str(H)),
            ('@@GRAF@@', GRAFITO), ('@@ORO@@', ORO),
            ('@@IZQ@@', str(CAJA['izq'])), ('@@ANCHO@@', str(A)),
            ('@@LOGO@@', 'logo_tour.png'), ('@@EQ@@', T['eq']),
            ('@@LEMA@@', T['lema']),
            ('@@LEGAL_TXT@@', T['legal']),
            ('@@LEGAL@@', str(H - CAJA['abajo'] + 70)),
            ('@@BARRA@@', str(H - CAJA['abajo'] + 10)),
            ('@@PLAN@@', json.dumps(plan)), ('@@CAJA@@', json.dumps(caja)),
            ('@@DUR@@', '%.2f' % total),
            ('@@O0@@', '%.2f' % (plan[-1]['t1'] - 0.10))):
        doc = doc.replace(marca, valor)

    R.logo_oscuro(os.path.join(FOTOS, 'logo_tour.png'))
    ruta = os.path.join(FOTOS, '_montaje.html')
    io.open(ruta, 'w', encoding='utf-8').write(doc)

    carpeta = tempfile.mkdtemp()
    n = int(total * FPS)
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')
           or [None])[0]
    print('montando %.1f s · %d fotogramas' % (total, n))
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox',
                                    '--allow-file-access-from-files'],
                              **({'executable_path': exe} if exe else {}))
        pg = b.new_page(viewport={'width': W, 'height': H})
        fallos = []
        pg.on('pageerror', lambda e: fallos.append(str(e)))
        pg.goto('file://' + ruta, wait_until='load')
        pg.wait_for_timeout(900)
        for i in range(n):
            pg.evaluate('enCuadre(%f)' % (i / float(FPS)))
            pg.screenshot(path=os.path.join(carpeta, '%04d.png' % i))
            if i % 90 == 0:
                print('  fotograma %d/%d' % (i, n))
        if fallos:
            print('🔴 errores de JS en el montaje: %s' % fallos[:3])
        b.close()

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    mudo = os.path.join(FOTOS, '_mudo.mp4')
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(FPS),
                    '-i', os.path.join(carpeta, '%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18',
                    '-movflags', '+faststart', mudo], check=True)
    shutil.rmtree(carpeta, ignore_errors=True)

    # ── LA MARCA SONORA ──────────────────────────────────────────────────
    # 🔑 El golpe tiene que caer cuando el logo ASIENTA, no cuando empieza el
    #    barrido: si suena antes, el oído lo separa de la marca y deja de
    #    leerse como una firma (medido en `tools/marca_sonora.py`, que fija el
    #    golpe en el segundo 2,00 del wav). Aquí el barrido arranca en O0 y
    #    tarda 0,5 s, así que el logo está entero en O0+0,5 → el wav empieza
    #    en O0 + 0,5 − 2,00.
    dest = os.path.join(SALIDA, 'reel-preflight.mp4')
    wav = os.path.join(RAIZ, 'out', 'marca_sonora', MARCA_SONORA + '.wav')
    asienta = (plan[-1]['t1'] - 0.10) + 0.50
    ms = int(round(max(0.0, asienta - GOLPE_EN_WAV) * 1000))
    if os.path.exists(wav):
        subprocess.run(
            [ff, '-y', '-loglevel', 'error', '-i', mudo, '-i', wav,
             '-filter_complex',
             '[1:a]adelay=%d|%d,pan=stereo|c0=c0|c1=c0[a]' % (ms, ms),
             '-map', '0:v:0', '-map', '[a]', '-c:v', 'copy',
             '-c:a', 'aac', '-b:a', '192k', '-shortest',
             '-movflags', '+faststart', dest], check=True)
        print('marca sonora %s · golpe en %.2f s' % (MARCA_SONORA, asienta))
    else:
        # ⚠️ Sin el wav el reel sale MUDO en vez de fallar: se regenera con
        #    `python3 tools/marca_sonora.py`, que no depende de nada externo.
        shutil.copy(mudo, dest)
        print('⚠️ sin marca sonora (falta %s) — el reel sale mudo' % wav)
    print('listo:', dest, '· %.1f MB' % (os.path.getsize(dest) / 1e6))
    return dest


if __name__ == '__main__':
    if '--solo-montar' not in sys.argv:
        captura()
    if '--solo-capturar' not in sys.argv:
        monta()
