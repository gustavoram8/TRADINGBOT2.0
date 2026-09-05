# -*- coding: utf-8 -*-
"""De píxel a PRECIO: leer el eje y ajustar la escala, tolerando lecturas malas.

    # en el VPS (necesita la clave):
    python3 tools/eje_precio.py --imagen docs/capturas_prueba/mnq_5m_zoom.png \\
        --modelo gemini:gemini-flash-latest
    # sin red, con etiquetas ya leídas:
    python3 tools/eje_precio.py --etiquetas 257:7676,489:7648

🔴 NO TOCA EL ANALIZADOR. Vive en tools/, no lo importa la app.

═══ POR QUÉ HACE FALTA ═══
La cadena ya dice *"cerró por debajo del nivel"* comparando píxeles, y para eso
no hace falta ningún precio. Pero para **enseñárselo a un cliente** hay que
poder escribir *"perforó 29.428,50"*, y eso exige la escala.

═══ POR QUÉ NO BASTA CON LEER DOS ETIQUETAS ═══
🔴 Un solo dígito mal leído destruye la escala entera, en silencio. Leer
`29.550` como `29.556` mueve todos los precios del gráfico y nadie se entera:
el resultado sigue pareciendo un número razonable. Y es un fallo que pasa: es
OCR sobre texto pequeño.

🔑 **EL SEGURO ES LA REDUNDANCIA, NO LA CONFIANZA.** Un eje de precios tiene
muchas etiquetas y todas caen sobre la MISMA recta: si a un precio le
corresponde una altura, a los demás les corresponde la suya con el mismo factor.
Así que se prueban todos los pares posibles, cada par propone una recta, y gana
**la recta que más etiquetas confirma**. Una lectura mala no tiene con quién
ponerse de acuerdo y se queda sola. Con seis etiquetas y una mala, el consenso
lo forman las cinco buenas.

⚠️ Se exige un mínimo de etiquetas de acuerdo (`MIN_ACUERDO`). Si no se llega,
**se devuelve None y el analizador habla sin precios**, que es lo correcto:
mejor decir "cerró por debajo del nivel" que inventarse una cifra.
"""
from __future__ import print_function

import argparse
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))

# Cuánto puede desviarse una etiqueta de la recta para contar como de acuerdo.
TOLERANCIA_PX = 2.0
# Etiquetas que tienen que confirmar la recta para darla por buena.
MIN_ACUERDO = 3


def ajusta(etiquetas):
    """`etiquetas` = [(y_px, precio)] → (precio_por_px, precio_en_y0, apoyos).

    Devuelve None si no hay consenso suficiente."""
    pts = [(float(y), float(p)) for y, p in etiquetas]
    if len(pts) < MIN_ACUERDO:
        return None
    mejor = None
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            (y1, p1), (y2, p2) = pts[i], pts[j]
            if abs(y1 - y2) < 1e-6 or abs(p1 - p2) < 1e-9:
                continue
            m = (p2 - p1) / (y2 - y1)          # precio por píxel (negativo)
            b = p1 - m * y1
            # cuántas etiquetas caen sobre esa recta, medido EN PÍXELES
            apoyos = [(y, p) for (y, p) in pts
                      if abs((p - b) / m - y) <= TOLERANCIA_PX]
            if mejor is None or len(apoyos) > len(mejor[2]):
                mejor = (m, b, apoyos)
    if mejor is None or len(mejor[2]) < MIN_ACUERDO:
        return None
    # refinado por mínimos cuadrados SOLO con los que están de acuerdo
    ys = [y for y, _ in mejor[2]]
    ps = [p for _, p in mejor[2]]
    n = len(ys)
    my = sum(ys) / n
    mp = sum(ps) / n
    sxy = sum((y - my) * (p - mp) for y, p in zip(ys, ps))
    sxx = sum((y - my) ** 2 for y in ys)
    if abs(sxx) < 1e-9:
        return None
    m = sxy / sxx
    b = mp - m * my
    return {'por_px': m, 'base': b, 'apoyos': len(mejor[2]),
            'total': len(pts),
            'precio': (lambda y: m * y + b)}


def _numero(txt):
    """'29.550,75' o '29,550.75' o '7676' → float. None si no es un precio."""
    t = txt.strip().replace(' ', '')
    if not re.match(r'^[\d.,]+$', t) or not re.search(r'\d', t):
        return None
    # el ÚLTIMO separador con 1-2 dígitos detrás es el decimal
    m = re.search(r'[.,](\d{1,2})$', t)
    if m:
        ent = re.sub(r'[.,]', '', t[:m.start()])
        return float('%s.%s' % (ent, m.group(1))) if ent else None
    ent = re.sub(r'[.,]', '', t)
    return float(ent) if ent else None


def _pide():
    return ('En esta imagen hay un eje de precios vertical. Devuelve SOLO un '
            'array JSON con TODAS las etiquetas numéricas del eje, sin '
            'inventarte ninguna. Cada elemento: '
            '{"box_2d": [ymin, xmin, ymax, xmax], "label": "el número tal cual '
            'aparece"} con las coordenadas normalizadas de 0 a 1000.')


def lee(prov, modelo, ruta):
    """Lee las etiquetas del eje con el modelo. 🔴 Solo corre en el VPS."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'ci', os.path.join(RAIZ, 'tools', 'cajas_ia.py'))
    ci = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ci)
    from PIL import Image
    H = Image.open(ruta).size[1]
    txt = ci._pregunta(prov, modelo, ci._clave(prov), ruta, 0, todas=False)
    out = []
    for m in re.finditer(
            r'"box_2d"\s*:\s*\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*'
            r'(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]\s*,\s*"label"\s*:\s*"([^"]*)"',
            txt):
        ym, _xm, yM, _xM, lab = m.groups()
        precio = _numero(lab)
        if precio is None:
            continue
        y = (float(ym) + float(yM)) / 2.0 / 1000.0 * H
        out.append((y, precio))
    return out, txt


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--imagen')
    ap.add_argument('--modelo', metavar='PROVEEDOR:MODELO')
    ap.add_argument('--etiquetas', help='y:precio,y:precio,... ya leídas')
    a = ap.parse_args()
    if a.etiquetas:
        et = []
        for p in a.etiquetas.split(','):
            y, _, pr = p.partition(':')
            et.append((float(y), _numero(pr)))
    else:
        if not (a.imagen and a.modelo):
            raise SystemExit('hace falta --etiquetas, o --imagen y --modelo.')
        prov, _, modelo = a.modelo.partition(':')
        et, crudo = lee(prov, modelo, a.imagen)
        print('%d etiquetas leídas' % len(et))
        for y, p in sorted(et):
            print('   y=%7.1f  →  %s' % (y, p))
        if not et:
            print(crudo[:500])
    r = ajusta(et)
    if not r:
        print('\n🔴 SIN CONSENSO: no se puede fijar la escala. El analizador '
              'debe hablar SIN precios en vez de inventarse uno.')
        sys.exit(1)
    print('\n✅ escala: %.4f por píxel · %d de %d etiquetas de acuerdo'
          % (r['por_px'], r['apoyos'], r['total']))
    if r['apoyos'] < r['total']:
        print('   ⚠️ %d etiqueta(s) descartada(s) por no caer en la recta — '
              'eso es OCR fallando, y es justo lo que este método absorbe.'
              % (r['total'] - r['apoyos']))
