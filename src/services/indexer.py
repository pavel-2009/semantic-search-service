"""Build and store movie embeddings in Qdrant."""

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
from scraper.schemas import Movie, MoviesDocument

logger = logging.getLogger(__name__)
MAX_BATCH_SIZE = 100


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
        """Read and validate one JSON Lines movie record at a time."""
        logger.info("Loading movies: path=%s", filepath)

        if not filepath.exists():
            legacy_path = filepath.with_suffix(".json")
            if filepath.suffix == ".jsonl" and legacy_path.exists():
                logger.warning(
                    "JSON Lines file not found; reading legacy JSON file: path=%s",
                    legacy_path,
                )
                filepath = legacy_path
            else:
                logger.error("Movies file not found: path=%s", filepath)
                raise FileNotFoundError(f"File not found: {filepath}")

        return self._iter_movies(filepath)

    @staticmethod
    def _iter_movies(filepath: Path) -> Iterator[Movie]:
        with filepath.open(encoding="utf-8") as file:
            line_number = 0
            for first_line in file:
                line_number += 1
                if first_line.strip():
                    break
            else:
                return

            if first_line.lstrip().startswith("["):
                logger.warning("Reading legacy JSON array: path=%s", filepath)
                try:
                    movies = MoviesDocument.model_validate_json(
                        first_line + file.read()
                    ).root
                except ValidationError as exc:
                    raise ValueError(
                        "Movies JSON must contain a valid list of movies"
                    ) from exc
                yield from movies
                return

            try:
                yield Movie.model_validate_json(first_line)
            except ValidationError:
                logger.exception(
                    "Skipping invalid movie record: path=%s line=%d",
                    filepath,
                    line_number,
                )

            for line in file:
                line_number += 1
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
        batch_size = min(batch_size, MAX_BATCH_SIZE)

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
