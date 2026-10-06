# ModeraShield — Complete Production System Design

## 1. Overview

ModeraShield is a multimodal content moderation platform designed to accept text, image, and audio moderation requests through an API, process expensive moderation work asynchronously, persist durable results, and optionally notify customers through webhooks.

### Current capabilities

- Text moderation
- Image moderation
- Audio transcription followed by text moderation
- Media ingestion and storage abstraction
- PostgreSQL persistence
- Transactional outbox
- Kafka event transport
- Asynchronous moderation workers
- Webhook delivery
- Tenant-scoped API-key authentication
- Metrics endpoints

**Video is intentionally a future extension and is not part of the current inference implementation.**

---

# 2. Design Goals

## Functional

- Accept text, image, and audio moderation requests.
- Return quickly without waiting for expensive ML inference.
- Persist moderation requests and results.
- Process moderation asynchronously.
- Support customer webhooks.
- Keep tenants isolated.
- Support future model/version evolution.
- Provide operational metrics and failure visibility.

## Non-functional

- No silent request loss.
- At-least-once event delivery.
- Idempotent processing.
- Horizontal scalability.
- Fault isolation between modalities.
- Secure handling of untrusted media.
- Recoverability after infrastructure failures.
- Observable processing pipelines.

---

# 3. Core Design Principles

## 3.1 PostgreSQL is the source of truth

```text
PostgreSQL  = authoritative state
Redis       = temporary infrastructure / rate limiting / cache
Kafka       = event transport
ObjectStore = media storage
```

Redis or Kafka must not become the authoritative source of moderation state.

## 3.2 Expensive work is asynchronous

```text
Client
  ↓
API
  ↓
Persist request + outbox
  ↓
202 Accepted
  ↓
Kafka
  ↓
Worker
  ↓
ML inference
  ↓
Result
```

The API should not wait for Whisper, image inference, or other expensive ML operations.

## 3.3 At-least-once delivery + idempotency

Exactly-once semantics across PostgreSQL, Kafka, ML inference, and webhooks are not a realistic global guarantee.

Use:

```text
At-least-once delivery
        +
Idempotent processing
        +
Unique constraints
        +
Durable state transitions
```

Duplicate delivery is expected and must be safe.

## 3.4 Tenant isolation everywhere

Every tenant-owned resource must be scoped to the authenticated tenant.

The tenant identity comes from the authenticated API key, never from an untrusted client-supplied tenant ID.

---

# 4. Production High-Level Architecture

```text
                         ┌─────────────────────┐
                         │      Customers      │
                         │ SDK / REST / Apps   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Load Balancer / WAF │
                         └──────────┬──────────┘
                                    │
                   ┌────────────────┴────────────────┐
                   ▼                                 ▼
          ┌────────────────┐                ┌────────────────┐
          │   API Server   │                │   API Server   │
          │    FastAPI     │                │    FastAPI     │
          └───────┬────────┘                └───────┬────────┘
                  │                                 │
                  └──────────────┬──────────────────┘
                                 │
                     ┌───────────┴───────────┐
                     ▼                       ▼
                  Redis                 PostgreSQL
              Rate limiting             Source of Truth
                     │                       │
                     │                ┌──────┴──────┐
                     │                │             │
                     │             Requests       Outbox
                     │                              │
                     │                              ▼
                     │                            Kafka
                     │                              │
                     │             ┌────────────────┼────────────────┐
                     │             ▼                ▼                ▼
                     │          Text Pool        Image Pool      Audio Pool
                     │             │                │                │
                     │             ▼                ▼                ▼
                     │          Text Model      Image Model       Whisper
                     │                                                │
                     │                                                ▼
                     │                                           Text Model
                     │             └────────────────┬───────────────┘
                     │                              │
                     │                              ▼
                     │                         PostgreSQL
                     │                              │
                     │                              ▼
                     │                       Webhook Deliveries
                     │                              │
                     │                              ▼
                     │                       Webhook Workers
                     │                              │
                     │                              ▼
                     │                           Customer
                     │
                     ▼
                 Rate-limit
                  counters
```

Media follows a separate storage path:

```text
API
 │
 ▼
Object Storage
 │
 ▼
ModerationAsset
 │
 ▼
Kafka event contains asset_id
 │
 ▼
Worker
 │
 ▼
Object Storage
```

**Media bytes are never placed in PostgreSQL, Kafka, or outbox payloads.**

---

