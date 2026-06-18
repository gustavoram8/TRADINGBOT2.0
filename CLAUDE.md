# Scalpel — ICT Trade Analysis Platform
## Notas del proyecto para Claude Code

---

> **🟢 EN CURSO (2026-06-17) — MARKET TIMING: KILL ZONES "TERMINAL" + CALENDARIO ECONÓMICO**
> **(PENDIENTE: que el usuario revise visualmente en el VPS y confirme si le gusta el estilo A)**
>
> **Rama de trabajo de esta línea:** `claude/intelligent-turing-94qh5i` (NO la `epic-lovelace`).
> Commits previos: `6386884` (1ª versión), `52a4c5a` (dos carriles + filtro alto/medio impacto).
>
> **✅ REDISEÑO APLICADO (sesión 2026-06-17, decisiones del usuario tomadas):**
> 1. **Estilo Kill Zones = A) "Terminal de trading"** (el usuario eligió A; si no le gusta probar C
>    "gauge/velocímetro"). Implementado como panel `.kzt` "KILL ZONE TERMINAL": barra de título con
>    semáforo + cursor parpadeante + LED "LIVE · ET", relojes NY (Orbitron, oro) y Local (con tz
>    real), banner de sesión activa, timeline de 2 carriles restyleado (bloques con gradiente+glow),
>    y **filas de lectura tipo terminal** (`.kz-row`) con LED, ventana, **barra de progreso** de la
>    sesión y stat (● restante / → próxima). Paleta on-brand grafito+oro (`--kzt-gold #f5b942`).
> 2. **✅ HORA EXACTA EN VIVO en el marcador NOW** — `#kz-now-flag` ahora muestra `HH:MM:SS` (NY)
>    pegado a la línea amarilla, actualizado cada segundo. Requisito cumplido.
> 3. **Calendario = Opción A (decisión del usuario por riesgo legal):** se DEJA el widget de
>    TradingView (no construir uno propio — sería MÁS riesgoso porque nos volvería el "publicador"
>    de las horas). Se añadió **disclaimer educativo in-page** (`ec.disclaimer`, 4 idiomas) dejando
>    claro que la data es de TradingView (un tercero), puede estar mal/retrasada/caída, y que
>    **Trader Acelerator NO se responsabiliza** de errores/caídas de terceros. Además se agregó una
>    **cláusula nueva en los T&C** (`terms.html`, Sección 11 "Disclaimers"): "Third-party data,
>    embedded content, and economic calendar" cubriendo TradingView/datos embebidos.
> 4. **✅ Navegación:** mini-nav **sticky** `Analyzer · Kill Zones · Calendar` (`#mt-nav`, con
>    scroll-spy vía IntersectionObserver + scroll suave) + **chevron animado** "↓ Market Timing"
>    (`.mt-chevron`) al final del analizador + divisores con peso (`.mt-divider`).
>
> **DÓNDE VIVE (todo en `scalpel/templates/index.html`):**
> - HTML: chevron + `<div id="market-timing">` (con `#mt-nav`, `<section id="kill-zones" class="kzt">`,
>   `<section id="economic-calendar" class="ec-section">`) justo antes de `</div><!-- /analyze-container -->`.
> - CSS: bloque "MARKET TIMING — KILL ZONE TERMINAL" (vars `--kzt-*`, `.kzt`, `.kz-row`, `.mt-nav`,
>   `.mt-chevron`, etc.) antes de `/* ── CARD ── */`.
> - JS: IIFE "MARKET TIMING — Kill Zones live clock…" antes de `window.__TA_INIT_OK = true;`
>   (incluye el scroll-spy del mini-nav al final).
> - i18n: `MT_I18N` (en/es/fr/pt) — claves nuevas: `mt.discover`, `mt.nav.*`, `kz.online`, `ec.disclaimer`.
> - Kill Zones (hora NY/ET, DST vía Intl): Asia 20–00, London 02–05, NY AM 07–10, Lunch 12–13,
>   NY PM 13:30–16, Silver Bullets SB1 03–04 / SB2 10–11 / SB3 14–15.
> - Verificado: `node --check` OK, Jinja compila, y render real de `/app` (Flask test client) muestra
>   todo el markup nuevo. Falta solo la revisión VISUAL del usuario en vivo.
>
> **🔜 PRÓXIMO (cuando el usuario revise):** si no le gusta el estilo A "Terminal", construir el
> estilo **C "Gauge/velocímetro"** (reloj circular 24h con sesión activa al centro + aguja NOW con
> hora exacta). Lo demás (calendario+disclaimer+T&C, mini-nav, chevron, hora NOW) ya quedó cerrado.
>
> **DESPLIEGUE:** el usuario debe correr en el VPS:
> `cd /var/www/TRADINGBOT2.0 && git pull origin claude/intelligent-turing-94qh5i && supervisorctl restart traderacelerator`
>
> **NOTA DE INFRAESTRUCTURA:** esta semana el usuario sufre caídas del navegador ("OH NO" + robot)
> por conversaciones MUY largas que agotan la RAM del navegador. Solución acordada: sesiones nuevas
> y limpias + cerrar pestañas viejas. Por eso se creó esta nota: para retomar sin perder contexto.

---

