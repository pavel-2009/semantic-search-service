"""Shared embedding model loader."""

import logging
from time import perf_counter

from sentence_transformers import SentenceTransformer

from core.config import settings


logger = logging.getLogger(__name__)


class ModelLoader:
    """Load the embedding model once and reuse it across services."""

    _model: SentenceTransformer | None = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """Return the shared embedding model instance."""
        if cls._model is not None:
            logger.debug("Reusing embedding model: model=%s", settings.EMBEDDING_MODEL)
            return cls._model

        started_at = perf_counter()
        logger.info("Loading embedding model: model=%s", settings.EMBEDDING_MODEL)
        cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info(
            "Embedding model loaded: model=%s duration_ms=%.1f",
            settings.EMBEDDING_MODEL,
            (perf_counter() - started_at) * 1000,
        )
        return cls._model
