"""Application-level shared dependencies."""

from functools import lru_cache

from src.repositories.qdrant_repository import QdrantRepository
from src.services.indexer.config import config
from src.services.indexer.embedder import MovieEmbedder
from src.services.search_service.parsing.text_parser import TextParser
from src.services.search_service.ranking.ranking import RerankingService
from src.services.search_service.search_service import SearchService


@lru_cache(maxsize=1)
def get_search_service() -> SearchService:
    """Return the shared SearchService instance."""
    return SearchService(
        parser=TextParser(),
        embedder=MovieEmbedder(
            model_name=config.model_name,
            device=config.device,
            use_fp16=config.use_fp16,
            batch_size=config.batch_size,
            sparse_min_weight=config.sparse_min_weight,
            min_plot_len=config.min_plot_length,
        ),
        qdrant_repo=QdrantRepository(
            collection_name=config.collection_name,
            dense_dim=config.dense_dim,
        ),
        reranker=RerankingService(device=config.device),
    )
