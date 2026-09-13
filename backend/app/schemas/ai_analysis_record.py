from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AIAnalysisRecordResponse(BaseModel):
    id: int
    finding_id: int

    provider: str
    model: str
    prompt_version: str

    verdict: str
    confidence: float

    summary: str
    risk_explanation: str
    recommended_action: str

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )