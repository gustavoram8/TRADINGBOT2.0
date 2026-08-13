# 🚀 LANZAMIENTO — abrir Tradeable Academy al público

> **Qué es esto.** La checklist para abrir `tradeable.academy` al público. Escrita el **2026-07-30**;
> **reescrita la cabecera el 2026-08-13**, porque casi todo lo de abajo ya se hizo y el interruptor
> cambió de sitio.

---

## ⚡ EL ESTADO REAL (2026-08-13) — leer ESTO antes que el resto del archivo

**El candado del sitio es `PREVIEW_USERS`, ya NO nginx.** nginx sirve la app en el dominio desde la
config ABIERTA (`deploy/nginx/tradeable.academy.abierto.conf`); el pase de nginx ya no existe. Lo
único que tapa el sitio es la lista de usuarios de vista previa en la aplicación.

**Abrir al público = un comando:**
```bash
cd /var/www/TRADINGBOT2.0
python3 tools/set_env.py --quitar PREVIEW_USERS
supervisorctl reread && supervisorctl update      # SIN restart detrás
# comprobar:  grep -i preview /var/log/trader.out.log | tail -1   → candado=apagado
```

**Lo que ya está HECHO de las secciones viejas de abajo** (no rehacer):
- ✅ PayPal LIVE encendido con suscripciones y webhook verificado (2026-08-10, `check_subs.py` 5 bien).
- ✅ Correo: `info@`/`support@tradeable.academy` reales (cPanel del papá), SPF/DKIM/DMARC, la app
  envía como `info@` (2026-08-08).
- ✅ nginx con `proxy_pass` a gunicorn, estáticos, webhooks con más espera (config abierta).
- ✅ `SITE_URL=https://tradeable.academy` puesta; bypass de `scalpel_anon` y cabeceras desplegados.
- ✅ Oferta de bienvenida 30% encendida (`LAUNCH_DISCOUNT_PCT=30`; apagarla el 12-oct-2026).

**Lo que queda para el lanzamiento DE VERDAD (el del anuncio público):**
1. 🔴 **Rotar los secretos de producción** (pendiente #0 de `CLAUDE.md`, se pegaron en el chat el
   2026-08-13): PayPal Secret → `SECRET_KEY` → OpenAI → GitHub → correo → NOWPayments → PostgreSQL.
2. **`PUBLIC_HTTPS=1`** (cookies Secure + ProxyFix + IP real). ⚠️ Apaga el acceso por
   `http://IP:5001` — avisar al dueño antes; su vista previa pasa a ser el propio dominio.
3. **Cambiar nginx a `tradeable.academy.live.conf`** cuando se quiera salir en Google: la config
   abierta actual sigue con `robots.txt` en `Disallow: /` a propósito (apertura sin indexar).
   Receta en la cabecera del propio archivo `.conf`. Purgar caché de Cloudflare después.
4. **Cerrar el puerto 5001 al exterior** (sección D de abajo).
5. Copyright (sección 3 de abajo) y reservar los handles `@tradeableacademy` (ya reservados IG/TikTok).

> ⚠️ `/register` también está detrás del candado: quitar `PREVIEW_USERS` abre TAMBIÉN los registros.
> Y la lista se escribe ENTERA al reponerla, no se añade.

---

> **Lo de aquí para abajo es el documento original (2026-07-30).** Sigue siendo útil como referencia
> de por qué se hizo cada cosa, pero su "estado hoy" quedó viejo: usar la sección de arriba.
>
> **Estado de entonces:** el dominio funciona y muestra la página de construcción. La aplicación real
> sigue corriendo aparte en `62.171.180.22:5001` (IP cruda, sin HTTPS) y **ahí es donde el usuario
> previsualiza sus cambios**. Los dos mundos no se tocan todavía.

---

## 🔐 DEUDA DE SEGURIDAD YA ARREGLADA EN CÓDIGO — falta desplegarla (2026-08-03)

El dueño decidió **no desplegar todavía** y arreglarlo el día que se abra el sitio. Anotado aquí
para que no se pierda; **el `git pull` + restart de la sección de deploy ya lo lleva dentro**, no
hay nada extra que hacer, solo desplegar.

1. **Bypass de `/analyze` y `/validate` — CERRADO en el repo, ABIERTO en producción.**
   `has_access()` aceptaba cualquier valor del cookie `scalpel_anon` (resto del acceso de invitado,
   retirado hace tiempo). Nadie escribe ese cookie, pero el candado lo honraba: con
   `curl -H 'Cookie: scalpel_anon=loquesea'` se entraba sin cuenta. Y el límite de uso se cuenta
   contra ese mismo valor, elegido por quien llama → **rotándolo, análisis de IA ilimitados a costa
   del dueño** (~$0.03 cada uno). ⚠️ **Mientras el puerto 5001 siga público y la clave de OpenAI de
   pago siga conectada, esto es dinero real en riesgo cada día que pasa sin desplegar.**
