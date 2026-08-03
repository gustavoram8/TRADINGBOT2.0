# -*- coding: utf-8 -*-
"""Comprueba el correo saliente ANTES de confiarle los OTP y los reseteos.

Por qué hace falta: si el SMTP está mal configurado la app NO se cae — escribe
un aviso en el log y sigue. O sea que el registro parece funcionar mientras
ningún usuario recibe su código. Esto lo saca a la luz en 20 segundos.

Qué hace, en orden:
  1. resuelve los MX del dominio del remitente (si no hay MX, nadie te escribe);
  2. lee SPF, DKIM y DMARC en el DNS (sin ellos, todo cae en spam);
  3. se conecta al SMTP y AUTENTICA;
  4. si le pasas --enviar, manda un correo de prueba al buzón de avisos.

Nunca imprime la contraseña.

    cd /var/www/TRADINGBOT2.0
    python3 tools/check_mail.py            # solo diagnóstico
    python3 tools/check_mail.py --enviar   # además manda uno de prueba
"""
import os
import smtplib
import ssl
import subprocess
import sys
from email.message import EmailMessage


def _dotenv(path='scalpel/.env'):
    out = {}
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


HAY_DNS = None          # None = todavía no se sabe; False = sin herramientas


def dig(nombre, tipo):
    """Consulta DNS con las herramientas del sistema, sin dependencias.

    Devuelve la lista de respuestas, [] si el registro no existe, o None si no
    se pudo consultar. Distinguir "no existe" de "no pude mirar" importa: lo
    primero es un problema de configuración y lo segundo, de esta máquina.
    """
    global HAY_DNS
    for cmd in (['dig', '+short', tipo, nombre],
                ['host', '-t', tipo, nombre],
                ['nslookup', '-type=' + tipo, nombre]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        HAY_DNS = True
        if out.returncode == 0:
            return [l.strip() for l in out.stdout.splitlines() if l.strip()]
        return []
    HAY_DNS = False
    return None


def _smtp(passwd, cuenta, servidor, puerto, avisos, problemas):
    """Conecta, autentica y (con --enviar) manda un correo de prueba."""
    print('\n── SMTP ──')
    if not passwd:
        print('  (sin contraseña no se puede probar el envío)')
        return 1
    try:
        with smtplib.SMTP(servidor, puerto, timeout=25) as s:
            s.ehlo()
            s.starttls(context=ssl.create_default_context())
            s.ehlo()
            s.login(cuenta, passwd)
            print('  ✅ conexión y autenticación correctas')
            if '--enviar' in sys.argv:
                m = EmailMessage()
                m['Subject'] = 'Prueba de correo — Tradeable Academy'
                m['From'] = cuenta
                m['To'] = avisos
                m.set_content(
                    'Si estás leyendo esto, el correo saliente del sitio '
                    'funciona.\n\nRemitente: %s\nSMTP: %s:%d\n'
                    % (cuenta, servidor, puerto))
                s.send_message(m)
                print('  ✅ correo de prueba enviado a %s' % avisos)
                print('     (si no llega en 2 minutos, mirá la carpeta de spam '
                      '— eso significaría que falta SPF/DKIM)')
    except smtplib.SMTPAuthenticationError:
        print('  ⛔ el servidor RECHAZÓ las credenciales.')
        print('     Con Gmail/Workspace hay que usar una "contraseña de '
              'aplicación" (16 caracteres), no la contraseña normal, y tener '
              'la verificación en dos pasos activada en esa cuenta.')
        return 1
    except Exception as e:
        print('  ⛔ no se pudo conectar: %s: %s' % (e.__class__.__name__, e))
        return 1

    print()
    if problemas:
        print('⚠️  Envía, pero con esto pendiente: %s.' % ', '.join(problemas))
        print('    Mientras falte SPF/DKIM, buena parte de tus correos van a '
              'spam — y un código de verificación en spam es un registro perdido.')
        return 1
    print('✅ Todo en orden.')
    return 0


def main():
    env = _dotenv()
    def var(k, d=''):
        return (os.environ.get(k) or env.get(k, d)).strip()

    cuenta = var('MAIL_USERNAME', 'mauroramirezmij@gmail.com')
    passwd = var('MAIL_APP_PASSWORD')
    servidor = var('MAIL_SERVER', 'smtp.gmail.com')
    puerto = int(var('MAIL_PORT', '587') or 587)
    avisos = var('ADMIN_EMAIL') or cuenta
    dominio = cuenta.split('@')[-1]

    print('Remitente : %s' % cuenta)
    print('Avisos a  : %s' % avisos)
    print('SMTP      : %s:%d' % (servidor, puerto))
    print('Contraseña: %s' % ('presente (%d caracteres)' % len(passwd) if passwd
                              else 'FALTA — la app no envía nada'))
    if '@' not in cuenta:
        print('\n⛔ MAIL_USERNAME no parece un correo.')
        return 1

    problemas = []
    print('\n── DNS de %s ──' % dominio)
    mx = dig(dominio, 'MX')
    if HAY_DNS is False:
        print('  (no hay dig/host/nslookup en esta máquina: DNS SIN COMPROBAR.')
        print('   Instalá `dnsutils` o corré esto en el VPS.)')
    if mx:
        print('  MX    : %s' % '; '.join(mx[:4]))
        if not any('google' in m.lower() or 'aspmx' in m.lower() for m in mx) \
           and 'gmail.com' not in dominio:
            print('          ⚠️  no parecen los de Google Workspace')
    elif mx == []:
        print('  MX    : ninguno — a este dominio NO le puede llegar correo')
        problemas.append('sin MX')

    txt = dig(dominio, 'TXT')
    if txt is None:
        print('  SPF/DMARC/DKIM: sin comprobar')
        return _smtp(passwd, cuenta, servidor, puerto, avisos, problemas)
    txt = txt or []
    spf = [t for t in txt if 'v=spf1' in t]
    print('  SPF   : %s' % (spf[0][:110] if spf else 'FALTA → tus correos caen en spam'))
    if not spf:
        problemas.append('sin SPF')
    if len(spf) > 1:
        print('          ⚠️  hay MÁS DE UN SPF; el estándar solo admite uno y '
              'los servidores lo tratan como error')
        problemas.append('SPF duplicado')

    dmarc = dig('_dmarc.' + dominio, 'TXT')
    print('  DMARC : %s' % (dmarc[0][:110] if dmarc else 'FALTA → recomendado'))
    if not dmarc:
        problemas.append('sin DMARC')

    dkim = dig('google._domainkey.' + dominio, 'TXT')
    print('  DKIM  : %s' % ('publicado' if dkim else
                            'FALTA (o usa otro selector) → firma tus correos '
                            'desde la consola de Workspace'))
    if not dkim:
        problemas.append('sin DKIM')

    return _smtp(passwd, cuenta, servidor, puerto, avisos, problemas)


if __name__ == '__main__':
    sys.exit(main())
