# CONTEXTO TRADEABLE — LÉEME PRIMERO

> **Qué es esta carpeta.** El expediente completo de **Tradeable Academy**
> (`https://tradeable.academy`): qué es, cómo se construyó, cómo funciona por
> dentro, qué está vivo, qué está apagado, qué falta, qué se decidió y por qué.
> Está escrita para que **otra IA u otro desarrollador** pueda tomar el proyecto
> sin haber estado en ninguna de las conversaciones donde se construyó.
>
> **Foto tomada el 2026-11-15.** Todo lo que diga "hoy" se refiere a esa fecha.
> Rama real del código: `claude/gallant-volta-i7cqmf` (ver punto 1 de abajo).

---

## 🔴 LAS 12 COSAS QUE HAY QUE SABER ANTES DE TOCAR NADA

1. **El código real NO está en `main`.** `main` está congelada en el 2026-05-09
   y contiene solo el bot de trading viejo. Todo Tradeable (≈1.500 commits)
   vive en la rama **`claude/gallant-volta-i7cqmf`** del repo de GitHub
   `gustavoram8/TRADINGBOT2.0`. Quien clone y mire `main` no verá el sitio.
   🔴 **Y nunca se hace push ni merge a `main`:** tiene un workflow de GitHub
   que, al recibir un push, entra al servidor y redespliega el bot viejo
   (doc 19).
2. **El sitio está ABIERTO al público y cobra dinero real** desde el
   2026-08-13. PayPal está en modo LIVE desde el 2026-08-10, con suscripciones
   mensuales que se cobran solas. No hay entorno de pruebas conectado: cualquier
   cambio en pagos corre contra dinero de verdad.
3. **Todo el backend es UN archivo:** `scalpel/app.py` (~18.300 líneas, Flask).
   Y casi toda la interfaz de la app es UNA plantilla: `scalpel/templates/index.html`
   (~31.300 líneas). Es así a propósito del historial, no por diseño ideal.
4. **Producción = un VPS Contabo** (PostgreSQL + gunicorn bajo supervisor +
   nginx + Cloudflare). El proceso de supervisor se llama `traderacelerator`
   (con UNA sola "c": es un typo viejo y se queda así). Sin reiniciar ese
   proceso, lo que se sube a GitHub no se refleja en el sitio.
5. **Los secretos NO viven en el repo.** Viven en la línea `environment=` de la
   config de supervisor y en `scalpel/.env` (ignorado por git). Esta carpeta
   documenta los **nombres** de las variables, nunca sus valores.
   ⚠️ Excepción encontrada al armar este expediente: ver `13_SEGURIDAD.md`
   (hay una contraseña de administrador *por defecto* escrita en el código).
6. **Hay DOS analizadores de gráficos, y no hay que confundirlos:**
   - el **del sitio** (en producción): le manda la captura a GPT-4o con un
     prompt largo. Es el "motor de karting". → `09_ANALIZADOR_DEL_SITIO.md`
   - el **Analizador 2.0** (laboratorio, en `tools/`): una cadena que MIDE las
     velas con píxeles y aritmética y le da a la IA hechos ya verificados. Es
     la "turbina". **No está conectado al sitio.** → carpeta
     `10_ANALIZADOR_2_LABORATORIO/`
7. **El analizador del sitio NO SE TOCA sin permiso explícito del dueño.** Es
   una regla dura. El laboratorio es "backstage" y puede cambiar; producción no.
8. **El sitio es EDUCATIVO, nunca asesoría financiera.** Ni señales, ni
   promesas de ganancia, ni "deberías comprar". Esto gobierna cada texto.
   En la cara pública jamás se nombra "GPT-4o" ni "OpenAI": se dice
   *"our proprietary AI engine"*.
9. **Cuatro idiomas siempre a la par:** inglés, español, francés y portugués.
   Cualquier texto nuevo se escribe en los cuatro o no se sube.
10. **Nada que un usuario haya ganado o comprado se le quita jamás** (camos,
    cosméticos, XP, rango). Es regla del dueño y está en los Términos.
11. **En el mismo VPS vive el bot de trading viejo** (`/opt/tradingbot`),
    apagado pero intacto. **Es del dueño y no se toca ni se borra nunca.**
