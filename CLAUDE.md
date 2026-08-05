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
· **FALTA del paso 5:** los camos de los 11 meses siguientes (arte mensual que encarga el usuario).
  Cada uno = tema CSS + slug en `CAMO_SLUGS`/`CAMO_READY`/`CAMO_NAMES` + una línea en
  `CAMO_WHEEL_DESCS` ×4 idiomas; `_publish_roulette_camos()` lo publica solo al arrancar.

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

## 📌 PENDIENTES DE ÉL (recordárselos cuando toque, no cada mensaje)
1. **Revisar cómo quedó "Mi cuenta"** (punto 20, hecho el 2026-08-04): dijo *"aún no he revisado
   cómo quedó"*. Preguntarle si le convence la posición (va la primera del menú) antes de darlo
   por bueno del todo.
2. **Devolverle el escrito de PayPal cuando lo pida.** Está en la sección "▶️ RETOMAR PAYPAL" de
   este archivo: los 4 clics de su papá, sus 5 comandos, cómo comprobar que quedó bien y que la
   compra de prueba va con cuenta nueva. Se lo entrega tal cual cuando diga "sigamos con PayPal".

## 📅 Recordatorio diario
> 🔔 **PARA EL 2026-08-03 (pedido explícito del usuario):** re-revisar juntos los TONOS del
> 1º/2º/3º del salón de la fama (commit `eb50f46`: f1 = blanco incandescente + movimiento + halo,
> f2 = degradado quieto, f3 = brasa plana `#c9603a`) y repasar lo hecho el 2026-08-02 (panel
> temporada + fama + chips del foro). Mostrar este aviso al primer mensaje de ese día y luego
> borrar esta nota.

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
- [ ] **2. Propuesta comercial:** cambiar el acuerdo a **3 meses iniciales**, con revisión a los 30
  días y opción de renovación por otros 3 si se cumplen expectativas de cualquiera de las partes.
- [ ] **3. "My coupons":** ya no hay cupones de descuento. ¿Se quita, o se deja solo para mostrar el
  cupón de referido activo de cara a la próxima renovación?
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
- [ ] **5. T&C:** ¿hay que delimitar los dos productos nuevos (cursores y marcos)?
- [ ] **6. T&C:** revisar si dice algo de la **ruleta y cupones de descuento** — hoy los premios son
  SOLO cosméticos.
- [ ] **7. Validez jurídica de la propuesta comercial.** No tiene empresa constituida ni vive en la
  zona del influencer. ¿Qué valor legal tiene el documento? ¿Firmarlo le da marco legal?
- [ ] **8. Tessera:** el interior y los efectos le gustan, pero el **diseño se siente pobre** —
  sospecha de la tipografía, que no le pega a la marca.
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
- [ ] **13. Chalkboard funcional:** hoy es pobre, hay interacciones tediosas. Añadir herramientas
  propias de cada metodología (ej.: arrastrar una **secuencia de velas** ya dibujada).
- [ ] **14. Chalkboard visual:** el panel de la pizarra se ve **estrecho** frente al fondo del
  sitio, como una diapositiva encogida.
- [ ] **15. Pre-Flight:** revisar las "estadísticas" — hay comparaciones que no aportan.
- [ ] **16. Intranet del influencer:** que vea SUS clientes, sus comisiones y nada más. Propone un
  rol tipo admin, "Commercial Ally". ⚠️ Ojo: `/partner` ya existe (2026-08-01) — revisar qué falta
  en vez de rehacerlo.
- [ ] **17. Foro — simulacro de tráfico real:** cuentas falsas publicando, comentando, siguiéndose,
  mandándose DMs y **tratando de romper las reglas**. Reportar bugs encontrados, qué falta, y si
  alguna regla es evadible o algo prometido no se puede hacer.
- [ ] **18. Subidas al foro:** permitir capturas **del propio sitio** (landing, camos, etc.) y
  bloquear drogas, desnudos, armas y asesoría financiera — **sin censurar de más**.
- [ ] **19. 🔴 Calidad del analizador fuera de ICT/STDV.** No sabe operar armónicos ni otras
  metodologías y **no puede juzgar si el análisis es correcto**. Hay que encontrarle una forma de
  validarlo. (El punto más difícil de la lista.)
- [x] ✅ **20. "Mi cuenta" en el menú de arriba a la derecha (2026-08-04).** No existía ninguna
  forma de llegar a Ajustes desde ahí: vivía solo en el acordeón **Products** del lateral, que es
  el último sitio donde alguien busca su propia cuenta. Fila nueva `#menu-account` → `/settings`,
  puesta la PRIMERA del menú (encima de Planes, Rango y Cupones) porque es la de uso más frecuente.
  Clave `account.mine` ×4 idiomas. Verificado en navegador real: visible y traducida en EN/ES/FR/PT
  y el clic aterriza en `/settings`. ⚠️ Ajustes ya trae contraseña, 2FA, cerrar otras sesiones y el
  estado del plan — no hacía falta contenido nuevo, faltaba la puerta.
- [ ] **21. Simular tráfico farmeando XP** y desbloqueando rangos, para cazar bugs del cableado.
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

### ▶️ RETOMAR PAYPAL — la receta exacta (pausado 2026-08-04: el papá salió)
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
  4. `supervisorctl reread && supervisorctl update && supervisorctl restart traderacelerator`
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
🟡 **Estado al 2026-08-03:** la cuenta del papá **YA ES BUSINESS**, pero las credenciales que pasó
son de **SANDBOX** (dinero de mentira; se le explicó que en sandbox nunca llega un dólar y que las
de cobrar están en la pestaña **Live**, con Client ID y Secret distintos). **El usuario decidió
pausarlo** para atender primero el correo del dominio. ⚠️ **NO pegar el Secret en el chat** — va del
panel de PayPal directo a supervisor + `scalpel/.env`.
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
1. ✅ Dominio comprado y linkeado al VPS con HTTPS (2026-07-30). **Sigue faltando el CORREO
   EMPRESARIAL** (`support@tradeable.academy`): hoy los OTP/reset salen de un Gmail personal y el
   correo publicado en T&C/Privacy no existe todavía. Ver el "Plan de correo" arriba (Workspace 1
   usuario + alias, o Zoho free; transaccional aparte; SPF+DKIM+DMARC en Cloudflare).
2. **ENCENDER PAYPAL — es lo único que falta para poder COBRAR.** (Esta alerta decía "instalar Stripe LIVE"; quedó obsoleta con el pivote del 2026-07-26 y se corrigió el 2026-08-01.) El código está listo y probado con PayPal simulado (46 checks). Lo pendiente es configuración: (a) subir la cuenta del papá a **PayPal Business**; (b) crear la app REST y copiar **Client ID** y **Secret**; (c) webhook a `/webhook/paypal` con los 6 eventos y copiar el **Webhook ID**; (d) las 4 variables en supervisor conf + `scalpel/.env` → restart. Detalle paso a paso en "📌 PENDIENTE INMEDIATO". **Mostrar este recordatorio una vez al día hasta que el usuario confirme que PayPal está activo.**
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
