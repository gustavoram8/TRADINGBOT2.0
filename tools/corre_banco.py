# -*- coding: utf-8 -*-
"""Pasa el banco de gráficos por el MISMO modelo y prompt que producción.

    venv/bin/python3 tools/corre_banco.py            # dice qué haría y el costo
    venv/bin/python3 tools/corre_banco.py --si       # lo corre (gasta dinero)
    venv/bin/python3 tools/corre_banco.py --si --caso H3 E4   # solo esos
    venv/bin/python3 tools/corre_banco.py --si I3 --idioma English --tag en

NO toca el analizador: importa `build_system_prompt`, el cliente y el modelo
de `app.py` en SOLO lectura y arma el mensaje de usuario CALCADO del endpoint
`/analyze` (mismos campos, misma imagen en base64, mismo detail, mismos
max_tokens y temperature). Lo que se mide es lo que un cliente recibiría.

Requiere `OPENAI_API_KEY` (en el VPS vive en scalpel/.env y en supervisor).
Cada caso ≈ $0.03; el banco entero ≈ $0.70 por pasada.

Resultados → out/banco_analizador/resultados/<id>.md + resultados.json.
Después:  venv/bin/python3 tools/califica_banco.py
"""
from __future__ import print_function

import base64
import io
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Idioma de la RESPUESTA (el analizador contesta en el del cliente). El banco
# se corrió en español; `--idioma English` sirve para material en inglés.
IDIOMA = 'Spanish'
BANCO = os.path.join(RAIZ, 'out', 'banco_analizador')
RES = os.path.join(BANCO, 'resultados')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

try:
    import app as A
except Exception as e:                                    # pragma: no cover
    sys.exit('no se pudo cargar la app: %s%s' % (
        e, ('\n\n👉 Usa el intérprete del entorno:\n'
            '   venv/bin/python3 %s' % os.path.relpath(__file__, RAIZ))
        if 'No module named' in str(e) else ''))


def mensaje_usuario(f, idioma):
    """Calco del user_message de /analyze — si aquél cambia, revisar éste."""
    confl = ', '.join(f['confluences']) if f['confluences'] else 'None specified'
    bloque = ''
    if f['notes']:
        bloque = f"""
TRADER'S TRADE CONSTRUCTION (what the trader saw and why they took this trade):
\"\"\"
{f['notes']}
\"\"\"
This is the trader's own account of how they built the trade — their reasoning, the levels they identified, what they were waiting for, and how they decided to enter. Treat this as their declared thesis. Your job is to:
1. Evaluate whether what they described is visible and consistent with what you see on the chart.
2. Contrast their declared construction against the actual price action — where does the chart confirm their thesis? Where does it diverge or show something they may not have accounted for?
3. Be specific: if they say they identified a FVG or OB at a certain point, look for it on the chart and comment on its quality. If they mention a liquidity sweep, verify whether it looks like a clean sweep with displacement on the chart.
Do NOT simply repeat their construction back — analyze and contrast it."""
    return f"""Trade submitted for retrospective, educational analysis (approach: {f['approach']}):

Instrument: {f['instrument']}
DIRECTION (ground truth — the trader took a {f['direction']} position): {f['direction']}
Session: {f['session']}
Result: {f['result']}
HTF Bias held: {f['htf_bias']}
Traded aligned with HTF bias: {f['aligned']}
Approach / model used: {f['approach']}
Confluences identified by trader: {confl}
{bloque}
This was a {f['direction']} trade — anchor your entire analysis to that fact. Locate where the trader entered and exited on the chart using the {f['direction']} direction as your reference. Analyze it through the trader's stated approach ({f['approach']}) via the METHODOLOGY ROUTER — if the approach is OTE / Std Dev, lead with the dedicated OTE / Standard Deviation lens (its distinct fib-driven trigger), not a generic ICT read. Identify possible setup considerations — or confirm if the setup was technically sound and this may have been within normal statistical variance.

LANGUAGE: Write your entire response in {idioma}. Keep ICT-specific terms and acronyms (FVG, IFVG, OTE, CHoCH, MSS, BOS, OB, SMT, BSL, SSL, EQH, EQL, Kill Zone, Silver Bullet, etc.) in their standard English form, but write all explanatory prose in {idioma}."""


