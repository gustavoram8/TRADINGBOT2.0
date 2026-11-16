# 04 · INFRAESTRUCTURA Y DEPLOY

> ⚠️ Nada de esto se pudo comprobar en vivo al escribir el expediente (no hay
> acceso al VPS desde donde se redactó). Es lo que consta en las notas y en los
> archivos del repo. La sección final trae los comandos para **verificar el
> estado real** en el servidor.

## El camino de una visita

```
Visitante → Cloudflare (DNS + proxy + caché, SSL "Full (strict)")
          → VPS Contabo 62.171.180.22
          → nginx (puerto 443, certificado Let's Encrypt)
              ├─ /static/…  → lo sirve nginx directo (caché 7 días)
              └─ todo lo demás → proxy a gunicorn en 127.0.0.1:5001
          → gunicorn (4 workers × 4 hilos) corriendo scalpel/app.py
          → PostgreSQL (local, en el mismo VPS)
```

## El servidor

| Dato | Valor |
|---|---|
| Proveedor | Contabo (VPS) |
| IP | `62.171.180.22` |
| RAM | 7,8 GB + 2 GB de swap (`/swapfile`, en `/etc/fstab`) |
| Zona horaria del sistema | Europa/Berlín (⚠️ por eso PostgreSQL se fuerza a UTC) |
| Carpeta del proyecto | `/var/www/TRADINGBOT2.0` |
| Entorno Python | `venv/` dentro del proyecto (`venv/bin/python3`) |
| Gestor de procesos | **supervisor**. Proceso: **`traderacelerator`** (una sola "c") |
| Config de supervisor | `/etc/supervisor/conf.d/*trader*.conf` |
| gunicorn | `--max-requests 300 --max-requests-jitter 50 -w 4 --threads 4 -k gthread`, arranca `scalpel.app:app` |
| Logs | `/var/log/trader.out.log` (y `*trader*.log`) |
| Otro inquilino del VPS | El bot viejo en `/opt/tradingbot` — **apagado, intocable** (ver doc 19) |
| Puerto 25 saliente | Bloqueado por Contabo (por eso el correo no sale desde el VPS) |

**Por qué `--max-requests`:** hubo caídas por una fuga lenta de memoria; los
workers se reciclan cada ~300 peticiones. No era falta de RAM.

**Capacidad medida (parcial):** 432 peticiones/s en `/login` sin fallos; 500
conexiones simultáneas sin caerse. **No está probado** cómo responde con 500
usuarios reales con sesión iniciada (la prueba completa quedó pendiente).

## Dominio, DNS y HTTPS

- **Dominio:** `tradeable.academy` (comprado el 2026-07-30).
- **DNS en Cloudflare:** registros A de `@` y `www` → la IP del VPS, con el
  proxy naranja encendido. SSL en modo **Full (strict)** — nunca "Flexible"
  (produce un bucle de redirecciones) ni "Automatic".
- **Certificado:** Let's Encrypt en el VPS, renovado solo por `certbot.timer`.
- **Registros de correo** en Cloudflare: MX, SPF, DKIM (selector `default`),
  DMARC. Se gestionan por terminal con `tools/dns_cf.py`.
- 🔴 **El registro TXT `google-site-verification` no se borra nunca:** si
  desaparece, Google desverifica el dominio y se pierde Search Console.
- ⚠️ El servidor de correo (del papá del dueño) tiene su propia zona DNS de
  `tradeable.academy`. **Jamás usar esos nameservers:** la web se caería.

## Los cuatro estados de nginx (`deploy/nginx/`)

| Archivo | Qué hace | robots.txt |
|---|---|---|
| `tradeable.academy.conf` | Solo la página de "en construcción" | Disallow |
| `tradeable.academy.preview.conf` | La app solo para quien traiga un "pase" | Disallow |
| `tradeable.academy.abierto.conf` | La app para todos, sin indexar | Disallow |
| **`tradeable.academy.live.conf`** | **La app para todos, indexable** | **Allow** |

