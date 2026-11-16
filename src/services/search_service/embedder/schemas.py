"""Schemas for the embedder service."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EmbedderResponse:
    """Response schema for the embedder service."""

    embeddings: List[List[float]]
    """List of embeddings for the input texts."""
    model: str
    """The model used to generate the embeddings."""
    usage: Optional[dict] = None
    """Optional usage information, such as token counts."""

