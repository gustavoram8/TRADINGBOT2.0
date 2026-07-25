# Scalpel — Trader Accelerator · Notas ACTIVAS para Claude Code

> 📦 El historial completo (tareas terminadas, detalles técnicos de Synapse, quiz hardcore,
> sesiones pasadas, análisis de costos de IA, ideas en stand-by) está en **`CLAUDE_ARCHIVE.md`**,
> que **NO** se carga en cada mensaje. Mantener este archivo CORTO para ahorrar tokens; al
> terminar una tarea, mover su detalle al archivo en vez de dejarlo aquí.

---

## 🔧 Operativa (LEER SIEMPRE)
- **Rama de trabajo:** `claude/gallant-volta-i7cqmf`
- **Deploy en VPS** (Contabo `62.171.180.22:5001`, supervisor). Proceso: **`traderacelerator`** (¡una sola 'c', typo viejo!):
  ```
  cd /var/www/TRADINGBOT2.0 && git pull origin claude/gallant-volta-i7cqmf && supervisorctl restart traderacelerator
  ```
  Sin el restart, lo pusheado NO se refleja en producción. **Recordar el deploy tras cada push.**
- Producción usa **PostgreSQL** + gunicorn (venv). **Config gunicorn actual (2026-06-23):** `--max-requests 300 --max-requests-jitter 50 -w 4 --threads 4 -k gthread` (4 workers × 4 hilos = 16 concurrentes; reciclaje de workers anti-fuga). Editar en `/etc/supervisor/conf.d/*trader*.conf`. Env vars en supervisor conf y `scalpel/.env` (gitignored, mantener ambos en sync). ⚠️ `user`/`order` son reservadas en PG → quotear `"user"`/`"order"` en SQL crudo.

### 🖥️ Infra / escalado (medido 2026-06-23)
- **VPS Contabo: 7.8 GB RAM** (NO es chico). + **swap 2 GB** agregado (`/swapfile`, en `/etc/fstab`).
- **Bug OOM resuelto:** el ERROR 500 en `/register` reportado era un worker muerto por OOM (fuga de memoria lenta sin reciclar workers), NO un bug de código (el registro funciona: probado, da 302). **Fix aplicado:** swap + `--max-requests` (reciclaje) + threads. Causa real NO era falta de RAM (sobra), era fuga sin reciclar.
- **Prueba de carga (PARCIAL, leer con cuidado):** `ab -n 3000 -c 200 /login` → **432 req/s, 0 fallidas** (válido). Locust lanzó **500 conexiones concurrentes** y el servidor **NO se cayó, NO hizo OOM, siguió RUNNING** (RAM 1.6/7.8 GB) → probado que **no se rompe bajo 500 conexiones**. PERO: la siembra de los 500 usuarios `loadtest` **falló** (DB quedó en `encontrados: 0`), así que los logins fallaban y las peticiones eran **más ligeras que un usuario autenticado real**; además locust murió con el SSH → **NO tenemos tabla de latencias ni prueba de la experiencia logueada real**. **Conclusión honesta: NO está probado del todo que aguante 500 usuarios reales usando todo el sitio; solo que no se cae/OOM bajo 500 conexiones.** PENDIENTE hacerlo bien: (1) sembrar usuarios y verificar que imprima `sembrados 500`; (2) correr locust desde una máquina estable o en el VPS con `tmux`/`nohup` para que sobreviva; (3) capturar la tabla `Aggregated` (median/p95/req-s/% fails). NO load-testear `/analyze` (IA: cuesta dinero + ya gateada por límites de plan).
- **🔴 TAREA INFRA CLAVE — nginx + dominio + SSL** delante de gunicorn: hoy se sirve en IP cruda `:5001` sin nginx ni HTTPS. nginx = sirve estáticos sin ocupar workers, amortigua clientes lentos (el mayor multiplicador de capacidad real), maneja miles de conexiones, da SSL Let's Encrypt. **Es EL salto necesario para 500 usuarios reales.** (DNS A → 62.171.180.22 + nginx reverse proxy a 127.0.0.1:5001 + certbot.)
- **Confidencialidad IA:** en el front público NUNCA decir "GPT-4o"/"OpenAI" → "our proprietary AI engine".
- **Calidad:** validar antes de pushear (Jinja parse, `node --check` del JS tocado, i18n con claves parejas en EN/ES/FR/PT).

