from pydantic_settings import BaseSettings , SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str

    HOST: str
    PORT: int

    DATABASE_URL: str

    SECRET_KEY: str

    ENVIRONMENT: str

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    STORAGE_PROVIDER: str = "local"
    STORAGE_ROOT: str = "./storage"
    # This is intentionally configurable; deployments should set a limit suited
    # to their reverse proxy and storage provider.
    MAX_MEDIA_SIZE_BYTES: int = 104_857_600
    # Comma-separated so it remains straightforward to configure through env.
    ALLOWED_MEDIA_TYPES: str = (
        "image/jpeg,image/png,image/gif,image/webp,"
        "audio/mpeg,audio/wav,audio/x-wav,audio/ogg,audio/mp4,audio/x-m4a,audio/flac,audio/webm,"
        "video/mp4,video/webm,video/quicktime"
    )

    # Image moderation configuration
    IMAGE_MODERATION_MODEL: str = "Falconsai/nsfw_image_detection"
    IMAGE_MODERATION_THRESHOLD: float = 0.5
    IMAGE_MAX_DIMENSION: int = 8192
    IMAGE_MAX_TOTAL_PIXELS: int = 25_000_000
    IMAGE_ALLOWED_FORMATS: str = "JPEG,PNG,GIF,WEBP"

    # Audio moderation configuration
    AUDIO_TRANSCRIPTION_MODEL: str = "openai/whisper-tiny"
    AUDIO_TRANSCRIPTION_DEVICE: str = "auto"
    AUDIO_TRANSCRIPTION_LANGUAGE: str | None = None
    AUDIO_MAX_SIZE_BYTES: int = 25_000_000
    AUDIO_MAX_DURATION_SECONDS: float = 300.0
    AUDIO_ALLOWED_FORMATS: str = "WAV,MP3,OGG,FLAC"

    WEBHOOK_REQUEST_TIMEOUT_SECONDS: float = 5.0
    WEBHOOK_MAX_ATTEMPTS: int = 5
    WEBHOOK_BACKOFF_SECONDS: int = 30
    WEBHOOK_WORKER_POLL_SECONDS: float = 2.0

    OUTBOX_CLAIM_BATCH_SIZE: int = 100
    # A minute covers ordinary broker latency while allowing an interrupted
    # publisher to recover work promptly during development and small deployments.
    OUTBOX_CLAIM_TIMEOUT_SECONDS: int = 60
    OUTBOX_PUBLISHER_POLL_SECONDS: float = 2.0

    REDIS_URL: str = "redis://localhost:6379/0"

    RATE_LIMIT_REQUESTS: int = 2
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file = ".env",
        extra = "ignore"
    )

    @property
    def allowed_media_types(self) -> frozenset[str]:
        return frozenset(
            media_type.strip().lower()
            for media_type in self.ALLOWED_MEDIA_TYPES.split(",")
            if media_type.strip()
        )

    @property
    def image_allowed_formats(self) -> frozenset[str]:
        return frozenset(
            fmt.strip().upper()
            for fmt in self.IMAGE_ALLOWED_FORMATS.split(",")
            if fmt.strip()
        )

    @property
    def audio_allowed_formats(self) -> frozenset[str]:
        return frozenset(
            fmt.strip().upper()
            for fmt in self.AUDIO_ALLOWED_FORMATS.split(",")
            if fmt.strip()
        )

settings = Settings()
