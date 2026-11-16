# 08 · QUÉ FALTA Y HOJA DE RUTA

> El dueño lo dijo así: *"lo que hemos hecho no ha servido para optimizarlo
> al 100% todavía — de hecho, creería que aún falta."* Tiene razón. Este
> documento dice **cuánto falta, en qué orden, y cómo se sabría que está listo**.

## Dónde está parado (2026-11-15)

```
[■■■■■■■■□□]  Diagnóstico          cerrado: la IA no mide ni deduce
[■■■■■■■■□□]  Localizar velas      funciona por tiras (Gemini)
[■■■■■□□□□□]  Medir el paso        banco 78/80 · real 3 de 6 fallan     ← BLOQUEA TODO
[■■■■■■■□□□]  Medir el extenso     ~86–91% en el banco
[■■■■■■■■■□]  Dirección de la vela 92–96%
[■■■■■■■■□□]  Escala de precios    0,32 pt en la única captura validada
[■■■■■■□□□□]  Catálogo de hechos   ICT/SMC básico; faltan familias
[■■■■■□□□□□]  Redacción con hechos demostrado en laboratorio (variantes C/E)
[□□□□□□□□□□]  Conexión al sitio    no empezada (decisión del dueño)
```

---

## FASE 1 — Que la medición sea de fiar en gráficos reales

**Es el cuello de botella. Nada de lo de abajo tiene sentido hasta cerrar esto.**

### 1.1 Que el banco dibuje gráficos como un TradingView real
El banco acierta el paso en 78–79 de 80 láminas y la realidad falla 3 de 6.
Mientras el banco no reproduzca el fallo, no se puede arreglar con garantías.
Añadir a `banco_cadena.lamina()`:
- **cajas de sesión del MISMO color exacto que una de las velas** (el caso
  `nq_5m_oct`: caja de Asia = vela alcista, RGB idéntico);
- **velas con contorno negro de 1 px** y relleno gris claro / gris oscuro (el
  tema del dueño), como variante frecuente;
- **barra de herramientas** a la izquierda y **cabecera con texto** arriba;
- **eje de tiempo** con etiquetas abajo;
- pasos **fraccionarios pequeños** (4–6 px) con muchas velas.

**Listo cuando:** el banco reproduce el sesgo "por lo bajo" (el estimador
actual falla en esas láminas nuevas).

### 1.2 Arreglar el medidor del paso
Diagnóstico pendiente de confirmar: `_arranques` asume un solo fondo por
franja → casi todas las franjas se descartan → votan las de texto de la cabecera.
Candidatos a probar **en el banco mejorado**:
- usar como señal **los bordes negros de 1 px** de las velas (en `nq_5m_oct`:
  197 columnas de borde ≈ 100 velas × 2);
- **leer el eje de tiempo** (distancia entre etiquetas de hora ÷ velas por
  hora): es la verdad independiente que ya se usa a mano. Requiere saber la
  temporalidad (la da el trader o se lee de la cabecera);
- pedirle el paso al **modelo** como estimación gruesa y afinarlo con píxeles
  (mismo reparto de siempre);
- **comprobación cruzada:** si dos métodos discrepan más de un 10%, parar y
  avisar en vez de seguir.

**Listo cuando:** ≥ 95% de láminas del banco mejorado **y** las 6 capturas
reales dentro de ±3% del paso medido a mano. Sin afinar contra ellas.

### 1.3 Subir el extenso de la vela de ~86% a ≥ 95%
Cada vela mal medida abre un FVG falso y su order block falso.
- Reparto del error por tipo de "basura" (`--sin-marca`, `--sin-verticales`,
  `--sin-dibujos`) para atacar el mayor.
- **Dibujos del trader:** pedirle al modelo dónde dibujó (el banco ya lo imita
  con `--pistas-dib`) y excluir esas zonas.
- Líneas verticales de cajas de sesión en la columna de entrada.

**Listo cuando:** máximo y mínimo ≥ 95% (mínimo de 3 semillas) y FVG ≥ 90%.

### 1.4 Higiene
- `requirements` del laboratorio **con versiones fijadas**.
- Arreglar o reescribir `flechas.py` (su autoprueba falla con librerías nuevas).
- Actualizar `docs/capturas_prueba/LEEME.md` (datos de paso viejos) y anotar
  el RGB de las velas de cada captura en `velas.md`.
- Un solo comando que corra las tres semillas y actualice **los dos sitios** de
  la tabla de precisión.
- Copiar a `docs/` las columnas y comparativas que hoy solo existen en el VPS.

---

## FASE 2 — Completar lo que el analizador sabe decir

Orden sugerido (por lo que un trader de ICT nombra más):

