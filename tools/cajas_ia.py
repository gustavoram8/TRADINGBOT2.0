# -*- coding: utf-8 -*-
"""¿Sabe un modelo LOCALIZAR las velas de un gráfico, con coordenadas?

    python3 tools/cajas_ia.py --imagen docs/capturas_prueba/mes_5m.png \\
        --modelo gemini:gemini-3-pro

🔴 NO TOCA EL ANALIZADOR. Vive en tools/, nadie lo importa.

═══ QUÉ PREGUNTA, Y POR QUÉ NO ES LO MISMO QUE YA PROBAMOS ═══
Las pruebas anteriores (`agudeza_visual.py`) le pedían a GPT-4o un JUICIO:
"¿se cruzan?", "¿está por debajo de 30?". Salió en azar, y cuando se le pidió
la posición de una línea falló por 93 px de media.

Esto pregunta otra cosa: **"dime dónde está cada vela, con sus coordenadas"**.
Es la función de *grounding* que algunos modelos traen entrenada a propósito
—la misma familia de tarea que usan los detectores de objetos— y GPT-4o no
tiene. Si un modelo devuelve cajas correctas, la comparación deja de ser suya:
la hace el código, exacta. "El cuerpo termina en y=240 y el nivel está en
y=247" no admite interpretación.

⚠️ Un mal resultado aquí descarta ESTE ATAJO, no la idea. Un detector entrenado
   (YOLO y familia) es otra tecnología y habría que medirlo aparte.

🔴 SE CORRE EN EL VPS: este contenedor tiene bloqueado el proxy hacia
   generativelanguage.googleapis.com. La clave se lee del entorno, de
   `scalpel/.env` o del `environment=` de supervisor — nunca se escribe aquí.

Salida: un PNG con las cajas dibujadas encima. Se mira y se juzga a ojo, que
para esto es el criterio correcto: o están sobre las velas, o no lo están.
"""
from __future__ import print_function

import argparse
import base64
import io
import json
import os
import re
import sys
import time

from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

def _pide(n):
    """El encargo. 🔴 Se PIDEN POCAS VELAS a propósito.

    Pedir las ~120 del gráfico hacía que el modelo escribiera durante más de
    cinco minutos y la petición se agotara por tiempo. Y no hace falta: la
    pregunta del experimento es *si sabe localizar una vela*, y eso se responde
    igual de bien con 25 que con 120. Menos salida = respuesta en segundos y
    sin truncarse."""
    return (
        'Esta imagen es un gráfico de trading de velas japonesas. '
        'Detecta ÚNICAMENTE las %d velas que están MÁS A LA DERECHA del '
        'gráfico (cada barra de precio individual: su cuerpo rectangular junto '
        'con su mecha). NO detectes las líneas horizontales, ni las zonas de '
        'color de fondo, ni el panel de precios de la derecha, ni los textos.\n'
        'Devuelve SOLO un array JSON, sin nada más. Cada elemento: '
        '{"box_2d": [ymin, xmin, ymax, xmax], "label": "vela"} '
        'con las coordenadas normalizadas de 0 a 1000.' % n)


def _clave(prov):
    """Reutiliza el buscador de claves de agudeza_visual: entorno → .env →
    línea `environment=` del conf de supervisor (donde vive en producción)."""
    import importlib.util
    ruta = os.path.join(RAIZ, 'tools', 'agudeza_visual.py')
    spec = importlib.util.spec_from_file_location('ag', ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._clave(prov)


def _pregunta(prov, modelo, clave, ruta, velas=25, tope=8000):
    """Una pregunta con imagen, reintentando lo que es temporal.

    🔴 Los 429 (cuota) y los 503 (servidor saturado) NO son fallos del modelo:
    son ruido de la infraestructura. Sin reintento, la prueba muere en el primer
    intento y uno concluye que el modelo no sirve — que es justo la conclusión
    equivocada. En la capa gratuita de Google los dos aparecen a menudo.

    ⚠️ Y cuando de verdad falla, se imprime el CUERPO del error: el mensaje de
    Google dice el motivo exacto (modelo retirado, cuota agotada, clave mala) y
    sin él uno se queda adivinando con un número de tres cifras."""
    import requests
    b64 = base64.b64encode(open(ruta, 'rb').read()).decode('ascii')
    if prov == 'gemini':
        url = ('https://generativelanguage.googleapis.com/v1beta/openai/'
               'chat/completions')
    elif prov == 'openai':
        url = 'https://api.openai.com/v1/chat/completions'
    else:
        raise SystemExit('proveedor no soportado aquí: %s' % prov)
    cuerpo = {
        'model': modelo, 'max_completion_tokens': tope,
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': _pide(velas)},
            {'type': 'image_url',
             'image_url': {'url': 'data:image/png;base64,' + b64,
                           'detail': 'high'}}]}]}
    cab = {'Authorization': 'Bearer ' + clave}
    espera = 5.0
    for intento in range(1, 9):
        # ⏱️ 900 s: con 300 se agotaba mientras el modelo aún escribía.
        r = requests.post(url, timeout=900, headers=cab, json=cuerpo)
        if r.status_code in (429, 500, 502, 503, 504):
            ra = r.headers.get('Retry-After')
            try:
                pausa = float(ra) if ra else espera
            except ValueError:
                pausa = espera
            pausa = min(pausa, 60)
            print('   %d (temporal) — reintento %d/8 en %.0f s'
                  % (r.status_code, intento, pausa))
            time.sleep(pausa)
            espera = min(espera * 1.7, 60)
            continue
        if r.status_code == 400 and 'max_completion_tokens' in r.text:
            cuerpo['max_tokens'] = cuerpo.pop('max_completion_tokens')
            continue
        if r.status_code >= 400:
            print('\n--- respuesta del servidor (%d) ---' % r.status_code)
            print(r.text[:900])
            raise SystemExit('el proveedor rechazó la petición.')
        return r.json()['choices'][0]['message'].get('content') or ''
    raise SystemExit('8 intentos y sigue saturado. Prueba más tarde o con otro '
                     'modelo (--modelo gemini:gemini-2.5-flash-lite).')


