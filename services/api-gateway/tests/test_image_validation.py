import io
import pytest
from PIL import Image

from app.core.config import settings
from app.services.media.exceptions import (
    ImageCorruptError,
    ImageDecompressionBombError,
    ImageDimensionError,
    ImageFormatError,
)
from app.services.media.image_validator import validate_and_load_image


def _create_image_bytes(format="PNG", size=(50, 50), color="blue", mode="RGB"):
    buf = io.BytesIO()
    img = Image.new(mode, size, color=color)
    img.save(buf, format=format)
    buf.seek(0)
    return buf


def test_valid_png_accepted():
    stream = _create_image_bytes(format="PNG", size=(64, 64))
    img = validate_and_load_image(stream)
    assert img.size == (64, 64)
    assert img.mode == "RGB"


def test_valid_jpeg_accepted():
    stream = _create_image_bytes(format="JPEG", size=(100, 80))
    img = validate_and_load_image(stream)
    assert img.size == (100, 80)
    assert img.mode == "RGB"


def test_rgba_converted_to_rgb():
    stream = _create_image_bytes(format="PNG", size=(32, 32), mode="RGBA", color=(255, 0, 0, 128))
    img = validate_and_load_image(stream)
    assert img.mode == "RGB"


def test_grayscale_converted_to_rgb():
    stream = _create_image_bytes(format="PNG", size=(32, 32), mode="L", color=128)
    img = validate_and_load_image(stream)
    assert img.mode == "RGB"


def test_plain_text_rejected():
    stream = io.BytesIO(b"Hello world, this is definitely not an image!")
    with pytest.raises(ImageCorruptError, match="Cannot identify or decode image"):
        validate_and_load_image(stream)


def test_empty_stream_rejected():
    stream = io.BytesIO(b"")
    with pytest.raises(ImageCorruptError, match="Cannot identify or decode image"):
        validate_and_load_image(stream)


def test_corrupted_truncated_image_rejected():
    raw_valid = _create_image_bytes(format="PNG", size=(100, 100)).getvalue()
    # Truncate halfway through PNG data
    truncated = io.BytesIO(raw_valid[: len(raw_valid) // 3])
    with pytest.raises(ImageCorruptError):
        validate_and_load_image(truncated)


def test_unsupported_format_bmp_rejected():
    stream = _create_image_bytes(format="BMP", size=(20, 20))
    with pytest.raises(ImageFormatError, match="Unsupported image format: BMP"):
        validate_and_load_image(stream)


def test_dimension_exceeded_rejected(monkeypatch):
    monkeypatch.setattr(settings, "IMAGE_MAX_DIMENSION", 100)
    stream = _create_image_bytes(format="PNG", size=(101, 50))
    with pytest.raises(ImageDimensionError, match="exceed maximum permitted limit"):
        validate_and_load_image(stream)


def test_total_pixels_exceeded_rejected(monkeypatch):
    monkeypatch.setattr(settings, "IMAGE_MAX_TOTAL_PIXELS", 5000)
    # 80x80 = 6400 > 5000
    stream = _create_image_bytes(format="PNG", size=(80, 80))
    with pytest.raises(ImageDecompressionBombError, match="exceed maximum permitted limit"):
        validate_and_load_image(stream)
