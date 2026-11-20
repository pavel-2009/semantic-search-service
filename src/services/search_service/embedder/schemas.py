"""Schemas for the embedder service."""

from dataclasses import dataclass, field
from typing import List, Optional

from src.services.indexer.schemas import SparseVectorData


@dataclass
class EmbedderResponse:
    """Response schema for the embedder service.

    A zero in a filter range means that the corresponding bound is not set.
    """

    embeddings: List[List[float]]
    """Dense embeddings aligned with embedding_names."""
    model: str
    """The model used to generate the embeddings."""
    embedding_names: List[str] = field(default_factory=list)
    """Names of the dense embeddings (plot, vibe), in embedding order."""
    sparse_vector: Optional[SparseVectorData] = None
    """Sparse entity embedding, if one was generated."""
    year_range: tuple[int, int] = (0, 0)
    """Year bounds; zero means that the bound is not set."""
    rating_range: tuple[float, float] = (0.0, 0.0)
    """Rating bounds; zero means that the bound is not set."""
    usage: Optional[dict] = None
    """Optional usage information, such as token counts."""

