# -*- coding: utf-8 -*-
"""La venta del PDF de Synapse, de punta a punta, con PayPal simulado.

    python3 tools/test_pdf_venta.py

Esta compra sale a LIVE sin que el dueño pueda ensayarla en sandbox, así que
la suite recorre TODO el circuito: comprar → aprobar → capturar → webhook →
descargar en los cuatro idiomas → re-descargar meses después. Y las reglas
del producto: precio server-side, sin comisión del socio, sin tocar planes,
libro aparte, avisos correctos, y las redes de rescate (webhook y barrido)
para el comprador que cierra la pestaña.

La generación del PDF se sustituye por un stub en casi todos los checks (la
real tarda ~15 s y ya se verificó aparte generando los 4 idiomas); el ÚLTIMO
check genera uno de verdad para que la cadena completa quede probada.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'pv.db')
os.environ.update(PAYPAL_CLIENT_ID='x', PAYPAL_SECRET='y', PAYPAL_ENV='live',
                  PAYPAL_WEBHOOK_ID='wh-test')
import app as A  # noqa: E402
from flask import g  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

PASS = FAIL = 0
CLAVE = 'Xk9!mQ2#pL5v'


def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c)
    PASS += ok
    FAIL += (not ok)
    print('   %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))


ESTADO = {'orden': 'PPS-1'}


def falso_api(method, path, payload=None, request_id=None):
    if path.endswith('/v1/oauth2/token'):
        return 200, {'access_token': 't', 'expires_in': 30000}
    if path.endswith('/v2/checkout/orders'):
        return 201, {'id': ESTADO['orden'], 'status': 'CREATED',
                     'links': [{'rel': 'approve',
                                'href': 'https://paypal.test/aprobar-pdf'}]}
    if path.endswith('/capture'):
        return 201, {'id': ESTADO['orden'], 'status': 'COMPLETED',
                     'purchase_units': [{'payments': {'captures': [{
                         'id': 'CAPS', 'status': 'COMPLETED',
                         'amount': {'value': '15.00', 'currency_code': 'USD'}}]}}]}
    if '/v1/notifications/verify-webhook-signature' in path:
        return 200, {'verification_status': 'SUCCESS'}
    return 200, {'id': ESTADO['orden'], 'status': 'COMPLETED',
                 'purchase_units': [{'payments': {'captures': [{
                     'id': 'CAPS', 'status': 'COMPLETED',
                     'amount': {'value': '15.00', 'currency_code': 'USD'}}]}}]}


A._paypal_api = falso_api
avisos = []
A._wa_encolar = lambda t: avisos.append(t)
A.WA_PHONE, A.WA_APIKEY = '+0', 'k'

# Stub del generador: el PDF real (~15 s por idioma) ya se verificó aparte.
real_build = A._build_synapse_pdf
pedidos_de_pdf = []


def build_stub(buyer_name, buyer_email, order_id, lang='en'):
    pedidos_de_pdf.append((buyer_name, buyer_email, order_id, lang))
    return b'%PDF-1.7 stub ' + lang.encode()


A._build_synapse_pdf = build_stub


def cliente(nombre):
    c = A.app.test_client()
    with A.app.app_context():
        g.pop('_login_user', None)
    c.post('/login', data={'identifier': nombre, 'password': CLAVE})
    return c


with A.app.app_context():
    A.db.create_all()
    def usuario(n, admin=False, plan='premium'):
        # las compradoras van en premium: desde 2026-08-07 COMPRAR el PDF exige
        # el plan (decisión del dueño; Synapse entera es premium). Lo comprado
        # se conserva aunque el plan caiga — eso se prueba más abajo.
        u = A.User(username=n, email=n + '@demo.invalid', plan=plan,
                   email_verified=True, is_admin=admin)
        u.set_password(CLAVE)
        A.db.session.add(u)
        A.db.session.commit()
        return u.id
    UID = usuario('lectora')
    UID2 = usuario('mirona')
    JEFE = usuario('jefa', admin=True)
    UFREE = usuario('gratis', plan='free')

# ── 1 · comprar ───────────────────────────────────────────────────────────
print('── 1 · la compra')
# el candado: sin premium NO se compra, ni llamando al endpoint directo
cf = cliente('gratis')
r = cf.post('/api/synapse/pdf/buy', json={'lang': 'es'})
check('🔴 un usuario FREE no puede comprar (403 premium_only) aunque llame '
      'al endpoint a mano',
      r.status_code == 403 and (r.get_json() or {}).get('error') == 'premium_only',
      '%s %s' % (r.status_code, r.get_json()))
c = cliente('lectora')
r = c.post('/api/synapse/pdf/buy', json={'lang': 'xx'})
check('idioma inventado → 400', r.status_code == 400, r.status_code)
r = c.post('/api/synapse/pdf/buy', json={'lang': 'es', 'price': 0.01})
j = r.get_json() or {}
check('responde con la URL de PayPal',
      r.status_code == 200 and 'paypal.test' in (j.get('url') or ''),
      '%s %s' % (r.status_code, j))
with A.app.app_context():
    o = A.SynapseOrder.query.filter_by(user_id=UID).first()
    check('el pedido existe, en el idioma pedido', o and o.lang == 'es')
    check('🔴 al precio del SERVIDOR — el "price" del cliente se ignora',
          o and abs(o.price - A.SYNAPSE_PDF_PRICE) < 0.001, o.price if o else None)
    OID = o.id
r = c.get('/synapse/pdf/mine?lang=es')
check('🔴 y NO se entrega antes de pagar (403)', r.status_code == 403, r.status_code)

# repetir la compra reutiliza el pendiente (cambiando idioma), no apila
r = c.post('/api/synapse/pdf/buy', json={'lang': 'fr'})
with A.app.app_context():
    n = A.SynapseOrder.query.filter_by(user_id=UID).count()
    o = A.db.session.get(A.SynapseOrder, OID)
    check('reintentar NO apila pedidos (%d) y actualiza el idioma (%s)'
          % (n, o.lang), n == 1 and o.lang == 'fr')

# ── 2 · vuelve de PayPal ──────────────────────────────────────────────────
print('── 2 · la vuelta de PayPal')
del avisos[:]
r = c.get('/synapse/pdf/paypal/return/%d' % OID, follow_redirects=False)
check('captura y manda a la página de descarga',
      r.status_code == 302 and '/synapse/pdf/ready' in r.headers['Location'],
      r.headers.get('Location'))
with A.app.app_context():
    o = A.db.session.get(A.SynapseOrder, OID)
    check('el pedido queda pagado', o.status == 'paid', o.status)
    check('y aplicado (idempotencia armada)', o.applied_at is not None)
    check('🔴 SIN fila en el libro de PLANES — el socio no comisiona',
          A.SaleBreakdown.query.count() == 0)
    check('y el plan de la cuenta NO se tocó',
          A.db.session.get(A.User, UID).plan == 'premium')
check('el dueño recibe UN WhatsApp de venta',
      len(avisos) == 1 and 'VENTA confirmada' in avisos[0], avisos)
check('que dice que es el PDF', 'Biblioteca Synapse' in avisos[0]
      and '$15.00' in avisos[0], avisos and avisos[0])

# la página de descarga, ya como dueña
r = c.get('/synapse/pdf/ready?lang=fr')
cuerpo = r.get_data(as_text=True)
check('la página "preparando" sale en modo descarga',
      'spdf.readyTitle' in cuerpo and '/synapse/pdf/mine?lang=fr' in cuerpo)

# ── 3 · el webhook repetido no duplica nada ───────────────────────────────
print('── 3 · el webhook, dos veces')
del avisos[:]
evento = {'event_type': 'PAYMENT.CAPTURE.COMPLETED',
          'resource': {'id': 'CAPS', 'status': 'COMPLETED',
                       'custom_id': 'spdf-%d' % OID,
                       'amount': {'value': '15.00'}}}
for _ in range(2):
    r = c.post('/webhook/paypal', json=evento)
    check('el webhook se acepta (%s)' % r.status_code, r.status_code == 200)
check('🔴 y NO re-avisa la venta (%d avisos)' % len(avisos), len(avisos) == 0)

# ── 4 · la descarga: suya, en 4 idiomas, para siempre ─────────────────────
print('── 4 · la descarga')
for lang in ('en', 'es', 'fr', 'pt'):
    r = c.get('/synapse/pdf/mine?lang=%s' % lang)
    check('descarga %s' % lang.upper(),
          r.status_code == 200 and r.data.startswith(b'%PDF')
          and r.headers['Content-Type'] == 'application/pdf', r.status_code)
check('la marca de agua lleva SU pedido',
      pedidos_de_pdf and pedidos_de_pdf[-1][:3] == ('lectora',
                                                    'lectora@demo.invalid',
                                                    'SPDF-%d' % OID))
r = c.get('/synapse/pdf/mine?lang=es')
check('la 5ª descarga aún pasa (el tope es 5/10 min)', r.status_code == 200,
      r.status_code)
r = c.get('/synapse/pdf/mine?lang=es')
check('la 6ª se frena (429): generar el PDF cuesta CPU',
      r.status_code == 429, r.status_code)
# meses después (los eventos de auditoría "envejecen") sigue siendo suyo
with A.app.app_context():
    for ev in A.AuditEvent.query.filter_by(event_type='pdf_downloaded'):
        ev.created_at = datetime.now(timezone.utc) - timedelta(days=90)
    A.db.session.commit()
with A.app.app_context():
    # y aunque su plan haya CAÍDO a free: la compra exige premium, conservarla no
    A.db.session.get(A.User, UID).plan = 'free'
    A.db.session.commit()
r = c.get('/synapse/pdf/mine?lang=pt')
check('🔴 y meses después, YA SIN PREMIUM, sigue descargable — es para siempre',
      r.status_code == 200, r.status_code)
with A.app.app_context():
    A.db.session.get(A.User, UID).plan = 'premium'
    A.db.session.commit()

# otra cuenta no puede
r2 = cliente('mirona')
check('otra cuenta NO puede descargarlo (403)',
      r2.get('/synapse/pdf/mine?lang=es').status_code == 403)
check('ni comprarlo dos veces el que ya lo tiene',
      (c.post('/api/synapse/pdf/buy', json={'lang': 'es'}).get_json()
       or {}).get('error') == 'already_owned')

# ── 5 · el /app pinta el estado correcto ──────────────────────────────────
print('── 5 · el modal en /app')
c.set_cookie('scalpel_splash_ts', '1')
html = c.get('/app').get_data(as_text=True)
check('la dueña ve "Descargar tu PDF"', 'syn-pdf-mine' in html)
r2.set_cookie('scalpel_splash_ts', '1')
html2 = r2.get('/app').get_data(as_text=True)
check('quien no lo tiene ve el botón de compra', 'syn-pdf-buy' in html2)
with A.app.app_context():
    g.pop('_login_user', None)
cj = cliente('jefa')
cj.set_cookie('scalpel_splash_ts', '1')
check('el admin conserva su preview',
      'syn-pdf-download' in cj.get('/app').get_data(as_text=True))

# ── 6 · el comprador que cierra la pestaña ────────────────────────────────
print('── 6 · pagó y cerró la pestaña: el barrido lo rescata')
ESTADO['orden'] = 'PPS-2'
del avisos[:]
r = r2.post('/api/synapse/pdf/buy', json={'lang': 'pt'})
with A.app.app_context():
    o2 = A.SynapseOrder.query.filter_by(user_id=UID2).first()
    check('pedido pendiente creado', o2 is not None and o2.status == 'pending')
    barridos, rescatados = A.payments_sweep()
    o2 = A.db.session.get(A.SynapseOrder, o2.id)
    check('🔴 el barrido de /admin lo encuentra y lo entrega',
          rescatados >= 1 and o2.status == 'paid', (rescatados, o2.status))
check('y la venta rescatada también avisa',
      any('VENTA confirmada' in a for a in avisos), avisos)
check('ahora sí puede descargar',
      r2.get('/synapse/pdf/mine?lang=pt').status_code == 200)

# ── 7 · el libro de compras únicas ────────────────────────────────────────
print('── 7 · el libro en /admin')
with A.app.app_context():
    with A.app.test_request_context('/admin'):
        ctx = A._build_cosmetics_context()
    check('el PDF suma en compras únicas ($%.2f)' % ctx['cos_lifetime_total'],
          abs(ctx['cos_lifetime_total'] - 30.0) < 0.01)
    check('🔴 y lleva su total APARTE: $%.2f en %d libro(s)'
          % (ctx['spdf_lifetime_total'], ctx['spdf_lifetime_count']),
          abs(ctx['spdf_lifetime_total'] - 30.0) < 0.01
          and ctx['spdf_lifetime_count'] == 2)
    check('las filas dicen qué libro y en qué idioma',
          any('Synapse Library PDF' in ' '.join(f['piezas'])
              for f in ctx['cos_rows']))
    with A.app.test_request_context('/admin'):
        rev = A._build_revenue_context()
    check('Revenue de PLANES sigue en $%.2f' % rev['lifetime_total'],
          rev['lifetime_total'] == 0.0)

# ── 8 · un ensayo en sandbox quedaría sellado ─────────────────────────────
print('── 8 · sandbox = ensayo, nunca ingreso')
A.PAYPAL_ENV = 'sandbox'
try:
    with A.app.app_context():
        o3 = A.SynapseOrder(user_id=JEFE, lang='en', label='Synapse Library PDF (EN)',
                            price=15.0, payment_method='paypal', provider_ref='PPS-3')
        A.db.session.add(o3)
        A.db.session.commit()
        A._paypal_apply_status(o3, 'completed', 15.0, 'CAP3', 'spdf')
        check('🔴 nace sellado como ensayo', o3.is_test)
        with A.app.test_request_context('/admin'):
            ctx = A._build_cosmetics_context()
        check('y el libro no lo suma ($%.2f)' % ctx['spdf_lifetime_total'],
              abs(ctx['spdf_lifetime_total'] - 30.0) < 0.01)
finally:
    A.PAYPAL_ENV = 'live'

# ── 9 · un PDF de verdad, por la ruta real ────────────────────────────────
print('── 9 · una generación REAL por la ruta de descarga')
A._build_synapse_pdf = real_build
r = c.get('/synapse/pdf/mine?lang=es')
check('🔴 genera el PDF real (%d KB)' % (len(r.data) // 1024),
      r.status_code == 200 and r.data.startswith(b'%PDF')
      and len(r.data) > 200_000, r.status_code)

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
