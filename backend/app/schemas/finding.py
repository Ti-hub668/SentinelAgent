from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FindingResponse(BaseModel):
    id: int
    scan_task_id: int
    asset_id: int

    source: str
    finding_type: str
    title: str
    severity: str
    target: str

    description: str | None = None
    evidence: str | None = None
    remediation: str | None = None

    status: str
    risk_score: int | None = None
    risk_level: str | None = None
    risk_reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)