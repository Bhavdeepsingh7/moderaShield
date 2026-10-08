"""At-least-once webhook worker; claims are durable and HTTP runs outside DB locks."""
import asyncio, hashlib, hmac, ipaddress, json, logging, socket, uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import httpx
from sqlalchemy import select, update
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.webhook import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)

def _now(): return datetime.now(timezone.utc).replace(tzinfo=None)
def _lock(stmt, db):
    return stmt.with_for_update(skip_locked=True) if db.bind and db.bind.dialect.name == "postgresql" else stmt

def claim_pending_deliveries(db_factory=SessionLocal, batch_size=None):
    db = db_factory()
    try:
        with db.begin():
            stmt = select(WebhookDelivery).where(WebhookDelivery.status == "pending", WebhookDelivery.next_attempt_at <= _now()).order_by(WebhookDelivery.created_at).limit(batch_size or settings.WEBHOOK_CLAIM_BATCH_SIZE)
            claimed = []
            for d in db.scalars(_lock(stmt, db)).all():
                token = uuid.uuid4(); d.status, d.claim_token, d.claimed_at = "processing", token, _now(); d.attempt_count += 1
                claimed.append({"id": d.id, "claim_token": token}); logger.info("webhook_delivery_claimed delivery_id=%s attempt=%d", d.id, d.attempt_count)
            return claimed
    finally: db.close()

def recover_stale_claims(db_factory=SessionLocal, timeout_seconds=None):
    db = db_factory()
    try:
        with db.begin():
            cutoff = _now() - timedelta(seconds=timeout_seconds or settings.WEBHOOK_CLAIM_TIMEOUT_SECONDS)
            rows = db.scalars(_lock(select(WebhookDelivery).where(WebhookDelivery.status == "processing", WebhookDelivery.claimed_at < cutoff), db)).all()
            for d in rows: d.status, d.claim_token, d.claimed_at = "pending", None, None; logger.warning("webhook_delivery_recovered delivery_id=%s", d.id)
            return len(rows)
    finally: db.close()

async def _validate_destination(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname: raise ValueError("Webhook URL is not HTTP(S)")
    try: records = await asyncio.get_running_loop().run_in_executor(None, lambda: socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM))
    except socket.gaierror as exc: raise httpx.ConnectError("Webhook hostname resolution failed") from exc
    if any(not ipaddress.ip_address(r[4][0]).is_global for r in records): raise ValueError("Webhook hostname resolves to a non-public address")

def _backoff(delivery_id, attempt, response=None):
    retry_after = getattr(response, "headers", {}).get("Retry-After") if response else None
    if retry_after:
        try: return max(0, min(int(retry_after), settings.WEBHOOK_MAX_BACKOFF_SECONDS))
        except ValueError: pass
    base = min(settings.WEBHOOK_MAX_BACKOFF_SECONDS, settings.WEBHOOK_BACKOFF_SECONDS * 2 ** (attempt - 1))
    return min(settings.WEBHOOK_MAX_BACKOFF_SECONDS, base + int(hashlib.sha256(f"{delivery_id}:{attempt}".encode()).hexdigest()[:8], 16) % max(1, min(base, settings.WEBHOOK_BACKOFF_SECONDS)))

async def _attempt(item, db_factory, client, validate_destination=True):
    db = db_factory()
    try:
        d = db.scalar(select(WebhookDelivery).where(WebhookDelivery.id == item["id"], WebhookDelivery.status == "processing", WebhookDelivery.claim_token == item["claim_token"]))
        if not d: return
        delivery_id, attempt_count = d.id, d.attempt_count
        wh = db.scalar(select(Webhook).where(Webhook.id == d.webhook_id, Webhook.tenant_id == d.tenant_id))
        outcome, error, response = "failed", "Webhook not found or disabled", None
        if wh and wh.enabled:
            payload = json.dumps(d.payload, separators=(",", ":")).encode()
            if len(payload) > settings.WEBHOOK_MAX_PAYLOAD_BYTES: error = "Webhook payload exceeds configured size limit"
            else:
                headers = {"Content-Type":"application/json", "X-ModeraShield-Event-ID":str(d.id), "X-ModeraShield-Event":d.event_type, "X-ModeraShield-Timestamp":str(int(datetime.now(timezone.utc).timestamp())), "X-ModeraShield-Signature":hmac.new(wh.secret.encode(), payload, hashlib.sha256).hexdigest()}
                db.rollback()
                try:
                    if validate_destination: await _validate_destination(wh.url)
                    response = await client.post(wh.url, content=payload, headers=headers, timeout=settings.WEBHOOK_REQUEST_TIMEOUT_SECONDS)
                    if 200 <= response.status_code < 300: outcome, error = "delivered", None
                    elif response.status_code in (408,429) or response.status_code >= 500: outcome, error = "retry", f"Retryable HTTP error: {response.status_code}"
                    else: outcome, error = "failed", f"Permanent HTTP error: {response.status_code}"
                except ValueError as exc: outcome, error = "failed", str(exc)
                except (httpx.RequestError, asyncio.TimeoutError) as exc: outcome, error = "retry", str(exc)[:500] or exc.__class__.__name__
        values = {"claim_token":None, "claimed_at":None, "last_error":error}
        if outcome == "delivered": values.update(status="delivered", delivered_at=_now()); logger.info("webhook_delivery_succeeded delivery_id=%s", delivery_id)
        elif outcome == "failed" or attempt_count >= settings.WEBHOOK_MAX_ATTEMPTS:
            values["status"]="failed"; values["last_error"] = f"Max attempts reached. Last error: {error}" if outcome == "retry" else error; logger.warning("webhook_delivery_failed delivery_id=%s", delivery_id)
        else: values.update(status="pending", next_attempt_at=_now()+timedelta(seconds=_backoff(delivery_id,attempt_count,response))); logger.info("webhook_delivery_retry_scheduled delivery_id=%s", delivery_id)
        if db.in_transaction(): db.rollback()
        with db.begin():
            db.execute(update(WebhookDelivery).where(WebhookDelivery.id==item["id"],WebhookDelivery.status=="processing",WebhookDelivery.claim_token==item["claim_token"]).values(**values))
    finally: db.close()

async def process_delivery(db, delivery, client):
    """Compatibility helper; normal worker calls claim_pending_deliveries first."""
    token=uuid.uuid4(); delivery.status, delivery.claim_token, delivery.claimed_at="processing",token,_now(); delivery.attempt_count+=1; db.commit()
    await _attempt({"id":delivery.id,"claim_token":token}, lambda: db, client, validate_destination=False)

async def deliver_pending(db_factory=SessionLocal, client=None):
    recover_stale_claims(db_factory); claimed=claim_pending_deliveries(db_factory)
    if client:
        for item in claimed: await _attempt(item, db_factory, client)
    else:
        async with httpx.AsyncClient(follow_redirects=False) as owned:
            for item in claimed: await _attempt(item, db_factory, owned)
    return len(claimed)

async def main():
    async with httpx.AsyncClient(follow_redirects=False) as client:
        while True:
            try: await deliver_pending(SessionLocal, client)
            except Exception: logger.exception("Unexpected webhook worker failure")
            await asyncio.sleep(settings.WEBHOOK_WORKER_POLL_SECONDS)

if __name__ == "__main__": asyncio.run(main())
