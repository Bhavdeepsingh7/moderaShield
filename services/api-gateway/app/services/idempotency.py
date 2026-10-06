import hashlib
import json
from app.schemas.moderation import ModerationRequestCreate


def compute_request_hash(data: ModerationRequestCreate) -> str:
    """
    Computes a deterministic SHA-256 hash of the semantic payload fields
    for a text or media moderation request.
    """
    content_type_str = (
        data.content_type.value
        if hasattr(data.content_type, "value")
        else str(data.content_type)
    )

    if data.media is not None:
        payload = {
            "checksum": data.media.checksum,
            "content_type": content_type_str,
        }
    else:
        payload = {
            "content": data.content,
            "content_type": content_type_str,
        }

    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
