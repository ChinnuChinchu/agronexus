"""Agronomy tables: crop coefficients (Kc), paddy water guidance and fertilizer timing.

Kc values follow FAO Irrigation and Drainage Paper 56 where it publishes them.
Entries marked approximate are estimates. Fertilizer data is timing guidance only,
never doses.
"""

from dataclasses import dataclass
from typing import Literal


# ---------- crop water (Kc per growth stage) ----------
def _five(ini: float, mid: float, end: float) -> tuple[float, ...]:
    """Kc for the 5-stage seasonal crops (initial ... harvest-ready)."""
    return (ini, round((ini + mid) / 2, 2), mid, round((mid + end) / 2, 2), end)


def _four(ini: float, mid: float, end: float) -> tuple[float, ...]:
    """Kc for the 4-stage root and rhizome crops."""
    return (ini, round((ini + mid) / 2, 2), mid, end)


def _three(bearing: float) -> tuple[float, ...]:
    """Kc for perennials: establishment, juvenile growth, bearing."""
    return (round(bearing * 0.55, 2), round(bearing * 0.8, 2), bearing)


@dataclass(frozen=True)
class CropWater:
    kind: Literal["upland", "flooded"]
    kc: tuple[float, ...] = ()
    approximate: bool = False


CROP_WATER: dict[str, CropWater] = {
    "Rice (Paddy)": CropWater("flooded"),
    "Maize": CropWater("upland", _five(0.30, 1.20, 0.60)),
    "Tomato": CropWater("upland", _five(0.60, 1.15, 0.80)),
    "Brinjal (Eggplant)": CropWater("upland", _five(0.60, 1.05, 0.90)),
    "Okra (Lady's finger)": CropWater("upland", _five(0.50, 1.00, 0.70), approximate=True),
    "Chilli": CropWater("upland", _five(0.60, 1.05, 0.90)),
    "Cowpea": CropWater("upland", _five(0.50, 1.05, 0.60), approximate=True),
    "Groundnut": CropWater("upland", _five(0.40, 1.15, 0.60)),
    "Banana": CropWater("upland", _five(0.50, 1.10, 1.00)),
    "Sugarcane": CropWater("upland", _five(0.40, 1.25, 0.75)),
    "Ginger": CropWater("upland", _four(0.50, 1.00, 0.70), approximate=True),
    "Turmeric": CropWater("upland", _four(0.50, 1.00, 0.70), approximate=True),
    "Tapioca (Cassava)": CropWater("upland", _four(0.30, 0.80, 0.30)),
    "Coconut": CropWater("upland", _three(0.95), approximate=True),
    "Rubber": CropWater("upland", _three(1.00), approximate=True),
    "Arecanut": CropWater("upland", _three(1.00), approximate=True),
    "Black Pepper": CropWater("upland", _three(0.90), approximate=True),
    "Cardamom": CropWater("upland", _three(0.90), approximate=True),
    "Coffee": CropWater("upland", _three(1.00), approximate=True),
    "Cashew": CropWater("upland", _three(0.75), approximate=True),
    "Mango": CropWater("upland", _three(0.85), approximate=True),
}

# stage name -> (headline, detail), for flooded paddy
PADDY_GUIDANCE: dict[str, tuple[str, str]] = {
    "Seedling": (
        "Keep the soil saturated",
        "Maintain about 2-3 cm of standing water. Avoid deep flooding on young seedlings.",
    ),
    "Tillering": (
        "Maintain shallow standing water",
        "Keep about 5 cm of standing water and top up when it drops below 2-3 cm.",
    ),
    "Panicle / Flowering": (
        "Do not let the field dry out",
        "This is the most water-sensitive stage. Keep about 5 cm of standing water.",
    ),
    "Grain filling": (
        "Keep the soil moist",
        "Keep the soil moist and let the standing water recede gradually.",
    ),
    "Harvest-ready": (
        "Drain the field before harvest",
        "Drain the field about 7-10 days before harvest so the soil firms up for harvesting.",
    ),
}
PADDY_DEFAULT_GUIDANCE = (
    "Manage standing water",
    "Maintain shallow standing water and follow your local practice.",
)


