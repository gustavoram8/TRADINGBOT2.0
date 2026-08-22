# -*- coding: utf-8 -*-
"""La RODADA de temporadas de la ruleta, probada mes a mes.

    venv/bin/python3 tools/test_rodada.py   (o python3)

Contexto (2026-08-22): el sitio abrió sin clientes y el dueño decidió no
quemar la tanda de agosto ante una sala vacía. Chronicles corre agosto Y
septiembre; lo de septiembre pasa a octubre, etc.; Quetzalcóatl queda FUERA
(su gracia era el equinoccio de marzo). Las filas de la base conservan su
sello original — la traducción vive en `RULETA_RODADA`.

Lo que se vigila, porque es lo que el dueño pidió con nombre y apellido:
«No podemos permitir que algún camo, cursor o marco que no es de una
temática, se cuele en ella.» Cada mes se compara la tanda COMPLETA contra el
conjunto EXACTO esperado — no "contiene", igualdad de conjuntos.

⚠️ El mes se simula reemplazando `A._current_season`: todas las lecturas del
   servidor (tanda, spin, tienda) resuelven el nombre en el módulo al momento
   de la llamada, así que el parche llega a todas.
"""
from __future__ import print_function

import os
import sys
import tempfile

os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'r.db')
os.environ.setdefault('SECRET_KEY', 'test-rodada')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'scalpel'))
import app as A  # noqa: E402

OK, MAL = 0, []


def caso(nombre, cond, extra=''):
    global OK
    if cond:
        OK += 1
        print('  ✅ %s' % nombre)
    else:
        MAL.append(nombre)
        print('  🔴 %s %s' % (nombre, extra))


def tanda_en(mes):
    A._current_season = lambda: mes
    return {i.slug for i in A._roulette_tanda()}


def lote(temado, libre1, libre2, libre3=None, camo=None):
    s = {temado, libre1, 'cur-%s' % temado, 'cur-%s' % libre2, 'cur-%s' % libre3}
    if camo:
        s.add('camo-%s' % camo)
    return s


