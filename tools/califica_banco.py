# -*- coding: utf-8 -*-
"""Coteja las respuestas del banco contra su rúbrica y arma el informe.

    venv/bin/python3 tools/califica_banco.py

Lee `out/banco_analizador/resultados/resultados.json` (lo escribe
corre_banco.py) y el `manifest.json`, y produce `INFORME.md` con un veredicto
por caso:

  🟢 LO CAZÓ    — la señal CLAVE de la rúbrica aparece (en las trampas: que
                  corrigió al trader; en los demás: la lectura central);
  🔴 NO LO CAZÓ — la señal clave falta, o dijo algo PROHIBIDO (validar un
                  patrón falso, confirmar un dato inventado, culpar a lo que
                  estaba bien);
  🟡 A REVISAR  — la clave está pero con matices, o hay señales secundarias
                  ausentes: lo decide un humano leyendo el texto.

⚠️ El regex es un DETECTOR, no un juez: caza formulaciones esperadas. Un 🔴
merece leerse antes de condenar (el modelo pudo decirlo con otras palabras) —
por eso cada caso lleva su extracto y el archivo completo al lado.
"""
from __future__ import print_function

import io
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ, 'out', 'banco_analizador')


def main():
    # --tag v2 → califica la carpeta resultados-v2 y escribe INFORME-v2.md
    args = list(sys.argv[1:])
    sufijo = ''
    if '--tag' in args:
        sufijo = '-' + args[args.index('--tag') + 1]
    try:
        with io.open(os.path.join(BANCO, 'manifest.json'),
                     encoding='utf-8') as fh:
            casos = json.load(fh)
        with io.open(os.path.join(BANCO, 'resultados' + sufijo,
                                  'resultados.json'),
                     encoding='utf-8') as fh:
            resultados = json.load(fh)
    except IOError as e:
        sys.exit('falta un insumo (%s).\nOrden: banco_analizador.py → '
                 'corre_banco.py --si → califica_banco.py' % e)

    lineas = ['# Informe del banco del analizador\n']
    tabla = ['| caso | tipo | veredicto | clave | prohibido |',
             '|---|---|---|---|---|']
    cuenta = {'🟢': 0, '🔴': 0, '🟡': 0, '—': 0}

    for caso in casos:
        rid = caso['id']
        r = resultados.get(rid)
        es_trampa = '_trampa_' in rid
        # el tipo sale del RESULT del formulario, no del nombre del caso (el
        # nombre mentía en I6/H5/W5: son perdidos sin el sufijo "_perdido")
        res_form = caso['form'].get('result', '')
        tipo = 'TRAMPA' if es_trampa else \
            {'Loss': 'perdido', 'Breakeven': 'BE'}.get(res_form, 'ganado')
        if not r:
            tabla.append('| %s | %s | — sin correr | | |' % (rid, tipo))
            cuenta['—'] += 1
            continue
        texto = r['texto']

        claves_ok, claves_mal, extras_ok, extras_mal = [], [], [], []
        for patron, desc, clave in caso['rubrica']['espera']:
            hay = re.search(patron, texto, re.I | re.S) is not None
            (claves_ok if clave and hay else
             claves_mal if clave else
             extras_ok if hay else extras_mal).append(desc)
        prohibidos = [desc for patron, desc in caso['rubrica']['prohibido']
                      if re.search(patron, texto, re.I | re.S)]

        if prohibidos or (claves_mal and not claves_ok):
            ver = '🔴 NO LO CAZÓ'
        elif claves_mal:
            ver = '🟡 A REVISAR'
        elif extras_mal and not es_trampa:
            # En un ganado/perdido las secundarias son parte de la lectura;
            # en una TRAMPA solo importa la pregunta única: ¿corrigió o no?
            ver = '🟡 A REVISAR'
        else:
            ver = '🟢 LO CAZÓ'
        cuenta[ver.split()[0]] += 1

        tabla.append('| %s | %s | %s | %d/%d | %d |'
                     % (rid, tipo, ver.split()[0],
                        len(claves_ok), len(claves_ok) + len(claves_mal),
                        len(prohibidos)))
        lineas.append('\n---\n\n## %s — %s · %s\n' % (rid, tipo, ver))
        lineas.append('**Qué es (verdad del gráfico):** %s\n' % caso['humano'])
        if claves_ok:
            lineas.append('**Señal clave encontrada:** ' +
                          ' · '.join(claves_ok) + '\n')
        if claves_mal:
            lineas.append('**🔴 Señal clave AUSENTE:** ' +
                          ' · '.join(claves_mal) + '\n')
        if prohibidos:
            lineas.append('**🔴 Dijo lo prohibido:** ' +
                          ' · '.join(prohibidos) + '\n')
        if extras_mal:
            lineas.append('**Secundarias ausentes:** ' +
                          ' · '.join(extras_mal) + '\n')
        recorte = texto.strip().replace('\n', ' ')
        lineas.append('\n> %s%s\n\n*(completo en `resultados/%s.md` · '
                      '%d tok · $%.4f)*\n'
                      % (recorte[:600], '…' if len(recorte) > 600 else '',
                         rid, r['completion_tokens'], r['costo']))

    resumen = ('**Resultado global:** 🟢 %(🟢)d cazados · 🔴 %(🔴)d fallados · '
               '🟡 %(🟡)d a revisar · %(—)d sin correr\n' % cuenta)
    salida = '\n'.join([lineas[0], resumen, ''] + tabla + lineas[1:])
    ruta_inf = os.path.join(BANCO, 'INFORME%s.md' % sufijo)
    with io.open(ruta_inf, 'w', encoding='utf-8') as fh:
        fh.write(salida)

    print(resumen)
    for fila in tabla[2:]:
        print('  ' + fila.strip('| ').replace(' | ', '  ·  '))
    print('\nInforme completo: %s' % os.path.relpath(ruta_inf, RAIZ))
    return 0


if __name__ == '__main__':
    sys.exit(main())
