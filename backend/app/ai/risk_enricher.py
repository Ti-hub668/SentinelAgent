import json

from pydantic import ValidationError

from app.ai.llm_client import call_llm
from app.ai.risk_enrichment_prompt_builder import (
    build_risk_enrichment_prompt,
)
from app.schemas.risk_enrichment import (
    RiskEnrichmentInput,
    RiskEnrichmentResult,
)


def clean_risk_enrichment_json(
    raw_text: str,
) -> str:
    text = raw_text.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def enrich_risk(
    data: RiskEnrichmentInput,
) -> RiskEnrichmentResult:
    prompt = build_risk_enrichment_prompt(data)

    raw_response = call_llm(
        prompt,
        response_schema=RiskEnrichmentResult,
    )

    cleaned_response = clean_risk_enrichment_json(
        raw_response
    )

    try:
        parsed = json.loads(cleaned_response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "LLM returned invalid Risk Enrichment JSON"
        ) from exc

    try:
        result = RiskEnrichmentResult.model_validate(
            parsed
        )
    except ValidationError as exc:
        raise RuntimeError(
            "LLM response does not match "
            "RiskEnrichmentResult schema"
        ) from exc

    return result