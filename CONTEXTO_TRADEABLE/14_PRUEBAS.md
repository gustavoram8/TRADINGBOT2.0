# 14 · PRUEBAS

## Cómo se prueba este proyecto

- **No hay un framework** (ni pytest ni unittest). Cada prueba es un **script
  suelto** en `tools/` que imprime una línea por comprobación y termina con un
  resumen tipo `23/23`. Código de salida 0 = todo bien.
- **No hay integración continua.** El único workflow de `.github/` es del bot
  viejo. Las pruebas se corren a mano antes de subir.
- **Nombres en español** y cabeceras que explican *qué blindan y por qué*
  (casi siempre, el fallo real que las originó).
- **Hay 86 scripts de prueba** (`test_*.py`) y 3 simuladores (`simula_*.py`).

## Tipos de prueba

| Tipo | Cómo funciona | Ejemplos |
|---|---|---|
| **De servidor** | Importan `scalpel/app.py` con una base SQLite temporal y usan `app.test_client()`. PayPal/cripto se **simulan**. | `test_subs.py`, `test_cupon_al_cobrar.py`, `test_cuenta.py` |
| **De navegador real** | Playwright + Chromium contra el servidor local. Miden píxeles, clics y errores de consola. | `test_chalkboard_ux.py`, `test_carrito_ui.py`, `test_creators.py` |
| **De arranque** | Borran columnas de una base ya creada y vuelven a arrancar (simulan un deploy). | `test_boot_migracion.py`, `test_boot_postgres.py` |
| **Con PostgreSQL real** | Necesitan un PostgreSQL de verdad. | `test_horas_pg.py`, `test_boot_postgres.py` |
| **Simuladores de ataque** | Golpean las reglas por HTTP como lo haría un usuario tramposo. | `simula_foro.py` (65 reglas), `simula_xp.py` (36 defensas), `simula_socio.py` |
| **Del laboratorio** | Sin red, contra verdad por construcción. | `test_analizador2.py`, `test_eje_precio.py`, `test_rejilla.py`, `hechos_grafico.py --probar`, `banco_cadena.py` |
| **Validadores de contenido** | Paridad de idiomas, estructura. | `audit_legal_translations.py`, `validate_synapse_content.py`, `validate_daily_bank.js` |

## Cómo correrlas

```bash
pip install --ignore-installed blinker -r scalpel/requirements.txt   # (el blinker del sistema estorba)
python3 tools/test_subs.py            # una
for t in tools/test_*.py; do echo "== $t"; python3 "$t" | tail -1; done   # todas (tarda)
```

**Antes de subir cualquier cambio** (regla de calidad del proyecto):
1. que las plantillas Jinja tocadas compilen;
2. `node --check` del JavaScript tocado;
3. claves de traducción parejas en los 4 idiomas;
4. las pruebas de la zona tocada;
5. si se tocó lo legal: `audit_legal_translations.py`;
6. si se tocó un banco de preguntas: `extract_quiz_key.js` + `validate_daily_bank.js`;
7. si se añadió una columna: `test_boot_migracion.py`.

## Estado comprobado al armar este expediente (2026-11-15)

Solo se corrieron las del laboratorio (las del sitio no se corrieron en esta
pasada; sus cifras son las anotadas en las notas cuando se escribieron):

| Prueba | Resultado |
|---|---|
| `hechos_grafico.py --probar` | ✅ 75/75 |
| `test_analizador2.py` | ✅ 15/15 |
| `test_eje_precio.py` | ✅ 18/18 |
| `test_rejilla.py` | ✅ 15/15 |
| `banco_cadena.py --laminas 12` | ✅ corre; cifras coherentes con la tabla |
| `flechas.py --probar` | 🔴 0/4 (depende de la versión de librerías; ver carpeta 10, doc 06) |

⚠️ **Recomendado para quien herede el proyecto:** correr la batería completa
una vez y anotar qué pasa y qué no. Llevan sin correrse juntas desde agosto.

## 🔴 Trampas conocidas de las pruebas

- **SQLite perdona lo que PostgreSQL no** (claves ajenas, zonas horarias,
  palabras reservadas, secuencias). Las pruebas de borrado usan
  `PRAGMA foreign_keys=ON`. Una base recién creada **no prueba un deploy**.
