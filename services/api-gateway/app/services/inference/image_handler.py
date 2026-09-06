import logging
from sqlalchemy.orm import Session

from app.models.moderation import ModerationRequest
from app.services.media.asset_resolver import AssetResolver
from app.services.media.image_validator import validate_and_load_image
from .handler import ModerationHandler
from .image import ImageInferenceService

logger = logging.getLogger(__name__)


class ImageModerationHandler(ModerationHandler):
    """Handles image moderation by resolving the asset, validating it, and running inference."""

    def __init__(
        self,
        asset_resolver: AssetResolver | None = None,
        inference_service: ImageInferenceService | None = None,
    ):
        self.asset_resolver = asset_resolver or AssetResolver()
        self.inference_service = inference_service or ImageInferenceService()

    def handle(self, db: Session, request: ModerationRequest) -> dict:
        """Resolve the asset stream, validate the image, and return normalized moderation results."""
        try:
            image_stream = self.asset_resolver.open_asset(db, request)
        finally:
            if db is not None and getattr(db, "in_transaction", None) and db.in_transaction():
                db.rollback()

        try:
            image = validate_and_load_image(image_stream)
            return self.inference_service.moderate(image)
        finally:
            image_stream.close()
