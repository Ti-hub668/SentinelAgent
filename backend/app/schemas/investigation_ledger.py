from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


InvestigationRunStatus = Literal[
    "running",
    "completed",
    "failed",
]


InvestigationEventStatus = Literal[
    "started",
    "completed",
    "failed",
]


class InvestigationEventRecord(BaseModel):
    id: int
    run_id: int
    event_type: str
    node_name: str | None = None
    status: InvestigationEventStatus
    summary: str | None = None
    event_metadata: dict[str, Any] | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class InvestigationRunRecord(BaseModel):
    id: int
    finding_id: int
    status: InvestigationRunStatus
    final_verdict: str | None = None
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None

    model_config = {
        "from_attributes": True,
    }

class InvestigationRunListItem(InvestigationRunRecord):
    """
    Lightweight run summary used by Audit Center.
    """

    event_count: int = 0

class InvestigationTrace(BaseModel):
    """
    Complete audit trace for one investigation.
    """

    run: InvestigationRunRecord

    events: list[
        InvestigationEventRecord
    ] = Field(
        default_factory=list
    )