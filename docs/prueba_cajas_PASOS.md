# Prueba de las cajas — pasos, uno por uno

> **Qué se prueba:** si un modelo de IA sabe decir **dónde está cada vela**, con
> coordenadas. No si "entiende" el gráfico — solo si lo localiza.
> **Por qué importa:** si devuelve las cajas bien, la comparación
> ("¿cerró por encima del nivel?") la hace el código y es exacta. Eso es lo que
> hoy el analizador no puede hacer.
> **Cuesta:** $0 (capa gratuita de Google) y unos 10 minutos.
> 🔴 **No toca el sitio.** No se reinicia nada, no cambia el analizador.

---

## PASO 1 — Sacar la clave (en tu PC, 2 minutos)

1. Entra en **https://aistudio.google.com/apikey**
2. Inicia sesión con tu cuenta de Google.
3. Botón **"Create API key"** (Crear clave de API).
4. Si te pide elegir un proyecto, acepta el que te ofrezca por defecto.
5. Copia la clave. Empieza por `AIza...`

🔴 **Esa clave NO se pega en el chat con Claude.** Va directa del navegador a la
terminal del VPS, en el paso 3.

⚠️ Mientras estés ahí, apunta el **nombre exacto del modelo** que aparezca en la
lista (algo como `gemini-3-pro` o `gemini-2.5-pro`). Lo necesitas en el paso 4.

---

## PASO 2 — Entrar al VPS y actualizar (1 minuto)

```
cd /var/www/TRADINGBOT2.0
git pull origin claude/gallant-volta-i7cqmf
```

---

## PASO 3 — Guardar la clave (30 segundos)

```
python3 tools/set_env.py GEMINI_API_KEY=AIza_lo_que_copiaste
```

Escribe la clave en `scalpel/.env` y en la config de supervisor, hace copia de
seguridad de los dos y **no imprime el valor**.

⚠️ **NO hace falta `supervisorctl restart` ni `update`.** La app no usa esta
clave; la lee directamente el script de la prueba. Producción no se entera.

---

## PASO 4 — Correr la prueba (2 minutos)

```
venv/bin/python3 tools/cajas_ia.py \
    --imagen docs/capturas_prueba/mes_5m.png \
    --modelo gemini:gemini-3-pro
```

Si sale un error diciendo que el modelo no existe, cambia `gemini-3-pro` por el
nombre que viste en el paso 1.

Si sale `ModuleNotFoundError: requests`:
```
venv/bin/pip install requests
```

**Lo que verás:** cuántas cajas devolvió y la ruta de un PNG con esas cajas
dibujadas encima de tu gráfico. Algo así:

```
118 cajas devueltas por gemini:gemini-3-pro
dibujado en /var/www/TRADINGBOT2.0/out/lee_grafico/mes_5m_cajas.png
```

---

## PASO 5 — Mandarme el resultado

Abre ese PNG y pégalo en el chat. Con verlo basta para juzgarlo: **o los
recuadros caen sobre las velas, o no caen.**

⚠️ Si los recuadros salen todos girados o desplazados en bloque, **no
concluyas que falló**: es el orden en que ese modelo escribe las coordenadas.
Repite el paso 4 añadiendo `--orden xyxy` al final y vuelve a mirar.

---

## Cómo se lee el resultado

- **Las cajas caen sobre las velas** → el atajo funciona. El analizador podría
  pasar a localizar los elementos con este modelo y hacer las comparaciones en
  código, sin licencias de datos y sin entrenar nada.
- **Las cajas caen mal** → queda descartado *este atajo*, pero **no la idea**.
  El siguiente camino es un detector entrenado (familia YOLO), que es otra
  tecnología: se le enseñan miles de gráficos generados con colores, temas e
  indicadores aleatorios, y aprende la FORMA de una vela en vez de su color.
  Eso son semanas de trabajo y unos $10-30 de alquiler de tarjeta gráfica una
  sola vez.
