import io
import pytest
from PIL import Image
import torch

from app.services.inference.image import ImageInferenceService


class DummyConfig:
    id2label = {0: "normal", 1: "nsfw"}


class DummyOutput:
    def __init__(self, logits):
        self.logits = logits


class DummyModel:
    def __init__(self, nsfw_logit=2.0, normal_logit=-2.0):
        self.config = DummyConfig()
        self.nsfw_logit = nsfw_logit
        self.normal_logit = normal_logit

    def to(self, device):
        return self

    def eval(self):
        return self

    def __call__(self, **kwargs):
        # returns batch of size 1 with [normal_logit, nsfw_logit]
        logits = torch.tensor([[self.normal_logit, self.nsfw_logit]])
        return DummyOutput(logits)


class DummyProcessor:
    def __call__(self, images=None, return_tensors="pt"):
        return {"pixel_values": torch.zeros((1, 3, 224, 224))}


def test_image_inference_contract_flagged():
    dummy_model = DummyModel(nsfw_logit=5.0, normal_logit=-5.0)
    dummy_processor = DummyProcessor()

    service = ImageInferenceService(
        model_name="mock-nsfw-model",
        threshold=0.5,
        loader=lambda _: (dummy_processor, dummy_model, torch.device("cpu")),
    )

    img = Image.new("RGB", (64, 64), color="red")
    result = service.moderate(img)

    assert result["is_flagged"] is True
    assert result["categories"] == ["nsfw"]
    assert "nsfw" in result["scores"]
    assert "normal" in result["scores"]
    assert result["scores"]["nsfw"] > 0.9
    assert result["model"] == "mock-nsfw-model"


def test_image_inference_contract_approved():
    dummy_model = DummyModel(nsfw_logit=-5.0, normal_logit=5.0)
    dummy_processor = DummyProcessor()

    service = ImageInferenceService(
        model_name="mock-nsfw-model",
        threshold=0.5,
        loader=lambda _: (dummy_processor, dummy_model, torch.device("cpu")),
    )

    img = Image.new("RGB", (64, 64), color="green")
    result = service.moderate(img)

    assert result["is_flagged"] is False
    assert result["categories"] == []
    assert result["scores"]["nsfw"] < 0.1
    assert result["scores"]["normal"] > 0.9
    assert result["model"] == "mock-nsfw-model"


def test_image_inference_threshold_boundary():
    # logits = [0.0, 0.0] -> softmax = [0.5, 0.5]
    dummy_model = DummyModel(nsfw_logit=0.0, normal_logit=0.0)
    dummy_processor = DummyProcessor()

    # Threshold 0.5 -> 0.5 >= 0.5 -> flagged
    service1 = ImageInferenceService(
        threshold=0.5,
        loader=lambda _: (dummy_processor, dummy_model, torch.device("cpu")),
    )
    res1 = service1.moderate(Image.new("RGB", (10, 10)))
    assert res1["is_flagged"] is True
    assert res1["categories"] == ["nsfw"]

    # Threshold 0.51 -> 0.5 < 0.51 -> not flagged
    service2 = ImageInferenceService(
        threshold=0.51,
        loader=lambda _: (dummy_processor, dummy_model, torch.device("cpu")),
    )
    res2 = service2.moderate(Image.new("RGB", (10, 10)))
    assert res2["is_flagged"] is False
    assert res2["categories"] == []


def test_image_inference_invalid_type():
    service = ImageInferenceService()
    with pytest.raises(TypeError, match="Expected PIL.Image.Image"):
        service.moderate("not an image")


def test_real_model_inference_cached():
    # Runs the actual cached model on a synthetic test image to ensure
    # transformers integration, device handling, and normalization work for real.
    service = ImageInferenceService()
    img = Image.new("RGB", (224, 224), color="blue")
    result = service.moderate(img)

    assert isinstance(result["is_flagged"], bool)
    assert isinstance(result["categories"], list)
    assert isinstance(result["scores"], dict)
    assert "nsfw" in result["scores"]
    assert "normal" in result["scores"]
    assert isinstance(result["scores"]["nsfw"], float)
    assert isinstance(result["scores"]["normal"], float)
    assert result["model"] == "Falconsai/nsfw_image_detection"
