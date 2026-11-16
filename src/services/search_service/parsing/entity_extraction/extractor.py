"""Extract named entities (with Natasha) and genres from a query as plain text."""

import sys

import pymorphy3

sys.modules.setdefault("pymorphy2", pymorphy3)

from natasha import (  # noqa: E402
    Doc,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsNERTagger,
    Segmenter,
)

from src.services.search_service.parsing.dictionary_builder import DictionaryBuilder  # noqa: E402
from src.services.search_service.parsing.entity_extraction.schemas import (  # noqa: E402
    ExtractedEntities,
)


class EntityExtractor:
    """Find person/entity names and genres in a query, build entity text and cut them out."""

    def __init__(self, builder: DictionaryBuilder | None = None) -> None:
        self.genre_processor = (builder or DictionaryBuilder()).build_genre_processor()
        self.segmenter = Segmenter()
        embedding = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(embedding)
        self.ner_tagger = NewsNERTagger(embedding)
        self.morph_vocab = MorphVocab()

    def extract(self, text: str) -> ExtractedEntities:
        """Return extracted entities text and the query text without those spans."""
        spans: list[tuple[int, int, str]] = [
            (start, end, genre)
            for genre, start, end in self.genre_processor.extract_keywords(text, span_info=True)
        ]

        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        doc.tag_ner(self.ner_tagger)
        for span in doc.spans:
            if span.type == "PER":
                span.normalize(self.morph_vocab)
                spans.append((span.start, span.stop, span.normal or span.text))

        merged = self._resolve_spans(spans)
        found = list(dict.fromkeys(name for _, _, name in merged))

        pieces: list[str] = []
        last = 0
        for start, end, _ in merged:
            pieces.append(text[last:start])
            last = end
        pieces.append(text[last:])

        return ExtractedEntities(
            text=self._clean("".join(pieces)),
            entities=". ".join(found) if found else None,
        )

    @staticmethod
    def _resolve_spans(spans: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
        result: list[tuple[int, int, str]] = []
        for start, end, name in sorted(spans, key=lambda item: (item[0], -(item[1] - item[0]))):
            if not result or start >= result[-1][1]:
                result.append((start, end, name))
        return result

    @staticmethod
    def _clean(text: str) -> str:
        words = [word for word in text.split() if word.strip(",.;:-–—")]
        return " ".join(words).strip(" ,.;:-")
