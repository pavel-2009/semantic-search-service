"""Application-level shared dependencies."""

from functools import lru_cache

from src.core.config import settings
from src.repositories.qdrant_repository import QdrantRepository
from src.services.indexer.embedder import MovieEmbedder
from src.services.search_service.parsing.text_parser import TextParser
from src.services.search_service.ranking.ranking import RerankingService
from src.services.search_service.search_service import SearchService


@lru_cache(maxsize=1)
def get_qdrant_repository() -> QdrantRepository:
    """Return the shared lightweight Qdrant repository."""
    return QdrantRepository(
        collection_name=settings.QDRANT_COLLECTION,
        dense_dim=settings.EMBEDDING_DIM,
    )


@lru_cache(maxsize=1)
def get_search_service() -> SearchService:
    """Return the shared SearchService instance."""
    return SearchService(
        parser=TextParser(),
        embedder=MovieEmbedder(
            model_name=settings.EMBEDDING_MODEL,
            device=settings.COMPUTE_DEVICE,
            use_fp16=settings.EMBEDDING_USE_FP16,
            batch_size=settings.INDEX_BATCH_SIZE,
            sparse_min_weight=settings.SPARSE_MIN_WEIGHT,
            min_plot_len=settings.MIN_PLOT_LENGTH,
        ),
        qdrant_repo=QdrantRepository(
            collection_name=settings.QDRANT_COLLECTION,
            dense_dim=settings.EMBEDDING_DIM,
        ),
        reranker=RerankingService(device=settings.COMPUTE_DEVICE),
    )
