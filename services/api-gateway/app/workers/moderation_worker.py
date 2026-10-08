"""Kafka consumer for the text moderation pipeline."""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from aiokafka.errors import CommitFailedError

import app.messaging.kafka as kafka
from app.db.session import SessionLocal
from app.core.config import settings
from app.messaging.topics import MODERATION_REQUESTS_TOPIC
from app.models.moderation import ModerationRequest
from app.models.moderation_result import ModerationResult
from app.services.webhook_service import create_deliveries_for_request
from app.services.inference.registry import get_moderation_handler
from app.services.media.exceptions import NonRetriableProcessingError

logger = logging.getLogger(__name__)
MAX_RETRIES = 3


class RetriableProcessingError(Exception):
    """Signals that the Kafka offset must remain uncommitted."""


def _set_completed_status(request: ModerationRequest, result: ModerationResult) -> None:
    """The API exposes approved/flagged as the two completed outcomes."""
    request.status = "flagged" if result.is_flagged else "approved"


def _processing_claim_is_stale(request: ModerationRequest) -> bool:
    """Return whether a crashed worker's claim can safely be replaced."""
    if request.updated_at is None:
        return True
    updated_at = request.updated_at
    if updated_at.tzinfo is None:  # SQLite test databases return naive values.
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return updated_at <= datetime.now(timezone.utc) - timedelta(
        seconds=settings.MODERATION_PROCESSING_LEASE_SECONDS
    )


def _run_inference(request_id: UUID, content_type: str) -> dict:
    """Run synchronous inference in its own thread-owned DB session.

    This is intentionally separate from the claim transaction: no request row
    lock or transaction remains open while models/storage perform slow work.
    """
    db = SessionLocal()
    try:
        request = db.get(ModerationRequest, request_id)
        if request is None:
            raise RuntimeError("Moderation request disappeared during processing")
        # Do not retain even a read transaction while model execution runs.
        # Handlers that need an asset open and finish their own short DB work.
        db.expunge(request)
        db.rollback()
        return get_moderation_handler(content_type).handle(db, request)
    finally:
        db.close()


