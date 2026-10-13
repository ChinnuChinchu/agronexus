import datetime as dt
from collections import defaultdict
from collections.abc import Sequence
from statistics import mean, median
from typing import Any

from app.schemas.market import MarketPriceRow, PriceSummary, Signal, TrendPoint

FRESH_WINDOW_DAYS = 14      # markets that reported within this many days of the newest date
STALE_AFTER_DAYS = 14       # data older than this gets a warning
SIGNAL_WINDOW_DAYS = 30
SIGNAL_THRESHOLD_PCT = 5.0
SIGNAL_MIN_POINTS = 5


def days_old(as_of: dt.date | None, today: dt.date) -> int | None:
    return None if as_of is None else (today - as_of).days


def is_stale(age: int | None) -> bool:
    return age is not None and age > STALE_AFTER_DAYS


def build_board(
    rows: Sequence[Any], as_of: dt.date, district: str | None
) -> tuple[list[MarketPriceRow], PriceSummary | None]:
    """The latest price at each market (and variety), own district first."""
    cutoff = as_of - dt.timedelta(days=FRESH_WINDOW_DAYS - 1)
    latest: dict[tuple[str, str], Any] = {}
    for row in rows:
        if row.price_date < cutoff or row.price_date > as_of:
            continue
        key = (row.market_name, row.variety)
        current = latest.get(key)
        if current is None or row.price_date > current.price_date:
            latest[key] = row

    mine = (district or "").strip().lower()
    items = [
        MarketPriceRow(
            market=row.market_name,
            district=row.district_name,
            variety=row.variety,
            date=row.price_date,
            min_price=row.min_price,
            max_price=row.max_price,
            modal_price=row.modal_price,
            in_my_district=bool(mine) and row.district_name.strip().lower() == mine,
        )
        for row in latest.values()
    ]
    items.sort(key=lambda m: (not m.in_my_district, -m.modal_price, m.market, m.variety))

    if not items:
        return items, None

    modals = [m.modal_price for m in items]
    summary = PriceSummary(
        average_modal=round(mean(modals)),
        highest_modal=max(modals),
        lowest_modal=min(modals),
        markets=len({m.market for m in items}),
    )
    return items, summary


def daily_series(rows: Sequence[Any]) -> list[TrendPoint]:
    """One point per day: the median modal price across the markets that reported."""
    by_day: dict[dt.date, list[Any]] = defaultdict(list)
    for row in rows:
        by_day[row.price_date].append(row)

    return [
        TrendPoint(
            date=day,
            median_modal=round(median(r.modal_price for r in by_day[day])),
            markets=len({r.market_name for r in by_day[day]}),
        )
        for day in sorted(by_day)
    ]


def _pct_change(new: int, old: int) -> float | None:
    if not old:
        return None
    return round((new - old) / old * 100, 1)


def change_since(points: Sequence[TrendPoint], days: int) -> float | None:
    """Percent change of the latest point against the last point at least `days` earlier."""
    if not points:
        return None
    latest = points[-1]
    target = latest.date - dt.timedelta(days=days)
    earlier = [p for p in points if p.date <= target]
    if not earlier:
        return None
    return _pct_change(latest.median_modal, earlier[-1].median_modal)


def compute_signal(points: Sequence[TrendPoint]) -> Signal:
    """The latest price against its own recent average. An indication, not a forecast."""
    insufficient = Signal(
        label="insufficient_data",
        pct_vs_average=None,
        average_modal=None,
        message="Not enough recent price data to compare.",
    )
    if not points:
        return insufficient

    latest = points[-1]
    window_start = latest.date - dt.timedelta(days=SIGNAL_WINDOW_DAYS - 1)
    window = [p for p in points if p.date >= window_start]
    if len(window) < SIGNAL_MIN_POINTS:
        return insufficient

    average = mean(p.median_modal for p in window)
    pct = round((latest.median_modal - average) / average * 100, 1)

    if pct > SIGNAL_THRESHOLD_PCT:
        label = "above_average"
        message = f"The latest price is {pct}% above its {SIGNAL_WINDOW_DAYS}-day average."
    elif pct < -SIGNAL_THRESHOLD_PCT:
        label = "below_average"
        message = f"The latest price is {abs(pct)}% below its {SIGNAL_WINDOW_DAYS}-day average."
    else:
        label = "stable"
        message = f"The latest price is close to its {SIGNAL_WINDOW_DAYS}-day average."

    return Signal(
        label=label, pct_vs_average=pct, average_modal=round(average), message=message
    )