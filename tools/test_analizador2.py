# -*- coding: utf-8 -*-
"""Prueba de la cadena entera, SIN red, contra la captura real del dueño.

    python3 tools/test_analizador2.py

🔑 QUÉ BLINDA. El BOS de la vela x=886 es el único hecho de toda esta cadena
verificado contra una fuente INDEPENDIENTE: el indicador BoS/ChoCh del propio
dueño dibuja ahí su marca (línea que termina en x=886, y=614) y la cadena —que
no lee un solo píxel de texto ni de esa línea— llega al mismo sitio por
geometría, con el nivel a 3 px.

⚠️ Y ya se perdió una vez: al encadenar, midiendo sobre la imagen entera en vez
de sobre la franja del gráfico, ese BOS DESAPARECÍA y salían otros tres. El
fallo no daba ningún error: la salida seguía pareciendo razonable. Por eso esto
es una prueba y no una nota.

Las columnas van fijas a propósito: son las que devolvió Gemini el 2026-09-05.
Así la prueba mide LA CADENA, no la red ni la disponibilidad del modelo.
"""
from __future__ import print_function

import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analizador2 as A2  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGEN = os.path.join(RAIZ, 'docs', 'capturas_prueba', 'mnq_5m_zoom.png')

COLUMNAS = (
    "760-767:503-525,769-777:463-535,780-788:302-488,789-798:416-577,"
    "801-809:538-575,812-820:392-573,822-831:410-529,833-841:387-492,"
    "843-852:460-565,854-863:507-609,865-873:509-620,875-884:502-606,"
    "886-895:503-633,897-905:606-657,908-916:606-636,918-926:540-621,"
    "928-937:477-560,939-947:502-590,950-958:526-590,960-967:463-545,"
    "971-979:465-567,981-989:476-551,992-1000:491-549,1005-1010:489-564,"
    "1013-1021:468-528,1024-1032:460-521,1035-1043:504-587,1045-1053:539-593,"
    "1056-1064:538-598,1066-1074:528-568,1077-1085:484-538,1088-1096:516-592,"
    "1098-1107:579-633,1109-1117:604-637,1119-1127:528-620,1130-1138:535-598,"
    "1141-1149:540-587,1151-1159:501-560,1162-1170:501-543,1172-1180:500-569,"
    "1182-1191:492-571,1194-1202:492-539,1204-1212:485-512,1215-1223:464-495,"
    "1226-1234:468-510,1235-1240:493-520")