# 5. Architecture Planes

```text
CONTROL PLANE
API / Authentication / Tenant / Requests / Webhooks
              │
              ▼
EVENT PLANE
Outbox → Kafka → Workers
              │
              ▼
INFERENCE PLANE
Text / Image / Whisper + Text Moderation
```

This separation makes scaling and failure isolation easier.

---

# 6. Current vs Production vs Future

## 6.1 Implemented

- FastAPI API
- API-key authentication
- Tenant-scoped requests
- PostgreSQL
- Moderation request/result models
- Moderation assets
- Local storage abstraction
- Image moderation
- Audio transcription + moderation
- Outbox pattern
- Kafka
- Moderation worker
- Retry handling
- Idempotent result persistence
- Webhook delivery
- Metrics endpoints

## 6.2 Production hardening

- Redis rate limiting
- Real idempotency keys
- S3/object-storage migration
- Kafka HA
- Outbox row claiming
- Processing leases
- Separate worker pools
- Webhook concurrency control
- SSRF egress protection
- Webhook signatures
- TLS everywhere
- Secrets management
- Additional DB indexes
- Automated backups/PITR
- Distributed tracing
- Load testing
- Autoscaling
- Formal DLQ handling

## 6.3 Future

- Dedicated model-serving infrastructure
- GPU inference fleet
- Video moderation
- Model canary infrastructure
- Advanced analytics
- Multi-region deployment
- Cross-region disaster recovery
- Sophisticated model routing

---

# 7. Capacity Planning

## Baseline assumptions

```text
Tenants                           = 1,000
Requests / tenant / day           = 1,000
Total requests / day              = 1,000,000
Peak multiplier                   = 5x

Text                              = 70%
Image                             = 20%
Audio                             = 10%

Average image size                = 500 KB
Average audio size                = 2 MB

Webhook adoption                  = 30%
Average webhooks / enabled tenant = 1

Media retention                   = 30 days
```

## Request rate

```text
1,000,000 / 86,400
≈ 11.6 requests/sec
```

Peak:

```text
11.6 × 5
≈ 58 requests/sec
```

Approximate peak modality traffic:

```text
Text   ≈ 40.5 RPS
Image  ≈ 11.6 RPS
Audio  ≈ 5.8 RPS
```

These are planning assumptions, not measured production limits.

## Media storage

```text
Image:
200,000 × 500 KB
≈ 100 GB/day

Audio:
100,000 × 2 MB
≈ 200 GB/day

Total:
≈ 300 GB/day

30 days:
≈ 9 TB
```

## Database growth

A rough assumption of three DB rows per request gives:

```text
≈ 3,000,000 rows/day
≈ 90,000,000 rows/30 days
```

Actual storage depends on indexes, JSON metadata, row overhead, timestamps, and retention.

## Worker concurrency

Use:

```text
required concurrency ≈ arrival rate × average processing time
```

Illustrative processing times:

```text
Text  = 100 ms
Image = 300 ms
Audio = 5 sec
```

At peak:

```text
Text:
40.5 × 0.1 ≈ 4 workers worth of concurrency

Image:
11.6 × 0.3 ≈ 4 workers worth of concurrency

Audio:
5.8 × 5 ≈ 29 workers worth of concurrency
```

These timings must eventually be replaced with benchmarked values.

---

# 8. API Design

## Public endpoints

```text
POST   /api/v1/moderate
POST   /api/v1/moderate/media

GET    /api/v1/moderate/{request_id}

POST   /api/v1/webhooks
GET    /api/v1/webhooks
DELETE /api/v1/webhooks/{webhook_id}

GET    /api/v1/metrics/overview
GET    /api/v1/metrics/breakdown
GET    /api/v1/metrics/categories
GET    /api/v1/metrics/usage
```

## Text request

```json
{
  "content_type": "text",
  "content": "example text"
}
```

## Media request

```text
POST /api/v1/moderate/media
Content-Type: multipart/form-data
```

The API validates media before creating the moderation request.

## Response

Moderation is asynchronous:

```http
202 Accepted
```

Example:

```json
{
  "id": "request-uuid",
  "tenant_id": "tenant-uuid",
  "content_type": "image",
  "status": "pending"
}
```

---

# 9. Idempotency

Production API should support:

```http
Idempotency-Key: <unique-client-generated-key>
```

Database:

```text
moderation_request
------------------
id
tenant_id
idempotency_key
...
```

