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

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False
    )