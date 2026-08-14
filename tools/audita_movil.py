# -*- coding: utf-8 -*-
"""Barrido de las vistas MÓVIL y TABLET del sitio entero.

    venv/bin/python3 tools/audita_movil.py            # todo
    venv/bin/python3 tools/audita_movil.py --caps     # + capturas PNG

Levanta la app con SQLite en un puerto libre, crea una cuenta premium, entra,
y recorre las páginas públicas y las pestañas de /app en 5 tamaños reales
(iPhone SE, iPhone 14 Pro, iPad mini vertical, iPad Pro vertical y iPad
apaisado). Por cada combinación mide, en el navegador de verdad:

  · DESBORDE HORIZONTAL — `scrollWidth > innerWidth`. Es EL fallo de móvil:
    la página se va de lado y el usuario ve media pantalla en blanco. Nombra
    además los elementos concretos que se salen (los 5 peores);
  · TEXTO ILEGIBLE — nodos con texto real por debajo de 11px;
  · BOTONES INTOCABLES — clicables por debajo de 32×32 px (Apple pide 44);
  · SOLAPES — cajas fijas/pegajosas que tapan contenido.

⚠️ Trampas del entorno, aprendidas a golpes:
  · `/app` exige el cookie `scalpel_splash_ts` y lo BORRA al servirse → hay
    que reponerlo antes de CADA visita;
  · Google Fonts y los CDN son inalcanzables aquí: se abortan por ruta, si no
    cada carga tarda ~30 s esperando un `load` que nunca llega;
  · `wait_until='domcontentloaded'`, nunca el `load` completo.

No toca la base de producción: usa una SQLite temporal que se borra al salir.
"""
from __future__ import print_function

import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp(prefix='auditamovil-')
CAPS = os.path.join(RAIZ, 'out', 'audita_movil')

PANTALLAS = [
    ('iPhone SE',        375,  667, 2),
    ('iPhone 14 Pro',    393,  852, 3),
    ('iPad mini vert',   768, 1024, 2),
    ('iPad Pro vert',   1024, 1366, 2),
    ('iPad apaisado',   1180,  820, 2),
]

PUBLICAS = [('/', 'landing'), ('/pricing', 'precios'), ('/login', 'login'),
            ('/register', 'registro'), ('/guide', 'guia'),
            ('/socials', 'socials'), ('/terms', 'terminos'),
            ('/cosmetics', 'cosmeticos'), ('/contact', 'contacto')]

# Pestañas de /app: (data-tab, etiqueta). Se cambian por clic real.
TABS = [('analyze', 'Analizador'), ('quiz', 'Quiz'), ('forum', 'Foro'),
        ('scalper', 'Chalkboard'), ('preflight', 'Pre-Flight'),
        ('synapse', 'Synapse'), ('improve', 'Timing')]

MEDIDA_JS = r"""
() => {
  const W = window.innerWidth;
  const de = document.documentElement;
  const desborde = Math.max(de.scrollWidth, document.body.scrollWidth) - W;
  const culpables = [];
  if (desborde > 1) {
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none') continue;
      const exceso = Math.round(r.right - W);
      if (exceso > 2) {
        // solo el elemento MÁS INTERNO que se sale: si no, sale toda la
        // cadena de padres y el informe se vuelve ilegible
        let hijoCulpable = false;
        for (const h of el.children) {
          const rh = h.getBoundingClientRect();
          if (rh.width && rh.right - W > 2) { hijoCulpable = true; break; }
        }
        if (!hijoCulpable) culpables.push({
          sel: el.tagName.toLowerCase() +
               (el.id ? '#' + el.id : '') +
               (el.className && typeof el.className === 'string'
                 ? '.' + el.className.trim().split(/\s+/).slice(0,2).join('.')
                 : ''),
          exceso: exceso, ancho: Math.round(r.width),
          txt: (el.textContent || '').trim().slice(0, 40)
        });
      }
    }
    culpables.sort((a, b) => b.exceso - a.exceso);
  }
  // texto diminuto (con texto propio real, no heredado)
  const chico = [];
  for (const el of document.querySelectorAll('body *')) {
    const propio = [...el.childNodes]
      .filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join('');
    if (propio.length < 3) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden') continue;
    const px = parseFloat(cs.fontSize);
    if (px && px < 11) chico.push({px: Math.round(px * 10) / 10,
                                   txt: propio.slice(0, 32)});
  }
  // clicables pequeños
  const mini = [];
  for (const el of document.querySelectorAll(
       'button, a, input[type=submit], [role=button], .pill, .tab-btn')) {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    if (getComputedStyle(el).visibility === 'hidden') continue;
    if (r.width < 32 || r.height < 32) mini.push({
      w: Math.round(r.width), h: Math.round(r.height),
      txt: (el.textContent || el.value || '').trim().slice(0, 24)
    });
  }
  return {W, desborde, culpables: culpables.slice(0, 5),
          chico: chico.slice(0, 6), nChico: chico.length,
          mini: mini.slice(0, 5), nMini: mini.length};
}
"""


