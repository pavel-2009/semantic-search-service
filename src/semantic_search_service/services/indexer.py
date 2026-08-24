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

    
