# ANALIZADOR 2.0 — RESUMEN ("la turbina")

> **Esta carpeta guarda el trabajo más valioso y más frágil del proyecto.** Es
> investigación con mediciones: qué se probó, qué funcionó, qué fracasó, con
> qué números, y qué falta. Si se pierde, hay que volver a descubrirlo todo.
>
> 🔴 **Nada de esto está conectado al sitio.** Vive en `tools/`, la aplicación
> no lo importa, y el analizador de producción sigue igual. Conectarlo es una
> decisión del dueño que **aún no ha tomado**.

## La comparación del dueño

*"Es como comparar un motor de karting con una turbina de avión."*

- **El kart** (producción): se le manda la captura a GPT-4o y se le pide que
  la "mire" y opine. Funciona para lo general, pero **no mide**.
- **La turbina** (laboratorio): una cadena de piezas donde **cada una hace solo
  lo que sabe hacer, y eso se ha medido**. Al final la IA no mira el gráfico
  para deducir: recibe una lista de **hechos ya comprobados** y solo redacta.

## El descubrimiento que lo originó

Se midió con 168 láminas de prueba (31-ago-2026) y salió algo que contradice la
intuición: **el problema del analizador no es que vea mal.**

- GPT-4o lee texto de 9 píxeles y detecta una línea de 2 píxeles. Ve de sobra.
- Pero **no sabe decir si una cosa está por encima de otra.** Ni ampliando la
  zona 4 veces. A "¿el RSI está bajo 30?" responde NO siempre; a "¿está sobre
  30?" responde SÍ siempre. Es una lectura firme y equivocada.
- Y "¿esto cerró por encima de aquello?" es **la operación central de todo el
  análisis técnico**: una ruptura, un FVG, una barrida, un order block… todo
  son comparaciones de altura.

Consecuencia: cambiar a un modelo "con más resolución" probablemente no arregla
nada. Hay que **dejar de pedirle a un modelo de lenguaje que mida**.

## La doctrina (en cuatro líneas)

1. **Un modelo de visión dice DÓNDE está cada vela** (en qué columna). Eso sí
   lo hace bien: Gemini acierta el centro de la vela a ≤1 píxel.
2. **Los píxeles dicen CUÁNTO mide** (máximo, mínimo, cuerpo, color). Aritmética.
3. **El código deduce los HECHOS** (BOS, FVG, barrida, liquidez…). Son
   definiciones, y una definición se calcula.
4. **GPT-4o solo REDACTA**, con los hechos delante y sabiendo dónde entró el
   trader.

El patrón se repitió cinco veces: **el modelo lee y reconoce muy bien, y sitúa
mal.** Cada vez la solución fue la misma: que el modelo diga *qué* y
*aproximadamente dónde*, y que los píxeles digan *exactamente dónde*.

## La cadena, de un vistazo

```
captura.png
   │
   ├─1─ recorta_grafico   encuentra el panel y el paso entre velas       (píxeles)
   ├─2─ cajas_ia          ¿en qué columna está cada vela?                (Gemini, por tiras)
   ├─3─ rejilla_velas     recupera las velas que el modelo se dejó       (píxeles)
   ├─4─ afina_velas       máximo, mínimo, cuerpo de cada vela            (píxeles)
   ├─5─ afina_velas       alcista / bajista, sin conocer los colores     (píxeles)
   ├─6─ eje_precio        de píxel a precio                              (Gemini lee dígitos + píxeles dan la altura)
   ├─7─ hechos_grafico    BOS, FVG, barridas, liquidez, estructura…      (aritmética)
   │
   └──► BLOQUE DE HECHOS  (texto, en tres niveles de seguridad)
              │
   analizador_lab  → se lo entrega a GPT-4o junto al prompt REAL del sitio
                     y compara la respuesta con la del analizador de hoy
```

Programa que lo encadena todo: `tools/analizador2.py`. Juez: `tools/banco_cadena.py`.

## Cómo se sabe si algo funciona: el banco

`banco_cadena.py` **dibuja él mismo** gráficos con colores, temas y "basura"
al azar (cajas de sesión, líneas, marcas de agua, dibujos del trader). Como los
dibuja, conoce cada vela **al píxel**. Luego pasa la cadena y cuenta aciertos.
**Ningún arreglo se da por bueno si el banco no lo confirma**, y nunca se afina
contra las capturas del dueño (ya se cometió ese error una vez).

## Los números de hoy (última medición honesta: 16-sep-2026)

Cada cifra es el **peor resultado** de las tandas medidas (no la media).

