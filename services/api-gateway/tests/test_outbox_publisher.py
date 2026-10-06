import asyncio
import os
import concurrent.futures
from datetime import datetime, timezone, timedelta
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401 - registers mapped tables
from app.models.outbox import OutboxEvent
from app.workers.outbox_publisher import (
    claim_pending_events,
    recover_stale_claims,
    publish_single_event,
    publish_pending_events,
)
import app.messaging.kafka as kafka


@pytest.fixture
def db_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    yield factory

    Base.metadata.drop_all(engine)


@pytest.fixture
def postgres_db_factory():
    """An isolated PostgreSQL database supplied by TEST_DATABASE_URL."""
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL locking tests")

    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


class MockKafkaProducer:
    def __init__(self, should_fail=False, fail_on_id=None):
        self.should_fail = should_fail
        self.fail_on_id = fail_on_id
        self.published_messages = []

    async def send_and_wait(self, topic, key, value):
        if self.should_fail:
            raise RuntimeError("Kafka broker unavailable")
        if self.fail_on_id and self.fail_on_id in value.decode("utf-8"):
            raise RuntimeError(f"Kafka error on event {self.fail_on_id}")
        self.published_messages.append({"topic": topic, "key": key, "value": value})


def test_postgresql_concurrency_no_double_claim(postgres_db_factory, monkeypatch):
    db_factory = postgres_db_factory
    with db_factory.begin() as db:
        event_id = uuid4()
        aggregate_id = uuid4()
        db.add(
            OutboxEvent(
                id=event_id,
                event_type="moderation.requested",
                aggregate_id=aggregate_id,
                payload=f'{{"event_id": "{event_id}", "request_id": "{aggregate_id}"}}',
                status="pending",
            )
        )

    def claim_once():
        return claim_pending_events(db_factory, batch_size=5)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        fut_a = executor.submit(claim_once)
        fut_b = executor.submit(claim_once)
        claimed_a = fut_a.result()
        claimed_b = fut_b.result()

    ids_a = {item["id"] for item in claimed_a}
    ids_b = {item["id"] for item in claimed_b}
    assert ids_a.isdisjoint(ids_b)
    assert ids_a | ids_b == {event_id}
    assert sorted([len(ids_a), len(ids_b)]) == [0, 1]

    claim = (claimed_a or claimed_b)[0]
    mock_producer = MockKafkaProducer()
    monkeypatch.setattr(kafka, "kafka_producer", mock_producer)
    assert asyncio.run(publish_single_event(claim, db_factory)) is True

    with db_factory() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        assert event.status == "published"
        assert event.published_at is not None


def test_stale_claim_recovery(db_factory):
    stale_id = uuid4()
    stale_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=120)

    with db_factory.begin() as db:
        db.add(
            OutboxEvent(
                id=stale_id,
                event_type="moderation.requested",
                aggregate_id=uuid4(),
                payload='{"test": 1}',
                status="processing",
                claimed_at=stale_time,
                attempts=1,
            )
        )

    recovered = recover_stale_claims(db_factory, timeout_seconds=60)
    assert recovered == 1

    with db_factory() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.id == stale_id))
        assert event.status == "pending"
        assert event.claimed_at is None

    # Verify event can be claimed again
    claimed = claim_pending_events(db_factory, batch_size=10)
    assert len(claimed) == 1
    assert claimed[0]["id"] == stale_id


def test_publish_success_path(db_factory, monkeypatch):
    event_id = uuid4()
    agg_id = uuid4()

    with db_factory.begin() as db:
        db.add(
            OutboxEvent(
                id=event_id,
                event_type="moderation.requested",
                aggregate_id=agg_id,
                payload=f'{{"event_id": "{event_id}", "request_id": "{agg_id}"}}',
                status="pending",
            )
        )

    claimed = claim_pending_events(db_factory, batch_size=10)
    assert len(claimed) == 1
    assert claimed[0]["attempts"] == 1

    mock_producer = MockKafkaProducer()
    monkeypatch.setattr(kafka, "kafka_producer", mock_producer)

    success = asyncio.run(publish_single_event(claimed[0], db_factory))
    assert success is True
    assert len(mock_producer.published_messages) == 1

    with db_factory() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        assert event.status == "published"
        assert event.published_at is not None
        assert event.claimed_at is None


def test_publish_failure_path(db_factory, monkeypatch):
    event_id = uuid4()

    with db_factory.begin() as db:
        db.add(
            OutboxEvent(
                id=event_id,
                event_type="moderation.requested",
                aggregate_id=uuid4(),
                payload='{"test": 1}',
                status="pending",
            )
        )

    claimed = claim_pending_events(db_factory, batch_size=10)
    assert len(claimed) == 1

    mock_producer = MockKafkaProducer(should_fail=True)
    monkeypatch.setattr(kafka, "kafka_producer", mock_producer)

    success = asyncio.run(publish_single_event(claimed[0], db_factory))
    assert success is False

    with db_factory() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        assert event.status == "pending"
        assert event.attempts == 1
        assert event.claimed_at is None
        assert "Kafka broker unavailable" in event.last_error


