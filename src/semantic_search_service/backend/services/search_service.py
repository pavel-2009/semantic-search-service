"""Service for semantic movie search in Qdrant."""

import logging
from time import perf_counter
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

from text_cleaner import clean_text  # type: ignore

from semantic_search_service.backend.schemas import MovieResult, SearchFilters, SearchRequest
from semantic_search_service.core.config import settings
from semantic_search_service.core.qdrant_client import QdrantClientSingleton

logger = logging.getLogger(__name__)


class SearchService:
    """Search normalized movie documents stored in Qdrant."""

    def __init__(self) -> None:
        self.collection_name = settings.QDRANT_COLLECTION
        self.qdrant: QdrantClient = QdrantClientSingleton.get_client()
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def search(self, request: SearchRequest) -> list[MovieResult]:
        """Run semantic search with optional metadata filters."""
        started_at = perf_counter()
        cleaned_query = clean_text(request.query)  # type: ignore
        vector = self.model.encode(cleaned_query).tolist()
        query_filter = self._build_filters(request.filters) if request.filters else None

        result = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=request.top_k,
            query_filter=query_filter,
            with_payload=True,
        )

        logger.info(
            "Search completed: query_length=%d results=%d duration_ms=%.1f",
            len(request.query),
            len(result.points),
            (perf_counter() - started_at) * 1000,
        )
        return [self._to_movie_result(point) for point in result.points]

    @staticmethod
    def _to_movie_result(point: Any) -> MovieResult:
        """Convert a Qdrant point to the public movie response."""
        payload = point.payload or {}
        country = payload.get("country")

        return MovieResult(
            id=int(point.id),
            title=str(payload.get("title") or "Без названия"),
            year=payload.get("year"),
            rating=payload.get("rating"),
            genres=payload.get("genres", []),
            countries=[str(country)] if country else [],
            director=payload.get("director"),
            actors=payload.get("actors", []),
            description=payload.get("description") or None,
            poster_url=payload.get("poster_url"),
            score=float(point.score),
        )

    @staticmethod
    def _build_filters(filters: SearchFilters) -> models.Filter | None:
        """Build Qdrant filters from API filter schemas."""
        conditions: list[models.Condition] = []

        if filters.year:
            if filters.year.gte is not None:
                conditions.append(
                    models.FieldCondition(
                        key="year",
                        range=models.Range(gte=filters.year.gte),
                    )
                )
            if filters.year.lte is not None:
                conditions.append(
                    models.FieldCondition(
                        key="year",
                        range=models.Range(lte=filters.year.lte),
                    )
                )

        if filters.rating:
            if filters.rating.gte is not None:
                conditions.append(
                    models.FieldCondition(
                        key="rating",
                        range=models.Range(gte=filters.rating.gte),
                    )
                )
            if filters.rating.lte is not None:
                conditions.append(
                    models.FieldCondition(
                        key="rating",
                        range=models.Range(lte=filters.rating.lte),
                    )
                )

        if filters.country:
            conditions.append(
                models.FieldCondition(
                    key="country",
                    match=models.MatchValue(value=filters.country),
                )
            )

        if filters.genre:
            conditions.append(
                models.FieldCondition(
                    key="genres",
                    match=models.MatchAny(any=filters.genre),
                )
            )

        return models.Filter(must=conditions) if conditions else None

    def get_stats(self) -> dict[str, Any]:
        """Return collection statistics."""
        info = self.qdrant.get_collection(self.collection_name)
        return {
            "collection": self.collection_name,
            "total_points": info.points_count,
            "status": info.status,
            "model": settings.EMBEDDING_MODEL,
            "embedding_dim": settings.EMBEDDING_DIM,
        }
