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
`CAMO_READY` en app.py — **hoy `{'rising-sun','pole','premium','fourth','naval','mission','blackflag','standard'}`**, el resto pendiente; endpoints
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

## Stack técnico
- Backend: Flask + SQLAlchemy + PostgreSQL (prod) / SQLite (local). Auth: Flask-Login (free/standard/premium).
- IA: OpenAI SDK → GitHub Models hoy (GPT-4o Vision análisis, GPT-4o moderación foro). **Migrar a OpenAI pago = setear env var `OPENAI_API_KEY` (NO se toca código)** — el cliente en `app.py` (~línea 180) es condicional: con la clave usa OpenAI pago (sin `base_url`), sin la clave cae a GitHub Models. Log de arranque `[AI] backend=openai|github model=…` en `trader.out.log`. Reversible: quitar la env var y reiniciar. Mismo modelo/prompt para ambos.
- Frontend: Jinja2 + vanilla JS, i18n EN/ES/FR/PT (`scalpel_lang`), tema claro/oscuro (`scalpel_theme`, default light).
- App: `scalpel/app.py`. Local: `FLASK_DEBUG=1 python3 scalpel/app.py`.

## Límites de plan
| Plan | Screenshots | Ventana | Proyectos analizador | Foro | Pre-Flight |
|---|---|---|---|---|---|
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

### 📌 COLA ACORDADA CON EL USUARIO (2026-07-31) — ir de a UNO, pulir y recién pasar al siguiente
El usuario listó 6 puntos y pidió expresamente no hacerlos de golpe: *"la idea es ir punto por punto
y pulir cada punto primero para luego pasar al otro"*. Estado:
1. ✅ **`/socials`** — hecha, renombrada (chocaba con Communities del foro) y **enlazada** (menú
   Products + footer de la landing). Falta solo que él cree las cuentas y setear las env vars.
2. ✅ **`(?)` de ayuda contextual** — cableados Analizador, Chalkboard, Foro y Quiz (+ Pre-Flight,
   que ya estaba). Español reescrito tras su observación de que sonaba a traducción literal.
3. ✅ **Previews de camos v2** — el card muestra la PIEL, el preview el interior, y los camos de dos
   looks llevan una **flechita ⇆ en el propio card** para alternar los dos grafitos.
4. ⏳ **¿Hay que quitar el testimonio del usuario de la landing?** — duda legal SUYA. Revisar contra
   la **regla FTC de reseñas (2024)**, que es concreta sobre testimonios de personas con vínculo con
   la empresa (dueño/fundador): el problema no suele ser publicarlo, sino publicarlo **sin revelar el
   vínculo**. Revisar también qué dicen los T&C propios sobre reseñas. NO borrar nada sin decidirlo
   con él.
5. ⏳ **Sorteos en los T&C** — hoy la línea legal vive solo en `/socials` (`comm.legal`). Falta
   evaluar si se agrega una sección/cláusula propia (sin compra, sorteo manual del dueño, no
   afiliado a ninguna red social, se puede cancelar, quién puede participar, 18+). Si se toca
   `terms.html` → traducir a ES/FR/PT en `legal_i18n.js` y correr
   `python3 tools/audit_legal_translations.py`.
6. ⏳ **Enriquecer `/guide`** — dijo que está *"muy pobre... como si fuera una síntesis de la
   síntesis"*. Ahora importa más que antes: **los 5 drawers de ayuda enlazan a `/guide#…`**, así que
   la guía es el destino del "ver la guía completa". Anclas reales: `analyze`, `chalk`, `forum`,
   `quiz`, `preflight`, `synapse`, `timing`, `plans`, `account`.

**Además, sueltos de la misma sesión:** faltan por cablear los `(?)` de Synapse, Kill Zones,
Rangos/XP, Notas y Subida; y encender PayPal (ver "PENDIENTE INMEDIATO" más abajo).