def test_partial_batch_failure(db_factory, monkeypatch):
    id_a = uuid4()
    id_b = uuid4()
    id_c = uuid4()

    with db_factory.begin() as db:
        db.add(OutboxEvent(id=id_a, event_type="test", aggregate_id=uuid4(), payload=f'{{"id": "{id_a}"}}', status="pending"))
        db.add(OutboxEvent(id=id_b, event_type="test", aggregate_id=uuid4(), payload=f'{{"id": "{id_b}"}}', status="pending"))
        db.add(OutboxEvent(id=id_c, event_type="test", aggregate_id=uuid4(), payload=f'{{"id": "{id_c}"}}', status="pending"))

    mock_producer = MockKafkaProducer(fail_on_id=str(id_c))
    monkeypatch.setattr(kafka, "kafka_producer", mock_producer)

    published_count = asyncio.run(publish_pending_events(db_factory))
    assert published_count == 2

    with db_factory() as db:
        ev_a = db.scalar(select(OutboxEvent).where(OutboxEvent.id == id_a))
        ev_b = db.scalar(select(OutboxEvent).where(OutboxEvent.id == id_b))
        ev_c = db.scalar(select(OutboxEvent).where(OutboxEvent.id == id_c))

        assert ev_a.status == "published"
        assert ev_b.status == "published"
        assert ev_c.status == "pending"
        assert "Kafka error on event" in ev_c.last_error


def test_crash_after_kafka_stale_recovery(db_factory, monkeypatch):
    event_id = uuid4()
    stale_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=120)

    with db_factory.begin() as db:
        db.add(
            OutboxEvent(
                id=event_id,
                event_type="moderation.requested",
                aggregate_id=uuid4(),
                payload='{"test": 1}',
                status="processing",
                claimed_at=stale_time,
                attempts=1,
            )
        )

    # Recover stale event after simulated crash post-Kafka publish
    recovered = recover_stale_claims(db_factory, timeout_seconds=60)
    assert recovered == 1

    with db_factory() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        assert event.status == "pending"

    # Event can now be published again (at-least-once redelivery)
    mock_producer = MockKafkaProducer()
    monkeypatch.setattr(kafka, "kafka_producer", mock_producer)

    published_count = asyncio.run(publish_pending_events(db_factory))
    assert published_count == 1

    with db_factory() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        assert event.status == "published"


def test_stale_publisher_cannot_finalize_a_reclaimed_event(db_factory, monkeypatch):
    """An old publisher must not overwrite a claim recovered by another one."""
    event_id = uuid4()
    with db_factory.begin() as db:
        db.add(
            OutboxEvent(
                id=event_id,
                event_type="moderation.requested",
                aggregate_id=uuid4(),
                payload='{"test": 1}',
                status="pending",
            )
        )

    first_claim = claim_pending_events(db_factory, batch_size=1)[0]
    with db_factory.begin() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        event.claimed_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=120)

    assert recover_stale_claims(db_factory, timeout_seconds=60) == 1
    second_claim = claim_pending_events(db_factory, batch_size=1)[0]
    assert second_claim["claim_token"] != first_claim["claim_token"]

    mock_producer = MockKafkaProducer()
    monkeypatch.setattr(kafka, "kafka_producer", mock_producer)
    assert asyncio.run(publish_single_event(first_claim, db_factory)) is False

    with db_factory() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        assert event.status == "processing"
        assert event.claim_token == second_claim["claim_token"]


def test_postgresql_stale_claim_recovery(postgres_db_factory):
    db_factory = postgres_db_factory
    event_id = uuid4()
    with db_factory.begin() as db:
        db.add(
            OutboxEvent(
                id=event_id,
                event_type="moderation.requested",
                aggregate_id=uuid4(),
                payload='{"test": 1}',
                status="processing",
                claimed_at=datetime.now(timezone.utc) - timedelta(seconds=120),
                claim_token=uuid4(),
                attempts=1,
            )
        )

    assert recover_stale_claims(db_factory, timeout_seconds=60) == 1
    claimed = claim_pending_events(db_factory, batch_size=1)
    assert [item["id"] for item in claimed] == [event_id]


def test_postgresql_claim_token_ownership(postgres_db_factory, monkeypatch):
    db_factory = postgres_db_factory
    event_id = uuid4()
    with db_factory.begin() as db:
        db.add(
            OutboxEvent(
                id=event_id,
                event_type="moderation.requested",
                aggregate_id=uuid4(),
                payload='{"test": 1}',
                status="pending",
            )
        )

    old_claim = claim_pending_events(db_factory, batch_size=1)[0]
    with db_factory.begin() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        event.claimed_at = datetime.now(timezone.utc) - timedelta(seconds=120)

    assert recover_stale_claims(db_factory, timeout_seconds=60) == 1
    new_claim = claim_pending_events(db_factory, batch_size=1)[0]
    mock_producer = MockKafkaProducer()
    monkeypatch.setattr(kafka, "kafka_producer", mock_producer)

    assert asyncio.run(publish_single_event(old_claim, db_factory)) is False
    with db_factory() as db:
        event = db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        assert event.status == "processing"
        assert event.claim_token == new_claim["claim_token"]
