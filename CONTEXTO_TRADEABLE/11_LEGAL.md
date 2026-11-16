# 11 · LEGAL Y REGLAS DE CONTENIDO

> ⚠️ Esto resume cómo quedó armado lo legal del sitio. **No es asesoría
> jurídica.** Varias piezas están pendientes de validar con un abogado.

## El principio que gobierna todo

**El sitio es educativo e informativo. Nunca es asesoría financiera, ni
recomendación, ni señal, ni promesa de ganancia.** Aplica a cada texto, a cada
respuesta de la IA, a cada publicación en redes.

Prohibido en cualquier superficie:
- decir "compra", "vende", "entra ahora";
- afirmar que un precio "va a" subir o bajar;
- prometer o insinuar rentabilidad o tasas de acierto del alumno;
- hablar en absolutos ("siempre funciona", "la mejor estrategia").

En la cara pública **no se nombra "GPT-4o" ni "OpenAI"**: se dice
*"our proprietary AI engine"*.

## Quién es el vendedor

- **Negocio independiente de un operador individual**, con sede en
  **Venezuela**. No hay empresa constituida (la "LLC" prevista dependía del
  socio que no se sumó).
- Los Términos incluyen un **mecanismo de cesión futura** a una sociedad del
  mismo negocio, por si algún día se constituye.
- El cobro lo recibe una cuenta de PayPal a nombre de un tercero (familiar);
  los Términos lo cubren en el párrafo "Quién recibe el pago".
- Nombres comerciales definidos en la Sección 1: **Tradeable Academy**
  (oficial) y **Tradeable**. "Trader Accelerator" fue eliminado.

## Documentos legales del sitio

| Documento | Dónde | Idiomas |
|---|---|---|
| Términos y Condiciones | `scalpel/templates/terms.html` (inglés) + `static/legal_i18n.js` (ES/FR/PT) | 4 |
| Política de Privacidad | `scalpel/templates/privacy.html` + `legal_i18n.js` | 4 |
| Acuerdo de Colaboración (para creadores) | `docs/acuerdo_colaboracion.md` → PDF con `tools/build_acuerdo_pdf.py` | Español |

- **Versión de los Términos:** `TERMS_VERSION = "2026-06-05"` en `app.py`. Cada
  cuenta guarda **cuándo** aceptó y **qué versión** (evidencia del clickwrap).
  ⚠️ Los Términos se han reescrito varias veces desde junio y la constante no
  se ha subido: revisar si corresponde actualizarla.
- **Contacto publicado:** `support@tradeable.academy`.

### 🔴 Regla al tocar cualquier texto legal
```bash
python3 tools/audit_legal_translations.py
```
Compara cláusula por cláusula el inglés contra ES/FR/PT (números, plazos,
montos y tamaño). Importa porque los Términos dicen que, si la ley del
comprador exige su idioma, **manda su idioma**: un error de traducción en una
cláusula de dinero es exigible. Última auditoría: 144 cláusulas correctas.

## Las secciones de los Términos que más se han trabajado

| Sección | Contenido clave |
|---|---|
| **1** | Quién es el operador; nombres comerciales; cesión futura. |
| **5 — Planes, pagos y facturación** | Métodos (PayPal/tarjeta y USDT); quién recibe el pago; **renovación automática mensual**; baja sin costo ni preaviso; período empezado no reembolsable; reintentos de cobro; **un solo plan a la vez**; subir es inmediato, bajar se programa; anual y USDT no son recurrentes; contracargo por un plan entregado = incumplimiento; **cosméticos** (camos, marcos, cursores): ventanas festivas, rotación mensual, piezas solo-ruleta, y que **lo comprado y lo ganado no se revoca**; remite a "los ciclos ofrecidos al finalizar la compra". |
| **6 — Ruleta y premios** | Premios cosméticos, rotación, el premio entregado se queda. Se conserva el párrafo de códigos de descuento (los códigos viejos y los de colaboradores siguen vivos). |
| **7** | Excepciones; referencia a mentoría (condicional). |
| **11** | Calendario económico y datos de terceros: informativos. |
| **12** | Limitación de responsabilidad. |
| **14 — Disputas** | Arreglo informal 30 días → **tribunales de Venezuela**; reclamos individuales; se respetan los derechos irrenunciables del consumidor en su país. |
| **15 — Ley aplicable** | **República Bolivariana de Venezuela**, con la misma salvedad. |
| **19 — Sorteos** | Sin compra, 18+, excluye al operador y familia, sorteo manual, premios personales, sin afiliación con redes sociales. |
| **20 — Mentoría** | Solo se muestra con `MENTORSHIP_ENABLED=1`. |

