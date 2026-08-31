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
    WEBHOOK_REQUEST_TIMEOUT_SECONDS: float = 5.0
    WEBHOOK_MAX_ATTEMPTS: int = 5
    WEBHOOK_BACKOFF_SECONDS: int = 30
    WEBHOOK_WORKER_POLL_SECONDS: float = 2.0

    model_config = SettingsConfigDict(
        env_file = ".env",
        extra = "ignore"
    )

settings = Settings()
