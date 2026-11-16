# -*- coding: utf-8 -*-
"""Regenera el inventario de CONTEXTO_TRADEABLE y arma el ZIP para entregar.

    python3 tools/empaqueta_contexto.py            # inventario + ZIP
    python3 tools/empaqueta_contexto.py --solo-inventario

QUÉ HACE
  1. Escribe `CONTEXTO_TRADEABLE/99_INVENTARIO_DE_ARCHIVOS.md` a partir de lo
     que hay de verdad en el repo (nombres, tamaños y, para las herramientas,
     la primera línea de su cabecera).
  2. Arma `out/CONTEXTO_TRADEABLE_<fecha>.zip` con el expediente + anexos:
     las notas crudas, el código del laboratorio, las capturas de prueba, los
     resultados de los bancos y las configs de nginx.
  3. ANTES de cerrar el ZIP busca correos y llaves en todo lo que va dentro, y
     SE NIEGA a crearlo si encuentra algo que no esté en la lista permitida.

POR QUÉ EL ZIP NO LLEVA EL CÓDIGO DEL SITIO
  `scalpel/` pesa ~88 MB (modelos 3D, arte de camos) y el backend lleva escrito
  el correo personal del dueño y una contraseña por defecto. El código se
  entrega dando acceso al repositorio, no por ZIP.

🔴 Este programa NO LEE el contenido de los archivos de la raíz ni de
   `scalpel/*.py` (solo nombre y tamaño), ni de las herramientas `check_*`:
   algunos llevan el correo del dueño y no hay por qué abrirlos para listarlos.
"""
from __future__ import print_function

import argparse
import ast
import datetime
import io
import os
import re
import subprocess
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = os.path.join(RAIZ, 'CONTEXTO_TRADEABLE')
INV = os.path.join(CTX, '99_INVENTARIO_DE_ARCHIVOS.md')

# Las herramientas `check_*` no se abren: se describen a mano.
CHECK = {
    'borrados': 'Vigilante: ¿alguna cuenta borrada conserva un cobro vivo en PayPal? (`--cortar`)',
    'cripto': 'Estado de la pasarela cripto (NOWPayments).',
    'horas': 'Comprueba que las fechas se guardan en UTC.',
    'mail': 'Diagnóstico del correo: MX, SPF, DKIM, DMARC, conexión y envío de prueba.',
    'oferta': '¿Sigue encendida la oferta de bienvenida y a qué porcentaje?',
    'paypal': '¿Autentican las credenciales de PayPal y a qué entorno pertenecen?',
    'posts_hoy': 'Cuenta las publicaciones del día (diagnóstico del cupo diario del foro).',
    'subs': '¿Sirven de verdad las renovaciones? Planes activos y webhook correcto.',
    'suscripcion': 'Revisa lo que PayPal tiene anotado para una suscripción concreta.',
}

# El laboratorio del Analizador 2.0 y sus bancos (van al ZIP como anexo).
LAB = ['analizador2', 'analizador_lab', 'hechos_grafico', 'banco_cadena',
       'recorta_grafico', 'cajas_ia', 'eje_precio', 'lee_grafico',
       'afina_velas', 'rejilla_velas', 'flechas', 'mapa_velas',
       'colores_velas', 'agudeza_visual', 'verifica_agudeza',
       'test_analizador2', 'test_eje_precio', 'test_rejilla',
       'banco_analizador', 'corre_banco', 'califica_banco',
       'informe_banco_pdf', 'set_env', 'empaqueta_contexto']

# Direcciones que SÍ pueden aparecer en el ZIP (públicas o de ejemplo).
CORREOS_OK = re.compile(
    r'@(tradeable\.academy|anthropic\.com|example\.(com|org)|demo\.invalid|'
    r'test\.(com|invalid)|x\.com|users\.noreply\.github\.com|'
    r'[a-z0-9.-]*\.invalid|dominio\.com|correo\.com|mail\.com|localhost)$', re.I)
