# 04 · EL BANCO DE PRUEBAS Y TODAS LAS MEDICIONES

> **Archivo:** `tools/banco_cadena.py` (1.060 líneas). Corre **sin red y gratis**.
> ```
> python3 tools/banco_cadena.py --laminas 72 --semilla 7
> ```

## Por qué existe

El dueño no preguntó "¿te gustan los recuadros?". Preguntó si al final el
analizador puede decir *"efectivamente rompió X a la baja"* **sin
inventárselo**. Eso solo se contesta con un porcentaje, y el porcentaje solo
vale si la verdad es exacta. Aquí lo es: **el banco dibuja los gráficos**, así
que conoce cada vela al píxel sin medir nada.

## Qué dibuja (feo y aleatorio a propósito)

Cada lámina sortea: fondo claro u oscuro · **dos colores de vela cualesquiera**
(rosados, dorados, morados: la queja literal del dueño) · cuerpos **rellenos o
huecos** · ancho y separación · rejilla sí o no. Y encima, la "basura" que
rompió las capturas reales:

| Basura | Desde | Qué representa |
|---|---|---|
| Zona translúcida por detrás | 04-sep | Caja de sesión / killzone |
| Líneas horizontales y una discontinua | 04-sep | Niveles, fibs |
| Etiquetas de texto | 04-sep | Precios, nombres |
| **Marca de agua** en letras enormes, del color de las velas | 09-sep | El nombre de la sesión ("London") |
| **Líneas verticales** | 09-sep | El borde de una caja de sesión |
| **Dibujos del trader** (flechas, fibs) | 09-sep | Lo que el sitio le pide marcar |
| Velas estrechas | 09-sep | Gráficos muy comprimidos |

⚠️ **Solo las láminas del banco tienen velas huecas.** Las del dueño son rellenas.

## Qué mide (por separado, para saber qué falla)

| Eslabón | Pregunta | Dónde |
|---|---|---|
| A · localizar | ¿en qué columna está cada vela? / ¿cuál es el paso? | El paso se mide aquí. Las columnas del modelo **se imitan** (con su error y quitando velas). ⚠️ La cabecera del archivo menciona una opción `--columnas-ia` para inyectar columnas reales de Gemini: **hoy no existe**; el eslabón A con modelo real solo se mide sobre capturas reales en el VPS. |
| B · medir | ¿de dónde a dónde se extiende? | Aquí |
| C · concluir | ¿eso es un FVG, un BOS…? | Aquí |

**Dos cifras por familia:**
- **acierta** = de lo que afirma, cuánto es cierto (*lo que decide si le
  mentimos a un cliente*);
- **encuentra** = de lo que hay, cuánto ve.

**Contra dos verdades:** la serie de **precio** original (resultado honesto,
con el redondeo a píxeles incluido) y la misma serie **ya redondeada** (aísla
el fallo del extractor). Si la primera sale mal y la segunda bien, el límite es
la captura, no el código.

**Condiciones "reales" por defecto:** el banco **quita el 14% de las velas**
(lo que se deja el modelo) y deja que la rejilla las recupere; imita la guía
vertical del modelo **con su error medido** (σ 5–9 px y 20% de fallos de 30 px),
nunca con la verdad; y **mide el paso él solo**.

**Los hechos se emparejan por posición, no por índice** (`_empareja`): si falta
una vela, todos los índices posteriores se corren y un BOS bien detectado
contaría como fallo (con esa métrica errónea el daño salía el triple).

## Opciones útiles

| Opción | Para qué |
|---|---|
| `--laminas N`, `--semilla S` | Tamaño y azar de la tanda |
| `--faltan 0.14` | Fracción de velas que el "modelo" no devuelve |
| `--sin-rejilla` | Ver el daño de no recuperar velas |
| `--sin-guia` | Medir sin la pista vertical del modelo |
| `--paso-regalado` | Darle el paso verdadero (como hacía el banco hasta el 13-sep) |
| `--sin-marca`, `--sin-verticales`, `--sin-dibujos`, `--sin-bordes` | Apagar cada tipo de basura para aislar su efecto |
| `--pistas-dib` | Con la pista (imitada) del modelo sobre dónde dibujó el trader |
| `--tolerancia`, `--salida` | Píxeles de margen; carpeta de láminas |

---

# LAS MEDICIONES, EN ORDEN CRONOLÓGICO

> Se conservan todas porque **la evolución es el dato**: muestra qué arreglo
> movió qué número, y cuáles eran ilusiones.

## 4-sep · Primera medición (24 láminas, 1.436 velas)

