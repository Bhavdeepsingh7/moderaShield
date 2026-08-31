"""Kafka consumer for the text moderation pipeline."""

import asyncio
import json
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from aiokafka.errors import CommitFailedError

import app.messaging.kafka as kafka
from app.db.session import SessionLocal
from app.messaging.topics import MODERATION_REQUESTS_TOPIC
from app.models.moderation import ModerationRequest
from app.models.moderation_result import ModerationResult
from app.services.webhook_service import create_deliveries_for_request
from app.services.inference.registry import get_inference_service

logger = logging.getLogger(__name__)
MAX_RETRIES = 3


class RetriableProcessingError(Exception):
    """Signals that the Kafka offset must remain uncommitted."""


def _set_completed_status(request: ModerationRequest, result: ModerationResult) -> None:
    request.status = "flagged" if result.is_flagged else "approved"


async def process_message(message) -> None:
    """Process one record; retryable failures deliberately leave it uncommitted."""
    try:
        request_id = UUID(json.loads(message.value.decode("utf-8"))["request_id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        # A malformed record cannot become valid on retry, so it is safe to ack.
        logger.error("Discarding malformed moderation record: %s", error)
        return

    db = SessionLocal()
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
                create_deliveries_for_request(db, request, existing)
                return
            if request.status == "failed":
                create_deliveries_for_request(db, request, None)
                return

            request.status = "processing"
            content_type = request.content_type
            content = request.content

        try:
            # Transformer inference is synchronous and can block for long
            # enough to starve aiokafka heartbeats during cold model loading.
            # Run it off the event loop while retaining the same model call.
            inference_service = get_inference_service(content_type)

            result = await asyncio.to_thread(inference_service.moderate, content,)
        except Exception as error:
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
                    create_deliveries_for_request(db, request, existing)
                    return

                request.retry_count += 1
                # Some built-in errors (notably MemoryError) stringify to an
                # empty string. Persist a useful deterministic diagnostic.
                request.last_error = str(error) or error.__class__.__name__
                if request.retry_count >= MAX_RETRIES:
                    request.status = "failed"
                    logger.exception("Moderation request %s failed permanently", request_id)
                    create_deliveries_for_request(db, request, None)
                    return
                request.status = "pending"
                retry_count = request.retry_count

            raise RetriableProcessingError(
                f"Moderation request {request_id} failed attempt "
                f"{retry_count}/{MAX_RETRIES}"
            ) from error

        try:
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
                    create_deliveries_for_request(db, request, existing)
                    return
                if request.status == "failed":
                    create_deliveries_for_request(db, request, None)
                    return

                moderation_result = ModerationResult(
                    request_id=request_id,
                    is_flagged=result["is_flagged"],
                    category=result["categories"],
                    score=result["scores"],
                    model=result["model"],
                )
                
                db.add(moderation_result)
                _set_completed_status(request, moderation_result)
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
