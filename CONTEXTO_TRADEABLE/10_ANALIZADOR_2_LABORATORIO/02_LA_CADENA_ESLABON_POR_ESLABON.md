# 02 · LA CADENA, ESLABÓN POR ESLABÓN

> Cada pieza vive en `tools/`. Programa que las encadena: `tools/analizador2.py`
> (función `analiza()`). Ninguna importa nada del sitio.

```
captura → [1 panel+paso] → [2 columnas] → [3 rejilla] → [4 extenso] → [5 dirección]
        → [6 precio] → [7 hechos] → BLOQUE DE HECHOS → (laboratorio) → IA redacta
```

---

## Eslabón 1 — Encontrar el panel y el paso entre velas
**Archivo:** `recorta_grafico.py` · **Con qué:** solo píxeles

**Para qué:** saber dónde está el área de velas y cuántos píxeles hay de una
vela a la siguiente ("el paso"). Con eso se parte la imagen en **tiras** de
menos de ~80 velas (regla de las 8 milésimas) para mandárselas al modelo.

**Cómo:**
- La señal son los **bordes verticales** (cambio de color entre una columna y
  la siguiente), no "la tinta": contar píxeles que no son fondo satura cuando
  el fondo cambia a lo ancho (bandas de sesión). Medido: 424 de 424 filas.
- **El panel** se halla buscando las zonas cuyos bordes "laten" al ritmo de las
  velas. El eje de precios y las barras de herramientas tienen bordes pero no
  laten. No hay coordenadas fijas.
- **El paso** lo mide `paso_por_huecos()` (desde el 16-sep): cuenta de una vela
  a la siguiente, como una persona. Tres claves:
  1. se **juntan todas las franjas** horizontales en vez de elegir una;
  2. los **trozos de una misma vela se agrupan** (una vela hueca deja borde,
     mecha, borde: contando trozos el paso salía un tercio), con el corte
     calculado franja por franja y la moda sobre el conjunto;
  3. para afinar se usa la franja que **más concuerda** con el paso, no la más
     poblada (que es la más ruidosa).
- `_elige()` desempata entre candidatos mirando cuántas velas caen dentro de
  una casilla del tamaño del paso (con el paso doble salen dos montones).
- **El alto no se recorta** a propósito: detectarlo cortaba velas.
- Las tiras se **solapan** unas velas para que ninguna quede partida.

**Estado:** 🟡 78–79 de 80 láminas del banco. 🔴 **Falla en 3 de 6 capturas
reales, siempre por lo bajo** (ver doc 05). Es el fallo abierto nº 1.
Escape manual: `--paso N` fuerza el valor medido a mano.

**Histórico:** el estimador viejo (`paso_velas`, por periodicidad) acertaba 18
de 80: se había afinado contra cuatro capturas del dueño y no generalizaba.

---

## Eslabón 2 — ¿En qué columna está cada vela?
**Archivo:** `cajas_ia.py` · **Con qué:** modelo de visión (Gemini)

**Para qué:** que el modelo devuelva, para cada vela de una tira, un recuadro.
**Solo se usa su rango de columnas (x).** Sus coordenadas verticales se tiran;
solo quedan como "guía" aproximada de por dónde anda la vela.

**Cómo:**
- Se le manda una tira y se le piden **todas** sus velas.
- Gemini responde en milésimas (0–1000); se convierten a píxeles.
- Lector tolerante a JSON cortado; caché en disco de las respuestas; reintenta
  503 pero **no** un 429 de cuota (reintentar gasta cuota).
- Las columnas se **guardan en disco** en cuanto se tienen
  (`out/analizador2/columnas_<imagen>.txt`): una corrida no se paga dos veces.
- Al juntar tiras, dos cajas cuyo centro dista menos de medio paso son la
  misma vela.

**Modelo por defecto:** `gemini:gemini-3.6-flash` (constante
`MODELO_POR_DEFECTO`). 🔴 Google retiró tres veces el modelo usado (2.5-flash-
lite, el alias `-latest`, 2.5-flash). **Nunca un alias `-latest`**: cambia el
modelo en silencio y dos corridas iguales miden cosas distintas.
`cajas_ia.py --modelos gemini` lista los que acepta la clave.

**Estado:** 🟢 centro a ≤1 px en recortes. ⚠️ **Se deja entre el 14% y el 27%
de las velas** sin devolver → por eso existe el eslabón 3.

---

## Eslabón 2-bis — Poner las columnas en su sitio
**Archivo:** `analizador2.py` (`normaliza_ancho`, `encaja_en_rejilla`,
`banda_de_las_guias`)

Tres correcciones que nacieron de fallos reales:
- **Mismo ancho para todas.** El modelo devolvía cajas de 5 a 12 px con velas
  cada 7,5: 23 de 104 se solapaban con la vecina y la franja contenía dos velas.
