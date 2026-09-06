"""Image moderation inference service."""

from functools import lru_cache
import logging
from typing import Any

from PIL import Image
import torch
from transformers import AutoModelForImageClassification

try:
    from transformers import ViTImageProcessorPil as ImageProcessorClass
except ImportError:
    try:
        from transformers import ViTImageProcessor as ImageProcessorClass
    except ImportError:
        from transformers import AutoImageProcessor as ImageProcessorClass

from app.core.config import settings
from .base import InferenceService

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    """Load and cache transformer image processor and classification model."""
    logger.info("Loading image moderation model '%s'...", model_name)
    processor = ImageProcessorClass.from_pretrained(model_name)
    model = AutoModelForImageClassification.from_pretrained(model_name)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    logger.info("Image moderation model '%s' loaded on %s", model_name, device)

    return processor, model, device


class ImageInferenceService(InferenceService):
    """Inference service for image moderation using Vision Transformer."""

    def __init__(
        self,
        model_name: str | None = None,
        threshold: float | None = None,
        loader=None,
    ):
        self.model_name = model_name or settings.IMAGE_MODERATION_MODEL
        self.threshold = (
            threshold
            if threshold is not None
            else settings.IMAGE_MODERATION_THRESHOLD
        )
        self._load = loader or _load_model

    @torch.inference_mode()
    def moderate(self, content: Image.Image) -> dict:
        """Run moderation inference on a decoded PIL Image.

        Returns normalized dictionary:
        {
            "is_flagged": bool,
            "categories": list[str],
            "scores": dict[str, float],
            "model": str,
        }
        """
        if not isinstance(content, Image.Image):
            raise TypeError(
                f"Expected PIL.Image.Image, got {type(content).__name__}"
            )

        if content.mode != "RGB":
            content = content.convert("RGB")

        processor, model, device = self._load(self.model_name)

        inputs = processor(images=content, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        outputs = model(**inputs)
        logits = outputs.logits
        probabilities = (
            torch.softmax(logits, dim=-1).squeeze().cpu().tolist()
        )

        id2label = getattr(model.config, "id2label", {0: "normal", 1: "nsfw"})
        scores: dict[str, float] = {}

        if isinstance(probabilities, float):
            probabilities = [1.0 - probabilities, probabilities]

        for i, prob in enumerate(probabilities):
            label = str(id2label.get(i, id2label.get(str(i), f"class_{i}"))).lower()
            scores[label] = round(float(prob), 4)

        nsfw_score = scores.get("nsfw", 0.0)
        is_flagged = nsfw_score >= self.threshold
        categories = ["nsfw"] if is_flagged else []

        return {
            "is_flagged": is_flagged,
            "categories": categories,
            "scores": scores,
            "model": self.model_name,
        }
