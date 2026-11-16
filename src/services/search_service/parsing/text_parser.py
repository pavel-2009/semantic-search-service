"""Entry point for parsing text into a structured format."""

import re
from dataclasses import dataclass

from src.services.search_service.parsing.dictionary_builder import DictionaryBuilder
from src.services.search_service.parsing.entity_extraction import EntityExtractor
from src.services.search_service.parsing.filter_extractor import FilterExtractor
from src.services.search_service.parsing.vibe_extractor import VibeExtractor

_DANGLING_WORDS = frozenset(
    "а без в во для до за и из к ко на над о об обо от по под при про с со у через".split()
)
_PUNCTUATION = " ,.;:!?-–—"


@dataclass
class ParsedText:
    """Represents the structured format of parsed text."""

    plot: str | None
    vibe: str | None
    entities: str | None
    filter: dict[str, int | float] | None = None


class TextParser:
    """Extract filters, mood and entities from a natural-language query."""

    def __init__(self) -> None:
        self.filter_extractor = FilterExtractor()
        self.vibe_extractor = VibeExtractor()
        self.entity_extractor = EntityExtractor()
        self.stop_processor = DictionaryBuilder().build_stop_processor()

    def parse(self, text: str) -> ParsedText:
        """Parse a query and clean the remaining plot text."""
        entities = self.entity_extractor.extract(text)
        filters = self.filter_extractor.extract(entities.text)
        vibe = self.vibe_extractor.extract(filters.text)

        plot_text = DictionaryBuilder.remove_stop_words(vibe.text, self.stop_processor)
        filter_values = filters.model_dump(exclude={"text"}, exclude_none=True)
        return ParsedText(
            plot=self._clean_plot(plot_text),
            vibe=vibe.vibe,
            entities=entities.entities,
            filter=filter_values or None,
        )

    @staticmethod
    def _clean_plot(text: str) -> str | None:
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s*([,.;:!?])\s*", r"\1 ", text)
        text = re.sub(r"([,.;:!?])(?:\s*[,.;:!?])+", r"\1", text)
        text = text.strip(_PUNCTUATION)
        words = text.split()

        while words and words[0].strip(_PUNCTUATION).lower() in _DANGLING_WORDS:
            words.pop(0)
        while words and words[-1].strip(_PUNCTUATION).lower() in _DANGLING_WORDS:
            words.pop()

        cleaned = " ".join(words).strip(_PUNCTUATION)
        return cleaned or None
