# 📜 Guía paso a paso — Registro de Copyright (copyright.gov)

> **Objetivo:** convertir tu "prueba de que fuiste primero" (git + fechas) en el
> **derecho real a demandar** por plagio de tu contenido. En EE.UU. el copyright
> existe automáticamente al crear la obra, PERO **debes registrarlo para poder
> presentar una demanda** (Corte Suprema, *Fourth Estate*, 2019). Registrarlo
> **antes de publicar o dentro de los primeros 3 meses** desbloquea **daños
> estatutarios + honorarios de abogado** (lo que hace que demandar valga la pena).
>
> ⚠️ Guía informativa, no asesoría legal. El registro es DIY (lo puedes hacer tú).
> Para la redacción del depósito de código (ocultar secretos) un abogado de IP ayuda,
> pero no es obligatorio.

---

## ⏱️ TIMING — lo más importante
- **Ideal:** registrar **justo al lanzar** (o en los días previos), NO meses después.
- La fecha que cuenta es la de **presentación** (aunque el certificado tarde meses en llegar).
- Si registras DESPUÉS de que alguien te copie: aún puedes demandar, pero **pierdes**
  los daños estatutarios y los honorarios → la demanda se vuelve poco rentable.

---

## 🏛️ Antes de empezar (2 decisiones)
1. **¿A nombre de quién se registra?** → A nombre de **la empresa** (la entidad de tu
   socio), NO de una persona. Asegúrate de que exista una **cesión de IP** que diga que
   el producto y su contenido pertenecen a la empresa. (Si el código lo escribiste tú,
   firma una asignación de derechos a la empresa.)
2. **Estado de publicación:** "unpublished" si aún no has lanzado; "published" con su
   fecha una vez en vivo. (Puedes registrar la versión pre-lanzamiento como inédita.)

---

## 💵 Costo total estimado: **~$135 – $260 (una sola vez)**
- Tarifa por obra: **$45** (un autor, una obra, no work-for-hire) o **$65** (estándar/otros).
- Son ~3-4 obras (ver abajo) → ~$135-260 en total. Pago con tarjeta en el portal.

---

## 📦 QUÉ registrar y EN QUÉ ORDEN (de mayor a menor valor)

### 1) Código fuente — *Computer Program* (lo primero, es el corazón del producto)
- **Tipo de obra en el portal:** "Computer Program" (categoría Literary Work / Obra Literaria).
- **Depósito:** NO subes todo el código. Se suben **"identifying portions"** = las
  **primeras 25 + últimas 25 páginas** del código fuente.
- **🔒 Secretos:** puedes **TACHAR/redactar** las porciones con secretos comerciales
  (ej. tu `SYSTEM_PROMPT`, claves, lógica sensible) antes de subir. Esto protege tus
  prompts mientras igual registras el código.
- Cubre la lógica/funcionalidad del sitio.

### 2) Contenido y diseño del sitio web — *Literary Work / Visual Arts*
- **Qué cubre:** el **texto/copy** de la web, las guías educativas en pantalla, el
  **diseño visual** y el "look & feel" (en la medida en que sea expresión original).
- **Depósito:** un **snapshot representativo** → exporta las páginas clave a **PDF** o
  captura de pantalla (landing, /app, pricing, etc.) y súbelo como un solo documento.
- Nota: el sitio es una "obra viva"; registras la **versión del lanzamiento**. Cambios
  grandes futuros se re-registran (no te obsesiones — registra el lanzamiento y, si
  acaso, una vez al año la versión mayor).

### 3) Los PDFs / guías educativas — *Literary Work*
- Tus PDFs descargables (Synapse, certificados, guías) son **obras vendibles distintas**
  y valiosas. Regístralas (puedes agruparlas si comparten autor/claimant).
- **Depósito:** los PDFs mismos.
- Bonus: tus PDFs ya llevan **watermark personalizado** → eso ya es una "huella" extra.

### 4) Logo / ilustraciones — *Work of the Visual Arts* (opcional)
- Las ilustraciones SVG y el logo. **Para el logo, la protección fuerte viene de la
  MARCA (trademark)**, así que esto es secundario; regístralo si tienes gráficos
  originales destacados.

---

## 🪜 PASOS EN EL PORTAL (copyright.gov)
1. Entra a **https://www.copyright.gov** → **"Register a Copyright"** → portal de
   registro electrónico (eCO / Registration System). Crea una cuenta.
2. **"Register a new claim"** → elige el **tipo de obra** (Literary Work para código y
   texto; Visual Arts para gráficos).
3. **Title:** título de la obra (ej. "Trader Accelerator — Source Code", "Trader
   Accelerator — Website Content", etc.).
4. **Author / Claimant:** la **empresa** como claimant. Año de creación. Publicación
   (published/unpublished + fecha).
5. **Paga** la tarifa ($45/$65).
6. **Sube el depósito** (el archivo: porciones de código redactadas / PDF del sitio /
   los PDFs / los gráficos).
7. **Submit.** Recibes un **número de caso**; el certificado llega por correo en
   semanas/meses, pero la **fecha efectiva = la de presentación**.
8. **Guarda** el comprobante y el certificado en un lugar seguro (y respáldalo).

---

## ✅ Checklist rápido
- [ ] Cesión de IP a la empresa lista (la empresa es la dueña)
- [ ] Cuenta creada en copyright.gov
- [ ] (1) Código fuente registrado — con secretos/prompts tachados en el depósito
- [ ] (2) Contenido + diseño del sitio registrado (PDF snapshot del lanzamiento)
- [ ] (3) PDFs / guías educativas registradas
- [ ] (4) Logo/ilustraciones (opcional — el logo va mejor por marca)
- [ ] Registrado **antes de publicar o dentro de los 3 meses** del lanzamiento
- [ ] Certificados guardados y respaldados
- [ ] Git history intacto (prueba de prioridad) — **no borrar**

---

## 🔗 Y aparte (NO es copyright, no confundir)
- **El NOMBRE/logo** → se protege con **registro de MARCA** en la USPTO (cuando se
  decida el nombre). Es un trámite **separado** del copyright.
- **Los prompts/lógica secreta** → *trade secret*: se protegen manteniéndolos en
  secreto (ya viven server-side) + NDAs con quien los vea.
