from app.db.seed import CATALOG
from app.services.market_mapping import CROP_COMMODITY_ALIASES, match_names, normalise_name


def test_normalise_name():
    assert normalise_name("Paddy (Dhan) (Common)") == "paddydhancommon"
    assert normalise_name("Paddy (Dhan) (Common)") == normalise_name("paddy(dhan)(common)")


def test_every_catalog_crop_has_an_alias_entry():
    assert set(CROP_COMMODITY_ALIASES) == {item["name"] for item in CATALOG}


def test_match_names_ignores_spacing_and_case():
    available = ["Paddy (Dhan) (Common)", "Rice", "Coconut", "Tender Coconut"]
    assert match_names("Rice (Paddy)", available) == ["Paddy (Dhan) (Common)"]
    assert match_names("Coconut", available) == ["Coconut"]


def test_match_names_unknown_crop_or_no_data():
    assert match_names("Dragon Fruit", ["Coconut"]) == []
    assert match_names("Coconut", ["Rice"]) == []