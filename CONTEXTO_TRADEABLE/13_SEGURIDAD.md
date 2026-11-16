# 13 · SEGURIDAD

> Este documento **no contiene ningún secreto**. Señala dónde están y qué
> riesgos hay, sin repetir valores.

## 🔴 Hallazgos que alguien debe mirar (encontrados al armar el expediente)

### H1. Hay una contraseña de administrador por defecto escrita en el código
- **Dónde:** `scalpel/app.py`, función `init_db()` (línea ~18259): si la
  variable `ADMIN_PASSWORD` no existe, la cuenta admin se crea con un valor
  fijo que está en el archivo (y por tanto en GitHub y en su historial).
- **Cuándo importa:** solo al **crear** la cuenta admin por primera vez (si ya
  existe una cuenta con el correo de avisos, no se toca).
- **Riesgo real:** si la cuenta admin de producción se creó sin esa variable y
  **nunca se le cambió la contraseña**, cualquiera con acceso al repo conoce la
  contraseña del administrador.
- **Qué hacer:** (1) confirmar que la contraseña del admin (`maurotradesve`) se
  cambió desde Ajustes y activar 2FA en esa cuenta; (2) quitar el valor por
  defecto del código (que falle o genere una al azar si falta la variable);
  (3) tener presente que el valor viejo sigue en el historial de git.
- ⚠️ Esto matiza la nota vieja de que "los secretos no están en GitHub".

### H2. El correo personal del dueño está escrito en cuatro archivos del repo
`scalpel/app.py` (valor por defecto del remitente), `scalpel/.env.example`,
`daily_audit_summary.py` y `tools/check_mail.py`. No es una llave, pero es un
dato personal en el repo. Convendría cambiarlo por la dirección del dominio.
(En `CLAUDE_ARCHIVE.md` ya se quitó.)

### H3. Un número de teléfono de ejemplo en un comentario
`scalpel/app.py`, junto a `WA_PHONE`. Verificar que no sea un número real.

### H4. No hay límite de intentos de contraseña en `/login`
Leyendo la ruta no aparece ningún freno a probar contraseñas una tras otra
(sí lo hay en el segundo factor: 5 intentos; y en "olvidé mi contraseña": 5 por
hora, pero guardado en la sesión, o sea que se evita borrando cookies).
Recomendado: límite por cuenta y por IP en el servidor.

### H5. No hay protección CSRF con token
No se usa Flask-WTF ni tokens. La defensa actual es la cookie `SameSite=Lax`
(con `PUBLIC_HTTPS=1`). Suficiente para lo básico; un endurecimiento pendiente.

### H6. Las copias de seguridad viven en el mismo servidor
Si el VPS se pierde, se pierden la base y sus copias.

---

## El incidente del 13 de agosto de 2026

- Se pegaron en el chat de trabajo, en texto plano, **todos** los secretos de
  la línea `environment=` de supervisor: secreto LIVE de PayPal, `SECRET_KEY`
  de Flask, clave de OpenAI, token de GitHub, contraseña del correo,
  NOWPayments y PostgreSQL. Causa: un `grep` sobre esa línea.
- **Alcance:** la única copia fuera del VPS es el historial de aquella
  conversación, que no es pública.
- **Decisión del dueño: NO rotarlos; asume el riesgo.** Textual: *"si es ese el
  riesgo yo lo asumo"*. 🔴 **No volver a insistirle**, salvo que él pregunte o
  aparezca una señal real (cargo raro en PayPal, gasto de OpenAI que no cuadra,
  sesión de admin que él no abrió).
- **Si algún día decide rotar**, el orden es: (1) secreto de PayPal; (2)
  `SECRET_KEY` (con ella se falsifican sesiones de cualquiera, admin incluido;
  rotarla cierra todas las sesiones); (3) OpenAI; (4) token de GitHub;
  (5) correo; (6) NOWPayments; (7) PostgreSQL. Cada una con `tools/set_env.py`
  + `supervisorctl reread && supervisorctl update`. **Los valores nuevos, nunca
  al chat.**
- El único argumento que sigue siendo cierto: el riesgo no crece con el tiempo;
  **crece el precio de arreglarlo** (más clientes con sesión abierta).

## Dónde viven los secretos

| Lugar | Qué |
|---|---|
| `/etc/supervisor/conf.d/*trader*.conf`, línea `environment=` | **La fuente real en producción** |
| `/var/www/TRADINGBOT2.0/scalpel/.env` | Copia para las herramientas (ignorado por git) |
| `scalpel/.secret_key` | `SECRET_KEY` generada si no hay variable (ignorado por git) |
| Config de nginx de vista previa | El "pase" (no está en el repo) |
| Paneles de PayPal, OpenAI, Cloudflare, NOWPayments, Google | Las cuentas en sí |

