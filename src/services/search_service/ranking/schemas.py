"""Reranking schemas."""

from dataclasses import dataclass


@dataclass
class RerankingRequest:
    """Reranking request schema."""

    query: str
    documents: list[dict]


@dataclass
class RerankingResponse:
    """Reranking response schema."""

    reranked_documents: list[dict]