with A.app.app_context():
    A.init_db()

    print('── la tanda de cada mes, contra el conjunto EXACTO ──')
    CHRON = {'chronicles', 'mars', 'cur-chronicles', 'cur-candle',
             'cur-rocket', 'camo-chronicles'}
    caso('agosto 2026 = Chronicles completo (6 piezas)',
         tanda_en('2026-08') == CHRON, str(tanda_en('2026-08')))
    caso('septiembre 2026 = LA MISMA tanda de Chronicles',
         tanda_en('2026-09') == CHRON, str(tanda_en('2026-09')))
    caso('octubre 2026 = American Football COMPLETO (camo construido 2026-08-22)',
         tanda_en('2026-10') == {'gridiron', 'sakura', 'cur-gridiron',
                                 'cur-coin', 'cur-anchor', 'camo-gridiron'},
         str(tanda_en('2026-10')))
    caso('noviembre 2026 = Nile COMPLETO (camo construido 2026-08-22)',
         tanda_en('2026-11') == {'nile', 'terminal', 'cur-nile',
                                 'cur-chart', 'cur-compass', 'camo-nile'})
    caso('diciembre 2026 = Colosseum',
         tanda_en('2026-12') == {'colosseum', 'cartography', 'cur-colosseum',
                                 'cur-bell', 'cur-bulb'})
    caso('enero 2027 = Summit',
         tanda_en('2027-01') == {'summit', 'obsidian', 'cur-summit',
                                 'cur-diamond', 'cur-flame'})
    caso('febrero 2027 = Bengal',
         tanda_en('2027-02') == {'bengal', 'candlegrid', 'cur-bengal',
                                 'cur-target', 'cur-star'})
    caso('marzo 2027 = Olympus — y NADA de Quetzalcóatl',
         tanda_en('2027-03') == {'olympus', 'circuit', 'cur-olympus',
                                 'cur-clock', 'cur-dice'},
         str(tanda_en('2027-03')))
    print('── de abril en adelante el calendario vuelve a su mes original ──')
    caso('abril 2027 = Baseball (opening day conservado)',
         tanda_en('2027-04') == {'baseball', 'orderflow', 'cur-baseball',
                                 'cur-lock', 'cur-mug'})
    caso('mayo 2027 = Apiarist (floración conservada)',
         tanda_en('2027-05') == {'apiarist', 'volume', 'cur-apiarist',
                                 'cur-crown', 'cur-cactus'})
    caso('julio 2027 = Zeppelin (último lote)',
         tanda_en('2027-07') == {'zeppelin', 'arcade', 'cur-zeppelin',
                                 'cur-hourglass', 'cur-moon'})
    caso('agosto 2027: calendario agotado → tanda vacía (la rueda anuncia)',
         tanda_en('2027-08') == set())

    print('── Quetzalcóatl fuera del calendario, en TODOS los meses ──')
    QUETZAL = {'quetzal', 'volcano', 'cur-quetzal', 'cur-key', 'cur-umbrella'}
    meses = ['2026-%02d' % m for m in range(8, 13)] + \
            ['2027-%02d' % m for m in range(1, 9)]
    caso('ninguna pieza del lote quetzal sale en ningún mes',
         all(not (tanda_en(m) & QUETZAL) for m in meses))
    caso('las piezas de quetzal SIGUEN en la base (nada se borra, solo '
         'quedan sin mes)',
         A.CosmeticItem.query.filter_by(slug='quetzal').count() == 1
         and A.CosmeticItem.query.filter_by(slug='cur-key').count() == 1)

    print('── la tienda: estados y etiquetas por mes ──')
    u = A.User(username='rodada', email='rd@x.com', email_verified=True)
    u.set_password('Zx9!wQ4mNp2r')
    u.email_canonical = u.email
    u.plan = 'premium'
    A.db.session.add(u)
    A.db.session.commit()

    import re as _re

    def tienda_en(mes):
        A._current_season = lambda: mes
        c = A.app.test_client()
        c.post('/login', data={'identifier': 'rodada',
                               'password': 'Zx9!wQ4mNp2r'})
        r = c.get('/cosmetics')
        assert r.status_code == 200, r.status_code
        return r.data.decode('utf-8')

    h = tienda_en('2026-09')
    # ⚠️ el slug 'gridiron' aparece en `window.CAMO_STATE.ready` (una lista de
    #    DATOS que lleva todos los camos con CSS, chronicles incluido desde
    #    siempre): lo que delataría la sorpresa es una TARJETA — su arte.
    caso('sept: el marco Chronicles se pinta y gridiron sigue sin TARJETA',
         'chronicles' in h and 'plates/gridiron.svg' not in h
         and 'camo_skin_gridiron' not in h)
    caso('sept: quetzal no aparece', 'quetzal' not in h)
    h = tienda_en('2026-10')
    caso('oct: la tarjeta del marco gridiron ya se pinta',
         'plates/gridiron.svg' in h)
    caso('oct: el camo gridiron sale en el estante de ruleta',
         'camo_skin_gridiron' in h)
    # ⚠️ la tarjeta reparte slug y etiqueta en varias líneas: la ventana del
    #    regex tiene que aceptar saltos ([\s\S]), no [^\n]
    caso('oct: chronicles sigue visible (ya pasó) con cierre en 2026-09',
         'chronicles' in h and _re.search(
             r'chronicles[\s\S]{0,600}2026-09', h) is not None)
    caso('oct: quetzal no aparece', 'quetzal' not in h)
    h = tienda_en('2027-06')
    caso('jun-2027: quetzal tampoco (ni como "terminada")', 'quetzal' not in h)

    print('── el spin entrega SOLO piezas del lote vivo ──')
    A._current_season = lambda: '2026-09'
    c = A.app.test_client()
    c.post('/login', data={'identifier': 'rodada', 'password': 'Zx9!wQ4mNp2r'})
    fila = A.DailyQuizState.query.filter_by(user_id=u.id).first()
    if fila is None:
        fila = A.DailyQuizState(user_id=u.id)
        A.db.session.add(fila)
    fila.spins_available = 12
    A.db.session.commit()
    premios = set()
    for _ in range(12):
        r = c.post('/api/daily/spin')
        if r.status_code != 200:
            break
        premios.add(r.get_json()['slug'])   # el spin responde plano, sin 'prize'
    esperado_spin = {'chronicles', 'mars', 'cur-chronicles', 'cur-candle',
                     'cur-rocket', 'chronicles'}  # el camo llega con slug pelado
    caso('12 giros en septiembre: todo premio es del lote Chronicles',
         premios <= esperado_spin, str(premios))
    caso('y en 12 giros la tanda entera cayó (5 piezas + camo pelado)',
         len(premios) >= 5, str(premios))

print()
print('%d/%d' % (OK, OK + len(MAL)))
if MAL:
    print('FALLAN:', MAL)
    sys.exit(1)
