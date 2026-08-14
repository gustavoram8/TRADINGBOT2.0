# -*- coding: utf-8 -*-
"""¿Se pisan la botarga y el texto en la bienvenida del Quiz? Medido."""
import os, socket, subprocess, sys, tempfile, time, re

RAIZ = '/home/user/TRADINGBOT2.0'
TMP = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
from playwright.sync_api import sync_playwright

s = socket.socket(); s.bind(('127.0.0.1', 0)); PORT = s.getsockname()[1]; s.close()
env = {**os.environ, 'DATABASE_URL': 'sqlite:///' + TMP + '/q.db',
       'SECRET_KEY': 'quiz'}
for k in ('PUBLIC_HTTPS', 'PREVIEW_USERS', 'SITE_URL'):
    env.pop(k, None)

CAMO = sys.argv[1] if len(sys.argv) > 1 else None
siembra = '''
import sys; sys.path.insert(0,"scalpel"); import app as A
from datetime import datetime, timedelta, timezone
with A.app.app_context():
    A.db.create_all()
    u = A.User.query.filter_by(username="q").first()
    if not u:
        u = A.User(username="q", email="q@t.invalid", email_verified=True)
        u.set_password("Zx9!wQ4mNp2r"); u.email_canonical=u.email
        A.db.session.add(u)
    u.plan="premium"
    u.plan_expires_at = datetime.now(timezone.utc)+timedelta(days=30)
    u.active_camo = %r
    if %r: u.owned_camos = %r
    A.db.session.commit()
print("OK")
''' % (CAMO, CAMO, CAMO)
r = subprocess.run([sys.executable, '-c', siembra], capture_output=True,
                   text=True, cwd=RAIZ, env=env)
if 'OK' not in r.stdout:
    sys.exit(r.stderr[-600:])

srv = subprocess.Popen([sys.executable, '-c',
    'import sys; sys.path.insert(0,"scalpel"); import app as A;'
    'A.app.run(host="127.0.0.1", port=%d, threaded=True)' % PORT],
    cwd=RAIZ, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = 'http://127.0.0.1:%d' % PORT
for _ in range(60):
    try:
        socket.create_connection(('127.0.0.1', PORT), .3).close(); break
    except OSError: time.sleep(.4)

JS = """() => {
  const lg = document.querySelector('.quiz-welcome-logo');
  const ct = document.querySelector('.qw-content');
  if (!lg || !ct) return {falta:true};
  const a = lg.getBoundingClientRect(), b = ct.getBoundingClientRect();
  const solapeX = Math.min(a.right,b.right) - Math.max(a.left,b.left);
  const solapeY = Math.min(a.bottom,b.bottom) - Math.max(a.top,b.top);
  const cs = getComputedStyle(lg);
  // ¿y contra los BOTONES de intención, que es lo que el dueño ve pisado?
  let peor = 0, quien = '';
  document.querySelectorAll('.quiz-welcome-opt, .quiz-welcome-q, .quiz-welcome-title')
    .forEach(e => {
      const r = e.getBoundingClientRect();
      const sx = Math.min(a.right,r.right) - Math.max(a.left,r.left);
      const sy = Math.min(a.bottom,r.bottom) - Math.max(a.top,r.top);
      if (sx > 0 && sy > 0 && sx*sy > peor) {
        peor = sx*sy; quien = (e.textContent||'').trim().slice(0,34);
      }
    });
  return {pos:cs.position, tr:cs.transform.slice(0,28), h:Math.round(a.height),
          w:Math.round(a.width), logo:[Math.round(a.left),Math.round(a.right)],
          txt:[Math.round(b.left),Math.round(b.right)],
          solapeCaja: (solapeX>0&&solapeY>0) ? Math.round(solapeX) : 0,
          peorTxt: Math.round(Math.sqrt(peor)), quien};
}"""

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    for w, h, etq in [(768,1024,'iPad mini vert'), (834,1112,'iPad Air vert'),
                      (1024,1366,'iPad Pro vert'), (1180,820,'iPad apaisado'),
                      (1366,1024,'iPad Pro apaisado'), (1600,900,'escritorio')]:
        ctx = nav.new_context(viewport={'width':w,'height':h},
            has_touch=True, is_mobile=False)
        ctx.route(re.compile(r'^https?://(?!127\.0\.0\.1)'), lambda r: r.abort())
        pg = ctx.new_page()
        pg.goto(base+'/login', wait_until='domcontentloaded')
        pg.fill('input[name=identifier]','q'); pg.fill('input[name=password]','Zx9!wQ4mNp2r')
        pg.click('button[type=submit]'); pg.wait_for_timeout(600)
        ctx.add_cookies([{'name':'scalpel_splash_ts','value':'1','url':base}])
        pg.goto(base+'/app', wait_until='domcontentloaded'); pg.wait_for_timeout(800)
        b = pg.query_selector('[data-tab="quiz"]')
        if b: b.click(); pg.wait_for_timeout(900)
        m = pg.evaluate(JS)
        if m.get('falta'):
            print('  %-20s (no hay bienvenida)' % etq); ctx.close(); continue
        mal = m['peorTxt'] > 0
        print('  %s %-18s logo[%4d..%4d] %3dx%3d  texto[%4d..%4d]  pos=%-8s %s'
              % ('❌' if mal else '✅', etq, m['logo'][0], m['logo'][1],
                 m['w'], m['h'], m['txt'][0], m['txt'][1], m['pos'],
                 ('PISA «%s»' % m['quien']) if mal else ''))
        ctx.close()
    nav.close()
srv.terminate()
