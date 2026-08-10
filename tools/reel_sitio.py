# -*- coding: utf-8 -*-
"""Graba el SITIO REAL en movimiento y lo deja en vertical para Instagram.

La diferencia con `reel_order_block.py`: aquel DIBUJA una animacion desde cero;
este FILMA la aplicacion de verdad —la Camara de Tessera abriendose, con sus
paredes subiendo y la constelacion apareciendo— que es el efecto mas
cinematografico que ya tiene el producto.

Se usa la grabacion propia de Playwright (~25 fps en tiempo real) y NO capturas
sueltas: una captura tarda ~100 ms, asi que mientras se guarda, la animacion
sigue corriendo y saldrian 10 fotogramas de una animacion de 2 segundos.

    python3 tools/reel_sitio.py
"""
from __future__ import print_function

import glob
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, 'out', 'reels')
PUERTO = 5094
CL = 'Zx9!wQ4mNp2r'
# 🔑 Se filma YA EN VERTICAL. Grabar el escritorio (1280x800) y luego rellenar
# arriba y abajo deja la app como una franja en medio de dos barras negras: en
# Instagram eso se lee como un vídeo mal montado. La app es responsive, así que
# a 900x1600 se coloca sola y llena el encuadre.
ANCHO, ALTO = 900, 1600
GRAFITO = '0d0f14'


def arranca_servidor(db):
    os.environ['DATABASE_URL'] = 'sqlite:///' + db
    os.environ.setdefault('SECRET_KEY', 'reel-sitio')
    sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))
    import app as A
    with A.app.app_context():
        A.db.create_all()
        u = A.User.query.filter_by(username='camara').first()
        if u is None:
            u = A.User(username='camara', email='k@demo.invalid',
                       plan='premium', email_verified=True)
            A.db.session.add(u)
        u.set_password(CL)
        u.email_canonical = u.email
        u.plan = 'premium'
        A.db.session.commit()
    threading.Thread(target=lambda: A.app.run(port=PUERTO, threaded=True,
                                              use_reloader=False),
                     daemon=True).start()
    for _ in range(80):
        time.sleep(.25)
        try:
            urllib.request.urlopen('http://127.0.0.1:%d/health' % PUERTO,
                                   timeout=1)
            return
        except Exception:
            pass
    sys.exit('el servidor no arrancó')


def main():
    os.makedirs(SALIDA, exist_ok=True)
    tmp = tempfile.mkdtemp()
    arranca_servidor(os.path.join(tmp, 'r.db'))
    URL = 'http://127.0.0.1:%d' % PUERTO
    from playwright.sync_api import sync_playwright

    exe = (glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')
           or [None])[0]
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'],
                              **({'executable_path': exe} if exe else {}))
        # El login se hace en un contexto SIN grabar y se guarda la sesión: así
        # el vídeo empieza directamente en la app y no hay que recortar por ojo
        # el formulario de entrada.
        prev = b.new_context(viewport={'width': ANCHO, 'height': ALTO})
        pp = prev.new_page()
        pp.route('**/*', lambda r: r.continue_()
                 if '127.0.0.1' in r.request.url else r.abort())
        pp.goto(URL + '/login', wait_until='domcontentloaded')
        pp.fill('input[name=identifier]', 'camara')
        pp.fill('input[name=password]', CL)
        pp.click('button[type=submit]')
        pp.wait_for_timeout(800)
        pp.evaluate("localStorage.setItem('scalpel_lang','es')")
        sesion = prev.storage_state()
        prev.close()

        ctx = b.new_context(viewport={'width': ANCHO, 'height': ALTO},
                            storage_state=sesion,
                            record_video_dir=tmp,
                            record_video_size={'width': ANCHO, 'height': ALTO})
        pg = ctx.new_page()
        pg.route('**/*', lambda r: r.continue_()
                 if '127.0.0.1' in r.request.url else r.abort())
        # ⚠️ /app borra el cookie del splash al servirse: es de un solo uso
        pg.context.add_cookies([{'name': 'scalpel_splash_ts', 'value': '1',
                                 'url': URL + '/'}])
        pg.goto(URL + '/app', wait_until='domcontentloaded')
        pg.wait_for_timeout(2200)
        # aqui empieza lo que se quiere ver: la Camara abriendose
        pg.evaluate("document.getElementById('nx-cube').click()")
        pg.wait_for_timeout(3600)          # paredes + constelacion
        pg.evaluate("document.querySelectorAll('.nx-nd')[0].click()")
        pg.wait_for_timeout(2200)          # la sala del asistente
        ctx.close()                        # cerrar el contexto ESCRIBE el video
        b.close()

    crudo = sorted(glob.glob(os.path.join(tmp, '*.webm')))
    if not crudo:
        sys.exit('Playwright no dejó ningún vídeo')
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    dest = os.path.join(SALIDA, 'reel-camara.mp4')
    # se recorta la carga de la app y se sube a 1080x1920 (misma proporción
    # 9:16 que el encuadre grabado, así no hay barras ni deformación)
    subprocess.run([
        ff, '-y', '-loglevel', 'error', '-ss', '1.6', '-i', crudo[0],
        '-vf', 'scale=1080:1920:flags=lanczos,format=yuv420p',
        '-r', '30', '-c:v', 'libx264', '-crf', '19',
        '-movflags', '+faststart', dest], check=True)
    print('listo:', dest)
    print('tamaño: %.1f MB' % (os.path.getsize(dest) / 1e6))
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
