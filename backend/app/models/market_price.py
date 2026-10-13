from datetime import date

from sqlalchemy import CheckConstraint, Date, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketPrice(Base):
    """One day's wholesale (mandi) price of a commodity variety at a market.

    All prices are in Rs per quintal (100 kg).
    """

    __tablename__ = "market_prices"
    __table_args__ = (
        UniqueConstraint(
            "price_date",
            "state_name",
            "market_name",
            "commodity",
            "variety",
            name="uq_market_prices_day_market_commodity_variety",
        ),
        CheckConstraint("modal_price > 0", name="ck_market_prices_modal_positive"),
        CheckConstraint("min_price <= max_price", name="ck_market_prices_min_le_max"),
        Index("ix_market_prices_commodity_date", "commodity", "price_date"),
        Index("ix_market_prices_state_commodity_date", "state_name", "commodity", "price_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    price_date: Mapped[date] = mapped_column(Date)
    state_name: Mapped[str] = mapped_column(String(100))
    district_name: Mapped[str] = mapped_column(String(100), default="", server_default="")
    market_name: Mapped[str] = mapped_column(String(150))
    commodity: Mapped[str] = mapped_column(String(100))
    variety: Mapped[str] = mapped_column(String(100), default="", server_default="")
    min_price: Mapped[int] = mapped_column(Integer)
    max_price: Mapped[int] = mapped_column(Integer)
    modal_price: Mapped[int] = mapped_column(Integer)