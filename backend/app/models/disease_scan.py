from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DiseaseScan(Base):
    """The result of one photo analysis. The photo itself is never stored."""

    __tablename__ = "disease_scans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ok', 'uncertain', 'crop_mismatch')", name="ck_disease_scans_status"
        ),
        CheckConstraint(
            "level IN ('strong', 'possible', 'uncertain')", name="ck_disease_scans_level"
        ),
        Index("ix_disease_scans_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    crop_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    level: Mapped[str] = mapped_column(String(20))
    result_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    confidence_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    healthy: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )