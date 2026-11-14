"""Qdrant database repository for indexer and search service."""

from qdrant_client import models

from core.contracts import IndexerStats
from core.qdrant_client import QdrantClientSingleton
from services.indexer.config import config
from services.indexer.schemas import IndexedMoviePoint


class QdrantRepository:
    """Qdrant database repository."""

    def __init__(
        self,
        collection_name: str = config.collection_name,
        dense_dim: int = config.dense_dim,
    ) -> None:
        self.client = QdrantClientSingleton.get_client()
        self.collection_name = collection_name
        self.dense_dim = dense_dim

    def create_collection(self, collection_name: str | None = None) -> None:
        """Create the collection and payload indexes if it does not exist."""
        collection_name = collection_name or self.collection_name

        if self.client.collection_exists(collection_name):
            print(f"Collection {collection_name} already exists")
            return

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=self._get_vectors_config(),
            sparse_vectors_config=self._get_sparse_vectors_config(),
        )

        indexes = {
            "year": models.PayloadSchemaType.INTEGER,
            "rating": models.PayloadSchemaType.FLOAT,
            "duration_min": models.PayloadSchemaType.INTEGER,
            "genres": models.PayloadSchemaType.KEYWORD,
            "directors": models.PayloadSchemaType.KEYWORD,
            "actors": models.PayloadSchemaType.KEYWORD,
        }

        for field, schema in indexes.items():
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=schema,
            )

        print(f"Collection {collection_name} created successfully")

    def recreate_collection(self, collection_name: str | None = None) -> None:
        """Delete and recreate the collection."""
        collection_name = collection_name or self.collection_name

        if self.client.collection_exists(collection_name):
            self.client.delete_collection(collection_name)
        self.create_collection(collection_name)

    def upsert_points(self, points: list[IndexedMoviePoint]) -> None:
        """Upsert a batch of indexed movie points into Qdrant."""
        if not points:
            print("Points list is empty")
            return

        struct: list[models.PointStruct] = []
        for point in points:
            vectors: dict = {
                "vibe": point.vibe_vector,
                "sparse": models.SparseVector(
                    indices=point.sparse_vector.indices,
                    values=point.sparse_vector.values,
                ),
            }

            if point.plot_vector is not None:
                vectors["plot"] = point.plot_vector

            struct.append(
                models.PointStruct(
                    id=point.point_id,
                    vector=vectors,
                    payload=point.payload.model_dump(),
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=struct,
            wait=True,
        )

    def get_stats(self, collection_name: str | None = None) -> IndexerStats:
        """Return collection statistics."""
        collection_name = collection_name or self.collection_name
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
