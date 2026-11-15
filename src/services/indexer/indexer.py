"""Build and store movie embeddings in Qdrant."""

from collections.abc import Iterator
from itertools import chain
from pathlib import Path
from time import perf_counter

from pydantic import ValidationError

from core.contracts import IndexerStats, Movie
from core.logger import get_logger
from repositories.qdrant_repository import QdrantRepository
from services.indexer.config import config
from services.indexer.embedder import MovieEmbedder

logger = get_logger(__name__)
MAX_BATCH_SIZE = config.batch_size


class Indexer:
    """Index normalized movies in Qdrant."""

    def __init__(self) -> None:
        logger.info(
            "Initializing indexer: collection=%s model=%s",
            config.collection_name,
            config.model_name,
        )
        self.collection_name = config.collection_name
        self.repo = QdrantRepository(
            collection_name=config.collection_name,
            dense_dim=config.dense_dim,
        )
        self.embedder = MovieEmbedder(
            model_name=config.model_name,
            device=config.device,
            use_fp16=config.use_fp16,
            batch_size=config.batch_size,
            sparse_min_weight=config.sparse_min_weight,
            min_plot_len=config.min_plot_length,
        )
        logger.info("Indexer initialized")

    def create_collection(self, force_recreate: bool = False) -> None:
        """Create or recreate the Qdrant collection."""
        if force_recreate:
            self.repo.recreate_collection()
        else:
            self.repo.create_collection()

    def recreate(self) -> None:
        """Recreate the Qdrant collection."""
        self.repo.recreate_collection()

    def load_movies(self, filepath: Path = config.dataset_path) -> Iterator[Movie]:
        """Read and validate one JSON Lines movie record at a time."""
        logger.info("Loading movies: path=%s", filepath)

        if not filepath.exists():
            logger.error("Movies file not found: path=%s", filepath)
            raise FileNotFoundError(f"File not found: {filepath}")

        with filepath.open(encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    yield Movie.model_validate_json(line)
                except ValidationError:
                    logger.exception(
                        "Skipping invalid movie record: path=%s line=%d",
                        filepath,
                        line_number,
                    )

    def index_movies(
        self,
        filepath: Path = config.dataset_path,
        batch_size: int = config.batch_size,
        force_recreate: bool = False,
    ) -> None:
        """Create embeddings and upsert movies into Qdrant in batches."""
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero")
        batch_size = min(batch_size, MAX_BATCH_SIZE)

        started_at = perf_counter()
        logger.info(
            "Starting movie indexing: path=%s batch_size=%d force_recreate=%s",
            filepath,
            batch_size,
            force_recreate,
        )

        movies = self.load_movies(filepath)
        first_movie = next(movies, None)
        if first_movie is None:
            logger.error("No valid movies available for indexing: path=%s", filepath)
            raise RuntimeError(f"No movies available for indexing: {filepath}")

        self.create_collection(force_recreate=force_recreate)

        batch: list[Movie] = []
        total_processed = 0
        total_indexed = 0
        total_failed = 0

        for movie in chain((first_movie,), movies):
            total_processed += 1
            batch.append(movie)
            if len(batch) < batch_size:
                continue

            points = self.embedder.embed_batch(batch)
            indexed, failed = self.repo.upsert_points(points)
            total_indexed += indexed
            total_failed += failed
            batch = []

        if batch:
            points = self.embedder.embed_batch(batch)
            indexed, failed = self.repo.upsert_points(points)
            total_indexed += indexed
            total_failed += failed

        logger.info(
            "Indexing finished: processed=%d indexed=%d failed=%d duration_ms=%.1f",
            total_processed,
            total_indexed,
            total_failed,
            (perf_counter() - started_at) * 1000,
        )
        if total_failed:
            raise RuntimeError(f"Failed to index {total_failed} of {total_processed} movies")

    def get_stats(self) -> IndexerStats:
        """Return collection statistics."""
        logger.info("Fetching Qdrant collection stats: collection=%s", self.repo.collection_name)
        stats = self.repo.get_stats()
        logger.info(
            "Qdrant collection stats received: collection=%s points=%s status=%s",
            stats.collection,
            stats.points_count,
            stats.status,
        )
        return stats
