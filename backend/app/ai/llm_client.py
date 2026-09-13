import httpx
from openai import OpenAI

from app.core.config import settings
from app.schemas.ai_analysis import AIAnalysisResult


def call_openai(prompt: str) -> str:
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY
    )

    response = client.responses.create(
        model=settings.OPENAI_MODEL,
        input=prompt
    )

    return response.output_text


def call_ollama(prompt: str) -> str:
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,

        # 强制模型按照 AIAnalysisResult 返回
        "format": AIAnalysisResult.model_json_schema(),

        "options": {
            "temperature": 0
        }
    }

    response = httpx.post(
        url,
        json=payload,
        timeout=180
    )

    response.raise_for_status()

    data = response.json()

    return data["response"]


def call_llm(prompt: str) -> str:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        return call_openai(prompt)

    if provider == "ollama":
        return call_ollama(prompt)

    raise ValueError(
        f"Unsupported LLM provider: {provider}"
    )