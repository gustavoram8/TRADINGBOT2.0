# Scalpel — ICT Trade Analysis Platform
## Notas del proyecto para Claude Code

---

> **✅ COMPLETADO (2026-06-06) — LIMPIEZA FINAL DE DISTRACTORES DEL QUIZ**
>
> Hecho: **11 distractores beginner** (commit `8947397`) y **~60 distractores intermediate**
> (commit `7c2a2a8`) reescritos como misconceptions técnicamente plausibles en EN/ES/FR/PT,
> validados con `node --check` (0 ocurrencias de `\\'`), pusheados a `claude/epic-lovelace-GsOuo`.
> Los 3 niveles (beginner/intermediate/advanced) quedan limpios. **SIGUIENTE:** Quiz Hardcore
> con TradingView Lightweight Charts (aún no empezado). El detalle histórico de abajo se conserva
> como referencia del procedimiento.
>
> ---
>
> **🟢 (HISTÓRICO) TAREA — LIMPIEZA FINAL DE DISTRACTORES DEL QUIZ**
>
> **Contexto:** El `QUESTION_BANK` en `scalpel/templates/index.html` tuvo una pasada
> completa para hacer todos los distractores `ok:false` técnicamente plausibles
> (misconceptions reales, no respuestas absurdas/dismissive). El **nivel avanzado quedó
> 100% limpio** (5 commits: `716502a`, `ac1b7fd`, `b50283a`, `95b092e`, `54fcf29`).
> Pero el barrido final reveló **residuos genuinamente malos** que las pasadas previas
> (que apuntaron a listas específicas) dejaron sin tocar:
>
> - **BEGINNER: 11 distractores malos.** Ejemplos exactos a arreglar:
>   - L8158 Order Blocks: "Nothing, OBs are random" · "It guarantees a 100% win"
>   - L8540 Liquidity: "Equal highs mean the market is bullish forever"
>   - L8548 Liquidity: "They are never targets"
>   - L9290 Confluences: "A coin flip" · "Closing the chart"
>   - L9294 Confluences: "Guaranteed wins" · L9302 Confluences: "It guarantees losses"
>   - L9362 Liquidity: "Nowhere" · L9366 Liquidity: "Nothing" · L9460 Candlestick: "Nothing"
>
> - **INTERMEDIATE: 59 distractores malos.** Frases dismissive tipo: "They are identical",
>   "They are unrelated", "Never trade ranges", "AMD cannot nest", "Walls never break",
>   "Liquidity is fictional", "Flip a coin", "Ignore liquidity", "Phases never change",
>   "ICT does not use stops", "No stop needed for FVGs", "Close the platform",
>   "Any candle is an OB", "OBs only form on news", "Volume causes news", "Over-analysis",
>   "PO3 is unrelated to AMD", "Gartley has no D point", etc.
>   (lista completa: correr el script de barrido de abajo para regenerar líneas exactas)
>
> **Cómo retomarlo (procedimiento probado que funcionó para el avanzado):**
> 1. **Regenerar la lista exacta** con un script Python que busca líneas `lv:'beginner'`/
>    `lv:'intermediate'`, ubica el `opts:` en las siguientes ~5 líneas, y extrae las
>    opciones `ok:false` cortas (<24 chars) o con frases dismissive.
> 2. **Principio:** cada distractor `ok:false` debe ser una *misconception técnicamente
>    plausible* (algo que un trader real creería pero está mal), misma longitud que la
>    respuesta `ok:true`, en los **4 idiomas (en/es/fr/pt)**, conservando `ok:false`.
> 3. **⚠️ REGLA DE ESCAPING CRÍTICA:** dentro de un string JS con comilla simple, escapar
>    apóstrofes con UN solo backslash `\'` — NUNCA dos (`\\'` rompe el archivo). Mejor aún:
>    si el valor tiene apóstrofe, usar comillas dobles como delimitador (`fr:"l'OB..."`).
> 4. **Validar SIEMPRE** tras editar: extraer el `<script>` que contiene `QUESTION_BANK`
>    y correr `node --check`. Verificar que `\\'` aparezca 0 veces.
> 5. **Commit por nivel** (beginner, luego intermediate) y push a `claude/epic-lovelace-GsOuo`.
>    Recordar al usuario el `git pull` + `supervisorctl restart traderacelerator` en el VPS.
> 6. Se pueden usar agentes Opus en **secuencia** (no paralelo — editan el mismo archivo y
>    colisionan), uno por metodología, dándoles los strings exactos a reemplazar.
>
> **DESPUÉS de esto:** sigue pendiente el **Quiz Hardcore con gráficos de TradingView**
> (Lightweight Charts) — preguntas basadas en gráficos reales. Aún no empezado.

---

