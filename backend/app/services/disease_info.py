"""General guidance for each condition the model knows.

Plain advice only: no product names and no doses. Check it against the KAU Package of
Practices and local advice before relying on it.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DiseaseEntry:
    name: str
    summary: str
    symptoms: tuple[str, ...]
    actions: tuple[str, ...]
    prevention: tuple[str, ...]
    similar: tuple[str, ...] = ()   # keys of conditions in the same crop it is often confused with
    healthy: bool = False
    urgent: bool = False


DISCLAIMER = (
    "This is an automated suggestion based on the photo, not a diagnosis. Please confirm with "
    "your Krishi Bhavan or the KAU plant clinic before treating your crop."
)

PHOTO_TIPS = (
    "Photograph a single leaf and fill most of the frame with it.",
    "Use daylight, avoid heavy shadow, and keep the camera steady and in focus.",
    "Show the spots or damage clearly, and try a second photo of a different affected leaf.",
)

DISEASE_INFO: dict[tuple[str, str], DiseaseEntry] = {
    # ---------------- Tomato ----------------
    ("Tomato", "bacterial_spot"): DiseaseEntry(
        name="Bacterial spot",
        summary=(
            "A bacterial disease that thrives in warm, wet weather and spreads by rain splash "
            "and by handling wet plants."
        ),
        symptoms=(
            "Small, dark, water-soaked spots on leaves that turn brown or black, often with a "
            "yellow halo",
            "Spots can join up and make leaves look ragged",
            "Raised, scabby spots on green fruit",
        ),
        actions=(
            "Remove and destroy badly affected leaves or plants",
            "Avoid working among wet plants, and water at the base instead of overhead",
            "Ask your Krishi Bhavan which approved treatment suits your area",
        ),
        prevention=(
            "Use disease-free seed and healthy seedlings",
            "Rotate away from tomato and other solanaceous crops for 2 to 3 years",
            "Clean tools and keep plants spaced for good airflow",
        ),
        similar=("tomato_yellow_leaf_curl_virus",),
    ),
    ("Tomato", "early_blight"): DiseaseEntry(
        name="Early blight",
        summary="A fungal disease (Alternaria) that usually starts on the older, lower leaves.",
        symptoms=(
            "Brown spots with concentric rings, like a target",
            "Yellowing around the spots, and older leaves may drop",
            "Dark, sunken lesions on stems and at the stem end of fruit",
        ),
        actions=(
            "Remove infected lower leaves and destroy them",
            "Mulch the soil to stop spores splashing up, and avoid wetting the leaves",
            "Ask your Krishi Bhavan whether a fungicide is needed",
        ),
        prevention=(
            "Rotate crops and clear plant debris after harvest",
            "Stake plants so leaves stay off the soil",
            "Keep plants well fed and watered, because stressed plants are affected more",
        ),
        similar=("target_spot", "septoria_leaf_spot"),
    ),
    ("Tomato", "late_blight"): DiseaseEntry(
        name="Late blight",
        summary=(
            "A fast-spreading disease (Phytophthora) favoured by cool, wet, humid weather. It can "
            "destroy a crop within days."
        ),
        symptoms=(
            "Large, irregular, greasy-looking patches that turn brown to black",
            "White fuzzy growth under the leaf in humid weather",
            "Firm, brown, greasy-looking patches on fruit",
        ),
        actions=(
            "Act quickly: remove and destroy infected plants, and do not compost them",
            "Avoid wetting the leaves, and avoid working in the field when plants are wet",
            "Contact your Krishi Bhavan promptly, because spread can be very fast",
        ),
        prevention=(
            "Plant healthy seedlings in well-drained soil with good airflow",
            "Do not plant near potato crops or leftover infected plants",
            "Watch the crop closely during cool, rainy spells",
        ),
        urgent=True,
    ),
    ("Tomato", "leaf_mold"): DiseaseEntry(
        name="Leaf mold",
        summary="A fungal disease of humid conditions, common in dense or poorly ventilated crops.",
        symptoms=(
            "Pale green or yellow patches on the upper leaf surface",
            "Olive-green to brown velvety mold on the underside of the same leaf",
            "Leaves curl, wither and dry out",
        ),
        actions=(
            "Improve ventilation and reduce humidity around the plants",
            "Remove affected leaves and avoid wetting the foliage",
            "Ask your Krishi Bhavan if treatment is needed",
        ),
        prevention=(
            "Give plants wider spacing, and prune and stake them for airflow",
            "Water in the morning, at the base of the plant",
            "Clear crop residue after harvest",
        ),
        similar=("target_spot",),
    ),
    ("Tomato", "septoria_leaf_spot"): DiseaseEntry(
        name="Septoria leaf spot",
        summary=(
            "A fungal disease that starts on the lower leaves and moves upward, especially in "
            "warm, wet weather."
        ),
        symptoms=(
            "Many small, round spots with dark edges and grey or tan centres",
            "Tiny black specks in the middle of the spots",
            "Badly affected leaves turn yellow and drop",
        ),
        actions=(
            "Remove infected lower leaves",
            "Mulch the soil and avoid overhead watering",
            "Clear plant debris, and ask your Krishi Bhavan about treatment if it keeps spreading",
        ),
        prevention=(
            "Rotate away from tomato for 2 to 3 years",
            "Stake plants and keep them spaced for airflow",
            "Avoid working among wet plants",
        ),
        similar=("target_spot", "early_blight"),
    ),
    ("Tomato", "spider_mites_two_spotted_spider_mite"): DiseaseEntry(
        name="Spider mites (two-spotted spider mite)",
        summary=(
            "Tiny pests that suck sap from the underside of leaves. They multiply fastest in hot, "
            "dry, dusty weather."
        ),
        symptoms=(
            "Fine yellow speckling on the leaves",
            "Fine webbing on the underside of leaves and at the growing tips",
            "Leaves turn bronze, dry out and drop in bad infestations",
        ),
        actions=(
            "Check the underside of leaves with a hand lens to confirm the mites",
            "Wash plants with a strong stream of water and remove heavily infested leaves",
            "Avoid dust and drought stress, and ask your Krishi Bhavan before using any miticide "
            "so that natural enemies are not harmed",
        ),
        prevention=(
            "Keep plants well watered in dry spells",
            "Check the underside of leaves every week",
            "Control weeds around the field, which can host mites",
        ),
        similar=("target_spot", "tomato_yellow_leaf_curl_virus"),
    ),
    ("Tomato", "target_spot"): DiseaseEntry(
        name="Target spot",
        summary=(
            "A fungal disease (Corynespora) that produces ringed spots and looks very similar to "
            "early blight and other leaf spots."
        ),
        symptoms=(
            "Brown spots with concentric rings, sometimes with a yellow halo",
            "Spots can appear on leaves, stems and fruit",
            "Heavily affected leaves turn yellow and drop",
        ),
        actions=(
            "Remove infected leaves and improve airflow around the plants",
            "Avoid overhead watering",
            "Confirm the diagnosis with your Krishi Bhavan, because it is easily confused with "
            "early blight and other leaf spots",
        ),
        prevention=(
            "Rotate crops and remove plant debris after harvest",
            "Avoid a dense canopy by pruning and staking",
            "Use clean planting material",
        ),
        similar=(
            "early_blight",
            "septoria_leaf_spot",
            "leaf_mold",
            "spider_mites_two_spotted_spider_mite",
        ),
    ),
    ("Tomato", "tomato_yellow_leaf_curl_virus"): DiseaseEntry(
        name="Tomato yellow leaf curl virus",
        summary="A virus spread by whiteflies. There is no cure for infected plants.",
        symptoms=(
            "Leaves curl upward and turn yellow, especially along the edges",
            "Leaves are small and crumpled, and plants are stunted",
            "Flowers drop and few fruit set",
        ),
        actions=(
            "Remove and destroy infected plants early so that whiteflies do not spread the virus",
            "Control whiteflies, for example with yellow sticky traps and by removing weeds, and "
            "ask your Krishi Bhavan about approved options",
            "Do not plant new seedlings next to infected plants",
        ),
        prevention=(
            "Use virus-free seedlings, ideally raised under insect-proof net",
            "Choose resistant or tolerant varieties where available",
            "Check the undersides of leaves for whiteflies every week",
        ),
        similar=("bacterial_spot", "spider_mites_two_spotted_spider_mite"),
    ),
    ("Tomato", "tomato_mosaic_virus"): DiseaseEntry(
        name="Tomato mosaic virus",
        summary="A virus that spreads by touch, contaminated tools and seed. There is no cure.",
        symptoms=(
            "Mottled light and dark green patches on leaves",
            "Leaves distorted, narrow or fern-like, and plants stunted",
            "Fruit that ripens unevenly",
        ),
        actions=(
            "Remove and destroy infected plants",
            "Wash your hands and disinfect tools after handling infected plants",
            "Avoid handling tobacco before touching the plants, because tobacco can carry "
            "related viruses",
        ),
        prevention=(
            "Use certified, disease-free seed",
            "Choose resistant varieties where available",
            "Keep tools and hands clean, and rotate crops",
        ),
    ),
    ("Tomato", "healthy"): DiseaseEntry(
        name="Healthy",
        summary="No sign of disease was detected on this leaf.",
        symptoms=(),
        actions=(
            "Keep scouting regularly, because one leaf photo cannot show problems on the stem, "
            "fruit or roots",
            "Continue balanced feeding and watering",
        ),
        prevention=("Water at the base, keep good spacing, and remove old or fallen leaves",),
        healthy=True,
    ),
    # ---------------- Maize ----------------
    ("Maize", "cercospora_leaf_spot_gray_leaf_spot"): DiseaseEntry(
        name="Gray leaf spot (Cercospora)",
        summary=(
            "A fungal disease favoured by warm, humid weather and dense crops. It spreads from the "
            "lower leaves upward."
        ),
        symptoms=(
            "Long, narrow, rectangular tan to gray lesions that run parallel to the leaf veins",
            "Lesions join up, and large areas of leaf die in severe cases",
        ),
        actions=(
            "Check how far up the plant the lesions have spread, especially before flowering",
            "Ask your Krishi Bhavan about treatment if the upper leaves are affected",
            "Remove or bury infected crop residue after harvest",
        ),
        prevention=(
            "Rotate maize with a non-cereal crop",
            "Choose tolerant hybrids and avoid overcrowding the crop",
            "Manage crop residue",
        ),
        similar=("northern_leaf_blight",),
    ),
    ("Maize", "common_rust"): DiseaseEntry(
        name="Common rust",
        summary=(
            "A fungal disease that spreads on the wind and is favoured by cool, moist weather. It "
            "is often minor unless it starts early and is severe."
        ),
        symptoms=(
            "Small, round to elongated, reddish-brown raised pustules on both sides of the leaf",
            "Rubbing a pustule leaves rust-coloured powder on your finger",
        ),
        actions=(
            "Keep watching how quickly it spreads, especially before tasselling",
            "Ask your Krishi Bhavan about treatment if infection is heavy on young plants",
        ),
        prevention=(
            "Choose resistant hybrids",
            "Plant at the recommended time so young plants avoid long cool, wet spells",
        ),
    ),
    ("Maize", "northern_leaf_blight"): DiseaseEntry(
        name="Northern leaf blight",
        summary=(
            "A fungal disease favoured by moderate temperatures and humid weather, starting on the "
            "lower leaves."
        ),
        symptoms=(
            "Long, cigar-shaped, grey-green to tan lesions on the leaves",
            "Lesions can grow several centimetres long and join up, killing large areas of leaf",
        ),
        actions=(
            "Check how far up the plant the lesions have spread",
            "Ask your Krishi Bhavan about treatment if the upper leaves are affected around "
            "flowering",
            "Remove or bury infected crop residue after harvest",
        ),
        prevention=(
            "Choose resistant hybrids",
            "Rotate crops and manage crop residue",
            "Avoid overcrowding the crop",
        ),
        similar=("cercospora_leaf_spot_gray_leaf_spot",),
    ),
    ("Maize", "healthy"): DiseaseEntry(
        name="Healthy",
        summary="No sign of disease was detected on this leaf.",
        symptoms=(),
        actions=(
            "Keep scouting regularly, because one leaf photo cannot show every problem",
            "Continue balanced feeding and watering",
        ),
        prevention=("Rotate crops and manage crop residue after harvest",),
        healthy=True,
    ),
}


def get_info(crop: str, key: str) -> DiseaseEntry | None:
    return DISEASE_INFO.get((crop, key))