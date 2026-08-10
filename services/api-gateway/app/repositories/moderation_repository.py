from sqlalchemy.orm import Session

from app.models.moderation import ModerationRequest

class ModerationRepository:

    def create(
            self ,
            db:Session,
            moderation_request: ModerationRequest,
    )-> ModerationRequest:
        db.add(moderation_request)
        db.commit()
        db.refresh(moderation_request)

        return moderation_request


moderation_repository = ModerationRepository()