# -*- coding: utf-8 -*-
"""Un ensayo en el SANDBOX de cripto no puede contar como venta real."""
import os, sys
os.environ.setdefault('CRYPTO_API_BASE', 'https://api-sandbox.nowpayments.io/v1')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scalpel'))
sys.path.insert(0, 'scalpel')
import app as A

ok = fallas = 0
def check(t, c, extra=''):
    global ok, fallas
    if c: ok += 1; print('   ok    %s' % t)
    else: fallas += 1; print('   FALLA %s %s' % (t, extra))

class P:  # pedido de mentira
    def __init__(s, metodo): s.payment_method = metodo; s.is_test = False

print('── el detector de ensayos ──')
print('CRYPTO_API_BASE =', A.CRYPTO_API_BASE)
check('🔴 cripto en SANDBOX se detecta como ensayo',
      A.es_pedido_de_prueba(P('crypto')))
A.CRYPTO_API_BASE = 'https://api.nowpayments.io/v1'
check('cripto en PRODUCCIÓN es venta real',
      not A.es_pedido_de_prueba(P('crypto')))
sellado = P('crypto'); sellado.is_test = True
check('un pedido ya sellado manda sobre el entorno de hoy',
      A.es_pedido_de_prueba(sellado))
check('un pedido manual (sin método) no es ensayo',
      not A.es_pedido_de_prueba(P('')))
print('\nRESULTADO: %d ok, %d fallas' % (ok, fallas))
sys.exit(1 if fallas else 0)