> **✅ COMPLETADO (2026-06-18) — ADMIN: ANALYTICS DE ANÁLISIS + MEDIDOR DE SALDO OPENAI**
>
> Nueva sección **"🤖 AI Usage & Spend"** en `/admin` (`admin.html`, ancla `#ai-spend`, link en el nav).
> Rama `claude/intelligent-turing-94qh5i`. Tres cosas pedidas por el usuario:
> 1. **Tabla de análisis por usuario** (today / 7d / 30d) con **bandera roja 🚩** cuando alguien
>    supera el cupo de su plan dentro de la ventana del plan (Free 1/7d · Standard 1/24h · Premium
>    5/24h) → detecta bug o abuso. Datos de `UsageLog` (ya existía, 1 fila por análisis exitoso).
> 2. **Métricas + proyección mensual** (análisis y costo estimado today/7d/30d, avg costo/análisis,
>    proyección 30d, promedio por plan).
> 3. **Medidor de "combustible" OpenAI** (decisión del usuario: **medidor propio**, NO API oficial —
>    OpenAI no expone el saldo restante con la API key normal). El admin ingresa el saldo real
>    (`AICreditCheckpoint`); restante = saldo − gasto estimado desde ese checkpoint. Reconciliar =
>    re-ingresar el saldo real (nuevo checkpoint). Endpoint `POST /admin/ai-credit/set`.
>
> **Piezas (todo en `scalpel/app.py` salvo la UI):**
> - Modelos nuevos `AICostLog` (1 fila por llamada IA: tokens + costo estimado) y `AICreditCheckpoint`
>   (snapshot de saldo). Tablas creadas por `db.create_all()` (no necesitan migración ALTER).
> - `record_ai_cost(kind, response, user_id, plan)` — best-effort, **nunca lanza**; lee
>   `response.usage` y estima costo con `AI_PRICE_IN/OUT` (GPT-4o $2.50/$10 por 1M, override por env
>   `AI_PRICE_IN_PER_1M`/`AI_PRICE_OUT_PER_1M`).
> - **(2026-06-18, 2ª iteración) Cableado en las 5 llamadas IA del sitio:** `/analyze` (kind=`analyze`),
>   `/validate` (kind=`validate`), `moderate_forum_text` (kind=`forum_text`), `moderate_forum_image`
>   (kind=`forum_image`) y `scout_chat` (kind=`scout`, hoy DESACTIVADO por `SCOUT_ENABLED=False` pero
>   ya queda medido para cuando se reactive). NO hay más llamadas IA en el código (auditado).
> - **Desglose por categoría en el admin:** Analyzer (analyze+validate) · Forum moderation
>   (forum_text+forum_image) · Scout. `ai_cost_cat`/`ai_calls_cat` (today/7d/30d) → tabla "Cost by category".
> - `_build_ai_analytics_context()` arma todo el contexto; `admin()` lo pasa con `**ai_ctx`.
> - ⚠️ `UsageLog` NO se tocó (sigue contando el rate-limit); el costo vive en `AICostLog` aparte.
> - Verificado: import OK, `/admin` render 200 con la sección, 🚩 en usuario que excede, medidor
>   funciona (set $50 → "$50.00 left", baja con gasto posterior al checkpoint).
> - **NOTA:** hoy aún se usa el token gratis de GitHub Models (no OpenAI pago), así que el costo es
>   un **estimado** ($0 real por ahora) pero ya sirve para la proyección. Cuando migren a OpenAI pago,
>   el medidor refleja el gasto real. GitHub Models puede no devolver `usage` → el helper degrada a 0
>   sin romper nada.
>
> **🔔 RECORDATORIO PARA EL USUARIO (cuando cargue plata REAL en la API de OpenAI):** debe **PROBAR
> LAS DOS COSAS por separado** para ver el costo final real de cada una, ya que ahora están divididas
> en el admin (tabla "Cost by category"):
>   1. **Análisis de screenshots** (Analyzer = analyze + validate) — hacer 5-10 análisis reales y mirar
>      el costo en el panel vs `platform.openai.com/usage`. Estimado: ~$0.02/análisis.
>   2. **Moderación del foro** (text + image) — publicar 5-10 posts/comentarios (algunos con imagen) y
>      ver el costo. Estimado: ~$0.003/publicación (centavos).
>   Objetivo: confirmar los estimados contra el gasto real de OpenAI y ajustar `AI_PRICE_*` si hiciera falta.
> **Deploy:** `git pull origin claude/intelligent-turing-94qh5i && supervisorctl restart traderacelerator`.

---

> **🥇 PRIORIDAD #1 — LO PRIMERO QUE CLAUDE DEBE ENTENDER EN CADA SESIÓN NUEVA**
> **(ANTI-TRAMPA QUIZ/DAILY — LLAVE DE RESPUESTAS SERVER-SIDE, 2026-06-13):**
>
> El Daily Challenge y el Quiz ya **NO confían en que el cliente diga "acerté"**. Esto es
> crítico entenderlo antes de tocar nada del quiz/daily/XP:
>
> 1. ✅ **Las preguntas y respuestas NO se tocaron** — solo se derivó una llave
>    (`scalpel/quiz_answer_key.json`) del banco existente con un extractor que lo evalúa tal cual.
> 2. ✅ **El user tiene que marcar la opción real** — el cliente manda `selected` (cuál marcó,
>    índice original) y el **servidor juzga**; `{correct:true}` ya no gana nada (verificado en test).
> 3. ✅ **El servidor nunca expone la respuesta** — la validación solo devuelve correcto/incorrecto,
>    jamás el índice correcto. El Daily da 1 intento/día (no se puede fuzzear). Bonus: también se
>    cerró un spoof de nivel (decir que una beginner es advanced ya no paga +12).
>
> **Piezas:** `tools/extract_quiz_key.js` (extractor, evalúa el `QUESTION_BANK` real con Node) →
> `scalpel/quiz_answer_key.json` (la llave) → `_load_quiz_key()` en `app.py` (la **regenera al
> arrancar si hay `node`**, si no usa el JSON commiteado). El puerto Python de
> `mulberry32`/`_cycle_order` en `app.py` está **verificado bit a bit** contra el cliente — NO lo
> alteres sin re-verificar paridad. Endpoints: `/api/daily/answer` y `/api/quiz/answer` reciben
> `selected` y validan server-side.
>
> **⚠️ SI EDITAS EL `QUESTION_BANK` (index.html):** corre `node tools/extract_quiz_key.js` y
> commitea el JSON actualizado (por si el VPS no tiene node).
>
> **🚀 DEPLOY (este cambio es backend + necesita el JSON nuevo). En el VPS:**
> ```
> cd /var/www/TRADINGBOT2.0 && git pull origin claude/epic-lovelace-GsOuo && supervisorctl restart traderacelerator
> ```
> (Si el VPS tiene `node`, la llave se regenera sola al arrancar; si no, usa el JSON commiteado.)

---

