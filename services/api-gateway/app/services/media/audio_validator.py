"""Audio validation and safe decoding service."""

import io
import logging
import struct
from typing import BinaryIO, NamedTuple

import numpy as np
import soundfile as sf

from app.core.config import settings
from app.services.media.exceptions import (
    AudioCorruptError,
    AudioDurationError,
    AudioFormatError,
    AudioSizeError,
    AudioValidationError,
)

logger = logging.getLogger(__name__)


class AudioValidationResult(NamedTuple):
    """Result of audio validation and decoding."""
    metadata: dict[str, object]
    audio_array: np.ndarray
    duration_seconds: float


def normalize_audio_mime_type(mime_type: str) -> str:
    """Normalize audio MIME type string."""
    clean = mime_type.split(";", 1)[0].strip().lower()
    normalizations = {
        "audio/x-wav": "audio/wav",
        "audio/wave": "audio/wav",
        "audio/mp3": "audio/mpeg",
        "audio/x-m4a": "audio/mp4",
        "audio/x-flac": "audio/flac",
    }
    return normalizations.get(clean, clean)


def _detect_magic_format(header: bytes) -> str | None:
    """Detect known audio container formats from leading magic bytes."""
    if len(header) < 4:
        return None
    if header[:4] == b"RIFF" and len(header) >= 12 and header[8:12] == b"WAVE":
        return "WAV"
    if header[:3] == b"ID3" or header[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "MP3"
    if header[:4] == b"OggS":
        return "OGG"
    if header[:4] == b"fLaC":
        return "FLAC"
    if len(header) >= 8 and header[4:8] == b"ftyp":
        return "MP4"
    if header[:4] == b"\x1a\x45\xdf\xa3":
        return "WEBM"
    if header[:2] in (b"\xff\xf1", b"\xff\xf9"):
        return "AAC"
    return None


def validate_and_load_audio(
    stream: BinaryIO | bytes,
    size_bytes: int | None = None,
) -> AudioValidationResult:
    """Safely decode, validate, and verify audio from a binary stream or bytes.

    Enforces:
    - Non-empty payload check
    - Configurable maximum size check (AUDIO_MAX_SIZE_BYTES)
    - Format allowlisting (ignoring untrusted client MIME headers)
    - Configurable maximum duration check (AUDIO_MAX_DURATION_SECONDS)
    - Integrity check (decoding all audio samples to catch corrupted/truncated streams)
    - Resampling and channel averaging to 16 kHz mono float32 for Whisper
    """
    if isinstance(stream, (bytes, bytearray)):
        stream = io.BytesIO(stream)
    elif hasattr(stream, "seek"):
        stream.seek(0)

    raw_bytes = stream.read()
    if hasattr(stream, "seek"):
        stream.seek(0)

    actual_size = len(raw_bytes)
    if actual_size == 0:
        logger.warning("Audio validation failed: stream is empty")
        raise AudioCorruptError("Audio stream is empty")

    effective_size = size_bytes if size_bytes is not None else actual_size
    if effective_size > settings.AUDIO_MAX_SIZE_BYTES:
        logger.warning(
            "Audio rejected: size %s bytes exceeds maximum limit of %s bytes",
            effective_size,
            settings.AUDIO_MAX_SIZE_BYTES,
        )
        raise AudioSizeError(
            f"Audio size {effective_size} bytes exceeds maximum permitted "
            f"limit of {settings.AUDIO_MAX_SIZE_BYTES} bytes"
        )

    buffer = io.BytesIO(raw_bytes)

    try:
        info = sf.info(buffer)
    except Exception as error:
        buffer.seek(0)
        header = buffer.read(16)
        magic_format = _detect_magic_format(header)
        if magic_format and magic_format not in settings.audio_allowed_formats:
            logger.warning("Audio rejected: detected unsupported format '%s'", magic_format)
            raise AudioFormatError(
                f"Unsupported audio format: {magic_format}. "
                f"Allowed formats: {sorted(settings.audio_allowed_formats)}"
            ) from error

        logger.warning("Audio failed validation: unidentifiable or malformed data: %s", error)
        raise AudioCorruptError(
            f"Cannot identify or decode audio: {error}"
        ) from error

    detected_format = (info.format or "").upper()
    if detected_format not in settings.audio_allowed_formats:
        logger.warning("Audio rejected: unsupported format '%s'", detected_format)
        raise AudioFormatError(
            f"Unsupported audio format: {detected_format or 'unknown'}. "
            f"Allowed formats: {sorted(settings.audio_allowed_formats)}"
        )

    duration = float(info.duration)
    if duration <= 0:
        raise AudioCorruptError(f"Invalid audio duration: {duration}s")

    if duration > settings.AUDIO_MAX_DURATION_SECONDS:
        logger.warning(
            "Audio rejected: duration %.2fs exceeds maximum limit of %.2fs",
            duration,
            settings.AUDIO_MAX_DURATION_SECONDS,
        )
        raise AudioDurationError(
            f"Audio duration {duration:.2f}s exceeds maximum permitted "
            f"limit of {settings.AUDIO_MAX_DURATION_SECONDS:.2f}s"
        )

    sample_rate = int(info.samplerate)
    channels = int(info.channels)
    if sample_rate <= 0 or channels <= 0:
        raise AudioCorruptError(
            f"Invalid audio stream properties: sample_rate={sample_rate}, channels={channels}"
        )

    if detected_format == "WAV" and len(raw_bytes) >= 12 and raw_bytes[:4] == b"RIFF":
        riff_size = struct.unpack("<I", raw_bytes[4:8])[0] + 8
        if len(raw_bytes) < riff_size:
            logger.warning(
                "Audio rejected: truncated WAV stream (expected %s bytes, got %s)",
                riff_size,
                len(raw_bytes),
            )
            raise AudioCorruptError(
                f"WAV stream is truncated: expected at least {riff_size} bytes, got {len(raw_bytes)}"
            )

    try:
        buffer.seek(0)
        data, _ = sf.read(buffer, dtype="float32")
    except Exception as error:
        logger.warning("Audio failed sample decoding: corrupted or truncated data: %s", error)
        raise AudioCorruptError(
            f"Malformed or truncated audio data: {error}"
        ) from error

    if len(data) == 0:
        raise AudioCorruptError("Audio data contains no decodable audio frames")

    if np.isnan(data).any() or np.isinf(data).any():
        raise AudioCorruptError("Audio data contains NaN or Inf values")

    # Downmix multi-channel to mono float32
    if data.ndim > 1:
        data = data.mean(axis=1)

    # Resample to 16,000 Hz if needed (Whisper feature extractor requirement)
    if sample_rate != 16000:
        target_len = int(round(len(data) * 16000.0 / sample_rate))
        if target_len > 0:
            data = np.interp(
                np.linspace(0, len(data), target_len, endpoint=False),
                np.arange(len(data)),
                data,
            ).astype(np.float32)

    metadata: dict[str, object] = {
        "duration_seconds": round(duration, 2),
        "sample_rate": sample_rate,
        "channels": channels,
        "format": detected_format.lower(),
    }

    return AudioValidationResult(
        metadata=metadata,
        audio_array=data,
        duration_seconds=duration,
    )
