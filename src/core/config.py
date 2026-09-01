"""Project configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "movies"

    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM: int = 384
    MAX_TEXT_LENGTH: int = 2000
    BATCH_SIZE: int = 32

    DATA_PATH: Path = Path(__file__).resolve().parents[1] / "scraper" / "data" / "movies.json"
    MAX_PAGES_SCRAPER: int = 100

    LOG_LEVEL: str = "INFO"
    POISKKINO_API_KEY: str = ""
    BOT_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
