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

        print(f"Processing moderation request: {request_id}")

        content = moderation_request.content

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

    except Exception:
        db.rollback()
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