# -*- coding: utf-8 -*-
"""Fotos de la pantalla REAL del analizador, para el reel 2.

Levanta el sitio en local con un usuario premium sembrado, rellena el
formulario del analizador **como lo haría una persona** —sube el gráfico, elige
la metodología, escribe sus notas— y fotografía cada paso.

🔑 EL GRÁFICO QUE SE SUBE ES EL DEL BANCO (`I5_sl_cazado_perdido`) y las notas
   son las REALES de ese caso: el trader culpa a la manipulación. Así el reel
   entero —animación, formulario y veredicto— habla del MISMO trade.

⚠️ NO se pulsa "Analizar". Eso llamaría a la API de pago, y además el veredicto
   del banco ya existe y es el de este mismo gráfico. El reel enseña la
   herramienta funcionando y luego cita la respuesta; no se falsifica una
   pantalla de resultado.

⚠️ `/app` BORRA el cookie `scalpel_splash_ts` al servirse (es de un solo uso):
   hay que volver a ponerlo antes de CADA visita o la siguiente rebota a
   /welcome. Ya nos costó tiempo en los tests de cursores.

    python3 tools/capta_analizador.py
"""
from __future__ import print_function

import glob
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'out', 'reels', '_az')
GRAFICO = os.path.join(RAIZ, 'out', 'banco_analizador',
                       'I5_sl_cazado_perdido.png')
PUERTO = 5137
USUARIO = 'reeldemo'
CL = 'Zx9!wQ4mNp2r'
VW, VH, DPR = 1500, 1000, 2

NOTAS = ("The setup was textbook: sweep of the equal lows, bullish "
         "displacement with an FVG, and I entered on the retracement. I put "
         "the stop tight just under my entry candle to improve the R:R. Price "
         "went down exactly to take my stop and then ran straight to my target "
         "without me. Pure manipulation against me — the trade was well built.")


