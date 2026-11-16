# 09 · EL ANALIZADOR DEL SITIO (el que está en producción)

> 🔴 **Regla del dueño: este analizador no se toca sin su permiso explícito.**
> Todo lo experimental va en el laboratorio (`tools/`, carpeta 10 de este
> expediente). El laboratorio LEE este código para compararse con él, pero
> nunca lo modifica ni lo importa.

## Qué hace, visto por el trader

1. Elige (o crea) un proyecto y pulsa analizar.
2. Sube **una captura** de su gráfico (TradingView, NinjaTrader…; JPG, PNG o
   WebP, hasta 20 MB) con la **entrada y la salida marcadas**.
3. Rellena el formulario:
   - instrumento · **dirección (long/short)** · sesión · resultado
     (ganado/perdido/BE) · sesgo de temporalidad mayor · ¿operó alineado?
   - **metodología** (una de 7)
   - confluencias (casillas)
   - **"Trade Construction"**: hasta 200 palabras contando qué vio y por qué
     entró.
4. Recibe un análisis de 200–420 palabras, en su idioma, con hasta 3
   observaciones y una reflexión final.

## Qué pasa por dentro (`scalpel/app.py`)

```
navegador ──POST /validate──►  ¿se ven entrada, salida, SL/TP?       (GPT-4o, imagen en baja, 150 tokens, temp 0)
    │                            └─ si falla la llamada, deja pasar (es un filtro blando)
    ▼
navegador ──POST /analyze───►  1. ¿tiene sesión?            has_access()
                               2. ¿le quedan análisis?      check_rate_limit()  → 429 limit_reached
                               3. recorta las notas         2.000 caracteres, luego 200 palabras
                               4. reduce la imagen          normalize_chart_image() → máx 1280 px, JPEG q85
                               5. arma el prompt            build_system_prompt(metodología)
                               6. llama al modelo           gpt-4o, imagen "high", 900 tokens, temp 0.3
                               7. anota uso, costo y XP     log_usage(), record_ai_cost(), add_xp()
                               ◄── {"analysis": "…markdown…"}
```

- **Modelo:** `gpt-4o` (variable `SCALPEL_MODEL`).
- **Proveedor:** OpenAI de pago si existe `OPENAI_API_KEY`; si no, GitHub
  Models (gratis, con límites por minuto). Mismo modelo y mismo prompt.
- **Costo:** ~$0,02–0,03 por análisis (dos llamadas).
- El navegador convierte el Markdown a HTML con `marked` y lo limpia con
  `DOMPurify`.
- **No se guarda la captura ni el texto del análisis en el servidor** (solo el
  registro de uso y de costo). El historial visible vive en el navegador.
  ⚠️ Confirmar leyendo `index.html` antes de prometerle historial a alguien.

## El prompt del sistema (`SYSTEM_PROMPT`, líneas ~3680–3939)

Es un texto largo en inglés, partido en secciones con marcas `@@SEC:NOMBRE@@`.
`build_system_prompt(approach)` arma el envío **solo con lo que aplica** a la
metodología elegida, para no pagar tokens de más:

| Parte | Cuándo viaja |
|---|---|
| **Bloque global** (siempre): personaje "Scalpel", filosofía de *posibilidades, no veredictos*, **límites de cumplimiento**, protocolo de lectura en dos fases, regla de no inventar, dirección como verdad, cómo leer marcadores | Siempre |
| Cláusula de verificación de afirmaciones | Si `ANALYZE_VERIFY_CLAIMS=1` (**encendida en producción**) |
| `ICT` (conocimiento completo, incluye OTE/StdDev y SMT) + `ROUTER` + `ICTPROCESS` | Metodología ICT, OTE o SMC |
| `SP_CORE_LITE` (base compacta) + **su bloque** (`WYCKOFF`, `PATTERNS`, `HARMONIC`, `ELLIOTT` o `TA`) | Las otras 5 metodologías |
| `OUTPUT` (formato y tono de la respuesta) | Siempre |
| Todo junto | Metodología desconocida (respaldo seguro) |

### Las ideas que gobiernan el prompt

1. **Posibilidades, nunca veredictos.** Prohibido "lo hiciste mal". Siempre
   "algo a considerar…", "podría sugerir…". Cada concepto de ICT admite varias
   interpretaciones válidas; se juzga contra las reglas del propio trader.
2. **Límites legales permanentes** (ganan a cualquier otra instrucción): jamás
   decir comprar/vender/entrar; jamás afirmar que un precio "va a" subir o
   bajar; jamás prometer ganancias. El análisis es **retrospectivo y educativo**.
3. **Leer el gráfico PRIMERO, al trader después** (dos fases). Si la lectura
   propia difiere de la tesis del trader, **esa diferencia es la observación
   principal**.
4. **No inventar estructura.** Si algo no se ve, decir "no puedo confirmarlo en
   la captura".
5. **La dirección la dice el trader y es verdad absoluta.** No se deduce de
   colores de flechas.
6. **Un setup válido también pierde.** Si todo estaba bien, decirlo: fue
   varianza estadística.

### La cláusula de verificación (`VERIFY_CLAIMS_CLAUSE`)

