# -*- coding: utf-8 -*-
"""¿Por dónde hay que recortar una captura, sin preguntarle nada al cliente?

    python3 tools/recorta_grafico.py --imagen docs/capturas_prueba/mnq_5m.png

🔴 NO TOCA EL ANALIZADOR. Vive en tools/, no lo importa la app.

═══ QUÉ RESUELVE ═══
La regla de las 8 milésimas (ver CLAUDE.md): Gemini solo separa una vela de su
vecina si esa vela ocupa **más de ~8 milésimas del ancho de lo que le mandas**,
o sea si en la imagen caben menos de ~125 velas. La captura del dueño traía 255
y cada caja se comía dos o tres.

El arreglo NO es pedirle al cliente que acerque el gráfico — es **recortar
nosotros**. Pero para recortar hay que saber dos cosas que nadie nos dice: dónde
está el panel de velas y cuánto mide una vela. Las dos salen de la imagen.

🔑 **LA SEÑAL SON LOS BORDES VERTICALES, NO LA TINTA.** Contar "píxeles que no
son fondo" por columna no sirve en un gráfico entero: el fondo cambia también a
lo ANCHO (bandas de killzone, cajas de fib, sombreados), y la máscara sale
saturada — medido, daba 424 de 424 filas en todas las columnas. En cambio el
**cambio de color entre una columna y la siguiente** no depende de qué fondo
haya: el borde izquierdo y el derecho de cada cuerpo lo producen igual sobre
blanco, sobre negro o sobre un teal translúcido.

🔑 **EL PASO SE MIDE POR PERIODICIDAD, CON DESPLAZAMIENTOS FRACCIONARIOS.** Un
gráfico de velas es lo más regular que hay, así que se busca cada cuántas
columnas el perfil de bordes se parece a sí mismo. ⚠️ Y hay que permitir
**medios píxeles**: en la captura del MES el paso real es 5,5 y con lags enteros
el ganador salía 11 — el DOBLE, que habría hecho recortes con la mitad de velas
de las debidas. Por eso, tras encontrar el mejor, se prueba **la mitad**, y la
mitad de esa, mientras siga correlacionando casi igual de bien.

Medido sobre las tres capturas reales del dueño: 5,62 (real 5,5) · 8,25 (real 8)
· 10,50 (real 10,5).

🔑 **EL PANEL SE ENCUENTRA CON LA MISMA MEDIDA.** El eje de precios de la
derecha, la barra de herramientas y el eje de tiempo tienen bordes, pero **no
laten al paso de las velas**. Se recorre la imagen por ventanas y se conservan
las que sí. Nada de coordenadas fijas: cada cliente tiene su plataforma, su
resolución y sus barras.
"""
from __future__ import print_function

import argparse

import numpy as np
from PIL import Image

# Velas por recorte. Por debajo de ~125 el modelo las separa (regla de las 8
# milésimas); 80 deja margen porque el recorte no es exacto al píxel.
MAX_VELAS = 80
# Paso mínimo y máximo creíble entre velas, en píxeles.
PASO_MIN, PASO_MAX = 3.0, 40.0
# Cuánto tiene que cambiar el color entre dos columnas para contar como borde.
UMBRAL_BORDE = 60
# La mitad de un paso se acepta como paso verdadero si correlaciona al menos
# así de bien respecto del ganador. Con 0.80 se colaba un tercio espurio.
UMBRAL_MITAD = 0.85
# Cuánto tiene que hundirse la correlación ENTRE la mitad y el candidato para
# creer que son fundamental y armónica. Si no baja de esto, es una meseta.
UMBRAL_VALLE = 0.75
# Fuerza mínima del latido para dar una ventana por "panel de velas".
# ⚠️ Medido sobre las tres capturas: DENTRO del panel el latido baila entre 0,08
# y 0,58 (una ventana puede caer en un tramo lateral, con velas casi iguales, y
# hundirse); FUERA cae a 0,00 o negativo. Con 0,25 la cadena se partía y el
# panel salía a un tercio de su tamaño. El corte va bajo y se toleran huecos.
LATIDO_MIN = 0.10
# Fracción de la densidad máxima de bordes para que una ventana cuente como
# parte del panel de velas.
# ⚠️ Se eligió PASÁNDOSE, no quedándose corto. Medido en las cuatro capturas:
# con 0,25 el panel de la MNQ se cortaba y perdía ~56 velas reales; con 0,20 el
# de la del OTE se pasa 330 px hacia la zona vacía. Pasarse cuesta UNA llamada
# de más sobre un trozo sin velas, de la que el modelo devuelve poco o nada y
# que el juntado descarta solo. Quedarse corto pierde velas, y una vela que no
# está no se puede recuperar después.
DENSIDAD_MIN = 0.20
HUECOS = 1
VENTANA = 160
BANDA = 40


