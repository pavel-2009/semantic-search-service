"""Tests for year and rating rules of FilterExtractor."""

import pytest

from src.services.search_service.parsing.filter_extractor import ExtractedFilters, FilterExtractor

extractor = FilterExtractor(current_year=2026)


def years(text: str) -> tuple[int | None, int | None]:
    result = extractor.extract(text)
    return result.year_gte, result.year_lte


def rating(text: str) -> tuple[float | None, float | None]:
    result = extractor.extract(text)
    return result.rating_gte, result.rating_lte


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("фильм 2014 года", (2014, 2014)),
        ("в 2014 году", (2014, 2014)),
        ("с 2005 по 2015", (2005, 2015)),
        ("от 2010 до 2020", (2010, 2020)),
        ("между 2000 и 2010", (2000, 2010)),
        ("2010-2020", (2010, 2020)),
        ("после 2010", (2011, None)),
        ("с 2010 года", (2010, None)),
        ("начиная с 2012", (2012, None)),
        ("2015 и новее", (2015, None)),
        ("до 2000", (None, 1999)),
        ("до 2000 включительно", (None, 2000)),
        ("не позже 2000", (None, 2000)),
        ("1999 и раньше", (None, 1999)),
        ("фильмы 90-х", (1990, 1999)),
        ("в 80е", (1980, 1989)),
        ("2000-х", (2000, 2009)),
        ("восьмидесятые", (1980, 1989)),
        ("нулевые", (2000, 2009)),
        ("начало 2000-х", (2000, 2003)),
        ("конец 90-х", (1997, 1999)),
        ("последние 5 лет", (2022, None)),
        ("за последние три года", (2024, None)),
        ("в этом году", (2026, 2026)),
        ("в прошлом году", (2025, 2025)),
        ("свежее", (2022, None)),
        ("классика", (None, 1989)),
        ("просто фильм", (None, None)),
        ("в 3000 году", (None, None)),
        ("годов 90-х и позже", (1990, None)),
        ("90-е и новее", (1990, None)),
        ("80-х и раньше", (None, 1989)),
        ("после 90-х", (2000, None)),
        ("до 90-х", (None, 1989)),
        ("до 90-х включительно", (None, 1999)),
        ("с 80-х по 90-е", (1980, 1999)),
        ("комедии 80-х или 90-х годов", (1980, 1999)),
        ("двухтысячных годов", (2000, 2009)),
        ("за последний год", (2025, 2025)),
        ("за последнее время", (2022, None)),
        ("21 век", (2001, None)),
        ("не хочу старые фильмы", (1990, None)),
        ("не хочу старые фильмы, с 2010 года и новее", (2010, None)),
        ("без свежих фильмов", (None, None)),
    ],
)
def test_year_rules(text: str, expected: tuple[int | None, int | None]) -> None:
    assert years(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("рейтинг выше 7.5", (7.5, None)),
        ("с рейтингом не ниже 8", (8.0, None)),
        ("оценка 7,5", (7.5, None)),
        ("рейтинг от 7 до 9", (7.0, 9.0)),
        ("оценка 6-8", (6.0, 8.0)),
        ("рейтинг 8+", (8.0, None)),
        ("8+", (8.0, None)),
        ("оценка 8 и выше", (8.0, None)),
        ("7 из 10", (7.0, None)),
        ("рейтинг ниже 5", (None, 5.0)),
        ("оценка до 6", (None, 6.0)),
        ("высокий рейтинг", (7.0, None)),
        ("низкий рейтинг", (None, 5.0)),
        ("рейтинг 15", (None, None)),
        ("без рейтинга", (None, None)),
        ("с высоким рейтингом и хорошими отзывами", (7.0, None)),
        ("избегай фильмов с низким рейтингом и негативными отзывами", (6.0, None)),
        ("с высоким рейтингом, избегай фильмов с низким рейтингом", (7.0, None)),
        ("избегай фильмов с рейтингом ниже 6", (6.0, None)),
        ("не обязательно с высоким рейтингом", (None, None)),
        ("рейтинг >= 8", (8.0, None)),
        ("положительные отзывы", (7.0, None)),
    ],
)
def test_rating_rules(text: str, expected: tuple[float | None, float | None]) -> None:
    assert rating(text) == expected


def test_matched_phrases_are_removed_from_text() -> None:
    result = extractor.extract("Комедия 90-х с рейтингом выше 7.5, про друзей")
    assert (result.year_gte, result.year_lte) == (1990, 1999)
    assert result.rating_gte == 7.5
    assert result.text == "комедия, про друзей"


def test_year_and_rating_do_not_interfere() -> None:
    result = extractor.extract("триллер с 2005 по 2015 рейтинг 7-9")
    assert (result.year_gte, result.year_lte) == (2005, 2015)
    assert (result.rating_gte, result.rating_lte) == (7.0, 9.0)
    assert result.text == "триллер"


def test_no_filters_returns_normalized_text() -> None:
    result = extractor.extract("Что-нибудь про Ёжика")
    assert result == ExtractedFilters(text="что-нибудь про ежика")


def test_decade_prefix_godov_is_cleanly_removed() -> None:
    result = extractor.extract("Фильмы годов 90-х и позже про космос")
    assert (result.year_gte, result.year_lte) == (1990, None)
    assert result.text == "фильмы про космос"
