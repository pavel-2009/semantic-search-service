"""Contract of the entity extractor."""

from pydantic import BaseModel


class ExtractedEntities(BaseModel):
    """Entities text for the sparse vector plus the remaining query text."""

    text: str
    entities: str | None = None
