# 07 · FUNCIONALIDADES — qué hay en el sitio, pieza por pieza

> Para cada pieza: qué hace, dónde vive, en qué estado está y qué trampas tiene.
> El detalle de construcción de cada una está en `CLAUDE_ARCHIVE.md` (anexo).

---

## 1. Entrada al sitio

**Flujo:** portada (`/`) → registro o login → splash (`/welcome`) → app (`/app`).

- **Registro:** usuario, correo, contraseña, **fecha de nacimiento (18+)** con
  tres selectores, aceptación de Términos (se guarda fecha y versión). Rechaza
  contraseñas débiles y alias del mismo buzón (`juan+2@gmail.com`).
- **Verificación:** código de 6 dígitos por correo.
- **Login:** "recordar este dispositivo" (cookie de 10 años), 2FA opcional,
  aviso por correo cuando entra un dispositivo nuevo.
- **Splash:** animación de bienvenida obligatoria antes de `/app`.
- **Idioma:** se guarda en `scalpel_lang`; si no hay preferencia, en páginas
  sueltas se usa el idioma del navegador.
- ⚠️ **Pendiente:** antiflood por IP en `/register` (mil registros automáticos
  quemarían la reputación del correo).

## 2. El analizador de capturas (el corazón del producto)

Documentado aparte en **`09_ANALIZADOR_DEL_SITIO.md`**. En corto: el trader
sube una captura con entrada y salida marcadas, rellena instrumento, dirección,
sesión, resultado, sesgo, metodología, confluencias y hasta 200 palabras de
"construcción del trade". El sitio valida la captura, llama a la IA y devuelve
un análisis educativo en su idioma.

- **Proyectos:** carpetas para agrupar análisis (1 / 5 / 10 según plan).
- **Límite:** Free 1 por semana · Standard 1 por día · Premium 5 por día.

## 3. Pre-Flight (👑 Premium)

Entrenador de disciplina: el trader arma su **checklist de confluencias** y,
**antes** de entrar a un trade, marca cuáles se cumplen → veredicto
*go / caution / no-go*. Después anota el resultado.

- **Estadísticas** rediseñadas el 2026-08-12 tras medir con datos simulados que
  las viejas eran ruido. **Regla:** ninguna tasa sin su muestra y ningún
  "mejor/peor" con menos de 10 casos por lado. Muestra: adherencia (% de trades
  tomados que eran *go*), **expectativa en R**, drawdown máximo, descartados y
  pendientes. Se quitaron "mejor confluencia", "mejor día" y "overrides
  ganadores" por engañosos.
- Hasta 10 checklists (mismo límite que proyectos). Tabla con buscador y orden.
- ⚠️ El servidor devuelve como mucho 500 chequeos; pasados ~2 años de uso
  diario, los más viejos dejarían de verse sin aviso. Anotado, no arreglado.
- Herramienta de prueba: `tools/demo_preflight.py`.

## 4. Foro (💠 Standard y Premium)

Comunidad interna tipo red social.

- Publicaciones (2 por día), comentarios, 5 reacciones, guardados.
- Pestañas: general, **Siguiendo**, **Comunidades**.
- **Comunidades privadas:** máximo 3 por usuario, nombre único; se entra por
  solicitud o invitación; el creador puede cerrarla (las publicaciones se
  vacían con ella).
- **Mensajes directos** entre miembros de pago.
- **Moderación por IA antes de publicar** (texto e imagen). Conoce la jerga de
  trading para no censurarla. La imagen se clasifica: fuera de tema, sexual,
  drogas, armas, violencia o **venta de señales** (lo más peligroso legalmente).
  Si la IA está caída, deja pasar (*fail-open*).
- **Disciplina:** advertencias → silenciado temporal automático → sugerencia de
  baneo que **solo un admin confirma**.
- Placas ("marcos") y nombre encendido para el top del ranking.
- Probado con `tools/simula_foro.py`: 65 reglas atacadas por HTTP, 0 evadibles.

## 5. Quiz (👑)

- **Banco general** (`QUESTION_BANK`, dentro de `index.html`): principiante,
  intermedio, avanzado.
