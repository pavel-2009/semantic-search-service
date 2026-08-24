"""Qdrant singleton client"""

from qdrant_client import QdrantClient
from semantic_search_service.core.config import settings


class QdrantClientSingleton:
    """Qdrant singleton client"""

    _instance: QdrantClient | None = None

    @classmethod
    def get_client(cls) -> QdrantClient:
        if cls._instance is None:
            cls._instance = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT
            )
        return cls._instance
