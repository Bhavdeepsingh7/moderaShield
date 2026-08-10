from aiokafka import AIOKafkaProducer
import json
from app.core.config import settings
from app.messaging.events import ModerationRequestEvent
from app.messaging.topics import MODERATION_REQUESTS_TOPIC
kafka_producer: AIOKafkaProducer | None = None

async def start_kafka() -> None:
    global kafka_producer

    kafka_producer = AIOKafkaProducer(
        bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS,
    )

    await kafka_producer.start()


async def stop_kafka() -> None:
    global kafka_producer

    if kafka_producer is not None:
        await kafka_producer.stop()
        kafka_producer = None


async def publish_moderation_request(
        event: ModerationRequestEvent,
) -> None:

    if kafka_producer is None:
        raise RuntimeError("Kafka producer is not initialized")

    value = json.dumps(
        event.model_dump(mode = "json")
    ).encode("utf-8")

    key = str(event.request_id).encode("utf-8")

    await kafka_producer.send_and_wait(
        MODERATION_REQUESTS_TOPIC,
        key=key,
        value=value,
    )
    

    