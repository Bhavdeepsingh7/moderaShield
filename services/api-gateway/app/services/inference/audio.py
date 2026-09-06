"""Speech-to-text inference service using Whisper."""

from abc import ABC, abstractmethod
from functools import lru_cache
import logging
from typing import Any, BinaryIO

import numpy as np
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from app.core.config import settings
from app.services.media.audio_validator import validate_and_load_audio

logger = logging.getLogger(__name__)


def resolve_device(device_setting: str) -> torch.device:
    """Resolve device setting to torch.device ('auto', 'cpu', 'cuda')."""
    if device_setting == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device_setting)


@lru_cache(maxsize=1)
def _load_whisper_model(model_name: str, device_str: str):
    """Load and cache Whisper processor and conditional generation model."""
    logger.info("Loading speech-to-text model '%s' on %s...", model_name, device_str)
    processor = WhisperProcessor.from_pretrained(model_name)
    model = WhisperForConditionalGeneration.from_pretrained(model_name)

    device = resolve_device(device_str)
    model.to(device)
    model.eval()
    logger.info("Speech-to-text model '%s' loaded on %s", model_name, device)

    return processor, model, device


class SpeechToTextService(ABC):
    """Abstract base class for speech-to-text services."""

    model_name: str

    @abstractmethod
    def transcribe(
        self,
        audio: BinaryIO | bytes | np.ndarray,
        duration_seconds: float | None = None,
    ) -> dict:
        """Transcribe audio to normalized dictionary:
        {
            "text": str,
            "language": str | None,
            "duration_seconds": float | None,
        }
        """
        raise NotImplementedError


class WhisperSpeechToTextService(SpeechToTextService):
    """Inference service for speech-to-text transcription using Whisper."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        language: str | None = None,
        loader=None,
    ):
        self.model_name = model_name or settings.AUDIO_TRANSCRIPTION_MODEL
        self.device_str = device or settings.AUDIO_TRANSCRIPTION_DEVICE
        self.language = (
            language
            if language is not None
            else settings.AUDIO_TRANSCRIPTION_LANGUAGE
        )
        self._load = loader or _load_whisper_model

    @torch.inference_mode()
    def transcribe(
        self,
        audio: BinaryIO | bytes | np.ndarray,
        duration_seconds: float | None = None,
    ) -> dict:
        """Transcribe an audio array or stream.

        Returns normalized dictionary:
        {
            "text": str,
            "language": str | None,
            "duration_seconds": float | None,
        }
        """
        if isinstance(audio, (bytes, bytearray)) or hasattr(audio, "read"):
            validation_res = validate_and_load_audio(audio)
            audio_array = validation_res.audio_array
            duration_seconds = validation_res.duration_seconds
        elif isinstance(audio, np.ndarray):
            audio_array = audio
        else:
            raise TypeError(
                f"Expected BinaryIO, bytes, or np.ndarray, got {type(audio).__name__}"
            )

        # Empty or near-silence audio detection avoids hallucination and wasteful inference
        if len(audio_array) == 0 or np.max(np.abs(audio_array)) < 1e-3:
            return {
                "text": "",
                "language": self.language,
                "duration_seconds": duration_seconds,
            }

        processor, model, device = self._load(self.model_name, self.device_str)

        inputs = processor(audio_array, sampling_rate=16000, return_tensors="pt")
        input_features = inputs.input_features.to(device)

        generate_kwargs: dict[str, Any] = {}
        if self.language:
            generate_kwargs["language"] = self.language

        predicted_ids = model.generate(input_features, **generate_kwargs)
        transcription = processor.batch_decode(
            predicted_ids,
            skip_special_tokens=True,
        )[0].strip()

        return {
            "text": transcription,
            "language": self.language,
            "duration_seconds": duration_seconds,
        }
