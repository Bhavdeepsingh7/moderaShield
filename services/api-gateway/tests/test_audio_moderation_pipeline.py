import asyncio
import io
import json
import logging
import math
import struct
import wave
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints import moderation as moderation_endpoint
from app.api.v1.endpoints.moderation import router
from app.core.config import settings
from app.db.base import Base
import app.db.models
from app.dependencies.auth import get_current_tenant
from app.dependencies.database import get_db
from app.models.moderation import ModerationRequest
from app.models.moderation_asset import ModerationAsset
from app.models.moderation_result import ModerationResult
from app.models.outbox import OutboxEvent
from app.models.tenant import Tenant
from app.models.webhook import Webhook, WebhookDelivery
from app.services.inference.audio import SpeechToTextService
from app.services.inference.audio_handler import AudioModerationHandler
from app.services.inference.text import TextInferenceService
from app.services.media.exceptions import AudioCorruptError
from app.services.storage.local import LocalStorageService
from app.workers import moderation_worker


def _make_test_wav_bytes(
    duration_seconds: float = 1.0,
    sample_rate: int = 16000,
    num_channels: int = 1,
    amplitude: float = 0.5,
) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        total_frames = int(duration_seconds * sample_rate)
        frames = bytearray()
        for i in range(total_frames):
            val = int(32767.0 * amplitude * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
            for _ in range(num_channels):
                frames.extend(struct.pack("<h", val))
        wf.writeframes(frames)
    return buf.getvalue()


class Message:
    def __init__(self, request_id):
        self.value = json.dumps({"request_id": str(request_id)}).encode()


@pytest.fixture
def audio_pipeline_env(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(moderation_worker, "SessionLocal", factory)

    storage = LocalStorageService(tmp_path / "storage")
    monkeypatch.setattr(moderation_endpoint.media_service, "storage", storage)

    monkeypatch.setattr(
        "app.services.media.asset_resolver.get_storage_service",
        lambda provider: storage,
    )

    yield factory, storage

    Base.metadata.drop_all(engine)


def test_audio_moderation_end_to_end_flow(audio_pipeline_env, monkeypatch):
    factory, storage = audio_pipeline_env

    tenant = Tenant(id=uuid4(), name="audio-tenant", slug="audio-tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)
        webhook = Webhook(
            id=uuid4(),
            tenant_id=tenant.id,
            url="https://example.com/webhook",
            secret="test-secret",
            enabled=True,
        )
        db.add(webhook)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/moderate")

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_tenant] = lambda: tenant

    # 1. API audio upload
    wav_bytes = _make_test_wav_bytes(duration_seconds=1.0)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/moderate/media",
            files={"file": ("speech.wav", wav_bytes, "audio/wav")},
        )
        assert response.status_code == 201
        res_data = response.json()
        request_id = UUID(res_data["id"])
        assert res_data["content_type"] == "audio"
        assert res_data["status"] == "pending"

    # Verify initial DB state, asset, outbox, and storage
    with factory() as db:
        req = db.get(ModerationRequest, request_id)
        assert req is not None
        assert req.asset_id is not None
        assert req.content is None  # Never store raw audio bytes in content!
        asset = db.get(ModerationAsset, req.asset_id)
        assert asset is not None
        assert asset.mime_type == "audio/wav"
        assert storage.exists(asset.object_key)

        outbox = db.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == request_id))
        assert outbox is not None
        outbox_payload = json.loads(outbox.payload)
        assert outbox_payload["request_id"] == str(request_id)
        assert outbox_payload["asset_id"] == str(asset.id)
        assert "speech.wav" not in outbox.payload
        assert len(outbox.payload) < 500  # No raw bytes in outbox

    # 2. Worker consumes message with mocked STT and text moderation
    class MockSTT(SpeechToTextService):
        calls = 0
        model_name = "test-whisper-tiny"

        def transcribe(self, audio, duration_seconds=None):
            self.calls += 1
            return {
                "text": "Hello world, having a wonderful day",
                "language": "en",
                "duration_seconds": duration_seconds or 1.0,
            }

    class MockText(TextInferenceService):
        calls = 0
        model_name = "test-text-v1"

        def moderate(self, content: str) -> dict:
            self.calls += 1
            assert content == "Hello world, having a wonderful day"
            return {
                "is_flagged": False,
                "categories": [],
                "scores": {"toxic": 0.01, "threat": 0.005},
                "model": self.model_name,
            }

    mock_stt = MockSTT()
    mock_text = MockText()
    handler = AudioModerationHandler(
        transcription_service=mock_stt,
        text_service=mock_text,
    )
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    asyncio.run(moderation_worker.process_message(Message(request_id)))

    # 3. Verify final DB state, asset_metadata, and webhook delivery
    with factory() as db:
        req = db.get(ModerationRequest, request_id)
        assert req.status == "approved"
        assert req.retry_count == 0

        asset = db.get(ModerationAsset, req.asset_id)
        assert asset.asset_metadata is not None
        assert asset.asset_metadata["format"] == "wav"
        assert asset.asset_metadata["sample_rate"] == 16000

        mod_res = db.scalar(select(ModerationResult).where(ModerationResult.request_id == request_id))
        assert mod_res is not None
        assert mod_res.is_flagged is False
        assert mod_res.category == []
        assert mod_res.score == {"toxic": 0.01, "threat": 0.005}
        assert mod_res.model == "test-whisper-tiny + test-text-v1"

        delivery = db.scalar(select(WebhookDelivery).where(WebhookDelivery.request_id == request_id))
        assert delivery is not None
        assert delivery.event_type == "moderation.completed"
        assert delivery.payload["status"] == "approved"
        assert delivery.payload["is_flagged"] is False
        assert delivery.payload["model"] == "test-whisper-tiny + test-text-v1"
        assert "transcript" not in delivery.payload
        assert "audio" not in delivery.payload

    # 4. Duplicate message idempotency: duplicate delivery does not re-run inference
    asyncio.run(moderation_worker.process_message(Message(request_id)))
    assert mock_stt.calls == 1
    assert mock_text.calls == 1

    # 5. Verify status retrieval endpoint
    with TestClient(app) as client:
        status_resp = client.get(f"/api/v1/moderate/{request_id}")
        assert status_resp.status_code == 200
        body = status_resp.json()
        assert body["status"] == "approved"
        assert body["is_flagged"] is False
        assert body["scores"] == {"toxic": 0.01, "threat": 0.005}
        assert body["model"] == "test-whisper-tiny + test-text-v1"


