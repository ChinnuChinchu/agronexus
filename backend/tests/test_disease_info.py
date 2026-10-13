import json

import pytest

from app.services.disease_classifier import ML_DIR
from app.services.disease_info import DISEASE_INFO, get_info

LABELS = ML_DIR / "labels.json"


def test_every_entry_is_complete():
    for (crop, key), entry in DISEASE_INFO.items():
        assert entry.name and entry.summary, (crop, key)
        assert entry.actions and entry.prevention, (crop, key)
        if not entry.healthy:
            assert entry.symptoms, (crop, key)


def test_similar_references_point_to_real_conditions_in_the_same_crop():
    for (crop, key), entry in DISEASE_INFO.items():
        for other in entry.similar:
            assert (crop, other) in DISEASE_INFO, (crop, key, other)
            assert other != key


def test_each_crop_has_a_healthy_entry():
    crops = {crop for crop, _ in DISEASE_INFO}
    for crop in crops:
        assert DISEASE_INFO[(crop, "healthy")].healthy is True


def test_get_info():
    assert get_info("Tomato", "late_blight").urgent is True
    assert get_info("Tomato", "no_such_condition") is None


@pytest.mark.skipif(not LABELS.exists(), reason="labels.json is not installed")
def test_every_class_in_the_model_has_guidance():
    classes = json.loads(LABELS.read_text(encoding="utf-8"))["classes"]
    for item in classes:
        assert (item["crop"], item["key"]) in DISEASE_INFO, item["label"]