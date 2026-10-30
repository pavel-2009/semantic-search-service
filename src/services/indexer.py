"""Build and store movie embeddings in Qdrant."""

import json
import logging
from collections.abc import Iterator
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

logger = logging.getLogger(__name__)


class Indexer:
    """Index normalized movies in Qdrant."""

    def __init__(self) -> None:
        logger.info(
            "Initializing indexer: collection=%s model=%s",
            settings.QDRANT_COLLECTION,
            settings.EMBEDDING_MODEL,
        )
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

        logger.info(
            "Creating Qdrant collection: collection=%s vector_size=%d distance=cosine",
            self.collection_name,
            self.embedding_dim,
        )
        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.embedding_dim,
                distance=models.Distance.COSINE,
            ),
        )
        logger.info("Qdrant collection created: collection=%s", self.collection_name)

    def load_movies(self, filepath: Path) -> Iterator[Movie]:
        """Stream and validate movies from a JSON array."""
        logger.info("Loading movies: path=%s", filepath)

        if not filepath.exists():
            logger.error("Movies file not found: path=%s", filepath)
            raise FileNotFoundError(f"File not found: {filepath}")

        return self._iter_movies(filepath)

    @staticmethod
    def _iter_movies(filepath: Path) -> Iterator[Movie]:
        decoder = json.JSONDecoder()
        buffer = ""
        position = 0
        eof = False

        with filepath.open(encoding="utf-8") as file:
            def read_more() -> None:
                nonlocal buffer, position, eof
                chunk = file.read(64 * 1024)
                buffer = buffer[position:] + chunk
                position = 0
                eof = not chunk

            def skip_whitespace() -> None:
                nonlocal position
                while True:
                    while position < len(buffer) and buffer[position].isspace():
                        position += 1
                    if position < len(buffer) or eof:
                        return
                    read_more()

            def read_value() -> object:
                nonlocal position
                while True:
                    try:
                        value, position = decoder.raw_decode(buffer, position)
                        return value
                    except json.JSONDecodeError as exc:
                        if eof:
                            raise ValueError("Movies JSON contains invalid data") from exc
                        read_more()

            skip_whitespace()
            if position == len(buffer):
                raise ValueError("Movies JSON must contain a list of movies")
            if buffer[position] != "[":
                raise ValueError("Movies JSON must contain a list of movies")
            position += 1
            first = True

            while True:
                skip_whitespace()
                if position == len(buffer):
                    raise ValueError("Movies JSON contains an unterminated list")
                if buffer[position] == "]":
                    position += 1
                    break
                if not first:
                    if buffer[position] != ",":
                        raise ValueError("Movies JSON must separate movies with commas")
                    position += 1
                    skip_whitespace()
                    if position == len(buffer) or buffer[position] == "]":
                        raise ValueError("Movies JSON contains a trailing comma")

                try:
                    yield Movie.model_validate(read_value())
                except ValidationError as exc:
                    logger.error("Invalid movie record in %s: %s", filepath, exc)
                    raise ValueError("Movies JSON contains an invalid movie record") from exc
                first = False

            while True:
                skip_whitespace()
                if position < len(buffer):
                    raise ValueError("Movies JSON contains data after the movie list")
                if eof:
                    break
                read_more()

    @staticmethod
    def _normalize_movie(movie: Movie) -> Movie:
        """Return a movie validated against the canonical movie contract."""
        return Movie.model_validate(movie)

    def prepare_text(self, movie: Movie) -> str:
        """Build the text used for movie embeddings."""
        parts: list[str] = []

        title_field = Movie.model_fields.get("title")
        if movie.title and title_field and movie.title != title_field.default:
            has_details = any(
                value not in (None, "", [], {})
                for value in (
                    movie.description,
                    movie.director,
                    movie.country,
                    movie.year,
                    movie.rating,
                    movie.actors,
                    movie.genres,
                )
            )
            label = "Название:" if has_details else "Название"
            parts.append(f"{label} {movie.title}")
        if movie.description:
            parts.append(f"Описание: {movie.description}")
        if movie.director:
            parts.append(f"Режиссёр: {movie.director}")
        if movie.country:
            parts.append(f"Страна: {movie.country}")
        if movie.year is not None:
            parts.append(f"Год: {movie.year}")
        if movie.rating is not None:
            parts.append(f"Рейтинг: {movie.rating}")
        if movie.actors:
            parts.append(f"Актёры: {', '.join(movie.actors)}")
        if movie.genres:
            parts.append(f"Жанры: {', '.join(movie.genres)}")

        cleaned = clean_text(". ".join(parts), preserve_punctuation=True)
        if not cleaned:
            logger.warning("Empty text for movie %d", movie.id)
            cleaned = "Фильм без описания."
        return cleaned[: settings.MAX_TEXT_LENGTH]

    def index_movies(self, filepath: Path, batch_size: int = settings.BATCH_SIZE) -> None:
        """Create embeddings and upsert movies into Qdrant."""
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero")

        started_at = perf_counter()
        logger.info("Starting movie indexing: path=%s batch_size=%d", filepath, batch_size)
        movies = self.load_movies(filepath)
        self.create_collection()
        batch: list[models.PointStruct] = []
        total_processed = 0
        total_indexed = 0
        total_failed = 0

        for movie in movies:
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
        if total_processed == 0:
            logger.warning("No movies available for indexing: path=%s", filepath)
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