### 📊 FINANCIAL HUB — Excel entregado (2026-07-31, fuera del repo)
El usuario pidió por PDF un **modelo financiero de 14 hojas** para el acuerdo comercial →
entregado `Tradeable_Academy_Financial_Hub.xlsx` (14 hojas exactas del PDF, 832 fórmulas puras
sin macros, recalc 0 errores + 52 checks numéricos independientes verdes). Todo parametrizado
desde la hoja Configuración. **Decisiones aplicadas** (de la transcripción de la propuesta, el
usuario confirmó que ya estaban definidas): comisión RECURRENTE en cada re-pago; "ventas
válidas" = subs activos netos de chargebacks; el % del tramo (30/35/40 desde 1/25/75) aplica a
TODA la facturación comisionable; comisión siempre sobre lo pagado; descuento del código
perpetuo (20% mensual); anual = Modelo A 15% vs Modelo B 35% extra (ambos editables — el 20%
acordado antes se puede probar escribiéndolo); 15 cuentas Premium ×3 meses al llegar a 75
(única vez); Premium propio del influencer si ≥15 subs; comisiones anuales en 12 cuotas;
PayPal % + fijo configurables; costos fijos VPS/Workspace/IA incluidos. Un influencer hoy,
tabla lista para 10. ⚠️ Si piden regenerarlo: script en scratchpad de la sesión
(`hub/build_hub.py`) — NO está commiteado (deliberado: números del negocio fuera del repo).

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
- **Redes sociales (2026-07-28):** crear un **Gmail NUEVO dedicado** a nombre de la empresa (nunca el
  personal) como identidad raíz de Instagram/TikTok/X/YouTube/Threads + 2FA + códigos de respaldo
  guardados. **Reservar los handles `@tradeableacademy` YA**, aunque los perfiles queden vacíos. El
  correo asociado se puede migrar después a `@tradeable.academy` sin perder cuentas ni seguidores.
- **Persistencia server-side de Scalper boards** (hoy en localStorage del navegador).

### 🟡 Importante (post-lanzamiento)
- APScheduler + OpenAI Web Search para Scout (auto-actualizar prop firms).
- Verificar prop firms que aceptan Venezuela (hoy solo OneUp Trader).
- Ratings del Scout con fuente verificable (Trustpilot, etc.).

### 📌 PENDIENTE INMEDIATO — encender PayPal (pedido para el 2026-07-27)
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
1. ✅ Dominio comprado y linkeado al VPS con HTTPS (2026-07-30). **Sigue faltando el CORREO
   EMPRESARIAL** (`support@tradeable.academy`): hoy los OTP/reset salen de un Gmail personal y el
   correo publicado en T&C/Privacy no existe todavía. Ver el "Plan de correo" arriba (Workspace 1
   usuario + alias, o Zoho free; transaccional aparte; SPF+DKIM+DMARC en Cloudflare).
2. **INSTALAR STRIPE REAL (modo LIVE) — es lo ÚNICO que falta para poder COBRAR cuando alguien contrata un plan.** El código ya está listo y probado en modo TEST (ver "🟢 Stripe" abajo); **la LLC YA ESTÁ hecha.** Lo pendiente es puramente de configuración: (a) poner las claves `sk_live_…` + `whsec_…` en supervisor conf y `scalpel/.env`; (b) **conectar en el dashboard de Stripe la cuenta bancaria del amigo** para recibir los payouts; (c) configurar el webhook `/webhook/stripe` en el dashboard de Stripe (necesita el dominio+HTTPS del punto 1). **El cobro es en USD por tarjeta vía Stripe → payout a la cuenta bancaria del amigo. NO se cobra USDT ni Binance.** **Mostrar este recordatorio una vez al día hasta que el usuario confirme que Stripe LIVE está activo.**
   ⚠️ **RECORDATORIO OBLIGATORIO AL TOCAR STRIPE (pedido explícito del usuario 2026-07-25 — repetir SIN
   EXCEPCIONES cada vez que se trabaje en Stripe):** al activar Stripe LIVE hay que **actualizar la Sección 5
   de los T&C** (`terms.html`, "Plans, Payments & Billing"): hoy dice *"Payments are currently processed
   manually (e.g., by bank transfer…)"* — con Stripe activo debe decir que los pagos se procesan por tarjeta
   vía nuestro procesador de pagos (Stripe), **manteniendo** el "no auto-renovación" (decisión firme del
   usuario: TODO el sitio sin renovación automática; el cliente re-paga manualmente cada período). Actualizar
   también las traducciones ES/FR/PT de esa sección en `legal_i18n.js`.

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
- **Textos legales:** al tocar `terms.html`, `privacy.html` o `legal_i18n.js`, correr
  `python3 tools/audit_legal_translations.py` — compara cláusula por cláusula el inglés contra ES/FR/PT
  (números, plazos, montos y tamaño). Importa porque los T&C ahora dicen que si la ley del comprador
  exige que mande **su** idioma, manda su idioma: un error de traducción en una cláusula de dinero es
  exigible. Auditoría completa hecha 2026-07-26 (141 cláusulas ✅; lectura íntegra del ES de las
  Secciones 2, 7, 11, 12, 14 y 15 — fieles). Único hallazgo: la Secc. 12 EN protegía a
  "TRADER ACCELERATOR" mientras el resto del contrato y las 3 traducciones decían "Tradeable" →
  unificado, y la Secc. 1 ahora define los tres nombres comerciales.
- Commits/pushes siempre a la rama de trabajo de arriba. NO crear PR salvo que el usuario lo pida.