def puerto_libre():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main():
    caps = '--caps' in sys.argv
    solo = [a for a in sys.argv[1:] if not a.startswith('--')]
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit('falta playwright: venv/bin/pip install playwright')

    puerto = puerto_libre()
    env = dict(os.environ)
    env['DATABASE_URL'] = 'sqlite:///' + os.path.join(TMP, 'a.db')
    env.setdefault('SECRET_KEY', 'auditamovil')
    env['PORT'] = str(puerto)
    env.pop('PUBLIC_HTTPS', None)      # sin HTTPS no hay cookie Secure
    env.pop('PREVIEW_USERS', None)     # sin candado
    env.pop('SITE_URL', None)

    # cuenta premium sembrada antes de levantar el server
    siembra = (
        'import sys; sys.path.insert(0, "scalpel"); import app as A\n'
        'with A.app.app_context():\n'
        '    A.db.create_all()\n'
        '    u = A.User.query.filter_by(username="movil").first()\n'
        '    if not u:\n'
        '        u = A.User(username="movil", email="movil@t.invalid",\n'
        '                   email_verified=True)\n'
        '        u.set_password("Zx9!wQ4mNp2r"); u.email_canonical = u.email\n'
        '        A.db.session.add(u)\n'
        '    u.plan = "premium"\n'
        '    from datetime import datetime, timedelta, timezone\n'
        '    u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=30)\n'
        '    A.db.session.commit()\n'
        'print("SEMBRADO")\n')
    r = subprocess.run([sys.executable, '-c', siembra], capture_output=True,
                       text=True, cwd=RAIZ, env=env)
    if 'SEMBRADO' not in r.stdout:
        print(r.stderr[-800:])
        sys.exit('no se pudo sembrar la cuenta de prueba')

    srv = subprocess.Popen(
        [sys.executable, '-c',
         'import sys; sys.path.insert(0, "scalpel"); import app as A; '
         'A.app.run(host="127.0.0.1", port=%d, threaded=True)' % puerto],
        cwd=RAIZ, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = 'http://127.0.0.1:%d' % puerto
    for _ in range(60):
        try:
            socket.create_connection(('127.0.0.1', puerto), 0.3).close()
            break
        except OSError:
            time.sleep(0.4)
    else:
        srv.kill()
        sys.exit('el servidor de prueba no levantó')

    if caps:
        os.makedirs(CAPS, exist_ok=True)
    problemas = []
    resumen = []

    with sync_playwright() as pw:
        # ⚠️ El Chromium instalado aquí (build 1194) no coincide con el que
        # este Playwright espera (1234) y `launch()` a secas manda a correr
        # `playwright install`, que está prohibido en este entorno. Se apunta
        # al binario que SÍ existe.
        chrome = '/opt/pw-browsers/chromium'
        nav = pw.chromium.launch(
            executable_path=chrome if os.path.exists(chrome) else None)
        for nombre, w, h, dpr in PANTALLAS:
            ctx = nav.new_context(viewport={'width': w, 'height': h},
                                  device_scale_factor=1, is_mobile=w < 820,
                                  has_touch=True)
            # cortar TODO lo externo: sin esto cada carga espera 30 s
            ctx.route(re.compile(r'^https?://(?!127\.0\.0\.1)'),
                      lambda ruta: ruta.abort())
            pg = ctx.new_page()
            errores_js = []
            pg.on('pageerror', lambda e: errores_js.append(str(e)[:90]))

            # login una vez por contexto
            pg.goto(base + '/login', wait_until='domcontentloaded')
            pg.fill('input[name=identifier]', 'movil')
            pg.fill('input[name=password]', 'Zx9!wQ4mNp2r')
            pg.click('button[type=submit]')
            pg.wait_for_timeout(700)

            print('\n══ %s (%d×%d) ══' % (nombre, w, h))
            objetivos = [(u, n) for u, n in PUBLICAS
                         if not solo or any(s in n for s in solo)]
            for url, etiqueta in objetivos:
                try:
                    pg.goto(base + url, wait_until='domcontentloaded',
                            timeout=15000)
                    pg.wait_for_timeout(450)
                    m = pg.evaluate(MEDIDA_JS)
                except Exception as e:
                    print('  ⚠️  %-12s no cargó (%s)' % (etiqueta, str(e)[:40]))
                    continue
                reporta(nombre, etiqueta, m, problemas, resumen)
                if caps and m['desborde'] > 1:
                    pg.screenshot(path=os.path.join(
                        CAPS, '%s_%s.png' % (etiqueta, nombre.replace(' ', ''))))

            # /app y sus pestañas
            if not solo or any(s in 'app' for s in solo):
                ctx.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                                  'url': base}])
                pg.goto(base + '/app', wait_until='domcontentloaded',
                        timeout=20000)
                pg.wait_for_timeout(900)
                m = pg.evaluate(MEDIDA_JS)
                reporta(nombre, 'app:inicio', m, problemas, resumen)
                for tab, eti in TABS:
                    try:
                        b = pg.query_selector('[data-tab="%s"]' % tab)
                        if not b:
                            continue
                        b.click()
                        pg.wait_for_timeout(700)
                        m = pg.evaluate(MEDIDA_JS)
                    except Exception:
                        continue
                    reporta(nombre, 'app:' + eti, m, problemas, resumen)
                    if caps and m['desborde'] > 1:
                        pg.screenshot(path=os.path.join(
                            CAPS, 'app-%s_%s.png'
                            % (eti, nombre.replace(' ', ''))))
            if errores_js:
                print('  ⚠️  errores JS: %s' % ' | '.join(errores_js[:2]))
            ctx.close()
        nav.close()

    srv.terminate()
    shutil.rmtree(TMP, ignore_errors=True)

    print('\n' + '=' * 66)
    desb = [p for p in problemas if p[0] == 'desborde']
    print('RESULTADO: %d vistas medidas · %d con DESBORDE horizontal'
          % (len(resumen), len(desb)))
    if desb:
        print('\nLo que se sale de la pantalla (lo peor primero):')
        for _, pantalla, pagina, px, quien in sorted(desb, key=lambda p: -p[3])[:14]:
            print('  %+5d px  %-16s %-14s %s' % (px, pagina, pantalla, quien))
    if caps:
        print('\nCapturas de las vistas rotas: %s'
              % os.path.relpath(CAPS, RAIZ))
    return 1 if desb else 0


def reporta(pantalla, pagina, m, problemas, resumen):
    resumen.append((pantalla, pagina))
    marcas = []
    if m['desborde'] > 1:
        quien = m['culpables'][0]['sel'] if m['culpables'] else '(no localizado)'
        problemas.append(('desborde', pantalla, pagina, m['desborde'], quien))
        marcas.append('DESBORDE +%dpx → %s' % (m['desborde'], quien))
    if m['nChico']:
        marcas.append('%d textos <11px' % m['nChico'])
    if m['nMini']:
        marcas.append('%d clicables <32px' % m['nMini'])
    estado = '❌' if m['desborde'] > 1 else ('· ' if marcas else '✅')
    print('  %s %-16s %s' % (estado, pagina, '; '.join(marcas)))


if __name__ == '__main__':
    sys.exit(main())
