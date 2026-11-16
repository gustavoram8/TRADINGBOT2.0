# 02 · HISTORIA DEL PROYECTO

> Reconstruida del historial de git (1.503 commits) y de las notas de trabajo.
> El detalle fino de cada punto está en `CLAUDE_ARCHIVE.md` (anexo).

## Números gordos

- **Primer commit:** 2026-04-28. **Último:** 2026-10-12.
- **1.503 commits:** abril 2 · mayo 213 · junio 388 · julio 330 · agosto 459 ·
  septiembre 102 · octubre 9.
- **Autoría:** ~1.473 commits de Claude (IA), el resto del dueño desde el VPS.
- **Ramas:** 14 en el remoto. La única viva es `claude/gallant-volta-i7cqmf`.
  `main` se quedó en el 2026-05-09.

## Línea de tiempo

### Abril – mayo 2026 · El bot de trading (prehistoria)
- **28-abr:** nace el repo `TRADINGBOT2.0` como un **bot de trading ICT**:
  backtesting en Python, panel en Next.js, panel en Streamlit.
- **09-may:** último commit de `main`. El bot queda desplegado en el VPS en
  `/opt/tradingbot` (hoy apagado, intacto).

### 26 de mayo · Nace Scalpel
- Commit `8d8cb02`: *"Add Scalpel — ICT trade analysis web app (MVP)"*. Una app
  Flask aparte, en la carpeta `scalpel/`, que analiza capturas con GPT-4o Vision.
  Es el giro del proyecto: de "bot que opera" a "herramienta que enseña".

### Finales de mayo – junio · Se arma el producto
- **Synapse** (cerebro 3D con three.js), flujo de entrada en 4 pantallas
  (landing → login/registro → splash → app), registro obligatorio con código
  por correo.
- **Quiz** con tres niveles y luego el **Quiz Hardcore** (16 metodologías × 10
  escenarios = 160).
- **10–11 jun:** producción pasa a **PostgreSQL + gunicorn**; registro de
  auditoría, copias de seguridad diarias, monitor por WhatsApp.
- **11–13 jun:** ruleta, testimonios (solo reales, regla FTC), sistema
  **XP / 8 rangos**, anti-trampa del quiz (las respuestas viven en el servidor).
- **17–19 jun:** Kill Zones + calendario económico; repaso legal completo
  (fuera todo lenguaje de asesoría); panel de gasto de IA; el prompt se vuelve
  "router de ramas" (se envía solo la metodología elegida).
- **20–23 jun:** renombre a "Trader Accelerator"; se parte `CLAUDE.md` y nace
  `CLAUDE_ARCHIVE.md`; se resuelve una caída por falta de memoria (reciclaje de
  workers + swap).

### Julio · Monetización y comunidad
- **02–10 jul:** se escribe el **banco del Reto Diario**: 200 preguntas
  "ultrahardcore" en 22 lotes, en 4 idiomas; el banco deja de enviarse al
  navegador (anti-trampa total).
- **12 jul:** Stripe integrado y probado en modo test.
- **16–17 jul:** prompt dinámico por metodología + reducción de imagen a
  1280 px (control de costo); se conecta la **API de pago de OpenAI**; panel de
  admin en 6 pestañas.
- **24–26 jul:** **Tessera** (asistente), funnel completo de **Mentorías**,
  área de miembros, foro "Raygun Mark II" (comunidades, seguir, mensajes).
- **26 jul — EL PIVOTE:** el mentor/socio (Gabriel Celis) no se suma. Sin él no
  hay empresa ni banco en EE. UU. → sin Stripe. Consecuencias: mentorías
  ocultas, cobro por **USDT (NOWPayments) y PayPal**, y los Términos se
  re-anclan a **Venezuela**. Nombre oficial pasa a **Tradeable Academy**.
- **27 jul:** primer bug serio de producción (secuencias de PostgreSQL).
- **30 jul:** se compra **`tradeable.academy`**; DNS en Cloudflare, HTTPS,
  página de "en construcción". Se apaga el bot viejo que respondía en el dominio.
- **31 jul:** ayuda contextual "(?)", `/socials`, libro de ventas, reserva
  anti-contracargo, Financial Hub en Excel.

### Agosto · Pulido, pagos de verdad y apertura
- **01 ago:** paquete de seguridad de cuentas (18+, 2FA, sesiones), referidos
  con atribución perpetua, panel del colaborador, planes anuales APAGADOS.
- **02 ago:** la ruleta pasa de dar cupones a dar **cosméticos por temporada**;
  nace la tienda de cosméticos; segundo bug serio de producción (la app no
  arrancaba tras un deploy → regla "las migraciones no usan el ORM").
