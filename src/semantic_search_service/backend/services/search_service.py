"""Service for semantic search in Qdrant"""

from typing import List, Dict, Any, Optional
from qdrant_client.http import models
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from text_cleaner import clean_text  # type: ignore

from semantic_search_service.core.qdrant_client import QdrantClientSingleton
from semantic_search_service.core.config import settings
from semantic_search_service.backend.schemas import SearchRequest, SearchFilters, MovieResult


class SearchService:
    """Semantic search service for searching similar films in Qdrant"""

    def __init__(self):
        self.qdrant: QdrantClient = QdrantClientSingleton.get_client()
        self.collection_name = settings.QDRANT_COLLECTION
        self.model: SentenceTransformer = SentenceTransformer(settings.EMBEDDING_MODEL)

    def search(self, request: SearchRequest) -> List[MovieResult]:
        """Search films with request conditions"""

        cleaned_query: str = clean_text(request.query)  # type: ignore

        vector = self.model.encode(cleaned_query).tolist()  # type: ignore

        query_filter = self._build_filters(request.filters) if request.filters else None

        search_result = self.qdrant.query_points(
            collection_name=self.collection_name,
            vector=vector,
            limit=request.top_k,
            query_filter=query_filter,
            with_payload=True,
        )

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
            for point in search_result
        ]

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
        collection_info = self.qdrant.get_collection(self.collection_name)
        return {
            "collection": self.collection_name,
            "total_points": collection_info.points_count,
            "status": collection_info.status,
            "model": settings.EMBEDDING_MODEL,
            "embedding_dim": settings.EMBEDDING_DIM,
        }