"""Qdrant singleton client"""

import logging
from time import perf_counter

from qdrant_client import QdrantClient

from core.config import settings


logger = logging.getLogger(__name__)


class QdrantClientSingleton:
    """Qdrant singleton client"""

    _instance: QdrantClient | None = None

    @classmethod
    def get_client(cls) -> QdrantClient:
        if cls._instance is not None:
            logger.debug("Reusing existing Qdrant client")
            return cls._instance

        logger.info(
            "Creating Qdrant client: host=%s port=%s",
            settings.QDRANT_HOST,
            settings.QDRANT_PORT,
        )
        started_at = perf_counter()
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

        logger.info("Qdrant client created successfully: duration_ms=%.1f", (perf_counter() - started_at) * 1000)
        return cls._instance
