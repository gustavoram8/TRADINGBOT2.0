# -*- coding: utf-8 -*-
"""Banco de pruebas de marcos de avatar.

Renderiza cada marco en los DOS tamaños en que va a existir de verdad —
40px (fila del foro, junto a la medalla del rango) y 96px (tabla de la
temporada / panel) — en tema claro y oscuro, y saca una captura.

    python3 tools/frames_preview.py <slug>      # uno
    python3 tools/frames_preview.py             # todos

Existe porque un marco no se puede juzgar en el editor: lo que decide si
sirve es si se distingue A 40px, que es donde lo va a ver el 95% de la gente.
"""
import os
import subprocess
import sys
import tempfile

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
OUT = os.environ.get('FRAMES_OUT', '/tmp/frames_preview.png')

# ── Los marcos. Cada uno: css (las reglas del anillo) y una nota de diseño. ──
FRAMES = {
    'steel-bezel': {
        'name': 'Steel Bezel',
        'note': 'Bisel de acero mecanizado con muescas, como el aro de un '
                'instrumento. Silueta: dentada. Material: acero cepillado.',
        'css': """
.fr-steel-bezel { padding: calc(var(--w) * 1.15); }
.fr-steel-bezel::before {
  content:''; position:absolute; inset:0; border-radius:50%;
  /* 24 facetas anchas: a 96px se leen como un bisel torneado, y a 40px se
     funden en un anillo de acero limpio en vez de hacer moaré. */
  background:
    conic-gradient(from 0deg,
      rgba(255,255,255,.34) 0deg 7.5deg, rgba(0,0,0,.30) 7.5deg 15deg),
    conic-gradient(from 208deg, #5d6673, #d9e0ea 22%, #79838f 47%,
                   #f0f4f9 68%, #6c7684 86%, #5d6673);
  background-blend-mode: soft-light, normal;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.45),
              0 1px 3px rgba(8,12,18,.45);
}
.fr-steel-bezel::after {
  content:''; position:absolute; border-radius:50%;
  inset: calc(var(--w) * 0.78);
  background: radial-gradient(circle at 34% 24%, rgba(255,255,255,.42), transparent 58%);
  box-shadow: inset 0 0 0 1.5px rgba(12,16,24,.6);
}
""",
    },
}


PAGE = """<!doctype html><meta charset="utf-8">
<style>
  body { margin:0; font-family:'Inter',system-ui,sans-serif; }
  .pane { padding:26px 30px; }
  .pane.light { background:#f4f6fa; color:#15171f; }
  .pane.dark  { background:#0d1016; color:#e7ebf2; }
  .row { display:flex; align-items:center; gap:34px; margin-bottom:22px; }
  .lbl { font-size:11px; font-weight:800; letter-spacing:.1em; text-transform:uppercase;
         opacity:.55; width:150px; }
  .name { font-size:15px; font-weight:800; }
  .note { font-size:12px; opacity:.6; max-width:520px; line-height:1.5; }

  /* El avatar tal cual existe hoy en el foro */
  .av { border-radius:50%; display:grid; place-items:center; color:#fff;
        font-weight:800; text-transform:uppercase; flex:0 0 auto;
        background:linear-gradient(135deg,#2563eb,#1e40af); }

  /* El marco envuelve al avatar. --w = grosor del anillo. */
  .fr { position:relative; border-radius:50%; display:grid; place-items:center;
        flex:0 0 auto; }
  .fr > .av { position:relative; z-index:2; }
  .fr::before, .fr::after { pointer-events:none; z-index:1; }

  .sz-forum { --w:3px; }
  .sz-forum > .av { width:40px; height:40px; font-size:16px; }
  .sz-big { --w:7px; }
  .sz-big > .av { width:96px; height:96px; font-size:38px; }

  /* contexto real de la fila del foro */
  .forumrow { display:flex; align-items:center; gap:8px; font-size:13.5px; font-weight:700; }
  .medal { width:18px; height:18px; border-radius:4px;
           background:linear-gradient(135deg,#f3c768,#a87f1f); }
  .rankpill { font-size:9px; font-weight:600; padding:2px 5px; border-radius:3px;
              border:1px solid rgba(160,140,80,.5); color:#a88a3e; }
__FRAMECSS__
</style>
__BODY__
"""


def build_html(slugs):
    css = ''.join(FRAMES[s]['css'] for s in slugs)
    body = []
    for theme in ('light', 'dark'):
        body.append('<div class="pane %s">' % theme)
        for s in slugs:
            f = FRAMES[s]
            body.append(
                '<div class="row">'
                '<div class="lbl">%s</div>'
                '<div class="fr sz-forum fr-%s"><div class="av">M</div></div>'
                '<div class="forumrow">'
                '<div class="fr sz-forum fr-%s"><div class="av">M</div></div>'
                '<span class="medal"></span><span>marcus_dw</span>'
                '<span class="rankpill">Trading Legend</span></div>'
                '<div class="fr sz-big fr-%s"><div class="av">M</div></div>'
                '<div><div class="name">%s</div><div class="note">%s</div></div>'
                '</div>' % (theme, s, s, s, f['name'], f['note']))
        body.append('</div>')
    return PAGE.replace('__FRAMECSS__', css).replace('__BODY__', '\n'.join(body))


def shoot(slugs):
    html = build_html(slugs)
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False) as fh:
        fh.write(html)
        path = fh.name
    script = f'''
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path={CHROME!r})
    pg = b.new_page(viewport={{'width': 1080, 'height': 400}}, device_scale_factor=2)
    pg.goto('file://{path}')
    pg.wait_for_timeout(500)
    pg.screenshot(path={OUT!r}, full_page=True)
    b.close()
'''
    subprocess.run([sys.executable, '-c', script], check=True)
    os.unlink(path)
    print('captura →', OUT)


if __name__ == '__main__':
    pedidos = sys.argv[1:] or list(FRAMES)
    faltan = [s for s in pedidos if s not in FRAMES]
    if faltan:
        print('no existen:', faltan, '\ndisponibles:', list(FRAMES))
        sys.exit(1)
    shoot(pedidos)
