# 18 · MARCA, REDES Y CONTENIDO

## La idea que manda

Ver `01_QUE_ES_TRADEABLE.md`: **ecosistema educativo; el analizador cubre al
mentor cuando no está; el trader de las 3 AM.** Todo contenido debe poder
responder *"¿esto de qué le sirve al tipo de las 3 AM?"*. Y nunca: señales,
promesas, "somos tu mentor".

**Listón visual:** *"que parezca la casa de Elon Musk… que al verla digan «qué
locura es esta»"*. No "correcto y limpio": **que pare el scroll.** El dueño
manda referencias de artes que le gustan; se calibra con ellas antes de producir.

## Identidad

| Elemento | Valor |
|---|---|
| Nombre | **Tradeable Academy** (corto: Tradeable) |
| Dominio | `tradeable.academy` |
| Azul de marca | **`#004feb`** |
| Avatar / icono | La **"a"** del logotipo sobre el azul (no el logotipo entero: a 16 px es una mancha) |
| Logotipo | `scalpel/static/logo.png` (con caja blanca horneada) y **`logo_t.png`** (transparente; es el que se usa). En correos: `logo_t.png` sobre fondo blanco fijo |
| Tipografías del sitio | Inter (texto), Space Grotesk (títulos), JetBrains Mono (números/HUD), Orbitron (Tessera) |
| Tema por defecto | Claro; hay oscuro y camos |
| Mascota | La "botarga" (cambia de disfraz con cada camo) |
| Tessera | Teseracto **rubí** (`#e0244a` / `#ff5c78`) |
| Estética de Mentorías y Kill Zones | Grafito + dorado |
| Iconos y ficha de Google | `tools/gen_favicon.py` genera favicon, iconos e imagen OG; se declaran en `templates/_iconos.html` |

🔴 **No cambiar el archivo del favicon** sin motivo: Google tarda en recogerlo.

## Redes

- **Instagram y TikTok: `@tradeableacademy`** (creadas). El resto (X, YouTube,
  Reddit, Discord, Telegram) aparecen en `/socials` cuando se configure su enlace.
- Recomendación acordada: correo raíz dedicado a la empresa para todas las
  redes, con 2FA y códigos de respaldo guardados.
- **`/creators`** (`https://tradeable.academy/creators`): el enlace fijado en
  una historia destacada de Instagram para captar creadores.
- **`/proyecto`**: presentación para pegar en un mensaje directo.
- **Solo se contacta a creadores por correo, nunca por privado** (lo dice la
  propia página, contra suplantadores).
- Lista de trabajo de creadores: `docs/influencers.md` (todos "sin contactar").

## Herramientas de contenido (en `tools/`)

| Herramienta | Qué produce |
|---|---|
| `gen_posts_ig.py` + `posts_ig_textos.md` + `rasteriza_posts.py` | Publicaciones de Instagram con el kit de marca |
| `gen_historias_ig.py` | Historias (incluidas "historias de concepto": barrida, displacement…, que puentean al analizador) |
| `reel_sitio.py`, `reel_tour.py`, `reel_analizador.py`, `reel_preflight.py`, `reel_quiz.py`, `reel_order_block.py`, `reel_tiktok.py`, `edita_reel.py` | Reels grabando el sitio real con un navegador automatizado |
| `reels_guiones.md`, `docs/reel_narracion.md`, `narra_preflight.py`, `pega_narracion.py`, `marca_sonora.py` | Guiones, narración y sonido |
| `capta_analizador.py`, `capta_quiz.py`, `escena_pc.py`, `gen_chart_foro.py` | Capturas y escenas para piezas |
| `gen_tira_botarga.py`, `botarga_rig.py`, `limpia_botarga_nueva.py`, `botarga_oscura.py`, `recorta_emociones.py` | Trabajo con las botargas |
| `build_*_camo.py`, `gen_camo_skins.py`, `build_plates.py`, `plates_preview.py`, `build_cursors.py`, `cursors_preview.py`, `frames_preview.py` | Arte de camos, placas y cursores |
| `gen_favicon.py` | Iconos e imagen para compartir |
| `md_a_pdf.py`, `build_acuerdo_pdf.py`, `informe_banco_pdf.py` | Documentos en PDF |

Tipografías descargadas por esas herramientas van a `tools/.fuentes/`
(ignorado por git; licencia SIL OFL).

## Reglas de contenido

- **Educativo, nunca señal.** Un ejemplo de foro con objetivo de precio "suena
  a señal": se reescribió como pregunta de estudio.
- **La IA "aplica la metodología que elige el trader" y explica una operación
  ya tomada.** No "detecta patrones", no dice qué operar.
- **Reseñas solo reales.** Nada inventado, ni en redes.
- **No publicar porcentajes de comisión** en páginas públicas.
- **Autopublicación en redes:** investigada en agosto (YouTube fuerza privado
  sin auditoría de API; X es de pago; Reddit semi-manual). **Sin construir.**
- Si algún día se comunica el Analizador 2.0: cuidado con frases como "acierta
  el 96%" — es precisión de **medición de un gráfico**, no de predicción del
  mercado. Mal dicho, suena a promesa.

## Documentos de marca y negocio en el repo

| Archivo | Qué es |
|---|---|
| `docs/acuerdo_colaboracion.md` / `.pdf` | Acuerdo con creadores |
| `docs/influencers.md` | Lista de creadores a contactar |
| `docs/cambio_visual_2026-08-10.md` + `docs/ref_visual/` | Antes/después del arreglo de rendimiento visual |
| `docs/reel_narracion.md` | Narración de reels |
| `Scalpel_Checklist_PreLanzamiento.pdf`, `Scalpel_Costos_Operativos_IA.pdf`, `scalpel_costos_operativos.csv` | Documentos tempranos (nombre viejo) |
| `rank_badges_preview*.html`, `legend_badge_preview.html` | Maquetas de las medallas de rango |
