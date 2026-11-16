# 03 · ARQUITECTURA Y CÓDIGO

## Con qué está fabricado (y en qué versión)

### Servidor (Python) — `scalpel/requirements.txt`
| Pieza | Versión | Para qué |
|---|---|---|
| Flask | 3.1.0 | El framework web. Toda la app. |
| Flask-SQLAlchemy | 3.1.1 | Acceso a la base de datos (ORM). |
| Flask-Login | 0.6.3 | Sesiones de usuario. |
| Flask-Mail | 0.10.0 | Envío de correos. |
| Werkzeug | 3.1.3 | Contraseñas (hash), ProxyFix. |
| openai (SDK) | 1.82.0 | Hablar con el modelo de IA. |
| python-dotenv | 1.1.0 | Leer `.env` en local. |
| gunicorn | 23.0.0 | Servidor de producción. |
| Pillow | ≥10.0.0 | Reducir la captura antes de mandarla a la IA; imágenes OG. |
| segno | ≥1.6 | Código QR **solo** para dar de alta el 2FA. |
| stripe | ≥11.0.0 | Opcional; inerte sin clave. |
| sentry-sdk[flask] | 2.20.0 | Opcional; inerte sin `SENTRY_DSN`. |
| WeasyPrint | ⚠️ no está en requirements | Genera el PDF de Synapse y el del acuerdo. Hay que instalarlo aparte donde se use. |

Base de datos: **PostgreSQL** en producción, **SQLite** (`scalpel/scalpel.db`)
en local. Versión de Python del VPS: ⚠️ sin verificar desde aquí (el código es
compatible con 3.10+; en desarrollo se usó 3.11).

### Navegador (sin frameworks)
HTML con plantillas **Jinja2** + **JavaScript puro** (no hay React, ni build,
ni npm para el sitio). Librerías externas **guardadas dentro del sitio** en
`scalpel/static/vendor/` para no depender de CDNs:

| Librería | Versión | Dónde se usa |
|---|---|---|
| three.js + GLTFLoader | r128 | Synapse (cerebro y modelos 3D) |
| fabric.js | 5.3.1 | Chalkboard (pizarra) |
| jsPDF | 2.5.1 | Exportar la pizarra a PDF |
| marked | 18.0.9 | Convertir el análisis (Markdown) a HTML |
| DOMPurify | 3.4.13 | Limpiar ese HTML (anti-XSS) |

Además: widget de calendario económico de TradingView (externo) y Google Fonts
(Inter, Space Grotesk, JetBrains Mono, Orbitron).

### Servicios externos
| Servicio | Uso |
|---|---|
| **OpenAI API** (GPT-4o y GPT-4o-mini) | Analizador, validación de captura, moderación del foro, asistente. |
| GitHub Models | Respaldo gratuito si no hay clave de OpenAI (mismo modelo, con límites). |
| **PayPal** (Orders v2 + Subscriptions v1) | Cobro principal. |
| NOWPayments | Cobro en USDT (condicional). |
| Stripe | Integrado, apagado. |
| Cloudflare | DNS + proxy + caché delante del VPS. |
| Let's Encrypt (certbot) | Certificado HTTPS en el VPS. |
| CallMeBot | Avisos por WhatsApp al dueño. |
| Google Gemini | **Solo en el laboratorio** del Analizador 2.0 (localizar velas). |
| Google Search Console | Indexación (dominio verificado por TXT). |

## Cómo está organizado el repositorio

```
TRADINGBOT2.0/
├── scalpel/                 ← TODO EL SITIO (88 MB, casi todo imágenes y 3D)
│   ├── app.py               ← el backend entero (~18.300 líneas)
│   ├── assistant_kb.py      ← lo que sabe el asistente Tessera (dossier)
│   ├── synapse_translations.py  ← títulos de Synapse en ES/FR/PT
│   ├── daily_bank.js        ← las 200 preguntas del Reto Diario (NO se sirve al navegador)
│   ├── daily_bank_content.json  ← lo mismo, ya procesado para el servidor
│   ├── quiz_answer_key.json ← las respuestas correctas (solo servidor)
│   ├── requirements.txt
│   ├── templates/           ← 48 plantillas HTML
│   │   ├── index.html       ← LA APP (~31.300 líneas: todas las pestañas)
│   │   ├── landing.html     ← portada pública
│   │   ├── admin.html       ← panel de administración
│   │   └── … (login, register, checkout*, settings, terms, privacy, camos, …)
│   └── static/
│       ├── vendor/          ← librerías de terceros
│       ├── models/          ← modelos 3D de Synapse (14 MB)
│       ├── camo_src/, camo_skin_*.jpg, camo_prev_*.jpg, logo2_*.png  ← arte de camos y botargas
│       ├── plates/, cursors/ ← placas de foro y cursores
│       ├── pages_i18n.js, legal_i18n.js, improve_i18n.js, auth.js  ← traducciones
│       ├── synapse_library.js, synapse_content_{es,fr,pt}.json, synapse_export.json
│       └── auth.css, pay.css, improve.css
├── tools/                   ← 188 archivos: pruebas, utilidades del VPS, generadores de arte,
│                              y TODO el laboratorio del Analizador 2.0
├── docs/                    ← acuerdo de colaboración, resultados del banco, capturas de prueba
├── deploy/                  ← configs de nginx y página de "en construcción"
├── CONTEXTO_TRADEABLE/      ← este expediente
├── CLAUDE.md                ← notas ACTIVAS (se cargan en cada sesión de Claude)
├── CLAUDE_ARCHIVE.md        ← notas históricas (367 KB)
├── LANZAMIENTO.md           ← checklist de apertura
├── backup_db.py, monitor.py, daily_audit_summary.py, migrate_to_postgres.py  ← scripts del VPS
└── (todo lo demás)          ← el BOT VIEJO: app/, components/, lib/, strategy/, backtest.py… ver doc 19
```

