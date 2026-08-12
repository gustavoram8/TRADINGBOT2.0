# -*- coding: utf-8 -*-
"""Pre-Flight usado COMO UN CLIENTE, para ver si las estadísticas sirven.

Pedido del dueño: *"hagas una especie de demo de prueba… te armes unos 3
proyectos distintos, cada uno con sus confluencias, y simules varias pasadas de
trades… Necesito que lo hagas DE VERDAD, no quiero que infles ni edites
resultados"*.

🔑 CÓMO SE GENERAN LOS RESULTADOS, declarado ANTES de mirar nada. Si el
resultado de cada trade lo eligiera yo a mano, la prueba no valdría: enseñaría
lo que yo quiera. Así que cada proyecto tiene una regla FIJA y un azar con
semilla, y luego se reporta lo que salga:

  · Proyecto 1 — ICT (SÍ hay señal):     P(ganar) = 0.34 + 0.055 · nº de
    confluencias marcadas, y "Barrida de liquidez" suma otro +0.10. O sea:
    marcar más casillas realmente ayuda, y una casilla concreta ayuda más.
  · Proyecto 2 — Wyckoff (NO hay señal): P(ganar) = 0.50 SIEMPRE, marques lo
    que marques. Sirve para ver si el panel se INVENTA patrones donde no hay.
  · Proyecto 3 — Chartismo (win rate bajo, R alto): P(ganar) = 0.38 fija, pero
    las ganadoras cobran 3-5R y las perdedoras pierden 1R. Es el caso clásico
    de "gano poco y aun así gano dinero": sirve para ver si el panel lo dice o
    si solo enseña el win rate y engaña.

Todo entra por la MISMA API que usa la pantalla (`/api/preflight/*`), y las
estadísticas se leen en un NAVEGADOR de verdad, porque se calculan en el
cliente. Nada se escribe a mano en la base.

    python3 tools/demo_preflight.py
"""
from __future__ import print_function