Según las notas, hoy está activa la **live** (la portada fue aceptada por
Google el 2026-08-14). Cambiar de estado = copiar el archivo a
`/etc/nginx/sites-available/tradeable.academy`, `nginx -t` y
`systemctl reload nginx`; después re-ejecutar certbot (el archivo copiado pisa
las líneas del certificado) — la receta está en la cabecera de cada `.conf`.

🔴 **Tras tocar nginx, comprobar siempre:**
`curl -s https://tradeable.academy/robots.txt` — tres de las cuatro configs
bloquean a Google, y ese fallo no da ningún error.

⚠️ `nginx -t` dice "el archivo es válido", **no** "es el que está cargado".

## Cómo se despliega un cambio

```bash
cd /var/www/TRADINGBOT2.0
git pull origin claude/gallant-volta-i7cqmf
supervisorctl restart traderacelerator
```

- Sin el `restart`, lo subido **no se refleja** en producción.
- 🔴 **Si cambió la config de supervisor** (por ejemplo, una variable de
  entorno): usar `supervisorctl reread && supervisorctl update` y **NO**
  encadenar `restart` detrás. `update` ya reinicia; el segundo reinicio mata a
  gunicorn a mitad del arranque y el sitio da **502** unos 40 segundos.
- Los archivos estáticos llevan `?v=<fecha de modificación>` (helper
  `estatico()`), así que un cambio de CSS/JS/imagen se ve aunque nginx y
  Cloudflare cacheen 7 días. Si algo estático no usa ese helper, hay que
  **purgar la caché de Cloudflare**.
- Al arrancar, la app corre sola `init_db()`: crea tablas nuevas y aplica las
  migraciones de columnas. No hay un paso de migración manual.

## Variables de entorno

**Dónde viven:** en la línea `environment=` de la config de supervisor (**ahí
es donde producción las lee de verdad**; bajo gunicorn el `.env` no se carga) y
en `scalpel/.env` (lo leen las herramientas de `tools/`). **Deben estar
iguales en los dos sitios.**

**Cómo se cambian sin editor:**
```bash
python3 tools/set_env.py NOMBRE=valor      # escribe en los dos sitios, hace copia, no imprime el valor
python3 tools/set_env.py --quitar NOMBRE
supervisorctl reread && supervisorctl update
```

🔴 **No hacer `grep` sobre la línea `environment=`**: imprime TODOS los
secretos juntos. Así se filtraron al chat el 2026-08-13.

### Catálogo (solo nombres; los valores no están en este expediente)

**Núcleo**
| Variable | Qué controla | Si falta |
|---|---|---|
| `SECRET_KEY` | Firma de sesiones y enlaces | Se genera y guarda en `scalpel/.secret_key` |
| `DATABASE_URL` | Conexión a PostgreSQL | Usa SQLite local |
| `SITE_URL` | Dirección oficial (`https://tradeable.academy`) para enlaces absolutos | Usa el Host de cada petición |
| `PUBLIC_HTTPS` | `1` = detrás de nginx con HTTPS: ProxyFix + cookies seguras | Sin esto el login por dominio no es seguro |
| `PREVIEW_USERS` | Lista de usuarios que ven el sitio; el resto ve "próximamente" | Sitio abierto (estado actual) |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Cuenta admin que se crea si no existe | ⚠️ Hay valores por defecto en el código — ver doc 13 |
| `SENTRY_DSN` | Seguimiento de errores | Apagado |
| `PORT`, `FLASK_ENV`, `FLASK_DEBUG` | Solo desarrollo local | — |

