# 05 · PRUEBAS CON CAPTURAS REALES DEL DUEÑO

> **Carpeta:** `docs/capturas_prueba/` (7 imágenes de 6 gráficos distintos +
> textos de construcción + `LEEME.md` + `velas.md`).
> **Columnas ya obtenidas de Gemini:** `docs/columnas/` y, en el VPS,
> `out/analizador2/columnas_<imagen>.txt`.
>
> **Por qué tienen que ser reales:** un gráfico dibujado por uno mismo usa los
> colores y formas que uno elige, así que el extractor acierta siempre. Lo que
> lo rompe es justo lo que no se puede fabricar: el suavizado de la plataforma,
> la compresión, temas cualesquiera, indicadores y cajas translúcidas encima.
>
> ⚠️ Las notas originales numeran las capturas de forma inconsistente
> ("la cuarta", "la quinta"…). Aquí se identifican **por nombre de archivo**.
>
> 🔴 **Todas las velas del dueño son RELLENAS** (gris claro alcistas, negro o
> gris oscuro bajistas, contorno negro de 1 px). Ficha: `velas.md`.

## Las capturas

| Archivo | Tamaño | Qué es | Paso real | Paso que mide la cadena (medido el 2026-11-15) |
|---|---|---|---|---|
| `mes_5m.png` | 778×655 | MES 5m, tema con cajas de sesión, fibs, textos, flechas | 5,5 px | 🔴 **4,09** |
| `mnq_5m.png` | 1818×873 | MNQ 5m, **255 velas** a lo ancho | ~8 px | ✅ 7,97 |
| `mnq_5m_zoom.png` | 1816×875 | El mismo gráfico acercado (189 velas) | 10,5 px | 🟡 10,65 (1,4% alto; la rejilla lo afina después con los centros del modelo) |
| `mes_ote_perdedor.png` | 1817×825 | MES 5m, **SHORT** en el 0,5 del OTE, perdido | 7,4 px | 🔴 **6,27** |
| `mes_long_ote.png` | 1497×825 | MES 5m, **LONG** en el 0,5 del OTE, perdido | ⚠️ sin verdad anotada | 6,15 (sin contrastar) |
| `mnq_long_ote.png` | 1503×830 | MNQ 5m, **LONG** en el 0,5 del OTE, perdido | ~6,7 px | ✅ 6,69 |
| `nq_5m_oct.png` | 957×865 | NQ1! 5m, 2-oct-2026, **LONG**, enviada "a ciegas" | 5,84 px | 🔴 **3,48** |

Medido con `python3 tools/recorta_grafico.py --imagen docs/capturas_prueba/X.png`
(numpy 2.4, Pillow 13). Las notas de octubre daban 3,45 para la última: la
diferencia es de versión de librerías.

**Tres de seis gráficos fallan en el primer paso, y siempre por lo bajo.** Un
sesgo con dirección tiene una causa; no es ruido.

---

## `mes_5m.png` — la primera (septiembre)

- Hundió a `lee_grafico.py` (el extractor solo-píxeles): velas gris claro y
  negras, no verdes y rojas; la caja translúcida y las velas que tapa formaban
  una sola mancha; una línea de fib tiene la altura de un doji.
- Sirvió para la **prueba de las cajas** de Gemini: centro a ≤1 px, 0 de 25
  velas sin caja (doc 01).
- Hoy: el medidor del paso da 4,09 donde el real es 5,5.

## `mnq_5m.png` y `mnq_5m_zoom.png` — la regla de las 8 milésimas

- Con 255 velas en pantalla, cada caja de Gemini se comía 2–3 velas.
- Acercar el gráfico (189 velas) no bastaba: 4,4 milésimas por vela.
- **Recortando** (500,200 → 1020,800): 1 vela por caja, 0 de 93 sin marcar.
- **Primera validación de punta a punta** sobre `mnq_5m_zoom` con el recorte
  760,200 → 1240,780: 46 cajas, saltos de 8–13 px sin un solo hueco doble.
- ✅ **Verificación externa nº 1:** su indicador BoS/ChoCh termina su línea en
  **x=886, y=614**; la cadena calcula un BOS bajista en la vela que empieza en
  **x=886**, rompiendo un giro en **y=611**. Misma vela, 3 px.
  Blindado en `tools/test_analizador2.py` (15/15).
- ✅ **Escala de precios:** −0,4645 puntos/px, 22 de 26 etiquetas de acuerdo,
  0,32 puntos de error contra la línea de break-even.
- Fallos que solo salieron aquí: dos velas medidas de 425 px (mediana 70)
  pegadas al borde de una banda de killzone → `tope_alto`; y la misma ruptura
  contada tres veces → `bos_eventos`.

## `mes_ote_perdedor.png` — el SHORT perdido (6–7 sep)

