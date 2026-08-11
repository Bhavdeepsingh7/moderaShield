import asyncio
import json

from sqlalchemy import select

from app.db.session import SessionLocal
import app.messaging.kafka as kafka
from app.models.outbox import OutboxEvent
from app.messaging.topics import MODERATION_REQUESTS_TOPIC

async def publish_pending_events():
    db = SessionLocal()

    try:
        events = db.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.status == "pending")
            .order_by(OutboxEvent.created_at)
            .limit(100)
        ).all()

        for event in events:
            if kafka.kafka_producer is None:
                raise RuntimeError("Kafka producer is not initialized")

            await kafka.kafka_producer.send_and_wait(
                MODERATION_REQUESTS_TOPIC,
                key=str(event.aggregate_id).encode("utf-8"),
                value=event.payload.encode("utf-8"),
            )

            event.status = "published"

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


async def main():
    await kafka.start_kafka()

    try:
        while True:
            try:
                await publish_pending_events()
            except Exception as e:
                print(f"Outbox publisher error: {e}")

            await asyncio.sleep(2)

    finally:
        await kafka.stop_kafka()

if __name__ == "__main__":
    asyncio.run(main())