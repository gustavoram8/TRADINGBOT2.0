# 99 · INVENTARIO DE ARCHIVOS

> **Generado automáticamente** por `tools/empaqueta_contexto.py` el 2026-11-16.
> Rama `claude/gallant-volta-i7cqmf` · último commit: 3455402 · 2026-10-12 · --entrada-x: la flecha se senala en pixeles, no en numero de vela
> No editar a mano: volver a correr el programa.

**849 archivos** bajo control de versiones.

## Reparto por carpeta

| Carpeta | Archivos | Peso | De qué proyecto |
|---|---|---|---|
| `scalpel` | 426 | 86.4 MB | Tradeable (el sitio) |
| `tools` | 191 | 2.2 MB | Tradeable |
| `docs` | 99 | 1.7 MB | Tradeable (+ manual del bot) |
| `(raíz)` | 45 | 2.6 MB | Mezcla (ver doc 19) |
| `dashboard` | 16 | 187 KB | Bot viejo |
| `app` | 15 | 143 KB | Bot viejo |
| `deploy` | 8 | 207 KB | Tradeable (+ nginx del bot) |
| `indicators` | 8 | 94 KB | Bot viejo |
| `components` | 5 | 24 KB | Bot viejo |
| `reporting` | 5 | 49 KB | Bot viejo |
| `data` | 4 | 29 KB | Bot viejo |
| `lib` | 4 | 34 KB | Bot viejo |
| `risk` | 4 | 27 KB | Bot viejo |
| `validation` | 4 | 28 KB | Bot viejo |
| `api_server` | 3 | 23 KB | Bot viejo |
| `strategy` | 3 | 142 KB | Bot viejo |
| `config` | 2 | 11 KB | Bot viejo |
| `out` | 2 | 19 KB | Salidas guardadas |
| `.github` | 1 | 2 KB | Bot viejo (workflow peligroso) |
| `.streamlit` | 1 | 121 B | Bot viejo |
| `reports` | 1 | 8 KB | Bot viejo |
| `scripts` | 1 | 13 KB | Bot viejo |
| `store` | 1 | 1 KB | Bot viejo |

## `scalpel/` — el sitio

### Archivos de primer nivel

| Archivo | Peso |
|---|---|
| `scalpel/.env.example` | 982 B |
| `scalpel/app.py` | 910 KB |
| `scalpel/assistant_kb.py` | 16 KB |
| `scalpel/daily_bank.js` | 1.4 MB |
| `scalpel/daily_bank_content.json` | 1.3 MB |
| `scalpel/quiz_answer_key.json` | 11 KB |
| `scalpel/requirements.txt` | 906 B |
| `scalpel/synapse_translations.py` | 35 KB |
| `scalpel/tools_camo_cut.py` | 6 KB |

### Plantillas (`scalpel/templates/`)

| Plantilla | Líneas | Peso |
|---|---|---|
| `index.html` | 31302 | 3.6 MB |
| `landing.html` | 2707 | 161 KB |
| `admin.html` | 1577 | 93 KB |
| `guide.html` | 611 | 77 KB |
| `terms.html` | 1350 | 76 KB |
| `camos.html` | 1207 | 73 KB |
| `mentorship_area.html` | 1131 | 67 KB |
| `creators.html` | 647 | 35 KB |
| `settings.html` | 526 | 33 KB |
| `contact.html` | 480 | 26 KB |
| `privacy.html` | 473 | 24 KB |
| `improve_apply.html` | 413 | 22 KB |
| `checkout.html` | 388 | 21 KB |
| `checkout_status.html` | 335 | 19 KB |
| `certificate.html` | 287 | 17 KB |
| `improve_plans.html` | 232 | 15 KB |
| `device_preview.html` | 333 | 15 KB |
| `socials.html` | 226 | 14 KB |
| `verify_certificate.html` | 259 | 14 KB |
| `partner.html` | 215 | 14 KB |
| `admin_trace.html` | 279 | 14 KB |
| `splash.html` | 368 | 12 KB |
| `register.html` | 193 | 10 KB |
| `proyecto.html` | 198 | 9 KB |
| `checkout_success.html` | 142 | 8 KB |
| `_pay_marks.html` | 134 | 8 KB |
| `checkout_method.html` | 145 | 7 KB |
| `checkout_done.html` | 135 | 7 KB |
| `mentorship_checkout.html` | 108 | 6 KB |
| `checkout_switch.html` | 105 | 5 KB |
| `login.html` | 113 | 5 KB |
| `twofa_setup.html` | 74 | 4 KB |
| `synapse_pdf_ready.html` | 74 | 4 KB |
| `improve_inside.html` | 76 | 4 KB |
| `twofa_codes.html` | 54 | 3 KB |
| `improve_mindset.html` | 61 | 3 KB |
| `improve_gap.html` | 62 | 3 KB |
| `forgot_password.html` | 61 | 3 KB |
| `improve.html` | 64 | 3 KB |
| `checkout_soon.html` | 49 | 3 KB |
| `_iconos.html` | 38 | 3 KB |
| `store_indicators.html` | 45 | 3 KB |
| `verify_email.html` | 61 | 3 KB |
| `reset_password.html` | 52 | 2 KB |
| `mentorship_checkout_success.html` | 52 | 2 KB |
| `login_2fa.html` | 48 | 2 KB |
| `mentorship_checkout_done.html` | 48 | 2 KB |
| `pdf_expired.html` | 28 | 1 KB |

### Estáticos (`scalpel/static/`)

| Grupo | Archivos | Peso |
|---|---|---|
| `logo2*` | 26 | 18.8 MB |
| `logo4*` | 24 | 16.1 MB |
| `models/` | 5 | 13.6 MB |
| `logo3*` | 24 | 12.5 MB |
| `camo_src/` | 23 | 9.0 MB |
| `vendor/` | 7 | 1.5 MB |
| `tessera_emociones.png` | 1 | 1.1 MB |
| `logo5*` | 2 | 945 KB |
| `logo*` | 5 | 707 KB |
| `camo_skin*` | 19 | 547 KB |
| `camo_prev*` | 17 | 527 KB |
| `synapse_content*` | 3 | 487 KB |
| `synapse_bg.jpg` | 1 | 466 KB |
| `logo7*` | 2 | 446 KB |
| `emo*` | 11 | 298 KB |
| `legal_i18n.js` | 1 | 266 KB |
| `synapse_export.json` | 1 | 201 KB |
| `cursors/` | 111 | 184 KB |
| `pages_i18n.js` | 1 | 171 KB |
| `synapse_library.js` | 1 | 98 KB |
| `plates/` | 67 | 97 KB |
| `improve_i18n.js` | 1 | 73 KB |
| `og-image.png` | 1 | 50 KB |
| `icon*` | 3 | 34 KB |
| `improve.css` | 1 | 26 KB |
| `foro_ejemplo.png` | 1 | 26 KB |
| `auth.js` | 1 | 21 KB |
| `tesseract.png` | 1 | 18 KB |
| `pay.css` | 1 | 15 KB |
| `synapse_candles.png` | 1 | 13 KB |
| `auth.css` | 1 | 7 KB |
| `tira-botarga.png` | 1 | 7 KB |
| `apple-touch-icon.png` | 1 | 6 KB |
| `favicon.ico` | 1 | 4 KB |
| `.gitkeep` | 1 | 0 B |
| `uploads/` | 1 | 0 B |

## `tools/` — herramientas, pruebas y laboratorio

🔬 = laboratorio del Analizador 2.0 · 🧪 = prueba · ⚙️ = operación del VPS