**Construcción del trade** (`mes_ote_construccion.txt`): bajista en
temporalidad mayor; esperó a las 9:30 NY su MSS bajista en 5m; marcó el OTE;
entró en el 0,5; FVG bajistas apilados en 1H/15m/5m; buscaba LRL. El precio
nunca terminó de bajar y subió hasta su stop.

- Gemini devolvió **88 columnas donde hay ~102** → nació la **rejilla**.
- Las cajas iban de 5 a 12 px con velas cada 7,5; 23 de 104 se solapaban →
  `normaliza_ancho`. Y las columnas caían a **media vela** de su sitio →
  `encaja_en_rejilla` ("el fallo raíz").
- **Flechas:** roja en x=612,5 → vela 81 (entrada); azul en x=703,5 → vela 93.
  En esa ventana los hechos decían: acumulación en 70–78, pierna de
  manipulación alcista en la 77, BOS alcista en la 83.
- Primeras variantes del laboratorio (A, B, C, D) se corrieron aquí.
- Hoy: el medidor del paso da 6,27 donde el real es 7,4.

## `mes_long_ote.png` — LONG en el 0,5 del OTE (9 sep)

**Construcción** (`mes_long_ote.txt`): marcó el OTE sobre su MSS alcista de 5m
(no el último, que vio pequeño); esperaba una corrección por FVG de 5/10/15m;
entró en el 0,5; salió en su stop; R:R 1:2; 1H alcista.

- **Dos pares de flechas y solo uno es el trade** (el dueño: *"ignora las
  primeras dos flechas… esas no son"*). Los píxeles solos no deciden cuál es la
  marca del trader; además confunden las etiquetas "0,62" y "0,705" del fib.
- **La entrada no tiene flecha** (entró en la línea del 0,5; solo marcó la
  salida).
- **El borde vertical de una caja de sesión cruza las columnas de su entrada y
  de su stop**: tinta de 295 y 441 px en un gráfico de vela mediana 41. Destapó
  el agujero de las líneas verticales.
- Seis defectos reportados por el dueño; un solo parámetro causaba dos.

## `mnq_long_ote.png` — el trade de la primera comparación (9–16 sep)

**Construcción** (`mnq_long_ote.txt`): LONG en el 0,5 del fib. Tesis: *"un
cierre de 1H que ocasionó un Structure Shift a alcista"*. Y la frase que lo
hizo la mejor prueba: *"consideraba que había mucha más liquidez superior —
aunque quizá pueda estarme equivocando"*. Eso se puede contestar con aritmética.

- ✅ **Verificación externa nº 2:** mínimo sin barrer en 29.334,12; línea "SS"
  de su indicador en 29.333,00 → **1,1 puntos**.
- **La respuesta a su duda sobre la liquidez:** en su vela de entrada había 3
  niveles arriba contra 2 abajo, el de arriba más cerca y con el camino limpio.
  *La aritmética le daba la razón y el trade falló igual.*
- **El medidor del paso viejo decía 5,50** → la rejilla inventaba ~30 velas:
  **163 velas donde hay 135**. Con el medidor nuevo: 6,69 px y 135 velas; el
  dueño las verificó a ojo (el modelo devolvió 124 y la rejilla recuperó 11).
  - ⚠️ Por eso la numeración cambió: **su entrada era "la vela 149" en las
    corridas viejas y es la vela 123 en las buenas.**
- Velas leídas como "negro": 37 → 3 al arreglar el paso.
- Al arreglar los giros empatados: entre la vela 72 y la 123 la cadena no veía
  ni un giro; ahora ve seis. Su MSS alcista se mueve de la vela 120 a la 113.
- ✅ **Verificación externa nº 3 — su fib, al píxel:**

  | | Medido en la captura | Calculado (anclas 117 y 120) |
  |---|---|---|
  | su 0,5 | y = 368,5 | y = 367,5 |
  | su 0,79 | y = 433,5 | y = 432,8 |

- 🔴 **Con su fib entró en discount, dentro de la OTE** (cierre de la 123 en
  0,698). El informe automático le dijo **premium**, porque la cadena anclaba
  en 99–121. → Decisión: premium/discount solo con las anclas del trader.

### La primera comparación contra el sitio (6 variantes)

`tools/analizador_lab.py` produce varias respuestas al mismo trade, usando el
prompt real del sitio (extraído de `app.py` sin ejecutarlo):

| Variante | Qué recibe la IA | Resultado |
|---|---|---|
| **A** | Lo que recibe hoy el sitio | 🔴 No cita ni una vela. Repite las confluencias del trader. Inventa un CHoCH. |
| **B** | A + cláusula de verificación | 🔴 Igual, y además afirma que entró "fuera de una Kill Zone" (entró dentro). |
| **C** | A + **bloque de hechos** | ✅ Cita velas, precios y niveles reales. 0 inventados (auditado). |
| **D** | Solo hechos verificados + "prohibido inventar referencias" | ⚠️ Se inventó la vela 141. (Justo la variante con la prohibición.) |
| **E** | Bloque completo con tasas + tabla de todas las velas | ✅ Cita reales, 0 inventados. |
| **F** | **Solo** la tabla de velas (OHLC), sin hechos | 🔴 No saca ni un BOS. "Evalúa si el camino era de baja resistencia": devuelve la pregunta. |

**Lo que quedó demostrado:**
1. **A, B y F son el grupo de control y salieron mal**, que era lo que había
   que demostrar. No es que el experimento falle.
2. **La IA no deduce** (F): con los números delante no calcula nada.
3. **La IA sí usa los hechos, si se le dice dónde mirar.** Sin la vela de
   entrada citaba un BOS de cien velas antes del trade. Con ella: *"el cierre
   de la vela 143 muestra un BOS bajista, señal de advertencia para una
   posición larga"*. (⚠️ Los números de vela de estas citas —143, 149, 156—
   son de corridas de septiembre con numeraciones distintas entre sí, anteriores
   al arreglo del paso; valen como ejemplo del comportamiento, no como
   referencia de velas.)
