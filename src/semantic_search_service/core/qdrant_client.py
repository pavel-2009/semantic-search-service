"""Qdrant singleton client"""

import logging

from qdrant_client import QdrantClient

from semantic_search_service.core.config import settings


logger = logging.getLogger(__name__)


class QdrantClientSingleton:
    """Qdrant singleton client"""

    _instance: QdrantClient | None = None

    @classmethod
    def get_client(cls) -> QdrantClient:
        if cls._instance is None:
            logger.info(
                "Creating Qdrant client: host=%s port=%s",
                settings.QDRANT_HOST,
                settings.QDRANT_PORT,
            )
            try:
                cls._instance = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                )
            except Exception:
                logger.exception(
                    "Failed to create Qdrant client: host=%s port=%s",
                    settings.QDRANT_HOST,
                    settings.QDRANT_PORT,
                )
                raise
            logger.info("Qdrant client created successfully")
        return cls._instance
