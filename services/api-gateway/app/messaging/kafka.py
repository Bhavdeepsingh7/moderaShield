import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError
import json

from app.core.config import settings
from app.messaging.events import ModerationRequestEvent
from app.messaging.topics import MODERATION_REQUESTS_TOPIC


logger = logging.getLogger(__name__)
kafka_producer: AIOKafkaProducer | None = None


def kafka_connection_config() -> dict:
    config = {
        "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        "security_protocol": settings.KAFKA_SECURITY_PROTOCOL,
    }

    if settings.KAFKA_SECURITY_PROTOCOL in {"SASL_SSL", "SASL_PLAINTEXT"}:
        config.update({
            "sasl_mechanism": settings.KAFKA_SASL_MECHANISM,
            "sasl_plain_username": settings.KAFKA_SASL_USERNAME,
            "sasl_plain_password": settings.KAFKA_SASL_PASSWORD,
        })

    return config



async def ensure_moderation_requests_topic() -> None:
    """Create the moderation request topic when it is not already present."""
    admin = AIOKafkaAdminClient(
        **kafka_connection_config()
    )

    await admin.start()
    try:
        await admin.create_topics(
            [
                NewTopic(
                    MODERATION_REQUESTS_TOPIC,
                    num_partitions=3,
                    replication_factor=1,
                )
            ]
        )
        logger.info("Created Kafka topic %s", MODERATION_REQUESTS_TOPIC)
    except TopicAlreadyExistsError:
        logger.debug("Kafka topic %s already exists", MODERATION_REQUESTS_TOPIC)
    finally:
        await admin.close()


async def start_kafka() -> None:
    global kafka_producer

    await ensure_moderation_requests_topic()

    kafka_producer = AIOKafkaProducer(
        **kafka_connection_config()
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


async def create_consumer(topic: str, group_id: str, **consumer_options):
    if topic == MODERATION_REQUESTS_TOPIC:
        await ensure_moderation_requests_topic()

    consumer = AIOKafkaConsumer(
        topic,
        **kafka_connection_config(),
        group_id=group_id,
        auto_offset_reset ="earliest",
        enable_auto_commit=False,
        **consumer_options,
    )

    await consumer.start()

    return consumer


async def publish(topic: str, payload: dict) -> None:
    if kafka_producer is None:
        raise RuntimeError("Kafka producer is not initialized")

    await kafka_producer.send_and_wait(
        topic,
        value=json.dumps(payload).encode("utf-8"),
    )