2. **Cabeceras de seguridad** (nosniff, X-Frame-Options, Referrer-Policy, Permissions-Policy): no
   había ninguna. Añadidas en el mismo commit. CSP se dejó fuera a propósito (la app usa scripts en
   línea por todas partes; es trabajo aparte con pruebas) y HSTS también, porque obligaría a HTTPS
   y hoy se sirve por IP cruda.
3. **`proxy_pass` a gunicorn: NO está hecho.** Verificado el 2026-08-03 con
   `grep -n "proxy_pass" /etc/nginx/sites-enabled/*` en el VPS → **cero coincidencias**. nginx sigue
   sirviendo solo la página estática. El procedimiento está en la sección C de este archivo, y
   cerrar el 5001 en la D. ⚠️ Cablear el proxy **no** cierra el puerto: son dos pasos distintos.

`tools/test_seguridad.py` (10/10) comprueba las dos primeras cosas; correrlo tras el deploy.

---

## 🧭 Resumen en una frase

Conectar el dominio a la aplicación **no es una obra, es un interruptor** (unas 10 líneas de nginx).
Lo que sí lleva trabajo son los **tres bloqueantes de negocio** y los **cuatro arreglos de código**
que hay que dejar hechos ANTES de accionarlo.

---

# 🔴 BLOQUEANTES — sin esto, abrir hace daño

### 1. Nadie puede pagarte

Stripe, PayPal y la pasarela cripto están **construidos y probados, pero apagados** (les faltan las
claves; el patrón es condicional, ver `CLAUDE.md`). Si se abre el sitio así, un visitante se registra,
decide comprar, hace clic en un plan… y choca contra un muro. Es el peor momento para perder a alguien:
justo cuando ya decidió pagar. **Y no vuelve.**

- **Stripe LIVE:** claves `sk_live_…` + `whsec_…` + cuenta bancaria conectada en el dashboard +
  webhook a `https://tradeable.academy/webhook/stripe`.
- **PayPal:** cuenta Business + Client ID + Secret + Webhook ID → `https://tradeable.academy/webhook/paypal`.
- **Cripto (NOWPayments):** `CRYPTO_API_KEY` + `CRYPTO_IPN_SECRET` → `https://tradeable.academy/webhook/crypto`.

✅ **Buena noticia:** los tres webhooks **exigían dominio con HTTPS**, y eso ya existe desde el
2026-07-30. Antes no se podían ni configurar. Ese freno desapareció.

🔴 **Y ahora los planes mensuales SE COBRAN SOLOS** (decisión del dueño, cableado el 2026-08-04),
lo que convierte el dominio con HTTPS en un requisito duro y no en una mejora: en una renovación
**nadie vuelve a la web**, así que el cobro del mes 2 en adelante llega ÚNICAMENTE por webhook. Sin
`PAYPAL_WEBHOOK_ID` y sin HTTPS, se cobraría al cliente y su plan no se extendería, en silencio.
Por eso `PAYPAL_SUBS_ENABLED` exige el webhook y los dos ids de plan; sin ellos el sitio cae al pago
suelto de siempre y no promete ninguna renovación. Crear los planes: `tools/paypal_setup_subs.py`
(o directamente `tools/set_paypal.py`, que ya los crea de paso).

⚠️ **La Sección 5 de los T&C ya está reescrita** con la renovación automática, la baja y los
reintentos (EN + ES/FR/PT, auditor 144 cláusulas OK). Si algún día se enciende Stripe LIVE, revisarla
otra vez.

### 📌 Al tocar la pasarela, hacer TAMBIÉN estas dos cosas

> Ambas quedaron pedidas el 2026-07-30 y esperan a que haya un riel de cobro vivo.

**(a) Disparadores nuevos de CallMeBot (WhatsApp).** Hoy `send_whatsapp_alert()` (`app.py:168`) tiene
**un solo disparador: el manejador de errores 500**. Añadir uno es una línea. Orden acordado:

1. 🔴 **PRIMERO el cortafuegos anti-inundación.** Sin él, un bug en una página muy visitada dispara un
   WhatsApp *por cada* petición fallida → cientos de mensajes en minutos, CallMeBot corta por abuso y
   el día que pase algo de verdad **no llega nada**. Hace falta agrupar: misma firma de error dentro de
   una ventana (p. ej. 15 min) = un solo aviso, con contador. Esto protege también la alerta que ya existe.