Constraint:

```text
UNIQUE(tenant_id, idempotency_key)
```

Flow:

```text
Client
  │
  │ same Idempotency-Key
  ▼
API
  │
  ▼
Existing request?
  │
  ├── yes → return existing request
  │
  └── no  → create request
```

---

# 10. Authentication

Current model:

```text
X-API-Key: msk_xxxxx
        │
        ▼
Authentication
        │
        ▼
Hash API key
        │
        ▼
Find active key
        │
        ▼
tenant_id
```

Never store plaintext API keys.

Recommended fields:

```text
api_keys
--------
id
tenant_id
key_hash
prefix
created_at
last_used_at
expires_at
revoked_at
```

---

# 11. Authorization

Authentication identifies the tenant.

Authorization ensures every operation is tenant-scoped.

Example:

```sql
SELECT *
FROM moderation_request
WHERE id = :request_id
AND tenant_id = :authenticated_tenant_id;
```

Never trust a client-provided tenant ID.

UUID knowledge alone must never grant cross-tenant access.

---

# 12. Rate Limiting

Redis is introduced primarily for distributed API rate limiting.

Example logical key:

```text
ratelimit:{tenant_id}:{window}
```

Potential limits:

```text
Free       → lower request rate
Pro        → higher request rate
Enterprise → custom limits
```

Exact limits should be configuration-driven.

Redis is not authoritative state.

If Redis is unavailable, use an explicit fail-open/fail-closed policy based on endpoint and abuse risk.

---

# 13. Database Design

## Core relationship

```text
Tenant
  │
  ├── APIKey
  ├── Webhook
  └── ModerationRequest
             │
             ├── ModerationAsset
             │
             └── ModerationResult
```

Event infrastructure:

```text
ModerationRequest
       │
       ▼
OutboxEvent
```

Webhook infrastructure:

```text
ModerationRequest
       │
       ▼
WebhookDelivery
```

## ModerationRequest

```text
id
tenant_id
content_type
content
status
retry_count
last_error
asset_id
created_at
updated_at
```

Relationship:

```text
ModerationAsset 1 → N ModerationRequest
```

with:

```text
ModerationRequest.asset_id
    → ModerationAsset.id
```

and `ON DELETE SET NULL`.

## ModerationAsset

```text
id
tenant_id
storage_provider
object_key
mime_type
size_bytes
checksum
asset_metadata
created_at
updated_at
```

## ModerationResult

Current logical relationship:

```text
ModerationRequest 1 → 1 ModerationResult
```

enforced by:

```text
UNIQUE(request_id)
```

Future model-versioned results could use:

```text
UNIQUE(request_id, model_version)
```

## Important indexes

```text
ModerationRequest:
(tenant_id, created_at)
(tenant_id, status)
(asset_id)

Outbox:
(status, created_at)

WebhookDelivery:
(status, next_attempt_at)
```

---

# 14. Request State Machine

```text
             ┌──────────────┐
             │    pending   │
             └──────┬───────┘
                    │
                    ▼
             ┌──────────────┐
             │  processing  │
             └──────┬───────┘
                    │
              ┌─────┴─────┐
              │           │
              ▼           ▼
         completed      failed
```

Transient failures return to:

```text
pending
```

Permanent failures move to:

```text
failed
```

---

# 15. Media Pipeline

```text
Client upload
     ↓
MIME validation
     ↓
Size validation
     ↓
Content/magic-byte validation
     ↓
Object storage
     ↓
ModerationAsset
     ↓
ModerationRequest
     ↓
Outbox
     ↓
Kafka
     ↓
Worker
     ↓
AssetResolver
     ↓
Validation / decoding
     ↓
ML inference
     ↓
ModerationResult
```

Media bytes never enter Kafka.

---

# 16. Object Storage

Current architecture uses a storage abstraction with local storage.

Production should use S3-compatible object storage.

Database stores:

```text
storage_provider
object_key
mime_type
size_bytes
checksum
metadata
tenant_id
```

Object keys should be generated server-side:

```text
tenant/{tenant_id}/assets/{uuid}
```

Clients must not choose arbitrary filesystem/object paths.

---

# 17. Media Security

Do not trust:

```text
filename
extension
declared Content-Type
```

alone.

Validation:

```text
Upload
 ↓
Declared MIME allowlist
 ↓
File size limit
 ↓
Magic-byte/content validation
 ↓
Safe decode
 ↓
Dimension/duration limits
 ↓
Store
```