def test_audio_flagged_moderation(audio_pipeline_env, monkeypatch):
    factory, storage = audio_pipeline_env
    tenant_id = uuid4()
    tenant = Tenant(id=tenant_id, name="flag-tenant", slug="flag-tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)

    wav_bytes = _make_test_wav_bytes(duration_seconds=1.0)
    object_key = f"{tenant_id}/{uuid4()}.wav"
    storage.put(object_key, io.BytesIO(wav_bytes))

    with factory.begin() as db:
        asset = ModerationAsset(
            tenant_id=tenant_id,
            storage_provider="local",
            object_key=object_key,
            mime_type="audio/wav",
            size_bytes=len(wav_bytes),
        )
        db.add(asset)
        db.flush()
        req = ModerationRequest(
            tenant_id=tenant_id,
            content_type="audio",
            asset_id=asset.id,
            status="pending",
        )
        db.add(req)
        db.flush()
        request_id = req.id

    class FlaggedSTT(SpeechToTextService):
        model_name = "flagged-whisper"
        def transcribe(self, audio, duration_seconds=None):
            return {"text": "I will attack you tomorrow", "language": "en", "duration_seconds": 1.0}

    class FlaggedText(TextInferenceService):
        model_name = "flagged-text-v1"
        def moderate(self, content: str) -> dict:
            return {
                "is_flagged": True,
                "categories": ["threat"],
                "scores": {"threat": 0.96, "toxic": 0.89},
                "model": self.model_name,
            }

    handler = AudioModerationHandler(
        transcription_service=FlaggedSTT(),
        text_service=FlaggedText(),
    )
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    asyncio.run(moderation_worker.process_message(Message(request_id)))

    with factory() as db:
        req = db.get(ModerationRequest, request_id)
        assert req.status == "flagged"

        res = db.scalar(select(ModerationResult).where(ModerationResult.request_id == request_id))
        assert res.is_flagged is True
        assert res.category == ["threat"]
        assert res.score["threat"] == 0.96
        assert res.model == "flagged-whisper + flagged-text-v1"


def test_audio_empty_speech_pipeline(audio_pipeline_env, monkeypatch):
    factory, storage = audio_pipeline_env
    tenant_id = uuid4()
    tenant = Tenant(id=tenant_id, name="empty-tenant", slug="empty-tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)

    wav_bytes = _make_test_wav_bytes(duration_seconds=1.0)
    object_key = f"{tenant_id}/{uuid4()}.wav"
    storage.put(object_key, io.BytesIO(wav_bytes))

    with factory.begin() as db:
        asset = ModerationAsset(
            tenant_id=tenant_id,
            storage_provider="local",
            object_key=object_key,
            mime_type="audio/wav",
            size_bytes=len(wav_bytes),
        )
        db.add(asset)
        db.flush()
        req = ModerationRequest(
            tenant_id=tenant_id,
            content_type="audio",
            asset_id=asset.id,
            status="pending",
        )
        db.add(req)
        db.flush()
        request_id = req.id

    class SilentSTT(SpeechToTextService):
        model_name = "silent-whisper"
        def transcribe(self, audio, duration_seconds=None):
            return {"text": "", "language": None, "duration_seconds": 1.0}

    handler = AudioModerationHandler(transcription_service=SilentSTT())
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    asyncio.run(moderation_worker.process_message(Message(request_id)))

    with factory() as db:
        req = db.get(ModerationRequest, request_id)
        assert req.status == "approved"

        res = db.scalar(select(ModerationResult).where(ModerationResult.request_id == request_id))
        assert res.is_flagged is False
        assert res.category == []
        assert res.score["toxic"] == 0.0


def test_audio_validation_failure_is_terminal(audio_pipeline_env, monkeypatch):
    factory, storage = audio_pipeline_env
    tenant_id = uuid4()
    tenant = Tenant(id=tenant_id, name="corrupt-tenant", slug="corrupt-tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)

    # Store corrupt garbage
    corrupt_bytes = b"NOT_VALID_AUDIO_DATA"
    object_key = f"{tenant_id}/{uuid4()}.wav"
    storage.put(object_key, io.BytesIO(corrupt_bytes))

    with factory.begin() as db:
        asset = ModerationAsset(
            tenant_id=tenant_id,
            storage_provider="local",
            object_key=object_key,
            mime_type="audio/wav",
            size_bytes=len(corrupt_bytes),
        )
        db.add(asset)
        db.flush()
        req = ModerationRequest(
            tenant_id=tenant_id,
            content_type="audio",
            asset_id=asset.id,
            status="pending",
        )
        db.add(req)
        db.flush()
        request_id = req.id

    handler = AudioModerationHandler()
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    # Worker executes and terminates without raising RetriableProcessingError
    asyncio.run(moderation_worker.process_message(Message(request_id)))

    with factory() as db:
        req = db.get(ModerationRequest, request_id)
        assert req.status == "failed"
        assert req.retry_count == 1
        assert "AudioCorruptError" in req.last_error or "Cannot identify or decode audio" in req.last_error

        # No moderation result persisted
        res = db.scalar(select(ModerationResult).where(ModerationResult.request_id == request_id))
        assert res is None


def test_audio_transient_failure_retries_and_recovers(audio_pipeline_env, monkeypatch):
    factory, storage = audio_pipeline_env
    tenant_id = uuid4()
    tenant = Tenant(id=tenant_id, name="flaky-tenant", slug="flaky-tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)

    wav_bytes = _make_test_wav_bytes(duration_seconds=1.0)
    object_key = f"{tenant_id}/{uuid4()}.wav"
    storage.put(object_key, io.BytesIO(wav_bytes))

    with factory.begin() as db:
        asset = ModerationAsset(
            tenant_id=tenant_id,
            storage_provider="local",
            object_key=object_key,
            mime_type="audio/wav",
            size_bytes=len(wav_bytes),
        )
        db.add(asset)
        db.flush()
        req = ModerationRequest(
            tenant_id=tenant_id,
            content_type="audio",
            asset_id=asset.id,
            status="pending",
        )
        db.add(req)
        db.flush()
        request_id = req.id

    class FlakySTT(SpeechToTextService):
        attempts = 0
        model_name = "flaky-whisper"

        def transcribe(self, audio, duration_seconds=None):
            self.attempts += 1
            if self.attempts < 3:
                raise ConnectionResetError("Temporary GPU/model connectivity issue")
            return {"text": "Recovered text", "language": "en", "duration_seconds": 1.0}

    class FlakyText(TextInferenceService):
        model_name = "flaky-text-v1"
        def moderate(self, content: str) -> dict:
            return {"is_flagged": False, "categories": [], "scores": {}, "model": self.model_name}

    flaky_stt = FlakySTT()
    handler = AudioModerationHandler(
        transcription_service=flaky_stt,
        text_service=FlakyText(),
    )
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    # Attempt 1: fails retriable
    with pytest.raises(moderation_worker.RetriableProcessingError):
        asyncio.run(moderation_worker.process_message(Message(request_id)))

    with factory() as db:
        req = db.get(ModerationRequest, request_id)
        assert req.status == "pending"
        assert req.retry_count == 1

    # Attempt 2: fails retriable
    with pytest.raises(moderation_worker.RetriableProcessingError):
        asyncio.run(moderation_worker.process_message(Message(request_id)))

    with factory() as db:
        req = db.get(ModerationRequest, request_id)
        assert req.status == "pending"
        assert req.retry_count == 2

    # Attempt 3: succeeds
    asyncio.run(moderation_worker.process_message(Message(request_id)))

    with factory() as db:
        req = db.get(ModerationRequest, request_id)
        assert req.status == "approved"
        assert req.retry_count == 2

        res = db.scalar(select(ModerationResult).where(ModerationResult.request_id == request_id))
        assert res is not None
        assert res.is_flagged is False


def test_audio_data_confidentiality_and_no_transcript_in_logs(audio_pipeline_env, monkeypatch, caplog):
    factory, storage = audio_pipeline_env
    tenant_id = uuid4()
    tenant = Tenant(id=tenant_id, name="privacy-tenant", slug="privacy-tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)

    secret_phrase = "TOP_SECRET_SPEECH_DATA_CONFIDENTIAL_12345"
    wav_bytes = _make_test_wav_bytes(duration_seconds=1.0)
    object_key = f"{tenant_id}/{uuid4()}.wav"
    storage.put(object_key, io.BytesIO(wav_bytes))

    with factory.begin() as db:
        asset = ModerationAsset(
            tenant_id=tenant_id,
            storage_provider="local",
            object_key=object_key,
            mime_type="audio/wav",
            size_bytes=len(wav_bytes),
        )
        db.add(asset)
        db.flush()
        req = ModerationRequest(
            tenant_id=tenant_id,
            content_type="audio",
            asset_id=asset.id,
            status="pending",
        )
        db.add(req)
        db.flush()
        request_id = req.id

    class PrivateSTT(SpeechToTextService):
        model_name = "private-whisper"
        def transcribe(self, audio, duration_seconds=None):
            return {"text": secret_phrase, "language": "en", "duration_seconds": 1.0}

    class PrivateText(TextInferenceService):
        model_name = "private-text-v1"
        def moderate(self, content: str) -> dict:
            return {"is_flagged": False, "categories": [], "scores": {}, "model": self.model_name}

    handler = AudioModerationHandler(
        transcription_service=PrivateSTT(),
        text_service=PrivateText(),
    )
    monkeypatch.setattr(moderation_worker, "get_moderation_handler", lambda ct: handler)

    with caplog.at_level(logging.INFO):
        asyncio.run(moderation_worker.process_message(Message(request_id)))

    # Verify transcript and raw bytes are NOT present in application logs
    all_logs = caplog.text
    assert secret_phrase not in all_logs
    assert "TOP_SECRET" not in all_logs
    assert str(wav_bytes[:20]) not in all_logs

    # Verify DB has no transcript
    with factory() as db:
        req = db.get(ModerationRequest, request_id)
        assert req.content is None
        res = db.scalar(select(ModerationResult).where(ModerationResult.request_id == request_id))
        assert res is not None
        # Result columns do not contain the raw transcript
        assert not hasattr(res, "transcript")


def test_audio_upload_oversized_rejected(audio_pipeline_env, monkeypatch):
    factory, storage = audio_pipeline_env
    monkeypatch.setattr(settings, "AUDIO_MAX_SIZE_BYTES", 500)

    tenant = Tenant(id=uuid4(), name="size-tenant", slug="size-tenant", status="active")
    with factory.begin() as db:
        db.add(tenant)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/moderate")

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_tenant] = lambda: tenant

    # 1000 bytes > 500 bytes limit
    wav_bytes = _make_test_wav_bytes(duration_seconds=1.0)
    assert len(wav_bytes) > 500

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/moderate/media",
            files={"file": ("large.wav", wav_bytes, "audio/wav")},
        )
        assert response.status_code == 413
        assert "exceeds the configured size limit" in response.json()["detail"]
