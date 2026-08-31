import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy import select
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.webhook import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)


async def process_delivery(db, delivery: WebhookDelivery, client: httpx.AsyncClient) -> None:
    webhook = db.scalar(select(Webhook).where(Webhook.id == delivery.webhook_id))
    if not webhook or not webhook.enabled:
        delivery.status = "failed"
        delivery.last_error = "Webhook not found or disabled"
        db.commit()
        return

    payload_bytes = json.dumps(delivery.payload).encode("utf-8")
    
    # Calculate HMAC-SHA256 signature
    signature = hmac.new(
        webhook.secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-ModeraShield-Event-ID": str(delivery.id),
        "X-ModeraShield-Signature": signature,
    }

    delivery.attempt_count += 1
    logger.info("Attempting webhook delivery %s (attempt %d)", delivery.id, delivery.attempt_count)

    try:
        response = await client.post(
            webhook.url,
            content=payload_bytes,
            headers=headers,
            timeout=settings.WEBHOOK_REQUEST_TIMEOUT_SECONDS,
        )
        
        if 200 <= response.status_code < 300:
            delivery.status = "delivered"
            delivery.delivered_at = datetime.now(timezone.utc)
            delivery.last_error = None
            logger.info("Successfully delivered webhook event %s", delivery.id)
        elif response.status_code >= 500:
            raise httpx.HTTPStatusError(
                f"Transient HTTP error: {response.status_code}",
                request=response.request,
                response=response
            )
        else:
            # 4xx is permanent failure
            delivery.status = "failed"
            delivery.last_error = f"Permanent HTTP error: {response.status_code}"
            logger.warning("Permanent webhook delivery failure %s: HTTP %d", delivery.id, response.status_code)
            
    except (httpx.RequestError, httpx.HTTPStatusError) as error:
        last_error = str(error)
        logger.warning("Retryable error delivering webhook %s: %s", delivery.id, last_error)
        
        if delivery.attempt_count >= settings.WEBHOOK_MAX_ATTEMPTS:
            delivery.status = "failed"
            delivery.last_error = f"Max attempts reached. Last error: {last_error}"
            logger.error("Webhook event %s failed permanently after %d attempts", delivery.id, delivery.attempt_count)
        else:
            # Bounded exponential backoff: base_seconds * 2^(attempt - 1)
            backoff = settings.WEBHOOK_BACKOFF_SECONDS * (2 ** (delivery.attempt_count - 1))
            delivery.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)
            delivery.last_error = last_error
            # status remains "pending"
            
    db.commit()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger.info("Starting webhook delivery worker...")

    async with httpx.AsyncClient() as client:
        while True:
            db = SessionLocal()
            try:
                now = datetime.now(timezone.utc)
                stmt = (
                    select(WebhookDelivery)
                    .where(
                        WebhookDelivery.status == "pending",
                        WebhookDelivery.next_attempt_at <= now
                    )
                    .order_by(WebhookDelivery.created_at.asc())
                )
                deliveries = db.scalars(stmt).all()

                for delivery in deliveries:
                    await process_delivery(db, delivery, client)
                    
            except Exception as e:
                logger.exception("Unexpected error in webhook worker loop: %s", e)
            finally:
                db.close()

            await asyncio.sleep(settings.WEBHOOK_WORKER_POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