# ---------- fertilizer timing ----------
@dataclass(frozen=True)
class FertStep:
    title: str
    nutrients: str
    note: str
    stage_index: int | None = None   # seasonal crops: the growth stage the step belongs to
    months: tuple[int, ...] = ()     # perennial crops: months of the year (1-12)


@dataclass(frozen=True)
class FertSchedule:
    steps: tuple[FertStep, ...]
    approximate: bool = False


def _perennial(
    first_text: str,
    second_text: str,
    first: tuple[int, ...] = (5, 6),
    second: tuple[int, ...] = (9, 10),
    approximate: bool = False,
) -> FertSchedule:
    young = "Young plants need a smaller dose, so check the dose for the plant's age."
    return FertSchedule(
        steps=(
            FertStep(
                "First split dose",
                "Organic manure plus NPK",
                f"Apply {first_text}. {young}",
                months=first,
            ),
            FertStep(
                "Second split dose",
                "Organic manure plus NPK",
                f"Apply {second_text}. {young}",
                months=second,
            ),
        ),
        approximate=approximate,
    )


_VEGETABLE = FertSchedule(
    (
        FertStep(
            "Basal dose",
            "Organic manure, phosphorus (P) and part of the nitrogen (N) and potassium (K)",
            "Apply at planting or transplanting and mix well into the soil.",
            stage_index=0,
        ),
        FertStep(
            "First top dressing",
            "Nitrogen (N) and potassium (K)",
            "Apply during vegetative growth and irrigate lightly afterwards.",
            stage_index=1,
        ),
        FertStep(
            "Second top dressing",
            "Nitrogen (N) and potassium (K)",
            "Apply at flowering or early fruit set. Avoid late nitrogen, which gives leaves "
            "instead of fruit.",
            stage_index=2,
        ),
    )
)

_RHIZOME = FertSchedule(
    (
        FertStep(
            "Basal dose",
            "Organic manure and phosphorus (P)",
            "Apply in the planting beds before planting.",
            stage_index=0,
        ),
        FertStep(
            "First top dressing",
            "Nitrogen (N) and potassium (K)",
            "Apply during early vegetative growth and earth up the beds.",
            stage_index=1,
        ),
        FertStep(
            "Second top dressing",
            "Nitrogen (N) and potassium (K)",
            "Apply as the rhizomes start to develop and earth up again.",
            stage_index=2,
        ),
    )
)