> **📌 EN DISEÑO (2026-06-13) — SISTEMA DE XP / RANGOS ("hacer más vivo el sitio") — ESPEC. CONGELADA**
>
> Contexto: discusión sobre ganchos de retención (idea original mencionada por el usuario como
> sugerida por "Fable" en otra sesión) — el sitio tiene mucha amplitud pero pocas razones para
> volver al día siguiente. Ya implementado: testimonials + ruleta del daily challenge. Siguiente
> en la cola: **sistema de XP / Rangos** (diseño CONGELADO, luz verde del usuario 2026-06-13) +
> **reloj de Kill Zones en vivo + calendario económico** (en stand-by hasta terminar rangos).
>
> **⚠️ ACCESO REAL POR PLAN (verificado en código — base de todo el balance):**
> - **Free:** solo Analyze (1 análisis/7 días) + 1 camo de regalo NO (eso es Standard). Free = solo Analyze.
> - **Standard:** Analyze (1 análisis/24h) + 1 camo de regalo al comprar. Nada más.
> - **Premium:** TODO — Analyze (5/24h), Quiz, Pre-Flight, Foro, Daily Challenge+ruleta, Synapse, Chalkboard (Scalper).
> - Gates en `app.py`: Foro y Daily Challenge son `@premium_required`; Quiz/Synapse/Scalper chequean
>   `U.plan === 'premium'` en `switchTab` (`index.html`); Pre-Flight está en `FEATURES.premium` del
>   unlock reveal (premium-only, aunque su API hoy solo tiene `@login_required` — posible inconsistencia
>   a revisar). Analyze límites: `PLAN_LIMITS` = free 1/7d, standard 1/24h, premium 5/24h.
> - **Testimonial: abierto a TODOS los planes** (free incluido) — commit `d4d6a3d` cambió
>   `app_view()` de `plan in ('standard','premium')` a `if not unlock_plan:`. Sigue con gate de
>   ~20 min de uso real (localStorage `ta_usage_min`) del lado cliente.
>
> **DECISIÓN CLAVE — SIN MULTIPLICADOR (descarta el ×1/×2/×4 del boceto viejo):**
> La brecha entre planes NO se hace con multiplicador, sino con **ponderación inversa por plan**
> (las acciones que un plan pobre SÍ puede hacer valen MÁS por acción, para compensar que tiene
> menos fuentes). Objetivo de balance pedido por el usuario: **ratio a Legend Premium 1 : Standard ~2
> : Free ~3** (antes daba 12:1, inaceptable). El XP mide "progreso como trader", no "cuántas features
> tienes", por eso se normaliza.
>
> **TABLA DE XP — ACCIONES COMPARTIDAS (ponderadas por plan):**
> | Acción | Free | Standard | Premium |
> |---|---|---|---|
> | Primera visita del día¹ | +18 | +12 | +5 |
> | Análisis IA exitoso | +60 | +30 | +10 |
> | Testimonial (cada 30 días)² | +30 | +30 | +30 |
>
> **TABLA DE XP — EXCLUSIVAS DE PREMIUM:**
> | Acción | XP | Tope diario |
> |---|---|---|
> | Quiz — acertar pregunta NUEVA | +5/+8/+12 (beg/int/adv) | 20 XP/día |
> | Daily Challenge correcto | +15 | 1/día |
> | Daily Challenge — racha (cada 7)² | +30 | exento |
> | 1er checklist Pre-Flight² (único en la vida) | +20 | exento |
> | Pre-Flight check registrado | +5 c/u | solo primeros 3/día (15) |
> | Foro — post | +5 | 2/día (10) |
> | Foro — comentario | +2 | 5/día (10) |
> | Foro — reacción recibida | +1 | 5/día (5) |
>
> ¹ "Primera visita del día" = +XP la 1ª vez que se abre `/app` en un día calendario **UTC**
>   (misma convención que el Daily Challenge `_utc_today()`; funciona con sesión recordada, NO
>   depende de login por contraseña). Se guarda la fecha (`User.last_xp_active_date` propuesto);
>   recargar no vuelve a pagar.
> ² Exento del techo diario (recompensas raras, no farmeables).
>
> **TECHO MAESTRO DE XP/DÍA:**
> - Free: SIN techo (su límite de 1 análisis/semana ya lo topa naturalmente).
> - Standard: SIN techo (1 análisis/día ya es el tope natural).
> - **Premium: 80 XP/día** — único plan que combina muchas fuentes → necesita el candado.
>   Tras tocarlo, toda acción recurrente suma 0 ese día (testimonial/racha/1er-checklist exentos).
>
> **PROMEDIO REALISTA XP/DÍA:** Free ~27.6 · Standard ~43 · Premium ~84.
>
> **LOS 8 RANGOS (nombres CONFIRMADOS — mezcla general+ICT+mercados, NO solo ICT):**
> | # | Rango | XP acumulado |
> |---|---|---|
> | 1 | Paper Trader | 0 |
> | 2 | Retail Trader | 200 |
> | 3 | Chart Technician | 600 |
> | 4 | Liquidity Hunter | 1,400 |
> | 5 | Swing Strategist | 2,800 |
> | 6 | Order Flow Sniper | 5,000 |
> | 7 | Market Maker | 8,000 |
> | 8 | **Trading Legend** | 12,000 |
> Curva acelerada (incrementos +200/+400/+800/+1400/+2200/+3000/+4000). El usuario notó el salto
> final; se ofreció suavizarla pero quedó con esta. Pool de nombres alternos por si se cambia alguno:
> R3 Chartist/Technical Analyst · R5 Position/Trend Strategist · R6 Order Flow Analyst/Smart Money
> Sniper · R7 Institutional/Prop Trader · R8 Market Wizard/Apex Trader/The 1%.
>
> **VELOCIDAD (días a cada rango) — confirma el ratio 1:2:3 a Legend:**
> | Rango | Free | Standard | Premium |
> |---|---|---|---|
> | 2 Retail Trader | ~7d | ~5d | ~2d |
> | 3 Chart Technician | ~22d | ~14d | ~7d |
> | 4 Liquidity Hunter | ~1.7mes | ~1mes | ~17d |
> | 5 Swing Strategist | ~3.3mes | ~2.2mes | ~1mes |
> | 6 Order Flow Sniper | ~6mes | ~3.8mes | ~2mes |
> | 7 Market Maker | ~9.5mes | ~6mes | ~3.1mes |
> | 8 **Trading Legend** | **~14.3mes** | **~9.2mes** | **~4.7mes** |
> Mínimo absoluto a Legend (premium topando 80/día sin fallar): ~150 días (~5 meses) — prestigioso.
>
> **REGLA DEL TOPE DE QUIZ ("pagar completo o no pagar"):** una pregunta solo paga si CABE entera
> bajo el tope de 20/día. Si vas 13/20 y respondes una de +12, NO da un parcial de +7 ni quema la
> pregunta: queda disponible y mañana paga los +12 completos. Los topes NUNCA ruedan al día
> siguiente, pero así nunca se pierde el valor de una pregunta.
>
> **RECOMPENSAS POR RANGO (SIN dinero — la ruleta sigue siendo el único lugar con descuentos):**
> 1. **Badge de rango** junto al username — en foro (posts/comentarios), en testimonials/landing,
>    y en el menú inicial al lado del badge de plan (Free/Standard/Premium).
> 2. **Camo exclusivo** por cada subida de rango (8 camos — diseñar juntos, ver tarea prioritaria abajo).
> 3. **Acceso beta prioritario** a features nuevas para los rangos altos (rango 6-8).
> 4. **Certificado PDF descargable** al subir de rango (reusa el generador de PDFs existente).
>
> **ANTI-ABUSO (resumen de candados):**
> - Todo XP server-side, con llave de deduplicación por acción (no recontar reenviando). Tabla
>   `XPLog` auditable/reversible.
> - Login: 1×/día UTC (fecha guardada). · Análisis: solo si exitoso y consume cupo del plan.
> - Quiz: solo 1ª vez por `question_id` + tope 20/día. · Pre-Flight: checks ilimitados en FUNCIÓN,
>   pero solo primeros 3/día dan XP. · Daily Challenge: 1/día, cronometrado (ya existe).
> - Foro: topes por tipo + **reversión automática** si moderación IA marca spam en 24h.
> - Reacciones: tope 5/día + no cuentan las de cuentas nuevas/mismo dispositivo (anti-sockpuppet).
> - Premium techo maestro 80/día = candado final.
>
> **UI PEDIDA POR EL USUARIO — apartado "My Rank Progress":** en el menú del engranaje, JUSTO
> DEBAJO de "My Coupons" (`#menu-coupons`). Muestra: barra de XP + rango actual + "faltan X XP para
> [siguiente rango]" + lista de **acciones aún disponibles hoy** para sumar puntos (ej. "Daily
> Challenge ✓ · Quiz: 12/20 XP restantes · Análisis: 2/5 usados").
>
> **🔴 TAREA PRIORITARIA A FUTURO — DISEÑAR LOS CAMOS UNO POR UNO CON EL USUARIO:**
> Diseñar EN CONJUNTO (usuario + Claude): los 8 camos de recompensa por rango + los de cada plan
> (Standard "1 Camo included", Premium "3 camos") + los de la tienda. Hoy solo hay 3 placeholders
> (Navy Trader, Desert Ops, Forest Recon) en `camos.html`. NO hacerlo de forma autónoma.
>
> **SIGUIENTE PASO TÉCNICO (aún no iniciado):** modelo `XPLog` + campos `User.xp`/`User.rank` +
> `User.last_xp_active_date`; helper `add_xp(user, source, amount)` con dedup + topes; tracking de
> `question_id` premiados (quiz) y flag de 1er checklist; endpoint de progreso `/api/rank/progress`;
> UI "My Rank Progress" + badges; backfill de XP para usuarios existentes. DESPUÉS de esto: badges
> (diseño visual + animaciones por rango) — es lo siguiente a iterar con el usuario.

