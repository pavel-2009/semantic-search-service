"""Extract named entities (with Natasha), movie titles, and genres from a query."""

from functools import lru_cache
import json
from pathlib import Path
import re
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

from src.core.config import settings  # noqa: E402
from src.services.search_service.parsing.dictionaries import GENRE_TAGS, STOP_WORDS  # noqa: E402
from src.services.search_service.parsing.dictionary_builder import (  # noqa: E402
    DictionaryBuilder,
    get_morph_analyzer,
)
from src.services.search_service.parsing.entity_extraction.schemas import (  # noqa: E402
    ExtractedEntities,
)
from src.services.search_service.parsing.mood_dictionary import MOOD_TAGS  # noqa: E402

_QUOTED_TITLE_RE = re.compile(
    r"«([^»\n]{2,80})»"
    r"|„([^“\"\n]{2,80})[“\"]"
    r"|\"([^\"\n]{2,80})\""
    r"|(?<![а-яёa-z0-9])'([^'\n]{2,80})'(?![а-яёa-z0-9])"
)
_SIMILARITY_TRIGGER_RE = re.compile(
    r"(?<![а-яёa-z0-9])(?:похож\w*\s+(?:на|с)|в\s+духе|наподобие|вроде|типа|"
    r"такие\s+как|такой\s+как|как|аналог\w*|названи\w*(?:\s+которого)?)\s+",
    re.IGNORECASE,
)
_NEGATED_GENRE_RE = re.compile(
    r"(?:^|[.,;!?]\s*|\s)"
    r"(?:без|кроме|исключая|помимо|избега\w*|никак\w*|только\s+не|не)"
    r"(?:\s+(?:таких\s+жанр\w*\s+как|жанр\w*|фильм\w*))?"
    r"\s*(?:[а-яё-]+\s*(?:и|или)\s*)*$",
    re.IGNORECASE,
)
_TITLE_CONNECTORS = frozenset(
    {"по", "из", "в", "во", "на", "с", "со", "к", "о", "об", "у", "для", "от", "под", "над"}
)
_LIST_SEPARATORS_RE = re.compile(r"^\s*(?:,|и|или)\s+", re.IGNORECASE)
_TOKEN_SPAN_RE = re.compile(r"[а-яёa-z0-9-]+", re.IGNORECASE)
_HAS_LETTER_RE = re.compile(r"[а-яёa-z]", re.IGNORECASE)

_NON_PERSON_LEMMAS = frozenset(
    {w.lower().replace("ё", "е") for w in STOP_WORDS}
    | {t.lower().replace("ё", "е") for triggers in GENRE_TAGS.values() for t in triggers}
    | {t.lower().replace("ё", "е") for triggers in MOOD_TAGS.values() for t in triggers}
)


@lru_cache(maxsize=4)
def _load_known_titles(corpus_path_str: str) -> dict[str, str]:
    """Load lowercase title -> canonical title mapping from the movies dataset."""
    corpus_path = Path(corpus_path_str)
    if not corpus_path.is_file():
        return {}
    titles: dict[str, str] = {}
    with corpus_path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                movie = json.loads(line)
            except json.JSONDecodeError:
                continue
            title = str(movie.get("title", "")).strip()
            if len(title) >= 4:
                titles.setdefault(title.lower().replace("ё", "е"), title)
    return titles


def _normalize_title(raw: str) -> str:
    """Normalize an inflected Russian movie title to nominative while preserving proper casing."""
    cleaned = " ".join(raw.split()).strip(" ,.;:!?\"'«»„“")
    if not cleaned:
        return ""
    words = cleaned.split()
    morph = get_morph_analyzer()
    first_parse = morph.parse(words[0])[0]
    first_is_adj = first_parse.tag.POS in {"ADJF", "PRTF"}

    normalized: list[str] = []
    for idx, word in enumerate(words):
        if word.isascii() or not any(ch.isalpha() for ch in word):
            normalized.append(word)
            continue
        parse = morph.parse(word)[0]
        should_inflect = (idx == 0 or (idx == 1 and first_is_adj)) and parse.is_known and "nomn" not in parse.tag
        if should_inflect:
            nom = parse.inflect({"nomn"})
            form = nom.word if nom else parse.normal_form
            if word[0].isupper() and not word.isupper():
                form = form.capitalize()
            elif idx == 0 and word[0].islower():
                form = form.capitalize()
            normalized.append(form)
        elif idx == 0 and word[0].islower() and not word.isupper():
            normalized.append(word.capitalize())
        else:
            normalized.append(word)
    return " ".join(normalized)


