"""Entry point for parsing text into a structured format."""

import re
from dataclasses import dataclass

from src.services.search_service.parsing.dictionary_builder import DictionaryBuilder
from src.services.search_service.parsing.entity_extraction import EntityExtractor, KeywordExtractor
from src.services.search_service.parsing.filter_extractor import FilterExtractor
from src.services.search_service.parsing.vibe_extractor import VibeExtractor

_DANGLING_WORDS = frozenset(
    "а без в во для до за и или к ко на но над о об обо от по под при про с со у через чтобы чтоб".split()
)
_PUNCTUATION = " ,.;:!?-–—\"'«»„“"


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
        self.keyword_extractor = KeywordExtractor()
        self.stop_processor = DictionaryBuilder().build_stop_processor()

    def parse(self, text: str) -> ParsedText:
        """Parse a query and clean the remaining plot text."""
        entities = self.entity_extractor.extract(text)
        filters = self.filter_extractor.extract(entities.text)
        vibe = self.vibe_extractor.extract(filters.text)

        plot_text = DictionaryBuilder.remove_stop_words(vibe.text, self.stop_processor)
        cleaned_plot = self._clean_plot(plot_text)
        merged_entities = self._merge_entities(entities.entities, cleaned_plot, vibe.vibe)
        filter_values = filters.model_dump(exclude={"text"}, exclude_none=True)
        return ParsedText(
            plot=cleaned_plot,
            vibe=vibe.vibe,
            entities=merged_entities,
            filter=filter_values or None,
        )

    def _merge_entities(
        self,
        raw_entities: str | None,
        plot: str | None,
        vibe: str | None,
    ) -> str | None:
        base = [item.strip() for item in raw_entities.split(".") if item.strip()] if raw_entities else []
        exclude = list(base)
        if vibe:
            exclude.append(vibe)
        keywords = self.keyword_extractor.extract(plot, exclude=exclude)

        seen = {item.lower().replace("ё", "е") for item in base}
        combined = list(base)
        for kw in keywords:
            norm = kw.lower().replace("ё", "е")
            if norm not in seen:
                seen.add(norm)
                combined.append(kw)

        return ". ".join(combined) if combined else None

    @staticmethod
    def _clean_plot(text: str) -> str | None:
        text = re.sub(r"[«»\"'„“]\s*[«»\"'„“]", " ", text)
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
