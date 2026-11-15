"""Build the mood lookup for query parsing from the mood dictionary."""

import pymorphy3
from flashtext import KeywordProcessor

from services.search_service.parsing.mood_dictionary import MOOD_TAGS

CYRILLIC_LETTERS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


class DictionaryBuilder:
    """Expand dictionary lemmas into word forms with pymorphy3 and index them in flashtext."""

    def __init__(self, morph: pymorphy3.MorphAnalyzer | None = None) -> None:
        self.morph = morph or pymorphy3.MorphAnalyzer()

    def word_forms(self, lemma: str) -> set[str]:
        """Return all inflected forms of a lemma (the lemma itself is always included)."""
        forms = {lemma.lower()}
        for parse in self.morph.parse(lemma):
            if parse.normal_form == lemma.lower():
                forms.update(form.word for form in parse.lexeme)
        return forms

    def phrase_forms(self, phrase: str) -> set[str]:
        """Return forms of a phrase; only the last word is inflected for multi-word phrases."""
        *head, last = phrase.lower().split()
        prefix = " ".join(head)
        return {f"{prefix} {form}".strip() for form in self.word_forms(last)}

    def build_mood_processor(
        self, tags: dict[str, tuple[str, ...]] = MOOD_TAGS
    ) -> KeywordProcessor:
        """Map every form of each trigger (also with "ё" -> "е") to its mood tag."""
        processor = KeywordProcessor(case_sensitive=False)
        for char in CYRILLIC_LETTERS:
            processor.add_non_word_boundary(char)
        for tag, triggers in tags.items():
            for trigger in triggers:
                for form in self.phrase_forms(trigger):
                    processor.add_keyword(form, tag)
                    processor.add_keyword(form.replace("ё", "е"), tag)
        return processor
