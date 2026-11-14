"""Qdrant database repository for indexer and search service"""

from qdrant_client import models

from core.qdrant_client import QdrantClientSingleton


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
            vectors_config=self.get_vectors_config(),
            sparse_vectors_config=self.get_sparse_vectors_config()
        )
        print(f"Collection {collection_name} created successfully")
    

    def get_vectors_config(self):
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