import datetime
import glob
import json
import os
import random
import sys
import tempfile
import threading
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(tempfile.mkdtemp(), 'demo_pf.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + DB
os.environ.setdefault('SECRET_KEY', 'demo-preflight')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                          # noqa: E402

CL = 'Zx9!wQ4mNp2r'
PUERTO = 5120
SEMILLA = 20260812

PROYECTOS = [
    {
        'nombre': 'ICT — NY AM',
        'conf': ['Kill zone NY AM', 'Barrida de liquidez', 'FVG H1',
                 'Order block M15', 'Estructura HTF a favor', 'Riesgo <= 1%'],
        'instrumentos': ['NQ', 'ES'],
        'n': 34,
        # P(ganar) = base + peso · nº marcadas  (+ extra si está la clave)
        'base': 0.34, 'peso': 0.055, 'clave': 'Barrida de liquidez', 'extra': 0.10,
        'r_gana': (1.6, 2.8), 'r_pierde': (1.0, 1.0),
    },
    {
        'nombre': 'Wyckoff — Acumulación',
        'conf': ['Fase C identificada', 'Spring con volumen', 'Test seco',
                 'LPS confirmado', 'SOS previo', 'Volumen decreciente'],
        'instrumentos': ['XAUUSD', 'EURUSD'],
        'n': 30,
        'base': 0.50, 'peso': 0.0, 'clave': None, 'extra': 0.0,
        'r_gana': (1.4, 2.4), 'r_pierde': (1.0, 1.0),
    },
    {
        'nombre': 'Chartismo — Rupturas',
        'conf': ['Triángulo válido', 'Ruptura con volumen', 'Retest',
                 'Objetivo medido >= 2R', 'Sin noticias de alto impacto'],
        'instrumentos': ['BTCUSD', 'ES'],
        'n': 28,
        'base': 0.38, 'peso': 0.0, 'clave': None, 'extra': 0.0,
        'r_gana': (3.0, 5.0), 'r_pierde': (1.0, 1.0),
    },
]

# Proyectos de relleno para la prueba de ESTRÉS: Premium permite 10 pizarras
# (PROJECT_LIMITS['premium']), así que la comparación tiene que aguantar 10
# columnas sin cortar texto ni tarjetas. Nombres largos a propósito.
RELLENO = [
    ('SMC — Londres continuación', ['CHoCH M5', 'OB refinado', 'Liquidez interna']),
    ('Elliott — Onda 3 en NASDAQ', ['Onda 2 respetada', 'Impulso confirmado', 'Fibo 1.618']),
    ('Armónicos — Gartley diario', ['Punto B 0.618', 'PRZ definida', 'Divergencia RSI']),
    ('Rangos asiáticos y su barrida', ['Rango limpio', 'Barrida del alto', 'Vuelta al 50%']),
    ('Noticias — NFP y CPI (alto impacto)', ['Sin posición previa', 'Segundo movimiento', 'Spread normal']),
    ('Reversión a la media en oro', ['Banda tocada', 'RSI extremo', 'Sin tendencia diaria']),
    ('Swing semanal — acciones USA', ['Cierre semanal a favor', 'Volumen creciente', 'Sector fuerte']),
]

RIESGO = 200.0          # dólares arriesgados por trade (fijo, para que el P&L
                        # se pueda comparar entre proyectos)


def arranca_servidor():
    with A.app.app_context():
        A.db.create_all()
        u = A.User.query.filter_by(username='demopf').first()
        if u is None:
            u = A.User(username='demopf', email='demopf@demo.invalid',
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
            urllib.request.urlopen('http://127.0.0.1:%d/health' % PUERTO, timeout=1)
            return
        except Exception:
            pass


def siembra(extra=0):
    """Crea los proyectos y registra sus trades por la API real.

    `extra` añade proyectos de relleno para la prueba de estrés con el tope de
    Premium (10 pizarras).
    """
    proyectos = list(PROYECTOS)
    for nombre, conf in RELLENO[:extra]:
        proyectos.append({'nombre': nombre, 'conf': conf, 'instrumentos': ['NQ', 'EURUSD'],
                          'n': 22, 'base': 0.45, 'peso': 0.02, 'clave': None, 'extra': 0.0,
                          'r_gana': (1.5, 3.0), 'r_pierde': (1.0, 1.0)})
    rnd = random.Random(SEMILLA)
    c = A.app.test_client()
    c.post('/login', data={'identifier': 'demopf', 'password': CL},
           follow_redirects=True)

    resumen = []
    dia = datetime.date(2026, 6, 1)
    for p in proyectos:
        cfg = {'confluences': [{'id': 'c%d' % (i + 1), 'label': l}
                               for i, l in enumerate(p['conf'])],
               'min_go': len(p['conf']) - 1,
               'min_caution': len(p['conf']) // 2 + 1}
        r = c.post('/api/preflight/checklists',
                   json={'name': p['nombre'], 'config': cfg})
        assert r.status_code == 200, (p['nombre'], r.status_code, r.get_json())
        cl = r.get_json()['checklist']

        ganados = perdidos = saltados = 0
        pnl_total = 0.0
        d = dia
        for i in range(p['n']):
            # avanza 1-3 días y se salta fines de semana (un trader no opera)
            d = d + datetime.timedelta(days=rnd.randint(1, 3))
            while d.weekday() >= 5:
                d = d + datetime.timedelta(days=1)

            # cuántas confluencias se cumplen ese día: de 2 a todas
            k = rnd.randint(2, len(p['conf']))
            marcadas = rnd.sample(p['conf'], k)
            verdict = ('go' if k >= cfg['min_go']
                       else 'caution' if k >= cfg['min_caution'] else 'no-go')

            # 🔑 la regla FIJA declarada arriba decide la probabilidad
            pg = p['base'] + p['peso'] * k
            if p['clave'] and p['clave'] in marcadas:
                pg += p['extra']
            pg = max(0.05, min(0.95, pg))

            # un trader disciplinado casi no toma los no-go: se registran, pero
            # la mayoría quedan como 'skipped' (no tomado)
            tomado = True
            if verdict == 'no-go':
                tomado = rnd.random() < 0.25
            elif verdict == 'caution':
                tomado = rnd.random() < 0.65

            gana = rnd.random() < pg
            rr = round(rnd.uniform(*p['r_gana']), 1)
            instrumento = rnd.choice(p['instrumentos'])
            direccion = 'long' if rnd.random() < 0.55 else 'short'
            entrada = round(rnd.uniform(100, 20000), 2)
            if tomado:
                if gana:
                    pnl = round(RIESGO * rr, 2)
                    ganados += 1
                else:
                    pnl = -round(RIESGO * rnd.uniform(0.85, 1.05), 2)
                    perdidos += 1
                pnl_total += pnl
                salida = round(entrada * (1 + (0.004 if gana else -0.002) *
                                          (1 if direccion == 'long' else -1)), 2)
                resultado = 'win' if gana else 'loss'
            else:
                saltados += 1
                pnl, salida, resultado = None, None, 'skipped'

            payload = {
                'checklist_id': cl['id'], 'checklist_name': p['nombre'],
                'checked': marcadas, 'total': len(p['conf']), 'verdict': verdict,
                'trade_date': d.isoformat(), 'instrument': instrumento,
                'direction': direccion, 'entry_price': entrada,
                'exit_price': salida, 'rr': rr,
                'position_size': rnd.choice([1, 2, 3]), 'pnl': pnl,
            }
            r = c.post('/api/preflight/checks', json=payload)
            assert r.status_code == 200, (r.status_code, r.get_json())
            chk = r.get_json()['check']
            # el resultado se marca como lo hace el usuario: editando la fila
            r = c.put('/api/preflight/checks/%d' % chk['id'],
                      json={'outcome': resultado})
            assert r.status_code == 200, (r.status_code, r.get_json())

        resumen.append({
            'proyecto': p['nombre'], 'registrados': p['n'],
            'ganados': ganados, 'perdidos': perdidos, 'no_tomados': saltados,
            'pnl': round(pnl_total, 2),
            'win_rate_real': (round(100.0 * ganados / (ganados + perdidos), 1)
                              if (ganados + perdidos) else None),
        })
    return resumen


def lee_pantalla():
    """Abre la app en un navegador y saca las estadísticas que VE el usuario."""
    from playwright.sync_api import sync_playwright
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    url = 'http://127.0.0.1:%d' % PUERTO
    salida = {}
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'],
                              **({'executable_path': exe} if exe else {}))
        pg = b.new_context(viewport={'width': 1500, 'height': 1000}).new_page()
        errores = []
        pg.on('pageerror', lambda e: errores.append(str(e)))
        pg.route('**/*', lambda r: r.continue_()
                 if '127.0.0.1' in r.request.url else r.abort())
        pg.goto(url + '/login', wait_until='domcontentloaded')
        pg.fill('input[name=identifier]', 'demopf')
        pg.fill('input[name=password]', CL)
        pg.click('button[type=submit]')
        pg.wait_for_timeout(800)
        pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                                 'url': url + '/'}])
        pg.goto(url + '/app', wait_until='domcontentloaded')
        pg.wait_for_timeout(2200)
        pg.evaluate("""() => { const e =
            document.querySelector('.tab[data-tab="preflight"]'); if (e) e.click(); }""")
        pg.wait_for_timeout(2500)

        # tira de tarjetas de arriba (todas las pizarras juntas)
        salida['tiras'] = pg.evaluate("""() =>
            [...document.querySelectorAll('#pf-stats .pf-stat')].map(e => ({
              valor: (e.querySelector('.pf-stat-val')||{}).textContent,
              clave: (e.querySelector('.pf-stat-key')||{}).textContent,
              sub: (e.querySelector('.pf-stat-sub')||{}).textContent || '' }))""")

        # pestaña Proyectos: una tabla por proyecto
        pg.evaluate("""() => { const b =
            document.querySelector('.pf-tab[data-pftab="projects"]'); if (b) b.click(); }""")
        pg.wait_for_timeout(1200)
        chips = pg.evaluate("""() => [...document.querySelectorAll('#pf-proj-chips .pf-proj-chip')]
            .map(b => b.textContent.trim())""")
        salida['proyectos'] = {}
        for i, nombre in enumerate(chips):
            pg.evaluate("""i => { const b = document.querySelectorAll('#pf-proj-chips .pf-proj-chip')[i];
                if (b) b.click(); }""", i)
            pg.wait_for_timeout(900)
            salida['proyectos'][nombre] = pg.evaluate("""() =>
                [...document.querySelectorAll('#pf-proj-stats tr')].map(tr =>
                  [...tr.children].map(td => td.textContent.trim()))""")
            if i == 0:
                pg.screenshot(path=os.path.join(RAIZ, 'out', 'tests', ('pf_proyecto_estres.png' if '--estres' in sys.argv else 'pf_proyecto.png')),
                              full_page=True)

        # pestaña Comparar: los 3 a la vez
        pg.evaluate("""() => { const b =
            document.querySelector('.pf-tab[data-pftab="compare"]'); if (b) b.click(); }""")
        pg.wait_for_timeout(900)
        pg.evaluate("""() => document.querySelectorAll('#pf-cmp-chips .pf-proj-chip')
            .forEach(b => b.click())""")
        pg.wait_for_timeout(1400)
        salida['comparacion'] = pg.evaluate("""() =>
            [...document.querySelectorAll('#pf-cmp-table tr')].map(tr =>
              [...tr.children].map(td => td.textContent.trim()))""")
        pg.screenshot(path=os.path.join(RAIZ, 'out', 'tests', ('pf_comparar_estres.png' if '--estres' in sys.argv else 'pf_comparar.png')),
                      full_page=True)
        # desplazada hasta el final: comprueba que la primera columna se queda
        # fija y que el ÚLTIMO proyecto se alcanza
        pg.evaluate("""() => { const c =
            document.querySelector('#pf-cmp-table .pf-stats-table');
            if (c) c.scrollLeft = c.scrollWidth; }""")
        pg.wait_for_timeout(500)
        salida['tras_scroll'] = pg.evaluate("""() => {
            const c = document.querySelector('#pf-cmp-table .pf-stats-table');
            const p = c.querySelector('tbody tr td:first-child');
            const r = p.getBoundingClientRect(), rc = c.getBoundingClientRect();
            const ult = c.querySelector('thead th:last-child');
            return {etiqueta_visible: r.left >= rc.left - 2 && r.right <= rc.right + 2,
                    texto_etiqueta: p.textContent.trim(),
                    ultimo_proyecto: ult.textContent.trim(),
                    ultimo_visible: ult.getBoundingClientRect().right <= rc.right + 2,
                    sombra: c.classList.contains('hay-mas')}; }""")
        pg.screenshot(path=os.path.join(RAIZ, 'out', 'tests',
                      ('pf_comparar_scroll.png' if '--estres' in sys.argv else 'pf_cmp_scroll.png')),
                      full_page=True)
        salida['desborde'] = pg.evaluate("""() => {
            const c = document.querySelector('#pf-cmp-table .pf-stats-table');
            const t = c && c.querySelector('table');
            const cont = document.querySelector('#pf-cmp-table');
            return c ? {ancho_visible: Math.round(c.clientWidth),
                        ancho_tabla: Math.round(t.scrollWidth),
                        se_puede_scrollear: getComputedStyle(c).overflowX,
                        sobra: Math.round(t.scrollWidth - c.clientWidth)} : null; }""")
        salida['errores_js'] = errores
        b.close()
    return salida