async def process_message(message) -> None:
    """Process one record; retryable failures deliberately leave it uncommitted."""
    try:
        request_id = UUID(json.loads(message.value.decode("utf-8"))["request_id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        # A malformed record cannot become valid on retry, so it is safe to ack.
        logger.error("Discarding malformed moderation record: %s", error)
        return

    db = SessionLocal()
    claim_token = uuid4()
    try:
        # The row lock serializes normal duplicate deliveries.  Looking for an
        # existing result before inference makes redelivery a cheap no-op.
        with db.begin():
            request = db.scalar(
                select(ModerationRequest)
                .where(ModerationRequest.id == request_id)
                .with_for_update()
            )
            if request is None:
                logger.warning("Moderation request %s does not exist", request_id)
                return
            existing = db.scalar(
                select(ModerationResult).where(ModerationResult.request_id == request_id)
            )
            if existing is not None:
                _set_completed_status(request, existing)
                request.processing_token = None
                create_deliveries_for_request(db, request, existing)
                return
            if request.status == "failed":
                request.processing_token = None
                create_deliveries_for_request(db, request, None)
                return

            # A current claim belongs to another delivery.  Do not run model
            # inference twice; leave this Kafka record uncommitted so it can
            # later observe that worker's terminal transaction.  An abandoned
            # claim is recoverable after its lease expires.
            if request.status == "processing" and not _processing_claim_is_stale(request):
                raise RetriableProcessingError(
                    f"Moderation request {request_id} is already processing"
                )

            request.status = "processing"
            request.processing_token = claim_token
            content_type = request.content_type

        try:
            # Transformer inference is synchronous and can block for long
            # enough to starve aiokafka heartbeats during cold model loading.
            # Run it off the event loop while retaining the same model call.
            result = await asyncio.to_thread(_run_inference, request_id, content_type)
        except Exception as error:
            if db.in_transaction():
                db.rollback()
            with db.begin():
                request = db.scalar(
                    select(ModerationRequest)
                    .where(ModerationRequest.id == request_id)
                    .with_for_update()
                )
                if request is None:
                    return
                # Another delivery may have completed while inference ran.
                existing = db.scalar(
                    select(ModerationResult).where(ModerationResult.request_id == request_id)
                )
                if existing is not None:
                    _set_completed_status(request, existing)
                    request.processing_token = None
                    create_deliveries_for_request(db, request, existing)
                    return

                # A reclaimed delivery owns the request now.  Its outcome is
                # authoritative, so this stale worker must not mutate retry
                # metadata or overwrite a terminal status.
                if request.processing_token != claim_token:
                    raise RetriableProcessingError(
                        f"Moderation request {request_id} processing claim was replaced"
                    )

                request.retry_count += 1
                # Some built-in errors (notably MemoryError) stringify to an
                # empty string. Persist a useful deterministic diagnostic.
                request.last_error = str(error) or error.__class__.__name__
                is_terminal = (
                    isinstance(
                        error,
                        (
                            NonRetriableProcessingError,
                            FileNotFoundError,
                            PermissionError,
                            ValueError,
                        ),
                    )
                    or request.retry_count >= MAX_RETRIES
                )
                if is_terminal:
                    request.status = "failed"
                    request.processing_token = None
                    logger.warning(
                        "Moderation request %s failed permanently: %s",
                        request_id,
                        request.last_error,
                    )
                    create_deliveries_for_request(db, request, None)
                    return
                request.status = "pending"
                request.processing_token = None
                retry_count = request.retry_count

            raise RetriableProcessingError(
                f"Moderation request {request_id} failed attempt "
                f"{retry_count}/{MAX_RETRIES}"
            ) from error

        try:
            if db.in_transaction():
                db.rollback()
            # Result insertion and terminal status change succeed or fail together.
            with db.begin():
                request = db.scalar(
                    select(ModerationRequest)
                    .where(ModerationRequest.id == request_id)
                    .with_for_update()
                )
                if request is None:
                    return
                existing = db.scalar(
                    select(ModerationResult).where(ModerationResult.request_id == request_id)
                )
                if existing is not None:
                    _set_completed_status(request, existing)
                    request.processing_token = None
                    create_deliveries_for_request(db, request, existing)
                    return
                if request.status == "failed":
                    request.processing_token = None
                    create_deliveries_for_request(db, request, None)
                    return
                if request.processing_token != claim_token:
                    raise RetriableProcessingError(
                        f"Moderation request {request_id} processing claim was replaced"
                    )

                moderation_result = ModerationResult(
                    request_id=request_id,
                    is_flagged=result["is_flagged"],
                    category=result["categories"],
                    score=result["scores"],
                    model=result["model"],
                )
                
                db.add(moderation_result)
                _set_completed_status(request, moderation_result)
                request.processing_token = None
                create_deliveries_for_request(db, request, moderation_result)
        except IntegrityError:
            # The unique request_id index is the final guard for writers that
            # do not participate in the request-row lock.
            db.rollback()
            with db.begin():
                request = db.scalar(
                    select(ModerationRequest)
                    .where(ModerationRequest.id == request_id)
                    .with_for_update()
                )
                existing = db.scalar(
                    select(ModerationResult).where(ModerationResult.request_id == request_id)
                )
                if request is not None and existing is not None:
                    _set_completed_status(request, existing)
                    request.processing_token = None
                    create_deliveries_for_request(db, request, existing)
                    return
            raise
    finally:
        db.close()


async def main() -> None:
    consumer = await kafka.create_consumer(
        MODERATION_REQUESTS_TOPIC,
        group_id="moderation-worker",
        # Model initialization can take longer than Kafka's default poll
        # interval on a cold worker. Process one record at a time and retain
        # manual commits after the database transaction.
        max_poll_interval_ms=900_000,
        max_poll_records=1,
    )
    try:
        async for message in consumer:
            try:
                await process_message(message)
            except RetriableProcessingError as error:
                # Keep the offset uncommitted; Kafka will redeliver it.
                logger.warning("Leaving message uncommitted for retry: %s", error)
                continue
            except Exception:
                logger.exception("Unexpected worker failure; leaving message uncommitted")
                continue
            try:
                await consumer.commit()
            except CommitFailedError:
                # The record remains uncommitted and will be redelivered after
                # the consumer rejoins; do not terminate this worker.
                logger.warning("Kafka commit failed after processing; record remains uncommitted", exc_info=True)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())
