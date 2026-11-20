"""Build lookup structures for query parsing from static dictionaries."""

from collections.abc import Iterable
from functools import lru_cache

import pymorphy3
from flashtext import KeywordProcessor

from src.services.search_service.parsing_resources.dictionaries import GENRE_TAGS, STOP_WORDS
from src.services.search_service.parsing_resources.entity_patterns import CYRILLIC_LETTERS
from src.services.search_service.parsing_resources.mood_dictionary import MOOD_TAGS


@lru_cache(maxsize=1)
def get_morph_analyzer() -> pymorphy3.MorphAnalyzer:
    """Return a shared pymorphy3 analyzer instance."""
    return pymorphy3.MorphAnalyzer()


def _make_processor() -> KeywordProcessor:
    processor = KeywordProcessor(case_sensitive=False)
    for char in CYRILLIC_LETTERS:
        processor.add_non_word_boundary(char)
    return processor


class DictionaryBuilder:
    """Expand dictionary lemmas into word forms with pymorphy3 and index them in flashtext."""

    def __init__(self, morph: pymorphy3.MorphAnalyzer | None = None) -> None:
        self.morph = morph or get_morph_analyzer()

    def word_forms(self, lemma: str) -> set[str]:
        """Return all inflected forms of a lemma (the lemma itself is always included)."""
        lower = lemma.lower()
        forms = {lower}
        for parse in self.morph.parse(lemma):
            if parse.normal_form == lower:
                forms.update(form.word for form in parse.lexeme)
            elif parse.tag.POS == "PRTF" and parse.word == lower:
                # Participles have the verb infinitive as normal_form in pymorphy3;
                # keep only matching participle inflections instead of finite verb forms.
                forms.update(
                    form.word
                    for form in parse.lexeme
                    if form.tag.POS == "PRTF"
                    and form.tag.tense == parse.tag.tense
                    and form.tag.voice == parse.tag.voice
                )
        return forms

    def phrase_forms(self, phrase: str) -> set[str]:
        """Return forms of a phrase; only the last word is inflected for multi-word phrases."""
        *head, last = phrase.lower().split()
        prefix = " ".join(head)
        return {f"{prefix} {form}".strip() for form in self.word_forms(last)}

    def _build_processor(self, tags: dict[str, tuple[str, ...]]) -> KeywordProcessor:
        processor = _make_processor()
        for tag, triggers in tags.items():
            for trigger in triggers:
                for form in self.phrase_forms(trigger):
                    processor.add_keyword(form, tag)
                    processor.add_keyword(form.replace("ё", "е"), tag)
        return processor

    def build_mood_processor(
        self, tags: dict[str, tuple[str, ...]] = MOOD_TAGS
    ) -> KeywordProcessor:
        """Map every form of each trigger to its mood tag."""
        return self._build_processor(tags)

    def build_genre_processor(
        self, tags: dict[str, tuple[str, ...]] = GENRE_TAGS
    ) -> KeywordProcessor:
        """Map every form of each genre trigger to its canonical genre name."""
        return self._build_processor(tags)

    def build_stop_processor(
        self, lemmas: Iterable[str] = STOP_WORDS
    ) -> KeywordProcessor:
        """Build a flashtext processor matching all inflected forms of stop-word lemmas."""
        processor = _make_processor()
        for lemma in lemmas:
            for form in self.phrase_forms(lemma):
                processor.add_keyword(form)
                processor.add_keyword(form.replace("ё", "е"))
        return processor

    @staticmethod
    def remove_stop_words(text: str, processor: KeywordProcessor) -> str:
        """Cut stop-word spans out of text and collapse whitespace."""
        pieces: list[str] = []
        last = 0
        for _, start, end in processor.extract_keywords(text, span_info=True):
            pieces.append(text[last:start])
            last = end
        pieces.append(text[last:])
        return " ".join("".join(pieces).split())
