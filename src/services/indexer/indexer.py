"""Build and store movie embeddings in Qdrant."""

import logging
from collections.abc import Iterator
from itertools import chain
from pathlib import Path
from time import perf_counter

from pydantic import ValidationError
from qdrant_client.http import models

from core.config import settings
from core.contracts import IndexerStats, MoviePayload
from core.model_loader import ModelLoader
from core.qdrant_client import QdrantClientSingleton
from core.text_normalizer import clean_text
from scraper.schemas import Movie
from services.indexer.embedder import MovieEmbedder
from services.indexer.config import config
from repositories.qdrant_repository import QdrantRepository

logger = logging.getLogger(__name__)
MAX_BATCH_SIZE = config.batch_size


class Indexer:
    """Index normalized movies in Qdrant."""

    def __init__(self) -> None:
        logger.info(
            "Initializing indexer: collection=%s model=%s",
            settings.QDRANT_COLLECTION,
            settings.EMBEDDING_MODEL,
        )
        self.repo = QdrantRepository()
        self.embedder = MovieEmbedder()
        logger.info("Indexer initialized")

    def recreate(self):
        self.repo.recreate()

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

    @staticmethod
    def _normalize_movie(movie: Movie) -> Movie:
        """Return a movie validated against the canonical movie contract."""
        return Movie.model_validate(movie)


    def index_movies(
        self,
        filepath: Path,
        batch_size: int = settings.BATCH_SIZE,
        force_recreate: bool = False,
    ) -> None:
        """Create embeddings and upsert movies into Qdrant."""
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero")
        batch_size = min(batch_size, MAX_BATCH_SIZE)

        movies = self.load_movies()

        for movie in movies:
            normalized_movie = self._normalize_movie(movie)

            self.repo.upsert_points(normalized_movie)

    def _upload_batch(self, points: list[models.PointStruct]) -> tuple[int, int]:
        """Upload a batch, isolating failed points if the batch request fails."""
        logger.info(
            "Uploading vectors to Qdrant: collection=%s points=%d",
            self.collection_name,
            len(points),
        )
        try:
            upsert_started_at = perf_counter()
            self.qdrant.upsert(collection_name=self.collection_name, points=points)
            logger.info(
                "Vectors uploaded: collection=%s points=%d duration_ms=%.1f",
                self.collection_name,
                len(points),
                (perf_counter() - upsert_started_at) * 1000,
            )
            return len(points), 0
        except Exception:
            logger.exception(
                "Failed to upsert batch; retrying points individually: collection=%s points=%d",
                self.collection_name,
                len(points),
            )

        indexed = 0
        failed = 0
        for point in points:
            try:
                self.qdrant.upsert(collection_name=self.collection_name, points=[point])
                indexed += 1
            except Exception:
                failed += 1
                logger.exception("Failed to upsert movie: movie_id=%s", point.id)
        return indexed, failed

    def get_stats(self) -> IndexerStats:
        """Return collection statistics."""
        logger.info("Fetching Qdrant collection stats: collection=%s", self.collection_name)
        collection_info = self.qdrant.get_collection(self.collection_name)
        logger.info(
            "Qdrant collection stats received: collection=%s points=%s status=%s",
            self.collection_name,
            collection_info.points_count,
            collection_info.status,
        )
        return IndexerStats(
            collection=self.collection_name,
            points_count=collection_info.points_count or 0,
            status=str(collection_info.status),
        )