# Direcciones concretas revisadas a mano (2026-11-15) que aparecen en las notas
# viejas y NO son de nadie: ejemplos del alias de Gmail, nombres PROPUESTOS que
# nunca se crearon con el dominio descartado, y un buzón público de CME.
CORREOS_REVISADOS = {
    'juan+2@gmail.com', 'j.u.a.n@gmail.com',
    'support@traderaccelerator.com', 'hola@traderaccelerator.com',
    'traderaccelerator.hq@gmail.com', 'support.traderaccelerator@gmail.com',
    'noreply.traderaccelerator@gmail.com', 'marketdata@cmegroup.com',
}
PATRONES = [
    ('correo', re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+')),
    ('llave OpenAI', re.compile(r'\bsk-[A-Za-z0-9_-]{20,}')),
    ('llave Stripe', re.compile(r'\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{10,}')),
    ('llave Google', re.compile(r'\bAIza[0-9A-Za-z_-]{25,}')),
    ('token GitHub', re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}')),
    ('secreto webhook', re.compile(r'\bwhsec_[A-Za-z0-9]{10,}')),
    ('clave privada', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
]
TEXTO = ('.md', '.py', '.txt', '.conf', '.json', '.js', '.html', '.sh', '.csv',
         '.sql', '.yml', '.yaml', '.css')


def git_files():
    out = subprocess.check_output(['git', 'ls-files'], cwd=RAIZ)
    return [l for l in out.decode('utf-8').splitlines() if l.strip()]


def kb(n):
    if n >= 1024 * 1024:
        return '%.1f MB' % (n / 1048576.0)
    if n >= 1024:
        return '%d KB' % round(n / 1024.0)
    return '%d B' % n


def peso(rel):
    try:
        return os.path.getsize(os.path.join(RAIZ, rel))
    except OSError:
        return 0


def primera_linea(rel):
    """Primera línea útil de la cabecera de una herramienta."""
    try:
        src = io.open(os.path.join(RAIZ, rel), encoding='utf-8',
                      errors='replace').read()
    except OSError:
        return ''
    d = ''
    if rel.endswith('.py'):
        try:
            d = ast.get_docstring(ast.parse(src)) or ''
        except Exception:
            d = ''
    if not d:
        for ln in src.splitlines()[:10]:
            m = re.match(r'\s*(?:#|//|--|\*)\s*(?!-\*-|!)(.{12,})$', ln)
            if m:
                d = m.group(1)
                break
    for ln in d.strip().splitlines():
        ln = ln.strip()
        if ln:
            return ln.replace('|', '/')[:170]
    return ''


def lineas(rel):
    try:
        with io.open(os.path.join(RAIZ, rel), encoding='utf-8',
                     errors='replace') as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def inventario():
    fs = git_files()
    hoy = datetime.date.today().isoformat()
    try:
        rama = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=RAIZ
        ).decode().strip()
        commit = subprocess.check_output(
            ['git', 'log', '-1', '--format=%h · %ad · %s', '--date=short'],
            cwd=RAIZ).decode('utf-8').strip()
    except Exception:
        rama = commit = '?'
    o = []
    w = o.append
    w('# 99 · INVENTARIO DE ARCHIVOS')
    w('')
    w('> **Generado automáticamente** por `tools/empaqueta_contexto.py` el %s.' % hoy)
    w('> Rama `%s` · último commit: %s' % (rama, commit))
    w('> No editar a mano: volver a correr el programa.')
    w('')
    w('**%d archivos** bajo control de versiones.' % len(fs))
    w('')
    # ── por carpeta ──
    w('## Reparto por carpeta')
    w('')
    w('| Carpeta | Archivos | Peso | De qué proyecto |')
    w('|---|---|---|---|')
    tops = {}
    for f in fs:
        t = f.split('/')[0] if '/' in f else '(raíz)'
        a = tops.setdefault(t, [0, 0])
        a[0] += 1
        a[1] += peso(f)
    de = {'scalpel': 'Tradeable (el sitio)', 'tools': 'Tradeable',
          'docs': 'Tradeable (+ manual del bot)', 'deploy': 'Tradeable (+ nginx del bot)',
          'CONTEXTO_TRADEABLE': 'Este expediente', '(raíz)': 'Mezcla (ver doc 19)',
          '.github': 'Bot viejo (workflow peligroso)', 'out': 'Salidas guardadas'}
    for t, (n, p) in sorted(tops.items(), key=lambda kv: -kv[1][0]):
        w('| `%s` | %d | %s | %s |' % (t, n, kb(p), de.get(t, 'Bot viejo')))
    w('')

    # ── scalpel ──
    w('## `scalpel/` — el sitio')
    w('')
    w('### Archivos de primer nivel')
    w('')
    w('| Archivo | Peso |')
    w('|---|---|')
    for f in sorted(x for x in fs if x.startswith('scalpel/') and x.count('/') == 1):
        w('| `%s` | %s |' % (f, kb(peso(f))))
    w('')
    w('### Plantillas (`scalpel/templates/`)')
    w('')
    w('| Plantilla | Líneas | Peso |')
    w('|---|---|---|')
    tp = sorted((x for x in fs if x.startswith('scalpel/templates/')),
                key=lambda x: -peso(x))
    for f in tp:
        w('| `%s` | %d | %s |' % (os.path.basename(f), lineas(f), kb(peso(f))))
    w('')
    w('### Estáticos (`scalpel/static/`)')
    w('')
    w('| Grupo | Archivos | Peso |')
    w('|---|---|---|')
    grupos = {}
    for f in fs:
        if not f.startswith('scalpel/static/'):
            continue
        resto = f[len('scalpel/static/'):]
        if '/' in resto:
            g = resto.split('/')[0] + '/'
        else:
            base = os.path.basename(resto)
            m = re.match(r'(camo_prev|camo_skin|logo[0-9]*|emo|icon|synapse_content)', base)
            g = (m.group(1) + '*') if m else base
        a = grupos.setdefault(g, [0, 0])
        a[0] += 1
        a[1] += peso(f)
    for g, (n, p) in sorted(grupos.items(), key=lambda kv: -kv[1][1]):
        w('| `%s` | %d | %s |' % (g, n, kb(p)))
    w('')

    # ── tools ──
    w('## `tools/` — herramientas, pruebas y laboratorio')
    w('')
    w('🔬 = laboratorio del Analizador 2.0 · 🧪 = prueba · ⚙️ = operación del VPS')
    w('')
    w('| Archivo | Líneas | Qué es (primera línea de su cabecera) |')
    w('|---|---|---|')
    lab = set(LAB)
    for f in sorted(x for x in fs if x.startswith('tools/')):
        base = os.path.basename(f)
        nom = os.path.splitext(base)[0]
        if nom.startswith('check_') and base.endswith('.py'):
            desc, nl = CHECK.get(nom[6:], ''), '—'
            marca = '⚙️ '
        else:
            desc = primera_linea(f) if base.endswith(TEXTO) else ''
            nl = lineas(f) if base.endswith(TEXTO) else '—'
            marca = ('🔬 ' if nom in lab and nom not in ('set_env', 'empaqueta_contexto')
                     else '🧪 ' if nom.startswith(('test_', 'simula_'))
                     else '⚙️ ' if nom.startswith(('set_', 'paypal_', 'preparar_',
                                                    'limpiar_', 'diagnostico_', 'dns_'))
                     else '')
        w('| %s`%s` | %s | %s |' % (marca, f[len('tools/'):], nl, desc or '—'))
    w('')

    # ── docs / deploy ──
    for carpeta, titulo in (('docs/', '`docs/`'), ('deploy/', '`deploy/`')):
        w('## %s' % titulo)
        w('')
        w('| Archivo | Peso |')
        w('|---|---|')
        for f in sorted(x for x in fs if x.startswith(carpeta)):
            w('| `%s` | %s |' % (f, kb(peso(f))))
        w('')

    # ── raíz ──
    w('## Raíz del repositorio')
    w('')
    w('Solo nombre y peso (qué es cada uno: `19_BOT_VIEJO_Y_RAIZ_DEL_REPO.md`).')
    w('')
    w('| Archivo | Peso |')
    w('|---|---|')
    for f in sorted(x for x in fs if '/' not in x):
        w('| `%s` | %s |' % (f, kb(peso(f))))
    w('')
    w('## Resto de carpetas (bot viejo)')
    w('')
    viejos = sorted(t for t in tops if t not in (
        'scalpel', 'tools', 'docs', 'deploy', 'CONTEXTO_TRADEABLE', '(raíz)', 'out'))
    for t in viejos:
        w('- `%s/` — %d archivos' % (t, tops[t][0]))
    w('')
    with io.open(INV, 'w', encoding='utf-8') as f:
        f.write('\n'.join(o))
    print('inventario → %s  (%d archivos)' % (os.path.relpath(INV, RAIZ), len(fs)))


def revisa(nombre, datos):
    """Devuelve la lista de hallazgos sensibles en un archivo de texto."""
    if not nombre.lower().endswith(TEXTO):
        return []
    try:
        txt = datos.decode('utf-8', errors='replace')
    except Exception:
        return []
    mal = []
    for tipo, pat in PATRONES:
        for m in pat.finditer(txt):
            v = m.group(0)
            if tipo == 'correo':
                if (CORREOS_OK.search(v) or v.lower() in CORREOS_REVISADOS
                        or v.lower().endswith(('.png', '.jpg', '.svg'))):
                    continue
                # cosas con forma de correo que no lo son: user@2x, nombres de paquete…
                if re.search(r'@\d', v) or v.split('@')[1].count('.') == 0:
                    continue
            mal.append((tipo, v[:3] + '…' + v[-4:]))
    return mal


def empaqueta():
    hoy = datetime.date.today().isoformat()
    out = os.path.join(RAIZ, 'out')
    if not os.path.isdir(out):
        os.makedirs(out)
    destino = os.path.join(out, 'CONTEXTO_TRADEABLE_%s.zip' % hoy)

    entradas = []        # (ruta en el zip, ruta real)
    for base, _dirs, files in os.walk(CTX):
        for n in sorted(files):
            real = os.path.join(base, n)
            entradas.append((os.path.join('CONTEXTO_TRADEABLE',
                                          os.path.relpath(real, CTX)), real))
    A = 'CONTEXTO_TRADEABLE/anexos/'

    def anexa(rel, sub):
        real = os.path.join(RAIZ, rel)
        if os.path.isfile(real):
            entradas.append((A + sub + '/' + os.path.basename(rel), real))

    for n in ('CLAUDE.md', 'CLAUDE_ARCHIVE.md', 'LANZAMIENTO.md',
              'COPYRIGHT_REGISTRATION_GUIDE.md'):
        anexa(n, 'notas_crudas')
    for n in LAB:
        anexa('tools/%s.py' % n, 'codigo_laboratorio')
    anexa('scalpel/requirements.txt', 'sitio')
    anexa('scalpel/assistant_kb.py', 'sitio')
    anexa('docs/acuerdo_colaboracion.md', 'negocio')
    anexa('docs/prueba_cajas_PASOS.md', 'codigo_laboratorio')
    fs = git_files()
    for f in fs:
        if f.startswith('docs/capturas_prueba/'):
            entradas.append((A + 'capturas_prueba/' + os.path.basename(f),
                             os.path.join(RAIZ, f)))
        elif f.startswith('docs/columnas/'):
            entradas.append((A + 'columnas/' + os.path.basename(f),
                             os.path.join(RAIZ, f)))
        elif f.startswith('docs/banco_resultados'):
            entradas.append((A + 'banco_30_casos/' + f[len('docs/'):],
                             os.path.join(RAIZ, f)))
        elif f.startswith('deploy/nginx/'):
            entradas.append((A + 'nginx/' + os.path.basename(f),
                             os.path.join(RAIZ, f)))

    # 🔴 Nada sale sin pasar por aquí.
    problemas = []
    cargados = []
    for arc, real in entradas:
        with open(real, 'rb') as fh:
            datos = fh.read()
        for tipo, v in revisa(arc, datos):
            problemas.append((arc, tipo, v))
        cargados.append((arc, datos))
    if problemas:
        print('🔴 NO SE CREA EL ZIP: hay datos sensibles en lo que iba dentro.')
        for arc, tipo, v in problemas[:40]:
            print('   %-12s %s   en %s' % (tipo, v, arc))
        sys.exit(2)

    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as z:
        for arc, datos in cargados:
            z.writestr(arc, datos)
    print('zip → %s  (%d archivos, %s)' % (
        os.path.relpath(destino, RAIZ), len(cargados), kb(os.path.getsize(destino))))
    print('   revisado: 0 correos privados, 0 llaves.')
    return destino


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo-inventario', action='store_true')
    a = ap.parse_args()
    inventario()
    if not a.solo_inventario:
        empaqueta()


if __name__ == '__main__':
    main()
