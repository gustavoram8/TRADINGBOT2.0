# -*- coding: utf-8 -*-
"""El sitemap solo puede llevar URLs FINALES: ninguna que redirija.

Existe porque el fallo que reporto Search Console era invisible leyendo el
codigo — `pricing` parecia una pagina y hacia meses que era un redirect.
"""
from __future__ import print_function
import os, re, sys
sys.path.insert(0, '/home/user/TRADINGBOT2.0/scalpel')
os.environ.setdefault('SITE_URL', 'https://tradeable.academy')
import app as A

ok = fallos = 0


def chk(cond, msg):
    global ok, fallos
    if cond:
        ok += 1
    else:
        fallos += 1
        print('  FALLO:', msg)


with A.app.app_context():
    A.init_db()
c = A.app.test_client()
xml = c.get('/sitemap.xml')
chk(xml.status_code == 200, 'sitemap responde 200')
locs = re.findall(r'<loc>([^<]+)</loc>', xml.get_data(as_text=True))
chk(len(locs) > 0, 'el sitemap trae URLs')
print('URLs en el sitemap:', len(locs))

for u in locs:
    ruta = '/' + u.split('/', 3)[3] if u.count('/') > 2 else '/'
    r = c.get(ruta)
    chk(r.status_code == 200,
        '%s deberia dar 200 y da %s -> %s' % (ruta, r.status_code,
                                              r.headers.get('Location', '')))
    print('  %-14s %s' % (ruta, r.status_code))

# las que se sacaron a proposito
for fuera in ('/pricing', '/login', '/register'):
    chk(not any(l.endswith(fuera) for l in locs), '%s no debe estar' % fuera)
chk(c.get('/pricing').status_code in (301, 302), '/pricing sigue redirigiendo (no se rompio)')
chk(any(l.rstrip('/').endswith('tradeable.academy') for l in locs), 'la portada sigue')

print('\n%d bien, %d fallos' % (ok, fallos))
sys.exit(1 if fallos else 0)
