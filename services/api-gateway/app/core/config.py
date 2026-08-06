from pydantic_settings import BaseSettings , SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str

    HOST: str
    PORT: int

    DATABASE_URL: str

    SECRET_KEY: str

    ENVIRONMENT: str

    model_config = SettingsConfigDict(
        env_file = ".env",
        extra = "ignore"
    )

settings = Settings()