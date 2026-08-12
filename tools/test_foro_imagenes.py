# -*- coding: utf-8 -*-
"""Punto 18 — subidas de imagen al foro: qué entra y qué no.

    venv/bin/python3 tools/test_foro_imagenes.py

La decisión de "es un gráfico / es porno" la toma la IA y eso no se puede
probar sin gastar llamadas; lo que SÍ se prueba aquí es todo lo que rodea a
esa decisión, que es donde viven los bugs de verdad:

  · que cada categoría del moderador termina en el código de error correcto
    (offtopic → 'not_chart' con mensaje amable; sexual/drugs/weapons/violence/
    signal → 'content', mensaje seco y sin detalle);
  · que la advertencia se anota con LA CATEGORÍA, no con un 'image' genérico
    (es lo que deja al panel distinguir la foto equivocada del porno);
  · que un bloqueo no deja el archivo en disco ni crea el post;
  · que formato malo y tamaño excesivo se rechazan ANTES de pagar una llamada
    de IA;
  · que si la IA se cae, la subida pasa (fail-open — decisión vieja del
    sistema: una caída del moderador no puede tumbar el foro entero);
  · que el prompt conserva sus cláusulas obligatorias (si alguien lo edita y
    borra una categoría, esto lo caza);
  · paridad i18n de los mensajes nuevos ×4 idiomas.
"""
from __future__ import print_function

import io
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'fi.db')
os.environ.setdefault('SECRET_KEY', 'foro-img')
sys.path.insert(0, os.path.join(RAIZ, 'scalpel'))

import app as A                                           # noqa: E402

CLAVE = 'Zx9!wQ4mNp2r'
OK = FALLOS = 0


def check(cond, texto):
    global OK, FALLOS
    print(('  ✅ ' if cond else '  ❌ ') + texto)
    if cond:
        OK += 1
    else:
        FALLOS += 1


# PNG mínimo válido (1×1), sin depender de Pillow.
PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
       b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf'
       b'\xc0\xf0\x1f\x00\x05\x05\x02\x00\x9d\xb6\xdd\x94\x00\x00\x00\x00IEND'
       b'\xaeB`\x82')


def cliente():
    c = A.app.test_client()
    c.post('/login', data={'identifier': 'forera', 'password': CLAVE},
           follow_redirects=True)
    return c


def postea(c, titulo, con_imagen=True):
    data = {'title': titulo, 'body': 'Looking at this setup on NQ, thoughts?'}
    if con_imagen:
        data['image'] = (io.BytesIO(PNG), 'chart.png', 'image/png')
    return c.post('/forum/post', data=data,
                  content_type='multipart/form-data')


def moderador_fijo(respuesta, contador):
    def falso(b64, ct):
        contador.append(1)
        return dict(respuesta)
    return falso


