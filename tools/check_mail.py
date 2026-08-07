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


def _smtp(passwd, cuenta, remitente, servidor, puerto, avisos, problemas):
    """Conecta, autentica y (con --enviar) manda un correo de prueba."""
    print('\n── SMTP ──')
    if not passwd:
        print('  (sin contraseña no se puede probar el envío)')
        return 1
    # El 465 es SSL desde el primer byte; el 587 empieza en claro y sube con
    # STARTTLS. Hacerlo al revés no da un error legible: la conexión se cuelga.
    ssl_directo = puerto == 465
    print('  modo: %s (puerto %d)' % ('SSL' if ssl_directo else 'STARTTLS',
                                      puerto))
    try:
        ctx = ssl.create_default_context()
        abrir = ((lambda: smtplib.SMTP_SSL(servidor, puerto, timeout=25,
                                           context=ctx))
                 if ssl_directo else
                 (lambda: smtplib.SMTP(servidor, puerto, timeout=25)))
        with abrir() as s:
            s.ehlo()
            if not ssl_directo:
                s.starttls(context=ctx)
                s.ehlo()
            s.login(cuenta, passwd)
            print('  ✅ conexión y autenticación correctas')
            if '--enviar' in sys.argv:
                m = EmailMessage()
                m['Subject'] = 'Prueba de correo — Tradeable Academy'
                m['From'] = remitente
                m['To'] = avisos
                m.set_content(
                    'Si estás leyendo esto, el correo saliente del sitio '
                    'funciona.\n\nRemitente: %s\nSMTP: %s:%d (usuario %s)\n'
                    % (remitente, servidor, puerto, cuenta))
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
    # El usuario SMTP y el remitente pueden ser distintos (Resend/Brevo usan
    # una etiqueta o una API key como usuario). El DNS se revisa contra el
    # dominio del REMITENTE, que es lo que mira quien recibe el correo.
    remitente = var('MAIL_FROM') or cuenta
    passwd = var('MAIL_APP_PASSWORD')
    servidor = var('MAIL_SERVER', 'smtp.gmail.com')
    puerto = int(var('MAIL_PORT', '587') or 587)
    avisos = var('ADMIN_EMAIL') or remitente
    dominio = remitente.split('@')[-1]

    print('Usuario   : %s' % cuenta)
    print('Remitente : %s' % remitente)
    print('Avisos a  : %s' % avisos)
    print('SMTP      : %s:%d' % (servidor, puerto))
    print('Contraseña: %s' % ('presente (%d caracteres)' % len(passwd) if passwd
                              else 'FALTA — la app no envía nada'))
    if '@' not in remitente:
        print('\n⛔ El remitente (MAIL_FROM / MAIL_USERNAME) no es un correo.')
        return 1

    problemas = []
    print('\n── DNS de %s ──' % dominio)
    mx = dig(dominio, 'MX')
    if HAY_DNS is False:
        print('  (no hay dig/host/nslookup en esta máquina: DNS SIN COMPROBAR.')
        print('   Instalá `dnsutils` o corré esto en el VPS.)')
    if mx:
        print('  MX    : %s' % '; '.join(mx[:4]))
        junto = ' '.join(mx).lower()
        # Reconocer al proveedor, no dar por hecho que es Google. Y avisar del
        # choque clásico: los MX de Cloudflare Email Routing conviven mal con
        # los de un buzón real — si están los dos, el correo se pierde.
        quien = ('Google Workspace' if 'aspmx' in junto or 'google' in junto else
                 'Zoho' if 'zoho' in junto else
                 'Microsoft 365' if 'outlook' in junto or 'protection' in junto else
                 'Cloudflare Email Routing' if 'mx.cloudflare.net' in junto else None)
        if quien:
            print('          proveedor detectado: %s' % quien)
        if 'mx.cloudflare.net' in junto and quien != 'Cloudflare Email Routing':
            print('          ⛔ hay MX de Cloudflare Email Routing MEZCLADOS con '
                  'los de tu buzón: desactivá el routing o perderás correo')
            problemas.append('MX mezclados')
    elif mx == []:
        print('  MX    : ninguno — a este dominio NO le puede llegar correo')
        problemas.append('sin MX')

    txt = dig(dominio, 'TXT')
    if txt is None:
        print('  SPF/DMARC/DKIM: sin comprobar')
        return _smtp(passwd, cuenta, remitente, servidor, puerto, avisos, problemas)
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

    # El DKIM vive bajo un "selector" que elige CADA proveedor: Google usa
    # `google`, Zoho `zmail`, Resend `resend`… Buscar solo el de Google daba un
    # "FALTA" mentiroso en cualquier otro proveedor, así que se prueban todos
    # los habituales y se informa cuál está publicado.
    SELECTORES = [('google', 'Google Workspace'), ('zmail', 'Zoho'),
                  ('zoho', 'Zoho'), ('resend', 'Resend'), ('mail', 'Brevo'),
                  ('s1', 'genérico'), ('k1', 'Mailchimp/Mandrill'),
                  ('default', 'genérico')]
    hallado = None
    for sel, quien in SELECTORES:
        if dig('%s._domainkey.%s' % (sel, dominio), 'TXT'):
            hallado = (sel, quien)
            break
    if hallado:
        print('  DKIM  : publicado (selector "%s" — %s)' % hallado)
    else:
        print('  DKIM  : no encontrado en los selectores habituales (%s).'
              % ', '.join(s for s, _ in SELECTORES))
        print('          Publicá el TXT que te da tu proveedor y, en su panel, '
              'ACTIVÁ la firma: publicarlo sin activarla no sirve de nada.')
        problemas.append('sin DKIM')

    return _smtp(passwd, cuenta, remitente, servidor, puerto, avisos, problemas)


if __name__ == '__main__':
    sys.exit(main())
