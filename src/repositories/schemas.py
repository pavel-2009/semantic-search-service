"""Schemas for qdrant search"""

from dataclasses import dataclass
from qdrant_client.models import PointsList

from src.services.search_service.embedder.schemas import EmbedderResponse


@dataclass
class RetrievalResponse:
    request: EmbedderResponse
    response: PointsList