def main():
    global OK, FALLOS
    with A.app.app_context():
        A.db.create_all()
        u = A.User(username='forera', email='forera@demo.invalid',
                   email_verified=True)
        u.set_password(CLAVE)
        u.email_canonical = u.email
        u.plan = 'standard'
        A.db.session.add(u)
        A.db.session.commit()
        uid = u.id

    original = A.moderate_forum_image
    carpeta = os.path.join(A.BASE_DIR, 'static', 'uploads', 'forum')
    archivos = lambda: set(os.listdir(carpeta)) if os.path.isdir(carpeta) else set()

    print('\n══ 1 · imagen permitida (un gráfico, o una captura del sitio) ══')
    llamadas = []
    A.moderate_forum_image = moderador_fijo({'ok': True, 'category': 'ok', 'reason': ''}, llamadas)
    antes = archivos()
    c = cliente()
    r = postea(c, 'My NQ setup from this morning')
    check(r.status_code == 200, 'el post con imagen se publica (%s)' % r.status_code)
    check(len(archivos() - antes) == 1, 'la imagen queda guardada en disco')
    with A.app.app_context():
        check(A.ModWarning.query.filter_by(user_id=uid).count() == 0,
              'una subida legítima NO anota ninguna advertencia')

    print('\n══ 2 · foto equivocada (offtopic) → not_chart, mensaje amable ══')
    llamadas = []
    A.moderate_forum_image = moderador_fijo(
        {'ok': False, 'category': 'offtopic', 'reason': 'personal photo'}, llamadas)
    antes = archivos()
    r = postea(c, 'Check this out')
    d = r.get_json() or {}
    check(r.status_code == 422 and d.get('reason') == 'not_chart',
          "offtopic responde 422 'not_chart' (%s %s)" % (r.status_code, d.get('reason')))
    check(archivos() == antes, 'el archivo NO se guarda')
    with A.app.app_context():
        w = (A.ModWarning.query.filter_by(user_id=uid)
             .order_by(A.ModWarning.id.desc()).first())
        check(w is not None and w.reason == 'offtopic',
              'la advertencia lleva la categoría del moderador (%s)'
              % (w.reason if w else None))
        check(A.ForumPost.query.filter_by(user_id=uid).count() == 1,
              'el post bloqueado no se crea (sigue habiendo 1)')

    print('\n══ 3 · contenido vetado → content, sin detalle ══')
    for cat in ('sexual', 'drugs', 'weapons', 'violence', 'signal'):
        # ⚠️ Cada bloqueo del moderador SUMA para el silenciado automático (4
        # en 10 min = mute) — correcto en producción, pero aquí encadenamos 6
        # bloqueos en un segundo y a partir del 4º todo daría 403 'muted'. Se
        # limpia el estado entre categorías; el automute tiene su propia
        # sección más abajo, como conducta DESEADA y no como estorbo.
        with A.app.app_context():
            A.ModWarning.query.filter_by(user_id=uid).delete()
            A.db.session.get(A.User, uid).muted_until = None
            A.db.session.commit()
        llamadas = []
        A.moderate_forum_image = moderador_fijo(
            {'ok': False, 'category': cat, 'reason': 'x'}, llamadas)
        antes = archivos()
        r = postea(c, 'Interesting chart today maybe')
        d = r.get_json() or {}
        bien = (r.status_code == 422 and d.get('reason') == 'content'
                and archivos() == antes)
        with A.app.app_context():
            w = (A.ModWarning.query.filter_by(user_id=uid)
                 .order_by(A.ModWarning.id.desc()).first())
            bien = bien and w is not None and w.reason == cat
        check(bien, "categoría '%s' → 422 'content' + advertencia con su nombre" % cat)

    print('\n══ 3b · insistir con imágenes vetadas → silenciado automático ══')
    with A.app.app_context():
        A.ModWarning.query.filter_by(user_id=uid).delete()
        A.db.session.get(A.User, uid).muted_until = None
        A.db.session.commit()
    A.moderate_forum_image = moderador_fijo(
        {'ok': False, 'category': 'sexual', 'reason': 'x'}, [])
    ultimo = None
    for _ in range(6):
        ultimo = postea(c, 'Trying again with another chart')
        if ultimo.status_code == 403:
            break
    d = ultimo.get_json() or {}
    check(ultimo.status_code == 403 and d.get('error') == 'muted',
          'el que insiste queda muteado (%s %s)' % (ultimo.status_code, d.get('error')))
    with A.app.app_context():
        A.ModWarning.query.filter_by(user_id=uid).delete()
        A.db.session.get(A.User, uid).muted_until = None
        A.db.session.commit()

    print('\n══ 4 · formato y tamaño se rechazan SIN pagar IA ══')
    llamadas = []
    A.moderate_forum_image = moderador_fijo({'ok': True, 'category': 'ok', 'reason': ''}, llamadas)
    r = c.post('/forum/post', data={
        'title': 'gif attempt', 'body': 'body body body',
        'image': (io.BytesIO(b'GIF89a....'), 'x.gif', 'image/gif'),
    }, content_type='multipart/form-data')
    d = r.get_json() or {}
    check(r.status_code == 422 and d.get('reason') == 'format' and not llamadas,
          'GIF → format, 0 llamadas al moderador')
    gorda = PNG + b'\x00' * (8 * 1024 * 1024)
    r = c.post('/forum/post', data={
        'title': 'huge file', 'body': 'body body body',
        'image': (io.BytesIO(gorda), 'x.png', 'image/png'),
    }, content_type='multipart/form-data')
    d = r.get_json() or {}
    check(r.status_code == 422 and d.get('reason') == 'too_large' and not llamadas,
          '>8MB → too_large, 0 llamadas al moderador')

    print('\n══ 5 · la IA caída NO tumba el foro (fail-open, decisión vieja) ══')
    A.moderate_forum_image = original
    cliente_real = A.client

    class Roto:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    raise RuntimeError('API down')
    A.client = Roto
    try:
        with A.app.test_request_context('/'):
            res = A.moderate_forum_image('x', 'image/png')
        check(res['ok'] and res['category'] == 'ok',
              'moderador caído → la imagen pasa (ok=%s)' % res['ok'])
    finally:
        A.client = cliente_real

    print('\n══ 6 · el parser aguanta las respuestas raras del modelo ══')
    p = A._parse_mod_json
    check(p('{"allowed": false, "category": "drugs", "reason": "pills"}')['category'] == 'drugs',
          'JSON limpio con categoría')
    check(p('```json\n{"allowed": false, "category": "sexual", "reason": "n"}\n```')['category'] == 'sexual',
          'JSON envuelto en markdown')
    viejo = p('{"allowed": false, "reason": "meme"}')
    check(viejo['ok'] is False and viejo['category'] == 'ok',
          'respuesta SIN categoría (formato viejo) → bloquea como not_chart')
    check(p('garbage not json')['ok'] is True, 'basura → fail-open')

    print('\n══ 7 · el prompt conserva sus cláusulas obligatorias ══')
    P = A.FORUM_IMAGE_MOD_PROMPT
    for frase, motivo in [
        ('Tradeable Academy platform itself', 'permite capturas del propio sitio'),
        ('"drugs"', 'categoría drogas'),
        ('"weapons"', 'categoría armas'),
        ('"sexual"', 'categoría desnudos'),
        ('"violence"', 'categoría violencia'),
        ('"signal"', 'categoría venta de señales'),
        ('NOT financial advice', 'SL/TP propios no son asesoría (anti-sobre-censura)'),
        ('When genuinely uncertain', 'en la duda, permitir (anti-sobre-censura)'),
        ('never allow anything that fits', 'la duda NO aplica a lo vetado'),
    ]:
        check(frase in P, 'el prompt dice: %s' % motivo)

    print('\n══ 7b · el prompt de TEXTO sabe que la plataforma es on-topic ══')
    # 🔴 Lo cazó el dueño: subió una captura del quiz con el mensaje "¿Qué les
    # parece mi camo?" y lo bloqueó el moderador de TEXTO por "unrelated to
    # trading". Se arregló el prompt de imágenes en el punto 18 y se olvidó el
    # de texto, que es el que corre PRIMERO.
    TP = A.FORUM_TEXT_MOD_PROMPT
    for frase, motivo in [
        ('THE PLATFORM ITSELF IS ON-TOPIC', 'declara la plataforma como tema válido'),
        ('camo', 'camos'),
        ('roulette', 'ruleta'),
        ('ranks, XP', 'rangos y XP'),
        ('Chalkboard', 'pizarra'),
        ('bugs, feature requests', 'reportes y sugerencias'),
        ('greetings, introductions', 'saludos y presentaciones'),
        ('UNRELATED to trading or markets AND unrelated to this platform',
         'el bloqueo por off-topic exige que TAMPOCO sea de la plataforma'),
    ]:
        check(frase in TP, 'el prompt de texto cubre: %s' % motivo)

    print('\n══ 8 · i18n ×4 ══')
    html = io.open(os.path.join(RAIZ, 'scalpel', 'templates', 'index.html'),
                   encoding='utf-8').read()
    check(html.count("'forum.img.content':") == 4, "clave 'forum.img.content' en los 4 dicts")
    check(html.count("'forum.img.blocked':") == 4, "clave 'forum.img.blocked' en los 4 dicts")
    check("data.reason === 'content'" in html, "el cliente mapea el código 'content'")

    A.moderate_forum_image = original
    print('\nRESULTADO: %d/%d' % (OK, OK + FALLOS))
    return 0 if FALLOS == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
