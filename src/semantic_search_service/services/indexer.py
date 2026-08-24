"""Qdrant indexer"""

import json
from pathlib import Path
from typing import List, Dict, Any

from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

from text_cleaner import clean_text # type: ignore

from src.semantic_search_service.core.qdrant_client import QdrantClientSingleton
from src.semantic_search_service.core.config import settings


class Indexer:
    """Qdrant indexer"""

    def __init__(self) -> None:
        self.qdrant = QdrantClientSingleton.get_client()
        self.collection_name = settings.QDRANT_COLLECTION
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        self.embedding_dim = settings.EMBEDDING_DIM

    def create_collection(self) -> None:
        """Creats the collection if it doesn't exist"""

        collections = self.qdrant.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if exists:
            print(f"⚠️ Collection '{self.collection_name}' already exists")
            return

        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.embedding_dim,
                distance=models.Distance.COSINE
            )
        )

        print(f"✅ Collection '{self.collection_name}' created")

    def load_movies(self, filepath: Path) -> List[Dict[str, Any]]:
        """Load films from JSON"""
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"📦 Loaded {len(data)} films from {filepath}")
        return data

    def prepare_text(self, movie: Dict[str, Any]) -> str:
        """Formatting clean text from json"""
        parts: List[str] = []

        if movie.get("title"):
            parts.append(f"Название: {movie['title']}")

        if movie.get("description"):
            parts.append(f"Описание: {movie['description']}")

        if movie.get("director"):
            parts.append(f"Режиссёр: {movie['director']}")

        if movie.get("country"):
            parts.append(f"Страна: {movie['country']}")

        if movie.get("year"):
            parts.append(f"Год: {movie['year']}")

        if movie.get("rating"):
            parts.append(f"Рейтинг: {movie['rating']}")

        if movie.get("actors"):
            parts.append(f"Актёры: {', '.join(movie['actors'])}")

        if movie.get("tags"):
            parts.append(f"Теги: {', '.join(movie['tags'])}")

        raw_text = ". ".join(parts)

        cleaned: str = clean_text(raw_text) # type: ignore

        # Ограничиваем длину
        if len(cleaned) > settings.MAX_TEXT_LENGTH: # type: ignore
            cleaned = cleaned[:settings.MAX_TEXT_LENGTH] # type: ignore

        return cleaned # type: ignore
