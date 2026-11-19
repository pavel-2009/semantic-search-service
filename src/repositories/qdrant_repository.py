"""Qdrant database repository for indexer and search service."""

from time import perf_counter

from qdrant_client import models

from src.core.contracts import IndexerStats
from src.core.logger import get_logger
from src.core.config import settings
from src.core.qdrant_client import QdrantClientSingleton
from src.core.config import settings
from src.services.indexer.schemas import IndexedMoviePoint
from src.services.search_service.embedder.schemas import EmbedderResponse
from src.repositories.schemas import RetrievalResponse

logger = get_logger(__name__)


class QdrantRepository:
    """Qdrant database repository."""

    def __init__(
        self,
        collection_name: str = settings.QDRANT_COLLECTION,
        dense_dim: int = settings.EMBEDDING_DIM,
    ) -> None:
        self.client = QdrantClientSingleton.get_client()
        self.collection_name = collection_name
        self.dense_dim = dense_dim

    def create_collection(self, collection_name: str | None = None) -> None:
        """Create the collection and payload indexes if it does not exist."""
        collection_name = collection_name or self.collection_name
        logger.info("Checking Qdrant collection: collection=%s", collection_name)

        if self.client.collection_exists(collection_name):
            logger.info("Collection already exists: collection=%s", collection_name)
            return

        logger.info(
            "Creating Qdrant collection: collection=%s dense_dim=%d",
            collection_name,
            self.dense_dim,
        )
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=self._get_vectors_config(),
            sparse_vectors_config=self._get_sparse_vectors_config(),
        )

        indexes = {
            "year": models.PayloadSchemaType.INTEGER,
            "rating": models.PayloadSchemaType.FLOAT,
        }

        for field, schema in indexes.items():
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=schema,
            )

        logger.info("Qdrant collection created successfully: collection=%s", collection_name)

    def recreate_collection(self, collection_name: str | None = None) -> None:
        """Delete and recreate the collection."""
        collection_name = collection_name or self.collection_name
        logger.info("Recreating Qdrant collection: collection=%s", collection_name)

        if self.client.collection_exists(collection_name):
            self.client.delete_collection(collection_name)
            logger.info("Deleted existing Qdrant collection: collection=%s", collection_name)
        self.create_collection(collection_name)

    def upsert_points(self, points: list[IndexedMoviePoint]) -> tuple[int, int]:
        """Upsert a batch of indexed movie points into Qdrant, isolating failed points."""
        if not points:
            logger.warning("Points list is empty; skipping upsert: collection=%s", self.collection_name)
            return 0, 0

        struct: list[models.PointStruct] = []
        for point in points:
            vectors: dict = {
                "sparse": models.SparseVector(
                    indices=point.sparse_vector.indices,
                    values=point.sparse_vector.values,
                ),
            }

            if point.plot_vector is not None:
                vectors["plot"] = point.plot_vector
            if point.vibe_vector is not None:
                vectors["vibe"] = point.vibe_vector

            struct.append(
                models.PointStruct(
                    id=point.point_id,
                    vector=vectors,
                    payload=point.payload.model_dump(),
                )
            )

        started_at = perf_counter()
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=struct,
                wait=True,
            )
            logger.info(
                "Upserted points to Qdrant: collection=%s points=%d duration_ms=%.1f",
                self.collection_name,
                len(struct),
                (perf_counter() - started_at) * 1000,
            )
            return len(struct), 0
        except Exception:
            logger.exception(
                "Failed to upsert batch; retrying points individually: collection=%s points=%d",
                self.collection_name,
                len(struct),
            )

        indexed = 0
        failed = 0
        for point_struct in struct:
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[point_struct],
                    wait=True,
                )
                indexed += 1
            except Exception:
                failed += 1
                logger.exception("Failed to upsert movie: movie_id=%s", point_struct.id)

        return indexed, failed

    def get_points(self, embeddings: EmbedderResponse, top_k: int = settings.MAX_RETRIEVED_DOCUMENTS) -> RetrievalResponse:
        """Retrieve points from Qdrant based on embeddings."""
        logger.debug("Retrieving points from Qdrant: collection=%s", self.collection_name)

        year_gte, year_lte = embeddings.year_range
        rating_gte, rating_lte = embeddings.rating_range
        conditions: list[models.FieldCondition] = []

        if year_gte or year_lte:
            conditions.append(
                models.FieldCondition(
                    key="year",
                    range=models.Range(
                        gte=year_gte or None,
                        lte=year_lte or None,
                    ),
                ),
            )
        if rating_gte or rating_lte:
            conditions.append(
                models.FieldCondition(
                    key="rating",
                    range=models.Range(
                        gte=rating_gte or None,
                        lte=rating_lte or None,
                    ),
                ),
            )
        query_filter = models.Filter(must=conditions) if conditions else None

        prefetch: list[models.Prefetch] = []
        for vector_name, vector in zip(
            embeddings.embedding_names,
            embeddings.embeddings,
            strict=True,
        ):
            if vector:
                prefetch.append(
                    models.Prefetch(
                        query=vector,
                        limit=50,
                        using=vector_name,
                        filter=query_filter,
                    )
                )

        if embeddings.sparse_vector and embeddings.sparse_vector.indices:
            prefetch.append(
                models.Prefetch(
                    query=models.SparseVector(
                        indices=embeddings.sparse_vector.indices,
                        values=embeddings.sparse_vector.values,
                    ),
                    limit=50,
                    using="sparse",
                    filter=query_filter,
                )
            )

        if not prefetch:
            logger.warning("No embeddings provided for retrieval; returning empty response.")
            return RetrievalResponse(request=embeddings, response=[])

        try:

            response = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=prefetch,
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                query_filter=query_filter,
                limit=top_k * 5,  # Retrieve more points for reranking
                with_payload=True,
            )

        except Exception as e:
            logger.exception("Failed to retrieve points from Qdrant: collection=%s", self.collection_name)
            raise e

        sorted_points = sorted(response.points, key=self._rating_sort_key, reverse=True)
        return RetrievalResponse(request=embeddings, response=sorted_points)

    @staticmethod
    def _rating_sort_key(point: models.ScoredPoint) -> tuple[bool, float]:
        """Sort rated points by descending rating and place unrated points last."""
        if not point.payload:
            return False, 0.0

        rating = point.payload.get("rating")
        if rating is None:
            return False, 0.0

        try:
            return True, float(rating)
        except (TypeError, ValueError):
            return False, 0.0

    def get_stats(self, collection_name: str | None = None) -> IndexerStats:
        """Return collection statistics."""
        collection_name = collection_name or self.collection_name
        logger.debug("Fetching Qdrant collection stats: collection=%s", collection_name)
        collection_info = self.client.get_collection(collection_name)
        return IndexerStats(
            collection=collection_name,
            points_count=collection_info.points_count or 0,
            status=str(collection_info.status),
        )

    def _get_vectors_config(self) -> dict[str, models.VectorParams]:
        return {
            "plot": models.VectorParams(
                size=self.dense_dim,
                distance=models.Distance.COSINE,
            ),
            "vibe": models.VectorParams(
                size=self.dense_dim,
                distance=models.Distance.COSINE,
            ),
        }

    def _get_sparse_vectors_config(self) -> dict[str, models.SparseVectorParams]:
        return {
            "sparse": models.SparseVectorParams(),
        }
