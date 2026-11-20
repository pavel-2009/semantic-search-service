"""Tests for the final parsed query."""

from src.services.search_service.parsing import text_parser
from src.services.search_service.parsing.entity_extraction import ExtractedEntities
from src.services.search_service.parsing.filter_extractor import ExtractedFilters
from src.services.search_service.parsing.vibe_extractor import ExtractedVibe


def test_parse_cleans_remaining_text_and_collects_extractions(monkeypatch) -> None:
    class StubFilterExtractor:
        def extract(self, text: str) -> ExtractedFilters:
            assert text == "entity remainder"
            return ExtractedFilters(text="unused", year_gte=1990, rating_gte=7.5)

    class StubVibeExtractor:
        def extract(self, text: str) -> ExtractedVibe:
            assert text == "unused"
            return ExtractedVibe(text=" , с про   сны, ", vibe="Мрачный.")

    class StubEntityExtractor:
        def extract(self, text: str) -> ExtractedEntities:
            assert text == "original query"
            return ExtractedEntities(text="entity remainder", entities="триллер")

    monkeypatch.setattr(text_parser, "FilterExtractor", StubFilterExtractor)
    monkeypatch.setattr(text_parser, "VibeExtractor", StubVibeExtractor)
    monkeypatch.setattr(text_parser, "EntityExtractor", StubEntityExtractor)

    parsed = text_parser.TextParser().parse("original query")

    assert parsed.plot == "сны"
    assert parsed.vibe == "Мрачный."
    assert parsed.entities == "триллер"
    assert parsed.filter == {"year_gte": 1990, "rating_gte": 7.5}


def test_parse_returns_none_for_empty_optional_values(monkeypatch) -> None:
    class StubFilterExtractor:
        def extract(self, text: str) -> ExtractedFilters:
            return ExtractedFilters(text=text)

    class StubVibeExtractor:
        def extract(self, text: str) -> ExtractedVibe:
            return ExtractedVibe(text=text)

    class StubEntityExtractor:
        def extract(self, text: str) -> ExtractedEntities:
            return ExtractedEntities(text=text)

    monkeypatch.setattr(text_parser, "FilterExtractor", StubFilterExtractor)
    monkeypatch.setattr(text_parser, "VibeExtractor", StubVibeExtractor)
    monkeypatch.setattr(text_parser, "EntityExtractor", StubEntityExtractor)

    parsed = text_parser.TextParser().parse(" , . ")

    assert parsed.plot is None
    assert parsed.vibe is None
    assert parsed.entities is None
    assert parsed.filter is None


def test_clean_plot_normalizes_whitespace_and_repeated_punctuation() -> None:
    assert text_parser.TextParser._clean_plot("  фильм , , сюжет! ") == "фильм, сюжет"


def test_parse_removes_stop_words_from_plot(monkeypatch) -> None:
    class StubFilterExtractor:
        def extract(self, text: str) -> ExtractedFilters:
            return ExtractedFilters(text=text)

    class StubVibeExtractor:
        def extract(self, text: str) -> ExtractedVibe:
            return ExtractedVibe(text=text)

    class StubEntityExtractor:
        def extract(self, text: str) -> ExtractedEntities:
            return ExtractedEntities(text=text)

    monkeypatch.setattr(text_parser, "FilterExtractor", StubFilterExtractor)
    monkeypatch.setattr(text_parser, "VibeExtractor", StubVibeExtractor)
    monkeypatch.setattr(text_parser, "EntityExtractor", StubEntityExtractor)

    parser = text_parser.TextParser()

    assert parser.parse("посоветуй пожалуйста хороший фильм про космос").plot == "космос"
    assert parser.parse("расскажи, какие фильмы посмотреть про сны").plot == "сны"
    assert parser.parse("подскажи что-нибудь интересное").plot is None


def test_parse_full_space_query_extracts_filters_titles_vibe_and_tfidf_entities() -> None:
    parser = text_parser.TextParser()
    query = (
        'Посоветуй интересные приключенческие фильмы про космос, похожие на "Интерстеллар" '
        "и \"Гравитацию\". Годов 90-х и позже. Фильмы должны быть с высоким рейтингом и "
        "хорошими отзывами. Пожалуйста, избегай фильмов с низким рейтингом и негативными "
        "отзывами. Атмосфера - захватывающая, напряжённая, с элементами научной фантастики. "
        "Жанры: приключения, научная фантастика, драма. Заставляют задуматься о будущем "
        "человечества и космоса, избегай фильмов с предсказуемым сюжетом и клишированными "
        "персонажами."
    )

    parsed = parser.parse(query)

    assert parsed.filter == {"year_gte": 1990, "rating_gte": 7.0}
    assert parsed.vibe is not None
    vibe_lower = parsed.vibe.lower()
    assert "атмосферный" in vibe_lower
    assert "динамичный" in vibe_lower
    assert "напряжённый" in vibe_lower
    assert "философский" in vibe_lower
    assert parsed.entities is not None
    for expected in ("приключения", "Интерстеллар", "Гравитация", "фантастика", "драма", "космос", "человечество"):
        assert expected in parsed.entities
    assert parsed.plot is not None
    assert "космос" in parsed.plot
    for leaked in ("годо", "отзыв", "сюжет", "персонаж", "научной", "предсказуем", "клиширован"):
        assert leaked not in parsed.plot


def test_keyword_extractor_falls_back_gracefully_when_corpus_missing(tmp_path) -> None:
    from src.services.search_service.parsing.entity_extraction import KeywordExtractor

    extractor = KeywordExtractor(corpus_path=tmp_path / "missing.jsonl")
    keywords = extractor.extract(
        "космос будущем человечества космоса космических научных космоса человечества",
        exclude=["приключения"],
    )
    assert keywords[0] == "космос"
    assert "человечество" in keywords
    assert extractor.extract("космос") == []
