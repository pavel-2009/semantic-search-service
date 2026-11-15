"""Extract mood tags from a query and build the vibe text.

Example:
    "мрачный фильм про петлю времени, чтобы было жутко" ->
        moods: [мрачный, жуткий], vibe: "Мрачный, жуткий."

The vibe has exactly the format of the indexed movies (`core.vibe.format_vibe`).
The query text is not changed: the plot channel searches with the whole query.
"""

from core.vibe import format_vibe
from services.search_service.parsing.dictionary_builder import DictionaryBuilder
from services.search_service.parsing.vibe_extractor.schemas import ExtractedVibe


class VibeExtractor:
    """Find mood words in a query."""

    def __init__(self, builder: DictionaryBuilder | None = None) -> None:
        self.processor = (builder or DictionaryBuilder()).build_mood_processor()

    def extract(self, text: str) -> ExtractedVibe:
        """Return mood tags found in text (in order of appearance) and their vibe text."""
        moods = list(dict.fromkeys(self.processor.extract_keywords(text)))
        return ExtractedVibe(moods=moods, vibe=format_vibe(moods))
