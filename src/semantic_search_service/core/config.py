"""Project configuration"""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Project config"""

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "movies"

    # Embedding model
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    MAX_TEXT_LENGTH: int = 2000

    # Data
    DATA_PATH: Path = Path("src/semantic_search_service/scraper/scraper/data/movies.json")

    # Indexing
    BATCH_SIZE: int = 32

    # Observability
    LOG_LEVEL: str = "INFO"
    
    # Poiskkino API
    POISKKINO_API_KEY: str = ""  

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()