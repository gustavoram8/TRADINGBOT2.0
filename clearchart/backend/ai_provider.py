"""Capa de abstracción para el modelo de visión.

Soporta Google Gemini (gratuito), OpenAI (GPT-4o) y Anthropic (Claude). Se
elige con la variable de entorno AI_PROVIDER ("gemini", "openai" o
"anthropic"). Cada proveedor lee su propia API key del entorno.
"""
import os

from prompts import SYSTEM_PROMPT


class AIProviderError(Exception):
    """Error de configuración o de llamada al proveedor de IA."""


def analyze_chart(image_bytes: bytes, media_type: str, user_message: str) -> str:
    """Envía la imagen + el mensaje del trader al modelo y devuelve el texto."""
    provider = os.getenv("AI_PROVIDER", "gemini").lower().strip()

    if provider == "gemini":
        return _analyze_gemini(image_bytes, media_type, user_message)
    if provider == "openai":
        return _analyze_openai(image_bytes, media_type, user_message)
    if provider == "anthropic":
        return _analyze_anthropic(image_bytes, media_type, user_message)
    raise AIProviderError(
        f"AI_PROVIDER desconocido: '{provider}'. Usá 'gemini', 'openai' o 'anthropic'."
    )


def _analyze_gemini(image_bytes: bytes, media_type: str, user_message: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise AIProviderError("Falta GEMINI_API_KEY en el entorno.")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise AIProviderError("Instalá la librería: pip install google-genai") from exc

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=media_type),
            user_message,
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=2000,
        ),
    )
    text = response.text
    if not text:
        raise AIProviderError("Gemini no devolvió texto (¿imagen bloqueada o vacía?).")
    return text


def _analyze_openai(image_bytes: bytes, media_type: str, user_message: str) -> str:
    import base64

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIProviderError("Falta OPENAI_API_KEY en el entorno.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIProviderError("Instalá la librería: pip install openai") from exc

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model=model,
        max_tokens=2000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_message},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    },
                ],
            },
        ],
    )
    return response.choices[0].message.content


def _analyze_anthropic(image_bytes: bytes, media_type: str, user_message: str) -> str:
    import base64

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIProviderError("Falta ANTHROPIC_API_KEY en el entorno.")

    try:
        import anthropic
    except ImportError as exc:
        raise AIProviderError("Instalá la librería: pip install anthropic") from exc

    client = anthropic.Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": user_message},
                ],
            }
        ],
    )
    return "".join(block.text for block in response.content if block.type == "text")
