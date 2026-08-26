"""Project configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "movies"

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    MAX_TEXT_LENGTH: int = 2000
    BATCH_SIZE: int = 32

    DATA_PATH: Path = PROJECT_ROOT / "src" / "semantic_search_service" / "scraper" / "data" / "movies.json"

    LOG_LEVEL: str = "INFO"
    POISKKINO_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
