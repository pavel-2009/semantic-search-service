"""Shared embedding model loader."""

import os
from time import perf_counter

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from sentence_transformers import SentenceTransformer  # noqa: E402
from tenacity import retry, stop_after_attempt, wait_exponential  # noqa: E402

from core.config import PROJECT_ROOT, settings  # noqa: E402
from core.logger import get_logger  # noqa: E402

logger = get_logger(__name__)
LOCAL_BGE_MODEL_PATH = PROJECT_ROOT / "bge-m3"


class ModelLoader:
    """Load the embedding model once and reuse it across services."""

    _model: SentenceTransformer | None = None

    @classmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def get_model(cls) -> SentenceTransformer:
        """Return the shared embedding model instance, retrying failed loads."""
        model_path = (
            str(LOCAL_BGE_MODEL_PATH)
            if LOCAL_BGE_MODEL_PATH.exists()
            else settings.EMBEDDING_MODEL
        )
        if cls._model is not None:
            logger.debug("Reusing embedding model: model=%s", model_path)
            return cls._model

        started_at = perf_counter()
        logger.info("Loading embedding model: model=%s", model_path)
        cls._model = SentenceTransformer(model_path, local_files_only=LOCAL_BGE_MODEL_PATH.exists())
        logger.info(
            "Embedding model loaded: model=%s duration_ms=%.1f",
            model_path,
            (perf_counter() - started_at) * 1000,
        )
        return cls._model