| Archivo | Líneas | Qué es (primera línea de su cabecera) |
|---|---|---|
| `_legal_extract.py` | 58 | El inglés de cada cláusula, leído con un parser de verdad. |
| 🔬 `afina_velas.py` | 1015 | Del recuadro APROXIMADO de la IA al extenso EXACTO de la vela. |
| 🔬 `agudeza_visual.py` | 929 | PASO A — cuánto ve de fino cada modelo de visión sobre un gráfico de trading. |
| 🔬 `analizador2.py` | 1208 | ANALIZADOR 2.0 — la cadena entera, de una captura a HECHOS VERIFICADOS. |
| 🔬 `analizador_lab.py` | 751 | EL ANALIZADOR DEL SITIO, EN LABORATORIO — para comparar sin tocarlo. |
| `audit_legal_translations.py` | 103 | ¿Dice cada traducción lo mismo que el inglés? |
| `audita_legibilidad.py` | 312 | Punto 10: qué texto se pierde con un camo puesto. Medido, no mirado. |
| `audita_movil.py` | 301 | Barrido de las vistas MÓVIL y TABLET del sitio entero. |
| 🔬 `banco_analizador.py` | 1777 | Banco de gráficos SINTÉTICOS para medir el analizador (punto 19). |
| 🔬 `banco_cadena.py` | 1060 | La CADENA ENTERA, medida contra verdad por construcción. |
| `botarga_oscura.py` | 50 | La variante de MODO OSCURO de una botarga: flecha azul → naranja. |
| `botarga_rig.py` | 178 | Despieza la botarga común para poder ANIMARLA (animación de recortes). |
| `build_acuerdo_pdf.py` | 224 | Convierte docs/acuerdo_colaboracion.md en un PDF listo para firmar. |
| `build_alchemist_camo.py` | 346 | Genera el bloque CSS del camo THE ALCHEMIST y lo inserta en index.html. |
| `build_chronicles_camo.py` | 585 | Genera el bloque CSS del camo CHRONICLES y lo inserta en index.html. |
| `build_cursors.py` | 87 | Publica el catálogo de cursores como PNGs de 32x32 + manifiesto. |
| `build_gridiron_camo.py` | 282 | Genera el bloque CSS del camo AMERICAN FOOTBALL (`gridiron`) y lo inserta |
| `build_highnoon_camo.py` | 354 | Genera el bloque CSS del camo HIGH NOON y lo inserta en index.html. |
| `build_nile_camo.py` | 315 | Genera el bloque CSS del camo NILE y lo inserta en index.html. |
| `build_plates.py` | 48 | Publica el catálogo de marcos como archivos estáticos. |
| 🔬 `cajas_ia.py` | 408 | ¿Sabe un modelo LOCALIZAR las velas de un gráfico, con coordenadas? |
| 🔬 `califica_banco.py` | 132 | Coteja las respuestas del banco contra su rúbrica y arma el informe. |
| `capta_analizador.py` | 225 | Fotos de la pantalla REAL del analizador, para el reel 2. |
| `capta_quiz.py` | 329 | Fotos de la pantalla REAL del quiz, para el reel 3. |
| ⚙️ `check_borrados.py` | — | Vigilante: ¿alguna cuenta borrada conserva un cobro vivo en PayPal? (`--cortar`) |
| ⚙️ `check_cripto.py` | — | Estado de la pasarela cripto (NOWPayments). |
| ⚙️ `check_horas.py` | — | Comprueba que las fechas se guardan en UTC. |
| ⚙️ `check_mail.py` | — | Diagnóstico del correo: MX, SPF, DKIM, DMARC, conexión y envío de prueba. |
| ⚙️ `check_oferta.py` | — | ¿Sigue encendida la oferta de bienvenida y a qué porcentaje? |
| ⚙️ `check_paypal.py` | — | ¿Autentican las credenciales de PayPal y a qué entorno pertenecen? |
| `check_pg_sequences.sql` | 36 | ¿Queda algún contador de IDs que vaya a chocar en la próxima inserción? |
| ⚙️ `check_posts_hoy.py` | — | Cuenta las publicaciones del día (diagnóstico del cupo diario del foro). |
| ⚙️ `check_subs.py` | — | ¿Sirven de verdad las renovaciones? Planes activos y webhook correcto. |
| ⚙️ `check_suscripcion.py` | — | Revisa lo que PayPal tiene anotado para una suscripción concreta. |
| 🔬 `colores_velas.py` | 155 | DE QUÉ COLOR SON LAS VELAS DE ESTA CAPTURA. Se mide, no se opina. |
| `compara_esquemas.py` | 199 | MARGINAL (el del acuerdo) vs RETROACTIVO (la propuesta del papá). |
| `compara_legibilidad.py` | 118 | Antes y después del arreglo de legibilidad, lado a lado y a tamaño real. |
| `compara_visual.py` | 123 | Antes/después REAL del arreglo del scroll, medido píxel a píxel. |
| 🔬 `corre_banco.py` | 198 | Pasa el banco de gráficos por el MISMO modelo y prompt que producción. |
| `cursors_preview.py` | 646 | Catálogo de CURSORES + su banco de pruebas. |
| `demo_a_mi_cuenta.py` | 141 | Mete la demo de Pre-Flight en una cuenta REAL, para poder mirarla en pantalla. |
| `demo_preflight.py` | 305 | Pre-Flight usado COMO UN CLIENTE, para ver si las estadísticas sirven. |
| `demo_temporada.py` | 124 | Datos de DEMO para mirar el panel de temporada lleno, y borrarlos después. |
| ⚙️ `diagnostico_compra.py` | 157 | Qué pasó de verdad con las compras de una cuenta. SOLO LECTURA. |
| ⚙️ `dns_cf.py` | 170 | Crea o actualiza registros DNS en Cloudflare desde la terminal. |
| `edita_reel.py` | 351 | Monta un reel de verdad a partir de la grabación del sitio. |
| 🔬 `eje_precio.py` | 307 | De píxel a PRECIO: leer el eje y ajustar la escala, tolerando lecturas malas. |
| `escena_pc.py` | 224 | La botarga EN SU PC, animada — los planos de personaje del reel 2. |
| `extract_quiz_key.js` | 102 | Quiz answer-key extractor. |
| 🔬 `flechas.py` | 330 | LAS FLECHAS DE ENTRADA Y SALIDA que el trader dibuja en su captura. |
| `frames_preview.py` | 142 | Banco de pruebas de marcos de avatar. |
| `gen_camo_skins.py` | 82 | Render each ready camo's SKIN — the camo background alone, no app UI. |
| `gen_chart_foro.py` | 183 | Gráfico DIBUJADO POR NOSOTROS para el post de ejemplo del foro. |
| `gen_favicon.py` | 172 | Genera el icono del sitio en todos los tamaños que el mundo pide. |
| `gen_guide/build_guide.py` | 113 | Regenera /guide desde el contenido de guide_{en,es,frpt}.py. |
| `gen_guide/guide_en.py` | 206 | Contenido EN de la guía ampliada. Un dict por sección: lead, pasos y tip. |
| `gen_guide/guide_es.py` | 208 | Contenido ES. Escrito en español, no traducido del inglés palabra por palabra. |
| `gen_guide/guide_frpt.py` | 419 | Contenido FR y PT. Convención de siempre: FR en «vous», PT brasileño «você». |
| `gen_historias_ig.py` | 1156 | Historias de Instagram 1080×1920 — generador. |
| `gen_posts_ig.py` | 608 | Artes de Instagram/TikTok de Tradeable Academy — generador. |
| `gen_tira_botarga.py` | 112 | La tira de siluetas de la botarga para la banda azul de `/creators`. |
| 🔬 `hechos_grafico.py` | 1420 | PRUEBA BACKSTAGE (2/2) — los HECHOS de ICT/SMC, calculados sobre el OHLC. |
| 🔬 `informe_banco_pdf.py` | 214 | El informe del banco del analizador, en PDF para el dueño. |
| 🔬 `lee_grafico.py` | 453 | PRUEBA BACKSTAGE — reconstruir la serie OHLC desde el PÍXEL de un gráfico. |
| `limpia_botarga_nueva.py` | 228 | Deja una botarga recién encargada lista para el sitio: fondo fuera. |
| `limpia_tesseract.py` | 141 | Recorta el cubo de Tessera por su hexagono REAL, no por un umbral. |
| ⚙️ `limpiar_pruebas.py` | 284 | Borra los datos de PRUEBA antes de abrir el cobro de verdad. |
| `manda_correos_prueba.py` | 95 | Manda TODOS los correos que un usuario puede recibir, a una dirección tuya. |
| 🔬 `mapa_velas.py` | 150 | EL MAPA DE VELAS — pone el número de cada vela sobre la captura real. |
| `marca_sonora.py` | 382 | Candidatos a MARCA SONORA (audio logo) de Tradeable Academy. |
| `md_a_pdf.py` | 70 | Convierte un .md del repo en un PDF presentable, con la hoja de estilo de la |
| `mide_creditos_synapse.py` | 72 | — |
| `mide_quiz_movil.py` | 101 | ¿Se pisan la botarga y el texto en la bienvenida del Quiz? Medido. |
| `narra_preflight.py` | 175 | Calza la locución del reel de Pre-Flight y deja el vídeo a su ritmo. |
| ⚙️ `paypal_plan_diario.py` | 221 | Un plan de PRUEBA que se cobra cada DÍA, para ver una renovación de verdad. |
| ⚙️ `paypal_setup_subs.py` | 260 | Crea en PayPal el producto y los dos planes mensuales. Se corre UNA vez. |
| ⚙️ `paypal_setup_webhook.py` | 182 | Crea (o reutiliza) el webhook de PayPal y deja su id puesto en la config. |
| `pega_narracion.py` | 224 | Encaja la narración dentro del reel SIN cortar una sola sílaba. |
| `pf_demo_datos.py` | 161 | Los datos de la demo de Pre-Flight, sin tocar Flask ni ninguna base. |
| `plates_preview.py` | 1935 | Catálogo de MARCOS (placas del bloque de autor). |
| `posts_ig_textos.md` | 507 | Instagram — plan de publicación y captions |
| ⚙️ `preparar_prueba.py` | 312 | Deja una cuenta lista para el ensayo de compra, y el cupón creado. |
| `prueba_asistente_real.py` | 161 | ¿Se COMPORTA el asistente? Llamadas de verdad a la IA. |
| `quita_baranda.py` | 180 | Quita la baranda de la botarga (logo7) sin tocarle un dedo al personaje. |
| `rasteriza_posts.py` | 54 | Convierte a PNG las páginas que dejó `gen_posts_ig.py`. |
| `recorta_emociones.py` | 351 | Recorta los 12 rubíes de `tessera_emociones.png` y les BORRA EL FONDO. |
| 🔬 `recorta_grafico.py` | 516 | ¿Por dónde hay que recortar una captura, sin preguntarle nada al cliente? |
| `reel_analizador.py` | 623 | Reel 2 — EL ANALIZADOR. Primero el golpe, después la herramienta. |
| `reel_order_block.py` | 235 | Reel animado 1080x1920 — el concepto de Order Block, dibujado solo. |
| `reel_pf_datos.py` | 211 | Los datos del reel de Pre-Flight. El generador se declara ANTES de mirar. |
| `reel_preflight.py` | 916 | Reel #2 — PRE-FLIGHT: lo que tu propio historial dice de ti. |
| `reel_quiz.py` | 368 | Reel 3 — LOS QUIZZES. "¿Seguro que entendiste lo que estudiaste?" |
| `reel_sitio.py` | 136 | Graba el SITIO REAL en movimiento y lo deja en vertical para Instagram. |
| `reel_tiktok.py` | 121 | El mismo reel del tour, re-encuadrado para TIKTOK. |
| `reel_tour.py` | 851 | Reel #1 — EL TOUR: las herramientas del sitio, en uso, cortadas rápido. |
| `reels_guiones.md` | 136 | Reels — qué se puede animar por código y guiones de los 6 primeros |
| 🔬 `rejilla_velas.py` | 269 | Las velas que el modelo NO devolvió, recuperadas de la propia imagen. |
| ⚙️ `set_env.py` | 194 | Pone (o quita) variables de entorno en los DOS sitios, de un solo comando. |
| ⚙️ `set_paypal.py` | 239 | Deja PayPal configurado de una sola vez, sin editar archivos a mano. |
| 🧪 `simula_foro.py` | 361 | Punto 17: tráfico simulado en el foro, y un intento serio de romperlo. |
| 🧪 `simula_socio.py` | 164 | Da de alta un colaborador DE PRUEBA para ver el panel /partner lleno. |
| 🧪 `simula_xp.py` | 325 | Punto 21: un granjero de XP intenta inflar su rango por cada camino. |
| 🧪 `test_admin_plan_propio.py` | 146 | El admin puede cambiar SU propio plan (y solo el suyo entre admins). |
| 🧪 `test_ajustes.py` | 205 | ¿Funciona de verdad cada fila de /settings, o solo existe el boton? |
| 🔬 `test_analizador2.py` | 163 | Prueba de la cadena entera, SIN red, contra la captura real del dueño. |
| 🧪 `test_asistente.py` | 202 | El asistente del sitio: cableado, límites y lo que SABE. |
| 🧪 `test_asistente_wa.py` | 379 | El asistente de WhatsApp: ¿avisa de lo que importa y calla lo que no? |
| 🧪 `test_baile_del_cupon.py` | 177 | El "baile del cupón": ¿puede un cliente atado colarle un código a su |
| 🧪 `test_baja.py` | 284 | Darse de baja: ¿de verdad deja de cobrar, y de verdad respeta lo pagado? |
| 🧪 `test_baja_sub_fantasma.py` | 136 | Una suscripción que el comprador nunca aprobó no puede bloquear su baja. |
| 🧪 `test_boot_migracion.py` | 195 | Reproduce la caída de producción del 2026-08-02. |
| 🧪 `test_boot_postgres.py` | 179 | ¿Arranca la app contra una base de PRODUCCIÓN a la que le faltan columnas? |
| 🧪 `test_borrado_fk.py` | 177 | El borrado de cuenta contra una base que SI exige las claves foraneas. |
| 🧪 `test_borrar_comunidad.py` | 176 | Cerrar una comunidad del foro: quién puede, y qué se lleva por delante. |
| 🧪 `test_botargas_nuevas.py` | 171 | Las botargas de los camos NUEVOS (gridiron y nile) en navegador REAL. |
| 🧪 `test_botargas_std.py` | 103 | Prueba en navegador REAL: usuario con camo 'standard' puesto -> la |
| 🧪 `test_cambio_plan.py` | 208 | Bajar de plan se PROGRAMA: no se cobra hoy y no se pierden días. |
| 🧪 `test_carrito_ui.py` | 80 | El carrito mezclado: dos marcos + un camo + un cursor, y quitar UNO solo. |
| 🧪 `test_chalk_biblioteca.py` | 173 | La biblioteca de pizarras: guardar, reabrir, y lo que NO se puede hacer. |
| 🧪 `test_chalk_lib_nav.py` | 249 | La biblioteca, usada con el ratón: guardar, empezar en blanco, reabrir. |
| 🧪 `test_chalkboard_ux.py` | 775 | La pizarra tiene que dejarse usar sin pelear con ella. |
| 🧪 `test_chat_tema.py` | 153 | El fondo del chat de Tessera NO puede depender del camo. |
| 🧪 `test_check_borrados.py` | 151 | ¿El vigilante de cuentas borradas ve lo que tiene que ver? |
| 🧪 `test_check_suscripcion.py` | 166 | El verificador de una suscripción concreta, con un PayPal de mentira. |
| 🧪 `test_circuito_completo.py` | 268 | Recorrido COMPLETO de una cuenta: registro → verificación → sesión → |
| 🧪 `test_cobro_automatico.py` | 71 | Decision del dueno: PayPal y USDT van AUTOMATICOS — se paga y el plan se |
| 🧪 `test_codigo_verificacion.py` | 133 | El código de verificación que "no sirve": cada login lo mataba por detrás. |
| 🧪 `test_correo_bienvenida.py` | 86 | El correo de bienvenida no puede venderle humo a una cuenta Free. |
| 🧪 `test_correo_canonico.py` | 169 | Un buzón = una cuenta: los alias de Gmail ya no multiplican registros. |
| 🧪 `test_cosmeticos_paypal.py` | 69 | Con PayPal encendido, ¿se pueden comprar cosméticos de verdad? |
| 🧪 `test_creators.py` | 228 | El formulario de creadores de contenido (`/creators`), de punta a punta. |
| 🧪 `test_cripto_sandbox.py` | 31 | Un ensayo en el SANDBOX de cripto no puede contar como venta real. |
| 🧪 `test_cuenta.py` | 318 | Cambio de correo y borrado de cuenta: las dos filas que decian "muy pronto". |
| 🧪 `test_cupon_al_cobrar.py` | 137 | Un código se canjea cuando entra el dinero, NO cuando se pone en el carrito. |
| 🧪 `test_descuento_caduca.py` | 163 | Un descuento de promoción CADUCA; el de un socio no. |
| 🔬 `test_eje_precio.py` | 87 | Pruebas del ajuste de escala del eje de precios. |
| 🧪 `test_elegir_metodo.py` | 80 | El comprador SIEMPRE elige: PayPal o USDT. Si elige PayPal se le abre |
| 🧪 `test_enlace_resena.py` | 73 | El enlace "deja tu reseña" del correo del recibo. |
| 🧪 `test_escalera_socio.py` | 181 | La escalera 30/35/40 y qué pasa cuando un cliente hace chargeback. |
| 🧪 `test_favicon.py` | 110 | El icono del sitio existe, se sirve y está declarado. |
| 🧪 `test_foro_imagenes.py` | 276 | Punto 18 — subidas de imagen al foro: qué entra y qué no. |
| 🧪 `test_horas_pg.py` | 261 | El arreglo de zonas horarias, probado contra un POSTGRESQL REAL en Berlín. |
| 🧪 `test_ida_y_vuelta_promo.py` | 154 | Ida y vuelta: ¿puede un cliente atado saltar a una promo general y volver? |
| 🧪 `test_ingresos_prueba.py` | 146 | Los ensayos en sandbox no cuentan como ingresos. |
| 🧪 `test_intencion_compra.py` | 70 | Pulsar "Pasar a Premium" sin haber entrado tiene que llevarte AL PREMIUM, |
| 🧪 `test_ipn_cripto.py` | 151 | El aviso de pago en cripto se acepta, lo firme quien lo firme. |
| 🧪 `test_libro_cosmeticos.py` | 266 | El libro de cosméticos: aparte de los planes, por mes y por día. |
| 🧪 `test_limpiar_guiado.py` | 85 | El comando guiado: borra lo que se le dice, respeta lo que no, y NUNCA |
| 🧪 `test_limpieza.py` | 65 | La herramienta de limpieza: que borre lo que se le pide y NADA mas, y que |
| 🧪 `test_meses_apilados.py` | 256 | Nadie paga un mes que ya tiene pagado. |
| 🧪 `test_metodo_una_vez.py` | 146 | Al comprador NUNCA se le pregunta el método dos veces. |
| 🧪 `test_mis_cupones.py` | 127 | Punto 3: "Mis cupones" condicional + emisor de códigos personales en /admin. |
| 🧪 `test_no_apilar.py` | 223 | ¿Puede alguien, POR ALGUNA VÍA, acumular meses de plan? |
| 🧪 `test_panel_socio.py` | 204 | El panel del colaborador: quién entra, qué ve y la billetera del 4.4. |
| 🧪 `test_paypal_e2e.py` | 179 | El circuito de PayPal de punta a punta, con PayPal SIMULADO. |
| 🧪 `test_pdf_venta.py` | 299 | La venta del PDF de Synapse, de punta a punta, con PayPal simulado. |
| 🧪 `test_pedido_atascado.py` | 99 | El atasco que reporto el dueno: un pedido pendiente viejo bloquea cualquier |
| 🧪 `test_pedido_pendiente.py` | 268 | Comprar el plan X teniendo un pedido a medias del plan Y. |
| 🧪 `test_plan_en_vivo.py` | 176 | Cambio de plan desde /admin y baja del cliente: lo que ve cada uno. |
| 🧪 `test_plan_gratis.py` | 104 | ¿Se puede regalar un plan con un código del 100% y que llegue solo? |
| 🧪 `test_preparar_prueba.py` | 173 | La preparación del ensayo: que mire sin tocar, y que al aplicar CORTE. |
| 🧪 `test_preview_lock.py` | 98 | El candado de vista previa: solo las cuentas de la lista ven el sitio. |
| 🧪 `test_promo_31.py` | 236 | Cláusula 3.1/3.2 del acuerdo de socios, ejecutada de verdad. |
| 🧪 `test_promo_una_vez.py` | 118 | Una promoción general se canjea UNA vez por cuenta; la del socio, siempre. |
| 🧪 `test_recibo_email.py` | 158 | El recibo del comprador: se manda al activarse la compra, una sola vez. |
| 🧪 `test_recibo_features.py` | 110 | El recibo enumera TODO lo que trae el plan, y en los 4 idiomas. |
| 🧪 `test_red_cripto.py` | 92 | El carrito nombra la MISMA red en la que se va a cobrar. |
| 🧪 `test_registro_doble.py` | 137 | El doble envío del registro: "tu usuario ya está tomado"… por ti mismo. |
| 🔬 `test_rejilla.py` | 125 | Pruebas de la recuperación de velas por rejilla. |
| 🧪 `test_renovaciones.py` | 279 | Las renovaciones mensuales: la fecha que se le enseña y el corte de la baja. |
| 🧪 `test_reset_reenvio.py` | 60 | El reenvio del enlace de recuperacion: que funcione y que no se convierta en |
| 🧪 `test_robo_de_atribucion.py` | 141 | ¿Un cliente atado puede pasarse al código de OTRO creador dándose de baja? |
| 🧪 `test_rodada.py` | 180 | La RODADA de temporadas de la ruleta, probada mes a mes. |
| 🧪 `test_scroll_perf.py` | 169 | El scroll de /app tiene que ir fluido, y las tarjetas seguir legibles. |
| 🧪 `test_seguridad.py` | 56 | El candado de /analyze: cerrado para desconocidos, abierto para clientes. |
| 🧪 `test_set_paypal.py` | 69 | El configurador NO debe escribir nada si PayPal rechaza el par, y debe |
| 🧪 `test_setup_webhook.py` | 86 | Prueba el tool del webhook con un PayPal de mentira. |
| 🧪 `test_simula_socio.py` | 73 | Reproduce el fallo del 2026-08-13: borrar la demo de un colaborador YA USADO. |
| 🧪 `test_sitemap.py` | 49 | El sitemap solo puede llevar URLs FINALES: ninguna que redirija. |
| 🧪 `test_subs.py` | 374 | Suscripciones que se renuevan solas, ejecutadas de verdad. |
| 🧪 `test_tarifa_creador.py` | 130 | La tarifa del cliente de un socio no puede quedarse en la de LANZAMIENTO. |
| 🧪 `test_tira_banda.py` | 123 | La tira de botargas de la banda de `/creators`, comprobada en navegador. |
| 🧪 `test_unlocks.py` | 191 | Cuándo sale el "UNLOCKED" del plan — y, sobre todo, cuándo NO. |
| 🧪 `test_upgrade.py` | 225 | Subir de Standard a Premium: ¿te cobran uno o los dos? |
| 🧪 `test_vendor.py` | 171 | ¿Synapse y el Chalkboard funcionan SIN internet? |
| 🧪 `test_ventanas_festivas.py` | 70 | Ventanas festivas: calendario exacto acordado con el dueño (2026-08-02). |
| 🧪 `test_venv_shim.py` | 47 | Que el script se relance con el interprete de la app cuando el del sistema |
| 🧪 `test_viaje_temporada.py` | 139 | El VIAJE EN EL TIEMPO de la ruleta (`/admin/demo` scenario=season). |
| `validate_daily_bank.js` | 106 | DAILY_BANK validator — enforces the content rules of the dedicated Daily |
| `validate_synapse_content.py` | 117 | Valida el contenido de Synapse (base EN + overrides ES/FR/PT). |
| 🔬 `verifica_agudeza.py` | 130 | Comprueba que la verdad declarada del banco de agudeza es la que se DIBUJÓ. |

