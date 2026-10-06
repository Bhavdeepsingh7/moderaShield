import asyncio
from datetime import datetime, timedelta, timezone
import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import SessionLocal
import app.messaging.kafka as kafka
from app.models.outbox import OutboxEvent
from app.messaging.topics import MODERATION_REQUESTS_TOPIC

logger = logging.getLogger(__name__)


def _current_timestamp() -> datetime:
    """Returns current UTC timestamp without tzinfo for DB dialect compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def claim_pending_events(db_factory: sessionmaker, batch_size: int = 100) -> list[dict]:
    """
    Claim up to `batch_size` pending outbox events using short DB transaction.
    Uses FOR UPDATE SKIP LOCKED on PostgreSQL to prevent concurrent claims.
    """
    db = db_factory()
    try:
        with db.begin():
            stmt = (
                select(OutboxEvent)
                .where(OutboxEvent.status == "pending")
                .order_by(OutboxEvent.created_at, OutboxEvent.id)
                .limit(batch_size)
            )

            if db.bind and db.bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)
            elif db.bind and db.bind.dialect.name != "sqlite":
                stmt = stmt.with_for_update()

            events = db.scalars(stmt).all()
            if not events:
                return []

            now = _current_timestamp()
            claimed_items = []
            for event in events:
                claim_token = uuid.uuid4()
                event.status = "processing"
                event.claimed_at = now
                event.claim_token = claim_token
                event.attempts += 1

                claimed_items.append({
                    "id": event.id,
                    "claim_token": claim_token,
                    "aggregate_id": event.aggregate_id,
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "attempts": event.attempts,
                })

            db.flush()
            for item in claimed_items:
                logger.info(
                    "Outbox event claimed: event_id=%s, aggregate_id=%s, event_type=%s, attempt=%d",
                    item["id"],
                    item["aggregate_id"],
                    item["event_type"],
                    item["attempts"],
                )
            return claimed_items
    finally:
        db.close()


def recover_stale_claims(db_factory: sessionmaker, timeout_seconds: int = 60) -> int:
    """
    Find events stuck in 'processing' longer than timeout_seconds and reset to 'pending'.
    """
    db = db_factory()
    try:
        cutoff = _current_timestamp() - timedelta(seconds=timeout_seconds)
        with db.begin():
            stmt = (
                select(OutboxEvent)
                .where(
                    OutboxEvent.status == "processing",
                    OutboxEvent.claimed_at < cutoff,
                )
            )

            if db.bind and db.bind.dialect.name == "postgresql":
                stmt = stmt.with_for_update(skip_locked=True)
            elif db.bind and db.bind.dialect.name != "sqlite":
                stmt = stmt.with_for_update()

            stale_events = db.scalars(stmt).all()
            count = len(stale_events)
            for event in stale_events:
                logger.warning(
                    "Recovering stale outbox event: event_id=%s, aggregate_id=%s, event_type=%s, attempt=%d, claimed_at=%s",
                    event.id,
                    event.aggregate_id,
                    event.event_type,
                    event.attempts,
                    event.claimed_at,
                )
                event.status = "pending"
                event.claimed_at = None
                event.claim_token = None

            return count
    finally:
        db.close()


def _mark_event_published(
    db_factory: sessionmaker, event_id: uuid.UUID, claim_token: uuid.UUID
) -> bool:
    db = db_factory()
    try:
        with db.begin():
            result = db.execute(
                update(OutboxEvent)
                .where(
                    OutboxEvent.id == event_id,
                    OutboxEvent.status == "processing",
                    OutboxEvent.claim_token == claim_token,
                )
                .values(
                    status="published",
                    published_at=_current_timestamp(),
                    claimed_at=None,
                    claim_token=None,
                    last_error=None,
                )
            )
            return result.rowcount == 1
    finally:
        db.close()


def _mark_event_failed_retryable(
    db_factory: sessionmaker,
    event_id: uuid.UUID,
    claim_token: uuid.UUID,
    error_msg: str,
) -> bool:
    db = db_factory()
    try:
        with db.begin():
            result = db.execute(
                update(OutboxEvent)
                .where(
                    OutboxEvent.id == event_id,
                    OutboxEvent.status == "processing",
                    OutboxEvent.claim_token == claim_token,
                )
                .values(
                    status="pending",
                    claimed_at=None,
                    claim_token=None,
                    last_error=error_msg,
                )
            )
            return result.rowcount == 1
    finally:
        db.close()


async def publish_single_event(event_item: dict, db_factory: sessionmaker) -> bool:
    """
    Publishes one claimed event to Kafka outside the DB transaction.
    Updates DB individually upon success or failure.
    """
    event_id = event_item["id"]
    claim_token = event_item["claim_token"]
    aggregate_id = event_item["aggregate_id"]
    event_type = event_item["event_type"]
    payload = event_item["payload"]
    attempts = event_item["attempts"]

    if kafka.kafka_producer is None:
        error_msg = "Kafka producer is not initialized"
        logger.error(
            "Outbox event publish failed: event_id=%s, aggregate_id=%s, event_type=%s, attempt=%d, error=%s",
            event_id,
            aggregate_id,
            event_type,
            attempts,
            error_msg,
        )
        _mark_event_failed_retryable(db_factory, event_id, claim_token, error_msg)
        return False

    try:
        # Publish to Kafka
        await kafka.kafka_producer.send_and_wait(
            MODERATION_REQUESTS_TOPIC,
            key=str(aggregate_id).encode("utf-8"),
            value=payload.encode("utf-8"),
        )

        if not _mark_event_published(db_factory, event_id, claim_token):
            # A stale-claim recovery may have handed this row to another
            # publisher while Kafka was in flight.  Do not overwrite that
            # newer ownership; the acknowledged Kafka write is still a valid
            # at-least-once delivery.
            logger.warning(
                "Outbox publish acknowledged but claim ownership changed: event_id=%s, aggregate_id=%s, event_type=%s, attempt=%d",
                event_id,
                aggregate_id,
                event_type,
                attempts,
            )
            return False
        logger.info(
            "Outbox event published successfully: event_id=%s, aggregate_id=%s, event_type=%s, attempt=%d",
            event_id,
            aggregate_id,
            event_type,
            attempts,
        )
        return True

    except Exception as exc:
        sanitized_err = str(exc)[:500] or exc.__class__.__name__
        logger.error(
            "Outbox event publish failed: event_id=%s, aggregate_id=%s, event_type=%s, attempt=%d, error=%s",
            event_id,
            aggregate_id,
            event_type,
            attempts,
            sanitized_err,
        )
        if not _mark_event_failed_retryable(db_factory, event_id, claim_token, sanitized_err):
            logger.warning(
                "Outbox publish failure could not reset changed claim: event_id=%s, aggregate_id=%s, event_type=%s, attempt=%d",
                event_id,
                aggregate_id,
                event_type,
                attempts,
            )
        return False


async def publish_pending_events(db_factory: sessionmaker = SessionLocal) -> int:
    """
    Main polling step:
    1. Recovers stale claims.
    2. Claims N pending events in a short DB transaction.
    3. Publishes events to Kafka individually outside DB locks.
    """
    recover_stale_claims(db_factory, timeout_seconds=settings.OUTBOX_CLAIM_TIMEOUT_SECONDS)

    claimed_events = claim_pending_events(
        db_factory,
        batch_size=settings.OUTBOX_CLAIM_BATCH_SIZE,
    )

    if not claimed_events:
        return 0

    published_count = 0
    for item in claimed_events:
        success = await publish_single_event(item, db_factory)
        if success:
            published_count += 1

    return published_count


async def main() -> None:
    await kafka.start_kafka()
    logger.info("Outbox publisher worker started")

    try:
        while True:
            try:
                await publish_pending_events()
            except Exception as e:
                logger.exception("Unexpected outbox publisher loop error: %s", e)

            await asyncio.sleep(settings.OUTBOX_PUBLISHER_POLL_SECONDS)

    finally:
        await kafka.stop_kafka()
        logger.info("Outbox publisher worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
