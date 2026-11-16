# 17 · REGLAS DE TRABAJO

> Cómo se trabaja en este proyecto. Sirve igual para una IA que para una
> persona. Cada regla viene de algo que salió mal.

## 0. Las que no admiten excepción

1. 🔴 **Nunca hacer push ni merge a `main`.** Además de estar congelada, `main`
   tiene un workflow de GitHub (`.github/workflows/deploy.yml`) que, al recibir
   un push, entra al VPS y **redespliega el bot viejo**: reinicia sus procesos y
   vuelve a activar su sitio de nginx. Ver doc 19.
2. 🔴 **Se trabaja en `claude/gallant-volta-i7cqmf`.** Las sesiones en la nube
   de Claude arrancan por error en `claude/hopeful-volta-kk3zg2` (vieja):
   `git fetch origin claude/gallant-volta-i7cqmf && git checkout claude/gallant-volta-i7cqmf`.
3. 🔴 **No se crean Pull Requests** salvo que el dueño lo pida.
4. 🔴 **El bot viejo (`/opt/tradingbot`) no se toca ni se borra.**
5. 🔴 **El analizador de producción no se toca sin permiso explícito.**
6. 🔴 **Ningún secreto en el chat ni en el repo.** Nunca `grep`/`cat` sobre la
   línea `environment=` de supervisor.
7. 🔴 **Todo texto: educativo, nunca asesoría.** Nunca "GPT-4o/OpenAI" en público.
8. 🔴 **Cuatro idiomas a la par.**
9. 🔴 **Nada ganado o comprado se revoca.**
10. 🔴 **Pagos = dinero real.** Probar con cuenta desechable y mirar PayPal.
11. 🔴 **Las velas del dueño son rellenas.** Antes de opinar sobre el color de
    las velas de una captura: `tools/colores_velas.py` +
    `docs/capturas_prueba/velas.md`. Sin ficha, se le pregunta.

## 1. Cómo hablar con el dueño

- **Sin tecnicismos.** No es programador. Explicar con comparaciones de la vida
  real; si hay que usar un término, decir qué es.
- **Español**, tuteo, directo. Sin relleno ni autobombo.
- **Decir la verdad aunque no guste**, incluido "no lo sé" y "me equivoqué".
  No presentar un riesgo más grave de lo que es, ni menos.
- **Recomendar, no enumerar.** Si hay opciones, decir cuál y por qué.
- **Enseñar para que pueda comprobar:** una imagen, un número, un antes/después.
- **Cuando insiste en algo, tiene razón más veces de las que no.** Si repite
  una corrección, buscar la causa en otra parte en vez de defender la medición.
- **Uno por uno.** No abrir tres frentes; cerrar y pulir antes de pasar.
- **No reabrir decisiones cerradas** (doc 16) ni repetirle recordatorios que
  pidió no oír.
- **No prometer fechas ni resultados** que no dependan de uno.

## 2. Cómo darle comandos para el VPS

- Primero recordarle **entrar por SSH** (una vez pegó un comando en PowerShell
  de su PC).