| Eslabón B | |
|---|---|
| Máximo y mínimo exactos (±1 px) | 94,4% |
| Cuerpo exacto | 92,7% |
| Alcista/bajista | 97,8% |

## 5-sep · Tras atacar las velas truncadas (paleta de fondos + ventana ×5)

| Eslabón B | 4-sep | 5-sep |
|---|---|---|
| Máximo y mínimo | 94,4% | **96,7%** |
| Cuerpo | 92,7% | **95,8%** |
| Dirección | 97,8% | **98,4%** |

| Eslabón C | acierta | encuentra |
|---|---|---|
| BOS | 99,8% | 88,0% |
| Barrida | 93,7% | 93,2% |
| FVG | 86,8% | 98,1% |
| Order block | 81,8% | 91,4% |

⚠️ **Estos números eran optimistas**: el banco le daba al extractor las
columnas verdaderas de **todas** las velas y el paso verdadero.

## 6-sep · Primer agujero: las velas que faltan

Quitando el 14% de las velas: FVG 86,8 → **62,8**; OB 81,8 → **63,8**;
"encuentra" cae en todas. Con la rejilla: FVG 84,7 · OB 82,5 · BOS encuentra
98,1. (Tabla completa en el doc 02.)

## 9-sep · Segundo y tercer agujero: marca de agua y verticales

| Máximo y mínimo exactos | Sin nada | Solo marca de agua | Marca + verticales |
|---|---|---|---|
| | 96,3% | 85,8% | 82,9% |

⚠️ El 2,9 de las verticales **engaña por poco**: en el banco caen al azar y
tocan 1–2 velas de 60, pero cuando tocan **destruyen la vela entera**. En el
mundo real no caen al azar: el borde de una caja de sesión cae en la apertura
de la killzone, **justo donde entra un trader de ICT**. En la cuarta captura
del dueño cruzaba las columnas de su entrada y de su stop.

Raíz común: se asumía **un** fondo por fila y hay varios → fondo en dos
dimensiones.

## 9-sep · Cuarto agujero: los dibujos del trader

Con dibujos encima: máximos y mínimos 91,9 → **85,6%**. Seis intentos de
separarlos con píxeles, todos fallidos. Hallazgo: el daño **no está donde está
el dibujo** en cuatro de cada cinco casos.

## 9-sep · Liquidez y estructura (mínimo de 3 semillas, 24 láminas)

| Familia | Acierta |
|---|---|
| Liquidez completa (nivel + forma + estado) | 73,2% |
| · solo el nivel | 84,1% |
| · tomada / sin tomar | 82,5% |
| · LRL / HRL | 75,4% |
| DOL | 80,4% |
| Estructura | 84,5% |
| MSS | 87,0% |
| Tendencia | 87,5% |

⚠️ Ese día se descubrió que **toda la tabla llevaba días atrasada**: FVG decía
71,9 y medía 86,3; OB 68,9 → 83,5; manipulación 69,2 → 81,4. Se habían fijado
el día que se estrenó la marca de agua y no se re-midieron al arreglarla.

## 13-sep · 🔴 SÉPTIMO AGUJERO, el más caro: el paso regalado

El banco le pasaba a la cadena el paso entre velas **sacado de su propia
verdad**. Nunca probaba al estimador. Al quitarle la chuleta:

| | Con chuleta | Sin chuleta |
|---|---|---|
| Máximo y mínimo exactos | 85,9–88,7% | **70,1%** |
| Dirección | 93–97% | **84,3%** |
| Láminas con el paso mal | — | **75%** |

El estimador viejo acertaba **18 de 80** láminas.

## 16-sep · Medidor del paso nuevo (`paso_por_huecos`): 78–79 de 80

| | Antes | Después |
|---|---|---|
| Láminas con el paso mal | 75% | **4–11%** |
| Máximo y mínimo exactos | 70,1% | **85,5–91,3%** |
| Dirección | 84,3% | **92,3–96,5%** |

Se recuperó el nivel que se creía tener, pero esta vez es real.

⛔ Descartados por el banco: rellenar huecos cortos por píxeles (53/80 → 43/80)
y pesar la confianza por número de velas (arregla una captura, rompe dos).

## 16-sep · ✅ LA TABLA VIGENTE (primera honesta; tras arreglar los giros empatados)

72 láminas × 3 semillas (7, 11, 23). **Se usa el mínimo.**

