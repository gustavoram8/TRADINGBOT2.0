# Scalpel — Trader Accelerator · Notas ACTIVAS para Claude Code

> 📦 El historial completo (tareas terminadas, detalles técnicos de Synapse, quiz hardcore,
> sesiones pasadas, análisis de costos de IA, ideas en stand-by) está en **`CLAUDE_ARCHIVE.md`**,
> que **NO** se carga en cada mensaje. Mantener este archivo CORTO para ahorrar tokens; al
> terminar una tarea, mover su detalle al archivo en vez de dejarlo aquí.

> 🚀 **`LANZAMIENTO.md`** = la checklist para abrir el sitio al público (bloqueantes, arreglos de
> código previos, el cambio de nginx, verificación y plan de reversa). **Leerlo cuando el usuario
> diga que quiere abrir el sitio, o al tocar nginx / pagos / correo / dominio.** Tampoco se carga solo.

---

## 🔧 Operativa (LEER SIEMPRE)
- **Rama de trabajo:** `claude/gallant-volta-i7cqmf`
- **Deploy en VPS** (Contabo `62.171.180.22:5001`, supervisor). Proceso: **`traderacelerator`** (¡una sola 'c', typo viejo!):
  ```
  cd /var/www/TRADINGBOT2.0 && git pull origin claude/gallant-volta-i7cqmf && supervisorctl restart traderacelerator
  ```
  Sin el restart, lo pusheado NO se refleja en producción. **Recordar el deploy tras cada push.**
  ⚠️ **Cuando cambia el conf de supervisor, `supervisorctl update` YA reinicia el proceso: NO
  encadenar `restart` detrás.** Gunicorn tarda ~30 s en cerrar con elegancia, así que el segundo
  reinicio lo mata a mitad del arranque y el sitio devuelve **502 Bad Gateway** durante ~40 s
  (pasado el 2026-08-07). Usa `reread && update`, o `restart` a secas si el conf no cambió.
  · Para poner/quitar variables sin editor: **`python3 tools/set_env.py NOMBRE=valor`**
    (escribe en `.env` y en supervisor, respeta comas dentro de valores, hace copia y no imprime
    secretos). `--quitar NOMBRE` para el día del lanzamiento.
- Producción usa **PostgreSQL** + gunicorn (venv). **Config gunicorn actual (2026-06-23):** `--max-requests 300 --max-requests-jitter 50 -w 4 --threads 4 -k gthread` (4 workers × 4 hilos = 16 concurrentes; reciclaje de workers anti-fuga). Editar en `/etc/supervisor/conf.d/*trader*.conf`. Env vars en supervisor conf y `scalpel/.env` (gitignored, mantener ambos en sync). ⚠️ `user`/`order` son reservadas en PG → quotear `"user"`/`"order"` en SQL crudo.

### 🖥️ Infra / escalado (medido 2026-06-23)
- **VPS Contabo: 7.8 GB RAM** (NO es chico). + **swap 2 GB** agregado (`/swapfile`, en `/etc/fstab`).
- **Bug OOM resuelto:** el ERROR 500 en `/register` reportado era un worker muerto por OOM (fuga de memoria lenta sin reciclar workers), NO un bug de código (el registro funciona: probado, da 302). **Fix aplicado:** swap + `--max-requests` (reciclaje) + threads. Causa real NO era falta de RAM (sobra), era fuga sin reciclar.
- **Prueba de carga (PARCIAL, leer con cuidado):** `ab -n 3000 -c 200 /login` → **432 req/s, 0 fallidas** (válido). Locust lanzó **500 conexiones concurrentes** y el servidor **NO se cayó, NO hizo OOM, siguió RUNNING** (RAM 1.6/7.8 GB) → probado que **no se rompe bajo 500 conexiones**. PERO: la siembra de los 500 usuarios `loadtest` **falló** (DB quedó en `encontrados: 0`), así que los logins fallaban y las peticiones eran **más ligeras que un usuario autenticado real**; además locust murió con el SSH → **NO tenemos tabla de latencias ni prueba de la experiencia logueada real**. **Conclusión honesta: NO está probado del todo que aguante 500 usuarios reales usando todo el sitio; solo que no se cae/OOM bajo 500 conexiones.** PENDIENTE hacerlo bien: (1) sembrar usuarios y verificar que imprima `sembrados 500`; (2) correr locust desde una máquina estable o en el VPS con `tmux`/`nohup` para que sobreviva; (3) capturar la tabla `Aggregated` (median/p95/req-s/% fails). NO load-testear `/analyze` (IA: cuesta dinero + ya gateada por límites de plan).
- **🟡 nginx + dominio + SSL — HECHO A MEDIAS (2026-07-30).** ✅ Ya existe: dominio `tradeable.academy`
  comprado, DNS en Cloudflare (A `@` y `www` → 62.171.180.22, **proxy naranja ON**, modo SSL **Full
  (strict)** fijo — no "Automatic"), nginx instalado, certificado **Let's Encrypt** emitido para ambos
  nombres con `certbot.timer` renovando solo. ⚠️ **PERO nginx hoy sirve SOLO la página estática de
  "en construcción"** (`deploy/coming_soon/`, config en `deploy/nginx/tradeable.academy.conf`) — **NO
  hay reverse proxy a gunicorn todavía**, así que el multiplicador de capacidad (estáticos sin ocupar
  workers, amortiguar clientes lentos) **aún NO está activo**. La app real sigue expuesta directo en
  `0.0.0.0:5001` por IP cruda sin HTTPS (el usuario lo sabe y lo eligió así por ahora; ahí previsualiza
  sus cambios). **Falta para el día del lanzamiento:** cambiar el `location /` por
  `proxy_pass http://127.0.0.1:5001` con los headers `X-Forwarded-*`, y considerar cerrar el 5001 al
  exterior. Se ofreció un `preview.tradeable.academy` con contraseña y el usuario dijo que no por ahora.
- **⛔ El bot de trading viejo (`/opt/tradingbot`) — APAGADO, no borrado (2026-07-30).** Dos capas: (1)
  su sitio nginx `/etc/nginx/sites-enabled/tradingbot` **no tenía `server_name`** → era catch-all y
  respondía en el dominio nuevo; se quitó el symlink (el archivo sigue en `sites-available`). (2) Lo
  mantenía vivo **PM2** (no systemd, por eso no salía en `systemctl`): `tradingbot-next` (ocupaba el
  puerto 3000, expuesto a internet) y `tradingbot-frontend` **en bucle de +1.800 reinicios** chocando
  contra ese puerto ocupado, quemando CPU 24/7. Se hizo `pm2 stop all && pm2 save && pm2 kill` +
  `systemctl disable pm2-root`, con respaldo en `/root/.pm2/dump.pm2.backup-2026-07-30`. **NADA se
  borró.** Revivir = `systemctl enable --now pm2-root && pm2 resurrect && pm2 start all`.
  🔴 **REGLA PERMANENTE: ese proyecto es del usuario y NO se toca ni se borra jamás.**
- **Confidencialidad IA:** en el front público NUNCA decir "GPT-4o"/"OpenAI" → "our proprietary AI engine".
- **Calidad:** validar antes de pushear (Jinja parse, `node --check` del JS tocado, i18n con claves parejas en EN/ES/FR/PT).

## 🎯 QUÉ ES TRADEABLE — el posicionamiento OFICIAL (dictado por el dueño 2026-08-14)
> 🔴 **Esta es la idea que gobierna TODO el contenido (Instagram, TikTok, landing, copy).** Sale
> textual de él; no reformularla a la ligera ni suavizarla para que suene más comercial.

**Tradeable es un ECOSISTEMA de trading. Su herramienta principal es el analizador.**

**Lo que NO somos, y hay que decirlo:** no somos un bot de trading · **no somos mentores y NO
suplimos el papel de un mentor** · no vendemos señales · no prometemos resultados.

**El caso de uso REAL —el que hay que contar—:** el analizador te ayuda a encontrar el error de
un trade que **por "X" razón NO pudiste enseñarle a tu mentor**:
  · porque no tienes dinero para pagar un mentor;
  · porque son **las 3 AM** y te da pena contactarlo;
  · o porque tu mentor simplemente **no te contesta**.
Es **feedback rápido y barato para alguien en apuros** que necesita encontrar su error ya.

🔑 Ese es el ángulo que hace que el contenido NO sea genérico: no competimos con el mentor, lo
cubrimos cuando no está. Todo post/historia/reel debería poder responder "¿esto de qué le sirve
al tipo de las 3 AM?".

**Criterio visual del dueño (mismo día):** *"piensa en nuestro instagram como la fachada de una
casa en pleno 2026. Si la casa es vieja, no llama la atención aunque su patio sea grande (el
website). Hay que hacer que parezca la casa de Elon Musk y que al verla digan «qué locura es
esta»"*. Es decir: **el listón NO es "correcto y limpio", es que pare el scroll.** Va a mandar
referencias de artes que le parecen buenos → calibrar el sistema visual con ellas ANTES de
producir nada nuevo.

## 📝 `/creators` — solicitudes de creadores de contenido (2026-08-22)
> 🔗 **EL ENLACE, para cuando lo pida: `https://tradeable.academy/creators`**
> Va fijado en una historia destacada de Instagram. No está en ningún menú, ni
> en el sitemap, y lleva `noindex` — se llega por ese enlace o no se llega.
La puerta de entrada ANTES del acuerdo de colaboración y del código de creador. El enlace vive en
una **historia destacada de Instagram**; la página es SUELTA (nada del producto: ni pestañas, ni
barra lateral, ni Synapse), con `noindex`, **fuera del sitemap y de todos los menús**.
- **Modelo `CreatorApplication`** (tabla nueva → `create_all`, sin ALTER) + ruta `GET/POST
  /creators` + plantilla `creators.html` autocontenida (diccionario ×4 DENTRO de la plantilla,
  patrón de `contact.html` — no toca `pages_i18n.js`, así no puede romper otra página).
