"""Script for running the Qdrant indexer."""

from src.core.logger import get_logger, setup_logging
from src.core.config import settings
from src.services.indexer.indexer import Indexer

logger = get_logger(__name__)


def main() -> None:
    """Run the indexer and log the resulting collection statistics."""
    setup_logging()
    logger.info(
        "Starting indexer run: dataset=%s qdrant=%s collection=%s model=%s batch_size=%d",
        settings.INDEX_DATA_PATH,
        settings.QDRANT_URL,
        settings.QDRANT_COLLECTION,
        settings.EMBEDDING_MODEL,
        settings.INDEX_BATCH_SIZE,
    )

    indexer = Indexer()
    indexer.index_movies(
        filepath=settings.INDEX_DATA_PATH,
        batch_size=settings.INDEX_BATCH_SIZE,
        force_recreate=True,
    )

    stats = indexer.get_stats()
    logger.info(
        "Indexing completed successfully: collection=%s points=%d status=%s",
        stats.collection,
        stats.points_count,
        stats.status,
    )


if __name__ == "__main__":
    main()