## El mapa de `scalpel/app.py` (por zonas)

Es un archivo único. Se navega por estos tramos (líneas aproximadas):

| Líneas | Qué hay |
|---|---|
| 1–240 | Arranque: Sentry, `SECRET_KEY`, base de datos (PostgreSQL en UTC), `PUBLIC_HTTPS` (ProxyFix + cookies seguras), correo, cabeceras de seguridad (`_security_headers`, línea ~195), compresión gzip. |
| 244–270 | **Interruptores de funciones** (`SCOUT_ENABLED`, `PREFLIGHT_ENABLED`, `INDICATORS_ENABLED`, `MENTORSHIP_ENABLED`) y `TERMS_VERSION`. |
| 271–434 | Avisos por WhatsApp (`avisar`, cortafuegos anti-inundación, detección de "pagué y no me llegó"). |
| 435–530 | **Cliente de IA** (OpenAI o GitHub Models), precios por token, `normalize_chart_image`. |
| 528–690 | Configuración de Stripe, cripto (NOWPayments) y PayPal; `SITE_URL` y `abs_url()`. |
| 705–830 | Candado de vista previa (`PREVIEW_USERS`), interruptor de mentorías. |
| 833–2200 | **Los 57 modelos** de la base de datos (ver doc 05), con precios y economía del colaborador en medio (1261–1420). |
| 2205–2430 | Sistema XP / rangos (`add_xp`, `rank_for_xp`). |
| 2431–2680 | Límites por plan, catálogo de camos, precios de cosméticos, ventanas festivas. |
| 2681–2900 | Permisos: `has_access`, `premium_required`, `standard_required`, `check_rate_limit`. |
| 2886–3680 | Registro de uso y de gasto de IA (`log_usage`, `record_ai_cost`), correo (`_correo_html`, recibos, verificación; plantillas ×4 idiomas). |
| **3680–4160** | **Los prompts de IA:** `SYSTEM_PROMPT` (analizador), `SP_CORE_LITE`, cláusula de verificación, `build_system_prompt`, validador, moderadores del foro. |
| 4239–4400 | Portada, splash, favicon, sitemap, precios. |
| 4379–5600 | Mentorías (funnel + área de miembros + panel del mentor). |
| 5596–5820 | `/socials`, libro de ventas (admin), reseñas, sorteos. |
| 5818–6150 | Tienda de cosméticos y camos. |
| 6154–6800 | Legales, guía, Ajustes: contraseña, sesiones, 2FA, cambio de correo, borrar cuenta, cancelar/cambiar plan. |
| 6800–7150 | `/proyecto`, `/creators`, `/contact`, reporte de bugs. |
| 7151–8090 | `/app`, login, 2FA, registro, verificación, recuperación de contraseña. |
| 7950–8300 | Panel `/admin` y su cálculo (analítica, gasto de IA), trazas, vistas previas. |
| **8300–10760** | **Motor de pagos:** conciliación y barrido (`payments_sweep` ~8912), PayPal pedidos (`_paypal_create_order` ~9208) y suscripciones (`_sub_cobro` ~9745), `grant_plan_camo`, **`record_sale_breakdown` (~10283)**, **`_activate_plan_from_order` (~10411)**, `puede_comprar`, cupones (`_promo_para_compra`). |
| **10758–11770** | **Checkout y webhooks:** `/checkout*`, `/webhook/paypal`, `/webhook/crypto`, `/webhook/stripe`, acciones de pedido del admin. |
| 11769–12260 | Panel del colaborador, cupones (admin), gastos, poner plan a mano, demo, baneos. |
| 12437–13140 | Synapse (traducciones, PDF de pago, descargas). |
| 13139–13260 | **Asistente Tessera** (`/api/assistant/ask`). |
| **13260–13465** | **`/api/usage`, `/validate`, `/analyze`** — el analizador de producción. |
| 13466–14440 | Foro (posts, comentarios, reacciones, comunidades, mensajes, moderación de imágenes). |
| 14830–15120 | Prop Firm Scout (apagado). |
| 15123–15220 | Biblioteca del Chalkboard. |
| 15222–15400 | Huella de navegador, progreso de Synapse y Quiz. |
| 15437–16300 | Reto Diario, ranking, temporadas, ruleta, cosméticos. |
| 16302–16460 | Testimonios, respuesta del quiz, progreso de rango. |
| 16550–16940 | Certificados de rango (HTML, PDF, verificación pública, imagen OG). |
| 16944–17360 | Proyectos del analizador y Pre-Flight. |
| 17360–18216 | Las funciones de migración (`_migrate_*`), publicación de cosméticos. |
| 18217–18328 | `init_db()` (orden de migraciones + cuenta admin inicial), `/health`, manejador de errores 500. |

