# Reels — qué se puede animar por código y guiones de los 6 primeros

## Qué se puede hacer aquí y qué no

**SÍ se puede, y ya está probado:** vídeo `.mp4` 1080×1920 generado por código.
Cada fotograma se pinta en Chromium sin cabeza (el mismo motor que dibuja los
camos, las placas y los cursores), se captura y ffmpeg los cose. El primero
funcionando es `tools/reel_order_block.py` → `out/reels/reel-order-block.mp4`.

Con eso salen: velas que se dibujan solas, cajas que caen sobre su vela, huecos
que se abren, barras de rango que se llenan, listas que entran una a una,
cierres de marca, y portadas de reel. Todo con la paleta del sitio.

🔑 **Regla técnica del motor:** el estado de cada fotograma se calcula desde `t`
(el segundo exacto), **nunca** con animaciones CSS por reloj. Con animaciones
por tiempo la captura llega tarde o pronto y el vídeo tiembla.

**NO se puede desde aquí:**

- **Grabarte.** Nada de cámara ni de cara.
- **Vídeo generado por IA** (tipo Sora/Veo). No hay modelo de vídeo en este
  entorno; lo que hay es motion graphics por código, que para explicar conceptos
  es mejor: es exacto y reproducible.
- **Audio.** El audio se le pone en Instagram, que además es donde vive el audio
  de moda. ⚠️ Ponle siempre una pista: Instagram empuja menos los reels mudos, y
  aunque la mayoría mira sin sonido, el sistema sí lo mira.

**Lo honesto sobre el alcance:** los reels de motion graphics funcionan y son
perfectos para arrancar sin exponerte. Pero los que revientan casi siempre
tienen una cara humana. A medio plazo, o apareces tú o aparece alguien. No es
una opinión estética: es cómo se comporta el formato.

---

## R1 · Order Block ✅ YA RENDERIZADO

`tools/reel_order_block.py` · 8 s · sin voz · empareja con el **post 4**.

| t | Qué pasa | Texto en pantalla |
|---|---|---|
| 0.0-0.9 | Rejilla y título entran | CONCEPTO · **Order Block** |
| 0.9-2.4 | Las 7 velas se dibujan una a una | Siete velas. / Una sola es el order block. |
| 2.5-3.9 | Cajas rojas punteadas sobre **todas** las bajistas, y se van | Casi todo el mundo marca *cualquier vela roja*. |
| 4.0-4.9 | La vela del desplazamiento se enciende en azul con flecha | El precio se *desplaza*. |
| 5.0-7.0 | La caja dorada **cae** sobre la vela correcta y se queda | El válido es *la última bajista* antes de ese arranque. |
| 7.0-8.0 | Cierre de marca | Tradeable Academy · Contenido educativo |

**Gancho (los primeros 1,5 s deciden todo):** el título aparece sobre negro y
las velas empiezan a dibujarse. Si quieres más agresivo, se cambia el arranque
por la frase "lo estás marcando mal" y las cajas rojas de golpe.

---

## R2 · Fair Value Gap · 8 s · empareja con el **post 6**

Mismo motor, cambia el dibujo.

| t | Qué pasa | Texto |
|---|---|---|
| 0-1 | Título | CONCEPTO · **Fair Value Gap** |
| 1-2.5 | Tres velas se dibujan | Tres velas. Nada más. |
| 2.5-4 | Se trazan dos líneas: máximo de la 1ª y mínimo de la 3ª, rotuladas | Máximo de la 1ª. Mínimo de la 3ª. |
| 4-5.5 | La banda entre ambas se rellena de dorado y late una vez | **Ahí no se negoció nada.** |
| 5.5-7 | El precio vuelve y toca la banda | El mercado tiende a volver. |
| 7-8 | La banda se apaga a la mitad | Ni todos se rellenan, ni cuando te conviene. |

El último tramo es el que hace el reel distinto de los otros mil de FVG: casi
nadie dice la parte incómoda, y eso es exactamente lo que genera comentarios.

---

## R3 · Un gráfico, tres lecturas · 10 s · empareja con el **post 8**

El más "wow" de los seis y el más barato de producir: **un solo gráfico** y tres
capas que entran y salen encima.

| t | Qué pasa | Texto |
|---|---|---|
| 0-1.5 | Un gráfico limpio se dibuja | Mismo gráfico. |
| 1.5-4 | Capa ICT: pools de liquidez arriba y abajo, FVG marcado | El de **ICT** ve dónde quedó la liquidez. |
| 4-6.5 | La capa se borra. Capa Wyckoff: rango con fases A-E | El de **Wyckoff** ve en qué fase está la campaña. |
| 6.5-9 | Se borra. Capa price action: soporte, resistencia, reacción | El de **price action** ve la reacción en un nivel. |
| 9-10 | Las tres capas se superponen un instante y quedan en blanco | Ninguno se lo inventa. Leen en idiomas distintos. |

Cierre hablado o en texto: *"¿en cuál lees tú?"* → comentarios.

---

## R4 · Cientos de capturas · 7 s · empareja con el **post 2**

| t | Qué pasa | Texto |
|---|---|---|
| 0-2 | Una cuadrícula de capturas de gráficos se va llenando, cada vez más rápido, hasta desbordar | 1… 20… 80… 217 capturas. |
| 2-4 | Todo se congela y se apaga menos una | ¿En cuáles repetiste el mismo error? |
| 4-6 | Silencio visual, fondo limpio | Guardar tus trades no es revisarlos. |
| 6-7 | Marca | Tradeable Academy |

El contador subiendo es el gancho: el número creciendo retiene.

---

## R5 · Los dos frentes · 8 s · empareja con el **post 7**

Pantalla partida en vertical. Arriba **Análisis**, abajo **Ejecución**. Cada
error entra tecleado, uno a uno, alternando arriba/abajo. Al final las dos
mitades se juntan y aparece: *"Se corrigen distinto."*

Cierre: *"¿cuál de los dos te pasa más?"* — el A/B es lo que dispara comentarios,
porque responder cuesta una palabra.

---

## R6 · Los ocho rangos · 9 s · empareja con el **post 9**

La tira de pips se llena rango a rango, con el nombre de cada uno entrando y
saliendo (Paper Trader → … → Market Maker). Al llegar al octavo, todo se apaga
menos una línea: **"No se sube acertando operaciones."** Y debajo, pequeño:
*se sube estudiando*.

Es el reel de marca, no el de alcance: sirve para que el que ya te está mirando
entienda que esto es una academia y no una cuenta de señales.

---

## Orden de publicación sugerido

Los reels **no** sustituyen a los 9 posts: los posts son el escaparate, los
reels son la puerta. Publica los 9 posts primero (seguidos), y luego un reel
cada 2-3 días en este orden: **R1 → R4 → R2 → R3 → R5 → R6**.

R1 y R4 primero porque son los dos más "atrapa-scroll": uno enseña un error
concreto y el otro tiene un número subiendo.

⚠️ Y lo que ya sabes: **nada de esto reparte alcance mientras la cuenta esté
privada**. Los reels de una cuenta privada no entran en Explorar ni en el feed
de reels. Es el único requisito bloqueante.