**Reglas de manejo:**
- nunca un secreto en el chat ni en el repo;
- nunca `grep`/`cat` sobre la línea `environment=`;
- cambiar variables con `tools/set_env.py` (no imprime valores, hace copia);
- las herramientas de `tools/` informan "puesta / falta", nunca el valor.

---

## Lo que SÍ está hecho

### Cuentas
- Contraseñas con hash (Werkzeug). Rechazo de contraseñas débiles (lista común
  + no contener usuario o correo) en registro, cambio y recuperación.
- Verificación de correo obligatoria (código de 6 dígitos, 15 min).
- **2FA TOTP opcional** (compatible con apps estándar), 8 códigos de respaldo
  de un solo uso guardados con hash; quitarlo exige contraseña y código.
- **Cerrar las demás sesiones** y revocación al cambiar o recuperar contraseña,
  rotando `alt_id`.
- **Aviso por correo de dispositivo nuevo** (el primero se registra en silencio).
- Cambio de correo confirmado con código enviado al buzón nuevo.
- Un buzón = una cuenta (correo canónico contra alias de Gmail).
- Baneos siempre confirmados por un admin; huella de navegador contra evasión.
- Fecha de nacimiento (18+). Sin documentos de identidad, a propósito.

### Aplicación
- Cabeceras: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy`, `Permissions-Policy`.
- Con `PUBLIC_HTTPS=1`: cookies `Secure`, `HttpOnly`, `SameSite=Lax`; ProxyFix
  de un solo salto; la IP del cliente ya no se toma de una cabecera falsificable.
- **Permisos decididos en el servidor en cada petición** (el navegador solo pinta).
- **Precios siempre del servidor.**
- Webhooks verificados (PayPal contra su API; cripto con HMAC-SHA512).
- Todo el contenido de usuarios se pinta como texto (anti-XSS); el análisis de
  la IA pasa por DOMPurify.
- Respuestas del quiz y del reto diario solo en el servidor; el banco diario
  nunca se envía al navegador.
- Topes de tamaño: subida 20 MB, imagen 8.000 px, notas 2.000 caracteres,
  pizarra 2 MB.
- Límites: análisis por plan, asistente 25/hora y 80/día, foro 2 posts/día,
  mensajes 30/min, creadores 3 por IP/día, descargas del PDF 5 cada 10 min.
- Cerrado el acceso de invitado que permitía análisis ilimitados con una
  cookie inventada (`test_seguridad.py`).
- Registro de auditoría (`AuditEvent`) con resumen diario por correo.
- `noindex` y fuera del sitemap para páginas internas.
- Enlaces absolutos construidos desde `SITE_URL`, no desde el Host.

### Operación
- Reciclaje de workers; monitor horario; avisos por WhatsApp con cortafuegos
  contra inundación.
- Candado de emergencia (`PREVIEW_USERS`).

---

## Lo que FALTA (por prioridad)

| # | Pendiente | Nota |
|---|---|---|
| 1 | **H1: contraseña admin por defecto** | Verificar y quitar |
| 2 | **Cerrar el puerto 5001 al exterior** | El sitio se alcanza saltándose Cloudflare, sin HTTPS, por IP |
| 3 | **Límite de intentos en `/login`** (H4) | |
| 4 | **Antiflood por IP en `/register`** | Acordado como pendiente antes de lanzar; protege la reputación del correo |
| 5 | **IP real tras Cloudflare** (`CF-Connecting-IP` en nginx) | Hoy los límites por IP ven la IP de Cloudflare |
| 6 | **Copias de seguridad fuera del VPS** (H6) | |
| 7 | **HSTS** | Ya se puede: el dominio sirve por HTTPS |
| 8 | **CSP** | Trabajo aparte: la app usa scripts en línea por todas partes |
| 9 | **CSRF con token** (H5) | |
| 10 | Cron de `check_borrados.py` | Vigila cobros vivos en cuentas borradas |
| 11 | Activar Sentry (`SENTRY_DSN`) | Instalado e inactivo |
| 12 | Sacar el correo personal del código (H2) | |
| 13 | Prueba de carga con usuarios reales | |
| 14 | Rotar secretos | **Decisión del dueño: no.** No insistir |

## Comprobaciones

```bash
python3 tools/test_seguridad.py     # candado del analizador + cabeceras
python3 tools/test_cuenta.py        # contraseña, sesiones, borrado
python3 tools/test_preview_lock.py  # candado de vista previa
python3 tools/simula_foro.py        # 65 reglas del foro atacadas por HTTP
python3 tools/simula_xp.py          # 36 defensas contra farmeo de XP
```
⚠️ Varias pruebas viejas llevan rutas absolutas del entorno donde se
escribieron (`/home/user/TRADINGBOT2.0/...`): ajustarlas si se corren en otro sitio.