- **Hardcore:** 16 metodologías × 10 escenarios con gráfico.
- **Anti-trampa:** el navegador solo manda qué opción eligió; el servidor juzga
  con `quiz_answer_key.json`. Las opciones se barajan al mostrarse.
- Certificado por metodología al completar.
- **Huecos conocidos:** no hay quiz de Technical Analysis/indicadores, Elliott,
  Fundamental, Quant, Price Action básico ni OTE/StdDev.
- 🔴 Si se edita un banco: `node tools/extract_quiz_key.js && node
  tools/validate_daily_bank.js` y subir los JSON generados.

## 6. Reto Diario + Ruleta (👑)

- **Una pregunta al día**, de un banco propio de **200 preguntas** muy
  difíciles, sin gráficos, en 4 idiomas (`scalpel/daily_bank.js`, que **nunca**
  se envía al navegador). 60 segundos para responder.
- **Cada usuario tiene su propio calendario** de preguntas (permutación
  derivada de la clave secreta): no se puede soplar la respuesta a otro.
- **Racha:** 7 aciertos seguidos = un giro de ruleta.
- **Ranking mensual** (aciertos; desempata el menor tiempo) y salón de la fama.
- **La ruleta da cosméticos**, no descuentos: cada mes una **tanda** de 1 camo
  + 2 placas + 3 cursores que **no vuelve** al acabar el mes.

### Calendario de temporadas (`RULETA_RODADA` en `app.py`)
| Mes real | Temporada | Arte |
|---|---|---|
| Ago + Sep 2026 | Chronicles | ✅ |
| Oct 2026 | American Football (gridiron) | ✅ |
| Nov 2026 | Nile | ✅ |
| **Dic 2026** | **Colosseum** | 🔴 **falta el arte del camo** |
| Ene 2027 | Summit | pendiente |
| Feb 2027 | Bengal | pendiente |
| Mar 2027 | Olympus | pendiente |
| Abr 2027 → | Baseball, Apiarist, Welder, Zeppelin… (ya coinciden con su mes) | pendiente |

El admin puede "viajar en el tiempo" desde `/admin/demo` para ver un mes futuro.

## 7. Cosméticos y tienda (`/cosmetics`)

Tres tipos de pieza:
- **Camo:** tema visual completo del sitio (colores, fondo ilustrado, logo y
  mascota "botarga"). Algunos tienen dos "looks".
- **Placa / marco:** banda decorativa de 640×48 en el bloque de autor del foro.
- **Cursor:** puntero personalizado (solo se ve en computadora).

**Tres canales que nunca se mezclan:** ruleta (solo se gana), tienda (solo se
compra), campeón (solo por ranking). Una pieza pertenece a un canal para siempre.

**Precios** (el servidor es la única verdad): camo $4,99 · camo festivo $7,99 ·
cursor $1,99 (festivo $2,99) · placa $2,99 (festiva $3,99). Solo por PayPal.

**Piezas festivas:** se pueden comprar **solo durante 24 horas** en su fecha, en
hora de Venezuela (UTC−4): Año Nuevo, San Valentín, San Patricio, Pascua,
4 de julio, Halloween, Día de Muertos, solsticio (21-dic), Navidad.

**Camos con tema hecho (`CAMO_READY`):** rising-sun, pole, premium, fourth,
naval, mission, blackflag, standard, chronicles, gridiron, nile, highnoon,
alchemist. El resto del catálogo aparece como "próximamente".
- 🔴 **Alchemist no tiene botargas propias** (usa la mascota por defecto): las
  genera el dueño y están pendientes.

**Cada plan de pago trae su camo** (`standard`, `premium`), que se queda aunque
el plan venza. **Regla: nada se revoca jamás.**

**Reparto del arte:** lo procedimental (fondos, placas, cursores) lo generan
scripts de `tools/` (`build_*_camo.py`, `build_plates.py`, `build_cursors.py`);
los personajes (botargas) los encarga el dueño y se limpian con
`limpia_botarga_nueva.py` / `botarga_oscura.py`.

## 8. Chalkboard (👑) — la pizarra

Lienzo de diapositivas para dibujar setups, presentar y exportar a PDF.
Hecho con fabric.js.