2. Avisos que SÍ merecen interrumpir: **pagó y no se activó** (dinero cobrado, producto no entregado);
   **fallo del sistema de correo** ⚠️ *(punto ciego real de hoy: si el correo se rompe, el aviso de que
   el correo está roto se manda POR CORREO y nunca llega — WhatsApp es el canal correcto)*;
   **disputa/contracargo de PayPal** (tiene plazo para responder); **firma de webhook inválida repetida**
   (ataque o mala configuración).
3. Opcional, a gusto del usuario: **venta confirmada** (no es urgente, pero es el mensaje que quiere
   recibir). Como interruptor aparte para poder apagarlo cuando haya volumen.
4. Se quedan SOLO en correo: PDFs de Synapse, mensajes de contacto, un análisis suelto fallido.

⚠️ **No confundir con esto:** un camo o plan que "nunca se activó" **no puede fallar en silencio hoy**.
`grant_plan_camo()` corre dentro de la MISMA transacción que el plan (`_activate_plan_from_order`), así
que si fallara no se guardaría nada, el pedido quedaría sin aplicar, y eso ya lo cazan el barrido de
`/admin` y el aviso de "pagó pero no se activó". Está cubierto por construcción.

**(b) ✅ La TIENDA DE CAMOS ya está CABLEADA a PayPal (2026-07-30) — solo falta encender las claves.**
Decisión del usuario: camos se cobran **SOLO por PayPal**, precios se quedan en $1.99/$4.99 y la
comisión fija la asume él (cripto descartado: la fee de red supera el precio del skin). El flujo
completo está construido e inerte sin claves (detalle en `CLAUDE.md`, sección camos): `CamoOrder` +
precio server-side + `/api/camo/buy` + return + webhook por `custom_id` + barrido + activador
idempotente. E2E 18 checks verdes con PayPal simulado. **El día que se pongan las 4 env vars de
PayPal, los camos se venden solos — cero código pendiente.** Probar una compra real con
`PAYPAL_ENV=sandbox` antes de live.

### 2. `support@tradeable.academy` no existe

Los T&C y la Política de Privacidad lo publican **en cuatro idiomas** como canal de contacto oficial.
Hoy quien escriba ahí **recibe un rebote**. Además los correos de verificación y recuperación de
contraseña salen de un **Gmail personal**, que muchos filtros mandan a spam — y un correo de
verificación en spam es un registro perdido.

- Casilla real (Google Workspace 1 usuario + alias, o Zoho free). Plan detallado en `CLAUDE.md`.
- **Proveedor transaccional aparte** (Brevo/Resend) para los correos automáticos de la app. **NO usar
  Workspace para eso**: tope ~2.000 envíos/día y si se supera Google bloquea 24 h → nadie puede
  registrarse.
- **SPF + DKIM + DMARC** en Cloudflare, o todo cae en spam.

### 3. Copyright sin registrar

Ver `CLAUDE.md`. Conviene antes de publicar, o dentro de los 3 meses siguientes.

---

# 🟠 ARREGLOS DE CÓDIGO — obligatorios antes de accionar el interruptor

> Verificados leyendo `scalpel/app.py` el 2026-07-30. Hoy no molestan porque la app se sirve directo;
> **en cuanto nginx se ponga delante, sí molestan.**

### A. `ProxyFix` ✅ HECHO (2026-08-04) — solo falta encenderlo

Ya está en `app.py`, **detrás de `PUBLIC_HTTPS=1`**. Y el problema de los enlaces absolutos se
resolvió por otra vía, más directa: existe **`SITE_URL`** y un helper `abs_url()`, y los **20**
sitios que generaban enlaces absolutos pasan por él. Con `SITE_URL=https://tradeable.academy` los
enlaces salen bien aunque el esquema de la petición sea otro.

> ⚠️ Deliberadamente NO se usa `SERVER_NAME` de Flask: fijarlo hace que la app deje de responder a
> cualquier otro Host, así que el día de ponerlo la IP cruda devolvería 404 en TODO el sitio.

Lo que sigue debajo es el diagnóstico original, que se conserva porque explica por qué importa.

### A-bis. El diagnóstico original 🔴

`app.py` **no importa ni aplica** `werkzeug.middleware.proxy_fix.ProxyFix` (comprobado: 0 coincidencias).
Detrás de nginx, Flask creería que la conversación es por `http`, porque el cifrado termina en nginx.

Hay **13 sitios** que generan enlaces absolutos con `url_for(..., _external=True)`, y **todos saldrían
con `http://`**:

