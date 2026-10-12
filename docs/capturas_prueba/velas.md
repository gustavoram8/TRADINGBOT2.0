# De qué color son las velas de cada captura — LO DICE EL DUEÑO

🔴 **ESTE ARCHIVO EXISTE PORQUE CLAUDE SE EQUIVOCÓ MÁS DE CINCO VECES EN LO
MISMO, DURANTE MESES.** Siempre la misma afirmación —*"las velas son huecas"*—,
siempre corregida por el dueño, siempre arreglada, y siempre de vuelta a las
pocas semanas con la captura siguiente. Sus palabras del 17-oct:

> *"Cuántas veces tengo que decirte que mis velas NO son huecas, son color gris
> claro y creo que negro."*
> *"Esto mismo me lo has protestado mil veces, siempre te lo corrijo, me das la
> razón, lo terminas corrigiendo, todo está bien, te envío una captura nueva o
> pasan algunos días o semanas, y vuelves a caer en el mismo problema."*

## La regla, y no admite excepción

**Antes de escribir UNA SOLA FRASE sobre el color, el relleno o la forma de las
velas de una captura, hay que (a) correr `python3 tools/colores_velas.py` y
(b) leer la ficha de abajo. Si la captura no tiene ficha, se le PREGUNTA al
dueño y se anota. Nunca se deduce.**

⛔ Está prohibido escribir "parecen huecas", "el interior es del color del
fondo", "son de dos colores" o cualquier variante, por mucho que un corte de
píxeles lo sugiera. Ya se sugirió cinco veces y las cinco estaba mal.

## Por qué la máquina no puede decidirlo sola

Se probaron dos reglas automáticas el 17-oct y fallaron **en direcciones
opuestas**, que es la prueba de que no es cuestión de afinar un número:

| regla | qué hizo |
|---|---|
| clasificar por superficie en tiras estrechas | llamó **fondo** al gris que es la vela alcista |
| clasificar por número de tiras del ancho de un cuerpo | llamó **vela** a todo, papel blanco incluido |

Las dos causas, medidas:
1. Con las velas a ~6 px de paso, **el fondo que queda entre dos velas es una
   tira de 3 px** — exactamente igual de ancha que el cuerpo de una vela. La
   geometría no los separa.
2. 🔴 En `nq_5m_oct` **la caja de sesión de NY PM y la vela alcista son el MISMO
   RGB**, `(206,208,213)`. No parecidos: idénticos. Ninguna regla de color puede
   separarlos, y cualquier intento de meter los "fondos" en una lista borra las
   velas alcistas enteras.

---

## Fichas

### `nq_5m_oct.png` — NQ1! 5m (dictado por el dueño, 2026-10-17)
- **Alcistas: GRIS CLARO.** Medido: `(206,208,213)`, cuerpos de 3-5 px entre
  bordes negros de 1 px.
- **Bajistas: NEGRO / GRIS OSCURO.** Medido: `(74,74,74)` y `(0,0,0)`.
- **RELLENAS las dos. NO son huecas.**
- ⚠️ `(206,208,213)` es **además** el color de la caja de sesión de NY PM.

### `mnq_long_ote.png` · `mnq_5m.png` · `mnq_5m_zoom.png` · `mes_*.png`
- **RELLENAS. NO son huecas.** Dicho por el dueño varias veces desde septiembre.
- Pendiente de anotar el RGB exacto de cada una con `colores_velas.py`.

---

## Dónde sí hay velas huecas

**Solo en las láminas que dibuja el banco de pruebas** (`banco_cadena.py`), que
sortea cuerpos rellenos o huecos a propósito para que la cadena aguante las dos
cosas. De ahí salió la confusión original: un hallazgo verdadero *sobre el
banco* se arrastró a las capturas del dueño, donde es falso.
