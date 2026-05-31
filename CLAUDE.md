# Scalpel — ICT Trade Analysis Platform
## Notas del proyecto para Claude Code

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

## Stack técnico

- **Backend:** Flask + SQLAlchemy + SQLite (`scalpel.db`)
- **Auth:** Flask-Login (planes: free / standard / premium)
- **AI:** OpenAI SDK apuntando a GitHub Models (Azure inference endpoint) con `GITHUB_TOKEN`
  - GPT-4o Vision → análisis de screenshots
  - GPT-4o → moderación del foro + asesor del Scout
- **Frontend:** Jinja2 + vanilla JS, i18n EN/ES/FR/PT
- **Rama de desarrollo:** `claude/wonderful-gates-JAa9X` en `gustavoram8/TRADINGBOT2.0`
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
- [ ] **Desplegar en VPS** — el sitio corre localmente; necesita servidor en
      producción (DigitalOcean, Railway, Render, etc.) con dominio propio.
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

- [ ] **Migrar email a SendGrid** — actualmente no hay sistema de email
      (confirmación de registro, recuperación de contraseña, notificaciones).
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

## Notas de arquitectura importantes

- `init_scout_data()` corre en cada startup y refresca `blocked_countries`
  en todas las firmas — actúa como migración automática.
- `OFAC_DEFAULT_BLOCKLIST` en `app.py` define los 21 países bloqueados.
- `VENEZUELA_ALLOWED_SLUGS = {'oneup-trader'}` — única excepción documentada.
- El seed solo inserta firmas nuevas; no duplica si ya existen.
- Commits y pushes siempre a rama `claude/wonderful-gates-JAa9X`.

---

## 🎨 Synapse — Estado técnico actual (2026-05-31)

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
