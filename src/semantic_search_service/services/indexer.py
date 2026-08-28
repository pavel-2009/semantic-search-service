"""Build and store movie embeddings in Qdrant."""

import json
from pathlib import Path
from typing import Any

from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

from text_cleaner import clean_text  # type: ignore

from semantic_search_service.core.config import settings
from semantic_search_service.core.qdrant_client import QdrantClientSingleton


class Indexer:
    """Index normalized movies in Qdrant."""

    def __init__(self) -> None:
        self.qdrant = QdrantClientSingleton.get_client()
        self.collection_name = settings.QDRANT_COLLECTION
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.embedding_dim = settings.EMBEDDING_DIM

    def create_collection(self) -> None:
        """Create the collection if it does not exist."""
        collections = self.qdrant.get_collections().collections
        if any(collection.name == self.collection_name for collection in collections):
            print(f"⚠️ Collection '{self.collection_name}' already exists")
            return

        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.embedding_dim,
                distance=models.Distance.COSINE,
            ),
        )
        print(f"✅ Collection '{self.collection_name}' created")

    def load_movies(self, filepath: Path) -> list[dict[str, Any]]:
        """Load normalized movies from JSON."""
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        with filepath.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError("Movies JSON must contain a list")

        movies = [movie for movie in data if isinstance(movie, dict)]
        print(f"📦 Loaded {len(movies)} films from {filepath}")
        return movies

    def prepare_text(self, movie: dict[str, Any]) -> str:
        """Build the text used for movie embeddings."""
        parts: list[str] = []

        if movie.get("title"):
            parts.append(f"Название: {movie['title']}")
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

        cleaned = clean_text(". ".join(parts))  # type: ignore
        return cleaned[:settings.MAX_TEXT_LENGTH]

    def index_movies(
        self,
        filepath: Path,
        batch_size: int = settings.BATCH_SIZE,
    ) -> None:
        """Create embeddings and upsert movies into Qdrant."""
        self.create_collection()
        movies = self.load_movies(filepath)

        if not movies:
            print("❌ No data for indexing")
            return

        total = len(movies)
        print(f"🔄 Started indexing {total} films...")

        for start in range(0, total, batch_size):
            batch = movies[start : start + batch_size]
            points: list[models.PointStruct] = []

            for movie in batch:
                movie_id = movie.get("id")
                if movie_id is None:
                    continue

                vector = self.model.encode(self.prepare_text(movie)).tolist()
                points.append(
                    models.PointStruct(
                        id=int(movie_id),
                        vector=vector,
                        payload={
                            "id": int(movie_id),
                            "name": movie.get("name", ""),
                            "year": movie.get("year"),
                            "country": movie.get("country"),
                            "director": movie.get("director"),
                            "description": movie.get("description", ""),
                            "actors": movie.get("actors", []),
                            "tags": movie.get("tags", []),
                            "rating": movie.get("rating"),
                        },
                    )
                )

            if points:
                self.qdrant.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )

            print(f"  ✅ Loaded {min(start + len(batch), total)}/{total} films")

        print(f"🎉 Indexing finished. Total: {total} films")

    def get_stats(self) -> dict[str, Any]:
        """Return collection statistics."""
        collection_info = self.qdrant.get_collection(self.collection_name)
        return {
            "collection": self.collection_name,
            "points_count": collection_info.points_count,
            "status": collection_info.status,
        }

    def clear_collection(self) -> None:
        """Delete the collection."""
        self.qdrant.delete_collection(self.collection_name)
        print(f"🗑️ Collection '{self.collection_name}' deleted")

    def recreate_collection(self) -> None:
        """Delete and recreate the collection."""
        self.clear_collection()
        self.create_collection()
        print(f"🔄 Collection '{self.collection_name}' recreated")
