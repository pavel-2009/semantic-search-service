"""Reranking logic."""

import numpy as np

from src.core.model_loader import ModelLoader
from src.services.search_service.ranking.schemas import RerankingRequest, RerankingResponse


class RerankingService:
    """Reranking service."""

    def __init__(self) -> None:
        """Initialize the reranking service with the shared downloaded model."""
        self.model = ModelLoader.get_model()

    def rerank(self, request: RerankingRequest) -> RerankingResponse:
        """Rerank documents based on the query."""
        query = request.query
        documents = request.documents

        if not documents:
            return RerankingResponse(reranked_documents=[])

        query_embedding = np.asarray(
            self.model.encode(query, convert_to_numpy=True),
            dtype=np.float32,
        ).reshape(1, -1)
        document_embeddings = np.asarray(
            self.model.encode(
                [doc["text"] for doc in documents],
                convert_to_numpy=True,
            ),
            dtype=np.float32,
        )

        if document_embeddings.ndim == 1:
            document_embeddings = document_embeddings.reshape(1, -1)

        query_norm = np.linalg.norm(query_embedding, axis=1, keepdims=True)
        document_norms = np.linalg.norm(document_embeddings, axis=1, keepdims=True)
        scores = (
            document_embeddings @ query_embedding.T
        ).reshape(-1) / np.maximum(
            document_norms.reshape(-1) * query_norm.reshape(-1)[0],
            np.finfo(np.float32).eps,
        )

        scored_documents = [
            {"document": doc, "score": score} for doc, score in zip(documents, scores)
        ]
        scored_documents.sort(key=lambda x: x["score"], reverse=True)

        reranked_documents = [doc["document"] for doc in scored_documents]

        return RerankingResponse(reranked_documents=reranked_documents)