| Línea | Qué es | Qué se rompe |
|---|---|---|
| 4071 | Recuperación de contraseña | El enlace del correo |
| 5475-5477 | `success_url` / `cancel_url` de Stripe | **Retorno tras pagar** |
| 4985-4986 | `return_url` / `cancel_url` de PayPal | **Retorno tras pagar** |
| 4605-4607 | `ipn_callback_url` + success/cancel de cripto | **Aviso de pago recibido** |
| 3360-3362 | Checkout de mentoría (hoy oculto) | Retorno tras pagar |
| 6482 | Descarga del PDF de Synapse | El enlace del PDF |
| 9006, 9025 | Verificación de certificados | El enlace del certificado |

Un `return_url` mal formado = **un cliente que paga y aterriza en una página rota**.

```python
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
```

### B. `SESSION_COOKIE_SECURE` ✅ HECHO (2026-08-04) — solo falta encenderlo

Va en el mismo bloque `PUBLIC_HTTPS=1`, junto con `HTTPONLY`, `SAMESITE='Lax'`,
`REMEMBER_COOKIE_SECURE` y `PREFERRED_URL_SCHEME='https'`. La advertencia de abajo sigue siendo
válida y es la razón de que esté condicionado.

### B-bis. El diagnóstico original 🔴

No estaba configurado. La cookie de sesión viajaría sin la marca que la obliga a ir siempre
cifrada. Añadir junto con las otras banderas de endurecimiento:

```python
app.config.update(
    SESSION_COOKIE_SECURE=True,      # solo por HTTPS
    SESSION_COOKIE_HTTPONLY=True,    # invisible para JavaScript
    SESSION_COOKIE_SAMESITE='Lax',   # mitiga CSRF
    PREFERRED_URL_SCHEME='https',
)
```

⚠️ **Ojo:** `SESSION_COOKIE_SECURE=True` **rompe el acceso por `http://62.171.180.22:5001`** (la cookie
deja de enviarse → no se puede iniciar sesión). Como el usuario previsualiza sus cambios justo por ahí,
hay que **condicionarlo a una variable de entorno** (p. ej. `PUBLIC_HTTPS=1`), no ponerlo fijo, o
apagarle su vista previa sin avisar.

### C. La IP del cliente ✅ ARREGLADO EN CÓDIGO (2026-08-04)

`_client_ip()` ya NO lee el primer valor de `X-Forwarded-For` cuando `PUBLIC_HTTPS=1`: usa
`request.remote_addr`, que ProxyFix rellena con el salto que añade nuestro propio nginx — ese no lo
controla el visitante. La cabecera cruda solo se mira sin proxy (vista previa por IP y local).
Lo de `set_real_ip_from` de Cloudflare de abajo sigue siendo la mejora fina y queda pendiente.

### C-bis. El diagnóstico original 🟡

`_client_ip()` (`app.py:3423`) toma el **primer** valor de `X-Forwarded-For`. Detrás de Cloudflare eso
normalmente **es** el visitante real… pero Cloudflare **añade** la IP a la cadena que llegue, así que
alguien que mande su propia cabecera `X-Forwarded-For: 1.2.3.4` consigue que la app lea `1.2.3.4`.
Como esa función alimenta **límites por IP** (por ejemplo el antiflood de solicitudes), es un agujero
real, aunque menor.

**Arreglo correcto** — que nginx reescriba la IP de origen con la cabecera que Cloudflare sí garantiza:

```nginx
# Rangos de Cloudflare (bajar la lista actualizada de cloudflare.com/ips)
set_real_ip_from 173.245.48.0/20;
# … resto de rangos …
real_ip_header CF-Connecting-IP;
```

Así `$remote_addr` pasa a ser el visitante de verdad y `ProxyFix(x_for=1)` funciona bien.

### D. Cerrar el puerto 5001 al exterior 🟡

Hoy gunicorn escucha en `0.0.0.0:5001`, o sea **abierto a internet**. Una vez que nginx sirva el
dominio, dejarlo abierto significa que el sitio es accesible **saltándose Cloudflare** (sin protección
anti-ataques, sin HTTPS y revelando la IP del servidor).

- Cambiar el `--bind` de gunicorn a `127.0.0.1:5001` en la config de supervisor, **o**
- `ufw deny 5001` dejándolo accesible solo desde el propio servidor.

⚠️ **Esto elimina la vista previa por IP del usuario.** Antes de hacerlo, montarle el
`preview.tradeable.academy` con contraseña (ya ofrecido el 2026-07-30; dijo que no por ahora).

---

# 🔵 EL INTERRUPTOR — conectar el dominio a la aplicación

