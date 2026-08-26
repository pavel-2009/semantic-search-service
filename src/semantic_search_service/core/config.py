"""Project configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "movies"

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    MAX_TEXT_LENGTH: int = 2000
    BATCH_SIZE: int = 32

    DATA_PATH: Path = Path(__file__).resolve().parents[1] / "scraper" / "data" / "movies.json"

    LOG_LEVEL: str = "INFO"
    POISKKINO_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