---

> **🔔 SPAM OBLIGATORIO AL VOLVER (pedido por el usuario 2026-06-13, 1AM, antes de dormir):**
> La PRÓXIMA vez que el usuario escriba, mostrarle esta lista de "lo que falta del sistema de
> XP/Rangos". Etapas 1 (backend) y 2 (UI: medallas v3 + panel "My Rank Progress") YA están
> hechas, probadas y pusheadas (commits `5ea7bb0` backend, `6575905` UI). Falta:
>
> 1. **⚠️ CABLEAR EL QUIZ AL XP (gap real):** el endpoint `POST /api/quiz/answer` existe y otorga
>    XP, pero el quiz client-side (`QUESTION_BANK` en `index.html`) **todavía NO lo llama** cuando
>    aciertas una pregunta por primera vez. Hay que hacer que, al responder correcto, el cliente
>    haga `fetch('/api/quiz/answer', {question_id, level})`. Sin esto, la fuente de XP del quiz
>    no suma nada todavía. (Las otras fuentes —login, análisis, daily, pre-flight, foro,
>    testimonial— SÍ están cableadas server-side y funcionan.)
> 2. **Certificado PDF al subir de rango:** diseñar + lógica, reusando el generador de PDFs
>    existente. Idea: un panel/celebración "¡Subiste a [rango]!" con botón "Descargar certificado".
>    Hoy el rank-up solo emite un `record_audit_event('rank_up', ...)` silencioso — falta el
>    momento visual de celebración + el PDF descargable.
> 3. **Camos por rango (8):** diseñarlos UNO POR UNO con el usuario (ya es tarea prioritaria
>    anotada abajo). Los badges ya están; los camos no.
> 4. **Acceso beta prioritario (rangos 6-8):** es una política, no hay código aún — se cablea
>    cuando salga una feature nueva (mostrarla antes a rangos altos).
> 5. **Desplegar la Etapa 2 en el VPS y verificar visualmente** (el usuario aún no la había
>    desplegado al irse a dormir): `git pull` + `supervisorctl restart traderacelerator`, luego
>    abrir el menú de cuenta → ver la medalla + "My rank progress".
> 6. **Verificar/pulir en vivo:** medallas en foro (lag con muchos posts), look en light/dark,
>    el panel "My Rank Progress" con datos reales, y que el rango se vea en testimonials/landing.
> 7. (Opcional) **Backfill de XP** para dar XP retroactivo por actividad histórica si el usuario
>    lo quiere — hoy todos arrancan en xp=0 / Paper Trader.
>
> ---

> **🚨 MÁS URGENTE — PENDIENTE: CONECTAR CUENTA BANCARIA (pago por transferencia, NO Binance)**
>
> El usuario decidió que los pagos serán por **transferencia bancaria en USD a la cuenta
> de su amigo/socio**, NO por USDT/Binance como dice actualmente el sitio.
>
> **Hoy `scalpel/templates/checkout_done.html:109` dice textualmente:**
> `"Send ${{ '%.2f'|format(order.final_price) }} USD in USDT to our Binance account."`
>
> **Cuando el usuario traiga los datos bancarios** (banco, titular, número de cuenta /
> routing / SWIFT según corresponda), hay que:
> 1. Reemplazar ese texto en `checkout_done.html` por las instrucciones de transferencia
>    bancaria reales.
> 2. Cambiar `payment_method='usdt-binance'` (en `checkout_create()`, `scalpel/app.py`
>    ~línea 1760) a algo como `'bank-transfer'`.
> 3. Revisar si hay otras menciones a "Binance"/"USDT" en el sitio (`grep -rn
>    "Binance\|USDT\|usdt-binance" scalpel/`) y actualizarlas también.
>
> Esta tarea bloquea poder cobrar de forma realista — es la más urgente de todas
> las pendientes hasta que el usuario traiga los datos de la cuenta.

---

