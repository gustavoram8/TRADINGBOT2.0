# 01 · DIAGNÓSTICO DE VISIÓN — por qué la IA sola no alcanza

> Tres estudios, en orden. Cada uno contestó una pregunta y abrió la siguiente.

---

## Estudio 1 — El banco de 30 casos (13–14 de agosto de 2026)

**Pregunta:** ¿qué tan bien analiza el sitio fuera de ICT, donde el dueño no
puede juzgar?

**Método:** gráficos sintéticos construidos desde la definición aritmética de
cada patrón, con "trampas": etiquetas y notas que **mienten** (razones
armónicas falsas, onda 4 que solapa a la 1, RSI "en 28" cuando el panel marca
50,5, cruce de medias que no existe, lecturas de volumen sin panel de volumen).

**Herramientas:** `tools/banco_analizador.py`, `corre_banco.py`,
`califica_banco.py`, `informe_banco_pdf.py`. Resultados:
`docs/banco_resultados/`, `_v2/`, `_v3/`.

**Resultado:**
- Trades normales: bien.
- **Trampas: 8–9 de 10 falladas.** La IA **cree lo que le dicen** en vez de
  medir. Llegó a escribir "el gráfico muestra claramente 0,618 / 0,786" cuando
  eran 0,50 / 0,618.
- La cláusula de verificación (ver doc 09) arregla lo grueso. Siguen ciegos:
  razones armónicas, solape de Elliott, cruce de medias.

**Lo que dejó:** la sospecha de que el límite es de **vista**, no de prompt.

---

## Estudio 2 — Agudeza visual (31 de agosto – 1 de septiembre)

**Pregunta:** ¿a partir de qué tamaño en píxeles deja de ver el modelo?

**Herramientas:** `tools/agudeza_visual.py` (genera, corre y tabula) y
`tools/verifica_agudeza.py` (comprueba midiendo los píxeles del PNG que la
"verdad" declarada es la que se dibujó: 168/168).

**Método:** 168 láminas de **1920×1080** (el tamaño de una captura real; hacerlas
pequeñas habría anulado la prueba porque GPT-4o reduce el lado corto a 768 px).
Siete familias; cada una varía **un solo número en píxeles**.

### Resultado sobre GPT-4o

| Capacidad | Umbral | Veredicto |
|---|---|---|
| Leer una etiqueta del eje (OCR) | 9 px (100% desde 12) | ✅ suficiente |
| Detectar un elemento fino | 2 px, 24 de 24 | ✅ excelente |
| Contar líneas | inestable, sesgo de +1 | ⚠️ regular |
| ¿Se cruzan dos medias? | azar | 🔴 no lo hace |
| ¿El precio rompió el nivel? | azar | 🔴 no lo hace |
| ¿El RSI está bajo la guía de 30? | azar | 🔴 no lo hace |
| ¿Se solapan dos zonas? | azar | 🔴 no lo hace |

### Los tres controles sin los cuales el resultado se lee al revés

1. **Mitad SÍ, mitad NO.** GPT-4o contestó "NO" en las 72 láminas de
   RSI + ruptura + solape. Sin balance, eso habría parecido 100% de acierto en
   los casos NO.
2. **Familia "presencia"** (una pregunta trivial de sí/no). 24 de 24 →
   demuestra que la imagen llega bien, que el modelo *puede* decir SÍ, y que
   sus "NO" eran lecturas reales y no una muletilla.
3. **Pregunta invertida** (`--invertir`). A "¿está bajo 30?" dice NO siempre; a
   "¿está sobre 30?" dice SÍ siempre. **La misma afirmación en las 24
   láminas.** No es azar ni negativa: es una lectura firme y equivocada.

### Dos arreglos caseros, probados

| Idea | Resultado |
|---|---|
| ⛔ **Pedirle coordenadas** y comparar nosotros | Error medio **93 px** (8,6% del alto). Las 24 respuestas múltiplos de 10: no mide, estima proporciones. Pero la correlación fue 0,94: sabe *aproximadamente* dónde está todo. No sirve para decidir; **sí para apuntar un recorte.** |
| 🟡 **Mandar la zona ampliada 3–4×** (`--zoom`) | Solo mejora la **topología**: "¿se tocan estas dos líneas?" pasó de 50% a 75%. RSI, ruptura y solape siguieron en 50%. |