def _cajas(txt):
    """Las cajas del texto, AUNQUE EL JSON VENGA CORTADO.

    🔴 La primera versión hacía `json.loads` del array entero y devolvía cero
    cuando la respuesta se truncaba por el tope de tokens — con 120 velas pasa
    siempre. El modelo había hecho su trabajo y el fallo era del lector.

    🔑 Se buscan las cajas UNA A UNA con una expresión regular. Cada objeto
    completo se aprovecha y el último, si quedó a medias, se ignora."""
    out = []
    for m in re.finditer(r'"(?:box_2d|box|bbox)"\s*:\s*\[\s*'
                         r'(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*'
                         r'(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]', txt):
        out.append([float(v) for v in m.groups()])
    if out:
        return out
    # por si algún modelo devuelve el array pelado, sin la clave box_2d
    m = re.search(r'\[.*\]', txt, re.S)
    if m:
        try:
            for d in json.loads(m.group(0)):
                c = d.get('box_2d') or d.get('box') or d.get('bbox')
                if isinstance(c, list) and len(c) == 4:
                    out.append([float(v) for v in c])
        except (ValueError, AttributeError):
            pass
    return out


def pinta(ruta, cajas, salida, orden='yxyx'):
    """Dibuja las cajas sobre la imagen.

    ⚠️ El orden de las coordenadas NO es universal: Gemini documenta
    [ymin, xmin, ymax, xmax] normalizado a 0-1000, pero otros modelos usan
    [xmin, ymin, xmax, ymax]. Si las cajas salen giradas 90°, es esto — se
    prueba con `--orden xyxy` antes de concluir que el modelo falló."""
    im = Image.open(ruta).convert('RGB')
    d = ImageDraw.Draw(im)
    W, H = im.size
    for c in cajas:
        if orden == 'yxyx':
            y0, x0, y1, x1 = c
        else:
            x0, y0, x1, y1 = c
        caja = [x0 / 1000.0 * W, y0 / 1000.0 * H,
                x1 / 1000.0 * W, y1 / 1000.0 * H]
        caja = [min(max(v, 0), W if i % 2 == 0 else H) for i, v in enumerate(caja)]
        if caja[2] < caja[0]:
            caja[0], caja[2] = caja[2], caja[0]
        if caja[3] < caja[1]:
            caja[1], caja[3] = caja[3], caja[1]
        d.rectangle(caja, outline=(0, 220, 255))
    im.save(salida)
    return salida


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--imagen', required=True)
    ap.add_argument('--modelo', required=True, metavar='PROVEEDOR:MODELO')
    ap.add_argument('--orden', default='yxyx', choices=('yxyx', 'xyxy'))
    ap.add_argument('--velas', type=int, default=25,
                    help='cuántas velas pedir (de derecha a izquierda). Pocas '
                         'bastan para juzgar y evitan que se agote el tiempo.')
    ap.add_argument('--salida')
    a = ap.parse_args()
    prov, _, modelo = a.modelo.partition(':')
    txt = _pregunta(prov, modelo, _clave(prov), a.imagen, a.velas)
    cajas = _cajas(txt)
    print('%d cajas devueltas por %s' % (len(cajas), a.modelo))
    if cajas and not txt.rstrip().endswith((']', '```')):
        print('⚠️  la respuesta venía CORTADA: puede faltar alguna vela al final.')
    if not cajas:
        print('\n--- lo que contestó (primeros 600 caracteres) ---')
        print(txt[:600])
        sys.exit(1)
    sal = a.salida or os.path.join(
        RAIZ, 'out', 'lee_grafico',
        os.path.splitext(os.path.basename(a.imagen))[0] + '_cajas.png')
    if not os.path.isdir(os.path.dirname(sal)):
        os.makedirs(os.path.dirname(sal))
    print('dibujado en', pinta(a.imagen, cajas, sal, a.orden))
    print('\n👉 Mira ese PNG. Si las cajas caen sobre las velas, el atajo sirve.')
    print('   Si salen giradas o desplazadas en bloque, repite con --orden xyxy')
    print('   antes de dar el modelo por malo.')