Añadida en agosto tras el banco de 30 casos. Ordena tratar toda etiqueta, dibujo
o nota del trader como una **afirmación a comprobar contra el eje de precios**,
con tres salidas: lo confirma, lo contradice (y entonces es la observación
principal) o **no puede verificarlo y lo dice**. Incluye una regla de honestidad
numérica: nunca decir que un valor "es visible" si no lo derivó él mismo.

- Por defecto está **apagada en el código** (el prompt queda idéntico byte a
  byte); **en producción está encendida** (`ANALYZE_VERIFY_CLAIMS=1`).
- El log imprime `[AI] clausula-verificacion=ENCENDIDA` al arrancar. ⚠️ Buscar
  el nombre de la variable en el log da 0 resultados aunque esté encendida.

## El mensaje del usuario (lo que se le manda junto a la imagen)

Plantilla fija (línea ~13402): instrumento, **dirección marcada como verdad**,
sesión, resultado, sesgo, alineación, metodología, confluencias, el bloque de
"construcción del trade" (con la orden de contrastarlo, no repetirlo) y la orden
de idioma (prosa en el idioma del usuario, siglas de ICT en inglés).

## Qué tan bueno es — MEDIDO

### El banco de 30 casos (agosto 2026)

Como el dueño solo opera ICT/OTE y no puede etiquetar otras metodologías, se
construyeron **gráficos sintéticos desde la definición aritmética** de cada
patrón (un Gartley *es* B = 0,618·XA), así la verdad se conoce por construcción.

- `tools/banco_analizador.py` genera los casos: 5 metodologías × (ganado +
  perdido con confluencias + 2 **trampas**) + 4 de ICT/OTE + 6 perdidos con
  afirmaciones falsas = **30**.
- `tools/corre_banco.py` los pasa por el mismo prompt, modelo y parámetros que
  `/analyze` (~$0,35 la pasada). `tools/califica_banco.py` puntúa.
  `tools/informe_banco_pdf.py` arma el informe de 51 páginas.
- Resultados guardados en `docs/banco_resultados/`, `_v2/` y `_v3/`.

**Lo que salió:**
- **Trades normales: bien.** En los perdidos encontró la razón real.
- 🔴 **Trampas: falló 8–9 de 10.** El patrón es **complacencia**: cree las
  etiquetas y las notas en vez de medir. Validó razones armónicas falsas, un
  solape de onda 4 que existía, lecturas de volumen en un gráfico **sin panel
  de volumen**, un cruce de medias inexistente.
- Con la cláusula de verificación: caza las comparaciones gruesas y deja de
  inventar lecturas; **cero daño** a ICT/OTE. Pero **siguen ciegos** (límite de
  vista, no de prompt): razones armónicas finas, solape de Elliott, cruce de
  medias.

**Nota por metodología** (veredicto humano leyendo cada respuesta):
ICT/OTE **8** · Wyckoff **8** · Chart Patterns **7** · Elliott **6** ·
Technical Analysis **5,5** · Harmonic **5**.

⚠️ El calificador automático por expresiones regulares dio varios verdes y
rojos **falsos**. Siempre leer los textos antes de sentenciar.

### El estudio de agudeza visual (31-ago-2026)

Documentado en `10_ANALIZADOR_2_LABORATORIO/01_DIAGNOSTICO_DE_VISION.md`.
Conclusión: GPT-4o **ve de sobra** (lee texto de 9 px, detecta líneas de 2 px)
pero **no sabe decidir si una cosa está por encima de otra**, a ningún tamaño.
Y esa comparación es la operación central del análisis técnico.

### La primera comparación real (9-sep-2026)

Sobre un trade real del dueño, el analizador del sitio (con y sin cláusula)
**no citó ni una vela concreta**: le devolvió al trader sus propias
confluencias, se inventó un CHoCH y afirmó que entró "fuera de una Kill Zone"
cuando entró dentro. Es la medición que justifica el Analizador 2.0.

## Por qué no se "arregla con un mejor prompt"

Está probado tres veces: (1) la cláusula de verificación mejora lo grueso y no
lo fino; (2) pedirle coordenadas falla por 93 px de media; (3) darle la tabla
completa de precios de 149 velas no hace que deduzca un solo BOS. **La IA no
mide ni deduce: redacta.** De ahí el diseño del 2.0: medir con código y dejarle
a la IA solo la redacción.

## Límites y protecciones alrededor

- Cuota por plan contada en `UsageLog` (solo cuenta análisis exitosos).
- `/api/usage` devuelve siempre usados/máximo/restantes.
- Rechaza imágenes de más de 8.000 px de lado.
- El error de "límite por minuto" del proveedor gratuito se distingue del de
  autenticación.
- Hubo un botón para traducir el análisis ya entregado: **se retiró por
  decisión del dueño** (costo). No reponer sin que lo pida.

## Qué se le ofreció al dueño y está SIN respuesta

Que el analizador del sitio **deje de afirmar relaciones que no puede
verificar** (por ejemplo "cerró por encima del order block"). Es un cambio de
prompt, gratis. Toca producción: no se hace sin su visto bueno.
