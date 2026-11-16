# 06 · RUTAS Y ENDPOINTS

> Lista completa de las direcciones que atiende `scalpel/app.py` (≈230 rutas),
> agrupadas por función. Entre paréntesis, la línea aproximada en `app.py`.
> **Candados:** 🔓 público · 👤 con sesión · 💠 Standard o Premium · 👑 Premium ·
> 🛡️ solo admin · 🤝 colaborador (dueño de un código) · ⚪ función apagada.

## Páginas públicas
| Ruta | Qué es |
|---|---|
| 🔓 `/` (4239) | Portada (landing). Con sesión, lleva a la app. |
| 🔓 `/pricing` (4333) | Planes y precios. |
| 🔓 `/terms` · `/privacy` · `/guide` (6154–6164) | Términos, privacidad, guía de uso. |
| 🔓 `/contact` (7013) | Formulario de contacto/soporte. |
| 🔓 `/socials` (5596) | Redes oficiales + tablero del próximo sorteo. |
| 🔓 `/creators` (6938) | Formulario para creadores de contenido. Sin enlaces desde el sitio, `noindex`. |
| 🔓 `/proyecto` (6800) | Presentación del proyecto para creadores: el enlace que se pega en un mensaje directo de Instagram (que no deja adjuntar PDF). Suelta, `noindex`, fuera de menús y sitemap. |
| 🔓 `/cosmetics` (5818) · `/camos` (5970, redirige) | Tienda de cosméticos. |
| 🔓 `/verify/<code>` · `/v/<code>` · `/verify/<code>/og.png` (16848–16889) | Verificación pública de un certificado de rango + su imagen para redes. |
| 🔓 `/favicon.ico`, `/apple-touch-icon*.png`, `/icon-192.png` (4295) | Iconos en la raíz. |
| 🔓 `/sitemap.xml` (4308) | Mapa del sitio. |
| 🔓 `/health` (18285) | Estado para el monitor (JSON con conteos). |
| ⚪ `/store/indicators` (4360) | Tienda de indicadores (apagada). |

## Cuenta: entrar, registrarse, recuperar
| Ruta | Qué es |
|---|---|
| 🔓 `/register` (7689) | Registro (18+, aceptación de términos, correo canónico). |
| 🔓 `/verify-email` · `/resend-code` (7809–7852) | Código de 6 dígitos por correo. |
| 🔓 `/login` (7354) · `/login/2fa` (7447) | Entrada y segundo factor. |
| 🔓 `/forgot-password` · `/reset-password/<token>` (7889–7919) | Recuperación. |
| 🔓 `/start-free` (7868) | Resto del acceso de invitado: hoy solo redirige a registro. |
| 👤 `/logout` (7874) | Salir. |
| 👤 `/welcome` (4266) | Splash de entrada (deja la cookie que `/app` exige). |
| 👤 **`/app`** (7151) | **La aplicación.** Aquí se paga el XP de login y se disparan los "UNLOCKED". |

## Ajustes de la cuenta
| Ruta | Qué es |
|---|---|
| 👤 `/settings` (6169) | "Mi cuenta". |
| 👤 `/account/password` · `/account/sessions/close` (6177–6199) | Cambiar contraseña; cerrar las demás sesiones. |
| 👤 `/account/2fa/start` · `/confirm` · `/disable` (6226–6268) | Segundo factor (TOTP). |
| 👤 `/account/email` · `/confirm` · `/cancel` (6304–6374) | Cambio de correo con código. |
| 👤 `/account/cancel-plan` (6646) | **Darse de baja** (corta la renovación en PayPal). |
| 👤 `/account/switch-plan` · `/return/<id>` · `/cancel` (6696–6746) | Bajar de plan (programado). |
| 👤 `/account/reactivate-plan` (6769) | Lleva a `/pricing` (PayPal no "descancela"). |
| 👤 `/account/delete` (6543) | Borrar cuenta (exige baja previa). |
| 👤 `/api/fingerprint` (15222) | Registra la huella del navegador. |