- **`with app.test_client() as c:` conserva la sesión de SQLAlchemy** y su
  caché: el usuario se queda congelado en el plan viejo. Para algo que cruce
  dos sesiones, clientes **sin** `with`.
- **Flask-Login guarda el usuario en `g`**: con un `app_context()` abierto todo
  el script, la segunda petición corre como el primer usuario. Hacer
  `g.pop('_login_user', None)`.
- **Un doble de prueba que miente hace fallar código correcto** (los PayPal
  falsos respondían "ACTIVE" después de cancelar).
- **`page.click()` de Playwright teletransporta el puntero**: no reproduce
  fallos de "el menú se cierra al cruzar un hueco". Usar `mouse.move(steps=…)`.
- **`locator.screenshot()` incluye lo pintado encima**; para medir un lienzo,
  leer `getImageData`.
- **`offsetParent` es `null` en elementos `position:fixed`** aunque se vean.
- **Sin `FLASK_DEBUG`, Jinja cachea plantillas**: reiniciar el servidor de prueba.
- **CDNs inalcanzables en el contenedor** (Google Fonts, cdnjs): usar
  `wait_until='domcontentloaded'` y abortar peticiones externas, o cada carga
  tarda 30 s.
- **`/app` rebota a `/welcome`** sin la cookie del splash; `/login` y
  `/register` redirigen si ya hay sesión.
- **Cada caso con su propia IP** (`X-Forwarded-For`) cuando hay tope por IP.
- **`init_db` crea una cuenta admin**: no contar usuarios en absoluto.
- **Rutas absolutas** en varias pruebas viejas (`/home/user/TRADINGBOT2.0/…`).
- **Lo que no se puede probar sin gastar:** el juicio de la IA. Las pruebas
  cubren todo lo que la rodea.
- **El contenedor de desarrollo se recicla:** lo que esté en un scratchpad se
  pierde (ya se perdieron pruebas así). Toda prueba que valga, a `tools/`.

## Lo que NO está cubierto

- Una suscripción **activa de verdad** cancelándose de punta a punta en PayPal.
- Carga con usuarios reales autenticados.
- Móvil real (se emula con Playwright; el dueño y su hermano prueban a mano).
- El Analizador 2.0 con modelo real de forma automatizada.

---

## Lista completa (generada del repo)

🌐 = usa navegador real (Playwright).

