from typing import Literal

from pydantic import BaseModel, Field


DecisionAction = Literal[
    "close_false_positive",
    "monitor",
    "request_manual_review",
    "create_remediation_task",
    "escalate",
]


DecisionPriority = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


class DecisionResult(BaseModel):
    action: DecisionAction

    priority: DecisionPriority

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    reason: str

    requires_human_review: bool