Image protections:

```text
allowed formats
maximum dimensions
maximum total pixels
decompression-bomb protection
safe decoding
```

Audio protections:

```text
format validation
file-size limit
duration limit
safe decoding
NaN/Inf handling
resampling
channel normalization
```

---

# 18. Text Inference

```text
Kafka
  ↓
TextModerationHandler
  ↓
TextInferenceService
  ↓
Text model
  ↓
Normalized moderation result
  ↓
PostgreSQL
```

Normalized result:

```json
{
  "is_flagged": true,
  "categories": ["..."],
  "scores": {
    "category": 0.91
  },
  "model": "..."
}
```

---

# 19. Image Inference

```text
Kafka
  ↓
ImageModerationHandler
  ↓
AssetResolver
  ↓
Object Storage
  ↓
Image validation
  ↓
Decode
  ↓
Image model
  ↓
Thresholding
  ↓
Normalized result
  ↓
PostgreSQL
```

Current image implementation uses `Falconsai/nsfw_image_detection` with a configurable threshold.

Exact model labels should follow the model configuration rather than being assumed.

---

# 20. Audio Inference

```text
Kafka
  ↓
AudioModerationHandler
  ↓
AssetResolver
  ↓
Object Storage
  ↓
Audio validation
  ↓
Decode
  ↓
Normalize
  ↓
Whisper
  ↓
Transcript
  ↓
Text moderation model
  ↓
Normalized result
  ↓
PostgreSQL
```

Current transcription model:

```text
openai/whisper-tiny
```

with configurable device/language settings.

Empty or silent audio can be approved without sending empty content through the text model.

---

# 21. Worker Architecture

Current:

```text
Kafka
  ↓
Moderation Worker
  ↓
Modality Handler
  ↓
Model
```

Production:

```text
Kafka
 │
 ├── Text Worker Pool
 │
 ├── Image Worker Pool
 │
 └── Audio Worker Pool
```

Separate pools prevent expensive audio work from starving text/image workloads.

Worker responsibilities:

1. Consume Kafka event.
2. Validate event.
3. Claim/load request.
4. Check for existing result.
5. Select modality handler.
6. Execute inference.
7. Persist result.
8. Create webhook delivery.
9. Commit Kafka offset.

---

# 22. Duplicate Kafka Delivery

Scenario:

```text
Worker
  ↓
Inference
  ↓
DB result committed
  ↓
Kafka offset commit fails
```

Kafka redelivers the event.

Worker checks:

```text
Does ModerationResult already exist?
```

If yes:

```text
skip duplicate inference
```

The unique result constraint protects persistence:

```text
UNIQUE(request_id)
```

---

# 23. Processing Leases

A production worker should track:

```text
processing_started_at
lease_expires_at
```

Flow:

```text
pending
   ↓
processing
   ↓
worker crashes
   ↓
lease expires
   ↓
recovery process
   ↓
pending
   ↓
retry
```

This prevents requests from becoming permanently stuck in `processing`.

---

# 24. Retry Architecture

Retry only transient failures.

```text
Failure
  │
  ├── transient → retry
  │
  └── permanent → failed
```

Use exponential backoff with jitter.

Example:

```text
Attempt 1 → immediate
Attempt 2 → 30 sec
Attempt 3 → 60 sec
Attempt 4 → 120 sec
Attempt 5 → 240 sec
```

Never retry indefinitely.

---

# 25. Failure Classification

| Failure | Classification | Action |
|---|---|---|
| Kafka temporarily unavailable | Transient | Retry |
| PostgreSQL temporary failure | Transient | Retry |
| Object storage timeout | Transient | Retry |
| Model timeout | Transient | Retry |
| Corrupt image | Permanent | Fail |
| Unsupported media | Permanent | Fail |
| Invalid API request | Permanent | Reject |
| Invalid webhook URL | Permanent | Reject |
| Webhook 500 | Transient | Retry |
| Webhook 400 | Permanent | Stop retrying |
| Model configuration bug | Potentially systemic | Alert / rollback |

---

# 26. Dead Letter Queue

Logical topics:

```text
moderation.requests
moderation.retry
moderation.dlq
```

After retry exhaustion, poison events should be moved to the DLQ.

Current retry/DLQ topic concepts exist, but formal production DLQ processing remains a hardening task.

DLQ messages should retain enough diagnostic metadata without unnecessarily duplicating sensitive payloads.

