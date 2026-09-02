"""Service for semantic movie search in Qdrant."""

import logging
from time import perf_counter

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Record, ScoredPoint

from backend.schemas import MovieResult, SearchFilters, SearchRequest
from core.config import settings
from core.model_loader import ModelLoader
from core.qdrant_client import QdrantClientSingleton
from core.text_normalizer import clean_text

logger = logging.getLogger(__name__)


class SearchService:
    """Search normalized movie documents stored in Qdrant."""

    def __init__(self) -> None:
        logger.info(
            "Initializing SearchService: collection=%s model=%s",
            settings.QDRANT_COLLECTION,
            settings.EMBEDDING_MODEL,
        )
        self.collection_name = settings.QDRANT_COLLECTION
        self.qdrant: QdrantClient = QdrantClientSingleton.get_client()
        self.model = ModelLoader.get_model()
        logger.info(
            "SearchService initialized: collection=%s embedding_dim=%d",
            self.collection_name,
            settings.EMBEDDING_DIM,
        )

    def search(self, request: SearchRequest) -> list[MovieResult]:
        """Run semantic search with optional metadata filters."""
        started_at = perf_counter()
        logger.info(
            "Search started: query=%r top_k=%d filters=%s",
            request.query,
            request.top_k,
            request.filters is not None,
        )
        cleaned_query = clean_text(request.query)
        logger.debug(
            "Query cleaned: original_length=%d cleaned_length=%d",
            len(request.query),
            len(cleaned_query),
        )
        vector_started_at = perf_counter()
        vector = self.model.encode(cleaned_query).tolist()
        logger.debug(
            "Query vector created: dimension=%d duration_ms=%.1f",
            len(vector),
            (perf_counter() - vector_started_at) * 1000,
        )
        query_filter = self._build_filters(request.filters) if request.filters else None
        qdrant_started_at = perf_counter()
        result = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=request.top_k,
            query_filter=query_filter,
            with_payload=True,
        )
        logger.debug(
            "Qdrant query completed: points=%d duration_ms=%.1f",
            len(result.points),
            (perf_counter() - qdrant_started_at) * 1000,
        )
        results = [self._movie_from_scored_point(point) for point in result.points]
        logger.info(
            "Search completed: query_length=%d results=%d duration_ms=%.1f",
            len(request.query),
            len(results),
            (perf_counter() - started_at) * 1000,
        )
        return results

    def get_by_id(self, movie_id: int) -> MovieResult | None:
        """Return a movie by its Qdrant point ID."""
        points = self.qdrant.retrieve(
            collection_name=self.collection_name,
            ids=[movie_id],
            with_payload=True,
            with_vectors=False,
        )
        if not points:
            logger.info("Movie not found: movie_id=%d", movie_id)
            return None
        return self._movie_from_record(points[0])

    @staticmethod
    def _movie_from_scored_point(point: ScoredPoint) -> MovieResult:
        """Convert a scored search result to a movie response."""
        return SearchService._movie_from_payload(
            point_id=point.id,
            payload=point.payload,
            score=float(point.score),
        )

    @staticmethod
    def _movie_from_record(record: Record) -> MovieResult:
        """Convert a retrieved Qdrant record to a movie response."""
        return SearchService._movie_from_payload(
            point_id=record.id,
            payload=record.payload,
            score=0.0,
        )

    @staticmethod
    def _movie_from_payload(
        point_id: int | str,
        payload: dict | None,
        score: float,
    ) -> MovieResult:
        """Build a movie response from common Qdrant point data."""
        payload = payload or {}
        countries = payload.get("countries") or []
        if isinstance(countries, str):
            countries = [countries]

        if not countries and payload.get("country"):
            countries = [country.strip() for country in str(payload["country"]).split(",")]

        return MovieResult(
            id=int(point_id),
            title=str(payload.get("title") or "Фильм без названия"),
            year=payload.get("year"),
            rating=payload.get("rating"),
            genres=payload.get("genres", []),
            countries=[str(country) for country in countries],
            director=payload.get("director"),
            actors=payload.get("actors", []),
            description=payload.get("description") or None,
            poster_url=payload.get("poster_url"),
            score=score,
        )

    @staticmethod
    def _build_filters(filters: SearchFilters) -> models.Filter | None:
        """Build Qdrant filters from API filter schemas."""
        conditions: list[models.Condition] = []
        try:
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
                        key="countries",
                        match=models.MatchAny(any=[filters.country]),
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
        except AttributeError:
            return None
        

    def get_stats(self) -> dict[str, object]:
        """Return collection statistics."""
        info = self.qdrant.get_collection(self.collection_name)
        return {
            "collection": self.collection_name,
            "total_points": info.points_count,
            "status": info.status,
            "model": settings.EMBEDDING_MODEL,
            "embedding_dim": settings.EMBEDDING_DIM,
        }