- **Herramientas:** selección, lápiz, líneas, rayos, zonas, texto, borrador;
  familia **Trading** (secuencia de velas, **posición con R:R medido y
  editable**, Fibonacci configurable con banda OTE); familia **Patrones**
  (XABCD con razones calculadas, Elliott 0-5, ABC, hombro-cabeza-hombro, canal,
  extensión de Fibonacci, etiquetas de evento Wyckoff/SMC).
- **Atajos de teclado** de una letra; herramienta "pegajosa"; clic derecho
  termina o suelta.
- **Biblioteca en el servidor:** 20 diapositivas por proyecto, 30 proyectos por
  cuenta, 2 MB por proyecto. "Guardar" archiva y deja la pizarra en blanco.
- ✅ **Cerrado para el lanzamiento** por decisión del dueño: lo nuevo saldrá de
  reportes de usuarios reales.
- Pruebas: `test_chalkboard_ux.py` (80), `test_chalk_biblioteca.py` (23),
  `test_chalk_lib_nav.py` (18).

## 9. Synapse (👑) — la biblioteca 3D

Mapa visual del conocimiento: un cerebro 3D (three.js) con **5 metodologías y
41 temas** (Price Action 9, Technical Analysis 9, SMC/ICT 11, Fundamental 6,
Quant 6). Cada tema abre un "dossier" tipo libro con diagramas.

- Contenido: `static/synapse_library.js` (inglés) + `synapse_content_{es,fr,pt}.json`.
- Progreso por usuario; enlaces al quiz del tema.
- Modelos 3D con licencia CC BY: la **atribución es obligatoria** y aparece
  dentro de Synapse y en el pie (en negrita con halo, sin recuadro — el dueño
  rechazó el recuadro).
- **PDF de pago** ("Synapse Library", $15, precio de lista $20): 91 páginas,
  índice interactivo, 46 marcadores, 164 enlaces internos. Cada tema trae
  secciones exclusivas del PDF: *playbook*, *modos de fallo*, *ejercicio* y
  *temas relacionados*. Se genera con WeasyPrint, personalizado con el nombre
  del comprador. **Se vende solo dentro de Synapse** (no en la portada: orden
  expresa del dueño). Lo comprado sobrevive a bajar de plan.
- Validador: `python3 tools/validate_synapse_content.py`.

## 10. Kill Zones y calendario económico

Reloj en vivo de las sesiones (hora de Nueva York): Asia 20–00, Londres 2–5,
NY AM 9:30–11, almuerzo 12–13, NY PM 13:30–16, y las tres "Silver Bullet"
(3–4, 10–11, 14–15). Calendario económico con el widget de TradingView,
filtrable por instrumento, con aviso educativo.

## 11. Rangos y XP

Ocho rangos por puntos acumulados (nunca bajan):

| # | Rango | XP |
|---|---|---|
| 1 | Paper Trader | 0 |
| 2 | Retail Trader | 200 |
| 3 | Chart Technician | 600 |
| 4 | Liquidity Hunter | 1.400 |
| 5 | Swing Strategist | 2.800 |
| 6 | Order Flow Sniper | 5.000 (desde aquí: acceso beta) |
| 7 | Market Maker | 8.000 |
| 8 | Trading Legend | 12.000 |

**De dónde sale el XP:** entrar cada día (Free 18 / Standard 12 / Premium 5),
analizar (60 / 30 / 10), reseña (30, una vez al mes); y solo Premium: quiz
(5/8/12, tope 20 al día), reto diario (15, +30 por racha de 7), Pre-Flight
(20 la primera vez, 5 por chequeo, tope 15), foro (5 post / 2 comentario /
1 reacción, con topes). **Tope maestro Premium: 80 XP al día.** La ponderación
es inversa: lo poco que puede hacer un plan barato vale más.

- Al subir de rango: aviso animado, **medalla + certificado PDF** con código
  verificable público (`/verify/<código>`), compartible en redes.
- Probado con `tools/simula_xp.py`: 36 defensas, 0 formas de farmear.
- Pendiente de diseño: camos por rango (no existen; se quitó la promesa).

## 12. Tessera — el asistente

Un teseracto rubí anclado abajo a la derecha. Al abrirlo, una "cámara" con
**cinco puertas** en forma de constelación: 01 Chat de ayuda · 02 Guía ·
03 Teletransportador (saltar a cualquier sección) · 04 Soporte · 05 Reportar bug.

