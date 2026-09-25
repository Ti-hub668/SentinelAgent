from typing import Literal

from pydantic import BaseModel, Field


EnrichmentPriority = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


class RiskEnrichmentInput(BaseModel):
    finding_id: int

    finding_category: str

    evidence_status: str

    preliminary_verdict: Literal[
        "informational",
        "likely_true_positive",
        "likely_false_positive",
        "needs_review",
    ]

    evidence_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidence_reason: str

    severity: str

    risk_score: int | None = None

    risk_level: str | None = None

    structured_intelligence: str | None = None

    rag_context: str | None = None


class RiskEnrichmentResult(BaseModel):
    final_verdict: Literal[
        "informational",
        "likely_true_positive",
        "likely_false_positive",
        "needs_review",
    ]

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    priority: EnrichmentPriority

    summary: str

    risk_explanation: str

    intelligence_context: str

    recommended_action: str