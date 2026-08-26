# ModeraShield Python SDK

The official synchronous Python client for ModeraShield text moderation.

## Installation

From this repository:

```bash
pip install -e sdk/python
```

The package is prepared for the future public command `pip install moderashield`, but is not published to PyPI.

## Configuration and usage

```python
from moderashield import Moderashield

client = Moderashield(api_key="ms_live_xxxxxxxxx")
result = client.moderate_text("I am going to hurt you")

print(result.is_flagged)
print(result.categories)
print(result.scores["threat"])
```

You may instead configure `MODERASHIELD_API_KEY` and optionally `MODERASHIELD_BASE_URL`:

```python
client = Moderashield(poll_interval=1.0, timeout=30.0)
```

The default base URL is `http://localhost:8000`; set `MODERASHIELD_BASE_URL` or pass `base_url=` for another environment.

## Polling and results

`moderate_text()` creates a text job and polls the API until its status is `approved`, `flagged`, or `failed`. It never polls past `timeout`. The returned `ModerationResult` has `id`, `status`, `is_flagged`, `categories`, `scores`, `model`, `created_at`, and `updated_at` attributes.

The SDK automatically sends the supplied API key using the `X-API-Key` header. API keys are never logged.

## Exceptions

Catch `AuthenticationError`, `BadRequestError`, `NotFoundError`, `APIError`, `ModerashieldTimeoutError`, or `NetworkError` as needed. Invalid JSON or an API-contract mismatch raises `MalformedResponseError`.

## Local development

Run the API locally, then set:

```bash
set MODERASHIELD_API_KEY=your-api-key
set MODERASHIELD_BASE_URL=http://localhost:8000
python sdk/python/examples/basic.py
```
