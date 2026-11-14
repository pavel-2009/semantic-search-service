"""Build and store movie embeddings in Qdrant."""

import logging
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from core.contracts import IndexerStats
from repositories.qdrant_repository import QdrantRepository
from services.indexer.config import config
from services.indexer.embedder import MovieEmbedder
from services.indexer.schemas import MovieCard

logger = logging.getLogger(__name__)
MAX_BATCH_SIZE = config.batch_size


class Indexer:
    """Index normalized movies in Qdrant."""

    def __init__(self) -> None:
        logger.info(
            "Initializing indexer: collection=%s model=%s",
            config.collection_name,
            config.model_name,
        )
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

    def recreate(self) -> None:
        """Recreate the Qdrant collection."""
        self.repo.recreate_collection()

    def load_movies(self, filepath: Path = config.dataset_path) -> Iterator[MovieCard]:
        """Read and validate one JSON Lines movie card record at a time."""
        logger.info("Loading movies: path=%s", filepath)

        if not filepath.exists():
            logger.error("Movies file not found: path=%s", filepath)
            raise FileNotFoundError(f"File not found: {filepath}")

        with filepath.open(encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    yield MovieCard.model_validate_json(line)
                except ValidationError:
                    logger.exception(
                        "Skipping invalid movie record: path=%s line=%d",
                        filepath,
                        line_number,
                    )

    @staticmethod
    def _normalize_movie(movie: MovieCard) -> MovieCard:
        """Return a movie validated against the canonical movie card contract."""
        return MovieCard.model_validate(movie)

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

        if force_recreate:
            self.repo.recreate_collection()
        else:
            self.repo.create_collection()

        batch: list[MovieCard] = []
        for movie in self.load_movies(filepath):
            batch.append(self._normalize_movie(movie))
            if len(batch) >= batch_size:
                points = self.embedder.embed_batch(batch)
                self.repo.upsert_points(points)
                batch = []

        if batch:
            points = self.embedder.embed_batch(batch)
            self.repo.upsert_points(points)

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
