"""Maps our catalog crops to the commodity names used in the price data."""

import re
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.market_price import MarketPrice

# catalog crop name -> commodity names in the price data.
# Names are compared ignoring case, spaces and punctuation.
# Where a crop has several product forms with very different prices, one is chosen.
CROP_COMMODITY_ALIASES: dict[str, tuple[str, ...]] = {
    "Rice (Paddy)": ("Paddy(Dhan)(Common)",),
    "Maize": ("Maize",),
    "Tomato": ("Tomato",),
    "Brinjal (Eggplant)": ("Brinjal",),
    "Okra (Lady's finger)": ("Bhindi(Ladies Finger)",),
    "Chilli": ("Green Chilli",),
    "Cowpea": ("Cowpea(Veg)",),
    "Groundnut": ("Groundnut",),
    "Banana": ("Banana",),
    "Sugarcane": ("Sugarcane",),
    "Ginger": ("Ginger(Dry)",),
    "Turmeric": ("Turmeric",),
    "Tapioca (Cassava)": ("Tapioca",),
    "Coconut": ("Coconut",),
    "Rubber": ("Rubber",),
    "Arecanut": ("Arecanut(Betelnut/Supari)",),
    "Black Pepper": ("Black pepper",),
    "Cardamom": ("Cardamoms", "Cardamom"),
    "Coffee": ("Coffee",),
    "Cashew": ("Cashewnuts",),
    "Mango": ("Mango",),
}


def normalise_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def match_names(crop_name: str, available: Iterable[str]) -> list[str]:
    """The names in `available` that are price-data names for this crop."""
    wanted = {normalise_name(alias) for alias in CROP_COMMODITY_ALIASES.get(crop_name, ())}
    if not wanted:
        return []
    matched: list[str] = []
    for name in sorted(available):
        if normalise_name(name) in wanted and name not in matched:
            matched.append(name)
    return matched


def resolve_commodities(db: Session, crop_name: str) -> list[str]:
    available = db.scalars(select(MarketPrice.commodity).distinct()).all()
    return match_names(crop_name, available)


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.execute(
            select(
                MarketPrice.commodity,
                func.count(),
                func.min(MarketPrice.price_date),
                func.max(MarketPrice.price_date),
            ).group_by(MarketPrice.commodity)
        ).all()
    finally:
        db.close()

    stats = {name: (count, first, last) for name, count, first, last in rows}
    used: set[str] = set()

    print("Catalog crop -> commodity in the price data")
    for crop in CROP_COMMODITY_ALIASES:
        names = match_names(crop, stats)
        if not names:
            print(f"   {crop}: no price data yet")
            continue
        for name in names:
            count, first, last = stats[name]
            used.add(name)
            print(f"   {crop} -> {name}: {count} rows, {first} to {last}")

    unmapped = sorted(set(stats) - used)
    print("\nCommodities in the database that match no catalog crop:")
    print("   " + (", ".join(unmapped) if unmapped else "none"))


if __name__ == "__main__":
    main()