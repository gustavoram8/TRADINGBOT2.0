# -*- coding: utf-8 -*-
"""El icono del sitio existe, se sirve y está declarado.

    venv/bin/python3 tools/test_favicon.py

Vigila lo que el dueño reportó que faltaba: el logo que Google pinta junto a
cada resultado, el de la pestaña, el de "añadir a inicio" del iPhone y la
tarjeta que sale al pegar el enlace en WhatsApp / X / LinkedIn.

🔑 Lo importante que prueba: las rutas de la RAÍZ (`/favicon.ico`,
`/apple-touch-icon.png`) responden SIN que ninguna página las declare —
navegadores y Google las piden por convención, y por eso el icono aparece en
las 44 plantillas sin editar ninguna.
"""
from __future__ import print_function
import io as _io, os, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'f.db')
os.environ.setdefault('SECRET_KEY', 'fav')
os.environ['SITE_URL'] = 'https://tradeable.academy'
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
try:
    import app as A
except Exception as e:
    sys.exit('no se pudo cargar la app: %s%s' % (e,
        ('\n\n👉 venv/bin/python3 %s' % os.path.relpath(__file__, RAIZ))
        if 'No module named' in str(e) else ''))
from PIL import Image

OK = FALLOS = 0
def check(c, t):
    global OK, FALLOS
    print(('  ✅ ' if c else '  ❌ ') + t)
    if c: OK += 1
    else: FALLOS += 1

def main():
    with A.app.app_context():
        A.db.create_all()
    c = A.app.test_client()

    print('\n══ 1 · las rutas que el mundo pide SOLO, sin etiquetas ══')
    for ruta, mime in (('/favicon.ico', 'image/x-icon'),
                       ('/apple-touch-icon.png', 'image/png'),
                       ('/apple-touch-icon-precomposed.png', 'image/png'),
                       ('/icon-192.png', 'image/png')):
        r = c.get(ruta)
        check(r.status_code == 200
              and r.headers['Content-Type'].startswith(mime)
              and len(r.data) > 500,
              '%-38s %s (%d bytes)' % (ruta, r.status_code, len(r.data)))

    print('\n══ 2 · lo declarado en la landing ══')
    h = c.get('/').get_data(as_text=True)
    for frag, que in (
        ('rel="icon"', 'declara el icono'),
        ('sizes="192x192"', 'la resolución que Google prefiere'),
        ('apple-touch-icon', '"añadir a inicio" del iPhone'),
        ('theme-color" content="#004feb', 'color de marca en la barra del móvil'),
        ('og:image', 'tarjeta social'),
        ('summary_large_image', 'tarjeta grande en X'),
        ('https://tradeable.academy/static/og-image.png', '🔑 og:image ABSOLUTA'),
    ):
        check(frag in h, que)

    print('\n══ 3 · los archivos son lo que dicen ser ══')
    im = Image.open(_io.BytesIO(c.get('/static/og-image.png').data))
    check(im.size == (1200, 630), 'og-image.png mide 1200×630 (%dx%d)' % im.size)
    ico = Image.open(_io.BytesIO(c.get('/favicon.ico').data))
    check(ico.info.get('sizes', set()) >= {(16, 16), (32, 32), (48, 48)},
          'favicon.ico trae 16, 32 y 48 dentro')
    ap = Image.open(_io.BytesIO(c.get('/apple-touch-icon.png').data))
    # iOS pinta NEGRO detrás de un icono con transparencia: tiene que ser opaco
    check(ap.mode == 'RGB' and ap.size == (180, 180),
          'apple-touch-icon 180×180 y SIN transparencia (iOS la pinta negra)')

    print('\nRESULTADO: %d/%d' % (OK, OK + FALLOS))
    return 0 if not FALLOS else 1

if __name__ == '__main__':
    sys.exit(main())
