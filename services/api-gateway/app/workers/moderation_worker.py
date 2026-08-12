import asyncio
import json

from sqlalchemy import select

import app.messaging.kafka as kafka
from app.db.session import SessionLocal
from app.models.moderation import ModerationRequest
from app.messaging.topics import MODERATION_REQUESTS_TOPIC
from app.moderation.engine import moderation_engine
from app.models.moderation_result import ModerationResult


async def process_message(message):
    data = json.loads(message.value.decode("utf-8"))

    request_id = data["request_id"]

    db = SessionLocal()

    moderation_request = None
    MAX_RETRIES = 3

    try:
        moderation_request = db.scalar(
            select(ModerationRequest).where(
                ModerationRequest.id == request_id
            )
        )

        if moderation_request is None:
            print(f"Request {request_id} not found")
            return 

        if moderation_request.status in {"approved", "flagged"}:
            print(f"Request {request_id} already processed")
            return 

        moderation_request.status = "processing"
        db.commit()

        print(f"Processing moderation request: {request_id}")

        existing_result = db.scalar(
            select(ModerationResult).where(
                ModerationResult.request_id == moderation_request.id
            )
        )

        if existing_result is not None:
            print(f"Request {request_id} already has a moderation result")

            if moderation_request.status not in ("approved", "flagged"):
                moderation_request.status =(
                    "flagged"
                    if existing_result.is_flagged
                    else "approved"
                )

                db.commit()

            return 

        content = moderation_request.content

        if content == "crash":
            raise Exception("Simulated moderation failure")

        result = moderation_engine.moderate(content)

        moderation_result = ModerationResult(
            request_id = moderation_request.id,
            is_flagged = result.is_flagged,
            category=result.category,
            score =result.score,
            model="rule-based-v1",
        )

        db.add(moderation_result)

        if result.is_flagged:
            moderation_request.status = "flagged"
        else:
            moderation_request.status = "approved"

        db.commit()

        print(
            f"Request {request_id} completed "
            f"result={moderation_request.status} "
            f"category={result.category}"
            )

    except Exception as e:
        db.rollback()

        if moderation_request is not None:
            try:
                moderation_request.retry_count += 1

                moderation_request.last_error = str(e)

                if moderation_request.retry_count >= MAX_RETRIES:
                    moderation_request.status = "failed"
                else:
                    moderation_request.status = "pending"

                db.commit()

            except Exception:
                db.rollback()

        print(
            f"Failed to process request {request_id}: {e}"
        )

        raise

    finally:
        db.close()


async def main():
    consumer = await kafka.create_consumer(
        MODERATION_REQUESTS_TOPIC,
        group_id="moderation-worker",
    )

    try:
        async for message in consumer:
            try:
                await process_message(message)

                await consumer.commit()

            except Exception as e:
                print(f"Error processing message: {e}")

    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())