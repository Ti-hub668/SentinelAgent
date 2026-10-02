from typing import Literal

from pydantic import BaseModel, Field


ReconciliationState = Literal[
    "confirmed_completed",
    "not_found",
    "unsupported",
    "unknown",
]


class ToolReconciliationResult(BaseModel):
    state: ReconciliationState

    message: str

    output: dict = Field(
        default_factory=dict
    )

class ReconciliationRunSummary(
    BaseModel
):
    run_id: int = Field(
        ge=1,
    )

    checked: int = Field(
        ge=0,
    )

    confirmed: int = Field(
        ge=0,
    )

    unresolved: int = Field(
        ge=0,
    )

    failed: int = Field(
        ge=0,
    )