---

# 27. Outbox Pattern

Request and event are committed atomically:

```text
BEGIN TRANSACTION

INSERT ModerationRequest
INSERT OutboxEvent

COMMIT
```

Then:

```text
Outbox Publisher
      ↓
Kafka
```

This prevents:

```text
DB success
+
Kafka event lost
```

---

# 28. Outbox Concurrency

Production outbox publishers should prevent multiple instances from selecting the same pending rows simultaneously.

Options:

```text
SELECT ... FOR UPDATE SKIP LOCKED
```

or:

```text
pending
  ↓
publishing
  ↓
published
```

A crash after Kafka publish but before DB commit can still create a duplicate event. This is acceptable because consumers are idempotent.

---

# 29. Kafka Design

Current baseline:

```text
moderation.requests
3 partitions
```

For roughly 58 peak events/sec, this is sufficient from a raw throughput perspective.

Partition count should ultimately be based on:

```text
throughput
consumer parallelism
ordering requirements
future growth
```

## Partition key

Possible:

```text
tenant_id
```

Pros:
- tenant-level ordering

Cons:
- hot tenants can create hot partitions

Or:

```text
request_id
```

Pros:
- better distribution
- independent requests remain independent

Default preference:

```text
request_id
```

unless tenant-level ordering becomes an explicit requirement.

---

# 30. Kafka Security

Production Kafka should use:

```text
TLS
+
authentication
+
ACLs
```

Example:

```text
Outbox Publisher
 → WRITE moderation.requests

Moderation Worker
 → READ moderation.requests

DLQ Processor
 → READ moderation.dlq
```

Services should receive only the permissions they need.

---

# 31. Webhook Architecture

Moderation completion creates a durable webhook delivery record.

```text
ModerationResult
      ↓
WebhookDelivery
      ↓
WebhookWorker
      ↓
Customer endpoint
```

Webhook delivery failure must not fail moderation.

---

# 32. Webhook Retry

```text
Webhook
  ↓
500
  ↓
retry
  ↓
500
  ↓
retry
  ↓
success
```

4xx responses generally indicate permanent customer-side rejection.

Network errors and 5xx responses are retryable.

---

# 33. Webhook Idempotency

Delivery can be duplicated:

```text
Webhook Worker
  ↓
POST customer
  ↓
Customer receives event
  ↓
Worker crashes before recording success
```

The worker retries.

Payload should include:

```json
{
  "event_id": "unique-event-id",
  "event": "moderation.completed",
  "request_id": "request-id"
}
```

Customers should deduplicate using `event_id`.

---

# 34. Webhook Signatures

Production webhooks should be signed.

```text
payload + webhook_secret
        ↓
HMAC-SHA256
        ↓
signature
```

Example:

```text
X-ModeraShield-Signature
```

Include a timestamp to reduce replay risk.

---

# 35. SSRF Protection

Customer-controlled webhook URLs create an SSRF risk.

A malicious URL could resolve to:

```text
127.0.0.1
10.0.0.0/8
169.254.169.254
```

URL validation alone is insufficient because DNS can change after validation.

Production webhook egress should include:

```text
DNS resolution
 ↓
Private/loopback/link-local IP blocking
 ↓
Redirect restrictions
 ↓
Network-level egress controls
```

---

# 36. PostgreSQL Security

Production PostgreSQL should use:

```text
private network
TLS
restricted DB user
strong credentials
automated backups
point-in-time recovery
```

The database should not be directly exposed to the public internet.

---

# 37. Secrets Management

Never commit:

```text
API keys
database passwords
Kafka credentials
webhook secrets
cloud credentials
```

into source control.

Use environment variables for simple deployments and a dedicated secrets manager for mature production.

---

# 38. Encryption

Production should use:

```text
TLS in transit
+
encryption at rest
```

for:

```text
PostgreSQL
Object storage
Backups
Secrets where supported
```

---

# 39. Observability

## Metrics

Track:

```text
API RPS
API latency
API error rate

Kafka consumer lag

Requests by modality

Queue latency
Processing latency

Text model latency
Image model latency
Whisper latency

Model error rate

Webhook success rate
Webhook latency

Retry count
DLQ count

Storage errors
```

## Logs

Every important operation should include:

```text
request_id
tenant_id
event_id
worker_id
model_version
status
latency
error
```

Do not log:

```text
API secrets
webhook secrets
raw media
sensitive raw user content
```

