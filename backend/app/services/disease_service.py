from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crop_type import CropType
from app.models.disease_scan import DiseaseScan
from app.models.user import User
from app.schemas.disease import Candidate, DiseaseGuide, PredictionResult, SimilarCondition
from app.services.disease_classifier import DiseaseClassifier
from app.services.disease_image import prepare_image
from app.services.disease_info import DISCLAIMER, PHOTO_TIPS, get_info
from app.services.disease_logic import Interpretation, Scored, interpret


# ---------- supported crops ----------
def _supported_names(classifier: DiseaseClassifier) -> set[str]:
    return {c.crop.lower() for c in classifier.classes}


def is_supported(classifier: DiseaseClassifier, crop_type: CropType) -> bool:
    return crop_type.name.lower() in _supported_names(classifier)


def list_supported_crop_types(db: Session, classifier: DiseaseClassifier) -> list[CropType]:
    names = _supported_names(classifier)
    crops = db.scalars(select(CropType).order_by(CropType.name))
    return [crop for crop in crops if crop.name.lower() in names]


# ---------- building the response ----------
def _candidate(scored: Scored) -> Candidate:
    entry = get_info(scored.info.crop, scored.info.key)
    name = entry.name if entry else scored.info.key.replace("_", " ").capitalize()
    return Candidate(
        key=scored.info.key,
        name=name,
        healthy=scored.info.healthy,
        confidence_pct=round(scored.probability * 100, 1),
    )


def _guide(scored: Scored) -> DiseaseGuide | None:
    entry = get_info(scored.info.crop, scored.info.key)
    if entry is None:
        return None

    similar = []
    for other in entry.similar:
        other_entry = get_info(scored.info.crop, other)
        if other_entry is not None:
            similar.append(SimilarCondition(key=other, name=other_entry.name))

    return DiseaseGuide(
        key=scored.info.key,
        name=entry.name,
        healthy=entry.healthy,
        urgent=entry.urgent,
        summary=entry.summary,
        symptoms=list(entry.symptoms),
        actions=list(entry.actions),
        prevention=list(entry.prevention),
        similar=similar,
    )


def describe(interpretation: Interpretation, crop: str) -> tuple[str, str]:
    """The headline and message for an outcome."""
    top = interpretation.top

    if interpretation.status == "crop_mismatch":
        return (
            f"This doesn't look like a {crop} leaf",
            "Check that you chose the right crop, or retake the photo of a single leaf. "
            "Only tomato and maize are supported so far.",
        )

    if interpretation.status == "uncertain" or top is None:
        return (
            "We're not sure",
            "The photo could not be matched to a condition with enough confidence. Try a clearer "
            "photo of a single leaf, or show it to an expert. The possibilities below are only "
            "guesses.",
        )

    strong = interpretation.level == "strong"
    name = _candidate(top).name
    if top.info.healthy:
        if strong:
            return (
                "Looks healthy",
                "No sign of disease was detected on this leaf. A single leaf photo cannot show "
                "every problem, so keep checking your plants.",
            )
        return (
            "Possibly healthy",
            "The leaf may be healthy, but the model is not certain. Check the other possibilities "
            "and try a clearer photo.",
        )

    if strong:
        return (
            f"Strong match: {name}",
            "The photo closely matches this condition. Compare the symptoms below with your "
            "plant, and confirm before treating.",
        )
    return (
        f"Possible match: {name}",
        "The model is not certain. Compare the symptoms below with your plant and look at the "
        "other possibilities.",
    )


def build_result(interpretation: Interpretation, crop: str, scan_id: int) -> PredictionResult:
    top = interpretation.top
    headline, message = describe(interpretation, crop)
    show_guide = interpretation.status == "ok" and top is not None

    return PredictionResult(
        scan_id=scan_id,
        crop=crop,
        status=interpretation.status,
        level=interpretation.level,
        headline=headline,
        message=message,
        top=_candidate(top) if top else None,
        alternatives=[_candidate(a) for a in interpretation.alternatives],
        guide=_guide(top) if show_guide else None,
        tips=list(PHOTO_TIPS) if interpretation.level != "strong" else [],
        disclaimer=DISCLAIMER,
    )


# ---------- analysing a photo ----------
def analyse_photo(
    db: Session,
    user: User,
    crop_type: CropType,
    image_bytes: bytes,
    classifier: DiseaseClassifier,
) -> PredictionResult:
    """Raises InvalidImage when the upload is not a usable photo."""
    array = prepare_image(image_bytes, getattr(classifier, "image_size", 224))
    probabilities = classifier.predict(array)
    interpretation = interpret(probabilities, classifier.classes, crop_type.name)

    top = interpretation.top
    scan = DiseaseScan(
        user_id=user.id,
        crop_name=crop_type.name,
        status=interpretation.status,
        level=interpretation.level,
        result_key=top.info.key if top else None,
        result_name=_candidate(top).name if top else None,
        confidence_pct=round(top.probability * 100, 1) if top else None,
        healthy=bool(top and top.info.healthy and interpretation.status == "ok"),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    return build_result(interpretation, crop_type.name, scan.id)


# ---------- history ----------
def list_scans(db: Session, user_id: int, limit: int = 20, offset: int = 0) -> list[DiseaseScan]:
    stmt = (
        select(DiseaseScan)
        .where(DiseaseScan.user_id == user_id)
        .order_by(DiseaseScan.created_at.desc(), DiseaseScan.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))


def get_scan(db: Session, user_id: int, scan_id: int) -> DiseaseScan | None:
    stmt = select(DiseaseScan).where(DiseaseScan.id == scan_id, DiseaseScan.user_id == user_id)
    return db.scalar(stmt)


def delete_scan(db: Session, scan: DiseaseScan) -> None:
    db.delete(scan)
    db.commit()