## Privacidad (puntos declarados)

Fecha de nacimiento, secreto de 2FA, cookie de dispositivo conocido, huella de
navegador (anti-evasión de baneos), datos de pago **gestionados por terceros**
(el sitio nunca ve datos de tarjeta), terceros: PayPal, plataforma cripto,
proveedor de IA, correo.

## Reglas que vienen de leyes concretas

| Regla | Origen | Cómo se cumple |
|---|---|---|
| **Reseñas solo de usuarios reales**; la del fundador, etiquetada | FTC (16 CFR 465), EE. UU. | Solo cuentas reales; columna `insider`; etiqueta visible; nota de cómo se recogen. |
| **Mayores de 18** | Varias | Fecha de nacimiento + casilla. **No** se piden documentos (decisión: no convertirse en custodio de datos sensibles). |
| **Sorteos** | Regulación de loterías | Sin compra + reglamento en la Sección 19. |
| **Atribución de modelos 3D** | Licencia CC BY | Crédito visible con enlaces dentro de Synapse y en el pie. |
| **Baja antes del borrado; no cobrar a quien se dio de baja** | Protección al consumidor | Reglas de pago del doc 08. |
| **OFAC** | Sanciones de EE. UU. | El Scout (apagado) tenía lista de países. ⚠️ Sin un control general de país en el registro. |

## Qué decide una disputa de pago

- Un contracargo **nunca** quita el plan automáticamente: avisa al dueño.
- La prueba de entrega es `/admin/trace` (accesos, análisis hechos, fechas).
- Ventana de disputa de PayPal: **180 días**.

## Pendientes legales

| Pendiente | Urgencia |
|---|---|
| **Validar con abogado las Secciones 14 y 15** (elección de foro y ley venezolana para clientes de EE. UU./Europa) | Alta |
| **Punto 7 de la checklist del dueño:** ¿qué valor legal tiene el acuerdo de colaboración sin empresa constituida y con el creador en otro país? | Abierto |
| Rellenar los 6 huecos del acuerdo y decidir el preaviso de terminación (hoy 15 días) | Media |
| **Registrar el copyright** (copyright.gov, ~$135–260). Guía: `COPYRIGHT_REGISTRATION_GUIDE.md`. Lo ideal era antes de publicar o dentro de los 3 meses siguientes al lanzamiento (13-ago → **venció hacia el 13-nov-2026**) | Alta |
| Revisar la Sección 5 si algún día se enciende Stripe | Condicional |
| Corregir la Sección 20 al conectar el video de mentorías (promete "solo streaming") | Condicional |
| Si el Analizador 2.0 muestra "acierta X%": revisar que no suene a predicción | Futuro |

## Documentos de revisión guardados en la raíz del repo

`LEGAL_REVIEW_Terms_and_Conditions.md`, `LEGAL_REVIEW_Privacy_Policy.md`,
`CHATGPT_TC_FULL_REVIEW.md`, `CHATGPT_TC_REVIEW_ROUND2.md`,
`legal_terms_review.html`, `legal_privacy_review.html` (revisiones de junio–
julio) y los PDF `Trader_Acelerator_Terms_and_Conditions.pdf` /
`…Privacy_Policy.pdf`, que son **versiones viejas**: los vigentes son las
plantillas del sitio.
