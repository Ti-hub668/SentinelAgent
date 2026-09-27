from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.response_plan import ToolRequest


PolicyDecision = Literal[
    "ALLOW",
    "DENY",
    "REQUIRE_APPROVAL",
]


ApprovalStatus = Literal[
    "pending",
    "approved",
    "rejected",
]


class ToolPolicyResult(BaseModel):
    """
    Deterministic policy result for one ToolRequest.
    """

    request_index: int

    tool_request: ToolRequest

    decision: PolicyDecision

    reason: str

    requires_human_approval: bool = False


class PolicyEvaluationResult(BaseModel):
    """
    Policy evaluation result for one ResponsePlan.
    """

    finding_id: int

    grounded_verdict: str

    dry_run: bool

    results: list[ToolPolicyResult] = Field(
        default_factory=list
    )

    allow_count: int = 0

    deny_count: int = 0

    approval_count: int = 0


class HumanApprovalRequest(BaseModel):
    """
    Explicit human approval record generated when
    Policy Engine returns REQUIRE_APPROVAL.
    """

    finding_id: int

    request_index: int

    tool_request: ToolRequest

    policy_reason: str

    status: ApprovalStatus = "pending"

    reviewer: str | None = None

    review_reason: str | None = None