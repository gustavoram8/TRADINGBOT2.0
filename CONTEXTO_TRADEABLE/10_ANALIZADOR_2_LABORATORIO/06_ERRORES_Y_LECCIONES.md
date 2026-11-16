# 06 · ERRORES, CALLEJONES SIN SALIDA Y LECCIONES

> Este documento existe para que **nadie tenga que volver a tropezar con lo
> mismo**. Cada entrada costó horas o días. Lo que lleva ⛔ se probó y se
> descartó con medición: no reintentarlo sin un motivo nuevo.

---

## A. Lo que se probó y NO funciona (⛔)

| Idea | Qué pasó |
|---|---|
| ⛔ **Mejorar el prompt para que la IA "verifique"** | Mejora lo grueso; lo fino (razones, solapes, cruces) sigue ciego. Y a veces afirma que verificó sin poder. |
| ⛔ **Pedirle a GPT-4o coordenadas** y comparar en código | Error medio de 93 px. No mide: estima proporciones. |
| ⛔ **Mandar la zona ampliada 3–4×** | Solo arregla "¿se tocan?". El orden vertical sigue en azar. |
| ⛔ **Darle a la IA la tabla completa de precios** (variante F) | No deduce ni un BOS. Devuelve la pregunta. |
| ⛔ **Darle una lista de hechos SIN verificar pidiéndole desconfianza** (primera variante C) | Se inventó dos referencias. |
| ⛔ **Prohibirle por escrito inventar referencias** (variante D) | Inventó la vela 141. La prohibición no sustituye a la auditoría. |
| ⛔ **Extraer velas solo con píxeles, sin modelo** (`lee_grafico.py`) | 100% en gráficos sintéticos; hundido en la primera captura real (colores no estándar, cajas translúcidas, fibs con altura de doji). |
| ⛔ **Pedirle al cliente que acerque el gráfico** | Consejo equivocado: lo que manda es cuántas velas caben a lo ancho. La solución es recortar nosotros. |
| ⛔ **Pedir ~120 velas de una vez a Gemini** | Escribe más de 5 minutos y la petición se agota. Por tiras de ≤80. |
| ⛔ **Filtrar los FVG pequeños** (mínimos de 2, 3, 4 y 6 px) | La precisión no se movió: los FVG falsos no son pequeños, salen de velas mal medidas. |
| ⛔ **Abstenerse en la vela "dudosa"** | Ninguna señal calculable separa bien: para cazar el 46% de las malas hay que marcar el 9% de las buenas. |
| ⛔ **Recortar el alto del panel** | Devolvía y=240–640 sobre un panel de 200–800 y cortaba velas. |
| ⛔ **Paso por periodicidad bajando a la mitad** (estimador viejo) | 18 de 80 láminas. Dos criterios de "aceptar la mitad" probados y descartados. |
| ⛔ **Puntuar el paso por "cuánta tinta cae en la casilla"** | Con el paso doble sale parecido; ganaba el doble. |
| ⛔ **Rellenar huecos cortos por píxeles** al medir el paso | 53/80 → 43/80: una línea punteada funde velas. |
| ⛔ **Pesar la confianza del paso por número de velas** | Arregla una captura y rompe dos. |
| ⛔ **Clasificar fondos por paleta para el paso** (octubre) | Paso mal en 4–8% → 15% de las láminas, y borraba las velas alcistas del dueño. Revertido. |
| ⛔ **Separar los dibujos del trader solo con píxeles** | Seis intentos. Una flecha (12×25 px) y una vela (13×30) son el mismo objeto. Hace falta que el modelo diga qué es. |
| ⛔ **Construir `mascara_huecos` con las columnas recibidas** | Mide peor que no hacer nada: el sitio de una vela ausente se usaría como fondo. |
| ⛔ **Medir sobre la imagen entera** en vez de la franja del gráfico | El BOS verificado desaparecía y salían otros tres. |
| ⛔ **Decidir alcista/bajista por el color más repetido del cuerpo** | El contorno negro gana la votación en velas pequeñas. Se lee el interior. |
| ⛔ **Dos reglas automáticas para decidir "vela o fondo" por color** | Fallaron en direcciones opuestas. La máquina mide; la persona decide. |
| ⛔ **Etiquetar "en ese momento / en la última vela" dentro de cada línea** | La IA las mezcla igual. Hacen falta secciones separadas. |
| ⛔ **Tendencia contando las últimas 4 etiquetas** | Un LL de 29 velas atrás arrastraba el veredicto. |
| ⛔ **Afirmar premium/discount con el rango automático** | No es un hecho, es una elección del trader. |
| ⛔ **Usar un alias de modelo `-latest`** | Google lo cambió en silencio; la misma orden empezó a fallar. |
| ⛔ **Reintentar un error 429 de cuota como un 503** | Reintentar cuota gasta cuota. |