> **✅ COMPLETADO (2026-06-11/12) — SESIÓN GRANDE: LOGIN alt_id · RULETA · CUPONES · UNLOCK REVEAL · TESTIMONIALS · LANDING REFRESH**
>
> Todo pusheado a `claude/epic-lovelace-GsOuo` Y `claude/intelligent-turing-94qh5i`, desplegado y verificado en el VPS.
> Último commit de la sesión: `77d5940`.
>
> **1. Fix de acceso intermitente ("candados") — `User.alt_id` (commits `8ca45f3`, `23cebec`):**
> - Causa raíz: cookies "remember me" viejas guardaban el PK numérico de antes de la migración
>   SQLite→PostgreSQL y podían resolver a la cuenta equivocada. La DB nunca estuvo mal.
> - Fix: `User.alt_id` (token aleatorio de 40 chars, unique+indexed), `get_id()` devuelve `alt_id`,
>   `load_user` busca por `alt_id`. Migración `_migrate_user_alt_id_column()` con backfill.
> - ⚠️ **LECCIÓN PostgreSQL #1**: `user` y `order` son palabras reservadas — SIEMPRE quotear
>   `"user"`/`"order"` en SQL crudo. El commit inicial sin quotes TUMBÓ producción (crash-loop).
> - ⚠️ Para tests con `test_client`: `s['_user_id'] = user.alt_id` (ya NO el id numérico).
>
> **2. Ruleta — rediseño visual + alcance de cupones (commits `d7372d7`, `7722fa4`, `4e07e71`, `dca4a00`):**
> - Rueda SVG estilo "market gauge": bisel dorado, 5 sectores grafito que se vuelven más dorados
>   según rareza del premio (5%→casi negro · mes gratis→oro pleno). Al usuario LE GUSTÓ este diseño
>   (el primero le pareció "carnaval/candy crush").
> - Códigos de descuento (`SPIN-XXXXXX`): únicos (loop anti-colisión), `max_uses=1`,
>   `restrict_user_id` (solo el ganador puede canjearlos — `_validate_promo` lo verifica).
> - Plan mensual → `valid_for='monthly'` (90 días). Plan ANUAL → `valid_for='store'` (1 año,
>   para futuras compras de indicadores/camos). `PromoCode.valid_for` ahora acepta 'store'.
> - "1 mes gratis" extiende `plan_expires_at` +30 días en cualquier ciclo.
>
> **3. "Mis cupones" (commits `fbbad57`, `270fd9b`):**
> - Endpoint `/api/daily/coupons` (@premium_required) — lista códigos del usuario con estado
>   (active/used/expired). Modal global `#coupons-overlay` + entrada `#menu-coupons` en el
>   account-menu (arriba, junto al User ID), visible solo para premium/admin.
>
> **4. Unlock reveal estilo Call of Duty (commits `3b56013`, `ba77cdf`, `4632676`, `46a83a3`):**
> - Panel full-screen mostrado UNA vez tras activarse una compra: `Order.celebrated_at`
>   (+ `_migrate_order_columns()` con `"order"` quoteado) se sella al renderizar `/app`.
> - Carrusel de features desbloqueados con flechas, dots, halo, rayos rotatorios, skip.
> - **Temas por plan via CSS vars** (`--uk`, `--uk-bright`, `--uk-mid`, `--uk-deep`):
>   Premium = dorado (default) · Standard = azul navy (`.unlock-overlay.standard`).
> - Slides Premium: analyzer5, **preflight (con badge NEW animado)**, forum, quiz, daily,
>   scalper (renombrado "Chalkboard"), synapse, indicators, **camos3** (3 camos).
> - Slides Standard: analyzer24, projects5, **camo1** (1 camo de regalo).
> - Landing: card Standard ahora anuncia "1 Camo included" (`ps4` i18n, 4 idiomas).
> - Tab Pre-Flight de la app también lleva badge `NEW` animado (`.new-badge`, animación barata
>   de background-position).
> - **Confidencialidad IA**: TODA mención a "GPT-4o" eliminada del sitio (commit `4d89449`) —
>   ahora dice "our proprietary AI engine" / "motor de IA propio". NUNCA revelar qué modelo se usa.
>
> **5. Sistema de TESTIMONIALS/reviews (commits `1199b50`, `9b28948`, `e3c3c2b`, `a90f86c`, `77d5940`):**
> - **Decisión legal**: NO reseñas inventadas (ilegal — regla FTC 2024, multas). Solo usuarios
>   reales. Curar testimonios positivos es legal si no se presenta como "score agregado".
> - Modelo `Testimonial` (user_id, rating 1-5, text, display_name snapshot, plan, published)
>   + `User.last_review_prompt_at` (+ migración).
> - Prompt in-app cada 30 días para Standard/Premium (modal estrellas+texto+consentimiento).
>   Gate adicional: solo aparece tras **20 min de uso real acumulado** (localStorage
>   `ta_usage_min`, cuenta solo con pestaña visible). "Más tarde" pospone 30 días.
> - Publicación AUTOMÁTICA si: rating ≥4 + consentimiento + texto. Ratings 1-3 quedan privados.
> - Endpoints: `/api/testimonial/submit` (POST) y `/api/testimonials` (público, máx 24).
> - **Carrusel book-flip en landing** (entre Pricing y CTA final): rotateY 3D cada 6s, avatar
>   monograma, estrellas, cita serif. Oculto hasta que exista ≥1 reseña publicada
>   (mostrar con `style.display='block'` — `''` NO funciona contra regla CSS, bug ya corregido).
> - Tema dual: dark = grafito/dorado · light = azul navy profundo.
> - ⚠️ **LECCIÓN PostgreSQL #2 (commit `9b28948`)**: una migración de columna nueva debe correr
>   ANTES que cualquier migración que consulte esa tabla via ORM (el SELECT pide TODAS las
>   columnas del modelo). `_migrate_user_review_column()` corre antes que la de alt_id.
>   Este bug también tumbó producción brevemente — probar migraciones simulando DB vieja.
>
> **6. Reglas de credenciales (commit `80c4ec8`):**
> - Username: 3-20 chars, `^[A-Za-z0-9][A-Za-z0-9._-]{2,19}$` (sin espacios).
> - Contraseña: 8+ chars con al menos 1 letra y 1 número. Aplica en register y reset.
> - Server-side + atributos HTML + mensajes específicos i18n 4 idiomas (auth.js).
> - Cuentas existentes NO afectadas. Admin renombrado: username ahora es **`maurotradesve`**.
>
> **7. Landing refresh v1+v2 (commits `f226847`, `3a82f7a`) — misma estructura, mejor acabado:**
> - **Card #7 "Pre-Flight"** en YOUR TOOLKIT (chip Premium + badge NEW animado, i18n `tc7_t/b`
>   4 idiomas). Título: "Seven instruments. One platform." · stat strip dice "7 Tools".
> - Hero: aurora dorada estática detrás del titular (gradiente puro, costo cero).
> - **Mock-terminal con efecto "typing en vivo"**: el análisis IA se escribe solo al entrar en
>   viewport (token-based, los spans se colorean mientras escribe), caret parpadeante, chips
>   de resultado en cascada al terminar.
> - Stat numbers cuentan 0→N con ease-out al revelarse.
> - Micro-interacciones hover: tool-cards (ícono spring + borde), cap-items (lift + letra se
>   rellena), pain-cards (slide), comm-cards (lift). CTA con barrido de luz.
> - Pricing: card Premium featured a scale(1.035) + halo dorado (jerarquía visual).
> - Tamaños de título "Sound familiar" vs "The solution" son DISTINTOS a propósito (decisión
>   del usuario: dejarlo así).
> - Todo respeta `prefers-reduced-motion` y usa solo transform/opacity/background-position.
>
> **Pendiente próximo de esta línea de trabajo:** seguir reduciendo lag en apartados pesados;
> posible ronda 3 de la landing si el usuario la pide.

---