| Familia | s7 | s11 | s23 | **Se usa** |
|---|---|---|---|---|
| BOS | 95,9 | 96,8 | 96,6 | **95,9** |
| Barrida | 90,4 | 86,8 | 90,6 | **86,8** |
| FVG | 81,4 | 82,1 | 81,9 | **81,4** |
| Estado del FVG | 74,2 | 75,7 | 76,7 | **74,2** |
| Order block | 73,6 | 76,5 | 78,2 | **73,6** |
| Manipulación | 80,7 | 74,0 | 81,3 | **74,0** |
| Liquidez | 76,2 | 74,4 | 75,0 | **74,4** |
| Estructura | 83,3 | 84,8 | 83,9 | **83,3** |

Familias con pocos casos por lámina — **144 láminas × 2 semillas**:

| Familia | s7 | s11 | **Se usa** |
|---|---|---|---|
| MSS / CHoCH | 69,4 | 73,1 | **69,4** |
| DOL | 80,6 | 83,3 | **80,6** |
| Tendencia | 75,7 | 79,2 | **75,7** |
| Acumulación (zona) | 93,7 | 93,9 | **93,7** |
| Zona premium/discount/equilibrio | 90,1 | 94,4 | **90,1** |
| Banda OTE | 94,3 | 95,8 | **94,3** |
| Rango (los 2 giros exactos) | 68,1 | 71,8 | 68,1 |

Acumulación con tres listones: puntas exactas 70,2% · con ±1 vela 74,5% ·
**zona que pisa a la real en más de la mitad 92,6–93,7%** (lo que se afirma).

**Efecto del arreglo de los giros empatados:** rango (2 giros) 67,1 → 72,9 ·
OTE 90,0 → 91,5 · premium/discount 94,3 → 91,7 · BOS 97,0 → 95,9 ·
estructura 85,2 → 83,3; y **lo que encuentra sube en todo** (BOS +1,4,
barrida +3,1, estructura +2,9, liquidez +2,3, MSS +7 a +9, rango +6,9).
*Afirma un pelín peor y ve bastante más.*

## 15-nov · Comprobación al armar este expediente

Tanda corta (12 láminas, semilla por defecto) corrida en un entorno limpio para
confirmar que el banco funciona: paso mal en 0 de 12 · máximo y mínimo 88,8% ·
dirección 97,1% · BOS 98,9% · barrida 87,5% · FVG 83,3% · OB 80,0%. Coherente
con la tabla. ⚠️ Con 12 láminas las familias raras bailan mucho (MSS salió
53,6% sobre 21 casos): **no usar tandas cortas para fijar números.**

---

## Reglas para leer y mantener estos números

1. **Mínimo de las semillas, nunca la media.** Si el número se le enseña a un
   cliente como "acierta X%", vale el peor que se haya visto.
2. **Para familias raras, subir las láminas, no las semillas.** Con 72 láminas
   el MSS dio 68,2 / 64,3 / 77,3; ese 64,3 lo habría **silenciado** por puro
   ruido. Con 144: 69,4 / 73,1.
3. **Los números viven en dos sitios de `analizador2.py`** (diccionario
   `PRECISION` y párrafo de la cabecera). Se cambian los dos o ninguno.
4. **Arreglar el código obliga a re-medir.**
5. **`rangop` (90,1) está a una décima de la raya de 90.** Es la primera a
   revisar en la próxima medición.
6. **Lo que el banco NO cubre:**
   - qué fib habría dibujado una persona (el 90,1% de premium/discount es
     contra *nuestra* definición de rango);
   - gráficos que se parezcan de verdad a un TradingView real: cajas de sesión
     **del mismo color exacto que una vela**, barra de herramientas, textos de
     cabecera. Por eso el paso acierta 78/80 aquí y falla en 3 de 6 capturas
     reales. **Mejorar la fábrica es el primer trabajo pendiente** (doc 08).

## Los siete "agujeros de fábrica"

Cada uno es un defecto del **banco** que tuvo el control de calidad en verde
mientras la cadena fallaba en la realidad:

1. Entregaba las columnas de **todas** las velas (el modelo se deja 14–27%).
2. No dibujaba la **marca de agua** de sesión.
3. No dibujaba **líneas verticales**.
4. No dibujaba los **dibujos del trader**.
5. No probaba **velas estrechas**.
6. El generador elegía a veces el color de la zona translúcida igual al de las
   velas → láminas ilegibles por las que se culpaba al extractor. Y "2,7
   puntos de daño de los fibs" eran culpa del generador.
7. **Regalaba el paso entre velas.**

**La regla que sale de los siete:** *si el dato se mide en producción, en el
banco también hay que medirlo.*
