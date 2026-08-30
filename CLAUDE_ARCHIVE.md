# 📦 ARCHIVO HISTÓRICO — Trader Accelerator (Scalpel)

> Snapshot del CLAUDE.md previo (historial de tareas ya completadas, detalles técnicos de
> Synapse, quiz hardcore, sesiones pasadas, análisis de costos de IA, ideas en stand-by).
> Movido aquí el 2026-06-22 para aligerar el CLAUDE.md activo y ahorrar tokens — este archivo
> NO se carga en cada mensaje. Consultar solo cuando se necesite contexto histórico.

---

# Scalpel — ICT Trade Analysis Platform
## Notas del proyecto para Claude Code

---

> **🔔🔔 MOSTRAR APENAS EL USUARIO ESCRIBA (recordatorio dejado 2026-06-22 para el día siguiente) 🔔🔔**
> Dos tareas en cola, en este orden:
>
> **#1 — FIXEAR EL APARTADO KILL ZONES (KZ) para que combine con la estética del sitio.**
> Hoy el KZ "Terminal" rompe visualmente con el resto del website. Rediseñarlo para que su
> look se parezca al **panel/listón de Mentorías** que se construyó (grafito #0e1018→#08090e +
> dorado suave #e0a83d/#f5c463, bordes con gradiente padding-box/border-box, barrido diagonal
> dorado, variante light mode). Referencia de estilo: la clase `.improve-ribbon` en
> `scalpel/templates/index.html` y el design system de `scalpel/static/improve.css`. El KZ vive
> en `scalpel/templates/index.html` (bloque "MARKET TIMING — KILL ZONE TERMINAL", clases `.kzt`,
> `.kz-row`, vars `--kzt-*`). Objetivo: armonizar colores/tipografía/bordes con la marca, NO
> reescribir la lógica del reloj/sesiones.
>
> **#2 — TERMINAR EL APARTADO DE MENTORÍAS ("Find New Ways to Improve").**
> Estado actual: páginas 1-4 hechas (`/improve`, `/improve/mindset`, `/improve/gap`,
> `/improve/inside`) + entrada vía listón dorado `.improve-ribbon` arriba de los tabs (admin-only
> por `_mentorship_gate()`, flag `MENTORSHIP_ENABLED`). FALTA:
> - **Página 5 — EL GRAN FILTRO** (`/improve/apply`): formulario de aplicación/calificación +
>   waiver educativo. (El CTA "See if it's for you" de la pág. 4 hoy cae en 404 — esta ruta aún no existe.)
> - **Página 6 — costos/disponibilidad**: 3 paquetes de llamadas (5/10/20 reuniones/mes, 30min) +
>   llamadas individuales + acceso a videos, tabla de disponibilidad, # de estudiantes, prueba social.
> - **Página 7 — área de miembros** (post-pago): biblioteca de videos (tipo YouTube, sube el trader),
>   reserva 1/1 con cupo/créditos, Q&A por video (reusar moderación IA), progreso, certificados.
> - **Reveal del mentor (foto/identidad) va AL FINAL**, después del filtro — nunca antes.
> - Más adelante: cablear Bunny Stream (video), Calendly/Cal.com (reservas), sistema de
>   cupos/créditos, pagos. Luego: i18n del funnel (hoy solo inglés).
>
> **Rama de trabajo:** `claude/gallant-volta-i7cqmf`. **Proceso supervisor del VPS:** `traderacelerator`
> (¡una sola 'c', typo viejo!). Deploy: `cd /var/www/TRADINGBOT2.0 && git pull origin
> claude/gallant-volta-i7cqmf && supervisorctl restart traderacelerator`.
>
> **💸 NOTA DE TOKENS:** el usuario nota que se le acaban rápido. La causa principal es que ESTE
> `CLAUDE.md` es enorme y se carga COMPLETO en cada mensaje. Ofrecer podarlo (archivar el historial
> ya completado en `CLAUDE_ARCHIVE.md` y dejar aquí solo lo activo) al iniciar — es el mayor ahorro.

---

> **✅ COMPLETADO (2026-06-20) — RENOMBRE DE MARCA: "Trader Acelerator" → "Trader Accelerator"**
>
> El nombre estaba MAL ESCRITO ("Acelerator" con una sola 'c'). Se corrigió a **"Trader Accelerator"**
> en TODO el sitio (401 ocurrencias, 36 archivos): landing, /app, T&C, Privacy, login/register/verify,
> pricing, checkout, certificados, Synapse, watermarks/footers de los PDFs (vía `synapse_translations.py`
> y `CERT_I18N` en `app.py`), banner animado de la landing (`W2='ACCELERATOR'`), nombre de archivo del
> PDF de certificado (`trader-accelerator-CODE.pdf`), notas internas (este CLAUDE.md + los LEGAL_REVIEW/
> CHATGPT_*.md) y scripts (monitor.py, backup_db.py, etc.). Reemplazo case-preserving
> (`acelerator/Acelerator/ACELERATOR` → `accelerator/Accelerator/ACCELERATOR`). Verificado: `py_compile`
> OK en todos los .py, `node --check` OK en auth.js, 0 ocurrencias viejas restantes.
>
> **⚠️ PENDIENTE LIGADO A ESTO — EMAIL/DOMINIO REAL EN LOS T&C:** el dominio del sitio **AÚN NO está
> definido** (no se sabe si será `.com`, `.net`, `.academy`, etc.). Por ahora el email en Privacy y T&C
> quedó como **`support@traderaccelerator.com`** (4 ocurrencias: `privacy.html:403`, `terms.html:153/810/852`).
> **Cuando el usuario compre/defina el dominio real, hay que cambiar ese email al correo REAL** (el que
> de verdad se cree, con el TLD que se escoja). Auditar de nuevo con: `git grep -in "traderaccelerator"`.

---

> **💡 EN STAND-BY (2026-06-21) — IDEA DE APARTADO NUEVO: "REPLAY LAB" (reconstrucción histórica de trades)**
> **ESENCIAL si algún día se quiere SUMAR un apartado nuevo.** Esta es la mejor idea que salió tras
> descartar MUCHAS (indicadores TradingView, journal, drills, mentor IA, Oracle/Co-Pilot/Hive, etc.).
> Cumple TODOS los requisitos del usuario: NO requiere entrenar IA por metodología (es DETERMINISTA),
> es legal-safe (educativo), distinto de todo lo existente, y de economía excelente.
>
> **NOMBRES tentativos:** Replay Lab · Trade Replay Engine · Backtest Lab (nombre irrelevante por ahora).
>
> **QUÉ ES:** el trader escribe SOLO los datos básicos de un trade (activo, fecha, hora de entrada,
> entry, exit, SL, TP, long/short, notas opcionales, y **cuánto ganó/perdió lo escribe él**) y la
> plataforma **reconstruye el gráfico REAL de ese momento histórico** (data de mercado grabada, NO
> inventada), dibuja entry/exit/SL/TP encima, y permite **cambiar de timeframe** (1m/5m/15m/1H…) y
> revisar el trade meses/años después **sin guardar screenshots a mano**.
>
> **QUÉ NO ES (límites claros del usuario):** NO datos en tiempo real · NO paper trading · NO ejecución
> de órdenes · NO copy trading · NO señales · NO asesoría financiera · NO es un journal tradicional.
> Solo **revisión histórica educativa.**
>
> **ARQUITECTURA GANADORA (clave de la economía):** NO llamar a una API por cada request. Se
> **pre-descarga y ALMACENA** la data histórica (velas 1-min) de los instrumentos, se **resamplea** a
> TFs mayores al vuelo, y cada reconstrucción es **una query a la DB** → costo marginal por usuario ≈ 0.
> - Almacén: **TimescaleDB** (extensión de PostgreSQL que ya usa producción) o tablas particionadas.
> - Render: **Lightweight Charts** (TradingView, MIT/Apache-2.0, GRATIS) — **YA está vendorizado** en
>   `index.html` (se trajo para el Hardcore Quiz). Es el motor correcto; le das OHLCV y dibuja. La
>   Charting Library avanzada NO se necesita (cuesta ~$1.500-3.000/mes white-label).
>
> **DATOS — costo y licencia (EL punto crítico, depende del activo):**
> | Activo | Fuente | Conseguir data | Licencia para MOSTRARLA |
> |---|---|---|---|
> | **Forex** (EURUSD…) | **Dukascopy** (libre, vía `dukascopy-node`) | **GRATIS** | Libre/ligera ✅ |
> | **Gold SPOT (XAUUSD)** | Dukascopy | **GRATIS** | Libre/ligera ✅ (usar SPOT, no el futuro) |
> | **NQ / MES (futuros CME)** | FirstRate (pago único ~$300-400, incl. contratos individuales) o Databento (PAYG, $125 créditos gratis) | **PAGO** | ⚠️ **Licencia CME = comodín** |
> - **El lío del $30k/año y los fees de CME es EXCLUSIVO de productos CME** (NQ, MES, Gold-FUTUROS COMEX).
>   **Forex y Gold-spot NO pasan por ahí** (mercado OTC descentralizado). Referencias CME: delayed ~$304/mes;
>   redistribución histórica pesada hasta ~$30.000/año (distribuidores grandes). El número exacto para
>   display histórico/educativo **CME no lo publica → hay que cotizarlo en marketdata@cmegroup.com.**
> - **Rollover de futuros (solo NQ/MES):** "NQ" son contratos trimestrales distintos (NQH5/NQM5/NQU5…)
>   que expiran (3er viernes mar/jun/sep/dic) y cotizan a precios distintos. Hay que cargar **el contrato
>   correcto de esa fecha** para que los precios cuadren con la entrada del trader. **Forex/Gold-spot NO
>   tienen esto** (son continuos). FirstRate ya incluye contratos individuales → resuelto.
>
> **COSTOS estimados:** MVP Forex+Gold-spot ≈ **$0** (data gratis + Lightweight Charts gratis + VPS actual).
> 100→10.000 usuarios ≈ ~$20 a ~$500/mes (solo infra/storage; la data es pre-comprada, NO escala con
> usuarios). Sumar NQ/MES = ~$300-400 una vez + licencia CME por cotizar.
>
> **COMPLEJIDAD / TAMAÑO REAL (importante — el usuario temía "cientos de miles de líneas"):**
> Es **~1.000-1.500 líneas de código nuevo**, NO cientos de miles (confundía volumen de DATOS —millones
> de filas— con volumen de CÓDIGO). Desglose: descarga ~100-150 (usa `dukascopy-node` ya hecho) ·
> tabla+inserción ~100-200 · endpoint+resampleo ~200-300 · página replay (Lightweight Charts) ~500-900.
> Dificultad: **MVP 4/10 · comercial 6/10 · avanzado 7-8/10**. El tiempo NO se va en codear (eso es rápido)
> sino en: (1) descargar/limpiar data (timezones GMT, huecos, fines de semana), (2) que la hora de entrada
> caiga en la vela correcta, y (3) **el loop de iteración con Claude porque NO ve el render** (mismo riesgo
> que hundió los indicadores — exige feedback PRECISO: error exacto + screenshot).
>
> **TIMELINE honesto:** MVP (1-2 activos, replay + marcadores + cambio de TF) = **días a ~1 semana** de
> ida y vuelta. Pulido/comercial = **~2 semanas**. NO 3+ semanas salvo snags.
>
> **PLAN POR FASES (recomendado para no arriesgar):**
> - **Fase 1 = Forex + Gold-spot** (data GRATIS de Dukascopy, CERO licencia) → construir y validar TODO
>   el motor de replay sin gastar ni arriesgar. Cubre 2 de los 4 mercados prioritarios.
> - **Fase 2 = NQ/MES** SOLO después de: (a) cotizar la licencia CME por escrito y (b) tener demanda
>   probada con Forex/Gold. Aquí entra el manejo de rollover de contratos.
> - **De-risk previo:** hacer un **"proof" mínimo de 1 sesión** (EURUSD, 1 trade, 1 TF, velas reales +
>   los 4 marcadores) para que el usuario lo VEA con sus ojos antes de comprometer 1-2 semanas.
>
> **VALUE-ADDS que lo hacen premium (vs. carpeta de screenshots / journal):** cambio de TF · "play
> forward" (ver cómo se resolvió) · dibujar/anotar sobre el chart · tags + librería filtrable · overlays
> de Kill Zones/sesiones (sinergia con lo que ya existe) · botón **"enviar al Analyzer"** (sinergia con
> la IA) · exportar el chart a imagen/PDF (reusa el generador de PDFs).
>
> **MONETIZACIÓN (modelo del usuario):** consumible con cupo → Premium incluye X reconstrucciones/slots;
> más uso o más instrumentos = pagar; Free/Standard pueden comprar acceso. Costo marginal ≈ 0 → margen altísimo.

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
>    **Trader Accelerator NO se responsabiliza** de errores/caídas de terceros. Además se agregó una
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
> `cd /var/www/TRADINGBOT2.0 && git pull origin claude/intelligent-turing-94qh5i && supervisorctl restart traderaccelerator`
>
> **NOTA DE INFRAESTRUCTURA:** esta semana el usuario sufre caídas del navegador ("OH NO" + robot)
> por conversaciones MUY largas que agotan la RAM del navegador. Solución acordada: sesiones nuevas
> y limpias + cerrar pestañas viejas. Por eso se creó esta nota: para retomar sin perder contexto.

---

> **✅ COMPLETADO (2026-06-18) — REPASO LEGAL: ELIMINAR LENGUAJE DE "ASESORÍA FINANCIERA" (PASO 1)**
>
> Decisión del usuario (validada también con ChatGPT): el sitio NO puede tener lenguaje confundible con
> asesoría financiera / recomendación de inversión / promesa de ganancia / absolutismo. Todo debe sonar
> **educativo / informativo / correctivo**. Auditoría con 5 agentes Explore en paralelo (marketing,
> auth+legal, index.html A y B, backend). Los pilares ya estaban bien (T&C, Privacidad, login/register,
> y el `SYSTEM_PROMPT` del analizador ya "blindado"); el riesgo estaba en copy de marketing/features.
> Correcciones aplicadas (rama `intelligent-turing`):
> - **Pre-Flight:** "which confluences actually pay / realmente pagan" → "performed best in your own
>   records" (4 idiomas). "The lamp tells you GO… before you click buy or sell" → "based on your own
>   checklist — a discipline aid, not a signal or recommendation". Disclaimer nuevo `pf.statsDisclaimer`
>   bajo el panel de stats (win rate/profit factor se mantienen como términos estándar PERO se aclara
>   que son del propio historial, no predicciones ni asesoría).
> - **Quiz:** "Our Certified Accelerated Traders" → "Our Quiz Masters" + sub "completed every quiz with
>   X%+ correct answers" (evita implicar credencial de trader). 4 idiomas.
> - **Certificado:** modal "Official certificate / certifies your rank" → "Rank achievement / record of
>   your learning". `certificate.html` + `CERT_I18N` (app.py): campo nuevo `eduNote` renderizado en el
>   PDF ("Educational achievement — Not a professional, financial, or trading qualification", 4 idiomas).
> - **Landing/pricing:** "Your edge, accelerated" → "Your learning, accelerated"; "Sharpen your edge.
>   Prove it." → "Sharpen your skills. Test them."; "like a senior trader" → "like an experienced
>   instructor"; "feedback infrastructure serious traders need" → "committed learners need"; "earn your
>   place" → "prove your knowledge"; "Trading alone is the hardest way to improve" → "Learning to read
>   charts alone…"; pricing hero "Sharpen every trade you take" → "Sharpen how you analyze every setup".
> - **header.sub del analizador:** reforzado a "— not verdicts, signals, or financial advice" (4 idiomas).
> - Verificado: node --check OK, Jinja OK, import app.py OK, /app render 200.
> - **DEJADO A PROPÓSITO (no es asesoría financiera):** badge "Most Popular", "serious traders" en
>   descriptores de comunidad del foro, nombres de stats estándar (ya con disclaimer), "earned a roulette
>   spin" (gamificación). Synapse PDFs ya traían disclaimer educativo.
> **⚠️ PASO 2 PENDIENTE (si el usuario lo pide):** segunda pasada fina sobre splash loading phrases,
> store_indicators/camos sales copy, settings, y un barrido de absolutismos residuales en quiz `exp`.
> **Deploy:** `git pull origin claude/intelligent-turing-94qh5i && supervisorctl restart traderaccelerator`.

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
> **Deploy:** `git pull origin claude/intelligent-turing-94qh5i && supervisorctl restart traderaccelerator`.

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
> cd /var/www/TRADINGBOT2.0 && git pull origin claude/epic-lovelace-GsOuo && supervisorctl restart traderaccelerator
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
>    desplegado al irse a dormir): `git pull` + `supervisorctl restart traderaccelerator`, luego
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
>   conf → `supervisorctl reread && update && restart traderaccelerator`. Capturaría TODA excepción
>   no controlada (dashboard en sentry.io, no en el panel admin).
>
> **6. Datos clave del VPS descubiertos/cambiados en esta sesión:**
> - La app corre con **venv**: `command=/var/www/TRADINGBOT2.0/venv/bin/gunicorn -w 4 -b 0.0.0.0:5001 scalpel.app:app`.
>   El `python3` del sistema NO tiene Flask (y pip del sistema es externally-managed; usar
>   `venv/bin/pip` o `--break-system-packages`).
> - Env vars de producción viven en `environment=` de `/etc/supervisor/conf.d/traderaccelerator.conf`
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
>    Recordar al usuario el `git pull` + `supervisorctl restart traderaccelerator` en el VPS.
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
> ║     → Objetivo: traderaccelerator.com (~$10.46 USD/año)          ║
> ║     → Usar el correo empresarial nuevo (NO el personal)         ║
> ║                                                                  ║
> ║  2. 📧 CREAR EL CORREO EMPRESARIAL (antes de comprar dominio)   ║
> ║     → Crear Gmail: traderaccelerator.hq@gmail.com                ║
> ║     → Crear Gmail: support.traderaccelerator@gmail.com           ║
> ║     → Activar verificación en 2 pasos en ambos                  ║
> ║     → Compartir contraseñas con el socio (Bitwarden/1Password)  ║
> ║                                                                  ║
> ║  3. 🔗 LINKEAR EL DOMINIO AL VPS (después de comprarlo)         ║
> ║     → En Cloudflare DNS: A record → 62.171.180.22              ║
> ║     → Configurar nginx + SSL (Let's Encrypt) en el VPS          ║
> ║     → Actualizar MAIL_USERNAME en supervisor al nuevo correo    ║
> ║     → Objetivo final: https://traderaccelerator.com              ║
> ║                                                                  ║
> ║  SIN ESTO: el sitio sigue en IP cruda, sin HTTPS, sin email     ║
> ║  empresarial, y los T&C dicen support@traderaccelerator.com      ║
> ║  que aún no existe. ¡HAZLO HOY!                                 ║
> ╚══════════════════════════════════════════════════════════════════╝
>
> Esta alerta se desactiva cuando el usuario confirme explícitamente
> que completó las 3 tareas. Hasta entonces: mostrarla 3 veces por sesión,
> SIN EXCEPCIÓN, aunque el usuario esté hablando de otro tema.

---

> **INSTRUCCIÓN PERMANENTE — DEPLOY EN VPS:**
> El sitio Trader Accelerator está desplegado en el VPS de Contabo (IP: `62.171.180.22`,
> puerto `5001`) gestionado por **supervisor**.
>
> **REGLA OBLIGATORIA:** Después de CADA push de cambios al repo, recordar siempre
> al usuario que debe ejecutar en el VPS:
> ```
> supervisorctl restart traderaccelerator
> ```
> Sin este comando, los cambios pusheados NO se reflejan en el sitio en vivo.
> El flujo completo para aplicar cambios en producción es:
> 1. `git pull origin claude/epic-lovelace-GsOuo` (en el VPS)
> 2. `supervisorctl restart traderaccelerator`
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

> **🥇 PRIORIDAD — TOKENS Y "RAMAS" DEL ANALIZADOR (leer SIEMPRE que se toque OpenAI API o**
> **construir los otros modelos/metodologías del Analizador de screenshots — 2026-06-19):**
>
> **1. 128k NO es un precio, es ESPACIO.** OpenAI cobra **por token usado**, no por la capacidad
> del contexto. Los 128k son el **techo** (cuánto CABE por petición), no algo que se paga. Analogía
> del vaso: 128k = tamaño del vaso · tokens enviados = agua que sirves · **pagas el agua, no el
> vaso**. Mandar 10k tokens cuesta lo mismo tenga el techo 8k o 128k. El tier gratis (techo 8k) no
> es "más barato" — es que **literalmente no deja** pasar de 8k (de ahí el error 413). **Resumen:
> 128k no es un precio, es espacio. Solo pagas los tokens reales de cada análisis.**
>
> **2. LAS "RAMAS" (branching por metodología) — el diseño correcto NO crece el costo por análisis:**
> La IA estará "dividida en ramas" (ICT + OTE + Wyckoff + STDV + patterns…), cada una con su lógica
> y análisis distinto según la metodología elegida. La duda del usuario: ¿crece el uso de tokens al
> agregar ramas? **Respuesta: depende de cómo se construya.**
> - **❌ Forma mala (todo junto):** meter TODAS las metodologías en UN solo prompt gigante y mandarlo
>   entero siempre → cada análisis paga por TODAS las ramas aunque use una sola. Crece feo:
>   `core 3,000 + 10 metodologías × 2,500 = ~28,000 tok/llamada` → caro e imposible en gratis.
> - **✅ Forma correcta (ROUTER — la intuición del usuario, que es la CORRECTA):** armar el prompt
>   **dinámicamente** = **núcleo ICT compartido + SOLO la rama seleccionada**. Si elige OTE → núcleo
>   + módulo OTE. Si elige Wyckoff → núcleo + módulo Wyckoff. **Nunca todas a la vez.**
>   `core 3,000 + 1 módulo 2,500 + imagen 1,500 + tesis 500 = ~7,500 tok/llamada`, y eso se mantiene
>   **casi constante** tengas 5, 20 o 50 metodologías en total.
> - **Conclusión exacta:** **NO crece por análisis** si se diseña como ramas que se cargan **una a la
>   vez**. La **biblioteca total** de metodologías puede crecer enorme, pero cada análisis solo carga
>   **[núcleo + 1 rama]** → el costo por análisis se queda plano. ("Se desvía a una rama distinta, no
>   todas a la vez" = precisamente el diseño correcto.)
>
> **3. POR QUÉ ESTO REFUERZA IR A PAGO:** justo porque habrá branching, cada rama (con su lógica
> detallada, escenarios, lectura de chart) puede ser rica y pesada **por sí sola**. En el tier gratis,
> **una sola rama + la imagen ya rompe los 8k**. Con los 128k del pago, cada rama puede ser todo lo
> detallada que se quiera sin chocar techo. Y el **núcleo compartido** (que se repite en cada llamada)
> lo agarra el **cache de OpenAI a mitad de precio** → el branching sale aún más eficiente.

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

- [ ] **💸 GASTO URGENTE — Registrar el COPYRIGHT en copyright.gov (~$135–260 una vez):**
      Es el ÚNICO paso que convierte la evidencia (git + fechas) en el **derecho real a
      demandar** por plagio de contenido. En EE.UU. **NO se puede demandar por copyright
      sin registrarlo antes** (Corte Suprema, *Fourth Estate* 2019). **Registrar ANTES de
      publicar o dentro de los 3 meses** del lanzamiento → desbloquea daños estatutarios +
      honorarios de abogado (lo que hace la demanda rentable). Registrar ~3-4 obras:
      (1) código fuente —con prompts/secretos tachados en el depósito—, (2) contenido+diseño
      del sitio, (3) PDFs/guías, (4) gráficos (opcional; el logo va por MARCA). A nombre de
      **la empresa** (no personal). **Guía completa paso a paso:** `COPYRIGHT_REGISTRATION_GUIDE.md`.
      OJO: esto es SEPARADO del registro de MARCA (nombre/logo, USPTO) que espera a decidir el nombre.
      Ya hecho dentro del sitio: cláusula "No Competing or Derivative Products" en T&C (Sección 8)
      + aviso `© 2026 ... All rights reserved` en todos los footers (commit `c0e1fb6`).

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
         luego `supervisorctl restart traderaccelerator`. El `SYSTEM_PROMPT` ICT, validate→analyze,
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
      Dominio objetivo: `traderaccelerator.com` (verificar disponibilidad al momento de comprar).
      Una vez comprado: apuntar DNS a IP del VPS `62.171.180.22` y configurar nginx + SSL
      (HTTPS gratis via Let's Encrypt) para que el sitio corra en `https://traderaccelerator.com`
      en vez de `http://62.171.180.22:5001`.
- [ ] **Migrar email de envío a cuenta dedicada** — actualmente los emails de verificación
      OTP y recuperación de contraseña salen desde el Gmail personal `mauroramirezmij@gmail.com`.
      Pasos una vez comprado el dominio:
      1. Crear Gmail dedicado (ej. `noreply.traderaccelerator@gmail.com` o configurar
         `hola@traderaccelerator.com` con Google Workspace ~$6/mes).
      2. Activar 2FA en esa cuenta → generar nuevo App Password.
      3. En el VPS actualizar `/etc/supervisor/conf.d/traderaccelerator.conf`:
         cambiar `MAIL_USERNAME` a la nueva dirección y `MAIL_APP_PASSWORD` a la nueva clave.
      4. `supervisorctl reread && supervisorctl restart traderaccelerator`
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
- [x] **Fix texto "Scalpel" → "Trader Accelerator"** en login/register — estaba en `static/auth.js` (i18n EN/ES/FR/PT), no en las plantillas.
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


---

# 📚 Movido de CLAUDE.md el 2026-09-06

Secciones de tareas YA TERMINADAS. Se archivan porque `CLAUDE.md` se
carga entero en cada mensaje y había llegado a 337 KB — el propio
archivo pide mantenerlo corto y llevábamos meses sin cumplirlo.
Nada se ha borrado: está todo aquí abajo, tal cual.

## 🟢 AYUDA CONTEXTUAL — los "(?)" por panel (PILOTO 2026-07-31)
Pedido del papá del usuario: *"la gente no adivina"*. Decisión: **(?) por panel** (no por campo) que
abre un **panel lateral deslizante**. Módulo autocontenido al final de `index.html` (patrón Tessera:
inyecta su CSS, arma su drawer, dict propio EN/ES/FR/PT, envuelve `window.applyLanguage`).
**Cablear un panel nuevo = 2 pasos:** (1) `data-help="<topic>"` en el heading, (2) el topic en
`HELP_CONTENT`. El `(?)` se inyecta solo. Cada drawer cierra con un enlace a `/guide#<seccion>` —
eso es lo que evita que esto se vuelva un TERCER manual que se desincroniza.
- **HECHO (5 paneles):** **Pre-Flight** (piloto, aprobado: *"está perfecto"*), **Analizador**,
  **Chalkboard**, **Foro** y **Quiz**. Los drawers de Pre-Flight y Foro **abren en la sección del
  sub-tab activo** (`activeSection()`; en el foro Communities→`comm`, Saved/Following→`feeds`);
  nunca hacen auto-scroll si toca la primera sección, para no tapar la introducción.
  · Quiz = **UN solo drawer con 3 secciones** (por tema / Daily / Hardcore) en vez de 3 botones
    pisándose en el mismo panel — decisión tomada con el usuario.
  · Chalkboard incluye el **aviso honesto** de que la pizarra vive en `localStorage` de ESE navegador
    y que la exportación es el guardado de verdad (mientras no exista persistencia server-side).
- ⚠️ **Dos trampas cazadas al probarlo en navegador real** (no se ven leyendo el código):
  1. **El Quiz abre en la pantalla de bienvenida**, no en el home → el `(?)` del home quedaba invisible
     justo para quien llega por primera vez. Solución: **segundo host con el MISMO topic** en la
     bienvenida (el módulo pinta un chip por cada `[data-help]`, así que dos hosts funcionan solos).
  2. Los enlaces al manual apuntaban a `#analyzer` y `#chalkboard`, que **NO existen**: los anclajes
     reales de `guide.html` son **`#analyze`** y **`#chalk`**. Al cablear un panel nuevo, verificar el
     ancla contra los `id=` de `guide.html` — un ancla muerta no da error, solo cae al tope de la página.
- ⚠️ Sin `FLASK_DEBUG` Jinja **cachea las plantillas**: tras editar `index.html` hay que reiniciar o
  la prueba en navegador mide la versión vieja (pasó: el 2º chip del quiz "no aparecía").
- **PENDIENTE:** (a) el usuario dijo que **`/guide` está muy pobre** ("síntesis de la síntesis") y hay
  que ampliarla; (b) faltan paneles por cablear (Synapse, Kill Zones, Rangos/XP, Notas, Subida);
  (c) se propuso además un **recorrido de primera vez** por apartado (una sola vez, saltable) — el
  usuario aún no lo pidió.
- ⚠️ **Trampa Jinja:** el CSS del bloque tenía `@media (...){#nxh,...}` y la secuencia **`{#` abre un
  comentario en Jinja** → `TemplateSyntaxError`. Se separa con un espacio: `{ #nxh`. Revisar `{#`,
  `{%` y `{{` en cualquier CSS/JS que se inserte en un template.

## 🔴 QR de certificados — ELIMINADOS, reemplazados por botones de compartir (2026-07-31)
**Decisión FINAL del usuario:** *"Quiero que te elimines los QR de los certificados. Simplemente
reemplaza los QR por algún botón para poder compartir el certificado en redes sociales."* → fuera
`_cert_qr_svg()`, `qr_svg`, `qr_url`, `.cert-qr` y `segno` de `requirements.txt`. **NO re-agregar QRs.**
- **En su lugar, el SELLO:** el código de verificación pasó a ser la pieza gráfica del certificado
  (`.cert-seal` = etiqueta + `cert.code` + `verify_url`), y **debajo del certificado** (solo si
  `not for_pdf`) una barra `.cert-share`: **X, Facebook, WhatsApp** (URLs de compartir directas),
  **"Más…"** (`navigator.share`, hoja del sistema) y **copiar enlace**.
- ⚠️ **Instagram y TikTok NO publican URL web de compartir** — la única vía es la hoja del sistema
  (`navigator.share`, solo móvil) con copiar-enlace de respaldo en escritorio. Eso lo explica la
  clave `cl.shareHint` (×4 idiomas), para que no parezca que faltan botones.
- Claves nuevas en `CERT_I18N`: `verifyLbl/share/shareCopy/shareCopied/shareMore/shareText/shareHint` ×4.
> **Historial (por qué se murieron):** estaban ROTOS y el usuario no pudo escanearlos. Dos bugs, y el
> gordo no era el tamaño: (1) 🔴 **el SVG de segno sale con `width`/`height` fijos y SIN `viewBox`**, y
> el certificado lo dimensionaba con `width:100%;height:100%` → **un SVG sin viewBox no remapea
> coordenadas al redimensionarse: conserva su tamaño intrínseco y se RECORTA**, perdiendo un cuadro
> localizador de esquina; (2) estaba a 58px = 1,4px por módulo cuando una cámara necesita ~3. Se
> arreglaron (viewBox + 150px + ruta corta `/v/<code>`, que baja el símbolo de v4/41 módulos a v3/37) y
> se verificó **decodificando de verdad** con OpenCV — y aun así el usuario decidió quitarlos porque no
> le daban ningún uso real. **Lecciones que se quedan:** un SVG escalado por CSS SIEMPRE necesita
> `viewBox`; y al probar QRs no basta con mirarlos, hay que decodificarlos.
> La ruta corta **`/v/<code>`** (alias de `/verify/<code>`) **SIGUE EXISTIENDO** y ahora la usan los
> botones de compartir.

**✅ La página `/verify/<code>` pasó de sosa a CREDENCIAL PÚBLICA (2026-07-31).** Razón: cada
certificado compartido trae tráfico externo y antes aterrizaba en una página en blanco. Ahora lleva:
tira de 8 pips con el rango alcanzado, bloque **"qué costó este rango"** (XP real, derivado de
`RANK_THRESHOLDS`, nunca escrito a mano), botón **copiar enlace**, botón **añadir a LinkedIn**
(`startTask=CERTIFICATION_NAME`, rellena el perfil del alumno), CTA "consigue el tuyo", y una línea
legal explícita (**logro educativo, NO título profesional ni licencia**). Claves nuevas en
`VERIFY_I18N` ×4 idiomas. ⚠️ **Trampa Jinja:** una clave llamada `copy` colisiona con `dict.copy` y
`{{ vl.copy }}` renderiza el método → renombrada a `copyLink`; hay un guard que revisa colisiones.
**Tarjeta social:** `/verify/<code>/og.png` genera con Pillow una imagen 1200×630 (nombre, rango,
tira de pips, color del rango) + meta OG/Twitter → al pegar el enlace en WhatsApp/LinkedIn/X sale
tarjeta rica en vez de un enlace pelado.

## 🟢 SOCIALS `/socials` — redes oficiales + próximo sorteo (2026-07-31)
**Contexto:** se evaluaron y DESCARTARON un plan de referidos (más descuentos = choca con el acuerdo
comercial) y un **sistema de sorteos automático** — el usuario lo rechazó explícitamente por carga
operativa para una sola persona: *"Prefiero yo hacerlo a mano cuando salga con el instagram"*. Lo que
sí se construyó es el **escaparate**: una página donde viven las cuentas oficiales y un tablero de
"próximo sorteo" **que el dueño llena a mano desde /admin**.
- ⚠️ **Se llamaba `/community` y se RENOMBRÓ a `/socials`** (pedido del usuario): chocaba con la
  pestaña **Communities** del foro. Dos cosas con el mismo nombre en un mismo producto confunden.
  Las claves i18n siguen siendo `comm.*` (internas); lo que cambió son las etiquetas visibles:
  Socials / Redes oficiales / Réseaux officiels / Redes oficiais.
- **`/socials`** (`socials.html`): hero + tablero del sorteo (card oscura con acento dorado,
  **cuenta regresiva en vivo**, expander "Cómo participar" con los pasos, línea legal, bloque de
  ganador) + cards de las cuentas oficiales con SVGs de marca inline.
- **Modelo `Giveaway`** (title, prize, ends_at, how_to, link, winner, active) + `_current_giveaway()`.
  **Pestaña "🎁 Giveaway" en `/admin`** con el formulario → `POST /admin/giveaway`. Sin sorteo activo
  la página se sirve igual, solo sin tablero.
- **`SOCIAL_LINKS`** sale de env vars (patrón condicional de siempre): **una cuenta sin variable
  simplemente no se pinta**, así que la página ya funciona hoy con las redes que todavía no existen.
- i18n: **20 claves `comm.*` ×4 idiomas** en `pages_i18n.js` (paridad verificada).
- Verificado en navegador real con datos sembrados: cuenta regresiva viva, 4 cards, título ES,
  pasos que despliegan, **sin desbordamiento horizontal en móvil**, 0 errores de JS.
- ✅ **YA ENLAZADA** (el usuario pidió que fuera visible aunque no haya sorteos ni cuentas todavía):
  menú **Products** (clave `products.socials` ×4) + **footer de la landing**. Los estados vacíos
  están cubiertos, así que la página nunca se ve rota: sin cuentas creadas el aviso del sorteo usa
  `comm.gwNoneSoon` en vez de `comm.gwNone` (que mandaba a "seguir las cuentas de abajo" cuando
  abajo no había ninguna). 21 claves `comm.*` ×4 a paridad.
- **PENDIENTE:** crear las cuentas y setear sus env vars (ver "Redes sociales" en tareas pendientes).

## 🎡 RULETA → COSMÉTICOS + TEMPORADAS (decidido 2026-08-02, EN CONSTRUCCIÓN)
**Decisión de fondo:** la ruleta deja de repartir DESCUENTOS (costaban ~$7.38/giro, eran premios
muertos para clientes atados al 20% del socio, y el mes gratis le robaba $12 de comisión al
influencer) y pasa a repartir **cosméticos**. Principio rector: *los camos son cómo TÚ ves el
sitio; marcos y cursores son cómo TE VEN los demás* (foro/tabla/panel).
**Decisiones CERRADAS con el usuario (no reabrir):**
- **Tanda mensual de ruleta = 2 marcos + 3 cursores + 1 camo** (camo CON botarga — el usuario
  asume producir 12/año). Rotación MENSUAL: lo no ganado **se pierde para siempre** y queda en la
  tienda en gris "temporada terminada — <mes año>". Piezas jamás cruzan de canal (ruleta ≠ tienda
  ≠ campeón); **nada se revoca nunca**.
- **Regla B de probabilidades:** el camo corre APARTE con su 5% fijo en cada giro (nunca engorda);
  marcos/cursores se reparten lo restante SIN repetidos; un giro nunca sale vacío; tanda limpiada
  → el giro se guarda (spins se acumulan, ya funciona así). Simulado: mes perfecto (4 giros) =
  18.5% de sacar el camo. Script `scratchpad/ruleta_prob.py`.
- **Ranking mensual:** más aciertos gana; empate → MENOR suma de segundos de las correctas
  (criterio del usuario, ej. Juan vs Gabriel). Tabla = top 20 + tu propia fila siempre. Nombres
  públicos. El #1 del mes gana un **marco de campeón** único e irrepetible (solo el #1, sin podio).
- **Racha** (estilo killstreak): correctas seguidas hasta fallar O saltarse un día; NO se reinicia
  por mes. **Salón de la fama** = mejores rachas históricas; el top 3 lleva el **nombre encendido**
  (único cosmético que SE PIERDE si te superan; efectos distintos, #1 el mejor). Chip `🔥 N` en el
  foro desde racha ≥2.
- **Armonía con rangos (condición del usuario):** rango = texto+metal (medalla+pastilla, dorado
  SOLO rangos 7-8); marco = forma+material, SIN texto, SIN paleta de rangos (excepción: marco del
  campeón puede competir con el dorado). En el foro el marco es ESTÁTICO (solo la medalla se
  anima); la animación del marco vive en tabla/panel a 72-96px. Avatar del foro sube a ~40px.
- **Tienda → "cosméticos"** (`/camos` redirige, columnas DB no se renombran): 4 estados de card
  (comprable / lo tienes / solo-ruleta con bio / temporada terminada). **Precios: $4.99 camo común,
  $7.99 de temporada, $1.99 cursor** (repricing aprobado; hoy no hay clientes = sin migración).
  **Carrito multi-ítem SÍ** (una sola comisión PayPal), compra individual se mantiene, **packs NO**
  (rechazados: abaratan la percepción). Cursores: 32×32, flecha+manito (2 archivos), sin animar,
  solo desktop; unos de ruleta y otros de tienda, jamás cruzan.
- **Descartados:** XP en ruleta, títulos por hazaña ("Liquidity Hunter, Roulette Pro Max" = choque
  con rangos), sello del certificado, escudo de racha, análisis extra, nombres con efecto como
  premio (quedan SOLO para el salón de la fama).
**Plan (ir de a uno):** (2) ✅ **panel temporada (2026-08-02):** botón 🏆 en el daily card → modal
`#daily-lb-overlay` (mis números / tabla del mes top-20+mi-fila-siempre con ⋯ de salto / salón de
la fama top-10) + API `/api/daily/leaderboard` (premium; mes = `_month_ranking` sobre el log,
desempate segundos ASC solo-correctas) + `DailyQuizState.best_streak_at` (empate de fama = quien
llegó PRIMERO; sin backfill, fecha desconocida pierde) + foro: `serialize_post/comment` llevan
`author_streak` (chip 🔥N desde racha ≥2, `_live_streak` aplica la regla del día saltado) y
`author_fame` (top-3 `_fame_top` cacheado 60s → `.fame-name.f1/f2/f3`, paleta FUEGO no dorada,
f1 animado con reduced-motion off). 17 claves `daily.lb.*` ×4. Verificado en navegador real
(EN claro + ES oscuro + foro): empate 19-19 resuelto por tiempo, fila propia fuera del top,
0 errores JS. ⚠️ Trampa: el botón vive en quiz-HOME y el quiz abre en la BIENVENIDA — para
probar hay que clickear un intent primero. (1) ✅ **registro de respuestas con tiempo** — `DailyAnswerLog` (fila
única user+día: correct/timed_out/seconds server-side/streak_after) escrito en `/api/daily/answer`,
+ `DailyQuizState.best_streak` (migración `_migrate_daily_best_streak_column`, backfill=streak
actual; `tools/test_boot_migracion.py` ahora cubre columnas de otras tablas, 6/6). E2E 17/17
(`scratchpad/test_daily_log.py`): unicidad diaria, timeout registrado, best_streak sobrevive al
fallo, consulta del ranking con desempate. **Va ANTES de abrir la temporada 1 — sin esto no hay
desempate reconstruible.** (2) panel racha + tabla mes + salón de la fama; (3) ✅ **ruleta → cosméticos (2026-08-02):** fuera
`ROULETTE_PRIZES`/descuentos/mes-gratis (los códigos SPIN viejos siguen válidos — nada se revoca;
`cpEmpty` y `unlock.f.daily.d` reescritos ×4). Modelos nuevos `CosmeticItem` (slug/kind/channel/
season 'YYYY-MM'/active — canal = muro duro ruleta≠tienda≠campeón) y `UserCosmetic` (ledger
append-only, unique user+item); tablas nuevas via create_all, sin ALTER. Motor: `_roulette_tanda()`
+ `/api/daily/tanda` (piezas del mes + owned + `next_tanda`) + `/api/daily/spin` reescrito con
Regla B (`ROULETTE_CAMO_ODDS=0.05`, `ROULETTE_KIND_WEIGHTS` frame 15/cursor 21.667; sin tanda →
409 `no_tanda` SIN quemar giro; tanda limpiada → 409 `tanda_cleared` SIN quemar giro; nunca vacío).
Cliente: modal muestra la RUEDA solo si hay tanda; si no, anuncio `#roulette-notanda` (fecha
próxima tanda + giros guardados, 7 claves `daily.tanda.*` ×4). E2E 20/20
(`scratchpad/test_tanda.py`): 6 giros sin repetidos, pieza de tienda jamás sale, Regla B medida
(4.7% 1er giro / 18.6% mes perfecto), cupón viejo sigue activo. Verificado en navegador (ES).
**La tanda se publica insertando `CosmeticItem` channel='roulette' season='YYYY-MM' — todavía no
hay piezas: la rueda anuncia hasta el paso 5.** (4) ✅ **tienda de cosméticos (2026-08-02):** `/camos`→301→`/cosmetics`
(la función de ruta sigue llamándose `camos` → todos los url_for siguen; enlaces de menú
Products/Tessera/teleport actualizados). **Repricing aplicado: $4.99 común / $7.99 temporada /
$1.99 cursor** (`CAMO_PRICE_THEME/SEASONAL`, `COSMETIC_PRICE_CURSOR`). Página renombrada ×4 +
secciones nuevas Marcos/Cursores server-rendered desde `CosmeticItem` con los **4 estados de
card** (comprable/$ · Tuyo · Solo-ruleta-este-mes · Temporada terminada—YYYY-MM en gris; +
estado campeón); vacías muestran aviso honesto de la Temporada 1. **Carrito multi-ítem:**
`CosmeticOrder` (slugs CSV + total server-side, espejo de CamoOrder → helpers PayPal comunes),
`POST /api/cosmetics/checkout` (valida no-plan/no-poseído/dedupe ANTES de cobrar; sin claves →
503 soon), return `/cosmetics/paypal/return/<id>`, webhook despacha `cosm-<id>`, sweep de /admin
cubre carritos, `_activate_cosmetics_from_order` (idempotente, enciende UNO solo si no hay activo,
jamás pisa el elegido). Compra individual intacta (`/api/camo/buy`). Packs NO (decisión). Cliente:
botón "Añadir al carrito" + barra `#cart-bar` (sessionStorage `nx_cosm_cart`, "un solo pago, una
sola comisión"). 18 claves `camos.*` nuevas/renombradas ×4 (paridad OK). E2E 25/25
(`scratchpad/test_carrito.py`) + navegador ES real (carrito $9.98, toast soon, 4 estados
pintados). ⚠️ Al probar la tienda como ADMIN no hay botones de compra: el admin posee TODO.
**PENDIENTE del paso 4:** precio de los marcos de tienda (el usuario aún no lo fijó — hoy ningún
`CosmeticItem` de tienda es frame, solo cursores a $1.99).** (5) 🟡 **EN CURSO — primeras piezas**
(colchón de 3 meses de tandas ANTES de encender la rotación — compromiso operativo: 6 piezas nuevas
cada mes, si un mes no hay tanda el sistema se ve muerto).
· **Marcos = PLACA del bloque de autor del foro** (avatar+medalla+nombre+chip+pastilla), NO un anillo
  alrededor del avatar (*"nadie pagará un dólar por decorar el borde de un círculo"*). Catálogo de
  **36 placas en `tools/plates_preview.py`**, lienzo real **640×48**. Reglas aprendidas a los golpes:
  la escena ocupa TODO el ancho (un motivo en la esquina se ve como sticker), los fondos NO son todos
  oscuros (cada placa declara el `ink` de su texto) y el **tercio izquierdo va tranquilo** porque ahí
  caen el avatar y el nombre. Reparto: **13 a la ruleta** (12 libres + Chronicles), 23 a la tienda,
  los 2 festivos con ventana de 24h el día de la festividad.
· **Las 12 temáticas mensuales están CERRADAS** con su calendario (constante `TEMPORADAS` en el mismo
  archivo). **Temporada 1 = AGOSTO 2026** (el dueño abre la plataforma esta semana o la siguiente):
  2026-08 Chronicles · 09 American Football · 10 Nile · 11 Colosseum · 12 Summit · 2027-01 Bengal ·
  02 Olympus · 03 Quetzalcóatl · 04 Baseball · 05 Apiarist · 06 Welder · 07 Zeppelin.
  Sep y Oct son a propósito las botargas más baratas (ahí se arma el colchón de 3 meses); de Nov en
  adelante alterna caro/barato, ningún mes repite la paleta del anterior, y la estación manda donde
  existe (NFL en septiembre, alpinismo en diciembre, Quetzalcóatl en el equinoccio de marzo, béisbol
  en el opening day de abril, floración del apicultor en mayo). Criterio del dueño para las
  temáticas: **poco transitadas** (nada de piratas, ninjas, vaqueros, astronautas, safaris) y
  **cerrado el cupo de deportes y de oficios**.
· 🔴 **RODADA DE TEMPORADAS (2026-08-22, decisión del dueño — el calendario de arriba ya NO es el
  vigente).** El sitio abrió sin clientes y no tenía sentido quemar la tanda de agosto ante una sala
  vacía: **Chronicles corre agosto Y septiembre**, lo de septiembre pasa a octubre, etc., y
  **Quetzalcóatl SALE** (rodado caía en abril, lejos de su equinoccio) — con lo que **de 2027-04 en
  adelante cada lote vuelve a su mes original** (béisbol en el opening day, apicultor en la
  floración). 🔑 **La base NO se re-estampa**: las filas de `CosmeticItem` conservan su sello (el
  "lote") y el dict **`RULETA_RODADA`** en app.py traduce mes real → lote vivo; para volver a rodar
  el calendario se edita SOLO ese dict. Los calendarios `ROULETTE_*_CALENDAR` quedan como catálogos
  de lotes — no editarles las fechas. El lote de quetzal (frame `quetzal` + libre `volcano` +
  cursores `cur-quetzal`/`key`/`umbrella`) sigue en la base pero sin mes: invisible en ruleta Y
  tienda; su arte libre queda para una temporada 2. `tools/test_rodada.py` **22/22** (tanda EXACTA
  por mes —igualdad de conjuntos, no "contiene"—, quetzal en 0 de 13 meses, tienda con
  estados/etiquetas por mes, 12 spins reales solo entregan el lote vivo). ⚠️ El spin responde
  PLANO (`slug` en la raíz, no `prize.slug`), y el mes se simula parcheando `A._current_season`.
· 🔴 **División de trabajo del arte:** lo procedimental (paisajes, lava, rejillas, vitrales, montañas,
  terminales) se dibuja acá; **las criaturas y personajes NO** — el dragón de Chronicles se intentó 4
  veces y el usuario lo cortó (*"es como si te hubiese enviado una foto de un iPhone y tú me hubieses
  devuelto un tronco de madera"*). El tigre de Bengal, como el dragón, vive en la **botarga** (la
  encarga el usuario); el marco es solo el bosque de bambú de noche con las brasas.
· **Deportes y legalidad** (respondido al usuario): un deporte no se registra; lo protegido son las
  MARCAS (nombres/escudos de equipos, logos NFL/MLB, "Super Bowl") y la imagen de jugadores reales.
  Botarga genérica = sin problema. Instrucción al ilustrador: cero logos, cero nombres de equipo,
  cero parecidos a un jugador identificable.
· ✅ **Las 12 placas temáticas DIBUJADAS y aprobadas (2026-08-02)** — el usuario solo pidió un fix:
  la pirámide de Quetzalcóatl tenía la "sombra del equinoccio" en un costado y parecía derruida →
  alfardas simétricas. **Y LA RULETA QUEDÓ CABLEADA DE VERDAD (mismo día):**
  `tools/build_plates.py` publica el catálogo como `scalpel/static/plates/<slug>.svg` + `plates.json`
  ({slug:{name,ink}}) — regenerar y commitear tras CUALQUIER cambio en `plates_preview.py`;
  `ROULETTE_FRAME_CALENDAR` en app.py (24 marcos = temático+libre por mes, pareja con contraste
  claro/oscuro) + `_publish_roulette_frames()` idempotente en `init_db()`; la tienda **oculta
  temporadas futuras** (no spoilear) y muestra el arte real como tira + botón Ponértelo/Quitártelo;
  columnas `User.active_frame`/`active_cursor` (migración `_migrate_user_cosmetic_wear_columns()`,
  `test_boot_migracion.py` 6/6); `POST /api/cosmetics/equip` (kind=frame; cursor da 400 hasta que
  exista su lado cliente; admin viste todo); `serialize_post/comment` llevan `author_frame`
  {slug,ink} gratis (el User ya viene cargado) y el foro pinta la placa detrás del bloque del autor
  (`mountPlate()`, CSS `.fplate-host`/`.fink-light|dark`, ESTÁTICA — solo la medalla se anima);
  al ganar un marco el modal muestra la placa + "Usarlo ahora". E2E 27/27
  (`scratchpad/test_marcos.py`) + navegador real (feed, comentario, tienda; 0 errores JS).
  ⚠️ El "2 min" del comentario era invisible sobre placa oscura → tinta con text-shadow ×2 modos.
· ✅ **19 marcos de TIENDA dibujados (2026-08-02, pendientes de aprobación del usuario):**
  **7 festivos** espejo de los camos festivos (santa/hallow/fourth/lucky/valentine/easter/newyear;
  con frost y muertos ya son 9) — regla: compra SOLO en ventana de 24h en la fecha estipulada
  (newyear 01-01 · valentine 02-14 · lucky 03-17 · easter móvil, la fija el dueño · fourth 07-04 ·
  hallow 10-31 · muertos 11-02 · frost 12-21 · santa 12-25; anotado en `FESTIVOS`); y **12 libres**
  con temáticas deliberadamente LEJOS de los camos comunes y de las 12 temporadas (gambit/ajedrez,
  beacon/faro, vineyard, archive/biblioteca, clockwork, windmill/tulipanes, fireflies, harvest,
  cascade, bazaar, salar, express/tren nocturno). El usuario asumió la coincidencia mars↔Mission y
  arcade↔camo arcade ("se deja así"). Catálogo total: 66 placas.
· ✅ **MARCOS DE TIENDA CABLEADOS (2026-08-02).** Arte aprobado y **precios fijados por el usuario:
  $2.99 libre / $3.99 festivo** (`FRAME_PRICE_COMMON`/`FRAME_PRICE_FESTIVE`). `_publish_store_frames()`
  en `init_db()` publica los 21 (9 festivos + 12 libres) como `CosmeticItem` channel='store',
  season=NULL (no rotan); idempotente por slug, jamás pisa una fila existente.
  🔴 **BUG DE FONDO CAZADO AL CABLEAR — los slugs CHOCAN:** el camo `santa` y el marco `santa` son
  la misma cadena, y el carrito guardaba slugs pelados → un carrito con ambos cobraba y entregaba
  mal. Arreglado con **referencias con prefijo** `camo:<slug>` / `item:<slug>`
  (`parse_cosmetic_ref`/`resolve_cosmetic_ref`); **un slug pelado se sigue leyendo como camo**, así
  los carritos en sessionStorage y los pedidos pendientes de antes del cambio siguen funcionando.
  `S.prices` pasó a estar keyeado por referencia (con slugs pelados el total salía mal).
  `_activate_cosmetics_from_order` reparte camos por `add_camo` y marcos/cursores por `UserCosmetic`,
  y se pone UNO solo si no hay nada puesto. Compra individual de marco = carrito de 1 (mismo riel
  PayPal, no se duplicó plumbing). Cursores: la sección ya quedó con los mismos botones para cuando
  existan. E2E `scratchpad/test_tienda.py` **38/38** + navegador ES (carrito mixto $10.97 = 2 marcos
  + 1 camo, 0 errores JS).
· ✅ **VENTANA DE 24h — CERRADA Y CABLEADA (2026-08-02, fechas y zona confirmadas por el usuario).**
  `FESTIVE_WINDOWS` **keyea por FESTIVIDAD, no por producto** (respuesta a su pregunta: el candado va
  por el nombre de la festividad, así el camo, el marco y el cursor de esa fecha comparten ventana y
  **una pieza que aún no existe hereda la regla el día que se cree**). Fechas: newyear 01-01 ·
  valentine 02-14 · lucky 03-17 · easter (calculada) · fourth 07-04 · hallow 10-31 · muertos 11-02 ·
  frost 12-21 · **santa 12-25**. Pascua se **calcula** (algoritmo gregoriano anónimo; verificado
  2026→5-abr, 2027→28-mar, 2028→16-abr, 2029→1-abr) con `EASTER_OVERRIDE` por si quiere pinchar un año.
  🕛 **La medianoche es la de VENEZUELA** (`FESTIVE_TZ = UTC-4` fijo, `FESTIVE_WINDOW_HOURS=24`).
  Se eligió Caracas y NO Nueva York porque **Venezuela no tiene horario de verano** (UTC-4 todo el
  año) mientras NY oscila −5/−4 y solo coinciden en verano: con offset fijo toda festividad abre a la
  misma hora real siempre, y no hace falta tzdata en el VPS.
  **La ventana busca siempre la PRÓXIMA ocurrencia**, así que desde el 2-ago-2026 el 4 de julio
  apunta a 2027 (el de 2026 ya pasó) y Halloween a 2026 — y cada año se repite sola sin tocar código.
  Se aplica a **marcos Y camos**: estado `locked` en la tarjeta con la fecha + tooltip de la zona
  horaria ×4 idiomas, y rechazo server-side en `/api/camo/buy` y en el checkout del carrito
  (`window_closed`) para que no se pueda saltar llamando al endpoint.
  `tools/test_ventanas_festivas.py` **26/26** (calendario exacto, bordes de la ventana en VET, salto
  de año, Pascua ×4 años) + prueba de viaje en el tiempo del cobro real 7/7.
  ⚠️ **Trampa cazada:** `data-i18n-title` **está reservado para el `<title>` del documento** en
  `pages_i18n.js` (usa `querySelector`, el primero gana) → para tooltips se agregó `data-i18n-tip`.
· ✅ **TIENDA — 3 ESTANTES + PREVIEW (2026-08-02).** Los marcos se separan por **CÓMO se consiguen**
  (no por estado): "Siempre disponibles" (12 libres) · "Festivos" (9, ventana de 24h) · "Solo por
  ruleta" (los 24 del calendario, jamás a la venta). ⚠️ El agrupador va por **canal**, no por estado:
  un marco de ruleta ya ganado se lee `owned` y con `state` habría caído en el estante de comprables.
  **Preview** = un botón 👁 en cada tarjeta que abre una **fila de foro simulada** con la placa detrás
  (avatar+medalla+nombre+chip+pastilla), armada desde el `art` + `ink` que el server manda en cada
  pieza → **cualquier marco futuro trae su preview gratis**, sin dibujar nada por pieza. Todo se pinta
  con un macro Jinja `frame_card()`, así los 2 marcos que entran cada mes heredan tarjeta, estados,
  estante y preview solos (probado viajando a septiembre: 7/7). 9 claves nuevas ×4 idiomas.
  ⚠️ **Trampa:** meter `JSON.stringify(url)` dentro de `style="background-image:url(...)"` parte el
  atributo (comilla doble dentro de comilla doble) y la placa sale en blanco → la URL se asigna por
  **propiedad** (`el.style.backgroundImage`), nunca por string de HTML.
· ✅ **CURSORES — DIBUJADOS Y CABLEADOS END-TO-END (2026-08-02, aprobados por el usuario).**
  **Son FIGURAS, no la flecha recoloreada** (decisión del usuario tras rechazar 2 enfoques; el
  criterio ganador: figura MACIZA, color plano, contorno grueso 1.8, objeto SIMPLE — media derrota
  fue elegir objetos de 4 piezas que no caben en 32px). Catálogo de **55** en
  `tools/cursors_preview.py`: 12 temáticos (uno por camo mensual: escudo/balón/pirámide/casco/bota/
  huella/ánfora/disco solar/pelota/tarro miel/careta/dirigible) + 24 libres de ruleta + 9 festivos +
  10 comunes de tienda. Cada cursor = 2 estados: normal y **_hot** (la misma figura encendida, para
  lo clickeable); estado activo = cuerpo + extra (CHISPAS por defecto). Hotspot fijo (2,2).
  **Publicación:** `tools/build_cursors.py` rasteriza (Chromium 128px→LANCZOS→32px, fondo
  transparente) a `scalpel/static/cursors/cur-<slug>[_hot].png` + `cursors.json` — regenerar y
  commitear tras cambiar el catálogo. **Chrome solo acepta PNG en `cursor:url()`** (SVG no).
  🔑 **Slug con prefijo `cur-`**: `CosmeticItem.slug` es único y los cursores comparten nombre con
  marcos/camos (chronicles, santa…) → `festivity_of()` quita el prefijo, y así el cursor festivo
  **hereda EXACTAMENTE la misma ventana de 24h (VET)** que su par camo y marco.
  **Ruleta:** `ROULETTE_CURSOR_CALENDAR` = 3/mes (1 temático con la MISMA season que su marco/camo
  + 2 libres barajados sin repetirse en el año; agosto = cur-chronicles + cur-candle + cur-rocket).
  `_publish_cursors()` idempotente en `init_db()`. Probabilidades: las de siempre (Regla B, cursor
  pesa 21.667 vs marco 15 → con tanda completa 2+3+1: camo 5%, marcos 30%, cursores 65%). El modal
  de premio muestra la figura + "Usarlo ahora".
  **Tienda:** $1.99 común / **$2.99 festivo** (`CURSOR_PRICE_FESTIVE`), mismos 3 estantes que
  marcos, carrito multi-rama (`item:cur-*` — probado carrito camo+marco+cursor), preview propio
  (2 estados zoom + tamaño real en chip claro/oscuro), candado festivo con fecha+zona.
  **Equipar/aplicar:** `/api/cosmetics/equip` kind=cursor → `User.active_cursor`; `/app` inyecta
  CSS `@media (pointer:fine)` (solo escritorio): figura en todo, `_hot` sobre clickeables, I-beam
  intacto en campos de texto. ⚠️ **`!important` obligatorio**: las reglas de clase del sitio
  (`.tab-btn{cursor:pointer}`) le ganan a selectores de elemento. ⚠️ `/app` exige el cookie
  `scalpel_splash_ts` (302 a /welcome sin él — pega en tests). E2E `scratchpad/test_cursores.py`
  **44/44** + regresión completa verde + navegador real (body/botón/textarea con los 3 cursores
  correctos, tienda y preview sin errores JS).
· ✅ **CAMO CHRONICLES — la 6ª pieza, y la tanda de agosto quedó COMPLETA (2026-08-02).**
  🔴 **Agujero real cazado al cablearlo:** ganar un camo en la ruleta solo escribía `UserCosmetic`,
  pero el motor de temas lee `User.owned_camos` (`owns_camo()` gatea `/api/camo/activate`) → el
  premio no habría pintado NADA. `daily_spin` ahora hace de puente (`add_camo` + se enciende solo
  si no hay otro camo activo, misma regla que `_activate_cosmetics_from_order`).
  **Arte — DOS correcciones del dueño, en este orden:** (1) *"Chronicles no se trata de volcanes,
  se trata de MEDIEVAL; lo que tiene que predominar de fondo es una especie de Reino"* → se tiraron
  dos escenas volcánicas (capas de montañas y llanura de basalto agrietado) y quedó un **reino
  amurallado**: almenas de borde a borde, puerta iluminada, torres de techo cónico con estandartes,
  torre del homenaje, aguja de catedral, caserío y ventanas encendidas; la lava sobrevive como
  cielo/horizonte + un volcán chico al fondo. (2) *"para light mode… un reino rodeado de colinas de
  montañas, un sol, cielo azul y despejado"* → **DOS looks** (patrón Pole/Mission/Standard): 🌙 la
  ciudad de noche, ☀️ el MISMO reino de día (sol, nubes, sierra nevada, colinas verdes, piedra
  clara, tejas de terracota, arboleda, camino a la puerta). Por eso **NO es DARK_ALWAYS** — el
  toggle elige escena. Generador reproducible: **`tools/build_chronicles_camo.py`** (una geometría,
  dos paletas en `PALETTE`; re-correrlo reinserta el bloque en `index.html`, es idempotente).
  **Cableado:** publicado como **`camo-chronicles`** — `CosmeticItem.slug` es único y el MARCO
  homónimo ya ocupaba el slug pelado (mismo motivo que `cur-`); el prefijo **nunca sale del
  ledger** (`camo_slug_of()`; `/api/daily/tanda` y `/api/daily/spin` sirven el pelado o la rueda no
  acierta el sector). `_publish_roulette_camos()` publica **solo el camo cuyo tema YA existe**
  (`CAMO_READY`) — un premio sin CSS no entrega nada y la ruleta no sabe devolver. `ROULETTE_CAMOS`
  + `camo_store_price()` → **jamás tiene precio** (muro de canal; `/api/camo/buy` también lo
  rechaza). Estante propio **"Camos de ruleta"** en `/cosmetics` (server-rendered, `data-wheel="1"`
  → `renderCard` devuelve temprano y respeta el pie del server; `slugOf()` ahora lee `data-slug`,
  así **un camo de otro mes no necesita tocar `CM2SLUG`**), ⇆ en la tarjeta y en el lightbox
  (`PREV_ALT`), y rama de camo en el modal del premio con "Usarlo ahora".
  E2E `scratchpad/test_camo_chronicles.py` **42/42** + regresión verde (marcos 32, cursores 45,
  tienda 38, ventanas 26, boot 6/6) + navegador real (claro y oscuro, tienda en ES, 0 errores JS).
  ⚠️ La **botarga del dragón la encarga el usuario** — mientras no exista, Chronicles usa el
  muñeco-flecha por defecto (igual que arrancó `standard`).
· ✅ **CAMO AMERICAN FOOTBALL (`gridiron`, mes real octubre) — HECHO (2026-08-22).** NOCHE DE
  PARTIDO, un solo look **DARK_ALWAYS** (como premium: el slug va en LAS DOS copias de la lista de
  index.html). Escena procedimental (`tools/build_gridiron_camo.py`, idempotente): gradería en
  sombra con el público como puntitos, dos torres de luz con halo, postes amarillos a la
  IZQUIERDA (la placa los lleva a la derecha — sin espejo), césped con bandas de corte, líneas de
  yarda, hash marks y números 10/50/10 **TRAZADOS con paths, no <text>** (un SVG de background no
  hereda fuentes); balón de cuero con cordón en la esquina inf-der. Acento = amarillo de postes.
  Muro de canal: `ROULETTE_CAMOS` ya lleva 'gridiron' (sin él la tienda le pintaba tarjeta de
  VENTA — cazado por test). Piel `camo_skin_gridiron.jpg` generada DETERMINISTA (div normal con el
  mismo background, nada de capturar pseudo-elementos). `test_rodada` 23/23 (oct = 6 piezas con
  camo; sept sin TARJETA de gridiron — el slug sí sale en `window.CAMO_STATE.ready`, que es una
  lista de datos, no una tarjeta).
· ✅ **CAMO NILE (mes real noviembre) — HECHO (2026-08-22).** El Egipto del río, **DOS looks**
  (patrón Chronicles, NO DARK_ALWAYS): ☀️ desierto a pleno sol (pirámides con cara iluminada/en
  sombra, obelisco, palmeras, papiros, el Nilo en lapislázuli) · 🌙 la MISMA geometría de noche
  (luna con mordisco, estrellas de 4 puntas con rechazo de distancia — regla Mission —, reflejo
  lunar roto en trazos sobre el agua). Adorno de esquina: la FALUCA (vela latina) navegando el
  río. Generador `tools/build_nile_camo.py` (una geometría, dos paletas, idempotente). Acento día
  = lapislázuli del río; acento noche = oro. Piel determinista `camo_skin_nile.jpg`.
  `test_rodada` 23/23 (noviembre = 6 piezas con camo-nile).
· ✅ **LAS 6 BOTARGAS DE gridiron Y nile, RECORTADAS Y CABLEADAS (2026-08-22).** Entregadas por el
  dueño. gridiron: jugador con balón / patada entre los postes / petardo que le explota. nile:
  faraón con nemes / la V en la cumbre de la pirámide / la caída al río entre templos.
  🔴 **Llegaron con el CUADRICULADO de transparencia HORNEADO en el píxel** (el generador exporta
  la vista de su visor): cuadros de 29 px alternando gris 213 y blanco 253, en RGB y sin alfa. Las
  de bienvenida sí venían con blanco plano. Herramienta nueva **`tools/limpia_botarga_nueva.py`**
  (`mirar` numera las bolsas cerradas, `cortar` inunda desde el borde; **jamás borra bolsas
  encerradas sola** — la lección de julio sigue en pie: aquí los blancos legítimos eran ojos,
  dientes, guantes, botas, el "88" de la camiseta y la espuma del río).
  ⚠️ **Tres cosas que solo se vieron MIRANDO la lámina sobre magenta, no leyendo el código:**
  1. **La sombra del suelo NO se borra, se reconstruye.** Llega pintada semitransparente ENCIMA
     del tablero: quitarla deja la botarga flotando (las del sitio la llevan, mírese
     `logo3_naval`), dejarla tal cual enseña los cuadros grises dentro de la elipse. Se resuelve
     con la regla de multiplicar — un gris G sobre blanco **es** tinta negra al alfa `255-G`.
  2. 🔴 **Quitar el tablero por GEOMETRÍA no funciona.** La lámina viene reescalada: los cuadros
     miden "29 px de media" y la rejilla se desfasa a lo ancho, así que la mejor fase global
     acierta el **52%** — o sea nada — y el resultado es un **tablero fantasma en el alfa** que se
     ve como cuadros oscuros sobre cualquier fondo. Lo que sí funciona es sin geometría: subir
     cada píxel del fondo hasta su **techo local** (ventana 33 px > un cuadro), con tope de un
     escalón. El techo se mide SOLO sobre el fondo alcanzable desde el borde — si no, un zapato
     blanco pegado a la sombra se la come.
  3. El suavizado del borde va **solo en la orilla** (dilatación de 2 px de lo que se quitó). La
     primera versión graduaba TODO píxel blanquecino y dejaba medio transparentes ojos, botas y
     el número de la camiseta.
  🔴 **Y dos defectos MÁS que cazó el dueño mirándolas puestas (mismo día):**
  · **Las AXILAS de los dos welcome.** Son bolsas de fondo ENCERRADAS por el brazo y el torso, y
    por diseño el script no las borra solo (regla de julio). Se pasan a mano tras leer el mapa
    numerado: `366` en el jugador, `794` en el faraón. **Al recortar cualquier botarga con los
    brazos pegados al cuerpo, mirar el mapa: es el defecto por defecto.** Las otras cuatro tienen
    los brazos abiertos y no lo traen (comprobado con el mapa, no de memoria).
  · 🔴 **El escalón del tablero NO se puede escribir a mano.** El MISMO generador exportó tres
    pares distintos en seis láminas: 253/213 (escalón 40), 255/205 (50) y **255/201 (54)**. Con
    un tope fijo de 45 la tercera se quedaba corta y el fondo salía con un **velo de cuadros casi
    transparentes** — lo que él vio en el PASS de Nile (4,3% del lienzo en alfa 1-19 → hoy 0,08%).
    `_niveles()` mide los dos grises de CADA lámina y usa el claro como "blanco del papel" al
    calcular la tinta, así el fondo cae a alfa 0 valga 253 o 255. ⚠️ El papel se busca desde 235:
    en una lámina muy tapada los cuadros oscuros pueden ser MÁS que los claros y ganarían el pico,
    con lo que el escalón saldría 0 y el tablero se quedaría entero.
  · El encuadre se mide con **alfa ≥ 16**, no con `getbbox()`: cuatro píxeles sueltos a alfa 2 en
    una esquina estiran el lienzo y —como la CSS escala el lienzo ENTERO— encogen la figura sin
    que se vea por qué.
  **`tools/botarga_oscura.py`** hace el `_dark`: flecha azul→naranja con el mapeo
  `(r,g,b)→(b, 0.6561·b, r)` **muestreado de la pareja real** `logo2_standard`/`_dark` (lo
  reproduce con error 0 sobre sus 159.726 px); el contorno queda fuera con `b>=31`.
  🔑 **Los dos camos NO keyean igual y confundirlos no da ningún error:** nile va por `.light`
  (dos looks) y **gridiron por `.camo-day`**, porque es DARK_ALWAYS y su body nunca lleva
  `.light` — con el selector equivocado la botarga se queda clavada en la variante oscura para
  siempre. Los archivos se recortan a su bbox + 2% de aire: la CSS escala el LIENZO ENTERO
  (`height:120px` / `70vh`), así que un margen grande encoge la figura.
  `tools/test_botargas_nuevas.py` **46/46** (12 archivos + navegador real, leyendo qué PNG sirve
  `getComputedStyle().content` en claro y oscuro).
  ⚠️ El PASS de nile es la pirámide entera con el muñeco diminuto en la cumbre: a los 120 px de
  `.quiz-result-mascot` la flecha queda a ~15 px. Es el arte tal cual llegó — si al dueño le
  parece pequeño, se reencuadra el PNG, no la CSS.
· 🕐 **VIAJE EN EL TIEMPO PARA REVISAR TANDAS FUTURAS (2026-08-22).** La tienda esconde las
  temporadas futuras a propósito, así que **ni el dueño podía revisar un camo/marco/cursor antes de
  estrenarlo**. Nuevo escenario `season` en `/admin/demo` (panel: selector con los 12 meses y SU
  temática + "Travel to that month"). 🔑 **El salto vive en `_current_season()`**, la fuente del
  mes, no en cada pantalla: así tanda, giro, tienda y etiquetas viajan TODOS juntos — un parche por
  vista habría dejado alguna sin viajar, que es justo el bug a cazar. De sesión, solo-admin, no
  escribe NADA; fuera de una petición (`has_request_context()`) siempre devuelve el mes real, así
  los publicadores del arranque no se ven afectados. El admin ya poseía todo (`owns_camo`), así que
  viajando puede además ponerse cualquier pieza. `tools/test_viaje_temporada.py` **13/13**.
  ⚠️ **Viajar NO te pone ningún camo — solo cambia el mes.** El primer intento aterrizaba en
  `/app` y el dueño veía el camo que ya llevaba puesto: parecía que el viaje no hacía nada
  ("no funciona"). Ahora aterriza en **`/cosmetics`** —donde vive la tanda— y la tienda pinta
  una **banda dorada** con el mes y un "Volver al presente"; sin ella, un admin que olvida
  salir del demo lee la tienda de otro mes como un bug del sitio. Para verlo PUESTO: botón
  **Activate** en la tarjeta. ⚠️ Ese botón lo cuelga el JS (`renderCard`), **en el HTML crudo
  del servidor NO aparece** — mirar solo el HTML hace concluir que falta cuando no falta.
  ⚠️ El test cayó en la trampa de `g`: Flask-Login cachea el usuario en el contexto de APP y la
  petición del 2º usuario corría como el 1º — el candado solo-admin salía verde SIN serlo. Hay que
  `g.pop('_login_user', None)` antes de cada cambio de usuario.
· **FALTA del paso 5:** los camos de los 9 meses siguientes (arte mensual que encarga el usuario;
  el siguiente es **Colosseum, mes real diciembre**).
  Cada uno = tema CSS + slug en `CAMO_SLUGS`/`CAMO_READY`/`CAMO_NAMES` + una línea en
  `CAMO_WHEEL_DESCS` ×4 idiomas; `_publish_roulette_camos()` lo publica solo al arrancar.

## 📦 LIBRERÍAS VENDORIZADAS — Synapse/Chalkboard sin CDNs (2026-08-10)
three.js r128 + su GLTFLoader, fabric v5.3.1 y jspdf 2.5.1 viven en
`scalpel/static/vendor/` y se cargan PRIMERO en local; los CDN quedan de respaldo. Mismas
versiones exactas → cero cambio visual/funcional; app.py intacto (PDF de Synapse 42/42).
- 🔴 Synapse cargaba DOS libs externas (el GLTFLoader venía aparte) y ANTES no tenía ningún
  fallback; los fallback de fabric @5.3.1 en jsdelivr/unpkg eran **URLs muertas** (npm nunca
  tuvo 5.3.1 — la "cadena de 3 CDN" era 1).
- ⚠️ `raw.githubusercontent` NO sirve como `<script>` (text/plain+nosniff) → el respaldo del
  tag de fabric va vía `cdn.jsdelivr.net/gh`. El dist del tag v5.3.1 se autodeclara "5.3.0"
  (tageo sin regenerar; es el mismo artefacto que espeja cdnjs).
- ⚠️ El velo de carga de Synapse dura **10 s a propósito** (LOAD_MS; cuenta hasta 100% aunque
  los assets ya estén) — un test que espere menos acusa "atascado" a algo que solo cuenta.
- `tools/test_vendor.py` **12/12** (navegador con TODA la red externa cortada: Synapse pinta,
  Chalkboard dibuja).
- ✅ **marked 18.0.9 + DomPurify 3.4.13 también vendorizados (2026-08-10, 2º commit).** Los usa
  el RENDER DEL ANÁLISIS (no el foro: el foro pinta con textContent). Solo se tocaron las DOS
  etiquetas del `<head>`; el consumidor (`marked.parse`/`DOMPurify.sanitize`) quedó intacto.
  🔴 **Hallazgo: la etiqueta vieja de marked era una URL 404 silenciosa** — pedía
  `npm/marked/marked.min.js` SIN versión, y marked no publica ese archivo en la raíz desde la
  v5 (2023); el guard `window.marked ? … : texto plano` lo tapaba. O sea: el análisis llevaba
  tiempo saliendo SIN formato (asteriscos literales) y parecía normal. Verificado offline: el
  pipeline exacto del analizador rinde negritas/listas y mata un `onerror` inyectado.
## 🐌 SCROLL — el cristal esmerilado costaba 3,6× (2026-08-10)
El dueño reportó lag al hacer scroll **en cualquier pestaña** (iMac 2011). Medido aislando un
sospechoso cada vez: **46 elementos con `backdrop-filter`** obligan a re-desenfocar su fondo en
CADA fotograma. **60,6 ms/fotograma (17 fps) → 16,7 ms (60 fps).** Descartadas con datos:
sombras (−22%), filtros (−4%), fondos de camo (−1%).
- ⚠️ **Bajar el radio NO sirve** (probado a 10/6/3 px: 58-65 ms igual). El precio es TENER la
  capa, no cuánto desenfoca. La única cura es quitarla de lo que se desplaza.
- Se conserva en lo que NO scrollea (sidebar, `.mt-nav`, velos de overlay). Las tarjetas pasan a
  fondo **opaco con el mismo color percibido** (`linear-gradient(var(--card),var(--card)), var(--bg)`
  — el truco que ya usaban los menús bajo camo): sin desenfoque, un fondo translúcido dejaría ver
  el arte del camo crudo detrás del texto.
- 🔴 **Dos velos INVISIBLES arrastraban desenfoque a pantalla completa siempre**: el de compra del
  PDF de Synapse (`display:flex; opacity:0`) costaba el **20% del scroll de TODA la app**, y el
  del cajón de ayuda (`#nxh-scrim`) otro tanto. El blur pasó a su clase `.open`. **Regla: un
  elemento invisible no puede llevar `backdrop-filter`** — `test_scroll_perf.py` lo vigila.
- ⚠️ `body.light .card{background:var(--card)}` le gana a un `.card` pelado → la 1ª versión dejó
  el modo claro translúcido. Lo cazó el test midiendo el fondo REAL por tema y camo.
- **NO lo causó la vendorización**: medido el commit anterior (bf0f5cf) = 62,8 ms con las mismas
  46 capas. Entró el 2026-07-05 con el rediseño Aurora Glass. `tools/test_scroll_perf.py` **8/8**.
- ✅ Verificado en **los 9 camos × 2 modos**: tarjeta opaca y 16,7 ms en las 20 combinaciones. La
  regla no nombra ningún camo (usa `var(--card)`/`var(--bg)`) → los camos futuros la heredan.
  El dueño confirmó que **no nota diferencia estética** y pidió dejarlo.
- 📄 **`docs/cambio_visual_2026-08-10.md` = el registro para el día del lanzamiento** (lo pidió el
  dueño, por si ve algo distinto y no sabe si es bug o caché): qué se tocó exactamente, la
  diferencia MEDIDA píxel a píxel (media 0,6-3,4 sobre 255 → por debajo del umbral visible; el
  oscuro cambia más porque su `--card` es mucho más transparente), capturas de referencia en
  `docs/ref_visual/` y cómo revertir (`git revert e0619d3`). Regenerable con
  `scratchpad/compara_visual.py`.
- 🟡 **HILO ABIERTO, sin cerrar:** tras desplegar el arreglo el dueño sigue notando que en su iMac
  2011 el **modo oscuro** va más pesado que el claro (sin camo). **No se reproduce aquí** —layout,
  estilos, JS y coste de sombras salen iguales o mejores en oscuro— pero este contenedor va **por
  software, sin GPU**, así que es ciego al coste de compositing, que es justo donde sufre una GPU
  vieja. Único candidato concreto encontrado: la sombra de `.card` es **40px de blur en oscuro y
  30px en claro** (línea ~84 vs ~87) y el coste crece ~con el cuadrado del radio → ~1,8× por
  tarjeta × ~14 tarjetas. Igualarlo son dos números; el dueño decidió no perseguirlo por ahora.
  ⚠️ **Medir con cuidado: 16,7 ms es el TECHO de vsync** — una vez ahí, todo marca igual y las
  diferencias de rasterizado quedan escondidas. Para compararlas hay que subir el viewport (2560×
  1440) o usar `Performance.getMetrics` de CDP; `--disable-gpu-vsync` NO sirve (rAF deja de
  esperar al pintado y mide 1,5 ms de nada).

- **Lag reportado por el dueño tras el deploy (2026-08-10): MEDIDO, no hay fuga.** Su hipótesis
  (animaciones de Synapse en bucle al salir) es falsa: `switchTab` llama `Synapse.pause()` →
  `stopLoop()`, y medido con rAF instrumentado: 0 callbacks/s en Analyze antes Y después de
  visitar Synapse (idénticos 47½ vs 49½ ms de frame en scroll). El 3D solo consume con su
  pestaña abierta (y ahí siempre costó lo mismo). Lo que SÍ cambió: la PRIMERA carga de los
  vendor (~1 MB) ahora sale del VPS — por IP cruda no hay caché de Cloudflare delante.
- Descarga sin CDN en este contenedor: registro de npm (tarballs) y raw.githubusercontent SÍ
  pasan el proxy; cdnjs/jsdelivr/unpkg no.

## 🔬 INVESTIGACIÓN — autopublicación en redes + upgrade de visión (2026-08-23, SIN construir)
> Última tarea antes de su pausa de 1-2 semanas. Solo investigación verificada; NO hay luz verde
> de construcción. Al volver, decidir fases.
**A. Autopublicar (YouTube/X/Reddit) — arquitectura recomendada: cola de aprobación en /admin +
cron en el VPS (patrón monitor.py).** Claude genera lotes → el dueño aprueba → el cron publica
espaciado. Por red (verificado 2026-08):
- **YouTube:** 🔴 subir por API desde un proyecto SIN AUDITAR deja el video FORZADO A PRIVADO
  (regla desde jul-2020; sin apelación — hay que pasar la API Compliance Audit de Google).
  Camino pragmático HOY: **programación nativa de YouTube Studio** (gratis, ilimitada): una
  sesión al mes deja 8-12 videos aprobados ya programados. API solo si algún día se quiere
  full-auto (la subida ya va en bucket propio ~100/día, la cuota no es problema — el candado es
  la auditoría).
- **X:** la API pasó a PAGO POR USO en feb-2026 (sin tier gratis para nuevos): $0.015/post pero
  **$0.20 si lleva URL** — y los nuestros llevarían link. ~30 posts/mes con link ≈ $6/mes, sin
  mínimo. Alternativas: programar nativo en x.com (gratis, manual) o Metricool ($22/mes + $10
  por cuenta de X).
- **Reddit:** API gratis (<100 req/min, PRAW). 🔴 PERO el full-auto respondiendo desde su cuenta
  es EL de mayor riesgo: regla del 10% de autopromo, shadowban por patrones automáticos
  (intervalos exactos, mismo dominio), subs de trading hostiles a promo. Recomendado SEMI-auto:
  cron caza hilos por keywords → Claude redacta borradores a una bandeja de /admin → él aprueba
  con un clic (la API publica lo aprobado). Sin link en la mayoría de respuestas.
- Si se construye: tabla ContentQueue + pestaña admin + `tools/social_cron.py`, credenciales por
  env (patrón condicional). Fase 1 X, fase 2 Reddit semi-auto, fase 3 YouTube.
**B. Upgrade de visión del analizador (hoy GPT-4o).** Estado 2026: Gemini (2.5/3.x Pro) lidera
los benchmarks multimodales; GPT-5.x fuerte en razonamiento con imágenes; Claude fuerte en docs.
Ningún ganador universal y NINGÚN benchmark público mide lo nuestro. 🔑 **La ventaja ya está
construida: el banco de 30 casos** (verdad por construcción + calificador) — una pasada por
modelo ≈ $0.35-1 y dice EXACTAMENTE si el candidato ve los 4 ciegos de GPT-4o (ratios armónicos
H3/H4, solape E3, cruce de medias T4, RSI T3). Plan al volver: variante de `corre_banco` con
base_url/model por parámetro (Gemini expone endpoint compatible-OpenAI → mismo SDK; NO se toca
el analizador), correr 2-3 candidatos, comparar nota y costo. Costos: hoy ≈$0.029/análisis;
Gemini 2.5 Pro y GPT-5 están en $1.25/M in + $10/M out (mismo orden); GPT-5.5 dobla ($5/$30).
El switch de producción sería config (patrón condicional), con su decisión.

## 📱 REDES SOCIALES — kit de marca generado (2026-08-04)
Instagram y TikTok abiertos por el dueño, 0 seguidores, 0 publicado. Hecho:
- **`tools/gen_posts_ig.py`** (+ `tools/rasteriza_posts.py` para el PNG) genera
  los 9 primeros posts 1080×1350, las 5 portadas de destacadas 1080×1080 y el
  avatar. Sale en `out/posts_ig/` (ignorado). Textos en `tools/posts_ig_textos.md`.
- **Azul de marca medido del propio logo: `#004feb`.** ⚠️ Se toma el color MÁS
  REPETIDO entre píxeles opacos, no el primero — el primero cae en el borde
  suavizado y da `#84a9e8`. El generador lo verifica con un assert.
- **Avatar = la "a", NO el logotipo.** El logotipo es 6:1 y la foto de perfil es
  un círculo: a 32px (comentarios) la palabra entera es una mancha. Va cuadrado
  a sangre — subir el círculo recortado deja esquinas que el visor rellena.
  ⚠️ Se probó la "a" + la flecha del logo y el dueño la RECHAZÓ: esa flecha nace
  después de la "e" final y al juntarla con la "a" cruza trazos ajenos.
- **Los posts son 4:5 pero la cuadrícula del perfil RECORTA al cuadrado central**
  → todo lo legible vive ahí (`--guias` lo dibuja).
- **Portadas de destacadas SIN texto**: Instagram escribe el título debajo del
  círculo; a ~64px una palabra dentro no se lee. Van con glifo.
- Sistema: grafito + rejilla + resplandor del landing; **un solo acento por
  pieza** (azul=producto, dorado=conocimiento, blanco=disciplina); números en
  JetBrains Mono. Tipografías se bajan a `tools/.fuentes/` (gitignored, SIL OFL).
- **Los diagramas de velas se dibujan desde OHLC y son correctos** (order block =
  última vela bajista antes del desplazamiento; FVG = hueco entre máximo de la 1ª
  y mínimo de la 3ª). Un diagrama bonito pero falso cuesta credibilidad.
- **PENDIENTE:** publicar (el dueño quería 9-12 piezas antes de la primera),
  campo "Nombre" con palabras clave, bio sin fecha de apertura, y el enlace
  cuando el sitio abra.

## 💬 CHAT DE TESSERA — sala propia a pantalla completa (2026-08-07)
El asistente dejó de vivir apretado dentro de la Cámara. Al pulsar la puerta **"Tessera AI
Assistant"** (renombrada; era "Tessera AI Chatbot") se abre `#nxc-ov`, una sala aparte: barra con
**← Tessera** (vuelve a la Cámara) · título con halo rubí · **"Volver a la app"**, y la conversación
en una columna de 860px. **Fondo = constelación de nodos** en canvas (`dibujarNodos()`): el lenguaje
de Synapse —puntos con glow + hilos a los 2 vecinos más cercanos, rechazo por distancia mínima— SIN
figuras 3D, más un aliento rubí desde abajo. **Estática**: se pinta una vez por apertura/resize/
cambio de tema (el MutationObserver la repinta en su otra paleta), así que no gasta batería y no
choca con reduced-motion. Verificado en Chromium real: login → cubo → Cámara → chat → pregunta →
claro y oscuro → volver → salir, **0 errores JS**.
- **El teseracto va encima de cada respuesta** (`tesseract.png`, 60px tras el ajuste del dueño).
  ✅ **Recorte arreglado (2026-08-10).** El dueño vio "residuos" fuera de la figura. Diagnóstico
  medido: el alfa era **estrictamente binario (0/255, cero intermedios)** = recorte por umbral, así
  que cada píxel del borde que era mezcla de cubo y fondo NEGRO sobrevivía al 100% (306 px de más
  sobre la silueta real; 196 de los 383 del contorno, casi negros).
  🔑 **Se arregla con GEOMETRÍA, no con color:** el contorno propio del cubo es granate muy oscuro
  → por tono es indistinguible del fondo sobrante, y limpiar "por color" se come el dibujo. Pero la
  silueta de un cubo isométrico es un **hexágono**: `tools/limpia_tesseract.py` lo ajusta al casco
  convexo, mete 2px (ahí vive el residuo), rasteriza a 8× (alfa parcial de verdad) y **quita el
  negro mezclado** con `color = obs/a` (exacto si el fondo era negro, que lo era).
  ⚠️ **NO es idempotente** — se niega a correr sobre un archivo que ya tenga alfa suave. El
  original se recupera de git. Al cambiar el PNG, subir el `?v=` (va por `?v=10`).
- 🔴 **El fondo del chat NO puede preguntar por `body.light` (bug real, 2026-08-10).** Lo cazó el
  dueño: Rising Sun + modo oscuro → el asistente pintado en BLANCO. La causa no es el camo, es que
  **hay camos que fuerzan la clase**: los **LIGHT_ALWAYS** (rising-sun, blackflag) llevan `.light`
  SIEMPRE —el suelo es crema en los dos modos— y marcan la preferencia oscura aparte con
  **`.camo-night`**; el **DARK_ALWAYS** (premium) **nunca** lleva `.light` y marca la clara con
  **`.camo-day`**. Regla del dueño: *el fondo del asistente es identidad propia como Synapse — no
  depende del camo — pero SÍ sigue el claro/oscuro del sitio.* Fix: helper **`temaClaro()`**
  (`camo-day || (light && !camo-night)`) + las 13 reglas `body.light #nxc-ov…` pasaron a
  **`#nxc-ov.nxc-claro`**, una clase que pone `sincTemaChat()` al abrir, al arrancar y en el
  MutationObserver del tema; `dibujarNodos()` usa el mismo helper.
  ⚠️ **Había un fallo ESPEJO que nadie había visto: premium en modo CLARO pintaba el chat NEGRO.**
  Por eso la comprobación se hizo camo por camo y no solo en el que él reportó.
  `tools/test_chat_tema.py` = **21/21** (9 camos × 2 modos + sin camo), midiendo el color REAL que
  pinta el navegador (fondo del overlay + píxel del canvas), no la clase que debería estar puesta.
  Con el código viejo **fallan justo 3**: rising-sun·dark, blackflag·dark y premium·light.
  ⚠️ Trampa del entorno: **`/app` BORRA el cookie `scalpel_splash_ts` al servirse** (es de un solo
  uso) → hay que volver a ponerlo antes de CADA visita o la siguiente rebota a `/welcome` y no
  existe ni el cubo. Y el camo lo pinta el SERVIDOR (`active_camo`): se cambia en la cuenta, no
  desde el navegador.
- 🔴 **Las 12 EMOCIONES se descartaron, y la lección importa más que el resultado.** Se perdió un día
  entero recortándolas. Causas, en orden: (1) la lámina estaba **solo en el VPS** y yo corté a ciegas
  con scripts en vez de mirarla; (2) **el chat guarda cada imagen que el usuario pega dentro del
  `.jsonl` de la sesión** — se extrae con `json`+`base64` y queda en disco, o sea que **SIEMPRE se
  puede trabajar una imagen pegada como archivo**; no saberlo fue lo que provocó las vueltas al VPS;
  (3) aun con la imagen delante, la lámina es **plana** (sombras, piso y confeti horneados), así que
  ningún recorte automático queda perfecto. El dueño cortó por lo sano: *"si lo ves muy complicado
  dejamos las emociones y dejamos el teseracto SIN EMOCIONES flotando"*. **Se quitó la lógica de tono
  del asistente** (prompt, parseo en `/api/assistant/ask` y cliente). Los `emo-*.png` y
  `tools/recorta_emociones.py` quedan en el repo **por si algún día hay cada cubo como PNG
  transparente de origen** — con eso el recorte es de un minuto. `emo-sorprendido` se borró: traía
  la marca de agua de Gemini pintada ENCIMA del cubo (quitarla deja hueco).
- ⚠️ **Trampa de despliegue cazada:** `git checkout <rama> -- 'scalpel/static/emo-*.png'` **no pisa
  los binarios** (el comodín entre comillas no expande) — el código llegaba y las imágenes no, y
  parecía caché. Para archivos concretos, **rutas explícitas**. Y al cambiar un PNG servido, subir el
  `?v=N` de su URL o Cloudflare sigue sirviendo el viejo.
- 🔴 **El VPS está parado en `claude/epic-lovelace-GsOuo`**, no en la rama de trabajo → cada
  `git pull origin claude/gallant-volta-i7cqmf` muere con *"divergent branches"* y el sitio no se
  actualiza. **Todo lo desarrollado SÍ está en `gallant-volta`** (verificado: `nxc-ov` aparece 15
  veces ahí y 0 en epic-lovelace). Arreglo pendiente de correr, no borra nada:
  `git fetch origin claude/gallant-volta-i7cqmf && git checkout -f -B claude/gallant-volta-i7cqmf
  origin/claude/gallant-volta-i7cqmf && git config pull.ff only` + restart. Tras eso el deploy de
  siempre vuelve a funcionar.

## 🐛 DOS BUGS CAZADOS POR EL HERMANO (2026-08-22)
1. 🔴 **Scroll lateral fantasma en `/app` entre ~900 y ~1200px** ("los elementos se montan al
   angostar"). Causa REAL: los 6 tooltips de metodología (`.pill-tip`, 360px, anclados a la
   izquierda de su pastilla) — **una caja `visibility:hidden` SIGUE contando para el overflow**
   del documento → 165-205px de scroll horizontal. El cajón de ayuda `#nxh` fue el primer
   sospechoso y quedó ABSUELTO probando (quitarlo no cambiaba nada; un `fixed` no crea scroll).
   **Fix:** `html{overflow-x:clip}` en index.html (`clip`, NO `hidden`: hidden convierte a html
   en contenedor de scroll y rompe sticky) + IIFE al final del body que al abrir un tip lo
   EMPUJA dentro del viewport (CSS puro no sabe cuál pastilla queda al borde: el grupo envuelve
   en 2 líneas) recolocando la flecha vía `--flecha`. Verificado: 0px de scroll lateral REAL en
   6 anchos, tip de Elliott Wave abierto dentro, 0 errores JS.
   ⚠️ **`scrollWidth` MIENTE con `clip`**: sigue reportando el contenido recortado. Para saber si
   hay scroll de verdad hay que intentar `window.scrollTo(500,0)` y leer `scrollX`.
   ⚠️ Dos FALSOS positivos clásicos al sondear solapes: los hijos de un velo `opacity:0`
   (syn-pdf) declaran opacity 1 (no se hereda, se compone), y el acordeón PLEGADO de la tabla
   comparativa de la landing (`.cmp-panel{max-height:0;overflow:hidden}`) deja cajas fantasma
   con rect. La landing quedó LIMPIA — no tenía nada real.
1b. 🔴 **Y el arreglo NO se vio al desplegar: salían las CLAVES en crudo**
   (`reg.dobMonth`/`reg.dobDay`/`reg.dobYear`). No era un fallo del arreglo —
   era **caché de estáticos**: nginx sirve `/static/` con `max-age=604800`
   (7 días) y Cloudflare cachea delante, así que el navegador tenía el
   `auth.js` VIEJO con el HTML NUEVO. `Ctrl+F5` no basta: no toca la copia de
   Cloudflare. 🔑 **Fix permanente: helper `estatico('auth.js')`** en app.py
   (context processor) que pega `?v=<mtime>` — la URL cambia sola al desplegar
   y una URL nueva no la tiene cacheada nadie. Aplicado a las 15 referencias de
   `auth.js`/`auth.css`. **Al añadir un JS/CSS nuevo, usarlo**; un número de
   versión a mano es justo lo que se olvida. ⚠️ El síntoma es traicionero: la
   página no falla, sale a medias — y parece un bug del código recién escrito.

2. 🔴 **La fecha de nacimiento del registro "no estaba en formato USA".** El `<input type=date>`
   nativo lo formatea el navegador según el idioma del SISTEMA de quien mira y la página no
   puede forzarlo. **Fix:** tres selectores Mes(NOMBRE)/Día/Año — con el mes por nombre no
   existe formato que confundir. Orden USA en el DOM; auth.js pone `dmy` en es/fr/pt (CSS
   `order` reordena) y pone los nombres de mes con `Intl` según el idioma del sitio; años
   futuros se auto-añaden (el HTML llega a 2008 = hoy−18). El server compone birth_y/m/d y
   SIGUE aceptando `birth_date` entero (tests/clientes viejos). Suites: registro_doble 17/17,
   codigo_verificacion 13/13, correo_canonico 24/24, boot 8/8 + 5 casos nuevos del compositor.

## 🕐 LAS FECHAS SE GUARDABAN EN HORA DE BERLÍN (2026-08-13) — leer antes de tocar fechas
🔴 **El VPS está en Europa/Berlín.** Todo el código guarda con `datetime.now(timezone.utc)`, pero
las columnas son `DateTime` SIN zona, y al insertar un valor CON zona en una columna sin zona
**PostgreSQL lo convierte a la zona de la SESIÓN** (la del sistema operativo). Cada fecha se
escribía **+2 h** y al releerla se interpretaba como UTC: instantes **en el futuro**.
- **Lo que rompía, y cómo se vio:** una publicación de las 23:21 UTC quedaba fechada al día
  siguiente → NO contaba para el cupo diario → el dueño publicaba y seguía diciendo "2 restantes".
  También afectaba a rachas y a la ventana antiflood de comentarios (una fila "2 h en el futuro"
  contaba como "hace un instante" → el límite de 5/minuto era 5/2-horas).
- **Fix:** la sesión de PostgreSQL se abre con `connect_args={'options': '-c timezone=utc'}`, y los
  DOS helpers gemelos (`_as_utc` **y** `_aware`, 30 usos, muchos en pagos) **CONVIERTEN** las fechas
  con zona en vez de devolverlas tal cual.
- ⚠️ **Las filas viejas conservan su desfase y NO se migran**: Berlín es +1 en invierno y +2 en
  verano, una corrección en bloque estropearía media base. Se cura sola con los datos nuevos; una
  fila desplazada **bloquea de más, nunca regala cuota** (probado).
- 🔴 **`tools/test_horas_pg.py` 16/16 levanta un PostgreSQL REAL con el servidor en Berlín.** Existe
  porque **toda la batería del repo corre sobre SQLite, que no convierte zonas: era ciega a esto por
  construcción.** Cualquier bug de fechas futuro se prueba ahí, no en SQLite.
- `tools/check_horas.py [--probar]` compara los tres relojes (proceso / base / última fila escrita).
- ⚠️ **La cuota del analizador NUNCA estuvo rota**: es una ventana DESLIZANTE (`now - window`), no un
  día de calendario, así que escribía y comparaba desplazado y se cancelaba. Y por eso **la zona del
  cliente da igual**: UK o USA recuperan su análisis 24 h exactas después de gastarlo. Lo que SÍ va
  por día UTC (corte a las 00:00 UTC = 20:00 en Nueva York): cupo de posts, Reto Diario y su racha,
  topes de XP. No es un bug, es una decisión — si un cliente americano se queja de que "la racha se
  reinicia a las 8pm", es por aquí.

## 🚪 REGISTRO — dos fallos que espantaban clientes (2026-08-13)
Los cazó el dueño creando la cuenta de su papá. Ninguno se veía en los tests porque los dos nacen
del **tiempo real** de una persona usando el formulario.
- 🔴 **"Ese usuario ya está tomado"… dicho por tu propia cuenta.** El POST del registro envía el
  correo de verificación **por SMTP DENTRO de la petición** (2-6 s con la página colgada y el botón
  vivo) → segundo clic → el primer envío ya había creado la cuenta y el segundo choca contra ella.
  La cuenta quedaba perfectamente creada y solo se descubría probando a loguear.
  **Fix en dos capas:** el botón se deshabilita al primer envío válido (`reg.creating` ×4; solo si
  `checkValidity()`, o un formulario incompleto dejaría el botón muerto sin haber enviado nada); y
  en el servidor, un conflicto donde **el buzón canónico coincide Y la contraseña verifica contra el
  hash de la cuenta chocada** no es conflicto: es el mismo creador reintentando → se le manda a la
  pantalla del código. **La contraseña es la prueba de identidad** — un extraño con el username o el
  correo de otro sigue viendo el error de siempre. `tools/test_registro_doble.py` **17/17**.
- 🔴 **"Código incorrecto" con el código bien tecleado.** CADA login de una cuenta sin verificar
  **regeneraba el código y mataba el anterior** — y el flujo real de alguien atascado es probar el
  login varias veces. Letal cuando el buzón es de OTRA persona (fue el caso: el padre le dictaba un
  código que el propio login del hijo acababa de invalidar). También explica los "dos códigos que
  nunca pedí": uno del registro, otro de su login.
  **Fix:** el login solo genera y envía si NO hay uno vigente. El botón "reenviar código" sigue
  rotándolo — ésa es la vía explícita. `tools/test_codigo_verificacion.py` **13/13**.
- ⚠️ Tres checks de `test_correo_canonico` se **reencuadraron** (usaban la misma contraseña que la
  cuenta base = "la misma persona"). La regla que vigilan —un buzón, una cuenta— sigue intacta, y
  ahora además se prueba el alias de un extraño. 24/24.
- ⚠️ **Trampa de los tests de registro:** un `test_client` que ya verificó queda LOGUEADO, y a un
  usuario con sesión `/register` lo redirige a `/welcome` sin crear nada. Cliente nuevo por caso.

## 🎁 LA OFERTA DE BIENVENIDA, ENCENDIDA AL 30% (2026-08-13)
`LAUNCH_DISCOUNT_PCT=30` puesta en producción. **El descuento se aplica al crear el pedido, antes de
elegir riel**, así que vale igual por PayPal y por USDT: primer mes $17.50/$35, renovación $25/$50.
Solo mensual y solo para quien **nunca ha pagado** (atado a la cuenta, no a una cookie).
- Línea de arranque nueva **`[Oferta] bienvenida=30% → premium $35.00 (lista $50)…`** — un número que
  toca precios tiene que poder confirmarse desde la terminal; el error caro no es que no quede
  puesta, es que quede un 3 donde iba un 30.
- 🔴 **Dos fallos que solo aparecían con la oferta ENCENDIDA** (o sea: habrían salido el día del
  lanzamiento, cobrando dinero real): (1) el porcentaje estaba escrito **a mano** en las 4
  traducciones de la landing ("15%") y el diccionario pisa lo que renderiza Jinja → habría mostrado
  $35 junto a "↓ 15%"; ahora lleva `{pct}` y el número sale de `LAUNCH_PCT`. (2) `checkout.html`
  cargaba `pages_i18n.js` al FINAL del body pero su script lo usa al parsear → cuando el primer mes
  y la renovación difieren, la excepción tumbaba el bloque y **el carrito no avisaba de que el precio
  sube en el mes 2**. El diccionario pasó al `<head>`.
- ⚠️ **NO caduca sola**: apagarla el **12-oct-2026** con `LAUNCH_DISCOUNT_PCT=0`. Y ojo — el dueño
  apagó la oferta sin querer copiando el bloque de apagado que iba en el mismo mensaje que el de
  encendido: **nunca dar los dos comandos juntos.**
- ⚠️ Choca con el socio: su código da 20% y esto da 30% público. Su dinero no se rompe (el cliente
  atado renueva a SU tarifa y la comisión se paga igual), pero su código deja de ser un privilegio.
- `tools/check_oferta.py [usuario…]` dice si está encendida y **por qué una cuenta la ve o no** —
  "tener plan Free HOY" ≠ "no haber pagado nunca": un pedido pagado en el historial la excluye para
  siempre, que es lo que despistó al dueño (sus cuentas de prueba ya habían pagado).

## 🚀 EL SITIO ESTÁ ABIERTO AL PÚBLICO (2026-08-13, orden del dueño: "YA SALIMOS")
Ejecutado y VERIFICADO en el VPS: `PREVIEW_USERS` quitada (candado=apagado) + **`PUBLIC_HTTPS=1`**
+ nginx cambiado a la config **live** (`robots.txt` → `Allow: /`, estáticos por nginx con
`max-age=604800`, `/sitemap.xml` nuevo con solo páginas públicas, candado anti-caché
private/no-store + Vary: Cookie añadido a la live). Registro abierto, compras con dinero real y
la oferta del 30% activa. Copia de la config anterior en `…/tradeable.academy.antes-de-abrir`.
- ⚠️ **La vista previa por `http://IP:5001` YA NO sirve para loguearse** (cookie Secure): el dueño
  prueba en el propio dominio desde ahora. NO diagnosticar como avería.
- **Cerrar de emergencia** = volver a poner `PREVIEW_USERS=maurotradesve,gussytrades,guaramo2026`
  (+ `reread && update`); nginx no hace falta tocarlo.
- Pendientes del mismo día: los 2 clics de Cloudflare (Purge Everything + Always Use HTTPS),
  alta en Search Console cuando quiera acelerar a Google, y 🔴 el #0 (rotar secretos).

## 🔑 EL CANDADO DEL LANZAMIENTO ERA `PREVIEW_USERS` (histórico; quitado el 2026-08-13)
Descubierto al dar acceso al papá del dueño: **nginx está en la config ABIERTA** (`…academy.abierto
.conf`) — el pase de nginx ya no existe, `nginx -T | grep pase` solo devuelve comentarios. Lo único
que tapa el sitio hoy es el candado de la aplicación: `PREVIEW_USERS=maurotradesve,gussytrades,
guaramo2026`. Cualquier otro —anónimo o logueado— ve "Próximamente".
- **Abrir al público el día del lanzamiento = `set_env.py --quitar PREVIEW_USERS`.** No hay que tocar
  nginx. (Actualizar `LANZAMIENTO.md` con esto.)
- ⚠️ **`/register` también está detrás del candado**, así que para crear una cuenta nueva hay que
  quitarlo, registrar y volver a ponerlo CON el nombre nuevo en la lista — **la lista se escribe
  entera, no se añade**. Y mientras está quitado el sitio queda 100% público (ya no hay segunda
  barrera): hacerlo del tirón.
- Confirmar siempre con `grep -i preview /var/log/trader.out.log | tail -1`.

## 🔴 La tarifa del cliente de un socio se congelaba en la de LANZAMIENTO (2026-08-13)
Salió al explicarle cómo distingue PayPal un descuento de creador (perpetuo) de la oferta pública
(de una vez). `_tramos` calculaba la tarifa PERPETUA con `_quote()`, que aplica **max(oferta,
código)** porque al comprador se le cobra el mejor precio. Con la oferta al 30% y un socio al 20%,
la **renovación quedaba en $35 en vez de $40, para siempre** — el gancho temporal convertido en
precio de por vida, contra la cláusula 3.1 del acuerdo. **$5/mes por cada cliente de socio captado
durante la ventana de lanzamiento, mientras siguiera suscrito.**
- **Fix:** `_tarifa_de_creador(lista, pc)` aplica **solo** el descuento del socio; el primer mes
  sigue cobrando el mejor precio disponible. 🔑 Las **dos ramas** (código de socio en el pedido /
  cuenta atada que canja una promo general) pasaron a un solo camino — el fallo vivía en las dos y
  el primer arreglo solo tapó una.
- ⚠️ **Lo que la pasarela ve es un IMPORTE, nunca un "cupón":** PayPal recibe dos tramos
  (`TRIAL` 1 ciclo con el primer mes + `REGULAR` sin fin con la renovación) y NOWPayments una
  factura por `final_price`. Por eso un error aquí no lo caza ningún panel externo: PayPal cobraría
  $35/mes tan feliz durante años.
- `tools/test_tarifa_creador.py` **16/16** (con el código viejo fallan 4).

## 📅 Recordatorio diario
> 🔔 **SIN CERRAR, del aviso que tocaba el 2026-08-03:** re-revisar juntos los TONOS del 1º/2º/3º
> del salón de la fama (commit `eb50f46`: f1 = blanco incandescente + movimiento + halo, f2 =
> degradado quieto, f3 = brasa plana `#c9603a`). Se le recordó el 2026-08-10 y **sigue sin mirarlo**;
> no volver a ponerle fecha: sacarlo cuando toque el quiz o los cosméticos.

La **primera vez que el usuario escriba cada día calendario** (`currentDate`), mostrar (si ya se mostró
hoy, no repetir):
1. "📋 TAREAS PENDIENTES" (la lista de abajo).
2. "🎯 QUIZ GAPS — temas sin quiz" (ver sección abajo): las metodologías/gatillos que NO tienen quiz
   (beginner/intermediate/advanced/hardcore/daily). Recordatorio pedido por el usuario el 2026-07-18.

## 🎯 QUIZ GAPS — metodologías/gatillos SIN quiz (auditado 2026-07-18)
> Universo de quizzes actual = solo 4 metodologías (`ict`, `smc`, `wyckoff`, `patterns`). Existe en
> Synapse y/o el analizador de screenshots pero **no tiene ninguna pregunta de quiz**:
- **🔴 Technical Analysis / Indicadores** — está en Synapse (9 temas) **Y** es un botón del analizador,
  pero CERO quizzes: Moving Averages, RSI, MACD, Bollinger, Volume, MA Cross, RSI Divergence,
  MACD Cross, Squeeze Break. *(máxima prioridad — es el gap más flagrante.)*
- **🔴 Elliott Wave** — es un approach del analizador pero no hay ni quiz ni contenido en Synapse
  (Impulso 1-5, corrección ABC, Wave 3 extension, Zigzag, Flat, Diagonal…).
- **🟡 Fundamental Analysis** — Synapse (6 temas): Macro Drivers, Interest Rates, News/Data,
  Intermarket, News Fade, Data Continuation.
- **🟡 Quantitative** — Synapse (6 temas): Probability, Backtesting, Risk of Ruin, Algo Systems,
  Mean Reversion, Momentum.
- **🟡 Price Action básico** (Synapse `price`, parcial) — SIN quiz dedicado: Support & Resistance,
  Trend & Structure, Supply & Demand, Breakout-Retest, Pin Bar, Engulfing. *(Sí hay: Candlestick,
  Chart Patterns, Harmonic.)*
- **🟡 OTE / Std Dev** — approach propio del analizador, sin topic de quiz dedicado (solo se roza vía
  "Premium/Discount" en el Daily y dentro de las preguntas ICT).
> **SÍ tienen quiz (completo, 3 niveles + hardcore + daily):** ICT (Order Blocks, FVG, Market Structure,
> Kill Zones, Liquidity, AMD, PD Arrays), Wyckoff (Accumulation, Distribution, Market Phases), SMC
> (Structure, Confluences, Liquidity), Patterns (Candlestick, Chart, Harmonic). **Wyckoff SÍ tiene.**
> *(Nota: `daily_bank.js` tiene 200 preguntas pero solo 136 con tag `m:`/`topic:`.)*

---

## 🟢 EN CURSO — Auditoría de copy ES + pendientes (rama actual)

**Auditoría de español (calidad): ✅ COMPLETA** en todo lo traducido. Pusheada en 8 partes
(commits "ES copy audit part 1..8"): landing, UI (`index.html` todos los dicts: base I18N,
MT_I18N, UNLOCK/reveal planes, REVIEW/testimonios, RANK, TOPIC, DAILY, mapa Synapse, explainer),
PDFs, certificado/verify, Mentorías (`improve_i18n.js`), Synapse (`synapse_translations.py`),
quiz banks completos (QUESTION_BANK 398 q + HARDCORE_SCENARIOS), auth.js, contact, splash.
Decisiones del usuario: **Legal (T&C/Privacy) se queda en INGLÉS**; registro ES **LatAm neutro**
(asesoría, no asesoramiento); en el PDF legal de Synapse se añadió **nota "el inglés prevalece"**
en los 4 idiomas; **"pierna"** (=leg, 66 casos en quiz) se DEJA tal cual; **kicker** del
certificado en inglés. Pocos errores reales hallados (todo estaba muy bien hecho).

**✅ ESPAÑOL — gap de traducción CERRADO (2026-06-23):** las superficies que estaban 100% en
inglés ya están traducidas a ES: `pricing.html`, `checkout.html`, `checkout_done.html`,
`settings.html`, `camos.html`, `store_indicators.html` + los **EMAILS** (`send_reset_email`/
`send_verification_email`, marca corregida **"Scalpel" → "Trader Accelerator"**). Infra nueva:
`scalpel/static/pages_i18n.js` (motor client-side data-i18n, mismo patrón que `improve_i18n.js`,
lee `scalpel_lang`; dicts EN+ES a paridad de 153 claves, stubs `fr`/`pt` vacíos listos para
rellenar). Idioma de emails vía **cookie `scalpel_lang`** (espejo del localStorage, escrita en
`index.html` + `improve_i18n.js`); el server la lee en `_email_lang()` (`app.py`), fallback EN.
Valores dinámicos de Jinja (montos, fechas, plan) quedan server-rendered; fechas `strftime` siguen
en inglés (no se localizaron nombres de mes — bajo impacto).

**🟡 FRANCÉS — Task #2 EN PROGRESO (audit honesto, 2026-06-23):** (1) ✅ rellenado el FR que
faltaba: stub `fr` de `pages_i18n.js` (153 claves) + `EMAIL_I18N` reset/verify. (2) ✅ **leído a
fondo para coherencia (0 errores reales):** dict UI principal `I18N`, MT_I18N, mentorías
(`improve_i18n.js`), `auth.js`, `synapse_translations.py` (+ PDF legal), `landing.html`,
`contact.html`, `splash.html`, certificado+verify (`app.py`), y ranks/reveals (RANK_I18N, rank-up,
UNLOCK_I18N). Todo francés profesional y natural; jerga en inglés (Win rate, draw on liquidity,
kill zone…) intencional e igual que ES; kicker certificado en inglés (decisión previa). (3) ⚠️
**QUIZ: solo 75 de ~398 preguntas leídas literalmente** (todas impecables) + escaneo automático
del 100% de `index.html` (3.365 valores, 0 inglés sin traducir). **FALTAN ~323 preguntas +
HARDCORE_SCENARIOS por leer literalmente** (multi-sesión: ~7.700 líneas, no cabe en una sola).
`synapse_content_fr.json` (1.396 líneas) muestreado, no leído completo. Convención: sitio **"vous"**,
mentorías **"tu"**. Fechas `strftime` en inglés (igual que ES).

**🟢 PORTUGUÉS — Task #3 (audit honesto, 2026-06-24):** (1) ✅ rellenado el hueco: stub `pt` de
`pages_i18n.js` (153 claves, paridad EN/ES/FR/PT) + `EMAIL_I18N` reset/verify (`_email_lang()` ya
acepta `pt`). (2) ✅ **2 hallazgos reales corregidos:** (a) `synapse_translations.py` estaba en
**portugués de PORTUGAL** (utilizador, ficheiros, partilha, indemnização, direitos de autor,
monitoriza, Procura, Varrimento, Harmónicos, Juro, Macroeconómicos) → convertido a **brasileño**
(usuário, arquivos, compartilhamento, indenização, direitos autorais, monitora, Demanda, Varredura,
Harmônicos, Juros, Macroeconômicos, Sumário); el resto del sitio ya era PT-BR (verificado: marcadores
PT-PT solo vivían en ese archivo). (b) `checkout_done` decía "Faturamento" pero la categoría del form
de contacto es "Cobrança" → corregido. (3) ✅ **leído a fondo (PT-BR, 0 incoherencias):** dict UI
principal (gran parte), MT_I18N (kill zones), mentorías, auth.js, contact.html, splash.html, landing,
certificado+verify, y **quiz** (26 muestras ES/FR-equivalentes leídas en PT + 125 inline). Automático:
paridad total + 0 inglés sin traducir en 3.365 valores + 0 marcadores europeos restantes en todo el
sitio. Convención: **"você"** (informal) en todo PT, jerga en inglés igual que ES/FR. **NO** leído
literal el 100% del quiz PT ni cada línea del dict principal (igual criterio que ES/FR).

**✅ LEGAL — T&C + Privacy TRADUCIDOS (COMPLETO 2026-07-01, decisión NUEVA 2026-06).** ⚠️ **CAMBIO de
regla:** antes T&C/Privacy se quedaban SOLO en inglés; tras discusión legal, el usuario decidió
**traducirlos a ES/FR/PT** con la **cláusula "el inglés prevalece"** (controlling-language, banner en
cada página) que cubre malentendidos de traducción/terminología. La versión inglesa sigue siendo la
servida, autoritativa y legalmente vinculante. Infra: `scalpel/static/legal_i18n.js` (motor genérico
que **cachea el inglés original** `el.__en` como fuente autoritativa; solo guarda es/fr/pt; claves sin
traducir caen al inglés cacheado; lee `scalpel_lang`, escribe localStorage+cookie). Ambas páginas
etiquetadas con `data-i18n`/`data-i18n-html`/`data-i18n-title` + `<script src="/static/legal_i18n.js">`.
**HECHO:** `terms.html` **18/18 secciones** (claves `terms.*`, 61/idioma) + `privacy.html` **15/15
secciones** (claves `priv.*`, 52/idioma). Total **113 claves/idioma a paridad EN/ES/FR/PT** (verificado:
0 faltantes, 0 dups, 0 claves HTML sin dict). FR: apóstrofes tipográficos `’` (U+2019) dentro de strings
con delimitador `'` y comillas HTML dobles; guillemets `« »`. PT brasileño (você, "Sumário",
"prevalecente"). El PDF legal de Synapse YA estaba traducido (con "inglés prevalece") — eso es aparte.
**Nota:** fechas "Last updated" quedan server/estáticas en inglés (bajo impacto, igual criterio que el
resto del sitio con `strftime`).

**✅ T&C — SECCIÓN 19 MENTORÍA + límites de planes (2026-07-25, luz verde del usuario).** `terms.html`
pasó de 18 a **19 secciones**: nueva **"19. Mentorship Program — Additional Terms"** (claves nuevas
`terms.toc19/t19/b19`, SIN renumerar nada — Contact sigue siendo 18; cero refs rotas). Contenido 19:
dos productos (Programa de Clases / Reuniones 1-1), mentores=educadores no asesores (callout),
en-vivos ocasionales sin frecuencia garantizada, acceso termina con la membresía + streaming-only/no
descargas (breach de Secc 8 → terminación Secc 10), reuniones 30min (tarde/no-show del cliente =
entregada; cierre anticipado de mutuo acuerdo = entregada; extensión = cortesía del mentor sin cargo),
compra solo con disponibilidad de calendario, cancelación del mentor → reprogramar 14 días o reembolso
prorrateado, idiomas ES/EN only, plataformas de terceros (Discord/video), pago único sin auto-renovación,
18+. **Secc 5 ampliada:** límites por plan (Free 1/7d+1proj; Standard 1/24h+5proj+Foro; Premium
5/24h+10proj+Foro+features) + remisión al card al momento de compra + **camos/PDF = compra única solo
decorativa/solo contenido** + camos permanentes anclados al User ID (se pierden si terminación por
violación). **Secc 7:** "Sole Exception"→"Exception" + excepción nueva (reunión cancelada por mentor,
prorrateo de lo pagado) + **plazo de procesamiento 15 días hábiles**. Traducciones ES/FR/PT completas en
`legal_i18n.js` (paridad 64 claves/idioma verificada; FR con apóstrofes tipográficos). **Checkbox de
aceptación** en el carrito de mentoría (`mco2.terms` ×4): required nativo + backstop server en
`/mentorship/checkout/create` (sin `terms_ok=1` → redirect a review, no crea orden) + audit detail.
E2E probado + navegador ES. **Decisiones registradas:** reembolso SOLO (a) falla técnica 72h (ya existía)
y (b) reunión cancelada por mentor no reprogramada en 14 días, prorrateado a lo pagado; nada más es
reembolsable. Pre-Flight queda premium-only. **PENDIENTE legal aparte:** contrato privado con Gabriel
(contratista independiente: IP de las clases grabadas, reparto, obligaciones, no-cobro-extra) — NO va
en los T&C públicos.

**🟢 CAMOS — sistema de skins comprables (EN CURSO, actualizado 2026-07-19).** Un camo = un *theme* que
reskinea SOLO el fondo/colores del sitio (layout/paneles/posiciones NO cambian) + swap de la mascota en
el Quiz (welcome + pass/fail). **Infra base (cableada, estable):** `User.active_camo`/`owned_camos` +
helpers `camos_owned()/add_camo()/owns_camo()` (admin posee TODO); `CAMO_SLUGS` (20 slugs) y
`CAMO_READY` en app.py — **hoy `{'rising-sun','pole','premium','fourth','naval','mission','blackflag','standard','chronicles','gridiron','nile','highnoon','alchemist'}`**, el resto pendiente; endpoints
`/api/camo/activate` `/api/camo/deactivate`; `/app` pinta `body.camo-<slug>` pre-paint (sin FOUC);
tienda `/camos` con ownership/compra. ✅ **TIENDA CABLEADA A PAYPAL (2026-07-30, inerte sin claves):**
decisión del usuario = camos SOLO por PayPal ($1.99 themes / $4.99 seasonal, asume la comisión fija;
cripto descartado porque la fee de red supera el precio). Piezas: `CamoOrder` (tabla separada, patrón
MentorshipOrder, precio/label snapshot server-side — el browser solo manda slug), catálogo
`camo_store_price()` + `CAMO_SEASONAL`/`CAMO_NAMES`, `POST /api/camo/buy` (valida: listo, no-plan,
no-poseído; sin claves → 503 `soon` y la tienda muestra su toast), `GET /camos/paypal/return/<id>`,
webhook `/webhook/paypal` despacha por `custom_id` `camo-<id>` (los helpers `_paypal_*` ahora llevan
`kind`), activador idempotente `_activate_camo_from_order` (enciende el camo solo si no hay otro
activo), barrido de /admin extendido a CamoOrders, y `send_payment_alert_email` tolera ambos tipos de
pedido. **E2E 18 checks verdes** (PayPal simulado): precio server-side aunque el cliente mande otro,
webhook repetido no re-activa, barrido rescata compra abandonada. **Al encender PayPal no hay nada más
que hacer para camos** — mismas 4 env vars.
✅ **PREVIEWS EN LA TIENDA — el card muestra la PIEL, el preview el interior (v2, 2026-07-31).**
El usuario pidió el cambio: *"en ese card como tal esté el grafito o piel del camo, y que luego al
hacer preview sí se vea desde dentro"* — la app encogida en un card de 150px no dice nada del skin.
- **Card** = `static/camo_skin_<slug>[_alt].jpg` (900×450, 2:1 igual que el swatch → sin recorte;
  11 archivos, 315 KB en total). Generador **`tools/gen_camo_skins.py`** (ya no vive en un scratchpad).
- **Lightbox** = vista desde dentro (`camo_prev_<slug>.jpg`, los screenshots de /app que ya existían)
  + la piel debajo anclada abajo (`object-position:center bottom`, porque casi todo el arte va en una
  esquina inferior). En los camos de 2 looks (standard/mission/pole) el botón **cambia AMBAS imágenes**
  → se comparan los dos grafitos sin salir del preview.
- ⚠️ **Dos trampas al generar las pieles** (están documentadas dentro del script):
  1. **Tessera se re-asigna su `element.style` en un bucle rAF** → ocultarla con display/visibility NO
     pega, y el cubito rojo quedó incrustado en las 11 pieles. Hay que **QUITAR** la interfaz del DOM.
  2. El arte del camo vive en `body::before/::after` con **z-index negativo**, y con la página desnuda
     Chromium lo pinta **o no, al azar** (mismo quirk de compositing que costó horas con Tessera; los
     estilos computados y la clase están correctos igual). Copiar los fondos a divs reales es
     determinista pero **deforma los fondos multicapa** (rising-sun salía rojo plano) → se mantienen
     los pseudo-elementos y se **REINTENTA hasta verificar** (~50% de acierto por intento).
  3. **Regla:** nunca escribir una imagen sin medirla (stddev) — una página en blanco se captura sin
     dar ningún error y termina publicada como un rectángulo blanco en la tienda. Los no-listos conservan su degradado + "Coming soon". **Bios corregidas ×4
idiomas** (camos.html EN + los 4 dicts de pages_i18n.js — ojo: el dict EN PISA el HTML al cargar, hay
que editar ambos): naval ya no dice "azul marino" (es camuflaje oliva + condecoraciones), blackflag =
mapa del tesoro (no "carbón y hueso"), pole = plano de ingeniería (no "rojo de carrera"), mission =
dos looks (cosmos/Marte), fourth = Estatua de la Libertad + monumentos + fuegos, sun = washi/kanji,
standard/premium enriquecidas. Migración
prod ya aplicada (columnas `active_camo`/`owned_camos` en `user` + auto-heal `_migrate_user_camo_columns()`
en `init_db()` — futuras columnas nuevas: SIEMPRE auto-migración, nunca pedirle al usuario SQL a mano).
**Mascotas (welcome/pass/fail, light+dark) — 7 de 7 camos LISTAS y con cutout limpio:** rising-sun, naval,
mission, pole, blackflag, premium (Obsidian Gold), fourth (USA, solo welcome — faltan pass/fail, el
usuario las subirá después). Proceso de cutout: `scalpel/tools_camo_cut.py` (semi-automático: detecta
huecos blancos ENCERRADOS por el contorno —axilas, entre piernas, barandillas— los numera sobre el arte,
un humano decide cuáles son fondo vs. feature blanco real —guantes/ojos/dientes—, aplica con bordes
suavizados). Dark = recolor de flecha azul→naranja `#dd9100` (mismo tono que la mascota default dark,
sampleado con precisión de píxel); camos con arte que NO debe recolorearse (ej. bandera USA) usan
`recolor=False`. **Themes (fondo) — 8 de 20 LISTOS:**
- **Standard Steel** ✅ **(2026-07-30, el camo del plan Standard).** **DOS looks** (patrón Pole/Mission).
  🌙 **dark** = placa de grafito + histograma de volumen (abajo). ☀️ **light** = placa de acero pálido
  (`--bg:#dfe3ea`, acento `#3d6d9c`, **logo por defecto**, sin invert) + la **FICHA TÉCNICA de una
  vela** abajo-derecha: la vela dibujada como pieza de taller (cotas RANGE/BODY con flechas, líneas
  auxiliares punteadas, rótulos HIGH/CLOSE/OPEN/LOW y cajetín "FIG. 1 — CANDLE"). Truco del grabado:
  todo el dibujo va en `<defs>` y se pinta con DOS `<use>` — uno blanco desplazado 1.6px debajo y uno
  oscuro encima (`currentColor` + `color` en el `<use>`) → se lee como surco en el metal, no como
  impresión. Rótulos en inglés (misma convención que los diagramas de Synapse).
  ⚠️ **Se PROBÓ y se DESCARTÓ una FIGURA DE CHLADNI en arena** (granos sobre las líneas nodales de una
  placa vibrando): al usuario le pareció "un mandala" y **no se entendía qué era**. NO re-proponerla.
  🔴 **Lección general: en este sitio el adorno tiene que RECONOCERSE a la primera** — lo abstracto
  bonito no vale, aunque sea original. (Del intento quedó un truco reutilizable: para dibujar miles de
  puntos sin inflar el CSS, extraer el contorno con marching squares y emitir `M x,y h.01` con
  `stroke-linecap:round` — 2.600 `<circle>` costaban 175 KB, así 31 KB. Un `stroke-dasharray` NO sirve:
  cada subtrazo reinicia la fase y se ve como línea continua.)
  Placa de acero mecanizado = **veta diagonal cepillada**
  (`repeating-linear-gradient` 112°) sobre degradado grafito; abajo-derecha, un **histograma de
  VOLUMEN en relieve** (relleno `#0f1218` más oscuro que la placa → se lee como sombra tallada, filo
  de luz arriba-izq, canto oscuro a la derecha) con **línea cero** y **media móvil de 5 barras**.
  ⚠️ **Las alturas NO son decorativas:** se derivan de una serie de precio simulada (`series()` en
  `scratchpad/build_standard_camo.py`), así los picos caen en los movimientos grandes — es lo que hace
  que se lea como volumen y no como un gráfico de barras creciente. Proceso de decisión: 3 temas
  (acero / parqué-teletipo / skyline) → eligió acero → 3 derivados (mosaico treemap / bóveda / acero
  templado) → **rechazó los tres**, la bóveda "horrible", y pidió el fondo original + *un relieve de
  esquina en sombra* → 3 relieves (mosaico escalonado / barras / monedas) → eligió barras → 3 formas
  de que se lean como volumen (precio arriba / media móvil / tinte direccional) → eligió media móvil.
  **Lecciones:** (a) el usuario quiere el fondo SOBRIO y el adorno CONTENIDO en una esquina, no
  patrones a pantalla completa; (b) nada de objetos grandes tipo bóveda; (c) un relieve de esquina
  **sólo se ve en pantallas ≥~1300px** — a 1000px los paneles lo tapan entero (aceptado por él);
  (d) el cubo de Tessera vive en esa misma esquina y se le monta encima (aceptado). **Mascotas: NO
  tiene arte propio TODAVÍA** — usa el muñeco-flecha por defecto, igual que arrancó `fourth`.
  🎨 **TEMÁTICA DE BOTARGA APROBADA (2026-07-30): EL HERRERO.** Razón: el camo es una placa de acero y
  el herrero es quien la hizo — no es un disfraz pegado, es el origen del material; además mete **fuego
  naranja contra el gris frío**, así la botarga resalta sin tocar el fondo. Lectura de marca: el acero
  no se encuentra, se forja (encaja con un plan de entrada). **Las 3 poses:**
  · **welcome (`logo2_standard`)** — junto al yunque, delantal de cuero, gafas de soldador subidas en
    la frente, martillo al hombro; con las tenazas sostiene **una vela japonesa al rojo vivo** (el
    lingote ES una vela — ese es el guiño) + un par de chispas. Postura relajada y confiada.
  · **pass (`logo3_standard`)** — levanta la pieza terminada: la misma vela, ahora **acero pulido y
    frío, perfecta**, reflejando la luz; sonrisa de lado, martillo colgando. Orgullo tranquilo, no
    celebración exagerada.
  · **fail (`logo4_standard`)** — la pieza **partida sobre el yunque** (dos mitades + una esquirla
    saliendo), él con mueca de "otra vez será", martillo aún en alto. **Sin drama ni humillación** —
    el herrero rompe piezas todos los días.
  ⚠️ **Requisitos para el ilustrador:** (1) el personaje debe **conservar su flecha AZUL** — la
  variante de modo oscuro se genera recoloreando ese azul a naranja `#dd9100`; si cambia el color de la
  flecha hay que hacer el dark a mano (`recolor=False`). (2) **Nada de zonas blancas cerradas que sean
  fondo** (axilas, huecos entre brazos) — ver la lección del recorte del 18-jul; los blancos legítimos
  (ojos, dientes, chispas, humo) sí se quedan. (3) Fondo transparente, 6 archivos:
  `logo{2,3,4}_standard[_dark].png`. **Alternativas descartadas:** el maquinista de precisión (más frío)
  y el afinador de la placa (demasiado críptico).
- **Rising Sun** ✅ — un solo look para light/dark (cream washi + disco de sol + banda diagonal + kanji).
- **Pole** ✅ (F1 blueprint) — **dos** looks, uno por modo: ☀️ light = papel de taller (grafito + acento
  rojo), 🌙 dark = cianotipo azul (líneas blancas + acento azul); ambos con grid, plano técnico del F1,
  mapa de circuito, corte de neumático, textura+viñeta. Precedente de que un camo SÍ puede tener
  variantes light/dark propias (no todos son "un solo look" como Rising Sun).
- **Obsidian Gold (Premium)** ✅ — un solo look (obsidiana negra + arcos Art Déco dorados concéntricos +
  zigurat, esquina inf-izq). Pasó por 3 rondas de iteración de diseño (geométrico→telaraña rechazado→
  conceptual "La Bóveda/Reservas de oro/Bull dorado" ofrecido→usuario eligió volver a un Art Déco pulido
  sin líneas finas = "A3 arcos+zigurat"). Lección: el usuario rechaza patrones que parezcan "telaraña"
  (líneas finas radiando) — para dorado/lujo usar formas MACIZAS/rellenas o vetas orgánicas, no líneas.
- **Fourth of July (USA Special)** ✅ **(theme aprobado como dirección, 2026-07-24 — falta retoque fino
  en la PC del usuario + mascotas pass/fail).** Escena navy al atardecer: **Estatua de la Libertad** (antorcha
  dorada) abajo-izq + **horizonte de monumentos DC** (Monumento a Washington, Capitolio, Lincoln/Casa Blanca,
  retroiluminado) + estrellas + estrella-emblema. **Monumentos REDIBUJADOS (2026-07-25):** la 1ª versión de la
  Estatua de la Libertad "parecía dibujo de niño" → rehecha en SVG procedural (`scratchpad/build_fourth_scene.py`):
  pedestal escalonado, túnica esbelta con pliegues, corona de 7 picos, tablilla pegada al costado, brazo en alto
  (acortado a pedido) con antorcha. Monumentos DC limpios (obelisco, cúpula del Capitolio con columnas, Lincoln con
  columnata). La antorcha lleva una **llama estática dorada** en el SVG. Capa `center bottom / 100% auto`.
  **Camo ESPECIAL con animación:** fuegos artificiales (`#nx-fw-layer`, `<script>` propio gateado a
  `body.camo-fourth`) — **reposicionados (2026-07-25) más arriba y hacia los lados** (~56% en las columnas
  laterales altas, resto en la franja superior central) para que los paneles —dibujados por encima de la capa
  de fuegos— NO los tapen; pausados/ocultos fuera de `camo-fourth` o en Synapse, off bajo `prefers-reduced-motion`.
  ⚠️ **Se PROBÓ y se DESCARTÓ una llama animada de la antorcha** (`#nx-torch`, radial-gradients parpadeantes): al
  usuario le pareció fea ("bola de Dragon Ball") → eliminada. NO re-agregar. La llama estática del SVG se queda.
  ⚠️ **Fix Capitolio (2026-07-25):** el 3er monumento (cúpula) tenía el domo muy PLANO (arco rx=70 vs
  media-cuerda 52 → apex ~y189) mientras el tambor/estatuita estaban en y140-176 → parecían un "rectángulo
  flotando". Fix: domo alto (rx=52=media-cuerda, ry=60 → apex ~y138) + base-tambor, todo conectado.
  ⚠️ **🔴 LECCIÓN CRÍTICA — el recorte del 18-jul DESTRUYÓ arte (descubierto y revertido 2026-07-25):** el
  commit `e86ff8f` ("clear enclosed background pockets") borró **bolsas blancas encerradas** de forma
  automática y se comió **arte legítimo en CASI TODAS las botargas**: interiores de llamas, relleno de humo,
  blancos de velas. Medido: `logo3_blackflag` −39.305px, `logo4_blackflag` −27.307px (el barco en llamas
  perdió el relleno de casi todas las llamas —incluidas las tablas flotando— quedando solo contornos naranjas
  sobre el pergamino), `logo4_pole` −27.197, `logo3_naval` −26.436, `logo3_mission` −22.206, `logo4_naval`
  −22.142, `logo4_premium` −20.202, y −4.000/−9.000 en todos los welcome. **Fix:** restaurados los 32 PNG
  desde `5b1c773` (revisión previa al recorte) y re-aplicados SOLO los arreglos verificados por el usuario
  (fourth: punta+axila+estrella; blackflag welcome: axila; blackflag pass: 3 bolsas reales entre piernas y
  bajo brazos). **REGLA: NUNCA correr un borrado automático de "blancos encerrados" sobre estas botargas** —
  el personaje y su escenario tienen blancos legítimos por todos lados (llamas, humo, velas, arroz, guantes,
  ojos). Cualquier recorte debe ser por semilla puntual + verificación visual del antes/después.
  ⚠️ **Fix botargas welcome (recorte viejo, 2026-07-25):** el cutout del 18-jul dejó defectos en las
  botargas del "muñeco-flecha": (a) la **punta inferior de la flecha** transparente (se veía el fondo) y
  (b) la **axila izquierda** rellena de BLANCO (debía ser transparente). Corregido en **fourth** (punta
  rellenada continuando las franjas con el ángulo real −9.5°; axila borrada) y **blackflag** (axila
  borrada, light+dark). Las otras (mission/naval/premium/rising_sun) NO tienen el defecto: sus poses/
  disfraces (traje, rifle, brazos cruzados, guante dorado) cubren la axila; sus blancos encerrados son
  features legítimas (verificado con detector de bolsas blancas encerradas). Scripts en `scratchpad/`
  (`fix_tip_stripes.py`, `clear_armpit.py`, `build_fourth_scene.py`). Regla: NO tocar la mano/guante.
  ⚠️ La estatua queda parcialmente detrás del sidebar en
  `/app` (translúcido, se ve tenue); plena en welcome/móvil. Patrón iOS-safe (body transparent +
  `::before` fixed, como Premium — NO `background-attachment:fixed`). Logo blanco (invert de `logo_t`) en ambos
  modos. Un solo look navy; mascota welcome ya está (dark+light), **pass/fail las sube el usuario**. ⚠️ **Lección
  de cableado:** un comentario en el CSS que contenía literalmente `</body>` hizo que el patcher insertara el
  `<script>` DENTRO del `<style>` (el `.replace('</body>')` pegó en la 1ª aparición) → CSS pintaba pero el JS no
  corría. Fix: nunca poner el texto del anchor dentro del contenido insertado + insertar en el ÚLTIMO `</body>`
  (`rpartition`) + assert de `<script>` count. Verificado end-to-end en `/app` real (layer creado, fuegos vivos).
- **Naval (militar/táctico)** ✅ **(2026-07-24).** ⚠️ El mascota `naval` NO es náutico: es un **soldado de
  combate** (casco, chaleco táctico, lentes de aviador, fusil disparando velas verdes) → el theme es
  **militar**. Elegido de 3 variantes (A camuflaje / B HUD-radar / C honor olive+oro): el usuario eligió
  **A = camuflaje de campo** (blobs orgánicos olive/khaki/verde-oscuro/tan, acento ámbar `#e0872f` que pega
  con el equipo del mascota). Un solo look; iOS-safe (body transparent + `::before` fijo); logo blanco
  (invert de `logo_t`). Mascotas welcome/pass/fail ya estaban. **Condecoraciones de general AGREGADAS
  (2026-07-25):** el usuario probó con Gemini pero prefirió evitar la watermark → se armó un cluster de
  medallas **en SVG procedural** (código, `scratchpad/medals.py`) con oro degradado (radialGradient),
  brillos y **sombras (`feDropShadow`)** — 4 estrellas de rango + ribbon rack + 3 medallas (estrella con
  rayos, cruz patée, estrella con corona). Se cableó como capa del `::before` del naval (`right 1% bottom
  1% / 250px`). **Aprendizaje: los filtros/gradientes SVG SÍ renderizan cuando el SVG va como
  `background-image` data-URI** (verificado en `/app` real). No hace falta Gemini para arte así.
- **Mission (espacial/NASA)** ✅ **(2026-07-24).** Mascota = **astronauta** con cohete "NASDAQ BULLISH"
  → theme espacial. Elegido de 3 variantes (A cosmos/nebulosa / B control de misión HUD / C to-the-moon):
  el usuario eligió **A = cosmos** — espacio profundo navy-púrpura + nubes de nebulosa (radiales púrpura/
  magenta/azul) + campo de estrellas + **planeta con anillo** (arriba-der), acento cian `#5fd0ff`. iOS-safe
  (body transparent + `::before` fijo); logo blanco (invert de `logo_t`). Mascotas ya estaban. Sin animación.
  **DOS looks (patrón Pole, 2026-07-25):** el cosmos es ahora SOLO el modo oscuro (`body.camo-mission:not(.light)`);
  el **light** es una **escena de MARTE artística** pedida por el usuario: atmósfera BLANCA arriba (no negra),
  **estrellas como destellos de 4 puntas** (`spark()`, no círculos — pedido explícito), cordilleras superpuestas
  rojo/naranja/marrón (`rFar/rMid/rNear/rFg` con bandas de niebla `fog`) y un **valle-cañón en primer plano**
  (paredes rojas enmarcan los lados, centro abierto para legibilidad). Vars Marte: `--bg:#f7e6d6`,
  paneles frosted `rgba(253,247,240,0.56/0.66)` (translúcidos para que se vea la escena), `--text:#3a2113`,
  `--accent:#c8542a`. Logo **por defecto (oscuro)** en Marte, blanco solo en cosmos. Verificado en `/app` real:
  light→`camo-mission light` (Marte, filtro logo none), dark→`camo-mission` (cosmos, logo invert).
  ⚠️ **LECCIÓN DE ESCALADO (2026-07-25):** la 1ª versión de Marte usaba UN solo SVG (cielo+montañas)
  con `center bottom / cover` → en monitores de otra relación de aspecto el `cover` escalaba la escena y
  el **horizonte flotaba a media pantalla** ("montañas muy hacia arriba"). Fix ROBUSTO = **separar en capas
  ancladas**: montañas en su propio SVG (solo cordilleras+niebla, fondo transparente) sized `center bottom /
  100% auto` (la altura depende SOLO del ancho, nunca del alto de la ventana → horizonte siempre pegado al
  fondo en cualquier aspect ratio); estrellas en otro SVG `center top / 100% auto`; sol + glow del horizonte
  como radiales CSS; cielo `linear-gradient(#fff→#f0cdb2)` de fallback. Estrellas también ADELGAZADAS a ~16
  con rechazo por distancia mínima (150px) — antes 78, se veían apiñadas/poco creíbles. Verificado en 1680×780
  (ancho/bajo) y 1200×1000 (alto): montañas siempre abajo. **Regla general: nunca uses `cover` para una
  escena con horizonte; anclá la tierra con `100% auto center bottom`.**
- **Blackflag (pirata)** ✅ **(2026-07-25).** Mascota = pirata (tricornio con calavera, parche, loro).
  Elegido de 3 variantes (A mapa del tesoro / B Jolly Roger / C galeón): el usuario eligió **A = mapa del
  tesoro** — pergamino cálido + rosa de los vientos (abajo-der) + ruta punteada + islas + **X roja
  "marks the spot" abajo-izq** (agregada a pedido). Acento rojo `#a5401f`. **LIGHT_ALWAYS** como rising-sun
  (pergamino claro en ambos modos; solo la mascota flipea vía `.camo-night`). ⚠️ **Ojo:** LIGHT_ALWAYS/
  DARK_ALWAYS están **DUPLICADOS** en index.html — hay que agregar el slug en LAS DOS copias: el pre-paint
  (`LIGHT_ALWAYS` ~línea 4375) **y** la función apply-theme (`LIGHT_ALWAYS_T` ~línea 9422); si solo tocás
  una, el modo oscuro pierde la clase `light` y los paneles salen oscuros sobre el pergamino. Mascotas
  cambiadas a keyear por `:not(.camo-night)`/`.camo-night` (no `.light`) por ser LIGHT_ALWAYS.
  ⚠️ **Fix de escalado (2026-07-25, mismo problema que Marte):** la ruta punteada y las islas usaban
  `center / cover` → se agrandaban/recortaban distinto según el aspect ratio del monitor. Cambiadas a
  `center / 100% 100%` → composición del mapa idéntica en cualquier pantalla (la leve distorsión es
  imperceptible en trazos abstractos). La X (104px) y la brújula (190px) ya eran px fijos anclados a la
  esquina → robustas, no se tocaron. Verificado 1680×780 y 1200×1000.
  ⚠️ **Fix ruta→X (2026-07-25):** al mover la X a su propia capa de esquina abajo-izq, la ruta punteada seguía
  terminando arriba-derecha → la X quedaba "solitaria sin sentido". Rediseñada: el rastro sale de la brújula
  (abajo-der), serpentea por el mapa y **termina justo en la X** (canvas ~128,650) + 3 dotscillos que entran a
  la X. Dasharray `0.5 15` con `stroke-linecap=round` = puntitos de mapa del tesoro.
  ⚠️ **Fix definitivo X (2026-07-25):** la X era un elemento SEPARADO anclado a la esquina con tamaño FIJO
  (`left 4% bottom 9% / 104px`) mientras la ruta usaba `100% 100%` (porcentajes) → en pantallas grandes la
  ruta (que escala) se alejaba de la X (fija) y "no llegaba ni cerca". Solución: **la X ahora se dibuja
  DENTRO del mismo SVG de la ruta** (canvas ~125,665), así ambas escalan juntas con `100% 100%` y el rastro
  termina SIEMPRE en la X en cualquier pantalla (verificado 1440 y 1920). Se eliminó la capa X de esquina.
  Regla: elementos que DEBEN tocarse van en el MISMO sistema de coordenadas (mismo SVG), nunca uno con
  `100% 100%` y otro con px fijo anclado a la esquina.
- **High Noon + The Alchemist** ✅ **(2026-08-22, v2 — los 2 primeros camos de TIENDA).**
  🔴 **La v1 (calle del oeste / mesa de laboratorio) la tachó el dueño con razón:** *"prácticamente
  iguales al de Egipto e iguales entre ellos… color arena en light y de noche en dark"*. El
  diagnóstico que queda: eso era la fórmula de los camos de RULETA (paisaje en franja baja +
  recolor nocturno). **Los camos de TIENDA buenos son un MATERIAL, no una escena** (Pole =
  plano/cianotipo, Standard = acero, Premium = obsidiana, Blackflag = mapa) **y sus dos looks
  cambian de material, no de hora** (patrón Pole/Mission). Se le ofrecieron 3 variantes por camo,
  eligió las recomendadas:
  · **High Noon = CUERO DE TALABARTERÍA**: la piel entera con su veta (tile repetido cuyos poros
    no tocan los bordes), costura doble de guiones en los 4 bordes EN CSS PURO (abraza cualquier
    viewport sin estirar puntadas), conchos de latón en las esquinas, cenefa repujada abajo
    (volutas + abanicos + fondo picado; surco = truco de Standard, dos <use>) y la ESTRELLA DE
    SHERIFF herrada a fuego, MACIZA (de puro contorno se perdía de noche). ☀️ cuero miel nuevo /
    🌙 el mismo cuero engrasado espresso con hilo y latón dorados.
  · **Alchemist = LA PÁGINA DEL GRIMORIO**: el MISMO dibujo en dos tintas — ☀️ ferrogálica + pan
    de oro sobre vitela / 🌙 FOSFORESCENTE (esmeralda con halo + oro encendido sobre púrpura casi
    negro; el halo = el mismo path gordo y translúcido debajo, sin filtros). Dibujo: diagrama de
    la Gran Obra abajo-izq (cuadratura del círculo + 4 elementos + el oro al centro, trazos
    GRUESOS — nada de telaraña), la receta de símbolos alquímicos como geometría (sin <text>),
    márgenes de cuaderno en CSS puro, y el alambique a tinta goteando oro en la esquina.
  · ✅ **Botargas de HIGH NOON entregadas por el dueño y cableadas (2026-08-23):** welcome = el
    sheriff con su estrella de TRADING POLICE · pass = a caballo con el lazo (¡YIJAAH!) · fail =
    el tropezón con el matojo. Recorte con el mapa numerado: axila del welcome (id 281 — el
    defecto por defecto, otra vez), interior del lazo + huecos del rollo de cuerda en el pass
    (las letras YIJAAH y sus blancos SE QUEDAN), y 25 huecos entre las ramas del matojo en el
    fail (las nubes de polvo y el zapato que entra en él NO se tocan). Keyea por `.light` como
    nile; URLs por `estatico()`. `test_botargas_nuevas.py` ahora cubre 3 camos: **69/69**.
  · 🔴 **FALTAN LAS BOTARGAS DE THE ALCHEMIST** — el dueño no las había generado al cerrar la
    sesión del 2026-08-23 (dijo que volvería en 1-2 semanas; pidió EXPLÍCITAMENTE recordárselo).
    Mientras, Alchemist usa el muñeco-flecha por defecto y se vende igual. Propuestas ya dadas:
    welcome = alquimista con matraz esmeralda y grimorio · pass = lingote/matraz de oro · fail =
    el matraz explotado (hollín + círculos limpios de las gafas). Al llegar: mismo proceso
    (limpia_botarga_nueva con mapa, botarga_oscura, bloque CSS keyed por .light tras el de
    highnoon, extender test_botargas_nuevas).
  Cableado: `CAMO_READY` + swatch con piel + `PREV_ALT` (⇆); bios ×4 ya existían. 8 imágenes
  regeneradas (`scratchpad/gen_hn_alq.py`, que ahora saca el stack de capas DEL index.html —
  sirve para cualquier camo futuro). Tienda 18/18 + rodada 23/23 + viaje 13/13.
  🔑 **El riel de PayPal NO se cablea por camo** (pregunta del dueño): `camo_store_price()`
  devuelve None para todo slug fuera de `CAMO_READY` y `/api/camo/buy` rechaza ahí — un camo sin
  arte no se puede comprar ni llamando al endpoint a mano; al entrar en `CAMO_READY` queda
  comprable solo, con su precio y su ventana festiva si aplica.
  ⚠️ **Trampa del generador de pieles (2 lecciones):** (1) re-correr un builder cortaba hasta el
  ancla de Blackflag y SE COMÍA los bloques insertados en medio — el corte va hasta el SIGUIENTE
  `/* ═══`, no hasta un ancla fija; (2) un data-URI de SVG dentro de `style='…'` (comilla simple)
  **parte el atributo en la primera comilla del URI** y la declaración entera muere — ni el
  gradiente pinta, y el guard de stddev NO lo caza porque el gradiente solo ya varía. El CSS de
  prueba va SIEMPRE en `<style>`.
- **Pendientes de theme:** 10 slugs más sin arte de mascota
  aún. Antes de diseñar cada uno: preguntar 1ª idea/temática al usuario (así arrancó Pole: "plano de
  construcción de F1"), ofrecer 3 variantes, iterar sobre la elegida, cablear igual que Pole/Premium
  (bloque CSS con vars `--bg/--surface/--card/--border/--border2/--text/--muted/--accent/--accent-h/
  --win/--loss/--be`, sección insertada en `index.html` tras el bloque del camo anterior, slug agregado a
  `CAMO_READY` en app.py). Validar con: parse Python + Jinja + UN screenshot real (no artifact — no le
  carga en el iPad) del CSS ya insertado antes de pushear.
- **⚠️ REGLA DE TOKENS para previews visuales (pedida por el usuario 2026-07-19):** un solo prompt de
  "mostrame 3 variantes" puede consumir ~80% del límite de 5h si la conversación ya viene cargada de
  imágenes previas — el costo de cada turno escala con TODO el historial, no solo lo nuevo. Mitigar
  con: (1) screenshots a resolución reducida por default (~900-1000px ancho, density_factor=1, NO 2000px+
  a doble densidad — eso ya se usó de más en esta sesión); (2) preferir iterar sobre 1 variante a la vez
  en vez de tirar 3 de entrada, salvo pedido explícito de "3 opciones"; (3) al cerrar un camo (theme+
  mascota cableados y pusheados), sugerir activamente arrancar SESIÓN NUEVA para el siguiente — todo lo
  hecho ya vive en el código y en este archivo, no se pierde nada, solo se evita re-arrastrar imágenes
  viejas en el contexto de cada turno futuro.

**✅ PRODUCTS MENU — acordeón inline en el sidebar (2026-07-18, RESUELTO).** En `/app` (shell Aurora)
el menú Products vive DENTRO del `.ag-sidebar` como **acordeón inline** (`position:static`) que se expande
debajo de la pestaña Products (que es la ÚLTIMA tab). **Scroll del sidebar = condicional (revisado 2026-07-25):**
`.ag-sidebar` tiene `max-height:calc(100vh-44px); overflow-y:auto; overflow-x:visible` (~línea 24758) → el
scrollbar propio **solo aparece cuando el contenido no cabe**. Con Products abierto el contenido mide ~912px:
en pantallas altas (≥~960px) cabe TODO sin scroll; en laptops bajitos (768–900px) aparece el scroll interno
y **Settings (último item) queda accesible DENTRO del sidebar**. ⚠️ Se probó quitar el scroll del todo
(`overflow:visible`, sin max-height) pero en pantallas bajas Settings quedaba colgando abajo, solo visible
scrolleando TODA la página (sticky más alto que el viewport) → revertido. El scroll condicional es lo correcto.
⚠️ **NO reintentar flotar el menú:** hubo 4 intentos rechazados — (1) `position:fixed` en su
lugar (el `backdrop-filter` del sidebar lo atrapa/recorta), (2) pop-out a `<body>` como flyout AL LADO
("debe abrir hacia abajo, no a la derecha"), (3) dropdown abajo con lift-up (tapaba logo/tabs de arriba),
(4) 2 columnas (se partía, feo). El pop-out SIEMPRE terminaba como panel blanco flotante que **se
superponía** al panel del sidebar (Products es la última tab → el menú caía sobre la cola del sidebar).
Solución final = **inline original** (IIFE ~línea 11029: `place()` hace `return` si
`menu.closest('.ag-sidebar')`; solo posiciona fixed en el fallback sin-Aurora). Agregado:
`btn.scrollIntoView({block:'nearest'})` al abrir. Verificado en navegador real (Playwright + app logueada):
`inSidebar:true`, `withinSidebar:true` (0 overlap), sidebar scrollea y revela todos los items. Móvil igual.

**✅ SYNAPSE WEB — i18n CABLEADO (2026-07-17).** Bug reportado: el mapa/dossiers de Synapse
salían en inglés bajo ES/FR/PT. Causa: las traducciones YA existían completas y auditadas
(`synapse_content_{es,fr,pt}.json` 41 temas + `synapse_translations.py` TITLES/METHODS) pero **solo
las consumía el PDF** — el flipbook web leía únicamente el inglés de `synapse_library.js`. Fix: endpoint
`/api/synapse/l10n/<lang>` (titles+methods+content, cache 1h; en/desconocido→pack vacío) + en el
cliente `loadSynL10n()` (cache por idioma, fallback total a inglés si falla) con helpers
`synMeth/synTitle/synSub` aplicados en: galaxia (nombres+subs), clúster (título barra, núcleo,
etiquetas neuronas), píldora de progreso (clave nueva `LX.pillOf`), cabecera del dossier y
**merge campo-a-campo en `buildPages`** (`Object.assign({}, base, override)`). El pack se espera en
`open()` (`Promise.all`) → primer render ya traducido; wrap de `window.applyLanguage` re-renderiza si
cambia idioma en vivo. Cerebro 3D: labels flotantes vía `METH_L10N`+`methLabel()` (SMC / ICT igual en
todos). Subs de metodología (5 strings) traducidos inline (`SYN_SUBS`). Diagramas SVG quedan con labels
EN (misma convención que el PDF). NO tocado: `SYNAPSE_TO_QUIZ_TOPIC` (keyed por label EN — no traducir
el CATALOG en sí, solo en render).

**🟡 DAILY CHALLENGE — reconstrucción del banco (EN PROGRESO 2026-07-02).** Hallazgos: (1) el Daily
tomaba preguntas `lv:'advanced'` (169) del QUESTION_BANK — NO cumple el plan del usuario (200+
ultrahardcore dedicadas); (2) 🔴 BUG anti-trampa CORREGIDO: el modal Daily mostraba opciones SIN
barajar y 397/398 preguntas del banco tienen la correcta en posición A → pulsar siempre la primera
farmeaba la ruleta (fix commiteado: shuffle de display, `data-i` conserva índice original, server
intacto). Decisión del usuario: pool NUEVO dedicado **`DAILY_BANK`** (en `index.html`, justo antes
de HARDCORE_SCENARIOS), **SIN gráficos**, talla ultrahardcore, 4 opciones TODAS coherentes (ninguna
descartable sin saber), **longitud pareja entre opciones** (no adivinar por el largo), EN/ES/FR/PT
con léxico natural. **NO CABLEADO aún**: el Daily sigue tirando de advanced hasta llegar a 200+;
entonces flip en UN commit (cliente `POOL` ~línea 20380 + `_daily_correct_index()`/`_ADV_ANS` en
app.py → `daily` del JSON + regenerar key). Infra lista: `tools/validate_daily_bank.js` (paridad de
idiomas, exactamente 1 ok, ratio de longitud ≤1.45, distribución de posición correcta) y
`tools/extract_quiz_key.js` extendido (emite `daily` en `quiz_answer_key.json`). **Progreso:
200/200 ✅ COMPLETO + FLIP CABLEADO (2026-07-10)** — lote 1 (ICT×6, SMC×2, Wyckoff×2) + pasada de revisión (3 fixes: "un Asia amplia",
"tout autant", calco thin→mercado delgado/mince/raso) + lotes 2-3 (liquidez interna→externa, LPS
por esfuerzo, esfuerzo-vs-resultado, HCH-vs-demanda-HTF, PRZ-vs-displacement, PD-arrays+inducement,
BOS-vs-grab, SMT, envolvente-vs-ubicación, independencia de confluencias) + lote 4 (breaker-vs-
mitigation-block, Power of Three vs open diario, Fase B construye la causa, liquidez de trendline,
consequent encroachment, SOW, objetivo-medido-vs-FVG-HTF, low-resistance run, strong-vs-weak high,
reacumulación-vs-distribución) + lote 5 (Judas swing, ranking de OBs, ST-vs-Spring, ápex del triángulo, jerarquía de swings, niveles obvios/concentración) + lote 6 (turtle soup, test post-UTAD, inducement-sobre-POI, FVG-en-premium, doji/ubicación, JAC/BUEC, dealing range liquidez-a-liquidez, Asia H/L, salud del markup, ABCD extendido) + lote 7 (rejection block wick-vs-body, silver bullet como filtro no gatillo, flip demanda→oferta tras displacement, wick vs body en order blocks, HTF wick vs LTF trend/sweep semanal, shortening of the thrust, BC exige el AR, rising wedge como motor desacelerando, island top inventario varado, Gartley-vs-Bat vía punto B) + lote 8 (OTE 0.62–0.79 vs equilibrium, liquidity-void-vs-FVG, POI-origen-tras-CHoCH, retests erosionan el nivel, comprador-de-ruptura-como-liquidez, UT-vs-UTAD por fase, graduación del spring por volumen, anatomía de bandera contra-tendencia, megáfono/ensanchamiento, cup-and-handle shakeout del asa) + lote 9 (NWOG como array de referencia, inversion FVG, stop estructural bajo el swept low, relative equal lows, preliminary support, LPSY por pobreza del rally, acumulación sin spring/LPS, three drives, advance block vs tres soldados, clasificación de gaps por contexto) + lote 10 (perfil semanal low lunes-martes, re-anclar dealing range tras sweep, seek-and-destroy como no-trade, confirmación LTF como filtro-con-precio, PDH/PDL liquidez de consenso, Fase D cambio de régimen, conteo horizontal P&F, triángulo descendente doble filo, throwback sano callado, Crab extensión 1.618 XA) + lote 11 (CBDR proyecciones stdev, market maker model curva simétrica, escalar POIs anidados como UN trade, definición de displacement, mitigación fractal wick-1m-en-zona-diaria, Composite Operator como lente, stepping-stone count, parábola sin pisos, inside bar compresión, pendiente del neckline HCH) + lote 12 (IPDA lookbacks 20/40/60 como ventana de escaneo, mandato dual liquidez-o-rebalanceo, compresión-erosiona-el-POI, zonas de velas de noticias degradadas, absorción bajo resistencia, Fase E caja de herramientas de tendencia, entradas Wyckoff junto a su invalidación vs breakout, rounding top por ritmo, pennant-vs-triángulo-simétrico por escala/anclaje del objetivo, piercing line regla del 50%) + lote 13 (midnight open compra-en-descuento, balanced price range, correlación EURUSD+GBPUSD es UN trade, persistencia de FVGs como salud de tendencia, ilusión del breakeven, techos callados vs pisos climáticos, tiempo≠causa, el conteo no es deuda, V-reversal sin apoyo estructural, HCH fallido señal-en-reversa) + lote 14 (London Close retracement del perfil, procedimiento del draw sesgo→camino, re-entrada si-la-idea-sobrevive, parciales en piscinas internas, tríada spread/cierre/volumen, piramidación de campaña Wyckoff, fuerza comparativa en reacciones, diamond top, calidad de trendline por toques/pendiente, segundo pico del doble techo por participación) + lote 15 (AMD/Power-of-Three fractal, consequent encroachment de la mecha grande, CHoCH exige sweep previo, riesgo se elige-no-se-mide-en-pips, primer movimiento de la noticia como manipulación, creeks menores vs creek mayor, método de 5 pasos de Wyckoff mercado-primero, morning star anatomía del cuerpo medio, dead cat bounce vs base real, hammer con/sin volumen) + lote 16 (unicorn model breaker+FVG mismo nivel, propulsion block demanda apilada, first presented FVG como referencia de apertura, swing failure pattern liquidez tomada-y-rechazada, macros ICT ventanas de reloj :50–:10, order block mitigado-vs-no-mitigado por órdenes gastadas, Fase A clímax de venta detiene el markdown, terminal shakeout más violento que un spring, falling wedge desaceleración alcista, evening star estructura de tres velas) + lote 17 (los 4 estados de entrega como máquina secuencial, rango con ambas piscinas externas purgadas=mapa gastado, opening range gap RTH settlement→open, POIs opuestos frescos encierran al precio=no-trade hasta displacement, liquidez=órdenes en reposo vs volume profile=negocio hecho, Fase C tiene shelf-life (spring+test sin SOS pronto=etiquetas en revisión), volumen relativo a la norma de sesión/reloj, harami-vs-inside-bar cuerpos-vs-rangos, marubozu contra resistencia sin follow-through=absorción, ruptura de trendline≠reversión regla 1-2-3) + lote 18 (NY lunch=digestión programada la tarde decide, por-qué-reaccionan-las-zonas=órdenes límite pasivas sin llenar, zona perforada durante noticia=falla de ejecución no de idea (reclaim=pista), grado de la zona fija su reloj (zona diaria se juzga en días), overhead supply=compradores atrapados venden en su empate, las 3 leyes de Wyckoff=dirección+magnitud+advertencias (una sola no basta), calidad del AR pronostica el rango (fuerte=acumulación débil=rebote de vacío), firma de volumen del HCH (hombro derecho pesado contradice el techo), channel overthrow=exceso terminal no aceleración, canal-vs-cuña=paralelismo codifica presión) + lote 19 (CISD close-vs-wick en la entrega, proximal-vs-distal de una zona (fill-rate vs confirmación), varrida wick-only vs close-through (cuál atrapa más), triángulo simétrico sin dirección inherente (sigue la tendencia previa), no-demand bar (esfuerzo-resultado en velas alcistas), stopping volume a mitad de caída (climax en miniatura sin necesitar rango previo), ease of movement (deslizamiento fácil=poca oferta vs ascenso trabajoso=vendedores activos), ADR como gobernador de objetivos realistas no un techo duro, abandoned baby (aislamiento total=doble abandono de posiciones), kicker de dos velas (ausencia total de solape=capitulación forzada)) + lote 20 (buy-side liquidity=de quién son las órdenes (stops de cortos+rupturas, no zona de compra), opens de velas de expansión como soporte del order flow, calificar la reacción del POI (displacement valida / deriva advierte), half-way point de Wyckoff (corrección que pierde el 50% del avance pone en duda la tendencia), la ola como unidad de la cinta (comparación ola-a-ola expone quién gana fuerza), rising three methods (contención=continuación), misma barra ancha nacida temprano-vs-tarde (iniciación vs clímax candidato), el patrón solo existe al cierre (envolvente intrabar puede evaporarse), targets del mapa no de R-múltiplos (el mercado no ve tu R), picos gemelos necesitan tiempo entre sí (2 campañas vs 1 consolidación)) + lote 21 (el setup expira con su ventana (tesis de Londres muerta en NY open aunque el precio no invalidara), swing point necesita definición mecánica (test fractal — sin ella todo BOS/CHoCH hereda ambigüedad), setup A+ 3 min antes del CPI=suspendido (el edge asume flujo ordenado), los 9 tests de Wyckoff=puerta de convicción no gatillo, la zona retrospectiva (backtest con zonas retroajustadas mide hindsight no método), asimetría de volumen en rupturas (subir necesita combustible/caer solo ausencia de bids — E&M), "más compradores que vendedores" es imposible (volumen 1:1; agresión contra liquidez en reposo), filtro del 3% de E&M=prima de seguro contra whipsaw, estacionalidad=viento no timón (confluencia de fondo bajo estructura), confirmación vive DEBAJO del marco de la zona (shift del mismo grado consume la reacción por construcción)) + lote 22 FINAL ×3 (kill zones presuponen participación (semana muerta navideña=reloj sin mecanismo), la ilusión del stop de fin de semana (stop no ejecuta en mercado cerrado — riesgo de gap, decisión de TAMAÑO no de stop), gap a través de la neckline=completación enfática no defecto). Histograma FINAL [50,51,51,48]. Sesgo longitud final 91/200=45.5%. **FLIP EJECUTADO Y VERIFICADO (2026-07-10, aprobado por usuario):** cliente `const POOL = DAILY_BANK` (línea ~25644) + server `_ADV_ANS`→`_DAILY_ANS` cargado de `data.get('daily')` en `_load_quiz_key()` y usado en `_daily_correct_index()` — UN commit. Verificación hecha: (1) acuerdo BIT-A-BIT cliente-vs-server (picker JS extraído y replicado en node vs picker Python: misma n=200, mismo poolIdx, mismo índice correcto para el seed del día); (2) end-to-end con test_client: login → /api/daily/start → /api/daily/answer con el índice correcto → `correct:true, streak:1`. El Daily ya sirve las 200 nuevas. Documento de revisión con las 200 Q&A entregado al usuario (fuera del repo). **Lote 19 escrito por Fable — auditoría propia ANTES de commitear encontró que 9 de 10 preguntas originales duplicaban temas ya cubiertos en el lote 13** (medianoche/discount, balanced price range, correlación-un-trade, persistencia FVG, ilusión breakeven, techos-callados, tiempo≠causa, conteo≠deuda, V-reversal, HCH-fallido) — las 9 fueron REESCRITAS con temas 100% vírgenes (verificados con grep contra los 176 títulos existentes antes de escribir) antes de pushear; ninguna duplicada llegó a producción. 3 fallos de longitud detectados y corregidos (ratio >1.45 en ES/FR/PT) antes de commitear. Sesgo longitud: 74/166 (44.6%, venía de 47%) — seguir favoreciendo correctas cortas/medias. **Nota: lotes 15-16 los escribió Opus 4.8** (Fable llegó a su límite diario); mismo estándar, validadores OK, lote 16 con 0 warnings de longitud. **Audit Fable 2026-07-09 de lotes 15-16:** lote 15 impecable (10/10); en lote 16 se cazó 1 repetición real — "IRL→ERL delivery" duplicaba la #11 (internal-vs-external rotation) → REEMPLAZADA por "ICT macros" (tema virgen). Adyacencias revisadas y OK (SFP≠sweep-and-reverse #2: cierre-adentro vs displacement; OB mitigado≠ranking #32: trampa "nivel probado" vs combo-intención; evening star y falling wedge = espejos canónicos de morning star/rising wedge con ángulo distinto — aceptados). Recurrente error de opción de-más (5ª opción / doble ok:true) — cazado y corregido en la #8 antes de commitear. Nota usuario 2026-07-03 (2ª vez): pidió confirmar que TODO tema sea de las metodologías del sitio — confirmado (todo es ICT/SMC/Wyckoff/patrones canónicos); al reportar cada lote, dar mini-glosario en español simple de los términos raros. ⚠️ Ojo con error recurrente al escribir opciones: `',ok:false}},ok:false},` duplicado en línea pt (pasó 3 veces, lotes 10/12) — revisar cierre `'},ok:X},` antes de validar. Sesgo de longitud: 45/96 correctas=más-larga (lotes 10-11 correctas CORTAS) — mantener mezcla. Nota usuario 2026-07-03: preguntó si CBDR/MMXM son ICT → confirmado que sí (canónicos, nivel mentorship); dijo que si no encajaban con los temas del sitio no servían — quedaron por ser ICT genuino. **Regla de diseño extra:** incluir correctas que sean afirmaciones FUERTES (no siempre la
de tono moderado) para matar la heurística de examen. Tras CADA lote:
`node tools/extract_quiz_key.js && node tools/validate_daily_bank.js` y commitear también el JSON.

**🟢 TESSERA — hub ANCLADO de ayuda (2026-07-24, v4 rediseño).** Teseracto RUBÍ pequeño (44px)
anclado abajo-derecha con nube de pensamiento comic ("¿Te echo una mano?" i18n×4, clickeable,
oculta <420px). ⚠️ **Fix i18n (2026-07-25):** la burbuja NO se re-traducía al cambiar idioma (se
veía en el idioma del page-load) — NO era del camo 4 de julio, era global. Causa: la IIFE de Tessera
solo llamaba `setBubble()` dentro de `appear()` (que no corre estando anclada) y **nunca enganchaba
`window.applyLanguage`** como el resto del sitio. Fix: wrap de `applyLanguage` (patrón estándar,
líneas ~22259/24044/24425) que refresca la burbuja siempre y re-`fill()`ea la Cámara si está abierta.
Verificado EN/ES/FR/PT. La Cámara ya se re-traducía sola porque `fill()` corre en cada `openOv()`. Reemplazó a los FABs de soporte y bug (ocultos vía CSS, JS inerte;
`window.__nxOpenBug` dispara el modal de bug desde adentro) y a las entradas Guía/Contacto/Tessera
del menú Products (Products = solo productos/planes/legal/settings). **La Cámara tiene identidad
visual PROPIA y FIJA** (igual bajo cualquier camo/tema, como Synapse): bóveda dimensional oscura,
paredes grid rubí con puntitos-estrella, título Orbitron blanco-caliente con halo rubí, labels
JetBrains Mono HUD, tarjetas-puerta numeradas 01-05 con brackets en esquinas (cero variables del
tema del sitio). **5 tools:** 01 Tessera AI Chatbot (dormida "Despierta pronto" hasta pagar
backend IA), 02 Guía de uso (/guide), 03 Teletransportador (tabs+páginas), 04 Soporte (/contact),
05 Reportar bug (modal real). La calculadora de riesgo se ELIMINÓ (decisión usuario). Módulo
reescrito limpio (sin código muerto del roaming); mecanismos anti-quirk de pintado INTACTOS
(fades rAF sobre element.style, attach en init()). Verificado por HTTP en navegador real.
**PENDIENTE:** cablear el chatbot cuando se pague la IA; valorar auto-ocultar la nube tras ~8s.

**🟢 TESSERA — asistente nativo del sitio (BASE HECHA 2026-07-24).** Idea del usuario: un "Toodles
de Mickey Mouse" para el website — teseracto dorado semi-animado que aparece/desaparece por el /app
(no invasivo, con estela) y al abrirlo forma una cámara 3D (paredes cerrándose una a una) con tools
dentro. **Nombre elegido: "Tessera"** (propuesto por Claude, estilo Ouroboros: teseracto + la ficha
de entrada de la antigüedad; alternativas descartadas: Nexus, Ouro). **TODO vive en UN solo bloque
`<script>` autocontenido al final de `index.html`** (inyecta su propio CSS `#nx-css`; borrar el
bloque = quitar la feature; `NX_NAME`/`NX_ENABLED` al tope). Base construida: (1) cubo viajero
(2 cubos wireframe anidados girando, glow+estela, 5 slots por bordes de pantalla, ciclo ~7.5s
visible + 11-28s oculto, pausa en quiz/synapse/overlay); (2) click → popover: Abrir / Fijarlo /
Dejarlo viajar / Ocultarlo (modo en localStorage `nx_mode`: roam|pin|hidden); (3) oculto → el FAB
de soporte (`#help-fab`) intercepta su click y ofrece: abrir Tessera / traer el cubo de vuelta /
contactar soporte; + entrada "Tessera" insertada en el menú Products; (4) overlay "cámara":
paredes de grid dorado suben secuencialmente (fondo→izq→der→techo) + glow de piso + hub con 5
tools: **El Oráculo** (chatbot IA de preguntas del sitio — tarjeta dormida "Despierta pronto"
hasta que el usuario pague/instale el backend), **Cámara de Riesgo** (calculadora de position size
FUNCIONAL: cuenta/riesgo%/stop + presets NQ $20, MNQ $2, ES $50, MES $5, YM $5, GC $100 + $/pt
custom, disclaimer educativo), **Teletransportador** (saltos a tabs del app + páginas),
**El Mapa** (/guide), **Ayuda Humana** (/contact) + selector de modo del cubo. i18n propio
EN/ES/FR/PT (`NX_T`, lee `scalpel_lang`), reduced-motion y mobile fallbacks.
**Pulido 2026-07-24 (v3, tras corrección):** (1) hub **coplanar** con la pared trasera (mismo
`translateZ(-238px)`, más angosto/bajo) → la perspectiva encoge ambos igual y el panel NUNCA se sale
de las paredes en ningún viewport. (2) Paredes = efecto original (**scaleY rise** desde el piso) **+**
el wipe del título "TRADEABLE ACADEMY" de la landing (**`clip-path` inset**), **COMBINADOS** en
`nxWall`/`nxCeil` (no reemplazados). Geometría original de las paredes laterales/techo (rotateY 55°,
sin translateZ) — se ven las 4. (3) **SOLO el cubo es RUBÍ** (`#e0244a`/`#ff5c78`; faces, glow, trail,
drop-shadow); **la Cámara sigue DORADA** intacta (paredes, paneles, tipografías). ⚠️ Error corregido:
un commit previo pintó TODA la cámara de rubí y reemplazó (en vez de combinar) el efecto de paredes —
el usuario NO pidió eso; solo el cubo rubí y COMBINAR efectos. (4) **Estela de estrellas**:
`trailBurst()` lanza ~7 estrellas rubí al aparecer el cubo (reduced-motion respetado).
⚠️ **Lección técnica (costó horas):** en esta página cargada de capas, cambios de opacity/display
vía CLASE/stylesheet sobre el root fixed NUNCA repintaban (quirk de Chromium; los estilos computados
y el hit-testing decían "visible" pero 0 píxeles) → la visibilidad se maneja con **fades rAF mutando
`element.style` directamente** y el attach va en `init()` post-DOMContentLoaded. Verificado
end-to-end con Playwright contra Flask real por HTTP (los tests file:// engañan). **PENDIENTE:**
cablear el chatbot del Oráculo cuando el usuario pague el servicio de IA; más tools (ideas
bienvenidas); persistencia server-side del modo; pulir slots en mobile.

**🚨 BUG ABIERTO — ERROR 500 en `/register`** (reportado 2026-06-23, prod IP cruda). Sin
investigar a fondo (sin acceso a logs). Sospechas: (1) `send_verification_email` lanza excepción
(SMTP/Gmail OTP); o (2) esquema PostgreSQL de prod desactualizado (faltan columnas
`terms_version`/`terms_accepted_at` o tabla fingerprints — falta migrar). Ver causa real con
`supervisorctl tail -f traderacelerator stderr` en el VPS y reproducir. **Bloquea registros.**

---

## 🟢 Mentorías + Kill Zones (rama actual)

**Kill Zones (KZ): ✅ TERMINADO.** Estética armonizada con la marca (grafito+dorado, borde con
gradiente como el listón de Mentorías). Horarios según indicador del usuario: NY AM 9:30–11:00,
London 2–5, Asia 20–00, Lunch 12–13, NY PM 13:30–16, SB1 3–4 / SB2 10–11 / SB3 14–15. Tooltip de
hover con hora exacta ET + local. Las bandas van en ET para todos; reloj/hover local se
personalizan por navegador. Calendario económico: se recarga al cambiar tema (fix legibilidad
light), filtro por instrumento (chips: NQ/ES/MES/YM/XAU→US, EURUSD→US+EU, etc., guardado en
localStorage, disclaimer educativo reforzado en 4 idiomas). Vive en `index.html` (bloque "MARKET
TIMING", clases `.kzt`/`.kz-row`, vars `--kzt-*`, JS IIFE "Kill Zones live clock").

**Mentorías ("Find New Ways to Improve"):** páginas 1-4 hechas y traducidas EN/ES/FR/PT
(`/improve`, `/improve/mindset`, `/improve/gap`, `/improve/inside`) + listón dorado
`.improve-ribbon` arriba de los tabs en `/app` (admin-only por `_mentorship_gate()`, flag
`MENTORSHIP_ENABLED`). i18n: `scalpel/static/improve_i18n.js` (4 idiomas, lee `scalpel_lang`, con
selector EN/ES/FR/PT en el header de cada página) + claves `improve.rb.*` en `MT_I18N` para el
listón. Estilo: `scalpel/static/improve.css`.
**✅ Pág 5 — CÓMO FUNCIONA + GRAN FILTRO (`/improve/apply`) HECHA (2026-07-24, v2):** página
detallada completa — cómo funciona cada programa y su pago (**biblioteca grabada = suscripción
mensual**; **calls 1-1 = paquetes mensuales 5/10/20 de 30min + sueltas** — decisiones del usuario
2026-07-24), perfil del mentor SIN identidad (reveal sigue siendo post-filtro, confirmado), y el
formulario del Gran Filtro fusionado con la pregunta **"¿qué te interesa?"** (rec/calls/both →
columna `program` en `MentorshipApplication` + auto-migración guarded). Al enviar → redirect a:
**✅ Pág 6 — LA OFERTA (`/improve/plans`) HECHA (2026-07-24):** gated por sesión
(`improve_applied`; admin previewea directo) — filtro primero, precios después. Estructura: bloque
reveal del mentor (**PENDIENTE bio real del usuario — nunca inventar**), tarjetas con viñetas por
rama (borrador razonable, confirmar con el usuario), tiers 5/10/20/suelta, tarjeta combo ambos, y
precios reales **(reajustados 2026-07-24 tras research de mercado + capacidad)**: biblioteca $350/mes;
**reunión online 1-1 (30 min) = $100 suelta** ($200/h, alineado al piso premium de la industria; Fede
Esses ~$1000/mes, 1-1 industria $100-500/h). Paquetes: **3/mes=$270 ($90 c-u, ahorras $30)**, **6/mes=
$480 ($80 c-u, ahorras $120)** — se ELIMINARON 5/10/20 porque la capacidad real de Gabriel es ~36
reuniones/mes TOTAL (~9/sem) y un 20-pack se comía media agenda; 6 es el tope por persona (~6 mentees
llenan las 36). **combo "Ambos" = 2 sub-tiers** biblioteca(−25%, $350→$263) + paquete: +3=$533(~$650~,
ahorras $117), +6=$743(~$950~, $207). Tiers = total + tachadura `.ptwas` + pastilla verde `.ptsave`
"Ahorras $X" (`p6.save`). ⚠️ 25% de $350=$262.50 redondeado a $263. i18n 4 idiomas a paridad, 0 claves
de template sin dict. Probado end-to-end con test_client (form+enum 400, redirect, gate 302→apply,
migración re-agrega columna).
**✅ CHECKOUT DE MENTORÍA — paneles seleccionables + Stripe AISLADO (2026-07-24).** Los tiers/combos de
`/improve/plans` son **seleccionables** (`.ptier.selectable`/`.buy.selectable`, hover+click, 1 a la vez,
✓ dorado) → barra de carrito fija `.mcart` sube con nombre+precio+"Ir a pagar" (i18n `mcart.*`). **Aislamiento
TOTAL vs planes del sitio** (miedo del usuario a cobros cruzados): tabla **separada `MentorshipOrder`** (auto-
creada por `create_all`, no toca `user.plan` JAMÁS); **precio SIEMPRE server-side** desde `MENTORSHIP_SKUS`
(el browser solo manda el SKU: library/meet3/meet6/meet_single/combo3/combo6 — nunca el monto); rutas
`/mentorship/checkout/create|success`; **mismo `mode='payment'` (pago único, sin auto-renovación sorpresa)**;
el webhook `/webhook/stripe` **despacha por `metadata.kind=='mentorship'`** → `_activate_mentorship_order`
(idempotente, solo registra+email a la empresa; fulfillment real = tarea futura con área de miembros), y las
sesiones de plan (sin `kind`) siguen su camino intacto. Templates `mentorship_checkout_{done,success}.html`.
**Test de aislamiento pasó**: pago de mentoría NO cambia `user.plan`; webhook de plan SÍ; evento mentoría
apuntando a un Order de plan no lo activa; idempotencia OK; precio siempre del SKU. Stripe sigue inerte sin
`STRIPE_SECRET_KEY` (cae a la página `done` manual).
**✅ SESIÓN 2026-07-25 (5 tareas Fable):** (1) **Página-carrito de revisión** `GET /mentorship/checkout?sku=`
(template `mentorship_checkout.html`, estilo mentorías, espejo del "Review your order" del landing): programa +
qué-incluye (reusa claves p6.a*/b*/c*) + total server-side + "Continuar al pago" → POST create. El mcart ahora
es GET a esa página (ya no POST directo). Claves `mco2.*` ×4 idiomas. CSS `.mco2-*` en improve.css. (2) **Cards
con PESTAÑAS**: cards 2 (meetings) y 3 (Ambos) ya NO apilan tiers — cada una tiene tab-strip (`.ptabs`/`.ptab`/
`.ppane`, JS en improve_plans.html) con UNA pestaña por paquete mostrando SU precio grande + tachado + ahorro +
botón Elegir (mismo layout que card 1). Labels `p6.tab*` ×4. (3) **Renombres + ES natural** (×4 idiomas):
"biblioteca grabada"→**"Clases pregrabadas y operativas en vivo"** y "llamadas/calls"→**"reuniones online"**
en TODO el funnel (labels, tabs "Clases + 3/6", nombres de carrito, form); bio del mentor SIN mención de
capital propio ("enseña exactamente lo que opera, sesión tras sesión"); 5/10/20 calls desactualizado→3/6;
"aplicación"→"solicitud"; "Elige tu sala"→"Elige tu programa"; lead de puertas reescrito; país ejemplo
Venezuela→Estados Unidos/United States. (4) **Barrido de botargas COMPLETO** (41 archivos logo2/3/4 ×
light/dark): detector de bolsas blancas encerradas en 2 escalas + verificación visual — CERO defectos nuevos
(todos los blancos son features: ojos/guantes/botas/humo/pizarra); los únicos reales eran fourth+blackflag
welcome, ya corregidos. (5) **Menús Products/User por camo**: se ELIMINARON los hardcodes por-camo del
`.products-menu` y el blanco forzado de `body.light` en ambos menús → regla genérica
`body[class*="camo-"] { background: linear-gradient(var(--card),var(--card)), var(--bg) }` (mismo color que
los paneles del camo, presente y futuros) + acordeón del sidebar SIEMPRE transparente (`!important`).
Verificado en fourth/naval/mission-Marte/blackflag/premium.
**✅ CARDS estilo landing (2026-07-24):** las 3 tarjetas de `/improve/plans` adoptaron el diseño de
las cards Standard/Premium del landing (`.pcard` en `improve.css`: nombre mayúsc. dorado + tagline +
precio grande + divisor + features con check-circles + botón full-width; "Ambos" = featured con
badge "Más elegido" + borde/botón dorado; grilla 3-col → 1-col en móvil, paleta oscura de mentorías).
**Contenido REAL del Programa 01 cargado** (viñetas a1-a6, ya no genéricas): curso completo cero→real
(teoría/metodologías/psicotrading), operativas reales grabadas con desglose de cada decisión de
Gabriel, backtests propios, sesiones en vivo ocasionales, **comunidad privada Tradeable Academy (hub
Discord + en el sitio)**, acceso 24/7. ES reescrito natural (LatAm, "tú"). ⚠️ Fix a11y: `.pcard`/`.hw`/
`.af` arrancaban `opacity:0` sin estar en la regla `prefers-reduced-motion` → invisibles para ese
usuario; agregados. **PENDIENTE:** label sigue "Programa 01 · La biblioteca grabada" (infravalora el
contenido real — ofrecer renombrar); bio real de Gabriel; revisar redacción ES del resto de mentorías.
**✅ FORMULARIO REHECHO — FAQ de perfil (2026-07-24, decisiones del usuario):** el form dejó de
ser filtro pasa/no-pasa → es FAQ para conocer al trader; al enviar (a) guarda en DB, (b) **manda
email a la empresa** (`send_mentorship_application_email`, `ADMIN_EMAIL` env default Gmail actual,
best-effort) y (c) desbloquea `/improve/plans` al instante. **TODOS los campos obligatorios**,
casi todo clickeable: se mantienen nombre/email/programa/experiencia/etapa/horas + NUEVOS: objetivos
(chips multi), fortaleza+debilidad (6 áreas; reemplazan los textos libres struggle/why — columnas
legacy quedan ''), activos (chips: futuros/forex/cripto/acciones/varios), país + **tz del navegador
auto**, idioma de clases/calls (**ES/EN only — nota visible en apply y plans en 4 idiomas**), franja
para calls, cómo-nos-conociste, rango de edad + check 18+. 10 columnas nuevas + auto-migración +
validación enum/CSV server-side. i18n 143 claves/idioma a paridad. E2E probado (cada campo faltante
→ 400). **PRÓXIMO (ya discutido, PENDIENTE de armar):** (1) **agenda custom** de calls (opción A:
/admin marca disponibilidad, la página de planes muestra ocupado/libre; reserva real después con
Stripe); (2) **rediseño de /improve/plans**: bio desglosada de Gabriel + planes nuevos — el plan
mensual de biblioteca incluirá: curso completo de cero a operativa real, teoría/metodologías/
psicotrading, backtests de Celis, operativas live pregrabadas, directos ocasionales, **comunidad
ultra-privada Discord + sección en el sitio**, acceso 24/7; value-adds propuestos por Claude
(certificado del curso, quizzes por módulo, Q&A grupal mensual, plantillas de Celis, camo exclusivo
de miembro, prioridad de agenda) — usuario aún no confirmó cuáles; **falta discutir los planes 1-1**
(costos ya definidos). ⚠️ Legal: "demostración de rentabilidad" SIEMPRE como track record personal
de Gabriel con disclaimer, nunca promesa de resultados del alumno.

**✅ ÁREA DE MIEMBROS (`/mentorship/area`) CONSTRUIDA (2026-07-26, la "Pág 7" pendiente).** Gate:
`is_mentorship_member()` = admin O `MentorshipOrder` paid con kind `library`/`combo` (compra combo
también desbloquea; probado). No-miembro → redirect a `/improve/plans`; APIs → 403. Template
standalone `mentorship_area.html` (base improve.css + CSS `.ma-*` inline, i18n `ma.*` 28 claves ×4
en `improve_i18n.js`). **4 tabs miembro + 1 mentor (admin):** (1) **Inicio** — banner ON-AIR (el
mentor lo prende/apaga con título+URL; poll 60s), últimas subidas, seguir-viendo; (2) **Clases** —
carpetas/módulos (nombre+emoji+descr) con progreso done/total por usuario, videos con título/descr/
duración/kind (CLASS/LIVE REC/BACKTEST), modal player (`playerFor()`: YouTube→embed, mp4/webm/m3u8→
`<video nodownload>`, resto iframe), marcar-completada, comentarios por video; (3) **Comunidad** —
canales creados por el mentor (lockeables = solo-mentor/anuncios), chat con replies, 5 reacciones
(👍🔥📈❤️🤝 toggle), pins (top-3 arriba), poll 8s, flood 20/min; (4) **Preguntas** — buzón al mentor
(máx 5 abiertas), el mentor responde inline y el alumno ve Q&A. **Panel mentor:** live on/off, CRUD
carpetas/videos/canales, responder, pin/delete. Modelos: MentorshipFolder/Video/VideoComment/Question/
Channel/Message/MsgReaction/Progress/LiveState (create_all los crea). CTA "Entrar al área" en
checkout success (solo library/combo). E2E test_client: 44 checks verdes (gates, CRUD, cascade
delete, lock, pin, rate-limits).

**🔴 PENDIENTE DECIDIDO — BUNNY STREAM (decisión tomada 2026-07-26, ejecución DIFERIDA por el
usuario).** El hosting de video definitivo **es Bunny**, no YouTube: el usuario confirmó que puede
pagarlo sin problema (~$1-3/mes al arranque, ~$13 con 20 alumnos; sin cuota fija, saldo prepago que
se consume como la API de OpenAI). **Motivos de la decisión:** (1) YouTube **modera** — educación
financiera con operativas puede recibir strike y se caen TODAS las clases a la vez; Bunny no mira el
contenido; (2) el link "no listado" es público e irrevocable (un alumno lo filtra y el curso de $350
queda gratis); en Bunny el acceso se firma por usuario y vence; (3) marca/publicidad de YouTube dentro
de una academia premium. **Orden pedido por el usuario:** primero Fases A→B→C→D del área, y **recién
al final se conecta Bunny**. Mientras tanto el mentor carga links de YouTube **solo para probar** —
⚠️ **NO subir las clases reales de Gabriel a YouTube**, habría que resubir todo a mano al migrar.
**Ya está preparado:** `MentorshipVideo.source` (`youtube`/`file`/`embed`) + `provider_id` + `thumb_url`
se clasifican server-side en `_video_meta_from_url()`; agregar Bunny = un valor más + una rama en
`playerFor()`. Lo específico de YouTube son ~8 líneas. **Falta:** cuenta Bunny + Stream Library +
claves por env var (patrón OpenAI/Stripe, NUNCA en el repo) + subida arrastrar-y-soltar directa del
navegador a Bunny (TUS/direct upload, no pasa por el VPS) + duración/miniatura automáticas + URLs
firmadas. ⚠️ **Al conectarlo hay que corregir los T&C Secc. 19**: hoy promete "solo streaming, sin
descargas", lo cual con YouTube/mp4 es técnicamente falso — reformular como obligación del alumno
(prohibido descargar/redistribuir/compartir enlaces), no como promesa técnica.

**PENDIENTE (resto):** subida de archivos, notificaciones email de respuestas.

**✅ FORO "RAYGUN MARK II" — Communities + Follows + DMs (2026-07-26).** Boost estilo Instagram
para el foro (Standard+Premium). **Backend:** `ForumCommunity/Member/Follow/DM` + `ForumPost.
community_id` (auto-migración guarded `_migrate_forum_post_community_column()`); `/forum/communities`
GET/POST (máx 3 por usuario, nombre único case-insens, pretrip, creador auto-join y no puede salir);
`/forum/community/<id>/membership`; postear en comunidad = solo miembros (403 `not_a_member` si no);
`/forum/feed?community=<id>` y `?feed=following`; `/forum/follow` (toggle por username);
`/forum/dm/threads` (unread por hilo + total) y `/forum/dm/with/<username>` (abrir marca leído,
`?after=` polling, 30/min, pretrip). `serialize_post` suma `community` + `following_author`.
**Cliente (index.html):** tabs nuevos **Following** y **Communities** (panel: crear con emoji/nombre/
descr, cards con join/leave/abrir, feed de comunidad con barra ←); chip de comunidad en los posts
(clic entra); selector "Publicar en" en el composer (general o comunidad unida; publicar dentro de
una comunidad te deja ahí); botón **Seguir/Siguiendo** + **✉** en el header de posts ajenos;
**drawer de DMs** (botón Mensajes con badge de no-leídos, hilos, burbujas, Enter-envía, poll 8s
abierto). i18n 26 claves `forum.*` ×4 a paridad. E2E test_client backend verde + render de /app
verificado (sin screenshots, modo ahorro).

**Datos del mentor + precios CARGADOS (2026-07-24, base):** mentor **Gabriel Celis**, ~6 años (⚠️
años TENTATIVOS — el usuario confirma y reeditamos), ex-Forex, hoy futuros **S&P 500 + Nasdaq**.
Precios DEFINIDOS (2026-07-24, tras research de mercado + límite de capacidad de Gabriel): biblioteca
**$350/mes** (se queda; rango industria $299-500); **reunión online 1-1 (30 min) = $100 suelta**
(decisión usuario: subir el 1-1 porque estaba muy barato vs industria $100-500/h y vs Fede Esses
~$1000/mes). Paquetes chicos por **capacidad real ~36 reuniones/mes TOTAL** (Gabriel estimado ~9/sem,
tope 6/mes por persona): **3/mes=$270 ($90 c-u, ahorras $30)**, **6/mes=$480 ($80 c-u, ahorras $120)**.
Se ELIMINARON los paquetes de 10 y 20 (no caben en la agenda). **combo "Ambos" con 25% OFF a biblioteca**
($350→$263) + paquete: **+3=$533** (~$650~, ahorras $117), **+6=$743** (~$950~, ahorras $207). Tiers
muestran total + `.ptunit` ($/reunión) + tachadura `.ptwas` + pastilla verde "ahorras". **⚠️ El estimado
de 9 reuniones/sem de Gabriel NO está confirmado por él — validar su disponibilidad real.**
**FALTA:**
- **Confirmar del usuario:** años exactos de Gabriel, precios definitivos de calls, si hay descuento
  de combo, y detalle final de las viñetas de cada plan (las actuales = borrador razonable).
- **Revisión de aplicaciones**: pestaña/lista en `/admin` para ver `MentorshipApplication` y marcar
  accepted/rejected (+ email al aplicante). Hoy solo se guardan en DB.
- **Pág 7 — área de miembros** (post-pago): biblioteca de videos (sube el trader), reserva 1/1
  con cupo/créditos, Q&A por video (reusar moderación IA), progreso, certificados.
- **Reveal del mentor (foto/identidad) va AL FINAL**, después del filtro — nunca antes.
- Luego: cablear Bunny Stream (video), Calendly/Cal.com (reservas), cupos/créditos, pagos.

---

## 🔁 SUSCRIPCIONES — los planes mensuales se cobran SOLOS (cableado 2026-08-04)
**Decisión reafirmada del dueño:** *"habíamos quedado en que los planes SÍ DEBÍAN DE COBRARSE
AUTOMÁTICAMENTE. y que el cliente cuando quisiera podía darse de baja"*. Se le señaló que los T&C
decían lo contrario y aun así lo confirmó → hecho, y los T&C reescritos.
- **Es OTRA API de PayPal.** Pago suelto = `/v2/checkout/orders` (lo de siempre, cosméticos incluidos).
  Suscripción = `/v1/billing/subscriptions`, y **esa sí exige crear producto + planes con id fijo** —
  esto era la media razón que tenía el papá del dueño; para los cosméticos no hace falta nada de eso.
  Se crean por API con **`tools/paypal_setup_subs.py`** (idempotente, busca por nombre antes de crear;
  `set_paypal.py` ya lo llama de paso, así configurar PayPal sigue siendo UN comando).
- **Modelo `PlanSubscription` = el PERMISO de cobro; `Order` sigue siendo UN cobro.** Cada mes cobrado
  escribe una Order nueva → extensión del plan, libro de ventas y comisión del socio pasan por
  `_activate_plan_from_order`/`record_sale_breakdown` de siempre. Cero código paralelo.
  `_sub_cobro()` es idempotente por `provider_ref` (id de la venta) → aviso repetido no regala un mes.
- **El descuento del socio sobrevive:** el precio se manda sobrescribiendo `pricing_scheme` al abrir
  cada suscripción, así un cliente atado paga $40/mes para siempre sin crear un plan por descuento.
  La renovación copia `promo_code` → el socio cobra comisión en cada mes. Probado ($12 al 30%).
- 🔴 **`PAYPAL_SUBS_ENABLED` exige `PAYPAL_WEBHOOK_ID`**, y por eso el dominio con HTTPS pasó de
  "mejora" a **requisito duro**: en una renovación **nadie vuelve a la web**, así que el cobro del mes 2
  en adelante llega ÚNICAMENTE por webhook. Sin él se cobraría y el plan no se extendería, en silencio.
  Sin los ids de plan el sitio cae al pago suelto y no promete ninguna renovación (nunca se cae en
  silencio a "un solo cobro" tras haber anunciado la renovación en el carrito).
- 🔴 **Bug real arreglado de paso:** `/account/cancel-plan` solo levantaba una bandera (no pasaba nada
  porque nada renovaba). Con cobro automático detrás eso = cobrarle a quien pulsó "darme de baja".
  Ahora corta en PayPal de verdad; si PayPal no responde **NO se le dice que está cancelado**
  (`sec=cancel_failed`). **El plan pagado nunca se revoca** — cancelar corta el mes siguiente.
  `reactivate-plan` manda a `/pricing`: la API de PayPal no tiene "descancelar".
- Subir de Standard a Premium **cancela sola** la suscripción vieja (si no, se cobran las dos).
- **Anual y USDT NO son recurrentes.** El anual por decisión (un contracargo de $408 no lo cubre
  ninguna reserva). USDT porque **no se puede**: una cadena de bloques no deja cobrar sin que el dueño
  del dinero firme cada vez. Lo que NOWPayments llama "suscripciones" es **factura recurrente por
  correo** que el cliente paga a mano, o débito de un saldo que él precarga en NOWPayments — útil,
  pero NO es el cobro automático de una tarjeta. Hay que decírselo así al cliente.
- Cobro rechazado → `BILLING.SUBSCRIPTION.PAYMENT.FAILED` avisa al dueño por correo
  (`_avisar_cobro_fallido`) porque **es el único fallo que nadie nota**: el cliente no está delante.
- **T&C Secc. 5 reescrita** ×4 idiomas (renovación, baja sin preaviso ni coste, período empezado no
  reembolsable, reintentos, anual/USDT no recurrentes, no se sube el importe sin avisar). Auditor 144.
- `tools/test_subs.py` **41/41** con PayPal simulado.

## 📧 UN BUZÓN = UNA CUENTA — correo canónico en el registro (2026-08-09)
Auditoría multi-cuentas pedida por el dueño. Diagnóstico honesto que se le dio: la huella de
navegador solo se compara contra BANEADOS (varias cuentas desde el mismo navegador = permitido),
se calcula en el cliente (falsificable, y sin JS se salta), y NO hay límite por IP en /register.
**Decisión del dueño tras discutirlo: cablear SOLO el punto 1 (alias de correo)** — el resto se
anotó como "si aparece abuso real". Razones: el foro exige plan de PAGO (un baneado que vuelve
con cuenta free no puede publicar; volver a molestar = pagar $25 otra vez y perder XP/rango/
cosméticos), y 10 cuentas free = ~$1.20/mes de análisis. El único truco de coste CERO era el
alias: `juan+2@gmail.com` / `j.u.a.n@gmail.com` = EL MISMO buzón (documentado por Google).
- **`User.email_canonical`** (índice NO único a propósito: filas viejas podrían colisionar y un
  índice único tumbaría el arranque; la unicidad la impone /register). `_correo_canonico()`:
  minúsculas; quita `+etiqueta` solo en proveedores que lo documentan (`_CORREO_SUBDIR`); quita
  puntos SOLO en gmail (`_CORREO_SIN_PUNTOS`) — en un dominio corriente juan.perez@ ≠ juanperez@.
- Migración `_migrate_user_email_canonical_column()` con **backfill** (sin él la regla nace coja:
  el alias de una cuenta ANTERIOR no chocaría — justo el baneado con cuenta vieja). SQL crudo
  tocando solo id/email. `test_boot_migracion` 7/7 (columna nueva cubierta).
- El rechazo usa el MISMO error `email_taken` de siempre — no delata nada.
- `tools/test_correo_canonico.py` **19/19**. ⚠️ El test comprueba `reg.errEmail` (la clave que
  renderiza la plantilla), no el nombre interno del error; e init_db siembra un admin (no contar
  usuarios en absoluto).
- **PENDIENTE ANTES DE LANZAR (acordado):** antiflood en /register por IP — no por los análisis,
  sino porque mil registros automáticos = mil correos de verificación desde info@ = reputación
  del dominio quemada y los códigos de clientes reales cayendo en spam.

## 🔴 El cupón se canja al COBRAR, no al ponerlo en el carrito (2026-08-08)
Lo cazó el dueño probando en producción: aplicó un cupón de un solo uso, pulsó pagar, se volvió
atrás y el sitio le dijo **"límite alcanzado"**. Su propio carrito a medias le había gastado el
código. Causa: `uses_count` se **reservaba al crear el pedido** y solo se devolvía al cancelarlo,
y `is_redeemable()` mira ese contador. Es EXACTAMENTE el mismo fallo que ya se había corregido
para el límite por cuenta (`promo_ya_usado` mira pedidos PAGADOS) — la reserva sobrevivió en el
contador global.
- **Fix:** `_consumir_uso_de_promo(order, user, renewal)` en `_activate_plan_from_order`. Se anota
  **una vez por (cuenta, código)**, en la primera compra pagada → `uses_count` pasa a significar
  *"cuántos CLIENTES trajo este código"*: ni las renovaciones ni una subida de plan posterior lo
  inflan (antes, un código de socio tecleado a mano sí lo hacía).
- 🔴 **Se quitaron los DOS decrementos** (`_soltar_pedido` y el botón de cancelar de /admin): sin
  reserva, restar ahí le quitaría el canje a OTRA persona que sí pagó.
- ⚠️ **Precio asumido a sabiendas:** `max_uses` deja de ser una reserva, así que dos carritos
  abiertos a la vez podrían pagar ambos y pasarse del tope por uno. Regalar un descuento de más es
  más barato que impedirle comprar a alguien que quiere pagar.
- `tools/test_cupon_al_cobrar.py` **11/11** (con el código viejo fallan 5, incluido el `maxed` que
  vio el dueño). Dos suites documentaban la conducta vieja y se **reencuadraron** sobre la regla
  nueva, no se debilitaron: `test_pedido_pendiente` (19/19) y `test_promo_31` (20/20 — ahora
  verifica que una compra con cupón general NO le sume un cliente al socio).

## 🔴 Una suscripción NUNCA APROBADA bloqueaba la baja del cliente (2026-08-08)
Salió al preparar el ensayo de compra, pero es un bug de cliente de pleno derecho. El comprador
llega a la pantalla de PayPal y la cierra → de nuestro lado queda una `PlanSubscription` 'pending'
con su `provider_ref`; en PayPal esa suscripción nunca se activó, así que **cancelar responde 404**.
`_paypal_sub_cancel` leía cualquier código ≠422 como fallo → `cancel_plan` devolvía
`sec=cancel_failed` y **la baja no cancelaba NADA, ni siquiera la suscripción de verdad detrás**.
- **Fix:** `_sub_puede_cobrar(sub)` le PREGUNTA a PayPal antes de rendirse. Solo `ACTIVE` y
  `SUSPENDED` cobran (una suspendida se puede reanudar); `APPROVAL_PENDING`/`CANCELLED`/`EXPIRED`
  y el 404 no. ⚠️ **Ante una API muda devuelve True** (= sigue bloqueando): dar por cortado lo que
  no se pudo comprobar es como se cobra a quien pidió la baja.
- `tools/test_baja_sub_fantasma.py` **10/10** (fantasma no bloquea · una ACTIVE que no se corta
  sigue avisando · PayPal mudo bloquea · el botón de baja de punta a punta).

## 🧪 Probar una compra REAL sin gastar dinero (2026-08-08)
`tools/preparar_prueba.py <cuenta> [--aplicar]` deja una cuenta lista para el ensayo en UN comando:
baja el plan a Free, suelta pedidos pendientes, **corta en PayPal los permisos de cobro vivos** y
crea el cupón general de un solo uso. Sin `--aplicar` solo informa. 🔴 **Se detiene** si alguna
suscripción no se pudo cortar: bajar el plan dejando vivo el permiso deja la cuenta gratuita en el
sitio mientras PayPal le sigue cobrando. `test_preparar_prueba.py` **24/24**.

## 🌐 `SITE_URL` — los enlaces absolutos dejan de depender del Host (2026-08-04)
Los 20 `url_for(..., _external=True)` pasaron a **`abs_url()`**, que antepone `SITE_URL` si está.
Sin esto, entrar por la IP cruda hacía que la vuelta de PayPal y los enlaces de los correos salieran
como `http://62.171.180.22:5001/...`. ⚠️ **NO se usa `SERVER_NAME` de Flask** (lo obvio): fijarlo hace
que la app deje de responder a cualquier otro Host → 404 en TODO el sitio por la IP, y parece caído.
`PUBLIC_HTTPS=1` enciende **ProxyFix + cookies Secure/HttpOnly/SameSite** y hace que `_client_ip()`
use `remote_addr` en vez de un `X-Forwarded-For` que escribe quien llama (era falsificable, y de ahí
cuelgan límites por IP). ⚠️ Encenderlo **apaga el acceso por `http://IP:5001`** (la cookie deja de
viajar) — es el precio de cerrar bien, y hay que avisarle antes.
**nginx listo en `deploy/nginx/tradeable.academy.live.conf`** (proxy_pass, estáticos servidos por
nginx, `client_max_body_size 24m`, `location ~ ^/webhook/` con más espera, robots.txt abierto). El
archivo viejo de "en construcción" se conserva para volver atrás con un comando.

## 🟣 PayPal — 2º riel de cobro (código LISTO 2026-07-26, falta encender)
Mismo patrón condicional que cripto/Stripe: **inerte sin claves** (`PAYPAL_CLIENT_ID`/`PAYPAL_SECRET`,
+ `PAYPAL_ENV=sandbox|live`, `PAYPAL_WEBHOOK_ID`, `PAYPAL_BRAND_NAME`). Convive con USDT, no lo
reemplaza.
- **Elección de método:** `available_payment_rails()` → si hay **>1 riel**, `/checkout/create` manda a
  **`/checkout/pay/<order_id>`** (plantilla nueva `checkout_method.html`, i18n `cpay.*` ×4, un `<form>`
  por riel, sin JS decidiendo el destino). Con **1 solo riel** el flujo es idéntico al de antes (directo).
  Bonus: un pedido pendiente abandonado ya **no encierra** al comprador — lo devuelve a elegir método.
- **Ciclo PayPal (Orders v2):** `_paypal_create_order` (guarda `provider_ref`=id de PayPal) → el
  comprador aprueba → `/checkout/paypal/return/<id>` **captura** → `_paypal_apply_status` →
  `_activate_plan_from_order` (el MISMO activador idempotente de siempre). 3 redes de seguridad iguales
  a cripto: webhook `/webhook/paypal` (verificado contra la API de PayPal con `PAYPAL_WEBHOOK_ID`),
  reconciliación al abrir `/checkout/status/<id>`, y el barrido al abrir /admin (`payments_sweep`, ex
  `crypto_sweep`, ahora despacha por `payment_method` vía `_reconcile_order`). `PayPal-Request-Id` en
  create/capture = idempotencia del lado de PayPal; un `ORDER_ALREADY_CAPTURED` se resuelve leyendo el
  pedido, no fallando.
- **Disputas/contracargos:** eventos `CUSTOMER.DISPUTE.*`, `PAYMENT.CAPTURE.REVERSED/REFUNDED` marcan
  `pay_status` y **avisan por correo al dueño** (arreglado: antes el aviso no salía en pedidos ya
  pagados) + salen en la bandeja "Pagos que necesitan atención" de /admin con etiqueta propia. **NUNCA
  revocan el plan solos** — la decisión es del dueño, con `/admin/trace` como prueba de entrega.
- **T&C/Privacy actualizados** (EN + ES/FR/PT en `legal_i18n.js`, paridad 115 claves verificada):
  Secc. 5 pasó de "pagos en USDT" a **"Métodos de pago" (a) tarjeta/PayPal (b) USDT**, + párrafo nuevo
  **"Quién recibe el pago"** (el titular que muestra el proveedor puede diferir del nombre comercial;
  la contraparte sigue siendo el negocio de la Secc. 1) — **esto cierra la incoherencia** de que el
  contrato nombre a un vendedor y el recibo muestre otro —, + párrafo **"Pagos con tarjeta y PayPal"**
  (reembolso por el mismo método, registro de entrega presentable ante una disputa, contracargo por un
  plan sí entregado = incumplimiento, suspensión mientras se resuelve). El párrafo cripto quedó acotado
  a "cuando pagas en criptomonedas". Privacy 2.2 + tabla de terceros: fila de PayPal.
- **Para ENCENDER:** cuenta PayPal Business → REST app → Client ID + Secret → **poner el nombre
  comercial "Tradeable Academy" en la cuenta** (para que el recibo coincida con los T&C) → webhook
  apuntando a `/webhook/paypal` con los eventos CHECKOUT.ORDER.APPROVED, PAYMENT.CAPTURE.COMPLETED/
  DENIED/REFUNDED/REVERSED y CUSTOMER.DISPUTE.CREATED → copiar el **Webhook ID** → las 4 variables en
  supervisor conf + `scalpel/.env` (NUNCA en el repo/chat) → restart. Probar antes con `PAYPAL_ENV=sandbox`.
  ⚠️ El webhook necesita dominio+HTTPS; sin eso la captura del return-url y el barrido de /admin cubren
  igual la activación.
- **Probado (46 checks, PayPal simulado):** compra completa, aviso repetido no estira la vigencia, firma
  inválida y falta de WEBHOOK_ID rechazadas, comprador que aprueba y no vuelve (rescatado por
  reconciliación / página de pedido / barrido), pago rechazado a la bandeja sin entregar plan, disputa
  que avisa y no quita el plan, elección de riel con los dos encendidos, precio siempre server-side,
  aislamiento entre compradores, y con las claves apagadas todo vuelve al flujo manual.

## 🟡 Cambio de plan EN VIVO + qué hace de verdad "darse de baja" (2026-08-05)
Dos cosas que el dueño vio como fallos. Una lo era y la otra no.
- **La pantalla no se enteraba.** Bajó a Free a `gussytrades` desde /admin y el otro siguió viendo
  su plan hasta refrescar. ⚠️ **Era pintura, no permisos:** el servidor decide en CADA petición, así
  que la pantalla vieja nunca da acceso a nada (verificado: al bajarlo, su misma sesión reporta
  `plan=free`, cuota 1 y el foro le devuelve 403 sin refrescar ni volver a entrar).
  **Vigilante `nx-plan-watch`** al final de `index.html`: pregunta a `/api/usage` (ya devolvía el
  plan) cada 60 s y **al volver la pestaña al frente**, que es cuando pasa de verdad. 🔴 **No recarga
  a ciegas**: si hay texto a medio escribir o un análisis corriendo, saca una barra
  ("Tu plan cambió a X · Actualizar / Ahora no", ×4 idiomas) en vez de borrarle el trabajo.
  ⚠️ **Trampa cazada en navegador real:** la primera versión usaba `offsetParent !== null` para
  saber si un campo se ve, y **en `position:fixed` eso vale null aunque esté a la vista** (el
  carrito y los drawers del sitio son fijos) → la nota escrita se contaba como inexistente y la
  recarga se la llevaba. Se usa `getClientRects().length`.
- **"El botón de darse de baja no funciona: sigo siendo premium."** Eso es lo pactado: la baja corta
  la RENOVACIÓN, no el mes pagado (T&C Secc. 5). 🔴 **Pero había un fallo real detrás, mío:** el
  botón de /admin ponía el plan **sin fecha de vencimiento**, así que no había nada que terminara y
  la baja no producía ningún efecto nunca. Ahora otorga 30 días + `plan_cycle='monthly'` (repetir el
  mismo plan NO estira la fecha: sería regalar meses a cada clic). Y Ajustes ya no se queda mudo sin
  fecha (`settings.cancelledNoDate` ×4).
- El **unlock de Premium que "vuelve a saltar"** no es de la baja: es el reveal de la compra, que
  se dispara en el primer `/app` que se abre después de que el pedido se aplica (una vez por pedido,
  `Order.celebrated_at`). Si compró y se fue directo a Ajustes a cancelar, lo ve al volver.
- ⚠️ **Trampa de los tests:** con `with app.test_client() as c:` Flask **conserva** el contexto de la
  última petición, y con él la sesión de SQLAlchemy — o sea su caché de objetos. El usuario se queda
  congelado en el plan viejo y el test acusa un fallo del servidor **que no existe**. Clientes sin
  `with` para nada que cruce dos sesiones. `tools/test_plan_en_vivo.py` **20/20** + navegador real
  (recarga sola, barra con texto a medias, el botón, y en español).

## 🔴 "UNLOCKED" que salta cuando no toca — reglas fijadas (2026-08-05)
**Síntoma:** compró COSMÉTICOS siendo Premium y le saltó el unlock de **Standard**. Los cosméticos no
tienen nada que ver (viven en `CamoOrder`/`CosmeticOrder` y no crean pedidos de plan): el unlock
quedaba **en cola** hasta el siguiente `/app`, sin comprobar si seguía describiendo la cuenta — era
el Standard que había comprado antes en esa misma cuenta, esperando para asomar en cualquier momento.
**Regla del dueño:** *"El unlock solo tiene sentido cuando haces upgrade / cambias de plan o cuando
pagas alguno por primera vez."* Cableado en dos sitios:
- `_activate_plan_from_order`: una **renovación nace ya sellada** (`celebrated_at`). 🔴 Sin esto, con
  el cobro automático encendido, a un cliente fiel le saltaba "UNLOCKED Premium" **todos los meses**.
- `/app`: se celebra **solo si el pedido coincide con el plan de HOY** (cuenta ya en Premium + pedido
  viejo de Standard = ruido, se descarta), y se sella **TODA la cola**, no solo el que se enseña —
  antes los demás iban asomando de uno en uno en visitas siguientes.
- No dispara: cosméticos, plan puesto a mano desde /admin (nadie compró nada), ni un plan ya vencido.
- El reveal de **RANK** es otra cosa y sigue igual: a propósito NO se sella hasta que el usuario lo
  cierra (`/api/rank/celebrated`), para que un render que nadie vio no se lo trague.
`tools/test_unlocks.py` **14/14** (con el código viejo fallan 3: el caso del dueño, la renovación y
la cola). Las filas viejas de producción se sellan solas en el siguiente `/app`, sin enseñar nada.

## 🔁 RENOVACIONES — la fecha que se enseña y el corte de la baja (2026-08-05)
El dueño vio en Ajustes *"PREMIUM · CANCELLING · Access ends Nov 03, 2026"* estando en agosto.
- **El Nov 3 no era un bug:** son sus **tres compras de prueba apiladas** (una renovación SUMA 30
  días al vencimiento vigente). Para volver a un mes limpio: /admin → Free → el plan otra vez.
- 🔴 **Lo que SÍ era un fallo: se enseñaba la fecha equivocada.** "Se renueva sola" mostraba
  `plan_expires_at` (el fin del ACCESO) cuando el cobro lo manda `sub.next_billing_at` (PayPal). Con
  acceso apilado no coinciden: le anunciaba un cargo el 3-nov cuando PayPal cobra el 4-sep, y el día
  del cargo real no lo estaría esperando. Ahora se muestra la de PayPal + línea aparte
  `settings.paidThrough` ("acceso ya pagado hasta el…") cuando van por delante. **La fecha de
  renovación se ve en Ajustes**, que ya es la primera entrada del menú (punto 20).
- 🔴 **Hueco de la baja, cerrado:** `cancel_plan` cortaba solo la suscripción que teníamos por
  ACTIVA. Una en **`pending`** —aprobada en PayPal pero sin sincronizar de nuestro lado, que es lo
  que pasa si el comprador cierra la pestaña y el aviso se pierde— seguía cobrando **mientras la
  pantalla decía "cancelado"**. Ahora `subs_por_cortar()` devuelve pending+active+suspended y se
  cortan TODAS; una fila sin `provider_ref` (nunca llegó a PayPal) se cierra en local y **no bloquea
  la baja**. Ajustes usa `sub_para_mostrar()`, que sincroniza UNA vez la 'pending' dudosa para no
  decir "sin cobro automático" a quien sí le van a cobrar.
- 🔴 **La letra pequeña del carrito se contradecía (2026-08-05).** Decía *"Se renueva sola cada mes"*
  **y justo debajo** *"Pago único, nadie te vuelve a cobrar"*. Dos fallos superpuestos, los dos en
  `checkout.html`/`pay.css`: (1) `hidden` es solo `display:none` de la hoja del NAVEGADOR y
  **cualquier regla de autor le gana** — `.pfi{display:flex}` dejaba visible la línea marcada como
  oculta (fix: `.pfi[hidden]{display:none}`); (2) `letra()` miraba solo `.prail-in:checked`, y **con
  un solo riel no hay radios** (la fila solo informa) → nada marcado → anunciaba "pago único" aunque
  fuera a cobrarse solo (fix: `data-rail` en la etiqueta, se lee de ahí). Verificado en navegador con
  1 riel y con 2, y **reproducida la causa exacta** borrando la regla nueva en caliente: vuelven a
  salir las dos frases. ⚠️ Regla general: `[hidden]` **no sirve** en un elemento con `display` puesto
  por clase; si se oculta por JS con `hidden`, hay que añadir la regla `[hidden]` al lado.
- **`tools/paypal_plan_diario.py`** cierra la mitad que los avisos simulados NO prueban: crea en
  **sandbox** un plan de ciclo **DIARIO** para ver una renovación REAL en ~24 h (PayPal cobra solo y
  manda su aviso sin que nadie vuelva a la web, que es justo lo que pasa en una renovación de
  verdad). Se niega a correr con `PAYPAL_ENV=live`. `apagar` lo desactiva.
- **`tools/check_suscripcion.py` (2026-08-08) prueba una suscripción REAL sin que nadie pague.**
  `check_subs.py` mira los PLANES (el molde); éste mira lo que PayPal tiene anotado para UNA
  persona: primer mes, renovación, fecha del próximo cobro. 🔑 **PayPal registra los importes en
  cuanto el comprador llega a la pantalla de aprobación, ANTES de mover un dólar** → basta con
  empezar una compra y CERRAR esa pantalla. Compara los tres pares que tienen que cuadrar (lo que
  cobró el carrito ↔ el tramo TRIAL · lo que Ajustes anuncia ↔ el tramo REGULAR · que ese sea
  mensual sin fin) y grita si no cuadran, que es el descuadre que acaba en disputa y es invisible
  desde la web. `venv/bin/python3 tools/check_suscripcion.py [usuario|I-xxx|--todas]`.
  `test_check_suscripcion.py` 13/13. ⚠️ **Un cupón del 100% NO sirve para probar nada de esto:** un
  pedido de $0 no toca la pasarela (se activa solo, `payment_method='free'`) y no crea suscripción.
  ⚠️ Con `PAYPAL_ENV=live` una compra de prueba **SÍ entra en el libro de ventas** (`is_test` solo
  se sella solo en sandbox) → hay que revertirla a mano en /admin, y queda tachada.
- **`tools/check_subs.py`** contesta *"¿sirven de verdad las renovaciones?"* sin esperar un mes:
  pregunta a PayPal si los dos planes existen, están ACTIVOS y son mensuales sin fin; si los ids no
  están cruzados; y si el webhook apunta a `SITE_URL` por HTTPS con `PAYMENT.SALE.COMPLETED` (por ahí
  llega cada cobro; sin él se cobra y el plan no se extiende, en silencio). Da un veredicto por plan.
- **Al pasar a LIVE no cambia NADA del código**, solo la config: los ids de plan y el webhook **no
  cruzan de sandbox a live** → repetir `set_paypal.py` + `paypal_setup_webhook.py` con credenciales
  Live y volver a correr `check_subs.py`.
`tools/test_renovaciones.py` **20/20** (fecha mostrada, cobro mensual que extiende, aviso repetido que
no regala mes, baja que corta pending+active, PayPal que no responde → no se miente, fila huérfana).

## 🛒 CARRITO CON MINIATURAS + RECIBO CON IDENTIDAD (2026-08-05)
- **El carrito enseñaba un rectángulo gris** en vez del producto. El código YA intentaba reutilizar
  el arte de la tarjeta, pero **cada tipo lo guarda en un sitio distinto** y solo miraba uno:
  camo → fondo del `.camo-swatch` · marco → fondo de `.cm-plate-strip`, que es un **hijo** · cursor →
  un `<img>`, sin fondo ninguno. `arteDe(card)` busca los tres. El cursor va **contenido** sobre
  fondo claro (`.cp-art.cur`): es una figura de 32px con transparencia y a `cover` no se reconoce.
  ⚠️ La imagen se asigna por **propiedad** (`el.style.backgroundImage`), nunca dentro del string de
  HTML — un `url("…")` lleva comillas dobles y parte el atributo `style` (misma trampa de la tienda).
- **El "cuadrado" del recibo era un emoji sin fuente:** 🧾 (U+1F9FE, de 2018) no está en todas las
  fuentes del sistema y el navegador dibuja el *tofu*. 🔴 **Regla: un icono de la interfaz no puede
  depender de las fuentes de quien mira → SVG inline.**
- 🔴 **La lista del recibo se escribió DE MEMORIA y se dejó fuera medio plan** (lo cazó el dueño
  mirándolo en francés): Premium anuncia **9 funciones** en el reveal de UNLOCKED (`FEATURES` en
  `index.html`) y el recibo enseñaba 4 — faltaban Quiz, Reto Diario, Chalkboard y Synapse. Corregido
  a 9+1 (proyectos) ×4 idiomas, con los MISMOS nombres que el reveal. **Regla: la lista del recibo y
  la del reveal son la misma cosa; al tocar una, tocar la otra.**
  `tools/test_recibo_features.py` **15/15** compara ambas y falla si se desincronizan.
- **`/checkout/status` con identidad de plan:** hero y pastilla en dorado (Premium) o acero
  (Standard), bloque **"Lo que acabas de desbloquear"** con las ventajas del plan comprado, y la
  **fecha del próximo cobro** con su importe (la pregunta que todos se hacen al pagar; decirla ahí
  sale más barato que un correo a soporte, y que una disputa). 21 claves `cstat.*` ×4.
  · El estado salía crudo de la base (*"Estado: paid"* en la página en español) → traducido, con el
    valor crudo de reserva para lo raro, que es lo que soporte necesita ver.
  · Con el plan ya activo el botón dorado era **"Necesito ayuda"** — empujar a soporte a quien acaba
    de tener una compra perfecta. Ahora el dorado es "Volver a la app"; soporte manda solo mientras
    el pago está en el aire.
- ⚠️ **Sin `FLASK_DEBUG` Jinja cachea las plantillas**: hay que reiniciar el server o la prueba en
  navegador mide la versión vieja (volvió a pasar).
- **PayPal "Pay in 4" — NO se puede quitar, y no hace falta.** El dueño temía cobrar a plazos: con
  Pay Later **PayPal le paga el importe COMPLETO al capturar** y asume el riesgo de impago. En el
  flujo de redirección (el nuestro) la oferta la decide PayPal según el comprador; solo se puede
  filtrar con `disable-funding` del SDK de JavaScript, que no usamos. Fuente: PayPal.

## 🔴 NADIE PAGA UN MES QUE YA TIENE PAGADO (2026-08-05)
El dueño, textual: *"si yo pago 4 premiums por adelantado, ¿qué sentido tiene que al cabo de un mes
me cobren de nuevo la mensualidad? Va totalmente en contra de la protección al consumidor."* Tenía
razón, y no era solo el número raro de la pantalla.
- **Dos cosas correctas por separado que juntas cobran de más:** cada compra suelta SUMA 30 días al
  vencimiento (bien: una renovación no debe quitarte lo que te queda), pero el cobro automático de
  PayPal corre por su cuenta cada 30 días. Quien pagara 3 meses de golpe acumulaba 90 días **y**
  seguía pagando cada 30.
- 🔴 **El agujero:** el candado de "no compres el plan que ya tienes" vivía SOLO en `/checkout` (el
  GET, la pantalla). **`/checkout/create` (el POST) no lo repetía** → un formulario viejo, el botón
  atrás o un enlace guardado creaban el pedido igual. Medido con el código anterior: 3 intentos =
  **$75 cobrados y 89 días apilados**.
- **Regla fijada por el dueño:** **nadie paga más de un plan a la vez**, ni siquiera adelantando
  meses (el ciclo anual, que sería la vía legítima, sigue apagado hasta tener un método con menos
  exposición a contracargos que PayPal). Un solo decisor `puede_comprar(user, plan)` que usan **las
  dos** puertas: rechaza **el mismo plan** (`ya_lo_tienes`), Free (`no_existe` — bajar a Free es el
  botón de baja en Ajustes) y, de cinturón, cualquier suscripción viva de ese plan aunque
  `user.plan` todavía no lo refleje (`ya_suscrito`).
- ✅ **CAMBIAR de plan se permite en LAS DOS direcciones (2026-08-05).** Bajar estaba bloqueado y era
  un callejón sin salida: un Premium solo podía irse cancelando y esperando a que se le acabara el
  mes. En `/pricing` la tarjeta Standard mostraba un **"—"** a los Premium → ahora **"Cambiar a
  Standard"** (`pricing.switchStandard` ×4).
- **Al cambiar, el mes EMPIEZA DE CERO** (decisión explícita del dueño): los días que quedaban del
  plan anterior **no se arrastran ni se suman**. Ya era el comportamiento del código; lo que faltaba
  era **decirlo antes de cobrar** → aviso ámbar `.pswap` en el carrito con **los días exactos que
  pierde** (`checkout.swapTitle/swapBody` ×4, verificado en navegador en los 4 idiomas).
  ⚠️ El aplicador de `pages_i18n.js` no sustituía variables → se le añadió **`data-i18n-vars`**
  (JSON en el atributo). Hacía falta porque el número lo sabe el SERVIDOR y el texto que lo rodea
  cambia de orden entre idiomas; partir la frase en trozos no funciona en FR/PT.
- ⚠️ `test_circuito_completo` afirmaba *"no puede bajar a standard estando en premium"* — regla
  vieja, actualizada a la nueva (y se le añadió el check de que sí se le avisa).
- ⚠️ `tools/test_promo_31.py` probaba la cláusula 3.1 **recomprando el mismo plan**, que ya no se
  puede: se reencuadró sobre una SUBIDA de Standard a Premium (misma cláusula, compra legítima).
`tools/test_meses_apilados.py` **15/15** (con el código viejo fallan 5, incluido el caso exacto).

## ⬇️ BAJAR DE PLAN SE PROGRAMA (2026-08-05, decisión del dueño)
**Regla:** **subir** = inmediato (pagas hoy, mes nuevo, pierdes los días del plan barato — avisado en
el carrito). **Bajar** = **programado**: no se cobra nada hoy, conservas tu plan hasta la fecha que ya
pagaste, y ese día empieza el más barato. Se puede cancelar desde Ajustes hasta que entre en vigor.
- **Por qué:** el downgrade inmediato cobraba $25 el mismo día y tiraba los días de Premium que
  quedaban → quien llevaba 3 días pagaba **$75 por un mes de Standard**. Es el mismo principio de los
  meses apilados (nadie paga dos veces el mismo período) y además **contradecía la Secc. 5 de los
  T&C**, que promete acceso hasta el final del período pagado. La opción programada es la única que
  **no necesita cláusula de excepción** — ése fue el criterio con el que el dueño eligió.
- **Cómo:** endpoint **`revise`** de PayPal (`_paypal_sub_revise`), que aplica el plan nuevo **a
  partir del siguiente ciclo** sobre la MISMA suscripción — no hay que cancelar y recrear, así que
  deshacerlo es otra revisión. El precio se manda sobrescribiendo el `pricing_scheme`, así el
  descuento del socio sobrevive también al cambio. ⚠️ Hasta que el cliente **no aprueba en PayPal**
  no cambia nada: sigue con su plan y su importe (fallo seguro correcto).
- Columnas nuevas `PlanSubscription.pending_plan/pending_price/pending_at`
  (`_migrate_sub_pending_columns`, cubiertas en `test_boot_migracion` 6/6). `_aplicar_cambio_si_toca`
  vuelca el cambio al llegar el cobro, mirando **fecha O importe** (un aviso que se retrasa unas horas
  sigue siendo del plan nuevo; un reloj desajustado no debe entregar lo que no se pagó) y corre
  **antes** de `_sub_cobro`, que crea el pedido a partir de `sub.plan`.
- Pantalla propia `checkout_switch.html` (no un carrito: no hay nada que cobrar, enseñar un total
  sería mentir), rutas `/account/switch-plan[/return|/cancel]`, y Ajustes muestra "Cambia a X el
  <fecha> · $Y" con botón de deshacer. 11 claves `swap.*` + 6 `settings.switch*` ×4 idiomas.
- **T&C Secc. 5**: párrafo nuevo *"Un solo plan a la vez; cambio de plan"* — no acumulables, ni
  recomprar ni adelantar meses; subir es inmediato y el período anterior termina ahí; bajar se
  programa; un cambio pedido por el cliente no es una baja ni da derecho a reembolso. ×4 idiomas,
  `audit_legal_translations.py` 144 cláusulas OK.
`tools/test_cambio_plan.py` **28/28** + navegador real ×4 idiomas.

## ⬆️ SUBIR DE PLAN — nunca dos cobros a la vez (2026-08-05)
Miedo del dueño, textual: *"compro standard y más tarde upgradeo a premium: ¿me cobran solo el
último, o los dos?"*. **Solo el último**, y ahora también en el caso feo.
- **Camino normal:** al activarse la nueva, `_sub_activada` corta en PayPal **todas** las demás del
  usuario. Probado en las dos direcciones (subir y bajar): queda UNA viva y el plan de la cuenta la
  refleja.
- **Caso feo (el que faltaba):** aprueba el Premium, cierra la pestaña y el aviso se pierde → la
  vieja sigue activa en PayPal y la nueva está 'pending' de nuestro lado = **dos cargos el mes que
  viene**. Ahora, antes de dar por bueno un cobro, `_sobra_esta_suscripcion()` mira si hay una
  posterior que PayPal dé por activa; si la hay, **corta la vieja en el acto** (no habrá un segundo
  cargo), **acredita igual el dinero que ya se movió** (quedárselo sin dar días sería peor) y manda
  `_avisar_doble_cobro` al dueño, porque el reembolso lo decide una persona.
- 🔴 **Bug real cazado al probarlo:** `_sub_cobro` ponía la suscripción en `active` sin mirar su
  estado, así que el último cargo de una recién cancelada **la resucitaba** — la ficha decía que
  seguía cobrando algo que en PayPal ya no existe. Ahora solo revive desde `pending` (alta normal) o
  `suspended` (PayPal la suspendió por un cobro fallido y ahora sí cobró). `cancelled` no vuelve.
- ⚠️ **Subir de plan REINICIA el mes** (no prorratea): quien lleva 5 días de Standard y pasa a
  Premium pierde los 25 restantes. Es la regla actual y es defendible, pero está sin decir en
  ninguna pantalla — si algún día hay quejas, es aquí.
- **La letra pequeña del carrito** ya no depende del JS: el servidor pinta la frase correcta de
  entrada (`auto0` en `checkout.html`), porque ya sabe qué riel viene marcado. Antes mandaba "pago
  único" oculto-a-medias y lo corregía el JS al cargar → parpadeo, y frase falsa si el JS no corría.
`tools/test_upgrade.py` **18/18**.

## 🔴 BAJA → BORRADO: el orden es sagrado (2026-08-10, decisión del dueño)
**La regla, en una línea: el borrado de cuenta NO cancela nada; EXIGE que la baja ya esté hecha.**
- **"Cancelar plan"** es el ÚNICO sitio que corta cobros. Usa `_cortar_todos_los_cobros()`, que
  mira **todas** las filas con `provider_ref` (`permisos_de_cobro()`, no solo pending/active/
  suspended: una fila que aquí consta 'cancelled' puede seguir viva ALLÍ si un corte falló), las
  cancela y después **le PREGUNTA a PayPal** que ninguna pueda cobrar. `_sub_puede_cobrar` responde
  **True ante una API muda** → un fallo de red bloquea, nunca deja pasar. Sin confirmación NO se le
  dice "cancelado" (`sec=cancel_failed`).
- **"Eliminar cuenta"** solo comprueba que no quede cobro posible; si lo hay responde
  `del_active` ("cancela tu plan primero"). 🔑 **Motivo del dueño:** si algo fallara tras borrar, esa
  persona no tendría ni cómo volver a soporte — su cuenta ya no existe. Con este orden, *cuenta
  borrada + cobro vivo* es **imposible por construcción**, y mientras el cobro exista la cuenta
  existe y puede escribir.
- Redes que quedan detrás: guard de cuenta borrada en **`_activate_plan_from_order`** (la puerta
  común de los **6** caminos que activan un plan — estaba solo en `_sub_cobro`, o sea 5 abiertos), y
  `_avisar_cobro_a_borrada` si aun así llegara dinero (no revive el plan, no anota comisión —ese
  dinero se devuelve, no se reparte—, reintenta cortar y avisa por WhatsApp+correo).
- **`tools/check_borrados.py`** = el vigilante. Recorre las cuentas borradas y le pregunta a PayPal
  por cada permiso; `--cortar` cancela lo que siga vivo. Salidas para cron: **0** limpio · **2** algo
  vivo · **3** no se pudo comprobar ("no lo sé" NO es "está bien"). Lee las credenciales de
  `scalpel/.env` (verificado 2026-08-10: son las mismas LIVE que usa supervisor).
  ⚠️ **PENDIENTE: dejarlo en un cron diario.** Sin eso hay que acordarse de correrlo.
- 🔴 **Tres bugs REALES cazados al auditarlo, todos invisibles en SQLite:**
  (1) **el foro no se borraba y en silencio** — borrar una publicación es FK violation en PostgreSQL
  (comentarios/reacciones/guardados de OTROS la referencian sin cascada) y el `try/except` por tabla
  se lo tragaba: la cuenta quedaba "eliminada" y sus publicaciones seguían con su texto. Ahora se
  **VACÍA** (`title/body=''` + `is_deleted`), que es el mecanismo que el foro ya usa; (2) fuera el
  `try/except` por tabla — el borrado es **todo o nada** (`del_error`); (3) **`deleted_N` era
  secuestrable** (username es único: alguien registra `deleted_7` y revienta el borrado del 7) →
  marca **`deleted#N`**, y `USERNAME_RE` no admite `#`.
  `tools/test_borrado_fk.py` corre con `PRAGMA foreign_keys=ON` para que SQLite se porte como PG.
- ⚠️ **Trampa de los simuladores:** los PayPal falsos de `test_subs`/`test_renovaciones` respondían
  ACTIVE **después** de cancelar (el real no), y tumbaban la verificación nueva. Un doble de prueba
  que miente hace fallar código correcto.
- 🔴 **LO QUE SIGUE SIN PROBARSE:** nadie ha visto cancelarse una suscripción **ACTIVE de verdad** —
  haría falta una suscripción real (cuenta de comprador + primer cobro). Lo demás sí tocó PayPal
  live. Tests: `test_cuenta` 45/45 · `test_borrado_fk` 15/15 · `test_check_borrados` 10/10.

## 🟢 Stripe — pagos con tarjeta (código LISTO, probado en TEST 2026-07-12)
Integración **condicional**: totalmente inerte hasta setear `STRIPE_SECRET_KEY` → sin la clave, prod
sigue con el flujo manual USDT/Binance intacto (cero regresión). Reutiliza el `Order` model y
`_activate_plan_from_order` (idempotente) existentes; **nada** de doble activación aunque el webhook
dispare dos veces.
- **Flujo:** `/checkout/create` crea la Order `pending` → si `STRIPE_ENABLED` y `final_price>0`,
  crea Stripe Checkout Session y redirige a la página hosteada de Stripe → el pago se confirma por
  `/webhook/stripe` (canónico, server-to-server) **y** por `/checkout/success` (verifica la sesión
  vía API de Stripe; sirve para test local sin webhook). Ambos llaman `_activate_plan_from_order`.
- **Piezas nuevas** (`app.py`): bloque config Stripe (~línea 195, `STRIPE_SECRET_KEY`/
  `STRIPE_WEBHOOK_SECRET`/`STRIPE_ENABLED`, import perezoso de `stripe`), rama Stripe en
  `checkout_create`, rutas `checkout_success` + `stripe_webhook`. Template nuevo
  `checkout_success.html` (i18n EN/ES/FR/PT, claves `csuccess.*` en `pages_i18n.js`). `stripe>=11.0.0`
  en `scalpel/requirements.txt`.
- **Probar en TEST (sin LLC ni dominio, gratis):** (1) cuenta en stripe.com, copiar `sk_test_…`;
  (2) `pip install stripe`; (3) exportar `STRIPE_SECRET_KEY=sk_test_…` y correr
  `FLASK_DEBUG=1 python3 scalpel/app.py`; (4) ir a /pricing → elegir plan → paga con tarjeta de
  prueba `4242 4242 4242 4242` (cualquier fecha futura/CVC) → aterriza en `/checkout/success` con el
  plan activado. El webhook local requiere Stripe CLI (`stripe listen --forward-to
  localhost:5001/webhook/stripe`) pero **no es necesario** para el test porque success-page también
  activa. Seguridad: success-page solo activa si `payment_status=='paid'` **y** la Order es del
  usuario logueado; el webhook verifica firma si `STRIPE_WEBHOOK_SECRET` está seteado.
- **Para LIVE (LLC ya hecha):** solo falta config — claves `sk_live_…`/`whsec_…` + conectar la cuenta
  bancaria del amigo en el dashboard de Stripe (payouts) + webhook con dominio/HTTPS. Cobro USD por
  tarjeta → payout al banco del amigo (Stripe maneja el payout; el código no necesita datos bancarios).
  **NO se cobra USDT/Binance.** Ver "🚨 Alerta recurrente" #2.

## 🔴 Bug de PRODUCCIÓN resuelto (2026-08-02) — la app no arrancaba tras el deploy
**Síntoma:** supervisor eternamente en `STARTING`, puerto 5001 sin escuchar, `Worker failed to
boot`, RAM/disco/CPU perfectos. **Causa:** `_migrate_user_alt_id_column()` hacía el backfill con
una consulta **del ORM**, que SELECTea TODAS las columnas del modelo `User`; en `init_db()` corría
ANTES de `_migrate_user_security_columns()`/`_migrate_referral_columns()`, así que en prod (tabla
`user` ya existente, sin esas columnas) reventaba con `UndefinedColumn: user.birth_date` y **morían
los 4 workers al arrancar**. En local NUNCA se ve: `create_all()` nace con todas las columnas.
**Fix en dos capas:** (1) el backfill pasa a **SQL crudo** tocando solo `id`/`alt_id` → inmune a
cualquier columna futura del modelo; (2) todas las migraciones de la tabla `user` se agrupan ARRIBA
del `alt_id`. ⚠️ **REGLA PERMANENTE: ninguna migración puede usar el ORM.** El ORM pide el modelo
COMPLETO; una migración corre justamente cuando la base todavía NO lo está. (Había un comentario en
el código advirtiendo esto desde hacía meses y aun así se violó al agregar el paquete de seguridad.)
⚠️ **Y una lección de proceso:** el paquete de seguridad se probó con 37 checks sobre SQLite
**creada desde cero** — eso no prueba NADA sobre un deploy. Toda columna nueva se prueba con
`scratchpad/test_boot_migracion.py`, que borra las columnas de una base ya creada y vuelve a
arrancar la app (con el código viejo da 1/5, con el arreglo 5/5).

## 🔴 Bug de PRODUCCIÓN resuelto (2026-07-27) — secuencias de PostgreSQL desincronizadas
**Síntoma:** al agregar un gasto en /admin → 500 `UniqueViolation: duplicate key ... expense_pkey,
Key (id)=(1) already exists`. **Causa raíz:** la base de prod tiene filas importadas con `id`
explícito (dump restaurado / migración desde SQLite); esas inserciones NO avanzan la secuencia de
PostgreSQL, así que el contador quedó en 1 mientras las filas iban por id 2, 7, etc. El siguiente
INSERT pide id=1 → choque. **NO era pérdida de datos.** **Fix:** `_resync_postgres_sequences()` en
`init_db()` — recorre todas las tablas, y si `max(id) > last_value` de su secuencia, la adelanta con
`setval`. Solo en PostgreSQL, solo hacia adelante (nunca atrás), guarded por tabla.
⚠️ **Ojo con `is_called`:** una secuencia recién creada tiene `last_value=1, is_called=false` y entrega
el 1 en la próxima llamada. La 1ª versión del fix comparaba `max_id > last_value`, así que una tabla con
UNA fila en id=1 (caso `mentorship_live_state`) quedaba sin reparar y seguía chocando. La condición
correcta —ya aplicada— es: `next_id = last+1 if is_called else last`; si `next_id <= max_id`, `setval(seq,
max_id, true)`. Verificar siempre con `tools/check_pg_sequences.sql` (esa consulta SÍ lo detectaba). Reproducido en un
PostgreSQL real y verificado el antes/después. ⚠️ **Afectaba a TODAS las tablas, no solo `expense`** —
`order`, `user`, foro, etc. habrían fallado igual en la primera venta real.
⚠️ **Aparte (UX, no bug):** el panel de gastos filtra `incurred_on >= inicio del mes actual`, así que
los gastos de meses anteriores existen en la base pero NO se ven. Se siente como si se hubieran
borrado. PENDIENTE: agregar selector de mes / historial.

## 🗂️ CHALKBOARD — biblioteca de pizarras + tope de diapositivas (2026-08-12)
> ✅ **CERRADO PARA EL LANZAMIENTO (decisión del dueño, 2026-08-12):** *"por y hasta ahora podemos
> dejar el chalkboard tal cual al menos para aperturar la página al público, luego más adelante
> iremos agregando cosas, recibiendo reportes"*. **No seguir metiéndole herramientas por iniciativa
> propia** — lo que entre a partir de ahora sale de reportes de usuarios reales.
Pedido del dueño: *"limitar el número de diapositivas… no quiero que alguien malintencionado cree
40000"* y *"algo para poder guardar tus proyectos, y una vez guardado que se te reinicien las
diapositivas… alguna especie de biblioteca donde vayan esos proyectos, y que alguien pueda volver a
editarlos, exportarlos a PDF, presentar"*. Cierra el punto **"persistencia server-side de Scalper
boards"** que llevaba desde antes del lanzamiento en la lista de críticos.
- 🔴 **MEDIDO antes de elegir el número, y el peligro real no era el malintencionado:** una
  diapositiva con fondo de **REJILLA pesaba 32,3 KB** contra **0,3 KB** una con fondo liso — cien
  veces más. Causa: `canvas.toJSON()` **hornea el fondo como una imagen base64 del lienzo entero** y
  se guardaba **una copia idéntica por diapositiva** (y otra por cada paso de deshacer). Con el cupo
  de ~5 MB del navegador eso son **~155 diapositivas**, y al llenarse **`persist()` fallaba EN
  SILENCIO** (`catch (e) {}` mudo): seguías dibujando encima de algo que ya no se guardaba y al
  recargar aparecía la versión de hacía media hora. **Fix:** `instantanea()` quita el
  `backgroundImage` (el fondo ya lo manda `s.bg`, que se reaplica al cargar) → **32,3 → 0,1 KB**.
  ⚠️ `loadJSON` tuvo que volver a poner el fondo, o **deshacer** dejaba la diapositiva lisa.
- **Números FIJADOS por el dueño (2026-08-12, tras enseñarle lo medido):** **20 diapositivas por
  proyecto** (`MAX_SLIDES`) y **30 proyectos por cuenta** (`CHALK_MAX_BOARDS`). Él lo planteó al
  revés de mi primera propuesta y tenía razón: con proyectos, una clase larga se parte en dos y se
  organiza mejor que en una tira de 60. **Lo medido que sostiene el 30:** una diapositiva cargada al
  máximo (secuencia de velas + 10 objetos) = **28 KB** → un proyecto de 20 así = 560 KB → **30
  proyectos = 16 MB por usuario en el PEOR caso**; lo normal, 1-3 MB. Con 100 premium, ~300 MB
  reales. **El límite no lo pone el disco**, lo pone que una biblioteca de 60 tarjetas ya no se
  navega. El tope de diapositivas **avisa**, no ignora el clic; y el fallo de guardado ya no es
  mudo: `scalper.saveFail` dice que exportes a PDF ya.
- **Biblioteca:** modelo `ChalkBoard` + `/api/chalk/boards` (GET lista sin el contenido · POST
  guarda/sobrescribe · GET `<id>` abre · DELETE · POST `<id>/rename`), todo `@premium_required` y
  filtrado por `user_id`. **`CHALK_MAX_BOARDS = 20`** (decisión del dueño) impuesto **en el
  servidor**, `CHALK_MAX_BYTES` 2 MB y miniatura recortada a 120 KB. 🔑 **Con la biblioteca llena se
  puede seguir guardando SOBRE una existente** — si no, llenarla te dejaría sin poder guardar tu
  trabajo. Se guarda **el MISMO JSON que ya vivía en el navegador**, así que abrir = cargar ese
  estado; no hay una segunda representación que se desincronice.
- **Guardar = archivar y empezar en blanco** (decisión suya), con **"Devolvérmela"** en el aviso por
  si guardó sin querer. Abrir una pizarra **pide confirmación** si hay trabajo sin guardar en el
  lienzo (si no, un clic curioso se lleva por delante lo que estabas haciendo). Presentar y Exportar
  PDF son los botones de siempre, sobre la pizarra ya abierta.
- 🔴 **`window.T` NUEVO, y el motivo importa:** `I18N`/`currentLang` son `const`/`let` del `<script>`
  #12 y **eso NO los pone en `window`** — el Chalkboard vive en el #13 y no los veía, así que el
  primer aviso salió con la **clave cruda** en pantalla. Cualquier mensaje que se arme en tiempo de
  ejecución fuera de ese bloque necesita `window.T`. 22 claves `scalper.*` nuevas ×4 idiomas.
  ⚠️ El nombre por defecto reusaba `scalper.library` y proponía *"Biblioteca 2026-08-12"* como
  nombre de una pizarra → clave propia `scalper.newName`.
- ⚠️ **Trampa de medición (costó un falso fallo):** `locator.screenshot()` fotografía **la zona de
  pantalla** donde está el elemento, o sea que **incluye lo pintado encima**. El aviso "Guardada"
  cae sobre el lienzo → una pizarra recién vaciada marcaba 3.754 px "dibujados" y parecía que no se
  limpiaba. Para medir el LIENZO hay que leer `getImageData` del canvas.
- ⚠️ Al llenar la pizarra, el navegador se queda renderizando 60 miniaturas **más de los 6 s que
  dura el aviso** → mirarlo después de los 80 clics medía uno ya desvanecido.
- 📈 **HERRAMIENTAS DE OPERATIVA (2026-08-12).** Pedido suyo: *"más herramientas tipo la de conjunto
  de velas: ejemplo las de Take profit y SL"*. Dos nuevas, con **el mismo gesto que ya aprendió con
  las velas — el SENTIDO del arrastre decide**:
  · **Posición (`trade`, atajo `g`) — el R:R SE MIDE (2ª versión, mismo día).** Pedido del dueño:
    *"no se puede colocar para que realmente mida el margen R:R? tipo, si lo achicas baja a 1;2"*.
    🔑 **No se podía con la 1ª versión y el motivo importa:** la posición es UNA pieza agrupada, así
    que al achicarla **las dos zonas escalan igual** y la proporción es invariante — un 1:2 seguía
    siendo 1:2 por mucho que la encogieras. Para que el número signifique algo, el objetivo lo tiene
    que poner el usuario → **gesto de DOS pasos**: se arrastra de la entrada al stop (fija el
    riesgo) y luego el objetivo **sigue al ratón con el múltiplo recalculándose en vivo** hasta que
    se hace clic. Probado: 1:1, 1:3 y una venta a 1:2, todos medidos del dibujo.
    ⚠️ Consecuencia buena: como el grupo escala entero, **el número que quedó escrito nunca se
    vuelve mentira** al mover o redimensionar la pieza.
    · **Esta herramienta SÍ se apaga al colocarla** (petición expresa del dueño) — la excepción a la
      regla pegajosa, y con sentido: una posición se dibuja de una en una, no de tres en tres como
      los niveles. Clic derecho / Esc / cambiar de herramienta cancelan una a medio colocar.
    · Un decimal solo cuando hace falta (`1 : 2 R`, pero `1 : 1.7 R` no se redondea a 2 y miente).
    · La alternativa —tiradores para mover TP y SL por separado— se descartó: en fabric exige una
      clase propia con `toObject/fromObject`, y **los controles a medida NO sobreviven a
      `loadFromJSON`**, o sea que se perderían al reabrir la pizarra desde la biblioteca.
  · **Fibonacci (`fib`, atajo `i`)**: 0 donde sueltas y 1 donde empezaste (como en un gráfico de
    verdad), niveles 0/.236/.382/.5/.618/.705/.79/1 y **la banda OTE 0,62–0,79 sombreada**, porque
    OTE es una de las metodologías del sitio.
    ⚠️ La etiqueta "OTE" NO va en el centro de la banda: el centro es 0,705, que es un nivel, y caía
    encima de su línea. Va en el hueco (0,662).
  · 🔑 **Las dos entran en la familia existente** (que pasa de "Velas" a "Trading"): mismo gesto,
    misma cabecera, y **la barra no crece ni un botón**.
- 🛠️ **PIEZAS EDITABLES DE VERDAD (2026-08-12, 3ª versión — la que pidió).** Su veredicto de la
  anterior: *"está muy precaria esa herramienta, debe de ser algo como la de TradingView"*, con tres
  peticiones: editar el R:R después de colocarlo, poder separar TP arriba/abajo y SL arriba/abajo, y
  que los niveles y **colores** del Fibonacci se editen.
  · 🔑 **Por qué hubo que cambiar el fondo:** un `fabric.Group` es un dibujo MUERTO — sus piezas ya
    están calculadas, así que arrastrar un lado escala todo por igual y el R:R no puede cambiar.
    Ahora son **clases propias** (`fabric.Posicion`, `fabric.Fibo`) que guardan los NÚMEROS (riesgo,
    recompensa, niveles, colores) y se repintan de ellos: eso es lo que permite tiradores
    independientes y que el múltiplo se calcule **al pintar**, así que nunca queda viejo.
  · 🔴 **La trampa resuelta de entrada:** las pizarras se guardan en la biblioteca como JSON, y un
    objeto a medida solo revive si declara sus campos en `toObject` **y** registra `fromObject` con
    el nombre que fabric busca por su `type`. Los **controles NO se guardan nunca** → viven en el
    **prototipo**, así los hereda también una pieza revivida de la base. Verificado: se guardan como
    `['posicion','fibo']` y al reabrirlas siguen editables (un R:R tecleado de 3.5 sobrevivió).
  · **Posición:** tiradores de TP y SL por separado; **cruzar el TP por debajo de la entrada da la
    vuelta a la operación** (el stop se va al lado contrario — TP y SL del mismo lado no es ninguna
    operación). Barra propia con **R:R tecleable**, botón Compra/Venta y colores de TP, SL y entrada.
    Medido: bajar el TP → 1:1, subirlo → 1:3.7, cruzarlo → pasa a venta.
  · **Fibonacci:** barra con **un chip por nivel** (10 en el catálogo, 8 encendidos de salida) y
    colores de líneas, etiquetas y banda OTE, más tiradores en los dos extremos del recorrido.
  · ⚠️ **`_mueveExtremo` deja la ENTRADA clavada:** al cambiar el alto, fabric recoloca la caja por
    su centro y la entrada se desplazaría sola — moverías el TP y se te iría también el precio de
    entrada.
  · ⚠️ **Los `positionHandler` usan `finalMatrix` y FRACCIONES de `dim`**, como los controles de
    fabric. Con `calcTransformMatrix()` y píxeles absolutos los tiradores salían disparados fuera de
    la pieza (el del stop acababa en el fondo del lienzo).
  · 🔴 **`fabric` se carga BAJO DEMANDA**: declarar las clases en el cuerpo del módulo reventaba con
    *"fabric is not defined"* y dejaba la pizarra entera sin arrancar. Van en `defineClases()`, que
    se llama al crear el lienzo. Las constantes que usa la barra de edición van FUERA.
  · **`window.__skCanvas`** ahora lo publica la app: el lienzo vive en un closure y sin ese handle
    las pruebas tenían que adivinar midiendo píxeles (el test lo intentaba y salía siempre null).
  · ⚠️ **Trampa que costó una hora:** al colocar una pieza aparece su barra de edición y **el lienzo
    baja ~61 px**. Con la medida vieja los clics caían fuera y parecía que los tiradores no
    funcionaban, cuando funcionaban perfectamente. **Re-medir el lienzo tras colocar.**
- 🧭 **7 HERRAMIENTAS MÁS + FIBONACCI CONFIGURABLE (2026-08-12).** Pedido: *"agrega muchas más
  herramientas de trading. No solo pienses en ICT, recuerda que manejamos Wyckoff, harmonic,
  Elliott, SMC, análisis técnico, patrones chartistas"*, todas con la regla *"si aplicas alguna de
  estas herramientas, debes volver a seleccionarla si quieres colocar otra"*.
  · 🔑 **UN SOLO MOTOR de varios clics** (`MULTI` + `multiEmpieza/Punto/Previo/Cierra/Cancela`):
    armónicos, Elliott, HCH y canal son el MISMO gesto —marcar N puntos y unirlos—, solo cambia lo
    que se dibuja al final. **Añadir el próximo patrón son ~15 líneas**: una entrada en `MULTI` y su
    rama de dibujo. La figura sigue al ratón mientras se marca; clic derecho / Esc cancelan.
  · **XABCD armónico** (5 clics) con las **razones AB/XA, BC/AB, CD/BC calculadas del dibujo** — sin
    ellas un armónico es una polilínea de cinco puntos. ⚠️ **NO valida** si es Gartley/Bat/Cypher:
    dibuja y mide, no juzga (ponerle nombre exige rangos por variante; el dueño no lo pidió).
  · **Elliott 0-5** (6 clics) · **corrección ABC** (4) · **hombro-cabeza-hombro** (5 + clavicular
    automática por los dos valles) · **canal paralelo** (3: los 2 primeros la recta, el 3º el ancho;
    va con relleno o se lee como dos rectas sueltas) · **extensión de Fibonacci** (3, proyecta
    0/.618/1/1.272/1.618/2 desde C).
  · **Etiqueta de evento** (1 clic): la que más cubre por sí sola — catálogo `EVENTOS` con Wyckoff
    (PS, SC, AR, ST, Spring, Test, SOS, LPS, UTAD, BC) y SMC/ICT (BOS, CHoCH, MSS, OB, FVG, Liq,
    EQH, EQL, PDH, PDL). Lo que se anota en un gráfico son eventos CON NOMBRE, y el nombre se elige
    de una lista en vez de escribirlo cada vez.
  · **Familia nueva "Patrones"** en la barra para que el desplegable de Trading no se vuelva una
    lista de diez. Atajos `x` XABCD · `w` Elliott · `k` canal · `j` etiqueta.
  · **Fibonacci configurable** (lo pidió "tan editable como en TradingView"): los chips se
    **reconstruyen del catálogo UNIDO a los niveles de esa pieza**, así un nivel propio (0,886…) se
    quita igual que uno de fábrica — no hay dos clases de nivel. Campo para **añadir** cualquier
    nivel, **banda OTE reajustable** (dejó de estar clavada en 0,62–0,79), colores separados de
    líneas/etiquetas/banda y **grosor** de línea. Y el fib **también se suelta al colocarlo**.
  · ⚠️ La etiqueta de cada nivel de la extensión va a la DERECHA del final de su línea: encima, el
    último guion del punteado se lee como un signo menos (`- 2` → `-2`).
  · ⚠️ **La secuencia de velas se dejó PEGAJOSA a propósito** — él no la mencionó y no se le cambió
    algo que ya le funcionaba. Si algún día quiere la misma regla, es una línea.
  · `test_chalkboard_ux.py` **80/80** (18 comprobaciones nuevas; los patrones se verifican mirando
    los TEXTOS que quedan dentro de la pieza —las razones del armónico, las ondas, los niveles—, no
    que "dibuje algo").
- `tools/test_chalk_biblioteca.py` **23/23** (servidor: nadie ve ni toca las pizarras de otro, el
  tope se impone en el servidor, envíos gigantes rechazados) + `tools/test_chalk_lib_nav.py`
  **18/18** (navegador: guardar → queda 1 en blanco → deshacer → reabrir → **sobrevive a borrar el
  guardado local, que es el punto de tenerlo en el servidor** → borrar).
- [x] ✅ **15. Pre-Flight — estadísticas revisadas con una prueba real (2026-08-12).**
  🔑 **Antes de tocar nada se midió**, con `tools/demo_preflight.py`: 3 proyectos y ~92 trades
  registrados **por la API real**, con el generador declarado ANTES (uno con ventaja real metida a
  propósito, uno SIN ninguna señal, y uno de win rate bajo con R alto), repetido con **5 azares**.
  · 🔴 **"Mejor · peor confluencia" era una moneda:** en el proyecto que SÍ tenía una confluencia
    buena, el panel la acertó **1 de 5 veces** y una vez la señaló como la PEOR. En el proyecto donde
    ninguna confluencia hacía nada, coronaba una distinta cada tirada con porcentajes convincentes.
    También se probó el método correcto (con-la-casilla vs sin-ella): se acerca a la verdad (+8,1
    frente al +10 real) pero produce monstruos de +70 puntos calculados sobre **1 trade**. **No era
    la fórmula, era la muestra.**
  · 🔴 **"Mejor día de la semana"**: Vie/Mar/Mar/Lun/Jue entre semillas, siempre con 4 trades.
  · 🔴 **"Winning overrides"** decía *"rompiendo tus reglas ganaste el 56%"* sobre 9 trades, en una
    herramienta de disciplina.
  **REGLA NUEVA, de la que sale todo el rediseño: ninguna tasa sin su muestra, y ningún "mejor/peor"
  con menos de `MIN_MUESTRA`=10 por lado** (y 2 candidatos: llamar "mejor instrumento" al único que
  llega no es un ranking). Cuando no hay datos, **lo dice** en vez de coronar a alguien.
  **Fuera:** mejor·peor confluencia (por la de con-vs-sin), mejor día, overrides ganadores, tamaño
  medio de posición, R:R medio en ganadoras·perdedoras. **Dentro:** adherencia (% de los tomados que
  eran GO — lo que la herramienta existe para medir), **expectativa en R** (el dinero no se compara
  entre proyectos, la R sí; ordenó los 3 proyectos igual que la verdad), **drawdown máximo**,
  descartados y pendientes de marcar.
  · 🐛 **Bugs arreglados:** rachas y drawdown se calculaban por **orden de registro**, no por fecha
    del trade (quien anota el lunes los trades del viernes veía rachas falsas); la tira de arriba
    mezclaba las pizarras en un ranking único (una casilla de Wyckoff compitiendo con una de ICT) —
    ahora solo lleva números que sobreviven a juntar estrategias; tramos con n=1 mostrando 100%.
  · 🖥️ **Layout con muchos proyectos (Premium permite 10, no 5):** `white-space: nowrap` en los
    valores era lo que reventaba el ancho — con 3 proyectos la tabla medía **1255 px en un hueco de
    794** y la 3ª columna era invisible. Ahora los valores **envuelven** (con 3 proyectos la tabla
    mide 794 y cabe entera), la **primera columna se queda fija** al desplazar y hay **sombra en el
    borde** cuando queda algo a la derecha. Verificado con los 10: chips en 3 filas sin cortarse,
    último proyecto alcanzable, etiqueta de fila siempre visible, 0 errores JS.
  · **3 cosas más que reportó el dueño al verlo en su cuenta (2026-08-12):**
    (a) 🔴 **la "X" de borrar salía unas veces a la derecha y otras a la izquierda.** La fila es
    `flex` CON `wrap`, el selector de resultado llevaba `margin-left:auto` y la X era su hermano
    suelto: cuando el selector entraba justo al final de la línea pero la X ya no cabía, la X caía
    sola al principio de la línea siguiente. Ahora los dos van en una caja (`.pf-hist-acts`) que
    envuelve como UNA pieza — medido: las 92 filas con la X a 13 px del borde, sin excepción.
    (b) **Buscador y orden en la tabla del proyecto** (*"que alguien pueda ver la DATA de todos los
    trades… por si quiere buscarlos"*): campo de búsqueda sobre lo que el usuario VE (traducciones
    incluidas: "ganada" y "win" encuentran lo mismo), cabeceras ordenables con flecha, y contador
    "mostrando M de N" — sin él, filtrar y no ver nada parece que los trades se perdieron. Los
    vacíos van SIEMPRE al final, se ordene como se ordene.
    (c) 🔴 **La columna de P&L quedaba cortada**: 11 columnas × 12 px de relleno dejaban la tabla en
    820 px dentro de un hueco de 794. Con 8 px cabe entera (medido: sobra 0) y se sigue leyendo.
  · ⚠️ El servidor sirve como mucho **500 chequeos** (`limit(500)` en `preflight_list_checks`), de
    todas las pizarras juntas. Con 92 no se nota; a un usuario que registre a diario le llegaría en
    ~2 años y las más viejas dejarían de verse **sin avisar**. Anotado, no arreglado.
  · La demo queda en el repo para re-probar el panel tras cualquier cambio.
- [x] ✅ **16. Intranet del colaborador (2026-08-13).** `/partner` ya existía; se completó contra el
  acuerdo (`docs/acuerdo_colaboracion.md`, leído entero) en vez de rehacerse. **SIN rol nuevo, a
  propósito** (el dueño propuso "Commercial Ally"): colaborador = dueño de un código
  (`PromoCode.owner_user_id`), que es EXACTAMENTE lo que decide el dinero — un flag aparte serían
  dos verdades desincronizables. Lo cableado:
  · 🔴 **El admin recibía 404 en `/partner`** — el dueño no podía ver lo que iba a entregar (por eso
    "no encontraba el apartado"). Ahora el admin ve TODOS los paneles tal como los ve cada
    colaborador (punto 4.2: el panel es la fuente única), con banda de "vista de administrador" y
    billeteras en SOLO lectura.
  · **Entrada de menú** "Panel de colaborador" (`#menu-partner`, `is_partner` en SCALPEL_USER):
    solo existe para dueños de código y admin; el usuario común ni la ve (y `/partner` le da 404).
  · **Billetera USDT** (punto 4.4): la escribe EL COLABORADOR en su panel (decisión del dueño) —
    `User.partner_wallet/partner_wallet_net`, POST `/partner/wallet` con validación mínima (≥15
    chars, sin espacios) y **fila de auditoría `partner_wallet_set` = el "por escrito" del
    acuerdo**. El admin la ve pero NO la edita: una dirección tecleada por un tercero es justo el
    error que el 4.4 carga sobre el Colaborador.
  · **Fechas del acuerdo** (5.1–5.3): `User.partner_since` se sella solo al conectar el código en
    /admin (campo `since` opcional para fijarla; jamás pisa una ya puesta) → el panel calcula
    inicio, revisión de 30 días y fin del período de 3 meses con la nota de renovación automática.
  · **Día 15 con fecha concreta** (`_proxima_liquidacion()`) + "siempre en USDT" en banda dorada, y
    la nota de **qué NO genera comisión** (2.5: PDF de Synapse y cosméticos, solo suscripciones).
  · Migración `_migrate_partner_columns()` (boot 8/8), 18 claves `partner.*` + `account.partner` ×4.
  ⚠️ El ES del panel decía "socio" — palabra PROHIBIDA por el acuerdo (contradice "no existe
  sociedad") → "colaborador". `tools/test_panel_socio.py` **34/34** + navegador real (ES, los tres
  perfiles, billetera guardada desde la página, 0 errores JS).
  · ✅ **La escalera 30/35/40 y el chargeback: VERIFICADOS corriendo 79 ventas por
    `record_sale_breakdown` — `tools/test_escalera_socio.py` 19/19** (reconstruye `test_reglaB` y
    `test_rerank`, perdidos al reciclarse el contenedor). El % sube solo (24→30%, 25→35%, 74→35%,
    75→40%), una renovación NO sube tramo (cuenta clientes, no pagos), y un contracargo quita al
    cliente del recuento + cancela su comisión pendiente (o la vuelve **clawback** si ya se pagó) +
    hace subir de puesto a los de abajo (un 40% puede volver a 35%).
  · 🔴 **ESQUEMA MARGINAL CONFIRMADO POR EL DUEÑO (2026-08-13) — no reabrir.** Su papá propuso
    hacerlo **retroactivo** ("con 25 clientes cobra 35% por LOS 25") por ser más fácil de entender.
    Se midió con `tools/compara_esquemas.py` (constantes reales del sitio) y el dueño se quedó con
    el marginal. **El argumento que decidió no fue el coste** (+$853/año creciendo de 10 a 100
    clientes) **sino el incentivo invertido:** con el retroactivo el cliente 75 trae $40 y sube la
    comisión $134 → **te deja $101 PEOR que no tenerlo**, y no recuperas ese nivel hasta el cliente
    83 (8 clientes que valen cero). En el umbral de 25 pasa igual en pequeño (24→25: caes de $404 a
    $384, recuperas en el 27). O sea: habría puntos donde al dueño le conviene que el colaborador
    NO venda. Textual: *"dejémoslo así, y en caso de que para el colaborador sea complicado de
    entender se le replantea"*. Alternativa ofrecida y guardada por si hace falta simplificar:
    **33% plano** = mismo coste que el acuerdo actual ($6.851 vs $6.805 en ese año) en UNA frase,
    sin escalera ni zonas muertas. Explicación del marginal que sí entendió el papá: *"cada cliente
    tiene su propia tarifa y no cambia nunca, como la antigüedad"*.
- [x] ✅ **17. Foro — simulacro de tráfico real (2026-08-09) + COMUNIDADES PRIVADAS.**
  `tools/simula_foro.py` = **65 reglas atacadas por HTTP, 0 evadibles** (puertas por plan con el
  free EMPUJANDO la puerta, límites diarios, prefiltro, propiedad, silenciado, XSS: todo se pinta
  con textContent). **3 bugs reales cazados y arreglados:** (a) reaccionar/guardar contra ids
  inexistentes creaba filas huérfanas, y reaccionar a un post BORRADO seguía pagando XP al autor
  (farmeo invisible a moderación); (b) DM a un usuario FREE/baneado entraba a un buzón que el otro
  jamás podía abrir → ahora 403 `recipient_locked` con su texto ×4 (`forum.dmLocked`); (c) el feed
  general enseñaba los posts de comunidad a todo el mundo.
  **Comunidades PRIVADAS (decisión del dueño):** la tarjeta es la vista previa pública (nombre,
  emoji, descripción del creador, números); leer/abrir/comentar/reaccionar/guardar exige ser
  miembro. Entrar = **solicitud** (`ForumCommunityMember.status` 'pending'→'member'; rechazar
  BORRA la fila para poder re-pedir) que solo el creador acepta/rechaza (`GET/POST
  /forum/community/<id>/requests`), o **invitación directa** del creador (`/invite`). El feed
  general filtra a no-miembros (`_mis_comunidades_ids`); publicar exige status='member' (pending
  no es pertenencia). Migración `_migrate_forum_member_status_column()` (DEFAULT 'member' = el
  backfill: nadie que estaba dentro sale expulsado), boot test 7/7. 15 claves `forum.comm.*`/
  `forum.dmLocked` ×4. ⚠️ `ForumCommunityMember` NO tiene relación `user` — joins explícitos.
## 🗑️ CERRAR UNA COMUNIDAD DEL FORO (2026-08-14)
🔴 **No se podía, y era un agujero de verdad:** una comunidad creada era ETERNA — sin endpoint de
borrado (ni para el creador, ni para admin) y sin poder abandonarla (`creator_cannot_leave`). Su
nombre es **único en todo el sitio**, así que quedaba bloqueado para siempre, y consumía uno de los
**3 cupos** de la cuenta: tres pruebas dejaban a esa cuenta sin poder crear ninguna más. Lo cazó el
dueño preguntando cómo borrar las suyas.
- `POST /forum/community/<cid>/delete` — creador o admin. Fila de auditoría por cada cierre.
- **Decisión del dueño: las publicaciones se van CON ella.** No se reasignan al foro general aunque
  `community_id` sea nullable: las comunidades son **privadas**, y moverlas publicaría ante todo el
  mundo lo que alguien escribió contando con que solo lo verían los miembros.
- 🔑 Los posts se **VACÍAN** (`title=''`, `body=''`, `image_path=None`, `is_deleted`) y se
  desligan (`community_id=None`) — no se borran de la tabla: sus comentarios, reacciones y guardados
  son de OTRA gente y apuntan con clave ajena; un DELETE real revienta en PostgreSQL. **Es
  exactamente el bug del 2026-08-10**, que reaparece cada vez que algo con hijos se borra.
- Cliente: botón solo del creador, **en dos pasos** (arma → confirma) y **se desarma solo a los 5 s**
  para que no quede "cargado" esperando un clic despistado. 2 claves `forum.comm.del*` ×4.
- ⚠️ **Defecto que solo se vio en navegador:** `.cm-actions` no tenía `flex-wrap`, y con el 5º
  control la fila del creador desbordaba la tarjeta — el botón de cerrar quedaba **debajo** del de
  abrir (Playwright lo delató: "Abrir intercepts pointer events"). Leyendo el código no se ve.
- `tools/test_borrar_comunidad.py` **19/19** (con `PRAGMA foreign_keys=ON`) + `simula_foro` 65/65 +
  navegador real en ES. ⚠️ `/forum/post` lee `request.form`, NO JSON.

- [x] ✅ **21. Farmeo de XP + AUDITORÍA COMPLETA POR PLAN (2026-08-09).** `tools/simula_xp.py`
  = **36 defensas, 0 farmeables**. Farmeo: login repetido paga 1/día (⚠️ el XP de login se paga al
  ABRIR /app, no en el POST de login — y /app exige el cookie del splash), la misma pregunta de
  quiz en bucle paga 0 (dedup `q:<id>`), mentir el acierto no cuela, 40 correctas no pasan del
  tope de 20, borrar-y-republicar no burla el límite de 2 posts/día, la cuenta cómplice cambiando
  de emoji paga como UNA reacción, tope maestro premium 80/día. **Por plan:** montos exactos de
  login (18/12/5) y análisis (60/30/10); quiz/daily/pre-flight responden 403 a free y standard;
  testimonio = 30 XP UNA vez con ventana de 30 días server-side (4 POSTs = 1 fila); daily paga 15
  una vez por día UTC (repetir = 409) y el bono de racha 30 al llegar a 7; pre-flight = bono único
  20 + 5/check topado en 15/día; fuente inventada paga 0; los 16 bordes de `RANK_THRESHOLDS` dan
  el rango exacto; bajar de plan NO toca ni XP ni rango. Techos de un día perfecto: free 108
  (con análisis semanal y testimonio mensual) · standard ~97 · premium 160 irrepetible → el rango
  2 (200 XP) toma días: no hay atajo. ⚠️ Rutas reales: `/api/testimonial/submit`, y pre-flight
  exige `verdict` ∈ go/caution/no-go.
- [x] ✅ **18. Subidas al foro (2026-08-12).** El moderador de imágenes (`FORUM_IMAGE_MOD_PROMPT`)
  tenía tres agujeros; el peor no era el evidente: (1) las capturas del PROPIO SITIO se bloqueaban
  como "app que no es de trading" **y anotaban advertencia** que suma al automute — presumir tu camo
  3 veces = muteado; (2) drogas/desnudos/armas/violencia no estaban nombrados; (3) 🔴 **una imagen de
  VENTA DE SEÑALES pasaba limpia** ("BUY GOLD NOW, join my VIP" es "claramente de trading" según el
  prompt viejo — el texto ya lo bloqueaba, la imagen era el agujero, y es lo más peligroso legalmente
  para un sitio educativo). Ahora el moderador devuelve **categoría** → dos códigos: `offtopic` →
  `not_chart` (mensaje amable: qué SÍ se acepta) y sexual/drugs/weapons/violence/signal → `content`
  (seco, sin detalle que ayude a afinar el intento); la advertencia lleva la categoría, no 'image'
  genérico. **Anti-sobre-censura, 3 cláusulas explícitas:** los SL/TP dibujados en TU gráfico no son
  asesoría (todos los gráficos del foro los llevan), "en la duda permitir", y la duda jamás aplica a
  lo vetado. Respuesta sin categoría (formato viejo) bloquea como not_chart. `save_forum_image` ahora
  devuelve 4-tupla (…, moderation_dict). i18n: `forum.img.content` nueva ×4, `forum.img.blocked`
  reescrita ×4 (menciona el sitio). `tools/test_foro_imagenes.py` **32/32** + simula_foro 65/65.
  ⚠️ Lo que NO se puede probar sin gastar llamadas: el juicio de la IA en sí — el test cubre todo lo
  que lo rodea y vigila que el prompt conserve sus cláusulas. Fail-open se queda (IA caída → pasa).
- [x] ✅ **19. Calidad del analizador fuera de ICT/STDV — CERRADO (2026-08-14, el dueño lo dio por
  bueno: *"ya puedes tachar el punto del analizador"*).** Banco de 30 casos repetible, 5
  metodologías medidas con nota, cláusula desplegada en producción e informe en PDF. Lo que queda
  es un LÍMITE documentado (vista fina del modelo), no trabajo pendiente. Detalle abajo.
  El dueño no puede etiquetar Harmonic/Elliott/etc. (solo opera ICT/OTE) → la salida: **gráficos
  SINTÉTICOS construidos desde la definición aritmética del patrón** (un Gartley ES B=0.618·XA;
  la onda 4 NO solapa a la 1) — la verdad se sabe por construcción, sin experto. **Hecho:**
  `tools/banco_analizador.py` (20 casos = 5 metodologías × ganado + perdido-con-confluencias +
  2 trampas; render TradingView 1280×800 con entrada/salida/SL/TP/temporalidad/volumen/RSI; los
  asserts cazaron 7 fallos de la 1ª pasada) + `tools/corre_banco.py` (mismo prompt/modelo/params
  que `/analyze`, calcados; exige la clave de pago; ~$0.70 la pasada) + `tools/califica_banco.py`
  (rúbrica con señal clave / prohibidas → INFORME.md; probado con respuestas simuladas y borradas).
  Las TRAMPAS son lo central: etiquetas que mienten (ratios falsos, solape de onda 4, spring sin
  rango, RSI "en 28" que el panel marca 50.5, cruce de medias inexistente) → miden complacencia.
  **1ª PASADA CORRIDA Y LEÍDA (2026-08-13, $0.33, resultados en `docs/banco_resultados/`):**
  · **Trades normales: BIEN.** Ganados 4/5 limpios y en los 5 perdidos encontró la razón REAL
    (límite ciega, 5ª truncada, test con volumen alto —contradiciendo las notas del trader—,
    ruptura sin volumen, cruce en rango). Lo que el cliente usa a diario funciona.
  · 🔴 **Trampas: 8–9 de 10 FALLADAS. El patrón es COMPLACENCIA: cree las etiquetas y las notas,
    no MIDE.** Validó ratios falsos de Gartley leyendo las etiquetas ("el gráfico muestra
    claramente 0.618/0.786" cuando eran 0.50/0.618); validó un Butterfly cuyo D no supera X;
    afirmó "la onda 4 no entra en territorio de la 1, es visible" siendo falso; llamó "más larga"
    a una onda 3 que era la más corta; **alucinó lecturas de volumen en un gráfico SIN panel de
    volumen** (violando su propia regla); dio por "máximos iguales" un 2º pico 4.5 pts más alto;
    avaló un objetivo medido dibujado al DOBLE y encima aconsejó "más paciencia" hacia él;
    y confirmó un golden cross INEXISTENTE ("esto es visible en el gráfico"). T3 fue el único
    matiz (dudó del RSI=28 pero no leyó el 50.5 rotulado); W4 medio punto (objetó el contexto).
  · ⚠️ El calificador regex dio 2 rojos FALSOS (W2/W4 citaban al trader para corregirlo) —
    corregido W2; SIEMPRE leer los textos antes de sentenciar.
  **CIRUGÍA HECHA Y MEDIDA (2026-08-13/14, autorizada por el dueño con condición de no dañar
  ICT/OTE — resuelta por MEDICIÓN, el 100% de certeza no existe):** cláusula "toda etiqueta/nota es
  una AFIRMACIÓN a verificar contra el eje" + regla de honestidad numérica ("nunca digas que un
  valor es visible si no lo derivaste tú; repetir el número de las notas como si lo hubieras leído
  del panel es peor que callar"), **detrás de `ANALYZE_VERIFY_CLAIMS` (default APAGADA = prompt
  byte a byte idéntico, verificado por hash)**. Guardianes nuevos: 4 casos ICT/OTE (I1-I4) + 6
  perdidos con afirmaciones falsas (I5 SL cazado "manipulación", I6 BE prematuro, H5 dirección
  invertida, W5 contradicción tesis-corto, P5 TP tras la demanda, T5 divergencia oculta) = 30 casos.
  **Veredicto del antes/después (3 pasadas, ~$1 total, textos leídos a mano — el regex dio 6+
  rojos/verdes FALSOS, SIEMPRE leer):** la cláusula CAZA lo que antes tragaba en comparaciones
  gruesas — E4 onda 3 más corta, W3 "el panel de volumen no está visible" (antes alucinaba
  lecturas), P3 "los máximos no son exactamente iguales" citando el eje — y T3 se curó con la regla
  de honestidad (v2 había EMPEORADO: la orden de verificar le hacía AFIRMAR el RSI=28 falso).
  **CERO daño:** I1/I2 y los 7 ganados sin una sola sospecha inventada; los 12 perdidos igual de
  buenos. **Siguen ciegos (límite de VISTA, no de prompt — 2 iteraciones, no insistir):** ratios
  armónicos H3/H4, solape E3, cruce de medias T4. ⚠️ E3 dio verde FALSO en v3 (valida el solape
  citando la frase clave). Los 4 restantes son tareas de agudeza visual fina → siguientes peldaños:
  modelo más fuerte (medible con este banco) o pedir ratios en el formulario. Resultados en
  `docs/banco_resultados[,_v2,_v3]/`. ✅ **ENCENDIDA EN PRODUCCIÓN (verificado 2026-08-14):**
  `ANALYZE_VERIFY_CLAIMS=1` está en supervisor Y en `scalpel/.env`, y los 4 workers imprimen
  `[AI] clausula-verificacion=ENCENDIDA` al arrancar. Apagar = `set_env.py --quitar
  ANALYZE_VERIFY_CLAIMS` + `reread && update`.
  ⚠️ **Trampa de diagnóstico:** `grep ANALYZE_VERIFY_CLAIMS /var/log/trader.out.log` da 0 aunque
  esté encendida — el log imprime `clausula-verificacion`, no el nombre de la variable. Para saber
  el estado real hay que mirar la línea `[AI] clausula-…` del último arranque, no buscar la
  variable en el log (se dio un comando equivocado y confundió al dueño).
  📄 **`tools/informe_banco_pdf.py`** arma el PDF de 51 páginas con los 30 casos (gráfico +
  construcción del trade + respuesta del analizador + veredicto humano) y la **nota por
  metodología**: ICT/OTE 8 · Wyckoff 8 · Patterns 7 · Elliott 6 · TA 5.5 · Harmonic 5.
  ⚠️ Límite honesto anotado: sintético limpio = condición necesaria, no suficiente. NO se tocó
  nada del analizador (zona prohibida). `HOJA.md` = la spec para que Gabriel valide los 20 casos.
- [x] ✅ **20. "Mi cuenta" en el menú de arriba a la derecha (2026-08-04).** No existía ninguna
  forma de llegar a Ajustes desde ahí: vivía solo en el acordeón **Products** del lateral, que es
  el último sitio donde alguien busca su propia cuenta. Fila nueva `#menu-account` → `/settings`,
  puesta la PRIMERA del menú (encima de Planes, Rango y Cupones) porque es la de uso más frecuente.
  Clave `account.mine` ×4 idiomas. Verificado en navegador real: visible y traducida en EN/ES/FR/PT
  y el clic aterriza en `/settings`. ⚠️ Ajustes ya trae contraseña, 2FA, cerrar otras sesiones y el
  estado del plan — no hacía falta contenido nuevo, faltaba la puerta.
- [x] ✅ **22. Unlocks de rango ilegibles bajo camos (2026-08-03).** Una sola línea lo causaba:
  `body.light .ru-rwd{background:#f8f9fc}` — un blanco FIJO. Con un camo puesto el texto es claro
  (lo fija `--text` del camo) y caía sobre ese blanco: ilegible. En el tema claro por defecto
  `var(--bg)` vale `#F3F5FA`, prácticamente el mismo color, así que borrar la línea no cambia nada
  ahí y lo arregla en todos los camos de golpe. Medido el CONTRASTE real del título contra el fondo
  de la fila en **los 9 camos × 2 modos**: mínimo 8.70 (naval), máximo 17.23; el umbral AA es 4.5.
  Ninguno queda por debajo. El reveal de PLAN no tenía el problema: va sobre un velo oscuro fijo,
  sin overrides de `body.light`.
  🔴 **2ª PARTE (el usuario preguntó "¿puedes prometer que está al 100%?" y la respuesta era NO).**
  Aquella medición cubría 9 camos × 2 modos **pero no los 8 RANGOS**, y el rango cambia el color de
  acento del modal (`TH[rank]`). Re-auditado por **píxeles reales** (se recorta cada texto del
  screenshot y se compara con el color que de verdad quedó detrás — varios camos tienen paneles
  translúcidos y el cálculo teórico miente), con un usuario **NO admin** por el camino real:
  **1.380 lecturas**. Resultado: 1.240 bien (peor 6.83) y **87 fallando, todas el mismo elemento —
  el "RANK UP" pequeño de arriba** (`.ru-eyebrow`, `color:var(--ru-acc)`), en TODOS los rangos.
  Peor caso: dorado del rango 8 sobre el pergamino de blackflag = **1.39**.
  **Fix:** nada de tabla por camo (se rompería con el camo del mes siguiente) — `_legible()` acerca
  el acento al negro o al blanco hasta llegar a 5.0 contra el fondo REAL (`_fondo()` compone los
  `--surface` translúcidos hacia arriba hasta dar con algo opaco), y **devuelve el color intacto
  cuando ya contrasta**, así el look aprobado no cambia donde ya se leía. Var nueva `--ru-acc-tx`
  (NO se toca `--ru-acc`: lo usan el degradado del botón, los glows y los bordes).
  Verificado con `scratchpad/verifica_peores.py`: los 12 casos extremos pasan (1.39→5.81, 1.86→5.40,
  2.56→5.09; premium 11.44).
  ⚠️ **Dos lecciones de método:** (1) la 1ª versión del test cambiaba la clase del camo en el DOM
  **después** de que el modal ya había elegido su color → medía un color contra otro fondo y daba
  fallos falsos; hay que **recargar** con el camo guardado en la cuenta. (2) `pg.goto()` esperaba el
  `load` completo y la página pide un script a **cdnjs**, bloqueado en el contenedor → **~30s por
  carga** (70 min de reloj). Siempre `wait_until='domcontentloaded'` + `pg.route` abortando todo lo
  que no sea 127.0.0.1.
- [x] ✅ **23. Quitar "exclusive camo" de los unlocks de rango (2026-08-03).** Estaba en DOS sitios,
  y el segundo lo señaló él tras un primer arreglo incompleto: (a) la línea de progreso
  `rank.rewards` ×4 ("un nuevo badge, **un camo exclusivo** y un certificado PDF") y (b) 🔴 **el
  modal de subida de rango**, que entregaba TRES recompensas —medalla, **camo "reservado para este
  rango"** con etiqueta R1..R8, y certificado—; ese camo no existía en ninguna parte. Ahora entrega
  medalla + certificado (+ beta desde el rango 6). Borradas también las 4 claves `camo/camoD` de
  `RANK_I18N` para que nadie las reviva. ⚠️ NO se tocó `co.f.camo` de `checkout.html` ni
  `camo1`/`camos3` del reveal de plan: ese camo SÍ viene con el plan pago (`PLAN_CAMOS`).
- [x] ✅ **24. Brillos que se apagan (2026-08-03).** No era aleatorio ni cosa de camos concretos: el
  modo CLARO apagaba la marca a propósito (`body.light .tile-mark { opacity:.16; text-shadow:none }`,
  con el comentario "impact is intentionally softer here"). Por eso brillaba en oscuro y no en claro,
  en cualquier camo. El rayo del Quick Analysis y la inicial de cada proyecto son el MISMO elemento
  (`.tile-mark`), así que una sola regla arregla los dos. Ahora el claro también brilla: opacidad
  .26/.38/.44 (base/hover/activo) y halo **más cerrado** que en oscuro — sobre fondo claro un
  resplandor ancho y tenue no se ve, se ensucia; lo que lo hace legible es concentrarlo. Verificado
  en navegador: sin camo (oscuro y claro), Chronicles claro y Mission claro.
- [x] ✅ **25. Foro para Standard (2026-08-03).** Tenías razón y era el peor sitio posible: el
  **reveal "UNLOCKED" que se ve justo DESPUÉS de pagar** (`FEATURES.standard` en index.html) listaba
  solo analizador, proyectos y camo — el foro no aparecía, así que quien compraba Standard no se
  enteraba de que lo tenía. Agregado. Barridas las 8 superficies que anuncian el foro (tarjetas y
  tabla de la landing, tarjetas y tabla de pricing, checkout, T&C Secc. 5, el reveal y la guía):
  las otras 7 ya estaban bien. De paso, un comentario del código seguía diciendo "shown only for
  Premium members".


### 📌 COLA ACORDADA CON EL USUARIO (2026-07-31) — ir de a UNO, pulir y recién pasar al siguiente
El usuario listó 6 puntos y pidió expresamente no hacerlos de golpe: *"la idea es ir punto por punto
y pulir cada punto primero para luego pasar al otro"*. Estado:
1. ✅ **`/socials`** — hecha, renombrada (chocaba con Communities del foro) y **enlazada** (menú
   Products + footer de la landing). Falta solo que él cree las cuentas y setear las env vars.
2. ✅ **`(?)` de ayuda contextual** — cableados Analizador, Chalkboard, Foro y Quiz (+ Pre-Flight,
   que ya estaba). Español reescrito tras su observación de que sonaba a traducción literal.
3. ✅ **Previews de camos v2** — el card muestra la PIEL, el preview el interior, y los camos de dos
   looks llevan una **flechita ⇆ en el propio card** para alternar los dos grafitos.
4. ✅ **Testimonio del dueño / regla FTC (2026-08-01).** Respuesta: **no hay que quitarlo, hay que
   etiquetarlo.** 16 CFR 465.5 no prohíbe el testimonio de un directivo — prohíbe publicarlo **sin
   divulgar el vínculo** (multa hasta **$51.744 por infracción**). Cableado: columna
   `Testimonial.insider` (foto al enviar, hoy = cualquier admin; auto-migración **con backfill**,
   que acá SÍ corresponde) → viaja en `/api/testimonials` → la landing pinta una **etiqueta con
   borde** bajo el nombre (`.testi-insider`, sale del flag del servidor, `data-t` para que siga
   traducida) + **nota de cómo se recogen las reseñas** bajo el carrusel (cuentas reales, invitación
   in-app, XP por responder sea cual sea la nota). 4 claves ×4 idiomas.
   **Hallazgo aparte:** no existía NINGUNA forma de despublicar un testimonio sin tocar la base a
   mano → pestaña **"⭐ Reseñas"** en /admin con publicar/retirar auditado. Recomendación dada al
   usuario: **no publicar la suya** (5 estrellas firmadas por el dueño no convencen y restan
   credibilidad al resto) — él decide con el botón. `test_reviews.py` 18/18.
   ⚠️ Trampa del test: Flask-Login cachea el usuario en `g` (contexto de APP), así que con un
   `app_context()` abierto todo el script, la 2ª petición corre como el 1er usuario. Hay que hacer
   `g.pop('_login_user', None)` antes de cada petición.
5. ✅ **Sorteos en los T&C (2026-08-01).** Decisión: **sí, hacía falta** — la línea de 3 frases de
   `/socials` no es un reglamento, y un sorteo es figura regulada (compra+premio+azar = lotería en
   muchas jurisdicciones; las plataformas exigen declarar que no patrocinan). **Sección 19 nueva**:
   sin compra, 18+ o mayoría local, excluye al operador y su familia directa, nulo donde la ley lo
   prohíba, sorteo **manual** (lo del sitio es informativo), premios personales/no transferibles/sin
   canje, premio-plan no crea suscripción ni renueva, ganador alternativo, **sin afiliación a
   ninguna red social + liberación de la plataforma**, y modificación/cancelación sin compensación
   (porque participar no cuesta nada). Las reglas de cada sorteo prevalecen sobre la sección.
   ⚠️ **Mentoría se RENUMERÓ 19 → 20** (contra la nota vieja de "no renumerar"): los sorteos se ven
   siempre y mentoría está gateada por el flag, así que dejarla en 19 hacía saltar el índice de 18 a
   20 con el programa apagado. Se movieron `terms.toc19/t19/b19` → `…20` ×4 idiomas, **el número
   visible dentro de cada título traducido** (esto lo cazó el auditor, no yo) y la referencia
   cruzada desde la Secc. 7. Verificado 1..19 apagada / 1..20 encendida. `/socials` enlaza al
   reglamento (`comm.legalFull` ×4). Auditor: 144 cláusulas OK. `test_terms_gw.py` 20/20.
6. ✅ **`/guide` ampliada (2026-08-01).** De 1 frase + 3 pasos por sección a: intro que explica para
   qué sirve, 4-6 pasos con el porqué, y un **aviso `.tip`** con lo no obvio (la pizarra vive en el
   navegador y exportar es el guardado real; el daily rota por cuenta; un reloj de sesión no promete
   que pase algo). **2 errores de fondo cazados:** (a) el foro figuraba como "Premium" cuando es
   Standard+Premium desde julio, y la sección de planes tampoco lo listaba en Standard; (b) los
   pasos mandaban a pestañas con nombres traducidos **que no existen** — la pestaña es
   **"Chalkboard" en los 4 idiomas** y el foro es "Foro Trading" (verificar siempre contra las
   claves `tabs.*` de `index.html`). ⚠️ Los leads pasaron a `data-i18n-html`: llevan `<b>` y con
   `data-i18n` el applier usa `textContent` → las etiquetas salían literales.
   **El contenido vive en `tools/gen_guide/`** (`guide_en/es/frpt.py` + `build_guide.py`, se corre
   desde la raíz) y la plantilla se REGENERA desde ahí — editar 4 diccionarios a mano es como se
   desincronizan. 80 claves ×4 a paridad. Verificado en navegador real (claro, oscuro y ES).
   ⚠️ El bloque `fr` del dict usa **comillas dobles** (apóstrofes) → el patcher trabaja por líneas,
   no con regex sobre comillas.

**Además, sueltos de la misma sesión:** faltan por cablear los `(?)` de Synapse, Kill Zones,
Rangos/XP, Notas y Subida; y encender PayPal (ver "PENDIENTE INMEDIATO" más abajo).

### 🔐 SEGURIDAD DE CUENTAS — paquete completo (2026-08-01, luz verde del usuario)
**Contexto:** el papá sugirió pedir documentos de identidad en el registro. Se le explicó por qué NO
(KYC = custodiar datos sensibles + borra la línea "no somos bróker" + mata conversión + un menor
subiendo su cédula te deja con datos de un menor guardados) y eligió el paquete alternativo:
- **Fecha de nacimiento en el registro** (`User.birth_date`, server-side 18+, `_parse_birth_date`).
  El clickwrap 18+ + T&C se mantiene — evidencian cosas distintas. SIN backfill (cuentas viejas
  quedan sin fecha; inventarla sería peor). Errores nuevos `underage`/`weak_password` en register.
- **Contraseñas:** `_weak_password()` = lista común (~30, "password1" pasaba la regla vieja) + no
  contener usuario/correo. Aplica en registro, cambio y reset.
- **Cambio de contraseña REAL en Settings** (`POST /account/password`; la fila era un "Coming soon"
  sin ruta) + **"Cerrar las demás sesiones"** (`/account/sessions/close`). Mecanismo de revocación:
  **rotar `alt_id`** — todas las demás sesiones/remember-cookies dejan de resolver (la indirección
  ya existía; cero almacén de sesiones). El reset por correo también rota.
- **2FA TOTP opcional** (RFC 6238 con stdlib — hmac/struct, sin pyotp): alta `POST /account/2fa/start`
  → QR (segno de vuelta en requirements **SOLO para esto**; PNG a propósito — sin el viewBox de los
  SVG; **QR decodificado de verdad con OpenCV** antes de pushear) + clave manual; el secreto vive en
  la SESIÓN hasta confirmar un código (alta abandonada = cero efecto); 8 códigos de respaldo one-shot
  (hash sha256, mostrados UNA vez, `twofa_codes.html`); login = staging `pre2fa_*` 5 min / 5 intentos
  → `/login/2fa`; baja exige contraseña Y código. Plantillas `twofa_setup/twofa_codes/login_2fa`.
- **Aviso "dispositivo nuevo"** por correo: cookie aleatoria httponly `nx_dev` + tabla `KnownDevice`
  (NO usa el fingerprint: eso es anti-evasión de bans). ⚠️ El PRIMER dispositivo se registra en
  silencio — alertar sobre él habría mandado correo a todos los usuarios existentes en su siguiente
  login el día del deploy. `EMAIL_I18N['sec']` + `send_security_email()` best-effort ×4 idiomas.
- **Privacy 2.1** declara fecha de nacimiento, secreto TOTP y cookie de dispositivo (EN+ES/FR/PT,
  auditor 144 OK). i18n UI ×4 en `auth.js` (reg.dob, twofa.*) y `pages_i18n.js` (settings.*, sec2fa.*).
- Migración `_migrate_user_security_columns()` en `init_db()`. `test_secpack.py` **37/37**.
⚠️ **Trampa cazada:** pasarle el PROXY `current_user` a `login_user()` lo guarda como usuario de
sesión → `current_user` se resuelve a sí mismo → recursión infinita. Desenvolver con
`_get_current_object()` (hecho en `_kill_other_sessions`).

### 🔗 REFERIDOS — ATRIBUCIÓN PERPETUA + PANEL DEL SOCIO (2026-08-01, CABLEADO)
**Contexto:** auditoría ejecutando el flujo real dio 22/25 — la 1ª venta con código funcionaba
entera, pero descuento+atribución vivían EN EL PEDIDO: la renovación sin reescribir el código
volvía a $50 y el socio cobraba $0 (lo contrario de la propuesta comercial). Cableado:
- **`User.referred_by_code`/`referred_at`**: se fija UNA vez, en el primer pedido **PAGADO** con
  código `kind='creator'` público (carrito abandonado no ata; ruleta/personales no atan;
  re-atar es imposible — "primer código gana"). `_bind_referral()` en `_activate_plan_from_order`.
- **Checkout auto-aplica** el código guardado (`_stored_promo`): renovación a $40 sola, pedido con
  el código pegado → la comisión fluye por el camino normal. `uses_count` NO se infla con
  renovaciones. **Anti-robo:** cuenta atada → el código de OTRO creador responde `locked` (ni
  descuenta ni re-ata, jamás).
- **Cláusula 3.1 del acuerdo de socios — CABLEADA (2026-08-04):** una promoción **GENERAL**
  (`kind != 'creator'`) SÍ puede ganarle en PRECIO al código atado si deja el total estrictamente
  menor (peor o igual → error `worse`); la **atribución no se toca** — el pedido lleva el cupón
  general pero `record_sale_breakdown` cae a `referred_by_code` y el socio cobra igual, sobre lo
  pagado de verdad. Un solo decisor `_promo_para_compra()` (lo usan validate-code Y checkout_create).
  El carrito atado muestra el aviso de descuento permanente Y la casilla abierta
  (`checkout.promoLockedLabel`; ⚠️ el JS restaura el estado INICIAL pintado, no el precio base — en
  cuenta atada el $40 ya viene del server). Motivo: sin esto el cliente atado quedaba ATRAPADO en el
  peor precio y la 3.1 del acuerdo era mentira.
- **🔴 Candado 3.2 blindado contra el BORRADO del código (2026-08-04):** "atada" es la CUENTA
  (`referred_by_code`), no la fila del PromoCode — si el dueño borra el código del socio en /admin
  tras terminar la alianza, el cliente sigue siendo del socio; antes el guard colgaba de la fila y
  el código de OTRO creador entraba Y el libro le pagaba la comisión al rival. Además
  `record_sale_breakdown` ahora decide el socio POR EL VÍNCULO cuando la cuenta está atada (el
  código del pedido solo decide en cuentas sin vínculo: ventas manuales/clientes viejos); vínculo a
  fila borrada = venta sin atribuir (mejor que pagarle al rival). ⚠️ Por eso: **NUNCA borrar un
  código de creador con clientes atados — usar el toggle de desactivar**, que corta altas nuevas
  sin romper precio ni atribución. `tools/test_promo_31.py` 18/18. **Desactivar el código corta a NUEVOS, el
  cliente atado conserva precio y atribución** (decisión: la desactivación detiene altas, no rompe
  promesas). Cinturón extra: `record_sale_breakdown` cae al vínculo de la cuenta si el pedido llega
  sin código.
- **`/partner`** (`partner.html`, i18n ×4): el panel prometido al socio — suscriptores activos, %
  actual, reparto por tramos, comisión pendiente/pagada/mes, clawback, últimas ventas **SIN
  identidad del cliente**. Acceso = `PromoCode.owner_user_id` (campo **Owner** en /admin, ruta
  `/admin/promo/owner`); sin código propio → 404.
- Migración `_migrate_referral_columns()` (sin backfill, deliberado). `test_atrib.py` **23/23** +
  auditoría por el flujo real **26/26**. Panel verificado en navegador (ES).
⚠️ **El contenedor remoto se recicló esta sesión**: checkout quedó en otra rama (la del bot) y sin
deps de Python — la rama de trabajo vive en el remoto, recuperar con `git fetch origin
claude/gallant-volta-i7cqmf && git checkout …` + `pip install --ignore-installed blinker -r
scalpel/requirements.txt` (el blinker de debian rompe el install normal). Los tests del scratchpad
anteriores se PERDIERON (test_rerank/reglaB/ledger/reserva…) — los vigentes de esta tanda son
`test_atrib.py` y `audit_referidos.py`.

### 📒 LIBRO DE VENTAS — desglose por pago en /admin (2026-07-31, CABLEADO)
Pedido del usuario: que cada pago se desmenuce solo (bruto → desc. código → comisión socio →
fee → costo op → utilidad) y poder **cargar ventas a mano** para ver el comportamiento antes de
encender PayPal. **Misma matemática del Financial Hub.** Piezas: modelo `SaleBreakdown` (fila
única por venta, escrita al activarse y CONGELADA — posición/tramo/fee del momento; `order_id`
nullable = manuales), `record_sale_breakdown()` colgado de `_activate_plan_from_order`
(best-effort + idempotente), `PARTNER_TIERS` 30/35/40 **marginales por cliente** desde 1/25/75
(env-overridable), posición contada sobre ventas VIVAS (un chargeback la libera),
`_paypal_read_fee()` extrae la **fee real** de la captura (`seller_receivable_breakdown`) y sin
dato se estima 5.4%+$0.30 marcada "estim.". Reversa: fila tachada, comisión pendiente→cancelada
/ pagada→**clawback**. Panel: pestaña **"📒 Ventas"** (totales mes+histórico, selector de mes,
socios con "Día 15: marcar pagadas", tabla con la cadena completa, carga manual; manuales se
borran, reales solo se revierten). Rutas `/admin/ledger/*` auditadas. E2E 22 checks verdes.
**🔒 RESERVA ANTI-CHARGEBACK (2026-07-31):** `CHARGEBACK_RESERVE_PCT` (default 25, env-overridable)
aparta un % de **CADA venta** (mensual y anual). ⚠️ Se calcula **sobre lo PAGADO por el cliente, NO
sobre la utilidad** — un chargeback obliga a devolver el pago entero ($10 sobre $40, no $5 sobre
$20.54). Columnas `reserve_amt/reserve_pct/available_profit` congeladas por fila (auto-migración
`_migrate_sale_reserve_columns()`; filas viejas quedan en 0, backfillear inventaría una reserva que
nunca salió de la cuenta). El panel muestra **"TUYO Y DISPONIBLE"** como número grande y la reserva
en dorado; al revertir una venta su reserva sale del total con ella.
**Análisis que motivó esto (números medidos):** el 25% **sobra** para mensuales (un CB de $40 se
cubre con 5 clientes desde el 1er mes) pero **ningún % <100 cubre un CB anual** — cobras $408 y
devuelves $408. Con 3 mensuales + 1 anual, un CB anual deja en **−$126**; a partir de **10
mensuales** aguanta. Recomendación dada: no vender anuales hasta ~10 mensuales activos, y no
retirar como ganancia el dinero de un anual durante sus primeros 6 meses (ventana de disputa de
PayPal = 180 días). **El usuario decidirá luego si arriesga o si no publica planes anuales.**
**Al encender PayPal no hay nada más que cablear: el desglose ya corre en la activación.**

**🪜 REGLA B — la escalera 30/35/40 ordena CLIENTES, no pagos (2026-08-01, decisión del usuario).**
🔴 **Bug encontrado y corregido:** `_next_partner_position()` contaba **filas de venta**, así que cada
**renovación** empujaba al socio un puesto arriba — un socio con 10 clientes fieles llegaba al 40% en
el mes 8 sin haber cerrado un cliente nuevo (~$284/año de comisión de más en un caso chico). El
acuerdo dice "los primeros 24 **clientes** que cierre". Fix: `partner_active_customers(partner)`
cuenta `user_id` distintos vivos (las filas manuales sin `user_id` cuentan una cada una, no hay
contra qué deduplicar) y `_next_partner_position(partner, user_id=…)` **devuelve el puesto que ese
cliente ya tenía** si renueva. La escalera es un **ranking vivo, no una medalla**: si alguien se da de
baja, los de abajo suben un puesto (una reversión libera su posición). Carga manual: mismo
`username` + mismo socio = renovación (conserva puesto).
**Panel:** la tabla de socios muestra **Clientes** (lo que fija el tramo) con "N pago(s)" debajo,
**Reparto por tramos** ("24 al 30% · 50 al 35% · 1 al 40%"), **% efectivo** y **Próx. cliente**.
E2E `test_reglaB.py` 15/15 verde: renovación del cliente 1 sigue en puesto 1 al 30% y no crea cliente
nuevo (75 clientes / 76 pagos), reparto 24/50/1 = 33.5% efectivo, dos socios con pasteles separados
(Lucía arranca en su propio puesto 1), y una baja devuelve el puesto 75 al siguiente.
**Multi-influencer confirmado:** todo se calcula **por `partner`** — el socio B nunca ve ni cobra por
los clientes del A. Se puede negociar con varios en paralelo sin tocar código.

**🔁 RE-RANKING VIVO — el puesto se recalcula en CADA pago (2026-08-01, elegido por el usuario).**
🔴 **2º bug del mismo sistema:** al revertir una venta bajaba el CONTADOR de clientes pero no los
PUESTOS. Con 100 clientes y 3 bajas entre los primeros 24, el cliente nuevo tomaba el puesto 98 —que
un cliente vivo ya ocupaba— y ambos cobraban el tramo alto. Medido: panel 24/50/24 vs pago real
21/50/27, **$1.384 contra $1.372**, y la brecha crecía con cada baja.
**Fix:** `partner_roster(partner)` = clientes vivos ordenados por antigüedad (clave por `user_id`, o
por `username` en las filas manuales); `_next_partner_position()` devuelve el índice actual.
Propiedades: renovación conserva su lugar mientras no se vaya nadie más antiguo; **una baja hace
subir un puesto a los de abajo, así que alguien al 40% puede pasar a 35%** (decisión explícita del
usuario: el % refleja el tamaño de la cartera de HOY); puestos vigentes 1..N sin huecos ni repetidos.
**Las filas ya cobradas conservan su puesto y %** — un pago hecho no se reescribe; por eso el panel
separa columnas de **HOY** (clientes/reparto/% efectivo = próximo cobro) de las de dinero
(histórico). `test_rerank.py` 18/18. Alternativa descartada: congelar el % de por vida (con rotación
el reparto se despega del acuerdo y el panel deja de coincidir con lo que se liquida).

### 📊 FINANCIAL HUB — Excel entregado (2026-07-31, fuera del repo)
El usuario pidió por PDF un **modelo financiero de 14 hojas** para el acuerdo comercial →
entregado `Tradeable_Academy_Financial_Hub.xlsx` (14 hojas exactas del PDF, 832 fórmulas puras
sin macros, recalc 0 errores + 52 checks numéricos independientes verdes). Todo parametrizado
desde la hoja Configuración. **Decisiones aplicadas** (de la transcripción de la propuesta, el
usuario confirmó que ya estaban definidas): comisión RECURRENTE en cada re-pago; "ventas
válidas" = subs activos netos de chargebacks; tramos 30/35/40 **MARGINALES por cliente**
(1-24 → 30%, 25-74 → 35%, 75+ → 40%; corregido por el usuario — la 1ª versión aplicaba el %
del tramo a toda la facturación y INFLABA la comisión); comisión siempre sobre lo pagado;
descuento del código
perpetuo (20% mensual); anual = Modelo A 15% vs Modelo B 35% extra (ambos editables — el 20%
acordado antes se puede probar escribiéndolo); 15 cuentas Premium ×3 meses al llegar a 75
(única vez); Premium propio del influencer si ≥15 subs; comisiones anuales en 12 cuotas;
PayPal % + fijo configurables; costos fijos VPS/Workspace/IA incluidos. Un influencer hoy,
tabla lista para 10. ⚠️ Si piden regenerarlo: script en scratchpad de la sesión
(`hub/build_hub.py`) — NO está commiteado (deliberado: números del negocio fuera del repo).

### 🔴 Crítico (antes de lanzar)
- **⛔ OJO — LO DE STRIPE DE ESTA SECCIÓN ESTABA OBSOLETO (corregido 2026-08-01).** Decía "el cobro es
  por Stripe → payout al banco del amigo, NO se cobra USDT/Binance" y que Stripe LIVE era *lo único*
  que faltaba para cobrar. Eso es **anterior al pivote del 2026-07-26**, que lo dio vuelta: **sin
  banco en USA no hay Stripe**, y el cobro pasó a **PayPal + USDT** (ver el bloque "🔴 PIVOT
  2026-07-26" y "🟣 PayPal"). **El riel a encender es PayPal, no Stripe.** El código de Stripe queda
  en el repo, inerte sin `STRIPE_SECRET_KEY`, por si algún día aparece la sociedad y la cuenta
  bancaria. El fallback USDT de `checkout_done.html` **NO es texto viejo: es el flujo manual vigente**
  cuando no hay claves de pasarela.
- **Registrar COPYRIGHT** en copyright.gov (~$135–260). Guía: `COPYRIGHT_REGISTRATION_GUIDE.md`. Antes de publicar o ≤3 meses del lanzamiento.
- **Pagar OpenAI API + conectar (2 líneas) + probar con $5.** Estimado ~$0.02/análisis; `max_tokens` (validate=150, analyze=900) topa el costo. **Optimizaciones de costo YA hechas (2026-07-16):** (1) **prompt dinámico** — `build_system_prompt(approach)` en `app.py` arma el system prompt solo con los bloques de la metodología elegida (ICT+OTE viajan juntos; el resto = primer compacto `SP_CORE_LITE` + su bloque); global compliance/grounding/dirección + OUTPUT siempre van; approach desconocido = fallback completo. Ahorra ~5.3k tokens en ICT/OTE y ~10.5k en las otras 5 metodologías por llamada. (2) **resize de imagen** — `normalize_chart_image()` baja todo screenshot a `ANALYZE_IMG_MAX_PX=1280`px lado largo (JPEG q85) antes de la API → techo de costo fijo; no agranda las chicas (piso); guard `ANALYZE_IMG_HARD_PX=8000` rechaza dims absurdas (RAM). Aplicado en `/analyze` (detail=`high`) y `/validate` (detail=`low`); forum moderation con detail=`low`. `Pillow` en requirements (import perezoso, si falta manda original sin cap). Disclaimer i18n `upload.optNote` bajo el uploader. **Medir tokens reales de imagen con la API de pago conectada** para afinar el 1280px.
- **✅ OpenAI pago CONECTADO (2026-07-17):** switch por env var `OPENAI_API_KEY` (patrón condicional en `app.py` ~línea 190; sin la clave cae a GitHub Models). Log de arranque `[AI] backend=openai|github`. ⚠️ **En el VPS la key va en la línea `environment=` de supervisor, NO en `scalpel/.env`** (en prod no se lee el .env; `load_dotenv()` no lo encuentra bajo gunicorn). Aplicar cambios de esa línea con `supervisorctl reread && supervisorctl update` (o `reload`), NO solo `restart`. Medido: ICT analyze ≈ $0.029; el panel admin `/admin` (pestaña AI Spend) da el costo real por llamada.
- **✅ Analizador — extras (2026-07-17):** **límite Trade Construction** = 200 palabras + **tope duro de 2000 chars** (`NOTES_MAX_CHARS`). El char-cap es clave anti-abuso: un word-count solo se burla con un blob sin espacios ("1111…" ×1M = "1 palabra") que dispararía el costo → se clampa longitud cruda ANTES del word-cap. Cliente: `maxlength=2000` en el textarea + contador `#notes-counter`/`#notes-count` (rojo + recorta paste, clave i18n `notes.words`); server: recorte en `/analyze` (chars→words). Techo real de un análisis ≈ $0.03-0.04 pase lo que pase (prompt fijo + imagen 1280px + notas capadas). **✅ Fix contador de cuota (2026-07-17):** `/api/usage` ahora devuelve SIEMPRE `used/max/remaining` (antes solo si estabas bloqueado); el cliente llama `refreshQuota()` tras cada análisis → el "X / Y disponibles" (`#ag-quota`) se actualiza al instante en vez de quedar pegado al valor del page-load hasta recargar. El gate del server (`check_rate_limit` cuenta filas `UsageLog` committeadas en cada `/analyze`) SIEMPRE fue correcto — el bug era solo cosmético. **NOTA:** un switch de idioma del análisis arrojado (endpoint `/translate` + chips EN/ES/FR/PT) se construyó y luego se **RETIRÓ por decisión del usuario** (evitar cobros de más; el trader ya tiene su idioma preseteado antes de analizar) — no re-agregar salvo pedido explícito.
- **✅ Admin panel (2026-07-17):** reorganizado en **6 pestañas** (Users/Revenue/Moderation/AI Spend/Audit/Bugs, `.tabpane`/`.atab`, deep-link por hash preservado) + tabla **"Individual AI calls"** en AI Spend (costo/tokens por llamada, no solo total del día; `ai_calls_recent` en `_build_ai_analytics_context`) con filtro de texto.
- **Stripe:** código LISTO y probado en modo TEST, pero **NO es el riel del lanzamiento** — el pivote del 2026-07-26 lo descartó por falta de banco en USA. Queda inerte en el repo por si más adelante hay sociedad y cuenta. El riel a encender es **PayPal** (ver "📌 PENDIENTE INMEDIATO").
- **✅ Dominio COMPRADO Y EN LÍNEA (2026-07-30): `tradeable.academy`** — DNS en Cloudflare, HTTPS con
  Let's Encrypt, sirviendo la página de "en construcción". Ver el detalle en "🖥️ Infra / escalado".
  ⚠️ **`traderaccelerator.com` quedó DESCARTADO** — el dominio debía coincidir con el
  `support@tradeable.academy` ya publicado en T&C/Privacy en los 4 idiomas.
  **PENDIENTE del lanzamiento:** apuntar nginx a gunicorn (hoy sirve la página estática) y actualizar
  el webhook de Stripe/PayPal/cripto ahora que ya hay dominio con HTTPS.
- **Email dedicado** (migrar OTP/reset del Gmail personal a cuenta del dominio). Email en T&C/Privacy
  hoy: `support@tradeable.academy`. ⚠️ **Nombre oficial = "Tradeable Academy"** (empresa y dominio);
  "Tradeable" es solo la abreviatura. "Trader Accelerator" quedó ELIMINADO de T&C/Privacy en los 4
  idiomas (decisión del usuario 2026-07-26) — no reintroducirlo; el proceso `traderacelerator` de
  supervisor es aparte y se queda como está.
  **Plan de correo (definido 2026-07-28):** Google Workspace ~$7-8.40/**usuario**/mes, donde "usuario"
  = casilla del equipo, **NO** los usuarios registrados del sitio (Google no los cuenta). Hoy = **1
  usuario** + **alias gratis** (hasta 30: support@, hola@, billing@, legal@, noreply@) → una sola
  cuota cubre todas las direcciones. Alternativa gratis si falta caja: **Zoho Mail free** (5 casillas
  reales, dominio propio, solo webmail/app, sin IMAP). Cloudflare Email Routing es **gratis pero solo
  RECIBE** (reenvía a otra casilla; no se puede responder desde la dirección) — sirve de complemento,
  no de reemplazo. ⚠️ **NO usar Workspace como motor de los correos automáticos de la app** (OTP/reset):
  límite ~2.000 envíos/día y si se supera, Google bloquea 24h y **nadie puede registrarse** → usar un
  proveedor transaccional (Brevo/Resend, plan gratis) separado de la casilla humana. Configurar
  **SPF + DKIM + DMARC** sí o sí, o los correos caen en spam.
  🔴 **EL ALTA DE WORKSPACE SE TRABÓ (2026-08-03).** El usuario llegó hasta la verificación por
  teléfono y saltó *"actividad inusual"* sin recibir código (puso región **USA** con número
  **venezolano** — el antifraude lee la incoherencia). Al reintentar desde cero: *"el dominio ya
  está tomado"*, que **NO es un bug**: el primer intento ya creó una cuenta pendiente atada a
  `tradeable.academy`, así que choca consigo mismo. Salidas: entrar a la cuenta pendiente en
  admin.google.com, o el flujo de Google "el dominio ya está en uso" (se libera verificando la
  propiedad con un TXT). **Concepto clave que se le explicó: lo que evita el spam NO es el
  proveedor, es SPF+DKIM+DMARC + reputación** → no está atado a Workspace.
  **Plan alternativo propuesto:** (1) **Cloudflare Email Routing** hoy y gratis para RECIBIR en
  `support@` (el DNS ya está ahí; la dirección publicada en T&C pasa a existir de verdad);
  (2) **Resend/Brevo** para que la app ENVÍE con el dominio autenticado; (3) el buzón real
  (Workspace reintentado, o **Zoho Mail Lite ~$1/usuario/mes**, que sí trae SMTP — el Zoho *free*
  NO tiene IMAP/SMTP) sin apuro. ⚠️ Los MX de Email Routing **chocan** con los de Workspace/Zoho:
  al poner buzón real hay que desactivar el routing.
  ✅ **Código YA preparado (2026-08-03):** el remitente estaba repetido a mano en **10 sitios** →
  ahora `MAIL_ACCOUNT` (usuario SMTP), **`MAIL_FROM`** (remitente visible) y `ADMIN_INBOX` (buzón
  de avisos, cae en el remitente). 🔴 Separar usuario y remitente era **obligatorio** para los
  transaccionales: el usuario SMTP de Resend es literalmente la palabra `resend`, así que unidos
  el correo habría salido *"de: resend"* y rebotado. Línea de arranque `[Mail] …` y
  **`tools/check_mail.py`** (MX/SPF/DKIM/DMARC + conecta + autentica + `--enviar` manda uno de
  prueba; distingue "el registro no existe" de "no pude consultar DNS"). Existe porque **un SMTP
  mal configurado NO tumba la app**: deja un warning y sigue, o sea que el registro "funciona"
  mientras nadie recibe su código.
- **Redes sociales (2026-07-28):** crear un **Gmail NUEVO dedicado** a nombre de la empresa (nunca el
  personal) como identidad raíz de Instagram/TikTok/X/YouTube/Threads + 2FA + códigos de respaldo
  guardados. **Reservar los handles `@tradeableacademy` YA**, aunque los perfiles queden vacíos. El
  correo asociado se puede migrar después a `@tradeable.academy` sin perder cuentas ni seguidores.
- **Persistencia server-side de Scalper boards** (hoy en localStorage del navegador).

### 🟡 Importante (post-lanzamiento)
- APScheduler + OpenAI Web Search para Scout (auto-actualizar prop firms).
- Verificar prop firms que aceptan Venezuela (hoy solo OneUp Trader).
- Ratings del Scout con fuente verificable (Trustpilot, etc.).

### ✅ PAYPAL ESTÁ ENCENDIDO Y EN LIVE (confirmado 2026-08-10)
🔴 **NO volver a decirle "el día que enciendas PayPal" ni ofrecerle la receta de encendido.** Está
hecho: credenciales LIVE en el VPS, los dos planes de suscripción creados y el webhook apuntando a
`SITE_URL` por HTTPS. Verificado con `tools/check_subs.py` → **5 bien, 0 bloqueantes** (los dos
planes existen, ACTIVOS, mensuales sin fin, ids sin cruzar, y el webhook con `PAYMENT.SALE.COMPLETED`).
Se comprobó además una suscripción real con `tools/check_suscripcion.py` sin gastar dinero.
Lo que sigue vigente de la sección de abajo es solo **la referencia** de qué hace cada comando por si
hay que rehacer algo; el estado "pausado / falta encender" es HISTORIA, no una tarea.
⚠️ **Consecuencia práctica:** todo lo que se cablee contra PayPal corre ya contra dinero real. Nada de
"probar en sandbox" — no hay sandbox conectado. Antes de exponer una función nueva que llame a la API
(p. ej. el borrado de cuenta del 2026-08-10), hacer UNA prueba con cuenta desechable y comprobar el
resultado en el panel de PayPal.

### ▶️ Referencia histórica: cómo se encendió PayPal (hecho, no pendiente)
> Cuando el usuario diga **"sigamos con PayPal"**, es ESTO, sin volver a discutirlo. Ya está todo
> construido y probado; lo único que falta es que su papá le pase dos cadenas de texto.
- **Lo que le pide a su papá (4 clics, nada más):** developer.paypal.com → **Apps & Credentials** →
  interruptor arriba a la derecha en **Sandbox** → abrir la app (*Default Application*) → copiar
  **Client ID** y **Secret** (el Secret está tras un botón *Show*). **NO** tiene que crear productos,
  ni planes, ni webhooks — todo eso lo hacen los comandos. ⚠️ Puede que ya las tenga: el 2026-08-03
  el papá le pasó unas y resultaron ser justo las de sandbox.
- **Lo que corre él en el VPS**, en este orden:
  1. `cd /var/www/TRADINGBOT2.0 && git pull origin claude/gallant-volta-i7cqmf`
  2. `python3 tools/set_paypal.py` → pide las credenciales, las valida, dice a qué entorno
     pertenecen y **crea el producto + los 2 planes de suscripción** solo.
  3. `python3 tools/paypal_setup_webhook.py` → crea el webhook a `SITE_URL/webhook/paypal` con los
     **15 eventos** y deja `PAYPAL_WEBHOOK_ID` puesto. Idempotente; repara uno incompleto.
  4. `supervisorctl reread && supervisorctl update` (SIN `restart` detrás: `update` ya reinicia)
  5. Comprobar: `tail -20 /var/log/*trader*.log | grep -i paypal` → deben salir
     `subs=True planes=premium:set, standard:set` y `enabled=True env=sandbox … webhook_id=set`.
- **La compra de prueba: con una cuenta NUEVA, no la de admin** (el sitio bloquea comprar un plan
  igual o inferior al que ya tienes, y así se prueba el recorrido real). Comprador sandbox desde
  *Testing Tools → Sandbox accounts*. Lo que hay que ver: el plan se enciende Y **Ajustes dice "Se
  renueva sola el …" con el importe** — eso es la prueba de que quedó suscripción y no cobro suelto.
- ⚠️ **Nunca pegar el Secret en el chat.** Va del panel de PayPal directo al VPS.
- ⚠️ En sandbox no puede salir un cargo real, y además `record_sale_breakdown` **ignora los pedidos
  de PayPal cuando `PAYPAL_ENV != 'live'`** → los ensayos no ensucian el libro de ventas.

### 🚪 EL DOMINIO YA SIRVE LA APP, detrás de un PASE (2026-08-04)
`tradeable.academy` **ya no es la página de "en construcción" para el dueño**: nginx sirve la
aplicación real a quien traiga el pase, y la página de espera a todos los demás. Config viva:
`deploy/nginx/tradeable.academy.preview.conf` (los otros dos estados del dominio son
`…academy.conf` = solo en construcción, y `…academy.live.conf` = abierto al público).
- El pase entra por **galleta** (`/pase/<pase>`) o por **URL** (`?pase=<pase>`, que además deja la
  galleta puesta). El valor **NO está en el repo** — es una credencial; se regenera con
  `openssl rand -hex 16` y el `sed` que está documentado en la cabecera del propio archivo.
- 🔴 **Lo que costó 4 horas y no se puede olvidar:** con Cloudflare delante, **una puerta por galleta
  NO funciona si el origen deja cachear**. Su copia no distingue galletas: guardaba la página de
  espera en la primera visita de cualquiera y se la servía al dueño con pase puesto — y al revés,
  podía guardar una página ya autenticada y enseñársela a un desconocido. Se arregla en el ORIGEN
  (`Cache-Control: private, no-store` + `Vary: Cookie`), **no** vaciando la caché a mano, que se
  vuelve a llenar sola. ⚠️ Y `add_header` **no se hereda** en un `location` que tiene los suyos:
  hay que repetirlo dentro (le pasó al location de la puerta).
- ⚠️ **`nginx -t` dice "el archivo es válido", NO "el archivo está activo".** Antes de mandar al
  usuario a mirar Cloudflare o el navegador, comprobar qué config está cargada de verdad:
  `nginx -T | grep -c ta_pase`.
- **`SITE_URL` ya está puesta** (`https://tradeable.academy`), así que PayPal devuelve al dominio
  entres por donde entres. **`PUBLIC_HTTPS` sigue APAGADA a propósito**: con ella encendida se
  apaga el acceso por `http://IP:5001`, y el dueño conserva las dos puertas mientras prueba. Es
  tarea del día del lanzamiento.
- Verificar que los demás NO ven el sitio: ventana de incógnito NUEVA (cerrando las anteriores) o
  el teléfono con el WiFi apagado. `/`, `/login` y `/pricing` deben dar la página de espera.

### 📌 Detalle previo — encender PayPal (EN PAUSA por el usuario 2026-08-03)
📜 **Cómo fue (historia, ya resuelta).** El 2026-08-03 la cuenta del papá ya era **Business** pero las
credenciales que pasó eran de **SANDBOX**; se pausó para atender el correo del dominio y se retomó
después con las de **Live**. Hoy está encendido y verificado (ver el bloque ✅ de arriba).
⚠️ Lo único de esta sección que sigue siendo REGLA: **NO pegar el Secret en el chat** — va del panel
de PayPal directo a supervisor + `scalpel/.env`.
🔁 **Al retomarlo, ahora hay DOS cosas más que pedirle** (ver la sección de suscripciones arriba):
los **ids de los dos planes** (`tools/set_paypal.py` los crea solo, no hay que tocar el panel) y el
**Webhook ID**, que dejó de ser opcional: sin él las renovaciones se cobran y el plan no se extiende.
Piezas nuevas listas para cuando se retome: **`tools/check_paypal.py`** (pide un token y dice si el
par autentica y **a qué entorno pertenece**, sin imprimir valores; detecta el desajuste con
`PAYPAL_ENV`, que **cae en `live` por defecto** — sandbox contra el host de producción da un 401 sin
explicación); línea de arranque `[PayPal] enabled=… env=…`; y **`PAYPAL_RECEIPT_NAME`**, porque la
cuenta receptora **no se puede renombrar** a "Tradeable Academy" (se usa para otros cobros): si se
setea, el checkout avisa *"El cargo aparecerá a nombre de X"* (×4 idiomas) — la mejor defensa contra
el contracargo "no reconozco esto", y coherente con la Secc. 5 de los T&C ("Quién recibe el pago").
`PAYPAL_BRAND_NAME` se queda: es un campo por-orden de la página de aprobación, no un ajuste de la
cuenta. 🔴 **Y un agujero tapado antes de que lo pisara:** una compra en sandbox se habría anotado
como VENTA REAL en el libro (una fila con `order_id` no se puede borrar, solo revertir y queda
tachada; habría consumido puesto en la escalera del socio y apartado reserva de dinero inexistente)
→ `record_sale_breakdown` ahora salta los pedidos de PayPal cuando `PAYPAL_ENV != 'live'`: el plan
se activa igual (se ensaya el circuito), los libros no se tocan. `test_sandbox.py` 4/4.

Detalle original del procedimiento (sigue vigente):
El usuario NO entiende todavía qué son Client ID / Secret / Webhook ID → **explicárselo paso a paso
con capturas de dónde hace clic**, no solo nombrarlos. Orden: (1) **subir la cuenta personal del papá
a PayPal Business** (es un upgrade gratis, misma cuenta/saldo/correo — NO se crea una cuenta nueva;
hace falta sí o sí porque las credenciales LIVE de API solo se emiten a cuentas Business);
(2) poner **"Tradeable Academy"** como nombre comercial (opcional pero recomendado: es lo que ve el
comprador en el recibo); (3) developer.paypal.com → Apps & Credentials → crear app → copiar
**Client ID** y **Secret**; (4) Webhooks → agregar `https://<dominio>/webhook/paypal` con los 6
eventos → copiar el **Webhook ID**; (5) las 4 variables en supervisor conf + `scalpel/.env` → restart.
Probar primero con `PAYPAL_ENV=sandbox`. ⚠️ Sin dominio+HTTPS el webhook no llega — igual activa por
el return-url y el barrido de /admin, así que se puede dejar el Webhook ID para cuando haya dominio.

### 🚨 Alerta recurrente (mostrar hasta que el usuario confirme que lo hizo)
1. ✅ Dominio comprado y linkeado al VPS con HTTPS (2026-07-30). ✅ **CORREO EMPRESARIAL RESUELTO
   (2026-08-08), y NO fue por Workspace/Zoho/Mailcow** (Workspace y Zoho le rechazaban el alta;
   Mailcow exigía ticket a Contabo por el puerto 25 saliente, que está BLOQUEADO — medido). **El
   buzón vive en el servidor cPanel del papá** (`vps-8f2896f9.vps.ovh.us` = 15.204.88.98, OVH):
   casillas `info@` y `support@tradeable.academy` creadas allí, webmail en `:2096`. En Cloudflare
   (via **`tools/dns_cf.py`**, todo por terminal): MX→ese hostname, SPF `v=spf1 +a +mx
   +ip4:15.204.88.98 ~all`, DMARC `p=none` + rua, DKIM selector `default` (verificada íntegra:
   392 b64 → RSA 2048). **La app ENVÍA como `info@`** (SMTP SSL puerto 465 — se añadió soporte 465,
   antes solo STARTTLS/587) y **los avisos van a `support@`** (`ADMIN_EMAIL`). `check_mail.py
   --enviar` ✅ todo en orden. **Recibo de compra al COMPRADOR** (`send_receipt_email`, ×4 idiomas,
   plan/camo/carrito/PDF, 1 vez por pedido): `test_recibo_email.py` 13/13.
   ⚠️ El servidor del papá tiene una ZONA DNS PROPIA de tradeable.academy (ns guaramo.com) con
   `tradeable.academy→15.204.88.98`: NO usarla jamás como nameservers o la web se cae — solo se
   copian a Cloudflare los registros de correo. ⚠️ El candado de preview dejaba `/health` fuera y
   monitor.py (cron horario) mandaba un WhatsApp de error CADA HORA — `/health` ya está exento.
2. ✅ **PAYPAL YA ESTÁ ACTIVO EN LIVE (2026-08-10) — este aviso está CERRADO, no repetirlo.**
   El dueño lo confirmó y `check_subs.py` lo verificó contra la API real (5 bien, 0 bloqueantes).
   🔴 Esta alerta estuvo pidiendo "encender PayPal" **después** de que estuviera encendido, y por
   arrastrarla se le dijo "el día que enciendas PayPal" sobre algo que ya cobraba dinero real. Si una
   alerta recurrente se queda desactualizada, hace decir tonterías con confianza: al cerrar cualquier
   punto de esta lista, tacharlo el mismo día.
   ⚠️ **RECORDATORIO OBLIGATORIO AL TOCAR STRIPE (pedido explícito del usuario 2026-07-25 — repetir SIN
   EXCEPCIONES cada vez que se trabaje en Stripe):** al activar Stripe LIVE hay que **actualizar la Sección 5
   de los T&C** (`terms.html`, "Plans, Payments & Billing"): hoy dice *"Payments are currently processed
   manually (e.g., by bank transfer…)"* — con Stripe activo debe decir que los pagos se procesan por tarjeta
   vía nuestro procesador de pagos (Stripe), **manteniendo** el "no auto-renovación" (decisión firme del
   usuario: TODO el sitio sin renovación automática; el cliente re-paga manualmente cada período). Actualizar
   también las traducciones ES/FR/PT de esa sección en `legal_i18n.js`.

---

