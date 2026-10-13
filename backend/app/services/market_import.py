"""Import mandi price rows from a CSV or TSV file into the market_prices table.

Run inside the backend container:
    python -m app.services.market_import data/kerala_prices.csv --state Kerala
"""

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.market_price import MarketPrice

# our field -> accepted column headers (lower case, spaces become underscores)
COLUMN_ALIASES = {
    "price_date": ("t", "date", "arrival_date", "price_date"),
    "state_name": ("state_name", "state"),
    "district_name": ("district_name", "district"),
    "market_name": ("market_name", "market"),
    "commodity": ("cmdty", "commodity_name", "commodity"),
    "variety": ("variety",),
    "min_price": ("p_min", "min_price"),
    "max_price": ("p_max", "max_price"),
    "modal_price": ("p_modal", "modal_price"),
}
REQUIRED = ("price_date", "state_name", "market_name", "commodity", "modal_price")
DATE_FORMATS = ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d")
BATCH_SIZE = 1000
UNIQUE_CONSTRAINT = "uq_market_prices_day_market_commodity_variety"


@dataclass
class ImportResult:
    rows_read: int = 0
    rows_imported: int = 0
    skipped: Counter = field(default_factory=Counter)
    first_date: date | None = None
    last_date: date | None = None
    commodities: Counter = field(default_factory=Counter)


def _normalise(header: str) -> str:
    return header.strip().lower().replace(" ", "_")


def _map_columns(fieldnames: list[str]) -> dict[str, str]:
    available = {_normalise(name): name for name in fieldnames if name}
    mapping: dict[str, str] = {}
    for field_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in available:
                mapping[field_name] = available[alias]
                break

    missing = [name for name in REQUIRED if name not in mapping]
    if missing:
        raise ValueError(
            f"Missing columns for: {', '.join(missing)}. "
            f"Headers found in the file: {', '.join(fieldnames)}"
        )
    return mapping


def _text(value: str | None, limit: int) -> str:
    return (value or "").strip()[:limit]


def _price(value: str | None) -> int | None:
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return round(number) if number > 0 else None


def _parse_date(value: str | None) -> date | None:
    text = (value or "").strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    return None


def _parse_row(row: dict, columns: dict[str, str]) -> tuple[dict | None, str | None]:
    """Returns (record, None) for a good row or (None, reason) for a skipped one."""

    def get(name: str) -> str | None:
        column = columns.get(name)
        return row.get(column) if column else None

    price_date = _parse_date(get("price_date"))
    if price_date is None:
        return None, "bad date"

    state = _text(get("state_name"), 100)
    market = _text(get("market_name"), 150)
    commodity = _text(get("commodity"), 100)
    if not (state and market and commodity):
        return None, "missing state, market or commodity"

    modal = _price(get("modal_price"))
    if modal is None:
        return None, "missing or invalid modal price"

    low = _price(get("min_price")) or modal
    high = _price(get("max_price")) or modal
    if low > high:
        low, high = high, low

    return (
        {
            "price_date": price_date,
            "state_name": state,
            "district_name": _text(get("district_name"), 100),
            "market_name": market,
            "commodity": commodity,
            "variety": _text(get("variety"), 100),
            "min_price": low,
            "max_price": high,
            "modal_price": modal,
        },
        None,
    )


def _flush(db: Session, batch: dict[tuple, dict]) -> int:
    if not batch:
        return 0
    statement = insert(MarketPrice).values(list(batch.values()))
    statement = statement.on_conflict_do_update(
        constraint=UNIQUE_CONSTRAINT,
        set_={
            "district_name": statement.excluded.district_name,
            "min_price": statement.excluded.min_price,
            "max_price": statement.excluded.max_price,
            "modal_price": statement.excluded.modal_price,
        },
    )
    db.execute(statement)
    db.commit()
    count = len(batch)
    batch.clear()
    return count


def import_file(db: Session, path: Path, state: str | None = None) -> ImportResult:
    result = ImportResult()
    batch: dict[tuple, dict] = {}
    wanted_state = state.strip().lower() if state else None

    with path.open(newline="", encoding="utf-8-sig") as handle:
        first_line = handle.readline()
        if not first_line.strip():
            raise ValueError("The file is empty")
        handle.seek(0)

        delimiter = "\t" if first_line.count("\t") > first_line.count(",") else ","
        reader = csv.DictReader(handle, delimiter=delimiter)
        columns = _map_columns(reader.fieldnames or [])

        for row in reader:
            result.rows_read += 1
            record, reason = _parse_row(row, columns)
            if record is None:
                result.skipped[reason] += 1
                continue
            if wanted_state and record["state_name"].lower() != wanted_state:
                result.skipped["other state"] += 1
                continue

            key = (
                record["price_date"],
                record["state_name"],
                record["market_name"],
                record["commodity"],
                record["variety"],
            )
            batch[key] = record  # the last row for the same key wins

            result.commodities[record["commodity"]] += 1
            if result.first_date is None or record["price_date"] < result.first_date:
                result.first_date = record["price_date"]
            if result.last_date is None or record["price_date"] > result.last_date:
                result.last_date = record["price_date"]

            if len(batch) >= BATCH_SIZE:
                result.rows_imported += _flush(db, batch)

    result.rows_imported += _flush(db, batch)
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Import mandi prices from a CSV or TSV file")
    parser.add_argument("path", help="path to the file, e.g. data/kerala_prices.csv")
    parser.add_argument("--state", help="only import this state, e.g. Kerala")
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.is_file():
        sys.exit(f"File not found: {path}")

    db = SessionLocal()
    try:
        result = import_file(db, path, args.state)
        total = db.scalar(select(func.count()).select_from(MarketPrice))
    except ValueError as exc:
        sys.exit(f"Import failed: {exc}")
    finally:
        db.close()

    print(f"Rows read:      {result.rows_read}")
    print(f"Rows imported:  {result.rows_imported}")
    if result.skipped:
        print("Rows skipped:")
        for reason, count in result.skipped.most_common():
            print(f"   {reason}: {count}")
    if result.first_date:
        print(f"Date range:     {result.first_date} to {result.last_date}")
    print(f"Rows in table:  {total}")
    print(f"\nCommodities in this import ({len(result.commodities)}):")
    for name, count in sorted(result.commodities.items()):
        print(f"   {name}: {count}")


if __name__ == "__main__":
    main()