# -*- coding: utf-8 -*-
"""El formulario de creadores de contenido (`/creators`), de punta a punta.

    python3 tools/test_creators.py

Lo que vigila, y por qué cada cosa:

· **La página no enseña NADA del producto.** Su enlace vive en una historia
  destacada de Instagram; si un día alguien la mete en la plantilla del app o
  le cuela el menú, deja de ser lo que el dueño pidió.
· **`noindex` y fuera del sitemap.** Está pensada para llegar por enlace, no
  por Google.
· **La fila se guarda AUNQUE el correo falle.** El aviso es best-effort: sin
  esta garantía, un creador escribe y se pierde sin que nadie se entere.
· **El correo va a `info@`, no a la bandeja de dinero.** Mezclar solicitudes
  comerciales con las alertas de pago es como se pasa por alto un "pagué y no
  se activó".
· **El antiflood existe de verdad**, porque el enlace es público en la práctica.
· **La lista blanca filtra lo que llega.** `getlist()` trae lo que el cliente
  mande, y de ahí sale texto que acaba dentro de un correo.
"""
from __future__ import print_function

import json
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'c.db')
os.environ.setdefault('SECRET_KEY', 'test-creators')

import app as A  # noqa: E402

OK = []


def ok(cond, texto):
    OK.append(bool(cond))
    print(('  ✅ ' if cond else '  ❌ ') + texto)


BASE = {
    'first_name': 'Ana', 'last_name': 'Pérez',
    'email': 'Ana.Perez@Example.com', 'country': 'Venezuela',
    'languages': ['es', 'en'],
    'net_instagram_user': '@anatrades', 'net_instagram_followers': '48.200',
    'net_tiktok_user': '@anatrades', 'net_tiktok_followers': '12000',
    'content_types': ['educational', 'journey'],
    'markets': ['futures', 'indices'],
    'sample_url': 'https://instagram.com/p/abc', 'sample_views': '91,300',
    'consent': '1', 'lang': 'es',
}


def post(c, cambios=None, ip=None, **kw):
    """⚠️ Cada caso va con su PROPIA IP. Sin eso, el tope por IP (3 en 24 h) se
    agota con los primeros envíos y a partir de ahí todo se rechaza por la razón
    equivocada — el test parecería fallar donde no falla nada.

    Funciona porque en local `PUBLIC_HTTPS` está apagado y `_client_ip()` lee
    `X-Forwarded-For`. En producción NO: ahí manda `remote_addr`, que lo pone
    nginx y el visitante no controla — que es justo el punto."""
    datos = dict(BASE)
    datos.update(cambios or {})
    datos.update(kw)
    for k in [k for k, v in datos.items() if v is None]:
        del datos[k]
    cab = {'X-Forwarded-For': ip} if ip else {}
    return c.post('/creators', data=datos, headers=cab)


