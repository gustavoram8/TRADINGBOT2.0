"""Render each ready camo's SKIN — the camo background alone, no app UI.

Captured at 2:1 because the card swatch is 2:1: most camos put their art in a
corner, and a squarer capture would crop it away.

⚠️ Two traps, both learned the hard way:

1. Tessera re-asserts its own element.style on a rAF loop, so hiding it with
   display/visibility does not stick — the little red cube ends up baked into
   every skin. The UI has to be REMOVED from the DOM, not hidden.

2. The camo art lives in body::before/::after at z-index -2/-1, and Chromium
   paints them or not at random once the page is stripped: computed styles and
   the class are correct either way, and a blank page screenshots perfectly
   happily. Same family of compositing quirk as the Tessera cube. Copying the
   backgrounds onto real divs is deterministic but distorts multi-layer
   backgrounds (rising-sun came out flat red), so instead we keep the real
   pseudo-elements and RETRY until the render verifies. Roughly half the
   attempts land, so a handful of tries is plenty.

Nothing is written unverified: a white rectangle in the store is worse than no
image at all.
"""
import io, sys
from PIL import Image, ImageStat
from playwright.sync_api import sync_playwright

W, H, OUT_W, MIN_STDDEV, TRIES = 1280, 640, 900, 3.5, 8
CAMOS = [
    ('rising-sun', '',     'light'),
    ('blackflag',  '',     'light'),
    ('premium',    '',     ''),
    ('naval',      '',     ''),
    ('fourth',     '',     ''),
    ('pole',       '',     ''),   ('pole',     '_alt', 'light'),
    ('mission',    '',     ''),   ('mission',  '_alt', 'light'),
    ('standard',   '',     ''),   ('standard', '_alt', 'light'),
    ('chronicles', '',     ''),
]

STRIP = "()=>{ while (document.body.firstChild) document.body.removeChild(document.body.firstChild); }"
DECODE = """async () => {
  const urls = new Set();
  for (const pe of ['::before', '::after'])
    for (const m of (getComputedStyle(document.body, pe).backgroundImage || '')
                    .matchAll(/url\\((["']?)(.*?)\\1\\)/g)) urls.add(m[2]);
  await Promise.all([...urls].map(u => { const im = new Image(); im.src = u;
                                         return im.decode().catch(() => {}); }));
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
}"""

bad = []
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    ctx = b.new_context(viewport={'width': W, 'height': H}, device_scale_factor=1)
    p = ctx.new_page()
    p.goto('http://127.0.0.1:5001/login')
    p.fill('input[name="identifier"]', 'helptest')
    p.fill('input[name="password"]', 'Testing123!')
    p.click('button[type="submit"]'); p.wait_for_load_state('networkidle')
    for slug, suffix, extra in CAMOS:
        name, sd = 'camo_skin_%s%s.jpg' % (slug, suffix), 0
        for attempt in range(1, TRIES + 1):
            p.goto('http://127.0.0.1:5001/app', wait_until='networkidle')
            p.wait_for_timeout(500)
            p.evaluate(STRIP)
            p.evaluate("(c)=>{document.body.className=c;}", ('camo-%s %s' % (slug, extra)).strip())
            p.evaluate(DECODE)
            p.wait_for_timeout(600)
            im = Image.open(io.BytesIO(p.screenshot(type='png'))).convert('RGB')
            sd = max(ImageStat.Stat(im.convert('L')).stddev)
            if sd >= MIN_STDDEV:
                im.resize((OUT_W, OUT_W * H // W), Image.LANCZOS).save(
                    'scalpel/static/' + name, 'JPEG', quality=86, optimize=True)
                print('  ok        %-28s stddev=%5.1f intentos=%d' % (name, sd, attempt), flush=True)
                break
        else:
            bad.append((name, round(sd, 1)))
            print('  EN BLANCO %-28s stddev=%.1f' % (name, sd), flush=True)
    ctx.close(); b.close()
print('FALLIDAS:', bad or 'ninguna')
sys.exit(1 if bad else 0)
