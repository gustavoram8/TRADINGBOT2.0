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