- **03 ago:** el dueño dicta su **checklist de 25 puntos** (se le murió el
  teléfono y perdió sus notas). Se va cerrando uno por uno durante el mes.
- **04–05 ago:** **suscripciones automáticas** de PayPal; el dominio empieza a
  servir la app detrás de un pase; reglas de cambio de plan (subir inmediato,
  bajar programado, nadie paga dos veces); **primer bug cazado por una compra
  real** (cobraba un plan distinto al del carrito).
- **07–10 ago:** chat de Tessera a pantalla completa; correo del dominio
  funcionando; **PayPal LIVE (10-ago)**; librerías externas guardadas dentro
  del sitio; arreglo de rendimiento del scroll; regla "baja antes que borrado".
- **12 ago:** Chalkboard a fondo (biblioteca en servidor, herramientas de
  trading editables, 7 patrones).
- **13 ago — 🚀 EL SITIO SE ABRE AL PÚBLICO** (*"YA SALIMOS"*). Oferta de
  bienvenida del 30%. Ese mismo día se pegan por accidente los secretos del
  servidor en el chat; el dueño decide no rotarlos.
- **13–14 ago:** el **banco de 30 casos** mide al analizador y destapa que la
  IA "cree" lo que dicen las etiquetas en vez de medir. Se añade la cláusula de
  verificación. Favicon, ficha de Google, Search Console.
- **22–23 ago:** `/creators`, rodada de temporadas de la ruleta; el dueño se
  ausenta un par de semanas.

### 31 de agosto – septiembre · La turbina (Analizador 2.0)
- **31 ago:** el estudio de agudeza visual demuestra que el problema **no es la
  resolución**: GPT-4o ve de sobra pero no sabe comparar alturas.
- **04–05 sep:** Gemini sí localiza velas; nace la **cadena** (el modelo dice
  dónde, los píxeles miden, la aritmética concluye). Regla de las 8 milésimas,
  recorte automático, lectura del eje de precios.
- **06–10 sep:** bloque de hechos en tres niveles, liquidez completa,
  estructura y MSS, ventana del trade en tres partes, **primera comparación
  real** contra el analizador del sitio.
- **13–16 sep:** se descubre que el banco de pruebas le "regalaba" un dato a la
  cadena; se rehace el medidor del paso entre velas; **primera tabla de
  precisión honesta**; arreglo de los giros empatados; se mide la fib del dueño
  al píxel.

### Octubre · Última sesión de trabajo
- **12 oct:** el rango premium/discount pasa a depender de que el trader diga
  dónde ancló su fib; sexta captura real ("a ciegas") donde la cadena falla en
  el primer paso; regla definitiva sobre el color de las velas del dueño;
  robustez del laboratorio.

### Noviembre
- **15 nov:** se arma este expediente. Sin cambios de producto desde octubre.

## Las ramas que quedaron atrás

`analyze-ict-trading-bot-54reJ`, `analyze-repository-context-USRUv`,
`analyze-trading-bot-70XMZ`, `analyze-trading-bot-RNNU5`,
`backtest-chart-timeframes-S9Mvm`, `dazzling-goodall-SnVVP`,
`epic-lovelace-GsOuo` (Scalpel temprano), `fix-backtest-nginx-timeout-sWWgp`,
`fix-backtesting-trades-2F3q2`, `gracious-wozniak-SLDrW`,
`hopeful-volta-kk3zg2` (congelada el 2026-07-26; ⚠️ las sesiones en la nube de
Claude arrancan aquí por error y hay que cambiarse a mano),
`intelligent-turing-94qh5i`, `wonderful-gates-JAa9X` (donde nació Scalpel).
Ninguna tiene nada que no esté ya en `gallant-volta`.

## Las cinco lecciones que marcaron el proyecto

1. **Una compra real encuentra lo que cien pruebas no.** El peor bug de pagos
   lo cazó el dueño abandonando un carrito a medias, que es lo que hace todo el
   mundo y ninguna prueba hacía.
2. **Lo que funciona en la base de pruebas no prueba el deploy.** Dos caídas de
   producción vinieron de cosas que SQLite perdona y PostgreSQL no.
3. **Una nota desactualizada hace decir tonterías con confianza.** Se le dijo
   al dueño "cuando enciendas PayPal" cuando PayPal ya cobraba.
4. **Un banco de pruebas que le da la respuesta a la pieza que prueba, no la
   prueba.** El control de calidad del Analizador 2.0 estuvo meses en verde
   mientras fallaba en gráficos reales.
5. **Cuando el dueño insiste tres veces en lo mismo, la causa está en otra
   parte.** (El caso de las velas "huecas".)
