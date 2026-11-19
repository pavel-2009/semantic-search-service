"""Build and store movie embeddings in Qdrant."""

from collections.abc import Iterator
from itertools import chain
from pathlib import Path
from time import perf_counter

from pydantic import ValidationError

from src.core.contracts import EnrichedMovie, IndexerStats
from src.core.logger import get_logger
from src.core.config import settings
from src.repositories.qdrant_repository import QdrantRepository
from src.services.indexer.embedder import MovieEmbedder

logger = get_logger(__name__)
MAX_BATCH_SIZE = settings.INDEX_BATCH_SIZE


class Indexer:
    """Index normalized movies in Qdrant."""

    def __init__(self) -> None:
        logger.info(
            "Initializing indexer: collection=%s model=%s",
            settings.QDRANT_COLLECTION,
            settings.EMBEDDING_MODEL,
        )
        self.collection_name = settings.QDRANT_COLLECTION
        self.repo = QdrantRepository(
            collection_name=settings.QDRANT_COLLECTION,
            dense_dim=settings.EMBEDDING_DIM,
        )
        self.embedder = MovieEmbedder(
            model_name=settings.EMBEDDING_MODEL,
            device=settings.COMPUTE_DEVICE,
            use_fp16=settings.EMBEDDING_USE_FP16,
            batch_size=settings.INDEX_BATCH_SIZE,
            sparse_min_weight=settings.SPARSE_MIN_WEIGHT,
            min_plot_len=settings.MIN_PLOT_LENGTH,
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

    def load_movies(self, filepath: Path = settings.INDEX_DATA_PATH) -> Iterator[EnrichedMovie]:
        """Read and validate canonical movie records from a JSON Lines file."""
        logger.info("Loading movies: path=%s", filepath)

        if not filepath.exists():
            logger.error("Movies file not found: path=%s", filepath)
            raise FileNotFoundError(f"File not found: {filepath}")

        with filepath.open(encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    yield EnrichedMovie.model_validate_json(line)
                except ValidationError:
                    logger.exception(
                        "Skipping invalid movie record: path=%s line=%d",
                        filepath,
                        line_number,
                    )

    def index_movies(
        self,
        filepath: Path = settings.INDEX_DATA_PATH,
        batch_size: int = settings.INDEX_BATCH_SIZE,
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

        batch: list[EnrichedMovie] = []
        total_processed = 0
        total_indexed = 0
        total_failed = 0

        for movie in chain((first_movie,), movies):
            total_processed += 1
            batch.append(movie)
            if len(batch) < batch_size:
                continue

            points = self.embedder.embed_cards(batch)
            indexed, failed = self.repo.upsert_points(points)
            total_indexed += indexed
            total_failed += failed
            batch = []

        if batch:
            points = self.embedder.embed_cards(batch)
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
