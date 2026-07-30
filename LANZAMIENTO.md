# 🚀 LANZAMIENTO — abrir Tradeable Academy al público

> **Qué es esto.** La lista completa de lo que falta para que `tradeable.academy` deje de mostrar la
> página de "en construcción" y sirva la aplicación real. Escrito el **2026-07-30**, el día que el
> dominio quedó en línea con HTTPS.
>
> **Cómo usarlo.** Cuando el usuario diga *"ya estamos listos para abrir"*, Claude lee este archivo y
> ejecuta las secciones en orden. Nada de improvisar el día del lanzamiento.
>
> **Estado hoy:** el dominio funciona y muestra la página de construcción. La aplicación real sigue
> corriendo aparte en `62.171.180.22:5001` (IP cruda, sin HTTPS) y **ahí es donde el usuario
> previsualiza sus cambios**. Los dos mundos no se tocan todavía.

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

⚠️ **Al activar Stripe LIVE hay que actualizar la Sección 5 de los T&C** (hoy dice que los pagos se
procesan manualmente) **y sus traducciones ES/FR/PT en `legal_i18n.js`.** Ver `CLAUDE.md`.

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

### A. Falta `ProxyFix` 🔴

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

### B. Falta `SESSION_COOKIE_SECURE` 🔴

No está configurado (comprobado). La cookie de sesión viajaría sin la marca que la obliga a ir siempre
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

### C. La IP del cliente se puede falsificar 🟡

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
