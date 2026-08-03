# -*- coding: utf-8 -*-
"""El configurador NO debe escribir nada si PayPal rechaza el par, y debe
conservar las variables que ya hubiera en supervisor."""
import importlib.util, os, sys, tempfile, shutil

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('   %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

tmp = tempfile.mkdtemp()
conf = os.path.join(tmp, 'trader.conf')
LINEA_VIEJA = ('environment=DATABASE_URL="postgresql://u:p@localhost/db",'
               'SECRET_KEY="abc",OPENAI_API_KEY="sk-viejo",MAIL_APP_PASSWORD="a,b"')
open(conf, 'w').write('[program:traderacelerator]\ncommand=/x/gunicorn\n%s\nautostart=true\n' % LINEA_VIEJA)

spec = importlib.util.spec_from_file_location('sp', '/home/user/TRADINGBOT2.0/tools/set_paypal.py')
sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
sp.ENV = os.path.join(tmp, '.env')
open(sp.ENV, 'w').write('SECRET_KEY=abc\nPAYPAL_ENV=live\n')
import glob as _g
sp.glob.glob = lambda pat: [conf] if 'trader' in pat else []

print('── Parte la línea de supervisor sin romper nada')
d = sp._partir_environment(LINEA_VIEJA)
check('conserva las 4 variables', len(d) == 4, d)
check('y no parte la que lleva una coma dentro', d.get('MAIL_APP_PASSWORD') == 'a,b',
      d.get('MAIL_APP_PASSWORD'))

print('\n── Si PayPal rechaza, NO escribe nada')
antes_env = open(sp.ENV).read(); antes_conf = open(conf).read()
sp.token = lambda base, cid, sec: (False, 'HTTP 401 invalid_client')
sp.input = lambda p='': 'ID-MALO'
sp.getpass.getpass = lambda p='': 'SECRETO-MALO'
r = sp.main()
check('sale con error', r == 1, r)
check('el .env quedó intacto', open(sp.ENV).read() == antes_env)
check('y el conf de supervisor también', open(conf).read() == antes_conf)

print('\n── Con un par válido, escribe en los dos sitios')
sp.token = lambda base, cid, sec: (True, 'ok') if 'sandbox' not in base else (False, 'HTTP 401')
sp.input = lambda p='': 'ID-BUENO'
sp.getpass.getpass = lambda p='': 'SECRETO-BUENO'
r = sp.main()
check('sale bien', r == 0, r)
env = open(sp.ENV).read()
check('el .env trae el Client ID', 'PAYPAL_CLIENT_ID=ID-BUENO' in env)
check('y el Secret', 'PAYPAL_SECRET=SECRETO-BUENO' in env)
check('sin duplicar PAYPAL_ENV', env.count('PAYPAL_ENV=') == 1, env)
check('y detecta que son de live', 'PAYPAL_ENV=live' in env)
check('el .env queda solo legible por root', oct(os.stat(sp.ENV).st_mode)[-3:] == '600',
      oct(os.stat(sp.ENV).st_mode)[-3:])
c = open(conf).read()
check('supervisor conserva la base de datos', 'DATABASE_URL="postgresql://u:p@localhost/db"' in c)
check('conserva la clave de OpenAI', 'OPENAI_API_KEY="sk-viejo"' in c)
check('conserva la contraseña con coma', 'MAIL_APP_PASSWORD="a,b"' in c)
check('y añade las de PayPal', 'PAYPAL_CLIENT_ID="ID-BUENO"' in c and 'PAYPAL_SECRET="SECRETO-BUENO"' in c)
check('en UNA sola línea', len([l for l in c.splitlines() if l.startswith('environment=')]) == 1)
check('dejó copia de seguridad', len(_g.glob(conf + '.bak-*')) == 1)

print('\n── Un valor con espacio (pegado a medias) se rechaza')
sp.input = lambda p='': 'ID CON ESPACIO'
r = sp.main()
check('no lo acepta', r == 1, r)

shutil.rmtree(tmp)
print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