> **✅ COMPLETADO (2026-06-11) — SISTEMA DE FIABILIDAD: AUDIT LOG + ALERTAS + BACKUPS + SENTRY**
>
> Sesión del 2026-06-10/11 (commits `b67f1c3`, perf/XSS, `6f63d54` — pusheados a
> `claude/epic-lovelace-GsOuo` y `claude/intelligent-turing-94qh5i`, **desplegado y verificado en el VPS**):
>
> **1. Pre-Flight — UI (commit `b67f1c3`):**
> - Tab Pre-Flight movido ANTES del tab Quiz en la nav (orden alfabético).
> - Tablas de estadísticas/comparación (`.pf-table`, `.pf-stats-table`) rediseñadas estilo
>   Excel/spreadsheet: grid completo de bordes, zebra striping, tipografía normal (sin monospace),
>   verde/rojo suaves `#16a34a`/`#dc2626`, `tabular-nums`.
>
> **2. Performance + seguridad (`index.html`):**
> - Synapse: `figureHalf(y)` reemplazada por LUT precomputada (`FIG_HALF_LUT`, Float32Array,
>   step 0.05) — elimina ~5778 llamadas a `Math.exp()` por frame en `updateNet()`.
> - QCFire (fuego del badge del quiz): el loop rAF ahora se salta el trabajo pesado cuando
>   `document.hidden || canvas.offsetParent === null` (antes corría infinito en background).
> - XSS: salida de `marked.parse(data.analysis)` ahora se sanitiza con **DOMPurify**
>   (CDN `dompurify@3` agregado en `<head>`) antes del `innerHTML` en el Analyze.
>
> **3. Sistema de auditoría (commit `6f63d54` — `app.py` + `admin.html`):**
> - Modelo nuevo **`AuditEvent`** (tabla `audit_event`, creada auto por `db.create_all()`).
> - Helper **`record_audit_event(event_type, user_id, detail, success)`** — nunca lanza excepción.
> - 13 call-sites instrumentados: `order_created`, `order_paid`, `order_cancelled`, `plan_expired`,
>   `promo_created`, `pdf_issued`, `pdf_downloaded`, `email_verification` (register/login/resend),
>   `email_reset`, `email_contact`, `analysis_error`.
> - **Alertas inmediatas**: si falla un evento del set `AUDIT_ALERT_ON_FAILURE` (pagos, PDFs,
>   emails, analysis), `_send_audit_alert_email()` manda correo al admin (threaded, fire-and-forget).
> - **Panel admin**: sección "Audit Log" al final de `/admin` (últimos 150 eventos, filas rojas
>   para fallos, contador `(N ⚠)` en el nav).
>
> **4. Scripts cron nuevos (raíz del repo):**
> - **`daily_audit_summary.py`** — digest diario por correo de los AuditEvent de las últimas 24h.
>   ⚠️ Debe correr con el **Python del venv** (necesita Flask).
> - **`backup_db.py`** — backup diario a `backups/` (gitignored), retiene 14 días. Corre con
>   Python del sistema (solo stdlib). Detecta `DATABASE_URL` (env o `scalpel/.env`): si es
>   **PostgreSQL usa `pg_dump --format=custom`** (`.dump`); si no, copia SQLite (`.db`).
>   ⚠️ **PRODUCCIÓN USA POSTGRESQL** (confirmado 2026-06-11: `DATABASE_URL="postgresql...` en el
>   supervisor conf — la migración SQLite→PostgreSQL de la alerta de abajo YA SE HIZO en una
>   sesión anterior, junto con gunicorn -w 4). El `scalpel.db` del VPS es un residuo viejo.
>   Restaurar: `pg_restore --clean --if-exists -d "$DATABASE_URL" backups/scalpel_FECHA.dump`.
> - **Crontab del VPS (root) quedó así:**
>   ```
>   0 * * * *  WA_PHONE=... WA_APIKEY=... SITE_URL=... /usr/bin/python3 /var/www/TRADINGBOT2.0/monitor.py >> /var/log/ta_monitor.log 2>&1
>   0 8 * * *  cd /var/www/TRADINGBOT2.0 && /var/www/TRADINGBOT2.0/venv/bin/python3 daily_audit_summary.py >> /var/log/ta_audit_summary.log 2>&1
>   30 7 * * * cd /var/www/TRADINGBOT2.0 && /usr/bin/python3 backup_db.py >> /var/log/ta_backup.log 2>&1
>   ```
>
> **5. Sentry — instalado pero INACTIVO:**
> - Bloque opcional en `app.py` (tras `app = Flask(...)`) que solo se activa si existe la env var
>   `SENTRY_DSN`. `sentry-sdk==2.20.0` instalado en el **venv** del VPS. Para activarlo: cuenta
>   gratis en sentry.io → copiar DSN → agregar `SENTRY_DSN="..."` al `environment=` del supervisor
>   conf → `supervisorctl reread && update && restart traderacelerator`. Capturaría TODA excepción
>   no controlada (dashboard en sentry.io, no en el panel admin).
>
> **6. Datos clave del VPS descubiertos/cambiados en esta sesión:**
> - La app corre con **venv**: `command=/var/www/TRADINGBOT2.0/venv/bin/gunicorn -w 4 -b 0.0.0.0:5001 scalpel.app:app`.
>   El `python3` del sistema NO tiene Flask (y pip del sistema es externally-managed; usar
>   `venv/bin/pip` o `--break-system-packages`).
> - Env vars de producción viven en `environment=` de `/etc/supervisor/conf.d/traderacelerator.conf`
>   (6 vars: DATABASE_URL, WA_PHONE, WA_APIKEY, GITHUB_TOKEN, SECRET_KEY, MAIL_APP_PASSWORD).
>   Ahora también hay un **`scalpel/.env`** (gitignored, chmod 600) con las mismas vars entre
>   comillas, para que los scripts cron las vean vía `load_dotenv()`. **⚠️ Si se cambia una env var
>   en supervisor, actualizar TAMBIÉN `scalpel/.env`.**
> - **Gmail App Password renovado (2026-06-11):** el anterior estaba muerto (Google lo rechazaba
>   con 535 BadCredentials → los OTP/reset llevaban tiempo fallando en silencio). Se generó uno
>   nuevo, actualizado en supervisor conf y `scalpel/.env`, verificado con envío real exitoso.
>   Pendiente del usuario: borrar el App Password viejo en myaccount.google.com/apppasswords.
> - ⚠️ El terminal del usuario (Mac) convierte comillas rectas en curvas (“ ” ‘) al pegar —
>   si un `sed` falla con "unknown option to `s'", es eso. Preferir bloques `python3 - <<'EOF'`.
> - El usuario se pierde en editores tipo nano/vim — para el crontab usar el patrón
>   `(crontab -l | grep -v ...; echo '...') | crontab -` en vez de `crontab -e`.
>
> **Red de seguridad completa ahora:** fallo en pago/PDF/email → alerta inmediata por correo +
> fila roja en Audit Log · resumen diario 8:00 AM · backup DB diario 7:30 AM · monitor de salud
> cada hora (WhatsApp) · Sentry listo para activar.

---