FERTILIZER: dict[str, FertSchedule] = {
    "Rice (Paddy)": FertSchedule(
        (
            FertStep(
                "Basal dose",
                "Phosphorus (P) and part of the nitrogen (N) and potassium (K)",
                "Apply at the final puddling or transplanting, along with organic manure.",
                stage_index=0,
            ),
            FertStep(
                "First top dressing",
                "Nitrogen (N)",
                "Apply at active tillering, with a thin film of water in the field.",
                stage_index=1,
            ),
            FertStep(
                "Second top dressing",
                "Nitrogen (N) and potassium (K)",
                "Apply at panicle initiation, before flowering.",
                stage_index=2,
            ),
        )
    ),
    "Maize": FertSchedule(
        (
            FertStep(
                "Basal dose",
                "Phosphorus (P), potassium (K) and part of the nitrogen (N)",
                "Apply at sowing, placed near the seed rows.",
                stage_index=0,
            ),
            FertStep(
                "First top dressing",
                "Nitrogen (N)",
                "Apply during rapid vegetative growth, around knee height.",
                stage_index=1,
            ),
            FertStep(
                "Second top dressing",
                "Nitrogen (N)",
                "Apply at tasseling and flowering.",
                stage_index=2,
            ),
        )
    ),
    "Tomato": _VEGETABLE,
    "Brinjal (Eggplant)": _VEGETABLE,
    "Okra (Lady's finger)": _VEGETABLE,
    "Chilli": _VEGETABLE,
    "Cowpea": FertSchedule(
        (
            FertStep(
                "Basal dose",
                "Organic manure, phosphorus (P) and potassium (K)",
                "Apply at sowing. Cowpea fixes its own nitrogen, so little or no nitrogen "
                "fertilizer is needed.",
                stage_index=0,
            ),
        )
    ),
    "Groundnut": FertSchedule(
        (
            FertStep(
                "Basal dose",
                "Organic manure, phosphorus (P) and potassium (K)",
                "Apply at sowing. Groundnut fixes its own nitrogen.",
                stage_index=0,
            ),
            FertStep(
                "Gypsum dose",
                "Calcium (gypsum)",
                "Apply at flowering and earth up. It helps pod filling.",
                stage_index=2,
            ),
        )
    ),
    "Banana": FertSchedule(
        (
            FertStep(
                "Basal dose",
                "Organic manure and phosphorus (P)",
                "Apply in the planting pit at planting.",
                stage_index=0,
            ),
            FertStep(
                "Vegetative top dressings",
                "Nitrogen (N) and potassium (K)",
                "Apply in several small split doses during vegetative growth. Banana is a "
                "heavy potassium feeder.",
                stage_index=1,
            ),
            FertStep(
                "Flowering dose",
                "Potassium (K)",
                "Apply a last dose around flowering. Stop fertilizer once the bunch has "
                "emerged.",
                stage_index=2,
            ),
        )
    ),
    "Sugarcane": FertSchedule(
        (
            FertStep(
                "Basal dose",
                "Organic manure, phosphorus (P) and potassium (K)",
                "Apply in the planting furrows.",
                stage_index=0,
            ),
            FertStep(
                "First top dressing",
                "Nitrogen (N)",
                "Apply during tillering.",
                stage_index=1,
            ),
            FertStep(
                "Second top dressing",
                "Nitrogen (N) and potassium (K)",
                "Apply at the start of the grand growth phase, with earthing up.",
                stage_index=2,
            ),
        )
    ),
    "Ginger": _RHIZOME,
    "Turmeric": _RHIZOME,
    "Tapioca (Cassava)": FertSchedule(
        (
            FertStep(
                "Basal dose",
                "Organic manure and phosphorus (P)",
                "Apply in the planting mounds or ridges.",
                stage_index=0,
            ),
            FertStep(
                "Top dressing",
                "Nitrogen (N) and potassium (K)",
                "Apply during early vegetative growth, with earthing up.",
                stage_index=1,
            ),
        )
    ),
    "Coconut": _perennial(
        "with the pre-monsoon showers (May-June)", "after the monsoon (September-October)"
    ),
    "Rubber": _perennial(
        "before the monsoon (April-May)",
        "after the monsoon (September-October)",
        first=(4, 5),
    ),
    "Arecanut": _perennial(
        "with the onset of the monsoon (May-June)", "after the monsoon (September-October)"
    ),
    "Black Pepper": _perennial(
        "at the onset of the monsoon (May-June)",
        "in the later monsoon (August-September)",
        second=(8, 9),
    ),
    "Cardamom": _perennial(
        "with the onset of the monsoon (May-June)",
        "after the monsoon (September-October)",
        approximate=True,
    ),
    "Coffee": _perennial(
        "with the onset of the monsoon (May-June)",
        "after the monsoon (September-October)",
        approximate=True,
    ),
    "Cashew": _perennial(
        "with the onset of the monsoon (May-June)",
        "after the monsoon (September-October)",
        approximate=True,
    ),
    "Mango": _perennial(
        "with the onset of the monsoon (May-June)",
        "after the monsoon (September-October)",
        approximate=True,
    ),
}