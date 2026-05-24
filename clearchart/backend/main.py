"""ClearChart — servidor FastAPI.

Sirve el frontend estático y expone la API de análisis. Cada consulta es
independiente (stateless): recibe una imagen + las respuestas del trader y
devuelve el mapa limpio generado por el modelo de visión.
"""
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ai_provider import AIProviderError, analyze_chart
from prompts import QUESTIONS, build_user_message

ALLOWED_MEDIA_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="ClearChart")


def extract_analysis_json(text: str) -> dict:
    """Extrae y parsea el JSON del texto de respuesta del modelo.

    Elimina fences de markdown si están presentes, limpia espacios y parsea.
    Si el parseo falla, retorna un dict con parse_error=True y el texto raw.
    """
    cleaned = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"```", "", cleaned)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return {"parse_error": True, "raw": text}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/questions")
def get_questions():
    """Devuelve las preguntas fijas que el frontend renderiza en orden."""
    return {"questions": QUESTIONS}


@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    answers: str = Form(...),
):
    """Recibe el gráfico + las respuestas (JSON string) y devuelve el análisis."""
    media_type = image.content_type
    if media_type not in ALLOWED_MEDIA_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Formato no soportado. Subí una imagen PNG, JPG, WEBP o GIF.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="La imagen está vacía.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="La imagen supera el límite de 10 MB.")

    try:
        parsed = json.loads(answers)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Las respuestas no son un JSON válido.")
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="Las respuestas deben ser un objeto.")

    missing = [
        q["label"] for q in QUESTIONS
        if q.get("required") and not (parsed.get(q["id"]) or "").strip()
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Faltan respuestas obligatorias: " + "; ".join(missing),
        )

    user_message = build_user_message(parsed)

    try:
        result = analyze_chart(image_bytes, media_type, user_message)
    except AIProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - superficie de error del proveedor
        raise HTTPException(status_code=502, detail=f"Error al consultar el modelo: {exc}")

    parsed = extract_analysis_json(result)
    return JSONResponse({"analysis": parsed})


# El frontend se monta al final para que las rutas /api/* tengan prioridad.
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
