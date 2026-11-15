"""Contract of the vibe extractor."""

from pydantic import BaseModel, Field


class ExtractedVibe(BaseModel):
    """Mood tags found in a query and the vibe text built from them."""

    moods: list[str] = Field(default_factory=list)
    vibe: str | None = None
