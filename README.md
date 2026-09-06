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

## Audio Moderation (Phase 4)

ModeraShield provides production-quality audio moderation following the core architectural principle:
**Audio is transcribed to text and the transcript is passed through the existing text moderation model.**
The speech-to-text model itself does NOT perform moderation; it converts spoken speech into text, which is then moderated by the central text moderation engine (`bhavdeepsingh/moderashield-text-moderation`).

### End-to-End Architecture Flow

```
API audio upload (POST /api/v1/moderate/media)
    ↓
Storage Service (server-generated tenant-scoped key)
    ↓
ModerationAsset (metadata, size, checksum, mime_type)
    ↓
ModerationRequest (status="pending", content_type="audio", asset_id)
    ↓
Outbox Event (moderation.requested, metadata only)
    ↓
Kafka Topic (moderation-requests)
    ↓
Moderation Worker (consumer group: moderation-worker)
    ↓
AudioModerationHandler
    ↓
AssetResolver (tenant isolation check & storage stream open)
    ↓
Audio Security & Validation (container check, duration bounds, size limit, safe decoding)
    ↓
SpeechToTextService (OpenAI Whisper via Hugging Face Transformers)
    ↓
TextInferenceService (existing text classifier: toxic, obscene, threat, insult, identity_hate)
    ↓
Normalized Moderation Result (composite model name, scores, categories)
    ↓
ModerationResult (persisted outside inference transaction)
    ↓
Webhook Delivery (asynchronous tenant notification)
```

### Supported Formats & MIME Types
- **Allowlisted Media MIME Types**: `audio/wav`, `audio/x-wav`, `audio/mpeg`, `audio/ogg`, `audio/flac`, `audio/mp4`, `audio/x-m4a`, `audio/webm`
- **Supported Container Formats**: `WAV`, `MP3`, `OGG`, `FLAC` natively supported via `soundfile` / `libsndfile` (bundled in wheel without external dependencies). Video-container formats (e.g. `MP4`, `M4A`, `WEBM`) require system `ffmpeg`. If a container requires an external tool not installed on the system, it is rejected with an explicit `AudioFormatError`.
- **Validation**: Inspects magic bytes and container metadata rather than blindly trusting client-supplied `Content-Type`.

### Audio Security & Validation Limits
- **Maximum Audio Size**: 25,000,000 bytes (~25MB, configurable via `AUDIO_MAX_SIZE_BYTES`). Files exceeding this limit are rejected at upload time (HTTP 413) or worker validation (`AudioSizeError`).
- **Maximum Audio Duration**: 300.0 seconds (5 minutes, configurable via `AUDIO_MAX_DURATION_SECONDS`). Audio exceeding this limit is cleanly rejected as permanent `AudioDurationError`.
- **Integrity Check**: Audio sample frames are decoded and checked for NaN/Inf or truncation before inference.
- **Sample Rate & Channels**: Multi-channel audio is automatically downmixed to mono float32, and audio is resampled to 16,000 Hz for Whisper feature extraction.

### Speech-to-Text Model & Configuration
- **Model**: `openai/whisper-tiny` (configurable via `AUDIO_TRANSCRIPTION_MODEL`).
- **Device**: `auto` (detects `cuda` if available, otherwise falls back to `cpu`; configurable via `AUDIO_TRANSCRIPTION_DEVICE`).
- **Language**: Optional language code (e.g. `en`) or `None` for automatic language detection (configurable via `AUDIO_TRANSCRIPTION_LANGUAGE`).
- **Lazy Singleton Initialization**: Model weights are loaded and cached in memory across worker messages (`@lru_cache(maxsize=1)`) only when audio moderation is first requested, avoiding application startup overhead.

### Model Name & Attribution Contract
The final `model` attribute in `ModerationResult` clearly reflects both components:
```
<transcription-model> + <text-moderation-model>
```
Example: `"openai/whisper-tiny + moderashield-text-v1"`

### Normalized Moderation Output Schema
```json
{
    "is_flagged": false,
    "categories": [],
    "scores": {
        "toxic": 0.0012,
        "severe_toxic": 0.0001,
        "obscene": 0.0005,
        "threat": 0.0002,
        "insult": 0.0008,
        "identity_hate": 0.0001
    },
    "model": "openai/whisper-tiny + moderashield-text-v1"
}
```
*Note: If no speech is detected (e.g. silence or background noise), the request is approved with 0.0 scores without invoking the text model.*

### Failure Classification & Poison Pill Protection
- **Terminal Failures (`NonRetriableProcessingError`)**: Malformed audio (`AudioCorruptError`), unsupported format (`AudioFormatError`), duration limit exceeded (`AudioDurationError`), size limit exceeded (`AudioSizeError`), missing asset (`FileNotFoundError`), and tenant access mismatch (`PermissionError`). They transition `status = "failed"` immediately, record `last_error`, send failure webhook, and commit Kafka offset.
- **Retriable Failures**: Transient exceptions (network timeouts, storage connectivity issues, GPU out-of-memory) preserve uncommitted offset and retry up to `MAX_RETRIES` (3).

### Data Confidentiality & Privacy
- Raw audio bytes are never stored in PostgreSQL, Kafka event payloads, outbox events, application logs, or webhooks.
- Transcripts are ephemeral intermediate processing data and are NOT logged by default or stored in a separate table.