- **El chat responde solo sobre cómo funciona la plataforma** (no es tutor de
  trading). Usa un modelo pequeño (`gpt-4o-mini`) con un dossier
  (`scalpel/assistant_kb.py`) que toma precios y límites del código en vivo.
  Tope: 25 preguntas por hora y 80 por día por usuario.
- La cámara tiene estética propia y fija (no cambia con los camos).
- ⚠️ `assistant_kb.py` se carga por ruta de archivo, no con `import`: bajo
  gunicorn un import normal tumbaba los 4 workers.

## 13. Ayuda contextual, guía y soporte

- Botones **"(?)"** que abren un panel de ayuda en: Pre-Flight, Analizador,
  Chalkboard, Foro y Quiz. Faltan: Synapse, Kill Zones, Rangos, Notas y Subida.
- `/guide`: guía completa (se genera desde `tools/gen_guide/`; no editar la
  plantilla a mano).
- `/contact`: formulario → correo a soporte (y WhatsApp al dueño si el texto
  suena a "pagué y no me llegó").
- Reporte de bugs con captura, visible en `/admin`.

## 14. "Mi cuenta" (`/settings`)

Plan y fecha de próximo cobro, cambiar de plan, darse de baja, contraseña,
2FA, cerrar otras sesiones, cambiar correo, borrar cuenta. Es la primera
entrada del menú de usuario.

## 15. Panel de administración (`/admin`)

Pestañas: **Usuarios** (planes, baneos, modo demo) · **Ingresos** (pedidos,
"pagos que necesitan atención", cupones, gastos) · **Moderación** · **Gasto de
IA** (costo por llamada y por día, saldo) · **Auditoría** · **Bugs** ·
**📒 Ventas** (libro, colaboradores, "día 15: marcar pagadas") · **⭐ Reseñas**.
Faltan pestañas para ver solicitudes de creadores y de mentoría.

## 16. Colaboradores y creadores

- **`/creators`:** formulario para que un creador de contenido se postule. El
  enlace vive en una historia destacada de Instagram. Guarda la solicitud
  aunque el correo falle. No muestra porcentajes.
- **`/proyecto`:** presentación para pegar en un mensaje directo.
- **`/partner`:** panel del colaborador (clientes, tramo, comisiones, fechas
  del acuerdo, billetera USDT). Detalle económico en el doc 08.

## 17. Reseñas

Solo de usuarios reales (regla FTC). Se piden dentro de la app; dan XP sea cual
sea la nota. La reseña del fundador, si se publica, sale etiquetada. El admin
publica o retira con un botón.

## 18. `/socials`

Redes oficiales (Instagram y TikTok `@tradeableacademy`; las demás aparecen
cuando se configure su enlace) y tablero informativo del próximo sorteo (el
sorteo real se hace a mano; reglamento en la Sección 19 de los Términos).

---

## Funciones construidas y APAGADAS

| Función | Interruptor | Por qué está apagada |
|---|---|---|
| **Mentorías** (funnel `/improve*`, compra, área de miembros con clases, chat y preguntas) | `MENTORSHIP_ENABLED=0` | El mentor no se sumó. Con `=1` vuelve todo idéntico, incluida su sección de los Términos. Video definitivo decidido: Bunny Stream (sin conectar). |
| **Prop Firm Scout** (catálogo de 25 firmas + chat) | `SCOUT_ENABLED=0` | Falta mantener los datos al día con fuente verificable. |
| **Tienda de indicadores** | `INDICATORS_ENABLED=0` | Sin modelo de entrega viable en TradingView. |
| **Planes anuales** | `ANNUAL_PLANS_ENABLED=0` | Un contracargo anual no lo cubre ninguna reserva. |
| **Stripe** | sin `STRIPE_SECRET_KEY` | No hay banco en EE. UU. |

## Ideas en espera (no construidas)

- **Replay Lab:** reconstrucción histórica de un trade con datos reales
  (forex/oro gratis con Dukascopy; NQ/MES exige licencia de CME).
- **Trade of the Day.** Descartado hasta tener ingresos estables.
- **Autopublicación en redes** e investigación de visión (agosto, sin construir).
- **Certificados/camos por rango**, agenda de mentorías, subida directa de video.
