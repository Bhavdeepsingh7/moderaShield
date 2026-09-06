"""Exceptions for media handling, security, and validation."""


class NonRetriableProcessingError(Exception):
    """Signals that the error is permanent and retrying will never succeed."""


class ImageValidationError(NonRetriableProcessingError):
    """Base exception for image validation failures."""


class ImageCorruptError(ImageValidationError):
    """Raised when image data cannot be decoded or is corrupted."""


class ImageFormatError(ImageValidationError):
    """Raised when an unsupported image format is detected."""


class ImageDimensionError(ImageValidationError):
    """Raised when image width or height exceeds configured maximum limits."""


class ImageDecompressionBombError(ImageValidationError):
    """Raised when image pixel count exceeds decompression bomb protection limits."""
