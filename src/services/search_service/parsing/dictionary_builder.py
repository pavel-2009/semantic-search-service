"""Build lookup structures for query parsing from static dictionaries."""

from itertools import product
from collections.abc import Iterable, Mapping

import pymorphy3
from flashtext import KeywordProcessor

from services.search_service.parsing.dictionaries import (
    ATMOSPHERE_TAGS,
    COUNTRY_ADJECTIVES,
    GENRE_TAGS,
    STOP_WORDS,
    THEME_TAGS,
)


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

    def build_tag_processor(self, tags: Mapping[str, Iterable[str]]) -> KeywordProcessor:
        """Map every form of each trigger lemma (single or multi-word) to its tag."""
        processor = _make_processor()
        for tag, lemmas in tags.items():
            for lemma in lemmas:
                for form in self.phrase_forms(lemma):
                    processor.add_keyword(form, tag)
        return processor

    def build_atmosphere_processor(self) -> KeywordProcessor:
        """Processor for atmosphere (mood) tags."""
        return self.build_tag_processor(ATMOSPHERE_TAGS)

    def build_theme_processor(self) -> KeywordProcessor:
        """Processor for thematic tags."""
        return self.build_tag_processor(THEME_TAGS)

    def build_vibe_processor(self) -> KeywordProcessor:
        """Map every form of genre, atmosphere, theme and country words to `(kind, name)`.

        Forms are also added with "ё" replaced by "е": filter extraction normalizes the text.
        """
        processor = _make_processor()
        tag_groups = (
            ("genre", GENRE_TAGS),
            ("atmosphere", ATMOSPHERE_TAGS),
            ("theme", THEME_TAGS),
            ("country", COUNTRY_ADJECTIVES),
        )
        for kind, tags in tag_groups:
            for name, lemmas in tags.items():
                for lemma in lemmas:
                    for form in self.phrase_forms(lemma):
                        processor.add_keyword(form, (kind, name))
                        processor.add_keyword(form.replace("ё", "е"), (kind, name))
        return processor

    def phrase_forms(self, phrase: str) -> set[str]:
        """Return forms of a phrase; only the last word is inflected for multi-word phrases."""
        *head, last = phrase.lower().split()
        prefix = " ".join(head)
        return {f"{prefix} {form}".strip() for form in self.word_forms(last)}

    def build_names_processor(self, names: Iterable[str]) -> KeywordProcessor:
        """Map person names (full name or inflected surname) to the canonical full name.

        Names are expected as stored in `Movie.director` / `Movie.actors`.
        """
        processor = _make_processor()
        for name in names:
            tokens = name.split()
            if not tokens:
                continue
            processor.add_keyword(name, name)
            if len(tokens) < 2:
                continue
            *given, surname = tokens
            given_forms = [self._name_forms(token) for token in given]
            for surname_form in self._name_forms(surname):
                processor.add_keyword(surname_form, name)
                for combo in product(*given_forms):
                    processor.add_keyword(" ".join((*combo, surname_form)), name)
        return processor

    def _name_forms(self, token: str) -> set[str]:
        """Return all forms of a name token, falling back to the token itself."""
        forms = {token.lower()}
        for parse in self.morph.parse(token):
            if parse.normal_form == token.lower():
                forms.update(form.word for form in parse.lexeme)
        return forms

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
