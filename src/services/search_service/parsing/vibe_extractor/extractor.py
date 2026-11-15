"""Extract vibe (genres, atmosphere, themes, country, era) from a query.

Example:
    "мрачный триллер про космос, французский" -> vibe:
        "Жанры: триллер. Атмосфера и теги: мрачный, космос. Страна и эпоха: Франция."
    text: "про"
"""

from services.search_service.parsing.dictionary_builder import DictionaryBuilder
from services.search_service.parsing.vibe_extractor.schemas import ExtractedVibe


class VibeExtractor:
    """Find vibe words in a query, build the vibe description and cut the words out."""

    def __init__(self, builder: DictionaryBuilder | None = None) -> None:
        self.processor = (builder or DictionaryBuilder()).build_vibe_processor()

    def extract(self, text: str, decades: list[str] | None = None) -> ExtractedVibe:
        """Return the vibe found in text and the text with those words removed."""
        found: dict[str, list[str]] = {"genre": [], "atmosphere": [], "theme": [], "country": []}
        pieces: list[str] = []
        last = 0

        for (kind, name), start, end in self.processor.extract_keywords(text, span_info=True):
            if name not in found[kind]:
                found[kind].append(name)
            pieces.append(text[last:start])
            last = end
        pieces.append(text[last:])

        return ExtractedVibe(
            text=self._clean("".join(pieces)),
            vibe=self._build_vibe(found, decades or []),
        )

    @staticmethod
    def _build_vibe(found: dict[str, list[str]], decades: list[str]) -> str | None:
        parts: list[str] = []
        if found["genre"]:
            parts.append(f"Жанры: {', '.join(found['genre'])}.")
        tags = [*found["atmosphere"], *found["theme"]]
        if tags:
            parts.append(f"Атмосфера и теги: {', '.join(tags)}.")
        era = list(dict.fromkeys([*found["country"], *decades]))
        if era:
            parts.append(f"Страна и эпоха: {', '.join(era)}.")
        return " ".join(parts) or None

    @staticmethod
    def _clean(text: str) -> str:
        words = [word for word in text.split() if word.strip(",.;:-–—")]
        return " ".join(words).strip(" ,.;:-")
