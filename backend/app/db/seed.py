from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.crop_type import CropType

# ---- seasonal stage templates (percent of the crop cycle) ----
GENERAL_STAGES = [
    {"name": "Germination", "start_pct": 0, "end_pct": 10},
    {"name": "Vegetative growth", "start_pct": 10, "end_pct": 45},
    {"name": "Flowering", "start_pct": 45, "end_pct": 65},
    {"name": "Fruiting / Grain filling", "start_pct": 65, "end_pct": 90},
    {"name": "Harvest-ready", "start_pct": 90, "end_pct": 100},
]

CEREAL_STAGES = [
    {"name": "Seedling", "start_pct": 0, "end_pct": 15},
    {"name": "Tillering", "start_pct": 15, "end_pct": 45},
    {"name": "Panicle / Flowering", "start_pct": 45, "end_pct": 65},
    {"name": "Grain filling", "start_pct": 65, "end_pct": 90},
    {"name": "Harvest-ready", "start_pct": 90, "end_pct": 100},
]

TUBER_STAGES = [
    {"name": "Sprouting", "start_pct": 0, "end_pct": 10},
    {"name": "Vegetative growth", "start_pct": 10, "end_pct": 50},
    {"name": "Rhizome / Tuber development", "start_pct": 50, "end_pct": 90},
    {"name": "Harvest-ready", "start_pct": 90, "end_pct": 100},
]


def seasonal(name: str, category: str, days: int, stages: list[dict]) -> dict:
    return {
        "name": name,
        "category": category,
        "cycle": "seasonal",
        "duration_days": days,
        "bearing_age_months": None,
        "stages": stages,
    }


def perennial(name: str, category: str, bearing_months: int) -> dict:
    return {
        "name": name,
        "category": category,
        "cycle": "perennial",
        "duration_days": None,
        "bearing_age_months": bearing_months,
        "stages": [
            {"name": "Establishment", "start_month": 0, "end_month": 12},
            {"name": "Juvenile growth", "start_month": 12, "end_month": bearing_months},
            {"name": "Bearing", "start_month": bearing_months, "end_month": None},
        ],
    }


CATALOG = [
    # seasonal (durations are approximate defaults)
    seasonal("Rice (Paddy)", "Cereal", 120, CEREAL_STAGES),
    seasonal("Maize", "Cereal", 105, CEREAL_STAGES),
    seasonal("Tomato", "Vegetable", 110, GENERAL_STAGES),
    seasonal("Brinjal (Eggplant)", "Vegetable", 120, GENERAL_STAGES),
    seasonal("Okra (Lady's finger)", "Vegetable", 90, GENERAL_STAGES),
    seasonal("Chilli", "Vegetable", 150, GENERAL_STAGES),
    seasonal("Cowpea", "Pulse", 90, GENERAL_STAGES),
    seasonal("Groundnut", "Oilseed", 110, GENERAL_STAGES),
    seasonal("Banana", "Fruit", 330, GENERAL_STAGES),
    seasonal("Sugarcane", "Cash crop", 330, GENERAL_STAGES),
    seasonal("Ginger", "Spice", 240, TUBER_STAGES),
    seasonal("Turmeric", "Spice", 270, TUBER_STAGES),
    seasonal("Tapioca (Cassava)", "Tuber", 300, TUBER_STAGES),
    # perennial (bearing age in months is approximate)
    perennial("Coconut", "Plantation", 72),
    perennial("Rubber", "Plantation", 84),
    perennial("Arecanut", "Plantation", 60),
    perennial("Black Pepper", "Spice", 36),
    perennial("Cardamom", "Spice", 30),
    perennial("Coffee", "Plantation", 36),
    perennial("Cashew", "Plantation", 36),
    perennial("Mango", "Fruit", 60),
]


def seed_crop_types() -> int:
    db = SessionLocal()
    try:
        for item in CATALOG:
            existing = db.scalar(select(CropType).where(CropType.name == item["name"]))
            if existing:
                for key, value in item.items():
                    setattr(existing, key, value)
            else:
                db.add(CropType(**item))
        db.commit()
        return len(CATALOG)
    finally:
        db.close()


if __name__ == "__main__":
    print(f"Seeded {seed_crop_types()} crop types")