---

## B. Los fallos que costaron más

### B1. El banco le regalaba la respuesta a la pieza que probaba
Durante semanas el control de calidad estuvo en verde mientras el dueño veía
fallos en su gráfico. Siete veces el defecto estaba en el **banco**, no en la
cadena (lista en el doc 04). El más caro: le pasaba el paso entre velas
verdadero.
**Lección:** *si el dato se mide en producción, en el banco también.*

### B2. Las velas "huecas" (error reincidente, más de cinco veces)
Se afirmó una y otra vez que las velas del dueño eran huecas. Son **rellenas**.
Él lo corrigió cada vez; a las pocas semanas, con una captura nueva, se volvía
a caer. Sus palabras: *"eres como un laberinto sin salida"*.

- **De dónde venía:** el banco sí dibuja velas huecas; un hallazgo cierto
  *sobre el banco* se arrastró a sus capturas. Y un corte de píxeles muestra un
  interior más claro que el borde (el relleno gris claro), que "parece" hueco.
- **La trampa que lo hace reincidir:** en `nq_5m_oct` la caja de la sesión de
  Asia y su vela alcista son el **mismo RGB** (206,208,213).
- **El arreglo es de método, no de código:**
  1. regla al principio de `CLAUDE.md`;
  2. ficha por captura dictada por él: `docs/capturas_prueba/velas.md`;
  3. `tools/colores_velas.py`, que mide anchos y colores y **no da veredicto**;
  4. sin ficha, **se le pregunta**. Prohibido escribir "parecen huecas".

### B3. Dos días persiguiendo el color cuando la causa era el paso
Seis colores de cuerpo donde hay dos, 37 velas leídas como negro. El color
nunca fue la causa: con el paso mal, las columnas caían corridas y se leía el
borde de la vecina. Arreglado el paso, 37 → 3.
**Lección:** *cuando el dueño insiste tres veces en lo mismo, la causa está en
otra parte.*

### B4. El laboratorio le daba a la IA la tesis de OTRO trade
Los valores por defecto de `analizador_lab.py` llevaban las confluencias, la
dirección y la sesión del trade de septiembre. La prueba "a ciegas" de octubre
llamó short a un long y citó confluencias que nadie dijo. Lo cazó el dueño.
**Lección:** *un valor por defecto que describe un caso concreto es una mentira
con apariencia de configuración.* Hoy todo lo no declarado va como
`NOT PROVIDED — … Do NOT assume a value.`

### B5. Pruebas degradadas que no se anuncian
- Con el modelo de Gemini retirado, la corrida siguió **sin eje de precios** y
  el resultado parecía válido.
- Sin archivo de columnas, las variantes C y E salían **vacías** y el programa
  decía "guardado".
**Lección:** *una prueba degradada que no avisa es peor que una que falla.* Hoy
el laboratorio se detiene con un mensaje claro.

### B6. La tabla de precisión desactualizada
El bloque le decía a la IA "acierta 72%" de algo que acertaba 86% (y antes, lo
contrario). Y los números viven en **dos sitios** de `analizador2.py`.
**Lección:** *arreglar el código obliga a re-medir, y se cambian los dos sitios.*

### B7. Afinar contra las capturas del dueño
El estimador viejo del paso "funcionaba" en sus cuatro capturas y acertaba 18
de 80 láminas.
**Lección:** *sus capturas sirven para encontrar el mecanismo; el arreglo se
valida en el banco.*

