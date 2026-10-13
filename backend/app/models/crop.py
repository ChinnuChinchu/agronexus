from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.crop_type import CropType


class Crop(Base):
    __tablename__ = "crops"
    __table_args__ = (
        CheckConstraint("status IN ('growing', 'harvested', 'failed')", name="ck_crops_status"),
        CheckConstraint(
            "expected_harvest_date IS NULL OR expected_harvest_date >= planting_date",
            name="ck_crops_harvest_after_planting",
        ),
        CheckConstraint(
            "area_acres IS NULL OR area_acres > 0", name="ck_crops_area_positive"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    crop_type_id: Mapped[int] = mapped_column(
        ForeignKey("crop_types.id", ondelete="RESTRICT"), index=True
    )

    name: Mapped[str] = mapped_column(String(100))
    variety: Mapped[str | None] = mapped_column(String(100), nullable=True)
    area_acres: Mapped[float | None] = mapped_column(Float, nullable=True)

    planting_date: Mapped[date] = mapped_column(Date)
    expected_harvest_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="growing", server_default="growing")
    actual_harvest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    yield_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    yield_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    crop_type: Mapped[CropType] = relationship(lazy="joined")