## `docs/`

| Archivo | Peso |
|---|---|
| `docs/Manual_Usuario_Chuky_Bot.pdf` | 6 KB |
| `docs/acuerdo_colaboracion.md` | 14 KB |
| `docs/acuerdo_colaboracion.pdf` | 227 KB |
| `docs/assets/logo_acuerdo.png` | 154 KB |
| `docs/banco_resultados/E1_impulso_ganado.md` | 3 KB |
| `docs/banco_resultados/E2_truncada_perdido.md` | 2 KB |
| `docs/banco_resultados/E3_trampa_solape.md` | 2 KB |
| `docs/banco_resultados/E4_trampa_tercera_corta.md` | 2 KB |
| `docs/banco_resultados/H1_gartley_ganado.md` | 2 KB |
| `docs/banco_resultados/H2_bat_perdido.md` | 3 KB |
| `docs/banco_resultados/H3_trampa_ratios.md` | 2 KB |
| `docs/banco_resultados/H4_trampa_butterfly.md` | 2 KB |
| `docs/banco_resultados/H5_direccion_invertida.md` | 2 KB |
| `docs/banco_resultados/I1_ict_sweep_fvg_ganado.md` | 2 KB |
| `docs/banco_resultados/I2_ote_ganado.md` | 2 KB |
| `docs/banco_resultados/I3_ict_sin_barrida_perdido.md` | 2 KB |
| `docs/banco_resultados/I4_trampa_sweep_inventado.md` | 2 KB |
| `docs/banco_resultados/I5_sl_cazado_perdido.md` | 2 KB |
| `docs/banco_resultados/I6_be_prematuro.md` | 3 KB |
| `docs/banco_resultados/INFORME.md` | 36 KB |
| `docs/banco_resultados/P1_hch_ganado.md` | 2 KB |
| `docs/banco_resultados/P2_triangulo_perdido.md` | 2 KB |
| `docs/banco_resultados/P3_trampa_doble_techo.md` | 2 KB |
| `docs/banco_resultados/P4_trampa_objetivo.md` | 2 KB |
| `docs/banco_resultados/P5_tp_tras_soporte.md` | 3 KB |
| `docs/banco_resultados/T1_divergencia_ganado.md` | 2 KB |
| `docs/banco_resultados/T2_cruce_rango_perdido.md` | 2 KB |
| `docs/banco_resultados/T3_trampa_rsi_inventado.md` | 2 KB |
| `docs/banco_resultados/T4_trampa_cruce_inexistente.md` | 2 KB |
| `docs/banco_resultados/T5_divergencia_tipo.md` | 2 KB |
| `docs/banco_resultados/W1_acumulacion_ganado.md` | 2 KB |
| `docs/banco_resultados/W2_spring_falso_perdido.md` | 2 KB |
| `docs/banco_resultados/W3_trampa_sin_volumen.md` | 2 KB |
| `docs/banco_resultados/W4_trampa_sin_rango.md` | 2 KB |
| `docs/banco_resultados/W5_contradiccion_propia.md` | 2 KB |
| `docs/banco_resultados_v2/E1_impulso_ganado.md` | 2 KB |
| `docs/banco_resultados_v2/E2_truncada_perdido.md` | 2 KB |
| `docs/banco_resultados_v2/E3_trampa_solape.md` | 2 KB |
| `docs/banco_resultados_v2/E4_trampa_tercera_corta.md` | 2 KB |
| `docs/banco_resultados_v2/H1_gartley_ganado.md` | 2 KB |
| `docs/banco_resultados_v2/H2_bat_perdido.md` | 2 KB |
| `docs/banco_resultados_v2/H3_trampa_ratios.md` | 2 KB |
| `docs/banco_resultados_v2/H4_trampa_butterfly.md` | 2 KB |
| `docs/banco_resultados_v2/H5_direccion_invertida.md` | 2 KB |
| `docs/banco_resultados_v2/I1_ict_sweep_fvg_ganado.md` | 2 KB |
| `docs/banco_resultados_v2/I2_ote_ganado.md` | 2 KB |
| `docs/banco_resultados_v2/I3_ict_sin_barrida_perdido.md` | 2 KB |
| `docs/banco_resultados_v2/I4_trampa_sweep_inventado.md` | 2 KB |
| `docs/banco_resultados_v2/I5_sl_cazado_perdido.md` | 2 KB |
| `docs/banco_resultados_v2/I6_be_prematuro.md` | 2 KB |
| `docs/banco_resultados_v2/INFORME-v2.md` | 36 KB |
| `docs/banco_resultados_v2/P1_hch_ganado.md` | 2 KB |
| `docs/banco_resultados_v2/P2_triangulo_perdido.md` | 2 KB |
| `docs/banco_resultados_v2/P3_trampa_doble_techo.md` | 2 KB |
| `docs/banco_resultados_v2/P4_trampa_objetivo.md` | 2 KB |
| `docs/banco_resultados_v2/P5_tp_tras_soporte.md` | 2 KB |
| `docs/banco_resultados_v2/T1_divergencia_ganado.md` | 2 KB |
| `docs/banco_resultados_v2/T2_cruce_rango_perdido.md` | 2 KB |
| `docs/banco_resultados_v2/T3_trampa_rsi_inventado.md` | 2 KB |
| `docs/banco_resultados_v2/T4_trampa_cruce_inexistente.md` | 2 KB |
| `docs/banco_resultados_v2/T5_divergencia_tipo.md` | 2 KB |
| `docs/banco_resultados_v2/W1_acumulacion_ganado.md` | 2 KB |
| `docs/banco_resultados_v2/W2_spring_falso_perdido.md` | 2 KB |
| `docs/banco_resultados_v2/W3_trampa_sin_volumen.md` | 2 KB |
| `docs/banco_resultados_v2/W4_trampa_sin_rango.md` | 2 KB |
| `docs/banco_resultados_v2/W5_contradiccion_propia.md` | 2 KB |
| `docs/banco_resultados_v3/E3_trampa_solape.md` | 2 KB |
| `docs/banco_resultados_v3/E4_trampa_tercera_corta.md` | 2 KB |
| `docs/banco_resultados_v3/H3_trampa_ratios.md` | 2 KB |
| `docs/banco_resultados_v3/H4_trampa_butterfly.md` | 2 KB |
| `docs/banco_resultados_v3/INFORME-v3.md` | 11 KB |
| `docs/banco_resultados_v3/P3_trampa_doble_techo.md` | 3 KB |
| `docs/banco_resultados_v3/T3_trampa_rsi_inventado.md` | 2 KB |
| `docs/banco_resultados_v3/T4_trampa_cruce_inexistente.md` | 2 KB |
| `docs/banco_resultados_v3/W3_trampa_sin_volumen.md` | 2 KB |
| `docs/cambio_visual_2026-08-10.md` | 5 KB |
| `docs/capturas_prueba/LEEME.md` | 5 KB |
| `docs/capturas_prueba/mes_5m.png` | 78 KB |
| `docs/capturas_prueba/mes_long_ote.png` | 106 KB |
| `docs/capturas_prueba/mes_long_ote.txt` | 582 B |
| `docs/capturas_prueba/mes_ote_construccion.txt` | 702 B |
| `docs/capturas_prueba/mes_ote_perdedor.png` | 110 KB |
| `docs/capturas_prueba/mnq_5m.png` | 103 KB |
| `docs/capturas_prueba/mnq_5m_zoom.png` | 108 KB |
| `docs/capturas_prueba/mnq_long_ote.png` | 108 KB |
| `docs/capturas_prueba/mnq_long_ote.txt` | 414 B |
| `docs/capturas_prueba/nq_5m_oct.png` | 93 KB |
| `docs/capturas_prueba/velas.md` | 3 KB |
| `docs/columnas/columnas_mes_long_ote.txt` | 2 KB |
| `docs/columnas/columnas_mnq_long_ote.txt` | 2 KB |
| `docs/generate_user_manual.py` | 8 KB |
| `docs/influencers.md` | 14 KB |
| `docs/prueba_cajas_PASOS.md` | 3 KB |
| `docs/reel_narracion.md` | 5 KB |
| `docs/ref_visual/antes_despues.jpg` | 209 KB |
| `docs/ref_visual/referencia_chronicles_dark.jpg` | 41 KB |
| `docs/ref_visual/referencia_nocamo_dark.jpg` | 35 KB |
| `docs/ref_visual/referencia_nocamo_light.jpg` | 34 KB |
| `docs/ref_visual/referencia_rising-sun_light.jpg` | 37 KB |

