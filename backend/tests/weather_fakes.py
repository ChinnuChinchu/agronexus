from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(seconds=19800))


def ts(day: date, hour: int, minute: int = 0) -> int:
    """Epoch seconds for a given IST date and time."""
    return int(datetime(day.year, day.month, day.day, hour, minute, tzinfo=IST).timestamp())


def raw_slot(
    epoch: int,
    temp: float = 30.0,
    pop: float | None = 0.0,
    rain: float | None = None,
    wind: float = 2.0,
    cid: int = 800,
    humidity: int = 60,
    desc: str = "clear sky",
) -> dict:
    item = {
        "dt": epoch,
        "main": {"temp": temp, "humidity": humidity},
        "wind": {"speed": wind},
        "weather": [{"id": cid, "description": desc}],
    }
    if pop is not None:
        item["pop"] = pop
    if rain is not None:
        item["rain"] = {"3h": rain}
    return item


def raw_forecast(slots: list[dict]) -> dict:
    return {"city": {"timezone": 19800}, "list": slots}


def raw_current(base: date, temp: float = 30.0) -> dict:
    return {
        "dt": ts(base, 11, 30),
        "timezone": 19800,
        "main": {"temp": temp, "feels_like": temp + 2, "humidity": 55},
        "wind": {"speed": 3.0},
        "weather": [{"id": 802, "description": "scattered clouds"}],
    }


def default_forecast(base: date, wet_day_offset: int | None = 1) -> dict:
    """40 slots from base 14:30 IST. The wet day gets 8 x 2.2 = 17.6 mm of rain."""
    slots = []
    for i in range(40):
        epoch = ts(base, 14, 30) + i * 10800
        offset = (datetime.fromtimestamp(epoch, IST).date() - base).days
        if wet_day_offset is not None and offset == wet_day_offset:
            slots.append(raw_slot(epoch, pop=1.0, rain=2.2, cid=501, desc="moderate rain"))
        else:
            slots.append(raw_slot(epoch))
    return raw_forecast(slots)