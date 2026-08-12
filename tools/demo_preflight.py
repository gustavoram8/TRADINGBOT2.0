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

sys.path.insert(0, os.path.join(RAIZ, 'tools'))
import pf_demo_datos as D                                # noqa: E402

CL = 'Zx9!wQ4mNp2r'
PUERTO = 5120
SEMILLA = 20260812

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
    """Crea los proyectos y registra sus trades POR LA API real.

    🔑 Los datos salen de `pf_demo_datos.genera()`, el mismo generador que usa
    `demo_a_mi_cuenta.py`. Así lo que se audita aquí y lo que se ve en una
    cuenta real son exactamente los mismos números.
    """
    c = A.app.test_client()
    c.post('/login', data={'identifier': 'demopf', 'password': CL},
           follow_redirects=True)
    resumen = []
    for p, cfg, trades, res in D.genera(extra):
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
            # el resultado se marca como lo hace el usuario: editando la fila
            r = c.put('/api/preflight/checks/%d' % chk['id'],
                      json={'outcome': resultado})
            assert r.status_code == 200, (r.status_code, r.get_json())
        resumen.append(res)
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
