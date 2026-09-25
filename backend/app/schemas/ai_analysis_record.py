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

    # 新增：RAG Trace
    use_rag: bool | None = None
    rag_top_k: int | None = None
    retrieved_context: str | None = None

    # Stage 1 Evidence Assessment Trace
    finding_category: str | None = None
    evidence_status: str | None = None
    preliminary_verdict: str | None = None
    evidence_confidence: float | None = None
    evidence_reason: str | None = None

    # Stage 2 Risk Enrichment Trace
    priority: str | None = None

    # Structured Intelligence Trace
    structured_intelligence: str | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )