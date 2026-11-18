"""Reranking logic."""

from sentence_transformers import CrossEncoder

from src.services.search_service.ranking.schemas import RerankingRequest, RerankingResponse


class RerankingService:
    """Reranking service."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize the reranking service."""
        self.model = CrossEncoder(model_name)

    def rerank(self, request: RerankingRequest) -> RerankingResponse:
        """Rerank documents based on the query."""
        query = request.query
        documents = request.documents

        inputs = [(query, doc["text"]) for doc in documents]

        scores = self.model.predict(inputs)

        scored_documents = [
            {"document": doc, "score": score} for doc, score in zip(documents, scores)
        ]
        scored_documents.sort(key=lambda x: x["score"], reverse=True)

        reranked_documents = [doc["document"] for doc in scored_documents]

        return RerankingResponse(reranked_documents=reranked_documents)