- **Encajar en la rejilla real.** "El fallo raíz": las columnas caían **a media
  vela** de donde estaban (desplazadas +3,5 px), a caballo entre una vela y el
  hueco siguiente. Tapó a todos los demás fallos durante una sesión entera.
- **Medir solo dentro de la franja del gráfico** que marcan las guías. Con la
  imagen entera, los colores de la barra de herramientas y del eje de tiempo
  contaminaban el cálculo del fondo y el BOS validado desaparecía.

---

## Eslabón 3 — Recuperar las velas que el modelo se dejó
**Archivo:** `rejilla_velas.py` · **Con qué:** solo píxeles

**Idea:** un gráfico de velas es una **rejilla**: las velas caen a intervalos
exactos. Las columnas devueltas son muestras de una recta `x = a + paso·k`.
Ajustándola se sabe dónde deberían estar las que faltan, sin gastar otra llamada.

**Pero no se inventan velas.** Cada hueco propuesto tiene que **demostrar** que
hay una vela: el juez son los bordes verticales (un cuerpo pinta un borde a
cada lado; una línea de fib o un sombreado no). El listón se calibra con las
velas que el modelo sí marcó en esa misma imagen.

La guía vertical de una vela recuperada se **interpola** entre sus vecinas.

**Por qué importa tanto** (banco, quitando el 14% de las velas):

| | Con todas | Faltando 14% | + rejilla |
|---|---|---|---|
| FVG, acierta | 86,8% | 62,8% | 84,7% |
| Order block, acierta | 81,8% | 63,8% | 82,5% |
| BOS, encuentra | 88,0% | 77,1% | 98,1% |
| Barrida, encuentra | 93,2% | 68,4% | 90,9% |

Una vela que falta **no deja un hueco visible**: la lista se cierra sobre sí
misma y todo lo de después parece razonable.

**Estado:** 🟢 (`test_rejilla.py` 15/15). 🔴 **Depende por completo del paso**:
con un paso corto, la rejilla "recupera" velas que no existen (pasó: 163 velas
donde había ~127).

---

## Eslabón 4 — Medir cada vela (máximo, mínimo, cuerpo)
**Archivo:** `afina_velas.py` (`afina`) · **Con qué:** solo píxeles

**Idea central:** no se busca "lo verde" ni "lo oscuro". Se calcula **el fondo
de cada fila** dentro de una ventana alrededor de la vela, y todo lo que se
aparta del fondo es tinta.

**Las claves, cada una nacida de un fallo medido:**
- **El fondo se elige de una PALETA** de los pocos fondos del gráfico (el del
  panel y el de una caja de sesión), no "el color más repetido de la fila". En
  una fila donde las velas vecinas ocupan más de media ventana, el más repetido
  era el color de las velas y la mecha medida **desaparecía**. Era el 73% de
  las velas mal medidas.
- **Ventana ancha: 5 veces la vela** (×3 → 94,3%; ×5 → 96,2%; más no mejora).
- **Una línea horizontal desaparece sola**: cruza toda la ventana, así que en
  su fila ella *es* el fondo. Además `mascara_lineas` las detecta sobre el
  panel entero.
- **`mascara_huecos`** se construye sobre la rejilla completa, no sobre las
  columnas recibidas (si no, el hueco de una vela ausente se usaría como fondo).
- **Altura máxima creíble en dos pasadas** (`tope_alto`): se miden todas, se
  toma la mediana y se vuelven a medir las que pasan de 3 veces esa mediana.
  Nació de dos velas de 425 px (mediana 70) enganchadas al borde de una banda
  de sesión.
- **Cuerpo contra mecha:** se mide la *extensión* de la tinta por fila (el
  cuerpo ocupa el ancho de la vela; la mecha, 1–3 px).
- **Los dibujos del trader** (flechas, fibs, cajas) se contaban como vela.
  `colores_de_vela` parte de que un gráfico tiene 2–3 colores de vela y un
  dibujo es de otro. Pero **seis intentos de separarlos solo con píxeles
  fracasaron**: una flecha mide 12×25 px y una vela 13×30. Lo que los distingue
  es saber *qué* son, y eso lo dice el modelo (`--pistas-dib` en el banco).

**Estado:** 🟡 **85,5–91,3%** de máximos y mínimos exactos (±1 px) en
condiciones reales. Es el fallo abierto nº 2.

---

## Eslabón 5 — ¿Alcista o bajista?
**Archivo:** `afina_velas.py` (`color_cuerpo`, `direccion`)

**Sin conocer la paleta del tema.** Dos pasos:
1. Se agrupan las velas por color de cuerpo en los dos más repetidos.
2. Para saber cuál grupo es el alcista se usa una propiedad del propio gráfico:
   **la apertura de una vela cae cerca del cierre de la anterior**. Se prueban
   las dos asignaciones y gana la que mejor encadena.

