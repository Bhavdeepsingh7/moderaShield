from app.models.moderation import ModerationRequest

from .handler import ModerationHandler
from .text import TextInferenceService

class TextModerationHandler(ModerationHandler):
    def handle(self,db ,  request: ModerationRequest) -> dict:
        if request.content is None:
            raise ValueError("Text moderation has no content")

        inference_service = TextInferenceService()
        return inference_service.moderate(request.content)