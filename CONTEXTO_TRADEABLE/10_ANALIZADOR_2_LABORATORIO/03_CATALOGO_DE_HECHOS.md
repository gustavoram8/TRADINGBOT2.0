# 03 · CATÁLOGO DE HECHOS — qué sabe calcular la cadena

> **Archivo:** `tools/hechos_grafico.py` (1.420 líneas).
> **Autoprueba:** `python3 tools/hechos_grafico.py --probar` → **75/75**.
> Cada escenario de prueba se **construye** sabiendo en qué vela está el hecho
> y se exige que el detector lo encuentre **en ese índice exacto**.
>
> **Entrada de todas las funciones:** la serie de velas como lista
> (apertura, máximo, mínimo, cierre), en píxeles o en precio — da igual, son
> comparaciones. `k` = velas a cada lado para considerar un giro (se usa `k=3`).

**Idea de fondo:** nada de esto es percepción ni opinión. Son **definiciones**,
y una definición se calcula.

```
ruptura de nivel    →  cierre > nivel
midpoint tocado     →  mínimo ≤ CE ≤ máximo
liquidez tomada     →  mínimo < mínimo previo  Y  cierre por encima
FVG                 →  mínimo[i] > máximo[i-2]
```

---

## La base: giros (`swings`)

Una vela es **giro alto** si su máximo supera al de las `k` velas de cada lado
(giro bajo, al revés). Sin giros no hay BOS ni liquidez.

- Las `k` primeras y últimas velas **no pueden** ser giro (les falta un lado).
- 🔴 **El empate se permite por la izquierda (`>=`) y no por la derecha (`>`).**
  Con `>` estricto en ambos lados, dos velas contiguas con el mismo máximo se
  anulaban y **el giro desaparecía** — y dos máximos iguales son justo un EQH.
  En una serie medida en píxeles los empates son constantes. De una tanda de
  iguales queda la **última**, que es donde el precio se dio la vuelta.

## Rupturas

| Hecho | Función | Definición |
|---|---|---|
| **BOS** | `bos` | Un **cierre** más allá del giro previo. (Una mecha no rompe.) |
| **BOS como evento** | `bos_eventos` | **Uno por giro roto**, en el instante de la ruptura. `bos()` devuelve también todas las velas que siguen cerrando al otro lado (la misma ruptura contada varias veces); esto es lo que se le enseña a una persona. |
| **MSS / CHoCH** | `mss` | El BOS que va **en contra** del anterior: el control cambió de manos. El primer BOS del gráfico nunca es un MSS. Sale como cláusula de la línea del BOS, con tasa propia. |

## Huecos e imbalances

| Hecho | Función | Definición |
|---|---|---|
| **FVG** | `fvgs` | Tres velas: alcista si el mínimo de la 3ª queda por encima del máximo de la 1ª. Trae su **CE** (la mitad exacta). |
| **Estado del FVG** | `estado_fvgs` | `intacto` (no volvió) · `tocado` (entró sin llegar al CE) · `ce` (llegó a la mitad) · `lleno` (lo recorrió entero) · `invertido` (**cerró** al otro lado). Tocar no es cerrar. |
| **IFVG** | `invertidos` | Un FVG atravesado por un **cierre**, que pasa a actuar al revés. |
| **Order block** | `order_blocks` | La última vela de dirección **contraria** justo antes del desplazamiento que abrió un FVG. Sin FVG detrás no hay desplazamiento y es una vela cualquiera. Un OB ya atravesado por un cierre deja de contar como obstáculo. |

## Liquidez

| Hecho | Función | Definición |
|---|---|---|
| **Barrida** | `barridas` | La mecha pasa un giro previo y la vela **cierra de vuelta dentro**. Si el cierre también queda fuera, es una ruptura, no una barrida. |
| **Mapa de liquidez** | `liquidez` | Cada nivel con cuatro datos: **lado** (BSL arriba / SSL abajo) · **forma** (giro suelto, EQH/EQL si los extremos son iguales, REQH/REQL si solo se parecen) · **estado** (tomada, y en qué vela / sin tomar) · **resistencia del camino** (LRL / HRL) si sigue sin tomar. |
| **Obstáculos** | `obstaculos` | Zonas de sentido contrario (FVG sin rellenar y OB) entre el precio y un nivel. Cero = **LRL**; una o más = **HRL**. Se mira solo hasta la vela de referencia, nunca después. |
| **DOL** | `dol` | Qué liquidez queda **sin tomar** arriba y abajo, a qué distancia y con cuánto estorbo. **No predice** cuál buscará el precio (sería una señal). |
| *(histórico)* | `piscinas` | Niveles con 2 o más toques, promediados. La absorbió `liquidez`; se conserva porque el banco la sigue midiendo. |

Decisiones de diseño de la liquidez:
- **Dos tolerancias, en fracción del rango mediano de la vela**, no en puntos
  (5 puntos son dos velas en el MES y un cuarto de vela en el NQ).
- **El nivel de un grupo es el extremo, no la media**: los stops duermen sobre
  el máximo más alto.