**El color se lee del INTERIOR del cuerpo**, no del cuerpo entero: las velas
del dueño (y las de TradingView por defecto) llevan un **contorno negro de
1 px**, y en una vela pequeña el contorno tiene más píxeles que el relleno.
Medido: 42 de 163 velas cambiaban de color al quitarles 1 px de borde.

**Estado:** 🟢 **92,3–96,5%**. 🔑 El "problema del color" que se persiguió dos
días no era del color: eran las columnas corridas por el paso mal medido.

---

## Eslabón 6 — De píxel a precio
**Archivo:** `eje_precio.py` · **Con qué:** modelo (dígitos) + píxeles (altura)

**El riesgo no es no leer: es leer mal un dígito.** 29.550 leído como 29.556
mueve todos los precios y el resultado sigue pareciendo razonable.

**El seguro es la redundancia:** todas las etiquetas del eje caen sobre la
misma recta. Cada par propone una recta; **gana la que más etiquetas
confirma**. Una lectura mala se queda sola. Si no hay consenso mínimo,
devuelve `None` y **el bloque sale sin precios**.

**Y otra vez el mismo reparto:** el modelo leyó los 26 números bien y los situó
mal (177 px de error). Arreglo: `bandas_del_eje` mide con píxeles la altura de
cada etiqueta; la tira del eje se manda **por trozos de proporción 3:1**; cada
lectura se engancha a la banda medida más cercana.

**Resultado en captura real:** escala de −0,4645 puntos/px, 22 de 26 etiquetas
de acuerdo; comprobación independiente contra la línea de break-even: **0,32
puntos de error** (~1 tick del MNQ).

**Límite que no detecta solo:** si el recorte corta el mismo dígito a todas las
etiquetas (29.560 → 9.560), concuerdan entre sí y el precio sale desplazado
20.000 puntos. Por eso existe `MARGEN_EJE`.

**Estado:** 🟢 (`test_eje_precio.py` 18/18).

---

## Eslabón 7 — Los hechos
**Archivo:** `hechos_grafico.py` · **Con qué:** aritmética sobre la serie OHLC

Documentado entero en `03_CATALOGO_DE_HECHOS.md`. `--probar` → 75/75.

---

## La salida: el BLOQUE DE HECHOS
**Archivo:** `analizador2.py` (`hechos`, `bloque`)

Texto plano con una línea por hecho, numerando las velas. **Tres niveles**,
decididos por el banco:

| Precisión medida de la familia | Cómo sale |
|---|---|
| ≥ 90% (`MIN_PRECISION`) | Se afirma en seco |
| ≥ 65% (`MIN_MENCION`) | Se escribe **con su tasa de acierto al lado** |
| < 65% | No se escribe |

Por qué tres y no dos: con dos, el analizador solo podía hablar de BOS y
barridas y jamás de un FVG o un order block. El dueño: *"¿por qué no ve los FVG
si están dibujados?"*

**Otras reglas del bloque:**
- **Un hecho, una vez** (un mismo nivel con dos nombres se lee como confirmación).
- **Sin precios si el eje no dio consenso** ("cerró por debajo del swing").
- **La ventana del trade partida en tres secciones** cuando se conoce la vela
  de entrada: (1) lo que ya estaba antes de entrar, (2) lo que hizo su propia
  vela de entrada, (3) lo que pasó después. El corte va por la **última** vela
  que menciona cada línea. Etiquetar no bastó: hacían falta secciones separadas.
- **Premium/discount solo si el trader da las anclas de su fib** (`--rango`).
  Sin ellas se imprime `AVISO_SIN_RANGO`.
- Parámetros: `K_SWING=3` (velas a cada lado para un giro), `max_velas=80` por tira.

---

## Piezas auxiliares

| Archivo | Para qué |
|---|---|
| `flechas.py` | Localiza las flechas de entrada/salida del trader (manchas de color vivo, compactas y pequeñas; la de más a la izquierda es la entrada). ⚠️ Su autoprueba falla con las librerías de hoy — ver doc 06. Alternativa: `--entrada-x` a mano. |
| `mapa_velas.py` | Dibuja el **número de cada vela** sobre la captura para que el dueño compruebe de qué vela habla el informe. Imprescindible. |
| `colores_velas.py` | Mide de qué color son las velas de una captura. **No da veredicto.** Regla de conducta (doc 06). |
| `lee_grafico.py` | El **primer** extractor (todo por píxeles, sin modelo). 100% en sintéticos, se hundió en capturas reales. Conservado como referencia. |
| `analizador_lab.py` | Compara respuestas: el sitio hoy contra el sitio con el bloque (doc 05). |
| `banco_cadena.py` | El juez (doc 04). |

## Dependencias del laboratorio

`numpy`, `Pillow`, `requests`; `scipy` solo para `lee_grafico.py` y
`flechas.py`. 🔴 **No están en ningún `requirements`** ni tienen versión fijada.
En el VPS se usan desde `venv/bin/python3`.
