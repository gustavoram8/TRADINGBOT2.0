# -*- coding: utf-8 -*-
"""Prueba el tool del webhook con un PayPal de mentira."""
import importlib.util, io, json, os, sys, tempfile
RAIZ='/home/user/TRADINGBOT2.0'
ok=fallos=0
def check(c,t):
    global ok,fallos
    if c: ok+=1; print('  ok   ',t)
    else: fallos+=1; print('  FALLA',t)

def cargar():
    for m in [m for m in list(sys.modules) if m=='wh']: del sys.modules[m]
    spec=importlib.util.spec_from_file_location('wh', os.path.join(RAIZ,'tools','paypal_setup_webhook.py'))
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

LLAMADAS=[]
def falso_api(base, tk, method, path, payload=None):
    LLAMADAS.append((method,path,payload))
    if path=='/v1/notifications/webhooks' and method=='GET':
        return 200, {'webhooks': ESTADO['existentes']}
    if path=='/v1/notifications/webhooks' and method=='POST':
        return 201, {'id':'WH-NUEVO-1'}
    if method=='PATCH':
        return 200, {}
    return 200, {}
ESTADO={'existentes':[]}

wh=cargar()
wh.token=lambda base,cid,secret:'tk'
wh.api=falso_api
wh.leer_env=lambda: {'PAYPAL_CLIENT_ID':'c','PAYPAL_SECRET':'s',
                     'PAYPAL_ENV':'sandbox','SITE_URL':'https://tradeable.academy'}
wh.ENV='/tmp/whtest/.env'
# que no intente escribir en supervisor
import types

print('── 1 · no existe ninguno: lo crea con los 15 eventos')
LLAMADAS[:]=[]; ESTADO['existentes']=[]
try: wh.main([])
except SystemExit: pass
creacion=[c for c in LLAMADAS if c[0]=='POST']
check(len(creacion)==1,'se crea UNO')
evs=[e['name'] for e in creacion[0][2]['event_types']]
check(len(evs)==15,'lleva 15 eventos (%d)'%len(evs))
check('PAYMENT.SALE.COMPLETED' in evs,'incluye PAYMENT.SALE.COMPLETED (el de las renovaciones)')
check('BILLING.SUBSCRIPTION.PAYMENT.FAILED' in evs,'incluye el de cobro rechazado')
check(creacion[0][2]['url']=='https://tradeable.academy/webhook/paypal','la URL es la correcta')

print('── 2 · ya existe y esta completo: NO crea otro')
LLAMADAS[:]=[]
ESTADO['existentes']=[{'id':'WH-VIEJO','url':'https://tradeable.academy/webhook/paypal',
                       'event_types':[{'name':e} for e in wh.EVENTOS]}]
try: wh.main([])
except SystemExit: pass
check(not [c for c in LLAMADAS if c[0]=='POST'],'no crea duplicado')
check(not [c for c in LLAMADAS if c[0]=='PATCH'],'no toca nada si esta completo')

print('── 3 · existe pero le faltan eventos: los repara')
LLAMADAS[:]=[]
ESTADO['existentes']=[{'id':'WH-VIEJO','url':'https://tradeable.academy/webhook/paypal',
                       'event_types':[{'name':'PAYMENT.CAPTURE.COMPLETED'}]}]
try: wh.main([])
except SystemExit: pass
parches=[c for c in LLAMADAS if c[0]=='PATCH']
check(len(parches)==1,'lo repara con un PATCH')
check(len(parches[0][2][0]['value'])==15,'lo deja con los 15')
check(not [c for c in LLAMADAS if c[0]=='POST'],'y sigue sin duplicar')

print('── 4 · sin SITE_URL con https: se niega en vez de crear una URL rota')
wh2=cargar(); wh2.token=lambda *a:'tk'; wh2.api=falso_api
wh2.leer_env=lambda: {'PAYPAL_CLIENT_ID':'c','PAYPAL_SECRET':'s','PAYPAL_ENV':'sandbox','SITE_URL':''}
try:
    wh2.main([]); check(False,'deberia haber parado')
except SystemExit as e:
    check('HTTPS' in str(e),'para y explica que falta la direccion con HTTPS')

print('── 5 · sin credenciales: manda a set_paypal.py')
wh3=cargar(); wh3.leer_env=lambda: {}
try:
    wh3.main([]); check(False,'deberia haber parado')
except SystemExit as e:
    check('set_paypal' in str(e),'manda a correr set_paypal.py primero')

print('\nRESULTADO: %d/%d'%(ok,ok+fallos))
sys.exit(0 if fallos==0 else 1)
