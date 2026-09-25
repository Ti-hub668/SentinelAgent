from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    scan_task_id: Mapped[int] = mapped_column(
        ForeignKey("scan_tasks.id"),
        nullable=False,
        index=True
    )

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"),
        nullable=False,
        index=True
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    finding_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="info"
    )

    target: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    evidence: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    remediation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    template_id: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True
    )

    cve_ids: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    cwe_ids: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open"
    )
    risk_score: Mapped[int | None] = mapped_column(
    Integer,
    nullable=True
    )

    risk_level: Mapped[str | None] = mapped_column(
    String(20),
    nullable=True
    )

    risk_reason: Mapped[str | None] = mapped_column(
    Text,
    nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False
    )
