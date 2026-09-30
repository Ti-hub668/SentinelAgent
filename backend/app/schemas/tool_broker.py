from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.execution import (
    ExecutionIntent,
    ExecutionReceipt,
)
from app.schemas.response_plan import (
    ToolRequest,
)
from app.schemas.tool_capability import (
    ToolRegistryAuditMetadata,
)


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

    registry_metadata: (
        ToolRegistryAuditMetadata
        | None
    ) = None

    execution_intent: (
        ExecutionIntent
        | None
    ) = None

    execution_receipt: (
        ExecutionReceipt
        | None
    ) = None

    replayed: bool = False

    output: dict = Field(
        default_factory=dict
    )


class ToolBrokerBatchResult(BaseModel):
    finding_id: int

    results: list[
        ToolExecutionResult
    ] = Field(
        default_factory=list
    )

    simulated_count: int = 0

    replayed_count: int = 0

    blocked_count: int = 0

    failed_count: int = 0