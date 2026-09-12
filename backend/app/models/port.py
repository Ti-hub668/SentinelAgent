from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Port(Base):
    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    scan_task_id: Mapped[int] = mapped_column(
        ForeignKey("scan_tasks.id"),
        nullable=False
    )

    host: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    protocol: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    service: Mapped[str] = mapped_column(
        String(100),
        default="",
        nullable=False
    )

    product: Mapped[str] = mapped_column(
        String(255),
        default="",
        nullable=False
    )

    version: Mapped[str] = mapped_column(
        String(255),
        default="",
        nullable=False
    )