def main():
    if not os.path.exists(IMAGEN):
        print('falta', IMAGEN)
        return False
    cajas = A2.lee_columnas(COLUMNAS)

    hechos_, mal = [0], []

    def caso(n, cond, extra=''):
        hechos_[0] += 1
        print(('  ✅ ' if cond else '  🔴 ') + n + ('' if cond else ' %s' % extra))
        if not cond:
            mal.append(n)

    r = A2.analiza(IMAGEN, cajas=cajas, verboso=False)
    velas = r['velas']
    xs = [v['x0'] for v in velas]

    print('── las columnas se guardan y se releen igual ──')
    # 🔑 Es lo ÚNICO de la cadena que cuesta dinero y depende de que Google
    # conteste. Si el archivo que se guarda no se relee idéntico, una corrida
    # saturada obliga a volver a pagarlas.
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), 'cols_prueba.txt')
    with open(tmp, 'w') as f:
        f.write(','.join('%d-%d:%d-%d' % c for c in cajas))
    caso('@archivo devuelve las mismas columnas',
         A2.lee_columnas('@' + tmp) == cajas)

    print('── la cadena entrega las velas ──')
    caso('mide las 46 velas', len(velas) == 46, len(velas))
    alturas = [v['min'] - v['max'] for v in velas]
    # 🔴 ESTA COMPROBACIÓN SE REESCRIBIÓ EL 09-sep, y el motivo importa. Decía
    #    "ninguna vela mide más de 3× la mediana", y eso NO es cierto en un
    #    gráfico real: una vela de DESPLAZAMIENTO —la que abre un FVG, la que
    #    rompe estructura— mide tranquilamente 3 a 6 veces la mediana, y son
    #    justo las que decide un análisis de ICT. La más alta de esta captura
    #    mide 3,1× y es CORRECTA: la tinta de su columna va de y=306 a 521 y se
    #    mide 302-522.
    #    Un número mágico que declara imposible lo que el gráfico tiene delante
    #    no es una red de seguridad: es un freno. Se cambia por lo único que de
    #    verdad demuestra que no es un disparate — que la vela más alta COINCIDA
    #    CON LA TINTA de su propia columna.
    alto = max(range(len(velas)), key=lambda i: alturas[i])
    _a = np.asarray(Image.open(IMAGEN).convert('RGB')).astype(int)
    _c = _a[200:800, velas[alto]['x0']:velas[alto]['x1'] + 1]
    _ys = np.nonzero((np.abs(_c).sum(2) < 150).any(1))[0]
    caso('la vela más alta coincide con la tinta de su columna (±6 px)',
         len(_ys) and abs(velas[alto]['max'] - (_ys.min() + 200)) <= 6
         and abs(velas[alto]['min'] - (_ys.max() + 200)) <= 6,
         (velas[alto]['max'], velas[alto]['min']))
    caso('y ninguna se dispara de verdad (máx < 8× la mediana)',
         max(alturas) < 8 * sorted(alturas)[len(alturas) // 2], max(alturas))
    caso('todas tienen cuerpo dentro de su extenso',
         all(v['max'] <= v['cuerpo_alto'] <= v['cuerpo_bajo'] <= v['min']
             for v in velas))

    print('── el hecho verificado contra el indicador del dueño ──')
    bos = r['hechos']['bos']
    # ⚠️ Se compara la VELA que contiene x=886, no el píxel exacto de su borde
    #    izquierdo. Lo que el indicador del dueño afirma es "el BOS es esta
    #    vela", y una columna puede empezar en 885 o en 886 y seguir siendo la
    #    misma vela. Fijar el píxel hacía fallar la prueba ante una mejora
    #    legítima —encajar las columnas en la rejilla real las movió 1 px— y
    #    eso convierte al test en un freno en vez de en una red.
    en886 = [b for b in bos
             if velas[b['i']]['x0'] <= 886 <= velas[b['i']]['x1']]
    caso('hay un BOS en la vela que contiene x=886', len(en886) == 1,
         [(v['x0'], v['x1']) for v in (velas[b['i']] for b in bos)])
    if en886:
        caso('y es BAJISTA', en886[0]['tipo'] == 'bajista', en886[0]['tipo'])

    print('── ningún hecho se cuenta dos veces ──')
    # 🔴 Cazado en la corrida real: el mismo order block salía dos veces
    # palabra por palabra, porque se deriva de un FVG y una vela puede originar
    # dos FVG solapados. Un hecho repetido se lee como confirmación.
    for fam in ('fvg', 'ob', 'bos', 'barrida'):
        cl = [tuple(sorted(h.items())) for h in r['hechos'][fam]]
        caso('%s sin repetidos' % fam, len(cl) == len(set(cl)),
             '%d de %d' % (len(set(cl)), len(cl)))

    print('── el bloque no afirma lo que no puede ──')
    firmes, marcados = A2.bloque(velas, r['hechos'], None)
    # ⚠️ ESTAS DOS COMPROBACIONES CAMBIARON EL 09-sep, y no por un fallo: el
    #    bloque pasó de DOS niveles a TRES a propósito. Antes exigían que solo
    #    BOS y barridas se afirmaran y que FVG y order block se callaran; eso
    #    dejaba un analizador que vende ICT sin poder nombrar una pieza de ICT.
    #    Lo que hay que blindar ahora no es QUÉ familia está en cada nivel —eso
    #    lo decide el banco y se mueve— sino la REGLA: nada se afirma en seco
    #    por debajo del mínimo, y todo lo que va marcado lleva su tasa.
    caso('nada se afirma en seco por debajo del mínimo',
         all(A2.precision_de(f) >= A2.MIN_PRECISION for f, _ in firmes))
    caso('todo lo marcado lleva su tasa de acierto medida',
         all('[medido: acierta' in l for _f, l in marcados) and len(marcados) > 0)
    caso('nada por debajo del mínimo de mención se escribe',
         all(A2.precision_de(f) >= A2.MIN_MENCION for f, _ in firmes + marcados))
    # sin escala del eje, NINGUNA línea puede llevar la frase "en <precio>"
    caso('sin escala, ninguna línea inventa un precio',
         not any(' en 2' in l or ' entre 2' in l for _f, l in firmes + marcados))

    print()
    print('%d/%d' % (hechos_[0] - len(mal), hechos_[0]))
    if mal:
        print('FALLAN:', mal)
    return not mal


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
