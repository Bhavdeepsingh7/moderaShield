import io
from uuid import uuid4
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models
from app.models.moderation import ModerationRequest
from app.models.moderation_asset import ModerationAsset
from app.models.tenant import Tenant
from app.services.inference.audio_handler import AudioModerationHandler
from app.services.media.audio_validator import AudioValidationResult
from app.services.media.exceptions import AudioCorruptError


class FakeStream:
    def __init__(self, data=b"fake_audio_stream"):
        self.data = data
        self.closed = False

    def read(self, size=-1):
        return self.data

    def close(self):
        self.closed = True


class MockSpeechToText:
    def __init__(self, transcript="this is a test audio transcript"):
        self.transcript = transcript
        self.model_name = "test-whisper"
        self.transcribed_input = None

    def transcribe(self, audio, duration_seconds=None):
        self.transcribed_input = audio
        return {
            "text": self.transcript,
            "language": "en",
            "duration_seconds": duration_seconds or 1.0,
        }


class MockTextInference:
    def __init__(self, is_flagged=False, categories=None, scores=None):
        self.is_flagged = is_flagged
        self.categories = categories or []
        self.scores = scores or {"toxic": 0.05, "threat": 0.01}
        self.model_name = "test-text-model"
        self.moderated_content = None

    def moderate(self, content: str) -> dict:
        self.moderated_content = content
        return {
            "is_flagged": self.is_flagged,
            "categories": self.categories,
            "scores": self.scores,
            "model": self.model_name,
        }


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_audio_handler_rejects_wrong_content_type():
    handler = AudioModerationHandler()
    request = ModerationRequest(content_type="text", asset_id=uuid4())
    with pytest.raises(ValueError, match="Expected audio content type"):
        handler.handle(None, request)


def test_audio_handler_rejects_missing_asset_id():
    handler = AudioModerationHandler()
    request = ModerationRequest(content_type="audio", asset_id=None)
    with pytest.raises(ValueError, match="Audio moderation request has no asset"):
        handler.handle(None, request)


def test_audio_handler_missing_asset(db_session):
    tenant_id = uuid4()
    request = ModerationRequest(
        tenant_id=tenant_id,
        content_type="audio",
        asset_id=uuid4(),
    )
    handler = AudioModerationHandler()
    with pytest.raises(FileNotFoundError, match="Asset not found"):
        handler.handle(db_session, request)


def test_audio_handler_tenant_mismatch(db_session):
    owner_tenant = uuid4()
    other_tenant = uuid4()

    asset = ModerationAsset(
        tenant_id=owner_tenant,
        storage_provider="local",
        object_key="some/key.wav",
        mime_type="audio/wav",
    )
    db_session.add(asset)
    db_session.commit()

    request = ModerationRequest(
        tenant_id=other_tenant,
        content_type="audio",
        asset_id=asset.id,
    )
    handler = AudioModerationHandler()
    with pytest.raises(PermissionError, match="Asset does not belong to the request tenant"):
        handler.handle(db_session, request)


def test_audio_handler_successful_pipeline(db_session, monkeypatch):
    tenant_id = uuid4()
    asset = ModerationAsset(
        tenant_id=tenant_id,
        storage_provider="local",
        object_key="some/key.wav",
        mime_type="audio/wav",
    )
    db_session.add(asset)
    db_session.commit()

    request = ModerationRequest(
        tenant_id=tenant_id,
        content_type="audio",
        asset_id=asset.id,
    )

    stream = FakeStream()

    class FakeResolver:
        def open_asset(self, db, req):
            return stream

    stt_mock = MockSpeechToText(transcript="kill all enemies immediately")
    text_mock = MockTextInference(
        is_flagged=True,
        categories=["threat"],
        scores={"threat": 0.95, "toxic": 0.88},
    )

    def fake_validator(s):
        return AudioValidationResult(
            metadata={"duration_seconds": 2.5, "sample_rate": 16000, "channels": 1, "format": "wav"},
            audio_array="dummy_audio_array",
            duration_seconds=2.5,
        )

    handler = AudioModerationHandler(
        asset_resolver=FakeResolver(),
        transcription_service=stt_mock,
        text_service=text_mock,
        validator=fake_validator,
    )

    result = handler.handle(db_session, request)

    # 1. Stream was closed
    assert stream.closed is True

    # 2. STT service transcribed the audio
    assert stt_mock.transcribed_input == "dummy_audio_array"

    # 3. Text service moderated the transcript
    assert text_mock.moderated_content == "kill all enemies immediately"

    # 4. Result is normalized with composite model name
    assert result["is_flagged"] is True
    assert result["categories"] == ["threat"]
    assert result["scores"]["threat"] == 0.95
    assert result["model"] == "test-whisper + test-text-model"

    # 5. Asset metadata was safely persisted
    db_session.refresh(asset)
    assert asset.asset_metadata["duration_seconds"] == 2.5
    assert asset.asset_metadata["format"] == "wav"


def test_audio_handler_empty_speech_approved(db_session):
    tenant_id = uuid4()
    asset = ModerationAsset(
        tenant_id=tenant_id,
        storage_provider="local",
        object_key="silence.wav",
        mime_type="audio/wav",
    )
    db_session.add(asset)
    db_session.commit()

    request = ModerationRequest(
        tenant_id=tenant_id,
        content_type="audio",
        asset_id=asset.id,
    )

    stream = FakeStream()

    class FakeResolver:
        def open_asset(self, db, req):
            return stream

    stt_mock = MockSpeechToText(transcript="")  # No speech detected
    text_mock = MockTextInference()

    def fake_validator(s):
        return AudioValidationResult(
            metadata={"duration_seconds": 1.0, "sample_rate": 16000, "channels": 1, "format": "wav"},
            audio_array="silence_array",
            duration_seconds=1.0,
        )

    handler = AudioModerationHandler(
        asset_resolver=FakeResolver(),
        transcription_service=stt_mock,
        text_service=text_mock,
        validator=fake_validator,
    )

    result = handler.handle(db_session, request)

    assert stream.closed is True
    assert result["is_flagged"] is False
    assert result["categories"] == []
    assert result["scores"]["toxic"] == 0.0
    assert result["model"] == "test-whisper + test-text-model"
    # Text model was not called when there was no speech
    assert text_mock.moderated_content is None


def test_audio_handler_stream_closed_on_validation_error():
    request = ModerationRequest(
        tenant_id=uuid4(),
        content_type="audio",
        asset_id=uuid4(),
    )
    stream = FakeStream()

    class FakeResolver:
        def open_asset(self, db, req):
            return stream

    def bad_validator(s):
        raise AudioCorruptError("Corrupted stream header")

    handler = AudioModerationHandler(
        asset_resolver=FakeResolver(),
        validator=bad_validator,
    )

    with pytest.raises(AudioCorruptError, match="Corrupted stream header"):
        handler.handle(None, request)

    assert stream.closed is True
