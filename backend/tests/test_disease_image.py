from io import BytesIO

import pytest
from PIL import Image

from app.services import disease_image
from app.services.disease_image import InvalidImage, prepare_image


def encode(image, fmt):
    buffer = BytesIO()
    image.save(buffer, fmt)
    return buffer.getvalue()


def green(size=(300, 200)):
    return Image.new("RGB", size, (40, 130, 50))


def test_jpeg_becomes_the_model_input():
    array = prepare_image(encode(green(), "JPEG"))

    assert array.shape == (1, 224, 224, 3)
    assert array.dtype.name == "float32"
    assert 0 <= array.min() and array.max() <= 255
    assert abs(float(array[..., 1].mean()) - 130) < 6


def test_png_with_transparency_is_accepted():
    image = Image.new("RGBA", (120, 120), (40, 130, 50, 255))
    assert prepare_image(encode(image, "PNG")).shape == (1, 224, 224, 3)


def test_webp_is_accepted():
    assert prepare_image(encode(green(), "WEBP")).shape == (1, 224, 224, 3)


def test_wide_photo_is_centre_cropped_not_squashed():
    image = Image.new("RGB", (300, 100))
    image.paste((255, 0, 0), (0, 0, 100, 100))      # left third red
    image.paste((0, 255, 0), (100, 0, 200, 100))    # middle third green
    image.paste((0, 0, 255), (200, 0, 300, 100))    # right third blue

    array = prepare_image(encode(image, "PNG"))

    assert array[..., 0].mean() < 5      # no red
    assert array[..., 2].mean() < 5      # no blue
    assert array[..., 1].mean() > 250    # only the green middle is kept


def test_not_an_image_is_rejected():
    with pytest.raises(InvalidImage, match="could not be read"):
        prepare_image(b"this is not a picture")


def test_empty_upload_is_rejected():
    with pytest.raises(InvalidImage, match="empty"):
        prepare_image(b"")


def test_truncated_image_is_rejected():
    data = encode(green((600, 400)), "JPEG")
    with pytest.raises(InvalidImage):
        prepare_image(data[:100])


@pytest.mark.parametrize(
    "image, fmt", [(Image.new("P", (10, 10)), "GIF"), (green(), "BMP")]
)
def test_other_formats_are_rejected(image, fmt):
    with pytest.raises(InvalidImage, match="JPEG, PNG or WebP"):
        prepare_image(encode(image, fmt))


def test_huge_images_are_rejected_before_decoding(monkeypatch):
    monkeypatch.setattr(disease_image, "MAX_PIXELS", 1000)
    with pytest.raises(InvalidImage, match="too large"):
        prepare_image(encode(green((100, 100)), "PNG"))