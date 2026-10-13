from collections.abc import Sequence
from dataclasses import dataclass

from app.services.disease_classifier import ClassInfo

# Thresholds chosen from the model's confidence tables (see the training notebook).
STRONG_THRESHOLD = 0.95
POSSIBLE_THRESHOLD = 0.80
CROP_MISMATCH_MASS = 0.50   # below this, the photo does not look like the chosen crop
MAX_ALTERNATIVES = 2


@dataclass(frozen=True)
class Scored:
    info: ClassInfo
    probability: float


@dataclass(frozen=True)
class Interpretation:
    status: str      # "ok", "uncertain" or "crop_mismatch"
    level: str       # "strong", "possible" or "uncertain"
    crop_mass: float
    top: Scored | None
    alternatives: list[Scored]


def interpret(probabilities: Sequence[float], classes: Sequence[ClassInfo], crop: str) -> Interpretation:
    """Reads the model's output for the crop the farmer chose.

    Only that crop's classes are listed, but the confidence is the model's raw score,
    so a photo the model finds confusing never looks confident.
    """
    wanted = crop.strip().lower()
    scored = sorted(
        (Scored(c, float(probabilities[c.index])) for c in classes if c.crop.lower() == wanted),
        key=lambda s: s.probability,
        reverse=True,
    )
    if not scored:
        raise ValueError(f"The model has no classes for '{crop}'")

    crop_mass = sum(s.probability for s in scored)
    if crop_mass < CROP_MISMATCH_MASS:
        return Interpretation("crop_mismatch", "uncertain", crop_mass, None, [])

    top = scored[0]
    if top.probability >= STRONG_THRESHOLD:
        status, level = "ok", "strong"
    elif top.probability >= POSSIBLE_THRESHOLD:
        status, level = "ok", "possible"
    else:
        status, level = "uncertain", "uncertain"

    return Interpretation(status, level, crop_mass, top, scored[1 : 1 + MAX_ALTERNATIVES])