> **INSTRUCCIÓN PERMANENTE — RECORDATORIO DIARIO:**
> La fecha de hoy está disponible en el contexto del sistema (`currentDate`).
> Muestra la sección "📋 TAREAS PENDIENTES" completa **la primera vez que el usuario
> te escriba en cada día calendario** (lunes, martes, miércoles, etc.).
> Si ya la mostraste hoy (misma fecha en `currentDate`), NO la repitas en mensajes
> posteriores del mismo día. Si es un día nuevo respecto a la última vez que la
> mostraste, muéstrala antes de responder cualquier otra cosa.
> Esto es obligatorio sin excepción.

---

> **🚨🚨🚨 ALERTA URGENTE #2 — RECORDATORIO DIARIO (A PARTIR DEL 2026-06-06) 🚨🚨🚨**
>
> Mostrar este bloque la primera vez que el usuario escriba cada día, JUNTO con la alerta #1.
>
> ╔══════════════════════════════════════════════════════════════════╗
> ║  🔧  DOS TAREAS TÉCNICAS CRÍTICAS PENDIENTES — MAÑANA           ║
> ║                                                                  ║
> ║  1. 🗄️  MIGRACIÓN PostgreSQL (escalar a 500+ usuarios)          ║
> ║     → SQLite actual NO soporta escrituras simultáneas           ║
> ║     → Con 50+ usuarios simultáneos empieza a fallar             ║
> ║     → Migrar a PostgreSQL + Gunicorn en el VPS (costo: $0)      ║
> ║     → Tiempo estimado: ~1-2 horas                               ║
> ║     → Sin esto: el website se puede caer con crecimiento        ║
> ║                                                                  ║
> ║  2. 🩺  SISTEMA DE MONITOREO / HEALTH CHECK con IA              ║
> ║     → UptimeRobot: alerta si el sitio cae (gratis, 5 min)      ║
> ║     → Sentry: captura bugs automáticamente (gratis, 3 líneas)   ║
> ║     → Health endpoint propio: métricas de usuarios, DB, carga   ║
> ║     → Te avisa ANTES de que el sitio se rompa                   ║
> ║     → Tiempo estimado: ~30 min                                  ║
> ║                                                                  ║
> ║  RECOMENDACIÓN: hacer #2 primero (30 min), luego #1 (delicado)  ║
> ║  Así si algo sale mal en la migración, ya tienes alertas activas ║
> ╚══════════════════════════════════════════════════════════════════╝

---

