from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.market_price import MarketPrice
from app.services.market_import import import_file

HEADER = (
    "t\tcmdty\tmarket_id\tmarket_name\tstate_id\tstate_name\t"
    "district_id\tdistrict_name\tvariety\tp_min\tp_max\tp_modal"
)


def write(tmp_path, *lines, name="prices.tsv"):
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def row(
    day="30-10-2025",
    commodity="Coconut",
    market="Koduvayoor",
    state="Kerala",
    district="Palakkad",
    variety="Big",
    pmin=7200,
    pmax=7600,
    modal=7400,
):
    values = (day, commodity, 144, market, 32, state, 593, district, variety, pmin, pmax, modal)
    return "\t".join(str(v) for v in values)


def count(db):
    return db.scalar(select(func.count()).select_from(MarketPrice))


def test_imports_rows(db_session, tmp_path):
    path = write(
        tmp_path,
        HEADER,
        row(),
        row(market="Munnar", district="Idukki", pmin=6000, pmax=6800, modal=6500),
    )
    result = import_file(db_session, path)

    assert result.rows_read == 2
    assert result.rows_imported == 2
    assert count(db_session) == 2
    assert result.first_date == result.last_date == date(2025, 10, 30)
    assert result.commodities["Coconut"] == 2

    price = db_session.scalar(select(MarketPrice).where(MarketPrice.market_name == "Koduvayoor"))
    assert price.price_date == date(2025, 10, 30)
    assert price.state_name == "Kerala"
    assert price.district_name == "Palakkad"
    assert price.variety == "Big"
    assert (price.min_price, price.max_price, price.modal_price) == (7200, 7600, 7400)


def test_reimport_updates_prices_without_duplicates(db_session, tmp_path):
    import_file(db_session, write(tmp_path, HEADER, row(modal=7400)))
    import_file(db_session, write(tmp_path, HEADER, row(modal=7500), name="again.tsv"))

    assert count(db_session) == 1
    db_session.expire_all()
    assert db_session.scalar(select(MarketPrice.modal_price)) == 7500


def test_duplicate_rows_in_one_file_keep_the_last(db_session, tmp_path):
    path = write(tmp_path, HEADER, row(modal=7400), row(modal=7700))
    import_file(db_session, path)

    assert count(db_session) == 1
    assert db_session.scalar(select(MarketPrice.modal_price)) == 7700


def test_state_filter(db_session, tmp_path):
    path = write(
        tmp_path,
        HEADER,
        row(),
        row(state="Tamil Nadu", market="Pollachi", district="Coimbatore"),
    )
    result = import_file(db_session, path, state="kerala")

    assert result.rows_imported == 1
    assert result.skipped["other state"] == 1
    assert db_session.scalar(select(MarketPrice.state_name)) == "Kerala"


def test_comma_separated_file_with_other_headers_and_iso_dates(db_session, tmp_path):
    path = write(
        tmp_path,
        "date,state_name,district_name,market_name,commodity_name,variety,"
        "min_price,max_price,modal_price",
        "2025-10-30,Kerala,Palakkad,Koduvayoor,Coconut,Big,7200,7600,7400",
        name="prices.csv",
    )
    result = import_file(db_session, path)

    assert result.rows_imported == 1
    price = db_session.scalar(select(MarketPrice))
    assert price.price_date == date(2025, 10, 30)
    assert price.commodity == "Coconut"
    assert price.modal_price == 7400


def test_bad_rows_are_skipped_and_counted(db_session, tmp_path):
    path = write(
        tmp_path,
        HEADER,
        row(),
        row(day="not-a-date"),
        row(modal=""),
        row(modal=0),
        row(market=""),
        row(commodity=""),
    )
    result = import_file(db_session, path)

    assert result.rows_read == 6
    assert result.rows_imported == 1
    assert result.skipped["bad date"] == 1
    assert result.skipped["missing or invalid modal price"] == 2
    assert result.skipped["missing state, market or commodity"] == 2


def test_missing_min_max_default_to_modal_and_reversed_values_are_swapped(db_session, tmp_path):
    path = write(
        tmp_path,
        HEADER,
        row(market="A", pmin="", pmax="", modal=5000),
        row(market="B", pmin=6000, pmax=5000, modal=5500),
    )
    import_file(db_session, path)

    a = db_session.scalar(select(MarketPrice).where(MarketPrice.market_name == "A"))
    b = db_session.scalar(select(MarketPrice).where(MarketPrice.market_name == "B"))
    assert (a.min_price, a.max_price) == (5000, 5000)
    assert (b.min_price, b.max_price) == (5000, 6000)


def test_missing_columns_raise_a_clear_error(db_session, tmp_path):
    path = write(tmp_path, "a\tb", "1\t2")
    with pytest.raises(ValueError, match="Missing columns"):
        import_file(db_session, path)


def test_empty_file_raises(db_session, tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("")
    with pytest.raises(ValueError, match="empty"):
        import_file(db_session, path)