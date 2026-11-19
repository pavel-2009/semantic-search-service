"""Reranking schemas."""

from dataclasses import dataclass

from qdrant_client.models import ScoredPoint


@dataclass
class RerankingRequest:
    """Reranking request schema."""

    query: str
    documents: list[ScoredPoint]


@dataclass
class RerankingResponse:
    """Reranking response schema."""

    reranked_documents: list[dict]