**Inteligencia artificial**
| Variable | Qué controla | Por defecto |
|---|---|---|
| `OPENAI_API_KEY` | Usa la API de pago de OpenAI | Sin ella cae a GitHub Models |
| `GITHUB_TOKEN` | Respaldo gratuito (GitHub Models) | — |
| `SCALPEL_MODEL` | Modelo del analizador | `gpt-4o` |
| `ANALYZE_VERIFY_CLAIMS` | Cláusula "verifica antes de afirmar" | `0` en código; **`1` en producción** |
| `ANALYZE_IMG_MAX_PX` / `_DETAIL` / `_HARD_PX` | Tamaño máximo de la captura enviada | 1280 / high / 8000 |
| `AI_PRICE_IN_PER_1M`, `AI_PRICE_OUT_PER_1M` | Tarifas para estimar gasto | 2.50 / 10.0 |
| `ASSISTANT_MODEL`, `ASSISTANT_MAX_TOKENS`, `ASSISTANT_PER_HOUR`, `ASSISTANT_PER_DAY`, `ASSISTANT_PRICE_*` | Asistente Tessera | gpt-4o-mini / 320 / 25 / 80 |
| `GEMINI_API_KEY` | **Solo laboratorio** (la app no la usa) | — |

**Pagos**
| Variable | Qué controla |
|---|---|
| `PAYPAL_CLIENT_ID`, `PAYPAL_SECRET` | Enciende PayPal |
| `PAYPAL_ENV` | `live` o `sandbox` (⚠️ **por defecto es `live`**) |
| `PAYPAL_WEBHOOK_ID` | Verificar avisos; obligatorio para suscripciones |
| `PAYPAL_PLAN_STANDARD`, `PAYPAL_PLAN_PREMIUM` | Ids de los planes de suscripción |
| `PAYPAL_BRAND_NAME`, `PAYPAL_RECEIPT_NAME` | Nombre mostrado al comprador |
| `PAYPAL_FEE_PCT`, `PAYPAL_FEE_FIXED` | Estimación de comisión (5,4% + $0,30) |
| `CRYPTO_API_KEY`, `CRYPTO_IPN_SECRET`, `CRYPTO_API_BASE`, `CRYPTO_PAY_CURRENCY`, `USDT_ENABLED` | NOWPayments / USDT |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Stripe (apagado) |
| `ANNUAL_PLANS_ENABLED` | Planes anuales (`0`) |
| `LAUNCH_DISCOUNT_PCT` | Oferta de bienvenida (⚠️ `30` en producción, ver doc 15) |
| `PARTNER_TIER1_PCT` / `2` / `3` | Escalera del colaborador (30/35/40) |
| `OPCOST_STD_M`, `OPCOST_STD_A`, `OPCOST_PREM_M`, `OPCOST_PREM_A` | Costo operativo imputado por plan |
| `CHARGEBACK_RESERVE_PCT` | Reserva anti-contracargo (25) |
| `SYNAPSE_PDF_PRICE`, `SYNAPSE_PDF_LIST_PRICE` | Precio del PDF de Synapse |

