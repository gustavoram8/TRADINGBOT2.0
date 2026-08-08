# -*- coding: utf-8 -*-
"""El carrito nombra la MISMA red en la que se va a cobrar.

Lo cazó el dueño mirando su propio carrito: decía "red TRC-20 o ERC-20"
mientras las facturas se emiten SOLO en TRON. Un comprador que leyera eso y
enviara USDT por Ethereum a una dirección TRON perdería el dinero de forma
irreversible — es el único error de todo el circuito que no tiene arreglo.

La causa era que el texto estaba escrito a mano en la plantilla, sin relación
con `CRYPTO_PAY_CURRENCY`. Ahora se deriva de ella, así que no puede volver a
contradecirla.
"""
import importlib
import os
import sys

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scalpel')
ok = fallas = 0


def check(t, c, extra=''):
    global ok, fallas
    if c:
        ok += 1
        print('   ok    %s' % t)
    else:
        fallas += 1
        print('   FALLA %s %s' % (t, extra))


def cargar(moneda):
    """Arranca la app con esa moneda configurada."""
    for m in [m for m in sys.modules if m == 'app']:
        del sys.modules[m]
    os.environ['DATABASE_URL'] = 'sqlite://'
    os.environ['CRYPTO_API_KEY'] = 'x'
    os.environ['CRYPTO_PAY_CURRENCY'] = moneda
    sys.path.insert(0, RUTA)
    import app as A
    importlib.reload(A) if 'app' in sys.modules else None
    return A


print('── con la configuración real (USDT sobre TRON) ──')
A = cargar('usdttrc20')
check('la etiqueta de red dice TRON', A.CRYPTO_NET_LABEL == 'TRON (TRC-20)',
      A.CRYPTO_NET_LABEL)
check('🔴 y NO nombra Ethereum por ningún lado',
      'ERC' not in A.CRYPTO_NET_LABEL)
check('la moneda que se cobra es la misma que se anuncia',
      A.CRYPTO_PAY_CURRENCY == 'usdttrc20')

with A.app.app_context():
    A.db.create_all()
    u = A.User(username='comprador', email='c@demo.invalid', plan='free',
               email_verified=True)
    u.set_password('Zx9!wQ4mNp2r')
    A.db.session.add(u)
    A.db.session.commit()

c = A.app.test_client()
c.post('/login', data={'identifier': 'comprador', 'password': 'Zx9!wQ4mNp2r'})
html = c.get('/checkout?plan=standard&cycle=monthly').get_data(as_text=True)
check('el carrito imprime la red correcta', 'TRON (TRC-20)' in html)
check('🔴 el carrito YA NO ofrece ERC-20', 'ERC-20' not in html,
      [l for l in html.splitlines() if 'ERC-20' in l][:1])
check('y viaja como variable para las traducciones',
      'data-i18n-vars' in html and '"net"' in html)

print('── los textos traducidos usan la variable, no un nombre fijo ──')
js = open(os.path.join(RUTA, 'static', 'pages_i18n.js'), encoding='utf-8').read()
lineas = [l for l in js.splitlines() if 'cpay.cryptoShort' in l]
check('están los 4 idiomas', len(lineas) == 4, len(lineas))
check('🔴 ninguno menciona ERC-20 ni TRC-20 a mano',
      not any('ERC-20' in l or 'TRC-20' in l for l in lineas), lineas)
check('los 4 llevan el hueco {net}',
      all('{net}' in l for l in lineas))
check('los 4 avisan de que otra red pierde el dinero',
      all(any(p in l.lower() for p in ('loses the funds', 'pierde el dinero',
                                       'perd les fonds', 'perde o dinheiro'))
          for l in lineas))

print('── si algún día se cambia la moneda, el texto la sigue ──')
B = cargar('usdterc20')
check('con USDT sobre Ethereum, la etiqueta cambia sola',
      B.CRYPTO_NET_LABEL == 'Ethereum (ERC-20)', B.CRYPTO_NET_LABEL)
C = cargar('usdtbsc')
check('y con BNB Smart Chain también',
      C.CRYPTO_NET_LABEL == 'BNB Smart Chain (BEP-20)', C.CRYPTO_NET_LABEL)

print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