## Cómo está armada la interfaz

- **`index.html` es la app entera.** Una sola página con un "shell" (nombre
  interno: **Aurora**): barra lateral con pestañas (Analizador, Proyectos,
  Pre-Flight, Foro, Quiz, Chalkboard, Synapse, Kill Zones, Products), panel
  central y rail derecho. Cambiar de pestaña no recarga: `switchTab()` muestra
  y oculta paneles.
- Contiene ~13 bloques `<script>` grandes. **Ojo:** las variables declaradas
  con `const`/`let` en un bloque no existen en `window`, así que otros bloques
  no las ven (por eso existe `window.T` para traducir desde el Chalkboard).
- **El usuario llega al navegador en `window.SCALPEL_USER`** (plan, rango, XP,
  si es colaborador, si tiene cupones…). Es solo para pintar: **el servidor
  vuelve a decidir permisos en cada petición.**
- **Temas:** claro (por defecto) y oscuro (`scalpel_theme` en localStorage).
  Encima van los **camos**: una clase `camo-<slug>` en `<body>` que cambia
  colores, fondo ilustrado, logo y mascota.
- **Páginas sueltas** (landing, login, checkout, ajustes, términos, creators,
  etc.) son plantillas independientes, cada una con su `<head>`. No hay una
  plantilla base común; lo compartido se incluye con parciales (`_iconos.html`,
  `_pay_marks.html`).
- **Tessera** vive en un único bloque `<script>` autocontenido al final de
  `index.html` (inyecta su propio CSS; borrar el bloque = quitar la función).

## Patrones que se repiten en todo el código (hay que respetarlos)

1. **Patrón condicional ("inerte sin clave").** Cada integración externa se
   enciende solo si su variable de entorno existe. Sin clave, el sitio cae al
   comportamiento anterior sin romperse. Aplica a OpenAI, PayPal, cripto,
   Stripe, Sentry, WhatsApp, vista previa, oferta de bienvenida.
2. **Línea de arranque.** Cada bloque de configuración imprime una línea al
   iniciar (`[AI] backend=…`, `[PayPal] enabled=…`, `[Oferta] bienvenida=…`,
   `[Preview] candado=…`, `[Mail] …`). Es la forma de saber, desde el log, qué
   quedó de verdad configurado. Nunca imprimen valores secretos.
3. **Precio siempre del servidor.** El navegador solo manda un identificador
   (plan, SKU, slug). El monto jamás viaja desde el cliente.
4. **Un solo activador idempotente.** Todos los caminos que entregan un plan
   pasan por `_activate_plan_from_order()`. Un aviso repetido no regala nada.
5. **Tres redes de seguridad en cada cobro:** webhook + reconciliación al abrir
   la página del pedido + barrido al abrir `/admin`.
6. **Migraciones en SQL crudo, nunca con el ORM** (ver doc 05).
7. **Nada se borra de verdad si otros lo referencian:** publicaciones y cuentas
   se **vacían** (se les quita el contenido) en vez de eliminarse.
8. **Fechas en UTC.** El VPS está en hora de Berlín; la sesión de PostgreSQL se
   fuerza a UTC. Los cortes diarios (cupos, racha, XP) son a las 00:00 UTC.
9. **Comentarios largos que explican el porqué.** El código está lleno de
   comentarios (en español e inglés) que cuentan qué falló antes. Leerlos.

## Correr el sitio en local

```bash
pip install -r scalpel/requirements.txt
FLASK_DEBUG=1 python3 scalpel/app.py      # → http://localhost:5001
```
Sin variables de entorno: usa SQLite, crea las tablas solo, la IA apunta a
GitHub Models (necesita `GITHUB_TOKEN` para analizar), los pagos caen al flujo
manual y el correo solo escribe en el log. ⚠️ Sin `FLASK_DEBUG`, Jinja guarda
las plantillas en caché y hay que reiniciar para ver cambios de HTML.
⚠️ Recargar `/app` rebota a `/welcome` si falta la cookie del splash.
