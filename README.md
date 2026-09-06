# ModeraShield

## Media lifecycle (Phase 2)

Media is streamed to the configured storage provider under a server-generated,
tenant-scoped key. The database retains metadata only; the outbox event carries
request and asset identifiers, never media bytes. If creating the asset, request,
or outbox event fails after upload, the API attempts to delete the stored object
and preserves the original failure if that cleanup also fails.

Requests retain their assets through normal moderation outcomes, including a
permanent moderation failure. Deletion/retention policy and periodic orphan
reconciliation are operational concerns intentionally deferred to a later phase.
Client-declared MIME types are allowlisted and normalized for routing, but file
signature inspection is not yet implemented; deploy a trusted gateway/content
scanner where stronger verification is required.

## Image Moderation (Phase 3)

ModeraShield provides end-to-end image moderation using deep learning Vision Transformers while enforcing strict tenant isolation, memory security, and transactional safety.

### End-to-End Architecture Flow

```
API image upload (POST /api/v1/moderate/media)
    ↓
Storage Service (server-generated tenant-scoped key)
    ↓
ModerationAsset (metadata, size, checksum, mime_type)
    ↓
ModerationRequest (status="pending", content_type="image", asset_id)
    ↓
Outbox Event (moderation.requested, metadata only)
    ↓
Kafka Topic (moderation-requests)
    ↓
Moderation Worker (consumer group: moderation-worker)
    ↓
ImageModerationHandler
    ↓
AssetResolver (tenant isolation check & storage stream open)
    ↓
Image Security & Validation (format check, dimension bounds, decompression bomb protection)
    ↓
ImageInferenceService (Vision Transformer model inference)
    ↓
Normalized Moderation Result (is_flagged, categories, scores, model)
    ↓
ModerationResult (persisted outside inference transaction)
    ↓
Webhook Delivery (asynchronous tenant notification)
```

### Supported Formats & MIME Types
- **Allowlisted Media MIME Types**: `image/jpeg`, `image/png`, `image/gif`, `image/webp`
- **Supported Container Formats**: `JPEG`, `PNG`, `GIF`, `WEBP`
- Validation does NOT rely solely on client-provided headers; the actual file container and stream headers are inspected upon decoding.

### Image Security & Validation Limits
- **Maximum Media Size**: `104,857,600` bytes (100MB, configurable via `MAX_MEDIA_SIZE_BYTES`).
- **Maximum Dimensions**: 8,192 x 8,192 pixels (configurable via `IMAGE_MAX_DIMENSION`).
- **Decompression Bomb Protection**: Maximum 25,000,000 pixels (configurable via `IMAGE_MAX_TOTAL_PIXELS`). Images exceeding this limit are cleanly rejected.
- **Raster Integrity**: Pixel data is loaded safely (`image.load()`) to catch corrupted, malformed, or truncated images prior to inference.
- **Color Mode**: Automatically converts non-RGB images (such as RGBA, Palette P, Grayscale L) to RGB 3-channel tensors for model compatibility.

### Selected Moderation Model
- **Model**: `Falconsai/nsfw_image_detection` (configurable via `IMAGE_MODERATION_MODEL`)
- **Architecture**: Vision Transformer (`google/vit-base-patch16-224-in21k` fine-tuned for NSFW detection).
- **License**: Apache 2.0 (open source, permissive, commercial-friendly).
- **Weights Size**: ~343MB (`model.safetensors`).
- **Runtime**: PyTorch CPU inference mode (`@torch.inference_mode()`) or GPU (`cuda`) if available.
- **Model Loading**: Lazy singleton loader (`@lru_cache(maxsize=1)`) caches the model and processor in memory across worker messages without per-message initialization overhead.

### Model Output & Normalization Contract
- **Categories**: `["nsfw"]` when flagged, `[]` when approved.
- **Scores**: Normalized probabilities across labels (`normal` and `nsfw`), rounded to 4 decimal places.
- **Threshold**: Default `0.5` (configurable via `IMAGE_MODERATION_THRESHOLD`). An image is flagged (`is_flagged = True`) if `scores["nsfw"] >= threshold`.
- **Contract Schema**:
  ```json
  {
      "is_flagged": false,
      "categories": [],
      "scores": {
          "normal": 0.9823,
          "nsfw": 0.0177
      },
      "model": "Falconsai/nsfw_image_detection"
  }
  ```

### Failure Classification & Poison Pill Protection
- **Terminal Failures**: Malformed images, unsupported formats, decompression bombs, missing assets, and tenant access mismatches are classified as `NonRetriableProcessingError`. They transition the request to `status = "failed"` immediately, record `last_error`, trigger failure webhook notifications, and commit the Kafka message to avoid partition blocking or infinite retry loops.
- **Retriable Failures**: Transient exceptions (e.g., temporary resource exhaustion or network timeouts) preserve the uncommitted Kafka offset and retry up to `MAX_RETRIES` (3) before marking the request as permanently failed.

### Data Confidentiality
- Raw media bytes are never persisted in PostgreSQL, Kafka event payloads, outbox events, application logs, or webhook delivery payloads.
