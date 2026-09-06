"""Audio moderation handler."""

import logging
from typing import Callable
from sqlalchemy.orm import Session

from app.models.moderation import ModerationRequest
from app.models.moderation_asset import ModerationAsset
from app.services.media.asset_resolver import AssetResolver
from app.services.media.audio_validator import validate_and_load_audio
from .audio import SpeechToTextService, WhisperSpeechToTextService
from .handler import ModerationHandler
from .text import TextInferenceService

logger = logging.getLogger(__name__)


class AudioModerationHandler(ModerationHandler):
    """Handles audio moderation by resolving the asset, validating/decoding it,
    transcribing speech via Whisper, and moderating the transcript via the text moderation model.
    """

    def __init__(
        self,
        asset_resolver: AssetResolver | None = None,
        transcription_service: SpeechToTextService | None = None,
        text_service: TextInferenceService | None = None,
        validator: Callable | None = None,
    ):
        self.asset_resolver = asset_resolver or AssetResolver()
        self.transcription_service = (
            transcription_service or WhisperSpeechToTextService()
        )
        self.text_service = text_service or TextInferenceService()
        self.validator = validator or validate_and_load_audio

    def handle(self, db: Session, request: ModerationRequest) -> dict:
        """Resolve the asset stream, validate audio, transcribe, and moderate transcript."""
        if request.content_type != "audio":
            raise ValueError(f"Expected audio content type, got {request.content_type}")

        if request.asset_id is None:
            raise ValueError("Audio moderation request has no asset")

        try:
            audio_stream = self.asset_resolver.open_asset(db, request)
        finally:
            if db is not None and getattr(db, "in_transaction", None) and db.in_transaction():
                db.rollback()

        try:
            # 1. Validate audio format, size, duration, and decode to 16kHz mono float32
            validation_res = self.validator(audio_stream)

            # 2. Persist extracted audio metadata safely in ModerationAsset
            if db is not None:
                try:
                    with db.begin():
                        asset = db.get(ModerationAsset, request.asset_id)
                        if asset is not None:
                            current_meta = asset.asset_metadata or {}
                            asset.asset_metadata = {
                                **current_meta,
                                **validation_res.metadata,
                            }
                except Exception as meta_error:
                    logger.warning("Failed to persist asset metadata: %s", meta_error)

            # 3. Transcribe audio to text
            transcription = self.transcription_service.transcribe(
                validation_res.audio_array,
                duration_seconds=validation_res.duration_seconds,
            )

            transcript = transcription.get("text", "").strip()

            # 4. If no meaningful speech is detected, return approved result without invoking text model
            composite_model = f"{self.transcription_service.model_name} + {self.text_service.model_name}"
            if not transcript:
                logger.info("Audio request %s produced no detected speech; approving", request.id)
                return {
                    "is_flagged": False,
                    "categories": [],
                    "scores": {
                        "toxic": 0.0,
                        "severe_toxic": 0.0,
                        "obscene": 0.0,
                        "threat": 0.0,
                        "insult": 0.0,
                        "identity_hate": 0.0,
                    },
                    "model": composite_model,
                }

            # 5. Moderate the transcript using the existing text moderation model
            text_result = self.text_service.moderate(transcript)

            actual_text_model = text_result.get("model", self.text_service.model_name)
            composite_model = f"{self.transcription_service.model_name} + {actual_text_model}"

            return {
                "is_flagged": text_result["is_flagged"],
                "categories": text_result["categories"],
                "scores": text_result["scores"],
                "model": composite_model,
            }
        finally:
            if hasattr(audio_stream, "close"):
                audio_stream.close()
