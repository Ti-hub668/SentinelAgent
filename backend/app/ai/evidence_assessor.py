import json

from pydantic import ValidationError

from app.ai.evidence_prompt_builder import build_evidence_assessment_prompt
from app.ai.llm_client import call_llm
from app.schemas.ai_analysis import AIAnalysisInput
from app.schemas.evidence_assessment import EvidenceAssessmentResult


def clean_evidence_json(raw_text: str) -> str:
    text = raw_text.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def assess_evidence(
    data: AIAnalysisInput,
) -> EvidenceAssessmentResult:
    prompt = build_evidence_assessment_prompt(data)

    raw_response = call_llm(
        prompt,
        response_schema=EvidenceAssessmentResult,
    )

    cleaned_response = clean_evidence_json(raw_response)

    try:
        parsed = json.loads(cleaned_response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "LLM returned invalid Evidence Assessment JSON"
        ) from exc

    try:
        result = EvidenceAssessmentResult.model_validate(parsed)
    except ValidationError as exc:
        raise RuntimeError(
            "LLM response does not match EvidenceAssessmentResult schema"
        ) from exc

    return result