> **🚨🚨🚨 ALERTA URGENTE #1 — RECORDATORIO TRIPLE DIARIO (A PARTIR DEL 2026-06-06) 🚨🚨🚨**
>
> A partir del **viernes 5 de junio de 2026**, y **CADA DÍA** hasta que el usuario
> confirme que completó estas tareas, debes mostrar el siguiente bloque
> **EXACTAMENTE 3 VECES por sesión**: al inicio, a la mitad de la conversación
> (aproximadamente cada 5 mensajes del usuario), y justo antes de cada push/deploy.
>
> ╔══════════════════════════════════════════════════════════════════╗
> ║  ⚠️  TAREAS CRÍTICAS PENDIENTES — NO OLVIDAR HOY  ⚠️             ║
> ║                                                                  ║
> ║  1. 🌐 COMPRAR EL DOMINIO en Cloudflare Registrar               ║
> ║     → cloudflare.com/registrar → "Register Domains"             ║
> ║     → Objetivo: traderacelerator.com (~$10.46 USD/año)          ║
> ║     → Usar el correo empresarial nuevo (NO el personal)         ║
> ║                                                                  ║
> ║  2. 📧 CREAR EL CORREO EMPRESARIAL (antes de comprar dominio)   ║
> ║     → Crear Gmail: traderacelerator.hq@gmail.com                ║
> ║     → Crear Gmail: support.traderacelerator@gmail.com           ║
> ║     → Activar verificación en 2 pasos en ambos                  ║
> ║     → Compartir contraseñas con el socio (Bitwarden/1Password)  ║
> ║                                                                  ║
> ║  3. 🔗 LINKEAR EL DOMINIO AL VPS (después de comprarlo)         ║
> ║     → En Cloudflare DNS: A record → 62.171.180.22              ║
> ║     → Configurar nginx + SSL (Let's Encrypt) en el VPS          ║
> ║     → Actualizar MAIL_USERNAME en supervisor al nuevo correo    ║
> ║     → Objetivo final: https://traderacelerator.com              ║
> ║                                                                  ║
> ║  SIN ESTO: el sitio sigue en IP cruda, sin HTTPS, sin email     ║
> ║  empresarial, y los T&C dicen support@traderacelerator.com      ║
> ║  que aún no existe. ¡HAZLO HOY!                                 ║
> ╚══════════════════════════════════════════════════════════════════╝
>
> Esta alerta se desactiva cuando el usuario confirme explícitamente
> que completó las 3 tareas. Hasta entonces: mostrarla 3 veces por sesión,
> SIN EXCEPCIÓN, aunque el usuario esté hablando de otro tema.

---

> **INSTRUCCIÓN PERMANENTE — DEPLOY EN VPS:**
> El sitio Trader Acelerator está desplegado en el VPS de Contabo (IP: `62.171.180.22`,
> puerto `5001`) gestionado por **supervisor**.
>
> **REGLA OBLIGATORIA:** Después de CADA push de cambios al repo, recordar siempre
> al usuario que debe ejecutar en el VPS:
> ```
> supervisorctl restart traderacelerator
> ```
> Sin este comando, los cambios pusheados NO se reflejan en el sitio en vivo.
> El flujo completo para aplicar cambios en producción es:
> 1. `git pull origin claude/epic-lovelace-GsOuo` (en el VPS)
> 2. `supervisorctl restart traderacelerator`
>
> El VPS corre Ubuntu con supervisor — el proceso arranca automáticamente al reiniciar
> el servidor, sin necesidad de intervención manual.

---

## Stack técnico

- **Backend:** Flask + SQLAlchemy + SQLite (`scalpel.db`)
- **Auth:** Flask-Login (planes: free / standard / premium)
- **AI:** OpenAI SDK apuntando a GitHub Models (Azure inference endpoint) con `GITHUB_TOKEN`
  - GPT-4o Vision → análisis de screenshots
  - GPT-4o → moderación del foro + asesor del Scout
- **Frontend:** Jinja2 + vanilla JS, i18n EN/ES/FR/PT
- **Rama de desarrollo activa:** `claude/epic-lovelace-GsOuo` en `gustavoram8/TRADINGBOT2.0`
  - Rama anterior (archivada): `claude/wonderful-gates-JAa9X`
- **App:** `scalpel/app.py` · arrancar con `FLASK_DEBUG=1 python3 scalpel/app.py`
- **Acceso local desde iPhone:** `http://192.168.0.104:5001` (Mac en WiFi TP-Link, misma red)

---

## Límites de plan

| Plan     | Screenshots | Ventana |
|----------|-------------|---------|
| Free     | 1           | 7 días  |
| Standard | 1           | 24 h    |
| Premium  | 5           | 24 h    |

---

## 📋 TAREAS PENDIENTES

> Mostrar esta lista **una vez por día calendario**, la primera vez que el usuario escriba ese día.

### 🔴 Crítico — antes del lanzamiento

- [ ] **Pagos — plan de monetización decidido:**
      - **Fase 1 (ahora):** cobrar en USDT via Binance manualmente mientras se valida que la gente paga.
      - **Fase 2 (con 10–20 clientes pagando):** constituir LLC en EE.UU. (Wyoming/Delaware via Stripe Atlas,
        Firstbase.io o Northwest Registered Agent, ~$300–500 USD) y migrar a Stripe para automatizar
        activación/desactivación de planes. Alternativa más rápida: empresa en Colombia, México o Panamá.
      - **Opción puente:** ofrecer ambas opciones al usuario (Stripe + Binance USDT) para no perder clientes.

- [ ] **Pagar OpenAI API** — necesario para análisis de screenshots en producción y
      para el asesor IA del Prop Firm Scout. Sin esto el sitio funciona pero con
      el token gratuito de GitHub Models (limitado).
- [ ] **Configurar Stripe** — pagos de suscripción (Free → Standard → Premium).
      Sin esto no hay monetización.
- [x] **Desplegar en VPS** — sitio corriendo en Contabo VPS (`62.171.180.22:5001`)
      con supervisor (autostart + autorestart). Falta dominio propio (ver tarea abajo).
- [ ] **Comprar dominio en Cloudflare Registrar** — costo ~$10.46 USD/año para `.com`.
      URL: cloudflare.com/registrar → "Domain Registration" → "Register Domains".
      Dominio objetivo: `traderacelerator.com` (verificar disponibilidad al momento de comprar).
      Una vez comprado: apuntar DNS a IP del VPS `62.171.180.22` y configurar nginx + SSL
      (HTTPS gratis via Let's Encrypt) para que el sitio corra en `https://traderacelerator.com`
      en vez de `http://62.171.180.22:5001`.
- [ ] **Migrar email de envío a cuenta dedicada** — actualmente los emails de verificación
      OTP y recuperación de contraseña salen desde el Gmail personal `mauroramirezmij@gmail.com`.
      Pasos una vez comprado el dominio:
      1. Crear Gmail dedicado (ej. `noreply.traderacelerator@gmail.com` o configurar
         `hola@traderacelerator.com` con Google Workspace ~$6/mes).
      2. Activar 2FA en esa cuenta → generar nuevo App Password.
      3. En el VPS actualizar `/etc/supervisor/conf.d/traderacelerator.conf`:
         cambiar `MAIL_USERNAME` a la nueva dirección y `MAIL_APP_PASSWORD` a la nueva clave.
      4. `supervisorctl reread && supervisorctl restart traderacelerator`
- [ ] **Páginas legales** — redactar Términos y Condiciones + Política de
      Privacidad. Actualmente el footer solo tiene un disclaimer básico.
- [ ] **Revisión legal con Claude** — una vez terminado el sitio y redactados
      los T&C, hacer una prueba legal completa junto a Claude para identificar
      posibles problemas antes del lanzamiento público.
- [ ] **Persistencia server-side de Scalpe® boards** — actualmente los boards/slides
      se guardan en `localStorage` del navegador (por dispositivo). Si el usuario
      migra de dispositivo, limpia el caché o se despliega en VPS, los pierde.
      Implementar guardado en DB ligado a `user_id` (modelo `ScalperBoard`,
      endpoint `/api/scalper/save` y `/api/scalper/load`) antes del lanzamiento.
- [ ] **Acceso desde iPhone sin servidor local** — actualmente el servidor solo
      corre en el Mac. Para probar desde iPhone de forma permanente, desplegar
      en VPS es la solución real (ver tarea de VPS arriba).

### 🟡 Importante — mejoras post-lanzamiento

- [x] **Conectar el envío de emails (Gmail SMTP)** — `MAIL_APP_PASSWORD` configurado
      en el VPS (supervisor). Emails de verificación OTP y recuperación de contraseña
      funcionando. Pendiente: migrar a cuenta de email dedicada (ver tarea 🔴 arriba).
- [ ] **APScheduler + OpenAI Web Search para Scout** — agente que actualice
      automáticamente los datos de las 25 prop firms semanalmente (precios,
      países permitidos, promociones). Requiere OpenAI pagado.
- [ ] **Verificar prop firms que aceptan Venezuela** — actualmente solo OneUp
      Trader está marcada como Venezuela-friendly. Confirmar si alguna otra
      (posiblemente del Reino Unido) también acepta traders venezolanos.
- [ ] **Ratings del Scout con fuente verificable** — los ratings actuales
      (ej. Apex 4.6) son estimaciones. Antes del lanzamiento público, vincularlos
      a una fuente real (Trustpilot, reseñas propias, etc.) para poder respaldarlos.

### 🟢 Completado ✅

- [x] Análisis de screenshots con GPT-4o Vision
- [x] Foro de Trading con moderación IA (glosario de jerga ICT)
- [x] Prop Firm Scout — marketplace de 25 firmas con filtros y asesor IA
- [x] Límite de 5 análisis/día para plan Premium
- [x] Blocklist OFAC completa (21 países) en el Scout
- [x] Logos reales de prop firms (Google favicon + fallback monograma)
- [x] Página de precios actualizada con todos los beneficios Premium
- [x] Disclaimer legal en el apartado Scout
- [x] PDFs: desglose de costos + checklist pre-lanzamiento
- [x] i18n en 4 idiomas: EN / ES / FR / PT
- [x] Tema claro / oscuro
- [x] **Synapse — cabeza wireframe con glow suavizado** (opacidades: wireMat dark 0.25, glowMat dark 0.04)
- [x] **Synapse — reducción de lag** (~50% mejora: eliminado backdrop-filter blur, powerPreference high-performance, pixelRatio 1.5, loop pause al cambiar tab)
- [x] **Synapse — constelaciones neuronales** visibles en light mode (color azul profundo `0x2f5fa6`), exclusión de zona del torso/cabeza con perfil gaussiano `figureHalf(y)`, spread ampliado a ±21 unidades
- [x] **Synapse — figuras ghost (ghost glyphs)** — 14 mini-dibujos institucionales que se "dibujan solos" en las esquinas con animación de reveal progresivo (`setDrawRange`)
- [x] **Synapse — NET_N reducido 25%** (144 → 108 nodos) — commit `bda4070`
- [x] **Synapse — velocidad de constelaciones ×2** (netVel 0.006 → 0.012) — commit `bda4070`
- [x] **Synapse — figuras renovadas** — eliminadas: clocktower, vault, rocket · agregadas: fed, bull, ticker, usaflag, bullish, bearish · total: 14 figuras — commit `973a83b`
- [x] **Synapse — fix loading infinito** — `AbortController` 15s en fetch de modelos GLB, timeout 12s en `ensureThree()` — commit `705cbe4`
- [x] **Badge certificado "QC" con fuego animado** — canvas particle fire (`QCFire` IIFE) con blending aditivo (`lighter`), partículas con ciclo de vida blanco→amarillo→naranja→rojo, sin círculo amarillo de fondo, estrella negra en light mode / blanca en dark mode
- [x] **Products dropdown en la nav** — botón con caret, menú flotante (fixed, escapa overflow de tabs) con secciones: Plans (Free/Standard/Premium), Indicators, Camos, Terms, Settings. JS con `getBoundingClientRect()` para posicionamiento.
- [x] **Íconos de plan animados (cadencia 8s)** — Standard: estrella fugaz (`piShootingStar`), Premium: corona vibrando (`piCrownVibrate`), Free: check estático. Animación burst + pausa larga de ~7s.
- [x] **Ícono de Camos** — 4 barras diagonales paralelas (SVG), reemplaza ícono genérico.
- [x] **Rutas nuevas en `app.py`** — `/store/indicators`, `/camos`, `/terms`, `/settings` con sus templates correspondientes.
- [x] **Plantillas nuevas creadas** — `store_indicators.html`, `camos.html` (3 camos placeholder: Navy Trader, Desert Ops, Forest Recon), `terms.html`, `settings.html` (Account/Preferences/Notifications/Danger Zone).
- [x] **Fix logo en pricing.html** — bug de capa gris por `mix-blend-mode` en fondo blanco. Solución: `multiply` en light, `invert(1) + screen` en dark. Pricing ahora respeta el tema claro/oscuro del `localStorage`.
- [x] **Pantalla de carga de Synapse rediseñada** — pantalla opaca full-page con foto de fondo (`synapse_bg.jpg`), overlay oscuro radial, overlay de candlesticks animado (`synapse_candles.png`), barra de progreso two-phase.
- [x] **Two-phase Synapse loader** — Fase 1: shimmer CSS indeterminado (corre en compositor, inmune al bloqueo del main thread durante `buildScene()`). Fase 2: conteo rAF 0→100% una vez el main thread queda libre. Soluciona el freeze del contador.
- [x] **`synapse_bg.jpg` procesada con Pillow** — volteada horizontalmente, logo "CLAUDE" en el bisel del laptop eliminado copiando parche limpio del bisel adyacente (x:232–326, y:535–560 → x:326–420).
- [x] **`synapse_candles.png` creada con Pillow** — extracción de píxeles verdes (G>90, G-R>35, G-B>35, x<520) a PNG RGBA transparente. Animada con `@keyframes synCandleStorm` (drop-shadow verde, brightness/saturate altos, 3 destellos por ciclo de 2.6s).
- [x] **Quiz — opción D eliminada** — removida la opción "I'm just exploring" del menú de bienvenida del quiz.
- [x] **Registro obligatorio + verificación por email (OTP)** — eliminado el acceso de invitado (`/start-free` ahora redirige a `/register`, sin cookie anónima). Todo usuario debe crear cuenta con email + contraseña y verificar un código de 6 dígitos antes de entrar. Columnas nuevas en `User`: `email_verified`, `verification_code`, `verification_expires` (migración automática SQLite en `_migrate_user_verification_columns()` que marca verificados los usuarios previos). Falta solo conectar credenciales de email (ver tareas 🟡).
- [x] **"Recordar este dispositivo"** — checkbox en login/register. Si se activa: `login_user(remember=True)` con `REMEMBER_COOKIE_DURATION = 3650 días` (indefinido) → próximas visitas saltan landing + login. Si no: cookie de sesión (se borra al cerrar el navegador) → siempre se muestra landing + login.
- [x] **Nuevo flujo de entrada en 4 pasos** — Landing (`/`) → Login/Register → Welcome splash (`/welcome`, logo + candle orbitando) → App (`/app`). La `splash.html` (antes en `/`) ahora es la SEGUNDA pantalla post-login y redirige a `/app` en vez de `/login`.
- [x] **Fix texto "Scalpel" → "Trader Acelerator"** en login/register — estaba en `static/auth.js` (i18n EN/ES/FR/PT), no en las plantillas.
- [x] **Landing placeholder** (`landing.html`) — primera pantalla al entrar; pendiente diseño final en un paso posterior.

---

## 🔵 Stand-by — Ideas descartadas temporalmente

### Trade of the Day
Feature complejo descartado hasta que el negocio genere ingresos estables.
La idea: tras cada sesión (NY AM / NY PM / Lunch / London / Asia), el sistema detecta
automáticamente los mejores setups válidos por instrumento y metodología (ICT primero,
luego Patterns, Quant, STDV, etc.), los muestra al admin para que elija con un clic
(Fase 2), y eventualmente la IA aprende de esas elecciones y escoge sola (Fase 3).

**Por qué está en stand-by:** alto costo de desarrollo (~6 semanas intensivas) con
retorno incierto comparado con features de mayor impacto en conversión y retención.

**Costos estimados de implementación:**
- Polygon.io (datos históricos + tiempo real, Forex + Futuros CME): ~$29/mes
- Servidor adicional para correr el detector de setups y el modelo de ML: ~$20–40/mes
  (puede compartirse con el VPS principal si tiene suficiente RAM)
- Tiempo de desarrollo: ~6 semanas a 5h/día (Fase 2 completa con backtesting + display animado)
- OpenAI API opcional para validación de setups con visión: ~$10–30/mes según volumen
- **Total mensual en producción: ~$50–100/mes sobre los costos base del sitio**

**Stack técnico decidido:**
- Datos: Polygon.io ($29/mes)
- Display animado: TradingView Lightweight Charts (open-source, MIT, gratis)
- Detección: Python + scikit-learn para el modelo de scoring
- Instrumentos: EURUSD, GBPUSD, XAUUSD, ES (E-mini S&P 500)
- Timeframes: macro 4H/1H · estructura 1H/30m/15m/5m · entrada 5m/3m/2m/1m
- Metodología inicial: ICT (FVG, sweep, OB, MSS, displacement, AMD, BPR)
- Aprendizaje: RLHF-style — admin etiqueta sesiones históricas → modelo aprende criterio

---

## 🟣 Features construidos pero DESACTIVADOS (listos para reactivar)

> **RECORDATORIO PERMANENTE — PROP FIRM SCOUT:**
> El **Prop Firm Scout está completamente construido** (marketplace de 25 firmas,
> filtros, asesor IA, blocklist OFAC, logos reales) pero **desactivado temporalmente**
> mediante un feature flag. Saldrá al público mucho más adelante.
>
> **Cómo está apagado:** la variable `SCOUT_ENABLED` en `scalpel/app.py`
> (sección *Feature flags*, cerca del cliente de IA). Por defecto está en `False`.
> Con el flag apagado:
> - La pestaña "Prop Firm Scout" del menú (`index.html`) se oculta.
> - La vista `#scout-view` no se renderiza.
> - Las APIs `/api/scout/firms` y `/api/scout/chat` devuelven 404.
> - La mención del Scout en `pricing.html` (plan Premium) se oculta.
> - El flag se expone a todas las plantillas vía `@app.context_processor`
>   (`inject_feature_flags` → `scout_enabled`).
>
> **Cómo reactivarlo cuando el usuario lo pida:** cambiar a `SCOUT_ENABLED = True`
> en `scalpel/app.py` (o arrancar con `SCOUT_ENABLED=1 python3 scalpel/app.py`)
> y reiniciar el servidor. Todo el código del Scout (la pestaña, la vista, las APIs,
> el modelo `PropFirm`, el seed `init_scout_data()` y los datos en la DB) permanece
> **intacto** — no hay que reconstruir nada.
>
> ⚠️ El usuario reactivará el Scout **solo cuando lo solicite explícitamente.**

---

## 🔐 Flujo de autenticación — Arquitectura (sesión 2026-06-02)

### Flujo de 4 pantallas
```
/  (landing.html, placeholder)
   └─ si ya autenticado + verificado → salta a /welcome
/login  ó  /register   (+ checkbox "Remember this device")
   └─ register/login de cuenta no verificada → /verify-email (código OTP 6 díg.)
/welcome  (splash.html — logo + candle orbitando; SEGUNDA pantalla de carga)
   └─ redirige a /app
/app  (index.html — analyzer + herramientas; @login_required + email_verified)
```

### Rutas clave en `app.py`
| Ruta | Función | Notas |
|------|---------|-------|
| `/` | `landing()` | Primera pantalla. Si `is_authenticated && email_verified` → `/welcome` |
| `/welcome` | `welcome()` | `@login_required`. Splash post-login (setea cookie `scalpel_splash_ts` 60s) |
| `/app` | `app_view()` | `@login_required` + chequeo `email_verified`; sin splash-pass → `/welcome` |
| `/login` | `login()` | checkbox `remember`; no verificado → manda a `/verify-email` |
| `/register` | `register()` | crea user `email_verified=False`, genera código, → `/verify-email` |
| `/verify-email` | `verify_email()` | valida código (15 min exp.), activa cuenta, `login_user` |
| `/resend-code` | `resend_code()` | regenera y reenvía el código |
| `/start-free` | `start_free()` | **retirado** — redirige a `/register` (ya no hay invitados) |

### Detalles
- **Remember device:** `login_user(remember=bool)`; `REMEMBER_COOKIE_DURATION = 3650 días`.
  Pendientes de verificación se guardan en `session['pending_user_id']` y `session['pending_remember']`.
- **Columnas nuevas en `User`:** `email_verified` (Bool), `verification_code` (str 6), `verification_expires` (DateTime).
- **Migración SQLite:** `_migrate_user_verification_columns()` corre en `init_db()` — `ALTER TABLE` para columnas faltantes y marca `email_verified=1` a todos los usuarios previos (no se quedan bloqueados). El admin sembrado nace `email_verified=True`.
- **Código OTP:** `_new_verification_code()` → 6 dígitos. Email vía `send_verification_email()` (mismo SMTP que el reset). Sin `MAIL_APP_PASSWORD` el código se loguea como WARNING para pruebas locales.
- **Textos i18n** de login/register/verify viven en `scalpel/static/auth.js` (EN/ES/FR/PT), NO en las plantillas. `ve.sub` interpola `{email}` vía `data-email`.

---

## Notas de arquitectura importantes

- `init_scout_data()` corre en cada startup y refresca `blocked_countries`
  en todas las firmas — actúa como migración automática.
- `OFAC_DEFAULT_BLOCKLIST` en `app.py` define los 21 países bloqueados.
- `VENEZUELA_ALLOWED_SLUGS = {'oneup-trader'}` — única excepción documentada.
- El seed solo inserta firmas nuevas; no duplica si ya existen.
- Commits y pushes siempre a rama `claude/epic-lovelace-GsOuo`.

---

## 🎨 Synapse — Estado técnico actual (2026-06-02)

### Parámetros clave en `scalpel/templates/index.html`

```js
// Constelaciones neuronales
NET_N = 108           // nodos (144 → 108, -25%)
netVel *= 0.012       // velocidad (era 0.006, ahora ×2)
THRESH = 3.4          // distancia máxima para conectar nodos

// Zona de exclusión del cuerpo (perfil gaussiano)
FIG_Y0 = 3.0, FIG_Y1 = 16.8, CAM_Z = 16.5
figureHalf(y) = Math.max(3.4, 5.3 * exp(-((y-5.7)/2.4)²))  // cubre torso+cabeza

// Colores
colDim()    → dark: 0x9c8240  · light: 0x7aaed4
colBright() → dark: 0xc6a04e  · light: 0x5592c8
netCol()    → dark: 0x9c8240  · light: 0x2f5fa6  // azul profundo en light mode

// Modelos 3D
MODEL_VER = '11'   // brain.glb decimado 25k→6.7k caras (118 KB)
                   // head.glb Lee Perry-Smith, 15,076 caras
HEAD_Y = 5.7, BRAIN_Y = 13.8

// Wireframe opacidades (holoLineMats)
wireMat: dark 0.25 / light 0.46
glowMat: dark 0.04 / light 0.07

// Ghost glyphs timing
FIG_START=2.0, FIG_FORM=1.1, FIG_HOLD=1.7, FIG_DISS=0.7, FIG_WAIT=7.0
FIG_PERIOD = 10.5s por ciclo · 6 SLOTS · FIG_CAP=128 vértices por slot
```

### Pool de figuras ghost (14 total)

| # | Nombre | Descripción |
|---|--------|-------------|
| 1 | capitol | Capitolio con cúpula, 6 columnas, finial |
| 2 | temple | Templo clásico con 5 columnas, doble frontón |
| 3 | fed | Fachada Federal Reserve, 8 columnas, pedimento, puerta |
| 4 | skyline | Skyline urbano con 5 edificios variados |
| 5 | monument | Obelisco con escalones de base |
| 6 | bull | Toro de Wall Street (silueta de cuerpo completo) |
| 7 | scales | Balanza de la justicia |
| 8 | globe | Globo terráqueo con meridianos/ecuador |
| 9 | ticker | Cinta de ticker + candlesticks encima |
| 10 | usaflag | Bandera USA con franjas, cantón de estrellas, asta |
| 11 | bullish | Pantalla NYSE — tendencia alcista + flecha arriba |
| 12 | bearish | Pantalla NYSE — tendencia bajista + flecha abajo |
| 13 | chart | Gráfico de línea con ejes y flecha |
| 14 | bars | Gráfico de barras con 4 barras y baseline |

### Commits recientes (sesión 2026-05-31)

| Commit | Descripción |
|--------|-------------|
| `bda4070` | NET_N 144→108 y velocidad ×2 |
| `973a83b` | Figuras renovadas: quita clocktower/vault/rocket, agrega fed/bull/ticker/usaflag/bullish/bearish |
| `705cbe4` | Fix loading infinito: AbortController 15s + timeout ensureThree 12s |

### Commits recientes (sesión 2026-06-02)

| Commit | Descripción |
|--------|-------------|
| `b101f13` | Synapse loading screen: synapse_bg.jpg procesada, synapse_candles.png, two-phase loader, fix freeze contador |

---

## 🎨 Pantalla de carga de Synapse — Arquitectura

### Archivos estáticos
- **`scalpel/static/synapse_bg.jpg`** — ilustración de trading, volteada horizontalmente, logo "CLAUDE" del laptop eliminado con Pillow (patch copy x:232–420, y:535–560).
- **`scalpel/static/synapse_candles.png`** — overlay RGBA con solo los píxeles verdes extraídos de la ilustración original. Se anima por separado sobre el fondo.

### HTML de la pantalla de carga (en `index.html`, dentro de `#synapse-view`)
```html
<div class="syn-loading" id="syn-loading">
  <div class="syn-load-bg">
    <img class="syn-load-photo"  src="/static/synapse_bg.jpg" alt="" draggable="false" />
    <div class="syn-load-dark"></div>
    <img class="syn-load-candles" src="/static/synapse_candles.png" alt="" draggable="false" />
  </div>
  <div class="syn-load-inner">
    <div class="syn-load-title" data-i18n="synapse.loading">Initializing neural matrix…</div>
    <div class="syn-progress"><div class="syn-progress-fill" id="syn-progress-fill"></div></div>
    <div class="syn-progress-pct" id="syn-progress-pct">0%</div>
  </div>
</div>
```

### CSS clave
```css
.syn-load-candles { mix-blend-mode:screen; animation:synCandleStorm 2.6s ease-in-out infinite; }
@keyframes synCandleStorm {
  0%  { opacity:.95; filter:drop-shadow(0 0 6px #3dff7a) drop-shadow(0 0 12px #16ff5e) saturate(1.5) brightness(1.5); }
  6%  { opacity:1;   filter:drop-shadow(0 0 22px #c4ffd4) drop-shadow(0 0 40px #3dff80) saturate(1.8) brightness(3.0); }
  46% { opacity:1;   filter:drop-shadow(0 0 26px #d4ffe0) drop-shadow(0 0 46px #44ff88) saturate(1.9) brightness(3.3); }
  72% { opacity:1;   filter:drop-shadow(0 0 20px #b8ffcc) drop-shadow(0 0 38px #3dff80) saturate(1.8) brightness(2.8); }
  100%{ opacity:.95; filter:drop-shadow(0 0 7px #3dff7a) drop-shadow(0 0 13px #16ff5e) saturate(1.5) brightness(1.6); } }
/* Fase 1: shimmer indeterminado (compositor, inmune al main thread) */
.syn-progress.indeterminate .syn-progress-fill {
  width:40%; transition:none; animation:synIndet 1.15s ease-in-out infinite; }
@keyframes synIndet { 0%{transform:translateX(-115%);} 100%{transform:translateX(265%);} }
```

### Two-phase loader JS (lógica clave en `SynapseModule.open()`)
```javascript
// Fase 1: shimmer mientras buildScene() bloquea main thread
progress.classList.add('indeterminate');
pctEl.textContent = '';
await buildScene();   // bloquea JS, compositor sigue corriendo el shimmer
// Fase 2: main thread libre → conteo suave rAF 0→100%
progress.classList.remove('indeterminate');
await new Promise(resolve => {
  const step = () => {
    const t = Math.min(1, (Date.now()-countStart)/countDur);
    fill.style.width = Math.round(t*100)+'%';
    pctEl.textContent = Math.round(t*100)+'%';
    if (t<1) requestAnimationFrame(step); else resolve();
  };
  requestAnimationFrame(step);
});
```

---

## 🏷️ Badge certificado QCFire — Arquitectura

### HTML (en la pestaña de análisis, `index.html`)
```html
<span class="qc-badge">
  <canvas class="qc-fire-canvas" id="qc-fire-canvas" width="56" height="70" aria-hidden="true"></canvas>
  <span class="qc-star">★</span>
</span>
```

### CSS clave
```css
.qc-star { position:relative; z-index:3; font-size:22px; color:#fff; text-shadow:0 0 8px rgba(255,200,80,0.6); }
body.light .qc-star { color:#111; text-shadow:0 0 8px rgba(255,200,80,0.45); }
```

### JS — IIFE `QCFire`
- Canvas 2D con `globalCompositeOperation = 'lighter'` (blending aditivo).
- Partículas spawneadas en anillo alrededor de la estrella (radio ~18–28% del canvas).
- Ciclo de vida: blanco/amarillo (life<0.3) → naranja (life<0.6) → rojo→transparente.
- `start()` inicializa canvas con DPR scaling y lanza el loop `requestAnimationFrame`.

---

## 🧭 Products Dropdown — Arquitectura

### Posición en el DOM (`index.html`)
- Botón `#products-tab` con clase `tab tab-products` — **no participa en `switchTab()`** (excluido con `if (t.id === 'products-tab') return;`).
- Menú `#products-menu` con `position:fixed` — escapa el overflow de la barra de tabs.

### Rutas del menú
| Item | Ruta | Notas |
|------|------|-------|
| Free / Standard / Premium | `/pricing` | Los 3 redirigen a pricing |
| Indicators | `/store/indicators` | Storefront separado del tab in-app |
| Camos | `/camos` | Página de "skins" del sitio |
| Terms | `/terms` | T&C placeholder |
| Settings | `/settings` | Cuenta, preferencias, notificaciones |

### Íconos animados de plan (cadencia 8s)
- **Free:** check SVG estático.
- **Standard:** estrella SVG con `@keyframes piShootingStar` — entra desde abajo-izquierda diagonal, escala, luego reposa 7s.
- **Premium:** corona SVG dorada con `@keyframes piCrownVibrate` — vibra ~1s, reposa ~7s.
- **Camos:** 4 barras diagonales SVG (sin animación).

### Posicionamiento JS
```javascript
const rect = btn.getBoundingClientRect();
menu.style.top  = (rect.bottom + 6) + 'px';
menu.style.left = rect.left + 'px';
```
Cierre: clic fuera del menú, clic en cualquier item, o segundo clic en el botón.
