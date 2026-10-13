from datetime import date, timedelta

from app.db.seed import CATALOG
from app.models.crop_type import CropType
from app.models.market_price import MarketPrice
from app.services import market_service as ms

AS_OF = date(2025, 10, 30)
TODAY = date(2026, 10, 8)


def make_crop_type(db, name="Coconut"):
    item = next(c for c in CATALOG if c["name"] == name)
    crop_type = CropType(**item)
    db.add(crop_type)
    db.commit()
    db.refresh(crop_type)
    return crop_type


def add_price(
    db,
    day,
    market="Koduvayoor",
    district="Palakkad",
    commodity="Coconut",
    variety="Big",
    modal=7400,
    state="Kerala",
):
    db.add(
        MarketPrice(
            price_date=day,
            state_name=state,
            district_name=district,
            market_name=market,
            commodity=commodity,
            variety=variety,
            min_price=modal - 200,
            max_price=modal + 200,
            modal_price=modal,
        )
    )


def seed_two_markets(db):
    add_price(db, AS_OF, market="Koduvayoor", district="Palakkad", modal=7400)
    add_price(db, AS_OF, market="Munnar", district="Idukki", modal=6500, variety="Other")
    add_price(
        db, AS_OF, market="Pollachi", district="Coimbatore", state="Tamil Nadu", modal=9999
    )
    db.commit()


def test_board_for_crop(db_session):
    coconut = make_crop_type(db_session)
    seed_two_markets(db_session)

    board = ms.get_price_board(db_session, coconut, "kerala", "Palakkad", today=TODAY)

    assert board.has_data is True
    assert board.commodity_names == ["Coconut"]
    assert board.as_of == AS_OF
    assert board.days_old == (TODAY - AS_OF).days
    assert board.stale is True
    assert [m.market for m in board.markets] == ["Koduvayoor", "Munnar"]
    assert board.markets[0].in_my_district is True
    assert board.varieties == ["Big", "Other"]
    assert board.summary.highest_modal == 7400
    assert board.summary.lowest_modal == 6500
    assert board.unit == "Rs per quintal"

    recent = ms.get_price_board(
        db_session, coconut, "Kerala", None, today=AS_OF + timedelta(days=3)
    )
    assert recent.stale is False


def test_board_variety_filter(db_session):
    coconut = make_crop_type(db_session)
    seed_two_markets(db_session)

    board = ms.get_price_board(db_session, coconut, "Kerala", None, variety="other", today=TODAY)

    assert [m.market for m in board.markets] == ["Munnar"]
    assert board.varieties == ["Big", "Other"]


def test_board_for_a_crop_without_price_data(db_session):
    pepper = make_crop_type(db_session, "Black Pepper")
    seed_two_markets(db_session)  # only coconut prices exist

    board = ms.get_price_board(db_session, pepper, "Kerala", None, today=TODAY)

    assert board.has_data is False
    assert board.markets == []
    assert board.as_of is None
    assert board.commodity_names == []


def test_board_for_a_state_without_data(db_session):
    coconut = make_crop_type(db_session)
    seed_two_markets(db_session)
    add_price(db_session, AS_OF, market="Mysuru", state="Karnataka", district="Mysuru")
    db_session.commit()

    board = ms.get_price_board(db_session, coconut, "Maharashtra", None, today=TODAY)
    assert board.has_data is False

    karnataka = ms.get_price_board(db_session, coconut, "Karnataka", None, today=TODAY)
    assert [m.market for m in karnataka.markets] == ["Mysuru"]


def test_board_defaults_to_kerala(db_session):
    coconut = make_crop_type(db_session)
    seed_two_markets(db_session)

    board = ms.get_price_board(db_session, coconut, None, None, today=TODAY)

    assert board.state == "Kerala"
    assert board.has_data is True


def seed_rising_series(db):
    for i in range(40):
        add_price(db, AS_OF - timedelta(days=39 - i), modal=7000 + 10 * i)
    db.commit()


def test_trend(db_session):
    coconut = make_crop_type(db_session)
    seed_rising_series(db_session)

    trend = ms.get_price_trend(db_session, coconut, "Kerala", days=30, today=TODAY)

    assert trend.has_data is True
    assert trend.days == 30
    assert len(trend.points) == 30
    assert trend.points[0].date == AS_OF - timedelta(days=29)
    assert trend.points[-1].date == AS_OF
    assert trend.latest_modal == 7390
    assert trend.change_7d_pct == 1.0
    assert trend.change_30d_pct == 4.2
    assert trend.signal.label == "stable"
    assert trend.signal.average_modal == 7245
    assert trend.stale is True


def test_trend_clamps_days_and_handles_no_data(db_session):
    coconut = make_crop_type(db_session)
    seed_rising_series(db_session)

    short = ms.get_price_trend(db_session, coconut, "Kerala", days=3, today=TODAY)
    assert short.days == 7
    assert len(short.points) == 7

    long = ms.get_price_trend(db_session, coconut, "Kerala", days=1000, today=TODAY)
    assert long.days == 365

    pepper = make_crop_type(db_session, "Black Pepper")
    empty = ms.get_price_trend(db_session, pepper, "Kerala", today=TODAY)
    assert empty.has_data is False
    assert empty.points == []
    assert empty.signal is None


def test_available_crops_lists_only_crops_with_data(db_session):
    make_crop_type(db_session, "Coconut")
    make_crop_type(db_session, "Black Pepper")
    seed_two_markets(db_session)

    crops = ms.list_available_crops(db_session, "Kerala", today=TODAY)

    assert [c.name for c in crops] == ["Coconut"]
    assert crops[0].latest_date == AS_OF
    assert crops[0].days_old == (TODAY - AS_OF).days
    assert crops[0].stale is True