> **✅ COMPLETADO (2026-06-11) — QUIZ HARDCORE 100% RECONSTRUIDO (16 metodologías / 160 escenarios)**
>
> Las 16 metodologías del Quiz Hardcore (Order Blocks, FVGs, Market Structure, Liquidity, Kill Zones,
> AMD, PD Arrays, Wyckoff Accumulation/Distribution/Market Phases, SMC Structure/Confluences/Liquidity,
> Chart Patterns, Candlestick Patterns, Harmonic Patterns) están reconstruidas con los ángulos del
> usuario, validadas (`node --check` OK, 0 `\\'`, sin ids duplicados, balance de longitud dentro de
> límites) y pusheadas a `claude/epic-lovelace-GsOuo` (último commit `98ecd1e`). Detalle de commits
> por grupo en la sección "ESTADO ACTUAL DEL HARDCORE QUIZ" más abajo. **SIGUIENTE:** sin tarea de
> quiz pendiente — a la espera de nuevas indicaciones del usuario.
>
> ---
>
> **✅ (HISTÓRICO 2026-06-06) — LIMPIEZA FINAL DE DISTRACTORES DEL QUIZ**
>
> Hecho: **11 distractores beginner** (commit `8947397`) y **~60 distractores intermediate**
> (commit `7c2a2a8`) reescritos como misconceptions técnicamente plausibles en EN/ES/FR/PT,
> validados con `node --check` (0 ocurrencias de `\\'`), pusheados a `claude/epic-lovelace-GsOuo`.
> Los 3 niveles (beginner/intermediate/advanced) quedan limpios. El detalle histórico de abajo se
> conserva como referencia del procedimiento.
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

> **✅ ALERTA #2 RESUELTA (2026-06-11) — ya NO mostrar este bloque diariamente:**
>
> 1. 🗄️ **MIGRACIÓN PostgreSQL — HECHA** (sesión anterior): producción corre PostgreSQL
>    (`DATABASE_URL="postgresql...` en supervisor conf) + gunicorn -w 4. Confirmado 2026-06-11.
> 2. 🩺 **MONITOREO — HECHO** (2026-06-11): monitor.py cada hora (WhatsApp) + Audit Log con
>    alertas inmediatas por correo + resumen diario 8AM + backup pg_dump diario 7:30AM +
>    Sentry instalado (inactivo hasta configurar SENTRY_DSN). UptimeRobot descartado por el usuario.

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

> **📝 CONTEXTO — HARDCORE QUIZ · KILL ZONES y METODOLOGÍAS PENDIENTES**
>
> **Qué se hizo:** Se reconstruyeron los 10 escenarios `ict_kz_h1–h10` del array
> `HARDCORE_SCENARIOS` en `scalpel/templates/index.html`. Cada escenario tiene
> `chart` + `q` (4 idiomas) + `opts` (4 opciones) + `exp` + `revealChart` + `outcome`.
>
> **Los 10 ángulos implementados (en orden de id):**
> 1. `h1` — Setup perfecto 15 min antes de que cierre el KZ → Skip (outcome: loss)
> 2. `h2` — London alcista + NY abre bajista → el sesgo HTF diario manda, no la sesión más reciente (outcome: win)
> 3. `h3` — Setup válido fuera de toda kill zone → no tomarlo, falta volumen institucional (outcome: loss)
> 4. `h4` — KZ abierto pero ya ~90 pips expandidos → validez reducida, R:R colapsado (outcome: loss)
> 5. `h5` — London sweep bajista + NY setup alcista misma zona → confluencia AMD (outcome: win)
> 6. `h6` — Asia rango limpio, London rompe con vela pequeña sin desplazamiento → fake break (outcome: win)
> 7. `h7` — Dos setups opuestos en mismo KZ por timeframe → priorizar HTF sobre LTF (outcome: win)
> 8. `h8` — KZ de NY ya cerró, precio en zona perfecta → no operar (outcome: loss)
> 9. `h9` — Silver Bullet activo pero HTF en distribución → no confiar ciegamente (outcome: loss)
> 10. `h10` — 3 KZs con señales mixtas → sesgo viene del HTF draw, no del conteo de sesiones (outcome: win)
>
> **Outcomes: 4 loss (h3, h4, h8, h9) · 6 win (h2, h5, h6, h7, h10 · h1=skip/loss pedagógico)**
>
> ---
>
> **📋 ESTADO ACTUAL DEL HARDCORE QUIZ — Metodologías completadas vs. pendientes**
>
> **✅ Completadas (16 metodologías — TODAS):**
> - Order Blocks (`ict_ob_h1–h10`)
> - FVGs (`ict_fvg_h1–h10`)
> - Market Structure (`ict_ms_h1–h10`)
> - Liquidity / Sweeps (`ict_liq_h1–h10`) — reconstruidas commit `1e04f0e`
> - Kill Zones (`ict_kz_h1–h10`) — reconstruidas commit `feaf2ec`, distractores ya plausibles y validados (longest-wins 1/10, shortest 0/10)
> - AMD (`ict_amd_h1–h10`) — reconstruidas 2026-06-10 commit `ed538d9` con los 10 ángulos del usuario (manipulación extendida, acum vs distrib, AMD anidado, D sin sweep BSL, M sin expansión, acum larga, anclaje del ciclo, D diario vs H1, doble purga en una vela, micro-acum en mitad del trade). Outcomes 3 loss / 7 win.
> - PD Arrays (`ict_pd_h1–h10`) — reconstruidas 2026-06-11 commit `ffa4d25`.
> - Wyckoff Accumulation (`wyk_acc_h1–h10`) — reconstruidas 2026-06-11 commit `b4ca6f1`. Outcomes 2 loss / 8 win.
> - Wyckoff Distribution (`wyk_dist_h1–h10`) — reconstruidas 2026-06-11 commit `bc828b8`. Outcomes 2 loss / 8 win.
> - Wyckoff Market Phases (`wyk_phase_h1–h10`) — reconstruidas 2026-06-11 commit `64f7b5a`. Outcomes 2 loss / 8 win.
> - SMC Structure (`smc_str_h1–h10`) — reconstruidas 2026-06-11 commit `b4c9c4f`. Outcomes 2 loss / 8 win.
> - SMC Confluences (`smc_conf_h1–h10`) — reconstruidas 2026-06-11 commit `89cf6b8`. Outcomes 0 loss / 10 win.
> - SMC Liquidity (`smc_liq_h1–h10`) — reconstruidas 2026-06-11 commit `48ed38f`. Outcomes 3 loss / 7 win.
> - Chart Patterns (`pat_flag_h1–h10`) — reconstruidas 2026-06-11 commit `cc261f2`. Outcomes 5 loss / 5 win.
> - Candlestick Patterns (`pat_candle_h1–h10`) — reconstruidas 2026-06-11 commit `78a4924`. Outcomes 4 loss / 6 win.
> - Harmonic Patterns (`pat_harm_h1–h10`) — reconstruidas 2026-06-11 commit `98ecd1e`. Outcomes 1 loss / 9 win.
>
> **Estado: las 160 escenarios de HARDCORE_SCENARIOS están reconstruidos y validados** (escaping `\\'`=0,
> `node --check` OK, sin ids duplicados, balance de longitud dentro de límites en todos los grupos).
> No quedan metodologías pendientes de los ángulos provistos por el usuario.
>
> ---
>
> **Estándares de calidad (pipeline obligatorio para cada commit):**
> - **Balance de longitud**: script de ranking por `es:` → longest-wins ≤2/10, shortest-wins ≤2/10
> - **Geometría**: líneas ≥0.25 entre sí; ≤2 zonas; ≤2 marcadores en velas distintas;
>   revealChart extiende chart inicial con 2–3 velas extra
> - **Escaping**: `grep -c "\\\\'"` = 0; apóstrofes → `\'` (nunca `\\'`)
> - **Parse**: extraer `<script>` con `HARDCORE_SCENARIOS`, correr `node --check`; total esperado: 160+
> - **Distractores**: misconceptions plausibles con desarrollo técnico — nunca frases vacías o absurdas
>
> **Rama activa:** `claude/epic-lovelace-GsOuo` · Último commit Quiz Hardcore: `98ecd1e` (Harmonic Patterns, 2026-06-11) — las 16 metodologías / 160 escenarios completos.

