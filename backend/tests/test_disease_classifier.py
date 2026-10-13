import json

import numpy as np
import pytest

from app.services import disease_classifier as dc
from app.services.disease_classifier import ClassifierUnavailable, load_classes

MODEL = dc.ML_DIR / dc.MODEL_FILE
LABELS = dc.ML_DIR / dc.LABELS_FILE


@pytest.fixture(autouse=True)
def fresh_classifier():
    dc.reset_classifier()
    yield
    dc.reset_classifier()


def test_load_classes_reads_the_labels_file(tmp_path):
    path = tmp_path / "labels.json"
    path.write_text(
        json.dumps(
            {
                "image_size": 224,
                "classes": [
                    {"index": 0, "label": "A___x", "crop": "A", "key": "x", "healthy": False},
                    {"index": 1, "label": "A___healthy", "crop": "A", "key": "healthy", "healthy": True},
                ],
            }
        )
    )
    size, classes = load_classes(path)

    assert size == 224
    assert [(c.index, c.crop, c.key, c.healthy) for c in classes] == [
        (0, "A", "x", False),
        (1, "A", "healthy", True),
    ]


@pytest.mark.parametrize(
    "content",
    [
        None,
        "{not json",
        '{"image_size": 224}',
        json.dumps(
            {
                "image_size": 224,
                "classes": [{"index": 5, "label": "a", "crop": "A", "key": "x", "healthy": False}],
            }
        ),
    ],
    ids=["missing file", "invalid json", "missing classes", "bad indices"],
)
def test_bad_labels_files_are_rejected(tmp_path, content):
    path = tmp_path / "labels.json"
    if content is not None:
        path.write_text(content)
    with pytest.raises(ClassifierUnavailable):
        load_classes(path)


def test_classifier_is_unavailable_without_the_model_files(monkeypatch, tmp_path):
    monkeypatch.setattr(dc, "ML_DIR", tmp_path)
    with pytest.raises(ClassifierUnavailable, match="not installed"):
        dc.get_classifier()


@pytest.mark.skipif(
    not (MODEL.exists() and LABELS.exists()), reason="the disease model is not installed"
)
def test_real_model_returns_probabilities():
    pytest.importorskip("ai_edge_litert")
    classifier = dc.get_classifier()

    probabilities = classifier.predict(np.full((1, 224, 224, 3), 120, dtype=np.float32))

    assert probabilities.shape == (len(classifier.classes),)
    assert np.all(probabilities >= 0)
    assert abs(float(probabilities.sum()) - 1.0) < 1e-3
    assert {c.crop for c in classifier.classes} == {"Maize", "Tomato"}