def arranca(tmp):
    os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tmp, 'az.db')
    os.environ.setdefault('SECRET_KEY', 'reel-analizador')
    sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
    import app as A
    with A.app.app_context():
        A.db.create_all()
        u = A.User.query.filter_by(username=USUARIO).first()
        if u is None:
            u = A.User(username=USUARIO, email='az@demo.invalid',
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
            return
        except Exception:
            pass
    sys.exit('el servidor no arrancó')


def main():
    from playwright.sync_api import sync_playwright
    if not os.path.exists(GRAFICO):
        sys.exit('falta %s — corre antes tools/banco_analizador.py --en' % GRAFICO)
    shutil.rmtree(SALIDA, ignore_errors=True)
    os.makedirs(SALIDA)
    arranca(tempfile.mkdtemp())
    URL = 'http://127.0.0.1:%d' % PUERTO
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]

    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'],
                              **({'executable_path': exe} if exe else {}))
        ctx = b.new_context(viewport={'width': VW, 'height': VH},
                            device_scale_factor=DPR)
        pg = ctx.new_page()
        errores = []
        pg.on('pageerror', lambda e: errores.append(str(e)))

        def splash():
            pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                                     'url': URL}])

        pg.goto(URL + '/login', wait_until='domcontentloaded')
        pg.fill('#identifier', USUARIO)
        pg.fill('#password', CL)
        pg.click('button[type=submit]')
        pg.wait_for_timeout(1500)
        splash()
        pg.goto(URL + '/app', wait_until='domcontentloaded')
        pg.wait_for_timeout(2500)

        # ⚠️ tema OSCURO: el reel entero es grafito y una captura en claro
        #    canta como pegada de otro sitio.
        pg.evaluate("""() => {
            if (document.body.classList.contains('light')) {
              const b = document.querySelector('#theme-toggle,.theme-toggle,'
                        + '[data-act=theme],[onclick*=theme]');
              if (b) b.click(); else document.body.classList.remove('light');
            }
            try { localStorage.setItem('scalpel_theme','dark'); } catch(e){}
        }""")
        pg.wait_for_timeout(900)

        # ── el setup se rellena ENTERO ────────────────────────────────────
        # 🔴 Sin esto el panel lateral dice "CHART Missing" y "0/5": el reel
        #    estaría enseñando un formulario a medias, que es justo lo que un
        #    cliente leería como "no funciona".
        pg.evaluate("""opciones => {
            const eligeGrupo = (grupo, re) => {
              const g = document.querySelector(
                  '.pill-group[data-group=' + grupo + ']');
              if (!g) return;
              const ps = [...g.querySelectorAll('.pill')];
              const b = ps.find(e => re.test(e.textContent.trim())) || ps[0];
              if (b) b.click();
            };
            for (const [g, r] of opciones) eligeGrupo(g, new RegExp(r, 'i'));
        }""", [['instrument', 'NQ|Nasdaq|Index|Futures'],
                ['direction', 'Long'],
                ['session', 'New York|NY'],
                ['result', 'Loss'],
                ['htf_bias', 'Bull'],
                ['aligned', 'Yes']])
        pg.wait_for_timeout(1200)

        def foto(nom, sel=None, margen=0):
            if sel:
                el = pg.query_selector(sel)
                if not el:
                    print('  ⚠️ no existe %s' % sel)
                    return False
                el.screenshot(path=os.path.join(SALIDA, nom + '.png'))
            else:
                pg.screenshot(path=os.path.join(SALIDA, nom + '.png'))
            print('  ·', nom)
            return True

        # ── 0 · el selector de INSTRUMENTO (paso 1 del reel) ──
        pg.evaluate("""() => {
            const g = document.querySelector('.pill-group[data-group=instrument]');
            if (g) g.scrollIntoView({block:'center'});
        }""")
        pg.wait_for_timeout(700)
        foto('instrumento', '.pill-group[data-group="instrument"]')
        foto('sesion', '.pill-group[data-group="session"]')

        # ── 1 · el formulario, con sus metodologías ──
        pg.evaluate("""() => {
            const g = document.querySelector('.pill-group[data-group=approach]');
            if (g) g.scrollIntoView({block:'center'});
        }""")
        pg.wait_for_timeout(700)
        foto('metodologias', '.pill-group[data-group="approach"]')

        # ── 2 · se elige ICT, como en el caso del banco ──
        pg.evaluate("""() => {
            const g = document.querySelector('.pill-group[data-group=approach]');
            const b = [...g.querySelectorAll('.pill')].find(
                e => /ICT/i.test(e.textContent));
            if (b) b.click();
        }""")
        pg.wait_for_timeout(900)
        foto('metodologias_ict', '.pill-group[data-group="approach"]')

        # un par de confluencias, las del propio caso
        pg.evaluate("""() => {
            const g = document.querySelector('.pill-group[data-group=confluences]');
            if (!g) return;
            const ps = [...g.querySelectorAll('.pill')];
            for (const r of [/sweep|liquidity|EQL/i, /FVG|gap/i]) {
              const b = ps.find(e => r.test(e.textContent));
              if (b) b.click();
            }
        }""")
        pg.wait_for_timeout(800)


        # ── 3 · se sube el gráfico de verdad ──
        inp = pg.query_selector('input[type=file]')
        if inp:
            inp.set_input_files(GRAFICO)
            pg.wait_for_timeout(1800)
        foto('subida', '#preview-wrap') or foto('subida')

        # ── 4 · las notas del trader, tecleadas ──
        pg.fill('#notes', NOTAS)
        pg.wait_for_timeout(500)
        foto('notas', '#notes')

        # ── 5 · el formulario entero y el botón ──
        pg.evaluate("() => document.getElementById('analyze-btn')"
                    ".scrollIntoView({block:'center'})")
        pg.wait_for_timeout(600)
        foto('pantalla')
        foto('boton', '#analyze-btn')
        foto('columna', '#analyze-form') or foto('columna', 'form')
        b.close()

    if errores:
        print('🔴 errores JS:', errores[:3])
    print('fotos en %s' % os.path.relpath(SALIDA, RAIZ))


if __name__ == '__main__':
    main()
