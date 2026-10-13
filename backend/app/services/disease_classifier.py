"""Loads the TensorFlow Lite disease model and runs it on a prepared image."""

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

ML_DIR = Path(__file__).resolve().parents[2] / "ml"
MODEL_FILE = "disease_model.tflite"
LABELS_FILE = "labels.json"


class ClassifierUnavailable(Exception):
    """The model or its labels could not be loaded. The message is safe to show."""


@dataclass(frozen=True)
class ClassInfo:
    index: int
    label: str
    crop: str
    key: str
    healthy: bool


class DiseaseClassifier(Protocol):
    classes: list[ClassInfo]

    def predict(self, batch: np.ndarray) -> np.ndarray:
        """Probabilities for every class, for one image of shape (1, size, size, 3)."""
        ...


def load_classes(path: Path) -> tuple[int, list[ClassInfo]]:
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
        image_size = int(meta["image_size"])
        classes = [
            ClassInfo(
                index=int(item["index"]),
                label=str(item["label"]),
                crop=str(item["crop"]),
                key=str(item["key"]),
                healthy=bool(item["healthy"]),
            )
            for item in meta["classes"]
        ]
    except (OSError, ValueError, KeyError, TypeError):
        raise ClassifierUnavailable("The disease labels file could not be read") from None

    if not classes or [c.index for c in classes] != list(range(len(classes))):
        raise ClassifierUnavailable("The disease labels file is not valid")
    return image_size, classes


class LiteRTClassifier:
    def __init__(self, model_path: Path, labels_path: Path) -> None:
        self.image_size, self.classes = load_classes(labels_path)

        try:
            from ai_edge_litert.interpreter import Interpreter
        except ImportError:
            raise ClassifierUnavailable("The disease detection runtime is not installed") from None

        try:
            self._interpreter = Interpreter(model_path=str(model_path))
            self._interpreter.allocate_tensors()
        except (ValueError, RuntimeError, OSError):
            raise ClassifierUnavailable("The disease model could not be loaded") from None

        model_input = self._interpreter.get_input_details()[0]
        model_output = self._interpreter.get_output_details()[0]
        expected_shape = [1, self.image_size, self.image_size, 3]
        if list(model_input["shape"]) != expected_shape or int(model_output["shape"][-1]) != len(
            self.classes
        ):
            raise ClassifierUnavailable("The disease model does not match its labels file")

        self._input_index = model_input["index"]
        self._output_index = model_output["index"]
        self._lock = threading.Lock()  # the interpreter is not thread-safe

    def predict(self, batch: np.ndarray) -> np.ndarray:
        with self._lock:
            self._interpreter.set_tensor(self._input_index, batch.astype(np.float32, copy=False))
            self._interpreter.invoke()
            return np.array(self._interpreter.get_tensor(self._output_index)[0], dtype=np.float32)


_classifier: DiseaseClassifier | None = None
_lock = threading.Lock()


def get_classifier() -> DiseaseClassifier:
    """The shared classifier, loaded on first use."""
    global _classifier
    if _classifier is not None:
        return _classifier

    with _lock:
        if _classifier is None:
            model_path = ML_DIR / MODEL_FILE
            labels_path = ML_DIR / LABELS_FILE
            if not model_path.is_file() or not labels_path.is_file():
                raise ClassifierUnavailable("The disease detection model is not installed")
            _classifier = LiteRTClassifier(model_path, labels_path)
    return _classifier


def reset_classifier() -> None:
    """Forget the loaded classifier (used by tests)."""
    global _classifier
    with _lock:
        _classifier = None