from datetime import date, timedelta
from types import SimpleNamespace

from app.schemas.market import TrendPoint
from app.services import market_logic as ml

AS_OF = date(2025, 10, 30)


def d(offset):
    return AS_OF + timedelta(days=offset)


def row(day, market="A", district="Palakkad", variety="Big", modal=7000):
    return SimpleNamespace(
        price_date=day,
        market_name=market,
        district_name=district,
        variety=variety,
        min_price=modal - 200,
        max_price=modal + 200,
        modal_price=modal,
    )


def points(*pairs):
    return [TrendPoint(date=day, median_modal=value, markets=1) for day, value in pairs]


def series(values):
    """Consecutive daily points ending at AS_OF."""
    last = len(values) - 1
    return points(*[(d(i - last), value) for i, value in enumerate(values)])


# ---------- age ----------
def test_days_old_and_stale():
    assert ml.days_old(AS_OF, date(2025, 11, 4)) == 5
    assert ml.days_old(None, date(2025, 11, 4)) is None
    assert ml.is_stale(14) is False
    assert ml.is_stale(15) is True
    assert ml.is_stale(None) is False


# ---------- price board ----------
def test_board_keeps_latest_row_per_market_and_variety():
    rows = [
        row(d(-3), modal=7000),
        row(d(0), modal=7400),
        row(d(-1), market="B", modal=7100),
    ]
    items, _ = ml.build_board(rows, AS_OF, None)

    assert [(i.market, i.modal_price) for i in items] == [("A", 7400), ("B", 7100)]
    assert items[0].date == d(0)


def test_board_ignores_markets_not_reporting_recently():
    rows = [row(d(0), market="A"), row(d(-20), market="Old")]
    items, _ = ml.build_board(rows, AS_OF, None)
    assert [i.market for i in items] == ["A"]


def test_board_lists_my_district_first():
    rows = [
        row(d(0), market="Expensive", district="Idukki", modal=9000),
        row(d(0), market="Koduvayoor", district="Palakkad", modal=7400),
    ]
    items, _ = ml.build_board(rows, AS_OF, " palakkad ")

    assert [i.market for i in items] == ["Koduvayoor", "Expensive"]
    assert items[0].in_my_district is True
    assert items[1].in_my_district is False


def test_board_summary():
    rows = [
        row(d(0), market="A", modal=7000),
        row(d(0), market="B", modal=8000),
        row(d(0), market="C", modal=6000),
    ]
    _, summary = ml.build_board(rows, AS_OF, None)
    assert (summary.average_modal, summary.highest_modal, summary.lowest_modal) == (
        7000,
        8000,
        6000,
    )
    assert summary.markets == 3


def test_board_empty():
    items, summary = ml.build_board([], AS_OF, None)
    assert items == []
    assert summary is None


# ---------- trend ----------
def test_daily_series_uses_median_and_counts_markets():
    rows = [
        row(d(0), market="A", modal=7000),
        row(d(0), market="B", modal=8000),
        row(d(0), market="C", modal=9000),
        row(d(-1), market="A", modal=7500),
    ]
    result = ml.daily_series(rows)

    assert [p.date for p in result] == [d(-1), d(0)]
    assert result[0].median_modal == 7500
    assert result[1].median_modal == 8000
    assert result[1].markets == 3


def test_change_since():
    data = points((d(-30), 6000), (d(-8), 7000), (d(-2), 7200), (d(0), 7700))
    assert ml.change_since(data, 7) == 10.0   # against d(-8): 7000 -> 7700
    assert ml.change_since(data, 30) == 28.3  # against d(-30): 6000 -> 7700
    assert ml.change_since(data[2:], 7) is None
    assert ml.change_since([], 7) is None


# ---------- signal ----------
def test_signal_above_average():
    signal = ml.compute_signal(series([7000] * 9 + [8000]))
    assert signal.label == "above_average"
    assert signal.pct_vs_average == 12.7
    assert signal.average_modal == 7100
    assert "above" in signal.message


def test_signal_below_average():
    signal = ml.compute_signal(series([7000] * 9 + [6000]))
    assert signal.label == "below_average"
    assert signal.pct_vs_average == -13.0
    assert "below" in signal.message


def test_signal_stable():
    signal = ml.compute_signal(series([7000] * 9 + [7100]))
    assert signal.label == "stable"
    assert signal.average_modal == 7010


def test_signal_needs_enough_points():
    signal = ml.compute_signal(series([7000, 7100, 7200, 7300]))
    assert signal.label == "insufficient_data"
    assert signal.pct_vs_average is None


def test_signal_ignores_points_older_than_the_window():
    data = points((d(-60), 1000)) + series([7000] * 5)
    signal = ml.compute_signal(data)
    assert signal.label == "stable"
    assert signal.average_modal == 7000