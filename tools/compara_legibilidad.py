# -*- coding: utf-8 -*-
"""Antes y después del arreglo de legibilidad, lado a lado y a tamaño real.

    python3 tools/compara_legibilidad.py                 # los camos peores
    python3 tools/compara_legibilidad.py naval mission   # los que se pidan

Existe porque un número de contraste no convence a nadie: 4.6 pasa el umbral y
aun así puede verse sucio, y 4.4 puede leerse perfectamente. La decisión de si
el arreglo mejora o ensucia es del dueño, y para eso tiene que VERLO.

Genera un PNG por camo con la misma zona antes y después, recortada de la
página real —no un mockup— con el arreglo apagado y encendido mediante una
clase en el `<html>`, así la única diferencia entre las dos mitades es
exactamente lo que se está proponiendo.
"""
import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

BASE = 'http://127.0.0.1:5001'
USUARIO, CLAVE = 'audita10', 'Zx8!kQ2mLp7w'
SALIDA = os.path.join(RAIZ, 'out', 'legibilidad')

# La zona que el dueño señaló: el encabezado del analizador, que es texto
# suelto sobre el dibujo del camo, sin ningún panel detrás.
ZONA = 'footer'


def _rotula(im, texto, alto=34):
    from PIL import Image, ImageDraw
    out = Image.new('RGB', (im.size[0], im.size[1] + alto), (26, 28, 34))
    out.paste(im, (0, alto))
    d = ImageDraw.Draw(out)
    d.text((10, alto // 2 - 6), texto, fill=(235, 238, 245))
    return out


def main(argv):
    from PIL import Image
    from playwright.sync_api import sync_playwright
    import app as A

    camos = argv or ['naval', 'mission', 'chronicles', 'blackflag']
    os.makedirs(SALIDA, exist_ok=True)

    with A.app.app_context():
        u = A.User.query.filter_by(username=USUARIO).first()
        if not u:
            sys.exit('Falta el usuario de auditoría: corré antes '
                     'tools/audita_legibilidad.py')
        uid = u.id

    hechos = []
    with sync_playwright() as p:
        nav = p.chromium.launch(
            executable_path='/opt/pw-browsers/chromium'
            if os.path.exists('/opt/pw-browsers/chromium') else None)
        ctx = nav.new_context(viewport={'width': 1440, 'height': 900})
        ctx.route('**/*', lambda r: r.continue_()
                  if '127.0.0.1' in r.request.url else r.abort())
        pg = ctx.new_page()
        pg.goto(BASE + '/login', wait_until='domcontentloaded')
        pg.fill('input[name=identifier]', USUARIO)
        pg.fill('input[name=password]', CLAVE)
        pg.click('button[type=submit]')
        pg.wait_for_timeout(1200)

        for camo in camos:
            for modo in ('light', 'dark'):
                with A.app.app_context():
                    uu = A.db.session.get(A.User, uid)
                    uu.active_camo = camo
                    A.db.session.commit()
                pg.evaluate("m => localStorage.setItem('scalpel_theme', m)", modo)
                # ⚠️ El cookie de /welcome es de UN SOLO USO y /app lo borra:
                # hay que volver a pasar por la bienvenida en cada vuelta.
                pg.goto(BASE + '/welcome', wait_until='domcontentloaded')
                pg.goto(BASE + '/app', wait_until='domcontentloaded')
                pg.wait_for_timeout(1000)
                # ⚠️ El primero que coincide puede estar OCULTO: hay varios
                # `<footer>` en la página (el del libro de Synapse, por
                # ejemplo). Hay que quedarse con el primero VISIBLE o se acaba
                # esperando eternamente a que algo invisible entre en pantalla.
                loc = None
                for i in range(pg.locator(ZONA).count()):
                    cand = pg.locator(ZONA).nth(i)
                    try:
                        if cand.is_visible():
                            loc = cand
                            break
                    except Exception:
                        continue
                if loc is None:
                    print('  (no hay %s visible en %s/%s)' % (ZONA, camo, modo))
                    continue
                try:
                    loc.scroll_into_view_if_needed(timeout=2000)
                except Exception:
                    pass

                # ANTES: el arreglo apagado (se apaga desde el <html>, así que
                # la página es la misma en los dos lados salvo por él).
                pg.evaluate("() => document.documentElement.classList.add('sin-halo')")
                pg.wait_for_timeout(150)
                antes = Image.open(io.BytesIO(loc.screenshot())).convert('RGB')
                # DESPUÉS
                pg.evaluate("() => document.documentElement.classList.remove('sin-halo')")
                pg.wait_for_timeout(150)
                despues = Image.open(io.BytesIO(loc.screenshot())).convert('RGB')

                a = _rotula(antes, 'ANTES   %s · %s' % (camo, modo))
                b = _rotula(despues, 'DESPUES %s · %s' % (camo, modo))
                w = max(a.size[0], b.size[0])
                comp = Image.new('RGB', (w, a.size[1] + b.size[1] + 8), (26, 28, 34))
                comp.paste(a, (0, 0))
                comp.paste(b, (0, a.size[1] + 8))
                ruta = os.path.join(SALIDA, 'comp_%s_%s.png' % (camo, modo))
                comp.save(ruta)
                hechos.append(ruta)
                print('  %s' % ruta)
        nav.close()
    print('\n%d comparaciones en %s' % (len(hechos), SALIDA))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
