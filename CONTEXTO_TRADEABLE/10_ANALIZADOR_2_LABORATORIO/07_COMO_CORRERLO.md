# 07 · CÓMO CORRER EL LABORATORIO

## Dónde se corre cada cosa

| Qué | Dónde | Por qué |
|---|---|---|
| Banco, autopruebas, medir el paso, colores, mapa de velas | **Cualquier máquina** con Python | No usan red |
| Todo lo que llama a Gemini u OpenAI | **El VPS** | El entorno de desarrollo en la nube no alcanza esas APIs; y ahí están las claves |

## Requisitos

```bash
python3 -m pip install numpy Pillow requests      # cadena principal
python3 -m pip install scipy                      # solo lee_grafico.py y flechas.py
```
En el VPS usar siempre **`venv/bin/python3`**. ⚠️ Las versiones no están
fijadas (ver doc 06); medido en 2026-11 con numpy 2.4.6, Pillow 13.0, scipy 1.17.

## Las claves (nunca en el chat, nunca en el repo)

| Clave | Para qué | Cómo se pone |
|---|---|---|
| `GEMINI_API_KEY` | Localizar velas y leer el eje | `python3 tools/set_env.py GEMINI_API_KEY=…` |
| `OPENAI_API_KEY` | Que GPT-4o redacte (laboratorio) | Ya está en el VPS (la usa el sitio) |

- La de Gemini se saca en Google AI Studio (capa gratuita). Guía paso a paso
  para el dueño: `docs/prueba_cajas_PASOS.md`.
- **No hace falta reiniciar nada:** el sitio no usa la clave de Gemini.
- Las herramientas buscan la clave en: el entorno → `scalpel/.env` → la línea
  `environment=` de supervisor.

---

## 1. Sin red (gratis, en cualquier sitio)

```bash
# Autopruebas
python3 tools/hechos_grafico.py --probar      # 75/75  catálogo de hechos
python3 tools/test_analizador2.py             # 15/15  cadena sobre captura real (columnas fijas)
python3 tools/test_eje_precio.py              # 18/18  escala de precios
python3 tools/test_rejilla.py                 # 15/15  recuperación de velas
python3 tools/lee_grafico.py --probar         #        extractor viejo (sintéticos)
python3 tools/flechas.py --probar             # ⚠️ 0/4 con librerías nuevas (doc 06)

# El banco (el juez)
python3 tools/banco_cadena.py --laminas 72 --semilla 7     # ~10-20 min
python3 tools/banco_cadena.py --laminas 72 --semilla 11
python3 tools/banco_cadena.py --laminas 72 --semilla 23
python3 tools/banco_cadena.py --laminas 144 --semilla 7    # familias raras
python3 tools/banco_cadena.py --laminas 12                 # humo rápido (~1 min)

# Sobre una captura
python3 tools/recorta_grafico.py --imagen docs/capturas_prueba/X.png   # panel, paso y tiras
python3 tools/colores_velas.py   --imagen docs/capturas_prueba/X.png   # colores (OBLIGATORIO antes de opinar)
python3 tools/flechas.py         --imagen docs/capturas_prueba/X.png   # flechas candidatas

# La cadena reusando columnas ya obtenidas (sin gastar llamadas)
python3 tools/analizador2.py --imagen docs/capturas_prueba/mnq_long_ote.png \
    --columnas @docs/columnas/columnas_mnq_long_ote.txt --dibuja out/medido.png

# El mapa de velas numeradas (para que el dueño compruebe)
python3 tools/mapa_velas.py --imagen docs/capturas_prueba/mnq_long_ote.png \
    --columnas @docs/columnas/columnas_mnq_long_ote.txt \
    --marca 123:ENTRADA --salida out/mapa.png
```

## 2. En el VPS (con modelo)

```bash
cd /var/www/TRADINGBOT2.0 && git pull origin claude/gallant-volta-i7cqmf

# ¿Qué modelos acepta la clave?
venv/bin/python3 tools/cajas_ia.py --modelos gemini

# La cadena entera: de una captura al bloque de hechos
venv/bin/python3 tools/analizador2.py --imagen docs/capturas_prueba/X.png --modelo gemini:gemini-3.6-flash

# Solo el eje de precios
venv/bin/python3 tools/eje_precio.py --imagen docs/capturas_prueba/X.png --modelo gemini:gemini-3.6-flash
```

Las columnas quedan guardadas en `out/analizador2/columnas_X.txt`: las
siguientes corridas las encuentran solas y no vuelven a gastar llamadas.

