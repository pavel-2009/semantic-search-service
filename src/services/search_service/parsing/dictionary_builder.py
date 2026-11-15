"""Build lookup structures for query parsing from static dictionaries."""

from collections.abc import Iterable, Mapping

import pymorphy3
from flashtext import KeywordProcessor

from services.search_service.parsing.dictionaries import COUNTRY_ADJECTIVES, STOP_WORDS


CYRILLIC_LETTERS = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"


def _make_processor() -> KeywordProcessor:
    """Create a case-insensitive processor that treats Cyrillic letters as word characters."""
    processor = KeywordProcessor(case_sensitive=False)
    for char in CYRILLIC_LETTERS:
        processor.add_non_word_boundary(char)
    return processor


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

    def lemmatize(self, word: str) -> str:
        """Return the normal form of a word."""
        return self.morph.parse(word.lower())[0].normal_form

    def build_country_processor(
        self,
        adjectives: Mapping[str, Iterable[str]] = COUNTRY_ADJECTIVES,
    ) -> KeywordProcessor:
        """Map every adjective form to its canonical country name."""
        processor = _make_processor()
        for country, lemmas in adjectives.items():
            for lemma in lemmas:
                for form in self.word_forms(lemma):
                    processor.add_keyword(form, country)
        return processor

    def build_stop_words(self, lemmas: Iterable[str] = STOP_WORDS) -> frozenset[str]:
        """Return all word forms of the stop-word lemmas."""
        forms: set[str] = set()
        for lemma in lemmas:
            forms |= self.word_forms(lemma)
        return frozenset(forms)

    def build_stop_processor(self, lemmas: Iterable[str] = STOP_WORDS) -> KeywordProcessor:
        """Build a flashtext processor that finds stop words (see `remove_stop_words`)."""
        processor = _make_processor()
        for form in self.build_stop_words(lemmas):
            processor.add_keyword(form)
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