4. **Hay que partir la ventana en tres secciones.** Con una lista única
   escribió que el trade falló por "un OB bajista en la vela 156 y un FVG
   bajista en la 159": entró en la 149. Le reprochaba cosas aparecidas siete
   velas después de apretar el botón.
5. **La respuesta entera estaba en su propia vela de entrada:** cerró
   atravesando el FVG alcista de la vela 145, la zona en la que se apoyaba.
6. **El catálogo no tenía el hecho en el que él basó su tesis** (MSS) → se añadió.
7. **Auditar no es opcional.**

## `nq_5m_oct.png` — la prueba a ciegas (octubre)

El dueño la mandó **sin construcción del trade**, *"para ver qué logra detectar
o analizar por sí solo"*.

- 🔴 **La cadena falla en el primer paso:** estima 3,45 px por vela; el real es
  **5,84** (eje de tiempo: 70,10 px por hora ÷ 12 velas) / **6,00** (contando a
  mano en una franja limpia). Inventaría un 69% más de velas.
- Novedades de esta captura: barra de herramientas de TradingView a la
  izquierda (descartada como causa), tema claro con **cajas de sesión grises**,
  instrumento nuevo.
- 🔴 **La caja de la sesión de Asia tiene EXACTAMENTE el mismo color que su
  vela alcista** — RGB (206,208,213). Ninguna regla de color las separa; lo que
  las distingue es la forma (tiras de 3–5 px con borde negro contra una mancha
  de ~290 px). ⚠️ Las notas y `velas.md` dicen "caja de NY PM": **es la de
  Asia**, corregido por el dueño.
- ⛔ Se probó clasificar fondos por paleta para arreglar el paso: el banco lo
  rechazó (paso mal en 4–8% → 15% de las láminas) y **borraba las velas
  alcistas**. Revertido.
- **Diagnóstico pendiente:** `_arranques` asume un solo fondo por franja → la
  mayoría de las franjas se descartan y votan las de texto de la cabecera.
  **Señal candidata sin probar:** los bordes negros de 1 px de las velas
  (197 columnas de borde ≈ 100 velas × 2).
- Con el paso forzado a mano (`--paso 5.84`) la cadena corrió: **12 hechos** en
  el tramo (pocos). La variante C citó dos veces la vela 31, que no estaba en
  el bloque.
- **Contaminación descubierta por el dueño:** el laboratorio tenía valores por
  defecto que arrastraban las confluencias, la dirección y la sesión del trade
  de septiembre. La prueba "a ciegas" llamó short a un long. → Se quitaron
  todos los valores por defecto (`NOT PROVIDED — … Do NOT assume a value.`).
- **Quedó a medias** (no retomar sin que él lo pida): confirmar sus flechas
  (flecha azul hacia arriba en x≈530 = entrada; roja hacia abajo en x≈595 =
  salida), y recibir su construcción, sesión y resultado.

---

## Qué enseñan las seis en conjunto

- El **modelo de visión** cumple (localiza) siempre que se le mande por tiras.
- La **aritmética** cumple: tres verificaciones contra una fuente
  independiente, a 3 px, 1,1 puntos y 1 px.
- El punto débil es **la medición por píxeles en gráficos reales**: el paso
  (3 de 6) y el extenso (~86%).
- Cada captura nueva destapó algo que el banco no dibujaba. **El banco tiene
  que parecerse más a un TradingView real** antes de que sus porcentajes se le
  puedan enseñar a un cliente.
- **La revisión del dueño a ojo es parte del método**: él cazó la tendencia mal
  leída, el contorno negro, las velas "huecas", la contaminación del
  laboratorio y la caja de Asia.
