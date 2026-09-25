from typing import Literal

from pydantic import BaseModel, Field


FindingCategory = Literal[
    "information_observation",
    "security_misconfiguration",
    "exposure",
    "vulnerability",
    "ambiguous_security_signal",
]


EvidenceStatus = Literal[
    "confirmed",
    "insufficient",
    "contradicted",
]


PreliminaryVerdict = Literal[
    "informational",
    "likely_true_positive",
    "likely_false_positive",
    "needs_review",
]


class EvidenceAssessmentResult(BaseModel):
    finding_category: FindingCategory

    evidence_status: EvidenceStatus

    preliminary_verdict: PreliminaryVerdict

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    reason: str