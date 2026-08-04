# -*- coding: utf-8 -*-
"""Punto 10: qué texto se pierde con un camo puesto. Medido, no mirado.

    python3 tools/audita_legibilidad.py

QUÉ MIDE Y POR QUÉ ASÍ
----------------------
El texto que va DENTRO de un panel está a salvo: el panel tiene su propio
fondo. El que se pierde es el que cae directamente sobre el dibujo del camo —
el pie de página, los títulos sueltos, las notas pequeñas. Y ahí no vale
calcular el contraste con las variables CSS, porque el fondo real es una
ilustración: en la misma frase puede haber montaña oscura detrás de una mitad
y cielo claro detrás de la otra.

Por eso se recorta CADA texto del screenshot y se mide contra los píxeles que
de verdad quedaron detrás. Dentro del recorte, el color más repetido es el
fondo y el más alejado de él es la tinta; el contraste se calcula entre esos
dos con la fórmula de la WCAG (umbral 4.5 para texto normal).

TRAMPAS YA PAGADAS (están en CLAUDE.md, no volver a caer)
---------------------------------------------------------
· `pg.goto()` espera al `load` completo y la página pide un script a un CDN
  bloqueado en el contenedor → 30 s por carga. Con `domcontentloaded` + abortar
  todo lo que no sea 127.0.0.1, baja a menos de un segundo.
· Cambiar la clase del camo en el DOM NO sirve: hay que RECARGAR con el camo
  guardado en la cuenta, o se mide un color contra el fondo de otro.
· `pg.screenshot(clip=…)` usa coordenadas de PÁGINA y `getBoundingClientRect()`
  las da de VIEWPORT: con la página desplazada se mide otra zona. Se usa
  `locator.screenshot()`, que no tiene ese problema.
"""
import io
import json
import os
import sys
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

BASE = 'http://127.0.0.1:5001'
USUARIO, CLAVE = 'audita10', 'Zx8!kQ2mLp7w'
UMBRAL = 4.5              # WCAG AA para texto normal
SALIDA = os.path.join(RAIZ, 'out', 'legibilidad')

# Los 9 camos con tema dibujado. `''` = sin camo, la referencia.
CAMOS = ['', 'rising-sun', 'pole', 'premium', 'fourth', 'naval', 'mission',
         'blackflag', 'standard', 'chronicles']


