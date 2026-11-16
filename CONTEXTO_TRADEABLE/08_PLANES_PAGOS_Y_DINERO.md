# 08 · PLANES, PAGOS Y DINERO

> 🔴 **Todo esto corre contra dinero real.** PayPal está en LIVE desde el
> 2026-08-10 y no hay sandbox conectado. Antes de exponer cualquier cambio que
> llame a la pasarela: una prueba con cuenta desechable y mirar el panel de PayPal.

## 1. Los planes

| | Free | Standard | Premium |
|---|---|---|---|
| **Precio mensual** | $0 | **$25** | **$50** |
| Precio anual (apagado) | — | $240 | $480 |
| Análisis | 1 / 7 días | 1 / 24 h | 5 / 24 h |
| Proyectos y checklists | 1 | 5 | 10 |
| Foro | — | ✓ | ✓ |
| Pre-Flight, Quiz, Reto diario, Chalkboard, Synapse | — | — | ✓ |
| Camo del plan (permanente) | — | `standard` | `premium` |

- Precios en `PLAN_PRICING`, límites en `PLAN_LIMITS` y `PROJECT_LIMITS`
  (`app.py`). **Los precios redondos $25/$50 son decisión cerrada del dueño.**
- Todo se cobra y se muestra **en USD**.
- **Oferta de bienvenida** (`LAUNCH_DISCOUNT_PCT`): descuento solo en el
  **primer mes**, solo mensual, nunca en renovaciones. En producción quedó en
  **30%** ($17,50 / $35 el primer mes). 🔴 **No caduca sola** y el plan era
  apagarla el 12-oct-2026 — verificar (doc 15).

## 2. Los rieles de cobro

| Riel | Estado | Para qué |
|---|---|---|
| **PayPal** | 🟢 LIVE | Planes (suscripción mensual automática), cosméticos, PDF de Synapse. Recupera EE. UU./Canadá/Europa. |
| **USDT por NOWPayments** | 🟡 condicional (`CRYPTO_API_KEY`) | Planes, pago único (una cadena de bloques no permite cobro automático). Pensado para Venezuela/Argentina/Colombia/Brasil/Perú. ⚠️ Sin verificar si las claves están puestas en el VPS. |
| **USDT manual** | Respaldo | Sin claves de pasarela, `checkout_done.html` muestra instrucciones manuales. |
| **Stripe** | ⚪ apagado | Probado en modo test; sin banco en EE. UU. no se usa. |

- La cuenta de PayPal es **Business, a nombre del papá del dueño**. Como no se
  puede renombrar a "Tradeable Academy", el carrito avisa *"el cargo aparecerá a
  nombre de X"* (`PAYPAL_RECEIPT_NAME`) — defensa contra el contracargo "no
  reconozco esto".
- Si hay más de un riel encendido, el comprador elige en `/checkout/pay/<id>`.
- PayPal puede ofrecer "Pay in 4" al comprador: no se puede quitar y no
  importa (PayPal paga el importe completo y asume el riesgo).

## 3. Cómo viaja una compra de plan

```
/checkout  →  /checkout/create  →  PayPal (aprobar)  →  vuelta al sitio
   (carrito)     (crea Order         (suscripción          (/checkout/paypal/subscription/<id>)
                  'pending' +         o pago suelto)
                  PlanSubscription)
                                          ↓
                          _activate_plan_from_order(order)   ← ÚNICA puerta que entrega un plan
                                          ↓
        extiende el plan · otorga el camo · ata el referido · anota el cupón
        · escribe el libro de ventas (record_sale_breakdown) · manda el recibo
```

**Dos objetos distintos:**
- **`Order` = un cobro.** Cada mes cobrado crea una `Order` nueva.
- **`PlanSubscription` = el permiso** de PayPal para cobrar cada mes.

**Tres redes de seguridad** para que un pago nunca quede sin entregar:
1. el **webhook** (`/webhook/paypal`, verificado contra la API de PayPal);
2. la **reconciliación** al abrir la página del pedido;
3. el **barrido** cada vez que el admin abre `/admin` (`payments_sweep`).

Además: bandeja **"Pagos que necesitan atención"** y avisos al dueño (correo y
WhatsApp) cuando alguien pagó y no se activó, un cobro falló, hay una disputa o
llegó dinero a una cuenta borrada.