### El laboratorio de comparación (sitio de hoy contra sitio con hechos)

```bash
venv/bin/python3 tools/analizador_lab.py \
    --imagen docs/capturas_prueba/X.png \
    --modelo gemini:gemini-3.6-flash \
    --construccion docs/capturas_prueba/X.txt \
    --instrumento MNQ --direccion long --sesion "NY AM" --resultado loss \
    --approach "OTE / Std Dev" \
    --entrada-x 530 --salida-x 595 \
    --rango 117,120 \
    --solo A,C
```

| Opción | Significado |
|---|---|
| `--construccion archivo.txt` | El texto del trader. **Opcional** (prueba a ciegas). |
| `--instrumento --direccion --sesion --resultado --htf --alineado --approach --confluencias` | Lo que el trader declararía en el formulario. Lo que no se pase va como `NOT PROVIDED`. |
| `--entrada-x`, `--salida-x` | La x en píxeles de las flechas (la confirma una persona mirando el gráfico). |
| `--entrada N`, `--vela-salida N` | Lo mismo, por número de vela. |
| `--rango BAJO,ALTO` | Las dos velas donde el trader ancló su fib. Sin esto no se afirma premium/discount. |
| `--paso 5.84` | Fuerza el paso entre velas medido a mano. **Muleta de laboratorio.** |
| `--solo A,C` | Qué variantes correr (A sitio · B +cláusula · C +hechos · D estricta · E completa · F solo tabla). |
| `--sin-eje` | Corre sin precios (prueba degradada, declarada). |
| `--idioma` | Idioma de la respuesta (por defecto español). |
| `--salida` | Archivo de resultado (por defecto `out/comparativa.md`). |

**Costo:** Gemini en capa gratuita (con cuota diaria); cada variante de GPT-4o
≈ $0,03.

## 3. Medir el paso a mano (cuando el estimador falla)

1. **Por el eje de tiempo:** medir en píxeles la distancia entre dos etiquetas
   de hora y dividir por las velas que caben (en 5m, 12 velas por hora).
   Ejemplo `nq_5m_oct`: 70,10 px ÷ 12 = **5,84**.
2. **Contando velas** en una franja limpia y dividiendo el ancho.
3. Pasar el valor con `--paso`.

## 4. Flujo de trabajo para probar una captura nueva del dueño

1. Guardarla en `docs/capturas_prueba/` y añadir su entrada en `LEEME.md`.
2. **Preguntarle de qué color son sus velas** y anotarlo en `velas.md`.
   Correr `colores_velas.py`.
3. `recorta_grafico.py` → comparar el paso con el medido a mano.
4. En el VPS: `analizador2.py` con el modelo (y `--paso` si hizo falta).
5. `mapa_velas.py` → mandarle la imagen numerada y que confirme entrada y salida.
6. `analizador_lab.py` con sus datos (sin inventar ninguno).
7. **Leer las respuestas a mano** y auditar las velas citadas.
8. Si algo falló: reproducirlo en el **banco** (añadiendo esa "basura" a la
   fábrica si no existe), arreglar, re-medir la tabla.

## 5. Dónde queda cada salida

| Ruta | Contenido |
|---|---|
| `out/analizador2/columnas_<img>.txt` | Columnas devueltas por el modelo (reutilizables) |
| `out/comparativa.md` | Respuestas de las variantes del laboratorio |
| `out/lee_grafico/`, `out/banco_cadena/` | Láminas y dibujos de control |
| `docs/columnas/` | Columnas de dos capturas guardadas en el repo |
| `docs/banco_resultados*/` | Respuestas del banco de 30 casos (analizador del sitio) |

⚠️ `out/` está en `.gitignore`: **lo que se genere en el VPS no viaja al
repo**. Las columnas y comparativas que se quieran conservar hay que copiarlas
a `docs/`.

## 6. Otros bancos (analizador del sitio, no la cadena)

```bash
python3 tools/banco_analizador.py                    # genera los 30 casos sintéticos
venv/bin/python3 tools/corre_banco.py                # VPS: los pasa por el prompt real (~$0,35)
python3 tools/califica_banco.py                      # rúbrica → INFORME.md (leer los textos igual)
python3 tools/informe_banco_pdf.py                   # PDF de 51 páginas

python3 tools/agudeza_visual.py --generar            # 168 láminas de agudeza
python3 tools/verifica_agudeza.py                    # la verdad dibujada = la declarada
venv/bin/python3 tools/agudeza_visual.py --correr openai:gpt-4o   # VPS, cuesta dinero
python3 tools/agudeza_visual.py --tabla
```