12. **Las notas de trabajo originales** (`CLAUDE.md`, `CLAUDE_ARCHIVE.md`,
    `LANZAMIENTO.md`, en la raíz del repo) son la fuente cruda de todo esto:
    ~490 KB de bitácora. Esta carpeta las ordena; no las reemplaza. Algunas de
    sus secciones quedaron **desactualizadas** — `15_PENDIENTES.md` dice cuáles.

---

## 🗺️ MAPA DE LA CARPETA

| Archivo | Qué responde |
|---|---|
| `00_LEEME_PRIMERO.md` | Este archivo. |
| `01_QUE_ES_TRADEABLE.md` | Qué es el producto, para quién, qué NO es, nombres. |
| `02_HISTORIA.md` | Cronología de abril a noviembre de 2026. |
| `03_ARQUITECTURA_Y_CODIGO.md` | Con qué está hecho, versiones, cómo está organizado el código. |
| `04_INFRAESTRUCTURA_Y_DEPLOY.md` | Servidor, dominio, correo, cómo se despliega, variables de entorno. |
| `05_BASE_DE_DATOS.md` | Las 57 tablas, y las reglas de migración. |
| `06_RUTAS_Y_ENDPOINTS.md` | Todas las direcciones (URLs) del sitio y qué hace cada una. |
| `07_FUNCIONALIDADES.md` | Cada herramienta del sitio: qué hace, dónde vive, en qué estado está. |
| `08_PLANES_PAGOS_Y_DINERO.md` | Planes, precios, PayPal, suscripciones, cupones, colaboradores, libro de ventas. |
| `09_ANALIZADOR_DEL_SITIO.md` | El analizador que está en producción hoy. |
| `10_ANALIZADOR_2_LABORATORIO/` | **La parte más importante y delicada:** todo el trabajo del analizador nuevo (9 documentos). |
| `11_LEGAL.md` | Términos, privacidad, jurisdicción, reglas de contenido. |
| `12_IDIOMAS_I18N.md` | Cómo funciona la traducción a 4 idiomas. |
| `13_SEGURIDAD.md` | Qué hay, qué falta, y los hallazgos pendientes. |
| `14_PRUEBAS.md` | Las ~86 suites de prueba y cómo correrlas. |
| `15_PENDIENTES.md` | TODO lo que falta, ordenado por urgencia. Y qué notas viejas ya no valen. |
| `16_DECISIONES_DEL_DUENO.md` | Lo que ya se decidió y NO hay que volver a discutir. |
| `17_REGLAS_DE_TRABAJO.md` | Cómo se trabaja en este proyecto (y con el dueño). |
| `18_MARCA_REDES_Y_CONTENIDO.md` | Posicionamiento, estilo visual, redes, creadores. |
| `19_BOT_VIEJO_Y_RAIZ_DEL_REPO.md` | Qué es todo lo demás que hay en el repo. |
| `99_INVENTARIO_DE_ARCHIVOS.md` | Lista generada de cada archivo de Tradeable con su descripción. |
| `anexos/` | **Solo en el ZIP** (en el repo esos archivos ya están en su sitio). Ver abajo. |

### Qué trae `anexos/` dentro del ZIP

| Carpeta | Contenido | Dónde vive en el repo |
|---|---|---|
| `notas_crudas/` | `CLAUDE.md`, `CLAUDE_ARCHIVE.md`, `LANZAMIENTO.md`, guía de copyright — la bitácora original completa (~490 KB) | raíz |
| `codigo_laboratorio/` | Los 22 programas del Analizador 2.0 y sus bancos, + `set_env.py`, el empaquetador y la guía de la prueba de cajas | `tools/` |
| `capturas_prueba/` | Las 7 capturas reales del dueño, sus textos de construcción, `LEEME.md` y `velas.md` | `docs/capturas_prueba/` |
| `columnas/` | Columnas de velas devueltas por Gemini para dos capturas (permiten correr la cadena sin red) | `docs/columnas/` |
| `banco_30_casos/` | Las respuestas del analizador del sitio a los 30 casos sintéticos, en sus 3 pasadas, con informes | `docs/banco_resultados*/` |
| `nginx/` | Las 4 configuraciones del dominio | `deploy/nginx/` |
| `sitio/` | `requirements.txt` del sitio y el dossier del asistente (`assistant_kb.py`) | `scalpel/` |
| `negocio/` | El acuerdo de colaboración | `docs/` |

