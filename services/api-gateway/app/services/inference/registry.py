# from .base import InferenceService
from .handler import ModerationHandler
from .image_handler import ImageModerationHandler
from .text_handler import TextModerationHandler


_HANDLERS: dict[str, type[ModerationHandler]] = {
    "text": TextModerationHandler,
    "image": ImageModerationHandler,
}


def get_moderation_handler(content_type: str) -> ModerationHandler:

    handler_class = _HANDLERS.get(content_type)

    if handler_class is None:
        raise ValueError(
            f"Unsupported moderation content type: {content_type}"
        )

    return handler_class()


# def get_inference_service(content_type: str):
#     if content_type == "text":
#         from .text import TextInferenceService

#         return TextInferenceService()

#     raise ValueError(f"Unsupported moderation content type: {content_type}")