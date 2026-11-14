"""Script for running the Qdrant indexer."""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.core.logger import get_logger, setup_logging  # noqa: E402
from src.services.indexer.config import config  # noqa: E402
from src.services.indexer.indexer import Indexer  # noqa: E402

logger = get_logger(__name__)


def main() -> None:
    """Run the indexer and log the resulting collection statistics."""
    setup_logging()
    logger.info(
        "Starting indexer run: dataset=%s qdrant=%s collection=%s model=%s batch_size=%d",
        config.dataset_path,
        config.qdrant_url,
        config.collection_name,
        config.model_name,
        config.batch_size,
    )

    indexer = Indexer()
    indexer.index_movies(
        filepath=config.dataset_path,
        batch_size=config.batch_size,
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
