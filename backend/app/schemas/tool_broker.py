from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.response_plan import ToolRequest


BrokerStatus = Literal[
    "simulated",
    "blocked",
    "failed",
]


class ToolExecutionResult(BaseModel):
    finding_id: int

    request_index: int

    tool_request: ToolRequest

    policy_decision: str

    authorized: bool

    executed: bool

    dry_run: bool = True

    status: BrokerStatus

    message: str

    output: dict = Field(
        default_factory=dict
    )


class ToolBrokerBatchResult(BaseModel):
    finding_id: int

    results: list[ToolExecutionResult] = Field(
        default_factory=list
    )

    simulated_count: int = 0

    blocked_count: int = 0

    failed_count: int = 0