# -*- coding: utf-8 -*-
"""Manda TODOS los correos que un usuario puede recibir, a una dirección tuya.

Para revisarlos con tus propios ojos — asunto, texto, logo, Reply-To — sin
tener que provocar cada situación de verdad. Se corre EN EL VPS (ahí están las
credenciales del correo):

    python3 tools/manda_correos_prueba.py tradeableacademy@gmail.com
    python3 tools/manda_correos_prueba.py tradeableacademy@gmail.com en

El segundo argumento es el idioma (es/en/fr/pt; por defecto es). Manda 7
correos: verificación, restablecer contraseña, aviso de seguridad, recibo de
plan, recibo de cosmético, bienvenida y constancia de baja. Ninguno toca la
base de datos: los "usuarios" son de mentira, solo cambia el destinatario.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'scalpel'))
import app as A                # noqa: E402


def main():
    if len(sys.argv) < 2 or '@' not in sys.argv[1]:
        print(__doc__)
        return 1
    destino = sys.argv[1]
    lang = (sys.argv[2] if len(sys.argv) > 2 else 'es').lower()
    if lang not in ('en', 'es', 'fr', 'pt'):
        print('✗ Idioma no soportado: %s (usa en/es/fr/pt)' % lang)
        return 1
    if not A.app.config.get('MAIL_PASSWORD'):
        print('✗ El correo no está configurado (MAIL_APP_PASSWORD vacío).')
        return 1

    # Un usuario de mentira: las funciones solo le leen atributos.
    u = SimpleNamespace(
        username='Mauro', email=destino, plan='premium',
        plan_expires_at=datetime.now(timezone.utc) + timedelta(days=23,
                                                              hours=3))
    enviados = fallos = 0

    def manda(nombre, fn):
        nonlocal enviados, fallos
        try:
            with A.app.test_request_context(
                    '/', headers={'Cookie': 'scalpel_lang=%s' % lang,
                                  'User-Agent': 'Correo de prueba'}):
                ok = fn()
            print('  %s %s' % ('✓' if ok else '✗', nombre))
            enviados += bool(ok)
            fallos += not ok
        except Exception as exc:
            print('  ✗ %s — %s' % (nombre, exc))
            fallos += 1

    print('Mandando la colección a %s (idioma %s)…' % (destino, lang))
    with A.app.app_context():
        manda('1/7 verificación de registro',
              lambda: A.send_verification_email(destino, '482913'))
        manda('2/7 restablecer contraseña',
              lambda: A.send_reset_email(
                  destino, 'https://tradeable.academy/reset/EJEMPLO'))
        manda('3/7 aviso de seguridad (dispositivo nuevo)',
              lambda: A.send_security_email(u, 'new_device'))
        manda('4/7 recibo de PLAN (con la nota de renovación)',
              lambda: A.send_receipt_email(destino, 'Premium', 50.0,
                                           'plan-412', es_plan=True))
        manda('5/7 recibo de COSMÉTICO (sin nota de plan)',
              lambda: A.send_receipt_email(destino, 'F1 Blueprint (camo)',
                                           1.99, 'camo-88'))
        manda('6/7 bienvenida', lambda: A.send_welcome_email(u))
        manda('7/7 constancia de baja', lambda: A.send_cancel_email(u))

    print('\n%d enviados, %d fallos. Revisa la bandeja (y el spam, por si '
          'acaso) de %s.' % (enviados, fallos, destino))
    return 0 if not fallos else 1


if __name__ == '__main__':
    sys.exit(main())
