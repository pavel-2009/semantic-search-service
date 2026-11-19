"""Reranking logic."""

from sentence_transformers import CrossEncoder

from src.core.device import get_compute_device
from src.services.search_service.ranking.schemas import RerankingRequest, RerankingResponse
from src.core.config import settings


class RerankingService:
    """Reranking service."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str | None = None,
    ) -> None:
        """Initialize the reranking service."""
        self.model = CrossEncoder(
            model_name,
            device=device if device is not None else get_compute_device(),
        )

    def rerank(self, request: RerankingRequest, top_k: int = settings.MAX_RERANKED_DOCUMENTS) -> RerankingResponse:
        """Rerank documents based on the query."""
        query = request.query
        documents = request.documents

        inputs = [(query, doc.) for doc in documents]

        scores = self.model.predict(inputs)

        scored_documents = [
            {"document": doc, "score": float(score)}
            for doc, score in zip(documents, scores, strict=True)
        ]
        scored_documents.sort(key=lambda x: x["score"], reverse=True)

        reranked_documents = []
        for item in scored_documents[:top_k]:
            document = dict(item["document"])
            document["score"] = item["score"]
            reranked_documents.append(document)

        return RerankingResponse(reranked_documents=reranked_documents)
