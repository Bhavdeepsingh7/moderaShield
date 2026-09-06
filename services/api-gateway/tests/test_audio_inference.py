import numpy as np
import pytest
import torch

from app.services.inference.audio import (
    SpeechToTextService,
    WhisperSpeechToTextService,
    resolve_device,
)


class DummyWhisperProcessor:
    def __init__(self):
        self.called_inputs = None

    def __call__(self, audio, sampling_rate=16000, return_tensors="pt"):
        self.called_inputs = audio
        class Features:
            input_features = torch.zeros((1, 80, 3000))
        return Features()

    def batch_decode(self, sequences, skip_special_tokens=True):
        return ["hello this is transcribed text"]


class DummyWhisperModel:
    def __init__(self):
        self.device = torch.device("cpu")

    def to(self, device):
        self.device = device
        return self

    def eval(self):
        return self

    def generate(self, input_features, **kwargs):
        # return dummy token sequence
        return torch.tensor([[50258, 50259, 50359]])


def test_speech_to_text_service_contract_with_speech():
    dummy_processor = DummyWhisperProcessor()
    dummy_model = DummyModel = DummyWhisperModel()

    service = WhisperSpeechToTextService(
        model_name="mock-whisper-model",
        device="cpu",
        language="en",
        loader=lambda m, d: (dummy_processor, dummy_model, torch.device("cpu")),
    )

    # Audio with active sound signal
    audio = np.sin(np.linspace(0, 100, 16000)).astype(np.float32)
    result = service.transcribe(audio, duration_seconds=1.0)

    assert isinstance(result, dict)
    assert result["text"] == "hello this is transcribed text"
    assert result["language"] == "en"
    assert result["duration_seconds"] == 1.0


def test_speech_to_text_empty_silence_audio():
    dummy_processor = DummyWhisperProcessor()
    dummy_model = DummyWhisperModel()

    service = WhisperSpeechToTextService(
        model_name="mock-whisper-model",
        loader=lambda m, d: (dummy_processor, dummy_model, torch.device("cpu")),
    )

    # Pure silence (zeros)
    silent_audio = np.zeros(16000, dtype=np.float32)
    result = service.transcribe(silent_audio, duration_seconds=1.0)

    assert result["text"] == ""
    assert result["duration_seconds"] == 1.0
    # Processor and model should not even have been called for silence
    assert dummy_processor.called_inputs is None


def test_speech_to_text_invalid_type():
    service = WhisperSpeechToTextService()
    with pytest.raises(TypeError, match="Expected BinaryIO, bytes, or np.ndarray"):
        service.transcribe(12345)


def test_device_resolution():
    cpu_dev = resolve_device("cpu")
    assert cpu_dev.type == "cpu"

    auto_dev = resolve_device("auto")
    expected_type = "cuda" if torch.cuda.is_available() else "cpu"
    assert auto_dev.type == expected_type


def test_real_model_transcription_cached():
    # Tests the actual cached Whisper-tiny model on a short synthetic audio array
    service = WhisperSpeechToTextService(model_name="openai/whisper-tiny")
    # Generate 1 second of clean tone
    audio = (0.2 * np.sin(np.linspace(0, 440 * 2 * np.pi, 16000))).astype(np.float32)
    result = service.transcribe(audio, duration_seconds=1.0)

    assert isinstance(result, dict)
    assert "text" in result
    assert isinstance(result["text"], str)
    assert result["duration_seconds"] == 1.0