---

> **💰 CONTEXTO — COSTOS REALES DE LA API DE IA (revisión 2026-06-13)**
>
> **Modelo usado:** `gpt-4o` (GPT-4o), vía `OpenAI` SDK apuntando hoy al endpoint gratuito de
> GitHub Models (`https://models.inference.ai.azure.com`, `GITHUB_TOKEN`). El plan es migrar a
> la **API paga de OpenAI** (mismo modelo `gpt-4o`, mismo prompt/lógica — igual de certero, sin
> los límites de rate del tier gratuito). Si el usuario le dice a alguien qué IA usa: **"OpenAI
> API, GPT-4o"** es correcto — eso sí, en el SITIO PÚBLICO sigue la regla de confidencialidad
> de abajo ("our proprietary AI engine", nunca mencionar GPT-4o/OpenAI en el front-end).
>
> **⚠️ Corrección importante sobre qué consume tokens (el PDF `Scalpel_Costos_Operativos_IA.pdf`
> contaba solo 1 llamada y el Scout, que está DESACTIVADO → $0):**
>
> El análisis de un screenshot dispara **DOS llamadas Vision a GPT-4o**, no una:
> 1. `/validate` (`app.py`) — pre-chequeo: ¿se ven entry/exit/SL-TP en la imagen? `max_tokens=150`.
> 2. `/analyze` (`app.py`) — la llamada principal: imagen + `SYSTEM_PROMPT` ICT + datos del
>    formulario (instrument, direction, session, result, HTF bias, approach, confluences,
>    **notes/tesis del trader**), `max_tokens=900`.
>
> **¿Por qué el formulario consume tokens si "solo suben fotos"?** Porque las `notes` (tesis del
> trader) y los demás campos se mandan a la IA junto con la imagen para que **contraste lo que
> el trader dice que vio contra lo que realmente está en el gráfico** (no es un análisis
> genérico de la imagen sola). El costo del texto del formulario es marginal (~$0.001-0.002);
> lo caro es la imagen + el output.
>
> Aparte, **moderación del Foro** (solo premium): `moderate_forum_text` (texto de posts/
> comentarios, `max_tokens=120`, centavos) y `moderate_forum_image` (Vision, solo si el post
> lleva imagen).
>
> **Costo real por análisis (tarifas GPT-4o $2.50/1M input · $10/1M output):**
> | Llamada | Input (~tok) | Output (~tok) | Costo |
> |---|---|---|---|
> | `/validate` | ~1,400 | ~150 | ~$0.005 |
> | `/analyze` | ~2,600 | ~900 | ~$0.016 |
> | **Total por análisis** | | | **≈ $0.02** |
>
> **Proyección con 500 usuarios** (mix supuesto: Free 350 · Standard 100 · Premium 50 →
> ingresos $2,500/mes con Standard $10 + Premium $30). Límites: Free 1/semana (~4.3/mes) ·
> Standard 1/24h (~30/mes) · Premium 5/24h (~150/mes):
>
> | Escenario | Free (350) | Standard (100) | Premium (50) | Costo IA total | Margen sobre $2,500 |
> |---|---|---|---|---|---|
> | **Peor caso** (100% del límite) | 1,505 análisis → $30 | 3,000 → $60 | 7,500 → $150 | **≈ $240/mes** | ~90% |
> | **Realista** (~30-40% del límite) | ~700 → $14 | ~1,200 → $24 | ~2,000 → $40 | **≈ $80/mes** (+ ~$3 moderación) | ~97% |
>
> Conclusión: con 500 usuarios, la API de OpenAI cuesta entre **~$80 y ~$240/mes** según uso real,
> contra **$2,500/mes** de ingresos → margen de IA ~90-97%. Infraestructura (VPS+dominio) es
> aparte (~$7-13/mes), no es costo de OpenAI.

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

- [ ] **Pagar OpenAI API + conectar nuestra IA + probar consumo real con $5 de "combustible"**
      — necesario para análisis de screenshots en producción. Sin esto el sitio funciona pero
      con el token gratuito de GitHub Models (limitado por rate). Plan de 3 pasos:
      1. **Crear cuenta + cargar $5** en `platform.openai.com` (modelo prepago pago-por-uso,
         NO suscripción mensual; mínimo $5). Generar una `OPENAI_API_KEY`.
      2. **Conectar nuestra IA a GPT-4o pago — solo cambian 2 líneas de CONEXIÓN en `app.py`**
         (la lógica/prompt/flujo NO se toca, es el mismo modelo `gpt-4o`):
         ```python
         # HOY:  client = OpenAI(base_url="https://models.inference.ai.azure.com", api_key=GITHUB_TOKEN)
         # PAGO: client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
         ```
         Agregar `OPENAI_API_KEY` al `environment=` del supervisor conf **y** a `scalpel/.env`,
         luego `supervisorctl restart traderacelerator`. El `SYSTEM_PROMPT` ICT, validate→analyze,
         `max_tokens` (validate=150, analyze=900) y todo lo demás queda IDÉNTICO.
      3. **Probar cuánto gasta de verdad:** hacer 5-10 análisis de screenshots reales y mirar
         (a) el dashboard `platform.openai.com/usage` — costo real $ por request — y/o
         (b) el `response.usage` de cada respuesta (tokens reales). Objetivo: confirmar el
         estimado de **~$0.02/análisis** y ver cuántos análisis salen con los $5 (~250 esperados).
      - ⚠️ **El miedo de "que me claven $1 por screenshot" es imposible por código:** `max_tokens`
        topa el output (analyze=900, validate=150) → el peor caso absoluto es ~$0.025/análisis.
        Para llegar a $1 OpenAI tendría que subir precios ×40 o habría que quitar el `max_tokens`.
      - (Opcional, pendiente de decidir con el usuario) loguear `response.usage` en el Audit Log
        para ver el costo real centavo-por-centavo desde el panel admin.
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
