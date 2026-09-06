from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from app.models.moderation import ModerationRequest


class ModerationHandler(ABC):

    @abstractmethod
    def handle(self, db: Session, request: ModerationRequest) -> dict:
        """Handle a moderation request."""
        raise NotImplementedError
