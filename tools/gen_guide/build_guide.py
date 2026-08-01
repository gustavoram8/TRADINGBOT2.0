# -*- coding: utf-8 -*-
"""Regenera /guide desde el contenido de guide_{en,es,frpt}.py.

Se corre desde la raíz del repo:  python3 tools/gen_guide/build_guide.py
Editar una sección = editar los cuatro diccionarios de contenido y volver a
correr esto; el script verifica la paridad antes de escribir nada.

Trabaja por LÍNEAS, no con regex sobre el contenido: en este archivo cada
clave ocupa exactamente una línea, y los valores usan comillas simples o
dobles según lleven apóstrofe (el bloque fr usa dobles). Intentar casar las
comillas con una expresión regular es justo por donde se rompe.
"""
import io, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guide_en import EN
from guide_es import ES
from guide_frpt import FR, PT

P = 'scalpel/templates/guide.html'
SECS = ['analyze', 'preflight', 'quiz', 'forum', 'chalk', 'synapse',
        'timing', 'plans', 'account']
LANGS = [('en', EN), ('es', ES), ('fr', FR), ('pt', PT)]

# ── verificaciones previas ────────────────────────────────────────────────
for sec in SECS:
    n = {code: len(d[sec]['s']) for code, d in LANGS}
    assert len(set(n.values())) == 1, 'pasos desparejos en %s: %s' % (sec, n)
    for code, d in LANGS:
        assert d[sec]['d'].strip() and d[sec]['tip'].strip(), (sec, code)
# El apóstrofe recto rompería el string JS; FR y PT tienen que usar el tipográfico.
for code, d in LANGS:
    if code in ('fr',):
        for sec in SECS:
            for t in [d[sec]['d'], d[sec]['tip']] + d[sec]['s']:
                assert "'" not in t, 'apóstrofe recto en fr/%s: %s' % (sec, t[:60])
print('contenido: paridad ok, %d secciones x %d idiomas' % (len(SECS), len(LANGS)))

s = io.open(P, encoding='utf-8').read()
orig_len = len(s)

def jstr(t):
    return "'" + t.replace('\\', '\\\\').replace("'", "\\'") + "'"

# ── 1 · cuerpo del template ───────────────────────────────────────────────
for sec in SECS:
    i = s.index('id="%s"' % sec)
    # lead
    # El lead lleva negritas, asi que tiene que ser data-i18n-HTML: con
    # data-i18n el applier usa textContent y las etiquetas salen literales.
    viejo = '<p class="lead" data-i18n="guide.%s.d">' % sec
    if viejo in s:
        s = s.replace(viejo, '<p class="lead" data-i18n-html="guide.%s.d">' % sec)
    a = s.index('<p class="lead" data-i18n-html="guide.%s.d">' % sec, i)
    a2 = s.index('>', a) + 1
    b2 = s.index('</p>', a2)
    s = s[:a2] + EN[sec]['d'] + s[b2:]
    # pasos
    i = s.index('id="%s"' % sec)
    a = s.index('<ol class="steps">', i)
    b = s.index('</ol>', a) + len('</ol>')
    lis = '\n'.join('      <li data-i18n-html="guide.%s.s%d">%s</li>'
                    % (sec, k + 1, t) for k, t in enumerate(EN[sec]['s']))
    s = s[:a] + '<ol class="steps">\n%s\n    </ol>' % lis + s[b:]
    # tip justo después del </ol>
    fin = s.index('</ol>', s.index('id="%s"' % sec)) + len('</ol>')
    s = (s[:fin] + '\n    <p class="tip" data-i18n-html="guide.%s.tip">%s</p>'
         % (sec, EN[sec]['tip']) + s[fin:])

# ── 2 · los cuatro diccionarios ───────────────────────────────────────────
starts = {code: s.index('    %s: {\n' % code) for code, _ in LANGS}
orden = sorted(starts.items(), key=lambda kv: kv[1])
fin_obj = s.index('\n  };')
lims = {}
for k, (code, ini) in enumerate(orden):
    lims[code] = (ini, orden[k + 1][1] if k + 1 < len(orden) else fin_obj)

for code, D in reversed(orden):            # de atrás hacia delante: no mueve índices
    ini, fin = lims[code]
    dic = dict(LANGS)[code]
    lineas = s[ini:fin].split('\n')
    salida = []
    for ln in lineas:
        clave = ln.strip().split(':')[0].strip().strip("'\"")
        partes = clave.split('.')
        if len(partes) == 3 and partes[1] in SECS:
            sec, campo = partes[1], partes[2]
            if campo.startswith('s') and campo[1:].isdigit():
                continue                    # los pasos viejos se descartan
            if campo == 'tip':
                continue                    # se vuelve a emitir abajo
            if campo == 'd':
                salida.append("      'guide.%s.d':%s,"
                              % (sec, jstr(dic[sec]['d'])))
                for k, t in enumerate(dic[sec]['s']):
                    salida.append("      'guide.%s.s%d':%s,"
                                  % (sec, k + 1, jstr(t)))
                salida.append("      'guide.%s.tip':%s,"
                              % (sec, jstr(dic[sec]['tip'])))
                continue
        salida.append(ln)
    s = s[:ini] + '\n'.join(salida) + s[fin:]

# ── 3 · estilo del tip ────────────────────────────────────────────────────
if '.tip{' not in s:
    s = s.replace('    .note{',
        '    .tip{ font-size:13.6px; line-height:1.72; color:var(--ink-soft);\n'
        '      margin-top:16px; padding:13px 17px; border-left:3px solid var(--accent);\n'
        '      background:var(--accent-soft); border-radius:0 8px 8px 0; }\n'
        '    .tip b{ color:var(--ink); font-weight:700; }\n'
        '    .note{', 1)

io.open(P, 'w', encoding='utf-8').write(s)
print('escrito: %d -> %d caracteres (+%d)' % (orig_len, len(s), len(s) - orig_len))
