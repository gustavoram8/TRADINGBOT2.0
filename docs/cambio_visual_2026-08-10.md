# Qué cambió de aspecto el 2026-08-10 (arreglo del scroll)

> **Para qué sirve este documento.** El día que el sitio se abra al público, si
> algo se ve distinto de como lo recuerdas, aquí está exactamente qué se tocó,
> cuánto cambió medido en píxeles, cómo se ve hoy, y cómo revertirlo en un
> minuto. Sirve para no confundir un bug con este cambio, ni este cambio con un
> problema de caché.
>
> Commit: **`e0619d3`** — *"Scroll 3,6x mas fluido: el cristal esmerilado, solo
> donde no cuesta"*. El estado anterior es **`301bb3b`**.

---

## Por qué se tocó

El dueño reportó lag al hacer scroll (iMac 2011). Medido en navegador real: 46
elementos con `backdrop-filter` (cristal esmerilado) obligaban a re-desenfocar
su fondo **en cada fotograma del scroll**.

| | ms por fotograma | fps |
|---|---|---|
| Antes | 60,6 | 17 |
| Después | 16,7 | **60** |

Bajar el radio del desenfoque no servía (probado a 10, 6 y 3 px: 58-65 ms). El
coste es tener la capa, no cuánto desenfoca.

---

## Qué se cambió, exactamente

Todo vive en **un solo bloque de CSS** al final del `<style>` de Aurora en
`scalpel/templates/index.html`, más dos líneas sueltas. Nada de JavaScript,
nada de `app.py`, ninguna plantilla más.

**1 · Las tarjetas pierden el cristal y pasan a fondo opaco.**
Afecta a `.card`, `.ag-card`, `.account-btn`, `.disc-fp`, `.disc-pct`,
`.modal`, `.syn-toast`, `.syn-pdf-btn`, `.syn-dossier`.

```
antes:   background: var(--card)            + backdrop-filter: blur(20-22px)
después: background: linear-gradient(var(--card),var(--card)), var(--bg)
```

El color percibido es **el mismo**: es el mismo `var(--card)` compuesto sobre
`var(--bg)` en vez de sobre lo que hubiera detrás. Lo que se pierde es que el
fondo (degradado o arte del camo) ya no “se cuela” difuminado a través de la
tarjeta.

**2 · El cristal SE CONSERVA** en lo que no se desplaza al hacer scroll: la
barra lateral (`.ag-sidebar`), la nav de mentorías (`.mt-nav`) y los velos de
overlay. La barra lateral es la pieza de cristal más visible y sigue igual.

**3 · Dos velos invisibles dejan de desenfocar.** El de compra del PDF de
Synapse (`.syn-pdf-overlay`) y el del cajón de ayuda (`#nxh-scrim`) viven
siempre en la página con `opacity:0`; su desenfoque a pantalla completa se
calculaba en cada fotograma aunque nadie los viera. Ahora el desenfoque está en
su clase `.open`. **Visualmente idéntico** cuando se abren, porque la
transición siempre fue solo de opacidad.

### Lo que NO se tocó

Colores, tipografías, tamaños, espaciados, posiciones, bordes, sombras,
animaciones, el arte de ningún camo, el logo, ni ninguna pantalla fuera de
`/app`.

---

## Cuánto cambió, medido

Mismo servidor, misma cuenta, mismo viewport (1400×1000), scroll a 0. Diferencia
por píxel entre la captura de `301bb3b` y la de `e0619d3`, en escala 0-255:

| Escena | media | percentil 95 | máximo | dónde se concentra |
|---|---|---|---|---|
| sin camo · claro | **0,6** | 3 | 174 | rail derecho |
| sin camo · oscuro | **2,2** | 14 | 182 | rail derecho, arriba |
| Chronicles · oscuro | **3,4** | 18 | 145 | sobre el arte del camo |
| Rising Sun · claro | **1,5** | 7 | 96 | rail derecho, arriba |

**Cómo leerlo:** una diferencia media de 0,6-3,4 sobre 255 está por debajo del
umbral en que el ojo distingue dos tonos. Por eso el dueño no notó nada al
compararlo. Los máximos (96-182) existen pero son puntuales: bordes de tarjeta
justo encima de una zona del fondo con mucho contraste. El modo **oscuro cambia
más que el claro** porque su `var(--card)` es mucho más transparente
(`rgba(255,255,255,0.05)` frente a `0,72` en claro), así que antes dejaba pasar
más fondo.

Imágenes en `docs/ref_visual/`:

- `antes_despues.jpg` — las 4 escenas: antes | después | mapa de diferencias ×10
- `referencia_*.jpg` — **así debe verse hoy**. Compara contra esto el día del
  lanzamiento.

---

## Si el día del lanzamiento algo se ve raro

**1 · Primero descarta la caché**, que es lo más probable. Abre en **ventana de
incógnito nueva**, o recarga con Cmd+Shift+R. Si en incógnito se ve bien, era
caché (del navegador o de Cloudflare) y no un bug. Para forzar a Cloudflare:
purgar caché desde su panel.

**2 · Compara contra `docs/ref_visual/referencia_*.jpg`.** Si lo que ves
coincide, no hay bug: es este cambio y así quedó a propósito.

**3 · Si no coincide, revertir es un minuto.** Borra el bloque comentado
`══ RENDIMIENTO DEL SCROLL ══` del final del `<style>` de Aurora en
`index.html`, y devuelve el desenfoque de `#nxh-scrim` y `.syn-pdf-overlay` a su
regla base. O directamente:

```
git revert e0619d3
```

Vuelve el aspecto exacto de antes — y vuelve también el lag de scroll.

---

## Cómo reproducir la comparación

`scratchpad/compara_visual.py` la regenera entera: sirve el template viejo y el
nuevo con el mismo servidor y compara las capturas.

⚠️ **Dos trampas al medir esto**, por si se repite:

- **16,7 ms es el techo de vsync.** Una vez ahí, todo marca igual y las
  diferencias de rasterizado quedan escondidas. Para verlas hay que subir el
  viewport (2560×1440) o usar `Performance.getMetrics` de CDP.
  `--disable-gpu-vsync` **no** sirve: rAF deja de esperar al pintado y mide
  1,5 ms de nada.
- **Hay que fijar `scrollTo(0,0)` antes de capturar.** Si no, las dos capturas
  salen desplazadas unos píxeles y el "% de píxeles distintos" mide
  desalineación, no cambio visual — se reconoce porque en el mapa de
  diferencias aparece el texto duplicado en fantasma.