## 📅 Recordatorio diario
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

**🟢 CAMOS — sistema de skins comprables (EN CURSO, actualizado 2026-07-19).** Un camo = un *theme* que
reskinea SOLO el fondo/colores del sitio (layout/paneles/posiciones NO cambian) + swap de la mascota en
el Quiz (welcome + pass/fail). **Infra base (cableada, estable):** `User.active_camo`/`owned_camos` +
helpers `camos_owned()/add_camo()/owns_camo()` (admin posee TODO); `CAMO_SLUGS` (20 slugs) y
`CAMO_READY` en app.py — **hoy `{'rising-sun','pole','premium','fourth','naval','mission','blackflag'}`**, el resto pendiente; endpoints
`/api/camo/activate` `/api/camo/deactivate`; `/app` pinta `body.camo-<slug>` pre-paint (sin FOUC);
tienda `/camos` con ownership/compra (Stripe real AÚN pendiente, hoy toast "pago pronto"). Migración
prod ya aplicada (columnas `active_camo`/`owned_camos` en `user` + auto-heal `_migrate_user_camo_columns()`
en `init_db()` — futuras columnas nuevas: SIEMPRE auto-migración, nunca pedirle al usuario SQL a mano).
**Mascotas (welcome/pass/fail, light+dark) — 7 de 7 camos LISTAS y con cutout limpio:** rising-sun, naval,
mission, pole, blackflag, premium (Obsidian Gold), fourth (USA, solo welcome — faltan pass/fail, el
usuario las subirá después). Proceso de cutout: `scalpel/tools_camo_cut.py` (semi-automático: detecta
huecos blancos ENCERRADOS por el contorno —axilas, entre piernas, barandillas— los numera sobre el arte,
un humano decide cuáles son fondo vs. feature blanco real —guantes/ojos/dientes—, aplica con bordes
suavizados). Dark = recolor de flecha azul→naranja `#dd9100` (mismo tono que la mascota default dark,
sampleado con precisión de píxel); camos con arte que NO debe recolorearse (ej. bandera USA) usan
`recolor=False`. **Themes (fondo) — 7 de 20 LISTOS:**
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
- **Pendientes de theme:** 13 slugs más sin arte de mascota
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
debajo de la pestaña Products (que es la ÚLTIMA tab). Con logo(96px)+tabs+~10 items el sidebar supera
`max-height:calc(100vh-44px)` y muestra su **propio scrollbar** en pantallas bajas → los items de abajo
(Camos/Terms/Privacy/Guide/Contact/Settings) se ven scrolleando el sidebar. **Esto es lo aceptado por el
usuario.** ⚠️ **NO reintentar flotar el menú:** hubo 4 intentos rechazados — (1) `position:fixed` en su
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

## Stack técnico
- Backend: Flask + SQLAlchemy + PostgreSQL (prod) / SQLite (local). Auth: Flask-Login (free/standard/premium).
- IA: OpenAI SDK → GitHub Models hoy (GPT-4o Vision análisis, GPT-4o moderación foro). **Migrar a OpenAI pago = setear env var `OPENAI_API_KEY` (NO se toca código)** — el cliente en `app.py` (~línea 180) es condicional: con la clave usa OpenAI pago (sin `base_url`), sin la clave cae a GitHub Models. Log de arranque `[AI] backend=openai|github model=…` en `trader.out.log`. Reversible: quitar la env var y reiniciar. Mismo modelo/prompt para ambos.
- Frontend: Jinja2 + vanilla JS, i18n EN/ES/FR/PT (`scalpel_lang`), tema claro/oscuro (`scalpel_theme`, default light).
- App: `scalpel/app.py`. Local: `FLASK_DEBUG=1 python3 scalpel/app.py`.