unless there is a tightly controlled debugging requirement.

## Tracing

Eventually trace:

```text
API
 ↓
PostgreSQL
 ↓
Outbox
 ↓
Kafka
 ↓
Worker
 ↓
Model
 ↓
Webhook
```

---

# 40. Reliability Failure Matrix

| Failure | Expected behavior | Recovery |
|---|---|---|
| API crashes before DB commit | Request not durably accepted | Client retries |
| API crashes after DB commit | Outbox remains | Publisher retries |
| Kafka unavailable | Outbox accumulates | Publish after recovery |
| PostgreSQL unavailable | API returns 5xx | Retry later |
| Worker crashes | Kafka event may redeliver | Reprocess |
| Worker crashes after inference | Result may not exist | Reprocess |
| DB commit succeeds but Kafka commit fails | Duplicate event | Idempotent consumer |
| Object storage timeout | Retry | Backoff |
| Object permanently missing | Eventually fail | Failure event |
| Corrupt media | Permanent failure | No retry |
| Model transient error | Retry | Backoff |
| Model systemic failure | Alert | Rollback/fix |
| Webhook 5xx | Retry | Backoff |
| Webhook 4xx | Permanent delivery failure | Stop retrying |
| Webhook worker crashes | Duplicate possible | `event_id` dedupe |
| Redis unavailable | Apply defined rate-limit policy | Recover Redis |
| Outbox publisher crashes | Duplicate possible | Consumer idempotency |

---

# 41. Redis Failure Policy

Redis is not the source of truth.

If Redis is unavailable, the service must follow an explicit policy.

### Fail closed

```text
Reject requests
```

More protective against abuse but less available.

### Fail open

```text
Allow requests
```

More available but can temporarily bypass rate limits.

The production policy should be selected according to tenant plans and abuse risk.

---

# 42. Availability and SLOs

An initial target could be:

```text
API availability = 99.9%
```

Approximate monthly downtime budget:

```text
≈ 43.2 minutes / 30-day month
```

API availability and moderation latency are different SLOs.

Potential initial targets:

```text
API availability          99.9%
API p95 latency            < 300 ms

Text moderation p95        < 1 sec
Image moderation p95       < 3 sec
Audio moderation p95       < 15 sec
```

These are design targets and must be validated through benchmarking.

---

# 43. Scaling Strategy

## API

FastAPI servers should be stateless and horizontally scalable.

```text
API 1
API 2
API 3
...
```

## Workers

Scale based on:

```text
Kafka lag
CPU/GPU utilization
processing latency
queue latency
```

## Database

Start with:

```text
proper indexes
connection pooling
vertical scaling
```

Then introduce:

```text
read replicas
partitioning
archival
```

only when justified by measurements.

---

# 44. Modality Isolation

Separate pools:

```text
Kafka
 │
 ├── Text
 ├── Image
 └── Audio
```

Without isolation:

```text
Audio spike
    ↓
Workers saturated
    ↓
Text requests wait
```

With isolation:

```text
Audio spike
    ↓
Audio workers scale independently
```

---

# 45. Model Serving Evolution

Current:

```text
Worker
  ↓
Model loaded inside worker
```

This is simple and appropriate for the current stage.

Future:

```text
Moderation Worker
       ↓
Model Serving Layer
       │
       ├── Text model
       ├── Image model
       └── Whisper
```

Use dedicated model serving when justified by:

- large models
- GPU requirements
- duplicated memory pressure
- independent model scaling
- model deployment complexity
- multiple consumers

Do not introduce it prematurely.

---

# 46. Model Versioning

Results should eventually contain:

```text
model
model_version
threshold
configuration_version
```

Example:

```json
{
  "model": "text-moderation",
  "model_version": "v2.1",
  "threshold": 0.5
}
```

This enables reproducibility and controlled rollouts.

---

# 47. Model Canary Rollout

```text
v1 ──────────────── production

v2 ── canary ──→ 10%
                  │
                  ├── healthy → increase
                  │
                  └── unhealthy → rollback
```

Model performance should be monitored separately from infrastructure health.

---

# 48. Disaster Recovery

## PostgreSQL

Use:

```text
automated backups
+
point-in-time recovery
```

## Object storage

Use:

```text
versioning where appropriate
+
replication where required
+
lifecycle policies
```

## Kafka

Kafka is transport rather than the ultimate source of truth.

If Kafka fails:

