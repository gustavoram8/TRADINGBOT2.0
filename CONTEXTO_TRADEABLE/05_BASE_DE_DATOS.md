# 05 · BASE DE DATOS

- **Producción:** PostgreSQL (en el mismo VPS). **Local:** SQLite.
- **Dónde se definen las tablas:** todas en `scalpel/app.py`, como clases
  `db.Model` (líneas ~833–2200, más tres al final: `QuizProgress`,
  `SynapseProgress`, `ChalkBoard`).
- **No hay herramienta de migraciones** (ni Alembic ni similar). El esquema se
  mantiene con `db.create_all()` (crea tablas nuevas) + funciones propias
  `_migrate_*()` que añaden columnas a tablas existentes.

## Las 57 tablas, por familia

### Cuentas y seguridad
| Modelo | Qué guarda |
|---|---|
| **`User`** | La cuenta. Campos clave abajo. |
| `KnownDevice` | Dispositivos ya vistos por cuenta (para el aviso "dispositivo nuevo"). |
| `BrowserFingerprint` | Huella de navegador por cuenta (anti-evasión de baneos). |
| `BannedFingerprint` | Huellas vetadas. |
| `AuditEvent` | Registro de auditoría (logins, pagos, cambios, errores). |
| `BugReport` | Reportes de bugs enviados desde la app. |

**`User`, lo importante:** `username`, `email`, `email_canonical` (anti-alias
de Gmail), `password_hash`, `plan` (free/standard/premium), `is_admin`,
`plan_cycle`, `plan_started_at`, `plan_expires_at`, `cancel_at_period_end`,
verificación de correo (código de 6 dígitos), `is_banned`, `muted_until`,
`terms_accepted_at` + `terms_version` (evidencia del clickwrap), **`alt_id`**
(identificador aleatorio para las cookies de sesión; rotarlo cierra todas las
sesiones), `birth_date` (18+), 2FA (`totp_secret`, `totp_confirmed_at`,
`totp_backup`), cambio de correo pendiente, `deleted_at`, **`referred_by_code`**
(a qué colaborador pertenece el cliente, se fija una vez y para siempre),
`xp`, `rank`, `rank_celebrated`, `active_camo`, `owned_camos` (JSON),
`active_frame`, `active_cursor`, y datos de colaborador (`partner_wallet`,
`partner_wallet_net`, `partner_since`).

### Analizador e IA
| Modelo | Qué guarda |
|---|---|
| `UsageLog` | Una fila por análisis hecho (de aquí sale el límite por plan). |
| `AICostLog` | Costo y tokens de cada llamada a la IA (analyze / validate / assistant / moderación). |
| `AICreditCheckpoint` | Saldo de crédito de IA anotado a mano por el admin. |
| `AnalysisProject` | Proyectos/carpetas del analizador. |

### Pre-Flight
`PreflightChecklist` (la checklist de confluencias de una estrategia) ·
`PreflightCheck` (cada trade evaluado: veredicto go/caution/no-go, resultado, R).

### Foro
`ForumPost` · `ForumComment` · `ForumReaction` · `SavedPost` ·
`ForumCommunity` · `ForumCommunityMember` (con `status` pending/member) ·
`ForumFollow` · `ForumDM` · `ModWarning` (advertencias de moderación) ·
`BanSuggestion` (sugerencia de baneo que **un admin** confirma; nunca automático).

### Pagos y dinero
| Modelo | Qué guarda |
|---|---|
| **`Order`** | **Un cobro** de plan (pendiente/pagado/cancelado, método, referencia de la pasarela, cupón, `celebrated_at`, `is_test`). |
| **`PlanSubscription`** | **El permiso** de cobro recurrente en PayPal (id de suscripción, estado, próximo cobro, cambio de plan pendiente). |
| `PromoCode` | Cupones: generales, de creador (con `owner_user_id`) y personales (`restrict_user_id`). |
| **`SaleBreakdown`** | **El libro de ventas:** una fila congelada por venta (bruto → descuento → comisión del colaborador → comisión de la pasarela → costo → reserva → utilidad). |
| `Expense` | Gastos anotados a mano en `/admin`. |
| `CamoOrder` · `CosmeticOrder` | Compras de camos sueltos y carritos de cosméticos. |
| `SynapseOrder` · `SynapseDownloadToken` | Compra del PDF de Synapse y sus enlaces de descarga. |
| `MentorshipOrder` | Compras de mentoría (aisladas de los planes; función oculta). |