## Límites de plan
| Plan | Screenshots | Ventana |
|---|---|---|
| Free | 1 | 7 días |
| Standard | 1 | 24 h |
| Premium | 5 | 24 h |

## Feature flags
- **Prop Firm Scout:** construido pero DESACTIVADO (`SCOUT_ENABLED=False` en `app.py`). Reactivar solo si el usuario lo pide.
- **Mentorship:** `MENTORSHIP_ENABLED` (env, default 0). Con flag off el funnel es admin-only (preview por URL).

---

## 📋 TAREAS PENDIENTES

### 🔴 Crítico (antes de lanzar)
- **🚨 EL COBRO ES POR STRIPE (USD por tarjeta → payout a la cuenta bancaria del amigo). NO se cobra
  USDT/Binance.** Falta solo instalar Stripe LIVE (ver "🚨 Alerta recurrente" #2). ⚠️ El texto viejo
  de `checkout_done.html` ("Send $X USD in USDT to our Binance account") es el **fallback manual** que
  solo se muestra si Stripe está apagado — quedará obsoleto al activar Stripe LIVE. Cuando Stripe LIVE
  esté activo, decidir si borrar ese fallback USDT del todo (`grep -rn "Binance\|USDT" scalpel/`).
- **Registrar COPYRIGHT** en copyright.gov (~$135–260). Guía: `COPYRIGHT_REGISTRATION_GUIDE.md`. Antes de publicar o ≤3 meses del lanzamiento.
- **Pagar OpenAI API + conectar (2 líneas) + probar con $5.** Estimado ~$0.02/análisis; `max_tokens` (validate=150, analyze=900) topa el costo. **Optimizaciones de costo YA hechas (2026-07-16):** (1) **prompt dinámico** — `build_system_prompt(approach)` en `app.py` arma el system prompt solo con los bloques de la metodología elegida (ICT+OTE viajan juntos; el resto = primer compacto `SP_CORE_LITE` + su bloque); global compliance/grounding/dirección + OUTPUT siempre van; approach desconocido = fallback completo. Ahorra ~5.3k tokens en ICT/OTE y ~10.5k en las otras 5 metodologías por llamada. (2) **resize de imagen** — `normalize_chart_image()` baja todo screenshot a `ANALYZE_IMG_MAX_PX=1280`px lado largo (JPEG q85) antes de la API → techo de costo fijo; no agranda las chicas (piso); guard `ANALYZE_IMG_HARD_PX=8000` rechaza dims absurdas (RAM). Aplicado en `/analyze` (detail=`high`) y `/validate` (detail=`low`); forum moderation con detail=`low`. `Pillow` en requirements (import perezoso, si falta manda original sin cap). Disclaimer i18n `upload.optNote` bajo el uploader. **Medir tokens reales de imagen con la API de pago conectada** para afinar el 1280px.
- **✅ OpenAI pago CONECTADO (2026-07-17):** switch por env var `OPENAI_API_KEY` (patrón condicional en `app.py` ~línea 190; sin la clave cae a GitHub Models). Log de arranque `[AI] backend=openai|github`. ⚠️ **En el VPS la key va en la línea `environment=` de supervisor, NO en `scalpel/.env`** (en prod no se lee el .env; `load_dotenv()` no lo encuentra bajo gunicorn). Aplicar cambios de esa línea con `supervisorctl reread && supervisorctl update` (o `reload`), NO solo `restart`. Medido: ICT analyze ≈ $0.029; el panel admin `/admin` (pestaña AI Spend) da el costo real por llamada.
- **✅ Analizador — extras (2026-07-17):** **límite Trade Construction** = 200 palabras + **tope duro de 2000 chars** (`NOTES_MAX_CHARS`). El char-cap es clave anti-abuso: un word-count solo se burla con un blob sin espacios ("1111…" ×1M = "1 palabra") que dispararía el costo → se clampa longitud cruda ANTES del word-cap. Cliente: `maxlength=2000` en el textarea + contador `#notes-counter`/`#notes-count` (rojo + recorta paste, clave i18n `notes.words`); server: recorte en `/analyze` (chars→words). Techo real de un análisis ≈ $0.03-0.04 pase lo que pase (prompt fijo + imagen 1280px + notas capadas). **✅ Fix contador de cuota (2026-07-17):** `/api/usage` ahora devuelve SIEMPRE `used/max/remaining` (antes solo si estabas bloqueado); el cliente llama `refreshQuota()` tras cada análisis → el "X / Y disponibles" (`#ag-quota`) se actualiza al instante en vez de quedar pegado al valor del page-load hasta recargar. El gate del server (`check_rate_limit` cuenta filas `UsageLog` committeadas en cada `/analyze`) SIEMPRE fue correcto — el bug era solo cosmético. **NOTA:** un switch de idioma del análisis arrojado (endpoint `/translate` + chips EN/ES/FR/PT) se construyó y luego se **RETIRÓ por decisión del usuario** (evitar cobros de más; el trader ya tiene su idioma preseteado antes de analizar) — no re-agregar salvo pedido explícito.
- **✅ Admin panel (2026-07-17):** reorganizado en **6 pestañas** (Users/Revenue/Moderation/AI Spend/Audit/Bugs, `.tabpane`/`.atab`, deep-link por hash preservado) + tabla **"Individual AI calls"** en AI Spend (costo/tokens por llamada, no solo total del día; `ai_calls_recent` en `_build_ai_analytics_context`) con filtro de texto.
- **Stripe:** código LISTO y probado en modo TEST (ver "🟢 Stripe" abajo). **LLC ya hecha.** Falta activar LIVE (claves live + conectar la cuenta bancaria del amigo en Stripe + webhook con dominio). Cobro en USD por tarjeta → payout al banco del amigo, NO USDT. Ver "🚨 Alerta recurrente" #2.
- **Comprar dominio** (Cloudflare ~$10/año, objetivo `traderaccelerator.com`) → DNS A → `62.171.180.22` + nginx + SSL Let's Encrypt.
- **Email dedicado** (migrar OTP/reset del Gmail personal a cuenta del dominio). Email en T&C/Privacy hoy: `support@traderaccelerator.com` (cambiar al real cuando se defina el dominio; auditar `git grep -in traderaccelerator`).
- **Persistencia server-side de Scalper boards** (hoy en localStorage del navegador).

### 🟡 Importante (post-lanzamiento)
- APScheduler + OpenAI Web Search para Scout (auto-actualizar prop firms).
- Verificar prop firms que aceptan Venezuela (hoy solo OneUp Trader).
- Ratings del Scout con fuente verificable (Trustpilot, etc.).

### 🚨 Alerta recurrente (mostrar hasta que el usuario confirme que lo hizo)
1. Comprar dominio + crear correo empresarial + linkear dominio al VPS (DNS A → 62.171.180.22, nginx+SSL). Sin esto: sitio en IP cruda, sin HTTPS, sin email empresarial.
2. **INSTALAR STRIPE REAL (modo LIVE) — es lo ÚNICO que falta para poder COBRAR cuando alguien contrata un plan.** El código ya está listo y probado en modo TEST (ver "🟢 Stripe" abajo); **la LLC YA ESTÁ hecha.** Lo pendiente es puramente de configuración: (a) poner las claves `sk_live_…` + `whsec_…` en supervisor conf y `scalpel/.env`; (b) **conectar en el dashboard de Stripe la cuenta bancaria del amigo** para recibir los payouts; (c) configurar el webhook `/webhook/stripe` en el dashboard de Stripe (necesita el dominio+HTTPS del punto 1). **El cobro es en USD por tarjeta vía Stripe → payout a la cuenta bancaria del amigo. NO se cobra USDT ni Binance.** **Mostrar este recordatorio una vez al día hasta que el usuario confirme que Stripe LIVE está activo.**

---

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
- Commits/pushes siempre a la rama de trabajo de arriba. NO crear PR salvo que el usuario lo pida.
