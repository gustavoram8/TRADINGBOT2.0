# Scalpel — ICT Trade Analysis Platform
## Notas del proyecto para Claude Code

---

> **INSTRUCCIÓN PERMANENTE:** Al inicio de CADA sesión nueva, muestra al usuario
> la sección "📋 TAREAS PENDIENTES" completa antes de cualquier otra cosa.
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
- **App:** `scalpel/app.py` · arrancar con `python3 scalpel/app.py`

---

## Límites de plan

| Plan     | Screenshots | Ventana |
|----------|-------------|---------|
| Free     | 1           | 7 días  |
| Standard | 1           | 24 h    |
| Premium  | 5           | 24 h    |

---

## 📋 TAREAS PENDIENTES

> Mostrar esta lista al usuario al inicio de cada sesión.

### 🔴 Crítico — antes del lanzamiento

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

---

## Notas de arquitectura importantes

- `init_scout_data()` corre en cada startup y refresca `blocked_countries`
  en todas las firmas — actúa como migración automática.
- `OFAC_DEFAULT_BLOCKLIST` en `app.py` define los 21 países bloqueados.
- `VENEZUELA_ALLOWED_SLUGS = {'oneup-trader'}` — única excepción documentada.
- El seed solo inserta firmas nuevas; no duplica si ya existen.
- Commits y pushes siempre a rama `claude/wonderful-gates-JAa9X`.
