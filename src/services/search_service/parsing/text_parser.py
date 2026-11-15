"""Entry point for parsing text into a structured format."""

from dataclasses import dataclass
from typing import List, Optional

from src.services.search_service.parsing.filter_extractor import FilterExtractor
from src.services.search_service.parsing.vibe_extractor import VibeExtractor
from src.services.search_service.parsing.entity_extraction import EntityExtractor


@dataclass
class ParsedText:
    """Represents the structured format of parsed text."""
    plot: Optional[str]
    vibe: str
    entities: List[str]
    filter: Optional[dict] = None


class TextParser:
    def __init__(self):
        self.filter_extractor = FilterExtractor()
        self.vibe_extractor = VibeExtractor()
        self.entity_extractor = EntityExtractor()


    def parse(self, text: str) -> ParsedText:
        filters = self.filter_extractor.extract(text)
        text = filters.text

        vibe = self.vibe_extractor.extract(text)
        text = vibe.text

        entities = self.entity_extractor.extract(text)
        text = entities.text

        return ParsedText(
            plot=text,
            vibe=vibe.vibe,
            entities=entities.entities,
            filter=filters.filter
        )