| Qué afirma la cadena | Acierta | Cómo se usa |
|---|---|---|
| **BOS** (ruptura de estructura) | **95,9%** | Se afirma en seco |
| **Acumulación** (como zona) | **93,7%** | Se afirma en seco |
| **Premium/discount** (como zona) | **90,1%** | Solo si el trader dice dónde ancló su fib |
| Barrida de liquidez | 86,8% | Con su tasa al lado |
| Estructura (HH/HL/LH/LL) | 83,3% | Con su tasa |
| FVG | 81,4% | Con su tasa |
| DOL (liquidez pendiente) | 80,6% | Con su tasa |
| Tendencia | 75,7% | Con su tasa |
| Liquidez (nivel + forma + estado) | 74,4% | Con su tasa |
| Estado del FVG | 74,2% | Con su tasa |
| Pierna de manipulación | 74,0% | Con su tasa |
| Order block | 73,6% | Con su tasa |
| MSS / CHoCH | 69,4% | Con su tasa (cláusula del BOS) |
| *(por debajo de 65%)* | — | **No se escribe** |

Medición de las velas en sí: máximo y mínimo exactos **85,5–91,3%**; dirección
(alcista/bajista) **92,3–96,5%**; paso entre velas correcto en **89–96%** de
las láminas del banco.

## Tres verificaciones contra una fuente independiente (el indicador del dueño)

1. **BOS:** su indicador marcó un BOS en x=886, y=614. La cadena —que no lee
   ni texto ni líneas— calculó un BOS en la vela que empieza en x=886, con el
   nivel a **3 píxeles**.
2. **Liquidez:** el mínimo sin barrer salió en 29.334,12; la línea "SS" de su
   indicador estaba en 29.333,00. **1,1 puntos.**
3. **Su Fibonacci:** se midieron sus 7 líneas y se calculó dónde caerían con
   anclas en las velas 117 y 120. Diferencia: **1 píxel**.

## Dónde está parado HOY (2026-11-15)

✅ **Lo que ya funciona:** la cadena completa corre de punta a punta; el bloque
de hechos sale en tres niveles; la IA cita velas y precios reales cuando recibe
el bloque y sabe dónde entró el trader; la escala de precios acierta a 1 tick.

🔴 **Lo que la frena:**
1. **El primer paso falla en gráficos reales.** El medidor del paso entre
   velas acierta 78–79 de 80 láminas del banco, pero falla en **3 de las 6
   capturas reales** del dueño, siempre por lo bajo. El banco no dibuja
   gráficos lo bastante parecidos a un TradingView real.
2. **Medir el extenso de la vela ronda el 86%**; cada vela mal medida arrastra
   FVG y order blocks falsos.
3. **Faltan familias de hechos** que un trader de ICT usa: inducement,
   displacement como hecho propio, kill zones (no se lee el eje de tiempo),
   medias, RSI, MACD.
4. **No está conectado al sitio**, ni hay un programa único "de captura a
   respuesta" para producción.

## Los documentos de esta carpeta

| Archivo | Contenido |
|---|---|
| `01_DIAGNOSTICO_DE_VISION.md` | Las mediciones que demostraron que la IA no compara. |
| `02_LA_CADENA_ESLABON_POR_ESLABON.md` | Cada pieza: qué hace, cómo, qué trampas tiene. |
| `03_CATALOGO_DE_HECHOS.md` | Cada hecho que se calcula y su definición exacta. |
| `04_BANCO_DE_PRUEBAS_Y_MEDICIONES.md` | Cómo se mide, y todas las tablas de resultados en el tiempo. |
| `05_PRUEBAS_CON_CAPTURAS_REALES.md` | Las 6 capturas del dueño y la comparación contra el sitio. |
| `06_ERRORES_Y_LECCIONES.md` | Todo lo que salió mal y lo que se probó y se descartó. |
| `07_COMO_CORRERLO.md` | Comandos, requisitos, dónde poner la clave. |
| `08_QUE_FALTA_Y_HOJA_DE_RUTA.md` | Lo pendiente, en orden, y cómo se conectaría al sitio. |
| `ejemplos/` | **Una salida real:** el bloque de hechos de `mnq_long_ote` (135 velas), su mapa de velas numeradas con la entrada marcada, y un recorte ampliado de las velas medidas. Generados el 2026-11-15, sin red. |

## Reglas de esta zona (no negociables)

1. **No tocar el analizador del sitio** sin permiso explícito del dueño.
2. **Las velas del dueño NO son huecas.** Rellenas: gris claro las alcistas,
   negro/gris oscuro las bajistas. Antes de decir una palabra sobre el color
   de las velas de una captura: correr `tools/colores_velas.py` y leer
   `docs/capturas_prueba/velas.md`. Si no hay ficha, **se le pregunta**.
3. **Medir en el banco antes de dar algo por arreglado.**
4. **Nunca afinar contra sus capturas.** Sirven para encontrar el mecanismo del
   fallo; el arreglo se valida en el banco.
5. **Si un dato se mide en producción, en el banco también se mide.** Nada de
   regalarle la respuesta a la pieza que se está probando.
6. **Arreglar el código obliga a re-medir** la tabla de precisión.
7. **Auditar siempre** que la IA no cite velas que no estaban en el bloque.
8. **Nunca un modelo con alias `-latest`** para trabajo medible.
9. **Hablarle al dueño sin tecnicismos** y enseñarle la imagen para que pueda
   comprobarlo él mismo (`mapa_velas.py`).
