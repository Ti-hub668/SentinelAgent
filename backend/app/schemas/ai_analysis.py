from pydantic import BaseModel, Field


class AIAnalysisInput(BaseModel):
    finding_id: int

    source: str
    finding_type: str
    title: str
    severity: str
    target: str

    description: str | None = None
    evidence: str | None = None
    remediation: str | None = None

    risk_score: int | None = None
    risk_level: str | None = None
    risk_reason: str | None = None


class AIAnalysisResult(BaseModel):
    verdict: str

    confidence: float = Field(
        ge=0.0,
        le=1.0
    )

    summary: str
    risk_explanation: str
    recommended_action: str