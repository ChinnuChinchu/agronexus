"""Turns an uploaded photo into the array the disease model expects."""

from io import BytesIO

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PIXELS = 25_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class InvalidImage(Exception):
    """The upload is not a usable photo. The message is safe to show."""


def prepare_image(data: bytes, size: int = 224) -> np.ndarray:
    """Returns float32 RGB pixels (0-255) with shape (1, size, size, 3)."""
    if not data:
        raise InvalidImage("The image is empty")

    try:
        image = Image.open(BytesIO(data))
        if image.format not in ALLOWED_FORMATS:
            raise InvalidImage("Please upload a JPEG, PNG or WebP photo")

        # check the size from the header, before decoding any pixels
        if image.width * image.height > MAX_PIXELS:
            raise InvalidImage("The image is too large. Please use a smaller photo")

        if image.format == "JPEG":
            image.draft("RGB", (size * 2, size * 2))  # decode a smaller version, faster and lighter

        image = ImageOps.exif_transpose(image)  # respect the phone's rotation flag
        image = image.convert("RGB")
    except InvalidImage:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise InvalidImage("The image could not be read. Please upload a valid photo") from None

    side = min(image.size)  # centre-crop to a square, so lesions are not distorted
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    image = image.resize((size, size), Image.Resampling.BILINEAR)
    return np.asarray(image, dtype=np.float32)[None, ...]