### Gamificación y cosméticos
| Modelo | Qué guarda |
|---|---|
| `XPLog` | Libro de XP: cada punto ganado, con su fuente (solo se añade, nunca se resta). |
| `RankCertificate` | Certificados de rango emitidos (código verificable público). |
| `QuizProgress` · `SynapseProgress` | Avance por usuario. |
| `DailyQuizState` · `DailyAnswerLog` | Estado y respuestas del Reto Diario (racha, tiempos, ranking). |
| `RouletteSpin` | Cada giro de la ruleta y su premio. |
| `CosmeticItem` | Catálogo de piezas (slug, tipo, **canal**: ruleta / tienda / campeón, temporada). |
| `UserCosmetic` | Qué piezas tiene cada usuario (libro; nunca se borra). |
| `Testimonial` | Reseñas (con `insider` para etiquetar al fundador, regla FTC). |
| `Giveaway` | Sorteos mostrados en `/socials` (el sorteo real es manual). |

### Mentorías (función oculta)
`MentorshipApplication` · `MentorshipFolder` · `MentorshipVideo` ·
`MentorshipVideoComment` · `MentorshipNote` · `MentorshipAttachment` ·
`MentorshipQuestion` · `MentorshipChannel` · `MentorshipMessage` ·
`MentorshipMsgReaction` · `MentorshipProgress` · `MentorshipLiveState`.

### Varios
`ChalkBoard` (pizarras guardadas en el servidor) · `CreatorApplication`
(solicitudes de `/creators`; redes en un campo JSON) · `PropFirm` (catálogo del
Scout, apagado).

## 🔴 Reglas de migración (cada una costó una caída de producción)

1. **Ninguna migración puede usar el ORM.** El ORM pide TODAS las columnas del
   modelo; una migración corre justo cuando la base aún no las tiene. Usar SQL
   crudo que toque solo las columnas necesarias. (Caída del 2026-08-02: los 4
   workers morían al arrancar con `UndefinedColumn`.)
2. **Las migraciones de la tabla `user` van todas juntas y ARRIBA** en
   `init_db()`, antes de `_migrate_user_alt_id_column()`.
3. **Probar toda columna nueva con `tools/test_boot_migracion.py`**, que borra
   las columnas de una base ya creada y vuelve a arrancar. Probar contra una
   SQLite recién creada **no prueba nada** de un deploy.
4. **`user` y `order` son palabras reservadas en PostgreSQL:** en SQL crudo van
   entre comillas dobles (`"user"`, `"order"`).
5. **Secuencias de id:** tras importar filas con id explícito, PostgreSQL no
   avanza el contador y el siguiente INSERT choca. `_resync_postgres_sequences()`
   lo repara en cada arranque. Verificar con `tools/check_pg_sequences.sql`.
6. **Borrar algo con hijos revienta en PostgreSQL** (clave ajena) y SQLite lo
   deja pasar en silencio. Por eso publicaciones, comunidades y cuentas se
   **vacían** en vez de borrarse. Las pruebas de borrado corren con
   `PRAGMA foreign_keys=ON` para que SQLite se porte como PostgreSQL.
7. **Columnas nuevas con backfill solo cuando corresponde.** Inventar datos
   para filas viejas (una fecha de nacimiento, una reserva que nunca existió)
   es peor que dejarlas vacías.
8. **Índices únicos sobre datos viejos:** no. Un índice único que choque con
   filas existentes tumba el arranque (`email_canonical` no es único por eso).

## Orden real de `init_db()` (foto 2026-11-15)

`create_all` → migraciones de `user` (verificación, reseña, XP, mute, camos,
cosméticos puestos, colaborador, seguridad, referidos, correo canónico, cuenta)
→ `alt_id` → `order`, `promo_code`, `preflight_check`, reserva de ventas,
cambio de plan pendiente, estado de miembro del foro, `is_test` de pedidos y
cosméticos, `insider` de testimonios, mejor racha, mentorías, comunidad del
post → **resincronizar secuencias** → rellenar camos de plan → publicar marcos,
cursores y camos de ruleta en el catálogo → sincronizar nombres → crear la
cuenta admin si no existe → datos del Scout.

## Fechas

Todas las columnas de fecha son `DateTime` **sin zona**, y el código guarda
siempre `datetime.now(timezone.utc)`. Como el VPS está en hora de Berlín, la
sesión de PostgreSQL se abre con `-c timezone=utc`; sin eso cada fecha se
guardaba con 2 horas de más. Prueba: `tools/test_horas_pg.py` (necesita un
PostgreSQL real).

## Copias de seguridad

`backup_db.py` (cron 07:30): `pg_dump` diario, conserva 14 días, en una carpeta
`backups/` del VPS (ignorada por git). ⚠️ **No consta copia fuera del VPS**: si
el servidor se pierde, se pierden base y copias a la vez. Recomendado sacarlas.

## Migración histórica

`migrate_to_postgres.py` (raíz) es el script con el que se pasó de SQLite a
PostgreSQL en junio de 2026. Ya cumplió; se conserva como referencia.
