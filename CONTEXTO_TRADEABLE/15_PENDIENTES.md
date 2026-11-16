# 15 · PENDIENTES — todo lo que falta, por urgencia

> Foto del 2026-11-15. Reúne lo que estaba disperso en `CLAUDE.md`,
> `CLAUDE_ARCHIVE.md`, `LANZAMIENTO.md` y lo que se encontró al armar el expediente.

---

## 🔴 A · Revisar YA (tienen fecha vencida o riesgo real)

| # | Qué | Por qué urge | Cómo |
|---|---|---|---|
| A1 | **Oferta de bienvenida del 30%** | No caduca sola. El plan era apagarla el **12-oct-2026**. No consta que se apagara: si sigue, todo comprador nuevo paga el primer mes a $17,50 / $35 y compite con el descuento de los colaboradores. | En el VPS: `venv/bin/python3 tools/check_oferta.py`, o mirar la línea `[Oferta]` del log. Apagar: `python3 tools/set_env.py --quitar LAUNCH_DISCOUNT_PCT` + `supervisorctl reread && supervisorctl update`. **Decide el dueño.** |
| A2 | **Contraseña de admin por defecto en el código** | Ver doc 13, hallazgo H1. | Confirmar que la contraseña del admin se cambió; activar 2FA; quitar el valor del código. |
| A3 | **Camo de diciembre (Colosseum) sin arte** | La ruleta de diciembre lo anuncia como premio y no existe. Quedan días. | Construirlo (`tools/build_*_camo.py` como modelo), o rodar el calendario (`RULETA_RODADA`). **Decide el dueño.** |
| A4 | **Copyright sin registrar** | La ventana recomendada (3 meses desde la apertura del 13-ago) venció hacia el 13-nov. Sigue siendo registrable, con menos ventajas. | `COPYRIGHT_REGISTRATION_GUIDE.md` (~$135–260). |
| A5 | **Estado real de producción sin verificar** | Este expediente no pudo mirar el VPS. | Correr el bloque de verificación del doc 04. |
| A6 | **¿Hay ventas o clientes reales?** | No consta. De eso dependen varias decisiones (oferta, anuales, rotación de secretos). | `/admin` → Ventas e Ingresos. |

## 🟠 B · Seguridad e infraestructura

1. Cerrar el **puerto 5001** al exterior.
2. **Límite de intentos** en `/login`.
3. **Antiflood por IP en `/register`** (acordado antes de lanzar; no hecho).
4. **IP real** del visitante tras Cloudflare (`CF-Connecting-IP`).
5. **Copias de seguridad fuera del VPS.**
6. HSTS; CSP (trabajo aparte); CSRF con token.
7. **Cron diario de `tools/check_borrados.py`.**
8. Activar Sentry.
9. Prueba de carga con usuarios reales autenticados.
10. Sacar el correo personal del código (4 archivos).
11. WeasyPrint y dependencias del laboratorio fuera de `requirements`: documentar/fijar.
12. Subir `TERMS_VERSION` si corresponde (sigue en `2026-06-05`).

## 🟠 C · Pagos

1. 🔴 **Ver cancelarse una suscripción ACTIVA real** de punta a punta (nunca se
   ha visto).
2. Confirmar si **USDT/NOWPayments** tiene claves puestas y funciona.
3. Selector de mes en el panel de gastos.
4. Recordar: con PayPal en live, una compra de prueba entra al libro y hay que
   revertirla a mano.

## 🟡 D · Producto (sitio)

| Qué | Nota |
|---|---|
| **Botargas de The Alchemist** | Las genera el dueño; ideas acordadas (matraz esmeralda + grimorio / oro logrado / matraz explotado). Pidió que se le recordara. |
| Camos de temporada siguientes | Summit (ene), Bengal (feb), Olympus (mar), Baseball, Apiarist, Welder, Zeppelin. |
| Pestaña en `/admin` para **solicitudes de creadores** | Ofrecido, no pedido. Hoy solo llegan por correo. |
| Pestaña en `/admin` para solicitudes de mentoría | Solo relevante si se reabre. |
| "(?)" de ayuda que faltan | Synapse, Kill Zones, Rangos/XP, Notas, Subida. |
| Huecos del quiz | Technical Analysis, Elliott, Fundamental, Quant, Price Action básico, OTE/StdDev. |
| Pre-Flight: tope de 500 chequeos | Los más viejos dejarían de verse sin aviso. |
| Chalkboard | Cerrado; preguntas abiertas: ¿20 velas es el tope?, ¿editar una secuencia ya dibujada? |
| Legibilidad del pie bajo camos | ⛔ Intentado y revertido por el dueño. No reabrir sin que lo pida. |
| "Mi cuenta" | Hecho; el dueño dijo que aún no lo había revisado. |
| Certificado/camos por rango | Sin diseñar. |
| Redes: X, YouTube, Reddit, Discord, Telegram | Aparecen en `/socials` cuando se ponga su enlace. |

## 🟡 E · Legal y negocio

