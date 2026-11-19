"""Reranking logic."""

from typing import Any

from sentence_transformers import CrossEncoder
from qdrant_client.models import ScoredPoint

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
        documents: list[ScoredPoint] = request.documents

        formatted_documents = [self._document_from_point(point) for point in documents]
        inputs = [(query, text) for _, text in formatted_documents]

        scores = self.model.predict(inputs)

        scored_documents = [
            {"document": document, "score": float(score)}
            for (document, _), score in zip(formatted_documents, scores, strict=True)
        ]
        scored_documents.sort(key=lambda x: x["score"], reverse=True)

        reranked_documents = []
        for item in scored_documents[:top_k]:
            document = dict(item["document"])
            document["score"] = item["score"]
            reranked_documents.append(document)

        return RerankingResponse(reranked_documents=reranked_documents)

    @staticmethod
    def _document_from_point(point: ScoredPoint) -> tuple[dict[str, Any], str]:
        """Build the structured result and labeled text used by the reranker."""
        document = dict(point.payload or {})
        document.setdefault("id", point.id)
        fields = [
            ("Название", document.get("title")),
            ("Год", document.get("year")),
            ("Страны", ", ".join(document.get("countries") or [])),
            ("Жанры", ", ".join(document.get("genres") or [])),
            ("Настроение", ", ".join(document.get("moods") or [])),
            ("Рейтинг", document.get("rating")),
            ("Сюжет", document.get("description")),
        ]
        text = ". ".join(
            f"{label}: {str(value).strip()}"
            for label, value in fields
            if value is not None and str(value).strip()
        )
        return document, text
