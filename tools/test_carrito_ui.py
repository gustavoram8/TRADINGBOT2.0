# -*- coding: utf-8 -*-
"""El carrito mezclado: dos marcos + un camo + un cursor, y quitar UNO solo.

⚠️ Este test necesita el sitio CORRIENDO en 127.0.0.1:5001 y una cuenta NO
admin llamada `compradora` — el admin posee todos los cosméticos, así que no le
salen botones de compra. Si da ERR_CONNECTION_REFUSED no es una regresión: es
que el servidor no está levantado.
"""
import time
from playwright.sync_api import sync_playwright

PASS = FAIL = 0
def check(n, c, extra=''):
    global PASS, FAIL
    ok = bool(c); PASS += ok; FAIL += (not ok)
    print('   %-5s %s %s' % ('ok' if ok else 'FALLA', n, extra if not ok else ''))

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    ctx = b.new_context(viewport={'width': 1280, 'height': 1000})
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('**/*', lambda r: r.abort() if '127.0.0.1' not in r.request.url else r.continue_())
    pg.goto('http://127.0.0.1:5001/login', wait_until='domcontentloaded')
    pg.fill('input[name=identifier]', 'compradora'); pg.fill('input[name=password]', 'Xk9!mQ2#pL5v')
    pg.click('button[type=submit]'); pg.wait_for_load_state('domcontentloaded')
    pg.goto('http://127.0.0.1:5001/cosmetics', wait_until='domcontentloaded')
    pg.evaluate("()=>{localStorage.setItem('scalpel_lang','es');sessionStorage.removeItem('nx_cosm_cart');}")
    pg.reload(wait_until='domcontentloaded'); time.sleep(2.2)

    def cuenta():
        return int(pg.inner_text('#cb-count') or 0)
    def enCarrito():
        return pg.evaluate("()=>JSON.parse(sessionStorage.getItem('nx_cosm_cart')||'[]')")

    # dos marcos
    marcos = pg.locator('.cos-cart[data-ref^="item:"]:not([data-ref^="item:cur-"])')
    marcos.nth(0).click(); time.sleep(.3)
    marcos.nth(1).click(); time.sleep(.3)
    check('dos marcos en el carrito', cuenta() == 2, cuenta())

    # ahora un camo — aqui era donde se "deseleccionaban" los marcos
    pg.locator('.camo-cart-btn[data-cart]').first.click(); time.sleep(.4)
    check('al anadir el camo siguen los tres', cuenta() == 3, enCarrito())
    dicen = pg.evaluate("""()=>[...document.querySelectorAll('.cos-cart')]
        .filter(b=>b.classList.contains('in')).length""")
    check('y los botones de los marcos siguen diciendo "En el carrito"', dicen == 2, dicen)

    # un cursor
    pg.locator('.cos-cart[data-ref^="item:cur-"]').first.click(); time.sleep(.4)
    check('cuatro cosas mezcladas', cuenta() == 4, enCarrito())

    # el detalle
    pg.click('#cb-open'); time.sleep(.5)
    filas = pg.locator('.cp-row').count()
    check('el panel lista las cuatro', filas == 4, filas)
    tipos = pg.evaluate("()=>[...document.querySelectorAll('.cp-kd')].map(e=>e.textContent.split(' · ')[0])")
    check('cada una con su tipo', set(tipos) >= {'Camo', 'Placa de foro', 'Cursor'}, tipos)
    tot_panel = pg.inner_text('#cp-total'); tot_barra = pg.inner_text('#cb-total')
    check('el total cuadra con la barra', tot_panel == tot_barra, '%s vs %s' % (tot_panel, tot_barra))

    # quitar UNO
    pg.locator('.cp-rm').nth(1).click(); time.sleep(.5)
    check('quitar uno deja tres', cuenta() == 3, enCarrito())
    check('y el panel se actualiza', pg.locator('.cp-row').count() == 3)
    dicen = pg.evaluate("""()=>[...document.querySelectorAll('.cos-cart')]
        .filter(b=>b.classList.contains('in')).length""")
    check('los botones de la pagina reflejan el cambio', dicen >= 1, dicen)

    # vaciar
    pg.click('#cp-clear'); time.sleep(.5)
    check('vaciar lo deja en cero', cuenta() == 0 and enCarrito() == [], enCarrito())
    check('y esconde la barra',
          not pg.evaluate("()=>document.getElementById('cart-bar').classList.contains('show')"))
    print('\n   errores JS:', errs or 'ninguno')
    if errs: FAIL += 1
    b.close()

print('\nRESULTADO: %d ok, %d fallas' % (PASS, FAIL))
import sys; sys.exit(1 if FAIL else 0)
