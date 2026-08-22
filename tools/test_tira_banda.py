# -*- coding: utf-8 -*-
"""La tira de botargas de la banda de `/creators`, comprobada en navegador.

    python3 tools/test_tira_banda.py     # 0 = todo bien, 1 = algo falla

Cuatro cosas, y ninguna se puede saber leyendo el CSS:

1. **Que se mueva de verdad.** Una animación mal escrita no da ningún error:
   simplemente se queda quieta. Se congela en dos instantes y se cuentan los
   píxeles que cambian.
2. **Que el bucle no salte.** El recorrido tiene que ser EXACTAMENTE el ancho
   del mosaico; si no, cada vuelta da un tirón. Se compara el fotograma de t=0
   con el de un ciclo justo: tienen que ser idénticos.
   ⚠️ La duración se LEE del elemento, no se escribe aquí. Un doble de prueba
   con el número a mano hace fallar código correcto en cuanto se retoca la
   animación — ya pasó al subir de 2,6 s a 3,4 s.
3. **Que el texto negro siga legible sobre las siluetas.** Se busca el píxel
   MÁS CLARO de la franja del texto en la captura real y se calcula el
   contraste contra la tinta. Calcularlo sobre el color teórico del azul
   mentiría: encima hay blanco al 30 %.
4. **Que no cueste fotogramas.** Es una animación de `transform` sobre un solo
   elemento, así que debería resolverla el compositor sin repintar.
   ⚠️ 16,7 ms es el TECHO de vsync: a partir de ahí todo marca igual y la
   medida no distingue diferencias pequeñas. Sirve para cazar un desastre
   (un repintado por fotograma), no para afinar.
"""
import glob, os, sys, tempfile, threading, time, urllib.request
os.environ['DATABASE_URL']='sqlite:///'+os.path.join(tempfile.mkdtemp(),'c.db')
os.environ.setdefault('SECRET_KEY','x')
RAIZ='/home/user/TRADINGBOT2.0'
sys.path.insert(0, os.path.join(RAIZ,'scalpel'))
import app as A
with A.app.app_context(): A.db.create_all()
P=5213
threading.Thread(target=lambda: A.app.run(port=P,threaded=True,use_reloader=False),daemon=True).start()
for _ in range(80):
    time.sleep(.25)
    try: urllib.request.urlopen('http://127.0.0.1:%d/health'%P,timeout=1); break
    except Exception: pass
from playwright.sync_api import sync_playwright
from PIL import Image
out='/tmp/claude-0/-home-user-TRADINGBOT2-0/76bc4b43-7526-5346-b38c-f5b6471f49f5/scratchpad'
os.makedirs(out, exist_ok=True)
exe=(glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome') or [None])[0]

def lum(c):
    def f(v):
        v/=255.0
        return v/12.92 if v<=.03928 else ((v+.055)/1.055)**2.4
    return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2])

dif=saltos=ct=0; errs=[]
with sync_playwright() as p:
    b=p.chromium.launch(args=['--no-sandbox'],**({'executable_path':exe} if exe else {}))
    ctx=b.new_context(viewport={'width':900,'height':700}, device_scale_factor=2)
    pg=ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.route('**/*', lambda r: r.abort() if 'fonts.g' in r.request.url else r.continue_())
    pg.goto('http://127.0.0.1:%d/creators'%P, wait_until='domcontentloaded')
    pg.wait_for_timeout(900)

    # ── 1 · ¿se mueve? dos fotos separadas en el tiempo, congelando la animación
    tomas=[]
    for i,t in enumerate((0.0, 1.3)):
        pg.evaluate("""t => { const e=document.querySelector('.tira');
            e.style.animationDelay = (-t)+'s'; e.style.animationPlayState='paused'; }""", t)
        pg.wait_for_timeout(150)
        f=os.path.join(out,'_tira_%d.png'%i)
        pg.locator('.banda').screenshot(path=f); tomas.append(f)
    a,bb=[Image.open(x).convert('RGB') for x in tomas]
    dif=sum(1 for pa,pb in zip(a.getdata(), bb.getdata()) if pa!=pb)
    print('MOVIMIENTO: %d px distintos entre t=0.0 y t=1.3  -> %s'
          % (dif, 'SE MUEVE' if dif>2000 else '🔴 NO SE MUEVE'))

    # ── 2 · ¿el bucle salta? t=0 y t=2.6 (un ciclo justo) deben ser IDÉNTICOS
    # ⚠️ la duración se LEE del elemento. Escribirla a mano en el test hace que
    #    el test mienta en cuanto se cambia la animación — y un doble que miente
    #    hace fallar código correcto.
    dur = pg.evaluate("() => getComputedStyle(document.querySelector('.tira')).animationDuration")
    pg.evaluate("""d => { const e=document.querySelector('.tira');
        e.style.animationDelay = '-' + d; }""", dur)
    print('            (ciclo leído del CSS: %s)' % dur)
    pg.wait_for_timeout(150)
    f2=os.path.join(out,'_tira_ciclo.png'); pg.locator('.banda').screenshot(path=f2)
    c=Image.open(f2).convert('RGB')
    saltos=sum(1 for pa,pc in zip(a.getdata(), c.getdata()) if pa!=pc)
    print('BUCLE:      %d px distintos entre t=0 y t=un ciclo -> %s'
          % (saltos, 'SIN SALTO' if saltos<400 else '🔴 SALTA'))

    # ── 3 · contraste REAL del texto negro sobre el punto más claro de la banda
    pg.evaluate("() => { const e=document.querySelector('.tira'); e.style.animationDelay='0s'; }")
    pg.wait_for_timeout(150)
    f3=os.path.join(out,'_tira_contraste.png'); pg.locator('.banda').screenshot(path=f3)
    im=Image.open(f3).convert('RGB')
    # la franja de texto: el tercio vertical central
    W,H=im.size; y0,y1=int(H*.30), int(H*.70)
    zona=[im.getpixel((x,y)) for y in range(y0,y1,2) for x in range(0,W,3)]
    claro=max(zona, key=lum)
    ct=(lum(claro)+.05)/(lum((7,8,11))+.05)
    print('CONTRASTE:  píxel más claro tras el texto = rgb%s -> %.2f:1 %s'
          % (claro, ct, 'OK (>=4.5)' if ct>=4.5 else '🔴 POR DEBAJO DE AA'))

    # ── 4 · coste por fotograma, con la tira y sin ella
    def mide():
        return pg.evaluate("""() => new Promise(res => {
            let n=0, t0=performance.now();
            function paso(){ n++; if(performance.now()-t0<1600) requestAnimationFrame(paso);
                             else res(Math.round((performance.now()-t0)/n*100)/100); }
            requestAnimationFrame(paso); })""")
    pg.evaluate("() => { const e=document.querySelector('.tira'); e.style.animationPlayState='running'; }")
    con=mide()
    pg.evaluate("() => document.querySelector('.tira').remove()")
    sin=mide()
    print('COSTE:      con la tira %.2f ms/fotograma · sin ella %.2f ms -> %+.2f ms'
          % (con, sin, con-sin))
    print('JS:', errs or 'sin errores')
    b.close()

mal = [x for x in (('movimiento', dif > 2000), ('bucle', saltos < 400),
                   ('contraste', ct >= 4.5), ('js', not errs)) if not x[1]]
print()
print('RESULTADO:', 'TODO OK' if not mal else 'FALLA -> %s' % [x[0] for x in mal])
sys.exit(1 if mal else 0)