def main():
    manif_ruta = os.path.join(BANCO, 'manifest.json')
    if not os.path.exists(manif_ruta):
        sys.exit('No existe el banco. Genera primero:\n'
                 '  venv/bin/python3 tools/banco_analizador.py')
    with io.open(manif_ruta, encoding='utf-8') as fh:
        casos = json.load(fh)

    # --tag v2 → resultados-v2/: una pasada nueva NUNCA pisa la línea base,
    # porque el veredicto ES la comparación entre las dos carpetas.
    args = list(sys.argv[1:])
    global RES, IDIOMA
    if '--idioma' in args:
        i = args.index('--idioma')
        IDIOMA = args[i + 1]
        del args[i:i + 2]
    if '--tag' in args:
        i = args.index('--tag')
        RES = os.path.join(BANCO, 'resultados-' + args[i + 1])
        del args[i:i + 2]
    filtro = [a for a in args if not a.startswith('--')]
    if filtro:
        casos = [c for c in casos
                 if any(c['id'].startswith(f) for f in filtro)]
    if not casos:
        sys.exit('ningún caso coincide con el filtro %s' % filtro)

    est = len(casos) * 0.035
    print('%d casos × ~$0.035 ≈ $%.2f  (modelo %s, backend %s)'
          % (len(casos), est, A.MODEL, A.AI_BACKEND))
    if '--si' not in sys.argv:
        print('\n(mirando) no se llamó al modelo. Repite con --si para gastar.')
        return 0

    # El banco mide el ANALIZADOR DE PAGO, el que usan los clientes. Con el
    # respaldo gratuito de GitHub Models se mediría otro servicio con otros
    # límites — resultado engañoso, así que se exige la clave o un override.
    if A.AI_BACKEND != 'openai' and '--github' not in sys.argv:
        sys.exit('El backend activo es %r, no OpenAI de pago. En el VPS corre\n'
                 'este script con la clave presente (scalpel/.env la tiene).\n'
                 'Para forzar el backend gratuito igualmente: --github'
                 % A.AI_BACKEND)

    os.makedirs(RES, exist_ok=True)
    ruta_json = os.path.join(RES, 'resultados.json')
    resultados = {}
    if os.path.exists(ruta_json):
        with io.open(ruta_json, encoding='utf-8') as fh:
            resultados = json.load(fh)

    gastado = 0.0
    for k, caso in enumerate(casos):
        png = os.path.join(RAIZ, caso['png'])
        with open(png, 'rb') as fh:
            img64 = base64.b64encode(fh.read()).decode('utf-8')
        print('[%2d/%d] %-30s' % (k + 1, len(casos), caso['id']), end=' ',
              flush=True)
        t0 = time.time()
        r = A.client.chat.completions.create(
            model=A.MODEL,
            messages=[
                {'role': 'system',
                 'content': A.build_system_prompt(caso['form']['approach'])},
                {'role': 'user', 'content': [
                    {'type': 'text',
                     'text': mensaje_usuario(caso['form'], IDIOMA)},
                    {'type': 'image_url', 'image_url': {
                        'url': 'data:image/png;base64,' + img64,
                        'detail': A.ANALYZE_IMG_DETAIL}},
                ]},
            ],
            max_tokens=900, temperature=0.3)
        texto = r.choices[0].message.content or ''
        u = getattr(r, 'usage', None)
        pt = int(getattr(u, 'prompt_tokens', 0) or 0)
        ct = int(getattr(u, 'completion_tokens', 0) or 0)
        costo = pt * A.AI_PRICE_IN + ct * A.AI_PRICE_OUT
        gastado += costo
        print('%5.1fs  %5d+%4d tok  $%.4f' % (time.time() - t0, pt, ct, costo))
        resultados[caso['id']] = {'texto': texto, 'prompt_tokens': pt,
                                  'completion_tokens': ct,
                                  'costo': round(costo, 5),
                                  'modelo': A.MODEL}
        with io.open(os.path.join(RES, caso['id'] + '.md'), 'w',
                     encoding='utf-8') as fh:
            f = caso['form']
            fh.write('# %s\n\n**%s · %s · %s · %s**\n\n**Notas del trader:** '
                     '%s\n\n---\n\n%s\n'
                     % (caso['id'], f['approach'], caso['instrumento'],
                        f['direction'], f['result'], f['notes'], texto))
        # guardar tras CADA caso: un corte a mitad no pierde lo ya pagado
        with io.open(ruta_json, 'w', encoding='utf-8') as fh:
            json.dump(resultados, fh, ensure_ascii=False, indent=1)
        time.sleep(1)

    print('\nGastado: $%.3f · %d respuestas en %s'
          % (gastado, len(casos), os.path.relpath(RES, RAIZ)))
    print('Ahora:  venv/bin/python3 tools/califica_banco.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
