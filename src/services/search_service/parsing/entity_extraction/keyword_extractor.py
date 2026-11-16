"""TF-IDF keyword extraction for identifying the most important plot terms as entities."""

from collections import Counter
from collections.abc import Iterable
from functools import lru_cache
import json
import math
from pathlib import Path
import re

from sklearn.feature_extraction.text import TfidfVectorizer

from src.core.config import settings
from src.services.search_service.parsing.dictionaries import GENRE_TAGS, STOP_WORDS
from src.services.search_service.parsing.dictionary_builder import get_morph_analyzer

_TOKEN_RE = re.compile(r"[а-яёa-z0-9-]+", re.IGNORECASE)
_CONTENT_POS = frozenset({"NOUN", "ADJF", "PRTF"})


@lru_cache(maxsize=8192)
def _lemmatize_cached(word: str) -> tuple[str, str | None]:
    parse = get_morph_analyzer().parse(word)[0]
    return parse.normal_form.replace("ё", "е"), parse.tag.POS


@lru_cache(maxsize=4)
def _build_idf_table(corpus_path_str: str) -> tuple[dict[str, float], float]:
    """Fit TfidfVectorizer on movie titles and descriptions to obtain corpus IDF weights."""
    corpus_path = Path(corpus_path_str)
    if not corpus_path.is_file():
        return {}, 1.0

    docs: list[str] = []
    with corpus_path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                movie = json.loads(line)
            except json.JSONDecodeError:
                continue
            raw_text = f"{movie.get('title', '')} {movie.get('description', '')}"
            lemmas = [
                _lemmatize_cached(token)[0]
                for token in _TOKEN_RE.findall(raw_text.lower())
                if len(token) >= 3 and not token.isdigit()
            ]
            if lemmas:
                docs.append(" ".join(lemmas))

    if len(docs) < 2:
        return {}, 1.0

    vectorizer = TfidfVectorizer(
        min_df=1,
        max_df=0.85,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[а-яёa-z0-9-]{3,}\b",
    )
    vectorizer.fit(docs)
    idf_map = {
        term: float(idf)
        for term, idf in zip(vectorizer.get_feature_names_out(), vectorizer.idf_, strict=True)
    }
    max_idf = float(vectorizer.idf_.max()) if len(vectorizer.idf_) else 1.0
    return idf_map, max_idf


class KeywordExtractor:
    """Select the highest-scoring TF-IDF thematic terms from cleaned plot text."""

    def __init__(
        self,
        corpus_path: Path | None = None,
        min_tokens: int = 3,
        max_keywords: int = 5,
        relative_threshold: float = 0.4,
    ) -> None:
        self.corpus_path = corpus_path or settings.DATA_PATH
        self.min_tokens = min_tokens
        self.max_keywords = max_keywords
        self.relative_threshold = relative_threshold
        self._stop_lemmas = frozenset(
            {w.replace("ё", "е") for w in STOP_WORDS}
            | {k.lower().replace("ё", "е") for k in GENRE_TAGS}
            | {t.lower().replace("ё", "е") for ts in GENRE_TAGS.values() for t in ts}
        )

    def extract(self, text: str | None, exclude: Iterable[str] = ()) -> list[str]:
        """Return top TF-IDF lemmas from text, or an empty list for short queries."""
        if not text or not text.strip():
            return []

        excluded_lemmas = set(self._stop_lemmas)
        for item in exclude:
            for token in _TOKEN_RE.findall(item.lower()):
                excluded_lemmas.add(_lemmatize_cached(token)[0])

        candidates: list[tuple[str, str | None]] = []
        for token in _TOKEN_RE.findall(text.lower()):
            if len(token) < 3 or token.isdigit():
                continue
            lemma, pos = _lemmatize_cached(token)
            if lemma in excluded_lemmas:
                continue
            if pos is not None and pos not in _CONTENT_POS:
                continue
            candidates.append((lemma, pos))

        if len(candidates) < self.min_tokens:
            return []

        counts = Counter(lemma for lemma, _ in candidates)
        first_pos: dict[str, str | None] = {}
        for lemma, pos in candidates:
            first_pos.setdefault(lemma, pos)

        idf_map, max_idf = _build_idf_table(str(self.corpus_path))
        min_idf = 3.2 if idf_map else 0.0

        scored: list[tuple[float, str]] = []
        for lemma, count in counts.items():
            idf = idf_map.get(lemma, max_idf)
            if idf < min_idf and count < 2:
                continue
            tf = 1.0 + math.log(count)
            pos = first_pos[lemma]
            pos_weight = 1.25 if pos == "NOUN" else 0.85
            scored.append((tf * idf * pos_weight, lemma))

        if not scored:
            return []

        max_score = max(score for score, _ in scored)
        cutoff = max_score * self.relative_threshold
        scored.sort(key=lambda item: -item[0])

        return [
            lemma
            for score, lemma in scored[: self.max_keywords]
            if score >= cutoff
        ]
