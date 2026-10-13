import sys
from pathlib import Path

import numpy as np

from app.services.disease_classifier import ClassifierUnavailable, get_classifier
from app.services.disease_image import InvalidImage, prepare_image
from app.services.disease_logic import interpret

if len(sys.argv) != 3:
    sys.exit("Usage: python check_disease.py <image path> <Tomato|Maize>")

path, crop = Path(sys.argv[1]), sys.argv[2]
try:
    classifier = get_classifier()
    array = prepare_image(path.read_bytes(), getattr(classifier, "image_size", 224))
except (OSError, ClassifierUnavailable, InvalidImage) as exc:
    sys.exit(f"Failed: {exc}")

probabilities = classifier.predict(array)
result = interpret(probabilities, classifier.classes, crop)

print(f"status: {result.status} | level: {result.level} | share of the model's score on {crop}: "
      f"{result.crop_mass:.2f}")
if result.top:
    print(f"top: {result.top.info.key} ({result.top.probability:.3f})")
    for alternative in result.alternatives:
        print(f"   then: {alternative.info.key} ({alternative.probability:.3f})")

print("\nModel's three highest scores over all classes:")
for index in np.argsort(probabilities)[::-1][:3]:
    info = classifier.classes[int(index)]
    print(f"   {info.crop} / {info.key}: {probabilities[index]:.3f}")