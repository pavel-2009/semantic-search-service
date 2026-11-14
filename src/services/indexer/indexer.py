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

    def load_movies(self, filepath: Path) -> Iterator[Movie]:
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

        started_at = perf_counter()
        logger.info("Starting movie indexing: path=%s batch_size=%d", filepath, batch_size)
        movies = self.load_movies(filepath)
        first_movie = next(movies, None)
        if first_movie is None:
            logger.error("No valid movies available for indexing: path=%s", filepath)
            raise RuntimeError(f"No movies available for indexing: {filepath}")

        self.create_collection(force_recreate=force_recreate)
        batch: list[models.PointStruct] = []
        total_processed = 0
        total_indexed = 0
        total_failed = 0

        for movie in chain((first_movie,), movies):
            total_processed += 1
            try:
                text = self.prepare_text(movie)
                vector_started_at = perf_counter()
                vector = self.model.encode(text).tolist()
                logger.debug(
                    "Vector created: movie_id=%d text_length=%d vector_dim=%d duration_ms=%.1f",
                    movie.id,
                    len(text),
                    len(vector),
                    (perf_counter() - vector_started_at) * 1000,
                )
                countries = [
                    country.strip()
                    for country in (movie.country or "").split(",")
                    if country.strip()
                ]
                payload = MoviePayload(
                    id=movie.id,
                    title=movie.title,
                    year=movie.year,
                    country=movie.country,
                    countries=countries,
                    director=movie.director,
                    description=movie.description,
                    actors=movie.actors,
                    genres=movie.genres,
                    rating=movie.rating,
                    poster_url=movie.poster_url,
                )
                point = models.PointStruct(
                    id=movie.id,
                    vector=vector,
                    payload=payload.model_dump(),
                )
            except Exception:
                total_failed += 1
                logger.exception("Failed to prepare movie: movie_id=%d", movie.id)
                continue

            batch.append(point)
            if len(batch) < batch_size:
                continue

            indexed, failed = self._upload_batch(batch)
            total_indexed += indexed
            total_failed += failed
            batch = []

        if batch:
            indexed, failed = self._upload_batch(batch)
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