- **Un giro suelto también es liquidez.**
- Se agrupan **giros**, no todas las velas (un lateral de 20 velas daba "un
  nivel con 19 toques").
- Al agrupar se compara contra el **primer** nivel del grupo (si no, una deriva
  larga se traga el gráfico).
- **Qué se escribe:** toda la que sigue sin tomar; de la ya tomada, solo la de
  2 o más toques (la de un giro suelto ya la cuenta la familia "barrida").

## Estructura

| Hecho | Función | Definición |
|---|---|---|
| **Etiquetas** | `estructura` | Cada giro contra el anterior **de su mismo tipo**: HH, LH, HL, LL. Nunca alternando alto con bajo. El primero de cada tipo no lleva etiqueta. |
| **Tendencia** | `tendencia` | El **último** máximo contra el **último** mínimo: HH + HL = alcista; LH + LL = bajista; una sube y otra baja = **mixta**. |

🔑 "Mixta" no es una evasiva: es el estado más informativo (tras un solo LH la
estructura ya no es limpiamente alcista, y ahí se toman los peores trades).
⚠️ La versión vieja *contaba* las últimas 4 etiquetas y un LL de 29 velas atrás
arrastraba el veredicto; la cazó el dueño leyendo un informe.

## Rango operativo (premium / discount / OTE)

| Hecho | Función | Definición |
|---|---|---|
| **Rango del trader** | `rango_de` | Las dos anclas que dio **el trader** (mínimo de una vela, máximo de otra). Extremos exactos. |
| **Rango automático** | `rango_operativo` | El último giro alto contra el último bajo. `pierna` indica en qué orden vinieron. |
| **Ubicación** | `ubica` | Mitad (premium / discount / **equilibrio**), retroceso (0 = fin de la pierna, 1 = inicio) y si cae en la banda **OTE 0,62–0,79**. |

🔴 **Premium y discount no dependen de la dirección de la pierna** (premium es
la mitad de arriba, siempre). Lo que depende es el retroceso.

🔴 **El rango operativo no es un hecho: es una elección.** Sobre un trade real,
el dueño ancló su fib en las velas 117–120 y la cadena en la 99–121. Con el
suyo entró en *discount dentro de la OTE*; con el nuestro, en *premium*. Las
dos lecturas son legítimas. Por eso **el bloque solo afirma premium/discount si
el trader dice dónde ancló** (decisión del dueño, octubre).

## Patrones compuestos

| Hecho | Función | Definición |
|---|---|---|
| **Pierna de manipulación** | `manipulacion` | Una barrida **+** una reacción contraria inmediata (FVG o BOS al otro lado) dentro de una ventana de velas. Sin reacción es solo una mecha larga. |
| **Acumulación / rango** | `acumulacion` | Tramo donde las velas se pisan. Medida sin unidades: ancho del tramo ÷ suma de los rangos de sus velas. Segunda condición: el ancho no puede crecer más de un tope al añadir una vela (si no, el tramo lateral se come el inicio del impulso). Se afirma como **zona** ("en torno a"), no con puntas exactas. |

## Dos relojes

Algunos hechos se miden "en la última vela" y otros "en el momento de la
entrada". El bloque dice cuál es cuál, y cuando se conoce la entrada **se corta
el futuro de verdad**: `dol` y `obstaculos` trabajan sobre la serie recortada.

---

## 🔴 Lo que el catálogo NO tiene todavía

| Falta | Por qué importa |
|---|---|
| **Displacement** como hecho propio | Hoy solo existe implícito (el que abre un FVG). Es la "causa" que un trader de ICT nombra. |
| **Inducement** | Liquidez-cebo antes del punto de interés. |
| **Kill zones / horario** | La cadena **no lee el eje de tiempo**. No sabe en qué sesión cae cada vela. (El sitio de producción llegó a afirmar mal esto.) |
| **Breaker / mitigation block** | No calculados. |
| **Medias móviles, RSI, MACD, volumen** | Fuera por completo. Son paneles o líneas, no velas. |
| **Patrones clásicos, armónicos, Elliott, Wyckoff por fases** | No hay detectores. Hoy el 2.0 solo cubre el vocabulario ICT/SMC. |
| **Temporalidad mayor** | Solo se ve la captura. Un "MSS de 1H" no se puede verificar en una de 5m. |
| **SL / TP / R:R del trade** | No se leen las cajas de posición del trader. |

**Regla demostrada (variante F del laboratorio):** si un hecho no está
calculado en código, la IA **no lo deduce** aunque tenga la tabla completa de
precios delante. Todo lo que se quiera que el analizador sepa decir hay que
programarlo aquí y medirlo en el banco.

## Cómo se añade una familia nueva

1. Escribir la función en `hechos_grafico.py` con su definición exacta.
2. Añadir escenarios `esc_*` construidos a mano y sumarlos a `probar()`.
3. Enseñarle al banco a calcular la **verdad** de esa familia y a puntuarla
   (`banco_cadena.py`: `_hechos` y la tabla por familia).
4. Medir con al menos 3 semillas (familias con pocos casos: subir las láminas a
   144, no las semillas) y tomar el **mínimo**.
5. Poner ese número en **los dos sitios** de `analizador2.py`: el diccionario
   `PRECISION` y el párrafo de la cabecera.
6. Añadir su redacción en `bloque()`.