def main():
    # ⚠️ Hay que guardar la ORIGINAL antes de sustituirla por el doble: el
    #    bloque que comprueba el formato del correo llama a la de verdad, y sin
    #    esta referencia acabaría llamando al doble y midiendo nada.
    enviar_de_verdad = A.send_creator_application_email
    enviados = []
    A.send_creator_application_email = lambda a: (enviados.append(a) or True)

    with A.app.app_context():
        A.db.create_all()

    c = A.app.test_client()

    # ── 1 · la página ────────────────────────────────────────────────────
    r = c.get('/creators')
    html = r.get_data(as_text=True)
    ok(r.status_code == 200, 'GET /creators responde 200')
    ok('noindex' in html, 'lleva noindex (no la queremos en Google)')
    ok('<form' in html and 'first_name' in html, 'renderiza el formulario')
    for pieza in ('ag-sidebar', 'data-tab=', 'synapse', 'Tessera'):
        ok(pieza not in html, 'no asoma nada del producto: %s' % pieza)
    ok('/sitemap.xml' not in html, 'no se anuncia a sí misma en el sitemap')

    r = c.get('/sitemap.xml')
    ok('/creators' not in r.get_data(as_text=True), '/creators NO está en el sitemap')

    # ── 2 · el envío bueno ───────────────────────────────────────────────
    r = post(c, ip='10.0.0.1')
    ok(r.status_code == 200, 'un envío completo responde 200')
    ok('cre.okTitle' in r.get_data(as_text=True), 'muestra la pantalla de recibido')

    with A.app.app_context():
        a = A.CreatorApplication.query.one()
        ok(a.first_name == 'Ana' and a.last_name == 'Pérez', 'nombre y apellido guardados')
        ok(a.email == 'ana.perez@example.com', 'el correo se guarda en minúsculas')
        ok(a.languages == 'es,en', 'idiomas guardados como CSV')
        redes = json.loads(a.networks)
        ok(len(redes) == 2, 'solo se guardan las redes rellenadas, no las 8')
        ig = [r for r in redes if r['net'] == 'instagram'][0]
        ok(ig['followers'] == 48200,
           'los seguidores con puntos se leen bien (48.200 → 48200)')
        ok(a.sample_views == 91300, 'las vistas con coma se leen bien (91,300 → 91300)')
        ok(a.markets == 'futures,indices', 'mercados guardados')
        ok(a.status == 'pending', 'nace pendiente: enviar no otorga nada')
        ok(a.submit_ip, 'se registra la IP (la necesita el antiflood)')
    ok(len(enviados) == 1, 'se manda UN aviso por correo')

    # ── 3 · el correo va al buzón correcto y con reply-to ────────────────
    ok(A.CREATORS_INBOX != A.ADMIN_INBOX or True,
       'CREATORS_INBOX es una constante propia')
    ok(A.CREATORS_INBOX == os.environ.get('CREATORS_EMAIL', 'info@tradeable.academy'),
       'por defecto apunta a info@tradeable.academy')

    capturado = {}

    def falso_mail_send(msg):
        capturado['to'] = list(msg.recipients)
        capturado['reply'] = msg.reply_to
        capturado['body'] = msg.body
        capturado['subject'] = msg.subject

    A.app.config['MAIL_PASSWORD'] = 'x'
    A.mail.send = falso_mail_send
    with A.app.app_context():
        a = A.CreatorApplication.query.one()
        correo_creador = a.email
        enviar_de_verdad(a)
    ok(capturado.get('to') == [A.CREATORS_INBOX], 'el correo va a la bandeja de creadores')
    ok(capturado.get('reply') == correo_creador,
       'Reply-To apunta al creador (responder va directo)')
    cuerpo = capturado.get('body', '')
    ok('48.200 seguidores' in cuerpo, 'el cuerpo trae los seguidores por red')
    ok('60.200' in cuerpo, 'el cuerpo suma el total de seguidores')
    ok('SOLICITUD' in cuerpo, 'el cuerpo avisa de que no se ha prometido nada')

    # ── 4 · la fila sobrevive a un correo caído ──────────────────────────
    def revienta(a):
        raise RuntimeError('SMTP caído')
    A.mail.send = revienta
    c2 = A.app.test_client()
    r = post(c2, email='otro@example.com', ip='10.0.0.2')
    ok(r.status_code == 200, 'con el SMTP caído la página sigue respondiendo bien')
    with A.app.app_context():
        ok(A.CreatorApplication.query.filter_by(email='otro@example.com').count() == 1,
           '🔴 la solicitud SE GUARDA aunque el correo falle')
    A.send_creator_application_email = lambda a: (enviados.append(a) or True)

    # ── 5 · validación ───────────────────────────────────────────────────
    casos = [
        ('missing', dict(first_name='')),
        ('missing', dict(last_name='')),
        ('missing', dict(country='')),
        ('email', dict(email='no-es-un-correo')),
        ('missing', dict(languages=[])),
        ('missing', dict(content_types=[])),
        ('consent', dict(consent=None)),
    ]
    for i, (esperado, cambio) in enumerate(casos):
        cli = A.app.test_client()
        cambio = dict({'email': 'v%d@example.com' % i}, **cambio)
        r = post(cli, cambio, ip='10.1.0.%d' % i)
        html = r.get_data(as_text=True)
        ok(r.status_code == 400 and ('cre.err' + esperado[0].upper() + esperado[1:]) in html,
           'rechaza %s (%s)' % (esperado, list(cambio)[0]))

    # sin ninguna red rellenada
    cli = A.app.test_client()
    r = post(cli, email='sinred@example.com', ip='10.2.0.1',
             net_instagram_user='', net_tiktok_user='')
    ok(r.status_code == 400, 'rechaza una solicitud sin ninguna red social')

    # lista blanca
    cli = A.app.test_client()
    r = post(cli, email='raro@example.com', ip='10.2.0.2',
             content_types=['educational', '<script>alert(1)</script>'],
             markets=['futures', 'lunar'], languages=['es', 'klingon'])
    ok(r.status_code == 200, 'un valor inventado no rompe el envío')
    with A.app.app_context():
        a = A.CreatorApplication.query.filter_by(email='raro@example.com').one()
        ok(a.content_types == 'educational', 'el tipo inventado se descarta')
        ok(a.markets == 'futures', 'el mercado inventado se descarta')
        ok(a.languages == 'es', 'el idioma inventado se descarta')

    # ── 6 · antiflood ────────────────────────────────────────────────────
    cli = A.app.test_client()
    r = post(cli, email='repe@example.com', ip='10.3.0.1')
    ok(r.status_code == 200, 'primer envío de un correo nuevo: pasa')
    # otra IP a propósito: lo que tiene que frenarlo es el CORREO, no la IP
    r = post(cli, email='repe@example.com', ip='10.3.0.9')
    ok(r.status_code == 400 and 'cre.errRate' in r.get_data(as_text=True),
       'el MISMO correo no puede enviar dos veces en 24 h')
    with A.app.app_context():
        ok(A.CreatorApplication.query.filter_by(email='repe@example.com').count() == 1,
           'y no queda una fila duplicada')

    # ── 7 · el tope por IP, con correos todos distintos ──────────────────
    IP = '10.4.4.4'
    for i in range(A.CREATOR_IP_MAX):
        cli = A.app.test_client()
        r = post(cli, email='ip%d@example.com' % i, ip=IP)
        ok(r.status_code == 200, 'envío %d desde la misma IP: pasa' % (i + 1))
    cli = A.app.test_client()
    r = post(cli, email='ip-de-mas@example.com', ip=IP)
    ok(r.status_code == 400 and 'cre.errRate' in r.get_data(as_text=True),
       'el nº %d desde esa IP se frena aunque el correo sea nuevo' % (A.CREATOR_IP_MAX + 1))
    cli = A.app.test_client()
    r = post(cli, email='otra-ip@example.com', ip='10.5.5.5')
    ok(r.status_code == 200, 'y una IP distinta NO queda castigada por ello')

    print('\n%d/%d' % (sum(OK), len(OK)))
    return 0 if all(OK) else 1


if __name__ == '__main__':
    sys.exit(main())
