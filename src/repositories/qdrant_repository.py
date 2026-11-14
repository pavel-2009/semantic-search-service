"""Qdrant database repository for indexer and search service"""

from qdrant_client import models

from core.qdrant_client import QdrantClientSingleton
from services.indexer.schemas import IndexedMoviePoint


class QdrantRepository:
    """Qdrant database repository."""

    def __init__(self, collection_name: str):
        self.client = QdrantClientSingleton().get_client()
        self.collection_name = collection_name

    
    def create_collection(self, collection_name):
        """Collection creation"""
        if not collection_name:
            collection_name = self.collection_name

        # Check if the collection already exists
        if self.client.collection_exists(collection_name):
            print(f"Collection {collection_name} already exists")
            return

        self.client.create_collection(
            collection_name,
            vectors_config=self._get_vectors_config(),
            sparse_vectors_config=self._get_sparse_vectors_config()
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
                field_schema=schema
            )

        print(f"Collection {collection_name} created successfully")

    
    def recreate_collection(self, collection_name):
        """Collection recreation"""
        if not collection_name:
            collection_name = self.collection_name

        self.client.delete_collection(collection_name)
        self.create_collection(collection_name)
    

    def upsert_points(self, points: list[IndexedMoviePoint]):
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
                    id=point.id,
                    vector=vectors,
                    payload=point.payload.model_dump()
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=struct,
            wait=True
        )


    def _get_vectors_config(self):
        vectors_config = {}

        plot_vector = models.VectorParams(
            size=768,
            distance=models.Distance.COSINE
        )
        vibe_vector = models.VectorParams(
            size=768,
            distance=models.Distance.COSINE
        )

        vectors_config["plot_vector"] = plot_vector
        vectors_config["vibe_vector"] = vibe_vector

        return vectors_config


    def _get_sparse_vectors_config(self):
        sparse_vectors_config = {}

        ner_sparse_vector = models.SparseVectorParams()

        sparse_vectors_config["ner_sparse_vector"] = ner_sparse_vector

        return sparse_vectors_config
