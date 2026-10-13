import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.crop_type import CropType
from app.models.market_price import MarketPrice
from app.schemas.market import AvailableCrop, PriceBoard, PriceTrend
from app.services import market_logic as logic
from app.services.growth import today_local
from app.services.market_mapping import match_names, resolve_commodities

DEFAULT_STATE = "Kerala"
MIN_TREND_DAYS = 7
MAX_TREND_DAYS = 365


def _state(state: str | None) -> str:
    return (state or "").strip() or DEFAULT_STATE


def _conditions(names: list[str], state: str, variety: str | None = None) -> list:
    conditions = [
        MarketPrice.commodity.in_(names),
        func.lower(MarketPrice.state_name) == state.lower(),
    ]
    if variety:
        conditions.append(func.lower(MarketPrice.variety) == variety.strip().lower())
    return conditions


def list_available_crops(
    db: Session, state: str | None, today: dt.date | None = None
) -> list[AvailableCrop]:
    today = today or today_local()
    state = _state(state)

    latest_by_name = dict(
        db.execute(
            select(MarketPrice.commodity, func.max(MarketPrice.price_date))
            .where(func.lower(MarketPrice.state_name) == state.lower())
            .group_by(MarketPrice.commodity)
        ).all()
    )

    result: list[AvailableCrop] = []
    for crop in db.scalars(select(CropType).order_by(CropType.category, CropType.name)):
        names = match_names(crop.name, latest_by_name)
        if not names:
            continue
        latest = max(latest_by_name[name] for name in names)
        age = logic.days_old(latest, today)
        result.append(
            AvailableCrop(
                crop_type_id=crop.id,
                name=crop.name,
                category=crop.category,
                latest_date=latest,
                days_old=age,
                stale=logic.is_stale(age),
            )
        )
    return result


def get_price_board(
    db: Session,
    crop_type: CropType,
    state: str | None,
    district: str | None,
    variety: str | None = None,
    today: dt.date | None = None,
) -> PriceBoard:
    today = today or today_local()
    state = _state(state)
    variety = (variety or "").strip() or None
    names = resolve_commodities(db, crop_type.name)

    board = PriceBoard(
        crop_type_id=crop_type.id,
        crop_name=crop_type.name,
        state=state,
        commodity_names=names,
        has_data=False,
        variety=variety,
    )
    if not names:
        return board

    board.varieties = sorted(
        v
        for v in db.scalars(
            select(MarketPrice.variety).where(*_conditions(names, state)).distinct()
        )
        if v
    )

    conditions = _conditions(names, state, variety)
    as_of = db.scalar(select(func.max(MarketPrice.price_date)).where(*conditions))
    if as_of is None:
        return board

    window_start = as_of - dt.timedelta(days=logic.FRESH_WINDOW_DAYS - 1)
    rows = db.scalars(
        select(MarketPrice).where(
            *conditions,
            MarketPrice.price_date >= window_start,
            MarketPrice.price_date <= as_of,
        )
    ).all()

    markets, summary = logic.build_board(rows, as_of, district)
    age = logic.days_old(as_of, today)

    board.has_data = True
    board.as_of = as_of
    board.days_old = age
    board.stale = logic.is_stale(age)
    board.markets = markets
    board.summary = summary
    return board


def get_price_trend(
    db: Session,
    crop_type: CropType,
    state: str | None,
    days: int = 90,
    variety: str | None = None,
    today: dt.date | None = None,
) -> PriceTrend:
    today = today or today_local()
    state = _state(state)
    variety = (variety or "").strip() or None
    days = min(max(days, MIN_TREND_DAYS), MAX_TREND_DAYS)

    trend = PriceTrend(
        crop_type_id=crop_type.id,
        crop_name=crop_type.name,
        state=state,
        has_data=False,
        days=days,
        variety=variety,
    )

    names = resolve_commodities(db, crop_type.name)
    if not names:
        return trend

    conditions = _conditions(names, state, variety)
    as_of = db.scalar(select(func.max(MarketPrice.price_date)).where(*conditions))
    if as_of is None:
        return trend

    # extra history so the 30-day change and the signal can be computed
    lookback = max(days, logic.SIGNAL_WINDOW_DAYS) + 30
    rows = db.scalars(
        select(MarketPrice).where(
            *conditions,
            MarketPrice.price_date >= as_of - dt.timedelta(days=lookback),
            MarketPrice.price_date <= as_of,
        )
    ).all()

    all_points = logic.daily_series(rows)
    visible_start = as_of - dt.timedelta(days=days - 1)
    points = [p for p in all_points if p.date >= visible_start]
    age = logic.days_old(as_of, today)

    trend.has_data = True
    trend.as_of = as_of
    trend.days_old = age
    trend.stale = logic.is_stale(age)
    trend.points = points
    trend.latest_modal = all_points[-1].median_modal
    trend.change_7d_pct = logic.change_since(all_points, 7)
    trend.change_30d_pct = logic.change_since(all_points, 30)
    trend.signal = logic.compute_signal(all_points)
    return trend