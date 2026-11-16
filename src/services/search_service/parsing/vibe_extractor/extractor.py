"""Extract mood tags from a query, build the vibe text and remove those words from text."""

from src.core.vibe import format_vibe
from src.services.search_service.parsing.dictionary_builder import DictionaryBuilder
from src.services.search_service.parsing.vibe_extractor.schemas import ExtractedVibe


class VibeExtractor:
    """Find mood words in a query, build the vibe description and cut the words out."""

    def __init__(self, builder: DictionaryBuilder | None = None) -> None:
        self.processor = (builder or DictionaryBuilder()).build_mood_processor()

    def extract(self, text: str) -> ExtractedVibe:
        """Return the vibe found in text and the text with those words removed."""
        moods: list[str] = []
        pieces: list[str] = []
        last = 0

        for mood, start, end in self.processor.extract_keywords(text, span_info=True):
            if mood not in moods:
                moods.append(mood)
            pieces.append(text[last:start])
            last = end
        pieces.append(text[last:])

        return ExtractedVibe(
            text=self._clean("".join(pieces)),
            vibe=format_vibe(moods),
        )

    @staticmethod
    def _clean(text: str) -> str:
        words = [word for word in text.split() if word.strip(",.;:-–—")]
        return " ".join(words).strip(" ,.;:-")