- **Una sola línea**, sin `\` de continuación; listo para copiar y pegar.
- Decirle **qué va a ver** si salió bien.
- Avisar **antes** si el comando va a imprimir algo sensible.
- Su teclado/terminal convierte comillas rectas en curvas: evitar comillas
  cuando se pueda; para cosas largas, un script en `tools/` y un comando corto.
- Se pierde en `nano`/`vim`: nunca pedirle editar un archivo a mano. Para
  variables: `python3 tools/set_env.py`.
- Tras cambiar la config de supervisor: `reread && update`, **sin** `restart`.
- **Recordarle el deploy después de cada push** (`git pull` + `restart`).

## 3. Antes de subir un cambio

1. Plantillas Jinja tocadas: que compilen.
2. `node --check` del JavaScript tocado.
3. Claves de traducción parejas ×4 y ninguna clave del HTML sin diccionario.
4. Pruebas de la zona tocada (doc 14). Si no hay, escribir una en `tools/`.
5. Legal tocado → `audit_legal_translations.py`.
6. Banco de preguntas tocado → `extract_quiz_key.js` + `validate_daily_bank.js`
   y subir los JSON.
7. Columna nueva → migración en **SQL crudo** + `test_boot_migracion.py`.
8. Lo visual: **mirarlo en un navegador real** (claro, oscuro, un camo, móvil).
   Hay fallos que no se ven leyendo el código.
9. Commit con mensaje en español que diga **qué y por qué**. Sin nombrar el
   modelo de IA.
10. Push a la rama de trabajo. Avisar del deploy.

## 4. Cómo escribir código aquí

- **Seguir los patrones del doc 03:** inerte sin clave, línea de arranque,
  precio del servidor, un solo activador idempotente, vaciar en vez de borrar.
- **Comentar el porqué**, sobre todo si viene de un fallo.
- **Fallar ruidosamente.** Nada de `except: pass` que esconda un guardado
  fallido o una prueba degradada.
- **Sin valores por defecto que describan un caso concreto.**
- **Lo invisible no lleva `backdrop-filter`** (costaba 3,6× en el scroll).
- **Iconos de interfaz en SVG**, no emojis (dependen de las fuentes del usuario).
- **`[hidden]` no oculta** un elemento con `display` puesto por clase: añadir
  la regla `[hidden]{display:none}`.
- **Imágenes en `style` por propiedad**, no dentro de una cadena HTML.
- **Fechas en UTC**, siempre con `datetime.now(timezone.utc)`.
- **No importar módulos hermanos con `import x`** dentro de `scalpel/`: bajo
  gunicorn tumba los workers. Cargar por ruta de archivo.
- **No usar `SERVER_NAME` de Flask.**
- **No añadir dependencias ni CDNs** sin necesidad; las librerías del
  navegador van a `static/vendor/`.

## 5. Cómo medir (regla general, no solo del laboratorio)

- **Medir antes de cambiar** y después. Un número con su método.
- **Dato contra una verdad conocida**, no contra la propia intuición.
- **Ninguna tasa sin su muestra.** Ningún "mejor/peor" con pocos casos.
- **Leer los resultados a mano** antes de fiarse de un calificador automático.
- **Probar en lo que se parece a producción** (PostgreSQL, navegador real,
  gráfico real).
- **Si arreglas algo, vuelve a medir** lo que dependía de ello.

## 6. Cómo mantener la memoria del proyecto

- `CLAUDE.md` = notas **activas**, se cargan en cada sesión de Claude: debe
  ser corto y **cierto hoy**.
- `CLAUDE_ARCHIVE.md` = historia; no se carga sola.
- **Tachar un punto el mismo día que se cierra.** Una alerta que se queda
  vieja hace decir tonterías con confianza.
- Al cerrar una tarea, mover su detalle al archivo.
- **Este expediente** (`CONTEXTO_TRADEABLE/`) es una foto del 2026-11-15: si se
  sigue trabajando, actualizar al menos `00`, `15` y la carpeta `10`.
  Regenerar el inventario y el ZIP con `python3 tools/empaqueta_contexto.py`.
- El entorno de desarrollo en la nube **se recicla**: lo que no esté subido al
  repo se pierde.

## 7. Trampas del entorno de desarrollo en la nube (Claude Code)

- No alcanza OpenAI, Google, Instagram ni CDNs externos.
- Arranca en la rama equivocada y a veces sin dependencias de Python
  (`python3 -m pip install …`; el `pip` suelto puede apuntar a otro Python).
- Un filtro de privacidad bloquea comandos de terminal que nombren archivos
  donde aparece el correo del dueño (`scalpel/app.py` entre ellos): para leer
  esos archivos se usan las herramientas de lectura/búsqueda, no la terminal.
- No tiene acceso al VPS: todo lo de producción lo ejecuta el dueño.