```text
PostgreSQL
+
Outbox
```

allow unpublished work to be reconstructed/published after recovery.

For published but unprocessed events, Kafka retention and replay policy must be defined according to operational requirements.

---

# 49. Complete Recovery Example

If Kafka goes down:

```text
PostgreSQL        ✅
Object Storage    ✅
Kafka             ❌
```

New requests:

```text
API
 ↓
PostgreSQL
 ↓
Outbox
```

After Kafka recovers:

```text
Outbox
 ↓
Kafka
 ↓
Workers
 ↓
Results
```

The system catches up instead of losing requests.

---

# 50. Data Retention

Initial policy:

```text
Media                    ≈ 30 days
Hot moderation data      ≈ 30–90 days
Operational logs         Shorter retention
Aggregated metrics       Longer retention
```

Future:

```text
Hot DB
  ↓
Archive
  ↓
Delete
```

Retention should eventually be configurable by plan and compliance requirements.

---

# 51. Performance Engineering

Measure:

```text
p50
p95
p99
```

for:

```text
API latency
queue latency
text inference
image inference
audio transcription
webhook delivery
```

Optimize the actual bottleneck.

Example:

```text
API          40 ms
Kafka        10 ms
DB           20 ms
Image model 800 ms
```

Optimizing API latency from 40 ms to 20 ms is less valuable than optimizing image inference.

---

# 52. Complete End-to-End Request Lifecycle

```text
CLIENT
  │
  │ POST /moderate
  ▼
WAF / LB
  │
  ▼
API
  │
  ├── Authenticate API key
  ├── Authorize tenant
  ├── Rate limit
  ├── Validate input
  └── Check idempotency
  │
  ▼
POSTGRES
  │
  ├── ModerationRequest
  └── OutboxEvent
  │
  ▼
202 Accepted
  │
  │ ASYNC
  │
  ▼
OUTBOX PUBLISHER
  │
  ▼
KAFKA
  │
  ├──────────┬──────────┐
  ▼          ▼          ▼
 TEXT       IMAGE      AUDIO
WORKER      WORKER     WORKER
  │          │          │
  ▼          ▼          ▼
MODEL       MODEL      WHISPER
                         │
                         ▼
                    TEXT MODEL
  │          │          │
  └──────────┴──────────┘
             │
             ▼
         POSTGRES
             │
             ▼
      ModerationResult
             │
             ▼
       WebhookDelivery
             │
             ▼
       Webhook Worker
             │
             ▼
          CUSTOMER
```

---

# 53. Security + Reliability Principles

### Invalid API key

```text
401
```

Do not retry.

### Rate limit exceeded

```text
429
```

Do not enqueue the request.

### Corrupt media

```text
failed
```

Do not retry indefinitely.

### Kafka unavailable

```text
persist in outbox
```

Do not lose the request.

### Customer webhook unavailable

```text
moderation remains completed
webhook delivery retries separately
```

This separation prevents secondary failures from corrupting the primary moderation workflow.

---

# 54. Phase 6 Implementation Plan

The architecture should now move from design into implementation.

```text
6.1 Production configuration
       ↓
6.2 Redis rate limiting
       ↓
6.3 Idempotency
       ↓
6.4 Kafka + outbox hardening
       ↓
6.5 Processing leases / recovery
       ↓
6.6 Webhook security + concurrency
       ↓
6.7 S3/object-storage migration
       ↓
6.8 Observability
       ↓
6.9 Security hardening
       ↓
6.10 Worker scaling
       ↓
6.11 Load testing
       ↓
6.12 Failure / chaos testing
```

---

# 55. Phase 5 Completion

```text
5.1 Architecture Audit                 ✅
5.2 Capacity Estimation                ✅
5.3 High-Level Design                  ✅
5.4 API + Database Design              ✅
5.5 Kafka + Outbox Design              ✅
5.6 Worker + ML Inference              ✅
5.7 Reliability + Failure Handling     ✅
5.8 Security                           ✅
5.9 Observability                      ✅
5.10 Scaling + Performance             ✅
5.11 Disaster Recovery + Versioning    ✅
5.12 Final Architecture                ✅
```

## Phase 5 Status

**COMPLETE**

The architecture now defines:

```text
normal operation
+
failures
+
retries
+
duplicates
+
security
+
scaling
+
observability
+
disaster recovery
+
model evolution
```

The next stage is implementation and validation rather than further theoretical design.
