from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.policy import (
    HumanApprovalRequest,
    PolicyEvaluationResult,
)
from app.schemas.response_plan import ResponsePlan
from app.schemas.tool_broker import (
    ToolExecutionResult,
)


WorkflowStatus = Literal[
    "running",
    "failed",
    "investigation_completed",
    "awaiting_approval",
    "policy_blocked",
    "ready_for_execution",
    "dry_run_executed",
    "executed",
]

class AgentWorkflowStartResponse(BaseModel):
    """
    Lightweight response returned immediately
    after an Agent workflow has been scheduled.
    """

    run_id: int

    finding_id: int

    run_status: Literal[
        "running"
    ] = "running"

    workflow_status: Literal[
        "running"
    ] = "running"

class ApprovalReviewInput(BaseModel):
    reviewer: str = Field(
        min_length=1,
        max_length=100,
    )

    reason: str = Field(
        min_length=1,
        max_length=1000,
    )


class AgentWorkflowSummary(BaseModel):
    run_id: int

    finding_id: int

    run_status: str

    workflow_status: WorkflowStatus

    final_verdict: str | None = None

    response_plan: ResponsePlan | None = None

    policy_evaluation: (
        PolicyEvaluationResult | None
    ) = None

    approvals: list[
        HumanApprovalRequest
    ] = Field(default_factory=list)

    tool_results: list[
        ToolExecutionResult
    ] = Field(default_factory=list)

    event_count: int = 0