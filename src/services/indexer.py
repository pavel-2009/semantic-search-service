"""Build and store movie embeddings in Qdrant."""

import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Any

from qdrant_client.http import models

from core.config import settings
from core.model_loader import ModelLoader
from core.qdrant_client import QdrantClientSingleton
from core.text_normalizer import clean_text


logger = logging.getLogger(__name__)


class Indexer:
    """Index normalized movies in Qdrant."""

    def __init__(self) -> None:
        logger.info("Initializing indexer: collection=%s model=%s", settings.QDRANT_COLLECTION, settings.EMBEDDING_MODEL)

        self.qdrant = QdrantClientSingleton.get_client()
        self.collection_name = settings.QDRANT_COLLECTION
        self.model = ModelLoader.get_model()
        self.embedding_dim = settings.EMBEDDING_DIM

        logger.info("Indexer initialized: embedding_dim=%d", self.embedding_dim)

    def create_collection(self, force_recreate: bool = False) -> None:
        """Create the collection if it does not exist."""
        logger.info("Checking Qdrant collection: %s", self.collection_name)

        if force_recreate:
            self.recreate_collection()
            return

        collections = self.qdrant.get_collections().collections
        if any(collection.name == self.collection_name for collection in collections):
            logger.info("Collection already exists: %s", self.collection_name)
            return

        logger.info("Creating Qdrant collection: collection=%s vector_size=%d distance=cosine", self.collection_name, self.embedding_dim)

        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.embedding_dim,
                distance=models.Distance.COSINE,
            ),
        )

        logger.info("Qdrant collection created: collection=%s", self.collection_name)

    def load_movies(self, filepath: Path) -> list[dict[str, Any]]:
        """Load normalized movies from JSON."""
        logger.info("Loading movies: path=%s", filepath)
        
        if not filepath.exists():
            logger.error("Movies file not found: path=%s", filepath)
            raise FileNotFoundError(f"File not found: {filepath}")

        started_at = perf_counter()
        with filepath.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            logger.error("Invalid movies JSON: expected list, got=%s", type(data).__name__)
            raise ValueError("Movies JSON must contain a list")

        movies = [self._normalize_movie(movie) for movie in data if isinstance(movie, dict)]
        logger.info("Movies loaded: path=%s count=%d duration_ms=%.1f", filepath, len(movies), (perf_counter() - started_at) * 1000)
        return movies

    @staticmethod
    def _normalize_movie(movie: dict[str, Any]) -> dict[str, Any]:
        """Convert legacy scraper keys to the canonical movie contract."""
        normalized = dict(movie)
        normalized["title"] = movie.get("title") or movie.get("name") or ""
        normalized["genres"] = movie.get("genres") or movie.get("tags") or []
        normalized["countries"] = [
            country.strip()
            for country in str(movie.get("country") or "").split(",")
            if country.strip()
        ]
        normalized.pop("name", None)
        normalized.pop("tags", None)
        return normalized

    def prepare_text(self, movie: dict[str, Any]) -> str:
        """Build the text used for movie embeddings."""
        parts: list[str] = []

        if movie.get("title"):
            has_details = any(
                movie.get(field) is not None and movie.get(field) != ""
                for field in ("description", "director", "country", "year", "rating", "actors", "genres")
            )
            label = "Название:" if has_details else "Название"
            parts.append(f"{label} {movie['title']}")
        if movie.get("description"):
            parts.append(f"Описание: {movie['description']}")
        if movie.get("director"):
            parts.append(f"Режиссёр: {movie['director']}")
        if movie.get("country"):
            parts.append(f"Страна: {movie['country']}")
        if movie.get("year") is not None:
            parts.append(f"Год: {movie['year']}")
        if movie.get("rating") is not None:
            parts.append(f"Рейтинг: {movie['rating']}")
        if movie.get("actors"):
            parts.append(f"Актёры: {', '.join(map(str, movie['actors']))}")
        if movie.get("genres"):
            parts.append(f"Жанры: {', '.join(map(str, movie['genres']))}")

        cleaned = clean_text(". ".join(parts), preserve_punctuation=True)
        if not cleaned:
            logger.warning(f"Empty text for movie {movie.get('id')}")
            cleaned = "Фильм без описания."
        return cleaned[:settings.MAX_TEXT_LENGTH]

    def index_movies(self, filepath: Path, batch_size: int = settings.BATCH_SIZE) -> None:
        """Create embeddings and upsert movies into Qdrant."""
        started_at = perf_counter()
        logger.info("Starting movie indexing: path=%s batch_size=%d", filepath, batch_size)
        self.create_collection()
        movies = self.load_movies(filepath)

        if not movies:
            logger.warning("No movies available for indexing: path=%s", filepath)
            return

        existing_points, _ = self.qdrant.scroll(
            collection_name=self.collection_name,
            limit=settings.MAX_SCROLL_LIMIT,
            with_payload=False,
            with_vectors=False,
        )
        existing_ids = {point.id for point in existing_points}
        logger.info("Existing Qdrant points loaded: collection=%s count=%d", self.collection_name, len(existing_ids))

        total = len(movies)
        total_indexed = 0
        logger.info("Indexing started: total_movies=%d batch_size=%d", total, batch_size)

        for start in range(0, total, batch_size):
            batch = movies[start : start + batch_size]
            batch_started_at = perf_counter()
            points: list[models.PointStruct] = []
            skipped = 0

            logger.info("Processing batch: range=%d-%d size=%d", start + 1, min(start + len(batch), total), len(batch))

            for movie in batch:
                movie_id = movie.get("id")
                if movie_id is None:
                    skipped += 1
                    logger.warning("Skipping movie without id")
                    continue

                point_id = int(movie_id)
                if point_id in existing_ids:
                    skipped += 1
                    logger.debug("Skipping existing movie: movie_id=%d", point_id)
                    continue

                text = self.prepare_text(movie)
                vector_started_at = perf_counter()
                vector = self.model.encode(text).tolist()
                logger.debug("Vector created: movie_id=%s text_length=%d vector_dim=%d duration_ms=%.1f", movie_id, len(text), len(vector), (perf_counter() - vector_started_at) * 1000)
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "id": point_id,
                            "title": movie.get("title", ""),
                            "year": movie.get("year"),
                            "country": movie.get("country"),
                            "countries": movie.get("countries", []),
                            "director": movie.get("director"),
                            "description": movie.get("description", ""),
                            "actors": movie.get("actors", []),
                            "genres": movie.get("genres", []),
                            "rating": movie.get("rating"),
                            "poster_url": movie.get("poster_url"),
                        },
                    )
                )
                existing_ids.add(point_id)

            if points:
                logger.info("Uploading vectors to Qdrant: collection=%s points=%d", self.collection_name, len(points))
                try:
                    upsert_started_at = perf_counter()
                    self.qdrant.upsert(collection_name=self.collection_name, points=points)
                    logger.info("Vectors uploaded: collection=%s points=%d duration_ms=%.1f", self.collection_name, len(points), (perf_counter() - upsert_started_at) * 1000)
                except Exception:
                    logger.exception("Failed to upsert batch: collection=%s points=%d", self.collection_name, len(points))

            total_indexed += len(points)
            logger.debug("Batch completed: processed=%d/%d indexed=%d skipped=%d duration_ms=%.1f", min(start + len(batch), total), total, total_indexed, skipped, (perf_counter() - batch_started_at) * 1000)

        logger.info("Indexing finished: indexed=%d total=%d duration_ms=%.1f", total_indexed, total, (perf_counter() - started_at) * 1000)

    def get_stats(self) -> dict[str, Any]:
        """Return collection statistics."""
        logger.info("Fetching Qdrant collection stats: collection=%s", self.collection_name)
        collection_info = self.qdrant.get_collection(self.collection_name)
        logger.info("Qdrant collection stats received: collection=%s points=%s status=%s", self.collection_name, collection_info.points_count, collection_info.status)
        return {
            "collection": self.collection_name,
            "points_count": collection_info.points_count,
            "status": collection_info.status,
        }

    def clear_collection(self) -> None:
        """Delete the collection."""
        logger.info("Deleting Qdrant collection: collection=%s", self.collection_name)
        self.qdrant.delete_collection(self.collection_name)
        logger.info("Qdrant collection deleted: collection=%s", self.collection_name)

    def recreate_collection(self) -> None:
        """Delete and recreate the collection."""
        logger.info("Recreating Qdrant collection: collection=%s", self.collection_name)
        self.clear_collection()
        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.embedding_dim,
                distance=models.Distance.COSINE,
            ),
        )
        logger.info("Qdrant collection recreated: collection=%s", self.collection_name)
