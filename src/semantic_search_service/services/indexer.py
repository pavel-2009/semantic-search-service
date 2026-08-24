"""Qdrant indexer"""

import json
from pathlib import Path
from typing import List, Dict, Any

from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

from text_cleaner import clean_text

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