| # | Familia | Qué exige |
|---|---|---|
| 1 | **Displacement** como hecho propio | Definición por tamaño relativo de vela + FVG. Solo aritmética. |
| 2 | **Lectura del SL/TP y R:R** del trade | Localizar las cajas verde/roja de la herramienta de posición (modelo + píxeles). |
| 3 | **Entrada y salida automáticas** | Flechas fiables, o que el trader toque la vela en pantalla (más barato y seguro). |
| 4 | **Kill zones / sesión de cada vela** | Leer el eje de tiempo (también arregla el paso: 1.2). |
| 5 | **Inducement, breaker, mitigation** | Aritmética sobre lo ya calculado. |
| 6 | **Anclas del fib del trader** | Leerlas de la imagen (se hizo a mano al píxel) o pedírselas. |
| 7 | **Indicadores** (medias, RSI, MACD, volumen) | Otra extracción: líneas y paneles, no velas. Trabajo grande. |
| 8 | **Otras metodologías** (Wyckoff, patrones, armónicos, Elliott) | Hoy el 2.0 es solo ICT/SMC. Los armónicos y Elliott son casi pura aritmética sobre giros: buen candidato. |

Cada familia entra por el procedimiento del doc 03 ("cómo se añade una familia").

---

## FASE 3 — Demostrar que la respuesta al trader mejora

- **Repetir la comparación A contra C** con la medición ya fiable, sobre **al
  menos 10 trades reales** del dueño (ganados y perdidos), con sus datos reales.
- **Que el dueño califique a ciegas** cuál respuesta le sirve más.
- **Auditoría automática:** un comprobador que marque toda vela o precio citado
  que no esté en el bloque. Tasa de invención objetivo: 0.
- **Ajustar el prompt de redacción** para el mundo con hechos (hoy se reutiliza
  el del sitio con el bloque delante).
- Terminar la prueba pendiente de `nq_5m_oct` cuando el dueño dé sus datos.

**Listo cuando:** el dueño prefiere la respuesta con hechos en una mayoría
clara y no hay velas inventadas.

---

## FASE 4 — Llevarlo al sitio (🔴 solo con permiso del dueño)

### Lo que hay que construir
1. **Un programa único** "captura → bloque" sin intervención manual.
2. **Integración en `/analyze`** detrás de una variable de entorno (patrón del
   proyecto: `ANALYZER2_ENABLED=0` por defecto, prompt idéntico si está apagada).
3. **Clave de Gemini en producción** y manejo de cuota de pago.
4. **Plan B:** si la cadena no puede medir (paso dudoso, eje sin consenso,
   modelo caído), **caer al analizador actual** sin que el usuario note un error.
5. **Dos campos nuevos en el formulario:** señalar la vela de entrada (y
   salida), y —opcional— las anclas de su fib.
6. **Registro** de cada bloque generado para poder auditar reclamaciones.

### Lo que hay que medir antes
| Tema | Estado |
|---|---|
| **Tiempo:** hoy son varias llamadas a Gemini por tiras + eje + GPT-4o. Puede pasar de 60 s. nginx corta a los 180 s. | Sin medir |
| **Costo por análisis** con Gemini de pago | Sin medir (hoy capa gratuita) |
| **Cuota y concurrencia** (4 workers × 4 hilos) | Sin medir |
| **Dependencia de Google:** retiró el modelo 3 veces | Riesgo abierto; evaluar un detector propio |
| **Capturas de móvil, MT5, NinjaTrader, temas oscuros** | Sin probar con capturas reales |

### Cómo desplegarlo sin riesgo
1. Solo para la cuenta admin.
2. Luego modo sombra: se calcula el bloque y se guarda, pero al usuario se le
   sigue dando la respuesta de siempre; se comparan.
3. Luego Premium, con interruptor de apagado inmediato.

### Alternativa más barata, ofrecida y SIN respuesta del dueño
Que el analizador **actual** deje de afirmar relaciones que no puede verificar.
Solo cambia el prompt. Protege la credibilidad mientras llega el 2.0.

---

## Preguntas abiertas para el dueño

1. ¿Autoriza el cambio de prompt "no afirmes lo que no puedes verificar" en el
   analizador actual?
2. Cuando el 2.0 esté listo: ¿reemplaza al actual, o es una función Premium
   aparte ("análisis medido")?
3. ¿El trader señala su vela de entrada tocándola, o se insiste en detectar
   flechas?
4. ¿Se le piden las anclas de su fib en el formulario? (Decidido en octubre que
   sin ellas no se afirma premium/discount.)
5. ¿Cómo enseñar las tasas de acierto al cliente: tal cual ("acierta 81%") o
   como lenguaje ("posible FVG")? Ojo legal: nunca debe sonar a predicción.
6. ¿Presupuesto mensual para Gemini de pago?
7. Datos pendientes de `nq_5m_oct`: flechas, construcción, sesión, resultado.

## Lo que NO hay que hacer

- No conectar nada al sitio "para probar".
- No dar por buena una mejora por verla en una captura.
- No afinar contra las capturas del dueño.
- No volver a intentar lo marcado con ⛔ en el doc 06 sin un motivo nuevo.
- No decir una palabra sobre el color de sus velas sin `colores_velas.py` +
  `velas.md`.
- No prometerle fechas: cada fase se cierra con su criterio de "listo cuando".
