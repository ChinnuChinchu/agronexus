from app.db.seed import CATALOG
from app.services.agronomy_data import CROP_WATER, FERTILIZER, PADDY_GUIDANCE


def test_every_catalog_crop_has_water_and_fertilizer_entries():
    names = {item["name"] for item in CATALOG}
    assert set(CROP_WATER) == names
    assert set(FERTILIZER) == names


def test_crop_coefficients_match_the_stage_count():
    for item in CATALOG:
        info = CROP_WATER[item["name"]]
        if info.kind == "upland":
            assert len(info.kc) == len(item["stages"]), item["name"]


def test_crop_coefficients_are_sensible():
    for name, info in CROP_WATER.items():
        for kc in info.kc:
            assert 0.2 <= kc <= 1.35, name


def test_fertilizer_steps_match_the_crop_cycle():
    for item in CATALOG:
        schedule = FERTILIZER[item["name"]]
        assert schedule.steps, item["name"]
        if item["cycle"] == "seasonal":
            indexes = [s.stage_index for s in schedule.steps]
            assert all(i is not None and 0 <= i < len(item["stages"]) for i in indexes), item[
                "name"
            ]
            assert indexes == sorted(set(indexes)), item["name"]
            assert all(not s.months for s in schedule.steps), item["name"]
        else:
            for step in schedule.steps:
                assert step.stage_index is None, item["name"]
                assert step.months and all(1 <= m <= 12 for m in step.months), item["name"]


def test_only_paddy_is_flooded_and_has_guidance_for_every_stage():
    flooded = {name for name, info in CROP_WATER.items() if info.kind == "flooded"}
    assert flooded == {"Rice (Paddy)"}

    paddy = next(item for item in CATALOG if item["name"] == "Rice (Paddy)")
    for stage in paddy["stages"]:
        assert stage["name"] in PADDY_GUIDANCE