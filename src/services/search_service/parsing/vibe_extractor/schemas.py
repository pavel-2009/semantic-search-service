"""Contract of the vibe extractor."""

from pydantic import BaseModel


class ExtractedVibe(BaseModel):
    """Vibe description for the vibe vector plus the query text without vibe words."""

    text: str
    vibe: str | None = None