def perfil_bordes(a, y0=None, y1=None):
    """Cuántos cambios de color hay entre cada columna y la siguiente."""
    H = a.shape[0]
    if y0 is None:
        y0, y1 = int(H * 0.20), int(H * 0.90)
    z = a[y0:y1]
    return (np.abs(z[:, 1:] - z[:, :-1]).sum(2) > UMBRAL_BORDE).sum(0).astype(float)


def _latido(p, paso):
    """Parecido del perfil consigo mismo desplazado `paso` columnas.

    ⚠️ `paso` puede ser fraccionario: se interpola entre columnas. Sin eso, un
    gráfico con paso 5,5 se mide como 11."""
    n = len(p)
    m = int(np.floor(n - paso))
    if m < 20:
        return 0.0
    j = np.arange(m) + paso
    j0 = np.floor(j).astype(int)
    fr = j - j0
    b = p[j0] * (1 - fr) + p[np.minimum(j0 + 1, n - 1)] * fr
    a_ = p[:m] - p[:m].mean()
    b = b - b.mean()
    d = float(np.sqrt((a_ * a_).sum() * (b * b).sum()))
    return float((a_ * b).sum() / d) if d > 1e-9 else 0.0


def paso_velas(perfil):
    """El paso entre velas, en píxeles (puede ser fraccionario).

    🔑 EL PROBLEMA DE LAS ARMÓNICAS. Si el paso real son 5,5 px, entonces 11 y
    16,5 también correlacionan bien, y a veces MEJOR. Quedarse con 11 haría
    recortes con la mitad de las velas debidas, así que hay que bajar a la
    fundamental. Pero bajar a lo bruto es peor todavía.

    ⛔ DOS CRITERIOS PROBADOS Y DESCARTADOS (2026-09-05, sobre 4 capturas reales):
    · "acepta la mitad si supera el 85% del mejor" → en la captura del OTE la
      curva es una MESETA (3,50 · 4,50 · 5,50 · 6,50 · 7,50 valen todas ~0,50),
      así que la mitad pasaba el umbral sin ser un paso real: 7,50 → 3,75, y el
      panel salió donde no hay ni una vela.
    · "acepta la mitad solo si es un pico local" → arregla la del OTE y rompe la
      del MES, donde la fundamental 5,50 no queda exactamente en p/2.

    🔑 EL CRITERIO QUE SÍ DISTINGUE: **el valle**. Entre una fundamental y su
    armónica la correlación se HUNDE (en la captura del MES cae a 0,13 entre
    5,5 y 11,25). En una meseta no se hunde: se queda en 0,42 de mínimo. Así que
    la mitad solo se acepta si entre ella y el candidato actual hay un valle de
    verdad. Medido sobre las cuatro capturas: 5,50 · 8,25 · 10,50 · 7,50, con
    reales 5,5 · 8 · 10,5 · 7,4."""
    paso_g = 0.25
    rej = np.arange(PASO_MIN, PASO_MAX + 0.01, paso_g)
    cur = np.array([_latido(perfil, float(p)) for p in rej])
    i = int(cur.argmax())
    fuerza = float(cur[i])
    while True:
        objetivo = rej[i] / 2.0
        if objetivo < PASO_MIN:
            break
        # el mejor de la vecindad de la mitad, no la mitad exacta
        cerca = np.nonzero(np.abs(rej - objetivo) <= 0.75)[0]
        if not len(cerca):
            break
        j = int(cerca[np.argmax(cur[cerca])])
        if cur[j] < UMBRAL_MITAD * fuerza:
            break
        valle = float(cur[j + 1:i].min()) if i > j + 1 else cur[j]
        if valle >= UMBRAL_VALLE * cur[j]:
            break                      # meseta: no es una armónica
        i, fuerza = j, float(cur[j])
    return float(rej[i]), fuerza


def _racha(marcas, huecos):
    """La racha más larga de `True`, tolerando `huecos` falsos seguidos."""
    mejor = None
    i = 0
    n = len(marcas)
    while i < n:
        if not marcas[i]:
            i += 1
            continue
        j = i
        k = i
        fallos = 0
        while j < n:
            if marcas[j]:
                k = j
                fallos = 0
            else:
                fallos += 1
                if fallos > huecos:
                    break
            j += 1
        if mejor is None or k - i > mejor[1] - mejor[0]:
            mejor = (i, k)
        i = j + 1
    return mejor