## El analizador
| Ruta | Qué es |
|---|---|
| 👤 `/api/usage` (13260) | Cuántos análisis quedan; también informa el plan (lo usa el vigilante de cambio de plan). |
| 👤 **`/validate`** (13293) | Pre-chequeo: ¿la captura tiene marcadas entrada y salida? |
| 👤 **`/analyze`** (13338) | **El análisis.** Límite por plan → GPT-4o → guarda uso, costo y XP. |
| 👤 `/api/projects` GET/POST · `/<pid>` PUT/DELETE (16944–16998) | Proyectos del analizador. |

## Pagos y compras
| Ruta | Qué es |
|---|---|
| 👤 `/checkout` (10758) | Carrito del plan. |
| 👤 `/api/checkout/validate-code` (10841) | Validar un cupón. |
| 👤 `/checkout/create` (10908) | Crea el pedido y manda a la pasarela. |
| 👤 `/checkout/pay/<id>` (11103) | Elegir método cuando hay más de uno. |
| 👤 `/checkout/paypal/return/<id>` (11128) | Vuelta de PayPal (pago suelto): captura. |
| 👤 `/checkout/paypal/subscription/<id>` (11147) | Vuelta de PayPal (suscripción). |
| 👤 `/checkout/status/<id>` · `/api/checkout/status/<id>` (11520–11543) | Estado del pedido (reconcilia al abrirse). |
| 👤 `/api/checkout/txid/<id>` (11557) | Pegar el hash de una transferencia cripto. |
| 👤 `/checkout/cancel/<id>` (11712) | Cancelar un pedido pendiente. |
| 👤 `/checkout/success` (11575) | Vuelta de Stripe (apagado). |
| 🔓 **`/webhook/paypal`** (11277) | Avisos de PayPal (verificados contra su API). Por aquí llegan las renovaciones. |
| 🔓 `/webhook/crypto` (11456) | Avisos de NOWPayments (firma HMAC-SHA512). |
| 🔓 `/webhook/stripe` (11609) | Avisos de Stripe (apagado). |
| 👤 `/api/camo/buy` · `/camos/paypal/return/<id>` (6030–6066) | Comprar un camo suelto. |
| 👤 `/api/cosmetics/checkout` · `/cosmetics/paypal/return/<id>` (6088–6135) | Carrito de cosméticos. |
| 👤 `/api/camo/activate` · `/deactivate` · `/api/cosmetics/equip` (5977–6000) | Ponerse/quitarse camo, placa o cursor. |
| 👑 `/api/synapse/pdf/buy` · `/synapse/pdf/paypal/return/<id>` (13018–13055) | Comprar el PDF de Synapse. |
| 👤 `/synapse/pdf/ready` · `/synapse/pdf/mine` · `/synapse-pdf/<token>` (13074–12900) | Descargar el PDF comprado. |

## Foro (💠 Standard y Premium)
`/forum/feed` (14135) · `/forum/post/<pid>` · `/forum/post` POST (⚠️ recibe
`form`, no JSON) · `/forum/post/<pid>/comment` · `/forum/react` · `/forum/save`
· `/forum/post/<pid>/delete` · `/forum/comment/<cid>/delete` ·
`/forum/communities` GET/POST · `/forum/community/<cid>/membership` ·
`/delete` · `/requests` · `/invite` · `/forum/follow` · `/forum/dm/threads` ·
`/forum/dm/with/<username>` (13863–14430).

## Herramientas Premium (👑)
| Ruta | Qué es |
|---|---|
| `/api/preflight/checklists` (+ `/<cid>`) · `/api/preflight/checks` (+ `/<cid>`) (17134–17349) | Pre-Flight. |
| `/api/quiz/answer` (16369) · `/api/quiz/progress` · `/complete` · `/certified` (15313–15392) | Quiz (el servidor juzga la respuesta). |
| `/api/daily/status` · `/start` · `/answer` · `/leaderboard` · `/tanda` · `/spin` (16042–16207) | Reto Diario, ranking, tanda del mes y ruleta. |
| `/api/daily/coupons` (16273) | "Mis cupones" (👤, sin filtro de plan). |
| `/api/chalk/boards` GET/POST · `/<bid>` GET/DELETE · `/<bid>/rename` (15143–15207) | Biblioteca del Chalkboard. |
| `/api/synapse/topics` · `/progress` · `/toggle` (15249–15281) · `/api/synapse/l10n/<lang>` (12437) | Synapse. |

