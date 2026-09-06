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


class AudioValidationError(NonRetriableProcessingError):
    """Base exception for audio validation failures."""


class AudioCorruptError(AudioValidationError):
    """Raised when audio data cannot be decoded, is malformed, or is corrupted."""


class AudioFormatError(AudioValidationError):
    """Raised when an unsupported audio format is detected."""


class AudioDurationError(AudioValidationError):
    """Raised when audio duration exceeds configured maximum limits."""


class AudioSizeError(AudioValidationError):
    """Raised when audio size exceeds configured maximum byte limits."""