### El diagnóstico fino

No es que "no sepa comparar". Distingue:
- **Topología** ("¿estas dos líneas se tocan?") → sí, si el objeto es grande.
- **Orden vertical** ("¿A está por encima de B?") → **no, a ningún tamaño.**

Y el orden vertical es la operación central del análisis técnico.

### Trampas del propio estudio (ya resueltas)

- Los errores 429 de la API se guardaban como respuesta y el normalizador
  sacaba dígitos del mensaje de error ("429" + "1" = "4291", que parecía una
  lectura del eje) → un 26% falso.
- Dos rectas de pendiente opuesta se cruzan **siempre**: los casos "NO" estaban
  dibujados como "SÍ".
- Zonas que se tapaban volvían ambiguo un solape de 1 px.
- Correr una sola familia sobrescribía el archivo de resultados (ahora fusiona).

---

## Estudio 3 — ¿Puede un modelo LOCALIZAR velas? (2–4 de septiembre)

**Pregunta distinta:** no "¿está por encima?", sino **"dime dónde está cada
vela, con coordenadas"**. Es la capacidad de *grounding* que algunos modelos
traen entrenada (Gemini) y GPT-4o no.

**Herramienta:** `tools/cajas_ia.py`. Guía para el dueño:
`docs/prueba_cajas_PASOS.md`. Se corre en el VPS (desde el contenedor de
desarrollo no se alcanza la API de Google).

### Primera captura real (MES 5m, con cajas de sesión, fibs, textos y flechas)

Se pidieron las 25 velas de la derecha:

| Medida | Resultado |
|---|---|
| Centro de la caja vs. centro de su vela | **≤ 1 px** |
| Velas sin caja | **0 de 25** |
| Error del borde superior (mediana) | 3,5 px |
| Error del borde inferior (mediana) | 8 px (tres casos de 30–37) |

Entre 10 y 25 veces más preciso que GPT-4o. Y no encajonó ni una línea de fib,
ni una caja de sesión, ni un texto.

**El veredicto del dueño, a ojo, coincidió con la medición:** *"pareciera saber
en dónde está la vela; lo que pareciera no saber es de dónde a dónde se
extiende."*

**De ahí el reparto:** el modelo no tiene que dar la medida, **solo la
columna**. Sabiendo la columna, el máximo y el mínimo salen recorriendo los
píxeles de esa franja.

### Segunda captura (MNQ 5m, 1818 px, 255 velas): falló

25 cajas repartidas sobre 64 velas; cada caja se comía 2–3.

### La regla de las 8 milésimas

Gemini no devuelve píxeles: devuelve **milésimas del ancho** (0–1000), y su
caja mide ~8 milésimas mandes lo que mandes.

| | MES | MNQ |
|---|---|---|
| Ancho de la imagen | 778 px | 1818 px |
| Ancho de la caja | 5 px | 15 px |
| En milésimas del ancho | 6,4 | 8,3 |

**Una vela solo se separa de su vecina si ocupa más de ~8 milésimas del ancho
de la imagen**, es decir, si en la imagen caben **menos de ~125 velas**.

⚠️ Se le pidió al dueño que "acercara el gráfico" y **era el consejo
equivocado**: lo que manda no son los píxeles por vela, sino cuántas velas
caben a lo ancho.

### La solución: recortar

`cajas_ia.py --recorte x0,y0,x1,y1` manda solo un trozo y pide **todas** sus
velas. Recortar no mejora la imagen: **cambia el denominador.**

| | Imagen entera | Recorte |
|---|---|---|
| Ancho de caja | 15 px | 7 px (velas de 6) |
| Velas por caja | 2–3 | **1** |
| Velas sin marcar | 2 de 25 | **0 de 93** |
| Error del centro (mediana) | 1 px | **0 px** |

**Consecuencia para el producto:** no se le pide nada al cliente. El programa
recorta solo, manda por tiras y junta.

---

## Qué quedó sin probar

- **Otros modelos de visión** en las familias donde GPT-4o da azar (RSI,
  ruptura, solape): 72 láminas, menos de $0,50 y 15 minutos por candidato. Con
  la cadena ya no es urgente, pero sería la forma barata de saber si algún
  modelo razona espacialmente.
- **Detectores entrenados** (familia YOLO) para localizar velas sin depender de
  un servicio externo. No se midió.
