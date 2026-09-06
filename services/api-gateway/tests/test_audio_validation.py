import io
import math
import struct
import wave
import pytest

from app.core.config import settings
from app.services.media.audio_validator import (
    normalize_audio_mime_type,
    validate_and_load_audio,
)
from app.services.media.exceptions import (
    AudioCorruptError,
    AudioDurationError,
    AudioFormatError,
    AudioSizeError,
)


def _create_wav_bytes(
    duration_seconds: float = 1.0,
    sample_rate: int = 16000,
    num_channels: int = 1,
    amplitude: float = 0.5,
) -> bytes:
    """Generate a clean synthetic WAV byte stream."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        total_frames = int(duration_seconds * sample_rate)
        frames = bytearray()
        for i in range(total_frames):
            val = int(32767.0 * amplitude * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
            for _ in range(num_channels):
                frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return buf.getvalue()


def test_valid_wav_accepted():
    wav_bytes = _create_wav_bytes(duration_seconds=1.5, sample_rate=16000, num_channels=1)
    res = validate_and_load_audio(wav_bytes)

    assert res.duration_seconds == pytest.approx(1.5, abs=0.05)
    assert res.metadata["format"] == "wav"
    assert res.metadata["sample_rate"] == 16000
    assert res.metadata["channels"] == 1
    assert res.audio_array.ndim == 1
    assert len(res.audio_array) == pytest.approx(int(1.5 * 16000), abs=10)


def test_stereo_wav_downmixed_to_mono():
    wav_bytes = _create_wav_bytes(duration_seconds=1.0, sample_rate=16000, num_channels=2)
    res = validate_and_load_audio(wav_bytes)

    assert res.metadata["channels"] == 2
    assert res.audio_array.ndim == 1  # Result is flattened/averaged to 1D mono
    assert len(res.audio_array) == 16000


def test_non_16khz_wav_resampled():
    wav_bytes = _create_wav_bytes(duration_seconds=2.0, sample_rate=44100, num_channels=1)
    res = validate_and_load_audio(wav_bytes)

    assert res.metadata["sample_rate"] == 44100
    # Processed array should be resampled to 16,000 Hz
    expected_samples = 2 * 16000
    assert abs(len(res.audio_array) - expected_samples) <= 2


def test_plain_text_rejected():
    stream = io.BytesIO(b"This is not an audio file in any way.")
    with pytest.raises(AudioCorruptError, match="Cannot identify or decode audio"):
        validate_and_load_audio(stream)


def test_empty_stream_rejected():
    stream = io.BytesIO(b"")
    with pytest.raises(AudioCorruptError, match="Audio stream is empty"):
        validate_and_load_audio(stream)


def test_corrupted_truncated_wav_rejected():
    raw_valid = _create_wav_bytes(duration_seconds=2.0)
    # Truncate halfway through data frames
    truncated = raw_valid[: len(raw_valid) // 3]
    with pytest.raises(AudioCorruptError):
        validate_and_load_audio(truncated)


def test_unsupported_format_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_ALLOWED_FORMATS", "OGG,FLAC")
    wav_bytes = _create_wav_bytes(duration_seconds=1.0)
    with pytest.raises(AudioFormatError, match="Unsupported audio format: WAV"):
        validate_and_load_audio(wav_bytes)


def test_audio_duration_exceeded_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_MAX_DURATION_SECONDS", 2.0)
    # 3 seconds > 2 seconds limit
    wav_bytes = _create_wav_bytes(duration_seconds=3.0)
    with pytest.raises(AudioDurationError, match="exceeds maximum permitted limit"):
        validate_and_load_audio(wav_bytes)


def test_audio_size_exceeded_rejected(monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_MAX_SIZE_BYTES", 1000)
    wav_bytes = _create_wav_bytes(duration_seconds=1.0, sample_rate=16000)
    assert len(wav_bytes) > 1000
    with pytest.raises(AudioSizeError, match="exceeds maximum permitted limit"):
        validate_and_load_audio(wav_bytes)


def test_normalize_audio_mime_types():
    assert normalize_audio_mime_type("audio/x-wav") == "audio/wav"
    assert normalize_audio_mime_type("audio/wave") == "audio/wav"
    assert normalize_audio_mime_type("audio/mp3") == "audio/mpeg"
    assert normalize_audio_mime_type("audio/mpeg; charset=utf-8") == "audio/mpeg"
    assert normalize_audio_mime_type("audio/x-m4a") == "audio/mp4"
    assert normalize_audio_mime_type("audio/ogg") == "audio/ogg"
