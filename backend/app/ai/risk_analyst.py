import json

from pydantic import ValidationError

from app.ai.llm_client import call_llm
from app.ai.prompt_builder import build_risk_analysis_prompt
from app.schemas.ai_analysis import (
    AIAnalysisInput,
    AIAnalysisResult
)


def clean_llm_json(raw_text: str) -> str:
    """
    清理模型可能返回的 Markdown JSON 代码块。
    """

    text = raw_text.strip()

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def analyze_finding(
    data: AIAnalysisInput,
    rag_context: str | None = None,
) -> AIAnalysisResult:
    """
    调用 LLM 对 Finding 进行安全风险分析。
    """

    prompt = build_risk_analysis_prompt(
    data,
    rag_context=rag_context,
)

    raw_response = call_llm(prompt)

    cleaned_response = clean_llm_json(raw_response)

    try:
        parsed = json.loads(cleaned_response)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "LLM returned invalid JSON"
        ) from exc

    try:
        result = AIAnalysisResult.model_validate(parsed)

    except ValidationError as exc:
        raise RuntimeError(
            "LLM response does not match AIAnalysisResult schema"
        ) from exc

    return result