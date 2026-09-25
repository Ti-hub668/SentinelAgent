from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id"),
        nullable=False,
        index=True
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    prompt_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="v1"
    )

    verdict: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    risk_explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    recommended_action: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    use_rag: Mapped[bool | None] = mapped_column(
    nullable=True
    )

    rag_top_k: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    retrieved_context: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    # --------------------------------
    # Stage 1 Evidence Assessment Trace
    # --------------------------------

    finding_category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    evidence_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    preliminary_verdict: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    evidence_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    evidence_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------
    # Stage 2 Risk Enrichment Trace
    # --------------------------------

    priority: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # --------------------------------
    # Structured Intelligence Trace
    # --------------------------------

    structured_intelligence: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False
    )