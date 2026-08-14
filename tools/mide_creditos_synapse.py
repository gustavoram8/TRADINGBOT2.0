import os, socket, subprocess, sys, tempfile, time, re
RAIZ='/home/user/TRADINGBOT2.0'; TMP=tempfile.mkdtemp()
from playwright.sync_api import sync_playwright
s=socket.socket(); s.bind(('127.0.0.1',0)); PORT=s.getsockname()[1]; s.close()
env={**os.environ,'DATABASE_URL':'sqlite:///'+TMP+'/c.db','SECRET_KEY':'cr'}
for k in ('PUBLIC_HTTPS','PREVIEW_USERS','SITE_URL'): env.pop(k,None)
sb='''
import sys; sys.path.insert(0,"scalpel"); import app as A
from datetime import datetime, timedelta, timezone
with A.app.app_context():
    A.db.create_all()
    u=A.User.query.filter_by(username="c").first()
    if not u:
        u=A.User(username="c",email="c@t.invalid",email_verified=True)
        u.set_password("Zx9!wQ4mNp2r"); u.email_canonical=u.email; A.db.session.add(u)
    u.plan="premium"; u.plan_expires_at=datetime.now(timezone.utc)+timedelta(days=30)
    A.db.session.commit()
print("OK")'''
r=subprocess.run([sys.executable,'-c',sb],capture_output=True,text=True,cwd=RAIZ,env=env)
if 'OK' not in r.stdout: sys.exit(r.stderr[-500:])
srv=subprocess.Popen([sys.executable,'-c','import sys; sys.path.insert(0,"scalpel"); import app as A; A.app.run(host="127.0.0.1",port=%d,threaded=True)'%PORT],
    cwd=RAIZ,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
base='http://127.0.0.1:%d'%PORT
for _ in range(60):
    try: socket.create_connection(('127.0.0.1',PORT),.3).close(); break
    except OSError: time.sleep(.4)
JS="""() => {
  const c = document.querySelector('.syn-credit');
  if (!c) return {falta:true};
  const r = c.getBoundingClientRect(); const cs = getComputedStyle(c);
  // ¿algún ancestro tiene transform/filter? eso rompe position:fixed
  let culpable = '', n = c.parentElement;
  while (n && n !== document.body) {
    const s = getComputedStyle(n);
    if (s.transform !== 'none' || s.filter !== 'none' ||
        s.backdropFilter !== 'none' || s.willChange !== 'auto' ||
        s.perspective !== 'none' || s.contain.includes('paint')) {
      culpable = (n.id||n.className||n.tagName) + ' →' +
        (s.transform!=='none'?' transform':'') + (s.filter!=='none'?' filter':'') +
        (s.backdropFilter!=='none'?' backdrop':'') +
        (s.willChange!=='auto'?' will-change':'') +
        (s.perspective!=='none'?' perspective':'') +
        (s.contain.includes('paint')?' contain':'');
      break;
    }
    n = n.parentElement;
  }
  return {pos:cs.position, top:Math.round(r.top), bottom:Math.round(r.bottom),
          vh:window.innerHeight, visible: r.bottom>0 && r.top<window.innerHeight,
          culpable};
}"""
with sync_playwright() as pw:
    nav=pw.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    for w,h,e in [(393,852,'iPhone'),(768,1024,'iPad mini'),(1024,1366,'iPad Pro v'),(1366,1024,'iPad Pro ap'),(1600,900,'escritorio')]:
        ctx=nav.new_context(viewport={'width':w,'height':h}, has_touch=(w<1500))
        ctx.route(re.compile(r'^https?://(?!127\.0\.0\.1)'),lambda r:r.abort())
        pg=ctx.new_page()
        pg.goto(base+'/login',wait_until='domcontentloaded')
        pg.fill('input[name=identifier]','c'); pg.fill('input[name=password]','Zx9!wQ4mNp2r')
        pg.click('button[type=submit]'); pg.wait_for_timeout(600)
        ctx.add_cookies([{'name':'scalpel_splash_ts','value':'1','url':base}])
        pg.goto(base+'/app',wait_until='domcontentloaded'); pg.wait_for_timeout(800)
        b=pg.query_selector('[data-tab="synapse"]')
        if b: b.click(); pg.wait_for_timeout(1500)
        m=pg.evaluate(JS)
        if m.get('falta'): print('  %-12s (sin crédito en el DOM)'%e); ctx.close(); continue
        print('  %s %-12s pos=%-8s top=%5d bottom=%5d vh=%4d %s'
              %('✅' if m['visible'] else '❌', e, m['pos'], m['top'], m['bottom'],
                m['vh'], ('CULPABLE: '+m['culpable']) if m['culpable'] else ''))
        ctx.close()
    nav.close()
srv.terminate()