🔴 **Las renovaciones llegan ÚNICAMENTE por webhook** (nadie vuelve a la web en
el mes 2). Por eso `PAYPAL_SUBS_ENABLED` exige `PAYPAL_WEBHOOK_ID` y los dos ids
de plan; sin ellos el sitio cae al pago suelto y no promete renovación.

## 4. Las reglas del dinero (todas decididas por el dueño; no reabrir)

| Regla | Detalle |
|---|---|
| **Los mensuales se cobran solos** | El cliente se da de baja cuando quiera, sin costo ni preaviso. |
| **La baja corta la renovación, no el mes pagado** | Sigue con su plan hasta la fecha que ya pagó. |
| **Nadie paga dos planes ni adelanta meses** | `puede_comprar()` lo impide en las dos puertas (pantalla y POST). |
| **Subir de plan = inmediato** | Paga hoy, mes nuevo desde cero, pierde los días del plan barato (se le avisa con los días exactos antes de cobrar). La suscripción vieja se corta sola. |
| **Bajar de plan = programado** | No se cobra hoy; conserva su plan hasta la fecha pagada y ese día entra el barato (endpoint `revise` de PayPal). Se puede deshacer. |
| **El borrado de cuenta EXIGE la baja previa** | "Cancelar plan" es el único sitio que corta cobros; "Eliminar cuenta" solo comprueba que no quede ninguno. Así *cuenta borrada + cobro vivo* es imposible. |
| **Ante la duda, no se miente** | Si PayPal no responde al cancelar, NO se le dice al cliente "cancelado". |
| **El cupón se gasta al COBRAR**, no al ponerlo en el carrito | Un carrito abandonado no consume el código. |
| **El pedido pendiente solo se retoma si es la MISMA compra** | Si pide otra cosa, el viejo se suelta (y se corta su suscripción en PayPal). |
| **El "UNLOCKED" solo salta en compra nueva o cambio de plan** | Nunca en renovaciones ni por cosméticos. |
| **Anual y USDT no son recurrentes** | Anual por riesgo; USDT porque es técnicamente imposible. |
| **Contracargos y disputas NUNCA quitan el plan solos** | Avisan al dueño; decide una persona, con `/admin/trace` como prueba de entrega. |
| **Un cupón del 100% no toca la pasarela** | Pedido de $0 se activa solo (`payment_method='free'`) y no crea suscripción. |

## 5. Cupones (`PromoCode`)

Tres clases:
- **Generales** (campañas).
- **De creador** (`kind='creator'`, con dueño): dan descuento **perpetuo** al
  cliente y comisión al colaborador.
- **Personales** (atados a un usuario): premios de sorteo, compensaciones; se
  emiten desde `/admin`. Los "SPIN-XXXXXX" viejos de la ruleta siguen válidos.

**Atribución perpetua:** el primer pedido **pagado** con un código de creador
ata la cuenta a ese colaborador para siempre (`User.referred_by_code`). Desde
entonces el descuento se aplica solo en cada compra y la comisión fluye en cada
renovación. El código de otro creador sobre una cuenta atada responde `locked`.
Una promoción general sí puede ganarle en precio (si deja el total más bajo),
pero la comisión sigue yendo al colaborador original.

🔴 **Nunca borrar un código de creador con clientes atados: desactivarlo.**

## 6. Programa de colaboradores

Documento legal: `docs/acuerdo_colaboracion.md` (fuente) → PDF con
`tools/build_acuerdo_pdf.py`. **La palabra "socio" está prohibida**: se dice
"colaborador" (prestador independiente).

- **Comisión escalonada MARGINAL, cliente por cliente:** clientes 1–24 → 30%,
  25–74 → 35%, 75 en adelante → 40%. El cliente 25 gana 35%; **no** sube a los
  24 anteriores. (El esquema retroactivo se midió y se descartó: crea puntos
  donde al dueño le conviene que el colaborador no venda. Alternativa guardada:
  33% plano.)
- **Se cuentan CLIENTES, no pagos:** una renovación no sube de tramo.
- **Ranking vivo:** si un cliente se va, los de abajo suben un puesto (un 40%
  puede volver a 35%). Lo ya pagado no se reescribe.
- **Contracargo:** saca al cliente del recuento, cancela su comisión pendiente
  o la vuelve *clawback* si ya se pagó.
