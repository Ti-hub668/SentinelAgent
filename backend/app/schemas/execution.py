from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.policy import (
    PolicyDecision,
)
from app.schemas.response_plan import (
    ResponseActionType,
)


ApprovalExecutionStatus = Literal[
    "not_required",
    "missing",
    "pending",
    "approved",
    "rejected",
    "unknown",
]


ExecutionOutcome = Literal[
    "simulated",
    "executed",
    "replayed",
    "failed",
]


class ExecutionAuthorizationSnapshot(
    BaseModel
):
    """
    Authorization state captured immediately
    before an executor may be invoked.
    """

    policy_decision: PolicyDecision

    approval_required: bool

    approval_status: (
        ApprovalExecutionStatus
    )

    reviewer: str | None = None


class ExecutionIntent(BaseModel):
    """
    Stable description of one governed tool
    execution attempt.
    """

    execution_id: str = Field(
        min_length=1,
    )

    finding_id: int = Field(
        ge=1,
    )

    run_id: int = Field(
        ge=1,
    )

    request_index: int = Field(
        ge=0,
    )

    tool_name: ResponseActionType

    target: str | None = None

    request_fingerprint: str = Field(
        min_length=1,
    )

    idempotency_key: str = Field(
        min_length=1,
    )

    authorization: (
        ExecutionAuthorizationSnapshot
    )

    attempt: int = Field(
        default=1,
        ge=1,
    )

    created_at: datetime


class ExecutionReceipt(BaseModel):
    """
    Auditable result for an ExecutionIntent.
    """

    execution_id: str

    idempotency_key: str

    outcome: ExecutionOutcome

    executor_invoked: bool

    replayed: bool = False

    original_event_id: int | None = None

    completed_at: datetime