## Rangos, reseñas, asistente, reportes
| Ruta | Qué es |
|---|---|
| 👤 `/api/rank/progress` · `/api/rank/celebrated` (16436–16456) | Progreso de XP y sello del aviso de subida. |
| 👤 `/certificate/<rank>` · `/certificate/<rank>/pdf` (16791–16814) | Certificado de rango. |
| 👤 `/api/testimonial/submit` (16302) · 🔓 `/api/testimonials` (16347) | Reseñas. |
| 👤 `/review` (7138) | El enlace "deja tu reseña" del correo del recibo: guarda la intención en la sesión y lleva a `/app`. |
| 👤 `/api/assistant/ask` (13203) | Chat de Tessera. |
| 👤 `/api/bug/report` (7068) | Reportar un bug. |

## Colaboradores
| Ruta | Qué es |
|---|---|
| 🤝 `/partner` (11769) | Panel del colaborador (el admin ve todos). Quien no tiene código recibe 404. |
| 🤝 `/partner/wallet` (11864) | El colaborador registra su billetera USDT. |

## Administración (🛡️)
| Ruta | Qué es |
|---|---|
| `/admin` (8088) | Panel: Usuarios, Ingresos, Moderación, Gasto de IA, Auditoría, Bugs, 📒 Ventas, ⭐ Reseñas. Al abrirse hace el barrido de pagos. |
| `/admin/trace` (8195) | Traza de una cuenta/pedido (prueba de entrega ante disputas). |
| `/admin/set-plan` (12039) | Poner un plan a mano (30 días). |
| `/admin/order/mark-paid` · `/order/cancel` (11676–11695) | Acciones sobre pedidos. |
| `/admin/promo/create` · `/toggle` · `/delete` · `/owner` (11892–11991) | Cupones. ⚠️ No borrar un código de creador con clientes: desactivar. |
| `/admin/ledger/manual` · `/reverse` · `/delete` · `/pay-commissions` (5614–5713) | Libro de ventas. |
| `/admin/expense/add` · `/delete` (12004–12027) | Gastos. |
| `/admin/ai-credit/set` (11658) | Anotar saldo de IA. |
| `/admin/review/toggle` (5739) | Publicar/retirar una reseña. |
| `/admin/giveaway` (5785) | Sorteo de `/socials`. |
| `/admin/ban/confirm` · `/dismiss` · `/admin/unban` (12210–12256) | Baneos (siempre confirmados a mano). |
| `/admin/user/recompute-rank` (12122) | Recalcular rango. |
| `/admin/demo/set` · `/clear` (12138–12199) | Modo demo: ver el sitio como otro plan o "viajar" a otro mes de temporada. |
| `/admin/device-preview` · `/admin/preview/checkout` · `/success` · `/order` (8216–8277) | Vistas previas. |
| `/admin/bug/update` (7117) · `/admin/whatsapp/test` (5762) | Bugs; probar WhatsApp. |
| `/admin/synapse-pdf/issue` (12866) · `/synapse/pdf/admin-download` (12946) | Emitir/descargar el PDF. |

## Mentorías (⚪ ocultas: 404 para todos menos admin)
`/improve` · `/improve/mindset` · `/gap` · `/inside` · `/apply` · `/plans`
(4379–4543) · `/api/improve/apply` (5432) · `/mentorship/checkout` · `/create`
· `/success` (5242–5327) · `/mentorship/area` (4701) · `/api/ment/*` (≈30
rutas, 4711–5230: resumen, carpetas, videos, comentarios, notas, adjuntos,
progreso, preguntas, canales, mensajes, reacciones, y el panel del mentor).

## Prop Firm Scout (⚪ apagado)
`/api/scout/firms` (14830) · `/api/scout/chat` (14907).

---

### Notas para quien llame a estas rutas
- Casi todas las `/api/*` reciben y devuelven JSON. Excepciones conocidas:
  `/forum/post`, `/analyze` y `/validate` reciben formulario multipart.
- Los errores vienen como `{"error": "<código>"}` con un código corto que el
  cliente traduce (por ejemplo `limit_reached`, `premium_only`, `not_a_member`,
  `recipient_locked`, `rate`).
- Con el candado de vista previa activo, las `/api/*` responden 503
  `coming_soon`; los webhooks y `/health` siguen pasando.
