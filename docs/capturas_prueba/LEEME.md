# Capturas para probar el extractor de gráficos

Carpeta **temporal**. Aquí van screenshots REALES de gráficos (TradingView, MT5,
móvil, con y sin indicadores) para medir la robustez de `tools/lee_grafico.py`.

🔴 **Por qué tienen que ser reales y no dibujados por Claude:** un gráfico
generado usa los colores y las formas que elige quien lo genera, así que el
extractor acierta el 100% siempre y no se aprende nada. Lo que puede romperlo es
justo lo que no se puede fabricar: el antialiasing de la plataforma, la
compresión del PNG, temas de color cualquiera, indicadores y cajas
semitransparentes pintadas ENCIMA de las velas, y capturas de móvil reescaladas.

Se borran cuando termine la prueba.

    python3 tools/lee_grafico.py --leer docs/capturas_prueba/X.png \
        --pintar out/lee_grafico/X_marcado.png

## `mes_long_ote.png` — MES 5m, trade LONG en el 0,5 del OTE (2026-09-09)
La cuarta, y la más DURA de las cuatro: **paso de 4,5 px por vela** (las otras
7,5 · 8 · 10,5) y unas 155 velas a lo ancho. En milésimas del ancho de imagen
son **3,0**, muy por debajo de las ~8 que necesita el modelo para separar una
vela de su vecina: obliga a recortar por tiras sí o sí.

🔑 Trae DOS pares de flechas y solo uno es el trade. El dueño: *«ignora las
primeras dos flechas de entrada y salida que radican en una vela individual,
esas no son»*. Es el control real de que los píxeles solos no bastan para
decidir cuál es la marca del trader — encuentran los dos pares y además dos
falsas, que son las etiquetas «0,62» y «0,705» del fib.

⚠️ Y un caso nuevo: **la entrada NO está marcada con flecha**. Entró en la línea
del 0,5 del fib y solo marcó con flecha la salida. Un detector que dé por hecho
"la primera flecha es la entrada" se equivoca aquí.

## `mnq_long_ote.png` — MNQ 5m, LONG en el 0,5 del OTE (2026-09-10)
La quinta, y la primera de **otro instrumento** (NASDAQ 100 E-mini). Mismo
tamaño de vela que la cuarta (~3 px) pero otro tema, otras cajas y otro
recorrido, así que sirve de control: si falla igual que la del MES, el problema
es del método; si falla distinto, es de esa captura.


🔑 **Trae una hipótesis del dueño que se puede FALSAR con aritmética**, y eso la
hace la mejor prueba que hemos tenido: *«no veía motivos para que el precio
volviese a buscar liquidez, consideraba que había mucha más liquidez superior —
aunque quizá pueda estarme equivocando»*. La familia `piscinas` (BSL/SSL)
calcula máximos y mínimos iguales y si esa liquidez sigue SIN TOMAR. O sea que a
esa duda suya se le contesta con números, no con opinión.

⚠️ Su gráfico lleva además tres niveles «SS» dibujados por su indicador —dos
arriba y uno abajo—. NO se leen: la cadena no mira un solo píxel de texto ni de
línea. Sirven de árbitro independiente, como hizo la marca de BoS/ChoCh con el
BOS de la vela x=886.

## `nq_5m_oct.png` — NQ1! 5m, 02-oct-2026. 🔴 **LA CADENA FALLA EN EL PRIMER PASO**
La sexta, y la primera **a ciegas**: el dueño la mandó **SIN construcción del
trade** a propósito —*"para ver qué logra detectar o analizar por sí solo"*—. Es
la prueba más limpia que hemos tenido, porque sin su texto la IA no puede
repetirle sus propias confluencias, que es como fallaron las variantes A y B.

🔴 **Y la prueba se contestó sola, antes de gastar una llamada: el estimador del
paso entre velas da 3,45 px donde el real es 5,84.** O sea que inventaría un
**69% más de velas de las que hay**, y con las columnas corridas todo lo demás
—colores, extremos, FVG, BOS— sale mal por construcción.

**Dos verdades independientes, las dos de cosas que la cadena NO lee:**
· el **eje de tiempo** — las etiquetas de hora están a 70,10 px y una hora son 12
  velas de 5m → **5,84 px/vela**;
· **contar las velas a mano** en una franja limpia (y=700-770) → mediana **6,00 px**.

Es la **TERCERA** captura real donde el paso falla, con `mes_5m` (4,09 donde 5,5)
y `mes_ote_perdedor` (6,27 donde 7,4). Las tres por lo BAJO, o sea que el sesgo
tiene una dirección y por tanto una causa, no es ruido.

⚠️ **NO afinar el estimador contra esta captura.** Ese es exactamente el pecado
original que dejó el estimador viejo acertando 18 de 80 láminas: se ajustó a las
cuatro capturas del dueño y no generalizaba. Esta sirve para encontrar el
MECANISMO; el arreglo se valida en el banco y tiene que arreglar las tres.

⚠️ Novedades de esta captura que las cinco anteriores no tenían, cualquiera de
ellas puede ser la causa: **la barra de herramientas de TradingView a la
izquierda** (columnas 0-8 oscuras de arriba abajo, un borde vertical perfecto de
865 px); **tema claro con cajas de sesión grises encima**, así que el fondo local
de una vela no es blanco sino gris; e **instrumento nuevo** (NQ1! entero, no
MNQ/MES). Descartado ya que sea la barra: quitándola el paso sigue dando 3,45.