| Archivo | Qué comprueba (primera línea de su cabecera) |
|---|---|
| `simula_foro.py` | Punto 17: tráfico simulado en el foro, y un intento serio de romperlo. |
| `simula_socio.py` | Da de alta un colaborador DE PRUEBA para ver el panel /partner lleno. |
| `simula_xp.py` | Punto 21: un granjero de XP intenta inflar su rango por cada camino. |
| `test_admin_plan_propio.py` | El admin puede cambiar SU propio plan (y solo el suyo entre admins). |
| `test_ajustes.py` | ¿Funciona de verdad cada fila de /settings, o solo existe el boton? |
| `test_analizador2.py` | Prueba de la cadena entera, SIN red, contra la captura real del dueño. |
| `test_asistente.py` | El asistente del sitio: cableado, límites y lo que SABE. |
| `test_asistente_wa.py` | El asistente de WhatsApp: ¿avisa de lo que importa y calla lo que no? |
| `test_baile_del_cupon.py` | El "baile del cupón": ¿puede un cliente atado colarle un código a su |
| `test_baja.py` | Darse de baja: ¿de verdad deja de cobrar, y de verdad respeta lo pagado? |
| `test_baja_sub_fantasma.py` | Una suscripción que el comprador nunca aprobó no puede bloquear su baja. |
| `test_boot_migracion.py` | Reproduce la caída de producción del 2026-08-02. |
| `test_boot_postgres.py` | ¿Arranca la app contra una base de PRODUCCIÓN a la que le faltan columnas? |
| `test_borrado_fk.py` | El borrado de cuenta contra una base que SI exige las claves foraneas. |
| `test_borrar_comunidad.py` | Cerrar una comunidad del foro: quién puede, y qué se lleva por delante. |
| `test_botargas_nuevas.py` 🌐 | Las botargas de los camos NUEVOS (gridiron y nile) en navegador REAL. |
| `test_botargas_std.py` 🌐 | Prueba en navegador REAL: usuario con camo 'standard' puesto -> la |
| `test_cambio_plan.py` | Bajar de plan se PROGRAMA: no se cobra hoy y no se pierden días. |
| `test_carrito_ui.py` 🌐 | El carrito mezclado: dos marcos + un camo + un cursor, y quitar UNO solo. |
| `test_chalk_biblioteca.py` | La biblioteca de pizarras: guardar, reabrir, y lo que NO se puede hacer. |
| `test_chalk_lib_nav.py` 🌐 | La biblioteca, usada con el ratón: guardar, empezar en blanco, reabrir. |
| `test_chalkboard_ux.py` 🌐 | La pizarra tiene que dejarse usar sin pelear con ella. |
| `test_chat_tema.py` 🌐 | El fondo del chat de Tessera NO puede depender del camo. |
| `test_check_borrados.py` | ¿El vigilante de cuentas borradas ve lo que tiene que ver? |
| `test_check_suscripcion.py` | El verificador de una suscripción concreta, con un PayPal de mentira. |
| `test_circuito_completo.py` | Recorrido COMPLETO de una cuenta: registro → verificación → sesión → |
| `test_cobro_automatico.py` | Decision del dueno: PayPal y USDT van AUTOMATICOS — se paga y el plan se |
| `test_codigo_verificacion.py` | El código de verificación que "no sirve": cada login lo mataba por detrás. |
| `test_correo_bienvenida.py` | El correo de bienvenida no puede venderle humo a una cuenta Free. |
| `test_correo_canonico.py` | Un buzón = una cuenta: los alias de Gmail ya no multiplican registros. |
| `test_cosmeticos_paypal.py` | Con PayPal encendido, ¿se pueden comprar cosméticos de verdad? |
| `test_creators.py` | El formulario de creadores de contenido (`/creators`), de punta a punta. |
| `test_cripto_sandbox.py` | Un ensayo en el SANDBOX de cripto no puede contar como venta real. |
| `test_cuenta.py` | Cambio de correo y borrado de cuenta: las dos filas que decian "muy pronto". |
| `test_cupon_al_cobrar.py` | Un código se canjea cuando entra el dinero, NO cuando se pone en el carrito. |
| `test_descuento_caduca.py` | Un descuento de promoción CADUCA; el de un socio no. |
| `test_eje_precio.py` | Pruebas del ajuste de escala del eje de precios. |
| `test_elegir_metodo.py` | El comprador SIEMPRE elige: PayPal o USDT. Si elige PayPal se le abre |
| `test_enlace_resena.py` | El enlace "deja tu reseña" del correo del recibo. |
| `test_escalera_socio.py` | La escalera 30/35/40 y qué pasa cuando un cliente hace chargeback. |
| `test_favicon.py` | El icono del sitio existe, se sirve y está declarado. |
| `test_foro_imagenes.py` | Punto 18 — subidas de imagen al foro: qué entra y qué no. |
| `test_horas_pg.py` | El arreglo de zonas horarias, probado contra un POSTGRESQL REAL en Berlín. |
| `test_ida_y_vuelta_promo.py` | Ida y vuelta: ¿puede un cliente atado saltar a una promo general y volver? |
| `test_ingresos_prueba.py` | Los ensayos en sandbox no cuentan como ingresos. |
| `test_intencion_compra.py` | Pulsar "Pasar a Premium" sin haber entrado tiene que llevarte AL PREMIUM, |
| `test_ipn_cripto.py` | El aviso de pago en cripto se acepta, lo firme quien lo firme. |
| `test_libro_cosmeticos.py` | El libro de cosméticos: aparte de los planes, por mes y por día. |
| `test_limpiar_guiado.py` | El comando guiado: borra lo que se le dice, respeta lo que no, y NUNCA |
| `test_limpieza.py` | La herramienta de limpieza: que borre lo que se le pide y NADA mas, y que |
| `test_meses_apilados.py` | Nadie paga un mes que ya tiene pagado. |
| `test_metodo_una_vez.py` | Al comprador NUNCA se le pregunta el método dos veces. |
| `test_mis_cupones.py` | Punto 3: "Mis cupones" condicional + emisor de códigos personales en /admin. |
| `test_no_apilar.py` | ¿Puede alguien, POR ALGUNA VÍA, acumular meses de plan? |
| `test_panel_socio.py` | El panel del colaborador: quién entra, qué ve y la billetera del 4.4. |
| `test_paypal_e2e.py` | El circuito de PayPal de punta a punta, con PayPal SIMULADO. |
| `test_pdf_venta.py` | La venta del PDF de Synapse, de punta a punta, con PayPal simulado. |
| `test_pedido_atascado.py` | El atasco que reporto el dueno: un pedido pendiente viejo bloquea cualquier |
| `test_pedido_pendiente.py` | Comprar el plan X teniendo un pedido a medias del plan Y. |
| `test_plan_en_vivo.py` | Cambio de plan desde /admin y baja del cliente: lo que ve cada uno. |
| `test_plan_gratis.py` | ¿Se puede regalar un plan con un código del 100% y que llegue solo? |
| `test_preparar_prueba.py` | La preparación del ensayo: que mire sin tocar, y que al aplicar CORTE. |
| `test_preview_lock.py` | El candado de vista previa: solo las cuentas de la lista ven el sitio. |
| `test_promo_31.py` | Cláusula 3.1/3.2 del acuerdo de socios, ejecutada de verdad. |
| `test_promo_una_vez.py` | Una promoción general se canjea UNA vez por cuenta; la del socio, siempre. |
| `test_recibo_email.py` | El recibo del comprador: se manda al activarse la compra, una sola vez. |
| `test_recibo_features.py` | El recibo enumera TODO lo que trae el plan, y en los 4 idiomas. |
| `test_red_cripto.py` | El carrito nombra la MISMA red en la que se va a cobrar. |
| `test_registro_doble.py` | El doble envío del registro: "tu usuario ya está tomado"… por ti mismo. |
| `test_rejilla.py` | Pruebas de la recuperación de velas por rejilla. |
| `test_renovaciones.py` | Las renovaciones mensuales: la fecha que se le enseña y el corte de la baja. |
| `test_reset_reenvio.py` | El reenvio del enlace de recuperacion: que funcione y que no se convierta en |
| `test_robo_de_atribucion.py` | ¿Un cliente atado puede pasarse al código de OTRO creador dándose de baja? |
| `test_rodada.py` | La RODADA de temporadas de la ruleta, probada mes a mes. |
| `test_scroll_perf.py` 🌐 | El scroll de /app tiene que ir fluido, y las tarjetas seguir legibles. |
| `test_seguridad.py` | El candado de /analyze: cerrado para desconocidos, abierto para clientes. |
| `test_set_paypal.py` | El configurador NO debe escribir nada si PayPal rechaza el par, y debe |
| `test_setup_webhook.py` | Prueba el tool del webhook con un PayPal de mentira. |
| `test_simula_socio.py` | Reproduce el fallo del 2026-08-13: borrar la demo de un colaborador YA USADO. |
| `test_sitemap.py` | El sitemap solo puede llevar URLs FINALES: ninguna que redirija. |
| `test_subs.py` | Suscripciones que se renuevan solas, ejecutadas de verdad. |
| `test_tarifa_creador.py` | La tarifa del cliente de un socio no puede quedarse en la de LANZAMIENTO. |
| `test_tira_banda.py` 🌐 | La tira de botargas de la banda de `/creators`, comprobada en navegador. |
| `test_unlocks.py` | Cuándo sale el "UNLOCKED" del plan — y, sobre todo, cuándo NO. |
| `test_upgrade.py` | Subir de Standard a Premium: ¿te cobran uno o los dos? |
| `test_vendor.py` 🌐 | ¿Synapse y el Chalkboard funcionan SIN internet? |
| `test_ventanas_festivas.py` | Ventanas festivas: calendario exacto acordado con el dueño (2026-08-02). |
| `test_venv_shim.py` | Que el script se relance con el interprete de la app cuando el del sistema |
| `test_viaje_temporada.py` | El VIAJE EN EL TIEMPO de la ruleta (`/admin/demo` scenario=season). |
