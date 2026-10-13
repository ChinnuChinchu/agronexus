import numpy as np

from app.services.disease_classifier import ClassInfo

LABELS = [
    (0, "Maize", "cercospora_leaf_spot_gray_leaf_spot", False),
    (1, "Maize", "common_rust", False),
    (2, "Maize", "northern_leaf_blight", False),
    (3, "Maize", "healthy", True),
    (4, "Tomato", "bacterial_spot", False),
    (5, "Tomato", "early_blight", False),
    (6, "Tomato", "late_blight", False),
    (7, "Tomato", "leaf_mold", False),
    (8, "Tomato", "septoria_leaf_spot", False),
    (9, "Tomato", "spider_mites_two_spotted_spider_mite", False),
    (10, "Tomato", "target_spot", False),
    (11, "Tomato", "tomato_yellow_leaf_curl_virus", False),
    (12, "Tomato", "tomato_mosaic_virus", False),
    (13, "Tomato", "healthy", True),
]
CLASSES = [
    ClassInfo(index, f"{crop}___{key}", crop, key, healthy)
    for index, crop, key, healthy in LABELS
]
INDEX = {(c.crop, c.key): c.index for c in CLASSES}


class FakeClassifier:
    """Returns fixed scores, so tests do not need the real model."""

    image_size = 224

    def __init__(self):
        self.classes = CLASSES
        self.scores: dict[tuple[str, str], float] = {}
        self.calls = 0
        self.last_shape = None

    def predict(self, batch):
        self.calls += 1
        self.last_shape = batch.shape
        probabilities = np.zeros(len(CLASSES), dtype=np.float32)
        for (crop, key), value in self.scores.items():
            probabilities[INDEX[(crop, key)]] = value
        return probabilities