> ✅ **Ya no hay que escribirlo a mano: está en `deploy/nginx/tradeable.academy.live.conf`** (creado
> el 2026-08-04), con los estáticos, el `client_max_body_size`, el `robots.txt` corregido y un
> `location ~ ^/webhook/` aparte con más tiempo de espera. El archivo viejo se conserva para poder
> volver atrás con un solo comando. **Antes de recargar nginx**, poner en supervisor
> `SITE_URL=https://tradeable.academy` y `PUBLIC_HTTPS=1`.

Sustituir el `location /` de `deploy/nginx/tradeable.academy.conf`. Certbot ya creó el bloque `443`;
**el cambio va ahí, no en el bloque 80.**

```nginx
# Los estáticos los sirve nginx directo: no ocupan un worker de Python.
location /static/ {
    alias /var/www/TRADINGBOT2.0/scalpel/static/;
    expires 7d;
    add_header Cache-Control "public, max-age=604800";
}

location / {
    proxy_pass http://127.0.0.1:5001;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_redirect off;

    # El análisis con IA puede tardar bastante; el default de 60s lo cortaría
    # a la mitad y el usuario vería un 504 con el análisis ya pagado.
    proxy_read_timeout    180s;
    proxy_connect_timeout 10s;
}

# Los screenshots pesan: app.config['MAX_CONTENT_LENGTH'] son 20 MB (app.py:38).
# El default de nginx es 1 MB → rechazaría subidas legítimas con un 413.
client_max_body_size 20M;
```

### Y no olvidar (fallos silenciosos, de los que no dan error)

1. **Quitar el `robots.txt` que bloquea todo.** La config actual devuelve `Disallow: /` para que Google
   no indexe la página de obras. **Si se queda, el sitio abierto nunca aparece en Google.** Es el error
   más fácil de cometer y el más caro: pasan semanas sin que nadie entienda por qué no llega tráfico.
2. **Quitar `<meta name="robots" content="noindex">`** si algo de esa página se reutiliza.
3. **Cloudflare → SSL/TLS → Edge Certificates → "Always Use HTTPS": ON.**
4. **Revisar el caché de Cloudflare.** Por defecto no cachea HTML, pero conviene confirmar que no
   guarde páginas con sesión iniciada (sería un desastre de privacidad: un usuario viendo la página de
   otro). Regla: no cachear nada bajo `/app`, `/admin`, `/api`.
5. **Purgar el caché de Cloudflare** tras el cambio, o los visitantes seguirán viendo "en construcción".

---

# ✅ COMPROBACIÓN — después de accionar

```bash
# 1. Carga el sitio real, no la página de obras
curl -sI https://tradeable.academy/ | head -3
curl -s  https://tradeable.academy/ | grep -o "<title>.*</title>"

# 2. Los enlaces absolutos salen en https (la prueba de que ProxyFix funciona)
#    → pedir un reset de contraseña y mirar el enlace del correo

# 3. Estáticos servidos por nginx
curl -sI https://tradeable.academy/static/logo_t.png | grep -i "cache-control\|server"

# 4. robots.txt ya NO bloquea
curl -s https://tradeable.academy/robots.txt
```

Y a mano, en el navegador: **registrarse con un correo nuevo** (que llegue la verificación con enlace
`https://`), **iniciar sesión**, **subir un screenshot al analizador** (que no dé 413 ni 504) y
**llegar hasta la pantalla de pago** con un plan.

---

# ↩️ CÓMO REVERTIR (si algo sale mal)

Volver a la página de construcción es inmediato: se restaura el `location /` original
(`try_files $uri /index.html`) y `systemctl reload nginx`. La aplicación no se toca; sigue viva en el
5001. **Guardar una copia de la config antes de editarla:**

```bash
sudo cp /etc/nginx/sites-available/tradeable.academy \
        /etc/nginx/sites-available/tradeable.academy.antes-de-abrir
```

---

# 📌 Contexto que no hay que perder

- **El bot viejo (`/opt/tradingbot`) es un proyecto aparte del usuario. NO se toca ni se borra jamás.**
  Está apagado (PM2 detenido y desactivado el 2026-07-30) pero íntegro. Detalle en `CLAUDE.md`.
- **Mentorías (`MENTORSHIP_ENABLED`) siguen ocultas** — decidir si se abren o no antes del lanzamiento.
- **Cloudflare debe quedarse en Full (strict)**, nunca en "Flexible" (bucle de redirecciones).
- El certificado de Let's Encrypt **se renueva solo** (`certbot.timer`). No hay nada que recordar ahí.
- **Reservar los handles de redes sociales** `@tradeableacademy` antes de abrir, o alguien los toma.
