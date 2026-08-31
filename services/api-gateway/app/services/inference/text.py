from app.moderation.ml_engine import predict
from .base import InferenceService


class TextInferenceService(InferenceService):

    def moderate(self, content:str) -> dict:
        result =  predict(content)

        return {
            **result,
            "model": "moderashield-text-v1",
        }