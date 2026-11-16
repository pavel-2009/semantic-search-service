"""Schemas for the embedder service."""

from dataclasses import dataclass, field
from typing import List, Optional

from src.services.indexer.schemas import SparseVectorData


@dataclass
class EmbedderResponse:
    """Response schema for the embedder service."""

    embeddings: List[List[float]]
    """Dense embeddings aligned with embedding_names."""
    model: str
    """The model used to generate the embeddings."""
    embedding_names: List[str] = field(default_factory=list)
    """Names of the dense embeddings (plot, vibe), in embedding order."""
    sparse_vector: Optional[SparseVectorData] = None
    """Sparse entity embedding, if one was generated."""
    usage: Optional[dict] = None
    """Optional usage information, such as token counts."""

