from app.moderation.ml_engine import predict
from .base import InferenceService


class TextInferenceService(InferenceService):
    model_name: str = "moderashield-text-v1"

    def moderate(self, content: str) -> dict:
        result = predict(content)

        return {
            **result,
            "model": self.model_name,
        }