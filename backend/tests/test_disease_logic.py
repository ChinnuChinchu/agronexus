import pytest

from app.services.disease_classifier import ClassInfo
from app.services.disease_logic import interpret

CLASSES = [
    ClassInfo(0, "Corn___common_rust", "Maize", "common_rust", False),
    ClassInfo(1, "Corn___healthy", "Maize", "healthy", True),
    ClassInfo(2, "Tomato___early_blight", "Tomato", "early_blight", False),
    ClassInfo(3, "Tomato___late_blight", "Tomato", "late_blight", False),
    ClassInfo(4, "Tomato___healthy", "Tomato", "healthy", True),
]


def p(common_rust=0.0, maize_healthy=0.0, early=0.0, late=0.0, tomato_healthy=0.0):
    return [common_rust, maize_healthy, early, late, tomato_healthy]


def test_strong_match():
    result = interpret(p(early=0.02, late=0.96, tomato_healthy=0.02), CLASSES, "Tomato")

    assert result.status == "ok"
    assert result.level == "strong"
    assert result.top.info.key == "late_blight"
    assert result.top.probability == 0.96
    assert [a.info.key for a in result.alternatives] == ["early_blight", "healthy"]


def test_possible_match():
    result = interpret(p(early=0.06, late=0.88, tomato_healthy=0.06), CLASSES, "Tomato")
    assert (result.status, result.level) == ("ok", "possible")


def test_uncertain_still_lists_candidates():
    result = interpret(p(early=0.2, late=0.5, tomato_healthy=0.2, common_rust=0.1), CLASSES, "Tomato")

    assert (result.status, result.level) == ("uncertain", "uncertain")
    assert result.top.info.key == "late_blight"
    assert len(result.alternatives) == 2


@pytest.mark.parametrize(
    "top, level", [(0.95, "strong"), (0.80, "possible"), (0.79, "uncertain")]
)
def test_threshold_boundaries(top, level):
    result = interpret(p(late=top, early=1 - top), CLASSES, "Tomato")
    assert result.level == level


def test_crop_mismatch():
    result = interpret(p(common_rust=0.9, late=0.05, tomato_healthy=0.05), CLASSES, "Tomato")

    assert result.status == "crop_mismatch"
    assert result.level == "uncertain"
    assert result.top is None
    assert result.alternatives == []


def test_crop_mismatch_boundary():
    at_limit = interpret(p(common_rust=0.5, late=0.5), CLASSES, "Tomato")
    below_limit = interpret(p(common_rust=0.51, late=0.49), CLASSES, "Tomato")

    assert at_limit.status == "uncertain"
    assert below_limit.status == "crop_mismatch"


def test_only_the_chosen_crops_classes_are_listed():
    result = interpret(p(common_rust=0.97, maize_healthy=0.01, late=0.02), CLASSES, "Maize")

    assert result.top.info.key == "common_rust"
    assert [a.info.crop for a in result.alternatives] == ["Maize"]


def test_healthy_result():
    result = interpret(p(late=0.01, early=0.01, tomato_healthy=0.97, common_rust=0.01), CLASSES, "Tomato")
    assert result.top.info.healthy is True
    assert result.level == "strong"


def test_unknown_crop_raises():
    with pytest.raises(ValueError):
        interpret(p(late=1.0), CLASSES, "Banana")


def test_crop_name_is_case_insensitive():
    result = interpret(p(late=0.97, early=0.03), CLASSES, " tomato ")
    assert result.top.info.key == "late_blight"


def test_confidence_is_the_raw_score_not_renormalised():
    # the model puts only 0.90 of its score on tomato, so 0.85 is not "0.94 within tomato"
    result = interpret(p(common_rust=0.1, late=0.85, early=0.05), CLASSES, "Tomato")

    assert result.top.probability == 0.85
    assert result.level == "possible"