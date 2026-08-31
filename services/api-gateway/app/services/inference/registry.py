from .base import InferenceService


def get_inference_service(content_type: str) -> InferenceService:
    if content_type == "text":
        from .text import TextInferenceService
        return TextInferenceService()

    raise ValueError(
        f"Unsupported moderation content type: {content_type}"
    )