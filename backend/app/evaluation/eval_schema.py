from pydantic import BaseModel


class EvalCase(BaseModel):
    id: str

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

    expected_verdict: str