- **Correo a `CREATORS_INBOX`** (env `CREATORS_EMAIL`, default `info@tradeable.academy`) con
  **Reply-To del creador**. 🔴 **NO se reutiliza `ADMIN_INBOX`**: por ahí van las alertas de dinero
  y mezclarlas con correo comercial es como se pasa por alto un "pagué y no se activó".
- 🔴 **La fila se guarda AUNQUE el correo falle** — el aviso es best-effort; sin la fila, un creador
  escribe y se pierde sin que nadie se entere. Campos: nombre/apellido, correo, país, idiomas,
  **redes en JSON** (`[{net,user,followers}]` — en un solo campo porque añadir una red no puede
  exigir un ALTER), qué publica, mercados, publicación de muestra + sus vistas.
- **Antiflood** igual que las solicitudes de mentoría: 1 por correo/24 h + **3 por IP/24 h**
  (`CREATOR_IP_MAX`). Obligatorio: fijado en una destacada, el enlace es público en la práctica.
- **NO muestra la escala 30/35/40** (decisión): un enlace se reenvía, y publicar los porcentajes
  los vuelve compromiso público. La página dice que las condiciones van en el acuerdo. Y deja
  escrito que **enviar no otorga nada** — si alguien se cree colaborador y empieza a promocionar,
  el lío es del dueño.
- ⚠️ **La hoja de Google Fonts va NO BLOQUEANTE** (`media=print` + `onload`): una hoja pendiente en
  el `<head>` bloquea la ejecución de los `<script>` posteriores, así que la página se quedaba en
  inglés hasta que Fonts respondía. Importa porque el visitante llega desde el navegador interno de
  Instagram. Y el idioma se elige por **`navigator.language`** cuando no hay preferencia guardada:
  quien llega de una historia nunca ha abierto el sitio.
- 🔴 **Bloque "Qué pasa después" (2026-08-22).** El "te contactamos por correo" YA estaba dicho en
  TRES sitios —el lead, la casilla de consentimiento y la pantalla de gracias— y aun así el dueño
  leyó el formulario entero y no lo registró. **El problema no era el texto, era dónde vivía:** el
  final de una frase de introducción y una casilla legal son los dos sitios que nadie lee. Se sacó
  a un bloque propio (`.luego`, 3 pasos numerados) **justo encima del botón**, que es el único
  momento en que la persona se pregunta "¿y ahora qué?". Dice además que **solo se contacta por
  correo, nunca por privado** (defensa contra el que se haga pasar por Tradeable en DM) y que las
  condiciones van en el acuerdo. ⚠️ De paso se corrigió una promesa incumplible: *"leemos todas y
  respondemos por correo"* → *"las leemos todas; si encajamos, te escribimos"* — con una sola
  persona atendiendo, prometer respuesta a todos y no darla es peor que no prometerla.
- **Campos: se decidió NO añadir más (2026-08-22).** El dueño preguntó por "cuánto tiempo lleva en
  el trading" y se desaconsejó: no evalúas su trading, evalúas su AUDIENCIA (2 años y 80k
  enganchados valen más que 10 años y 900), auto-selecciona al revés (el de 8 meses que hace buen
  contenido no aplica), y ya está capturado en la opción *documenta su proceso*. Regla general: la
  página la abre alguien que llega de una historia y no te debe nada — cada campo extra cuesta
  solicitudes que nunca ves. Lo que de verdad decide ya está: **los usernames** (abres su cuenta y
  en 30 s sabes más que con cualquier campo autodeclarado) y **la publicación + sus vistas**
  (lo único que delata una audiencia comprada).
- `tools/test_creators.py` **50/50** + navegador real (es/en/pt + móvil 412px, envío completo).
  ⚠️ Cada caso del test va con su **propia IP** (`X-Forwarded-For`): sin eso el tope por IP se
  agota con los primeros envíos y todo lo demás se rechaza por la razón equivocada.
- **PENDIENTE:** no hay pestaña en `/admin` para verlas — hoy se leen por correo, y si el SMTP
  falla la fila solo se ve en la base. Ofrecido al dueño, aún no pedido.

## 📋 COLA PARA MAÑANA (2026-08-14, anotado a petición suya — SIN luz verde aún)
El dueño las dictó al cerrar la sesión de responsive. **No empezar ninguna hasta que lo diga.**

1. ✅ **2. LOGO CON CAJA — BARRIDO COMPLETO (2026-08-14, puntos 1 y 2 juntos).** La caja blanca vive
   HORNEADA en `logo.png`; `logo_t.png` es el mismo arte transparente. Barridas TODAS las
   referencias (28 plantillas + el correo): las páginas apuntan a `logo_t.png`.
   · **El correo** (`_correo_html`) era el caso del hermano: en un correo no hay CSS que disimule la
     caja (**los clientes de correo NO soportan `mix-blend-mode`**) y en Gmail oscuro salía un
     rectángulo blanco. Ahora `logo_t.png` + **`background:#ffffff` en el contenedor** — el seguro
     inverso: las letras del transparente son NEGRAS y en un cliente oscuro sin fondo propio
     quedarían invisibles.
   · 🔑 Tres familias de páginas: (a) SIN truco alguno (cosmetics/socials/contact/terms/privacy/
     store_indicators/partner/2FA) — ahí la caja SÍ se veía; (b) con el par
     `invert(1)+lighten / multiply` (auth, admin, splash, improve/mentorship) — la caja ya moría por
     blend, se cambió el archivo por uniformidad, mismo resultado; (c) `index.html` NO SE TOCÓ: el
     shell ya hace el swap en runtime y los camos pisan el logo con `content:url()`.
   · `admin_trace.html` no estaba en ninguna lista y era oscuro sin filtro → se le puso el par de
     admin. "Mi cuenta" (`/settings`) YA usaba `logo_t` — por eso él no lo recordaba con seguridad.
   · `test_recibo_email.py` ahora exige `logo_t.png` y prohíbe `logo.png` (23/23). Verificado por
     PÍXELES en navegador real (scratchpad `mide_logo.py`): 11 casos (8 páginas × temas), tinta
     dibujada y Δ esquina-vs-fondo ≤1 en todos. ⚠️ `/login` y `/register` REDIRIGEN con sesión
     abierta: medirlas ANTES de loguear o el selector no existe.
3. 🔴 **SEGURIDAD DEL SITIO — revisión general.** Contexto de lo que YA existe, para no repetirlo:
   cabeceras básicas puestas (nosniff, X-Frame-Options, Referrer-Policy, Permissions-Policy),
   `PUBLIC_HTTPS=1` con cookies Secure/HttpOnly/SameSite y ProxyFix, 2FA TOTP opcional, contraseñas
   débiles bloqueadas, avisos de dispositivo nuevo, `test_seguridad.py` 10/10. **Lo que NO está:**
   CSP (se dejó fuera a propósito: la app usa scripts en línea por todas partes, es trabajo aparte
   con pruebas), HSTS, antiflood por IP en `/register` (acordado como pendiente antes de lanzar,
   ver la sección del correo canónico), y el puerto 5001 sigue abierto a internet (sección D de
   `LANZAMIENTO.md`). Y él DECIDIÓ no rotar los secretos (pendiente #0): no reabrir salvo que
   pregunte.
4. ✅ **FAVICON + FICHA DE GOOGLE (2026-08-14).** No existía NADA: ni `favicon.ico`, ni
   `apple-touch-icon`, ni `og:image`, ni **una sola `<meta name="description">` en todo el sitio**.
   **`tools/gen_favicon.py`** genera todo desde la MISMA "a" y el mismo `#004feb` del kit de
   Instagram (favicon.ico 16/32/48 · icon-96/192/512 · apple-touch-icon 180 · og-image 1200×630 con
   el logotipo entero). **`scalpel/templates/_iconos.html`** = el único sitio donde se declaran
   (son 45 plantillas con `<head>` y ninguna base común); incluido en landing, `/app` y las 7
   páginas públicas del sitemap.
   · 🔑 **Las rutas van en la RAÍZ** (`/favicon.ico`, `/apple-touch-icon.png`,
     `…-precomposed.png`, `/icon-192.png` → `icono_raiz()`): navegadores y Google las piden **por
     convención, sin que ninguna etiqueta las declare**, así que el icono aparece también en las
     plantillas que no incluyen el parcial.
   · ⚠️ **El icono es la "a", NO el logotipo** (6:1 → a 16px la palabra es una mancha), **opaco y a
     sangre** (iOS pinta NEGRO detrás del alfa y pone sus propias esquinas) y con **proporción
     distinta por tamaño**; el `.ico` va a 0.74 y no a 0.58 porque a 16px los trazos finos se lavan.
     El azul se toma del **color MÁS REPETIDO** entre píxeles opacos (el primero cae en el borde
     suavizado y da `#84a9e8`), y la "a" se recorta pintando **solo los píxeles azules** — copiar el
     recuadro entero colaba un trozo del glifo vecino.
   · 🔴 **Lo que el dueño reportó DESPUÉS, y era lo gordo:** al buscarse en Google salía *"No hay
     información disponible sobre esta página"*. **Eso NO es el favicon: es el mensaje de "robots.txt
     me prohíbe leer la página"** — Google indexó la URL mientras el sitio aún servía `Disallow: /`
     y no había vuelto. Verificado con él que hoy da `Allow: /`. **De las 4 configs de nginx, TRES
     devuelven `Disallow: /`** (conf, abierto, preview) y solo `live.conf` abre: al tocar nginx,
     comprobar SIEMPRE `curl -s https://tradeable.academy/robots.txt`.
   · **Descripciones ×8 páginas** (una distinta por página — repetir la misma es peor que no
     ponerla: Google las trata como duplicados) + **`<link rel="canonical">`** vía `url_canonica()`
     (que `www.`, el dominio pelado y la IP declaren la MISMA dirección). Título de la landing:
     "Tradeable Academy — Trade analysis, review and practice" (a secas no decía qué es).
     ⚠️ **Van en INGLÉS a propósito:** el servidor sirve `<html lang="en">` y la traducción la
     aplica el navegador DESPUÉS; un buscador solo ve lo primero.
   · `tools/test_favicon.py` **32/32** (rutas raíz sin etiquetas, og:image ABSOLUTA, `.ico` con sus
     3 resoluciones dentro, apple-touch opaco, largo 60-165 de cada descripción, todas distintas,
     ninguna promete resultados).
   · ✅ **SEARCH CONSOLE DADO DE ALTA (2026-08-14):** propiedad de **Dominio**, verificada por el
     método *"Proveedor de nombres de dominio"* — **Google puso el TXT él mismo** vía su integración
     con Cloudflare (botón *Authorize*), no hizo falta `dns_cf.py`. Indexación de la portada
     solicitada y **sitemap enviado**. La *Prueba en tiempo real* confirmó **"La URL está disponible
     para Google"** — o sea que el bloqueo de robots está resuelto de verdad, no solo en el archivo.
     🔴 **EL REGISTRO TXT `google-site-verification` NO SE BORRA NUNCA** — si desaparece, Google
     desverifica el dominio y se pierde el panel. Ojo al limpiar DNS con `tools/dns_cf.py`.
     ⚠️ Convive sin problema con el SPF del correo en la raíz: puede haber muchos TXT en el mismo
     nombre, lo único prohibido es tener DOS que empiecen por `v=spf1`.
     ⚠️ **En una propiedad de DOMINIO el sitemap se escribe con la URL COMPLETA**
     (`https://tradeable.academy/sitemap.xml`); solo las de tipo *prefijo de URL* rellenan el
     dominio solas — con `sitemap.xml` a secas responde *"Dirección de sitemap no válida"*.
   · ⏳ **PENDIENTE:** el icono exige **no cambiar de archivo** mientras Google lo recoge (días o
     un par de semanas). *"Indexada"* ≠ *"leída"*: la portada llevaba tiempo indexada **y** con
     `Disallow`, que es justo lo que produce el *"No hay información disponible sobre esta página"*.

## 📌 PENDIENTES DE ÉL (recordárselos cuando toque, no cada mensaje)
0. ⚪ **ROTAR LOS SECRETOS — el dueño DECIDIÓ NO HACERLO y asume el riesgo (2026-08-13).** Textual:
   *"si es ese el riesgo yo lo asumo"*. 🔴 **NO volver a sacárselo cada semana**; solo si él
   pregunta, o si aparece una señal real (cargo raro en PayPal, gasto de OpenAI que no cuadra,
   sesión de admin que él no abrió).
   **Qué pasó:** el 13-ago se pegaron en el chat, en texto plano, TODOS los de la línea
   `environment=` de supervisor: Secret LIVE de PayPal, `SECRET_KEY` de Flask, clave de OpenAI,
   token de GitHub, contraseña del correo, NOWPayments y PostgreSQL. Fue por un comando que se le
   dio (`grep LAUNCH … *trader*.conf`), que imprime la línea ENTERA — **culpa compartida: no volver
   a mandar un grep sobre esa línea sin avisar de lo que va a salir.**
   **Alcance REAL, verificado:** `scalpel/.env` está en `.gitignore` y **nunca se commiteó**; el
   conf de supervisor no vive en el repo → **los secretos NO están en GitHub**. La única copia
   fuera del VPS es el historial de esta conversación, que no es público. ⚠️ **Se le presentó el
   riesgo más grave de lo que era** ("cada día que pasa es riesgo real") — corregido ante él.
   **Si algún día decide rotarlas**, el orden es: (1) PayPal Secret (es LIVE, opera su cuenta de
   cobros); (2) `SECRET_KEY` — con ella se falsifican sesiones de cualquier usuario, admin
   incluido; (3) OpenAI; (4) token GitHub; (5) correo; (6) NOWPayments; (7) PostgreSQL (solo
   localhost). Cada una con `set_env.py` + `reread && update`. **Los valores nuevos NUNCA al chat.**
   ⏳ **El único argumento que se le dio y sigue siendo cierto:** rotar `SECRET_KEY` cierra TODAS
   las sesiones abiertas. Hoy eso no le cuesta nada (3 cuentas); con clientes pagando, sí. El
   riesgo no crece con el tiempo — **crece el precio de arreglarlo**.
1. **Revisar cómo quedó "Mi cuenta"** (punto 20, hecho el 2026-08-04): dijo *"aún no he revisado
   cómo quedó"*. Preguntarle si le convence la posición (va la primera del menú) antes de darlo
   por bueno del todo.
2. 🔴 **BOTARGAS DE THE ALCHEMIST — las genera él, aún no existen (anotado 2026-08-23 a petición
   suya).** Se fue ~1-2 semanas (bajó al plan de $20) y pidió que se le recordara AL VOLVER: High
   Noon ya tiene sus 3 botargas cableadas; Alchemist vende con el muñeco-flecha por defecto hasta
   que entregue las suyas (ideas ya acordadas: matraz esmeralda + grimorio / oro logrado / matraz
   explotado con hollín y círculos de las gafas). Detalle del proceso en la sección del camo.
3. **Devolverle el escrito de PayPal cuando lo pida.** Está en la sección "▶️ RETOMAR PAYPAL" de
   este archivo: los 4 clics de su papá, sus 5 comandos, cómo comprobar que quedó bien y que la
   compra de prueba va con cuenta nueva. Se lo entrega tal cual cuando diga "sigamos con PayPal".

## 🔴 PIVOT 2026-07-26 — Socio fuera, cobro por CRIPTO, ley Venezuela
**Gabriel Celis NO se suma por ahora** (quizás más adelante). Consecuencias ejecutadas:
1. **Mentorías OCULTAS, no borradas**: kill switch `before_request` (corre ANTES del login → 404
   plano para todos menos admin) sobre `/improve*`, `/mentorship*`, `/api/ment/*`, `/api/improve*`
   + Secc. 19 de T&C + excepción de la Secc. 7 + índice, todo envuelto en `{% if mentorship_enabled %}`.
   **Volver = `MENTORSHIP_ENABLED=1` + restart**: vuelve TODO idéntico (verificado: T&C recuperan
   exactamente 7.886 chars). Las 3 fases del área de miembros quedan intactas.
2. **Sin banco USA** → cobro por **USDT vía procesador cripto (NOWPayments, patrón condicional)**:
   `CRYPTO_API_KEY`/`CRYPTO_IPN_SECRET`/`CRYPTO_PAY_CURRENCY` (default usdttrc20) en env — sin claves,
   producción sigue con el flujo manual USDT intacto. Flujo: order pending → factura hosteada
   (redirect 303) → webhook firmado HMAC-SHA512 `/webhook/crypto` activa (idempotente, reusa
   `_activate_plan_from_order`). **3 redes de seguridad**: (a) `/checkout/status/<id>` reconcilia
   contra el procesador al abrirse (+ poll 10s, + `/api/checkout/txid` para pegar el hash);
   (b) **barrido al abrir /admin** (`crypto_sweep`) — recupera pagos cuyo aviso se perdió aunque el
   cliente nunca vuelva; (c) bandeja "Pagos que necesitan atención" en Revenue (pagó-sin-activar /
   pago parcial / pendiente >24h) + botón activar a mano. **Correos al dueño**: venta confirmada,
   pago con problema (1 sola vez, `alerted_at`), y "pagó pero NO se activó" (ACCIÓN REQUERIDA).
   ⚠️ Sin `MAIL_APP_PASSWORD` los avisos solo van al log. Precios SIEMPRE en USD; USDT es el riel.
   Promesa pública: activación <24h o reembolso 100% (`CRYPTO_SLA_HOURS`).
3. **T&C/Privacy re-anclados a VENEZUELA** (2026-07-26, EN+ES/FR/PT en legal_i18n.js):
   Secc. 1 sin "LLC en formación" ni "Tradeable LLC" (negocio independiente de un operador individual
   + mecanismo de cesión futura a una sociedad — la LLC de Celis entraría por ahí, sin nombrarla aún);
   Secc. 5 = pagos USDT vía plataforma de terceros + cláusulas cripto (irreversibilidad, monto/red
   exactos, comisiones de red, reembolsos en USDT al valor USD, SLA 24h) + sigue el NO auto-renew;
   Secc. 14 arbitraje AAA → **tribunales competentes de Venezuela** (informal 30 días primero,
   reclamos individuales, carve-out de derechos irrenunciables del consumidor en su país, cláusula de
   "cesión futura" para volver a jurisdicción de la LLC); Secc. 15 Delaware → **República Bolivariana
   de Venezuela** + carve-out consumidor. Privacy 2.2 + tabla de terceros: plataforma cripto, nunca
   datos de tarjeta. ⚠️ **Validar Secc. 14/15 con abogado antes del lanzamiento** (elección de foro).
   ⚠️ `checkout_done.html` (instrucciones manuales Binance) queda como fallback sin claves cripto.
4. **PayPal: CABLEADO como 2º método (2026-07-26, decisión del usuario tras consultarlo con su hermano).**
   Se había desaconsejado (contracargos de bienes digitales sin protección al vendedor, ventana de
   disputa de 180 días, riesgo de revisión/retención en cuenta personal); el usuario reafirmó el pedido
   → construido. Mercados: USDT cubre Venezuela/Argentina/Colombia/Brasil/Perú; **PayPal recupera
   USA/Canadá/Europa**, que era el objetivo. Ver "🟣 PayPal" abajo.
**Para ENCENDER el cobro:** cuenta en nowpayments.io → API key + IPN secret → `CRYPTO_API_KEY` y
`CRYPTO_IPN_SECRET` en supervisor conf + `scalpel/.env` (NUNCA en el repo/chat) → restart. El webhook
se registra al crear cada factura (`ipn_callback_url`); **sin dominio/HTTPS el webhook puede fallar,
pero la reconciliación del success_url + el barrido de /admin cubren la activación igual**. Dominio
sigue siendo el desbloqueo para que el aviso instantáneo sea fiable.

## 🔴 Bug REAL cazado en la 1ª compra de prueba (2026-08-05) — te cobraba OTRO plan
**Síntoma del dueño:** *"fui a pagar por un plan standard y se me cobró y activó uno premium"*.
**NO era el sandbox** (lo sospechó, y era razonable): el cableado de PayPal estaba bien.
`checkout_create` devolvía el **pedido pendiente** fuera cual fuera el plan que se acabara de
pedir. Ese guard existe para que un intento abandonado no encierre al comprador (no puede apilar
pendientes), pero a ciegas convertía el intento viejo en un **cambiazo de producto**: había
abandonado a medias una compra de Premium, volvió a por Standard, y el carrito decía $25 mientras
la pasarela cobraba $50.
**Fix:** el pendiente **solo se retoma si es esta misma compra** (plan + ciclo + precio + cupón).
Si pide otra cosa, `_soltar_pedido()` lo suelta — y soltar es tres cosas, no una: (1) cancelar,
(2) devolver el uso reservado del cupón, (3) 🔴 **cortar en PayPal la suscripción que ese pedido
hubiera abierto**, porque `_sub_cobro` salda el primer cobro contra `first_order_id` mirando solo
que NO esté pagado — **un pedido cancelado le servía igual**, así que aprobar más tarde aquel
enlace viejo entregaba el plan ya descartado. Antes de soltar nada se **reconcilia** contra la
pasarela por si se pagó hace un instante y el aviso no llegó (cancelar ahí = cobrado sin plan).
`/checkout/cancel` usa el mismo desmontaje (antes dejaba la suscripción en pie).
**Bonus:** aplicar un cupón sobre algo que ya estaba en el carrito ahora funciona (cambia el
precio → pedido nuevo). Dos checks de `test_pedido_atascado` documentaban lo contrario —que el
cupón se ignoraba y había que cancelar a mano— y se actualizaron.
⚠️ **Lección:** un guard "no apiles pendientes" **tiene que comparar QUÉ es el pendiente**. Y esto
no lo cazó ninguna de las 46 comprobaciones de PayPal simulado: todas compraban UNA cosa. Lo cazó
la primera compra de una persona, que abandonó a mitad — como hace todo el mundo.
`tools/test_pedido_pendiente.py` **18/18** (con el código viejo falla justo el caso reportado).

## Stack técnico
- Backend: Flask + SQLAlchemy + PostgreSQL (prod) / SQLite (local). Auth: Flask-Login (free/standard/premium).
- IA: OpenAI SDK → GitHub Models hoy (GPT-4o Vision análisis, GPT-4o moderación foro). **Migrar a OpenAI pago = setear env var `OPENAI_API_KEY` (NO se toca código)** — el cliente en `app.py` (~línea 180) es condicional: con la clave usa OpenAI pago (sin `base_url`), sin la clave cae a GitHub Models. Log de arranque `[AI] backend=openai|github model=…` en `trader.out.log`. Reversible: quitar la env var y reiniciar. Mismo modelo/prompt para ambos.
- Frontend: Jinja2 + vanilla JS, i18n EN/ES/FR/PT (`scalpel_lang`), tema claro/oscuro (`scalpel_theme`, default light).
- App: `scalpel/app.py`. Local: `FLASK_DEBUG=1 python3 scalpel/app.py`.

## Límites de plan
| Plan | Screenshots | Ventana | Proyectos analizador | Foro | Pre-Flight |
|---|---|---|---|---|---|
> ⛔ **PLANES ANUALES APAGADOS (2026-08-01)** — `ANNUAL_PLANS_ENABLED` (env, default 0). Motivo: un
> anual de $390 con contracargo cuesta $390 + $20 de multa + la fee ya pagada = **$314 de tu
> bolsillo**, y la reserva del 25% sobre esa venta solo apartó $97,50 → faltan **$217**, que a $10
> por suscriptor mensual son **22 meses-cliente**. El mismo contracargo en un mensual deja $40. Y la
> ventana de disputa de PayPal son 180 días. **Apagado, no borrado:** `allowed_cycles()` filtra solo
> las 3 puertas del COMPRADOR (`/checkout`, `/checkout/create`, `validate-code`); el precio base, el
> libro de ventas y las previews siguen aceptando anual para no romper pedidos existentes, y **una
> suscripción anual vendida antes del cambio corre hasta su vencimiento**. En las plantillas se
> oculta el **selector entero** (un toggle de un solo botón se lee como roto). **T&C Secc. 5**
> reescrita para remitir a "los ciclos ofrecidos al finalizar la compra" (mismo patrón que el párrafo
> de métodos de pago) → correcta con anuales apagados y con anuales encendidos, sin reeditar el
> contrato; de paso se quitó "los mensuales se cobran de forma recurrente", que contradecía el
> no-auto-renew. ES/FR/PT traducidos, `audit_legal_translations.py` 141 cláusulas OK.
> `test_annual_off.py` 13/13.

| Free | 1 | 7 días | 1 | ✗ | ✗ |
| Standard | 1 | 24 h | 5 | ✓ (desde 2026-07-25) | ✗ |
| Premium | 5 | 24 h | 10 | ✓ | ✓ (10 checklists, mismo `project_limit()`) |

- **Foro = Standard + Premium (2026-07-25):** gate nuevo `standard_required`/`is_standard_up()` en app.py
  (8 endpoints /forum/*); cliente: `isPaid` en `setupFeaturePanels()` (forum-view keyea isPaid, resto isPremium),
  candado del tab forum, `switchTab` forum abre con standard, `forum.intro` ya no dice "Premium traders" (×4).
  Cards actualizadas: landing Standard (+`ps_forum` ×4), pricing.html standard card + tabla, checkout.html
  standard included. **Premium camos: la card decía "3 Camos included" → corregido a 1 camo especial** (pp_camos
  ×4, tabla comparativa 3→1, camos.hero "two ship with your plan"→"cada plan de pago incluye su propio skin" ×4).
  ✅ **Camo de plan CABLEADO (2026-07-27):** `PLAN_CAMOS = {'standard':'standard','premium':'premium'}` +
  `grant_plan_camo(user, plan, switch_on)` llamado desde `_activate_plan_from_order`. Al comprar: escribe el
  slug en `owned_camos` (**permanente**, como prometen los T&C Secc. 5) y lo **enciende solo** si (a) es un
  plan nuevo para el usuario —no una renovación— y (b) no tiene otro camo activo, para no pisar su elección.
  `owns_camo()` ahora mira `camos_owned()` PRIMERO → el camo sobrevive al vencimiento del plan (antes se lo
  quitaba, contradiciendo los T&C). ✅ **El camo `standard` YA tiene tema (2026-07-30) y está en
  `CAMO_READY`** → al comprar Standard se otorga **y se enciende solo** (antes se otorgaba inerte).
  **REGLA (usuario, 2026-07-27): NINGÚN camo se revoca jamás** — ni comprado ni obtenido con un plan. Por eso
  `_backfill_plan_camos()` corre en `init_db()` y registra el camo en las cuentas que YA tenían plan pagado
  antes de este cambio (solo agrega, nunca quita).

## Feature flags
- **Prop Firm Scout:** construido pero DESACTIVADO (`SCOUT_ENABLED=False` en `app.py`). Reactivar solo si el usuario lo pide.
- **Mentorship:** `MENTORSHIP_ENABLED` (env, default 0). Con flag off el funnel es admin-only (preview por URL).

---

## 📋 TAREAS PENDIENTES

### ✅ CHECKLIST DEL DUEÑO — 25 puntos (dictada 2026-08-03)
> 🔴 **Esta lista NO se toca ni se borra hasta que él lo diga.** La dictó de memoria porque **se le
> murió la pantalla del teléfono** y perdió sus notas. Instrucción explícita: *"No es para hacerlo
> todo de golpe, es para ir uno por uno como si fuese una checklist y resolviendo cada problema con
> Calidad, no con apuro."* Marcar ✅ al cerrar cada punto, con una línea de qué se hizo.
> (Renumerada 1-25: su lista traía dos #6 y saltaba el #8 y el #16.)

- [x] ✅ **1. Landing page desactualizada (2026-08-03, commit `5d8ae27`).** (a) Pre-Flight agregada
  al plan Premium; (b) **precios: se quedan redondos $25/$50** — decisión del dueño, opción A, NO
  reabrir; (c) "4 metodologías" → **7**, con los nombres reales (el analizador tiene 7 approaches y
  *Price Action* ni siquiera era uno); faltaban Harmonic y Elliott Wave en la rejilla, y
  "Quantitative & Hybrid" no correspondía a ningún botón (el real es *Technical Analysis*); la
  tarjeta STDV pasó a *OTE / Standard Deviation*; (d) bloque *"Sound familiar?"* reescrito para que
  los tres dolores mapeen uno a uno con lo que el sitio hace hoy (analizador, Pre-Flight, quiz);
  (e) *"WHAT THE AI READS"* reescrito: la IA no detecta patrones, **aplica la metodología que elige
  el trader** y explica la operación ya tomada — y de paso cierra por el lado legal, porque dice
  explícitamente que nunca indica qué operar; (f) los dos posts de ejemplo del foro llevaban
  objetivo de precio y sonaban a señal → reescritos como preguntas de estudio; (g) fuera su nombre
  del ranking de ejemplo. **Hallazgo aparte:** *"Sound familiar?"* y los posts del foro estaban
  **hardcodeados en inglés, sin `data-t`** → se veían en inglés bajo ES/FR/PT; ahora cableados ×4.
  · **Lo único que queda del punto es (h) y NO es trabajo de código:** decidir si su propio
  testimonio se publica. Desde el 2026-08-01 hay pestaña **"⭐ Reseñas"** en `/admin` para
  publicarlo o retirarlo con un botón, y la etiqueta de "fundador" ya sale sola (regla FTC).
  Recomendación dada: **no publicarlo** — 5 estrellas firmadas por el dueño restan credibilidad al
  resto, aunque estén etiquetadas.
  > ⚠️ Este punto se cerró el 2026-08-03 pero **se quedó sin tachar aquí**, y al día siguiente lo di
  > por pendiente y se lo volví a ofrecer al dueño. **Tachar el punto es parte de cerrarlo.**
- [x] ✅ **2. El acuerdo, reescrito entero (2026-08-10).** Ya trae los **3 meses iniciales** (5.1),
  la **revisión a los 30 días** (5.2) y la renovación por períodos de 3 meses (5.3). Vive en
  **`docs/acuerdo_colaboracion.md`** y se publica en PDF con **`tools/build_acuerdo_pdf.py`**
  (el `.md` es la fuente de verdad; el PDF **jamás** se edita a mano). Se aplicaron las 20
  anotaciones de su papá + lo hablado ese día. Decisiones de fondo que quedan fijadas:
  · **"socio" queda PROHIBIDO** en todo el documento → **"el Colaborador"**, prestador de servicios
    independiente: la palabra contradecía la propia cláusula de "no existe sociedad".
  · La escala 30/35/40 se explica **cliente por cliente** (con dibujo ASCII y ejemplo numérico);
    fuera "marginales" y "no es una medalla", que no se entendían.
  · Bajas: *"los que llegaron después cubren los puestos que quedaron vacíos"* (la metáfora
    arriba/abajo se eliminó — cada uno la leía al revés).
  · **Liquidaciones SIEMPRE en USDT** (no hay caja garantizada en PayPal). La comisión de RED del
    envío la paga la plataforma; conversión y retiro los paga él.
  · Revisión a 30 días = **conversación, no derecho a exigir cambios**: ninguna parte puede
    imponerle nada a la otra (miedo explícito del papá a una réplica económica en su contra).
  · **Renovación AUTOMÁTICA** por trimestres (el papá rechazó tener que firmar de nuevo cada vez).
  · Preaviso de cambios de producto **15 → 5 días**.
  · Cesión: solo formalizar el MISMO negocio en una empresa suya; **una venta o cambio de dueños
    exige acuerdo nuevo** (el texto viejo se leía como perpetuo aunque cambiaran los dueños).
  · No se usa "suscripción mensual" al definir la atribución: dejaría fuera el ciclo **anual**.
  · Logotipo **solo al final, centrado** (se intentó también un membrete arriba y lo rechazó).
  ⚠️ **Sigue SIN decidir:** el 5.4 (terminación anticipada) conserva **15 días** de preaviso — el
  papá solo pidió bajar el del punto 7. Y faltan por rellenar los 6 huecos entre corchetes.
- [x] ✅ **3. "My coupons" — condicional + emisor de códigos personales (2026-08-09).** Decisión:
  no se quita — la entrada del menú aparece **solo si la cuenta tiene algún código personal**, y
  **sin filtro de plan** (era premium-only: quien ganó un SPIN y bajó de plan dejaba de poder VERLO
  aunque siguiera válido — contra "nada se revoca jamás"; el free con cupón es justo el comprador).
  `/api/daily/coupons` pasó a @login_required; `has_coupons` viaja en SCALPEL_USER. **T&C ya
  correctos** (Secc. 6 dice "wheel prizes currently consist of virtual cosmetic items" — verificado,
  nada que tocar). **Bonus: /admin ahora emite códigos PERSONALES** (campo "Personal para (usuario)"
  → `restrict_user_id`; usuario inexistente = NO se crea el código): la pieza que faltaba para
  entregar premios de sorteos de /socials sin publicar un código que cualquiera pueda usar, y para
  compensaciones. Ya nada más crea códigos personales (la ruleta da cosméticos desde el 2026-08-02).
  `tools/test_mis_cupones.py` **11/11** + navegador real (free con cupón ve y abre su modal, 1 fila;
  premium sin cupones no ve la entrada; 0 errores JS). ⚠️ Ruta real:
  `/api/checkout/validate-code`, no `/api/validate-code`.
- [x] ✅ **4. Discover — cosméticos nuevos (2026-08-03).** Dos tarjetas: en **Extras** (la sección
  que ven Free, Standard **y** Premium, porque son compras aparte) la vieja "Tienda de camos"
  pasó a ser **"Tienda de cosméticos"** — camos + placas de foro + cursores, con la línea honesta
  de que el cursor solo se ve en computadora y que el carrito se paga de una sola vez; y en
  **Premium** una tarjeta nueva **"Ruleta de cosméticos del mes"** (la racha da giros; cada mes
  una tanda de 1 camo + 2 placas + 3 cursores; al acabar el mes esa tanda no vuelve). Ambas con
  pastillas Camos/Placas/Cursores. Redactado por idioma, no traducido: ES tú-LatAm, FR vous, PT-BR
  você. **De paso, 3 etiquetas "Próximamente" MENTIROSAS borradas** — colgaban del camo de
  Standard, del de Premium y de la tienda, y las tres cosas ya existen y se entregan (lo que falta
  es el riel de cobro, que tampoco lleva etiqueta en los planes). 5 claves nuevas ×4 a paridad
  (58/58/58/58, 0 claves de plantilla sin dict). Verificado en navegador con un usuario **Free**
  real en los 4 idiomas, 0 errores JS.
- [x] ✅ **5. T&C — cosméticos delimitados (2026-08-07).** La Secc. 5 pasó de hablar solo de "camos"
  a definir **cosméticos** como categoría: camos, **marcos de perfil** y **cursores** (con la nota
  honesta de que el cursor solo se ve en escritorio). Cubre además lo que no estaba escrito en
  ninguna parte: **ventanas festivas de 24h y rotación mensual** ("cuando su ventana o rotación
  termina, un artículo puede dejar de estar disponible permanentemente, y nada te da derecho a
  exigir que vuelva"), las piezas **solo-ruleta que jamás se venden**, y que lo comprado **Y lo
  ganado** queda anclado a la cuenta aunque el plan venza — la regla "nada se revoca jamás", ahora
  en el contrato. ×4 idiomas, auditor 144 cláusulas OK.
- [x] ✅ **6. T&C — ruleta con premios cosméticos (2026-08-07).** La Secc. 6 ya nombra los
  **cosméticos como premio**, su rotación mensual y que el premio entregado se queda. ⚠️ El párrafo
  de **códigos de descuento se CONSERVA a propósito**: los códigos del socio comercial y los SPIN
  viejos siguen vivos, así que ese texto sigue haciendo falta — no borrarlo pensando que sobra.
  · **Extra cazado al revisar:** los T&C decían que el PDF de Synapse era para suscriptores Premium
    y el **endpoint `/api/synapse/pdf/buy` no lo exigía** — la UI lo escondía, pero una cuenta Free
    podía comprarlo llamando la URL a mano. El dueño confirmó la regla (*"para acceder a Synapse
    ajuro necesitas premium"*) → candado server-side (`403 premium_only`), y **lo comprado
    sobrevive al downgrade** (`/synapse/pdf/mine` sin candado, como prometen los T&C).
    `test_pdf_venta.py` **42/42**.
  🔴 **(2026-08-08) La tarjeta de venta del PDF que había en la landing se ELIMINÓ por orden del
    dueño** (*"YO JAMÁS TE PEDÍ que metieras la venta del PDF en la landing"* — el commit `47afe4f`
    decía lo contrario, da igual): **la venta vive SOLO dentro de Synapse**, en el modal de siempre.
    NO re-agregar tarjetas/menciones de venta del PDF a la landing. El cableado interno quedó
    verificado tras la cirugía: 42/42 + landing sin restos `sylib`/`sy_*` + node --check.
- [ ] **7. Validez jurídica de la propuesta comercial.** No tiene empresa constituida ni vive en la
  zona del influencer. ¿Qué valor legal tiene el documento? ¿Firmarlo le da marco legal?
- [x] ✅ **8. Tessera — la Cámara pasa a CONSTELACIÓN (2026-08-10, aprobado: *"quedó excelente"*).**
  Tenía razón con la tipografía: TODO era Inter (título 30px/700, tarjetas 15.5px/600) y las
  "puertas numeradas con brackets" de la nota vieja habían decaído en **cinco filas de lista con
  hairlines**. Se le pasaron **8 maquetas** (A instrumentos · B puertas · C placa grabada ·
  D constelación · E mosaico · F ascensor de acero · G proyección sobre la pared · H rubí) y
  eligió **D**. Generadores en `scratchpad/tessera_mock.py` y `tessera_mock2.py`.
  · Cada puerta = un nodo con su hilo (lenguaje de Synapse). **Space Grotesk** muy espaciado en
    el título + **JetBrains Mono** en los números; las dos ya las carga el `<link>` de la página
    → cero peticiones nuevas. El **nodo entero es el botón**, no solo la etiqueta.
  · 🔑 **Los hilos y los nodos comparten las MISMAS coordenadas** (`NX_NODOS`/`NX_HILOS`): el SVG
    va con **`preserveAspectRatio="none"`** + `vector-effect:non-scaling-stroke`, y los nodos se
    colocan en % desde esos mismos números. Con el `meet` por defecto el SVG se centra con banda
    y **las líneas quedan cortas sin dar ningún error** — es el fallo clásico de este dibujo (la
    maqueta D se envió con él). Medido en navegador: extremo del hilo a **0.01 px** del centro
    de su punto. Mover un nodo mueve su hilo; NO duplicar esos números.
  · Los hilos de abajo cuelgan de su **vecino de arriba**, no del nodo central: un hilo 0→3
    cruzaba por encima de la descripción del 0 y parecía atravesarla.
  · **<820px la constelación no cabe** (cinco etiquetas de 160px) → las mismas puertas en columna
    y el SVG oculto (sin SVG no puede quedar un hilo suelto).
  · **Descripciones de las 5 puertas acortadas ×4 idiomas**: 76 caracteres en una columna de
    ~160px a 11px son 4 líneas y desbordaban. Subtítulo → "Cinco puertas · elige una", **oculto
    dentro del teletransportador** (`#nx-ov.nx-inner`), donde ya no hay puertas que elegir.
  · Verificado en navegador real (1440/1180/430 px · EN/ES/FR/PT): **0 px de desbordamiento en
    los 4 idiomas**, panel dentro de la pared del fondo, puerta 01 abre el chat y el ← vuelve
    con la constelación intacta, 0 errores JS. Visores: `scratchpad/ver_tessera2.py` y `3.py`.
  ⚠️ Trampas del entorno: **recargar `/app` rebota a `/welcome`** (fijar el idioma ANTES de
  entrar, y poner el cookie `scalpel_splash_ts`); y **Google Fonts es inalcanzable en el
  contenedor**, así que sin inyectar el pack embebido (`scratchpad/fuentes/caras.css`) se juzga
  la fuente del sistema en vez de la que se está eligiendo.
- [x] ✅ **9. Atribución de las 2 esculturas 3D de Synapse (2026-08-03).** No estaba borrada, pero
  daba igual: `.model-credits` vivía a **9.5px con `opacity:.62`** pegada al `<footer>` de
  `index.html` (o sea **solo en `/app`**), y **dentro de Synapse no aparecía**: `.synapse-app` mide
  `100vh - 108px`, así que el pie queda debajo del scroll justo mientras los modelos están en
  pantalla. CC BY pide atribución "razonable al medio" y eso no lo era.
  **Hecho:** crédito nuevo **`.syn-credit` DENTRO de Synapse** (centrado abajo) + el del pie a
  11.5px, ambos con **enlaces al autor y a la licencia** (la licencia también los pide).
  🔑 **Los dos en NEGRITA + HALO (`text-shadow` ×3 capas), sin caja de fondo.** El problema es que
  el texto va suelto sobre fondo impredecible: en el pie **cae literalmente encima del dibujo del
  camo** (las montañas de Marte, el reino de Chronicles) y en Synapse hay un **canvas WebGL** que
  puede pintar cualquier color justo debajo. Medido: antes **8 de 10 camos** dejaban el pie
  ilegible (mission claro = **1.02** sobre un umbral de 4.5).
  ⚠️ **Se probó primero con una pastilla opaca detrás y el usuario la RECHAZÓ** (*"me molesta
  visualmente el rectángulo blanco"*) — y tenía razón en lo de fondo: **ninguna licencia pide un
  recuadro**, CC BY solo pide que la atribución sea perceptible. También preguntó si bastaba con
  **negrita**: no, la negrita sola no cambia el color, solo pone más píxeles del mismo tono (1.02
  seguiría siendo 1.02); lo que sostiene la legibilidad es el halo, y la negrita ayuda porque le da
  más superficie. Verificado VISUALMENTE sobre el arte real de los camos y, en Synapse, con la
  escena forzada a negro / blanco / degradado claro / degradado cálido.
  `scratchpad/verifica_credito.py`. ⚠️ **Tres trampas del entorno, anotadas para no repetirlas:**
  (1) **three.js viene de un CDN inalcanzable en el contenedor** → el motor 3D NUNCA arranca aquí y
  Synapse se queda en su pantalla de carga, que **tapa** el crédito; para medir hay que ocultar
  `#syn-loading`. (2) `pg.screenshot(clip=...)` usa coordenadas de **página** y
  `getBoundingClientRect()` de **viewport** → con la página desplazada se mide otra zona (daba 1.03
  donde el CSS daba 10); usar `locator.screenshot()`. (3) al medir contraste hay que **componer el
  alfa del color del texto** sobre su fondo: un `rgba(23,25,35,.56)` no se ve tan oscuro como
  `(23,25,35)` y el contraste sale inflado.
  🔴 **Deja destapado el punto 10:** el `<footer>` que va JUSTO ENCIMA sigue con `--muted` suelto
  sobre el camo — mismo defecto, sin arreglar.
- [x] ⛔ **10. Legibilidad bajo camos — INTENTADO Y REVERTIDO (2026-08-04). NO reabrir sin que él
  lo pida.** El dueño lo paró: *"revierte lo que hiciste y dejemos todo como estaba"*. El sitio
  quedó **idéntico** (revert `e221f5b` de `f94ecb1`); no se tocó nada del punto 9.
  **Lo que sí quedó aprendido, para no repetir los errores si algún día se retoma:**
  · 🔴 **Medir el contraste con un número NO sirve contra un camo.** El fondo es una ILUSTRACIÓN:
    en la misma frase puede haber montaña oscura detrás de una mitad y cielo claro detrás de la
    otra. No existe un número que describa eso, ni un color de texto que funcione contra las dos.
    Se perdieron ~2 h construyendo un medidor de contraste por píxeles que solo daba ruido.
  · ⚠️ **Dos fallos del medidor, por si se vuelve a intentar:** (1) el filtro de "está protegido por
    un panel" exigía alfa ≥ 0.55 y los paneles del sitio son de VIDRIO → cientos de falsos
    positivos de texto que sí estaba protegido; (2) un recorte de un solo color se contaba como
    fallo con contraste 1.00, cuando significa que el texto no estaba ahí. **La pista de que todo
    era ruido: salían fallos SIN camo puesto.**
  · ✅ **Lo que SÍ funciona para enumerar el problema** (3 min, sin medir píxeles): recorrer el DOM
    y quedarse con el texto cuyo camino de ancestros hasta `body` no tiene NINGÚN fondo. Da 67
    nodos reales: encabezados de sección, calendario económico, foro, Pre-Flight, quiz y el pie.
  · 🔴 **El diagnóstico del ejemplo era erróneo:** el subtítulo que él señaló (*"Submit a trade for
    analysis…"*) NO es el caso malo — el dibujo de los camos vive ABAJO, así que arriba el texto
    cae sobre fondo liso. El que de verdad se pierde es **el pie**, que es justo el que el punto 9
    dejó explícitamente sin arreglar. ⚠️ Y él avisó que la ilegibilidad está **en varias partes**,
    no solo donde se miró.
  · ⚠️ **Un halo solo no basta ahí:** medido en el navegador, se aplicaba bien (crema sobre marrón)
    y aun así el pie seguía sin leerse, porque es de **11px con transparencia 0.64**. Haría falta
    tocar también el color, no solo ponerle contorno.
  · Las herramientas quedan en el repo por si sirven: `tools/audita_legibilidad.py` (el medidor,
    con sus trampas documentadas) y `tools/compara_legibilidad.py` (antes/después en la página
    real, apagando el arreglo con una clase en el `<html>`).
- [x] ✅ **11. PDF de Synapse interactivo (2026-08-04).** Las 41 líneas del índice son enlaces que
  saltan a su tema, y **además** el PDF lleva ahora **46 marcadores** — el panel de índice que abre
  el propio lector, que es lo que permite recorrerlo sin volver a la primera página cada vez
  (metodología en nivel 1, tema en nivel 2, vía `bookmark-level` de WeasyPrint).
  · El enlace **no parece un enlace**: hereda el color del índice, sin azul ni subrayado — un PDF
    de pago lleno de azul subrayado se lee como una web mal impresa.
  · ⚠️ **Un ancla muerta NO da error**: el enlace existe, se pulsa, y te deja al principio del
    documento. Por eso la comprobación no fue "¿hay enlaces?" sino resolver la tabla de destinos
    del PDF y verificar que **cada uno cae en una página distinta** (41 destinos → 41 páginas
    distintas, de la 5 a la 49, ninguno al inicio). Verificado en los 4 idiomas.
  · ⚠️ Trampa al verificar: WeasyPrint escribe destinos **con NOMBRE** (`/Dest: tema-…` + tabla
    `/Names/Dests`), no arrays de página. Un lector que espere arrays da "sin resolver" y parece
    que los enlaces están rotos cuando están perfectos.
- [x] ✅ **12. PDF de Synapse — más sustancia (COMPLETO 2026-08-04, las 5 tandas).**
  Diagnóstico medido: cada tema traía 367–962 chars (mediana ~600) — ficha de glosario, no capítulo.
  **El sistema (ya cableado, commiteado):** 4 campos nuevos y OPCIONALES por tema —
  `playbook` (la secuencia narrada, 3-6 pasos, caja verde) · `fails` (modos de fallo honestos,
  caja ámbar) · `drill` (un ejercicio concreto de backtest/journal, caja azul) · `related`
  (2-3 temas conectados CON ENLACE INTERNO usando las anclas del punto 11 — la red de Synapse
  dentro del PDF). Un tema sin tanda se imprime exactamente como antes (cero secciones vacías).
  El merge del PDF pasó a ser campo-a-campo como el web (antes un idioma rezagado PERDÍA
  secciones enteras en silencio). Etiquetas en `CHROME` ×4. `tools/validate_synapse_content.py`
  exige tanda completa, paridad ×4 idiomas, slugs de related reales y ratios de longitud.
  **Tanda 1 = Price Action (9 temas × 4 campos × 4 idiomas) ESCRITA y verificada:** PDF 50→59
  págs, 68 enlaces todos con destino válido (41 índice + 27 related), render inspeccionado
  visualmente (pymupdf). El contenido va en los JSON (`synapse_export.json` EN +
  `synapse_content_{es,fr,pt}.json`); ES=tú LatAm, FR=vous, PT-BR=você, jerga en inglés.
  **Tanda 2 = Technical Analysis (9 temas ×4×4) ESCRITA y verificada (mismo día):** PDF 59→68
  págs, 95 enlaces todos válidos, render inspeccionado (RSI). Doctrina alineada con el system
  prompt del analizador: la confluencia real cruza FAMILIAS (dos osciladores = una señal contada
  dos veces), los indicadores rezagan, divergencia regular≠oculta, Clase A, RSI clavado en
  tendencia, volumen con reloj de sesión, head-fake del squeeze.
  **Tanda 3 = SMC/ICT (11 temas ×4×4, la insignia) ESCRITA y verificada (mismo día):** PDF
  68→79 págs, 128 enlaces todos válidos, render inspeccionado (Order Blocks). Canon del
  DAILY_BANK: el OB se califica por su ORIGEN (barrida→displacement→BOS), inducement como
  carnada, mecha≠ruptura (sweep argumenta lo contrario), gaps como salud de la tendencia,
  CE, re-anclar el dealing range tras un sweep, kill zone = reloj no mecanismo, spring
  calificado por volumen, "más compradores que vendedores" es imposible.
  **Tandas 4+5 = Fundamental (6) + Quant (6) ESCRITAS y verificadas (mismo día) → 41/41 temas
  con su tanda.** RESULTADO FINAL: PDF **50→91 páginas** (casi el doble), **164 enlaces** internos
  todos con destino válido en los 4 idiomas, 46 marcadores, validador en verde. Canon fundamental:
  expectativas vs titular, el par cotiza DOS trayectorias, primer movimiento miente, fade solo de
  segundo nivel, zonas perforadas en noticia = falla de ejecución. Canon quant: expectativa desde
  el journal propio, rachas presupuestadas antes, Kelly como techo, martingala = disfraz de la
  ruina, el filtro de régimen ES la estrategia, pseudocódigo como espejo de lo discrecional.
  ⚠️ Un carácter chino se coló en un playbook EN ("每 session") — cazado por relectura antes de
  inyectar. Releer siempre la tanda antes de correr el inyector.
  Tras cada tanda: `python3 tools/validate_synapse_content.py` + rebuild + mirar el render.
  ⚠️ El flipbook web ignora los campos nuevos sin romperse (Object.assign) — los podrá usar
  algún día, pero HOY la profundidad es exclusiva del PDF de pago, lo que justifica su precio.
- [x] ✅ **13. Chalkboard funcional (2026-08-12).** Su queja textual: *"cuando seleccionabas una
  herramienta y la utilizabas tenías que volver a activarla, siento que vuelvo todo muy lento"*.
  · **Herramienta PEGAJOSA**: se quitó el `setTool('select')` que venía detrás de cada figura, línea,
    rayo y polilínea. ⚠️ **El texto es la única excepción a propósito**: al crearlo se entra a
    editar y el clic siguiente sirve para SALIR de la edición — con la herramienta puesta, ese clic
    crearía otro cuadro encima del que acabas de escribir.
  · **Atajos de una letra** (`ATAJOS`: v/p/l/r/o/t/e/a/h/y/n/f/d/c), **Ctrl+D** duplica (maneja el
    `activeSelection` desagrupándolo), **flechas** mueven 1px (10 con Shift), **Esc** vuelve a
    Seleccionar, y pulsar dos veces la misma herramienta la apaga.
  · 🕯️ **Secuencia de velas** (lo que él pidió): se arrastra y salen velas coherentes — cada una
    abre donde cerró la anterior y la mecha siempre contiene al cuerpo; la dirección del arrastre
    fija la tendencia, una vela por cada ~34px (4-20). ⚠️ **`state.lastX/lastY` hace falta** porque
    el rectángulo-guía normaliza min/max y ahí se pierde hacia dónde arrastraste.
    ⚠️ **Dos defectos que solo se vieron MIRANDO el dibujo:** con el ruido por debajo de la deriva
    salía una escalera perfecta (0 px rojos — ningún retroceso, imposible en un gráfico), y con las
    mechas de valor fijo salían cuerpos de 8px con mechas de 34. Las dos cosas se miden ahora en el
    test contando píxeles verdes/rojos.
- [x] ✅ **14. Chalkboard visual — el panel encogido, y luego la barra (2026-08-12).**
  · **1ª parte:** la pizarra usaba el **29%** de su panel → **93%**. El rail derecho de la app se
    esconde en esta pestaña (`body.ag-chalk-mode`), la rejilla pasa a 2 columnas y `fitCanvas()`
    calcula el alto disponible desde la posición real del contenedor (tope de escala 1.75 fuera de
    presentación, para no reventar la nitidez).
  · **2ª parte (él, al usarlo):** *"luego del límite inferior de la primera diapositiva aún hay más
    herramientas hacia abajo"*. Medido: **961 px fijos y 20 botones** → a 1440×900, **10 botones por
    debajo del lienzo y 4 FUERA de la pantalla**; a 1366×768, 11 y 6. **Ahora 335 px y 7 botones, 0
    y 0** en las tres resoluciones. Tres familias con desplegable (Líneas · Zonas · Velas) y los 7
    ajustes/acciones suben a la barra de arriba junto a Fondo/Presentar/PNG/Exportar PDF.
    🔑 **NO se reescribió el HTML de la barra: se MUEVEN los botones que ya existen** a sus
    desplegables, así cada uno conserva su manejador y `setTool`/`toolBtns`/atajos no se enteran.
    Un clic en la cabecera activa la última usada de esa familia (el caso normal sigue costando un
    clic); el desplegable abre al posar el ratón y lleva los nombres escritos.
  · ⚠️ **Se le propuso y se DESCARTÓ la barra en "L"** que él mismo sugería (herramientas bajo la
    diapositiva): se come justo el alto que acabábamos de recuperar —70 px a 1366×768, el 16% de la
    pizarra— y no escala, con la siguiente tanda vuelve a llenarse.
  · ⚠️ **Tres trampas de CSS, todas invisibles leyendo el código:** (1) `var(--card)` es
    **translúcido** → sobre la pizarra negra el desplegable salía gris y los nombres a medias (se
    opaca con `linear-gradient(var(--card),var(--card)), var(--bg)`, el mismo truco de los menús
    bajo camo); (2) el tooltip de la cabecera se coloca 48px a la derecha, o sea **dentro** del
    desplegable, y caía encima del primer nombre de su propia lista; (3) la flechita del grupo tuvo
    que irse a `::before` porque **`::after` de `.tool-btn` ya lo ocupa el tooltip** (`content:
    attr(data-tip)`) — misma especificidad, ganaba la última y la flecha se convertía en el tooltip
    descolocado.
  · 🔴 **El desplegable se cerraba al ir a coger la herramienta** (lo reportó él al usarlo). Entre
    la cabecera y el panel hay **8 px de aire que no pertenecen a ningún elemento**: al cruzarlos
    salta el `mouseleave` del grupo. Arreglado con un **puente transparente** (`::before` del propio
    desplegable) de **exactamente 8 px** —pasarse le come el borde derecho del botón cabecera a los
    clics, porque el panel va a `z-index:80`— más **260 ms de gracia** al salir (un atajo en diagonal
    hacia el tercer nombre se sale un instante del grupo). Abrir bajó de 340 a **150 ms**: 340 se
    sentía lento y era lo que empujaba a pulsar en vez de posar el ratón.
  · `tools/test_chalkboard_ux.py` **35/35** en navegador real + `test_vendor.py` 12/12.
    🔴 **El test pasaba con ese fallo puesto:** `page.click()` de Playwright **teletransporta** el
    puntero al destino, así que nunca cruzaba el hueco. Lo que reproduce el bug es
    `mouse.move(..., steps=25)`. Verificado quitando el arreglo: con el código viejo fallan 4.
    ⚠️ La comprobación de la tendencia de las velas era **inestable** (se generan con azar y medir
    solo el verde baila entre ejecuciones) → mide verdes **y** rojas: en un tramo alcista las rojas
    suben igual.
    ⚠️ El selector del test filtra `.tool-btn.active[data-tool]`: la cabecera de familia también se
    enciende y no lleva herramienta.
  · **PENDIENTE de preguntarle:** si 20 velas es el tope correcto, y si quiere poder editar una
    secuencia ya dibujada (hoy es un `fabric.Group`: se mueve y escala entera).
  · ✅ **CLIC DERECHO = dejar de colocar (2026-08-12).** Queja: *"si solo quieres colocar tres
    palitos no puedes, tienes que terminar la tendencia como de 5 líneas"*. **Eran DOS causas
    superpuestas:** (1) el **doble clic** que cerraba la polilínea **añade un punto de más** (su 1er
    clic coloca un vértice, el 2º cierra) → cerrar costaba un tramo; (2) **`POLY_MAX_PTS` estaba en
    6 = 5 tramos EXACTOS** y ahí se cerraba sola — ese "5" de su queja era literal. Tres niveles:
    polilínea a medias → cierra donde estás sin colocar nada · figura a medio arrastrar → se
    descarta · nada en curso → suelta la herramienta. Tope 6→**12** (con el cierre a voluntad, deja
    de gobernar la herramienta y pasa a ser red de seguridad).
    🔑 **El manejador va en el elemento del DOM, NO en `canvas.on(...)`:** fabric ignora el botón
    derecho por defecto (`fireRightClick` apagado), que es justo lo que hace falta para que cerrar
    no coloque un vértice. De paso se quita el menú del navegador sobre el dibujo.

## 🔵 Stand-by / futuro (detalle en CLAUDE_ARCHIVE.md)
- **Replay Lab** — reconstrucción histórica de trades (determinista, legal-safe). Fase 1 Forex+Gold-spot (data gratis Dukascopy, ~$0), Fase 2 NQ/MES (licencia CME por cotizar). ~1.000-1.500 líneas, Lightweight Charts ya vendorizado.
- **Sistema XP/Rangos** — ✅ CABLEADO Y FUNCIONANDO (verificado 2026-07-12). `add_xp()` se llama server-side en: login (`app.py`:1991), análisis (:3937), quiz (:5727, cliente `handleAnswer`→`/api/quiz/answer` en `index.html`:20744, premium/admin), daily correct+streak (:5544-46, cliente `/api/daily/answer`:21368), foro post/comment/reacción (:4313/4366/4400), testimonio (:5675), pre-flight first+check (:6474-75). El cliente refresca `U.xp`/`U.rank` con la respuesta. XP = ledger append-only `XPLog`; `rank = rank_for_xp(sum)` (monótono → nunca baja). Up/downgrade NO tocan xp/rank (`_expire_plan` solo cambia `plan`). FALTA aún: certificado PDF de rank-up, y diseñar los 8 camos por rango (con el usuario, no autónomo).
- **Trade of the Day** — descartado hasta tener ingresos estables.

---

## ⚖️ Reglas permanentes
- Todo el sitio debe sonar **educativo/informativo**, NUNCA asesoría financiera / recomendación /
  señal / promesa de ganancia / absolutismo. (Auditoría legal hecha; ver archivo.)
- **Reseñas:** solo usuarios reales (regla FTC 2024); nada inventado.
- **Anti-trampa quiz/daily:** validación server-side (`quiz_answer_key.json`, `/api/quiz/answer`,
  `/api/daily/answer`); el cliente manda `selected`, el server juzga. **Daily (2026-07-11): blindaje
  total** — el `DAILY_BANK` vive en `scalpel/daily_bank.js` (NUNCA se sirve al navegador; página bajó
  4.4→3.0MB); `/api/daily/start` sirve solo textos (pregunta+opciones), `/api/daily/answer` devuelve
  veredicto+`correct_index`+explicación. Ni consola ni view-source revelan la respuesta. **Rotación
  POR USUARIO:** permutación HMAC(SECRET_KEY, user:ciclo) — cada usuario tiene su propio calendario
  de preguntas (no se puede soplar la respuesta a otro), sin repetir dentro de un ciclo de 200 días.
  Si editas `DAILY_BANK` (en su archivo nuevo) o `QUESTION_BANK` (sigue en index.html): corre
  `node tools/extract_quiz_key.js && node tools/validate_daily_bank.js` y commitea AMBOS JSON
  (`quiz_answer_key.json` + `daily_bank_content.json`).
- **Textos legales:** al tocar `terms.html`, `privacy.html` o `legal_i18n.js`, correr
  `python3 tools/audit_legal_translations.py` — compara cláusula por cláusula el inglés contra ES/FR/PT
  (números, plazos, montos y tamaño). Importa porque los T&C ahora dicen que si la ley del comprador
  exige que mande **su** idioma, manda su idioma: un error de traducción en una cláusula de dinero es
  exigible. Auditoría completa hecha 2026-07-26 (141 cláusulas ✅; lectura íntegra del ES de las
  Secciones 2, 7, 11, 12, 14 y 15 — fieles). Único hallazgo: la Secc. 12 EN protegía a
  "TRADER ACCELERATOR" mientras el resto del contrato y las 3 traducciones decían "Tradeable" →
  unificado, y la Secc. 1 ahora define los tres nombres comerciales.
- Commits/pushes siempre a la rama de trabajo de arriba. NO crear PR salvo que el usuario lo pida.
## 📚 Detalle archivado (en `CLAUDE_ARCHIVE.md`, NO se carga solo)
> Tareas terminadas. Si hace falta el detalle de una, pídemelo y lo leo de ahí.
- 🟢 AYUDA CONTEXTUAL — los "(?)" por panel (PILOTO 2026-07-31)
- 🔴 QR de certificados — ELIMINADOS, reemplazados por botones de compartir (2026-07-31)
- 🟢 SOCIALS `/socials` — redes oficiales + próximo sorteo (2026-07-31)
- 🎡 RULETA → COSMÉTICOS + TEMPORADAS (decidido 2026-08-02, EN CONSTRUCCIÓN)
- 📦 LIBRERÍAS VENDORIZADAS — Synapse/Chalkboard sin CDNs (2026-08-10)
- 🐌 SCROLL — el cristal esmerilado costaba 3,6× (2026-08-10)
- 🔬 INVESTIGACIÓN — autopublicación en redes + upgrade de visión (2026-08-23, SIN construir)
- 📱 REDES SOCIALES — kit de marca generado (2026-08-04)
- 💬 CHAT DE TESSERA — sala propia a pantalla completa (2026-08-07)
- 🐛 DOS BUGS CAZADOS POR EL HERMANO (2026-08-22)
- 🕐 LAS FECHAS SE GUARDABAN EN HORA DE BERLÍN (2026-08-13) — leer antes de tocar fechas
- 🚪 REGISTRO — dos fallos que espantaban clientes (2026-08-13)
- 🎁 LA OFERTA DE BIENVENIDA, ENCENDIDA AL 30% (2026-08-13)
- 🚀 EL SITIO ESTÁ ABIERTO AL PÚBLICO (2026-08-13, orden del dueño: "YA SALIMOS")
- 🔑 EL CANDADO DEL LANZAMIENTO ERA `PREVIEW_USERS` (histórico; quitado el 2026-08-13)
- 🔴 La tarifa del cliente de un socio se congelaba en la de LANZAMIENTO (2026-08-13)
- 📅 Recordatorio diario
- 🎯 QUIZ GAPS — metodologías/gatillos SIN quiz (auditado 2026-07-18)
- 🟢 EN CURSO — Auditoría de copy ES + pendientes (rama actual)
- 🟢 Mentorías + Kill Zones (rama actual)
- 🔁 SUSCRIPCIONES — los planes mensuales se cobran SOLOS (cableado 2026-08-04)
- 📧 UN BUZÓN = UNA CUENTA — correo canónico en el registro (2026-08-09)
- 🔴 El cupón se canja al COBRAR, no al ponerlo en el carrito (2026-08-08)
- 🔴 Una suscripción NUNCA APROBADA bloqueaba la baja del cliente (2026-08-08)
- 🧪 Probar una compra REAL sin gastar dinero (2026-08-08)
- 🌐 `SITE_URL` — los enlaces absolutos dejan de depender del Host (2026-08-04)
- 🟣 PayPal — 2º riel de cobro (código LISTO 2026-07-26, falta encender)
- 🟡 Cambio de plan EN VIVO + qué hace de verdad "darse de baja" (2026-08-05)
- 🔴 "UNLOCKED" que salta cuando no toca — reglas fijadas (2026-08-05)
- 🔁 RENOVACIONES — la fecha que se enseña y el corte de la baja (2026-08-05)
- 🛒 CARRITO CON MINIATURAS + RECIBO CON IDENTIDAD (2026-08-05)
- 🔴 NADIE PAGA UN MES QUE YA TIENE PAGADO (2026-08-05)
- ⬇️ BAJAR DE PLAN SE PROGRAMA (2026-08-05, decisión del dueño)
- ⬆️ SUBIR DE PLAN — nunca dos cobros a la vez (2026-08-05)
- 🔴 BAJA → BORRADO: el orden es sagrado (2026-08-10, decisión del dueño)
- 🟢 Stripe — pagos con tarjeta (código LISTO, probado en TEST 2026-07-12)
- 🔴 Bug de PRODUCCIÓN resuelto (2026-08-02) — la app no arrancaba tras el deploy
- 🔴 Bug de PRODUCCIÓN resuelto (2026-07-27) — secuencias de PostgreSQL desincronizadas
- 🗂️ CHALKBOARD — biblioteca de pizarras + tope de diapositivas (2026-08-12)
- 🗑️ CERRAR UNA COMUNIDAD DEL FORO (2026-08-14)