## `deploy/`

| Archivo | Peso |
|---|---|
| `deploy/coming_soon/index.html` | 6 KB |
| `deploy/coming_soon/logo.png` | 172 KB |
| `deploy/dominio.sh` | 4 KB |
| `deploy/nginx-tradingbot.conf` | 2 KB |
| `deploy/nginx/tradeable.academy.abierto.conf` | 4 KB |
| `deploy/nginx/tradeable.academy.conf` | 2 KB |
| `deploy/nginx/tradeable.academy.live.conf` | 7 KB |
| `deploy/nginx/tradeable.academy.preview.conf` | 10 KB |

## Raíz del repositorio

Solo nombre y peso (qué es cada uno: `19_BOT_VIEJO_Y_RAIZ_DEL_REPO.md`).

| Archivo | Peso |
|---|---|
| `.env.local.example` | 347 B |
| `.gitignore` | 769 B |
| `CHATGPT_TC_FULL_REVIEW.md` | 29 KB |
| `CHATGPT_TC_REVIEW_ROUND2.md` | 8 KB |
| `CLAUDE.md` | 102 KB |
| `CLAUDE_ARCHIVE.md` | 359 KB |
| `COPYRIGHT_REGISTRATION_GUIDE.md` | 6 KB |
| `ICT - GATILLOS DE ENTRADA (EJEMPLOS) (1).pdf` | 1.3 MB |
| `LANZAMIENTO.md` | 20 KB |
| `LEGAL_REVIEW_Privacy_Policy.md` | 10 KB |
| `LEGAL_REVIEW_Terms_and_Conditions.md` | 30 KB |
| `Scalpel_Checklist_PreLanzamiento.pdf` | 11 KB |
| `Scalpel_Costos_Operativos_IA.pdf` | 10 KB |
| `Trader_Acelerator_Privacy_Policy.pdf` | 31 KB |
| `Trader_Acelerator_Terms_and_Conditions.pdf` | 58 KB |
| `Trading_Research_Mobile_iPhone.pdf` | 135 KB |
| `Trading_Research_Report_2025_2026.pdf` | 236 KB |
| `backtest.py` | 19 KB |
| `backup_db.py` | 4 KB |
| `daily_audit_summary.py` | 3 KB |
| `generate_mobile_report.py` | 60 KB |
| `generate_report.py` | 84 KB |
| `grant_legend.py` | 3 KB |
| `instrumentation.ts` | 877 B |
| `legal_privacy_review.html` | 13 KB |
| `legal_terms_review.html` | 34 KB |
| `legend_badge_preview.html` | 7 KB |
| `main.py` | 18 KB |
| `migrate_to_postgres.py` | 3 KB |
| `monitor.py` | 3 KB |
| `next.config.mjs` | 614 B |
| `nginx.conf.example` | 1 KB |
| `package.json` | 773 B |
| `postcss.config.mjs` | 145 B |
| `rank_badges_preview.html` | 11 KB |
| `rank_badges_preview_v2.html` | 11 KB |
| `rank_badges_preview_v3.html` | 14 KB |
| `rank_badges_preview_v4.html` | 16 KB |
| `requirements.txt` | 374 B |
| `reset_daily.py` | 2 KB |
| `scalpel_costos_operativos.csv` | 3 KB |
| `server.py` | 16 KB |
| `tailwind.config.ts` | 972 B |
| `tsconfig.json` | 548 B |
| `vercel.json` | 129 B |

## Resto de carpetas (bot viejo)

- `.github/` — 1 archivos
- `.streamlit/` — 1 archivos
- `api_server/` — 3 archivos
- `app/` — 15 archivos
- `components/` — 5 archivos
- `config/` — 2 archivos
- `dashboard/` — 16 archivos
- `data/` — 4 archivos
- `indicators/` — 8 archivos
- `lib/` — 4 archivos
- `reporting/` — 5 archivos
- `reports/` — 1 archivos
- `risk/` — 4 archivos
- `scripts/` — 1 archivos
- `store/` — 1 archivos
- `strategy/` — 3 archivos
- `validation/` — 4 archivos
