"""Durable, fenced ownership of an execution slot."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ExecutionClaim(Base):
    __tablename__ = "execution_claims"
    __table_args__ = (
        CheckConstraint("status IN ('claimed','completed','failed','released')", name="ck_execution_claim_status"),
        CheckConstraint("attempt >= 1", name="ck_execution_claim_attempt"),
        {"mysql_engine": "InnoDB"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("investigation_runs.id", ondelete="CASCADE"), index=True)
    request_index: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(80), nullable=False)
    execution_id: Mapped[str] = mapped_column(
    String(40),
    nullable=False,
    )

    tool_name: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    owner_token: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    receipt: Mapped[dict | None] = mapped_column(JSON)
    output: Mapped[dict | None] = mapped_column(JSON)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("investigation_events.id"))
