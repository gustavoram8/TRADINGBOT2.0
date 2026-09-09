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