def lum(c):
    def f(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def contraste(a, b):
    la, lb = lum(a), lum(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


def mide(png):
    """Contraste real de un recorte de texto: tinta contra lo que hay detrás."""
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert('RGB')
    px = list(im.getdata())
    if len(px) < 40:
        return None
    # Se cuantiza para que el suavizado de bordes no cuente como colores
    # distintos: sin esto, "el color más repetido" sería ruido.
    cuant = [(r // 16 * 16, g // 16 * 16, b // 16 * 16) for r, g, b in px]
    cuenta = Counter(cuant)
    fondo = cuenta.most_common(1)[0][0]
    # La tinta es el color más lejano al fondo que aparezca lo bastante como
    # para ser texto y no un píxel suelto del antialias.
    minimo = max(3, len(px) // 400)
    tinta, peor = None, 0.0
    for color, n in cuenta.items():
        if n < minimo:
            continue
        d = contraste(color, fondo)
        if d > peor:
            peor, tinta = d, color
    if tinta is None:
        return None
    return {'ratio': round(peor, 2), 'fondo': fondo, 'tinta': tinta}


JS_TEXTOS = """
() => {
  // Solo texto que cae SOBRE el fondo: se sube por los ancestros y si alguno
  // tiene fondo propio opaco, ese elemento está protegido y no interesa.
  const fuera = [];
  const visto = new Set();
  document.querySelectorAll('body *').forEach(el => {
    const txt = (el.textContent || '').trim();
    if (!txt || txt.length > 160) return;
    // solo hojas: si un hijo ya tiene el mismo texto, lo mide el hijo
    if ([...el.children].some(c => (c.textContent || '').trim() === txt)) return;
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 6 || r.width > 1200) return;
    if (r.bottom < 0 || r.top > 4000) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) return;
    // ¿tiene algún ancestro con fondo propio?
    let p = el, protegido = false;
    while (p && p !== document.body) {
      const b = getComputedStyle(p).backgroundColor;
      const m = b.match(/rgba?\\(([^)]+)\\)/);
      if (m) {
        const partes = m[1].split(',').map(s => parseFloat(s));
        const alfa = partes.length > 3 ? partes[3] : 1;
        if (alfa >= 0.55) { protegido = true; break; }
      }
      p = p.parentElement;
    }
    if (protegido) return;
    const clave = el.tagName + '|' + txt.slice(0, 40) + '|' + Math.round(r.top);
    if (visto.has(clave)) return;
    visto.add(clave);
    fuera.push({
      texto: txt.slice(0, 60),
      clase: (el.className || '').toString().slice(0, 60),
      tag: el.tagName.toLowerCase(),
      tam: parseFloat(cs.fontSize),
      sel_i: fuera.length,
    });
    el.setAttribute('data-audita', String(fuera.length - 1));
  });
  return fuera;
}
"""


def _cosecha(pg, camo, modo, tab, fallos, contador):
    """Mide todos los textos sueltos de la vista que hay ahora en pantalla."""
    try:
        textos = pg.evaluate(JS_TEXTOS)
    except Exception:
        return
    for t in textos:
        loc = pg.locator('[data-audita="%d"]' % t['sel_i'])
        try:
            png = loc.screenshot(timeout=2500)
        except Exception:
            continue
        r = mide(png)
        contador[0] += 1
        if r and r['ratio'] < UMBRAL:
            fallos.append({'camo': camo or 'sin-camo', 'modo': modo,
                           'tab': tab or 'inicio', **t, **r})


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit('Falta playwright')
    import app as A

    with A.app.app_context():
        A.db.create_all()
        u = A.User.query.filter_by(username=USUARIO).first()
        if not u:
            u = A.User(username=USUARIO, email=USUARIO + '@ej.com')
            u.set_password(CLAVE)
            for c in ('email_verified', 'is_verified', 'verified'):
                if hasattr(u, c):
                    setattr(u, c, True)
            A.db.session.add(u)
        # Premium y NO admin: el admin ve cosas que un cliente no, y lo que se
        # audita es lo que ve un cliente.
        u.plan = 'premium'
        u.is_admin = False
        from datetime import datetime, timedelta, timezone
        u.plan_expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        for slug in CAMOS:
            if slug:
                u.add_camo(slug)
        A.db.session.commit()
        uid = u.id

    os.makedirs(SALIDA, exist_ok=True)
    fallos, contador = [], [0]

    with sync_playwright() as p:
        nav = p.chromium.launch(
            executable_path='/opt/pw-browsers/chromium'
            if os.path.exists('/opt/pw-browsers/chromium') else None)
        ctx = nav.new_context(viewport={'width': 1440, 'height': 900})
        # ⚠️ Sin esto cada carga espera a un CDN bloqueado: 30 s en vez de 1.
        ctx.route('**/*', lambda r: r.continue_()
                  if '127.0.0.1' in r.request.url else r.abort())
        pg = ctx.new_page()

        pg.goto(BASE + '/login', wait_until='domcontentloaded')
        pg.fill('input[name=identifier]', USUARIO)
        pg.fill('input[name=password]', CLAVE)
        pg.click('button[type=submit]')
        pg.wait_for_timeout(1200)

        for camo in CAMOS:
            with A.app.app_context():
                uu = A.db.session.get(A.User, uid)
                uu.active_camo = camo
                A.db.session.commit()
            for modo in ('light', 'dark'):
                # ⚠️ DOS trampas encadenadas, y las dos costaron una pasada
                # entera de medición contra la página equivocada:
                #  1. `/app` exige el cookie que reparte `/welcome`.
                #  2. Y ese cookie es de UN SOLO USO: `/app` lo borra al
                #     servirse (`delete_cookie`). Así que un `reload()` de
                #     `/app` rebota a la bienvenida — y como esa página también
                #     lleva la clase del camo, todo parecía funcionar mientras
                #     se medían los cuatro textos del cargador.
                # Por eso el tema se deja puesto ANTES, y a `/app` se entra una
                # sola vez, sin recargar.
                pg.evaluate("m => localStorage.setItem('scalpel_theme', m)", modo)
                pg.goto(BASE + '/welcome', wait_until='domcontentloaded')
                pg.goto(BASE + '/app', wait_until='domcontentloaded')
                pg.wait_for_timeout(1100)
                if not pg.url.rstrip('/').endswith('/app'):
                    print('  ⚠️ %s/%s acabó en %s — no se mide'
                          % (camo or 'sin-camo', modo, pg.url))
                    continue
                # Recorrer las pestañas: cada una pinta su propio panel, y el
                # texto suelto de una no se ve desde otra.
                try:
                    pestanas = pg.evaluate(
                        "() => [...document.querySelectorAll('.tab-btn,[data-tab]')]"
                        ".map(b => b.getAttribute('data-tab')).filter(Boolean)")
                except Exception:
                    pestanas = []
                for tab in ([None] + list(dict.fromkeys(pestanas))[:12]):
                    if tab:
                        try:
                            pg.click('[data-tab="%s"]' % tab, timeout=1500)
                            pg.wait_for_timeout(280)
                        except Exception:
                            continue
                    _cosecha(pg, camo, modo, tab, fallos, contador)
                continue

                try:
                    textos = pg.evaluate(JS_TEXTOS)
                except Exception as exc:
                    print('  (no se pudo leer %s/%s: %s)' % (camo or 'sin-camo', modo, exc))
                    continue
                for t in textos:
                    loc = pg.locator('[data-audita="%d"]' % t['sel_i'])
                    try:
                        png = loc.screenshot(timeout=3000)
                    except Exception:
                        continue
                    r = mide(png)
                    medidos += 1
                    if r and r['ratio'] < UMBRAL:
                        fallos.append({'camo': camo or 'sin-camo', 'modo': modo,
                                       **t, **r})
        nav.close()

    fallos.sort(key=lambda f: f['ratio'])
    io.open(os.path.join(SALIDA, 'fallos.json'), 'w', encoding='utf-8').write(
        json.dumps(fallos, ensure_ascii=False, indent=1))

    print('\n%d textos medidos · %d por debajo de %.1f\n' % (contador[0], len(fallos), UMBRAL))
    porclase = Counter('%s.%s' % (f['tag'], (f['clase'].split() or [''])[0])
                       for f in fallos)
    print('LOS CULPABLES, por elemento (esto es lo que hay que arreglar):')
    for clase, n in porclase.most_common(15):
        peor = min(f['ratio'] for f in fallos
                   if '%s.%s' % (f['tag'], (f['clase'].split() or [''])[0]) == clase)
        print('  %-34s %3d casos · peor %.2f' % (clase, n, peor))
    print('\nLOS 12 PEORES CASOS:')
    for f in fallos[:12]:
        print('  %.2f  %-11s %-5s %-22s %s'
              % (f['ratio'], f['camo'], f['modo'], (f['clase'] or f['tag'])[:22],
                 f['texto'][:38]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