def panel(ruta):
    """(x0, x1, y0, y1) del panel de velas, y el paso entre velas."""
    a = np.asarray(Image.open(ruta).convert('RGB')).astype(int)
    H, W, _ = a.shape
    perfil = perfil_bordes(a)
    paso, fuerza = paso_velas(perfil)
    if not paso:
        return None
    # 🔴 EL PANEL SE ACOTA POR DENSIDAD DE BORDES, NO POR PERIODICIDAD.
    # Se probó con periodicidad y falla: una LÍNEA DISCONTINUA también es
    # periódica. En la captura del OTE, las ventanas de la zona vacía de la
    # derecha —solo cajas grises, fibs y punteadas— daban latidos de 0,48 y 0,68,
    # más altos que los de varias ventanas con velas de verdad, y el panel salió
    # en x 240-1440 cuando las velas están en 0-780.
    # 🔑 Lo que sí las separa es CUÁNTA tinta de borde hay: una vela es alta, así
    # que aporta decenas de cambios por columna; una raya aporta uno o dos.
    # Medido en esa captura: 8,6 a 38 donde hay velas, 0,7 a 4 donde no.
    paso_v = VENTANA // 2
    dens = [perfil[x:x + VENTANA].mean()
            for x in range(0, max(1, len(perfil) - VENTANA), paso_v)]
    tope = max(dens) if dens else 0.0
    marcas = [d >= DENSIDAD_MIN * tope for d in dens]
    tramo = _racha(marcas, HUECOS)
    if not tramo:
        return None
    x0 = tramo[0] * paso_v
    x1 = min(W, tramo[1] * paso_v + VENTANA)

    # 🔴 EL ALTO NO SE RECORTA, A PROPÓSITO. Se probó detectarlo con la misma
    # medida de periodicidad por bandas horizontales, y en la captura zoomeada
    # devolvía y=240-640 sobre un panel que va de 200 a 800: **cortaba velas por
    # arriba y por abajo**, y una vela cortada se mide mal — que es justo el
    # fallo que llevamos días persiguiendo.
    # Y no hace falta: la regla de las 8 milésimas es sobre el ANCHO. Recortar
    # a lo alto no aporta nada y solo puede quitar información. La barra de
    # herramientas y el eje de tiempo se quedan dentro; medido sobre la captura
    # del MES, el modelo no encajonó ni un icono ni una etiqueta.
    y0, y1 = 0, H
    return {'x0': int(x0), 'x1': int(x1), 'y0': y0, 'y1': y1,
            'paso': round(paso, 2), 'fuerza': round(fuerza, 3),
            'velas': int((x1 - x0) / paso)}


def tiras(ruta, max_velas=MAX_VELAS, solape=6):
    """Los recortes que hay que mandarle al modelo.

    ⚠️ Se solapan unas velas a propósito: la que cae justo en la costura
    saldría partida entre dos tiras, y una vela a medias mide mal. Con solape
    aparece entera al menos en una, y luego se juntan por su posición."""
    p = panel(ruta)
    if not p:
        return []
    ancho = int(max_velas * p['paso'])
    salto = int(max(1, (max_velas - solape) * p['paso']))
    out, x = [], p['x1']
    while x > p['x0']:
        a = max(p['x0'], x - ancho)
        out.append((a, p['y0'], x, p['y1']))
        if a <= p['x0']:
            break
        x -= salto
    out.reverse()
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--imagen', required=True)
    ap.add_argument('--max-velas', type=int, default=MAX_VELAS)
    a = ap.parse_args()
    p = panel(a.imagen)
    if not p:
        raise SystemExit('no se encontró un panel de velas en esa imagen.')
    W, H = Image.open(a.imagen).size
    print('imagen %dx%d' % (W, H))
    print('panel  x %d-%d · y %d-%d · paso %.2f px (latido %.2f) · ~%d velas'
          % (p['x0'], p['x1'], p['y0'], p['y1'], p['paso'], p['fuerza'], p['velas']))
    ts = tiras(a.imagen, a.max_velas)
    print('%d recorte(s) de %d velas:' % (len(ts), a.max_velas))
    for (x0, y0, x1, y1) in ts:
        mil = p['paso'] / float(x1 - x0) * 1000
        print('   --recorte %d,%d,%d,%d   →  %.1f milésimas por vela %s'
              % (x0, y0, x1, y1, mil, '✅' if mil >= 8 else '🔴'))