### B8. Numeración de velas inverificable
El informe decía "la vela 149" y el dueño no tenía cómo saber cuál era.
**Lección:** *lo que no se puede señalar no se puede verificar.* → `mapa_velas.py`.
Además, la entrada se anotó como vela 122 y era la 123.

### B9. Contar la misma cosa varias veces
La misma ruptura salía como tres BOS; los order blocks, repetidos; un nivel,
con dos nombres. **Un hecho repetido se lee como confirmación.**

### B10. Usar el futuro para juzgar el pasado
La IA culpó al trader por zonas aparecidas siete velas después de su entrada.
**Lección:** cortar la serie en la vela de entrada; ventana en tres secciones.

---

## C. Fallos de entorno y operación

| Fallo | Detalle |
|---|---|
| **El contenedor de desarrollo no llega a Google ni a OpenAI** | Todo lo que llama a un modelo se corre en el VPS. |
| **Una sesión SSH no hereda las variables de supervisor** | La clave se busca en el entorno, en `scalpel/.env` y en la línea `environment=` de supervisor. |
| **`scipy` no está en el VPS** | La cadena principal se liberó de esa dependencia; `lee_grafico.py` y `flechas.py` aún la usan. |
| **Google retiró el modelo tres veces** | 2.5-flash-lite, el alias `-latest`, 2.5-flash. Hoy: `gemini-3.6-flash`. Puede volver a pasar: `cajas_ia.py --modelos gemini`. |
| **Cuota gratuita** | 429 por minuto ≠ 429 por día; el texto del error se muestra. Las columnas se guardan en cuanto llegan. |
| **El dueño pegó un comando del VPS en PowerShell de su PC** | Primero hay que entrar por SSH. Comandos en **una sola línea**, sin `\`. |
| **Ruta de columnas equivocada** (`docs/columnas/` vs `out/analizador2/`) | El laboratorio ahora las busca solo. |
| **El sistema convierte comillas rectas en curvas al pegar** | Dar bloques listos para copiar. |
| 🔴 **`flechas.py --probar` da 0/4 en un entorno limpio** (2026-11-15: numpy 2.4.6, Pillow 13.0, scipy 1.17) | Sobredetecta: encuentra las dos flechas buenas y cuatro falsas. **Falla igual en el commit donde se creó**, así que no es una regresión del código: depende de la versión de las librerías. No investigado. Mientras tanto: `--entrada-x`. |
| 🔴 **Las dependencias del laboratorio no están fijadas** en ningún archivo | Consecuencia directa del punto anterior. Hay que crear un `requirements` propio con versiones. |
| **Notas con datos viejos** | `LEEME.md` de capturas habla de "paso de 4,5 px" y "155 velas" para capturas que hoy miden otra cosa; `velas.md` y `CLAUDE.md` decían "caja de NY PM" donde es la de Asia (corregido al armar este expediente). |

---

## D. Las lecciones, en limpio

1. **La IA redacta; no mide ni deduce.** Lo que deba saber, se calcula en código.
2. **El modelo dice qué y aproximadamente dónde; los píxeles, exactamente dónde.**
3. **Medir cada eslabón por separado**, o no se sabe cuál falló.
4. **Dos cifras por familia:** cuánto acierta de lo que afirma, y cuánto
   encuentra de lo que hay.
5. **La verdad tiene que ser por construcción**, y hay que verificar que lo
   dibujado es lo declarado midiendo la propia imagen.
6. **Controles contra la adivinanza:** mitad sí/mitad no, pregunta trivial,
   pregunta invertida.
7. **Mínimo, no media**; más láminas, no más semillas, para lo raro.
8. **El banco debe medir todo lo que producción mide**, y parecerse a lo real.
9. **Una fuente independiente vale más que cien láminas** (el indicador del dueño).
10. **Leer las respuestas a mano.** Los calificadores automáticos dieron verdes
    y rojos falsos.
11. **Auditar las velas citadas** contra el bloque, siempre.
12. **Fallar ruidosamente.** Nada de degradarse en silencio.
13. **Sin valores por defecto con contenido.**
14. **Fijar versiones:** del modelo y de las librerías.
15. **Que el dueño pueda comprobarlo a ojo.** Es parte del método, no cortesía.
16. **Un experimento con grupo de control que "sale mal" está funcionando.**