1. **Validar con abogado** las Secciones 14 y 15 de los Términos.
2. **Punto 7 de la checklist del dueño (el único sin cerrar de 25):** validez
   jurídica del acuerdo de colaboración sin empresa constituida.
3. Rellenar los 6 huecos del acuerdo; decidir el preaviso de terminación.
4. Lista de creadores a contactar (`docs/influencers.md`): todos "sin contactar".
5. ¿Publicar la reseña del fundador? (Recomendado: no.)

## 🔬 F · Analizador 2.0

Hoja de ruta completa en `10_ANALIZADOR_2_LABORATORIO/08_QUE_FALTA_Y_HOJA_DE_RUTA.md`.
En corto: (1) que el banco dibuje como un TradingView real; (2) arreglar el
medidor del paso (falla en 3 de 6 capturas reales); (3) subir la medición de
velas a ≥95%; (4) fijar dependencias y arreglar `flechas.py`; (5) completar
familias de hechos; (6) repetir la comparación con 10 trades reales;
(7) conexión al sitio **solo con permiso**.

**Preguntas sin respuesta del dueño:**
- ¿Autoriza que el analizador **actual** deje de afirmar lo que no puede
  verificar? (cambio de prompt)
- Datos del trade de `nq_5m_oct` (flechas, construcción, sesión, resultado).

## ⚪ G · En espera (no empezar sin que el dueño lo pida)

Mentorías (y Bunny Stream) · Prop Firm Scout · tienda de indicadores · planes
anuales · Stripe · Replay Lab · Trade of the Day · autopublicación en redes ·
rotar secretos (**decidió que no**).

---

## 🧹 NOTAS VIEJAS QUE YA NO VALEN (para no fiarse de ellas)

`CLAUDE.md` sigue siendo la memoria activa, pero arrastra secciones que
quedaron desactualizadas. **Antes de actuar sobre una de estas, creer a este
expediente o verificar:**

| Dónde | Qué dice | La realidad |
|---|---|---|
| `CLAUDE.md` → "Infra / escalado" → nginx | "nginx hoy sirve SOLO la página de en construcción; no hay reverse proxy" (30-jul) | Desde agosto nginx sirve la app; el sitio está abierto desde el 13-ago. |
| `CLAUDE.md` → "Operativa" | "Deploy en VPS (`62.171.180.22:5001`)" como acceso | Con `PUBLIC_HTTPS=1` ya no se puede iniciar sesión por IP:5001. Se entra por el dominio. |
| `CLAUDE.md` → "Stack técnico" | "IA: … GitHub Models hoy" | Producción usa la API de pago de OpenAI desde el 17-jul. |
| `CLAUDE.md` → "PIVOT 2026-07-26" punto 2 | "sigue el NO auto-renew" | Desde el 4-ago los mensuales se renuevan solos; los Términos se reescribieron. |
| `CLAUDE.md` → "Pendientes de él" #3 | "Devolverle el escrito de PayPal… RETOMAR PAYPAL" | PayPal está LIVE desde el 10-ago. |
| `CLAUDE.md` → "Cola para mañana" | Lista del 14-ago "sin luz verde" | Puntos 1, 2 y 4 hechos; el 3 (seguridad) es el bloque B de arriba. |
| `CLAUDE.md` → "SU FIB" | "Tres salidas… SIN respuesta todavía" | Eligió la opción 1 (octubre): premium/discount solo con las anclas del trader. Ya cableado. |
| `CLAUDE.md` → "Stand-by" → XP | "FALTA aún: certificado PDF de rank-up" | El certificado existe (`/certificate/<rango>/pdf`). Los números de línea citados ahí son viejos. |
| `CLAUDE.md` → título | "Scalpel — Trader Accelerator" | El nombre es Tradeable Academy. |
| `LANZAMIENTO.md` → cabecera | "Lo que queda: PUBLIC_HTTPS=1, cambiar nginx a live…" | Hecho el 13/14-ago. Sí quedan: puerto 5001 y copyright. |
| `LANZAMIENTO.md` → cuerpo (30-jul) | Bloqueantes: "nadie puede pagarte", "support@ no existe" | Resueltos. |
| `CLAUDE_ARCHIVE.md` → varias | "encender PayPal", "Stripe es el riel", "BUG ABIERTO 500 en /register" | Historia. El 500 era falta de memoria, resuelto. |
| `docs/capturas_prueba/LEEME.md` | "paso de 4,5 px", "~155 velas", "~3 px" | Estimaciones previas al medidor nuevo. Ver carpeta 10, doc 05. |
| Cabecera de `tools/banco_cadena.py` | Opción `--columnas-ia` | No existe. |
| Cifras "N/N" de pruebas en las notas | Resultado del día en que se escribieron | Varias suites crecieron después; correrlas para saber el estado. |

**Sugerencia:** el próximo que trabaje con `CLAUDE.md` debería limpiar esas
secciones (moviendo lo histórico al archivo) para que la memoria activa deje de
contradecir a la realidad.
