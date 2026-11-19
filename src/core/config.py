"""Single application configuration loaded from environment variables."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.device import get_compute_device

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEVICE = get_compute_device()


class Settings(BaseSettings):
    """Shared runtime, data, indexing, API and bot settings."""

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "movies"
    QDRANT_API_KEY: str = ""

    EMBEDDING_MODEL: str = str(PROJECT_ROOT / "bge-m3")
    EMBEDDING_DIM: int = 1024
    COMPUTE_DEVICE: str = Field(default_factory=get_compute_device)
    EMBEDDING_USE_FP16: bool = DEFAULT_DEVICE == "cuda"
    INDEX_BATCH_SIZE: int = 8 if DEFAULT_DEVICE == "mps" else 64
    SPARSE_MIN_WEIGHT: float = 0.08
    MIN_PLOT_LENGTH: int = 15
    INDEX_DATA_PATH: Path = PROJECT_ROOT / "src" / "scraper" / "data" / "movies.jsonl"

    MAX_TEXT_LENGTH: int = 2000
    DATA_PATH: Path = PROJECT_ROOT / "src" / "scraper" / "data" / "movies.jsonl"
    MAX_PAGES_SCRAPER: int = 100
    MAX_SCROLL_LIMIT: int = 10_000

    LOG_LEVEL: str = "INFO"
    POISKKINO_API_KEY: str = ""
    BOT_TOKEN: str = ""
    API_BASE_URL: str = "http://127.0.0.1:8000"

    MAX_RERANKED_DOCUMENTS: int = 10
    MAX_RETRIEVED_DOCUMENTS: int = 100

    @property
    def QDRANT_URL(self) -> str:
        """Return the configured Qdrant HTTP endpoint."""
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env" if (PROJECT_ROOT / ".env").exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
