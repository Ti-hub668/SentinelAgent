from typing import Literal

from pydantic import BaseModel, Field


GroundingStatus = Literal[
    "supported",
    "partially_supported",
    "unsupported",
]


class GroundingCheck(BaseModel):
    """
    Result of one deterministic grounding rule.
    """

    rule: str

    passed: bool

    reason: str


class GroundingResult(BaseModel):
    """
    Final grounding validation result for an investigation.
    """

    finding_id: int

    status: GroundingStatus

    score: float = Field(
        ge=0.0,
        le=1.0,
    )

    checks: list[GroundingCheck]

    original_verdict: str

    grounded_verdict: str

    requires_human_review: bool

    reason: str