**Correo y avisos**
| Variable | Qué controla |
|---|---|
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_SSL` | Servidor SMTP (hoy: el del dominio, puerto 465 SSL) |
| `MAIL_USERNAME`, `MAIL_APP_PASSWORD` | Cuenta que envía (`info@`) |
| `MAIL_FROM`, `MAIL_SENDER_NAME` | Remitente visible |
| `ADMIN_EMAIL` | Buzón de avisos de dinero (`support@`) |
| `CREATORS_EMAIL` | Buzón de solicitudes de creadores |
| `WA_PHONE`, `WA_APIKEY`, `WA_MUTE`, `WA_ESPACIADO` | WhatsApp por CallMeBot |

**Interruptores de funciones**
`SCOUT_ENABLED` (0) · `PREFLIGHT_ENABLED` (1) · `INDICATORS_ENABLED` (0) ·
`MENTORSHIP_ENABLED` (0) · `CHALK_MAX_BOARDS` (30) · `SOCIAL_INSTAGRAM`,
`SOCIAL_TIKTOK` (traen por defecto las cuentas `@tradeableacademy`), `SOCIAL_X`,
`SOCIAL_YOUTUBE`, `SOCIAL_REDDIT`, `SOCIAL_DISCORD`, `SOCIAL_TELEGRAM` (vacías =
la red no aparece en `/socials`; lista `SOCIAL_LINKS` en `app.py` ~5562).

## Correo

- **Buzones reales:** `info@tradeable.academy` y `support@tradeable.academy`,
  alojados en el **servidor cPanel del papá del dueño** (OVH). Webmail en el
  puerto 2096 de ese servidor.
- **La app envía como `info@`** por SMTP SSL (465). Los avisos internos llegan
  a `support@`.
- Workspace y Zoho rechazaron el alta; Mailcow no era posible por el puerto 25.
- **Diagnóstico:** `venv/bin/python3 tools/check_mail.py` (revisa MX, SPF,
  DKIM, DMARC, conecta y autentica; `--enviar` manda uno de prueba).
- ⚠️ Un SMTP mal configurado **no tumba la app**: deja un aviso en el log y
  sigue. O sea que el registro "funciona" mientras nadie recibe su código.

## Tareas automáticas (crontab de root en el VPS)

| Cuándo | Qué | Archivo |
|---|---|---|
| Cada hora | Consulta `/health`; si falla, WhatsApp | `monitor.py` |
| 07:30 | Copia de la base (`pg_dump`), conserva 14 días | `backup_db.py` |
| 08:00 | Resumen diario de auditoría por correo | `daily_audit_summary.py` (con `venv/bin/python3`) |

⚠️ **Pendiente:** poner `tools/check_borrados.py` en un cron diario (vigila que
ninguna cuenta borrada conserve un cobro vivo en PayPal).

## Procedimientos de emergencia

| Situación | Qué hacer |
|---|---|
| **Cerrar el sitio ya** | `python3 tools/set_env.py PREVIEW_USERS=maurotradesve,gussytrades,guaramo2026` + `supervisorctl reread && supervisorctl update`. Todo el mundo ve "próximamente"; webhooks y `/health` siguen pasando. |
| **Reabrir** | `python3 tools/set_env.py --quitar PREVIEW_USERS` + `reread && update`. |
| **502 Bad Gateway** | Esperar 40 s (gunicorn arrancando). Si sigue: `supervisorctl status`, `tail -50 /var/log/trader.out.log`. Si dice `Worker failed to boot`, casi siempre es una migración o un import (ver doc 05). |
| **"Pagué y no se activó"** | Abrir `/admin`: el barrido reconcilia solo. Si no, bandeja "Pagos que necesitan atención" → activar a mano. Diagnóstico: `tools/diagnostico_compra.py`. |
| **Volver a "en construcción" desde nginx** | Copiar `tradeable.academy.conf` y recargar nginx. |
| **Revivir el bot viejo** | `systemctl enable --now pm2-root && pm2 resurrect && pm2 start all` (solo si el dueño lo pide). |

## Lo que queda abierto en infraestructura

- **El puerto 5001 sigue abierto a internet** (gunicorn escucha en `0.0.0.0`):
  el sitio es alcanzable saltándose Cloudflare. Falta cambiar el bind a
  `127.0.0.1` o cerrarlo con el firewall.
- **IP real del visitante:** falta `set_real_ip_from` + `CF-Connecting-IP` en
  nginx para que los límites por IP vean al visitante y no a Cloudflare.
- **HSTS y CSP** no están puestos (ver doc 13).
- **Prueba de carga con usuarios reales**: pendiente.

## ✅ Comandos para verificar el estado real (correr en el VPS)

```bash
cd /var/www/TRADINGBOT2.0
git log --oneline -1                      # ¿qué versión está desplegada?
supervisorctl status                      # ¿RUNNING?
# Líneas de arranque del último inicio (no imprimen secretos):
grep -E '^\[(AI|PayPal|Cripto|Mail|Oferta|Preview)\]' /var/log/trader.out.log | tail -12
curl -s https://tradeable.academy/robots.txt
curl -sI https://tradeable.academy/ | head -5
nginx -T 2>/dev/null | grep -c proxy_pass # >0 = nginx sirve la app
crontab -l
venv/bin/python3 tools/check_subs.py      # ¿PayPal y las suscripciones sanos?
venv/bin/python3 tools/check_oferta.py    # ¿la oferta de bienvenida sigue encendida?
```