El ZIP y el inventario se regeneran con `python3 tools/empaqueta_contexto.py`,
que **se niega a crear el ZIP si detecta un correo privado o una llave** dentro.

**Orden de lectura sugerido para alguien nuevo:** 00 → 01 → 03 → 04 → 07 → 08 →
15 → 16 → 17. Y si va a trabajar en el analizador: 09 y luego la carpeta 10
entera, en orden.

---

## 🚦 ESTADO EN UNA PANTALLA (2026-11-15)

| Área | Estado |
|---|---|
| Sitio público `tradeable.academy` | 🟢 Abierto desde 2026-08-13 |
| Registro, login, verificación por correo, 2FA | 🟢 Funcionando |
| Analizador de capturas (producción) | 🟢 Funcionando (GPT-4o, 7 metodologías) |
| Planes Free / Standard $25 / Premium $50 | 🟢 Funcionando |
| Cobro por PayPal (suscripción mensual automática) | 🟢 LIVE |
| Cobro por USDT (NOWPayments) | 🟡 Código listo; depende de claves en el VPS |
| Cobro por Stripe | ⚪ Código listo, apagado (no hay banco en EE. UU.) |
| Planes anuales | ⚪ Apagados a propósito |
| Foro, Quiz, Reto diario, Ruleta, Pre-Flight, Chalkboard, Synapse | 🟢 Funcionando |
| Tienda de cosméticos (camos, placas, cursores) | 🟢 Funcionando (PayPal) |
| Asistente Tessera (chat de ayuda) | 🟢 Funcionando (modelo pequeño) |
| Panel de colaboradores `/partner` + libro de ventas | 🟢 Funcionando |
| Formulario de creadores `/creators` | 🟢 Funcionando |
| Mentorías | ⚪ Construidas y OCULTAS (el mentor no se sumó) |
| Prop Firm Scout, tienda de indicadores | ⚪ Construidos y apagados |
| **Analizador 2.0** | 🔬 En laboratorio. NO conectado al sitio |
| Último trabajo en el repo | 2026-10-12 (laboratorio del analizador) |

**Avisos que alguien tiene que mirar ya** (detalle en `15_PENDIENTES.md`):
- La oferta de bienvenida del 30% no caduca sola y estaba previsto apagarla el
  **12 de octubre de 2026**. No hay constancia de que se apagara.
- El camo de ruleta de **diciembre (Colosseum)** no tiene arte hecho.
- Hay una contraseña de admin por defecto en el código (`13_SEGURIDAD.md`).
- Un push a `main` redesplegaría el bot viejo sobre el servidor (`19_…`).
- El medidor del Analizador 2.0 falla en 3 de las 6 capturas reales (carpeta 10).

---

## 🧭 CÓMO ENTREGAR ESTO A OTRA PERSONA O IA

- **Si le das acceso al repo de GitHub:** dile que cambie a la rama
  `claude/gallant-volta-i7cqmf` y que empiece por esta carpeta. Tendrá el código
  completo y este expediente junto.
- **Si solo le mandas el ZIP:** el ZIP trae esta carpeta + las notas crudas +
  el código del laboratorio + las capturas de prueba. **No trae el código del
  sitio** (`scalpel/`), que pesa ~88 MB con imágenes y modelos 3D: ese se
  entrega por GitHub.
- **Nunca** mandes junto con esto el archivo `scalpel/.env` ni la config de
  supervisor del VPS: ahí están las llaves de PayPal, OpenAI, el correo y la
  base de datos.

## 📏 Convenciones de este expediente

- 🟢 vivo · 🟡 a medias · ⚪ apagado a propósito · 🔴 riesgo o regla dura ·
  🔬 experimental · ⛔ probado y descartado (no reintentar sin motivo nuevo).
- Cuando un dato viene **medido**, se dice con qué se midió. Cuando es algo que
  **no pude verificar** desde fuera del servidor, se marca con "⚠️ sin verificar".
- Los números de línea de `app.py` son de la foto del 2026-11-15; se mueven con
  cada cambio. Sirven para orientarse, no como direcciones fijas.
