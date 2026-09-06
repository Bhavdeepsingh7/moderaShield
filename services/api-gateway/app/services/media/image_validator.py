"""Image validation and safe decoding service."""

import logging
from typing import BinaryIO
from PIL import Image

from app.core.config import settings
from app.services.media.exceptions import (
    ImageCorruptError,
    ImageDecompressionBombError,
    ImageDimensionError,
    ImageFormatError,
    ImageValidationError,
)

logger = logging.getLogger(__name__)


def validate_and_load_image(stream: BinaryIO) -> Image.Image:
    """Safely decode, validate, and verify an image from a binary stream.

    Enforces:
    - Format allowlisting (ignoring untrusted client MIME metadata)
    - Decompression bomb protection (both Pillow-level and dimension checks)
    - Dimension boundaries (width, height, total pixels)
    - File integrity (load pixel data to catch corrupted/truncated streams)
    - Standard RGB mode conversion for downstream transformer inference
    """
    # Enforce Pillow total pixel threshold
    Image.MAX_IMAGE_PIXELS = settings.IMAGE_MAX_TOTAL_PIXELS

    try:
        image = Image.open(stream)
    except Image.DecompressionBombError as error:
        logger.warning("Image failed validation: decompression bomb detected: %s", error)
        raise ImageDecompressionBombError(
            f"Image exceeds maximum permitted pixel count: {error}"
        ) from error
    except Exception as error:
        logger.warning("Image failed validation: unidentifiable or malformed data: %s", error)
        raise ImageCorruptError(
            f"Cannot identify or decode image: {error}"
        ) from error

    detected_format = (image.format or "").upper()
    if detected_format not in settings.image_allowed_formats:
        logger.warning("Image rejected: unsupported format '%s'", detected_format)
        raise ImageFormatError(
            f"Unsupported image format: {detected_format or 'unknown'}. "
            f"Allowed formats: {sorted(settings.image_allowed_formats)}"
        )

    width, height = image.size
    if width <= 0 or height <= 0:
        raise ImageCorruptError(f"Invalid image dimensions: {width}x{height}")

    if width > settings.IMAGE_MAX_DIMENSION or height > settings.IMAGE_MAX_DIMENSION:
        logger.warning(
            "Image rejected: dimensions %sx%s exceed maximum limit of %s",
            width,
            height,
            settings.IMAGE_MAX_DIMENSION,
        )
        raise ImageDimensionError(
            f"Image dimensions {width}x{height} exceed maximum permitted "
            f"limit of {settings.IMAGE_MAX_DIMENSION}px"
        )

    total_pixels = width * height
    if total_pixels > settings.IMAGE_MAX_TOTAL_PIXELS:
        logger.warning(
            "Image rejected: total pixels %s exceed maximum limit of %s",
            total_pixels,
            settings.IMAGE_MAX_TOTAL_PIXELS,
        )
        raise ImageDecompressionBombError(
            f"Total pixels {total_pixels} exceed maximum permitted "
            f"limit of {settings.IMAGE_MAX_TOTAL_PIXELS}"
        )

    try:
        # Force decoding pixel data to ensure file is not truncated or corrupted
        image.load()
    except Image.DecompressionBombError as error:
        logger.warning("Image failed load: decompression bomb: %s", error)
        raise ImageDecompressionBombError(
            f"Image exceeds maximum permitted pixel count during load: {error}"
        ) from error
    except Exception as error:
        logger.warning("Image failed load: corrupted or truncated data: %s", error)
        raise ImageCorruptError(
            f"Malformed or truncated image data: {error}"
        ) from error

    if image.mode != "RGB":
        image = image.convert("RGB")

    return image
