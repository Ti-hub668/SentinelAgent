from typing import Literal

from pydantic import BaseModel, Field


AgentAction = Literal[
    "close_as_info",
    "mark_false_positive",
    "request_manual_review",
    "recommend_remediation",
]


class AgentDecisionInput(BaseModel):
    finding_id: int
    ai_analysis_id: int

    verdict: str
    confidence: float = Field(
        ge=0.0,
        le=1.0
    )

    severity: str
    risk_score: int
    risk_level: str


class AgentDecisionOutput(BaseModel):
    action: AgentAction

    priority: Literal[
        "low",
        "medium",
        "high"
    ]

    reason: str

    requires_human_review: bool

    recommended_next_step: str