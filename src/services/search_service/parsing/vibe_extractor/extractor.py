"""Extractor for vibes from text"""


from flashtext import KeywordProcessor
from typing import List

from .schemas import VibeExtracted
from services.search_service.parsing.dictionary_builder import DictionaryBuilder


class VibeExtractor:
    def __init__(self, dictionary: DictionaryBuilder):
        self.vibe_processor = KeywordProcessor()
        self.vibe_processor.add_keywords_from_dict(dictionary.vibes)

    def extract(self, text: str, decades: list[str]) -> List[VibeExtracted]:
        """Extract vibes from text"""
        matches = self.vibe_processor.extract_keywords(text)

        genres: list[str] = []
        tags: list[str] = []
        countries: list[str] = []

        for kind, canonical_val in matches:
            if kind == "genre":
                genres.append(canonical_val)
            elif kind == "tag":
                tags.append(canonical_val)
            elif kind == "country":
                countries.append(canonical_val)

        genres = list(dict.fromkeys(genres))
        tags = list(dict.fromkeys(tags))
        countries = list(dict.fromkeys(countries))

        vibe_text = self._build_template(
            genres=genres,
            tags=tags,
            countries=countries,
            decades=decades,
        )

        return VibeExtracted(
            vibe=vibe_text,
            
        )


    def _build_template(
        self,
        genres: list[str],
        tags: list[str],
        countries: list[str],
        decades: list[str],
    ) -> str | None:
        parts: list[str] = []

        if genres:
            parts.append(f"Жанры: {', '.join(genres)}.")
        if tags:
            parts.append(f"Атмосфера и теги: {', '.join(tags)}.")

        era = list(dict.fromkeys(countries + decades))
        if era:
            parts.append(f"Страна и эпоха: {', '.join(era)}.")

        return " ".join(parts) if parts else None
