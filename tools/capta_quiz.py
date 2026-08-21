# -*- coding: utf-8 -*-
"""Fotos de la pantalla REAL del quiz, para el reel 3.

Recorre el quiz como lo haría una persona —elige metodología, tema y nivel,
contesta— y fotografía cada pantalla: la rejilla de metodologías, la de temas,
las tarjetas de nivel, una pregunta con su reloj, y el veredicto con su
explicación.

🔑 NO se inventa ni una pantalla. Todo lo que sale en el reel es el quiz del
   sitio corriendo en local con un usuario premium sembrado.

⚠️ El quiz ABRE EN LA BIENVENIDA, no en el home: hay que pulsar un intento
   antes de que exista `#quiz-home`. Es la misma trampa que costó tiempo al
   cablear los (?) de ayuda.
⚠️ `/app` BORRA el cookie `scalpel_splash_ts` al servirse (es de un solo uso):
   hay que reponerlo antes de CADA visita o la siguiente rebota a /welcome.

    python3 tools/capta_quiz.py
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
SALIDA = os.path.join(RAIZ, 'out', 'reels', '_qz')
PUERTO = 5141
USUARIO = 'reelquiz'
CL = 'Zx9!wQ4mNp2r'
VW, VH, DPR = 1500, 1100, 2


def arranca(tmp):
    os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tmp, 'qz.db')
    os.environ.setdefault('SECRET_KEY', 'reel-quiz')
    sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
    import app as A
    with A.app.app_context():
        A.db.create_all()
        u = A.User.query.filter_by(username=USUARIO).first()
        if u is None:
            u = A.User(username=USUARIO, email='qz@demo.invalid',
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
    shutil.rmtree(SALIDA, ignore_errors=True)
    os.makedirs(SALIDA)
    arranca(tempfile.mkdtemp())
    URL = 'http://127.0.0.1:%d' % PUERTO
    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]
    leido = {}

    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'],
                              **({'executable_path': exe} if exe else {}))
        ctx = b.new_context(viewport={'width': VW, 'height': VH},
                            device_scale_factor=DPR)
        pg = ctx.new_page()
        errores = []
        pg.on('pageerror', lambda e: errores.append(str(e)))

        pg.goto(URL + '/login', wait_until='domcontentloaded')
        pg.fill('#identifier', USUARIO)
        pg.fill('#password', CL)
        pg.click('button[type=submit]')
        pg.wait_for_timeout(1500)
        pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                                 'url': URL}])
        pg.goto(URL + '/app', wait_until='domcontentloaded')
        pg.wait_for_timeout(2600)

        pg.evaluate("""() => {
            if (document.body.classList.contains('light'))
                document.body.classList.remove('light');
            try { localStorage.setItem('scalpel_theme','dark'); } catch(e){}
            const t = document.querySelector('.tab[data-tab="quiz"]');
            if (t) t.click();
            else if (window.switchTab) window.switchTab('quiz');
        }""")
        pg.wait_for_timeout(1800)

        def foto(nom, sel=None):
            if sel:
                el = pg.query_selector(sel)
                if not el:
                    print('  ⚠️ no existe %s' % sel)
                    return False
                caja = el.bounding_box()
                if not caja or caja['width'] < 4 or caja['height'] < 4:
                    # ⚠️ diagnóstico: no basta con decir "no visible", hay que
                    #    saber QUIÉN de la cadena de padres lo esconde
                    info = pg.evaluate("""sel => {
                        let e = document.querySelector(sel), out = [];
                        while (e && e !== document.body) {
                          const c = getComputedStyle(e);
                          out.push(e.id || e.className || e.tagName);
                          if (c.display === 'none' || c.visibility === 'hidden')
                            return 'oculto por ' + (e.id || e.className) +
                                   ' (' + c.display + '/' + c.visibility + ')';
                          e = e.parentElement;
                        }
                        return 'cadena: ' + out.slice(0,6).join(' < ');
                    }""", sel)
                    print('  ⚠️ sin caja %s → %s' % (sel, info))
                    return False
                el.screenshot(path=os.path.join(SALIDA, nom + '.png'))
            else:
                pg.screenshot(path=os.path.join(SALIDA, nom + '.png'))
            print('  ·', nom)
            return True

        # ⚠️ el quiz abre en la BIENVENIDA: hay que entrar antes de que exista
        #    #quiz-home
        pg.evaluate("""() => {
            const w = document.getElementById('quiz-welcome');
            if (!w || w.style.display === 'none') return;
            const b = w.querySelector('[data-intent="verify"]')
                   || w.querySelector('.quiz-welcome-opt');
            if (b) b.click();
        }""")
        pg.wait_for_timeout(1500)

        # ── 1 · las metodologías ──
        # ⚠️ La bienvenida puede saltar DIRECTO a los temas según el intent que
        #    se pulse, y entonces #quiz-home queda oculto. Se retrocede hasta
        #    el home antes de fotografiar la rejilla.
        for _ in range(4):
            en_home = pg.evaluate("""() => {
                const h = document.getElementById('quiz-home');
                return !!h && getComputedStyle(h).display !== 'none';
            }""")
            if en_home:
                break
            pg.evaluate("""() => {
                const b = [...document.querySelectorAll(
                    '#quiz-topics-back,#quiz-detail-back,#quiz-synapse-back')]
                    .find(e => getComputedStyle(e).display !== 'none' &&
                               e.offsetParent !== null);
                if (b) b.click();
            }""")
            pg.wait_for_timeout(1100)
        foto('metodologias', '#quiz-method-grid')

        # ── 2 · los temas de una de ellas ──
        pg.evaluate("""() => {
            const g = document.getElementById('quiz-method-grid');
            const c = g && g.querySelector('.quiz-method-card,button,[role=button]');
            if (c) c.click();
        }""")
        pg.wait_for_timeout(1400)
        foto('temas', '#quiz-topic-grid')
        leido['titulo_temas'] = pg.eval_on_selector(
            '#quiz-topics-title', 'e => e.textContent') if pg.query_selector(
            '#quiz-topics-title') else ''

        # ── 3 · los niveles de un tema ──
        pg.evaluate("""() => {
            const g = document.getElementById('quiz-topic-grid');
            const c = g && g.querySelector('.quiz-topic-card,button,[role=button]');
            if (c) c.click();
        }""")
        pg.wait_for_timeout(1400)
        foto('niveles', '#quiz-level-cards')
        leido['titulo_detalle'] = pg.eval_on_selector(
            '#quiz-detail-title', 'e => e.textContent') if pg.query_selector(
            '#quiz-detail-title') else ''

        # ── 4 · una pregunta, con su reloj ──
        pg.evaluate("""() => {
            const g = document.getElementById('quiz-level-cards');
            const cs = g ? [...g.querySelectorAll('.quiz-level-card,button')] : [];
            const c = cs[cs.length - 1] || cs[0];   // el nivel más duro
            if (c) c.click();
        }""")
        pg.wait_for_timeout(2200)
        foto('pregunta', '#quiz-question')
        foto('enunciado', '#quiz-q-text')
        foto('opciones', '#quiz-options')
        foto('reloj', '#quiz-timer')
        leido['pregunta'] = pg.eval_on_selector('#quiz-q-text',
                                                'e => e.textContent')
        leido['nivel'] = pg.eval_on_selector('#quiz-level-pill',
                                             'e => e.textContent')
        leido['tema'] = pg.eval_on_selector('#quiz-topic-pill',
                                            'e => e.textContent')

        # 🔑 el TEXTO de las opciones, para poder componerlas en el reel: la
        #    captura del bloque mide 1280 px y a lo ancho del lienzo no se lee
        leido['opciones'] = pg.evaluate("""() => [...document.querySelectorAll(
            '#quiz-options .quiz-opt, #quiz-options .quiz-option, #quiz-options button')]
            .map(e => ({txt: e.textContent.trim(), ok: e.dataset.ok === 'true'}))""")

        # ── 5 · el veredicto y su explicación ──
        pg.evaluate("""() => {
            const o = document.getElementById('quiz-options');
            const b = o && o.querySelector('.quiz-option,button');
            if (b) b.click();
        }""")
        pg.wait_for_timeout(1600)
        foto('veredicto', '#quiz-feedback')
        foto('pregunta_resuelta', '#quiz-question')
        leido['explicacion'] = (pg.eval_on_selector(
            '#quiz-feedback-exp', 'e => e.textContent')
            if pg.query_selector('#quiz-feedback-exp') else '')
        # cuál era la correcta, leída de la clase que pinta la app
        leido['correcta'] = pg.evaluate("""() => {
            const o = [...document.querySelectorAll(
                '#quiz-options .quiz-opt, #quiz-options .quiz-option')];
            const i = o.findIndex(e => e.dataset.ok === 'true'
                                    || /\\bcorrect\\b/.test(e.className));
            return {indice: i, texto: i >= 0 ? o[i].textContent.trim() : ''};
        }""")

        # ── 6 · una pregunta HARDCORE, que es la que lleva GRÁFICO ──
        for _ in range(6):
            hecho = pg.evaluate("""() => {
                const h = document.getElementById('quiz-home');
                return !!h && getComputedStyle(h).display !== 'none';
            }""")
            if hecho:
                break
            pg.evaluate("""() => {
                const b = [...document.querySelectorAll('button')].find(
                    e => /quiz-(retry|new)-btn|topics-back|detail-back/.test(e.id)
                         && e.offsetParent !== null);
                if (b) b.click();
            }""")
            pg.wait_for_timeout(1000)
        pg.evaluate("""() => {
            const g = document.getElementById('quiz-method-grid');
            const c = g && g.querySelector('.quiz-method-card,button,[role=button]');
            if (c) c.click();
        }""")
        pg.wait_for_timeout(1200)
        pg.evaluate("""() => {
            const g = document.getElementById('quiz-topic-grid');
            const c = g && g.querySelector('.quiz-topic-card,button,[role=button]');
            if (c) c.click();
        }""")
        pg.wait_for_timeout(1200)
        pg.evaluate("""() => {
            const g = document.getElementById('quiz-level-cards');
            const hc = document.querySelector('.quiz-hc-card:not(.locked)');
            if (hc) { hc.click(); return; }
            const cs = g ? [...g.querySelectorAll('.quiz-level-card')] : [];
            if (cs.length) cs[cs.length - 1].click();
        }""")
        pg.wait_for_timeout(2600)
        foto('hardcore', '#quiz-question')
        # ⚠️ NO todas las hardcore llevan gráfico: se avanzan preguntas hasta
        #    dar con una que sí, en vez de dar por hecho que la primera lo tiene.
        con_grafico = False
        for intento in range(8):
            hay = pg.evaluate("""() => {
                const v = [...document.querySelectorAll(
                    '.quiz-chart-svg-wrap, .quiz-chart-wrap')]
                  .filter(e => getComputedStyle(e).display !== 'none' &&
                               e.getBoundingClientRect().height > 40);
                if (v.length) v[0].setAttribute('data-reel-chart', '1');
                return v.length > 0;
            }""")
            if hay:
                con_grafico = True
                foto('hardcore_grafico', '#quiz-question')
                foto('hardcore_solo_grafico', '[data-reel-chart]')
                leido['hardcore_q'] = pg.eval_on_selector('#quiz-q-text',
                                                          'e => e.textContent')
                break
            # contesta y pasa a la siguiente
            pg.evaluate("""() => {
                const o = document.querySelector(
                    '#quiz-options .quiz-opt, #quiz-options .quiz-option');
                if (o) o.click();
            }""")
            pg.wait_for_timeout(900)
            pg.evaluate("""() => {
                const n = document.getElementById('quiz-next-btn');
                if (n && n.offsetParent !== null) n.click();
            }""")
            pg.wait_for_timeout(1300)
        if not con_grafico:
            print('  ⚠️ ninguna de las 8 primeras hardcore traía gráfico')
        leido['hardcore_q'] = (pg.eval_on_selector('#quiz-q-text',
                                                   'e => e.textContent')
                               if pg.query_selector('#quiz-q-text') else '')
        leido['hardcore_nivel'] = (pg.eval_on_selector('#quiz-level-pill',
                                                       'e => e.textContent')
                                   if pg.query_selector('#quiz-level-pill') else '')
        b.close()

    if errores:
        print('🔴 errores JS:', errores[:3])
    import json
    import io as _io
    with _io.open(os.path.join(SALIDA, 'leido.json'), 'w',
                  encoding='utf-8') as f:
        f.write(json.dumps(leido, ensure_ascii=False, indent=1))
    for k, v in leido.items():
        print('  %-16s %s' % (k, (v or '')[:70]))
    print('fotos en %s' % os.path.relpath(SALIDA, RAIZ))


if __name__ == '__main__':
    main()