def main():
    extra = 0
    if '--estres' in sys.argv:
        extra = 7          # 3 + 7 = 10 = el tope de Premium
    arranca_servidor()
    real = siembra(extra)
    print('\n===== LO QUE DE VERDAD PASÓ (lo sabe el generador, no el panel) =====')
    for r in real:
        print('  %-24s %d registrados · %dW %dL %d no tomados · win %s%% · P&L %s'
              % (r['proyecto'], r['registrados'], r['ganados'], r['perdidos'],
                 r['no_tomados'], r['win_rate_real'], r['pnl']))

    v = lee_pantalla()
    print('\n===== TIRA DE ARRIBA (todas las pizarras juntas) =====')
    for t in v['tiras']:
        print('  %-22s %s %s' % (t['clave'], t['valor'], t['sub']))

    for nombre, filas in v['proyectos'].items():
        print('\n===== PROYECTO: %s =====' % nombre)
        for f in filas:
            if len(f) >= 2:
                print('  %-38s %s' % (f[0], f[1]))

    print('\n===== COMPARACIÓN ENTRE PROYECTOS =====')
    for f in v['comparacion']:
        print('  ' + ' | '.join(x[:34] for x in f))
    print('\nerrores de JavaScript:', v['errores_js'][:4])
    ruta = os.path.join(RAIZ, 'out', 'tests', 'demo_preflight.json')
    with open(ruta, 'w') as fh:
        json.dump({'real': real, 'pantalla': v}, fh, indent=1, ensure_ascii=False)
    print('crudo en %s' % ruta)


if __name__ == '__main__':
    main()