def _is_valid_title_candidate(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 2 or not _HAS_LETTER_RE.search(stripped):
        return False
    words = stripped.split()
    if not (1 <= len(words) <= 7):
        return False
    lower_norm = stripped.lower().replace("ё", "е")
    if len(words) == 1 and lower_norm in _NON_PERSON_LEMMAS:
        return False
    return True


class EntityExtractor:
    """Find person/entity names, movie titles and genres in a query, and cut them out."""

    def __init__(
        self,
        builder: DictionaryBuilder | None = None,
        corpus_path: Path | None = None,
    ) -> None:
        self.genre_processor = (builder or DictionaryBuilder()).build_genre_processor()
        self.corpus_path = corpus_path or settings.DATA_PATH
        self.segmenter = Segmenter()
        embedding = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(embedding)
        self.ner_tagger = NewsNERTagger(embedding)
        self.morph_vocab = MorphVocab()
        self.morph = get_morph_analyzer()

    def extract(self, text: str) -> ExtractedEntities:
        """Return extracted entities text and the query text without those spans."""
        # Spans carry (start, end, priority, canonical_name | None).
        # None removes a negated entity span from text without adding it to entities.
        spans: list[tuple[int, int, int, str | None]] = []

        for genre, start, end in self.genre_processor.extract_keywords(text, span_info=True):
            name = None if self._is_negated_genre(text, start) else genre
            spans.append((start, end, 3, name))

        for start, end, title in self._extract_quoted_titles(text):
            spans.append((start, end, 3, title))

        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        doc.tag_ner(self.ner_tagger)
        for span in doc.spans:
            if span.type == "PER" and self._is_valid_person(span.text):
                span.normalize(self.morph_vocab)
                normal = (span.normal or span.text).strip()
                if not self._is_non_entity_phrase(normal):
                    spans.append((span.start, span.stop, 2, normal))

        for start, end, title in self._extract_unquoted_titles(text):
            spans.append((start, end, 1, title))

        merged = self._resolve_spans(spans)
        found = list(dict.fromkeys(name for _, _, _, name in merged if name is not None))

        pieces: list[str] = []
        last = 0
        for start, end, _, _ in merged:
            pieces.append(text[last:start])
            last = end
        pieces.append(text[last:])

        return ExtractedEntities(
            text=self._clean("".join(pieces)),
            entities=". ".join(found) if found else None,
        )

    @staticmethod
    def _is_negated_genre(text: str, start: int) -> bool:
        window_start = max(0, start - 60)
        prefix = text[window_start:start]
        return bool(_NEGATED_GENRE_RE.search(prefix))

    @staticmethod
    def _is_valid_person(span_text: str) -> bool:
        return any(ch.isupper() for ch in span_text)

    def _is_non_entity_phrase(self, phrase: str) -> bool:
        tokens = _TOKEN_SPAN_RE.findall(phrase.lower())
        if not tokens:
            return True
        lemmas = [self.morph.parse(t)[0].normal_form.replace("ё", "е") for t in tokens]
        return all(lemma in _NON_PERSON_LEMMAS for lemma in lemmas)

    def _extract_quoted_titles(self, text: str) -> list[tuple[int, int, str]]:
        titles: list[tuple[int, int, str]] = []
        for match in _QUOTED_TITLE_RE.finditer(text):
            inner = next(group for group in match.groups() if group is not None).strip()
            if not _is_valid_title_candidate(inner):
                continue
            normalized = _normalize_title(inner)
            if normalized:
                titles.append((match.start(), match.end(), normalized))
        return titles

    def _extract_unquoted_titles(self, text: str) -> list[tuple[int, int, str]]:
        """Extract unquoted movie titles appearing after similarity/reference cues."""
        titles: list[tuple[int, int, str]] = []
        known_titles = _load_known_titles(str(self.corpus_path))

        for trigger in _SIMILARITY_TRIGGER_RE.finditer(text):
            pos = trigger.end()
            while pos < len(text):
                matched_known = self._match_known_title_at(text, pos, known_titles)
                if matched_known is not None:
                    end_pos, canonical = matched_known
                    titles.append((pos, end_pos, canonical))
                    pos = end_pos
                else:
                    matched_cap = self._match_capitalized_title_at(text, pos)
                    if matched_cap is None:
                        break
                    end_pos, raw_title = matched_cap
                    if _is_valid_title_candidate(raw_title) and not self._is_non_entity_phrase(raw_title):
                        titles.append((pos, end_pos, _normalize_title(raw_title)))
                    pos = end_pos

                sep = _LIST_SEPARATORS_RE.match(text[pos:])
                if not sep:
                    break
                pos += sep.end()

        return titles

    @staticmethod
    def _match_known_title_at(
        text: str, pos: int, known_titles: dict[str, str]
    ) -> tuple[int, str] | None:
        if not known_titles:
            return None
        segment = text[pos : pos + 80]
        tokens = list(_TOKEN_SPAN_RE.finditer(segment))
        for count in range(min(len(tokens), 6), 0, -1):
            candidate = segment[: tokens[count - 1].end()]
            if not candidate.strip():
                continue
            key = " ".join(candidate.lower().replace("ё", "е").split())
            if key in known_titles:
                return pos + tokens[count - 1].end(), known_titles[key]
        return None

    def _match_capitalized_title_at(self, text: str, pos: int) -> tuple[int, str] | None:
        segment = text[pos : pos + 100]
        if not segment or segment[0] in "\"'«„":
            return None

        # Only consume contiguous tokens on the same clause (stop at punctuation/newlines).
        clause_match = re.match(r"[^\n,.;:!?]+", segment)
        if not clause_match:
            return None
        clause = clause_match.group(0)

        tokens = list(_TOKEN_SPAN_RE.finditer(clause))
        if not tokens:
            return None

        first_tok = tokens[0]
        if first_tok.start() != 0:
            return None
        first_word = first_tok.group(0)
        if not any(ch.isupper() for ch in first_word):
            return None

        first_pos = self.morph.parse(first_word)[0].tag.POS
        last_idx = 0
        idx = 1
        while idx < len(tokens) and idx < 6:
            between = clause[tokens[idx - 1].end() : tokens[idx].start()]
            if not between.strip() == "":
                break
            word = tokens[idx].group(0)
            lower = word.lower()
            if any(ch.isupper() for ch in word) or (word.isdigit() and len(word) <= 4):
                last_idx = idx
                idx += 1
            elif (
                idx == 1
                and first_pos in {"ADJF", "PRTF"}
                and self.morph.parse(lower)[0].tag.POS == "NOUN"
                and lower not in _NON_PERSON_LEMMAS
                and lower not in {"и", "или"}
            ):
                last_idx = idx
                idx += 1
            elif lower in _TITLE_CONNECTORS and idx + 1 < len(tokens):
                next_word = tokens[idx + 1].group(0)
                next_between = clause[tokens[idx].end() : tokens[idx + 1].start()]
                if next_between.strip() == "" and (
                    any(ch.isupper() for ch in next_word)
                    or next_word.isdigit()
                    or (
                        self.morph.parse(next_word.lower())[0].tag.POS == "NOUN"
                        and next_word.lower() not in _NON_PERSON_LEMMAS
                        and idx + 2 < len(tokens)
                        and tokens[idx + 2].group(0).isdigit()
                    )
                ):
                    last_idx = idx + 1
                    idx += 2
                    continue
                break
            else:
                break

        end = pos + tokens[last_idx].end()
        return end, text[pos:end]

    @staticmethod
    def _resolve_spans(
        spans: list[tuple[int, int, int, str | None]],
    ) -> list[tuple[int, int, int, str | None]]:
        # Sort by priority descending first so high-confidence entities (genres, quoted titles, PER)
        # claim their spans before lower-priority unquoted title candidates.
        chosen: list[tuple[int, int, int, str | None]] = []
        for span in sorted(spans, key=lambda item: (-item[2], item[0], -(item[1] - item[0]))):
            start, end, _, _ = span
            if all(end <= c_start or start >= c_end for c_start, c_end, _, _ in chosen):
                chosen.append(span)
        chosen.sort(key=lambda item: item[0])
        return chosen

    @staticmethod
    def _clean(text: str) -> str:
        words = [word for word in text.split() if word.strip(",.;:-–—")]
        return " ".join(words).strip(" ,.;:-")