- **Solo las suscripciones generan comisión** (no el PDF ni los cosméticos).
- **Liquidación el día 15, siempre en USDT.** La billetera la escribe el propio
  colaborador en `/partner` (queda auditado).
- **Plazo:** 3 meses iniciales, revisión a los 30 días, renovación automática
  por trimestres.
- Sin rol especial en el sistema: **colaborador = dueño de un `PromoCode`**.
- Se puede trabajar con varios a la vez; cada uno ve solo lo suyo.
- ⚠️ Faltan por rellenar 6 huecos entre corchetes en el acuerdo, y decidir el
  preaviso de terminación anticipada (hoy 15 días).

Pruebas: `test_escalera_socio.py`, `test_panel_socio.py`, `test_promo_31.py`,
`test_robo_de_atribucion.py`, `simula_socio.py`. Comparador de esquemas:
`tools/compara_esquemas.py`.

## 7. El libro de ventas (`SaleBreakdown`, pestaña 📒 Ventas)

Cada venta se desmenuza **una vez** y queda congelada:

```
bruto − descuento del código − comisión del colaborador − comisión de PayPal
      − costo operativo imputado − reserva anti-contracargo = utilidad disponible
```

- **Comisión de PayPal real**, leída de la captura; si no hay dato se estima
  (5,4% + $0,30) y se marca "estim.".
- **Reserva anti-contracargo: 25% de lo PAGADO** (no de la utilidad), porque un
  contracargo obliga a devolver el pago entero.
- **Costo operativo imputado:** $1/mes Standard, $5/mes Premium.
- Una reversión tacha la fila y saca su reserva del total.
- Ventas manuales se pueden cargar y borrar; las reales solo se revierten.
- Las compras de prueba en sandbox no entran al libro; ⚠️ con PayPal en live,
  una compra de prueba **sí entra** y hay que revertirla a mano.
- Existe un **Financial Hub en Excel** (14 hojas) con la misma matemática,
  entregado al dueño **fuera del repo** a propósito.

## 8. Costos de IA

- Cada análisis hace **2 llamadas** (validar + analizar) ≈ **$0,02–0,03**.
- Tarifa GPT-4o usada para estimar: $2,50 / $10 por millón de tokens.
- El gasto real por llamada se ve en `/admin` → Gasto de IA.
- Techos: imagen reducida a 1280 px, notas a 2.000 caracteres / 200 palabras,
  respuesta a 900 tokens.
- 10 cuentas Free cuestan ~$1,20 al mes en análisis.

## 9. Herramientas de pagos (en `tools/`, se corren en el VPS)

| Herramienta | Para qué |
|---|---|
| `set_paypal.py` | Poner credenciales; crea producto y planes de suscripción. |
| `paypal_setup_webhook.py` | Crea/repara el webhook con sus 15 eventos. |
| `paypal_setup_subs.py` | Crea los planes (lo llama `set_paypal.py`). |
| `check_paypal.py` | ¿Las credenciales autentican y a qué entorno pertenecen? |
| **`check_subs.py`** | **¿Sirven de verdad las renovaciones?** (planes activos, webhook correcto). |
| `check_suscripcion.py` | Revisa una suscripción concreta sin que nadie pague. |
| `check_borrados.py` | ¿Alguna cuenta borrada conserva un cobro vivo? (pendiente de cron). |
| `check_cripto.py` · `check_oferta.py` | Estado de cripto y de la oferta de bienvenida. |
| `preparar_prueba.py` | Deja una cuenta lista para ensayar una compra. |
| `diagnostico_compra.py` | Qué pasó con una compra concreta. |
| `limpiar_pruebas.py` | Limpia rastros de compras de prueba. |
| `paypal_plan_diario.py` | Plan de ciclo diario para ver una renovación real (solo sandbox). |

## 10. Lo que sigue sin probarse o sin hacer

- 🔴 **Nadie ha visto cancelarse una suscripción ACTIVA de verdad** de punta a
  punta (haría falta una compra real con una cuenta de comprador).
- Cron diario de `check_borrados.py`.
- Selector de mes en el panel de gastos (los de meses anteriores existen pero
  no se ven).
- Subir de plan reinicia el mes sin prorratear: está avisado en el carrito,
  pero si llegan quejas, es aquí.
- Validar con un abogado las Secciones 14/15 de los Términos (foro y ley).
