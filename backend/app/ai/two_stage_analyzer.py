from app.ai.evidence_assessor import assess_evidence
from app.ai.risk_enricher import enrich_risk
from app.schemas.ai_analysis import AIAnalysisInput
from app.schemas.evidence_assessment import EvidenceAssessmentResult
from app.schemas.risk_enrichment import (
    RiskEnrichmentInput,
    RiskEnrichmentResult,
)

TWO_STAGE_ANALYZER_VERSION = "2stage-v1.3"

def analyze_finding_two_stage(
    data: AIAnalysisInput,
    structured_intelligence: str | None = None,
    rag_context: str | None = None,
) -> tuple[
    EvidenceAssessmentResult,
    RiskEnrichmentResult,
]:
    """
    SentinelAgent two-stage AI analysis.

    Stage 1:
        Finding + Evidence
        -> Evidence Assessment

    Stage 2:
        Evidence Assessment
        + Structured Intelligence
        + RAG
        -> Risk Enrichment

    Structured intelligence and RAG are intentionally
    excluded from Stage 1.
    """

    evidence_result = assess_evidence(data)

    enrichment_input = RiskEnrichmentInput(
        finding_id=data.finding_id,
        finding_category=evidence_result.finding_category,
        evidence_status=evidence_result.evidence_status,
        preliminary_verdict=(
            evidence_result.preliminary_verdict
        ),
        evidence_confidence=evidence_result.confidence,
        evidence_reason=evidence_result.reason,
        severity=data.severity,
        risk_score=data.risk_score,
        risk_level=data.risk_level,
        structured_intelligence=structured_intelligence,
        rag_context=rag_context,
    )

    enrichment_result = enrich_risk(
        enrichment_input
    )

    return (
        evidence_result,
        enrichment_result,
    )