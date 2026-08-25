"""Service for semantic search in Qdrant"""

import logging
from time import perf_counter
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

from text_cleaner import clean_text  # type: ignore

from semantic_search_service.backend.schemas import MovieResult, SearchFilters, SearchRequest
from semantic_search_service.core.config import settings
from semantic_search_service.core.qdrant_client import QdrantClientSingleton


logger = logging.getLogger(__name__)


class SearchService:
    """Semantic search service for searching similar films in Qdrant"""

    def __init__(self):
        self.collection_name = settings.QDRANT_COLLECTION
        logger.info("Initializing search service: collection=%s", self.collection_name)

        try:
            self.qdrant: QdrantClient = QdrantClientSingleton.get_client()
        except Exception:
            logger.exception("Search service initialization failed while creating Qdrant client")
            raise

        started_at = perf_counter()
        logger.info("Loading embedding model: name=%s", settings.EMBEDDING_MODEL)
        try:
            self.model: SentenceTransformer = SentenceTransformer(settings.EMBEDDING_MODEL)
        except Exception:
            logger.exception("Embedding model loading failed: name=%s", settings.EMBEDDING_MODEL)
            raise
        logger.info(
            "Embedding model loaded: name=%s duration_ms=%.1f",
            settings.EMBEDDING_MODEL,
            (perf_counter() - started_at) * 1000,
        )

    def search(self, request: SearchRequest) -> List[MovieResult]:
        """Search films with request conditions"""

        logger.info(
            "Search started: collection=%s query_length=%d top_k=%d has_filters=%s",
            self.collection_name,
            len(request.query),
            request.top_k,
            request.filters is not None,
        )

        started_at = perf_counter()
        try:
            cleaned_query: str = clean_text(request.query)  # type: ignore
            logger.debug(
                        "Text cleaned: original_length=%d cleaned_length=%d duration_ms=%.1f",
                        len(request.query),
                        len(cleaned_query),  # type: ignore
                        (perf_counter() - started_at) * 1000,
                    )
            
        except Exception:
            logger.exception("Text cleaning failed: query_length=%d", len(request.query))
            raise
        
        started_at = perf_counter()
        try:
            vector = self.model.encode(cleaned_query).tolist()  # type: ignore
        except Exception:
            logger.exception(
                "Query embedding failed: model=%s cleaned_query_length=%d",
                settings.EMBEDDING_MODEL,
                len(cleaned_query),  # type: ignore
            )
            raise
        logger.debug(
            "Query embedded: vector_dimension=%d duration_ms=%.1f",
            len(vector),
            (perf_counter() - started_at) * 1000,
        )

        try:
            query_filter = self._build_filters(request.filters) if request.filters else None
        except Exception:
            logger.exception("Building Qdrant filters failed: filters=%s", request.filters)
            raise

        started_at = perf_counter()
        try:
            search_result = self.qdrant.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=request.top_k,
                query_filter=query_filter,
                with_payload=True,
            )
        except Exception:
            logger.exception(
                "Qdrant search failed: collection=%s top_k=%d has_filters=%s",
                self.collection_name,
                request.top_k,
                query_filter is not None,
            )
            raise
        logger.info(
            "Qdrant search completed: collection=%s result_count=%d duration_ms=%.1f",
            self.collection_name,
            len(search_result.points),
            (perf_counter() - started_at) * 1000,
        )

        try:
            return [
                MovieResult(
                    id=point.id,  # type: ignore
                    title=point.payload.get("title", ""),  # type: ignore
                    year=point.payload.get("year"),  # type: ignore
                    rating=point.payload.get("rating"),  # type: ignore
                    genres=point.payload.get("genres", []),  # type: ignore
                    countries=point.payload.get("countries", []),  # type: ignore
                    director=point.payload.get("director"),  # type: ignore
                    actors=point.payload.get("actors", []),  # type: ignore
                    description=point.payload.get("description"),  # type: ignore
                    poster_url=point.payload.get("poster_url"),  # type: ignore
                    score=point.score,  # type: ignore
                )
                for point in search_result.points
            ]
        except Exception:
            logger.exception(
                "Failed to convert Qdrant results to API response: collection=%s",
                self.collection_name,
            )
            raise

    def _build_filters(self, filters: SearchFilters) -> Optional[models.Filter]:
        """Building Qdrant-filters from Pydantic-schemas"""

        conditions: List[models.Condition] = []

        # Year filter
        if filters.year:
            if filters.year.gte is not None:
                conditions.append(
                    models.FieldCondition(
                        key="year",
                        range=models.Range(gte=float(filters.year.gte))
                    )
                )
            if filters.year.lte is not None:
                conditions.append(
                    models.FieldCondition(
                        key="year",
                        range=models.Range(lte=float(filters.year.lte))
                    )
                )

        # Rating filter
        if filters.rating:
            if filters.rating.gte is not None:
                conditions.append(
                    models.FieldCondition(
                        key="rating",
                        range=models.Range(gte=float(filters.rating.gte))
                    )
                )
            if filters.rating.lte is not None:
                conditions.append(
                    models.FieldCondition(
                        key="rating",
                        range=models.Range(lte=float(filters.rating.lte))
                    )
                )

        # Country filter
        if filters.country:
            conditions.append(
                models.FieldCondition(
                    key="country",
                    match=models.MatchValue(value=filters.country)
                )
            )

        # Genre filter (any of the list)
        if filters.genre:
            conditions.append(
                models.FieldCondition(
                    key="genres",
                    match=models.MatchAny(any=filters.genre)
                )
            )

        return models.Filter(must=conditions) if conditions else None

    def get_stats(self) -> Dict[str, Any]:
        """Return collection statistics"""
        started_at = perf_counter()
        logger.debug("Requesting Qdrant collection statistics: collection=%s", self.collection_name)
        try:
            collection_info = self.qdrant.get_collection(self.collection_name)
        except Exception:
            logger.exception(
                "Failed to get Qdrant collection statistics: collection=%s", self.collection_name
            )
            raise
        logger.info(
            "Qdrant collection statistics received: collection=%s points=%s duration_ms=%.1f",
            self.collection_name,
            collection_info.points_count,
            (perf_counter() - started_at) * 1000,
        )
        return {
            "collection": self.collection_name,
            "total_points": collection_info.points_count,
            "status": collection_info.status,
            "model": settings.EMBEDDING_MODEL,
            "embedding_dim": settings.EMBEDDING_DIM,
        }
