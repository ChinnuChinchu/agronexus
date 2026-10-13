from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CropType(Base):
    __tablename__ = "crop_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50))
    cycle: Mapped[str] = mapped_column(String(20))  # "seasonal" or "perennial"

    # seasonal crops: length of the cycle from planting to harvest
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # perennial crops: plant age (months) when it starts bearing
    bearing_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # seasonal:  [{"name": ..., "start_pct": 0, "end_pct": 10}, ...]
    # perennial: [{"name": ..., "start_month": 0, "end_month": 12 or null}, ...]
    stages: Mapped[list] = mapped_column(JSONB)